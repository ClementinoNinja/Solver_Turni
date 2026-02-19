import streamlit as st
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.styles import apply_custom_styles
from src.ui.view_admin import render_admin_view
from src.ui.view_roster import render_roster_view
from src.ui.view_employees import render_employees_view
from src.ui.view_requests import render_requests_view

st.set_page_config(page_title="OSS Manager", layout="wide")
apply_custom_styles()

st.sidebar.title("OSS Manager")
page = st.sidebar.radio("Navigazione", ["Visualizza Turni", "Generazione (Admin)", "Gestione Dipendenti", "Gestione Richieste"])

if page == "Generazione (Admin)":
    # Simple auth check
    password = st.sidebar.text_input("Password Admin", type="password")
    if password == st.secrets["admin"]["password"]:
        render_admin_view()
    else:
        st.warning("Inserisci password admin per accedere.")

elif page == "Gestione Dipendenti":
    password = st.sidebar.text_input("Password Admin", type="password", key="emp_pwd")
    if password == st.secrets["admin"]["password"]:
        render_employees_view()
    else:
        st.warning("Inserisci password admin per accedere.")

elif page == "Gestione Richieste":
    password = st.sidebar.text_input("Password Admin", type="password", key="req_pwd")
    if password == st.secrets["admin"]["password"]:
        render_requests_view()
    else:
        st.warning("Inserisci password admin per accedere.")

elif page == "Visualizza Turni":
    # Check if admin is logged in (session state hack) or ask password optionally for 'Edit Mode'
    # Per ora: Grid View è Read Only per tutti, Edit Mode solo se admin password presente in sidebar? 
    # Semplifichiamo: Se c'è password admin inserita -> Admin Mode
    # Ma password input è nell'altra pagina. Mettiamolo nella sidebar comune o gestiamo sessione.
    
    is_admin = False
    with st.sidebar:
        st.divider()
        admin_pwd = st.text_input("Admin Access (Opzionale)", type="password", key="main_admin_pwd")
        if admin_pwd == st.secrets["admin"]["password"]:
             is_admin = True
             st.success("Admin Mode Attivo")
    
    render_roster_view(is_admin=is_admin)
