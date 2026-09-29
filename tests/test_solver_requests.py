from datetime import date

import pytest

from src.engine.solver import ShiftSolver
from src.models.employee import Employee


def make_solver(requests=()):
    solver = ShiftSolver(
        [Employee(id="employee-1", nome_cognome="Test")],
        [date(2026, 1, 6)],
        requests=list(requests),
    )
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_absence_request_requirement(list(requests))
    solver.constraints_manager.add_request_constraints(
        list(requests), objective_function=solver.objective_function
    )
    solver.objective_function.set_minimization()
    return solver


def test_solver_does_not_create_an_unrequested_absence():
    solution, _ = make_solver().solve()
    assert solution
    assert solution[0]["shift_code"] not in {"F", "M", "104", "P"}


def test_approved_absence_is_forced():
    request = {
        "employee_id": "employee-1",
        "tipo_richiesta": "FERIE",
        "stato": "Approvato",
        "data_inizio": "2026-01-06",
        "data_fine": "2026-01-06",
    }
    solution, _ = make_solver([request]).solve()
    assert solution[0]["shift_code"] == "F"


def test_pending_absence_is_not_applied_or_generated():
    request = {
        "employee_id": "employee-1",
        "tipo_richiesta": "MALATTIA",
        "stato": "PENDING",
        "data_inizio": "2026-01-06",
        "data_fine": "2026-01-06",
    }
    solution, _ = make_solver([request]).solve()
    assert solution[0]["shift_code"] not in {"F", "M", "104", "P"}


def test_preferences_are_soft_and_can_be_unmet():
    request = {
        "employee_id": "employee-1",
        "tipo_richiesta": "Notte (Pref)",
        "stato": "APPROVED",
        "data_inizio": "2026-01-06",
        "data_fine": "2026-01-06",
    }
    solver = make_solver([request])
    solver.model.Add(solver.work["employee-1", "2026-01-06", "N"] == 0)
    solution, _ = solver.solve()
    assert solution[0]["shift_code"] != "N"


def test_inverted_request_dates_are_rejected():
    request = {
        "employee_id": "employee-1",
        "tipo_richiesta": "FERIE",
        "stato": "APPROVED",
        "data_inizio": "2026-01-07",
        "data_fine": "2026-01-06",
    }
    with pytest.raises(ValueError, match="invertito"):
        make_solver([request])
