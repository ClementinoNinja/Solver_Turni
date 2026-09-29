import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def _cached_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)


@st.cache_resource
def _cached_supabase_admin_client(url: str, key: str) -> Client:
    return create_client(url, key)


def get_supabase_client() -> Client:
    """
    Restituisce l'istanza singleton del client Supabase.
    Usa st.cache_resource per evitare di ricreare la connessione a ogni rerun.
    """
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]

    if not url or not key:
        raise ValueError("Supabase URL o Key non configurati in secrets.toml")

    return _cached_supabase_client(url, key)


def get_supabase_admin_client() -> Client:
    """Restituisce il client privilegiato solo dopo la verifica della sessione admin."""
    if not st.session_state.get("_admin_auth", False):
        raise PermissionError("Accesso amministratore richiesto.")
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"].get("service_role_key")
    if not url or not key:
        raise ValueError(
            "Configura supabase.service_role_key nei secrets lato server; "
            "supabase.key deve rimanere la chiave anon.")
    return _cached_supabase_admin_client(url, key)
