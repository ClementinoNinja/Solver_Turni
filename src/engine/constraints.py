from ortools.sat.python import cp_model
class ConstraintsManager:
    def __init__(self, model: cp_model.CpModel, shifts: dict, employees: list, days: list, work: dict,
                 locked_roster=None, previous_shifts=None, next_shifts=None, config=None):
        from src.engine.config import DEFAULT_SOLVER_CONFIG
        self.model = model
        self.shifts = shifts
        self.employees = employees
        self.days = days
        self.work = work # The 3D decision variable matrix work[emp_id, day, shift_code]
        self.locked_roster = locked_roster or []
        self.previous_shifts = previous_shifts or {}
        self.next_shifts = next_shifts or {}
        self.config = config or DEFAULT_SOLVER_CONFIG

    @staticmethod
    def _shift_history(value):
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value]

    def add_locked_shift_constraints(self):
        """Mantiene fisse le assegnazioni che il responsabile ha bloccato."""
        valid_emp_ids = {emp.id for emp in self.employees}
        valid_days = {day.isoformat() for day in self.days}
        for entry in self.locked_roster:
            emp_id = entry.get('employee_id')
            day = str(entry.get('data', ''))[:10]
            code = entry.get('shift_code')
            if emp_id not in valid_emp_ids or day not in valid_days:
                continue
            if code not in self.shifts:
                raise ValueError(f"Codice turno non configurato per un turno bloccato: {code!r}.")
            self.model.Add(self.work[emp_id, day, code] == 1)

    def add_one_shift_per_day(self):
        """
        Hard Constraint: Ogni dipendente deve avere esattamente un turno assegnato per ogni giorno.
        (Ricorda che Riposo e Smonto sono 'turni' con peso 0).
        """
        for emp in self.employees:
            for d in self.days:
                date_str = d.strftime("%Y-%m-%d")
                # Sum of all shift assignments for this day must be 1
                self.model.Add(
                    sum(self.work[emp.id, date_str, s_code] for s_code in self.shifts.keys()) == 1
                )

    def add_role_coverage(self):
        """
        Hard Constraint: Copertura basata sui ruoli (INF/OSS).
        Regole (Hard-coded per Sprint 7):
        - Mattina (1) / Pomeriggio (K):
            (Min 2 INF + Min 2 OSS) OR (Min 3 INF + Min 1 OSS)
        - Notte (N):
            Min 2 INF + Min 1 OSS
        """
        inf_employees = [e for e in self.employees if e.ruolo == 'INF']
        oss_employees = [e for e in self.employees if e.ruolo == 'OSS']

        if not inf_employees:
            raise ValueError(
                "Nessun dipendente con ruolo INF trovato: impossibile soddisfare i vincoli di copertura. "
                "Aggiungere almeno 3 dipendenti INF attivi."
            )
        if not oss_employees:
            raise ValueError(
                "Nessun dipendente con ruolo OSS trovato: impossibile soddisfare i vincoli di copertura. "
                "Aggiungere almeno 1 dipendente OSS attivo."
            )
        
        for d in self.days:
            date_str = d.strftime("%Y-%m-%d")
            
            # --- Mattina (1) e Pomeriggio (K) ---
            for shift_code, options in self.config.daytime_coverage.items():
                if shift_code in self.shifts:
                    inf_sum = sum(self.work[e.id, date_str, shift_code] for e in inf_employees)
                    oss_sum = sum(self.work[e.id, date_str, shift_code] for e in oss_employees)
                    alternatives = []
                    for alternative_index, (min_inf, min_oss) in enumerate(options):
                        condition = self.model.NewBoolVar(
                            f'{date_str}_{shift_code}_coverage_{alternative_index}'
                        )
                        self.model.Add(inf_sum >= min_inf).OnlyEnforceIf(condition)
                        self.model.Add(oss_sum >= min_oss).OnlyEnforceIf(condition)
                        alternatives.append(condition)
                    self.model.AddBoolOr(alternatives)
            
            # --- Notte (N) ---
            if 'N' in self.shifts:
                # Rule: Min 2 INF + Min 1 OSS
                inf_sum_n = sum(self.work[e.id, date_str, 'N'] for e in inf_employees)
                oss_sum_n = sum(self.work[e.id, date_str, 'N'] for e in oss_employees)
                
                
                self.model.Add(inf_sum_n >= self.config.night_min_inf)
                self.model.Add(oss_sum_n >= self.config.night_min_oss)

    def add_max_shift_capacity(self, max_capacity: int = None):
        """
        Hard Constraint: Non ci possono essere più di `max_capacity` persone assegnate
        allo stesso turno (Mattina, Pomeriggio, Notte).
        """
        max_capacity = self.config.shift_capacity if max_capacity is None else max_capacity
        for d in self.days:
            date_str = d.strftime("%Y-%m-%d")
            
            # Controlla solo i turni operativi, ignorando Riposo (R), Smonto (S) e assenze
            operational_shifts = ['1', 'K', 'N']
            for shift_code in operational_shifts:
                if shift_code in self.shifts:
                    shift_sum = sum(self.work[e.id, date_str, shift_code] for e in self.employees)
                    self.model.Add(shift_sum <= max_capacity)

    def add_no_morning_after_night(self):
        """
        Hard Constraint: Se lavori Notte (N) oggi, non puoi fare Mattina (1) domani.
        """
        # Itera fino al penultimo giorno
        for i in range(len(self.days) - 1):
            today = self.days[i]
            tomorrow = self.days[i+1]
            today_str = today.strftime("%Y-%m-%d")
            tomorrow_str = tomorrow.strftime("%Y-%m-%d")
            
            for emp in self.employees:
                # work[..., 'N'] + work[..., '1'] <= 1
                # Se N è 1, allora 1 deve essere 0. Se 1 è 1, N deve essere 0. (O entrambi 0)
                self.model.Add(
                    self.work[emp.id, today_str, 'N'] + 
                    self.work[emp.id, tomorrow_str, '1'] <= 1
                )

        if self.days:
            first_day = self.days[0].isoformat()
            last_day = self.days[-1].isoformat()
            for emp in self.employees:
                previous = self._shift_history(self.previous_shifts.get(emp.id))
                following = self._shift_history(self.next_shifts.get(emp.id))
                if previous and previous[-1] == 'N' and '1' in self.shifts:
                    self.model.Add(self.work[emp.id, first_day, '1'] == 0)
                if following and following[0] == '1' and 'N' in self.shifts:
                    self.model.Add(self.work[emp.id, last_day, 'N'] == 0)

    def add_smonto_consistent_constraint(self):
        """
        Hard Constraint: Il turno Smonto (S) può essere assegnato SOLO se il giorno prima c'era Notte (N).
        Se ieri non era N, oggi non può essere S.
        Logica: work[today, 'S'] implies work[yesterday, 'N']
        Equivalente: work[today, 'S'] <= work[yesterday, 'N']
        Per il primo giorno del periodo non conosciamo il giorno precedente:
        S viene vietato per evitare smonto non preceduto da notte.
        """
        if not self.days:
            return

        # Giorno 0: usa il turno storico se disponibile, altrimenti vieta S.
        if 'S' in self.shifts:
            day0_str = self.days[0].strftime("%Y-%m-%d")
            for emp in self.employees:
                previous = self._shift_history(self.previous_shifts.get(emp.id))
                if not previous or previous[-1] != 'N':
                    self.model.Add(self.work[emp.id, day0_str, 'S'] == 0)

        # Itera dal secondo giorno in poi
        for i in range(1, len(self.days)):
            today = self.days[i]
            yesterday = self.days[i-1]
            today_str = today.strftime("%Y-%m-%d")
            yesterday_str = yesterday.strftime("%Y-%m-%d")
            
            for emp in self.employees:
                if 'S' in self.shifts and 'N' in self.shifts:
                    # Se S è 1, allora N(ieri) DEVE essere 1.
                    # Se N(ieri) è 0, allora S deve essere 0.
                    self.model.Add(
                        self.work[emp.id, today_str, 'S'] <= self.work[emp.id, yesterday_str, 'N']
                    )

    def add_max_consecutive_nights_constraint(self):
        """Vieta sequenze di notti oltre il limite, includendo il confine mensile noto."""
        if 'N' not in self.shifts or not self.days:
            return

        limit = self.config.max_consecutive_nights
        for emp in self.employees:
            before = self._shift_history(self.previous_shifts.get(emp.id))[-limit:]
            after = self._shift_history(self.next_shifts.get(emp.id))[:limit]
            tokens = [(False, code == 'N') for code in before]
            tokens.extend(
                (True, self.work[emp.id, day.isoformat(), 'N'])
                for day in self.days
            )
            tokens.extend((False, code == 'N') for code in after)

            window_size = limit + 1
            for start in range(max(0, len(tokens) - window_size + 1)):
                window = tokens[start:start + window_size]
                if not any(is_variable for is_variable, _ in window):
                    continue
                fixed_nights = sum(value for is_variable, value in window if not is_variable)
                night_vars = [value for is_variable, value in window if is_variable]
                self.model.Add(sum(night_vars) + fixed_nights <= limit)

    def add_night_limitation_constraint(self):
        """
        Hard Constraint: I dipendenti con limitazione_notte = True non possono fare turni 'N'.
        """
        for emp in self.employees:
            if emp.limitazione_notte:
                for d in self.days:
                    date_str = d.strftime("%Y-%m-%d")
                    # Force 'N' assignment to 0
                    if 'N' in self.shifts:
                        self.model.Add(self.work[emp.id, date_str, 'N'] == 0)

    def add_absence_request_requirement(self, requests: list):
        """Vieta le assenze automatiche quando non esiste una richiesta approvata."""
        from datetime import date

        absence_types = {
            'FERIE': 'F',
            'MALATTIA': 'M',
            '104': '104',
            'PERMESSO': 'P',
        }
        approved = {'APPROVED', 'APPROVATO'}
        emp_ids = {emp.id for emp in self.employees}
        allowed = {}

        for req in requests:
            status = str(req.get('stato', '')).strip().upper()
            if status not in approved:
                continue
            raw_type = str(req.get('tipo_richiesta', req.get('tipo', ''))).strip()
            code = absence_types.get(raw_type.upper())
            if code is None:
                continue
            emp_id = req.get('employee_id')
            if emp_id not in emp_ids:
                raise ValueError(f"La richiesta di assenza fa riferimento a un dipendente non attivo: {emp_id}.")
            try:
                start = date.fromisoformat(str(req['data_inizio']))
                end = date.fromisoformat(str(req['data_fine']))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Intervallo date non valido nella richiesta di assenza: {req!r}.") from exc
            if end < start:
                raise ValueError(f"Intervallo invertito nella richiesta di assenza: {req!r}.")
            for day in self.days:
                if start <= day <= end:
                    key = (emp_id, day.isoformat())
                    if key in allowed and allowed[key] != code:
                        raise ValueError(
                            f"Richieste di assenza incompatibili per {emp_id} il {day.isoformat()}."
                        )
                    allowed[key] = code

        for emp in self.employees:
            for day in self.days:
                day_key = day.isoformat()
                for code in absence_types.values():
                    if code in self.shifts and allowed.get((emp.id, day_key)) != code:
                        self.model.Add(self.work[emp.id, day_key, code] == 0)

    def add_cycle_transition_objective(self, objective_function, penalty_cost: int = None):
        """Premia la successione effettiva 1 -> K -> N -> S -> R -> 1."""
        cycle = ("1", "K", "N", "S", "R")
        successor = {cycle[index]: cycle[(index + 1) % len(cycle)] for index in range(len(cycle))}
        penalty_cost = (self.config.cycle_transition_penalty
                        if penalty_cost is None else penalty_cost)
        if penalty_cost <= 0 or not self.days:
            return

        def penalize_variable_pair(employee, previous_day, current_day):
            previous_vars = {code: self.work[employee.id, previous_day, code] for code in cycle}
            current_vars = {code: self.work[employee.id, current_day, code] for code in cycle}
            previous_regular = sum(previous_vars.values())
            current_regular = sum(current_vars.values())
            active = self.model.NewBoolVar(f"cycle_active_{employee.id}_{previous_day}_{current_day}")
            self.model.Add(active <= previous_regular)
            self.model.Add(active <= current_regular)
            self.model.Add(active >= previous_regular + current_regular - 1)

            expected_transitions = []
            for previous_code in cycle:
                expected_var = self.model.NewBoolVar(
                    f"cycle_match_{employee.id}_{previous_day}_{current_day}_{previous_code}"
                )
                previous_var = previous_vars[previous_code]
                current_var = current_vars[successor[previous_code]]
                self.model.Add(expected_var <= previous_var)
                self.model.Add(expected_var <= current_var)
                self.model.Add(expected_var >= previous_var + current_var - 1)
                expected_transitions.append(expected_var)

            bad = self.model.NewBoolVar(f"cycle_break_{employee.id}_{previous_day}_{current_day}")
            self.model.Add(bad == active - sum(expected_transitions))
            objective_function.add_penalty(bad, penalty_cost)

        for employee in self.employees:
            previous_history = self._shift_history(self.previous_shifts.get(employee.id))
            first_day = self.days[0].isoformat()
            if previous_history and previous_history[-1] in cycle:
                expected = successor[previous_history[-1]]
                for code in cycle:
                    if code != expected:
                        objective_function.add_penalty(
                            self.work[employee.id, first_day, code], penalty_cost
                        )

            for index in range(1, len(self.days)):
                previous_day = self.days[index - 1].isoformat()
                current_day = self.days[index].isoformat()
                penalize_variable_pair(employee, previous_day, current_day)

            next_history = self._shift_history(self.next_shifts.get(employee.id))
            if next_history and next_history[0] in cycle:
                last_day = self.days[-1].isoformat()
                next_code = next_history[0]
                for code in cycle:
                    if successor[code] != next_code:
                        objective_function.add_penalty(
                            self.work[employee.id, last_day, code], penalty_cost
                        )

    def add_tripletta_constraint(self, objective_function, penalty_cost: int = None):
        """Compatibilità per chiamanti legacy: usa ora la successione effettiva."""
        return self.add_cycle_transition_objective(objective_function, penalty_cost)

    def add_request_constraints(self, requests: list, objective_function=None, preference_penalty: int = 100):
        """
        Gestisce le richieste:
        - FERIE (F), MALATTIA (M), 104, LEGGE_104: Hard Constraint -> Assegna quel turno specifico.
        - DESIDERATA: Se specifica un turno, cerchiamo di assegnarlo (Hard o Soft? Facciamo Hard per ora se esplicito).
          Se la richiesta è generica "Desiderata" e nelle note c'è scritto "Mattina", servirebbe parsing.
          Per MVP, assumiamo che DESIDERATA spacifichi un turno nelle note o usiamo un mapping fisso se estendiamo il DB.
          
        Per semplicità MVP:
        - Tipo 'FERIE' -> Forza 'F'
        - Tipo 'MALATTIA' -> Forza 'M'
        - Tipo '104' -> Forza '104'
        - Altro: Ignora o implementa logica custom
        """
        from datetime import date
        
        # Mappa Tipo Richiesta -> Codice Turno
        # Assumiamo che se l'utente chiede "Mattina" vuole il turno '1'
        absence_types = {
            'FERIE': 'F',
            'MALATTIA': 'M',
            '104': '104',
            'PERMESSO': 'P',
        }
        preferences = {
            'MATTINA (PREF)': '1',
            'POMERIGGIO (PREF)': 'K',
            'NOTTE (PREF)': 'N',
        }
        
        # Set di emp_id validi nel solver per evitare KeyError su dipendenti non attivi
        valid_emp_ids = {emp.id for emp in self.employees}

        for req in requests:
            emp_id = req.get('employee_id')

            # Salta richieste di dipendenti non presenti nel solver (es. disattivati)
            if emp_id not in valid_emp_ids:
                continue

            if str(req.get('stato', '')).strip().upper() not in {'APPROVED', 'APPROVATO'}:
                continue

            # Find dates
            try:
                start = date.fromisoformat(str(req['data_inizio']))
                end = date.fromisoformat(str(req['data_fine']))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Intervallo date non valido nella richiesta: {req!r}.") from exc
            if end < start:
                raise ValueError(f"Intervallo invertito nella richiesta: {req!r}.")
            req_type = str(req.get('tipo_richiesta', req.get('tipo', ''))).strip().upper()
            shift_code = absence_types.get(req_type)
            preference_code = preferences.get(req_type)

            if shift_code is None and preference_code is None:
                raise ValueError(f"Tipo di richiesta non riconosciuto: {req_type!r}.")

            if shift_code is not None and shift_code not in self.shifts:
                raise ValueError(f"Il turno richiesto {shift_code!r} non è configurato.")
            if preference_code is not None and preference_code not in self.shifts:
                raise ValueError(f"La preferenza {req_type!r} non è configurata.")

            # Iterate days in solver range
            for d in self.days:
                if start <= d <= end:
                    date_str = d.strftime("%Y-%m-%d")
                    # 1. Gestione Assenze Codificate (Hard Constraint)
                    if shift_code is not None:
                        self.model.Add(self.work[emp_id, date_str, shift_code] == 1)
                    elif preference_code is not None:
                        if objective_function is None:
                            raise ValueError("Le preferenze richiedono un obiettivo per assegnare la penalità.")
                        objective_function.add_penalty(
                            self.work[emp_id, date_str, preference_code].Not(), preference_penalty
                        )


