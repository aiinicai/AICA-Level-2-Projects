-- Client upload link (7 days, no login) – schema change to be applied by Lovable.
-- The firm makes a link for one assessment year and module; the client opens /u/<token> and uploads
-- files without an account. Files go to the private 'uploads' bucket under
--   <firm_id>/<engagement_id>/client/<token>/<file>
-- and appear in the year's uploads with source 'client_link'. Links stop working when they expire,
-- are revoked, or the year is made Final.

create table if not exists public.upload_links (
  id uuid primary key default gen_random_uuid(),
  firm_id uuid not null references public.firms(id) on delete cascade,
  engagement_id uuid not null references public.engagements(id) on delete cascade,
  module text not null default 'clause31' check (module in ('clause31','clause44')),
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

-- Is this token a live link for this firm / year? (used by the storage policy)
create or replace function public.client_link_ok(p_token text, p_firm text, p_eng text)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.upload_links l join public.engagements e on e.id = l.engagement_id
    where l.token = p_token and l.firm_id::text = p_firm and l.engagement_id::text = p_eng
      and l.revoked_at is null and l.expires_at > now() and not e.locked
  );
$$;

-- What the client's page shows (null when the link is not valid)
create or replace function public.client_link_info(p_token text)
returns jsonb language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'firm', f.name, 'client', c.name, 'ay', e.assessment_year, 'module', l.module, 'message', l.message,
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
  values (l.engagement_id, l.module, left(coalesce(nullif(trim(p_file_name), ''), 'file'), 200), p_path, p_size, 'client_link');
end;
$$;

revoke execute on function public.client_link_ok(text, text, text) from public;
revoke execute on function public.client_link_info(text) from public;
revoke execute on function public.client_link_register(text, text, text, bigint) from public;
grant execute on function public.client_link_ok(text, text, text) to anon, authenticated;
grant execute on function public.client_link_info(text) to anon, authenticated;
grant execute on function public.client_link_register(text, text, text, bigint) to anon, authenticated;

-- The client (not signed in) may only add new files under a live link's folder
create policy "uploads_client_link_write" on storage.objects for insert to anon, authenticated
  with check (bucket_id = 'uploads'
              and (storage.foldername(name))[3] = 'client'
              and public.client_link_ok((storage.foldername(name))[4], (storage.foldername(name))[1], (storage.foldername(name))[2]));
