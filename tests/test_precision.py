import sys
import os
sys.path.append(os.getcwd())
import pytest
from datetime import date
from src.engine.solver import ShiftSolver
from src.models.employee import Employee
from src.models.shift import Shift
from ortools.sat.python import cp_model

def test_decimal_precision():
    # Setup: 1 Employee, 1 Day.
    employees = [Employee(id="1", nome_cognome="Tester", team_id=1)]
    days = [date(2024, 1, 1)]
    
    solver = ShiftSolver(employees, days)
    
    # 1. Inject Custom Shifts *AND* Rebuild Var Map if needed? 
    # Solver.__init__ builds self.shifts then self.work.
    # self.work keys depend on self.shifts keys.
    # If we add 'A' to shifts AFTER init, self.work doesn't have it.
    # So we must use existing keys '1', 'K' but change properties.
    
    solver.shifts['1'] = Shift('1', 7.25, False, 'Decimale')
    solver.shifts['K'] = Shift('K', 7.00, False, 'Intero')
    
    # We relax all hard constraints that might use other shifts or logic
    # We only use "One Shift Per Day" which iterates over solver.shifts keys.
    solver.constraints_manager.add_one_shift_per_day()
    
    # Target 7.25 exactly
    target_map = {'1': 7.25}
    
    # Add Objective
    solver.objective_function.add_hours_balance_objective(
        employees, days, solver.work, solver.shifts, target_map
    )
    solver.objective_function.set_minimization()
    
    # Solve
    solution, stats = solver.solve()
    
    assert solution is not None, "Solver return None"
    assert stats['status'] in ['OPTIMAL', 'FEASIBLE'], f"Status: {stats['status']}"
    
    # Should pick '1' (7.25) because it matches target 7.25 perfectly. 
    # 'K' (7.00) has diff 0.25.
    
    s = [x for x in solution if x['employee_id'] == '1'][0]
    assigned = s['shift_code']
    print(f"Assigned: {assigned}")
    
    # If logic works, it picks '1'.
    assert assigned == '1', f"Expected '1' (7.25) match, got {assigned}"

if __name__ == "__main__":
    test_decimal_precision()
