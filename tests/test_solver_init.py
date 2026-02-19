import pytest
from datetime import date, timedelta
from src.engine.solver import ShiftSolver
from src.models.employee import Employee

def test_solver_initialization():
    # Setup Data
    employees = [
        Employee(id="1", nome_cognome="Mario", ruolo="INF"),
        Employee(id="2", nome_cognome="Luigi", ruolo="OSS")
    ]
    
    start_date = date(2024, 1, 1)
    days = [start_date + timedelta(days=i) for i in range(3)] # 3 days
    
    # Init Solver
    solver = ShiftSolver(employees, days)
    
    # Check variables creation
    # Total vars = num_emp * num_days * num_shift_types
    # 2 * 3 * 9 (standard shifts) = 54
    assert len(solver.work) == 2 * 3 * 9
    
    # Check if solving an empty model returns a solution (feasible)
    # Since we haven't added "Exactly one shift per day", it might return all false or random
    # But checking if solve runs without crashing is good enough for init test
    solution = solver.solve()
    assert solution is not None
