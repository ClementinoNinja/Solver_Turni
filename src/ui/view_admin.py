import streamlit as st
from dataclasses import replace
from datetime import date, timedelta
import calendar
from src.ui.state import AppState
from src.engine.solver import ShiftSolver
from src.database.repository import EmployeeRepository
from src.engine.validation import validate_roster
from src.engine.config import DEFAULT_SOLVER_CONFIG, SolverConfig

def render_admin_view():
    st.header("Amministrazione - Generazione Turni")
    
    # 1. Select Period
    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("Anno", min_value=2024, max_value=2031, value=date.today().year)
    with col2:
        month = st.selectbox("Mese", list(range(1, 13)), index=date.today().month - 1)
        
    num_days = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    days = [start_date + timedelta(days=i) for i in range(num_days)]
    
    st.info(f"Generazione per: {calendar.month_name[month]} {year} ({num_days} giorni)")
    
    # 2. Load Employees
    state = AppState()
    if not state.load_employees_safe(admin=True):
        return
    employees = state.employees

    if not employees:
        st.warning("Nessun dipendente trovato. Aggiungi dipendenti dalla sezione 'Gestione Dipendenti'.")
        return

    st.metric("Dipendenti Attivi", len(employees))

    repo = EmployeeRepository(admin=True)
    try:
        config = repo.get_solver_config()
        config_persisted = True
    except Exception as e:
        config = DEFAULT_SOLVER_CONFIG
        config_persisted = False
        st.warning(f"Impostazioni predefinite in uso; applicare la migrazione scheduler per salvarle: {e}")

    with st.expander("Configurazione solver", expanded=False):
        with st.form("solver_configuration"):
            st.caption("I valori iniziali mantengono le coperture già previste dall'applicazione.")
            morning_cols = st.columns(4)
            morning_coverage = (
                (
                    morning_cols[0].number_input("Mattina · alternativa 1 INF", 0, 50, config.morning_coverage_options[0][0]),
                    morning_cols[1].number_input("Mattina · alternativa 1 OSS", 0, 50, config.morning_coverage_options[0][1]),
                ),
                (
                    morning_cols[2].number_input("Mattina · alternativa 2 INF", 0, 50, config.morning_coverage_options[1][0]),
                    morning_cols[3].number_input("Mattina · alternativa 2 OSS", 0, 50, config.morning_coverage_options[1][1]),
                ),
            )
            evening_cols = st.columns(4)
            evening_coverage = (
                (
                    evening_cols[0].number_input("Pomeriggio · alternativa 1 INF", 0, 50, config.evening_coverage_options[0][0]),
                    evening_cols[1].number_input("Pomeriggio · alternativa 1 OSS", 0, 50, config.evening_coverage_options[0][1]),
                ),
                (
                    evening_cols[2].number_input("Pomeriggio · alternativa 2 INF", 0, 50, config.evening_coverage_options[1][0]),
                    evening_cols[3].number_input("Pomeriggio · alternativa 2 OSS", 0, 50, config.evening_coverage_options[1][1]),
                ),
            )
            general_cols = st.columns(4)
            night_min_inf = general_cols[0].number_input("Notte · minimo INF", 0, 50, config.night_min_inf)
            night_min_oss = general_cols[1].number_input("Notte · minimo OSS", 0, 50, config.night_min_oss)
            shift_capacity = general_cols[2].number_input("Capacità massima per turno", 1, 50, config.shift_capacity)
            max_time = general_cols[3].number_input("Tempo massimo solver (secondi)", 1, 600, config.max_time_seconds)
            penalty_cols = st.columns(4)
            cycle_penalty = penalty_cols[0].number_input(
                "Peso successione turni", 0, 10000, config.cycle_transition_penalty
            )
            night_balance_penalty = penalty_cols[1].number_input(
                "Peso equita notti", 0, 10000, config.night_balance_penalty
            )
            preference_penalty = penalty_cols[2].number_input("Peso preferenze", 0, 10000, config.preference_penalty)
            hours_penalty = penalty_cols[3].number_input("Peso scostamento ore", 0, 10000, config.hours_deviation_penalty)
            st.caption("Vincolo rigido: massimo 2 notti consecutive; ciclo preferito 1 -> K -> N -> S -> R.")
            daily_target_hours = st.number_input(
                "Ore teoriche per giorno lavorativo", min_value=0.25,
                max_value=24.0, value=config.daily_target_hours, step=0.25,
            )

            if st.form_submit_button("Salva configurazione", disabled=not config_persisted):
                try:
                    new_config = SolverConfig(
                        shift_capacity=shift_capacity,
                        morning_coverage_options=morning_coverage,
                        evening_coverage_options=evening_coverage,
                        night_min_inf=night_min_inf,
                        night_min_oss=night_min_oss,
                        cycle_transition_penalty=cycle_penalty,
                        night_balance_penalty=night_balance_penalty,
                        preference_penalty=preference_penalty,
                        hours_deviation_penalty=hours_penalty,
                        daily_target_hours=daily_target_hours,
                        max_time_seconds=max_time,
                    )
                    repo.save_solver_config(new_config)
                    st.success("Configurazione salvata.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Configurazione non salvata: {e}")

    pending_draft = st.session_state.get("_roster_draft")
    if (pending_draft and pending_draft["start"] == start_date.isoformat()
            and pending_draft["end"] == days[-1].isoformat()):
        st.subheader("Bozza pronta per la revisione")
        st.caption(
            f"Solver: {pending_draft['status']} · "
            f"obiettivo: {pending_draft['obj_value']} · "
            f"{len(pending_draft['entries'])} assegnazioni"
        )
        night_counts = {}
        for entry in pending_draft["entries"]:
            if entry.get("shift_code") == "N":
                employee_id = entry.get("employee_id")
                night_counts[employee_id] = night_counts.get(employee_id, 0) + 1
        st.caption("Distribuzione notti per dipendente")
        st.dataframe([
            {
                "Dipendente": f"{employee.nome_cognome} · {employee.matricola}",
                "Notti": night_counts.get(employee.id, 0),
            }
            for employee in employees
        ], use_container_width=True, hide_index=True)
        st.dataframe(pending_draft["entries"], use_container_width=True, hide_index=True)
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button("Pubblica calendario", type="primary"):
            try:
                repo.publish_roster_month(
                    pending_draft["start"], pending_draft["end"],
                    pending_draft["employee_ids"], pending_draft["expected"],
                    pending_draft["entries"],
                )
                st.session_state.pop("_roster_draft", None)
                st.success("Calendario pubblicato integralmente.")
                st.rerun()
            except Exception as e:
                st.error(f"Pubblicazione non riuscita: {e}")
        if cancel_col.button("Annulla bozza"):
            st.session_state.pop("_roster_draft", None)
            st.rerun()
    
    # 3. Request Input (Placeholder for future Sprint)
    st.info("Copertura prevista: mattina/pomeriggio (2+2 o 3+1), notte (2+1); target teorico 6 ore per giorno lavorativo, proporzionale al part-time.")
    
    # 4. Generate Action
    if st.button("GENERA TURNI", type="primary"):
        with st.spinner("L'algoritmo sta calcolando la soluzione ottimale..."):
            try:
                # Fetch Requests for the period
                start_date_str = start_date.strftime("%Y-%m-%d")
                end_date_str = (start_date + timedelta(days=num_days-1)).strftime("%Y-%m-%d")
                requests = repo.get_requests(start_date_str, end_date_str)
                expected_roster = [
                    row for row in repo.get_roster_by_month(start_date_str, end_date_str)
                    if row.get("employee_id") in {employee.id for employee in employees}
                ]

                # Legge anche il contesto adiacente per i vincoli già esistenti
                # e mantiene fissi i turni che il responsabile ha bloccato.
                boundary_rows = repo.get_roster_by_month(
                    (start_date - timedelta(days=2)).isoformat(),
                    (start_date + timedelta(days=num_days + 1)).isoformat(),
                )
                employee_ids = {employee.id for employee in employees}
                locked_roster = [
                    row for row in boundary_rows
                    if row.get("is_locked")
                    and row.get("employee_id") in employee_ids
                    and start_date_str <= str(row.get("data", ""))[:10] <= end_date_str
                ]
                boundary_by_key = {
                    (row["employee_id"], str(row.get("data", ""))[:10]): row["shift_code"]
                    for row in boundary_rows if row.get("employee_id") in employee_ids
                }
                previous_shifts = {
                    employee_id: [
                        boundary_by_key.get((employee_id, (start_date - timedelta(days=offset)).isoformat()))
                        for offset in (2, 1)
                    ] for employee_id in employee_ids
                }
                next_shifts = {
                    employee_id: [
                        boundary_by_key.get((employee_id, (start_date + timedelta(days=num_days + offset)).isoformat()))
                        for offset in (0, 1)
                    ] for employee_id in employee_ids
                }

                solver = ShiftSolver(
                    employees, days, requests=requests, locked_roster=locked_roster,
                    previous_shifts=previous_shifts, next_shifts=next_shifts,
                    config=config,
                )

                solver.add_hard_constraints()
                solver.add_soft_constraints()

                solution, stats = solver.solve()

                st.write(f"**Status Algoritmo:** {stats['status']}")
                st.write(f"Tempo: {stats['wall_time']:.2f}s, Rami esplorati: {stats['branches']}")

                if solution is not None:
                    validation_errors = validate_roster(
                        solution, employees, days, requests,
                        previous_shifts=previous_shifts, next_shifts=next_shifts,
                        config=solver.config,
                    )
                    if validation_errors:
                        st.error("Il solver ha prodotto una bozza che non supera la verifica indipendente.")
                        st.dataframe(
                            {"Problema": validation_errors},
                            use_container_width=True, hide_index=True,
                        )
                        return
                    if stats["status"] == "OPTIMAL":
                        st.success(f"Soluzione ottima trovata. Costo: {stats['obj_value']}")
                    else:
                        st.warning(
                            f"Soluzione valida ma non è provato che sia ottima. "
                            f"Costo: {stats['obj_value']}; limite: {stats['best_bound']}."
                        )
                    st.session_state["_roster_draft"] = {
                        "start": start_date_str,
                        "end": end_date_str,
                        "employee_ids": [employee.id for employee in employees],
                        "expected": expected_roster,
                        "entries": solution,
                        "status": stats["status"],
                        "obj_value": stats["obj_value"],
                        "best_bound": stats["best_bound"],
                    }
                    st.info("La soluzione è una bozza: controllala e pubblicala esplicitamente.")
                    st.rerun()
                else:
                    if stats["status"] == "INFEASIBLE":
                        st.error("I vincoli e le richieste non consentono una soluzione per questo periodo.")
                        st.info("Controlla coperture, assenze approvate, turni bloccati e limite di 2 notti consecutive.")
                    elif stats["status"] == "UNKNOWN":
                        st.warning("Il solver ha raggiunto il limite di tempo senza determinare la fattibilità.")
                    elif stats["status"] == "MODEL_INVALID":
                        st.error("Il modello dei turni non è valido; controllare la configurazione e i dati.")
                    else:
                        st.error(f"Il solver non ha prodotto una soluzione: {stats['status']}.")
            except ValueError as ve:
                st.error(f"Errore di configurazione: {ve}")
            except Exception as e:
                st.error(f"Errore durante la generazione: {e}")
                st.info("Verifica la connessione al database e i dati dei dipendenti.")
