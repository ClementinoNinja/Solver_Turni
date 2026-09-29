from typing import List, Optional
from src.database.client import get_supabase_admin_client, get_supabase_client
from src.models.employee import Employee
from src.engine.config import DEFAULT_SOLVER_CONFIG, SolverConfig


class EmployeeRepository:
    def __init__(self, admin: bool = False):
        self.table_name = "employees"
        self.admin = admin

    def _client(self):
        return get_supabase_admin_client() if self.admin else get_supabase_client()

    def get_solver_config(self) -> SolverConfig:
        response = (
            self._client().table("scheduler_settings").select("config")
            .eq("name", "default").execute()
        )
        if not response.data:
            return DEFAULT_SOLVER_CONFIG
        return SolverConfig.from_dict(response.data[0]["config"])

    def save_solver_config(self, config: SolverConfig):
        self._client().table("scheduler_settings").upsert({
            "name": "default", "config": config.to_dict(),
        }, on_conflict="name").execute()

    def get_all_employees(self, include_inactive: bool = False) -> List[Employee]:
        client = self._client()
        query = client.table(self.table_name).select("*")
        if not include_inactive:
            query = query.eq("attivo", True)
        response = query.execute()

        employees = []
        for row in response.data:
            employees.append(Employee(
                id=row['id'],
                matricola=row['matricola'],
                nome_cognome=row['nome_cognome'],
                ruolo=row['ruolo'],
                team_id=row['team_id'],
                limitazione_notte=row['limitazione_notte'],
                attivo=row.get('attivo', True),
                contract_percentage=float(row.get('contract_percentage', 100.0)),
            ))
        return employees

    def create_employee(self, employee: Employee) -> Employee:
        """
        Crea un nuovo dipendente su Supabase.
        """
        client = self._client()
        data = {
            "matricola": employee.matricola,
            "nome_cognome": employee.nome_cognome,
            "ruolo": employee.ruolo,
            "team_id": employee.team_id,
            "limitazione_notte": employee.limitazione_notte,
            "attivo": employee.attivo,
            "contract_percentage": employee.contract_percentage,
        }
        if employee.id:
            data['id'] = employee.id

        response = client.table(self.table_name).insert(data).execute()
        if response.data:
            row = response.data[0]
            employee.id = row['id']
            return employee
        raise Exception("Failed to create employee")

    def update_employee(self, employee_id: str, data: dict):
        """
        Aggiorna i campi di un dipendente.
        data: es. {"nome_cognome": "Mario Rossi", "ruolo": "OSS"}
        """
        client = self._client()
        client.table(self.table_name).update(data).eq("id", employee_id).execute()

    def delete_employee(self, employee_id: str):
        """
        Disattiva il dipendente conservando lo storico collegato.
        """
        client = self._client()
        client.table(self.table_name).update({"attivo": False}).eq("id", employee_id).execute()

    def get_employee_by_id(self, emp_id: str) -> Optional[Employee]:
        client = self._client()
        response = client.table(self.table_name).select("*").eq("id", emp_id).execute()
        if not response.data:
            return None

        row = response.data[0]
        return Employee(
            id=row['id'],
            matricola=row['matricola'],
            nome_cognome=row['nome_cognome'],
            ruolo=row['ruolo'],
            team_id=row['team_id'],
            limitazione_notte=row['limitazione_notte'],
            attivo=row.get('attivo', True),
            contract_percentage=float(row.get('contract_percentage', 100.0)),
        )

    def get_roster_by_month(self, start_date: str, end_date: str) -> List[dict]:
        """
        Recupera i turni in un range di date.
        """
        client = self._client()
        response = client.table("roster").select("*").gte("data", start_date).lte("data", end_date).execute()
        return response.data

    def get_public_roster_by_month(self, start_date: str, end_date: str) -> List[dict]:
        """Legge il calendario dalla vista che maschera i codici di assenza."""
        response = (
            self._client().table("roster_calendar").select("*")
            .gte("data", start_date).lte("data", end_date).execute()
        )
        return response.data

    def save_roster_entry(self, employee_id: str, date: str, shift_code: str, is_locked: Optional[bool] = None):
        """
        Salva o aggiorna un turno.
        Upsert basato su (employee_id, date).
        """
        client = self._client()
        data = {
            "employee_id": employee_id,
            "data": date,
            "shift_code": shift_code,
        }
        # Omettere il campo durante la rigenerazione conserva il flag esistente;
        # per nuove righe Supabase applica il default FALSE.
        if is_locked is not None:
            data["is_locked"] = is_locked
        client.table("roster").upsert(data, on_conflict="employee_id, data").execute()

    def publish_roster_month(self, start_date: str, end_date: str, employee_ids: List[str],
                             expected_roster: List[dict], entries: List[dict]):
        """Pubblica l'intero mese con un'unica transazione e verifica della revisione."""
        def normalized(rows, include_lock):
            result = []
            for row in rows:
                item = {
                    "employee_id": str(row["employee_id"]),
                    "data": str(row["data"])[:10],
                    "shift_code": row["shift_code"],
                }
                if include_lock:
                    item["is_locked"] = bool(row.get("is_locked", False))
                result.append(item)
            return sorted(result, key=lambda row: (row["employee_id"], row["data"]))

        response = self._client().rpc("publish_roster_month", {
            "p_start": start_date,
            "p_end": end_date,
            "p_employee_ids": employee_ids,
            "p_expected_roster": normalized(expected_roster, include_lock=True),
            "p_entries": normalized(entries, include_lock=True),
        }).execute()
        return response.data

    def get_requests(self, start_date: str, end_date: str) -> List[dict]:
        """
        Recupera le assenze/richieste che si sovrappongono al periodo dato.
        Condizione di overlap: data_inizio <= end_date AND data_fine >= start_date
        """
        client = self._client()
        response = (
            client.table("requests")
            .select("*")
            .lte("data_inizio", end_date)
            .gte("data_fine", start_date)
            .execute()
        )
        return response.data

    def delete_request(self, request_id: int):
        """
        Elimina fisicamente una richiesta o preferenza dal database.
        """
        client = self._client()
        client.table("requests").delete().eq("id", request_id).execute()

    def create_request(self, employee_id: str, request_type: str, start_date: str, end_date: str, note: str = ""):
        """
        Crea una nuova richiesta.
        """
        client = self._client()
        data = {
            "employee_id": employee_id,
            "tipo_richiesta": request_type,
            "data_inizio": start_date,
            "data_fine": end_date,
            "note": note,
            "stato": "APPROVED"
        }
        client.table("requests").insert(data).execute()
