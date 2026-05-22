import streamlit as st
from src.database.repository import EmployeeRepository
from src.models.employee import Employee
from src.ui.state import AppState

def render_employees_view():
    st.header("Gestione Dipendenti (Anagrafica)")
    
    repo = EmployeeRepository()
    state = AppState()
    
    # 1. New Employee Form
    with st.expander("Aggiungi Nuovo Dipendente", expanded=False):
        with st.form("new_employee_form"):
            col1, col2 = st.columns(2)
            matricola = col1.text_input("Matricola")
            nome = col2.text_input("Nome e Cognome")
            ruolo = col1.selectbox("Ruolo", ["INF", "OSS"])
            team_id = col2.number_input("Team ID (1-50)", min_value=1, max_value=50, value=1)
            notte_lim = st.checkbox("Limitazione Notte")
            
            if st.form_submit_button("Salva"):
                if matricola and nome:
                    new_emp = Employee(
                        matricola=matricola,
                        nome_cognome=nome,
                        ruolo=ruolo,
                        team_id=team_id,
                        limitazione_notte=notte_lim
                    )
                    try:
                        repo.create_employee(new_emp)
                        st.success(f"Dipendente {nome} creato con successo!")
                        # Force refresh
                        state.employees = [] # invalidate cache to reload
                        state.load_employees()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore creazione: {e}")
                else:
                    st.warning("Compila tutti i campi obbligatori.")

    # 2. List Employees (Editable)
    st.subheader("Elenco Dipendenti Attivi")
    state.load_employees()
    employees = state.employees
    
    if not employees:
        st.info("Nessun dipendente trovato.")
    else:
        # Prepare Dataframe-like structure for editor
        # Only show editable fields + ID (hidden/index)
        # Using dict for simplicity
        
        # Map objects to dict list
        emp_data = []
        for e in employees:
            emp_data.append({
                "ID": e.id,
                "Matricola": e.matricola,
                "Nome": e.nome_cognome,
                "Ruolo": e.ruolo,
                "Team": e.team_id,
                "Limitazione Notte": e.limitazione_notte,
                "Attivo": e.attivo
            })
            
        # Display Data Editor
        edited_data = st.data_editor(
            emp_data, 
            hide_index=True,
            column_config={
                "ID": st.column_config.TextColumn(disabled=True),
                "Ruolo": st.column_config.SelectboxColumn(options=["INF", "OSS"]),
                "Team": st.column_config.NumberColumn(min_value=1, max_value=50, step=1),
            },
            key="employee_editor"
        )
        
        # Check for changes & Save button
        if st.button("Salva Modifiche Tabella"):
            # Compare edited_data with original emp_data
            # In a real app we'd use session state to track specific diffs
            # Here we iterate and update changed rows
            
            changes_count = 0
            for i, row in enumerate(edited_data):
                original = emp_data[i]
                
                # Check simple diff
                if row != original:
                    # Construct update dict
                    updates = {}
                    import math
                    
                    if row["Matricola"] != original["Matricola"]: 
                         updates["matricola"] = row["Matricola"]
                    if row["Nome"] != original["Nome"]: 
                        updates["nome_cognome"] = row["Nome"]
                    if row["Ruolo"] != original["Ruolo"]: 
                        updates["ruolo"] = row["Ruolo"]
                    
                    # Handle potential NaN in numeric fields
                    if row["Team"] != original["Team"]:
                        val = row["Team"]
                        if val is None or (isinstance(val, float) and math.isnan(val)):
                             updates["team_id"] = None
                        else:
                             updates["team_id"] = int(val)
                             
                    if row["Limitazione Notte"] != original["Limitazione Notte"]: 
                        updates["limitazione_notte"] = row["Limitazione Notte"]
                    if row["Attivo"] != original["Attivo"]: 
                        updates["attivo"] = row["Attivo"]
                    
                    if updates:
                        repo.update_employee(row["ID"], updates)
                        changes_count += 1
            
            if changes_count > 0:
                st.success(f"Aggiornati {changes_count} dipendenti!")
                # Refresh
                state.employees = []
                state.load_employees()
                st.rerun()
            else:
                st.info("Nessuna modifica rilevata.")

    # 3. Elimina Dipendente
    st.divider()
    with st.expander("⚠️ Elimina Dipendente", expanded=False):
        st.warning("Attenzione: l'eliminazione è irreversibile e potrebbe causare errori nei turni passati associati a questo dipendente.")
        
        if employees:
            emp_map = {e.nome_cognome: e.id for e in employees}
            emp_to_delete = st.selectbox("Seleziona Dipendente da Eliminare", list(emp_map.keys()))
            
            if st.button("Elimina Definitivamente", type="primary"):
                try:
                    repo.delete_employee(emp_map[emp_to_delete])
                    st.success(f"Dipendente {emp_to_delete} eliminato con successo!")
                    state.employees = []
                    state.load_employees()
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante l'eliminazione: {e}")
        else:
            st.info("Nessun dipendente da eliminare.")
