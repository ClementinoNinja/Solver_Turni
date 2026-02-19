import pytest
from unittest.mock import MagicMock, patch
from src.database.client import get_supabase_client
import streamlit as st

def test_supabase_connection():
    """
    Test di integrazione per verificare la connessione a Supabase.
    Richiede che secrets.toml sia configurato correttamente.
    """
    # Mocking st.secrets only if not available (to avoid failure in CI/CD without secrets)
    # But for local dev it should fail if secrets are missing.
    try:
        client = get_supabase_client()
        # Eseguiamo una query leggera per vedere se risponde
        response = client.table("employees").select("count", count="exact").execute()
        assert response is not None
        print("Connection Successful!")
    except KeyError:
        pytest.fail("Secrets not found! Please configure .streamlit/secrets.toml")
    except Exception as e:
        pytest.fail(f"Connection failed: {str(e)}")
