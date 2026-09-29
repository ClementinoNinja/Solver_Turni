from datetime import date

from src.engine.solver import ShiftSolver
from src.engine.validation import validate_roster
from src.models.employee import Employee


def test_local_generate_and_validate_one_day_schedule():
    employees = [
        Employee(id=f"inf-{index}", nome_cognome=f"INF {index}", ruolo="INF")
        for index in range(8)
    ] + [
        Employee(id=f"oss-{index}", nome_cognome=f"OSS {index}", ruolo="OSS")
        for index in range(3)
    ]
    day = date(2026, 1, 6)
    solver = ShiftSolver(employees, [day])
    solver.add_hard_constraints()
    solver.add_soft_constraints()
    solution, stats = solver.solve()
    assert stats["status"] in {"OPTIMAL", "FEASIBLE"}
    assert validate_roster(solution, employees, [day]) == []
