from datetime import date, timedelta

from src.engine.solver import ShiftSolver
from src.models.employee import Employee


def _days(count):
    start = date(2026, 9, 1)
    return [start + timedelta(days=offset) for offset in range(count)]


def test_three_consecutive_nights_are_infeasible():
    employee = Employee(id="employee-1")
    days = _days(3)
    solver = ShiftSolver([employee], days)
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_max_consecutive_nights_constraint()
    for day in days:
        solver.model.Add(solver.work[employee.id, day.isoformat(), "N"] == 1)

    solution, stats = solver.solve()
    assert solution is None
    assert stats["status"] == "INFEASIBLE"


def test_two_consecutive_nights_are_allowed():
    employee = Employee(id="employee-1")
    days = _days(3)
    solver = ShiftSolver([employee], days)
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_max_consecutive_nights_constraint()
    solver.model.Add(solver.work[employee.id, days[0].isoformat(), "N"] == 1)
    solver.model.Add(solver.work[employee.id, days[1].isoformat(), "N"] == 1)
    solver.model.Add(solver.work[employee.id, days[2].isoformat(), "R"] == 1)

    solution, stats = solver.solve()
    assert stats["status"] in {"OPTIMAL", "FEASIBLE"}
    assert solution is not None


def test_night_limit_includes_previous_month_context():
    employee = Employee(id="employee-1")
    days = _days(1)
    solver = ShiftSolver([employee], days, previous_shifts={employee.id: ["N", "N"]})
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_max_consecutive_nights_constraint()
    solver.model.Add(solver.work[employee.id, days[0].isoformat(), "N"] == 1)

    solution, stats = solver.solve()
    assert solution is None
    assert stats["status"] == "INFEASIBLE"


def test_night_limit_includes_next_month_context():
    employee = Employee(id="employee-1")
    days = _days(2)
    solver = ShiftSolver([employee], days, next_shifts={employee.id: ["N"]})
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_max_consecutive_nights_constraint()
    for day in days:
        solver.model.Add(solver.work[employee.id, day.isoformat(), "N"] == 1)

    solution, stats = solver.solve()
    assert solution is None
    assert stats["status"] == "INFEASIBLE"


def test_night_balance_objective_distributes_equal_availability_evenly():
    employees = [Employee(id=f"employee-{index}") for index in range(3)]
    days = _days(6)
    solver = ShiftSolver(employees, days)
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_max_consecutive_nights_constraint()
    for employee in employees:
        for day in days:
            day_key = day.isoformat()
            solver.model.Add(solver.work[employee.id, day_key, "N"]
                             + solver.work[employee.id, day_key, "R"] == 1)
    solver.model.Add(
        sum(solver.work[employee.id, day.isoformat(), "N"] for employee in employees for day in days) == 6
    )
    solver.objective_function.add_night_balance_objective(
        employees, days, solver.work, penalty_cost=20
    )
    solver.objective_function.set_minimization()

    solution, stats = solver.solve()
    night_counts = {
        employee.id: sum(
            entry["employee_id"] == employee.id and entry["shift_code"] == "N"
            for entry in solution
        )
        for employee in employees
    }
    assert stats["status"] == "OPTIMAL"
    assert set(night_counts.values()) == {2}
