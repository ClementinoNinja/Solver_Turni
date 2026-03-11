import streamlit as st
from typing import List
from src.models.employee import Employee
from src.database.repository import EmployeeRepository

class AppState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppState, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if 'employees' not in st.session_state:
            st.session_state.employees = []
        if 'roster_cache' not in st.session_state:
            st.session_state.roster_cache = None

    def load_employees(self):
        """Carica i dipendenti dal DB solo se la lista è vuota."""
        if not st.session_state.employees:
            repo = EmployeeRepository()
            try:
                st.session_state.employees = repo.get_all_employees()
            except Exception as e:
                st.error(f"Errore caricamento dipendenti: {e}")

    def load_employees_safe(self) -> bool:
        """
        Carica i dipendenti con gestione errore.
        Restituisce True se il caricamento è riuscito, False altrimenti.
        """
        if not st.session_state.employees:
            repo = EmployeeRepository()
            try:
                st.session_state.employees = repo.get_all_employees()
            except Exception as e:
                st.error(f"Errore di connessione al database: {e}")
                st.info("Verifica che il progetto Supabase sia attivo e che le credenziali siano corrette.")
                return False
        return True

    @property
    def employees(self) -> List[Employee]:
        return st.session_state.employees

    @employees.setter
    def employees(self, value: List[Employee]):
        st.session_state.employees = value
