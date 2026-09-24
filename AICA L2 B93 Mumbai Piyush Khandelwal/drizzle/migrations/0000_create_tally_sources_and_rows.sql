-- Profiles for signed-in users
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY,
  email TEXT,
  full_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE ON public.profiles TO authenticated;
GRANT ALL ON public.profiles TO service_role;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own profile read" ON public.profiles FOR SELECT TO authenticated USING (auth.uid() = id);
CREATE POLICY "own profile write" ON public.profiles FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);
CREATE POLICY "own profile update" ON public.profiles FOR UPDATE TO authenticated USING (auth.uid() = id);

-- A connected accounting source (Tally to start with)
CREATE TABLE public.accounting_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  provider TEXT NOT NULL DEFAULT 'tally',
  name TEXT NOT NULL,
  company TEXT,
  token_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'pending',
  error TEXT,
  frequency TEXT NOT NULL DEFAULT 'manual',
  last_sync TIMESTAMPTZ,
  record_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX accounting_sources_user_idx ON public.accounting_sources(user_id);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.accounting_sources TO authenticated;
GRANT ALL ON public.accounting_sources TO service_role;
ALTER TABLE public.accounting_sources ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own sources select" ON public.accounting_sources FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "own sources insert" ON public.accounting_sources FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "own sources update" ON public.accounting_sources FOR UPDATE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "own sources delete" ON public.accounting_sources FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- Normalised records pushed in from the source
CREATE TABLE public.accounting_records (
  id BIGSERIAL PRIMARY KEY,
  source_id UUID NOT NULL REFERENCES public.accounting_sources(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  dataset TEXT NOT NULL,
  record_date DATE,
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX accounting_records_source_idx ON public.accounting_records(source_id, dataset);
CREATE INDEX accounting_records_user_idx ON public.accounting_records(user_id);
GRANT SELECT ON public.accounting_records TO authenticated;
GRANT ALL ON public.accounting_records TO service_role;
ALTER TABLE public.accounting_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own records select" ON public.accounting_records FOR SELECT TO authenticated USING (auth.uid() = user_id);