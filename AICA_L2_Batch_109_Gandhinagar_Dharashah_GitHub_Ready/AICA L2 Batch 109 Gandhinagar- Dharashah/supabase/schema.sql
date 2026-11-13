-- Execute in a NEW, dedicated Supabase project SQL editor.
create extension if not exists pgcrypto;
create table if not exists public.organizations(id uuid primary key default gen_random_uuid(),name text not null,created_at timestamptz not null default now());
create table if not exists public.profiles(user_id uuid primary key references auth.users(id) on delete cascade,organization_id uuid not null references public.organizations(id),role text not null check(role in ('admin','recruiter','viewer')),full_name text,created_at timestamptz not null default now());
create table if not exists public.jobs(id uuid primary key default gen_random_uuid(),organization_id uuid not null references public.organizations(id),title text not null,description text not null,status text not null default 'open' check(status in ('draft','open','closed')),created_by uuid references public.profiles(user_id),created_at timestamptz not null default now());
create table if not exists public.applications(id uuid primary key default gen_random_uuid(),organization_id uuid not null references public.organizations(id),job_id uuid not null references public.jobs(id) on delete cascade,filename text not null,storage_path text not null,file_sha256 text not null,match_score integer not null check(match_score between 0 and 100),matched_skills jsonb not null default '[]',missing_skills jsonb not null default '[]',explanation text,review_status text not null default 'pending' check(review_status in ('pending','reviewed','interview','hold')),created_at timestamptz not null default now());
create table if not exists public.reviews(id uuid primary key default gen_random_uuid(),organization_id uuid not null references public.organizations(id),application_id uuid not null references public.applications(id) on delete cascade,reviewer_id uuid not null references public.profiles(user_id),decision text not null,notes text,created_at timestamptz not null default now());
create index if not exists jobs_tenant on public.jobs(organization_id);
create index if not exists applications_job on public.applications(organization_id,job_id);
create index if not exists reviews_app on public.reviews(application_id);
alter table public.organizations enable row level security;
alter table public.profiles enable row level security;
alter table public.jobs enable row level security;
alter table public.applications enable row level security;
alter table public.reviews enable row level security;
-- Deliberately no browser-facing policies: all application data operations are
-- authenticated and tenant-scoped in FastAPI, using server-only service key.
-- Never expose the service key in the frontend.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('resumes','resumes',false,10485760,array['application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'])
on conflict(id) do nothing;
-- Storage bucket has no public access policy. Only the backend service key may write.
