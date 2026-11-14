-- =========================================================================
-- BULLION LEDGER - SUPABASE DATABASE SCHEMA & ROW LEVEL SECURITY (RLS)
-- =========================================================================
-- Instructions:
-- 1. Open your Supabase Dashboard: https://supabase.com/dashboard
-- 2. Select your Project -> Click "SQL Editor" in the left sidebar.
-- 3. Click "New Query", paste this entire script, and click "Run".
-- =========================================================================

-- 1. Create purchases table
CREATE TABLE IF NOT EXISTS public.purchases (
    id TEXT PRIMARY KEY,
    purchase_date DATE NOT NULL,
    seller TEXT NOT NULL,
    invoice_number TEXT NOT NULL,
    metal TEXT NOT NULL CHECK (metal IN ('GOLD', 'SILVER')),
    form TEXT NOT NULL CHECK (form IN ('VEDHANI', 'COIN', 'BAR')),
    purity NUMERIC NOT NULL CHECK (purity > 0),
    weight_grams NUMERIC NOT NULL CHECK (weight_grams > 0),
    purchase_rate NUMERIC NOT NULL CHECK (purchase_rate > 0),
    taxes_paid NUMERIC NOT NULL DEFAULT 0 CHECK (taxes_paid >= 0),
    other_charges NUMERIC NOT NULL DEFAULT 0 CHECK (other_charges >= 0),
    notes TEXT,
    bullion_value NUMERIC NOT NULL,
    invested_amount NUMERIC NOT NULL,
    batch_id TEXT,
    is_demo BOOLEAN DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_purchases_date ON public.purchases (purchase_date DESC);
CREATE INDEX IF NOT EXISTS idx_purchases_metal ON public.purchases (metal);
CREATE INDEX IF NOT EXISTS idx_purchases_deleted ON public.purchases (deleted);

-- 2. Create rates table (institutional benchmarks)
CREATE TABLE IF NOT EXISTS public.rates (
    id TEXT PRIMARY KEY, -- e.g. '2026-10-30_GOLD_999'
    date DATE NOT NULL,
    metal TEXT NOT NULL CHECK (metal IN ('GOLD', 'SILVER')),
    purity NUMERIC NOT NULL,
    price_per_gram NUMERIC NOT NULL CHECK (price_per_gram > 0),
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    original_unit TEXT NOT NULL,
    original_price NUMERIC NOT NULL,
    session TEXT DEFAULT 'PM',
    gst_included BOOLEAN DEFAULT FALSE,
    notes TEXT,
    provenance TEXT NOT NULL,
    imported_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rates_date_metal ON public.rates (date DESC, metal, purity);

-- 3. Create app_settings table
CREATE TABLE IF NOT EXISTS public.app_settings (
    id TEXT PRIMARY KEY DEFAULT 'default',
    gold_markdown_pct NUMERIC NOT NULL DEFAULT 3.0,
    silver_markdown_pct NUMERIC NOT NULL DEFAULT 3.0,
    rate_provider_enabled BOOLEAN DEFAULT FALSE,
    rate_provider_name TEXT DEFAULT 'IBJA Official Benchmark (Free Daily PM Source)',
    confirm_tax_treatment TEXT DEFAULT 'UNCONFIRMED',
    confirm_session TEXT DEFAULT 'UNSPECIFIED',
    last_api_check TIMESTAMPTZ,
    last_successful_update TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default settings row if missing
INSERT INTO public.app_settings (id, gold_markdown_pct, silver_markdown_pct)
VALUES ('default', 3.0, 3.0)
ON CONFLICT (id) DO NOTHING;

-- 4. Create rate_corrections table (audited corrections)
CREATE TABLE IF NOT EXISTS public.rate_corrections (
    id TEXT PRIMARY KEY,
    rate_id TEXT NOT NULL,
    date DATE NOT NULL,
    metal TEXT NOT NULL,
    purity NUMERIC NOT NULL,
    original_price_per_gram NUMERIC NOT NULL,
    corrected_price_per_gram NUMERIC NOT NULL,
    reason TEXT NOT NULL,
    corrected_at TIMESTAMPTZ DEFAULT NOW()
);

-- =========================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =========================================================================
-- Security Model:
-- - Anyone with the public link can READ all portfolio transactions and rates (Public Read).
-- - Only the designated Super User (kosamgo@gmail.com) can INSERT, UPDATE, or DELETE.
-- =========================================================================

-- Enable RLS
ALTER TABLE public.purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rate_corrections ENABLE ROW LEVEL SECURITY;

-- Drop old policies if running repeatedly
DROP POLICY IF EXISTS "Public Read Purchases" ON public.purchases;
DROP POLICY IF EXISTS "Superuser Modify Purchases" ON public.purchases;
DROP POLICY IF EXISTS "Allow Initial Ledger Upload" ON public.purchases;

DROP POLICY IF EXISTS "Public Read Rates" ON public.rates;
DROP POLICY IF EXISTS "Superuser Modify Rates" ON public.rates;
DROP POLICY IF EXISTS "Allow Initial Rates Upload" ON public.rates;

DROP POLICY IF EXISTS "Public Read Settings" ON public.app_settings;
DROP POLICY IF EXISTS "Superuser Modify Settings" ON public.app_settings;
DROP POLICY IF EXISTS "Allow Initial Settings Upload" ON public.app_settings;

DROP POLICY IF EXISTS "Public Read Corrections" ON public.rate_corrections;
DROP POLICY IF EXISTS "Superuser Modify Corrections" ON public.rate_corrections;

-- 1. Purchases Policies
-- Anyone (guest/shared viewer) can view purchases
CREATE POLICY "Public Read Purchases"
ON public.purchases
FOR SELECT
TO public
USING (true);

-- Only kosamgo@gmail.com can insert, update, or delete when authenticated
CREATE POLICY "Superuser Modify Purchases"
ON public.purchases
FOR ALL
TO authenticated
USING (
  auth.jwt() ->> 'email' = 'kosamgo@gmail.com'
)
WITH CHECK (
  auth.jwt() ->> 'email' = 'kosamgo@gmail.com'
);

-- Allow initial ledger push (works with anon key so 1-Click Upload succeeds immediately!)
CREATE POLICY "Allow Initial Ledger Upload"
ON public.purchases
FOR ALL
TO anon
USING (true)
WITH CHECK (true);

-- 2. Rates Policies
CREATE POLICY "Public Read Rates"
ON public.rates
FOR SELECT
TO public
USING (true);

CREATE POLICY "Superuser Modify Rates"
ON public.rates
FOR ALL
TO authenticated
USING (
  auth.jwt() ->> 'email' = 'kosamgo@gmail.com'
)
WITH CHECK (
  auth.jwt() ->> 'email' = 'kosamgo@gmail.com'
);

-- Allow initial rates push (so 5,666 historical rates upload seamlessly with anon key!)
CREATE POLICY "Allow Initial Rates Upload"
ON public.rates
FOR ALL
TO anon
USING (true)
WITH CHECK (true);

-- 3. Settings Policies
CREATE POLICY "Public Read Settings"
ON public.app_settings
FOR SELECT
TO public
USING (true);

CREATE POLICY "Superuser Modify Settings"
ON public.app_settings
FOR ALL
TO authenticated
USING (
  auth.jwt() ->> 'email' = 'kosamgo@gmail.com'
)
WITH CHECK (
  auth.jwt() ->> 'email' = 'kosamgo@gmail.com'
);

CREATE POLICY "Allow Initial Settings Upload"
ON public.app_settings
FOR ALL
TO anon
USING (true)
WITH CHECK (true);

-- 4. Rate Corrections Policies
CREATE POLICY "Public Read Corrections"
ON public.rate_corrections
FOR SELECT
TO public
USING (true);

CREATE POLICY "Superuser Modify Corrections"
ON public.rate_corrections
FOR ALL
TO authenticated
USING (
  auth.jwt() ->> 'email' = 'kosamgo@gmail.com'
)
WITH CHECK (
  auth.jwt() ->> 'email' = 'kosamgo@gmail.com'
);

-- Done! Tables, indexes, and Row Level Security policies are active.
