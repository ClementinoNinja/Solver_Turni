from datetime import date

from src.engine.validation import validate_roster
from src.models.employee import Employee


def test_complete_coverage_validates_for_all_three_operational_shifts():
    employees = [
        Employee(id=f"inf-{index}", ruolo="INF") for index in range(8)
    ] + [
        Employee(id=f"oss-{index}", ruolo="OSS") for index in range(3)
    ]
    day = date(2026, 1, 6)
    codes = ["1", "1", "1", "K", "K", "K", "N", "N", "1", "K", "N"]
    entries = [
        {
            "employee_id": employee.id,
            "data": day.isoformat(),
            "shift_code": code,
        }
        for employee, code in zip(employees, codes)
    ]
    assert validate_roster(entries, employees, [day]) == []


def test_validation_rejects_an_unrequested_absence():
    employee = Employee(id="employee-1")
    day = date(2026, 1, 6)
    errors = validate_roster(
        [{"employee_id": employee.id, "data": day.isoformat(), "shift_code": "F"}],
        [employee],
        [day],
    )
    assert any("Assenza senza richiesta approvata" in error for error in errors)


def test_validation_rejects_three_consecutive_nights_across_month_boundary():
    employee = Employee(id="employee-1")
    days = [date(2026, 1, 1)]
    entries = [
        {"employee_id": employee.id, "data": days[0].isoformat(), "shift_code": "N"}
    ]
    errors = validate_roster(
        entries, [employee], days,
        previous_shifts={employee.id: ["N", "N"]},
    )
    assert any("notti consecutive" in error for error in errors)


def test_validation_rejects_three_nights_ending_in_next_month():
    employee = Employee(id="employee-1")
    days = [date(2026, 1, 1), date(2026, 1, 2)]
    entries = [
        {"employee_id": employee.id, "data": day.isoformat(), "shift_code": "N"}
        for day in days
    ]
    errors = validate_roster(
        entries, [employee], days,
        next_shifts={employee.id: ["N"]},
    )
    assert any("notti consecutive" in error for error in errors)
