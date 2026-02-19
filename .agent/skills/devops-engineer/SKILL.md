---
name: devops-engineer
description: Utilizza questa skill per gestire l'infrastruttura del progetto, configurare l'ambiente di sviluppo locale, gestire le dipendenze Python, implementare la sicurezza dei segreti (secrets management), definire lo schema del database Supabase e automatizzare il deploy CI/CD su Streamlit Cloud.
---

# DEVOPS_ENGINEER.MD

## 1. Project Architecture Blueprint

L'architettura è progettata per disaccoppiare l'interfaccia (Streamlit), la logica (OR-Tools) e i dati (Supabase). Questo previene la creazione di "God Objects" (file giganti ingestibili).

### File System Structure

```text
openshift-scheduler/
│
├── .gitignore               # Esclusioni Git (CRITICO: contiene venv e secrets)
├── README.md                # Documentazione di onboarding
├── requirements.txt         # Dipendenze di produzione (pip freeze)
│
├── .streamlit/              # Configurazione locale Streamlit
│   └── secrets.toml         # Chiavi API locali (NON COMMISSARE MAI)
│
├── venv/                    # Ambiente virtuale Python (creato localmente)
│
└── src/                     # Source Code (Package Python)
    ├── __init__.py
    ├── main.py              # Entry Point: Avvia l'app Streamlit
    │
    ├── models/              # DATA DOMAIN (Classi & Schemi)
    │   ├── __init__.py
    │   ├── employee.py      # Dataclasses per Dipendenti
    │   └── shift.py         # Enum e costanti per i Turni
    │
    ├── database/            # INFRASTRUCTURE LAYER (Supabase)
    │   ├── __init__.py
    │   ├── client.py        # Singleton connessione Supabase
    │   └── repository.py    # Pattern Repository (CRUD methods)
    │
    ├── engine/              # BUSINESS LOGIC (Solver OR-Tools)
    │   ├── __init__.py
    │   ├── solver.py        # Orchestratore del processo di calcolo
    │   ├── constraints.py   # Definizione vincoli (Hard/Soft)
    │   └── objectives.py    # Funzioni di costo (Penalità)
    │
    └── ui/                  # PRESENTATION LAYER (Streamlit Views)
        ├── __init__.py
        ├── components.py    # Widget riutilizzabili (Cards, Metrics)
        ├── styles.py        # Custom CSS/Layout settings
        ├── view_admin.py    # Pagina di gestione e generazione
        └── view_roster.py   # Pagina di visualizzazione griglia

```

---

## 2. Environment Setup (Local Development)

Ogni sviluppatore deve seguire rigorosamente questa procedura per garantire la consistenza dell'ambiente.

### Prerequisiti

* Python 3.10 o superiore installato.
* Git installato.

### Inizializzazione Ambiente

Eseguire nel terminale (root del progetto):

```bash
# 1. Creazione Virtual Environment
python -m venv venv

# 2. Attivazione (Windows)
.\venv\Scripts\activate
# 2. Attivazione (Mac/Linux)
# source venv/bin/activate

# 3. Aggiornamento pip
pip install --upgrade pip

# 4. Installazione Dipendenze
pip install -r requirements.txt

```

---

## 3. Dependency Management (`requirements.txt`)

Il file `requirements.txt` definisce lo stack tecnologico.

```text
streamlit>=1.30.0     # Frontend Framework
supabase>=2.3.0       # Database Client
ortools>=9.8.0        # Optimization Engine (Google)
pandas>=2.1.0         # Data Manipulation
python-dotenv>=1.0.0  # Environment Variables management
plotly>=5.18.0        # Interactive Charts
xlsxwriter>=3.1.0     # Excel Export Engine
watchdog>=3.0.0       # Hot-reload in dev (opzionale ma utile)

```

---

## 4. Security & Configuration Management

La gestione dei segreti (API Keys, Password) avviene tramite variabili d'ambiente. **Nessuna password deve mai essere scritta nel codice `.py`.**

### Sviluppo Locale (`.streamlit/secrets.toml`)

Creare questo file manualmente (è ignorato da Git).

