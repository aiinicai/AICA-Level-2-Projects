-- Add client folder path to agents (stores OneDrive folder path for client context)
alter table if exists agents
add column if not exists client_folder_path text;
