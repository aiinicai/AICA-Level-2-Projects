create extension if not exists pgcrypto;

-- 1. PROFILES
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  mobile text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
grant select, update on public.profiles to authenticated;
grant all on public.profiles to service_role;

-- 2. FIRMS & MEMBERS
create table if not exists public.firms (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  frn text, gstin text, pan text, address text, city text, state text, pincode text,
  email text, phone text, logo_url text, partner_name text, membership_no text,
  plan text not null default 'trial' check (plan in ('trial','free','pro','enterprise')),
  trial_ends_at timestamptz not null default (now() + interval '14 days'),
  status text not null default 'active' check (status in ('active','disabled')),
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  updated_by uuid,
  updated_at timestamptz not null default now()
);
grant select, update on public.firms to authenticated;
grant all on public.firms to service_role;

create table if not exists public.firm_members (
  firm_id uuid not null references public.firms(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text not null default 'staff' check (role in ('owner','partner','staff','viewer')),
  created_at timestamptz not null default now(),
  primary key (firm_id, user_id)
);
create index if not exists firm_members_user_idx on public.firm_members(user_id);
grant select, update, delete on public.firm_members to authenticated;
grant all on public.firm_members to service_role;

create table if not exists public.invitations (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  email text not null,
  role text not null default 'staff' check (role in ('partner','staff','viewer')),
  status text not null default 'pending' check (status in ('pending','accepted','revoked')),
  invited_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  accepted_at timestamptz
);
create unique index if not exists invitations_pending_uniq
  on public.invitations(firm_id, lower(email)) where status = 'pending';
grant select, insert, update, delete on public.invitations to authenticated;
grant all on public.invitations to service_role;

-- 3. CLIENTS & ENGAGEMENTS
create table if not exists public.clients (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  name text not null,
  pan text,
  gstins text[] not null default '{}',
  status text not null default 'Individual'
    check (status in ('Individual','HUF','Firm','LLP','Company','AOP','BOI','Trust','Other')),
  address text, contact_person text, email text, mobile text, notes text,
  archived boolean not null default false,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  updated_by uuid,
  updated_at timestamptz not null default now()
);
create index if not exists clients_firm_idx on public.clients(firm_id);
grant select, insert, update, delete on public.clients to authenticated;
grant all on public.clients to service_role;

create table if not exists public.engagements (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  client_id uuid not null references public.clients(id) on delete cascade,
  assessment_year text not null,
  pl_total_expenditure numeric(18,2),
  status text not null default 'draft' check (status in ('draft','in_review','final')),
  assigned_to uuid references public.profiles(id) on delete set null,
  reviewed_by uuid references public.profiles(id) on delete set null,
  reviewed_at timestamptz,
  udin text,
  locked boolean not null default false,
  unlock_reason text,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  updated_by uuid,
  updated_at timestamptz not null default now(),
  unique (client_id, assessment_year)
);
create index if not exists engagements_firm_idx on public.engagements(firm_id);
grant select, insert, update, delete on public.engagements to authenticated;
grant all on public.engagements to service_role;

-- 4. UPLOADS, MAPPINGS, PARTY MASTER, EXPENSE ROWS
create table if not exists public.uploads (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  module text not null default 'clause44',
  file_name text not null,
  storage_path text,
  file_size bigint,
  source text not null default 'manual' check (source in ('manual','email','client_link')),
  software_detected text,
  row_count integer not null default 0,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  updated_by uuid,
  updated_at timestamptz not null default now()
);
grant select, insert, update, delete on public.uploads to authenticated;
grant all on public.uploads to service_role;

create table if not exists public.column_mappings (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  client_id uuid references public.clients(id) on delete cascade,
  name text not null,
  mapping jsonb not null,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  updated_by uuid,
  updated_at timestamptz not null default now()
);
grant select, insert, update, delete on public.column_mappings to authenticated;
grant all on public.column_mappings to service_role;

create table if not exists public.party_master (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  client_id uuid not null references public.clients(id) on delete cascade,
  party_name text not null,
  normalized_name text not null,
  gstin text,
  pan text,
  is_composition boolean not null default false,
  is_exempt boolean not null default false,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  updated_by uuid,
  updated_at timestamptz not null default now(),
  unique (client_id, normalized_name)
);
grant select, insert, update, delete on public.party_master to authenticated;
grant all on public.party_master to service_role;

create table if not exists public.expense_rows (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  upload_id uuid references public.uploads(id) on delete cascade,
  row_no integer,
  party_name text not null,
  normalized_name text not null,
  gstin text,
  effective_gstin text,
  gstin_status text not null default 'blank' check (gstin_status in ('valid','invalid','blank')),
  expense_head text,
  amount numeric(18,2) not null default 0,
  txn_date date,
  nature text check (nature in ('goods','services')),
  category text not null default 'unregistered'
    check (category in ('exempt','composition','other_registered','unregistered')),
  category_override text
    check (category_override in ('exempt','composition','other_registered','unregistered')),
  include boolean not null default true,
  remark text,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  updated_by uuid,
  updated_at timestamptz not null default now()
);
create index if not exists expense_rows_eng_idx on public.expense_rows(engagement_id, row_no);
create index if not exists expense_rows_party_idx on public.expense_rows(engagement_id, normalized_name);
create index if not exists expense_rows_head_idx on public.expense_rows(engagement_id, expense_head);
grant select, insert, update, delete on public.expense_rows to authenticated;
grant all on public.expense_rows to service_role;

-- 5. HISTORY, COMMENTS, ACTIVITY, LOGIN HISTORY
create table if not exists public.row_history (
  id bigint generated always as identity primary key,
  firm_id uuid not null references public.firms(id) on delete cascade,
  table_name text not null,
  record_id uuid not null,
  field text not null,
  old_value text,
  new_value text,
  changed_by uuid default auth.uid(),
  changed_at timestamptz not null default now()
);
create index if not exists row_history_record_idx on public.row_history(record_id);
grant select on public.row_history to authenticated;
grant all on public.row_history to service_role;

create table if not exists public.comments (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  row_id uuid references public.expense_rows(id) on delete cascade,
  body text not null,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now(),
  updated_by uuid,
  updated_at timestamptz not null default now()
);
grant select, insert, update, delete on public.comments to authenticated;
grant all on public.comments to service_role;

create table if not exists public.activity_log (
  id bigint generated always as identity primary key,
  firm_id uuid not null references public.firms(id) on delete cascade,
  user_id uuid default auth.uid(),
  action text not null,
  entity text,
  entity_id uuid,
  details jsonb,
  created_at timestamptz not null default now()
);
create index if not exists activity_log_firm_idx on public.activity_log(firm_id, created_at desc);
grant select, insert on public.activity_log to authenticated;
grant all on public.activity_log to service_role;

create table if not exists public.login_history (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid() references public.profiles(id) on delete cascade,
  device text,
  created_at timestamptz not null default now()
);
grant select, insert on public.login_history to authenticated;
grant all on public.login_history to service_role;

-- HELPER FUNCTIONS
create or replace function public.is_firm_member(p_firm uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.firm_members where firm_id = p_firm and user_id = auth.uid());
$$;

create or replace function public.firm_role(p_firm uuid)
returns text language sql stable security definer set search_path = public as $$
  select role from public.firm_members where firm_id = p_firm and user_id = auth.uid();
$$;

create or replace function public.can_edit_firm(p_firm uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce(public.firm_role(p_firm) in ('owner','partner','staff'), false);
$$;

create or replace function public.is_firm_admin(p_firm uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce(public.firm_role(p_firm) in ('owner','partner'), false);
$$;

create or replace function public.shares_firm_with(p_user uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.firm_members a
    join public.firm_members b on a.firm_id = b.firm_id
    where a.user_id = auth.uid() and b.user_id = p_user
  );
$$;

create or replace function public.engagement_editable(p_eng uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.engagements e
    where e.id = p_eng and not e.locked and public.can_edit_firm(e.firm_id)
  );
$$;

create or replace function public.gstin_is_valid(p text)
returns boolean language plpgsql immutable set search_path = public as $$
declare
  chars constant text := '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  g text := upper(trim(coalesce(p,'')));
  total int := 0;
  v int; prod int; i int; chk int;
begin
  if g !~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$' then
    return false;
  end if;
  for i in 1..14 loop
    v := strpos(chars, substr(g, i, 1)) - 1;
    prod := v * (case when i % 2 = 0 then 2 else 1 end);
    total := total + (prod / 36) + (prod % 36);
  end loop;
  chk := (36 - (total % 36)) % 36;
  return substr(chars, chk + 1, 1) = substr(g, 15, 1);
end;
$$;

-- TRIGGERS
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', split_part(new.email,'@',1)))
  on conflict (id) do nothing;
  return new;
end;
$$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

create or replace function public.set_audit_fields()
returns trigger language plpgsql set search_path = public as $$
begin
  if tg_op = 'INSERT' then
    new.created_by := coalesce(new.created_by, auth.uid());
    new.updated_by := coalesce(new.updated_by, auth.uid());
    new.updated_at := now();
  else
    new.created_by := old.created_by;
    new.created_at := old.created_at;
    new.updated_by := auth.uid();
    new.updated_at := now();
  end if;
  return new;
end;
$$;

do $$
declare t text;
begin
  foreach t in array array['firms','clients','engagements','uploads','column_mappings','party_master','expense_rows','comments']
  loop
    execute format('drop trigger if exists trg_audit on public.%I', t);
    execute format('create trigger trg_audit before insert or update on public.%I for each row execute function public.set_audit_fields()', t);
  end loop;
end $$;

create or replace function public.touch_profile()
returns trigger language plpgsql set search_path = public as $$
begin new.updated_at := now(); new.id := old.id; return new; end;
$$;
drop trigger if exists trg_touch_profile on public.profiles;
create trigger trg_touch_profile before update on public.profiles
  for each row execute function public.touch_profile();

create or replace function public.derive_firm_id()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if tg_table_name = 'engagements' or tg_table_name = 'party_master' then
    select firm_id into new.firm_id from public.clients where id = new.client_id;
  elsif tg_table_name in ('uploads','expense_rows','comments') then
    select firm_id into new.firm_id from public.engagements where id = new.engagement_id;
  elsif tg_table_name = 'column_mappings' and new.client_id is not null then
    select firm_id into new.firm_id from public.clients where id = new.client_id;
  end if;
  if new.firm_id is null then
    raise exception 'Parent record not found';
  end if;
  return new;
end;
$$;

do $$
declare t text;
begin
  foreach t in array array['engagements','party_master','uploads','expense_rows','comments','column_mappings']
  loop
    execute format('drop trigger if exists trg_derive_firm on public.%I', t);
    execute format('create trigger trg_derive_firm before insert on public.%I for each row execute function public.derive_firm_id()', t);
  end loop;
end $$;

create or replace function public.log_expense_row_changes()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  f text;
  o text;
  n text;
begin
  foreach f in array array['party_name','gstin','expense_head','amount','txn_date','nature','include','remark','category_override']
  loop
    execute format('select ($1).%I::text, ($2).%I::text', f, f) into o, n using old, new;
    if o is distinct from n then
      insert into public.row_history (firm_id, table_name, record_id, field, old_value, new_value, changed_by)
      values (new.firm_id, 'expense_rows', new.id, f, o, n, auth.uid());
    end if;
  end loop;
  return new;
end;
$$;
drop trigger if exists trg_expense_history on public.expense_rows;
create trigger trg_expense_history after update on public.expense_rows
  for each row execute function public.log_expense_row_changes();

create or replace function public.guard_engagement_lock()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  if old.locked and new.locked
     and (to_jsonb(new) - 'udin' - 'updated_at' - 'updated_by') is distinct from
         (to_jsonb(old) - 'udin' - 'updated_at' - 'updated_by') then
    raise exception 'This assessment year is locked (Final). Unlock it first.';
  end if;
  if old.locked and not new.locked and not public.is_firm_admin(old.firm_id) then
    raise exception 'Only Owner/Partner can unlock.';
  end if;
  if not old.locked and new.locked and not public.is_firm_admin(old.firm_id) then
    raise exception 'Only Owner/Partner can mark Final.';
  end if;
  new.firm_id := old.firm_id;
  new.client_id := old.client_id;
  return new;
end;
$$;
drop trigger if exists trg_guard_lock on public.engagements;
create trigger trg_guard_lock before update on public.engagements
  for each row execute function public.guard_engagement_lock();

-- RPC FUNCTIONS
create or replace function public.create_firm(
  p_name text, p_frn text default null, p_gstin text default null, p_address text default null,
  p_city text default null, p_state text default null, p_email text default null, p_phone text default null,
  p_partner_name text default null, p_membership_no text default null)
returns uuid language plpgsql security definer set search_path = public as $$
declare v_id uuid;
begin
  if auth.uid() is null then raise exception 'Not signed in'; end if;
  if coalesce(trim(p_name),'') = '' then raise exception 'Firm name is required'; end if;
  insert into public.firms (name, frn, gstin, address, city, state, email, phone, partner_name, membership_no, created_by)
  values (trim(p_name), p_frn, upper(p_gstin), p_address, p_city, p_state, p_email, p_phone, p_partner_name, p_membership_no, auth.uid())
  returning id into v_id;
  insert into public.firm_members (firm_id, user_id, role) values (v_id, auth.uid(), 'owner');
  insert into public.activity_log (firm_id, user_id, action, entity, entity_id)
  values (v_id, auth.uid(), 'firm.created', 'firm', v_id);
  return v_id;
end;
$$;

create or replace function public.accept_my_invitations()
returns integer language plpgsql security definer set search_path = public as $$
declare
  v_email text := lower(coalesce(auth.jwt()->>'email',''));
  v_count int := 0;
  r record;
begin
  if auth.uid() is null or v_email = '' then return 0; end if;
  for r in select * from public.invitations where lower(email) = v_email and status = 'pending' loop
    insert into public.firm_members (firm_id, user_id, role)
    values (r.firm_id, auth.uid(), r.role)
    on conflict (firm_id, user_id) do nothing;
    update public.invitations set status = 'accepted', accepted_at = now() where id = r.id;
    insert into public.activity_log (firm_id, user_id, action, entity, entity_id, details)
    values (r.firm_id, auth.uid(), 'member.joined', 'invitation', r.id, jsonb_build_object('role', r.role));
    v_count := v_count + 1;
  end loop;
  return v_count;
end;
$$;

create or replace function public.firm_team(p_firm uuid)
returns table (user_id uuid, role text, full_name text, email text, joined_at timestamptz)
language sql stable security definer set search_path = public as $$
  select m.user_id, m.role, p.full_name, p.email, m.created_at
  from public.firm_members m left join public.profiles p on p.id = m.user_id
  where m.firm_id = p_firm and public.is_firm_member(p_firm)
  order by case m.role when 'owner' then 0 when 'partner' then 1 when 'staff' then 2 else 3 end, p.full_name;
$$;

create or replace function public.upsert_parties(p_client uuid, p_parties jsonb)
returns integer language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  insert into public.party_master (client_id, firm_id, party_name, normalized_name, gstin)
  select p_client, c.firm_id, x->>'party_name', x->>'normalized_name', nullif(upper(trim(x->>'gstin')),'')
  from jsonb_array_elements(p_parties) x
  cross join public.clients c
  where c.id = p_client
  on conflict (client_id, normalized_name) do update
    set gstin = coalesce(nullif(party_master.gstin,''), excluded.gstin);
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

create or replace function public.reclassify_engagement(p_eng uuid)
returns integer language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if not public.engagement_editable(p_eng) then
    return 0;
  end if;
  with x as (
    select e.id,
      coalesce(nullif(upper(trim(e.gstin)),''), nullif(upper(trim(pm.gstin)),'')) as eg,
      coalesce(pm.is_exempt,false) as ex,
      coalesce(pm.is_composition,false) as co
    from public.expense_rows e
    join public.engagements en on en.id = e.engagement_id
    left join public.party_master pm on pm.client_id = en.client_id and pm.normalized_name = e.normalized_name
    where e.engagement_id = p_eng
  ), y as (
    select id, eg,
      case when eg is null then 'blank' when public.gstin_is_valid(eg) then 'valid' else 'invalid' end as st,
      ex, co
    from x
  )
  update public.expense_rows e set
    effective_gstin = y.eg,
    gstin_status = y.st,
    category = coalesce(e.category_override,
      case when y.st <> 'valid' then 'unregistered'
           when y.ex then 'exempt'
           when y.co then 'composition'
           else 'other_registered' end)
  from y
  where e.id = y.id
    and (e.effective_gstin is distinct from y.eg or e.gstin_status is distinct from y.st
         or e.category is distinct from coalesce(e.category_override,
            case when y.st <> 'valid' then 'unregistered' when y.ex then 'exempt'
                 when y.co then 'composition' else 'other_registered' end));
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

create or replace function public.clause44_summary(p_eng uuid)
returns table (
  total_uploaded numeric, excluded numeric, reported_total numeric,
  exempt numeric, composition numeric, other_registered numeric,
  registered_total numeric, unregistered numeric,
  row_count bigint, excluded_count bigint, invalid_gstin_count bigint,
  negative_count bigint, party_count bigint)
language sql stable security invoker set search_path = public as $$
  select
    coalesce(sum(amount),0),
    coalesce(sum(amount) filter (where not include),0),
    coalesce(sum(amount) filter (where include),0),
    coalesce(sum(amount) filter (where include and category='exempt'),0),
    coalesce(sum(amount) filter (where include and category='composition'),0),
    coalesce(sum(amount) filter (where include and category='other_registered'),0),
    coalesce(sum(amount) filter (where include and category in ('exempt','composition','other_registered')),0),
    coalesce(sum(amount) filter (where include and category='unregistered'),0),
    count(*),
    count(*) filter (where not include),
    count(*) filter (where gstin_status='invalid'),
    count(*) filter (where amount < 0),
    count(distinct normalized_name)
  from public.expense_rows where engagement_id = p_eng;
$$;

create or replace function public.clause44_party_summary(p_eng uuid)
returns table (normalized_name text, party_name text, gstin text, gstin_status text, category text,
               included_amount numeric, excluded_amount numeric, row_count bigint, gstin_variants bigint)
language sql stable security invoker set search_path = public as $$
  select e.normalized_name,
    min(e.party_name),
    max(e.effective_gstin),
    max(e.gstin_status),
    case when count(distinct e.category) filter (where e.include) > 1 then 'mixed'
         else max(e.category) filter (where e.include) end,
    coalesce(sum(e.amount) filter (where e.include),0),
    coalesce(sum(e.amount) filter (where not e.include),0),
    count(*),
    count(distinct e.effective_gstin)
  from public.expense_rows e
  where e.engagement_id = p_eng
  group by e.normalized_name
  order by 6 desc;
$$;

create or replace function public.clause44_head_summary(p_eng uuid)
returns table (expense_head text, total numeric, included_amount numeric, excluded_amount numeric,
               row_count bigint, excluded_count bigint)
language sql stable security invoker set search_path = public as $$
  select coalesce(expense_head,'(blank)'),
    coalesce(sum(amount),0),
    coalesce(sum(amount) filter (where include),0),
    coalesce(sum(amount) filter (where not include),0),
    count(*),
    count(*) filter (where not include)
  from public.expense_rows where engagement_id = p_eng
  group by coalesce(expense_head,'(blank)')
  order by 2 desc;
$$;

create or replace function public.clause44_exceptions(p_eng uuid)
returns table (kind text, normalized_name text, party_name text, detail text, amount numeric, row_count bigint)
language sql stable security invoker set search_path = public as $$
  select 'invalid_gstin', normalized_name, min(party_name), max(effective_gstin), sum(amount), count(*)
    from public.expense_rows where engagement_id = p_eng and gstin_status = 'invalid'
    group by normalized_name, effective_gstin
  union all
  select 'multiple_gstins', normalized_name, min(party_name), string_agg(distinct effective_gstin, ', '), sum(amount), count(*)
    from public.expense_rows where engagement_id = p_eng and effective_gstin is not null
    group by normalized_name having count(distinct effective_gstin) > 1
  union all
  select 'gstin_partly_missing', normalized_name, min(party_name), 'GSTIN present on some rows only', sum(amount), count(*)
    from public.expense_rows where engagement_id = p_eng
    group by normalized_name
    having count(*) filter (where nullif(trim(gstin),'') is null) > 0
       and count(*) filter (where nullif(trim(gstin),'') is not null) > 0
  union all
  select 'duplicate', normalized_name, min(party_name),
         coalesce(to_char(txn_date,'DD-MM-YYYY'),'no date') || ' / ' || coalesce(expense_head,''), sum(amount), count(*)
    from public.expense_rows where engagement_id = p_eng
    group by normalized_name, txn_date, expense_head, amount having count(*) > 1
  union all
  select 'negative_amount', normalized_name, party_name, coalesce(expense_head,''), amount, 1
    from public.expense_rows where engagement_id = p_eng and amount < 0;
$$;

create or replace function public.merge_parties(p_client uuid, p_from text, p_into text)
returns integer language plpgsql security invoker set search_path = public as $$
declare v_count int; v_into public.party_master;
begin
  select * into v_into from public.party_master where client_id = p_client and normalized_name = p_into;
  if not found then raise exception 'Target party not found'; end if;
  if exists (select 1 from public.expense_rows e join public.engagements en on en.id = e.engagement_id
             where en.client_id = p_client and en.locked and e.normalized_name = p_from) then
    raise exception 'This party is used in a locked (Final) year. Unlock that year first.';
  end if;
  update public.expense_rows e set normalized_name = p_into
    from public.engagements en
    where en.id = e.engagement_id and en.client_id = p_client and not en.locked and e.normalized_name = p_from;
  get diagnostics v_count = row_count;
  update public.party_master t set gstin = coalesce(nullif(t.gstin,''), f.gstin)
    from public.party_master f
    where t.id = v_into.id and f.client_id = p_client and f.normalized_name = p_from;
  delete from public.party_master where client_id = p_client and normalized_name = p_from;
  return v_count;
end;
$$;

create or replace function public.firm_dashboard(p_firm uuid)
returns jsonb language sql stable security invoker set search_path = public as $$
  select jsonb_build_object(
    'clients', (select count(*) from public.clients where firm_id = p_firm and not archived),
    'engagements', (select count(*) from public.engagements where firm_id = p_firm),
    'draft', (select count(*) from public.engagements where firm_id = p_firm and status = 'draft'),
    'in_review', (select count(*) from public.engagements where firm_id = p_firm and status = 'in_review'),
    'final', (select count(*) from public.engagements where firm_id = p_firm and status = 'final'),
    'my_open', (select count(*) from public.engagements where firm_id = p_firm and assigned_to = auth.uid() and status <> 'final'),
    'members', (select count(*) from public.firm_members where firm_id = p_firm)
  );
$$;

-- ROW LEVEL SECURITY
alter table public.profiles enable row level security;
alter table public.firms enable row level security;
alter table public.firm_members enable row level security;
alter table public.invitations enable row level security;
alter table public.clients enable row level security;
alter table public.engagements enable row level security;
alter table public.uploads enable row level security;
alter table public.column_mappings enable row level security;
alter table public.party_master enable row level security;
alter table public.expense_rows enable row level security;
alter table public.row_history enable row level security;
alter table public.comments enable row level security;
alter table public.activity_log enable row level security;
alter table public.login_history enable row level security;

create policy profiles_select on public.profiles for select to authenticated
  using (id = auth.uid() or public.shares_firm_with(id));
create policy profiles_update on public.profiles for update to authenticated
  using (id = auth.uid()) with check (id = auth.uid());

create policy firms_select on public.firms for select to authenticated using (public.is_firm_member(id));
create policy firms_update on public.firms for update to authenticated
  using (public.is_firm_admin(id)) with check (public.is_firm_admin(id));

create policy members_select on public.firm_members for select to authenticated using (public.is_firm_member(firm_id));
create policy members_update on public.firm_members for update to authenticated
  using (public.firm_role(firm_id) = 'owner' and user_id <> auth.uid())
  with check (public.firm_role(firm_id) = 'owner' and role <> 'owner');
create policy members_delete on public.firm_members for delete to authenticated
  using ((public.firm_role(firm_id) = 'owner' and role <> 'owner') or (user_id = auth.uid() and role <> 'owner'));

create policy inv_select on public.invitations for select to authenticated using (public.is_firm_admin(firm_id));
create policy inv_insert on public.invitations for insert to authenticated with check (public.is_firm_admin(firm_id));
create policy inv_update on public.invitations for update to authenticated
  using (public.is_firm_admin(firm_id)) with check (public.is_firm_admin(firm_id));
create policy inv_delete on public.invitations for delete to authenticated using (public.is_firm_admin(firm_id));

do $$
declare t text;
begin
  foreach t in array array['clients','column_mappings','party_master','comments']
  loop
    execute format('create policy %1$s_select on public.%1$I for select to authenticated using (public.is_firm_member(firm_id))', t);
    execute format('create policy %1$s_insert on public.%1$I for insert to authenticated with check (public.can_edit_firm(firm_id))', t);
    execute format('create policy %1$s_update on public.%1$I for update to authenticated using (public.can_edit_firm(firm_id)) with check (public.can_edit_firm(firm_id))', t);
    execute format('create policy %1$s_delete on public.%1$I for delete to authenticated using (public.can_edit_firm(firm_id))', t);
  end loop;
end $$;

create policy eng_select on public.engagements for select to authenticated using (public.is_firm_member(firm_id));
create policy eng_insert on public.engagements for insert to authenticated with check (public.can_edit_firm(firm_id));
create policy eng_update on public.engagements for update to authenticated
  using (public.can_edit_firm(firm_id)) with check (public.can_edit_firm(firm_id));
create policy eng_delete on public.engagements for delete to authenticated
  using (public.is_firm_admin(firm_id) and not locked);

create policy uploads_select on public.uploads for select to authenticated using (public.is_firm_member(firm_id));
create policy uploads_insert on public.uploads for insert to authenticated with check (public.engagement_editable(engagement_id));
create policy uploads_update on public.uploads for update to authenticated
  using (public.engagement_editable(engagement_id)) with check (public.engagement_editable(engagement_id));
create policy uploads_delete on public.uploads for delete to authenticated using (public.engagement_editable(engagement_id));

create policy rows_select on public.expense_rows for select to authenticated using (public.is_firm_member(firm_id));
create policy rows_insert on public.expense_rows for insert to authenticated with check (public.engagement_editable(engagement_id));
create policy rows_update on public.expense_rows for update to authenticated
  using (public.engagement_editable(engagement_id)) with check (public.engagement_editable(engagement_id));
create policy rows_delete on public.expense_rows for delete to authenticated using (public.engagement_editable(engagement_id));

create policy history_select on public.row_history for select to authenticated using (public.is_firm_member(firm_id));

create policy activity_select on public.activity_log for select to authenticated using (public.is_firm_member(firm_id));
create policy activity_insert on public.activity_log for insert to authenticated
  with check (public.is_firm_member(firm_id) and user_id = auth.uid());

create policy login_select on public.login_history for select to authenticated using (user_id = auth.uid());
create policy login_insert on public.login_history for insert to authenticated with check (user_id = auth.uid());

-- STORAGE: private bucket 'uploads', files stored under <firm_id>/...
create policy "uploads_read" on storage.objects for select to authenticated
  using (bucket_id = 'uploads' and public.is_firm_member(((storage.foldername(name))[1])::uuid));
create policy "uploads_write" on storage.objects for insert to authenticated
  with check (bucket_id = 'uploads' and public.can_edit_firm(((storage.foldername(name))[1])::uuid));
create policy "uploads_delete" on storage.objects for delete to authenticated
  using (bucket_id = 'uploads' and public.can_edit_firm(((storage.foldername(name))[1])::uuid));

-- FUNCTION GRANTS (signed-in users only)
revoke execute on function public.is_firm_member(uuid) from public, anon;
revoke execute on function public.firm_role(uuid) from public, anon;
revoke execute on function public.can_edit_firm(uuid) from public, anon;
revoke execute on function public.is_firm_admin(uuid) from public, anon;
revoke execute on function public.shares_firm_with(uuid) from public, anon;
revoke execute on function public.engagement_editable(uuid) from public, anon;
revoke execute on function public.create_firm(text,text,text,text,text,text,text,text,text,text) from public, anon;
revoke execute on function public.accept_my_invitations() from public, anon;
revoke execute on function public.firm_team(uuid) from public, anon;
revoke execute on function public.upsert_parties(uuid, jsonb) from public, anon;
revoke execute on function public.reclassify_engagement(uuid) from public, anon;
revoke execute on function public.clause44_summary(uuid) from public, anon;
revoke execute on function public.clause44_party_summary(uuid) from public, anon;
revoke execute on function public.clause44_head_summary(uuid) from public, anon;
revoke execute on function public.clause44_exceptions(uuid) from public, anon;
revoke execute on function public.merge_parties(uuid, text, text) from public, anon;
revoke execute on function public.firm_dashboard(uuid) from public, anon;
revoke execute on function public.handle_new_user() from public, anon, authenticated;

grant execute on function public.is_firm_member(uuid) to authenticated;
grant execute on function public.firm_role(uuid) to authenticated;
grant execute on function public.can_edit_firm(uuid) to authenticated;
grant execute on function public.is_firm_admin(uuid) to authenticated;
grant execute on function public.shares_firm_with(uuid) to authenticated;
grant execute on function public.engagement_editable(uuid) to authenticated;
grant execute on function public.create_firm(text,text,text,text,text,text,text,text,text,text) to authenticated;
grant execute on function public.accept_my_invitations() to authenticated;
grant execute on function public.firm_team(uuid) to authenticated;
grant execute on function public.upsert_parties(uuid, jsonb) to authenticated;
grant execute on function public.reclassify_engagement(uuid) to authenticated;
grant execute on function public.clause44_summary(uuid) to authenticated;
grant execute on function public.clause44_party_summary(uuid) to authenticated;
grant execute on function public.clause44_head_summary(uuid) to authenticated;
grant execute on function public.clause44_exceptions(uuid) to authenticated;
grant execute on function public.merge_parties(uuid, text, text) to authenticated;
grant execute on function public.firm_dashboard(uuid) to authenticated;
grant execute on function public.gstin_is_valid(text) to authenticated;