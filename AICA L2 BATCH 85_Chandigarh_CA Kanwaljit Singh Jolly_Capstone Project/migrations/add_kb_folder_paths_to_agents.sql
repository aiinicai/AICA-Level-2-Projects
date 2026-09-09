-- Add KB folder paths to agents (stores OneDrive folder paths for reusable KB sets)
alter table if exists agents
add column if not exists kb_folder_paths text[];
