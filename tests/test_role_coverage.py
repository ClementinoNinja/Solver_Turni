from datetime import date

import pytest

from src.engine.solver import ShiftSolver
from src.models.employee import Employee


def test_configured_role_coverage_is_satisfiable():
    employees = [
        Employee(id=f"inf-{index}", ruolo="INF") for index in range(8)
    ] + [
        Employee(id=f"oss-{index}", ruolo="OSS") for index in range(3)
    ]
    day = date(2026, 1, 6)
    solver = ShiftSolver(employees, [day])
    solver.constraints_manager.add_one_shift_per_day()
    solver.constraints_manager.add_role_coverage()
    solver.constraints_manager.add_max_shift_capacity()
    solution, stats = solver.solve()
    assert stats["status"] in {"OPTIMAL", "FEASIBLE"}
    assignments = {entry["employee_id"]: entry["shift_code"] for entry in solution}
    assert sum(code == "1" for code in assignments.values()) >= 4
    assert sum(code == "K" for code in assignments.values()) >= 4
    assert sum(code == "N" for code in assignments.values()) >= 3


def test_role_coverage_reports_a_missing_role():
    solver = ShiftSolver(
        [Employee(id="inf-1", ruolo="INF")], [date(2026, 1, 6)]
    )
    with pytest.raises(ValueError, match="Nessun dipendente con ruolo OSS"):
        solver.constraints_manager.add_role_coverage()
