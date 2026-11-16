# 3. Owner steps – simple, one click at a time

Never send passwords, OTPs, or secret keys to the developer or into chat. You will type secrets only into Google/GitHub screens yourself.

## Part A – Put the code in a company-controlled GitHub (about 20 minutes)

Your repository is `github.com/Vijayraj21/dra-career-portal`. If `Vijayraj21` is a personal account, first move the repository to a company organisation:

1. Sign in to github.com with the account that owns the repository.
2. Click your profile picture (top right) → **Your organizations** → **New organization** → choose **Free** → name it e.g. `vrs-corporate-solutions` → use the company email.
3. Open the repository → **Settings** (top bar) → scroll to the bottom **Danger Zone** → **Transfer** → choose the new organisation → type the name to confirm.
4. In the organisation: **Settings → Authentication security** → tick **Require two-factor authentication** → **Save**.
5. Install **GitHub Desktop** (desktop.github.com) → sign in → **File → Clone repository** → pick `dra-career-portal` → **Clone**.
6. Unzip `dra-career-portal.zip` (from this delivery). Copy **everything inside it** into the cloned folder (if asked, choose *Replace*).
7. In GitHub Desktop: bottom-left **Summary** box type `Phase 1: architecture, shared logic, rules, PWA shell` → **Commit to main** → **Push origin**.
8. On github.com open the repository → **Actions** tab. If asked, click **I understand my workflows, go ahead and enable them**. Wait for the **CI** run.
   - Green tick ✅ = website builds, shared tests pass and security-rules tests pass.
   - Red cross ❌ = click it, then click the red step, and send me a screenshot of the **error text** (it contains no secrets).
9. Protect the main branch: repository **Settings → Branches → Add branch ruleset** → name `main` → **Target branches: Include default branch** → tick **Require a pull request before merging** and **Require status checks to pass** (choose `test`) → **Create**.

## Part B – Create the STAGING Firebase project (about 15 minutes) – no real candidates here

1. Open console.firebase.google.com signed in with a **company** Google account (not personal Gmail if you have Google Workspace).
2. **Create a project** → name `vrs-dra-portal-staging` → Google Analytics: **Off** (fewer privacy questions) → **Create**.
3. Left menu **Build → Firestore Database → Create database** → **Location: asia-south1 (Mumbai)** ⚠️ cannot be changed later → **Start in production mode** → **Create**.
4. Left menu **Build → Storage → Get started** → choose the same location → production mode → **Done**.
5. Left menu **Build → Authentication → Get started** → **Sign-in method** tab → enable **Phone** and **Email/Password** → Save. (Do **not** add real phone numbers yet. In **Phone → Phone numbers for testing** add `+91 9999999999` with code `123456` – test numbers send no SMS and cost nothing.)
6. Authentication → **Settings → SMS region policy** → **Allow** → select **India** only → Save. (Blocks costly SMS abuse to other countries.)
7. Project overview ⚙️ → **Project settings → General → Your apps → Web (</>)** → nickname `web-staging` → **Register app**. The config shown is a public identifier, not a secret – keep the page open for Phase 2.

## Part C – Billing safety BEFORE anything paid (about 10 minutes)

1. Firebase console bottom-left **Upgrade** → **Blaze (pay as you go)** → link the company billing account. (Needed for Cloud Functions and SMS.)
2. Open console.cloud.google.com → top search box type **Budgets & alerts** → **Create budget**.
3. Name `staging-monthly` → Projects: `vrs-dra-portal-staging` → Next → **Specified amount** = your D2 number → Next → alert thresholds 50%, 90%, 100% → tick **Email alerts to billing admins and users** → **Finish**.
4. Note: a budget **alerts** you, it does not stop spending. We also add a hard daily SMS limit and AI request limits in the code (Phase 2 / Phase 4).

## Part D – Reply to me with
- Decisions D1–D9 (see `02-DECISIONS-NEEDED.md`).
- "Part A done – CI green/red (screenshot if red)".
- "Part B/C done" – and the **project ID** only (e.g. `vrs-dra-portal-staging`). Nothing else.

Production project (`vrs-dra-portal-prod`) is created later in Phase 9, the same way, only after you approve.