```toml
# .streamlit/secrets.toml

[supabase]
url = "INSERISCI_URL_SUPABASE_QUI"
key = "INSERISCI_KEY_ANON_QUI"

[admin]
password = "PASSWORD_SICURA_ADMIN" # Usata per sbloccare la modalità edit

```

### Produzione (Streamlit Community Cloud)

Nella dashboard di deploy, copiare il contenuto di `secrets.toml` nella sezione **"Advanced Settings" -> "Secrets"**.

### `.gitignore` (Firewall contro errori umani)

Il file `.gitignore` deve contenere tassativamente:

```gitignore
# Python artifacts
__pycache__/
*.py[cod]
*$py.class
*.so

# Environments
.env
.venv
env/
venv/
ENV/

# Streamlit
.streamlit/secrets.toml

# IDE & OS
.idea/
.vscode/
.DS_Store

```

---

## 5. Database Schema (Supabase/PostgreSQL)

Poiché non usiamo un ORM pesante (come SQLAlchemy) per mantenere leggerezza, lo schema è definito in SQL puro. Eseguire questo script nell'**SQL Editor** di Supabase una tantum.

```sql
-- 1. Setup Tabelle Base
CREATE TABLE IF NOT EXISTS employees (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    matricola TEXT UNIQUE NOT NULL,
    nome_cognome TEXT NOT NULL,
    ruolo TEXT CHECK (ruolo IN ('INF', 'OSS')),
    team_id INTEGER, -- Identifica la "Tripletta" (1-5)
    limitazione_notte BOOLEAN DEFAULT FALSE,
    attivo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shift_types (
    codice TEXT PRIMARY KEY,
    peso_orario NUMERIC(4, 2) NOT NULL,
    descrizione TEXT
);

-- Popolamento Turni Standard
INSERT INTO shift_types (codice, peso_orario, descrizione) VALUES
('1', 7.0, 'Mattina'), ('K', 7.0, 'Pomeriggio'), ('N', 10.0, 'Notte'),
('S', 0.0, 'Smonto'), ('R', 0.0, 'Riposo'),
('F', 6.0, 'Ferie'), ('M', 6.0, 'Malattia'), ('104', 6.0, 'Legge 104'), ('P', 6.0, 'Permesso')
ON CONFLICT DO NOTHING;

-- 2. Tabella Operativa (Turni)
CREATE TABLE IF NOT EXISTS roster (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    employee_id UUID REFERENCES employees(id),
    data DATE NOT NULL,
    shift_code TEXT REFERENCES shift_types(codice),
    is_locked BOOLEAN DEFAULT FALSE, -- Se TRUE, il solver non tocca questo turno
    UNIQUE(employee_id, data)
);

-- 3. Tabella Richieste
CREATE TABLE IF NOT EXISTS requests (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    employee_id UUID REFERENCES employees(id),
    data_inizio DATE NOT NULL,
    data_fine DATE NOT NULL,
    tipo TEXT CHECK (tipo IN ('Ferie', 'Malattia', '104', 'Permesso')),
    stato TEXT DEFAULT 'Approvato',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

```

---

## 6. CI/CD Pipeline (Deployment)

Il deploy è automatizzato tramite l'integrazione nativa Streamlit-GitHub.

1. **Commit & Push:** Lo sviluppatore esegue il push sul branch `main`.
2. **Streamlit Cloud Hook:** Rileva la modifica.
3. **Build:**
* Provisioning del container.
* `pip install -r requirements.txt`.


4. **Run:** Esecuzione di `streamlit run src/main.py`.

### Istruzioni per il primo Deploy

1. Andare su [share.streamlit.io](https://share.streamlit.io).
2. "New App" -> Selezionare Repository e Branch (`main`).
3. **Main file path:** Inserire `src/main.py` (Importante! Non è nella root).
4. Aprire "Advanced Settings" e incollare i Secrets.
5. Cliccare "Deploy".

---

## 7. Verifica e Testing

Per verificare che l'ambiente sia configurato correttamente prima di iniziare a scrivere codice complesso:

1. Creare un file `src/main.py` di test:
```python
import streamlit as st
import supabase
st.write("Environment check: OK")

```


2. Eseguire `streamlit run src/main.py`.
3. Se il browser si apre e mostra "Environment check: OK", la configurazione è valida.