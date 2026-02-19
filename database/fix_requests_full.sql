-- 1. Rinomina la colonna 'tipo' in 'tipo_richiesta' per coerenza con il codice
DO $$
BEGIN
  IF EXISTS(SELECT *
    FROM information_schema.columns
    WHERE table_name='requests' and column_name='tipo')
  THEN
      ALTER TABLE "requests" RENAME COLUMN "tipo" TO "tipo_richiesta";
  END IF;
END $$;

-- 2. Aggiungi la colonna 'note' se manca
ALTER TABLE "requests" ADD COLUMN IF NOT EXISTS "note" TEXT;

-- 3. Rimuovi il vincolo CHECK vecchio (che permetteva solo Ferie/Malattia Title Case)
--    Il codice usa UPPERCASE (FERIE, MALATTIA) e nuovi tipi (DESIDERATA)
ALTER TABLE "requests" DROP CONSTRAINT IF EXISTS "requests_tipo_check";
