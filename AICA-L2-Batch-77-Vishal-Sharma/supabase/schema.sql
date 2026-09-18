-- ============================================================================
-- Delegation Sheet -> Web App — Database Schema
-- Ecoo Global Advisors
--
-- Run this once in the Supabase SQL Editor (Dashboard > SQL Editor > New query)
-- on a fresh project. Safe to re-run top to bottom on an empty database.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. PROFILES  (one row per auth.users, extends it with app-specific fields)
-- ----------------------------------------------------------------------------
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  full_name text not null default '',
  is_admin boolean not null default false,
  can_create_and_assign boolean not null default false,
  -- Gates real use of the app (Part 2 — "no self-signup"). Google OAuth
  -- signup is left open at the Supabase Auth level (so a brand-new person
  -- can actually complete a sign-in and land on a "waiting for approval"
  -- screen, rather than a bare provider error) but everything past that
  -- screen requires this flag. Admin-invited accounts are marked approved
  -- immediately by handle_new_user() below — inviting IS the approval;
  -- this flag exists for the *other* path, someone who was never invited
  -- but still completed a Google sign-in on their own.
  is_approved boolean not null default false,
  created_at timestamptz not null default now()
);

-- Auto-create a profile row whenever a new auth user appears — either an
-- Admin invite (Supabase creates the auth.users row up front) or a Google
-- OAuth sign-in from someone who was never invited (self-signup is open at
-- the Auth layer; this is what the is_approved gate above is for).
-- New accounts start as a plain, non-assigning User; an Admin promotes them
-- afterwards from the Manage Users screen.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name, is_approved)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', ''),
    coalesce((new.raw_user_meta_data ->> 'invited')::boolean, false)
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ----------------------------------------------------------------------------
-- 2. CLIENTS  (simple managed lookup list — not tied to any assignee mapping,
--    per the decision that the old Client<->TeamLead<->TeamMember pairing is
--    not enforced in the new app)
-- ----------------------------------------------------------------------------
create table public.clients (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  created_at timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 3. TASKS
-- ----------------------------------------------------------------------------
create table public.tasks (
  id uuid primary key default gen_random_uuid(),
  task_number text not null unique,               -- e.g. ECOO260211004

  client_id uuid not null references public.clients(id),
  description text not null,

  assignor_id uuid not null references public.profiles(id),
  primary_assignee_id uuid not null references public.profiles(id),
  secondary_assignee_id uuid references public.profiles(id),

  urgency text not null check (urgency in ('Low', 'Medium', 'High')),
  status text not null default 'Open'
    check (status in ('Open', 'In Process', 'Pending at Client', 'Pending at Department', 'Hold', 'Closed')),

  start_date date,
  planned_date date not null,                     -- IMMUTABLE original commitment — never updated after insert

  closed_at timestamptz,
  closed_by uuid references public.profiles(id),

  -- A single, overwritable, Admin-only field — visible to everyone who can
  -- see the task, but only an Admin may set/change it. Distinct from
  -- task_comments (the timestamped, append-only thread everyone can post
  -- to); this is the old spreadsheet's single "Admin's remark" field,
  -- reintroduced deliberately alongside the thread, not instead of it.
  admin_remark text,

  created_at timestamptz not null default now()
);

create index tasks_primary_assignee_idx on public.tasks(primary_assignee_id);
create index tasks_secondary_assignee_idx on public.tasks(secondary_assignee_id);
create index tasks_assignor_idx on public.tasks(assignor_id);
create index tasks_status_idx on public.tasks(status);

-- ---- Task Number generator: ECOO + YYMMDD + 3-digit daily sequence --------
create table public.task_number_counters (
  day date primary key,
  last_seq int not null default 0
);

create function public.generate_task_number()
returns text
language plpgsql
as $$
declare
  today date := (now() at time zone 'Asia/Kolkata')::date;
  seq int;
begin
  insert into public.task_number_counters (day, last_seq)
  values (today, 1)
  on conflict (day) do update set last_seq = public.task_number_counters.last_seq + 1
  returning last_seq into seq;

  return 'ECOO' || to_char(today, 'YYMMDD') || lpad(seq::text, 3, '0');
end;
$$;

create function public.set_task_number()
returns trigger
language plpgsql
as $$
begin
  if new.task_number is null or new.task_number = '' then
    new.task_number := public.generate_task_number();
  end if;
  return new;
end;
$$;

create trigger before_insert_task_number
  before insert on public.tasks
  for each row execute function public.set_task_number();

-- ----------------------------------------------------------------------------
-- 4. TASK REVISIONS  (due-date change requests — unlimited history, 2-step
--    request/approve workflow, with the "impacts performance" flag)
-- ----------------------------------------------------------------------------
create table public.task_revisions (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references public.tasks(id) on delete cascade,

  requested_by uuid not null references public.profiles(id),
  proposed_date date not null,
  reason text not null default '',

  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  decided_by uuid references public.profiles(id),
  decided_at timestamptz,
  decision_note text,
  impacts_performance boolean,        -- only ever set at the moment of approval

  created_at timestamptz not null default now()
);

create index task_revisions_task_idx on public.task_revisions(task_id);

-- ----------------------------------------------------------------------------
-- 5. TASK COMMENTS  (timestamped thread — replaces the old overwritable
--    "Admin's remark" / "Team Remarks" fields; entries are never edited)
-- ----------------------------------------------------------------------------
create table public.task_comments (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references public.tasks(id) on delete cascade,
  author_id uuid not null references public.profiles(id),
  body text not null,
  created_at timestamptz not null default now()
);

create index task_comments_task_idx on public.task_comments(task_id);

-- ----------------------------------------------------------------------------
-- 6. HELPER — current user's profile lookup, used throughout RLS policies
-- ----------------------------------------------------------------------------
create function public.my_profile()
returns public.profiles
language sql
stable
security definer
set search_path = public
as $$
  select * from public.profiles where id = auth.uid();
$$;

create function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce((select is_admin from public.profiles where id = auth.uid()), false);
$$;

create function public.is_approved()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce((select is_approved from public.profiles where id = auth.uid()), false);
$$;

-- ----------------------------------------------------------------------------
-- 7. ROW LEVEL SECURITY
-- ----------------------------------------------------------------------------
alter table public.profiles enable row level security;
alter table public.clients enable row level security;
alter table public.tasks enable row level security;
alter table public.task_revisions enable row level security;
alter table public.task_comments enable row level security;

-- profiles: an approved user can read everyone's name (needed for assignee
-- pickers); an unapproved user can only read their own row (just enough to
-- render the "waiting for approval" screen, nothing else). Only Admin can
-- edit admin/permission/approval flags; a person may edit their own name.
create policy profiles_select_all on public.profiles
  for select using (auth.uid() is not null and (public.is_approved() or id = auth.uid()));

