from datetime import date

from src.engine.solver import ShiftSolver
from src.models.employee import Employee


def solve_with_forced_shifts(days, forced, previous_shifts=None):
    employee = Employee(id="employee-1", nome_cognome="Test")
    solver = ShiftSolver([employee], days, previous_shifts=previous_shifts)
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_smonto_consistent_constraint()
    for work_date, shift_code in forced.items():
        solver.model.Add(solver.work[employee.id, work_date, shift_code] == 1)
    return solver.solve()


def test_smonto_is_allowed_after_a_night():
    days = [date(2026, 1, 1), date(2026, 1, 2)]
    solution, stats = solve_with_forced_shifts(
        days,
        {("2026-01-01", "N"): True, ("2026-01-02", "S"): True},
    )
    assert stats["status"] in {"OPTIMAL", "FEASIBLE"}
    assert {(entry["data"], entry["shift_code"]) for entry in solution} == {
        ("2026-01-01", "N"), ("2026-01-02", "S")
    }


def test_smonto_is_forbidden_without_a_preceding_night():
    days = [date(2026, 1, 1), date(2026, 1, 2)]
    solution, stats = solve_with_forced_shifts(
        days, {("2026-01-01", "F"): True, ("2026-01-02", "S"): True}
    )
    assert solution is None
    assert stats["status"] == "INFEASIBLE"


def test_first_day_smonto_uses_previous_month_context():
    day = date(2026, 1, 1)
    solution, stats = solve_with_forced_shifts(
        [day], {("2026-01-01", "S"): True}, previous_shifts={"employee-1": "N"}
    )
    assert stats["status"] in {"OPTIMAL", "FEASIBLE"}
    assert solution[0]["shift_code"] == "S"


def test_first_day_smonto_is_forbidden_when_previous_shift_is_unknown():
    day = date(2026, 1, 1)
    solution, stats = solve_with_forced_shifts(
        [day], {("2026-01-01", "S"): True}
    )
    assert solution is None
    assert stats["status"] == "INFEASIBLE"
