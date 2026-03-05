import streamlit as st
from datetime import date
from src.database.repository import EmployeeRepository
from src.ui.state import AppState

def render_requests_view():
    st.header("Gestione Richieste & Assenze")
    
    repo = EmployeeRepository()
    state = AppState()
    state.load_employees()
    employees = state.employees
    emp_map = {e.nome_cognome: e.id for e in employees}
    
    # 1. Form Inserimento
    with st.expander("Inserisci Nuova Richiesta", expanded=True):
        with st.form("new_request"):
            col1, col2 = st.columns(2)
            emp_name = col1.selectbox("Dipendente", list(emp_map.keys()))
            # Update options: Remove DESIDERATA, add Shift preferences
            req_type = col2.selectbox("Tipo Richiesta", [
                "FERIE", "MALATTIA", "104", "PERMESSO",
                "Mattina (Pref)", "Pomeriggio (Pref)", "Notte (Pref)"
            ])
            
            col3, col4 = st.columns(2)
            d_start = col3.date_input("Data Inizio", value=date.today())
            d_end = col4.date_input("Data Fine", value=date.today())
            
            note = st.text_area("Note (Opzionale)")
            
            if st.form_submit_button("Salva Richiesta"):
                if d_end < d_start:
                    st.error("La data fine deve essere successiva alla data inizio.")
                else:
                    emp_id = emp_map[emp_name]
                    try:
                        repo.create_request(
                            employee_id=emp_id,
                            request_type=req_type,
                            start_date=d_start.isoformat(),
                            end_date=d_end.isoformat(),
                            note=note
                        )
                        st.success("Richiesta salvata con successo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore salvataggio: {e}")

    # 2. visualizzazione Richieste Esistenti
    st.divider()
    st.subheader("Richieste Future")
    
    # Filter only future requests or current month
    # For now, get all requests from today onwards
    # Mostra richieste da oggi in poi (nessuna data fine hardcodata)
    far_future = date(date.today().year + 10, 12, 31).isoformat()
    requests = repo.get_requests(date.today().isoformat(), far_future)
    
    if requests:
        # Convert to easy table
        # Need to join with employee names (simple lookup)
        emp_id_name = {e.id: e.nome_cognome for e in employees}
        
        table_data = []
        for r in requests:
            table_data.append({
                "ID": r['id'],
                "Dipendente": emp_id_name.get(r['employee_id'], r['employee_id']),
                "Tipo": r['tipo_richiesta'],
                "Inizio": r['data_inizio'],
                "Fine": r['data_fine'],
                "Note": r.get('note', '')
            })
            
        st.dataframe(table_data, use_container_width=True, hide_index=True)
        
        # 3. Elimina Richiesta
        st.divider()
        with st.expander("⚠️ Elimina Richiesta", expanded=False):
            # Map description string to ID
            req_map = {f"ID: {r['id']} - {emp_id_name.get(r['employee_id'], '')} ({r['tipo_richiesta']} {r['data_inizio']})": r['id'] for r in requests}
            
            req_to_delete = st.selectbox("Seleziona Richiesta da Eliminare", list(req_map.keys()))
            
            if st.button("Elimina", type="primary"):
                try:
                    repo.delete_request(req_map[req_to_delete])
                    st.success("Richiesta eliminata con successo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante l'eliminazione: {e}")
    else:
        st.info("Nessuna richiesta futura.")
