---
name: project-manager
description: Utilizza questa skill per gestire il progetto, pianificando le attività, assegnando responsabilità, monitorando lo stato e creando documentazione.
--- 

# PROJECT_MANAGER.MD

## 1. Scheda Progetto

* **Nome Progetto:** OpenShift Scheduler (OSS-Manager)
* **Obiettivo:** Automazione turni ospedalieri con vincoli complessi e costo zero.
* **Stakeholder:** Admin (Caposala/Coordinatore), Observer (Personale).
* **Licenza:** Proprietaria (Codice privato) / Open Source (Librerie usate).
* **Stato:** Pianificazione completata. Pronto per lo Sviluppo.

---

## 2. Architettura Tecnica (Zero Cost Stack)

L'infrastruttura è progettata per essere totalmente gratuita (Free Tier), sicura e accessibile da remoto.

| Componente | Tecnologia Scelta | Motivazione |
| --- | --- | --- |
| **Frontend/App** | **Streamlit** (Python) | Sviluppo rapido, interattivo, mobile-friendly, niente HTML/CSS/JS manuale. |
| **Backend Logic** | **Python 3.10+** | Necessario per *Google OR-Tools* e manipolazione dati complessa. |
| **Database** | **Supabase** (PostgreSQL) | Persistenza dati relazionale, Free tier generoso (500MB), Real-time capable. |
| **Solver Engine** | **Google OR-Tools** | Libreria CP-SAT (Constraint Programming) per ottimizzazione combinatoria. |
| **Hosting** | **Streamlit Community Cloud** | Hosting gratuito, CI/CD integrato con GitHub. Supporta repo privati. |
| **Auth/Security** | **Streamlit Secrets** + **Supabase Auth** | Gestione credenziali sicura (non nel codice). |

---

## 3. Modellazione Dati (Schema Database)

Il database (PostgreSQL su Supabase) avrà le seguenti tabelle principali:

### 3.1 `employees` (Anagrafica)

* `id` (UUID, PK)
* `matricola` (String, Unique)
* `nome_cognome` (String)
* `ruolo` (Enum: 'INF', 'OSS')
* `team_id` (Int - Riferimento alla "Tripletta": 1, 2, 3, 4, 5)
* `limitazione_notte` (Boolean - Default: False)
* `attivo` (Boolean - Default: True)

### 3.2 `shift_types` (Configurazione Turni)

* `codice` (PK: '1', 'K', 'N', 'S', 'R', 'F', 'M', '104', 'P')
* `peso_orario` (Float: es. 7.0, 10.0, 6.0)
* `descrizione` (String)

### 3.3 `roster` (Tabella dei Turni Assegnati)

* `id` (PK)
* `employee_id` (FK)
* `data` (Date)
* `shift_code` (FK -> shift_types)
* `is_locked` (Boolean - Se True, il solver non può modificare questo turno manualmente forzato)

### 3.4 `requests` (Assenze e Desiderata)

* `id` (PK)
* `employee_id` (FK)
* `data_inizio` (Date)
* `data_fine` (Date)
* `tipo` (Enum: 'Ferie', 'Malattia', '104', 'Permesso')
* `stato` (Enum: 'Richiesto', 'Approvato', 'Rifiutato')

---

## 4. Specifiche dell'Algoritmo (OR-Tools)

Il motore di calcolo è il cuore del sistema. Non è un semplice script procedurale, ma un **modello di vincoli (CP-SAT)**.

### 4.1 Definizione del Ciclo "Matrice Ideale"

L'algoritmo calcola il turno ideale basandosi sul `team_id` e sul giorno dell'anno (modulo 5).

* Sequenza: `1 (Matt) -> K (Pom) -> N (Notte) -> S (Smonto) -> R (Riposo)`.
* *Obiettivo Soft:* Assegnare al dipendente il turno previsto dalla matrice.
* *Deviazione:* Se il dipendente viene spostato dalla matrice (es. per coprire una malattia altrui), paga un costo di penalità, ma è permesso.

