from datetime import date

from src.engine.solver import ShiftSolver
from src.models.employee import Employee


def test_preference_penalty_is_configurable():
    employee = Employee(id="employee-1")
    day = date(2026, 1, 6)
    request = {
        "employee_id": employee.id,
        "tipo_richiesta": "MATTINA (PREF)",
        "stato": "APPROVED",
        "data_inizio": day.isoformat(),
        "data_fine": day.isoformat(),
    }
    solver = ShiftSolver(
        [employee], [day], requests=[request],
    )
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_absence_request_requirement([request])
    solver.constraints_manager.add_request_constraints(
        [request], objective_function=solver.objective_function,
        preference_penalty=37,
    )
    solver.model.Add(solver.work[employee.id, day.isoformat(), "K"] == 1)
    solver.objective_function.set_minimization()
    solution, stats = solver.solve()
    assert solution[0]["shift_code"] == "K"
    assert stats["obj_value"] == 37
