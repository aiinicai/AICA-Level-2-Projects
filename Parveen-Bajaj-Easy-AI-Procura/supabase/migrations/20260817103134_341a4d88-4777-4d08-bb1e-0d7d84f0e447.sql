
-- ENUMS
CREATE TYPE public.app_role AS ENUM ('MAKER','APPROVER','ADMIN','STOREKEEPER','FINANCE_MAKER','FINANCE_APPROVER');
CREATE TYPE public.supplier_status AS ENUM ('PENDING','ACTIVE','INACTIVE');
CREATE TYPE public.master_status AS ENUM ('ACTIVE','INACTIVE');
CREATE TYPE public.doc_status AS ENUM ('DRAFT','PENDING','APPROVED','REJECTED','CANCELLED');
CREATE TYPE public.grn_receipt_status AS ENUM ('ACCEPTED','PARTIAL','REJECTED');
CREATE TYPE public.item_condition AS ENUM ('OK','DAMAGED','WRONG_ITEM');

-- PROFILES
CREATE TABLE public.profiles (
  id uuid PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
  full_name text NOT NULL DEFAULT '',
  email text,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE ON public.profiles TO authenticated;
GRANT ALL ON public.profiles TO service_role;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "profiles_read" ON public.profiles FOR SELECT TO authenticated USING (true);
CREATE POLICY "profiles_update_own" ON public.profiles FOR UPDATE TO authenticated USING (id = auth.uid()) WITH CHECK (id = auth.uid());

-- USER ROLES
CREATE TABLE public.user_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users ON DELETE CASCADE,
  role public.app_role NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, role)
);
GRANT SELECT ON public.user_roles TO authenticated;
GRANT ALL ON public.user_roles TO service_role;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.has_role(_user_id uuid, _role public.app_role)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role = _role)
$$;

CREATE POLICY "roles_read" ON public.user_roles FOR SELECT TO authenticated USING (true);
CREATE POLICY "roles_admin_write" ON public.user_roles FOR ALL TO authenticated
  USING (public.has_role(auth.uid(), 'ADMIN')) WITH CHECK (public.has_role(auth.uid(), 'ADMIN'));

