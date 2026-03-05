from ortools.sat.python import cp_model
from datetime import date as _date

# Data di ancoraggio del ciclo tripletta: il giorno 0 corrisponde al turno '1' per il team 1.
# CALIBRARE con il responsabile turni se il ciclo non è allineato.
CYCLE_ANCHOR_DATE = _date(2026, 1, 5)

class ConstraintsManager:
    def __init__(self, model: cp_model.CpModel, shifts: dict, employees: list, days: list, work: dict):
        self.model = model
        self.shifts = shifts
        self.employees = employees
        self.days = days
        self.work = work # The 3D decision variable matrix work[emp_id, day, shift_code]

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
            for shift_code in ['1', 'K']:
                if shift_code in self.shifts:
                    # Sum of INF and OSS for this shift
                    inf_sum = sum(self.work[e.id, date_str, shift_code] for e in inf_employees)
                    oss_sum = sum(self.work[e.id, date_str, shift_code] for e in oss_employees)
                    
                    # Logic: (inf >= 2 AND oss >= 2) OR (inf >= 3 AND oss >= 1)
                    # We can use a boolean variable for each condition or intermediate bools.
                    
                    # Cond 1: 2+2
                    c1 = self.model.NewBoolVar(f'{date_str}_{shift_code}_2inf_2oss')
                    self.model.Add(inf_sum >= 2).OnlyEnforceIf(c1)
                    self.model.Add(oss_sum >= 2).OnlyEnforceIf(c1)
                    
                    # Cond 2: 3+1
                    c2 = self.model.NewBoolVar(f'{date_str}_{shift_code}_3inf_1oss')
                    self.model.Add(inf_sum >= 3).OnlyEnforceIf(c2)
                    self.model.Add(oss_sum >= 1).OnlyEnforceIf(c2)
                    
                    # At least one condition must be true
                    self.model.AddBoolOr([c1, c2])
            
            # --- Notte (N) ---
            if 'N' in self.shifts:
                # Rule: Min 2 INF + Min 1 OSS
                inf_sum_n = sum(self.work[e.id, date_str, 'N'] for e in inf_employees)
                oss_sum_n = sum(self.work[e.id, date_str, 'N'] for e in oss_employees)
                
                
                self.model.Add(inf_sum_n >= 2)
                self.model.Add(oss_sum_n >= 1)

    def add_max_shift_capacity(self, max_capacity: int = 5):
        """
        Hard Constraint: Non ci possono essere più di `max_capacity` persone assegnate
        allo stesso turno (Mattina, Pomeriggio, Notte).
        """
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

        # Giorno 0: impossibile verificare il giorno precedente -> vieta S
        if 'S' in self.shifts:
            day0_str = self.days[0].strftime("%Y-%m-%d")
            for emp in self.employees:
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

    def add_tripletta_constraint(self, objective_function, penalty_cost: int = 100):
        """
        Soft Constraint: Se il turno assegnato non rispetta la sequenza ideale, paga penalità.
        Sequenza ideale: 1 -> K -> N -> S -> R (Ciclo 5 giorni)
        Logic: Ideal shift dipende da (giorno_anno + offset_team) % 5
        Mapping: 0=1, 1=K, 2=N, 3=S, 4=R
        """
        # Mapping index to shift code
        cycle_map = {0: '1', 1: 'K', 2: 'N', 3: 'S', 4: 'R'}
        
        for emp in self.employees:
            if emp.team_id is None:
                continue # Skip employees without team/tripletta
            
            # Offset basato su team_id: team 1 -> offset 0, team 2 -> offset 1, etc.
            offset = (emp.team_id - 1) % 5

            for d in self.days:
                date_str = d.strftime("%Y-%m-%d")
                # Calcolo indice ciclo relativo a CYCLE_ANCHOR_DATE (non all'ordinale assoluto).
                # Il giorno 0 = CYCLE_ANCHOR_DATE corrisponde al turno '1' per il team 1.
                day_index = ((d - CYCLE_ANCHOR_DATE).days + offset) % 5
                ideal_shift = cycle_map.get(day_index)
                
                if ideal_shift and ideal_shift in self.shifts:
                    # Se il dipendente NON fa il turno ideale, paga penalità.
                    # BoolVar: is_not_ideal
                    # is_not_ideal = 1 - work[emp, date, ideal]
                    # Ma work è 1 se lavora quel turno.
                    # Quindi penalty applicata se work[..., ideal] è 0.
                    # Oppure, penalty applicata per ogni turno diverso assegnato? 
                    # Meglio: Reward se segue, Costo se non segue.
                    # Qui usiamo Penalità: Costo se work[ideal] == 0  => (1 - work[ideal]) * cost
                    
                    is_ideal_assigned = self.work[emp.id, date_str, ideal_shift]
                    objective_function.add_penalty(is_ideal_assigned.Not(), penalty_cost)

    def add_request_constraints(self, requests: list):
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
        type_to_shift = {
            'FERIE': 'F',
            'MALATTIA': 'M',
            '104': '104',
            'PERMESSO': 'P',
            # Preferenze Turno
            'Mattina (Pref)': '1',
            'Pomeriggio (Pref)': 'K',
            'Notte (Pref)': 'N'
        }
        
        # Set di emp_id validi nel solver per evitare KeyError su dipendenti non attivi
        valid_emp_ids = {emp.id for emp in self.employees}

        for req in requests:
            emp_id = req['employee_id']

            # Salta richieste di dipendenti non presenti nel solver (es. disattivati)
            if emp_id not in valid_emp_ids:
                continue

            # Find dates
            start = date.fromisoformat(req['data_inizio'])
            end = date.fromisoformat(req['data_fine'])

            # Iterate days in solver range
            for d in self.days:
                if start <= d <= end:
                    date_str = d.strftime("%Y-%m-%d")
                    req_type = req['tipo_richiesta']

                    # 1. Gestione Assenze Codificate (Hard Constraint)
                    if req_type in type_to_shift:
                        forced_shift = type_to_shift[req_type]
                        if forced_shift in self.shifts:
                             self.model.Add(self.work[emp_id, date_str, forced_shift] == 1)
                    
                    # 2. Gestione Desiderata (Es. Note="M") - Placeholder
                    # Se implementiamo desiderata specifici, qui andrebbe la logica.


