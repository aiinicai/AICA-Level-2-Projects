-- =====================================================================
--  Aggarwal Samir & Co — Task Delegation App
--  FILE 7 : Open assignment — anyone can create and assign work
--
--  The admin-allocates-everything model made the partner a bottleneck. This
--  moves control from LOCKS to HISTORY:
--
--    - any signed-in user may create a task and assign it to anyone
--    - the creator is always recorded honestly (assigned_by cannot be spoofed)
--    - due-date changes are no longer blocked; they are LOGGED instead, so
--      "date was extended by X on Y" is a recorded fact in the task history
--    - reassignment: an admin, or the person who originally assigned the task
--
--  Visibility widens with it: you see tasks assigned TO you and tasks
--  assigned BY you. Admin still sees everything.
--
--  Safe to re-run. Run AFTER 06.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Shared visibility rule, used by tasks and its child tables
-- ---------------------------------------------------------------------
create or replace function public.can_access_task(_task_id uuid)
returns boolean
language sql stable security definer set search_path = public
as $$
  select exists (
    select 1 from public.tasks t
    where t.id = _task_id
      and (t.assigned_to = auth.uid()
           or t.assigned_by = auth.uid()
           or public.is_admin())
  );
$$;

-- ---------------------------------------------------------------------
-- 2. tasks policies
-- ---------------------------------------------------------------------
drop policy if exists tk_select on public.tasks;
create policy tk_select on public.tasks
  for select to authenticated
  using (assigned_to = auth.uid() or assigned_by = auth.uid() or public.is_admin());

drop policy if exists tk_insert on public.tasks;
create policy tk_insert on public.tasks
  for insert to authenticated
  with check (assigned_by = auth.uid() or public.is_admin());

drop policy if exists tk_update on public.tasks;
create policy tk_update on public.tasks
  for update to authenticated
  using (assigned_to = auth.uid() or assigned_by = auth.uid() or public.is_admin())
  with check (assigned_to = auth.uid() or assigned_by = auth.uid() or public.is_admin());

drop policy if exists tk_delete on public.tasks;
create policy tk_delete on public.tasks
  for delete to authenticated
  using (assigned_by = auth.uid() or public.is_admin());

-- ---------------------------------------------------------------------
-- 3. Child tables follow the same visibility
-- ---------------------------------------------------------------------
drop policy if exists tc_select on public.task_comments;
create policy tc_select on public.task_comments
  for select to authenticated using (public.can_access_task(task_id));

drop policy if exists tc_insert on public.task_comments;
create policy tc_insert on public.task_comments
  for insert to authenticated
  with check (user_id = auth.uid() and public.can_access_task(task_id));

drop policy if exists ta_select on public.task_activity;
create policy ta_select on public.task_activity
  for select to authenticated using (public.can_access_task(task_id));

drop policy if exists tsh_select on public.task_stage_history;
create policy tsh_select on public.task_stage_history
  for select to authenticated using (public.can_access_task(task_id));

-- ---------------------------------------------------------------------
-- 4. Guard trigger — only two hard rules survive:
--    the creator cannot be falsified, and reassignment needs to be the
--    admin or the original assigner. Everything else is free and logged.
-- ---------------------------------------------------------------------
create or replace function public.guard_task_update()
returns trigger
language plpgsql security definer set search_path = public
as $$
declare
  v_completed boolean;
begin
  if not public.is_admin() then
    if new.assigned_by is distinct from old.assigned_by then
      raise exception 'The assigner of a task cannot be changed.';
    end if;
    if new.assigned_to is distinct from old.assigned_to
       and old.assigned_by <> auth.uid() then
      raise exception 'Only an administrator or the person who assigned this task can reassign it.';
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

-- ---------------------------------------------------------------------
-- 5. Log due-date changes, so an extension is a recorded fact
-- ---------------------------------------------------------------------
create or replace function public.log_task_activity()
returns trigger
language plpgsql security definer set search_path = public
as $$
declare
  v_old text;
  v_new text;
begin
  if new.stage_id is distinct from old.stage_id then
    select name into v_old from public.stages where id = old.stage_id;
    select name into v_new from public.stages where id = new.stage_id;

    insert into public.task_activity (task_id, changed_by, field, old_value, new_value)
    values (new.id, auth.uid(), 'stage', v_old, v_new);

    insert into public.task_stage_history (task_id, from_stage_id, to_stage_id, note, changed_by)
    values (new.id, old.stage_id, new.stage_id, new.help_note, auth.uid());
  end if;

  if new.assigned_to is distinct from old.assigned_to then
    insert into public.task_activity (task_id, changed_by, field, old_value, new_value)
    values (new.id, auth.uid(), 'assigned_to', old.assigned_to::text, new.assigned_to::text);
  end if;

  if new.due_date is distinct from old.due_date then
    insert into public.task_activity (task_id, changed_by, field, old_value, new_value)
    values (new.id, auth.uid(), 'due_date', old.due_date::text, new.due_date::text);
  end if;

  return new;
end;
$$;

drop trigger if exists trg_log_task_activity on public.tasks;
create trigger trg_log_task_activity
  after update on public.tasks
  for each row execute function public.log_task_activity();

-- =====================================================================
--  Verify, signed in as a NON-admin from the app:
--    create a task assigned to a colleague     -> allowed
--    change the due date on your own task      -> allowed, and a
--       "Due date changed from … to …" entry appears in its History
--    reassign a task a partner gave you        -> refused
-- =====================================================================
