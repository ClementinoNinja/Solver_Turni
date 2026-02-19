import pytest
from src.models.employee import Employee
from src.models.shift import SHIFT_DEFINITIONS, ShiftType

def test_shift_definitions():
    assert SHIFT_DEFINITIONS['1'].weight == 7.0
    assert SHIFT_DEFINITIONS['N'].weight == 10.0
    assert SHIFT_DEFINITIONS['F'].is_absence is True
    assert SHIFT_DEFINITIONS['1'].is_absence is False

def test_employee_creation():
    emp = Employee(
        id="123",
        matricola="MAT001",
        nome_cognome="Mario Rossi",
        ruolo="INF",
        team_id=1,
        limitazione_notte=False
    )
    assert emp.nome_cognome == "Mario Rossi"
    assert emp.ruolo == "INF"

def test_employee_target_hours():
    emp = Employee()
    # Assuming standard calculation: working_days * 6.0
    working_days = 20
    assert emp.calculate_target_hours(working_days) == 120.0
