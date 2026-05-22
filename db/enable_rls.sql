-- =====================================================================
-- Abilitazione Row Level Security (RLS) su tutte le tabelle public
-- =====================================================================
-- L'applicazione si connette a Supabase con la chiave `service_role`,
-- che BYPASSA RLS: enabling RLS qui non rompe né l'app né i test.
-- Effetto: chiunque abbia solo la `anon` key non potra' piu' leggere
-- o scrivere queste tabelle via PostgREST.
--
-- Eseguire una sola volta nel SQL Editor di Supabase.
-- Idempotente: si puo' rieseguire senza errori.
-- =====================================================================

-- --- Abilita RLS ------------------------------------------------------
ALTER TABLE public.shift_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.employees   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roster      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.requests    ENABLE ROW LEVEL SECURITY;

-- --- Forza RLS anche per i ruoli table-owner (best practice) ----------
-- Nota: service_role resta esente per definizione.
ALTER TABLE public.shift_types FORCE ROW LEVEL SECURITY;
ALTER TABLE public.employees   FORCE ROW LEVEL SECURITY;
ALTER TABLE public.roster      FORCE ROW LEVEL SECURITY;
ALTER TABLE public.requests    FORCE ROW LEVEL SECURITY;

-- --- Nessuna policy = nessun accesso per anon/authenticated -----------
-- Volutamente non creiamo policy: l'unico client autorizzato e' il
-- backend Streamlit, che usa la service_role key.
-- In futuro, se si introduce Supabase Auth lato utente, aggiungere
-- qui le CREATE POLICY necessarie.

-- --- Verifica ---------------------------------------------------------
-- SELECT tablename, rowsecurity, forcerowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public';
