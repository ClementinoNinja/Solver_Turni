from datetime import date

from src.engine.solver import ShiftSolver
from src.models.employee import Employee
from src.models.shift import Shift


def test_hour_balance_uses_fractional_shift_hours_without_mutating_defaults():
    employee = Employee(id="employee-1")
    day = date(2026, 1, 6)
    solver = ShiftSolver([employee], [day])
    shifts = dict(solver.shifts)
    shifts["1"] = Shift("1", 7.25, False, "Mattina")
    solver.shifts = shifts
    solver.constraints_manager.shifts = shifts
    solver.constraints_manager.add_one_shift_per_day()
    solver.objective_function.add_hours_balance_objective(
        [employee], [day], solver.work, shifts, {employee.id: 7.25}
    )
    solver.objective_function.set_minimization()
    solution, stats = solver.solve()
    assert stats["status"] == "OPTIMAL"
    assert solution[0]["shift_code"] == "1"
    assert ShiftSolver([employee], [day]).shifts["1"].weight == 7.0


def test_part_time_target_is_scaled_from_the_full_time_target():
    employee = Employee(id="part-time", contract_percentage=50)
    assert employee.calculate_target_hours(20) == 60.0
    assert employee.calculate_target_hours(20, daily_target_hours=7.5) == 75.0