-- new user handler: profile + first user becomes ADMIN
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE existing int;
BEGIN
  INSERT INTO public.profiles (id, full_name, email)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email,'@',1)), NEW.email)
  ON CONFLICT (id) DO NOTHING;

  SELECT count(*) INTO existing FROM public.user_roles;
  IF existing = 0 THEN
    INSERT INTO public.user_roles (user_id, role) VALUES
      (NEW.id,'ADMIN'),(NEW.id,'MAKER'),(NEW.id,'APPROVER'),
      (NEW.id,'STOREKEEPER'),(NEW.id,'FINANCE_MAKER'),(NEW.id,'FINANCE_APPROVER');
  ELSE
    INSERT INTO public.user_roles (user_id, role) VALUES (NEW.id,'MAKER') ON CONFLICT DO NOTHING;
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- DOCUMENT NUMBERING
CREATE TABLE public.document_sequences (
  doc_type text NOT NULL,
  year int NOT NULL,
  last_seq int NOT NULL DEFAULT 0,
  PRIMARY KEY (doc_type, year)
);
GRANT ALL ON public.document_sequences TO service_role;
ALTER TABLE public.document_sequences ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.next_document_number(p_type text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE y int := EXTRACT(YEAR FROM now())::int; s int;
BEGIN
  INSERT INTO public.document_sequences (doc_type, year, last_seq)
  VALUES (p_type, y, 1)
  ON CONFLICT (doc_type, year) DO UPDATE SET last_seq = public.document_sequences.last_seq + 1
  RETURNING last_seq INTO s;
  RETURN p_type || '-' || y::text || '-' || lpad(s::text, 4, '0');
END;
$$;

-- SUPPLIERS
CREATE TABLE public.suppliers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_code text NOT NULL UNIQUE,
  supplier_name text NOT NULL,
  address text,
  contact_person text,
  phone text,
  email text,
  vat_pin text,
  payment_terms text,
  status public.supplier_status NOT NULL DEFAULT 'PENDING',
  maker uuid REFERENCES auth.users,
  maker_name text,
  approver uuid REFERENCES auth.users,
  approver_name text,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.suppliers TO authenticated;
GRANT ALL ON public.suppliers TO service_role;
ALTER TABLE public.suppliers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "suppliers_read" ON public.suppliers FOR SELECT TO authenticated USING (true);
CREATE POLICY "suppliers_maker_insert" ON public.suppliers FOR INSERT TO authenticated
  WITH CHECK (public.has_role(auth.uid(),'MAKER') AND maker = auth.uid() AND status = 'PENDING');
CREATE POLICY "suppliers_maker_edit_pending" ON public.suppliers FOR UPDATE TO authenticated
  USING (maker = auth.uid() AND status = 'PENDING') WITH CHECK (maker = auth.uid());
CREATE POLICY "suppliers_approver_update" ON public.suppliers FOR UPDATE TO authenticated
  USING (public.has_role(auth.uid(),'APPROVER') AND maker <> auth.uid())
  WITH CHECK (public.has_role(auth.uid(),'APPROVER'));
CREATE POLICY "suppliers_maker_delete_pending" ON public.suppliers FOR DELETE TO authenticated
  USING (maker = auth.uid() AND status = 'PENDING');

-- DEPARTMENTS
CREATE TABLE public.departments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  department_code text NOT NULL UNIQUE,
  department_name text NOT NULL,
  hod text,
  status public.master_status NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.departments TO authenticated;
GRANT ALL ON public.departments TO service_role;
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "departments_read" ON public.departments FOR SELECT TO authenticated USING (true);
CREATE POLICY "departments_admin_write" ON public.departments FOR ALL TO authenticated
  USING (public.has_role(auth.uid(),'ADMIN')) WITH CHECK (public.has_role(auth.uid(),'ADMIN'));

-- ITEMS
CREATE TABLE public.items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_code text NOT NULL UNIQUE,
  item_description text NOT NULL,
  unit text NOT NULL,
  standard_price numeric(18,2),
  status public.master_status NOT NULL DEFAULT 'ACTIVE',
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.items TO authenticated;
GRANT ALL ON public.items TO service_role;
ALTER TABLE public.items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "items_read" ON public.items FOR SELECT TO authenticated USING (true);
CREATE POLICY "items_admin_write" ON public.items FOR ALL TO authenticated
  USING (public.has_role(auth.uid(),'ADMIN')) WITH CHECK (public.has_role(auth.uid(),'ADMIN'));

-- LPO
CREATE TABLE public.lpo_header (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lpo_number text NOT NULL UNIQUE DEFAULT public.next_document_number('LPO'),
  lpo_date date NOT NULL DEFAULT CURRENT_DATE,
  supplier_id uuid NOT NULL REFERENCES public.suppliers(id),
  department_id uuid NOT NULL REFERENCES public.departments(id),
  delivery_location text,
  payment_terms text,
  remarks text,
  total_value numeric(18,2) NOT NULL DEFAULT 0,
  status public.doc_status NOT NULL DEFAULT 'DRAFT',
  maker uuid NOT NULL REFERENCES auth.users,
  maker_name text,
  approver uuid REFERENCES auth.users,
  approver_name text,
  approved_at timestamptz,
  reject_reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.lpo_header TO authenticated;
GRANT ALL ON public.lpo_header TO service_role;
ALTER TABLE public.lpo_header ENABLE ROW LEVEL SECURITY;
CREATE POLICY "lpo_read" ON public.lpo_header FOR SELECT TO authenticated USING (true);
CREATE POLICY "lpo_maker_insert" ON public.lpo_header FOR INSERT TO authenticated
  WITH CHECK (public.has_role(auth.uid(),'MAKER') AND maker = auth.uid() AND status IN ('DRAFT','PENDING'));
CREATE POLICY "lpo_maker_update" ON public.lpo_header FOR UPDATE TO authenticated
  USING (maker = auth.uid() AND status IN ('DRAFT','PENDING')) WITH CHECK (maker = auth.uid() AND status IN ('DRAFT','PENDING'));
CREATE POLICY "lpo_approver_update" ON public.lpo_header FOR UPDATE TO authenticated
  USING (public.has_role(auth.uid(),'APPROVER') AND status = 'PENDING' AND maker <> auth.uid())
  WITH CHECK (public.has_role(auth.uid(),'APPROVER') AND status IN ('APPROVED','REJECTED','CANCELLED'));
CREATE POLICY "lpo_maker_delete_draft" ON public.lpo_header FOR DELETE TO authenticated
  USING (maker = auth.uid() AND status = 'DRAFT');

CREATE TABLE public.lpo_lines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lpo_id uuid NOT NULL REFERENCES public.lpo_header(id) ON DELETE CASCADE,
  item_id uuid NOT NULL REFERENCES public.items(id),
  quantity_ordered numeric(18,3) NOT NULL,
  unit_price numeric(18,2) NOT NULL,
  line_value numeric(18,2) GENERATED ALWAYS AS (round(quantity_ordered * unit_price, 2)) STORED
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.lpo_lines TO authenticated;
GRANT ALL ON public.lpo_lines TO service_role;
ALTER TABLE public.lpo_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "lpo_lines_read" ON public.lpo_lines FOR SELECT TO authenticated USING (true);
CREATE POLICY "lpo_lines_maker_write" ON public.lpo_lines FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.lpo_header h WHERE h.id = lpo_id AND h.maker = auth.uid() AND h.status IN ('DRAFT','PENDING')))
  WITH CHECK (EXISTS (SELECT 1 FROM public.lpo_header h WHERE h.id = lpo_id AND h.maker = auth.uid() AND h.status IN ('DRAFT','PENDING')));

