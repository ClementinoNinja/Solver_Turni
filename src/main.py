import streamlit as st
import sys
import os
import hmac

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.styles import apply_custom_styles
from src.ui.view_admin import render_admin_view
from src.ui.view_roster import render_roster_view
from src.ui.view_employees import render_employees_view
from src.ui.view_requests import render_requests_view


def _check_admin_password(password: str) -> bool:
    """Confronto timing-safe della password admin."""
    if not password:
        return False
    try:
        correct = st.secrets["admin"]["password"]
    except (KeyError, FileNotFoundError):
        st.sidebar.error("Secrets non configurati. Verifica .streamlit/secrets.toml")
        return False
    return hmac.compare_digest(password.encode(), correct.encode())


def _render_admin_login(key: str) -> bool:
    """
    Mostra il campo password nella sidebar e gestisce la sessione admin.
    Restituisce True se l'utente è autenticato come admin.
    """
    session_key = f"_admin_auth_{key}"

    if st.session_state.get(session_key):
        st.sidebar.success("Admin Mode Attivo")
        if st.sidebar.button("Logout", key=f"logout_{key}"):
            st.session_state[session_key] = False
            st.rerun()
        return True

    pwd = st.sidebar.text_input("Password Admin", type="password", key=f"pwd_{key}")
    if pwd:
        if _check_admin_password(pwd):
            st.session_state[session_key] = True
            st.rerun()
        else:
            st.sidebar.error("Password errata.")
    return False


st.set_page_config(page_title="OSS Manager", layout="wide")
apply_custom_styles()

st.sidebar.title("OSS Manager")
page = st.sidebar.radio("Navigazione", ["Visualizza Turni", "Generazione (Admin)", "Gestione Dipendenti", "Gestione Richieste"])

if page == "Generazione (Admin)":
    if _render_admin_login("gen"):
        render_admin_view()
    else:
        st.warning("Inserisci password admin per accedere.")

elif page == "Gestione Dipendenti":
    if _render_admin_login("emp"):
        render_employees_view()
    else:
        st.warning("Inserisci password admin per accedere.")

elif page == "Gestione Richieste":
    if _render_admin_login("req"):
        render_requests_view()
    else:
        st.warning("Inserisci password admin per accedere.")

elif page == "Visualizza Turni":
    with st.sidebar:
        st.divider()
        is_admin = _render_admin_login("roster")
    render_roster_view(is_admin=is_admin)
