import pytest
from datetime import date, timedelta
from src.engine.solver import ShiftSolver
from src.models.employee import Employee

def test_hard_constraints_infeasible():
    # Scenario: 1 Giorno, Min Coverage 3 Mattine, Ma solo 2 Dipendenti -> INFEASIBLE
    employees = [
        Employee(id="1", nome_cognome="A", ruolo="INF"),
        Employee(id="2", nome_cognome="B", ruolo="INF")
    ]
    days = [date(2024, 1, 1)]
    
    solver = ShiftSolver(employees, days)
    
    # Coverage richiesta: 3 su turno '1'
    min_coverage = {'1': 3}
    solver.add_hard_constraints(min_coverage)
    
    solution = solver.solve()
    assert solution is None # Deve fallire

def test_hard_constraints_feasible():
    # Scenario: 1 Giorno, Min Coverage 1 Mattina, 2 Dipendenti -> FEASIBLE
    employees = [
        Employee(id="1", nome_cognome="A", ruolo="INF"),
        Employee(id="2", nome_cognome="B", ruolo="INF")
    ]
    days = [date(2024, 1, 1)]
    
    solver = ShiftSolver(employees, days)
    min_coverage = {'1': 1}
    solver.add_hard_constraints(min_coverage)
    
    solution = solver.solve()
    assert solution is not None
    assert len(solution) == 2 # 2 dipendenti * 1 giorno
    
    # Check coverage
    morning_count = sum(1 for s in solution if s['shift_code'] == '1')
    assert morning_count >= 1

def test_no_morning_after_night():
    # Scenario: 2 Giorni. Dipendente A fa Notte Giorno 1.
    # Constraint deve impedire Mattina Giorno 2.
    # Forziamo Notte Giorno 1 tramite min coverage
    
    emp = Employee(id="1", nome_cognome="A", ruolo="INF")
    days = [date(2024, 1, 1), date(2024, 1, 2)]
    
    solver = ShiftSolver([emp], days)
    
    # Giorno 1 deve essere Notte (N)
    # Giorno 2 Mattina (1) sarebbe l'unica opzione se non ci fosse il vincolo
    # Ma il vincolo dovrebbe renderlo infattibile se forziamo anche Giorno 2 Mattina
    
    # Add manual constraint to force Night on day 1
    d1 = days[0].strftime("%Y-%m-%d")
    solver.model.Add(solver.work[emp.id, d1, 'N'] == 1)
    
    # Try to force Morning on day 2
    d2 = days[1].strftime("%Y-%m-%d")
    solver.model.Add(solver.work[emp.id, d2, '1'] == 1)
    
    solver.add_hard_constraints({}) # Add N->1 rule
    
    solution = solver.solve()
    assert solution is None # Should be infeasible