-- GRN
CREATE TABLE public.grn_header (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  grn_number text NOT NULL UNIQUE DEFAULT public.next_document_number('GRN'),
  grn_date date NOT NULL DEFAULT CURRENT_DATE,
  lpo_id uuid NOT NULL REFERENCES public.lpo_header(id),
  supplier_id uuid NOT NULL REFERENCES public.suppliers(id),
  department_id uuid NOT NULL REFERENCES public.departments(id),
  delivery_note_no text,
  received_by text,
  checked_by text,
  receipt_status public.grn_receipt_status NOT NULL DEFAULT 'ACCEPTED',
  status public.doc_status NOT NULL DEFAULT 'DRAFT',
  over_receipt_override boolean NOT NULL DEFAULT false,
  maker uuid NOT NULL REFERENCES auth.users,
  maker_name text,
  approver uuid REFERENCES auth.users,
  approver_name text,
  approved_at timestamptz,
  reject_reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.grn_header TO authenticated;
GRANT ALL ON public.grn_header TO service_role;
ALTER TABLE public.grn_header ENABLE ROW LEVEL SECURITY;
CREATE POLICY "grn_read" ON public.grn_header FOR SELECT TO authenticated USING (true);
CREATE POLICY "grn_maker_insert" ON public.grn_header FOR INSERT TO authenticated
  WITH CHECK ((public.has_role(auth.uid(),'STOREKEEPER') OR public.has_role(auth.uid(),'MAKER'))
    AND maker = auth.uid() AND status IN ('DRAFT','PENDING')
    AND EXISTS (SELECT 1 FROM public.lpo_header h WHERE h.id = lpo_id AND h.status = 'APPROVED'));
CREATE POLICY "grn_maker_update" ON public.grn_header FOR UPDATE TO authenticated
  USING (maker = auth.uid() AND status IN ('DRAFT','PENDING')) WITH CHECK (maker = auth.uid() AND status IN ('DRAFT','PENDING'));
CREATE POLICY "grn_approver_update" ON public.grn_header FOR UPDATE TO authenticated
  USING (public.has_role(auth.uid(),'APPROVER') AND status = 'PENDING' AND maker <> auth.uid())
  WITH CHECK (public.has_role(auth.uid(),'APPROVER') AND status IN ('APPROVED','REJECTED'));
CREATE POLICY "grn_maker_delete_draft" ON public.grn_header FOR DELETE TO authenticated
  USING (maker = auth.uid() AND status = 'DRAFT');

CREATE TABLE public.grn_lines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  grn_id uuid NOT NULL REFERENCES public.grn_header(id) ON DELETE CASCADE,
  lpo_line_id uuid NOT NULL REFERENCES public.lpo_lines(id),
  item_id uuid NOT NULL REFERENCES public.items(id),
  qty_ordered numeric(18,3) NOT NULL,
  qty_received numeric(18,3) NOT NULL DEFAULT 0,
  shortage_excess numeric(18,3) GENERATED ALWAYS AS (qty_received - qty_ordered) STORED,
  item_condition public.item_condition NOT NULL DEFAULT 'OK',
  remarks text
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.grn_lines TO authenticated;
GRANT ALL ON public.grn_lines TO service_role;
ALTER TABLE public.grn_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "grn_lines_read" ON public.grn_lines FOR SELECT TO authenticated USING (true);
CREATE POLICY "grn_lines_maker_write" ON public.grn_lines FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.grn_header g WHERE g.id = grn_id AND g.maker = auth.uid() AND g.status IN ('DRAFT','PENDING')))
  WITH CHECK (EXISTS (SELECT 1 FROM public.grn_header g WHERE g.id = grn_id AND g.maker = auth.uid() AND g.status IN ('DRAFT','PENDING')));

