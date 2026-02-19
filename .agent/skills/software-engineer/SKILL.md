---
name: software-engineer
description: prendere i requisiti (PM), l'infrastruttura (DevOps) e i vincoli di sicurezza (Security) e trasformarli in un **disegno tecnico dettagliato**.Ecco il `software_engineer.MD`. Qui definiamo *come* gli oggetti interagiscono, *come* funziona matematicamente il solver e *come* gestiamo lo stato dell'applicazione.
---

---

# SOFTWARE_ENGINEER.MD

## 1. Design Pattern & Architettura

Adotteremo un'architettura **Layered (a strati)** adattata per Streamlit.
Poiché Streamlit non ha un vero frontend/backend separato (gira tutto in un unico script Python), la separazione logica è vitale.

1. **Presentation Layer (UI):** Gestisce solo l'input utente e la visualizzazione. Non fa calcoli.
2. **Service Layer (Controller):** Orchesra la logica. Chiama il DB, chiama il Solver, gestisce la sessione.
3. **Domain Layer (Model):** Le classi pure (`Employee`, `Shift`) e le regole di business (es. "calcolo saldo ore").
4. **Data Layer (Repository):** Parla con Supabase.

---

## 2. Domain Modeling (Classi Core)

Useremo le Python `dataclasses` per definire i nostri oggetti. Sono leggere e tipizzate.

### A. `Employee`

```python
@dataclass
class Employee:
    id: str
    matricola: str
    nome: str
    ruolo: str # Enum: INF, OSS
    team_id: int # 1-5 (Per la tripletta)
    limitazione_notte: bool
    
    @property
    def target_hours_mensile(self, giorni_lavorativi: int) -> float:
        return giorni_lavorativi * 6.0

```

### B. `Shift` (Value Object)

```python
@dataclass(frozen=True)
class Shift:
    code: str # '1', 'K', 'N', ...
    weight: float # 7.0, 10.0
    is_absence: bool # True se F, M, 104

```

### C. `RosterEntry` (L'atomo del calendario)

```python
@dataclass
class RosterEntry:
    employee_id: str
    date: datetime.date
    shift_code: str
    is_locked: bool # Se True, il solver non può toccarlo

```

---

## 3. Solver Engineering (OR-Tools Implementation)

Questa è la parte più complessa. Tradurremo i vincoli in **Constraint Programming (CP-SAT)**.

### Variabili Decisionali

Il solver lavora su una matrice tridimensionale di booleani:


* : Dipendente
* : Giorno del mese
* : Tipo di turno (1, K, N, S, R...)

Se , allora Rossi fa Mattina il giorno 15.

### Definizione Matematica dei Vincoli

1. **Esattamente un turno al giorno:**



*(Nota: Riposo e Smonto sono considerati "turni" nel modello matematico)*
2. **Copertura Minima (Hard):**


3. **Rotazione Tripletta (Soft - Costo P):**
Definiamo la funzione `get_ideal_shift(team_id, date)`.
Se il turno assegnato non è quello ideale, aggiungi penalità .


4. **No Mattina dopo Notte (Hard):**
Se , allora .
Implica che  deve essere 0.

### Interfaccia Solver

```python
class ShiftSolver:
    def __init__(self, employees: List[Employee], days: List[date]):
        self.model = cp_model.CpModel()
        # ... init variables ...

    def add_hard_constraints(self, min_coverage: dict):
        # ... logic ...

    def add_soft_constraints(self, ideal_matrix: dict):
        # ... logic ...

    def solve(self) -> List[RosterEntry]:
        # Returns optimized roster or raises InfeasibleException

```

---

## 4. State Management (Streamlit Session)

Streamlit ricarica l'intera pagina a ogni click. Se non gestiamo lo stato, faremo 100 chiamate al DB inutilmente.

**Pattern: Singleton State Manager**

```python
# src/ui/state.py
class AppState:
    def __init__(self):
        if 'roster_cache' not in st.session_state:
            st.session_state.roster_cache = None
        if 'employees' not in st.session_state:
            st.session_state.employees = []

    def load_data(self):
        # Chiama il repository solo se la cache è vuota
        if not st.session_state.employees:
             st.session_state.employees = repo.get_all_employees()

```

---

## 5. Diagramma di Sequenza: "Genera Turno"

1. **Admin** clicca "Genera".
2. **Controller** recupera `employees` e `requests` (assenze) dal DB.
3. **Controller** istanzia `ShiftSolver`.
4. **Solver** costruisce il modello matematico CP-SAT.
5. **Solver** cerca la soluzione ottimale (max 180 sec).
6. **Solver** restituisce una lista di `RosterEntry`.
7. **Controller** salva la lista su Supabase (sovrascrivendo i turni non bloccati).
8. **UI** si aggiorna leggendo i nuovi dati.

---

## 6. Gestione Errori e Edge Cases

* **Infeasibility (Impossibile trovare soluzione):**
* Il solver potrebbe dire "Non posso mettere 2 infermieri la notte del 15 perché sono tutti in malattia".
* *Soluzione:* Il codice deve catturare l'eccezione e mostrare all'Admin: "Conflitto critico il giorno 15. Riduci i vincoli o sposta le ferie".


* **Race Conditions:**
* Due admin modificano lo stesso turno?
* *Mitigazione:* Grazie al timestamp di Supabase e RLS, l'ultima scrittura vince (Last Write Wins). Per ora accettabile.
