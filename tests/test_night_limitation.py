import pytest
from datetime import date
from src.engine.solver import ShiftSolver
from src.models.employee import Employee

def test_night_limitation_constraint():
    # 1. Setup
    employees = [
        # Emp 1 has limitation
        Employee(id="1", nome_cognome="A", team_id=1, limitazione_notte=True),
        # Emp 2 has no limitation
        Employee(id="2", nome_cognome="B", team_id=2, limitazione_notte=False),
    ]
    days = [date(2024, 1, 1)]
    
    # 2. Init Solver
    solver = ShiftSolver(employees, days)
    
    # Force night coverage to 1.
    # If A cannot do night, B MUST do night.
    solver.add_hard_constraints(min_coverage={'1': 0, 'K': 0, 'N': 1})
    
    solution = solver.solve()
    assert solution is not None, "Should find solution with B doing night"
    
    # 3. Verify
    s1 = next(s for s in solution if s['employee_id'] == '1')
    assert s1['shift_code'] != 'N', "Employee 1 has night limitation but got N"
    
    s2 = next(s for s in solution if s['employee_id'] == '2')
    assert s2['shift_code'] == 'N', "Employee 2 should cover night"
