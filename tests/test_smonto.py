import pytest
from datetime import date
from src.engine.solver import ShiftSolver
from src.models.employee import Employee

def test_smonto_consistency():
    # Setup
    employees = [Employee(id="1", nome_cognome="A", team_id=1)]
    # 2 days: D1, D2
    days = [date(2024, 1, 1), date(2024, 1, 2)]
    
    # Init Solver
    solver = ShiftSolver(employees, days)
    
    # 1. Test Valid: N -> S
    # We force D1=N. Solver should be able to assign S to D2.
    # Actually we just add standard constraints and see if N->S is allowed.
    pass

def test_smonto_forbidden_if_no_night():
    # 1. Setup
    employees = [Employee(id="1", nome_cognome="A", team_id=1)]
    days = [date(2024, 1, 1), date(2024, 1, 2)]
    
    # Request: FERIE on Day 1.
    # So Day 1 cannot be 'N'.
    requests = [{
        "employee_id": "1",
        "tipo_richiesta": "FERIE",
        "data_inizio": "2024-01-01",
        "data_fine": "2024-01-01"
    }]
    
    solver = ShiftSolver(employees, days, requests=requests)
    
    # Add minimal constraints
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_request_constraints(requests)
    
    # Activate our new specific constraint
    solver.constraints_manager.add_smonto_consistent_constraint()
    
    # We solve minimizing nothing (feasibility)
    solution, stats = solver.solve()
    
    # Verify:
    # D1 must be 'F' (Request)
    # D2 must NOT be 'S' (because D1 was not N)
    
    s1 = next(s for s in solution if s['data'] == '2024-01-01')
    s2 = next(s for s in solution if s['data'] == '2024-01-02')
    
    assert s1['shift_code'] == 'F'
    assert s2['shift_code'] != 'S', f"Found Smonto (S) on D2 even though D1 was {s1['shift_code']}"
    
    print(f"Day 1: {s1['shift_code']}, Day 2: {s2['shift_code']}")
