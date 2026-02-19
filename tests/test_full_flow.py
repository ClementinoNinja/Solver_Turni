import pytest
import pandas as pd
from datetime import date, timedelta
from src.engine.solver import ShiftSolver
from src.models.employee import Employee
from src.utils.exporter import to_excel

def test_full_system_flow():
    # 1. Setup Data
    employees = [
        Employee(id="1", nome_cognome="A", team_id=1),
        Employee(id="2", nome_cognome="B", team_id=2),
        Employee(id="3", nome_cognome="C", team_id=3),
    ]
    days = [date(2024, 1, 1) + timedelta(days=i) for i in range(5)]
    
    # 2. Solver Execution
    solver = ShiftSolver(employees, days)
    solver.add_hard_constraints(min_coverage={'1': 1}) # Minimal coverage
    solver.add_soft_constraints()
    
    solution = solver.solve()
    assert solution is not None
    assert len(solution) == 5 * 3 # 3 employees * 5 days
    
    # 3. Simulate Data for View
    # Convert solution list of dicts to a structure suitable for DataFrame
    # In the app we pivot, here we can just verify content
    
    # 4. Verify Export
    # Create a dummy DF simulating the grid
    data = {
        'A': {'1': 'M', '2': 'P'},
        'B': {'1': 'P', '2': 'M'}
    }
    df = pd.DataFrame(data)
    
    excel_bytes = to_excel(df)
    assert excel_bytes is not None
    assert len(excel_bytes) > 0
    assert excel_bytes.startswith(b'PK') # Valid Excel/Zip header
