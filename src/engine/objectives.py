from ortools.sat.python import cp_model
from src.utils.workload import credited_shift_hours, hours_to_solver_units
from datetime import date

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

    def add_hours_balance_objective(self, employees, days, work, shifts, target_hours_map,
                                    penalty_cost: int = 5):
        """
        Soft Constraint: Minimizza la deviazione dal monte ore target mensile.
        Gestisce pesi decimali (es. 7.25) moltiplicando tutto per 100.
        """
        SCALING_FACTOR = 100
        
        for emp in employees:
            target_float = target_hours_map.get(emp.id, 156.0) 
            from decimal import Decimal
            target_scaled = hours_to_solver_units(Decimal(str(target_float)), SCALING_FACTOR)
            
            # Calcola ore assegnate (espressione lineare)
            assigned_hours_expr = []
            for d in days:
                date_str = d.strftime("%Y-%m-%d")
                for s_code in shifts:
                    weight = credited_shift_hours(s_code, d, shifts)
                    weight_scaled = hours_to_solver_units(weight, SCALING_FACTOR)
                    if weight_scaled:
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
            self.penalties.append(abs_diff * penalty_cost)

    def add_night_balance_objective(self, employees, days, work, requests=(), locked_roster=(),
                                    penalty_cost: int = 20):
        """Distribuisce le notti per ruolo in proporzione a contratto e giorni disponibili."""
        if not days or penalty_cost <= 0:
            return

        absence_types = {"FERIE", "MALATTIA", "104", "PERMESSO"}
        approved = {"APPROVED", "APPROVATO"}
        absence_dates = set()
        for request in requests:
            if str(request.get("stato", "")).strip().upper() not in approved:
                continue
            kind = str(request.get("tipo_richiesta", request.get("tipo", ""))).strip().upper()
            if kind not in absence_types:
                continue
            try:
                start = date.fromisoformat(str(request["data_inizio"])[:10])
                end = date.fromisoformat(str(request["data_fine"])[:10])
            except (KeyError, TypeError, ValueError):
                continue
            for day in days:
                if start <= day <= end:
                    absence_dates.add((request.get("employee_id"), day.isoformat()))

        locked = {
            (row.get("employee_id"), str(row.get("data", ""))[:10]): row.get("shift_code")
            for row in locked_roster if row.get("is_locked")
        }
        day_keys = [day.isoformat() for day in days]

        for role in sorted({employee.ruolo for employee in employees}):
            eligible = []
            for employee in employees:
                if employee.ruolo != role or employee.limitazione_notte:
                    continue
                available_days = sum(
                    1 for day_key in day_keys
                    if (employee.id, day_key) not in absence_dates
                    and ((employee.id, day_key) not in locked or locked[(employee.id, day_key)] == "N")
                )
                if available_days <= 0:
                    continue
                weight = int(round(employee.contract_percentage * 100)) * available_days
                count = sum(work[employee.id, day_key, "N"] for day_key in day_keys)
                eligible.append((employee, weight, count))

            total_weight = sum(weight for _, weight, _ in eligible)
            if total_weight <= 0:
                continue
            total_nights = sum(count for _, _, count in eligible)
            max_delta = max(1, len(days) * len(eligible) * total_weight * 2)

            for employee, weight, count in eligible:
                delta = self.model.NewIntVar(-max_delta, max_delta, f"night_share_{role}_{employee.id}")
                abs_delta = self.model.NewIntVar(0, max_delta, f"abs_night_share_{role}_{employee.id}")
                deviation = self.model.NewIntVar(0, 100 * len(days), f"scaled_night_share_{role}_{employee.id}")
                self.model.Add(delta == count * total_weight - total_nights * weight)
                self.model.AddAbsEquality(abs_delta, delta)
                self.model.AddDivisionEquality(deviation, abs_delta * 100, total_weight)
                self.penalties.append(deviation * penalty_cost)