create policy profiles_update_admin on public.profiles
  for update using (public.is_admin());

create policy profiles_update_self_name on public.profiles
  for update using (id = auth.uid())
  with check (id = auth.uid());
  -- Note: this alone would let a user flip their own is_admin/can_create_and_assign/
  -- is_approved flags. The trigger below closes that gap.

create function public.protect_profile_privilege_columns()
returns trigger
language plpgsql
as $$
begin
  -- One named account is a permanent Admin, enforced at the database level
  -- so it survives even direct SQL, not just the API.
  if old.email = 'ecooglobal@gmail.com' and new.is_admin is distinct from true then
    raise exception 'This account is a permanent Admin and cannot be demoted';
  end if;

  if not public.is_admin() then
    if new.is_admin is distinct from old.is_admin
       or new.can_create_and_assign is distinct from old.can_create_and_assign
       or new.is_approved is distinct from old.is_approved then
      raise exception 'Only an Admin can change permission flags';
    end if;
  end if;
  return new;
end;
$$;

create trigger protect_profile_privilege_columns
  before update on public.profiles
  for each row execute function public.protect_profile_privilege_columns();

-- Admin manages accounts; there's no public self-signup (Part 2), so profile
-- rows are only ever created by the handle_new_user() trigger above.

-- clients: only an approved user can read the client list; Admin or any
-- "can assign" User can add new clients; only Admin can rename/remove.
create policy clients_select_all on public.clients
  for select using (public.is_approved());

create policy clients_insert on public.clients
  for insert with check (
    public.is_admin()
    or (public.is_approved() and (select can_create_and_assign from public.profiles where id = auth.uid()))
  );

