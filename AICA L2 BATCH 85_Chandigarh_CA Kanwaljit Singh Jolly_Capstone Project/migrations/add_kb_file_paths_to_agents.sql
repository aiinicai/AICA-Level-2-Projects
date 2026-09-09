-- Add KB file paths to agents (stores OneDrive file paths for reusable KB files)
alter table if exists agents
add column if not exists kb_file_paths text[];
