-- Adds legacy-style workflow folder/file selection to existing installations.
alter table public.agents
    add column if not exists workflow_file_paths jsonb not null default '[]'::jsonb;

comment on column public.agents.workflow_file_paths is
    'OneDrive workflow folders/files downloaded into workflow/ for each Codex run.';
