-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 6 : Let staff record their own work
--
--  Until now only an admin could create a task, so anything a staff member
--  picked up themselves — a client walking in, a query they agreed to handle —
--  either went untracked or had to be routed through a partner. That is the
--  opposite of what a status tracker is for.
--
--  A staff member may now create a task ONLY for themselves. They still cannot
--  assign work to a colleague; that stays with an administrator.
--
--  Safe to re-run.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. INSERT — self only, unless admin
-- ---------------------------------------------------------------------
drop policy if exists tk_admin_insert on public.tasks;
drop policy if exists tk_insert on public.tasks;

create policy tk_insert on public.tasks
  for insert to authenticated
  with check (
    public.is_admin()
    or (assigned_to = auth.uid() and assigned_by = auth.uid())
  );


-- ---------------------------------------------------------------------
-- 2. DELETE — an admin, or the owner of a task they raised themselves
-- ---------------------------------------------------------------------
drop policy if exists tk_admin_delete on public.tasks;
drop policy if exists tk_delete on public.tasks;

create policy tk_delete on public.tasks
  for delete to authenticated
  using (
    public.is_admin()
    or (assigned_to = auth.uid() and assigned_by = auth.uid())
  );


-- ---------------------------------------------------------------------
-- 3. The guard trigger, refined
--    It exists to stop staff quietly reassigning work or moving a deadline a
--    partner set. A task somebody raised for themselves has no partner-set
--    deadline, so locking its due date only traps a typo. Self-raised tasks
--    are therefore editable by their owner — but the assignee still cannot be
--    changed, so nobody can push their own work onto a colleague.
-- ---------------------------------------------------------------------
create or replace function public.guard_task_update()
returns trigger
language plpgsql security definer set search_path = public
as $$
declare
  v_completed boolean;
  v_self_raised boolean;
begin
  v_self_raised := old.assigned_by = auth.uid() and old.assigned_to = auth.uid();

  if not public.is_admin() then
    if new.assigned_to is distinct from old.assigned_to
       or new.assigned_by is distinct from old.assigned_by then
      raise exception 'Only an administrator can reassign a task.';
    end if;

    if not v_self_raised then
      if new.client_id is distinct from old.client_id
         or new.due_date is distinct from old.due_date then
        raise exception 'Only an administrator can change the client or due date of a task assigned to you.';
      end if;
    end if;
  end if;

  if new.stage_id is distinct from old.stage_id then
    new.stage_since := now();

    select s.is_terminal and not s.is_dropped into v_completed
    from public.stages s where s.id = new.stage_id;

    if coalesce(v_completed, false) then
      new.completed_at := now();
    else
      new.completed_at := null;
    end if;

    if not exists (select 1 from public.stages where id = new.stage_id and code = '03') then
      new.help_note := null;
    end if;
  end if;

  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists trg_guard_task_update on public.tasks;
create trigger trg_guard_task_update
  before update on public.tasks
  for each row execute function public.guard_task_update();

-- =====================================================================
--  Verify (as a non-admin, from the app):
--    creating a task for yourself      -> allowed
--    creating one for a colleague      -> "new row violates row-level security"
--    editing your own task's due date  -> allowed
--    editing a partner-set due date    -> refused with a clear message
-- =====================================================================
