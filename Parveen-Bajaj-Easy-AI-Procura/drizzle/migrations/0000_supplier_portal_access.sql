CREATE TABLE public.supplier_accounts (
 user_id uuid PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
 supplier_id uuid NOT NULL REFERENCES public.suppliers(id),
 contact_name text NOT NULL DEFAULT '',
 created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT ON public.supplier_accounts TO authenticated;
GRANT ALL ON public.supplier_accounts TO service_role;
ALTER TABLE public.supplier_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY supplier_accounts_read ON public.supplier_accounts FOR SELECT TO authenticated USING(user_id=auth.uid() OR public.has_role(auth.uid(),'ADMIN'));
CREATE INDEX supplier_accounts_supplier_idx ON public.supplier_accounts(supplier_id);
CREATE FUNCTION public.is_internal_user() RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public AS $$ SELECT EXISTS(SELECT 1 FROM public.user_roles WHERE user_id=auth.uid()) AND NOT EXISTS(SELECT 1 FROM public.supplier_accounts WHERE user_id=auth.uid()) $$;
CREATE FUNCTION public.owns_supplier(p_supplier uuid) RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public AS $$ SELECT EXISTS(SELECT 1 FROM public.supplier_accounts a JOIN public.suppliers s ON s.id=a.supplier_id WHERE a.user_id=auth.uid() AND a.supplier_id=p_supplier AND s.status='ACTIVE') $$;
REVOKE ALL ON FUNCTION public.is_internal_user(), public.owns_supplier(uuid) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.is_internal_user(), public.owns_supplier(uuid) TO authenticated,service_role;
ALTER POLICY profiles_read ON public.profiles USING(id=auth.uid() OR public.is_internal_user());
ALTER POLICY roles_read ON public.user_roles USING(user_id=auth.uid() OR public.is_internal_user());
ALTER POLICY suppliers_read ON public.suppliers USING(public.is_internal_user() OR public.owns_supplier(id));
ALTER POLICY departments_read ON public.departments USING(public.is_internal_user());
ALTER POLICY items_read ON public.items USING(public.is_internal_user() OR EXISTS(SELECT 1 FROM public.lpo_lines l JOIN public.lpo_header h ON h.id=l.lpo_id WHERE l.item_id=items.id AND public.owns_supplier(h.supplier_id) AND h.status IN('PENDING','APPROVED')));
ALTER POLICY lpo_read ON public.lpo_header USING(public.is_internal_user() OR (public.owns_supplier(supplier_id) AND status IN('PENDING','APPROVED')));
ALTER POLICY grn_read ON public.grn_header USING(public.is_internal_user() OR (public.owns_supplier(supplier_id) AND status IN('PENDING','APPROVED','REJECTED')));
ALTER POLICY inv_read ON public.invoices USING(public.is_internal_user() OR (public.owns_supplier(supplier_id) AND status IN('PENDING','APPROVED','REJECTED')));
ALTER POLICY lpo_lines_read ON public.lpo_lines USING(EXISTS(SELECT 1 FROM public.lpo_header h WHERE h.id=lpo_id));
ALTER POLICY grn_lines_read ON public.grn_lines USING(EXISTS(SELECT 1 FROM public.grn_header h WHERE h.id=grn_id));
ALTER POLICY inv_lines_read ON public.invoice_lines USING(EXISTS(SELECT 1 FROM public.invoices h WHERE h.id=invoice_id));
ALTER POLICY log_read ON public.approval_log USING(public.is_internal_user());
ALTER POLICY log_insert ON public.approval_log WITH CHECK(actor=auth.uid() AND public.is_internal_user());
DO $$ DECLARE t text; BEGIN FOREACH t IN ARRAY ARRAY['suppliers','departments','items','lpo_header','lpo_lines','grn_header','grn_lines','invoices','invoice_lines','approval_log','user_roles'] LOOP
 EXECUTE format('CREATE POLICY supplier_no_insert ON public.%I AS RESTRICTIVE FOR INSERT TO authenticated WITH CHECK(public.is_internal_user())',t);
 EXECUTE format('CREATE POLICY supplier_no_update ON public.%I AS RESTRICTIVE FOR UPDATE TO authenticated USING(public.is_internal_user()) WITH CHECK(public.is_internal_user())',t);
 EXECUTE format('CREATE POLICY supplier_no_delete ON public.%I AS RESTRICTIVE FOR DELETE TO authenticated USING(public.is_internal_user())',t);
 END LOOP; END $$;
CREATE FUNCTION public.link_supplier_account(p_email text,p_supplier uuid) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$ DECLARE account_id uuid; contact text; BEGIN
 IF NOT public.is_internal_user() OR NOT public.has_role(auth.uid(),'ADMIN') THEN RAISE EXCEPTION 'Administrator access required'; END IF;
 IF NOT EXISTS(SELECT 1 FROM public.suppliers WHERE id=p_supplier AND status='ACTIVE') THEN RAISE EXCEPTION 'Supplier must be approved and active'; END IF;
 SELECT id, full_name INTO account_id,contact FROM public.profiles WHERE lower(email)=lower(trim(p_email));
 IF account_id IS NULL THEN RAISE EXCEPTION 'Ask the supplier to register at the supplier login first'; END IF;
 IF EXISTS(SELECT 1 FROM public.user_roles WHERE user_id=account_id) THEN RAISE EXCEPTION 'Internal accounts cannot be linked as suppliers'; END IF;
 INSERT INTO public.supplier_accounts(user_id,supplier_id,contact_name) VALUES(account_id,p_supplier,coalesce(contact,'')) ON CONFLICT(user_id) DO UPDATE SET supplier_id=excluded.supplier_id, contact_name=excluded.contact_name;
 END $$;
REVOKE ALL ON FUNCTION public.link_supplier_account(text,uuid) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.link_supplier_account(text,uuid) TO authenticated,service_role;
CREATE OR REPLACE FUNCTION public.handle_new_user() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public AS $$ DECLARE existing int; BEGIN
 INSERT INTO public.profiles(id,full_name,email) VALUES(NEW.id,COALESCE(NEW.raw_user_meta_data->>'full_name',split_part(NEW.email,'@',1)),NEW.email) ON CONFLICT(id) DO NOTHING;
 IF NEW.raw_user_meta_data->>'account_type'='supplier' THEN RETURN NEW; END IF;
 SELECT count(*) INTO existing FROM public.user_roles;
 IF existing=0 THEN INSERT INTO public.user_roles(user_id,role) VALUES(NEW.id,'ADMIN'),(NEW.id,'MAKER'),(NEW.id,'APPROVER'),(NEW.id,'STOREKEEPER'),(NEW.id,'FINANCE_MAKER'),(NEW.id,'FINANCE_APPROVER');
 ELSE INSERT INTO public.user_roles(user_id,role) VALUES(NEW.id,'MAKER') ON CONFLICT DO NOTHING; END IF;
 RETURN NEW; END $$;