from datetime import date

from src.engine.solver import ShiftSolver
from src.models.employee import Employee


def test_employee_with_night_limitation_cannot_be_assigned_a_night():
    employee = Employee(id="employee-1", limitazione_notte=True)
    day = date(2026, 1, 6)
    solver = ShiftSolver([employee], [day])
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_night_limitation_constraint()
    solver.model.Add(solver.work[employee.id, day.isoformat(), "N"] == 1)
    solution, stats = solver.solve()
    assert solution is None
    assert stats["status"] == "INFEASIBLE"
