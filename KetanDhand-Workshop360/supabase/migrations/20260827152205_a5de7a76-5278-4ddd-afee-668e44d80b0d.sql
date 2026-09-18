CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

CREATE TABLE public.app_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  phone text NOT NULL UNIQUE,
  email text,
  password_hash text NOT NULL,
  role text NOT NULL CHECK (role IN ('owner','shopkeeper','mechanic')),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('approved','pending','rejected','deactivated')),
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT ALL ON public.app_users TO service_role;
ALTER TABLE public.app_users ENABLE ROW LEVEL SECURITY;

CREATE TABLE public.app_sessions (
  token text PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES public.app_users(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL DEFAULT now() + interval '30 days'
);
GRANT ALL ON public.app_sessions TO service_role;
ALTER TABLE public.app_sessions ENABLE ROW LEVEL SECURITY;

CREATE TABLE public.repairs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  repair_no text NOT NULL,
  bike_registration text NOT NULL,
  bike_model text NOT NULL,
  customer_name text NOT NULL DEFAULT '',
  customer_phone text NOT NULL DEFAULT '',
  mechanic_id uuid,
  mechanic_name text NOT NULL DEFAULT '',
  start_time timestamptz NOT NULL DEFAULT now(),
  completion_time timestamptz,
  status text NOT NULL DEFAULT 'repairing' CHECK (status IN ('repairing','ready_for_billing','completed')),
  items jsonb NOT NULL DEFAULT '[]'::jsonb,
  labour_charges numeric NOT NULL DEFAULT 0,
  discount numeric NOT NULL DEFAULT 0,
  tax_rate numeric NOT NULL DEFAULT 0,
  audit_trail jsonb NOT NULL DEFAULT '[]'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX repairs_bike_registration_idx ON public.repairs (bike_registration);
CREATE INDEX repairs_created_at_idx ON public.repairs (created_at DESC);
GRANT ALL ON public.repairs TO service_role;
ALTER TABLE public.repairs ENABLE ROW LEVEL SECURITY;

INSERT INTO public.app_users (id, name, phone, email, password_hash, role, status) VALUES
  ('11111111-1111-4111-8111-111111111111','Rajesh Owner','9876543210','owner@workshop.com', extensions.crypt('admin123', extensions.gen_salt('bf')),'owner','approved'),
  ('22222222-2222-4222-8222-222222222222','Sanjay Shopkeeper','9876543212','shopkeeper@workshop.com', extensions.crypt('shop123', extensions.gen_salt('bf')),'shopkeeper','approved'),
  ('33333333-3333-4333-8333-333333333333','Ramesh Kumar','9123456789','ramesh@workshop.com', extensions.crypt('mech123', extensions.gen_salt('bf')),'mechanic','approved'),
  ('44444444-4444-4444-8444-444444444444','Suresh Singh','9988776655','suresh@workshop.com', extensions.crypt('mech123', extensions.gen_salt('bf')),'mechanic','pending');

INSERT INTO public.repairs (id, repair_no, bike_registration, bike_model, customer_name, customer_phone, mechanic_id, mechanic_name, start_time, completion_time, status, items, labour_charges, discount, tax_rate, audit_trail, created_at) VALUES
  ('aaaaaaaa-0000-4000-8000-000000000101','REP-101','KA01AB1234','Hero Splendor Plus','Amit Sharma','9811122233','33333333-3333-4333-8333-333333333333','Ramesh Kumar', now() - interval '3 hours', NULL, 'repairing',
   '[{"id":"item-1","name":"Gulf Engine Oil 20W-50","quantity":1,"rate":450,"addedBy":"mechanic","addedByName":"Ramesh Kumar","timestamp":"2026-01-01T00:00:00.000Z"},{"id":"item-2","name":"Oil Filter","quantity":1,"rate":120,"addedBy":"mechanic","addedByName":"Ramesh Kumar","timestamp":"2026-01-01T00:00:00.000Z"}]'::jsonb,
   250, 0, 0,
   '[{"id":"aud-1","timestamp":"2026-01-01T00:00:00.000Z","userName":"Ramesh Kumar","userRole":"mechanic","action":"START_REPAIR","details":"Started repair for Hero Splendor Plus (KA01AB1234)"}]'::jsonb,
   now() - interval '3 hours'),
  ('aaaaaaaa-0000-4000-8000-000000000102','REP-102','KA05XY9988','Royal Enfield Classic 350','Vikram Malhotra','9822233344','33333333-3333-4333-8333-333333333333','Ramesh Kumar', now() - interval '1 day', now() - interval '22 hours', 'ready_for_billing',
   '[{"id":"item-201","name":"Brake Pad","quantity":2,"rate":350,"addedBy":"mechanic","addedByName":"Ramesh Kumar","timestamp":"2026-01-01T00:00:00.000Z"},{"id":"item-202","name":"Chain Sprocket Set","quantity":1,"rate":1850,"addedBy":"mechanic","addedByName":"Ramesh Kumar","timestamp":"2026-01-01T00:00:00.000Z"}]'::jsonb,
   500, 0, 0,
   '[{"id":"aud-10","timestamp":"2026-01-01T00:00:00.000Z","userName":"Ramesh Kumar","userRole":"mechanic","action":"START_REPAIR","details":"Started repair for Royal Enfield Classic 350 (KA05XY9988)"},{"id":"aud-11","timestamp":"2026-01-01T00:00:00.000Z","userName":"Ramesh Kumar","userRole":"mechanic","action":"FINISH_REPAIR","details":"Marked repair as Ready for Billing"}]'::jsonb,
   now() - interval '1 day');