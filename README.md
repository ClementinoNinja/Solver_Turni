# OpenShift Scheduler (OSS-Manager)

## Vision
Liberare i coordinatori infermieristici dall'incubo dei fogli Excel e dei calcoli manuali, garantendo turni equi, legali e trasparenti con un solo click.

## Setup
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
3. Install dependencies: `pip install -r requirements.txt`
4. Run the app: `streamlit run src/main.py`

## Database and access

1. Apply `database/schema.sql` to a new Supabase project, or back up and inspect an existing schema first.
2. Review and apply `database/migrations/20260928_scheduler_safety.sql` in a non-production project before using the new application version.
3. Set `supabase.url` and the Supabase anon key in `.streamlit/secrets.toml`; set the server-only `supabase.service_role_key` separately and never expose it to the browser or commit it.
4. Set `admin.password` in Streamlit secrets; the current admin login remains a shared password, so audit events cannot identify an individual operator.

The public calendar reads from the `roster_calendar` view, which returns `ASS` for every absence code; detailed codes and requests require the server-side admin client. Employee contract percentages and solver settings require the migration above. The migration is not applied automatically.

The solver treats the sequence `1 -> K -> N -> S -> R` as a preference, balances night duties by role, contract percentage and availability, and enforces a hard maximum of two consecutive nights, including known shifts across month boundaries.

## Tests

Run local tests with `pytest`. They use synthetic data and mocks; Supabase integration tests are skipped unless explicitly enabled with `RUN_SUPABASE_INTEGRATION=1`, `SUPABASE_TEST_URL`, and `SUPABASE_TEST_KEY` pointing to a dedicated test project.
