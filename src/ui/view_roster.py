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
        year = st.number_input("Anno", min_value=2024, max_value=2031, value=date.today().year, key="roster_year")
    with col2:
        month = st.selectbox("Mese", list(range(1, 13)), index=date.today().month - 1, key="roster_month")

    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    # 2. Load Data
    repo = EmployeeRepository()
    try:
        roster_data = repo.get_roster_by_month(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    except Exception as e:
        st.error(f"Errore di connessione al database: {e}")
        st.info("Verifica che il progetto Supabase sia attivo e che le credenziali in secrets.toml siano corrette.")
        return

    state = AppState()
    if not state.load_employees_safe():
        return
    employees = {e.id: e for e in state.employees}

    if not employees:
        st.info("Nessun dipendente trovato. Aggiungi dipendenti dalla sezione 'Gestione Dipendenti'.")
        return

    # 3. Pivot Data for Grid
    days = [start_date + timedelta(days=i) for i in range(last_day)]
    day_cols = [d.strftime("%d") for d in days]

    # Prepare data structure: {emp_name: {day: shift_code}}
    grid_data = {}

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

            # Privacy / Masking Logic
            if not is_admin:
                shift_def = SHIFT_DEFINITIONS.get(shift_code)
                if shift_def and shift_def.is_absence:
                    if shift_code in ['M', '104']:
                        shift_code = 'ASS'

            grid_data[emp_name][day_col] = shift_code

    df = pd.DataFrame.from_dict(grid_data, orient='index')
    if not df.empty:
        df = df[day_cols]

    # 4. Render Editor or Read-Only
    if is_admin:
        st.caption("Modalità Modifica: Doppio click sulla cella per cambiare il turno.")
        edited_df = st.data_editor(df, key="roster_editor", use_container_width=True)

        if not df.equals(edited_df):
            if st.button("Salva Modifiche"):
                st.warning("Salvataggio modifiche grid non ancora implementato. Usa la generazione turni.")
    else:
        st.caption("Modalità Sola Lettura")
        st.dataframe(df, use_container_width=True)

    # 5. Export
    if not df.empty:
        from src.utils.exporter import to_excel
        try:
            excel_data = to_excel(df, year, month)
            st.download_button(
                label="Scarica Excel",
                data=excel_data,
                file_name=f"turni_{year}_{month}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.warning(f"Errore generazione Excel: {e}")

    # Legenda
    with st.expander("Legenda Turni"):
        st.write("1: Mattina, K: Pomeriggio, N: Notte, S: Smonto, R: Riposo")

    # 6. Coverage Stats
    st.divider()
    st.subheader("Verifica Copertura Giornaliera")

    if df.empty:
        st.info("Nessun turno da visualizzare per questo periodo.")
        return

    coverage_data = []
    name_to_role = {e.nome_cognome: e.ruolo for e in state.employees}

    for day_str in day_cols:
        inf_1, oss_1 = 0, 0
        inf_K, oss_K = 0, 0
        inf_N, oss_N = 0, 0

        for emp_name, shift_code in df[day_str].items():
            role = name_to_role.get(emp_name, 'INF')

            if shift_code == '1':
                if role == 'INF': inf_1 += 1
                else: oss_1 += 1
            elif shift_code == 'K':
                if role == 'INF': inf_K += 1
                else: oss_K += 1
            elif shift_code == 'N':
                if role == 'INF': inf_N += 1
                else: oss_N += 1

        ok_1 = (inf_1 >= 2 and oss_1 >= 2) or (inf_1 >= 3 and oss_1 >= 1)
        ok_K = (inf_K >= 2 and oss_K >= 2) or (inf_K >= 3 and oss_K >= 1)
        ok_N = (inf_N >= 2 and oss_N >= 1)

        status = "OK" if (ok_1 and ok_K and ok_N) else "WARN"

        coverage_data.append({
            "Giorno": day_str,
            "Mattina (1)": f"{inf_1}I + {oss_1}O",
            "Pom (K)": f"{inf_K}I + {oss_K}O",
            "Notte (N)": f"{inf_N}I + {oss_N}O",
            "Stato": status
        })

    st.dataframe(pd.DataFrame(coverage_data), use_container_width=True, hide_index=True)
