-- Run once in the Supabase SQL editor for the SmartHire AI project.
create table if not exists public.interviews (
 id uuid primary key default gen_random_uuid(),
 organization_id uuid not null references public.organizations(id),
 application_id uuid not null references public.applications(id) on delete cascade,
 job_id uuid not null references public.jobs(id),
 starts_at timestamptz not null,
 duration_minutes integer not null default 30 check (duration_minutes between 15 and 240),
 mode text not null default 'online' check (mode in ('online','in_person','phone')),
 interviewer text not null default '',
 meeting_details text not null default '',
 notes text not null default '',
 status text not null default 'scheduled' check (status in ('scheduled','completed','cancelled')),
 created_by uuid not null,
 created_at timestamptz not null default now()
);
create index if not exists interviews_org_starts_idx on public.interviews(organization_id,starts_at);
alter table public.interviews enable row level security;
-- Backend uses service-role key after validating authenticated organization and role.
