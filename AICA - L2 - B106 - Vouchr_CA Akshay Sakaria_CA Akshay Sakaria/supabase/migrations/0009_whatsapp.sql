-- WhatsApp intake: staff send a bill photo / PDF to the firm's WhatsApp Business number → it becomes a draft in the Inbox.
-- Only numbers registered to an active user (with a valid DPDP consent) are accepted; unknown senders get a polite refusal
-- and nothing they sent is stored.

alter table profiles add column if not exists whatsapp_number text unique;        -- E.164 digits, e.g. 919876543210
alter table profiles add column if not exists whatsapp_verified_at timestamptz;   -- set after the user confirms from the app

alter table expenses drop constraint if exists expenses_entry_source_check;
alter table expenses add constraint expenses_entry_source_check check (entry_source in ('photo', 'qr', 'manual', 'pdf', 'whatsapp'));

-- One row per incoming WhatsApp message: lets retries from Meta be ignored (same wamid) and gives an audit trail.
create table whatsapp_messages (
  wamid        text primary key,                 -- WhatsApp message id
  received_at  timestamptz not null default now(),
  user_id      uuid references profiles(id),     -- null = unknown sender (nothing else stored)
  client_id    uuid references clients(id),
  kind         text not null,                    -- image / document / text / other
  status       text not null check (status in ('draft_created', 'duplicate', 'unknown_sender', 'no_consent', 'unsupported', 'too_large', 'error')),
  expense_id   uuid references expenses(id),
  detail       text
);
alter table whatsapp_messages enable row level security;
create policy whatsapp_messages_read on whatsapp_messages for select using (
  app_role() = 'super_admin' or (app_role() = 'client_admin' and client_id = app_client()) or user_id = auth.uid());
