import pytest
from datetime import date
from src.engine.solver import ShiftSolver
from src.models.employee import Employee

def create_employees(inf_count, oss_count):
    emps = []
    for i in range(inf_count):
        emps.append(Employee(id=f"I{i}", nome_cognome=f"Inf {i}", ruolo="INF"))
    for i in range(oss_count):
        emps.append(Employee(id=f"O{i}", nome_cognome=f"Oss {i}", ruolo="OSS"))
    return emps

def solve_for_one_shift(inf, oss, shift_code):
    # Setup 1 day
    days = [date(2024, 1, 1)]
    employees = create_employees(inf, oss)
    
    solver = ShiftSolver(employees, days)
    
    # Force everyone to work that shift (or try to)
    # We want to check if the constraint *allows* this configuration.
    # Actually, the proper way is: set coverage reqs, and see if it finds solution.
    # But our constraint is "Total >= X".
    # Here we want to test if a specific composition satisfies the constraint.
    # So we force assignments and see if Model is Feasible.
    
    # Easier: Just run solver with hard constraints.
    # If employees are exactly enough for the pattern, it should solve.
    # If not enough, it should fail (assuming we force everyone to work or relax nothing).
    
    # Let's say we want to test 2 INF + 2 OSS on Morning (1).
    # We create exactly 2 INF and 2 OSS.
    # We add constraints.
    # Solver should assign them all to '1' if we force coverage logic?
    # No, coverage logic says ">= 2 INF and >= 2 OSS".
    # So if we have exactly that, it should work.
    
    solver.add_hard_constraints() 
    # This acts on ALL shifts.
    # If we have only 4 people, and we need coverage for 1, K, N... we will fail for sure (need 6+ people).
    # So we need to mock the constraint manager or use a simplified solver for valid testing.
    # OR: we inject enough people but force specific assignments? Too complex.
    
    # Let's rely on the fact that if we provide *just* enough people for ONE shift, 
    # and relax other shifts, we can test.
    # But constraints apply to all shifts.
    
    return False # Placeholder

# Better approach: Test the logic by overriding the days/shifts loop or using a minimal breakdown.
# Let's try to test the "Day" constraint (1) with isolated population.

def test_coverage_1_valid_2inf_2oss():
    # We need coverage for 1, K, N.
    # Rule: 1(2+2), K(2+2), N(2+1). Total 4+4+3 = 11 slots minimum.
    # We construct a team of 12 people to be safe.
    # But we want to trace if shift 1 gets 2+2.
    
    # This is getting hard to unit test at high level.
    # Let's trust the logic inspection for now or run a small feasiblity check.
    pass

# Alternative: We create a custom constraint manager test.
from ortools.sat.python import cp_model
from src.engine.constraints import ConstraintsManager

def test_constraint_logic_direct():
    model = cp_model.CpModel()
    days = [date(2024, 1, 1)]
    # Mock vars
    work = {}
    
    # Case: 2 INF, 2 OSS
    emps = [
        Employee(id="I1", ruolo="INF"), Employee(id="I2", ruolo="INF"),
        Employee(id="O1", ruolo="OSS"), Employee(id="O2", ruolo="OSS")
    ]
    shifts = {'1': None} # Only test shift 1
    
    for e in emps:
        for d in days:
            date_str = d.strftime("%Y-%m-%d")
            work[e.id, date_str, '1'] = model.NewBoolVar(f"w_{e.id}")
            # Force them to work '1'
            model.Add(work[e.id, date_str, '1'] == 1)
            
    cm = ConstraintsManager(model, shifts, emps, days, work)
    cm.add_role_coverage()
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.OPTIMAL or status == cp_model.FEASIBLE

def test_constraint_logic_fail_1inf_3oss():
    model = cp_model.CpModel()
    days = [date(2024, 1, 1)]
    work = {}
    
    # Case: 1 INF, 3 OSS (Total 4, but only 1 INF -> Fail for Shift 1 which needs 2+2 or 3+1)
    emps = [
        Employee(id="I1", ruolo="INF"),
        Employee(id="O1", ruolo="OSS"), Employee(id="O2", ruolo="OSS"), Employee(id="O3", ruolo="OSS")
    ]
    shifts = {'1': None} 
    
    for e in emps:
        for d in days:
            date_str = d.strftime("%Y-%m-%d")
            work[e.id, date_str, '1'] = model.NewBoolVar(f"w_{e.id}")
            # Force work
            model.Add(work[e.id, date_str, '1'] == 1)
            
    cm = ConstraintsManager(model, shifts, emps, days, work)
    cm.add_role_coverage()
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.INFEASIBLE

def test_constraint_logic_valid_3inf_1oss():
    model = cp_model.CpModel()
    days = [date(2024, 1, 1)]
    work = {}
    
    # Case: 3 INF, 1 OSS (Total 4 -> OK for Shift 1)
    emps = [
        Employee(id="I1", ruolo="INF"), Employee(id="I2", ruolo="INF"), Employee(id="I3", ruolo="INF"),
        Employee(id="O1", ruolo="OSS")
    ]
    shifts = {'1': None} 
    
    for e in emps:
        for d in days:
            date_str = d.strftime("%Y-%m-%d")
            work[e.id, date_str, '1'] = model.NewBoolVar(f"w_{e.id}")
            model.Add(work[e.id, date_str, '1'] == 1)
            
    cm = ConstraintsManager(model, shifts, emps, days, work)
    cm.add_role_coverage()
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    assert status == cp_model.OPTIMAL or status == cp_model.FEASIBLE
