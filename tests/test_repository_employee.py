from unittest.mock import MagicMock, patch

from src.database.repository import EmployeeRepository
from src.models.employee import Employee


def test_get_all_employees_maps_database_rows_to_models():
    row = {
        "id": "employee-1",
        "matricola": "MAT-1",
        "nome_cognome": "Mario Rossi",
        "ruolo": "INF",
        "team_id": 2,
        "limitazione_notte": False,
        "attivo": True,
    }
    response = MagicMock(data=[row])
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value = response

    with patch("src.database.repository.get_supabase_client", return_value=client):
        employees = EmployeeRepository().get_all_employees()

    assert employees == [Employee(**row)]
    client.table.assert_called_once_with("employees")
