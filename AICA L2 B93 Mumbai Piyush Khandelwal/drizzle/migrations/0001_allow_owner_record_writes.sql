GRANT INSERT, UPDATE, DELETE ON public.accounting_records TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.accounting_records_id_seq TO authenticated;
CREATE POLICY "own records insert" ON public.accounting_records FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "own records update" ON public.accounting_records FOR UPDATE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "own records delete" ON public.accounting_records FOR DELETE TO authenticated USING (auth.uid() = user_id);