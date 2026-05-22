from ortools.sat.python import cp_model
from typing import List, Dict
from datetime import date
from src.models.employee import Employee
from src.models.shift import SHIFT_DEFINITIONS, Shift

class ShiftSolver:
    def __init__(self, employees: List[Employee], days: List[date], requests: List[dict] = None):
        self.employees = employees
        self.days = days
        self.requests = requests or []
        self.shifts = SHIFT_DEFINITIONS
        self.model = cp_model.CpModel()
        self.work = {} # Decision variables work[emp_id, date_str, shift_code]

        self._init_variables()
        
        # Initialize constraints manager
        from src.engine.constraints import ConstraintsManager
        self.constraints_manager = ConstraintsManager(
            self.model, self.shifts, self.employees, self.days, self.work
        )
        
        # Initialize objective function
        from src.engine.objectives import ObjectiveFunction
        self.objective_function = ObjectiveFunction(self.model)

    def add_hard_constraints(self):
        self.constraints_manager.add_one_shift_per_day()
        # self.constraints_manager.add_min_coverage(min_coverage) # Deprecated Sprint 7
        self.constraints_manager.add_role_coverage()
        self.constraints_manager.add_max_shift_capacity(5)
        self.constraints_manager.add_no_morning_after_night()
        self.constraints_manager.add_smonto_consistent_constraint()
        self.constraints_manager.add_night_limitation_constraint()
        # Apply requests constraints
        if self.requests:
             self.constraints_manager.add_request_constraints(self.requests)

    def add_soft_constraints(self):
        # Parametri penalità hardcoded per ora o passati come argomenti
        self.constraints_manager.add_tripletta_constraint(self.objective_function, penalty_cost=100)
        
        # Balance Hours Objective (Sprint 7.3)
        # Calculate target for this specific month
        if self.days:
            year = self.days[0].year
            month = self.days[0].month
            from src.utils.holidays import get_monthly_target_hours
            monthly_target = get_monthly_target_hours(year, month)
            
            # Create map (all emps have same target for now, usually based on contract)
            # Future: Employee.contract_percentage * monthly_target
            target_map = {e.id: monthly_target for e in self.employees}
            
            self.objective_function.add_hours_balance_objective(
                self.employees, self.days, self.work, self.shifts, target_map
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
        solver.parameters.max_time_in_seconds = 60.0
        
        status = solver.Solve(self.model)
        
        stats = {
            "status": solver.StatusName(status),
            "obj_value": solver.ObjectiveValue(),
            "wall_time": solver.WallTime(),
            "branches": solver.NumBranches()
        }
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return self._extract_solution(solver), stats
        return None, stats

    def _extract_solution(self, solver):
        solution = []
        for emp in self.employees:
            for d in self.days:
                date_str = d.strftime("%Y-%m-%d")
                for shift_code in self.shifts.keys():
                    if solver.BooleanValue(self.work[emp.id, date_str, shift_code]):
                        solution.append({
                            'employee_id': emp.id,
                            'data': date_str,
                            'shift_code': shift_code
                        })
        return solution
