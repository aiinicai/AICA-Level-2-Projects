# 4. Phase 3 – What was built, what was tested, how you check it

## Built
- **Multi-Step Profile Wizard (`web/src/pages/CandidateProfile.tsx`):**
  - **Step 1 (Basic & Contact):** Full Name, verified primary mobile (locked), optional alternate mobile, WhatsApp contact (with "Same as Primary" toggle), and optional restricted fields (Father/Guardian name, Date of Birth).
  - **Step 2 (Address & Location):** Complete 36 States/UTs dropdown, district, city, area/locality, 6-digit PIN code with real-time India Post prefix validation, and optional restricted street & permanent addresses.
  - **Step 3 (Official DRA Qualification):** Status selection (Certified, Training in Progress, Result Awaited, Not Certified). For certified candidates: certificate number, issuer (e.g. IIBF), name on certificate, passing date, training institute, and document upload (PDF/JPG/PNG, max 5MB).
  - **Step 4 (Education & Work Experience):** Highest education level, school/college, passing year; Fresher vs. Experienced toggle; total experience in months; repeatable employment entries (employer/agency, designation, role, dates, lenders handled, products handled, delinquency buckets handled, with clear privacy warnings to never enter borrower details); languages known tags.
  - **Step 5 (Job Preferences & Availability):** Joining availability (Immediate, 15 days, 30 days, 60+ days), opportunity status, vehicle & licence checks (two-wheeler, driving licence), and restricted current & expected monthly salary in INR.
  - **Step 6 (Photo & CV):** Direct upload to private Cloud Storage for profile photo (max 2MB) and CV/resume document (max 5MB).
- **Backend DRA Security Function (`functions/src/dra.ts`):**
  - `updateDraQualification`: Server-authoritative function enforcing that updating the certificate number or uploading a new certificate file resets `documentReview.status` to `pending` and clears issuer verification.
  - Recalculates candidate completeness score dynamically.
- **Client Storage & Firestore Integrations (`web/src/lib/firebase.ts`):**
  - Direct private upload to `incoming/{uid}/photo/`, `incoming/{uid}/cv/`, and `incoming/{uid}/dra/` enforcing file type and size limits.
  - Granular Firestore updates for core profile, sub-profile, restricted identity, and restricted compensation.

---

## Your Phase 3 Owner Demonstration Checklist

### 1. Update your GitHub repository
1. Copy updated files from `Anti_DRA_Career` to `Github_clone`:
   - `functions/src/dra.ts`
   - `functions/src/index.ts`
   - `web/src/lib/firebase.ts`
   - `web/src/pages/CandidateProfile.tsx`
   - `web/src/pages/CandidateDashboard.tsx`
   - `web/src/App.tsx`
   - `docs/04-PHASE3-DEMO-CHECKLIST.md`
2. In **GitHub Desktop**:
   - Summary box: `Phase 3: complete candidate profile wizard, DRA uploads and restricted fields`
   - Click **Commit to main** → Click **Push origin**.
3. On github.com, open **Actions** and verify that CI passes with a green checkmark ✅.

---

### 2. How to Test the Profile Wizard
1. Open the portal in your browser and sign in (using test number `9999999999` with code `123456`).
2. On your **Candidate Dashboard**, click **Complete Full Profile →**.
3. **Step 1 (Basic):** Review your name and contact preferences; click **Save & Continue**.
4. **Step 2 (Address):** Enter your district, area, and verify your PIN; click **Save & Continue**.
5. **Step 3 (DRA Qualification):**
   - Select **DRA Certified**.
   - Type Certificate Number (e.g. `DRA/2024/78901`) and Issuer `IIBF`.
   - Optionally choose a PDF or image file to upload.
   - Click **Save & Continue**. Notice how the review status is tracked as **Pending Review**.
6. **Step 4 (Experience):**
   - Select **Experienced**.
   - Click **+ Add Employer**. Enter an agency name, designation, select products (e.g. Personal Loans, Two-Wheeler) and buckets (e.g. 1-30 DPD).
   - Click **+ Add Qualification** to record Class 12th or Graduate details.
   - Click language tags (e.g., Hindi, English, Punjabi).
   - Click **Save & Continue**.
7. **Step 5 (Preferences):** Set joining availability, vehicle status, and expected salary. Click **Save & Continue**.
8. **Step 6 (Documents):** Optionally upload a profile photo or CV, then click **Go to Dashboard**.
9. Verify on your Dashboard that the **Profile Completeness bar** has increased towards 100%!
