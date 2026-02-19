import pytest
from datetime import date
from src.engine.solver import ShiftSolver
from src.models.employee import Employee

def test_solver_respects_requests():
    # 1. Setup
    employees = [
        Employee(id="1", nome_cognome="A", team_id=1),
        Employee(id="2", nome_cognome="B", team_id=2),
    ]
    days = [date(2024, 1, 1), date(2024, 1, 2)]
    
    # 2. Define Requests
    # Employee 1 has FERIE on 2024-01-01
    requests = [
        {
            "employee_id": "1",
            "tipo_richiesta": "FERIE",
            "data_inizio": "2024-01-01",
            "data_fine": "2024-01-01"
        },
        # Employee 2 has MALATTIA on 2024-01-02
        {
            "employee_id": "2",
            "tipo_richiesta": "MALATTIA",
            "data_inizio": "2024-01-02",
            "data_fine": "2024-01-02"
        }
    ]
    
    # 3. Initialize Solver with Requests
    solver = ShiftSolver(employees, days, requests=requests)
    
    # Add minimal constraints
    # Note: We need relax min coverage because if A is on Holiday, maybe we can't cover?
    # Let's set min coverage to 0 to test only the hard constraint of the request itself
    solver.add_hard_constraints(min_coverage={'1': 0, 'K': 0, 'N': 0})
    
    solution = solver.solve()
    
    # 4. Verify
    assert solution is not None
    
    # Check Employee 1 on Day 1 is 'F'
    s1 = next(s for s in solution if s['employee_id'] == '1' and s['data'] == '2024-01-01')
    assert s1['shift_code'] == 'F', f"Expected F, got {s1['shift_code']}"
    
    # Check Employee 2 on Day 2 is 'M'
    s2 = next(s for s in solution if s['employee_id'] == '2' and s['data'] == '2024-01-02')
    assert s2['shift_code'] == 'M', f"Expected M, got {s2['shift_code']}"
