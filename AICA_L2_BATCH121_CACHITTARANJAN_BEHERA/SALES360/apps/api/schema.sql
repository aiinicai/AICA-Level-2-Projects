CREATE TABLE IF NOT EXISTS migration(version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS company(id text PRIMARY KEY, name text NOT NULL, currency text NOT NULL DEFAULT 'AED');
CREATE TABLE IF NOT EXISTS organization_profile(company_id text PRIMARY KEY REFERENCES company(id),details jsonb NOT NULL,revision integer NOT NULL CHECK(revision>0),updated_at timestamptz NOT NULL DEFAULT now(),updated_by text NOT NULL);
CREATE TABLE IF NOT EXISTS app_user(id text PRIMARY KEY, company_id text NOT NULL REFERENCES company(id), name text NOT NULL, role text NOT NULL, password_hash text NOT NULL, active boolean NOT NULL DEFAULT true);
CREATE TABLE IF NOT EXISTS customer(id text PRIMARY KEY, company_id text NOT NULL REFERENCES company(id), code text NOT NULL, name text NOT NULL, email text NOT NULL DEFAULT '', trn text NOT NULL DEFAULT '', terms integer NOT NULL DEFAULT 30 CHECK(terms>=0), UNIQUE(company_id,code), UNIQUE(company_id,id));
CREATE TABLE IF NOT EXISTS project(id text PRIMARY KEY, company_id text NOT NULL, customer_id text NOT NULL, code text NOT NULL, name text NOT NULL, category text NOT NULL, fee numeric(18,2) NOT NULL CHECK(fee>0), status text NOT NULL DEFAULT 'Active', location text NOT NULL DEFAULT '', stages jsonb NOT NULL, version integer NOT NULL DEFAULT 1, UNIQUE(company_id,code), UNIQUE(company_id,id,customer_id), FOREIGN KEY(company_id,customer_id) REFERENCES customer(company_id,id));
CREATE TABLE IF NOT EXISTS certificate(id text PRIMARY KEY, company_id text NOT NULL, project_id text NOT NULL, customer_id text NOT NULL, reference text NOT NULL, revision integer NOT NULL DEFAULT 1, state text NOT NULL DEFAULT 'Draft', prepared_by text NOT NULL REFERENCES app_user(id), claim_date date NOT NULL, due_date date NOT NULL, fee numeric(18,2) NOT NULL, stages jsonb NOT NULL, cumulative numeric(18,2) NOT NULL, previous numeric(18,2) NOT NULL, settlement numeric(18,2) NOT NULL CHECK(settlement>0), approvals jsonb NOT NULL DEFAULT '[]', snapshot_hash text NOT NULL, UNIQUE(company_id,reference,revision), UNIQUE(company_id,id), FOREIGN KEY(company_id,project_id,customer_id) REFERENCES project(company_id,id,customer_id));
CREATE TABLE IF NOT EXISTS draft_invoice(id text PRIMARY KEY, company_id text NOT NULL, certificate_id text NOT NULL UNIQUE, reference text NOT NULL, confirmation jsonb, status text NOT NULL DEFAULT 'Awaiting confirmation', FOREIGN KEY(company_id,certificate_id) REFERENCES certificate(company_id,id));
CREATE TABLE IF NOT EXISTS invoice(id text PRIMARY KEY, company_id text NOT NULL, project_id text NOT NULL, customer_id text NOT NULL, certificate_id text UNIQUE, reference text NOT NULL, issue_date date NOT NULL, due_date date NOT NULL, net numeric(18,2) NOT NULL CHECK(net>0), vat numeric(18,2) NOT NULL CHECK(vat>=0), total numeric(18,2) NOT NULL CHECK(total=net+vat), category text NOT NULL, confirmation jsonb NOT NULL, UNIQUE(company_id,reference), UNIQUE(company_id,id,customer_id), FOREIGN KEY(company_id,project_id,customer_id) REFERENCES project(company_id,id,customer_id));
CREATE TABLE IF NOT EXISTS receipt(id text PRIMARY KEY, company_id text NOT NULL, customer_id text NOT NULL, reference text NOT NULL, receipt_date date NOT NULL, amount numeric(18,2) NOT NULL CHECK(amount>0), method text NOT NULL, UNIQUE(company_id,reference), UNIQUE(company_id,id,customer_id), FOREIGN KEY(company_id,customer_id) REFERENCES customer(company_id,id));
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS organization_snapshot jsonb NOT NULL DEFAULT '{}';
INSERT INTO migration(version) VALUES(5) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS allocation(id text PRIMARY KEY, company_id text NOT NULL, customer_id text NOT NULL, receipt_id text NOT NULL, invoice_id text NOT NULL, amount numeric(18,2) NOT NULL CHECK(amount>0), effective_date date NOT NULL, FOREIGN KEY(company_id,receipt_id,customer_id) REFERENCES receipt(company_id,id,customer_id), FOREIGN KEY(company_id,invoice_id,customer_id) REFERENCES invoice(company_id,id,customer_id));
CREATE TABLE IF NOT EXISTS audit_event(sequence bigserial PRIMARY KEY, company_id text NOT NULL, actor text NOT NULL, action text NOT NULL, entity_id text NOT NULL, payload jsonb NOT NULL, at timestamptz NOT NULL DEFAULT now(), previous_hash text NOT NULL, hash text NOT NULL);
CREATE TABLE IF NOT EXISTS contract(id text PRIMARY KEY, company_id text NOT NULL REFERENCES company(id), name text NOT NULL, hash text NOT NULL, size bigint NOT NULL, mime text NOT NULL, uploaded_at timestamptz NOT NULL DEFAULT now(), uploaded_by text NOT NULL, status text NOT NULL DEFAULT 'Quarantined', decision text, project_id text, UNIQUE(company_id,hash));
CREATE TABLE IF NOT EXISTS import_batch(id text PRIMARY KEY, company_id text NOT NULL REFERENCES company(id), hash text NOT NULL, payload jsonb NOT NULL, errors jsonb NOT NULL, status text NOT NULL DEFAULT 'Preview', created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,hash));
CREATE TABLE IF NOT EXISTS outbox(id text PRIMARY KEY, company_id text NOT NULL REFERENCES company(id), kind text NOT NULL, idempotency_key text NOT NULL, payload jsonb NOT NULL, status text NOT NULL DEFAULT 'Pending', attempts integer NOT NULL DEFAULT 0, result jsonb, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,kind,idempotency_key));
CREATE TABLE IF NOT EXISTS numbering(company_id text PRIMARY KEY REFERENCES company(id), invoice_next integer NOT NULL DEFAULT 1);
CREATE INDEX IF NOT EXISTS ix_project_search ON project(company_id,code,name);
CREATE INDEX IF NOT EXISTS ix_invoice_dates ON invoice(company_id,issue_date,due_date);
CREATE INDEX IF NOT EXISTS ix_receipt_date ON receipt(company_id,receipt_date);
CREATE INDEX IF NOT EXISTS ix_allocation_invoice ON allocation(company_id,invoice_id,effective_date);
CREATE OR REPLACE FUNCTION immutable_financial() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Posted financial history is immutable; use a reversal'; END $$;
DO $$ BEGIN
IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname='invoice_immutable') THEN
CREATE TRIGGER invoice_immutable BEFORE UPDATE OR DELETE ON invoice FOR EACH ROW EXECUTE FUNCTION immutable_financial();
CREATE TRIGGER receipt_immutable BEFORE UPDATE OR DELETE ON receipt FOR EACH ROW EXECUTE FUNCTION immutable_financial();
CREATE TRIGGER allocation_immutable BEFORE UPDATE OR DELETE ON allocation FOR EACH ROW EXECUTE FUNCTION immutable_financial();
CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE ON audit_event FOR EACH ROW EXECUTE FUNCTION immutable_financial();
END IF; END $$;
-- Version 9: VAT working papers are separate from the immutable sales ledger.
CREATE TABLE IF NOT EXISTS vat_invoice_review(
 invoice_id text PRIMARY KEY REFERENCES invoice(id),company_id text NOT NULL REFERENCES company(id),
 tax_point date NOT NULL,supply_date date NOT NULL,treatment text NOT NULL,emirate text NOT NULL DEFAULT '',
 description text NOT NULL,reason text NOT NULL,customer_snapshot jsonb NOT NULL,supplier_snapshot jsonb NOT NULL,
 revision integer NOT NULL DEFAULT 1,reviewed_by text NOT NULL,reviewed_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS vat_return(
 id text PRIMARY KEY,company_id text NOT NULL REFERENCES company(id),period_start date NOT NULL,period_end date NOT NULL,
 due_date date NOT NULL,deadline_reference text NOT NULL DEFAULT '',status text NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Reviewed','Filed')),
 entries jsonb NOT NULL DEFAULT '[]',review_reference text NOT NULL DEFAULT '',version integer NOT NULL DEFAULT 1,
 snapshot jsonb,source_hash text NOT NULL DEFAULT '',reviewed_by text,reviewed_at timestamptz,
 filing_date date,filing_reference text NOT NULL DEFAULT '',filing_evidence text NOT NULL DEFAULT '',filed_by text,
 created_at timestamptz NOT NULL DEFAULT now(),CHECK(period_start<=period_end),UNIQUE(company_id,period_start,period_end));
CREATE INDEX IF NOT EXISTS vat_invoice_period ON vat_invoice_review(company_id,tax_point);
INSERT INTO migration(version) VALUES(9) ON CONFLICT DO NOTHING;
CREATE UNIQUE INDEX IF NOT EXISTS ux_allocation_company ON allocation(company_id,id,customer_id);
CREATE TABLE IF NOT EXISTS financial_correction(
 id text PRIMARY KEY, company_id text NOT NULL,customer_id text NOT NULL,
 kind text NOT NULL CHECK(kind IN ('Credit note','Write-off','Refund','Receipt reversal','Allocation reversal')),
 invoice_id text,receipt_id text,allocation_id text,
 reference text NOT NULL,effective_date date NOT NULL,amount numeric(18,2) NOT NULL CHECK(amount>0),
 net numeric(18,2) NOT NULL DEFAULT 0,vat numeric(18,2) NOT NULL DEFAULT 0,
 reason text NOT NULL,actor text NOT NULL REFERENCES app_user(id),idempotency_key text NOT NULL,request_hash text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(company_id,idempotency_key),UNIQUE(company_id,reference),
 FOREIGN KEY(company_id,customer_id) REFERENCES customer(company_id,id),
 FOREIGN KEY(company_id,invoice_id,customer_id) REFERENCES invoice(company_id,id,customer_id),
 FOREIGN KEY(company_id,receipt_id,customer_id) REFERENCES receipt(company_id,id,customer_id),
 FOREIGN KEY(company_id,allocation_id,customer_id) REFERENCES allocation(company_id,id,customer_id),
 CHECK((kind IN ('Credit note','Write-off') AND invoice_id IS NOT NULL AND receipt_id IS NULL AND allocation_id IS NULL) OR (kind IN ('Refund','Receipt reversal') AND receipt_id IS NOT NULL AND invoice_id IS NULL AND allocation_id IS NULL) OR (kind='Allocation reversal' AND allocation_id IS NOT NULL AND receipt_id IS NOT NULL AND invoice_id IS NOT NULL)),
 CHECK((kind='Credit note' AND net>=0 AND vat>=0 AND net+vat=amount) OR (kind<>'Credit note' AND net=0 AND vat=0))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_receipt_reversal ON financial_correction(receipt_id) WHERE kind='Receipt reversal';
CREATE UNIQUE INDEX IF NOT EXISTS ux_allocation_reversal ON financial_correction(allocation_id) WHERE kind='Allocation reversal';
CREATE INDEX IF NOT EXISTS ix_correction_company_date ON financial_correction(company_id,effective_date);
DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_trigger WHERE tgname='correction_immutable') THEN CREATE TRIGGER correction_immutable BEFORE UPDATE OR DELETE ON financial_correction FOR EACH ROW EXECUTE FUNCTION immutable_financial(); END IF; END $$;
CREATE OR REPLACE VIEW sales_movement AS
 SELECT company_id,customer_id,project_id,issue_date AS date,category,net,vat,total FROM invoice
 UNION ALL SELECT f.company_id,f.customer_id,i.project_id,f.effective_date,i.category,-f.net,-f.vat,-f.amount FROM financial_correction f JOIN invoice i ON i.id=f.invoice_id WHERE f.kind='Credit note';
CREATE OR REPLACE VIEW cash_movement AS
 SELECT id,company_id,customer_id,receipt_date AS date,amount FROM receipt
 UNION ALL SELECT id,company_id,customer_id,effective_date,-amount FROM financial_correction WHERE kind IN ('Refund','Receipt reversal');
INSERT INTO migration(version) VALUES(4) ON CONFLICT DO NOTHING;
INSERT INTO migration(version) VALUES(1) ON CONFLICT DO NOTHING;
ALTER TABLE audit_event ADD COLUMN IF NOT EXISTS canonical_payload text;
INSERT INTO migration(version) VALUES(2) ON CONFLICT DO NOTHING;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS email text;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS email_verified boolean NOT NULL DEFAULT false;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS access_role text NOT NULL DEFAULT 'User' CHECK(access_role IN ('Administrator','Super user','User'));
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS account_status text NOT NULL DEFAULT 'Approved' CHECK(account_status IN ('Pending','Approved','Suspended'));
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS session_version integer NOT NULL DEFAULT 0;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS registered_at timestamptz NOT NULL DEFAULT now();
CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON app_user(lower(email)) WHERE email IS NOT NULL;
CREATE TABLE IF NOT EXISTS identity_token(id text PRIMARY KEY, user_id text NOT NULL REFERENCES app_user(id), purpose text NOT NULL CHECK(purpose IN ('verify','reset')), token_hash text NOT NULL UNIQUE, expires_at timestamptz NOT NULL, consumed_at timestamptz, created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS ix_identity_token_user ON identity_token(user_id,purpose,created_at);
CREATE TABLE IF NOT EXISTS identity_mail(id text PRIMARY KEY, company_id text NOT NULL REFERENCES company(id), user_id text NOT NULL REFERENCES app_user(id), encrypted_payload text NOT NULL, state text NOT NULL DEFAULT 'Pending', attempts integer NOT NULL DEFAULT 0, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), provider_reference text, error_code text);
DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM migration WHERE version=3) THEN
UPDATE app_user SET access_role=CASE WHEN role='System Administrator' THEN 'Administrator' WHEN role='Finance Administrator' THEN 'Super user' ELSE 'User' END,session_version=session_version+1;
INSERT INTO migration(version) VALUES(3);
END IF; END $$;

