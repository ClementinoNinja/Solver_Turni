from typing import List
from ortools.sat.python import cp_model

class ObjectiveFunction:
    def __init__(self, model: cp_model.CpModel):
        self.model = model
        self.penalties = []

    def add_penalty(self, condition_var, cost: int):
        """
        Aggiunge una penalità se condition_var è True (1).
        cost: intero positivo.
        """
        if cost > 0:
            self.penalties.append(condition_var * cost)

    def set_minimization(self):
        if self.penalties:
            self.model.Minimize(sum(self.penalties))
        else:
            # Se non ci sono penalità, basta trovare una soluzione (o minimizzare 0)
            self.model.Minimize(0)

    def add_hours_balance_objective(self, employees, days, work, shifts, target_hours_map):
        """
        Soft Constraint: Minimizza la deviazione dal monte ore target mensile.
        Gestisce pesi decimali (es. 7.25) moltiplicando tutto per 100.
        """
        SCALING_FACTOR = 100
        
        for emp in employees:
            target_float = target_hours_map.get(emp.id, 156.0) 
            target_scaled = int(target_float * SCALING_FACTOR)
            
            # Calcola ore assegnate (espressione lineare)
            assigned_hours_expr = []
            for d in days:
                date_str = d.strftime("%Y-%m-%d")
                for s_code, shift in shifts.items():
                    if shift.weight > 0:
                        # Converti peso float (es. 7.25) in int scalato (725)
                        weight_scaled = int(shift.weight * SCALING_FACTOR)
                        assigned_hours_expr.append(work[emp.id, date_str, s_code] * weight_scaled)
            
            total_hours_scaled = sum(assigned_hours_expr)
            
            # Deviazione assoluta: |total - target|
            # Ora tutto è in centesimi di ora
            diff = self.model.NewIntVar(-100000, 100000, f'diff_hours_{emp.id}')
            abs_diff = self.model.NewIntVar(0, 100000, f'abs_diff_hours_{emp.id}')
            
            self.model.Add(diff == total_hours_scaled - target_scaled)
            self.model.AddAbsEquality(abs_diff, diff)
            
            # Penalità
            # Se lo scarto è 1 ora (100 punti), penalità 500.
            if self.penalties is None: self.penalties = []
            self.penalties.append(abs_diff * 5)