-- validate over-receipt
CREATE OR REPLACE FUNCTION public.validate_grn_line()
RETURNS trigger LANGUAGE plpgsql SET search_path = public AS $$
DECLARE ovr boolean;
BEGIN
  SELECT over_receipt_override INTO ovr FROM public.grn_header WHERE id = NEW.grn_id;
  IF NEW.qty_received > NEW.qty_ordered AND NOT COALESCE(ovr,false) THEN
    RAISE EXCEPTION 'Quantity received (%) exceeds ordered quantity (%). Approver override required.', NEW.qty_received, NEW.qty_ordered;
  END IF;
  IF NEW.qty_received < 0 THEN
    RAISE EXCEPTION 'Quantity received cannot be negative';
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER grn_lines_validate BEFORE INSERT OR UPDATE ON public.grn_lines
FOR EACH ROW EXECUTE FUNCTION public.validate_grn_line();

-- INVOICES
CREATE TABLE public.invoices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  internal_number text NOT NULL UNIQUE DEFAULT public.next_document_number('INV'),
  invoice_number text NOT NULL,
  invoice_date date NOT NULL DEFAULT CURRENT_DATE,
  supplier_id uuid NOT NULL REFERENCES public.suppliers(id),
  grn_id uuid NOT NULL REFERENCES public.grn_header(id),
  lpo_id uuid REFERENCES public.lpo_header(id),
  invoice_value numeric(18,2) NOT NULL DEFAULT 0,
  vat_amount numeric(18,2) NOT NULL DEFAULT 0,
  total_value numeric(18,2) GENERATED ALWAYS AS (invoice_value + vat_amount) STORED,
  status public.doc_status NOT NULL DEFAULT 'DRAFT',
  maker uuid NOT NULL REFERENCES auth.users,
  maker_name text,
  approver uuid REFERENCES auth.users,
  approver_name text,
  approved_at timestamptz,
  reject_reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.invoices TO authenticated;
GRANT ALL ON public.invoices TO service_role;
ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "inv_read" ON public.invoices FOR SELECT TO authenticated USING (true);
CREATE POLICY "inv_maker_insert" ON public.invoices FOR INSERT TO authenticated
  WITH CHECK ((public.has_role(auth.uid(),'FINANCE_MAKER') OR public.has_role(auth.uid(),'MAKER'))
    AND maker = auth.uid() AND status IN ('DRAFT','PENDING')
    AND EXISTS (SELECT 1 FROM public.grn_header g WHERE g.id = grn_id AND g.status = 'APPROVED'));
