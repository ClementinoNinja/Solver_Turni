from unittest.mock import MagicMock, patch

from src.database.repository import EmployeeRepository


def test_save_roster_entry_upserts_locked_entry():
    client = MagicMock()
    response = MagicMock(data=[])
    client.table.return_value.upsert.return_value.execute.return_value = response

    with patch("src.database.repository.get_supabase_client", return_value=client):
        EmployeeRepository().save_roster_entry("employee-1", "2024-01-01", "M", is_locked=True)

    client.table.assert_called_once_with("roster")
    client.table.return_value.upsert.assert_called_once_with(
        {
            "employee_id": "employee-1",
            "data": "2024-01-01",
            "shift_code": "M",
            "is_locked": True,
        },
        on_conflict="employee_id, data",
    )
