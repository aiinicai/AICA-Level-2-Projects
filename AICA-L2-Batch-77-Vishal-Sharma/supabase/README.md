# Backend setup (Supabase)

## 1. Database

Open your Supabase project → **SQL Editor** → New query → paste the entire
contents of `schema.sql` → Run. That creates every table, RLS policy, and
trigger described in the Part 1–8 spec.

## 2. Google Sign-In

Supabase project → **Authentication → Providers → Google** → enable it, and
paste in the Client ID / Client Secret from Google Cloud Console (we'll set
that up together — see the app's main README).

Add this as an **Authorized redirect URI** in the Google Cloud OAuth client:
`https://<your-project-ref>.supabase.co/auth/v1/callback`

## 3. Edge Functions

Requires the Supabase CLI (`npm i -g supabase`, or already installed —
check with `supabase --version`).

```bash
cd webapp
supabase login
supabase link --project-ref <your-project-ref>

# secrets used by the functions below
supabase secrets set GMAIL_USER=youraccount@gmail.com
supabase secrets set GMAIL_APP_PASSWORD=your-16-char-app-password
supabase secrets set WEBHOOK_SECRET=$(openssl rand -hex 24)

supabase functions deploy admin-invite-user
supabase functions deploy send-task-email
```

`GMAIL_APP_PASSWORD` is a Google **App Password** (not your normal Gmail
password) — generate one at myaccount.google.com/apppasswords, which
requires 2-Step Verification to be turned on for that Gmail account.

## 4. Wire up the email-sending webhooks

Supabase project → **Database → Webhooks → Create a new hook**, twice:

**Hook A — task created**
- Table: `tasks`, Event: `INSERT`
- Type: HTTP request → Edge Function → `send-task-email`
- HTTP Headers: add `x-webhook-secret` = the `WEBHOOK_SECRET` value you set above

**Hook B — task delegated**
- Table: `tasks`, Event: `UPDATE`
- Type: HTTP request → Edge Function → `send-task-email`
- Same `x-webhook-secret` header

(The function itself figures out whether an UPDATE actually needs an email —
it only sends one when `secondary_assignee_id` just got set for the first time.)

## 5. Frontend env vars

Copy `.env.example` to `.env` in the `webapp` folder and fill in your
project's URL + anon key (Project Settings → API).
