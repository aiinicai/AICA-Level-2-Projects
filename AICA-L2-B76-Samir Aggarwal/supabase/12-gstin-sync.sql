-- =====================================================================
--  FILE 12 : Bridge clients.gstin into gst_registrations
--
--  The client master has always carried a GSTIN field (Add/Edit Client and
--  the bulk import both fill it), but the compliance engine reads the
--  gst_registrations table — so a client whose GSTIN was entered the normal
--  way still showed "no active GSTIN". This backfills every existing client
--  and keeps the two in sync from now on: setting or changing a client's
--  GSTIN automatically creates the matching registration. Multi-GSTIN
--  clients still add their additional registrations in the Compliance sheet.
--
--  Run AFTER 10 and 11. Safe to re-run.
-- =====================================================================

-- State named from the GSTIN's two-digit prefix, so the sheet reads sensibly.
create or replace function public.gstin_state(_gstin text)
returns text
language sql immutable
as $$
  select case left(_gstin, 2)
    when '01' then 'Jammu & Kashmir'  when '02' then 'Himachal Pradesh'
    when '03' then 'Punjab'           when '04' then 'Chandigarh'
    when '05' then 'Uttarakhand'      when '06' then 'Haryana'
    when '07' then 'Delhi'            when '08' then 'Rajasthan'
    when '09' then 'Uttar Pradesh'    when '10' then 'Bihar'
    when '19' then 'West Bengal'      when '21' then 'Odisha'
    when '22' then 'Chhattisgarh'     when '23' then 'Madhya Pradesh'
    when '24' then 'Gujarat'          when '27' then 'Maharashtra'
    when '29' then 'Karnataka'        when '30' then 'Goa'
    when '32' then 'Kerala'           when '33' then 'Tamil Nadu'
    when '36' then 'Telangana'        when '37' then 'Andhra Pradesh'
    else null end;
$$;

-- One-time backfill for every client whose GSTIN was entered the normal way.
insert into public.gst_registrations (client_id, gstin, state, is_active)
select c.id, upper(btrim(c.gstin)), public.gstin_state(upper(btrim(c.gstin))), true
from public.clients c
where c.gstin is not null
  and btrim(c.gstin) <> ''
  and upper(btrim(c.gstin)) ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$'
on conflict (client_id, gstin) do nothing;

-- Keep them in sync: setting or changing clients.gstin creates the matching
-- registration if it is not already there. Nothing is deleted on change —
-- an old GSTIN may still have live filings against it; deactivate it from
-- the Compliance sheet when it is genuinely retired.
create or replace function public.sync_client_gstin()
returns trigger
language plpgsql security definer set search_path = public
as $$
declare
  v_gstin text := upper(btrim(coalesce(new.gstin, '')));
begin
  if v_gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$' then
    insert into public.gst_registrations (client_id, gstin, state, is_active, created_by)
    values (new.id, v_gstin, public.gstin_state(v_gstin), true, auth.uid())
    on conflict (client_id, gstin) do update set is_active = true;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_sync_client_gstin on public.clients;
create trigger trg_sync_client_gstin
  after insert or update of gstin on public.clients
  for each row execute function public.sync_client_gstin();

-- =====================================================================
--  Verify:
--    select c.name, g.gstin, g.state
--    from public.gst_registrations g join public.clients c on c.id = g.client_id
--    order by c.name;
--  Every client with a GSTIN on its record should appear once.
-- =====================================================================
