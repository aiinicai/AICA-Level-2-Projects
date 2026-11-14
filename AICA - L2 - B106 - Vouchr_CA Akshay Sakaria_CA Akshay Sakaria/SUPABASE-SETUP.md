# Supabase go-live checklist (pending your go-ahead)

Nothing here has been run against a live project.

**Checked so far:**
- `npm run test:db` applies every migration (0001–0014) to a real Postgres (PGlite) and checks the rules: 33 checks.
- Supabase-specific parts are **not** covered: Auth, pg_cron, pg_net, Storage, and the Edge Function runtime.

## 1. Project and database
1. Create a project in the **Mumbai (ap-south-1)** region (data stays in India).
2. Apply `supabase/migrations/0001` … `0014` in order.
3. Enable the `pg_cron` and `pg_net` extensions.
4. **Auth:** e-mail OTP sign-in. Copy each user's e-mail into `profiles.email` at sign-up (used for alert e-mails).

## 2. The app still needs its data layer connected (part of this step)
Today the app keeps all data in the browser (demo store). Going live means:
- **Reads** of every table go through Supabase.
- **Writes** go through the database functions, never direct inserts. Users can't insert payments directly any more (0010):
  - `record_payment`
  - `apply_advance`
  - `save_bill_document`
  - `start_whatsapp_verification`
  - plain inserts/updates for the rest
- **Contract tests:** the same scenarios run against the demo store and the database (AUDIT-v0.4 A1). Then the demo store can be retired.

- **Auto-approval runs on the server.** Since 0014 a user cannot save a bill as approved. The rule in `src/lib/autoApprove.ts` (with the bill risk check from `src/lib/anomaly.ts`) has to move into `supabase/functions/_shared` and run with the service role after a bill is submitted.
- **Close the year** via a server function: fill `fiscal_years.closed_at` and lock the 12 months in one transaction.

This is the largest single piece of the Supabase step.

## 3. Server secrets (`supabase secrets set …`) — you enter these yourself, never in chat
| Secret | Used by | Notes |
|---|---|---|
| `CRON_SECRET` | all scheduled functions | A long random string; the same value goes in the cron jobs |
| `GOOGLE_SA_EMAIL`, `GOOGLE_SA_PRIVATE_KEY`, `GOOGLE_SHARED_DRIVE_ID` | drive-upload, drive-cleanup, sheets-mirror, whatsapp-webhook | **or** `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REFRESH_TOKEN` |
| `GEMINI_API_KEY`, `GEMINI_TIER=paid`, `GEMINI_MODEL`, `GEMINI_MODEL_FAST`, `AI_DAILY_LIMIT_PER_CLIENT` | ai-assist, whatsapp-webhook | AI is refused unless the tier is `paid` |
| `WHATSAPP_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_GRAPH_VERSION` | whatsapp-webhook | See WHATSAPP-SETUP.md |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (`mailto:…`) | alerts-dispatch | Generate once: `npx web-push generate-vapid-keys` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` | alerts-dispatch | The firm's own mail account; any provider |
| `APP_URL` | alerts-dispatch | The app's address, used for links in e-mails |

**Front-end build variables:**
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_VAPID_PUBLIC_KEY`, the same public key as on the server
- `VITE_AI_ENABLED`

## 4. Functions
Deploy:
- `ai-assist`
- `drive-upload`
- `drive-cleanup`
- `sheets-mirror`
- `compliance-watch`
- `alerts-dispatch`
- `drive-share`
- `whatsapp-webhook`

`whatsapp-webhook` is called by Meta, so deploy it with `--no-verify-jwt`. It checks Meta's signature itself.

## 5. Scheduled jobs (pg_cron → pg_net)
Each job sends the header `x-cron-secret: <CRON_SECRET>`. Without it the functions return 403.

| Job | When (IST) | Function |
|---|---|---|
| alerts | daily 08:00 | alerts-dispatch |
| Sheets mirror | daily 03:00 | sheets-mirror |
| Drive cleanup | daily 03:30 | drive-cleanup (moves unused uploads older than 24 h to Drive trash) |
| Drive sharing | daily 04:00, and after adding / deactivating a client admin | drive-share |
| rule-change watch | quarterly | compliance-watch |
| AI rule scan | as set in 0007 | ai-assist |

## 6. Before real clients
- **Verify in practice** (not tested yet):
  - push and e-mail delivery (`web-push` and `nodemailer` in Deno);
  - the e-invoice QR check with the real IRP key;
  - WhatsApp end to end with Meta;
  - Drive upload and cleanup with the real account.
- **Security:** run the Supabase security advisor and fix its warnings.
