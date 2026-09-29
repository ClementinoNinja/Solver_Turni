from datetime import date, timedelta

from src.engine.solver import ShiftSolver
from src.models.employee import Employee


def test_locked_turn_is_kept():
    employee = Employee(id="employee-1")
    day = date(2026, 1, 6)
    solver = ShiftSolver(
        [employee], [day],
        locked_roster=[{
            "employee_id": employee.id, "data": day.isoformat(),
            "shift_code": "K", "is_locked": True,
        }],
    )
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_locked_shift_constraints()
    solution, stats = solver.solve()
    assert stats["status"] in {"OPTIMAL", "FEASIBLE"}
    assert solution[0]["shift_code"] == "K"
    assert solution[0]["is_locked"] is True


def test_night_cannot_be_followed_by_morning():
    employee = Employee(id="employee-1")
    days = [date(2026, 1, 6) + timedelta(days=i) for i in range(2)]
    solver = ShiftSolver([employee], days)
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_no_morning_after_night()
    solver.model.Add(solver.work[employee.id, days[0].isoformat(), "N"] == 1)
    solver.model.Add(solver.work[employee.id, days[1].isoformat(), "1"] == 1)
    solution, stats = solver.solve()
    assert solution is None
    assert stats["status"] == "INFEASIBLE"


def test_month_boundary_observes_previous_and_next_turns():
    employee = Employee(id="employee-1")
    day = date(2026, 1, 1)
    solver = ShiftSolver(
        [employee], [day],
        previous_shifts={employee.id: "N"},
        next_shifts={employee.id: "1"},
    )
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_no_morning_after_night()
    solver.model.Add(solver.work[employee.id, day.isoformat(), "1"] == 1)
    solution, stats = solver.solve()
    assert solution is None
    assert stats["status"] == "INFEASIBLE"


def test_locked_turn_rejects_an_unknown_code():
    employee = Employee(id="employee-1")
    solver = ShiftSolver(
        [employee], [date(2026, 1, 1)],
        locked_roster=[{
            "employee_id": employee.id, "data": "2026-01-01",
            "shift_code": "UNKNOWN", "is_locked": True,
        }],
    )
    import pytest
    with pytest.raises(ValueError, match="non configurato"):
        solver.constraints_manager.add_locked_shift_constraints()
