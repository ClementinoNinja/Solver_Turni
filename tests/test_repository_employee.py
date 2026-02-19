import pytest
import streamlit as st
from src.database.repository import EmployeeRepository
from src.models.employee import Employee
from src.database.client import get_supabase_client

# Integration test - Requires working DB connection
def test_get_all_employees_integration():
    try:
        repo = EmployeeRepository()
        
        # Create a dummy employee for testing (cleanup later or rely on test db)
        # For now, we just check if the query runs without error and returns list
        employees = repo.get_all_employees()
        assert isinstance(employees, list)
    except Exception as e:
        pytest.fail(f"Integration test failed: {e}")