CREATE POLICY "inv_maker_update" ON public.invoices FOR UPDATE TO authenticated
  USING (maker = auth.uid() AND status IN ('DRAFT','PENDING')) WITH CHECK (maker = auth.uid() AND status IN ('DRAFT','PENDING'));
CREATE POLICY "inv_approver_update" ON public.invoices FOR UPDATE TO authenticated
  USING ((public.has_role(auth.uid(),'FINANCE_APPROVER') OR public.has_role(auth.uid(),'APPROVER')) AND status = 'PENDING' AND maker <> auth.uid())
  WITH CHECK ((public.has_role(auth.uid(),'FINANCE_APPROVER') OR public.has_role(auth.uid(),'APPROVER')) AND status IN ('APPROVED','REJECTED'));
CREATE POLICY "inv_maker_delete_draft" ON public.invoices FOR DELETE TO authenticated
  USING (maker = auth.uid() AND status = 'DRAFT');

CREATE TABLE public.invoice_lines (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id uuid NOT NULL REFERENCES public.invoices(id) ON DELETE CASCADE,
  grn_line_id uuid NOT NULL REFERENCES public.grn_lines(id),
  item_id uuid NOT NULL REFERENCES public.items(id),
  quantity numeric(18,3) NOT NULL,
  lpo_price numeric(18,2) NOT NULL DEFAULT 0,
  invoice_price numeric(18,2) NOT NULL DEFAULT 0,
  price_variance numeric(18,2) GENERATED ALWAYS AS (invoice_price - lpo_price) STORED,
  line_value numeric(18,2) GENERATED ALWAYS AS (round(quantity * invoice_price, 2)) STORED
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.invoice_lines TO authenticated;
GRANT ALL ON public.invoice_lines TO service_role;
ALTER TABLE public.invoice_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "inv_lines_read" ON public.invoice_lines FOR SELECT TO authenticated USING (true);
CREATE POLICY "inv_lines_maker_write" ON public.invoice_lines FOR ALL TO authenticated
  USING (EXISTS (SELECT 1 FROM public.invoices i WHERE i.id = invoice_id AND i.maker = auth.uid() AND i.status IN ('DRAFT','PENDING')))
  WITH CHECK (EXISTS (SELECT 1 FROM public.invoices i WHERE i.id = invoice_id AND i.maker = auth.uid() AND i.status IN ('DRAFT','PENDING')));

-- APPROVAL LOG
CREATE TABLE public.approval_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  doc_type text NOT NULL,
  doc_id uuid NOT NULL,
  doc_number text,
  action text NOT NULL,
  actor uuid REFERENCES auth.users,
  actor_name text,
  remarks text,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT ON public.approval_log TO authenticated;
GRANT ALL ON public.approval_log TO service_role;
ALTER TABLE public.approval_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "log_read" ON public.approval_log FOR SELECT TO authenticated USING (true);
CREATE POLICY "log_insert" ON public.approval_log FOR INSERT TO authenticated WITH CHECK (actor = auth.uid());

-- SEED master data
INSERT INTO public.departments (department_code, department_name, hod) VALUES
  ('DEP-ADM','Administration','J. Mwangi'),
  ('DEP-FIN','Finance','A. Kimani'),
  ('DEP-OPS','Operations','P. Otieno'),
  ('DEP-IT','Information Technology','S. Wanjiru'),
  ('DEP-STO','Stores','M. Achieng');

INSERT INTO public.items (item_code, item_description, unit, standard_price) VALUES
  ('ITM-0001','A4 Photocopy Paper 80gsm (ream)','REAM',620.00),
  ('ITM-0002','Toner Cartridge HP 26A','PCS',9800.00),
  ('ITM-0003','Ballpoint Pen Blue (box of 50)','BOX',480.00),
  ('ITM-0004','Diesel Fuel','LITRE',185.00),
  ('ITM-0005','Cleaning Detergent 5L','JERRYCAN',1250.00),
  ('ITM-0006','Laptop 14in i5 16GB','PCS',95000.00),
  ('ITM-0007','Office Chair Ergonomic','PCS',18500.00),
  ('ITM-0008','Safety Boots Pair','PAIR',4200.00);
