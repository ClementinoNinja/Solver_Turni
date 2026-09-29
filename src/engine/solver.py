from ortools.sat.python import cp_model
from typing import List, Dict
from datetime import date
from src.models.employee import Employee
from src.models.shift import SHIFT_DEFINITIONS, Shift
from src.engine.config import DEFAULT_SOLVER_CONFIG, SolverConfig

class ShiftSolver:
    def __init__(self, employees: List[Employee], days: List[date], requests: List[dict] = None,
                 locked_roster: List[dict] = None, previous_shifts: Dict[str, str] = None,
                 next_shifts: Dict[str, str] = None, config: SolverConfig = None):
        self.employees = employees
        self.days = days
        self.requests = requests or []
        self.locked_roster = locked_roster or []
        self.previous_shifts = previous_shifts or {}
        self.next_shifts = next_shifts or {}
        self.config = config or DEFAULT_SOLVER_CONFIG
        # Ogni solver possiede il proprio snapshot: i test e le personalizzazioni
        # non devono mutare le definizioni condivise tra generazioni.
        self.shifts = dict(SHIFT_DEFINITIONS)
        self.model = cp_model.CpModel()
        self.work = {} # Decision variables work[emp_id, date_str, shift_code]

        self._init_variables()
        
        # Initialize constraints manager
        from src.engine.constraints import ConstraintsManager
        self.constraints_manager = ConstraintsManager(
            self.model, self.shifts, self.employees, self.days, self.work,
            locked_roster=self.locked_roster,
            previous_shifts=self.previous_shifts,
            next_shifts=self.next_shifts,
            config=self.config,
        )
        
        # Initialize objective function
        from src.engine.objectives import ObjectiveFunction
        self.objective_function = ObjectiveFunction(self.model)

    def add_hard_constraints(self):
        self.constraints_manager.add_one_shift_per_day()
        self.constraints_manager.add_locked_shift_constraints()
        self.constraints_manager.add_absence_request_requirement(self.requests)
        # self.constraints_manager.add_min_coverage(min_coverage) # Deprecated Sprint 7
        self.constraints_manager.add_role_coverage()
        self.constraints_manager.add_max_shift_capacity()
        self.constraints_manager.add_no_morning_after_night()
        self.constraints_manager.add_smonto_consistent_constraint()
        self.constraints_manager.add_night_limitation_constraint()
        # Apply requests constraints
        if self.requests:
            self.constraints_manager.add_request_constraints(
                self.requests, objective_function=self.objective_function,
                preference_penalty=self.config.preference_penalty,
            )

    def add_soft_constraints(self):
        # Parametri penalità hardcoded per ora o passati come argomenti
        self.constraints_manager.add_tripletta_constraint(self.objective_function)
        
        # Balance Hours Objective (Sprint 7.3)
        # Calculate target for this specific month
        if self.days:
            year = self.days[0].year
            month = self.days[0].month
            from src.utils.holidays import get_monthly_target_hours
            monthly_target = get_monthly_target_hours(
                year, month, daily_target=self.config.daily_target_hours
            )
            
            # Create map (all emps have same target for now, usually based on contract)
            # Future: Employee.contract_percentage * monthly_target
            target_map = {
                e.id: monthly_target * e.contract_percentage / 100.0
                for e in self.employees
            }
            
            self.objective_function.add_hours_balance_objective(
                self.employees, self.days, self.work, self.shifts, target_map,
                penalty_cost=self.config.hours_deviation_penalty,
            )
        
        # Finalize objective
        self.objective_function.set_minimization()

    def _init_variables(self):
        """
        Crea le variabili booleane:
        work[e, d, s] = 1 se il dipendente e lavora il turno s nel giorno d.
        """
        for emp in self.employees:
            for d in self.days:
                date_str = d.strftime("%Y-%m-%d")
                for shift_code in self.shifts.keys():
                    self.work[emp.id, date_str, shift_code] = self.model.NewBoolVar(
                        f'work_{emp.id}_{date_str}_{shift_code}'
                    )

    def solve(self):
        solver = cp_model.CpSolver()
        # Setting parameters (time limit, etc)
        solver.parameters.max_time_in_seconds = self.config.max_time_seconds
        
        status = solver.Solve(self.model)
        
        has_solution = status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
        stats = {
            "status": solver.StatusName(status),
            "obj_value": solver.ObjectiveValue() if has_solution else None,
            "best_bound": solver.BestObjectiveBound() if has_solution else None,
            "wall_time": solver.WallTime(),
            "branches": solver.NumBranches()
        }
        
        if has_solution:
            return self._extract_solution(solver), stats
        return None, stats

    def _extract_solution(self, solver):
        solution = []
        locked_keys = {
            (row.get("employee_id"), str(row.get("data", ""))[:10], row.get("shift_code"))
            for row in self.locked_roster
            if row.get("is_locked")
        }
        for emp in self.employees:
            for d in self.days:
                date_str = d.strftime("%Y-%m-%d")
                for shift_code in self.shifts.keys():
                    if solver.BooleanValue(self.work[emp.id, date_str, shift_code]):
                        solution.append({
                            'employee_id': emp.id,
                            'data': date_str,
                            'shift_code': shift_code,
                            'is_locked': (emp.id, date_str, shift_code) in locked_keys,
                        })
        return solution
