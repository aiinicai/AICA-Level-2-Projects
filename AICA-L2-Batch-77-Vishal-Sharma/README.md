# Ecoo Delegation — Web App

Replaces the Google Sheets + Apps Script "Delegation Sheet" system. Full
design rationale lives in the project spec artifact (Parts 1–8); this file
is just the practical how-to-run guide.

**Stack:** React + Vite + TypeScript + Tailwind, talking directly to
Supabase (Postgres + Auth + Row Level Security + Edge Functions). Hosted on
Netlify as a static build, deployed by drag-and-drop.

## Local development

```bash
npm install
cp .env.example .env   # then fill in your Supabase project URL + anon key
npm run dev
```

## Backend setup

See `supabase/README.md` for the database schema, Google Sign-In wiring,
and Edge Function deployment (email sending + user invites).

## Deploying to Netlify (manual drag-and-drop)

```bash
npm run build
```

This produces a `dist/` folder. Go to your Netlify dashboard → **Sites** →
drag the `dist` folder onto the page. That's the whole deploy — repeat
after every round of changes.

## Project structure

```
src/
  auth/            Google Sign-In + session/profile context
  components/      Shared UI (layout, badges, dashboard widgets)
  lib/             Supabase client, typed queries, directory (name lookups)
  pages/           One file per screen/route
  types/           Data model types + the due-bucket calculation
supabase/
  schema.sql       Full DB schema, RLS policies, triggers — run once in the SQL Editor
  functions/       Edge Functions (admin-invite-user, send-task-email)
```

## Still to do before this is usable end-to-end

1. Create the Google Cloud OAuth Client ID (Sign-In with Google) — see below.
2. Follow `supabase/README.md` steps 1–4.
3. Fill in `.env` and run `npm run dev` to confirm login works.
4. Part 5's rating-formula widget is intentionally not built yet (deferred).

### Google OAuth Client ID — quick steps

1. console.cloud.google.com → create/select a project.
2. **APIs & Services → OAuth consent screen** → External → fill in app name/email → save.
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → type "Web application".
4. Authorized redirect URI: `https://<your-project-ref>.supabase.co/auth/v1/callback`
5. Copy the Client ID + Client Secret into Supabase (Authentication → Providers → Google).
