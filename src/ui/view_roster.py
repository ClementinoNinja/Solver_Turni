import streamlit as st
import pandas as pd
from datetime import date, timedelta
import calendar
from src.database.repository import EmployeeRepository
from src.models.employee import Employee
from src.engine.validation import validate_roster
from src.engine.config import DEFAULT_SOLVER_CONFIG
from src.utils.holidays import get_monthly_target_hours

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
    repo = EmployeeRepository(admin=is_admin)
    try:
        if is_admin:
            roster_data = repo.get_roster_by_month(start_date.isoformat(), end_date.isoformat())
            roster_employees = repo.get_all_employees(include_inactive=True)
        else:
            roster_data = repo.get_public_roster_by_month(start_date.isoformat(), end_date.isoformat())
            unique_employees = {row["employee_id"]: row for row in roster_data}
            roster_employees = [
                Employee(
                    id=employee_id, matricola=row["matricola"],
                    nome_cognome=row["employee_name"], ruolo=row["ruolo"],
                )
                for employee_id, row in unique_employees.items()
            ]
    except Exception as e:
        st.error(f"Errore di connessione al database: {e}")
        st.info("Verifica che il progetto Supabase sia attivo e che le credenziali in secrets.toml siano corrette.")
        return

    employees = {e.id: e for e in roster_employees}
    try:
        solver_config = repo.get_solver_config() if is_admin else DEFAULT_SOLVER_CONFIG
    except Exception:
        solver_config = DEFAULT_SOLVER_CONFIG

    if not employees:
        st.info("Nessun dipendente trovato. Aggiungi dipendenti dalla sezione 'Gestione Dipendenti'.")
        return

    # 3. Pivot Data for Grid
    days = [start_date + timedelta(days=i) for i in range(last_day)]
    day_cols = [d.strftime("%d") for d in days]

    # Le etichette includono la matricola per distinguere gli omonimi.
    employee_labels = {
        emp_id: f"{emp.nome_cognome} · {emp.matricola}"
        for emp_id, emp in employees.items()
    }
    grid_data = {}

    for emp_id, emp in employees.items():
        grid_data[employee_labels[emp_id]] = {day_col: "" for day_col in day_cols}

    # Fill with roster data
    for entry in roster_data:
        emp_id = entry['employee_id']
        if emp_id in employees:
            emp_name = employee_labels[emp_id]
            entry_date = date.fromisoformat(entry['data'])
            day_col = entry_date.strftime("%d")

            shift_code = entry['shift_code']

            grid_data[emp_name][day_col] = shift_code

    df = pd.DataFrame.from_dict(grid_data, orient='index')
    df.index.name = "Dipendente · matricola"
    if not df.empty:
        df = df[day_cols]

    # 4. Render Editor or Read-Only
    if is_admin:
        st.caption("Modalità Modifica: Doppio click sulla cella per cambiare il turno.")
        shift_options = ["", "1", "K", "N", "S", "R", "F", "M", "104", "P"]
        edited_df = st.data_editor(
            df, key="roster_editor", use_container_width=True,
            column_config={
                day: st.column_config.SelectboxColumn(options=shift_options)
                for day in day_cols
            },
        )
        current_locks = {
            (row["employee_id"], str(row["data"])[:10]): bool(row.get("is_locked", False))
            for row in roster_data
        }
        lock_data = {
            employee_labels[employee_id]: {
                day: current_locks.get((employee_id, (start_date + timedelta(days=int(day) - 1)).isoformat()), False)
                for day in day_cols
            }
            for employee_id in employees
        }
        lock_df = pd.DataFrame.from_dict(lock_data, orient="index")
        lock_df.index.name = "Dipendente · matricola"
        edited_lock_df = st.data_editor(
            lock_df, key="roster_lock_editor", use_container_width=True,
            column_config={
                day: st.column_config.CheckboxColumn(label=f"Blocca {day}")
                for day in day_cols
            },
        )

        pending_draft = st.session_state.get("_roster_draft")
        if (pending_draft and pending_draft["start"] == start_date.isoformat()
                and pending_draft["end"] == end_date.isoformat()):
            st.warning("Bozza manuale pronta: rivedila e pubblicala per confermare le modifiche.")
            confirm_col, cancel_col = st.columns(2)
            if confirm_col.button("Pubblica modifiche", type="primary"):
                try:
                    repo.publish_roster_month(
                        pending_draft["start"], pending_draft["end"],
                        pending_draft["employee_ids"], pending_draft["expected"],
                        pending_draft["entries"],
                    )
                    st.session_state.pop("_roster_draft", None)
                    st.success("Modifiche pubblicate integralmente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Pubblicazione non riuscita: {e}")
            if cancel_col.button("Annulla modifiche"):
                st.session_state.pop("_roster_draft", None)
                st.rerun()

        changed = not df.equals(edited_df) or not lock_df.equals(edited_lock_df)
        if changed and st.button("Prepara bozza modifiche", key="prepare_manual_roster"):
            try:
                active_employees = [emp for emp in roster_employees if emp.attivo]
                active_ids = {emp.id for emp in active_employees}
                for employee_id, employee in employees.items():
                    if employee.attivo:
                        continue
                    label = employee_labels[employee_id]
                    if not df.loc[label].equals(edited_df.loc[label]) or not lock_df.loc[label].equals(edited_lock_df.loc[label]):
                        raise ValueError(f"Lo storico di {employee.nome_cognome} è archiviato e non è modificabile.")

                entries = []
                additional_coverage = []
                additional_roles = {}
                for employee_id, employee in employees.items():
                    label = employee_labels[employee_id]
                    for day in day_cols:
                        work_date = (start_date + timedelta(days=int(day) - 1)).isoformat()
                        code = edited_df.loc[label, day] if employee.attivo else df.loc[label, day]
                        if pd.isna(code) or code == "":
                            continue
                        locked = bool(edited_lock_df.loc[label, day]) if employee.attivo else current_locks.get((employee_id, work_date), False)
                        row = {
                            "employee_id": employee_id,
                            "data": work_date,
                            "shift_code": str(code),
                            "is_locked": locked,
                        }
                        if employee_id in active_ids:
                            entries.append(row)
                        else:
                            additional_coverage.append(row)
                            additional_roles[employee_id] = employee.ruolo

                requests = repo.get_requests(start_date.isoformat(), end_date.isoformat())
                boundary_rows = repo.get_roster_by_month(
                    (start_date - timedelta(days=1)).isoformat(),
                    (end_date + timedelta(days=1)).isoformat(),
                )
                previous_shifts = {
                    row["employee_id"]: row["shift_code"] for row in boundary_rows
                    if str(row.get("data", ""))[:10] == (start_date - timedelta(days=1)).isoformat()
                }
                next_shifts = {
                    row["employee_id"]: row["shift_code"] for row in boundary_rows
                    if str(row.get("data", ""))[:10] == (end_date + timedelta(days=1)).isoformat()
                }
                errors = validate_roster(
                    entries, active_employees, days, requests,
                    previous_shifts=previous_shifts, next_shifts=next_shifts,
                    config=solver_config,
                    additional_coverage_entries=additional_coverage,
                    additional_employee_roles=additional_roles,
                )
                if errors:
                    st.error("Le modifiche non rispettano i vincoli del calendario.")
                    st.dataframe(pd.DataFrame({"Problema": errors}), hide_index=True)
                else:
                    expected = [
                        row for row in repo.get_roster_by_month(start_date.isoformat(), end_date.isoformat())
                        if row.get("employee_id") in active_ids
                    ]
                    st.session_state["_roster_draft"] = {
                        "start": start_date.isoformat(), "end": end_date.isoformat(),
                        "employee_ids": [emp.id for emp in active_employees],
                        "expected": expected, "entries": entries,
                        "status": "MODIFICA MANUALE", "obj_value": None,
                    }
                    st.rerun()
            except Exception as e:
                st.error(f"Impossibile preparare la bozza: {e}")
    else:
        st.caption("Modalità Sola Lettura")
        st.dataframe(df, use_container_width=True)

    # 5. Export
    if not df.empty:
        from src.utils.exporter import to_excel
        try:
            target_hours_map = {
                employee_labels[e.id]: get_monthly_target_hours(
                    year, month, daily_target=solver_config.daily_target_hours
                ) * e.contract_percentage / 100.0
                for e in roster_employees
            } if is_admin else None
            excel_data = to_excel(
                df, year, month, calculation_df=df,
                target_hours_map=target_hours_map, include_hours=is_admin,
            )
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
    label_to_role = {employee_labels[e.id]: e.ruolo for e in roster_employees}
    coverage_config = solver_config

    for day_str in day_cols:
        inf_1, oss_1 = 0, 0
        inf_K, oss_K = 0, 0
        inf_N, oss_N = 0, 0

        for employee_label, shift_code in df[day_str].items():
            role = label_to_role.get(employee_label, 'INF')

            if shift_code == '1':
                if role == 'INF': inf_1 += 1
                else: oss_1 += 1
            elif shift_code == 'K':
                if role == 'INF': inf_K += 1
                else: oss_K += 1
            elif shift_code == 'N':
                if role == 'INF': inf_N += 1
                else: oss_N += 1

        ok_1 = any(
            inf_1 >= min_inf and oss_1 >= min_oss
            for min_inf, min_oss in coverage_config.morning_coverage_options
        )
        ok_K = any(
            inf_K >= min_inf and oss_K >= min_oss
            for min_inf, min_oss in coverage_config.evening_coverage_options
        )
        ok_N = (
            inf_N >= coverage_config.night_min_inf
            and oss_N >= coverage_config.night_min_oss
        )

        status = "OK" if (ok_1 and ok_K and ok_N) else "WARN"

        coverage_data.append({
            "Giorno": day_str,
            "Mattina (1)": f"{inf_1}I + {oss_1}O",
            "Pom (K)": f"{inf_K}I + {oss_K}O",
            "Notte (N)": f"{inf_N}I + {oss_N}O",
            "Stato": status
        })

    st.dataframe(pd.DataFrame(coverage_data), use_container_width=True, hide_index=True)
