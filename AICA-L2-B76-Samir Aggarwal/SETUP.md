# First-time Setup

Three parts: **Supabase** (the database is the whole backend), **local
development**, and **Railway** (hosting). Allow 30–45 minutes end to end.

You need: a GitHub account, a [supabase.com](https://supabase.com) account, a
[railway.app](https://railway.app) account, and Node.js 20+ locally.

---

## Part 1 — Supabase

### 1.1 Create the project
New project → any name → choose a region close to your users (Mumbai for
India) → save the database password somewhere safe (you rarely need it again).

### 1.2 Run the SQL files, in this exact order
SQL Editor → New query → paste **the entire file** → Run → wait for
`Success` → next file.

> **The three rules that prevent every common failure:**
> 1. Run the files **in order** — later files assume earlier ones.
> 2. Files marked **RUN ALONE** add a value to an enum type; Postgres refuses
>    to *use* a new enum value in the same run that created it, so they cannot
>    be combined with anything.
> 3. Before pressing Run, **click once in the editor so no text is selected**
>    — if anything is highlighted, Supabase runs only the highlighted part.
>    This is the most common silent failure.

| # | File | What it creates | Note |
|---|------|-----------------|------|
| 1 | `01-schema.sql` | Core tables, allow-list signup, RLS, triggers | |
| 2 | `02-seed-task-master.sql` | 90 standard CA tasks | Optional — superseded by 04b |
| 3 | `03-stages-and-recurring.sql` | Stage master 01–05, stage history, recurring schedules | |
| 4 | `04a-add-weekly-recurrence.sql` | Adds Weekly | **RUN ALONE** |
| 5 | `04b-reseed-task-master.sql` | The firm's final 68-task catalogue | |
| 6 | `05-client-groups.sql` | Client groups | |
| 7 | `06-staff-self-assign.sql` | Staff can create their own tasks | |
| 8 | `07-open-assignment.sql` | Anyone assigns anyone; date changes logged not locked | |
| 9 | `08a-add-daily-recurrence.sql` | Adds Daily | **RUN ALONE** |
| 10 | `08b-daily-autogeneration.sql` | pg_cron morning job (08:00 IST) | |
| 11 | `09-schedule-periodicity.sql` | Periodicity per schedule; all cycles auto-generate | |
| 12 | `10-compliance-schema.sql` | Compliance engine: rules, ticks, GSTINs, due-date logic | |
| 13 | `11-compliance-seed.sql` | 71 Indian compliance rules | |
| 14 | `12-gstin-sync.sql` | Client-master GSTIN ⇄ registrations sync + backfill | |
| 15 | `13-visibility-leads.sql` | When tasks appear: monthly 10d, annual 60d before due | |
| 16 | `14-latest-comment.sql` | Latest comment on every task row (board cards) | |

Verify the result:

```sql
select
  (select count(*) from public.stages)                                as stages,          -- 5
  (select count(*) from public.task_master where is_active)           as catalogue,       -- 68
  (select count(*) from public.compliance_master)                     as compliance_rules,-- 71
  (select jobname from cron.job limit 1)                              as morning_job;     -- recurring-task-generator
```

### 1.3 Authentication settings
1. **Authentication → Sign In / Providers → Email → turn OFF "Confirm
   email"** → Save. With it on, every new user waits for a verification mail
   that the free-tier mailer often fails to deliver, and login appears broken.
2. **Authentication → URL Configuration**: set **Site URL** to your app's
   final URL, and add to **Redirect URLs**:
   `https://<your-app-domain>/reset-password` and
   `http://localhost:5173/reset-password` (for the password-reset flow).

### 1.4 Get the two keys
**Project Settings → API**: copy the **Project URL** and the **anon public**
key (`sb_publishable_…`). Both are safe in a browser — the anon key can only
act through row-level security. **Never use the service_role / secret key
anywhere in this app.**

---

## Part 2 — Run locally

```bash
npm install
cp .env.example .env      # then paste the URL and anon key into .env
npm run dev
```

Open http://localhost:5173.

**The first account to sign up becomes the administrator** (role admin,
designation Partner) — so register yourself first, with your real email.
Every later signup must first be added under **Employees → Add Employee**;
the database rejects any email not on that list.

Smoke test (5 minutes):
1. Employees → add a colleague's email. Clients → add a client with a GSTIN.
2. Clients → the client's **Compliance** button → tick *GSTR-3B*, set
   *Handled by*.
3. Recurring → **Run morning job now** → dated tasks appear for the current
   financial year (older periods arrive already marked overdue — that is the
   true pending position, not a bug).
4. Drag a card on the **Board** to *Need Help* — it must insist on a blocker
   note. Complete a compliance task — it must ask for the filing date.

---

## Part 3 — Deploy on Railway

1. Push this folder to a GitHub repository.
2. Railway → **New Project → Deploy from GitHub repo** → select the repo.
   (For a private repo, grant the Railway GitHub App access to it when asked:
   github.com/settings/installations → Railway → Repository access.)
3. **Before the build matters:** service → **Variables** → add
   ```
   VITE_SUPABASE_URL=https://<project-ref>.supabase.co
   VITE_SUPABASE_ANON_KEY=<anon public key>
   ```
   Vite bakes these in at **build** time — if a build ran without them, it
   fails loudly with `VITE_SUPABASE_URL is not set` (a deliberate guard);
   set the variables and redeploy.
4. Railway reads `railway.json` automatically: build `npm run build`, start
   `npm start`, health check `/healthz`. No manual configuration.
5. **Settings → Networking → Generate Domain** → open the URL → you should
   see the login page. Sign in; reaching the dashboard proves the full
   Railway → Supabase round trip.
6. Optional custom domain: add it under Custom Domain, create the CNAME
   record Railway shows you at your DNS provider, and update the Supabase
   Site URL / Redirect URLs (step 1.3) to match.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Grey "Configuration required" page | Build ran without the two variables | Set Variables, redeploy |
| "This email is not authorised" on signup | Email not on the allow-list | Employees → Add Employee first |
| "Incorrect email or password" for a brand-new user | Confirm-email was ON at signup | Turn it off (1.3), then confirm the user once: `update auth.users set email_confirmed_at = now() where email_confirmed_at is null;` |
| A compliance tick generates nothing | No assignee, or GST rule with no GSTIN | The red banner on the Status Board names the exact tick |
| An SQL file "ran" but nothing changed | Part of the paste was selected | Click once in the editor, re-run the whole file — every file is safe to re-run |
| Morning job didn't run | pg_cron missing | `select * from cron.job;` — if empty, re-run 08b then 09 |
