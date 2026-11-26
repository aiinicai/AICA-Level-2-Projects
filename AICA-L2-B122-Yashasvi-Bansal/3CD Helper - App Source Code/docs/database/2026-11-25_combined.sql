-- 3CD Helper – database changes of 25 Nov 2026, in one go (to be applied by Lovable as one new migration).
--   1. Clause 31: a new kind of loan entry, 'tds' (TDS deducted on interest – reduces the balance, not reported)
--   2. Client upload link (7 days, no login): upload_links table, its rules and functions, storage rule
--   3. The link can be for all clauses, and can send the client's Tally data to the firm's Google Drive
--   4. firms.settings: a place for firm-level settings (e.g. the address of the firm's Google Drive script)

-- 1 ------------------------------------------------------------------------------------------------
-- remove the existing check on loan_txns.kind, whatever its name
do $$
declare r record;
begin
  for r in select con.conname from pg_constraint con
           join pg_class t on t.oid = con.conrelid join pg_namespace n on n.oid = t.relnamespace
           where n.nspname = 'public' and t.relname = 'loan_txns' and con.contype = 'c'
             and pg_get_constraintdef(con.oid) ilike '%kind%'
  loop
    execute format('alter table public.loan_txns drop constraint %I', r.conname);
  end loop;
end $$;
alter table public.loan_txns add constraint loan_txns_kind_check
  check (kind in ('taken','repaid','specified_taken','specified_repaid','given','repayment_received','interest','tds'));

-- 4 ------------------------------------------------------------------------------------------------
alter table public.firms add column if not exists settings jsonb not null default '{}'::jsonb;

-- 2 + 3 --------------------------------------------------------------------------------------------
-- The firm makes a link for one assessment year; the client opens /u/<token> without an account and either
--   • uploads files (they go to the private 'uploads' bucket under <firm_id>/<engagement_id>/client/<token>/<file>
--     and appear in the year's uploads with source 'client_link'), or
--   • (deliver_to = 'drive') sends the Tally data to the firm's Google Drive through the firm's own Apps Script.
-- Links stop working when they expire, are revoked, or the year is made Final.
create table if not exists public.upload_links (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  module text not null default 'all' check (module in ('all','clause31','clause44')),
  deliver_to text not null default 'app' check (deliver_to in ('app','drive')),
  token text not null unique default replace(gen_random_uuid()::text || gen_random_uuid()::text, '-', ''),
  message text,
  expires_at timestamptz not null default now() + interval '7 days',
  revoked_at timestamptz,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now()
);
create index if not exists upload_links_eng_idx on public.upload_links(engagement_id);

alter table public.upload_links enable row level security;
grant select, insert, update, delete on public.upload_links to authenticated;
grant all on public.upload_links to service_role;

drop policy if exists upload_links_select on public.upload_links;
drop policy if exists upload_links_insert on public.upload_links;
drop policy if exists upload_links_update on public.upload_links;
drop policy if exists upload_links_delete on public.upload_links;
create policy upload_links_select on public.upload_links for select to authenticated
  using (public.is_firm_member(firm_id));
create policy upload_links_insert on public.upload_links for insert to authenticated
  with check (public.engagement_editable(engagement_id)
              and exists (select 1 from public.engagements e where e.id = engagement_id and e.firm_id = upload_links.firm_id)
              and expires_at <= now() + interval '30 days');
create policy upload_links_update on public.upload_links for update to authenticated
  using (public.can_edit_firm(firm_id)) with check (public.can_edit_firm(firm_id));
create policy upload_links_delete on public.upload_links for delete to authenticated
  using (public.can_edit_firm(firm_id));

-- Is this token a live link for this firm / year? (used by the storage rule)
create or replace function public.client_link_ok(p_token text, p_firm text, p_eng text)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.upload_links l join public.engagements e on e.id = l.engagement_id
    where l.token = p_token and l.firm_id::text = p_firm and l.engagement_id::text = p_eng
      and l.revoked_at is null and l.expires_at > now() and not e.locked
  );
$$;

-- What the client's page (and the firm's Drive script) may know about a live link (null when not valid)
create or replace function public.client_link_info(p_token text)
returns jsonb language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'firm', f.name, 'client', c.name, 'ay', e.assessment_year, 'module', l.module, 'message', l.message,
    'deliver_to', l.deliver_to, 'drive_url', case when l.deliver_to = 'drive' then f.settings->>'drive_url' end,
    'expires_at', l.expires_at, 'firm_id', l.firm_id, 'engagement_id', l.engagement_id,
    'files', coalesce((
      select jsonb_agg(jsonb_build_object('name', u.file_name, 'size', u.file_size, 'at', u.created_at) order by u.created_at)
      from public.uploads u
      where u.engagement_id = l.engagement_id and u.source = 'client_link'
        and u.storage_path like l.firm_id::text || '/' || l.engagement_id::text || '/client/' || l.token || '/%'), '[]'::jsonb))
  from public.upload_links l
  join public.engagements e on e.id = l.engagement_id
  join public.clients c on c.id = e.client_id
  join public.firms f on f.id = l.firm_id
  where l.token = p_token and l.revoked_at is null and l.expires_at > now() and not e.locked;