ALTER TABLE app_user ADD COLUMN IF NOT EXISTS username text;
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS work_areas jsonb NOT NULL DEFAULT '["*"]';
CREATE UNIQUE INDEX IF NOT EXISTS ux_user_username ON app_user(lower(username)) WHERE username IS NOT NULL;
CREATE TABLE IF NOT EXISTS first_admin_setup(company_id text PRIMARY KEY REFERENCES company(id),token_hash text NOT NULL,consumed_at timestamptz);
ALTER TABLE customer ADD COLUMN IF NOT EXISTS details jsonb NOT NULL DEFAULT '{}';
ALTER TABLE customer ADD COLUMN IF NOT EXISTS revision integer NOT NULL DEFAULT 0;
CREATE TABLE IF NOT EXISTS workbook_import(id text PRIMARY KEY,company_id text NOT NULL REFERENCES company(id),kind text NOT NULL,hash text NOT NULL,filename text NOT NULL,payload jsonb NOT NULL,errors jsonb NOT NULL,warnings jsonb NOT NULL,status text NOT NULL DEFAULT 'Preview',created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(company_id,kind,hash));
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS source_data jsonb NOT NULL DEFAULT '{}';
DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM migration WHERE version=6) THEN UPDATE app_user SET session_version=session_version+1; INSERT INTO migration(version) VALUES(6); END IF; END $$;

