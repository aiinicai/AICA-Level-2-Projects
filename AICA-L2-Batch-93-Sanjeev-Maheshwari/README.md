# GMJ Expense Settlement Tool — AICA Level 2 Capstone

**Batch 93 — Sanjeev Maheshwari**

A monthly expense submission, approval, and settlement workflow for a
chartered accountancy firm — built for real use, not just as a demo.
Employees submit conveyance/travel/lodging claims, a team head approves
them, and accounts settles them, with a full audit trail and a
deliberate lock on approved data.

## What's in this folder

| File | What it is |
|---|---|
| `index.html` | The working app. Self-contained — open it in a browser, or host it on GitHub Pages, and it talks directly to the Supabase backend below. No build step, no framework, no Lovable dependency. |
| `expense_claim_template.xlsx` | The bulk-entry template employees can fill offline and upload — with a dropdown-validated category column and a self-totaling formula. |
| `sql/1_schema.sql` | The full database schema — six tables, all workflow logic enforced through Postgres functions rather than open writes. |
| `sql/2_storage_policies.sql` | Access rules for uploaded receipt files, matching each role's visibility. |
| `sql/3_link_account_function.sql` | The function that links a new sign-up to a pre-existing employee record. |
| `sql/4_seed_test_data.sql` | Placeholder test users (one of each role) so the app can be tried immediately. |

## Why it's built this way

**The workflow's core rule — locked once approved, no exceptions except
a logged override — is enforced in the database, not the UI.** Every
status change (submit, approve, reject, settle, unlock) goes through a
dedicated Postgres function that checks who's calling and what state the
claim is in. There is deliberately no direct write path to a claim's
status from the client. This means the rule holds even if someone
bypasses the app entirely and queries the database directly — the
control is structural, not cosmetic.

**Access control mirrors the firm's actual reporting lines.** A Teams
table holds each team's head (and a backup, for when the head is away);
an employee's approver is *derived* from their team, not duplicated on
every employee record — so reassigning a head is a one-row change, not
a hunt through every employee under them.

**Three roles, one app.** Employee, team head, and accounts see
different screens from the same login, determined by database lookups
(team headship, an accounts flag) — not by three separate builds.

## Tools used, and why each one

| Tool | Role in this project |
|---|---|
| **Claude** | The entire design process — architecture, data model, the security-definer function pattern, and this build itself, worked through conversationally rather than written blind |
| **Supabase (Postgres)** | The real backend — schema, Row Level Security, and the state-machine functions. This is the offline, rules-based core: no AI call, no per-transaction cost, and it works whether or not any frontend is even running |
| **Plain HTML/JS + Supabase's client library** | The interface submitted here — chosen deliberately over a no-code builder so the capstone submission has no external dependency that could go down or run out of credits between now and evaluation |
| **Lovable** | Used earlier in this project's development to design and iterate the intended production UI (a richer, generated interface) — not included in this submission because build credits were exhausted mid-session. See "What's deferred" below |

## A genuine build-process note, not a polished-over gap

Partway through building the production version in Lovable, a UI
shortcut silently provisioned an isolated "Lovable Cloud" backend
instead of connecting to the real, external Supabase project — twice.
Both times it was caught before real data was written to it, diagnosed
correctly, and reversed. That troubleshooting — recognizing a tool had
quietly done something other than what was asked, verifying rather than
assuming, and correcting course — was as much a part of this course's
learning as the schema design was, and is included here rather than
edited out of the story.

## What's deferred to Phase 2 (documented, not forgotten)

- **The Lovable-generated production UI** — richer than this
  submission's hand-built interface, paused only on credits, connection
  already verified against the same live database
- **Notifications** (email and WhatsApp) — both designed in full,
  including a real cost comparison for WhatsApp Business API in India,
  deliberately deferred rather than rushed in
- **Policy limits, second-level approval for large amounts, and the
  settlement export format for accounts' downstream system** — open
  questions, not yet decided
- **Real firm data** — the seed file here is placeholder test data;
  actual team structure and employee master await entry

## Running it

1. Run the four SQL files in `sql/`, in numeric order, against a fresh
   Supabase project's SQL Editor
2. Open `index.html`'s `SUPABASE_PUBLISHABLE_KEY` constant and fill in
   the project's publishable key (or leave it — the app will prompt for
   it once and remember it in the browser)
3. Open `index.html` directly, or host it via GitHub Pages
4. Sign up using one of the test employee codes from
   `4_seed_test_data.sql` (`TEST-EMP-01`, `TEST-HEAD-01`,
   `TEST-ACC-01`) to see each role's view
