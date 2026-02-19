import streamlit as st
from datetime import date, timedelta
import calendar
from src.ui.state import AppState
from src.engine.solver import ShiftSolver
from src.database.repository import EmployeeRepository

def render_admin_view():
    st.header("Amministrazione - Generazione Turni")
    
    # 1. Select Period
    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("Anno", min_value=2026, max_value=2031, value=date.today().year)
    with col2:
        month = st.selectbox("Mese", list(range(1, 13)), index=date.today().month - 1)
        
    num_days = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    days = [start_date + timedelta(days=i) for i in range(num_days)]
    
    st.info(f"Generazione per: {calendar.month_name[month]} {year} ({num_days} giorni)")
    
    # 2. Load Employees
    state = AppState()
    state.load_employees()
    employees = state.employees
    
    st.metric("Dipendenti Attivi", len(employees))
    
    # 3. Request Input (Placeholder for future Sprint)
    st.info("Regole Copertura (Sprint 7): M/P (2+2 o 3+1), Notte (2+1)")
    
    # 4. Generate Action
    if st.button("GENERA TURNI", type="primary"):
        with st.spinner("L'algoritmo sta calcolando la soluzione ottimale..."):
            repo = EmployeeRepository()
            
            # Fetch Requests for the period
            start_date_str = start_date.strftime("%Y-%m-%d")
            # End date approximation (last day of month calculated above)
            end_date_str = (start_date + timedelta(days=num_days-1)).strftime("%Y-%m-%d")
            requests = repo.get_requests(start_date_str, end_date_str)
            
            solver = ShiftSolver(employees, days, requests=requests)
            
            # Add Constraints (Rules are now hardcoded in constraints.py)
            solver.add_hard_constraints()
            solver.add_soft_constraints()
            
            solution, stats = solver.solve()
            
            st.write(f"**Status Algoritmo:** {stats['status']}")
            st.write(f"Tempo: {stats['wall_time']:.2f}s, Rami esplorati: {stats['branches']}")
            
            if solution:
                st.success(f"Soluzione trovata! Costo: {stats['obj_value']}")
                
                # Save to DB
                repo = EmployeeRepository()
                progress_bar = st.progress(0)
                for idx, entry in enumerate(solution):
                    repo.save_roster_entry(
                        entry['employee_id'], 
                        entry['data'], 
                        entry['shift_code']
                    )
                    progress_bar.progress((idx + 1) / len(solution))
                
                st.balloons()
            else:
                st.error("Nessuna soluzione trovata! Rilassa i vincoli.")
                st.warning("""
                Possibili cause:
                1. Troppe richieste (Ferie/Malattia) in un singolo giorno.
                2. Vincoli di copertura troppo alti (es. 2 Notti con pochi dipendenti abilitati).
                3. Violazione riposi (es. Mattina dopo Notte forzata da preferenze).
                
                Prova a ridurre la copertura minima o rimuovere alcune preferenze.
                """)
