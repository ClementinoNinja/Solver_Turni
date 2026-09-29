from datetime import date

from src.engine.solver import ShiftSolver
from src.models.employee import Employee


def test_tripletta_cycle_is_a_penalty_not_a_hard_constraint():
    employee = Employee(id="employee-1", team_id=1)
    day = date(2026, 1, 5)
    solver = ShiftSolver([employee], [day])
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_tripletta_constraint(solver.objective_function)
    solver.model.Add(solver.work[employee.id, day.isoformat(), "K"] == 1)
    solver.objective_function.set_minimization()
    solution, stats = solver.solve()
    assert solution[0]["shift_code"] == "K"
    assert stats["obj_value"] == 100
