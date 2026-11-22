-- Run ONCE in a NEW, dedicated Supabase project, using its SQL Editor.
-- One firm per project. No demo clients or user accounts are created here.
begin;
create schema if not exists wl_private;
revoke all on schema wl_private from public, anon, authenticated;

create table wl_private.profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 name text not null check(length(name) between 1 and 150),
 role text not null default 'staff' check(role in ('staff','reviewer')),
 active boolean not null default false
);
create table wl_private.clients (
 id uuid primary key default gen_random_uuid(),
 name text not null check(length(name) between 1 and 200),
 active boolean not null default true,
 retainer_notes text not null default '' check(length(retainer_notes)<=3000)
);
create unique index wl_client_names on wl_private.clients(lower(name));
create table wl_private.entries (
 id uuid primary key default gen_random_uuid(),
 staff_id uuid not null references wl_private.profiles(id),
 client_id uuid not null references wl_private.clients(id),
 note text not null check(length(trim(note)) between 1 and 4000),
 category text not null default 'Other' check(length(category)<=100),
 status text not null check(status in ('In progress','Completed','Waiting')),
 minutes integer check(minutes between 0 and 1440),
 work_date date not null check(work_date between date '2000-01-01' and date '2100-12-31'),
 version integer not null default 1,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index wl_entry_staff on wl_private.entries(staff_id,work_date desc);
create index wl_entry_client on wl_private.entries(client_id);
create table wl_private.proposals (
 id uuid primary key default gen_random_uuid(),
 client_id uuid not null references wl_private.clients(id),
 status text not null default 'Draft' check(status in ('Draft','Issued','Cancelled')),
 invoice_number text, invoice_date date,
 created_at timestamptz not null default now(),
 created_by uuid not null references wl_private.profiles(id),
 check((status='Issued' and length(trim(invoice_number))>0 and invoice_date is not null) or (status<>'Issued' and invoice_number is null and invoice_date is null))
);
create unique index wl_invoice_unique on wl_private.proposals(lower(trim(invoice_number))) where status='Issued';
create table wl_private.reviews (
 entry_id uuid primary key references wl_private.entries(id),
 decision text not null default 'Pending' check(decision in ('Pending','Billable','Retainer','Complimentary','Ask staff')),
 stage text not null default 'Pending' check(stage in ('Pending','Clarification','Ready','Proposed','Billed','Closed')),
 amount numeric(12,2),
 reviewer_id uuid references wl_private.profiles(id),
 proposal_id uuid references wl_private.proposals(id),
 check((stage in ('Ready','Proposed','Billed') and decision='Billable' and amount>0 and amount<=9999999999.99) or (stage not in ('Ready','Proposed','Billed') and amount is null))
);
create table wl_private.messages (
 id uuid primary key default gen_random_uuid(),
 entry_id uuid not null references wl_private.entries(id),
 actor_id uuid not null references wl_private.profiles(id),
 body text not null check(length(trim(body)) between 1 and 2000),
 created_at timestamptz not null default now()
);
create table wl_private.proposal_items (
 proposal_id uuid not null references wl_private.proposals(id),
 entry_id uuid not null references wl_private.entries(id),
 description text not null,
 amount numeric(12,2) not null check(amount>0 and amount<=9999999999.99),
 primary key(proposal_id,entry_id)
);
create table wl_private.audit (
 id bigint generated always as identity primary key,
 actor_id uuid not null references wl_private.profiles(id),
 action text not null,
 details jsonb not null,
 created_at timestamptz not null default now()
);
create table wl_private.requests (
 actor_id uuid not null references wl_private.profiles(id),
 request_id uuid not null,
 result jsonb not null,
 primary key(actor_id,request_id)
);

alter table wl_private.profiles enable row level security;
alter table wl_private.clients enable row level security;
alter table wl_private.entries enable row level security;
alter table wl_private.reviews enable row level security;
alter table wl_private.messages enable row level security;
alter table wl_private.proposals enable row level security;
alter table wl_private.proposal_items enable row level security;
alter table wl_private.audit enable row level security;
alter table wl_private.requests enable row level security;
revoke all on all tables in schema wl_private from public, anon, authenticated;

create function wl_private.new_user() returns trigger language plpgsql security definer set search_path='' as $$
begin
 insert into wl_private.profiles(id,name) values(new.id,left(coalesce(nullif(new.raw_user_meta_data->>'name',''),split_part(new.email,'@',1),'Staff'),150));
 return new;
end $$;
revoke all on function wl_private.new_user() from public,anon,authenticated;
create trigger workledger_new_user after insert on auth.users for each row execute function wl_private.new_user();
insert into wl_private.profiles(id,name) select id,left(coalesce(nullif(raw_user_meta_data->>'name',''),split_part(email,'@',1),'Staff'),150) from auth.users on conflict do nothing;

-- Intentionally privileged boundary: caller identity and role are checked INSIDE
-- every function. No direct table privileges or service-role key are used by app.
create function public.wl_data() returns jsonb language plpgsql security definer set search_path='' as $$
declare u uuid:=auth.uid(); me wl_private.profiles; partner boolean;
begin
 select * into me from wl_private.profiles where id=u and active;
 if not found then raise exception 'Your account is not active. Ask the reviewer to activate it.'; end if;
 partner:=me.role='reviewer';
 return jsonb_build_object(
 'me',to_jsonb(me),
 'clients',coalesce((select jsonb_agg(case when partner then to_jsonb(c) else jsonb_build_object('id',c.id,'name',c.name,'active',c.active) end order by c.name) from wl_private.clients c),'[]'::jsonb),
 'people',coalesce((select jsonb_agg(to_jsonb(p) order by p.name) from wl_private.profiles p where partner or p.id=u),'[]'::jsonb),
 'entries',coalesce((select jsonb_agg(to_jsonb(e)||jsonb_build_object('review_status',coalesce(r.stage,'Pending')) order by e.work_date desc,e.created_at desc) from wl_private.entries e left join wl_private.reviews r on r.entry_id=e.id where partner or e.staff_id=u),'[]'::jsonb),
 'messages',coalesce((select jsonb_agg(to_jsonb(m) order by m.created_at) from wl_private.messages m join wl_private.entries e on e.id=m.entry_id where partner or e.staff_id=u),'[]'::jsonb),
 'reviews',case when partner then coalesce((select jsonb_agg(to_jsonb(r)) from wl_private.reviews r),'[]'::jsonb) else '[]'::jsonb end,
 'proposals',case when partner then coalesce((select jsonb_agg(to_jsonb(p) order by p.created_at desc) from wl_private.proposals p),'[]'::jsonb) else '[]'::jsonb end,
 'items',case when partner then coalesce((select jsonb_agg(to_jsonb(i)) from wl_private.proposal_items i),'[]'::jsonb) else '[]'::jsonb end,
 'audit',case when partner then coalesce((select jsonb_agg(to_jsonb(a)) from (select * from wl_private.audit order by id desc limit 200) a),'[]'::jsonb) else '[]'::jsonb end
 );
end $$;

create function public.wl_action(action text,payload jsonb,request_id uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare
 u uuid:=auth.uid(); me wl_private.profiles; e wl_private.entries; r wl_private.reviews;
 proposal wl_private.proposals; entry_id uuid; client_id uuid; ids uuid[]; item uuid; result jsonb;
 decision text; amount numeric(12,2); stage text; old_review jsonb;
begin
 select * into me from wl_private.profiles where id=u and active;
 if not found then raise exception 'Your account is not active.'; end if;
 if request_id is null then raise exception 'Request ID required.'; end if;
 perform pg_advisory_xact_lock(hashtextextended(u::text||request_id::text,0));
 select q.result into result from wl_private.requests q where q.actor_id=u and q.request_id=wl_action.request_id;
 if found then return result; end if;
 result:=jsonb_build_object('ok',true);

 if action='work' then
  client_id:=(payload->>'client_id')::uuid;
  if not exists(select 1 from wl_private.clients c where c.id=client_id and c.active) then raise exception 'Choose an active client.'; end if;
  if nullif(payload->>'id','') is null then
   insert into wl_private.entries(staff_id,client_id,note,category,status,minutes,work_date)
   values(u,client_id,trim(payload->>'note'),coalesce(nullif(payload->>'category',''),'Other'),payload->>'status',nullif(payload->>'minutes','')::integer,(payload->>'work_date')::date) returning id into entry_id;
   insert into wl_private.reviews(entry_id) values(entry_id);
  else
   entry_id:=(payload->>'id')::uuid;
   select * into e from wl_private.entries where id=entry_id for update;
   if not found or e.staff_id<>u then raise exception 'You can edit only your own entries.'; end if;
   if e.version<>(payload->>'version')::integer or payload->>'version' is null then raise exception 'This entry changed. Refresh and try again.'; end if;
   select * into r from wl_private.reviews where reviews.entry_id=wl_action.entry_id for update;
   if r.stage in ('Ready','Proposed','Billed') then raise exception 'This entry is approved for billing and locked.'; end if;
   update wl_private.entries set client_id=wl_action.client_id,note=trim(payload->>'note'),category=coalesce(nullif(payload->>'category',''),'Other'),status=payload->>'status',minutes=nullif(payload->>'minutes','')::integer,work_date=(payload->>'work_date')::date,version=version+1,updated_at=now() where id=entry_id;
   if r.stage='Closed' then update wl_private.reviews set decision='Pending',stage='Pending',amount=null,reviewer_id=null where reviews.entry_id=wl_action.entry_id; end if;
  end if;
  result:=result||jsonb_build_object('entry_id',entry_id);

 elsif action in ('reply','review') then
  entry_id:=(payload->>'entry_id')::uuid;
  select * into e from wl_private.entries where id=entry_id for update;
  if not found then raise exception 'Entry not found.'; end if;
  if e.version<>(payload->>'version')::integer or payload->>'version' is null then raise exception 'This entry changed. Refresh and try again.'; end if;
  select * into r from wl_private.reviews where reviews.entry_id=wl_action.entry_id for update;
  if action='reply' then
   if e.staff_id<>u or r.stage<>'Clarification' then raise exception 'No clarification is awaiting your response.'; end if;
   insert into wl_private.messages(entry_id,actor_id,body) values(entry_id,u,trim(payload->>'message'));
   update wl_private.reviews set stage='Pending',decision='Pending' where reviews.entry_id=wl_action.entry_id;
  else
   if me.role<>'reviewer' then raise exception 'Only the reviewer can decide billing.'; end if;
   if r.stage in ('Proposed','Billed') then raise exception 'Cancel the draft proposal first; issued work cannot be changed.'; end if;
   old_review:=to_jsonb(r);
   decision:=payload->>'decision'; amount:=null;
   if decision='Billable' then
    if e.status<>'Completed' then raise exception 'Complete the work before approving it for billing.'; end if;
    amount:=(payload->>'amount')::numeric(12,2);
    if amount is null or amount<=0 or amount>9999999999.99 then raise exception 'Enter a valid fee greater than zero.'; end if;
    stage:='Ready';
   elsif decision in ('Retainer','Complimentary') then stage:='Closed';
   elsif decision='Ask staff' then
    stage:='Clarification';
    insert into wl_private.messages(entry_id,actor_id,body) values(entry_id,u,trim(payload->>'message'));
   elsif decision='Pending' then stage:='Pending';
   else raise exception 'Choose a billing treatment.';
   end if;
   update wl_private.reviews set decision=wl_action.decision,stage=wl_action.stage,amount=wl_action.amount,reviewer_id=u where reviews.entry_id=wl_action.entry_id;
  end if;
  update wl_private.entries set version=version+1,updated_at=now() where id=entry_id;

 elsif me.role<>'reviewer' then raise exception 'Only the reviewer can do this.';

 elsif action='client' then
  if nullif(payload->>'id','') is null then
   insert into wl_private.clients(name,retainer_notes) values(trim(payload->>'name'),coalesce(payload->>'retainer_notes',''));
  else
   update wl_private.clients set name=trim(payload->>'name'),retainer_notes=coalesce(payload->>'retainer_notes',''),active=(payload->>'active')::boolean where id=(payload->>'id')::uuid;
   if not found then raise exception 'Client not found.'; end if;
  end if;

 elsif action='staff' then
  if (payload->>'id')::uuid=u then raise exception 'Your own reviewer account cannot be changed here.'; end if;
  update wl_private.profiles set name=trim(payload->>'name'),active=(payload->>'active')::boolean where id=(payload->>'id')::uuid and role='staff';
  if not found then raise exception 'Staff account not found.'; end if;

 elsif action='proposal' then
  select array_agg(distinct value::uuid order by value::uuid) into ids from jsonb_array_elements_text(payload->'ids');
  if ids is null or cardinality(ids)>200 then raise exception 'Select between 1 and 200 entries.'; end if;
  -- Lock source entries in one order to prevent duplicate inclusion and deadlocks.
  perform 1 from wl_private.entries where id=any(ids) order by id for update;
  foreach item in array ids loop
   select * into e from wl_private.entries where id=item;
   if not found then raise exception 'Entry not found.'; end if;
   select * into r from wl_private.reviews where reviews.entry_id=item for update;
   if not found or r.stage<>'Ready' or e.status<>'Completed' then raise exception 'An entry is no longer ready. Refresh and try again.'; end if;
   if client_id is null then client_id:=e.client_id; end if;
   if client_id<>e.client_id then raise exception 'Select work for one client only.'; end if;
  end loop;
  insert into wl_private.proposals(client_id,created_by) values(client_id,u) returning * into proposal;
  insert into wl_private.proposal_items(proposal_id,entry_id,description,amount) select proposal.id,entry_row.id,entry_row.note,review_row.amount from wl_private.entries entry_row join wl_private.reviews review_row on review_row.entry_id=entry_row.id where entry_row.id=any(ids);
  update wl_private.reviews set stage='Proposed',proposal_id=proposal.id where reviews.entry_id=any(ids);
  update wl_private.entries set version=version+1,updated_at=now() where id=any(ids);
  result:=result||jsonb_build_object('proposal_id',proposal.id);

 elsif action in ('issue','cancel_proposal') then
  select * into proposal from wl_private.proposals where id=(payload->>'id')::uuid for update;
  if not found or proposal.status<>'Draft' then raise exception 'Only a draft proposal can be changed.'; end if;
  if action='issue' then
   if length(trim(coalesce(payload->>'invoice_number',''))) not between 1 and 100 then raise exception 'Enter the issued invoice reference.'; end if;
   if nullif(payload->>'invoice_date','') is null then raise exception 'Enter the invoice date.'; end if;
   update wl_private.proposals set status='Issued',invoice_number=trim(payload->>'invoice_number'),invoice_date=(payload->>'invoice_date')::date where id=proposal.id;
   update wl_private.reviews set stage='Billed' where proposal_id=proposal.id;
  else
   update wl_private.proposals set status='Cancelled' where id=proposal.id;
   update wl_private.reviews set stage='Ready',proposal_id=null where proposal_id=proposal.id;
  end if;
 else raise exception 'Unknown action.';
 end if;

 insert into wl_private.audit(actor_id,action,details) values(u,action,jsonb_build_object('input',payload,'previous_review',old_review,'result',result));
 insert into wl_private.requests(actor_id,request_id,result) values(u,request_id,result);
 return result;
end $$;

revoke all on function public.wl_data() from public,anon;
revoke all on function public.wl_action(text,jsonb,uuid) from public,anon;
grant execute on function public.wl_data() to authenticated;
grant execute on function public.wl_action(text,jsonb,uuid) to authenticated;
commit;
