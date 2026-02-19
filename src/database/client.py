import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """
    Restituisce l'istanza singleton del client Supabase.
    Usa st.cache_resource per evitare di ricreare la connessione a ogni rerun.
    """
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)