-- Version 7 uses existing JSON company profiles for accounting periods; existing values remain unchanged.
INSERT INTO migration(version) VALUES(7) ON CONFLICT DO NOTHING;

-- Imported historical projects may have no known contract fee. They cannot prepare
-- new certificates until a positive fee is reviewed and their status is Active.
DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM migration WHERE version=8) THEN
 ALTER TABLE project ADD COLUMN IF NOT EXISTS opening_assessments jsonb NOT NULL DEFAULT '[]';
 ALTER TABLE project ADD COLUMN IF NOT EXISTS opening_net numeric(18,2) NOT NULL DEFAULT 0;
 ALTER TABLE project ADD COLUMN IF NOT EXISTS opening_review_reference text NOT NULL DEFAULT '';
 ALTER TABLE project DROP CONSTRAINT IF EXISTS project_fee_check;
 ALTER TABLE project ADD CONSTRAINT project_fee_check CHECK(fee>0 OR (fee=0 AND status='Needs contract review'));
 UPDATE project p SET status='Needs contract review',version=version+1 WHERE p.status='Active' AND EXISTS(SELECT 1 FROM invoice i WHERE i.project_id=p.id AND i.source_data ? 'import_id');
 INSERT INTO migration(version) VALUES(8);
END IF; END $$;
