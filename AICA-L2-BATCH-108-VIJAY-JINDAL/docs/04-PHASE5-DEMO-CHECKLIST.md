# 4. Phase 5 – What was built, what was tested, how you check it

## Built
- **Job Opportunities Explorer (`web/src/pages/Jobs.tsx`):**
  - Search by title, city, or keywords.
  - Multi-criteria filters: Role (Field, Telecalling, Backend, Team Leader, Supervisor, Manager), State/UT, and DRA Certification Policy (Mandatory, Preferred, Not Required).
  - Clean job cards showing Vacancy ID, Openings, City/State, approved employer display name, salary range (INR), and joining need.
  - Interactive "View & Apply" modal:
    - Automatically checks if candidate is signed in and whether they have already applied.
    - Single submission enforcement (deterministic ID `VAC-XXXX_UID`).
    - Enforces **Decision D5**: If DRA certification is mandatory and the candidate has not completed verified DRA review, it displays a clear advisory and accepts the application marked as **"DRA Eligibility Not Established"** for recruiters.
- **Candidate Application Tracking (`web/src/pages/MyApplications.tsx`):**
  - Displays submitted applications with reference IDs and submission dates.
  - Candidate-friendly status lifecycle: *Application Received* → *Under Review* → *Interview Scheduled* → *Selected / Offered* → *Not Progressed* → *Closed*.
  - Strict privacy protection: Zero internal recruiter notes or staff comments are ever exposed to the candidate.
- **Internal Recruitment Pipeline Dashboard (`web/src/pages/admin/RecruitmentDashboard.tsx`):**
  - Real-time pipeline counter cards (*Total Applications*, *DRA Review Needed*, *In Screening*, *Selected / Placed*).
  - Candidate applications table showing Candidate ID, Vacancy, DRA eligibility status, and candidate status.
  - Stage update dialog: Move candidates between 13 recruitment stages (*Screening*, *Contacted*, *Shortlisted*, *Interview Scheduled*, *Selected*, *Offered*, *Joined*, etc.).
  - Confidential internal notes: Stored in `applications_internal/` and completely invisible to candidates.
  - Vacancy management: View existing vacancies and publish new collection vacancies across India with full field rules.
- **Server-Side Security Functions (`functions/src/recruitment.ts`):**
  - `submitApplication`: Validates active candidate status, published vacancy status, closing date, and single-application rule in an atomic Firestore batch.
  - `updateApplicationStage`: Authorized staff only (`notes.recruitment` / `owner_admin`), maps internal recruitment stages to candidate-visible statuses, and logs audit events.

---

## Your Phase 5 Owner Demonstration Checklist

### 1. Update your GitHub repository
1. Copy updated files from `Anti_DRA_Career` to `Github_clone`:
   - `functions/src/recruitment.ts`
   - `functions/src/index.ts`
   - `web/src/lib/firebase.ts`
   - `web/src/pages/Jobs.tsx`
   - `web/src/pages/MyApplications.tsx`
   - `web/src/pages/CandidateDashboard.tsx`
   - `web/src/pages/admin/RecruitmentDashboard.tsx`
   - `web/src/App.tsx`
   - `docs/04-PHASE5-DEMO-CHECKLIST.md`
2. In **GitHub Desktop**:
   - Summary box: `Phase 5: vacancies explorer, 1-click apply, application tracking and recruitment pipeline`
   - Click **Commit to main** → Click **Push origin**.
3. On github.com, open **Actions** and verify that CI passes with a green checkmark ✅.

---

### 2. How to Test Vacancies & Applications
1. Sign in with test account `9999999999` (code `123456`).
2. Click **Jobs** in the top navigation.
3. Filter by role or state (e.g. choose "Field Collection" or "Punjab").
4. Click **View & Apply →** on any vacancy.
   - Review job description, openings, and salary.
   - Click **Confirm & Apply Free →**.
   - You will see the green confirmation: *"Application submitted successfully!"*
   - Notice the button changes to **Applied ✓**.
5. Click **View My Applications →** (or visit `/my-applications`).
   - Confirm your submitted application appears with status **Application Received**.
6. Visit `/admin/recruitment`:
   - View the internal pipeline table showing the new application.
   - Click **Update Stage ✎** to advance the application (e.g. to *Screening* or *Shortlisted*) and enter a confidential recruiter note.
   - Check `/my-applications` again and confirm the candidate status has cleanly updated to **Under Review** without leaking your internal notes!
