import pytest
from src.database.repository import EmployeeRepository
from datetime import date

def test_roster_operations():
    repo = EmployeeRepository()
    
    # 1. Create a dummy employee for testing (if not exists)
    employees = repo.get_all_employees()
    if not employees:
        from src.models.employee import Employee
        new_emp = Employee(
            matricola="TEST001",
            nome_cognome="Test User",
            ruolo="INF",
            team_id=1
        )
        created_emp = repo.create_employee(new_emp)
        test_emp_id = created_emp.id
    else:
        test_emp_id = employees[0].id
    test_date = "2024-01-01"
    
    # 2. Save a roster entry
    repo.save_roster_entry(test_emp_id, test_date, "M", is_locked=False)
    
    # 3. Read it back
    roster = repo.get_roster_by_month("2024-01-01", "2024-01-31")
    
    found = False
    for entry in roster:
        if entry['employee_id'] == test_emp_id and entry['data'] == test_date:
            assert entry['shift_code'] == "M"
            found = True
            break
    
    assert found
