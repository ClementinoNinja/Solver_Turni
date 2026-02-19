-- Policy per Employees
-- Consenti lettura a tutti gli utenti autenticati (necessario per vedere i colleghi)
CREATE POLICY "Enable read access for all authenticated users"
ON employees FOR SELECT
TO authenticated
USING (true);

-- Consenti creazione/modifica solo all'Admin
-- (Adattare la policy sulla mail se necessario, o usare service_role che bypassa tutto)
CREATE POLICY "Enable write access for admin only"
ON employees FOR ALL
TO authenticated
USING (auth.jwt() ->> 'email' = 'email.del.caposala@ospedale.it')
WITH CHECK (auth.jwt() ->> 'email' = 'email.del.caposala@ospedale.it');

-- Policy per Requests
CREATE POLICY "Enable read access for all authenticated users"
ON requests FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Enable insert for authenticated users"
ON requests FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = employee_id); -- O simile, ma per ora semplifichiamo

-- Grant permissions to authenticated role just in case
GRANT ALL ON TABLE employees TO authenticated;
GRANT ALL ON TABLE roster TO authenticated;
GRANT ALL ON TABLE requests TO authenticated;
