from typing import List, Optional
from src.database.client import get_supabase_client
from src.models.employee import Employee

class EmployeeRepository:
    def __init__(self):
        self.table_name = "employees"

    def get_all_employees(self) -> List[Employee]:
        client = get_supabase_client()
        response = client.table(self.table_name).select("*").eq("attivo", True).execute()
        
        employees = []
        for row in response.data:
            employees.append(Employee(
                id=row['id'],
                matricola=row['matricola'],
                nome_cognome=row['nome_cognome'],
                ruolo=row['ruolo'],
                team_id=row['team_id'],
                limitazione_notte=row['limitazione_notte']
            ))
        return employees

    def create_employee(self, employee: Employee) -> Employee:
        """
        Crea un nuovo dipendente su Supabase.
        """
        client = get_supabase_client()
        data = {
            "matricola": employee.matricola,
            "nome_cognome": employee.nome_cognome,
            "ruolo": employee.ruolo,
            "team_id": employee.team_id,
            "limitazione_notte": employee.limitazione_notte,
            "attivo": employee.attivo
        }
        # Se l'ID è presente, lo usiamo (utile per test o restore), altrimenti lascia fare a Supabase
        if employee.id:
            data['id'] = employee.id

        response = client.table(self.table_name).insert(data).execute()
        if response.data:
            row = response.data[0]
            employee.id = row['id']
            return employee
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
        client = get_supabase_client()
        client.table(self.table_name).update(data).eq("id", employee_id).execute()

    def delete_employee(self, employee_id: str):
        """
        Elimina fisicamente un dipendente dal database.
        (Alternativa: soft-delete impostando attivo=False, ma qui lo eliminiamo per pulizia in pre-prod)
        """
        client = get_supabase_client()
        client.table(self.table_name).delete().eq("id", employee_id).execute()

    def get_employee_by_id(self, emp_id: str) -> Optional[Employee]:
        client = get_supabase_client()
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
            limitazione_notte=row['limitazione_notte']
        )

    def get_roster_by_month(self, start_date: str, end_date: str) -> List[dict]:
        """
        Recupera i turni in un range di date.
        ritorna una lista di dizionari (o RosterEntry oggetto se creato)
        """
        client = get_supabase_client()
        response = client.table("roster").select("*").gte("data", start_date).lte("data", end_date).execute()
        return response.data

    def save_roster_entry(self, employee_id: str, date: str, shift_code: str, is_locked: bool = False):
        """
        Salva o aggiorna un turno.
        Upsert basato su (employee_id, date).
        """
        client = get_supabase_client()
        data = {
            "employee_id": employee_id,
            "data": date, # Assicurarsi che key corrisponda a colonna DB (data)
            "shift_code": shift_code,
            "is_locked": is_locked
        }
        client.table("roster").upsert(data, on_conflict="employee_id, data").execute()

    def delete_roster_entry(self, employee_id: str, date: str):
        """
        Elimina il turno di un dipendente in una specifica data.
        """
        client = get_supabase_client()
        client.table("roster").delete().eq("employee_id", employee_id).eq("data", date).execute()

    def get_requests(self, start_date: str, end_date: str) -> List[dict]:
        """
        Recupera le assenze/richieste nel periodo.
        """
        client = get_supabase_client()
        response = client.table("requests").select("*").gte("data_inizio", start_date).lte("data_inizio", end_date).execute()
        return response.data

    def delete_request(self, request_id: int):
        """
        Elimina fisicamente una richiesta o preferenza dal database.
        """
        client = get_supabase_client()
        client.table("requests").delete().eq("id", request_id).execute()

    def create_request(self, employee_id: str, request_type: str, start_date: str, end_date: str, note: str = ""):
        """
        Crea una nuova richiesta.
        """
        client = get_supabase_client()
        data = {
            "employee_id": employee_id,
            "tipo_richiesta": request_type,
            "data_inizio": start_date,
            "data_fine": end_date,
            "note": note,
            "stato": "APPROVED" # Auto-approve for MVP
        }
        client.table("requests").insert(data).execute()
