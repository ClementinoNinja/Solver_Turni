import streamlit as st
import pandas as pd
from datetime import date, timedelta
import calendar
from src.ui.state import AppState
from src.database.repository import EmployeeRepository
from src.models.shift import SHIFT_DEFINITIONS

def render_roster_view(is_admin: bool = False):
    st.header("Visualizzazione Turni")
    
    # 1. Select Period
    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("Anno", min_value=2026, max_value=2031, value=date.today().year, key="roster_year")
    with col2:
        month = st.selectbox("Mese", list(range(1, 13)), index=date.today().month - 1, key="roster_month")
        
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    # 2. Load Data
    repo = EmployeeRepository()
    roster_data = repo.get_roster_by_month(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    
    state = AppState()
    state.load_employees()
    employees = {e.id: e for e in state.employees}
    
    # 3. Pivot Data for Grid
    # Rows: Employee Names, Cols: Days
    # We need a DataFrame structure
    
    days = [start_date + timedelta(days=i) for i in range(last_day)]
    day_cols = [d.strftime("%d") for d in days]
    
    # Prepare data structure: {emp_name: {day: shift_code}}
    grid_data = {}
    
    # Pre-fill with empty or '-'
    for emp_id, emp in employees.items():
        grid_data[emp.nome_cognome] = {day_col: "" for day_col in day_cols}
        
    # Fill with roster data
    for entry in roster_data:
        emp_id = entry['employee_id']
        if emp_id in employees:
            emp_name = employees[emp_id].nome_cognome
            entry_date = date.fromisoformat(entry['data'])
            day_col = entry_date.strftime("%d")
            
            shift_code = entry['shift_code']
            
            # Privacy / Masking Logic (Sprint 4.4 merged here)
            if not is_admin:
                # Se è un turno sensibile (M, 104), mostra 'ASS' genericamente
                shift_def = SHIFT_DEFINITIONS.get(shift_code)
                if shift_def and shift_def.is_absence: # Semplificazione: tutte assenze mascherate? 
                    # Security specs: M e 104 mascherati. F e P visibili.
                    if shift_code in ['M', '104']:
                        shift_code = 'ASS'
            
            grid_data[emp_name][day_col] = shift_code

    df = pd.DataFrame.from_dict(grid_data, orient='index')
    # Reorder columns just in case
    df = df[day_cols]
    
    # 5. Export
    from src.utils.exporter import to_excel
    excel_data = to_excel(df, year, month)
    st.download_button(
        label="📥 Scarica Excel",
        data=excel_data,
        file_name=f"turni_{year}_{month}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # 4. Render Editor
    if is_admin:
        st.caption("Modalità Modifica: Doppio click sulla cella per cambiare il turno.")
        edited_df = st.data_editor(df, key="roster_editor", use_container_width=True)
        
        # Detect Changes (Differenza tra df e edited_df)
        if not df.equals(edited_df):
            if st.button("Salva Modifiche"):
                # TODO: Implementare logica di salvataggio back to DB
                # Iterare su celle diverse e chiamare repo.save_roster_entry
                # Richiede mappatura inversa Nome -> ID
                st.warning("Salvataggio modifiche grid non ancora implementato (Richiede logica diff complessa). Usa 'God Mode' cella singola in futuro.")
                # Per MVP Grid Edit è complesso. Implementiamo salvataggio dummy o lasciamo view only editable next sprint.
    else:
        st.caption("Modalità Sola Lettura")
        st.dataframe(df, use_container_width=True)

    # Legenda
    with st.expander("Legenda Turni"):
        st.write("1: Mattina, K: Pomeriggio, N: Notte, S: Smonto, R: Riposo")
        
    # 6. Coverage Stats (New! Sprint 7)
    st.divider()
    st.subheader("Verifica Copertura Giornaliera")
    
    # Calculate coverage from df
    # df columns are days (01, 02...). Values are shift codes.
    
    coverage_data = []
    
    # We iterate over day_cols which corresponds to the days in the month
    for day_str in day_cols:
        col_values = df[day_str].values
        
        # Count occurrences by Role
        # We need to map back from Name -> Role (or use the roster data directly if easier, but df has names/codes)
        # DF contains Shift Codes. Index is Name.
        # Let's iterate rows of the DF.
        
        inf_1, oss_1 = 0, 0
        inf_K, oss_K = 0, 0
        inf_N, oss_N = 0, 0
        
        for emp_name, shift_code in df[day_str].items():
            # lookup role
            # emp_name is key in grid_data, but we need ID or Object.
            # let's assume emp_name is unique or use a map
            # We built grid_data[emp.nome_cognome]
            # Need map: Name -> Role
            pass
            
        # Optimization: Build Name->Role map outside loop
        name_to_role = {e.nome_cognome: e.ruolo for e in state.employees}
        
        for emp_name, shift_code in df[day_str].items():
            role = name_to_role.get(emp_name, 'INF') # default
            
            if shift_code == '1':
                if role == 'INF': inf_1 += 1
                else: oss_1 += 1
            elif shift_code == 'K':
                if role == 'INF': inf_K += 1
                else: oss_K += 1
            elif shift_code == 'N':
                if role == 'INF': inf_N += 1
                else: oss_N += 1
        
        # Determine status
        # Rule M/P: (2I+2O) or (3I+1O) -> Total >= 4 and I>=2 and O>=1 coverage check
        # Rule N: 2I+1O
        
        ok_1 = (inf_1 >= 2 and oss_1 >= 2) or (inf_1 >= 3 and oss_1 >= 1)
        ok_K = (inf_K >= 2 and oss_K >= 2) or (inf_K >= 3 and oss_K >= 1)
        ok_N = (inf_N >= 2 and oss_N >= 1)
        
        status = "✅" if (ok_1 and ok_K and ok_N) else "⚠️"
        
        coverage_data.append({
            "Giorno": day_str,
            "Mattina (1)": f"{inf_1}I + {oss_1}O",
            "Pom (K)": f"{inf_K}I + {oss_K}O",
            "Notte (N)": f"{inf_N}I + {oss_N}O",
            "Stato": status
        })
        
    st.dataframe(pd.DataFrame(coverage_data), use_container_width=True, hide_index=True)
