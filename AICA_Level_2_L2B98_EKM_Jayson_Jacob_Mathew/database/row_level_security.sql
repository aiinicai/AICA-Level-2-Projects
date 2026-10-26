-- =====================================================================
-- DPDP Compliance Manager: tenant security
-- File 2 of 3. Run after database_schema.sql.
--
-- What this file does
--  1. Takes back the broad default privileges Supabase gives the API roles.
--  2. Defines the role-to-capability matrix (table role_capabilities).
--  3. Defines small, reviewed helper functions in app_private (not API-exposed).
--  4. Enables Row Level Security on every table and writes the policies.
--  5. Grants only the columns each table may change directly. Status columns and
--     approvals change only through the review functions in section 7.
--  6. Adds audit triggers, the review functions and the private evidence bucket policies.
--
-- Principles
--  * Client-side filters are not security. Every rule here is enforced in the database.
--  * Platform administrators have NO policy on client content. Support access, if ever
--    needed, goes through the service role with logging.
--  * A firm member has no client access until an engagement assignment is granted.
--  * Client users see firm work (assessments, reports) only after it is shared.
--  * RLS is deliberately not FORCED: the helper functions run as their owner and must
--    read membership tables without recursing into their own policies.
--
-- STATUS: for independent review. See TEST_PLAN.md before using real data.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Take back default privileges
-- ---------------------------------------------------------------------
revoke all on all tables    in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
revoke all on all functions in schema public from public, anon, authenticated;
alter default privileges in schema public revoke all on tables    from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
alter default privileges in schema public revoke execute on functions from public, anon, authenticated;

-- ---------------------------------------------------------------------
-- 2. Role capability matrix
-- ---------------------------------------------------------------------
create table public.role_capabilities (
  actor_kind  text not null check (actor_kind in ('client','firm')),
  role        text not null,
  capability  text not null,
  primary key (actor_kind, role, capability)
);
comment on table public.role_capabilities is 'The role-to-capability matrix. Policies ask "can this user do X on this tenant", never "is this user role Y". Change access here, in one place.';

insert into public.role_capabilities (actor_kind, role, capability) values
 -- client_admin: manages users and departments, approves risk acceptance, sees audit and exports
 ('client','client_admin','read_core'),('client','client_admin','read_outputs'),('client','client_admin','manage_users'),
 ('client','client_admin','manage_departments'),('client','client_admin','edit_profile'),('client','client_admin','approve_client'),
 ('client','client_admin','view_audit'),('client','client_admin','export'),
 -- privacy_lead: coordinates inventory, actions and evidence
 ('client','privacy_lead','read_core'),('client','privacy_lead','read_outputs'),('client','privacy_lead','manage_departments'),
 ('client','privacy_lead','edit_profile'),('client','privacy_lead','edit_inventory'),('client','privacy_lead','edit_actions'),
 ('client','privacy_lead','upload_evidence'),('client','privacy_lead','export'),
 -- department_coordinator: edits assigned inventory only
 ('client','department_coordinator','read_core'),('client','department_coordinator','read_outputs'),('client','department_coordinator','edit_inventory_assigned'),
 -- evidence_contributor: assigned items only
 ('client','evidence_contributor','read_assigned'),('client','evidence_contributor','upload_evidence_assigned'),
 -- management_viewer: approved dashboards and reports only
 ('client','management_viewer','read_outputs'),
 -- client_reviewer: client-side approver
 ('client','client_reviewer','read_core'),('client','client_reviewer','read_outputs'),('client','client_reviewer','approve_client'),
 -- firm team member (through an engagement assignment)
 ('firm','team_member','read_core'),('firm','team_member','read_outputs'),('firm','team_member','read_drafts'),
 ('firm','team_member','read_firm_notes'),('firm','team_member','write_firm_notes'),('firm','team_member','edit_profile'),
 ('firm','team_member','manage_departments'),('firm','team_member','edit_inventory'),('firm','team_member','edit_assessment'),
 ('firm','team_member','edit_actions'),('firm','team_member','upload_evidence'),('firm','team_member','export'),('firm','team_member','view_audit'),
 -- firm reviewer (through an engagement assignment)
 ('firm','reviewer','read_core'),('firm','reviewer','read_outputs'),('firm','reviewer','read_drafts'),
 ('firm','reviewer','read_firm_notes'),('firm','reviewer','write_firm_notes'),('firm','reviewer','review_evidence'),
 ('firm','reviewer','approve_firm'),('firm','reviewer','export'),('firm','reviewer','view_audit');

-- ---------------------------------------------------------------------
-- 3. Helper functions (private schema)
-- ---------------------------------------------------------------------
create function app_private.is_active_user() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.profiles p where p.id = auth.uid() and p.status = 'active')
$$;

create function app_private.is_platform_admin() returns boolean
language sql stable security definer set search_path = '' as $$
  select app_private.is_active_user() and exists (select 1 from public.platform_admins a where a.user_id = auth.uid())
$$;

create function app_private.firm_role(p_firm uuid) returns text
language sql stable security definer set search_path = '' as $$
  select fm.role from public.firm_memberships fm
   where fm.firm_id = p_firm and fm.user_id = auth.uid() and fm.status = 'active' and app_private.is_active_user()
$$;

create function app_private.tenant_firm(p_tenant uuid) returns uuid
language sql stable security definer set search_path = '' as $$
  select t.firm_id from public.tenants t where t.id = p_tenant
$$;