create policy clients_update_admin on public.clients
  for update using (public.is_admin());

create policy clients_delete_admin on public.clients
  for delete using (public.is_admin());

-- tasks: visible to Admin (all) or anyone approved who is the assignor,
-- primary, or secondary assignee on that row (Part 1 visibility rule).
create policy tasks_select on public.tasks
  for select using (
    public.is_admin()
    or (
      public.is_approved()
      and (
        assignor_id = auth.uid()
        or primary_assignee_id = auth.uid()
        or secondary_assignee_id = auth.uid()
      )
    )
  );

-- insert: Admin always; a plain profile only if approved and
-- can_create_and_assign, and only as themselves (can't post a task under
-- someone else's name).
create policy tasks_insert on public.tasks
  for insert with check (
    public.is_admin()
    or (
      public.is_approved()
      and (select can_create_and_assign from public.profiles where id = auth.uid())
      and assignor_id = auth.uid()
    )
  );

-- update: broad row-level gate here; the trigger below enforces the finer
-- column-by-column rules (close-lock, reopen-admin-only, immutable planned
-- date, who may delegate a Secondary assignee).
create policy tasks_update on public.tasks
  for update using (
    public.is_admin()
    or primary_assignee_id = auth.uid()
    or secondary_assignee_id = auth.uid()
  );

-- delete: Admin only, per Part 1 (Users can never delete, only close).
create policy tasks_delete_admin on public.tasks
  for delete using (public.is_admin());

create function public.enforce_task_update_rules()
returns trigger
language plpgsql
as $$
declare
  acting_is_admin boolean := public.is_admin();
  acting_can_assign boolean := coalesce((select can_create_and_assign from public.profiles where id = auth.uid()), false);
  is_primary boolean := old.primary_assignee_id = auth.uid();
  is_secondary boolean := old.secondary_assignee_id = auth.uid();
begin
  -- Planned Date is immutable for everyone, including Admin — the only
  -- sanctioned way to move a due date is an approved task_revisions row.
  if new.planned_date is distinct from old.planned_date then
    raise exception 'Planned Date cannot be edited directly — submit a revision instead';
  end if;

  if acting_is_admin then
    return new; -- Admin is a superset: no further restriction.
  end if;

  -- Closed rows are frozen for everyone except Admin (Part 1).
  if old.status = 'Closed' then
    raise exception 'This task is closed and can only be reopened by an Admin';
  end if;

  -- Non-admins may only ever flip status and, if permitted, delegate a
  -- Secondary assignee. Every other field is locked post-creation.
  if new.client_id is distinct from old.client_id
     or new.description is distinct from old.description
     or new.assignor_id is distinct from old.assignor_id
     or new.primary_assignee_id is distinct from old.primary_assignee_id
     or new.urgency is distinct from old.urgency
     or new.start_date is distinct from old.start_date
     or new.task_number is distinct from old.task_number
     or new.admin_remark is distinct from old.admin_remark then
    raise exception 'Only an Admin can edit this field';
  end if;

  -- Delegating a Secondary assignee: only the current Primary assignee, and
  -- only if they carry the can_create_and_assign permission (Part 1 — task-
  -- scoped authority, not a fixed roster).
  if new.secondary_assignee_id is distinct from old.secondary_assignee_id then
    if not (is_primary and acting_can_assign) then
      raise exception 'Only the Primary assignee (with assign permission) can delegate this task';
    end if;
  end if;

  -- Closing a task: Users can close only tasks assigned directly to them.
  if new.status = 'Closed' and old.status is distinct from 'Closed' then
    if not (is_primary or is_secondary) then
      raise exception 'You can only close a task assigned to you';
    end if;
    new.closed_at := now();
    new.closed_by := auth.uid();
  end if;

  return new;
end;
$$;

create trigger enforce_task_update_rules
  before update on public.tasks
  for each row execute function public.enforce_task_update_rules();

-- task_revisions: visible to anyone who can see the parent task.
create policy task_revisions_select on public.task_revisions
  for select using (
    exists (
      select 1 from public.tasks t
      where t.id = task_revisions.task_id
        and (
          public.is_admin()
          or (
            public.is_approved()
            and (
              t.assignor_id = auth.uid()
              or t.primary_assignee_id = auth.uid()
              or t.secondary_assignee_id = auth.uid()
            )
          )
        )
    )
  );

-- insert: the assignee (primary or secondary) requests a revision on their
-- own task (Part 3 — "assignee requests it").
create policy task_revisions_insert on public.task_revisions
  for insert with check (
    requested_by = auth.uid()
    and exists (
      select 1 from public.tasks t
      where t.id = task_revisions.task_id
        and (t.primary_assignee_id = auth.uid() or t.secondary_assignee_id = auth.uid())
        and t.status <> 'Closed'
    )
  );

-- update (approve/reject): only Admin, or the task's Primary assignee if they
-- carry can_create_and_assign (the delegator/manager role for that task).
-- A Primary assignee with can_create_and_assign may decide revisions on
-- their task, but never their own request — that would let the same
-- person both request and approve a due-date change, defeating the
-- 2-step oversight the whole revision workflow exists for. Admin is
-- exempt (superset role, same pattern as enforce_task_update_rules).
create policy task_revisions_update on public.task_revisions
  for update using (
    public.is_admin()
    or (
      task_revisions.requested_by <> auth.uid()
      and exists (
        select 1 from public.tasks t
        where t.id = task_revisions.task_id
          and t.primary_assignee_id = auth.uid()
          and (select can_create_and_assign from public.profiles where id = auth.uid())
      )
    )
  );

create function public.enforce_revision_decision_rules()
returns trigger
language plpgsql
as $$
begin
  if old.status <> 'pending' then
    raise exception 'This revision request has already been decided';
  end if;
  if new.status not in ('approved', 'rejected') then
    raise exception 'A revision can only move to approved or rejected';
  end if;
  if new.status = 'approved' and new.impacts_performance is null then
    raise exception 'Set whether this revision impacts performance before approving';
  end if;
  new.decided_by := auth.uid();
  new.decided_at := now();
  return new;
end;
$$;

create trigger enforce_revision_decision_rules
  before update on public.task_revisions
  for each row execute function public.enforce_revision_decision_rules();

-- task_comments: visible to anyone who can see the parent task; anyone who
-- can see the task can add a comment. No update/delete policies are defined
-- on purpose — entries are permanent once posted.
create policy task_comments_select on public.task_comments
  for select using (
    exists (
      select 1 from public.tasks t
      where t.id = task_comments.task_id
        and (
          public.is_admin()
          or (
            public.is_approved()
            and (
              t.assignor_id = auth.uid()
              or t.primary_assignee_id = auth.uid()
              or t.secondary_assignee_id = auth.uid()
            )
          )
        )
    )
  );

create policy task_comments_insert on public.task_comments
  for insert with check (
    author_id = auth.uid()
    and exists (
      select 1 from public.tasks t
      where t.id = task_comments.task_id
        and (
          public.is_admin()
          or (
            public.is_approved()
            and (
              t.assignor_id = auth.uid()
              or t.primary_assignee_id = auth.uid()
              or t.secondary_assignee_id = auth.uid()
            )
          )
        )
    )
  );

-- ----------------------------------------------------------------------------
-- 8. CONVENIENCE VIEW — effective due date (Planned Date, or the latest
--    approved revision if one exists), used by the Part 5 dashboard buckets.
--    Also surfaces the latest approved revision date on its own (distinct
--    from the coalesced effective_due_date, so the UI can show Planned Date
--    and Revised Date as two separate columns) and the latest remark.
-- ----------------------------------------------------------------------------
create view public.tasks_with_due_date as
select
  t.*,
  coalesce(
    (
      select r.proposed_date
      from public.task_revisions r
      where r.task_id = t.id and r.status = 'approved'
      order by r.decided_at desc
      limit 1
    ),
    t.planned_date
  ) as effective_due_date,
  (
    select r.proposed_date
    from public.task_revisions r
    where r.task_id = t.id and r.status = 'approved'
    order by r.decided_at desc
    limit 1
  ) as latest_revised_date,
  (
    select c.body
    from public.task_comments c
    where c.task_id = t.id
    order by c.created_at desc
    limit 1
  ) as latest_remark
from public.tasks t;

alter view public.tasks_with_due_date set (security_invoker = on);
