from datetime import date

from src.engine.solver import ShiftSolver
from src.models.employee import Employee


def test_cycle_objective_prefers_the_next_shift_without_team_ids():
    employee = Employee(id="employee-1")
    days = [date(2026, 1, 5), date(2026, 1, 6)]
    solver = ShiftSolver([employee], days)
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_cycle_transition_objective(solver.objective_function)
    solver.model.Add(solver.work[employee.id, days[0].isoformat(), "1"] == 1)
    solver.objective_function.set_minimization()
    solution, stats = solver.solve()
    shifts = {entry["data"]: entry["shift_code"] for entry in solution}
    assert shifts[days[1].isoformat()] == "K"
    assert stats["obj_value"] == 0