create function app_private.firm_admin_of_tenant(p_tenant uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select app_private.firm_role(app_private.tenant_firm(p_tenant)) = 'firm_admin'
$$;

-- The core question: may the signed-in user do p_cap on tenant p_tenant?
-- Client capabilities come from an active tenant membership. Firm capabilities come
-- only from an active engagement assignment held by an active member of the owning firm.
create function app_private.tenant_can(p_tenant uuid, p_cap text) returns boolean
language sql stable security definer set search_path = '' as $$
  select app_private.is_active_user() and (
    exists (select 1
              from public.tenant_memberships tm
              join public.role_capabilities rc
                on rc.actor_kind = 'client' and rc.role = tm.role and rc.capability = p_cap
             where tm.tenant_id = p_tenant and tm.user_id = auth.uid() and tm.status = 'active')
    or
    exists (select 1
              from public.engagement_assignments ea
              join public.tenants t on t.id = ea.tenant_id
              join public.firm_memberships fm
                on fm.firm_id = t.firm_id and fm.user_id = ea.user_id and fm.status = 'active'
              join public.role_capabilities rc
                on rc.actor_kind = 'firm' and rc.role = ea.role and rc.capability = p_cap
             where ea.tenant_id = p_tenant and ea.user_id = auth.uid() and ea.status = 'active')
  )
$$;

create function app_private.has_tenant_read(p_tenant uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select app_private.tenant_can(p_tenant, 'read_core') or app_private.tenant_can(p_tenant, 'read_outputs')
$$;

create function app_private.has_tenant_access(p_tenant uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select app_private.has_tenant_read(p_tenant) or app_private.tenant_can(p_tenant, 'read_assigned')
$$;

create function app_private.has_any_access() returns boolean
language sql stable security definer set search_path = '' as $$
  select app_private.is_active_user() and (
    exists (select 1 from public.tenant_memberships tm where tm.user_id = auth.uid() and tm.status = 'active')
    or exists (select 1 from public.firm_memberships fm where fm.user_id = auth.uid() and fm.status = 'active'))
$$;

create function app_private.can_read_library(p_firm uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select app_private.firm_role(p_firm) is not null
      or exists (select 1 from public.tenants t where t.firm_id = p_firm and app_private.has_tenant_access(t.id))
$$;

create function app_private.library_editor(p_scope text, p_firm uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select case when p_scope = 'global' then app_private.is_platform_admin()
              else app_private.firm_role(p_firm) is not null end
$$;

create function app_private.library_approver(p_scope text, p_firm uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select case when p_scope = 'global' then app_private.is_platform_admin()
              else app_private.firm_role(p_firm) in ('reviewer','firm_admin') end
$$;

create function app_private.shares_context(p_user uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select p_user = auth.uid()
      or app_private.is_platform_admin()
      or exists (select 1 from public.firm_memberships a join public.firm_memberships b on a.firm_id = b.firm_id
                  where a.user_id = auth.uid() and a.status = 'active' and b.user_id = p_user)
      or exists (select 1 from public.tenant_memberships tm
                  where tm.user_id = p_user and app_private.has_tenant_read(tm.tenant_id))
      or exists (select 1 from public.engagement_assignments ea
                  where ea.user_id = p_user and app_private.has_tenant_read(ea.tenant_id))
$$;

create function app_private.can_edit_activity(p_tenant uuid, p_department uuid, p_owner uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select app_private.tenant_can(p_tenant, 'edit_inventory')
      or (app_private.tenant_can(p_tenant, 'edit_inventory_assigned')
          and (p_owner = auth.uid()
               or exists (select 1 from public.departments d
                           where d.id = p_department and d.tenant_id = p_tenant and d.coordinator_user_id = auth.uid())))
$$;

create function app_private.owns_related(p_tenant uuid, p_item uuid, p_action uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.assessment_items i where i.id = p_item and i.tenant_id = p_tenant and i.owner_user_id = auth.uid())
      or exists (select 1 from public.corrective_actions c where c.id = p_action and c.tenant_id = p_tenant and c.owner_user_id = auth.uid())
$$;

create function app_private.can_upload_evidence(p_tenant uuid, p_item uuid, p_action uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select app_private.tenant_can(p_tenant, 'upload_evidence')
      or (app_private.tenant_can(p_tenant, 'upload_evidence_assigned') and app_private.owns_related(p_tenant, p_item, p_action))
$$;

-- Write one audit row. Only trusted functions call this.
create function app_private.write_audit(p_tenant uuid, p_firm uuid, p_action text, p_type text, p_id uuid, p_details jsonb)
returns void language plpgsql security definer set search_path = '' as $$
declare v_firm uuid := p_firm;
begin
  if v_firm is null and p_tenant is not null then
    select firm_id into v_firm from public.tenants where id = p_tenant;
  end if;
  insert into public.audit_events (tenant_id, firm_id, actor_id, action, entity_type, entity_id, details)
  values (p_tenant, v_firm, auth.uid(), p_action, p_type, p_id, coalesce(p_details, '{}'::jsonb));
end $$;

-- ---------------------------------------------------------------------
-- 4. Row Level Security: enable everywhere, then add policies
-- ---------------------------------------------------------------------
do $$
declare t record;
begin
  for t in select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relkind = 'r' loop
    execute format('alter table public.%I enable row level security', t.relname);
  end loop;
end $$;
-- platform_admins keeps RLS on and has no policy at all: no API access.

-- reference data
create policy cap_read on public.role_capabilities for select to authenticated using (true);
create policy cat_read on public.data_categories for select to authenticated
  using (app_private.has_any_access() or app_private.is_platform_admin());

-- profiles
create policy profiles_read on public.profiles for select to authenticated using (app_private.shares_context(id));
create policy profiles_update_self on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- firms and firm memberships
create policy firms_read on public.firms for select to authenticated
  using (app_private.is_platform_admin() or app_private.firm_role(id) is not null or app_private.can_read_library(id));
create policy firms_insert on public.firms for insert to authenticated with check (app_private.is_platform_admin());
create policy firms_update on public.firms for update to authenticated
  using (app_private.is_platform_admin() or app_private.firm_role(id) = 'firm_admin')
  with check (app_private.is_platform_admin() or app_private.firm_role(id) = 'firm_admin');

create policy fm_read on public.firm_memberships for select to authenticated
  using (user_id = auth.uid() or app_private.firm_role(firm_id) = 'firm_admin' or app_private.is_platform_admin());
create policy fm_insert on public.firm_memberships for insert to authenticated
  with check (app_private.firm_role(firm_id) = 'firm_admin' or app_private.is_platform_admin());
create policy fm_update on public.firm_memberships for update to authenticated
  using (app_private.firm_role(firm_id) = 'firm_admin' or app_private.is_platform_admin())
  with check (app_private.firm_role(firm_id) = 'firm_admin' or app_private.is_platform_admin());
create policy fm_delete on public.firm_memberships for delete to authenticated
  using (app_private.firm_role(firm_id) = 'firm_admin' or app_private.is_platform_admin());

-- tenants and client memberships
create policy tenants_read on public.tenants for select to authenticated
  using (app_private.has_tenant_access(id) or app_private.firm_role(firm_id) = 'firm_admin');
create policy tenants_insert on public.tenants for insert to authenticated
  with check (app_private.firm_role(firm_id) = 'firm_admin');
create policy tenants_update on public.tenants for update to authenticated
  using (app_private.firm_role(firm_id) = 'firm_admin' or app_private.tenant_can(id, 'edit_profile'))
  with check (app_private.firm_role(firm_id) = 'firm_admin' or app_private.tenant_can(id, 'edit_profile'));

create policy tm_read on public.tenant_memberships for select to authenticated
  using (user_id = auth.uid() or app_private.tenant_can(tenant_id, 'read_core') or app_private.firm_admin_of_tenant(tenant_id));
create policy tm_insert on public.tenant_memberships for insert to authenticated
  with check (app_private.tenant_can(tenant_id, 'manage_users') or app_private.firm_admin_of_tenant(tenant_id));
create policy tm_update on public.tenant_memberships for update to authenticated
  using (app_private.tenant_can(tenant_id, 'manage_users') or app_private.firm_admin_of_tenant(tenant_id))
  with check (app_private.tenant_can(tenant_id, 'manage_users') or app_private.firm_admin_of_tenant(tenant_id));
create policy tm_delete on public.tenant_memberships for delete to authenticated
  using (app_private.tenant_can(tenant_id, 'manage_users') or app_private.firm_admin_of_tenant(tenant_id));

-- engagements, assignments and notes
create policy eng_read on public.engagements for select to authenticated
  using (app_private.has_tenant_read(tenant_id) or app_private.firm_admin_of_tenant(tenant_id));
create policy eng_insert on public.engagements for insert to authenticated with check (app_private.firm_admin_of_tenant(tenant_id));
create policy eng_update on public.engagements for update to authenticated
  using (app_private.firm_admin_of_tenant(tenant_id)) with check (app_private.firm_admin_of_tenant(tenant_id));

create policy ea_read on public.engagement_assignments for select to authenticated
  using (user_id = auth.uid() or app_private.firm_admin_of_tenant(tenant_id) or app_private.tenant_can(tenant_id, 'read_firm_notes'));
create policy ea_insert on public.engagement_assignments for insert to authenticated with check (app_private.firm_admin_of_tenant(tenant_id));
create policy ea_update on public.engagement_assignments for update to authenticated
  using (app_private.firm_admin_of_tenant(tenant_id)) with check (app_private.firm_admin_of_tenant(tenant_id));
create policy ea_delete on public.engagement_assignments for delete to authenticated using (app_private.firm_admin_of_tenant(tenant_id));

create policy notes_read on public.engagement_notes for select to authenticated
  using (app_private.tenant_can(tenant_id, 'read_firm_notes')
         or (visibility = 'client_visible' and app_private.tenant_can(tenant_id, 'read_outputs')));
create policy notes_insert on public.engagement_notes for insert to authenticated
  with check (app_private.tenant_can(tenant_id, 'write_firm_notes') and author_id = auth.uid());
create policy notes_update on public.engagement_notes for update to authenticated
  using (author_id = auth.uid() and app_private.tenant_can(tenant_id, 'write_firm_notes'))
  with check (author_id = auth.uid() and app_private.tenant_can(tenant_id, 'write_firm_notes'));
create policy notes_delete on public.engagement_notes for delete to authenticated
  using (author_id = auth.uid() and app_private.tenant_can(tenant_id, 'write_firm_notes'));

-- institution structure
create policy dept_read on public.departments for select to authenticated using (app_private.tenant_can(tenant_id, 'read_core'));
create policy dept_insert on public.departments for insert to authenticated
  with check (app_private.tenant_can(tenant_id, 'manage_departments')
              and (coordinator_user_id is null or exists (select 1 from public.tenant_memberships tm
                    where tm.tenant_id = departments.tenant_id and tm.user_id = coordinator_user_id and tm.status = 'active')));
create policy dept_update on public.departments for update to authenticated
  using (app_private.tenant_can(tenant_id, 'manage_departments'))
  with check (app_private.tenant_can(tenant_id, 'manage_departments')
              and (coordinator_user_id is null or exists (select 1 from public.tenant_memberships tm
                    where tm.tenant_id = departments.tenant_id and tm.user_id = coordinator_user_id and tm.status = 'active')));

create policy vendors_read on public.vendors for select to authenticated using (app_private.tenant_can(tenant_id, 'read_core'));
create policy vendors_insert on public.vendors for insert to authenticated with check (app_private.tenant_can(tenant_id, 'edit_inventory'));
create policy vendors_update on public.vendors for update to authenticated
  using (app_private.tenant_can(tenant_id, 'edit_inventory')) with check (app_private.tenant_can(tenant_id, 'edit_inventory'));

create policy systems_read on public.systems for select to authenticated using (app_private.tenant_can(tenant_id, 'read_core'));
create policy systems_insert on public.systems for insert to authenticated with check (app_private.tenant_can(tenant_id, 'edit_inventory'));
create policy systems_update on public.systems for update to authenticated
  using (app_private.tenant_can(tenant_id, 'edit_inventory')) with check (app_private.tenant_can(tenant_id, 'edit_inventory'));

-- inventory
create policy pa_read on public.processing_activities for select to authenticated using (app_private.tenant_can(tenant_id, 'read_core'));
create policy pa_insert on public.processing_activities for insert to authenticated
  with check (app_private.can_edit_activity(tenant_id, department_id, owner_user_id) and created_by = auth.uid());
create policy pa_update on public.processing_activities for update to authenticated
  using (app_private.can_edit_activity(tenant_id, department_id, owner_user_id))
  with check (app_private.can_edit_activity(tenant_id, department_id, owner_user_id));

create policy as_read on public.activity_systems for select to authenticated using (app_private.tenant_can(tenant_id, 'read_core'));
create policy as_insert on public.activity_systems for insert to authenticated
  with check (exists (select 1 from public.processing_activities pa where pa.id = activity_id and pa.tenant_id = activity_systems.tenant_id
                       and app_private.can_edit_activity(pa.tenant_id, pa.department_id, pa.owner_user_id)));
create policy as_delete on public.activity_systems for delete to authenticated
  using (exists (select 1 from public.processing_activities pa where pa.id = activity_id and pa.tenant_id = activity_systems.tenant_id
                  and app_private.can_edit_activity(pa.tenant_id, pa.department_id, pa.owner_user_id)));

create policy av_read on public.activity_vendors for select to authenticated using (app_private.tenant_can(tenant_id, 'read_core'));
create policy av_insert on public.activity_vendors for insert to authenticated
  with check (exists (select 1 from public.processing_activities pa where pa.id = activity_id and pa.tenant_id = activity_vendors.tenant_id
                       and app_private.can_edit_activity(pa.tenant_id, pa.department_id, pa.owner_user_id)));
create policy av_delete on public.activity_vendors for delete to authenticated
  using (exists (select 1 from public.processing_activities pa where pa.id = activity_id and pa.tenant_id = activity_vendors.tenant_id
                  and app_private.can_edit_activity(pa.tenant_id, pa.department_id, pa.owner_user_id)));

create policy adc_read on public.activity_data_categories for select to authenticated using (app_private.tenant_can(tenant_id, 'read_core'));
create policy adc_insert on public.activity_data_categories for insert to authenticated
  with check (exists (select 1 from public.processing_activities pa where pa.id = activity_id and pa.tenant_id = activity_data_categories.tenant_id
                       and app_private.can_edit_activity(pa.tenant_id, pa.department_id, pa.owner_user_id)));
create policy adc_delete on public.activity_data_categories for delete to authenticated
  using (exists (select 1 from public.processing_activities pa where pa.id = activity_id and pa.tenant_id = activity_data_categories.tenant_id
                  and app_private.can_edit_activity(pa.tenant_id, pa.department_id, pa.owner_user_id)));

-- legal source and control library (global or firm owned)
create policy ls_read on public.legal_sources for select to authenticated
  using ((scope = 'global' and app_private.has_any_access()) or (scope = 'firm' and app_private.can_read_library(firm_id)) or app_private.is_platform_admin());
create policy ls_insert on public.legal_sources for insert to authenticated with check (app_private.library_editor(scope, firm_id) and created_by = auth.uid());
create policy ls_update on public.legal_sources for update to authenticated
  using (app_private.library_editor(scope, firm_id)) with check (app_private.library_editor(scope, firm_id));

create policy lsv_read on public.legal_source_versions for select to authenticated
  using (exists (select 1 from public.legal_sources s where s.id = legal_source_id
                  and (approval_state in ('approved','retired') or app_private.library_editor(s.scope, s.firm_id))));
create policy lsv_insert on public.legal_source_versions for insert to authenticated
  with check (created_by = auth.uid() and approval_state = 'draft' and exists (select 1 from public.legal_sources s where s.id = legal_source_id and app_private.library_editor(s.scope, s.firm_id)));
create policy lsv_update on public.legal_source_versions for update to authenticated
  using (approval_state in ('draft','in_review') and exists (select 1 from public.legal_sources s where s.id = legal_source_id and app_private.library_editor(s.scope, s.firm_id)))
  with check (exists (select 1 from public.legal_sources s where s.id = legal_source_id and app_private.library_editor(s.scope, s.firm_id)));

create policy ctl_read on public.controls for select to authenticated
  using ((scope = 'global' and app_private.has_any_access()) or (scope = 'firm' and app_private.can_read_library(firm_id)) or app_private.is_platform_admin());
create policy ctl_insert on public.controls for insert to authenticated with check (app_private.library_editor(scope, firm_id) and created_by = auth.uid());
create policy ctl_update on public.controls for update to authenticated
  using (app_private.library_editor(scope, firm_id)) with check (app_private.library_editor(scope, firm_id));

create policy cv_read on public.control_versions for select to authenticated
  using (exists (select 1 from public.controls c where c.id = control_id
                  and (review_status in ('approved','retired') or app_private.library_editor(c.scope, c.firm_id))));
create policy cv_insert on public.control_versions for insert to authenticated
  with check (created_by = auth.uid() and review_status = 'draft' and exists (select 1 from public.controls c where c.id = control_id and app_private.library_editor(c.scope, c.firm_id)));
create policy cv_update on public.control_versions for update to authenticated
  using (review_status in ('draft','in_review') and exists (select 1 from public.controls c where c.id = control_id and app_private.library_editor(c.scope, c.firm_id)))
  with check (exists (select 1 from public.controls c where c.id = control_id and app_private.library_editor(c.scope, c.firm_id)));

-- assessments
create policy asm_read on public.assessments for select to authenticated
  using (app_private.tenant_can(tenant_id, 'read_drafts') or (app_private.tenant_can(tenant_id, 'read_outputs') and shared_with_client));
create policy asm_insert on public.assessments for insert to authenticated
  with check (app_private.tenant_can(tenant_id, 'edit_assessment') and prepared_by = auth.uid() and status = 'draft');
create policy asm_update on public.assessments for update to authenticated
  using (app_private.tenant_can(tenant_id, 'edit_assessment') and status in ('draft','in_progress','returned','reopened'))
  with check (app_private.tenant_can(tenant_id, 'edit_assessment') and status in ('draft','in_progress','returned','reopened'));

create policy ad_read on public.applicability_decisions for select to authenticated
  using (app_private.tenant_can(tenant_id, 'read_drafts')
         or (app_private.tenant_can(tenant_id, 'read_outputs') and exists (select 1 from public.assessments a where a.id = assessment_id)));
create policy ad_insert on public.applicability_decisions for insert to authenticated with check (app_private.tenant_can(tenant_id, 'edit_assessment'));
create policy ad_update on public.applicability_decisions for update to authenticated
  using (app_private.tenant_can(tenant_id, 'edit_assessment')) with check (app_private.tenant_can(tenant_id, 'edit_assessment'));
create policy ad_delete on public.applicability_decisions for delete to authenticated using (app_private.tenant_can(tenant_id, 'edit_assessment'));

create policy ai_read on public.assessment_items for select to authenticated
  using (app_private.tenant_can(tenant_id, 'read_drafts')
         or (app_private.tenant_can(tenant_id, 'read_outputs') and exists (select 1 from public.assessments a where a.id = assessment_id))
         or (app_private.tenant_can(tenant_id, 'read_assigned') and owner_user_id = auth.uid()));
create policy ai_insert on public.assessment_items for insert to authenticated with check (app_private.tenant_can(tenant_id, 'edit_assessment'));
create policy ai_update on public.assessment_items for update to authenticated
  using (app_private.tenant_can(tenant_id, 'edit_assessment')) with check (app_private.tenant_can(tenant_id, 'edit_assessment'));
create policy ai_delete on public.assessment_items for delete to authenticated using (app_private.tenant_can(tenant_id, 'edit_assessment'));

create policy snap_read on public.assessment_snapshots for select to authenticated
  using (app_private.tenant_can(tenant_id, 'read_drafts')
         or (app_private.tenant_can(tenant_id, 'read_outputs') and exists (select 1 from public.assessments a where a.id = assessment_id)));

-- evidence
create policy ev_read on public.evidence_records for select to authenticated
  using (app_private.tenant_can(tenant_id, 'read_core')
         or (app_private.tenant_can(tenant_id, 'read_assigned')
             and (uploaded_by = auth.uid() or app_private.owns_related(tenant_id, assessment_item_id, corrective_action_id))));
create policy ev_insert on public.evidence_records for insert to authenticated
  with check (status = 'missing' and app_private.can_upload_evidence(tenant_id, assessment_item_id, corrective_action_id));
create policy ev_update on public.evidence_records for update to authenticated
  using (status in ('missing','submitted') and app_private.can_upload_evidence(tenant_id, assessment_item_id, corrective_action_id))
  with check (status in ('missing','submitted') and app_private.can_upload_evidence(tenant_id, assessment_item_id, corrective_action_id));

create policy evr_read on public.evidence_reviews for select to authenticated
  using (exists (select 1 from public.evidence_records e where e.id = evidence_id));

-- corrective actions
create policy ca_read on public.corrective_actions for select to authenticated
  using (app_private.tenant_can(tenant_id, 'read_core')
         or (app_private.tenant_can(tenant_id, 'read_assigned') and owner_user_id = auth.uid()));
create policy ca_insert on public.corrective_actions for insert to authenticated
  with check (app_private.tenant_can(tenant_id, 'edit_actions') and created_by = auth.uid());
create policy ca_update on public.corrective_actions for update to authenticated
  using (status in ('open','in_progress','blocked','submitted_for_review')
         and (app_private.tenant_can(tenant_id, 'edit_actions') or owner_user_id = auth.uid()))
  with check (status in ('open','in_progress','blocked','submitted_for_review')
         and (app_private.tenant_can(tenant_id, 'edit_actions') or owner_user_id = auth.uid()));

-- review decisions: firm reviewers see all; client users see client-side decisions and shared work
create policy rd_read on public.review_decisions for select to authenticated
  using (app_private.tenant_can(tenant_id, 'read_drafts')
         or (app_private.tenant_can(tenant_id, 'read_core')
             and (reviewer_capacity = 'client_reviewer' or subject_type in ('evidence','corrective_action','risk_acceptance')
                  or (subject_type = 'assessment' and exists (select 1 from public.assessments a where a.id = subject_id)))));

-- audit
create policy audit_read on public.audit_events for select to authenticated
  using ((tenant_id is not null and app_private.tenant_can(tenant_id, 'view_audit'))
         or (firm_id is not null and app_private.firm_role(firm_id) = 'firm_admin'
             and (tenant_id is null or entity_type in ('tenants','engagements','engagement_assignments','tenant_memberships','firm_memberships'))));

-- notifications and reports
create policy notif_read on public.notifications for select to authenticated
  using (user_id = auth.uid() and app_private.has_tenant_access(tenant_id));
create policy notif_update on public.notifications for update to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid() and status = 'read');

create policy rr_read on public.report_runs for select to authenticated
  using (app_private.tenant_can(tenant_id, 'read_drafts')
         or (app_private.tenant_can(tenant_id, 'read_outputs') and shared_with_client and status = 'final'));
create policy rr_insert on public.report_runs for insert to authenticated
  with check (app_private.tenant_can(tenant_id, 'edit_assessment') and generated_by = auth.uid());
create policy rr_update on public.report_runs for update to authenticated
  using (status = 'draft' and app_private.tenant_can(tenant_id, 'edit_assessment'))
  with check (status = 'draft' and app_private.tenant_can(tenant_id, 'edit_assessment'));

-- ---------------------------------------------------------------------
-- 5. Column-level grants. Anything not listed cannot be written from the API.
-- ---------------------------------------------------------------------
grant usage on schema app_private to authenticated;

grant select on all tables in schema public to authenticated;
revoke all on public.platform_admins from authenticated;

grant update (full_name) on public.profiles to authenticated;
grant insert (name) on public.firms to authenticated;
grant update (name) on public.firms to authenticated;
grant insert (firm_id, user_id, role, status) on public.firm_memberships to authenticated;
grant update (role, status, revoked_at) on public.firm_memberships to authenticated;
grant delete on public.firm_memberships to authenticated;

grant insert (firm_id, name, institution_type, sector, description, headcount_band, primary_contact_name, primary_contact_email, status) on public.tenants to authenticated;
grant update (name, institution_type, sector, description, headcount_band, primary_contact_name, primary_contact_email, status) on public.tenants to authenticated;
grant insert (tenant_id, user_id, role, status) on public.tenant_memberships to authenticated;
grant update (role, status, revoked_at) on public.tenant_memberships to authenticated;
grant delete on public.tenant_memberships to authenticated;

grant insert (tenant_id, firm_id, title, scope, status, onboarding_status, missing_information, start_date, assessment_period_start, assessment_period_end) on public.engagements to authenticated;
grant update (title, scope, status, onboarding_status, missing_information, start_date, assessment_period_start, assessment_period_end) on public.engagements to authenticated;
grant insert (tenant_id, engagement_id, user_id, role, status) on public.engagement_assignments to authenticated;
grant update (role, status, revoked_at) on public.engagement_assignments to authenticated;
grant delete on public.engagement_assignments to authenticated;
grant insert (tenant_id, engagement_id, visibility, body) on public.engagement_notes to authenticated;
grant update (visibility, body) on public.engagement_notes to authenticated;
grant delete on public.engagement_notes to authenticated;

grant insert (tenant_id, name, coordinator_user_id) on public.departments to authenticated;
grant update (name, coordinator_user_id, archived_at) on public.departments to authenticated;
grant insert (tenant_id, name, relationship, country_code, contract_status, notes) on public.vendors to authenticated;
grant update (name, relationship, country_code, contract_status, notes, archived_at) on public.vendors to authenticated;
grant insert (tenant_id, name, system_type, hosting_location, owner_department_id, vendor_id) on public.systems to authenticated;
grant update (name, system_type, hosting_location, owner_department_id, vendor_id, archived_at) on public.systems to authenticated;

grant insert (tenant_id, name, department_id, owner_user_id, description, data_principal_categories, collection_source, purposes, processing_operations, internal_recipients, external_recipients, lawful_ground, lawful_ground_rationale, notice_reference, consent_reference, retention_criteria, deletion_process, cross_border, cross_border_notes, children_data, special_case_flags, volume_indicator, sensitivity_indicator, review_date, status, archived_at, archived_reason) on public.processing_activities to authenticated;
grant update (name, department_id, owner_user_id, description, data_principal_categories, collection_source, purposes, processing_operations, internal_recipients, external_recipients, lawful_ground, lawful_ground_rationale, notice_reference, consent_reference, retention_criteria, deletion_process, cross_border, cross_border_notes, children_data, special_case_flags, volume_indicator, sensitivity_indicator, review_date, status, archived_at, archived_reason) on public.processing_activities to authenticated;
grant insert on public.activity_systems, public.activity_vendors, public.activity_data_categories to authenticated;
grant delete on public.activity_systems, public.activity_vendors, public.activity_data_categories to authenticated;

grant insert (scope, firm_id, title, issuing_authority, source_type, official_url) on public.legal_sources to authenticated;
grant update (title, issuing_authority, source_type, official_url) on public.legal_sources to authenticated;
grant insert (legal_source_id, version_label, retrieved_on, published_on, effective_on, notes) on public.legal_source_versions to authenticated;
grant update (version_label, retrieved_on, published_on, effective_on, notes) on public.legal_source_versions to authenticated;
grant insert (scope, firm_id, control_code, title, legal_source_id) on public.controls to authenticated;
grant update (title, legal_source_id) on public.controls to authenticated;
grant insert (control_id, version_no, legal_reference, statement, applicability_logic, commencement_status, effective_date, assessment_question, required_evidence, test_procedure, expected_result, risk_guidance, source_version_id, change_note) on public.control_versions to authenticated;
grant update (legal_reference, statement, applicability_logic, commencement_status, effective_date, assessment_question, required_evidence, test_procedure, expected_result, risk_guidance, source_version_id, change_note) on public.control_versions to authenticated;

grant insert (tenant_id, engagement_id, title, period_start, period_end, reviewer_id, limitations) on public.assessments to authenticated;
grant update (title, period_start, period_end, reviewer_id, limitations) on public.assessments to authenticated;
grant insert (tenant_id, assessment_id, question_code, question_text, outcome, rationale, evidence_id) on public.applicability_decisions to authenticated;
grant update (question_text, outcome, rationale, evidence_id) on public.applicability_decisions to authenticated;
grant delete on public.applicability_decisions to authenticated;
grant insert (tenant_id, assessment_id, control_version_id, applicability, applicability_rationale, result, evidence_quality, risk_level, assessor_notes, recommendation, owner_user_id, target_date) on public.assessment_items to authenticated;
grant update (applicability, applicability_rationale, result, evidence_quality, risk_level, assessor_notes, recommendation, owner_user_id, target_date) on public.assessment_items to authenticated;
grant delete on public.assessment_items to authenticated;

grant insert (tenant_id, title, description, category, source, storage_path, valid_until, activity_id, assessment_id, assessment_item_id, corrective_action_id, supersedes_id, version_no) on public.evidence_records to authenticated;
grant update (title, description, category, source, valid_until) on public.evidence_records to authenticated;

grant insert (tenant_id, assessment_item_id, title, issue, risk_level, risk_rationale, owner_user_id, due_date, dependencies) on public.corrective_actions to authenticated;
grant update (title, issue, risk_level, risk_rationale, owner_user_id, due_date, dependencies, closure_evidence_id) on public.corrective_actions to authenticated;

grant update (status) on public.notifications to authenticated;
grant insert (tenant_id, assessment_id, assessment_version, report_type, limitations, denominators) on public.report_runs to authenticated;
grant update (limitations, denominators) on public.report_runs to authenticated;

-- ---------------------------------------------------------------------
-- 6. Extra triggers that depend on who is calling
-- ---------------------------------------------------------------------
create function app_private.stamp_assessor() returns trigger
language plpgsql security definer set search_path = '' as $$
begin new.assessed_by := auth.uid(); new.assessed_at := now(); return new; end $$;
create trigger stamp_assessor before insert or update on public.applicability_decisions
  for each row execute function app_private.stamp_assessor();

-- An action owner without edit rights may change status, dependencies and closure evidence only.
create function app_private.guard_action_editor() returns trigger
language plpgsql security definer set search_path = '' as $$
declare skip text[] := array['updated_at','dependencies','closure_evidence_id','status','closed_at','closure_verified_by','closure_verified_at','risk_accepted_by','risk_acceptance_rationale','risk_accepted_at'];
begin
  if auth.uid() is not null and not app_private.tenant_can(new.tenant_id, 'edit_actions') then
    if (to_jsonb(new) - skip) is distinct from (to_jsonb(old) - skip) then
      raise exception 'You can update status, dependencies and closure evidence on your own actions, not the other fields' using errcode = '42501';
    end if;
  end if;
  return new;
end $$;
create trigger guard_action_editor before update on public.corrective_actions
  for each row execute function app_private.guard_action_editor();

-- Audit trail. Records ids, changed column names and status or role transitions. Never values of free text.
create function app_private.audit_row() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  j_new jsonb := case when tg_op = 'DELETE' then null else to_jsonb(new) end;
  j_old jsonb := case when tg_op = 'INSERT' then null else to_jsonb(old) end;
  v_src jsonb := coalesce(j_new, j_old);
  v_id uuid := nullif(v_src ->> 'id', '')::uuid;
  v_tenant uuid := nullif(v_src ->> 'tenant_id', '')::uuid;
  v_firm uuid := nullif(v_src ->> 'firm_id', '')::uuid;
  v_changed text[];
  v_details jsonb := '{}'::jsonb;
  k text;
begin
  if tg_table_name = 'tenants' then v_tenant := v_id; end if;
  if tg_op = 'UPDATE' then
    select array_agg(e.key order by e.key) into v_changed
      from jsonb_each(j_new) e where j_old -> e.key is distinct from e.value and e.key <> 'updated_at';
    if v_changed is null then return null; end if;
    v_details := jsonb_build_object('changed', to_jsonb(v_changed));
  end if;
  foreach k in array array['status','role','result','decision','lawful_ground','review_status','approval_state','outcome','evidence_quality'] loop
    if v_src ? k and (tg_op <> 'UPDATE' or j_old -> k is distinct from j_new -> k) then
      v_details := v_details || jsonb_build_object('new_' || k, j_new ->> k) || case when tg_op = 'UPDATE' then jsonb_build_object('old_' || k, j_old ->> k) else '{}'::jsonb end;
    end if;
  end loop;
  perform app_private.write_audit(v_tenant, v_firm, lower(tg_op), tg_table_name, v_id, v_details);
  return null;
end $$;

do $$
declare t text;
begin
  foreach t in array array['firm_memberships','tenants','tenant_memberships','engagements','engagement_assignments','departments','vendors','systems',
                           'processing_activities','assessments','applicability_decisions','assessment_items','evidence_records','evidence_reviews',
                           'corrective_actions','review_decisions','legal_source_versions','control_versions','report_runs'] loop
    execute format('create trigger audit_row after insert or update or delete on public.%I for each row execute function app_private.audit_row()', t);
  end loop;
end $$;

-- ---------------------------------------------------------------------
-- 7. Review and workflow functions (the only way to change status columns)
--    Each function checks the caller again, so a forged request fails here too.
-- ---------------------------------------------------------------------
create function public.submit_assessment_for_review(p_id uuid) returns void
language plpgsql security definer set search_path = '' as $$
declare a public.assessments;
begin
  select * into a from public.assessments where id = p_id;
  if a.id is null or not app_private.tenant_can(a.tenant_id, 'edit_assessment') then
    raise exception 'Not allowed' using errcode = '42501';
  end if;
  if a.status not in ('draft','in_progress','returned','reopened') then
    raise exception 'An assessment in status % cannot be submitted', a.status using errcode = '55000';
  end if;
  if a.reviewer_id is null then raise exception 'Assign a reviewer before submitting' using errcode = '23514'; end if;
  if not exists (select 1 from public.assessment_items where assessment_id = p_id) then
    raise exception 'Add at least one assessed control before submitting' using errcode = '23514';
  end if;
  update public.assessments set status = 'submitted_for_review', submitted_at = now() where id = p_id;
end $$;

create function public.decide_assessment(p_id uuid, p_decision text, p_comments text default null) returns void
language plpgsql security definer set search_path = '' as $$
declare a public.assessments;
begin
  select * into a from public.assessments where id = p_id;
  if a.id is null or not app_private.tenant_can(a.tenant_id, 'approve_firm') then
    raise exception 'Not allowed' using errcode = '42501';
  end if;
  if a.status <> 'submitted_for_review' then raise exception 'The assessment is not awaiting review' using errcode = '55000'; end if;
  if auth.uid() = a.prepared_by then raise exception 'The reviewer must be a different person from the preparer' using errcode = '42501'; end if;
  if a.reviewer_id is distinct from auth.uid() then raise exception 'Only the assigned reviewer can decide' using errcode = '42501'; end if;
  if p_decision not in ('approved','returned_for_revision','clarification_requested') then
    raise exception 'Unknown decision' using errcode = '22023';
  end if;
  insert into public.review_decisions (tenant_id, subject_type, subject_id, subject_version, decision, reviewer_id, reviewer_capacity, comments)
  values (a.tenant_id, 'assessment', a.id, a.version_no, p_decision, auth.uid(), 'firm_reviewer', p_comments);
  if p_decision = 'approved' then
    insert into public.assessment_snapshots (tenant_id, assessment_id, version_no, snapshot, created_by)
    values (a.tenant_id, a.id, a.version_no, jsonb_build_object(
        'assessment', to_jsonb(a),
        'applicability', (select coalesce(jsonb_agg(to_jsonb(d) order by d.question_code), '[]'::jsonb) from public.applicability_decisions d where d.assessment_id = a.id),
        'items', (select coalesce(jsonb_agg(to_jsonb(i) order by i.created_at, i.id), '[]'::jsonb) from public.assessment_items i where i.assessment_id = a.id)), auth.uid());
    update public.assessments set status = 'approved', approved_by = auth.uid(), approved_at = now(), shared_with_client = true where id = a.id;
  else
    update public.assessments set status = 'returned' where id = a.id;
  end if;
end $$;

create function public.reopen_assessment(p_id uuid, p_reason text) returns void
language plpgsql security definer set search_path = '' as $$
declare a public.assessments;
begin
  select * into a from public.assessments where id = p_id;
  if a.id is null or not app_private.tenant_can(a.tenant_id, 'approve_firm') then raise exception 'Not allowed' using errcode = '42501'; end if;
  if a.status <> 'approved' then raise exception 'Only an approved assessment can be reopened' using errcode = '55000'; end if;
  if length(btrim(coalesce(p_reason, ''))) = 0 then raise exception 'A reason is required to reopen an approved assessment' using errcode = '23514'; end if;
  insert into public.review_decisions (tenant_id, subject_type, subject_id, subject_version, decision, reviewer_id, reviewer_capacity, comments)
  values (a.tenant_id, 'assessment', a.id, a.version_no, 'reopened', auth.uid(), 'firm_reviewer', p_reason);
  update public.assessments set status = 'reopened', version_no = a.version_no + 1, shared_with_client = false,
         approved_by = null, approved_at = null, submitted_at = null where id = a.id;
end $$;

create function public.confirm_evidence_upload(p_id uuid, p_file_name text, p_mime_type text, p_size_bytes bigint, p_sha256 text) returns void
language plpgsql security definer set search_path = '' as $$
declare e public.evidence_records;
begin
  select * into e from public.evidence_records where id = p_id;
  if e.id is null or not app_private.can_upload_evidence(e.tenant_id, e.assessment_item_id, e.corrective_action_id) then
    raise exception 'Not allowed' using errcode = '42501';
  end if;
  if e.status <> 'missing' or e.storage_path is null then raise exception 'This evidence record is not waiting for a file' using errcode = '55000'; end if;
  if p_mime_type not in ('application/pdf','image/png','image/jpeg','text/plain','text/csv',
       'application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') then
    raise exception 'File type % is not allowed', p_mime_type using errcode = '23514';
  end if;
  if not exists (select 1 from storage.objects o where o.bucket_id = e.storage_bucket and o.name = e.storage_path) then
    raise exception 'The file was not found in storage. Upload it first.' using errcode = '23514';
  end if;
  update public.evidence_records
     set status = 'submitted', uploaded_by = auth.uid(), uploaded_at = now(),
         file_name = p_file_name, mime_type = p_mime_type, size_bytes = p_size_bytes, sha256 = lower(p_sha256)
   where id = p_id;
end $$;

create function public.decide_evidence(p_id uuid, p_decision text, p_comments text default null) returns void
language plpgsql security definer set search_path = '' as $$
declare e public.evidence_records; v_status text;
begin
  select * into e from public.evidence_records where id = p_id;
  if e.id is null or not app_private.tenant_can(e.tenant_id, 'review_evidence') then raise exception 'Not allowed' using errcode = '42501'; end if;
  if e.uploaded_by is not distinct from auth.uid() then raise exception 'Evidence cannot be reviewed by the person who uploaded it' using errcode = '42501'; end if;
  if p_decision not in ('under_review','verified','rejected','needs_refresh') then raise exception 'Unknown decision' using errcode = '22023'; end if;
  if p_decision in ('under_review','verified') and e.status not in ('submitted','under_review') then
    raise exception 'Evidence in status % cannot be moved to %', e.status, p_decision using errcode = '55000';
  end if;
  if p_decision = 'rejected' and e.status not in ('submitted','under_review','verified') then raise exception 'Evidence in status % cannot be rejected', e.status using errcode = '55000'; end if;
  if p_decision = 'needs_refresh' and e.status <> 'verified' then raise exception 'Only verified evidence can be marked for refresh' using errcode = '55000'; end if;
  if p_decision = 'verified' and e.valid_until is not null and e.valid_until < current_date then
    raise exception 'Evidence past its valid-until date cannot be verified' using errcode = '23514';
  end if;
  v_status := case p_decision when 'under_review' then 'under_review' when 'verified' then 'verified' when 'rejected' then 'rejected' else 'expired' end;
  insert into public.evidence_reviews (tenant_id, evidence_id, reviewer_id, decision, comments) values (e.tenant_id, e.id, auth.uid(), p_decision, p_comments);
  update public.evidence_records set status = v_status where id = e.id;
end $$;

create function public.set_action_status(p_id uuid, p_status text, p_reason text default null) returns void
language plpgsql security definer set search_path = '' as $$
declare c public.corrective_actions; v_reviewer boolean;
begin
  select * into c from public.corrective_actions where id = p_id;
  v_reviewer := c.id is not null and (app_private.tenant_can(c.tenant_id, 'approve_firm') or app_private.tenant_can(c.tenant_id, 'approve_client'));
  if c.id is null or not (app_private.tenant_can(c.tenant_id, 'edit_actions') or v_reviewer
       or (c.owner_user_id = auth.uid() and app_private.has_tenant_access(c.tenant_id))) then
    raise exception 'Not allowed' using errcode = '42501';
  end if;
  if p_status not in ('open','in_progress','blocked','submitted_for_review') then raise exception 'Use close_corrective_action or accept_risk for that status' using errcode = '22023'; end if;
  if c.status in ('closed','accepted_risk') then
    if not v_reviewer then raise exception 'Only a reviewer can reopen a closed action' using errcode = '42501'; end if;
    if p_status <> 'open' or length(btrim(coalesce(p_reason, ''))) = 0 then raise exception 'Reopening needs status open and a reason' using errcode = '23514'; end if;
    insert into public.review_decisions (tenant_id, subject_type, subject_id, decision, reviewer_id, reviewer_capacity, comments)
    values (c.tenant_id, 'corrective_action', c.id, 'reopened', auth.uid(),
            case when app_private.tenant_can(c.tenant_id, 'approve_firm') then 'firm_reviewer' else 'client_reviewer' end, p_reason);
    update public.corrective_actions set status = 'open', closed_at = null, closure_verified_by = null, closure_verified_at = null,
           risk_accepted_by = null, risk_acceptance_rationale = null, risk_accepted_at = null where id = c.id;
    return;
  end if;
  if p_status = 'submitted_for_review' and c.closure_evidence_id is null then
    raise exception 'Link closure evidence before submitting for review' using errcode = '23514';
  end if;
  update public.corrective_actions set status = p_status where id = c.id;
end $$;

create function public.close_corrective_action(p_id uuid) returns void
language plpgsql security definer set search_path = '' as $$
declare c public.corrective_actions; e public.evidence_records; v_cap text;
begin
  select * into c from public.corrective_actions where id = p_id;
  if c.id is null then raise exception 'Not allowed' using errcode = '42501'; end if;
  v_cap := case when app_private.tenant_can(c.tenant_id, 'approve_firm') then 'firm_reviewer'
                when app_private.tenant_can(c.tenant_id, 'approve_client') then 'client_reviewer' end;
  if v_cap is null then raise exception 'Not allowed' using errcode = '42501'; end if;
  if c.status <> 'submitted_for_review' then raise exception 'The action has not been submitted for review' using errcode = '55000'; end if;
  if c.owner_user_id is not distinct from auth.uid() or c.created_by is not distinct from auth.uid() then
    raise exception 'The reviewer must be different from the action owner and creator' using errcode = '42501';
  end if;
  select * into e from public.evidence_records where id = c.closure_evidence_id and tenant_id = c.tenant_id;
  if e.id is null or e.status <> 'verified' or (e.valid_until is not null and e.valid_until < current_date) then
    raise exception 'Closure evidence must be verified and current' using errcode = '23514';
  end if;
  insert into public.review_decisions (tenant_id, subject_type, subject_id, decision, reviewer_id, reviewer_capacity)
  values (c.tenant_id, 'corrective_action', c.id, 'approved', auth.uid(), v_cap);
  update public.corrective_actions set status = 'closed', closed_at = now(), closure_verified_by = auth.uid(), closure_verified_at = now() where id = c.id;
end $$;

create function public.accept_risk(p_id uuid, p_rationale text) returns void
language plpgsql security definer set search_path = '' as $$
declare c public.corrective_actions;
begin
  select * into c from public.corrective_actions where id = p_id;
  if c.id is null or not app_private.tenant_can(c.tenant_id, 'approve_client') then raise exception 'Not allowed' using errcode = '42501'; end if;
  if c.status in ('closed','accepted_risk') then raise exception 'The action is already %', c.status using errcode = '55000'; end if;
  if length(btrim(coalesce(p_rationale, ''))) = 0 then raise exception 'A rationale is required to accept a risk' using errcode = '23514'; end if;
  if c.owner_user_id is not distinct from auth.uid() then raise exception 'The action owner cannot accept their own risk' using errcode = '42501'; end if;
  insert into public.review_decisions (tenant_id, subject_type, subject_id, decision, reviewer_id, reviewer_capacity, comments)
  values (c.tenant_id, 'risk_acceptance', c.id, 'approved', auth.uid(), 'client_reviewer', p_rationale);
  update public.corrective_actions set status = 'accepted_risk', risk_accepted_by = auth.uid(), risk_accepted_at = now(), risk_acceptance_rationale = p_rationale where id = c.id;
end $$;

create function public.finalize_report(p_id uuid, p_share boolean default false) returns void
language plpgsql security definer set search_path = '' as $$
declare r public.report_runs;
begin
  select * into r from public.report_runs where id = p_id;
  if r.id is null or not app_private.tenant_can(r.tenant_id, 'approve_firm') then raise exception 'Not allowed' using errcode = '42501'; end if;
  if r.status <> 'draft' then raise exception 'The report is already final' using errcode = '55000'; end if;
  insert into public.review_decisions (tenant_id, subject_type, subject_id, subject_version, decision, reviewer_id, reviewer_capacity)
  values (r.tenant_id, 'report', r.id, r.assessment_version, 'approved', auth.uid(), 'firm_reviewer');
  update public.report_runs set status = 'final', shared_with_client = p_share where id = r.id;
end $$;

create function public.set_source_version_status(p_id uuid, p_state text, p_verify boolean default false, p_commencement text default null) returns void
language plpgsql security definer set search_path = '' as $$
declare v public.legal_source_versions; s public.legal_sources;
begin
  select * into v from public.legal_source_versions where id = p_id;
  select * into s from public.legal_sources where id = v.legal_source_id;
  if v.id is null or not app_private.library_editor(s.scope, s.firm_id) then raise exception 'Not allowed' using errcode = '42501'; end if;
  if p_state not in ('draft','in_review','approved','retired') then raise exception 'Unknown state' using errcode = '22023'; end if;
  if (p_state in ('approved','retired') or p_verify or v.approval_state = 'in_review' and p_state = 'draft')
     and not app_private.library_approver(s.scope, s.firm_id) then
    raise exception 'Only a reviewer can verify, approve, return or retire' using errcode = '42501';
  end if;
  update public.legal_source_versions
     set approval_state = p_state,
         verification_status = case when p_verify then 'verified' else verification_status end,
         verified_by = case when p_verify then auth.uid() else verified_by end,
         verified_at = case when p_verify then now() else verified_at end,
         commencement_status = coalesce(p_commencement, commencement_status)
   where id = p_id;
end $$;

create function public.set_control_version_status(p_id uuid, p_state text) returns void
language plpgsql security definer set search_path = '' as $$
declare v public.control_versions; c public.controls;
begin
  select * into v from public.control_versions where id = p_id;
  select * into c from public.controls where id = v.control_id;
  if v.id is null or not app_private.library_editor(c.scope, c.firm_id) then raise exception 'Not allowed' using errcode = '42501'; end if;
  if p_state not in ('draft','in_review','approved','retired') then raise exception 'Unknown state' using errcode = '22023'; end if;
  if p_state in ('approved','retired') or (p_state = 'draft' and v.review_status = 'in_review') then
    if not app_private.library_approver(c.scope, c.firm_id) then raise exception 'Only a reviewer can approve, return or retire' using errcode = '42501'; end if;
  end if;
  update public.control_versions
     set review_status = p_state,
         approved_by = case when p_state = 'approved' then auth.uid() else approved_by end,
         approved_at = case when p_state = 'approved' then now() else approved_at end,
         retired_at = case when p_state = 'retired' then now() else retired_at end
   where id = p_id;
end $$;

create function public.log_export(p_tenant uuid, p_export_type text, p_row_count integer) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if not app_private.tenant_can(p_tenant, 'export') then raise exception 'Not allowed' using errcode = '42501'; end if;
  perform app_private.write_audit(p_tenant, null, 'export', p_export_type, null, jsonb_build_object('rows', p_row_count));
end $$;

-- Runs as the caller, so it succeeds only if the caller can read the evidence record.
create function public.log_evidence_access(p_evidence uuid) returns void
language plpgsql security invoker set search_path = '' as $$
declare v_tenant uuid;
begin
  select tenant_id into v_tenant from public.evidence_records where id = p_evidence;
  if v_tenant is null then raise exception 'Not allowed' using errcode = '42501'; end if;
  perform app_private.write_audit(v_tenant, null, 'evidence_access', 'evidence_records', p_evidence, '{}'::jsonb);
end $$;

create function public.my_tenants() returns table (
  tenant_id uuid, tenant_name text, is_demo boolean, tenant_status text,
  client_role text, firm_roles text[], is_firm_admin boolean, capabilities text[])
language sql stable security definer set search_path = '' as $$
  select t.id, t.name, t.is_demo, t.status,
         (select tm.role from public.tenant_memberships tm where tm.tenant_id = t.id and tm.user_id = auth.uid() and tm.status = 'active'),
         coalesce((select array_agg(distinct ea.role order by ea.role) from public.engagement_assignments ea
                    join public.firm_memberships fm on fm.firm_id = t.firm_id and fm.user_id = ea.user_id and fm.status = 'active'
                   where ea.tenant_id = t.id and ea.user_id = auth.uid() and ea.status = 'active'), '{}'),
         app_private.firm_role(t.firm_id) = 'firm_admin',
         coalesce((select array_agg(distinct rc.capability order by rc.capability) from public.role_capabilities rc
                    where app_private.tenant_can(t.id, rc.capability)), '{}')
    from public.tenants t
   where app_private.is_active_user() and (app_private.has_tenant_access(t.id) or app_private.firm_role(t.firm_id) = 'firm_admin')
$$;

-- Dashboard numbers for one client. Every figure comes with its denominator.
-- Not Assessed is never counted as compliant. Sections the caller may not read come back null.
create function public.dashboard_metrics(p_tenant uuid) returns jsonb
language plpgsql stable security definer set search_path = '' as $$
declare
  v_core boolean := app_private.tenant_can(p_tenant, 'read_core');
  v_out  boolean := app_private.tenant_can(p_tenant, 'read_outputs');
  v_draft boolean := app_private.tenant_can(p_tenant, 'read_drafts');
  v_inv jsonb; v_asm jsonb; v_ev jsonb; v_act jsonb; v_rev jsonb; v_lib jsonb; v_aid uuid; v_total int; v_impl int;
begin
  if not (v_core or v_out) then raise exception 'Not allowed' using errcode = '42501'; end if;

  if v_core then
    select jsonb_build_object(
      'total', count(*) filter (where status <> 'archived'),
      'needs_review', count(*) filter (where status = 'needs_review'),
      'draft', count(*) filter (where status = 'draft'),
      'archived', count(*) filter (where status = 'archived'),
      'lawful_ground_not_yet_assessed', count(*) filter (where status <> 'archived' and lawful_ground = 'not_yet_assessed'),
      'cross_border_unknown', count(*) filter (where status <> 'archived' and cross_border = 'unknown'),
      'children_data', count(*) filter (where status <> 'archived' and children_data))
    into v_inv from public.processing_activities where tenant_id = p_tenant;

    select jsonb_build_object(
      'total', count(*),
      'missing', count(*) filter (where status = 'missing'),
      'submitted_or_under_review', count(*) filter (where status in ('submitted','under_review')),
      'verified', count(*) filter (where status = 'verified'),
      'rejected', count(*) filter (where status = 'rejected'),
      'expired_or_past_valid_until', count(*) filter (where status = 'expired' or (valid_until is not null and valid_until < current_date and status <> 'rejected')))
    into v_ev from public.evidence_records where tenant_id = p_tenant;

    select jsonb_build_object(
      'total', count(*),
      'open', count(*) filter (where status not in ('closed','accepted_risk')),
      'overdue', count(*) filter (where status not in ('closed','accepted_risk') and due_date < current_date),
      'high_or_critical_open', count(*) filter (where status not in ('closed','accepted_risk') and risk_level in ('high','critical')),
      'closed', count(*) filter (where status = 'closed'),
      'risk_accepted', count(*) filter (where status = 'accepted_risk'))
    into v_act from public.corrective_actions where tenant_id = p_tenant;
  end if;

  select a.id into v_aid from public.assessments a
   where a.tenant_id = p_tenant and (v_draft or a.shared_with_client) order by a.created_at desc limit 1;
  if v_aid is not null then
    select count(*), count(*) filter (where result = 'implemented_verified') into v_total, v_impl
      from public.assessment_items where assessment_id = v_aid;
    select jsonb_build_object(
      'assessment_id', v_aid,
      'status', (select status from public.assessments where id = v_aid),
      'version', (select version_no from public.assessments where id = v_aid),
      'period_start', (select period_start from public.assessments where id = v_aid),
      'period_end', (select period_end from public.assessments where id = v_aid),
      'items_total', v_total,
      'results', jsonb_build_object(
         'implemented_verified', v_impl,
         'partial', count(*) filter (where result = 'partial'),
         'gap', count(*) filter (where result = 'gap'),
         'not_assessed', count(*) filter (where result = 'not_assessed'),
         'not_applicable', count(*) filter (where result = 'not_applicable')),
      'implemented_verified_share_of_all_items',
         case when v_total > 0 then round(100.0 * v_impl / v_total, 1) end,
      'denominator_note', 'Share = implemented_verified / items_total. Not Assessed and Not Applicable stay in the denominator and are never counted as compliant.')
    into v_asm from public.assessment_items where assessment_id = v_aid;

    select jsonb_build_object('control_versions_with_newer_approved_version', count(*))
      into v_lib
      from public.assessment_items i
      join public.control_versions cv on cv.id = i.control_version_id
     where i.assessment_id = v_aid
       and exists (select 1 from public.control_versions n where n.control_id = cv.control_id and n.version_no > cv.version_no and n.review_status = 'approved');
  end if;

  if v_draft then
    select jsonb_build_object(
      'assessments_awaiting_review', (select count(*) from public.assessments where tenant_id = p_tenant and status = 'submitted_for_review'),
      'evidence_awaiting_review', (select count(*) from public.evidence_records where tenant_id = p_tenant and status in ('submitted','under_review')),
      'actions_awaiting_review', (select count(*) from public.corrective_actions where tenant_id = p_tenant and status = 'submitted_for_review'))
    into v_rev;
  end if;

  return jsonb_build_object('tenant_id', p_tenant, 'generated_at', now(), 'as_of_date', current_date,
                            'inventory', v_inv, 'assessment', v_asm, 'evidence', v_ev, 'actions', v_act,
                            'reviews_pending', v_rev, 'library_impact', v_lib);
end $$;

-- ---------------------------------------------------------------------
-- 8. Private evidence bucket and storage policies
-- ---------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('evidence', 'evidence', false, 26214400,
        array['application/pdf','image/png','image/jpeg','text/plain','text/csv',
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'])
on conflict (id) do update set public = false, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

-- Path convention: {tenant_id}/{random uuid}/{file name}. The evidence_records row is created first with that exact path (the id column is not writable by the browser, so the folder is a random uuid, not the row id).
-- Download works only if the caller can read that evidence_records row (its own policy applies).
create policy evidence_objects_read on storage.objects for select to authenticated
  using (bucket_id = 'evidence'
         and exists (select 1 from public.evidence_records e where e.storage_path = objects.name and e.storage_bucket = objects.bucket_id));
-- Upload works only for a path that matches a waiting evidence row the caller may upload for.
create policy evidence_objects_insert on storage.objects for insert to authenticated
  with check (bucket_id = 'evidence'
         and exists (select 1 from public.evidence_records e
                      where e.storage_path = objects.name and e.storage_bucket = objects.bucket_id and e.status = 'missing'
                        and app_private.can_upload_evidence(e.tenant_id, e.assessment_item_id, e.corrective_action_id)));
-- No update or delete policy: evidence files are immutable. Deletion is a retention decision made by an administrator.

-- ---------------------------------------------------------------------
-- 9. Function privileges
-- ---------------------------------------------------------------------
-- Functions created after section 1 inherited Supabase's default grant to anon. Take it back.
revoke all on all functions in schema public from public, anon, authenticated;
alter default privileges in schema public revoke all on functions from public, anon, authenticated;
revoke all on all functions in schema app_private from public, anon;
grant execute on all functions in schema app_private to authenticated;
grant execute on function
  public.submit_assessment_for_review(uuid), public.decide_assessment(uuid, text, text), public.reopen_assessment(uuid, text),
  public.confirm_evidence_upload(uuid, text, text, bigint, text), public.decide_evidence(uuid, text, text),
  public.set_action_status(uuid, text, text), public.close_corrective_action(uuid), public.accept_risk(uuid, text),
  public.finalize_report(uuid, boolean), public.set_source_version_status(uuid, text, boolean, text),
  public.set_control_version_status(uuid, text), public.log_export(uuid, text, integer), public.log_evidence_access(uuid),
  public.my_tenants(), public.dashboard_metrics(uuid)
to authenticated;