$$;

-- Record a file the client has uploaded through the link
create or replace function public.client_link_register(p_token text, p_path text, p_file_name text, p_size bigint)
returns void language plpgsql security definer set search_path = public as $$
declare l public.upload_links%rowtype;
begin
  select ul.* into l from public.upload_links ul join public.engagements e on e.id = ul.engagement_id
   where ul.token = p_token and ul.revoked_at is null and ul.expires_at > now() and not e.locked;
  if not found then raise exception 'This upload link has expired or is no longer valid'; end if;
  if p_path not like l.firm_id::text || '/' || l.engagement_id::text || '/client/' || l.token || '/%' or p_path like '%..%' then
    raise exception 'Invalid file path';
  end if;
  if not exists (select 1 from storage.objects o where o.bucket_id = 'uploads' and o.name = p_path) then
    raise exception 'File not found';
  end if;
  if (select count(*) from public.uploads u where u.engagement_id = l.engagement_id and u.storage_path like l.firm_id::text || '/' || l.engagement_id::text || '/client/' || l.token || '/%') >= 50 then
    raise exception 'Too many files on this link';
  end if;
  insert into public.uploads (engagement_id, module, file_name, storage_path, file_size, source)
  values (l.engagement_id, case when l.module = 'clause31' then 'clause31' else 'clause44' end,
          left(coalesce(nullif(trim(p_file_name), ''), 'file'), 200), p_path, p_size, 'client_link');
end;
$$;

revoke execute on function public.client_link_ok(text, text, text) from public;
revoke execute on function public.client_link_info(text) from public;
revoke execute on function public.client_link_register(text, text, text, bigint) from public;
grant execute on function public.client_link_ok(text, text, text) to anon, authenticated;
grant execute on function public.client_link_info(text) to anon, authenticated;
grant execute on function public.client_link_register(text, text, text, bigint) to anon, authenticated;

-- The client (not signed in) may only add new files under a live link's folder
drop policy if exists "uploads_client_link_write" on storage.objects;
create policy "uploads_client_link_write" on storage.objects for insert to anon, authenticated
  with check (bucket_id = 'uploads'
              and (storage.foldername(name))[3] = 'client'
              and public.client_link_ok((storage.foldername(name))[4], (storage.foldername(name))[1], (storage.foldername(name))[2]));

-- 5 ------------------------------------------------------------------------------------------------
-- Sign in with a username instead of the email. The sign-in system stays email-based: the app asks
-- email_for_login() for the email of a username, then signs in with that email and the password.
alter table public.profiles add column if not exists username text;
alter table public.profiles drop constraint if exists profiles_username_format;
alter table public.profiles add constraint profiles_username_format
  check (username is null or username ~ '^[a-z0-9][a-z0-9._-]{2,29}$');
create unique index if not exists profiles_username_key on public.profiles (lower(username));

-- The email to sign in with (a username is looked up; an email is returned as given; null when unknown)
create or replace function public.email_for_login(p_login text)
returns text language sql stable security definer set search_path = public, auth as $$
  select case
    when position('@' in coalesce(p_login, '')) > 0 then trim(p_login)
    else (select u.email from public.profiles p join auth.users u on u.id = p.id
          where lower(p.username) = lower(trim(p_login)) limit 1)
  end;
$$;
revoke execute on function public.email_for_login(text) from public;
grant execute on function public.email_for_login(text) to anon, authenticated;

-- Set (or clear) one's own username; checks the format and that nobody else has it
create or replace function public.set_my_username(p_username text)
returns text language plpgsql security definer set search_path = public as $$
declare v text := lower(nullif(trim(p_username), ''));
begin
  if auth.uid() is null then raise exception 'Sign in first'; end if;
  if v is not null and v !~ '^[a-z0-9][a-z0-9._-]{2,29}$' then
    raise exception 'Username: 3 to 30 letters, numbers, dot, dash or underscore, starting with a letter or number';
  end if;
  if v is not null and exists (select 1 from public.profiles where lower(username) = v and id <> auth.uid()) then
    raise exception 'This username is already taken';
  end if;
  update public.profiles set username = v where id = auth.uid();
  return v;
end;
$$;
revoke execute on function public.set_my_username(text) from public;
grant execute on function public.set_my_username(text) to authenticated;
