import pytest
from datetime import date
from src.engine.solver import ShiftSolver
from src.models.employee import Employee

def test_solver_respects_preferences():
    # 1. Setup
    employees = [
        Employee(id="1", nome_cognome="A", team_id=1),
    ]
    days = [date(2024, 1, 1)]
    
    # 2. Define Requests (Preferences)
    requests = [
        {
            "employee_id": "1",
            "tipo_richiesta": "Mattina (Pref)", # Should map to '1'
            "data_inizio": "2024-01-01",
            "data_fine": "2024-01-01"
        }
    ]
    
    # 3. Initialize Solver with Requests
    solver = ShiftSolver(employees, days, requests=requests)
    
    # 4. Solve
    # We relax coverage to ensure only preference matters
    solver.add_hard_constraints(min_coverage={'1': 0, 'K': 0, 'N': 0})
    
    solution = solver.solve()
    assert solution is not None
    
    # 5. Verify
    s1 = next(s for s in solution if s['employee_id'] == '1' and s['data'] == '2024-01-01')
    assert s1['shift_code'] == '1', f"Expected '1' (Mattina), got {s1['shift_code']}"
