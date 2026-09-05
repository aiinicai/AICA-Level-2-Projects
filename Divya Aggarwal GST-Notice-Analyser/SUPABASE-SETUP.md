# Backend setup — Supabase

This app stores data in a **Supabase** PostgreSQL database with real user
accounts. Everyone in the same *firm* signs in with their own account and
shares that firm's clients and notices. Setup is on Supabase's **free tier**
and takes about five minutes.

> The Anthropic API is the only thing that ever costs money, and only if you
> enable automatic extraction (Step 4, optional). The **Add Notice → Use
> Claude.ai** flow is free.

---

## What you need

- Node.js 18+.
- A **Supabase** account — <https://supabase.com> (sign in with GitHub is easiest).

---

## Step 1 — Create a Supabase project

1. <https://supabase.com/dashboard> → **New project**.
2. Name it anything (e.g. `gst-notice-analyser`), set a database password (Supabase stores it, you won't need to remember it), pick the region closest to you.
3. Wait ~2 minutes for it to provision.
4. Go to **Project Settings → API** (or **Data API**) and copy two values:
   - **Project URL** → `https://xxxxxxxx.supabase.co`
   - **anon / publishable key** → safe to expose client-side; Row-Level Security protects the data.

---

## Step 2 — Create the database schema

1. In the Supabase dashboard, open **SQL Editor → New query**.
2. Open [`supabase/schema.sql`](./supabase/schema.sql) from this project, copy its **entire contents**, paste into the editor.
3. Click **Run**. You should see "Success. No rows returned." (Safe to re-run.)

This creates the tables, the `firms` / `firm_members` structure, and
Row-Level Security so each firm only ever sees its own data.

---

## Step 3 — Authentication

Email/password sign-up is on by default. One recommended tweak for local review:

- **Authentication → Providers → Email** → turn **"Confirm email"** *off*, so
  you can sign up and land in the app immediately, with no confirmation email step.

---

## Step 4 — Automatic AI extraction (optional)

Skip this and just use the free **Use Claude.ai** paste flow if you don't
need one-click extraction. To enable it, deploy the included Edge Function
(needs the [Supabase CLI](https://supabase.com/docs/guides/cli)):

```bash
npm install -g supabase
supabase login
supabase link --project-ref YOUR-PROJECT-REF   # from your project URL
supabase functions deploy extract-notice
supabase secrets set ANTHROPIC_API_KEY=sk-ant-api...
```

---

## Step 5 — Run it locally

```bash
npm install
cp .env.example .env.local
```

Edit `.env.local` and paste the two values from Step 1:

```
VITE_SUPABASE_URL=https://xxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_...
```

Then:

```bash
npm run dev
```

Open the URL it prints (`http://localhost:5180`). You should see a **Sign in** screen.

---

## Step 6 — First run

1. **Create an account** (your email + a password of your choice).
2. You'll be asked about a firm → **Create a firm** (you become its owner).
3. **Add a client**, then **Add Notice → Use Claude.ai** and follow the on-screen prompts.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Blank page, console says `supabaseUrl is required` | `.env.local` is missing or the dev server was started before it existed — create/edit it, then stop and restart `npm run dev` (Vite only reads env files at startup). |
| Sign-up says "check your email" and nothing happens | Turn **Confirm email** off (Step 3), or open the confirmation link from Authentication → Users in the Supabase dashboard. |
| Signed in but stuck on "Loading…" | The schema wasn't run — redo Step 2. Check the browser console for a Postgres error. |
| Automatic extraction says "not configured" | Expected until Step 4 is done — use **Use Claude.ai** instead. |