### 4.2 Gerarchia dei Vincoli e Penalità (Cost Function)

Il solver cercherà di minimizzare la somma totale delle penalità.

**A. Hard Constraints (Penalità: INFINITO - Inviolabili)**

1. **Copertura Minima:**
* Mattina: Min 2 INF (+ OSS variabile)
* Pomeriggio: Min 2 INF (+ OSS variabile)
* Notte: Min 2 INF (+ 1 OSS)


2. **Riposo Biologico:** Nessun turno dopo la Notte se non Smonto (`N -> S` obbligatorio).
3. **11 Ore:** Vietato `K -> 1` (Pomeriggio -> Mattina successiva).
4. **Limitazioni Salute:** Se `limitazione_notte = True`, turno `N` vietato.
5. **Assenze Garantite:** Malattia e L.104 sono intoccabili (fissati come `locked`).

**B. Soft Constraints (Penalità Variabile - Ottimizzabili)**

1. **Negare Ferie Approvate:** Costo **100.000** (Estrema ratio).
* *Nota:* L'algoritmo preferirà rivoluzionare mezza turnazione (costo basso cumulativo) piuttosto che negare un giorno di ferie.


2. **Negare Permesso:** Costo **50.000**.
3. **Rottura Matrice (Fuori Tripletta):** Costo **100** per ogni turno diverso dall'ideale.
4. **Sbilanciamento Ore (Target 36h):** Costo **10** per ogni ora di deviazione dalla media.
5. **Consecutività:** Costo **500** se > 7 giorni di lavoro consecutivo (senza R o S).

### 4.3 Strategia di Ricerca

Il solver non si ferma alla prima soluzione trovata ("First Solution").

* Imposteremo un **Time Limit** (es. 60 secondi).
* In questo tempo, il solver esplorerà milioni di combinazioni per trovare quella con il "Costo Totale" più basso (quindi quella che garantisce ferie e matrice al maggior numero di persone possibile).

---

## 5. UI/UX Workflow (Streamlit)

### Pagina 1: Dashboard & Input

* **Sidebar:** Selettore Mese/Anno, Upload Assenze massivo (CSV/Excel).
* **KPI Panel:** Visualizzazione rapida "Giorni scoperti", "Ferie a rischio".
* **Action:** Bottone gigante "GENERA TURNI".

### Pagina 2: Interactive Roster (Output)

* **Visualizzazione:** `st.data_editor`. Una griglia tipo Excel modificabile.
* Righe: Dipendenti.
* Colonne: Giorni del mese.
* Celle: Codici turno colorati (1=Giallo, N=Blu, R=Grigio, F=Rosso).


* **Modifica Manuale:** L'Admin clicca su una cella e cambia `1` in `F`.
* **Live Validation:** Al cambio manuale, un pannello laterale ricalcola istantaneamente: "Attenzione! Giorno 12 Mattina: Solo 1 Infermiere (Violazione Minimo)".

### Pagina 3: Statistiche & Export

* Grafici a barre del saldo ore per dipendente.
* Export in Excel/PDF formattato per la stampa in reparto.

---

## 6. Roadmap di Sviluppo

### Fase 1: Setup & Data Layer

* Creazione Repo GitHub (Private) e progetto Supabase.
* Script Python per creare le tabelle su Supabase.
* Interfaccia Streamlit base per inserimento/visualizzazione dipendenti (CRUD).

### Fase 2: Il Motore

* Implementazione logica OR-Tools.
* Traduzione dei vincoli "Tripletta" e "Copertura" in codice.
* Test su dati fittizi (Scenario: "Tutti in ferie a Ferragosto" -> vedere come reagisce).

### Fase 3: Integrazione UI 

* Collegamento Frontend -> Solver.
* Visualizzazione griglia risultati.
* Gestione dei messaggi di errore (es. "Impossibile coprire la notte del 15").

### Fase 4: Refinement & Deploy 

* Aggiunta funzionalità Export Excel.
* Deploy su Streamlit Community Cloud.
* Test con dati reali del mese precedente per verifica correttezza.
