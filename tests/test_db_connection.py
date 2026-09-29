import os

import pytest
from supabase import create_client


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SUPABASE_INTEGRATION") != "1",
    reason="Test d'integrazione: richiede RUN_SUPABASE_INTEGRATION=1 e credenziali dedicate di test.",
)


def test_supabase_connection():
    url = os.environ.get("SUPABASE_TEST_URL")
    key = os.environ.get("SUPABASE_TEST_KEY")
    if not url or not key:
        pytest.fail("Impostare SUPABASE_TEST_URL e SUPABASE_TEST_KEY per il database di test.")

    response = create_client(url, key).table("employees").select("id").limit(1).execute()
    assert response is not None
