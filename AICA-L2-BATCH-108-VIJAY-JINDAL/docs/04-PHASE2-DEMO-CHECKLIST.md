# 4. Phase 2 – What was built, what was tested, how you check it

## Built
- **Firebase Authentication Integration (`web/src/lib/firebase.ts`):**
  - Phone OTP provider configured for Indian numbers (+91).
  - Invisible reCAPTCHA verifier anchor (`#recaptcha-container`).
  - 60-second cooldown timer before allowing OTP resend (cost control).
  - Staging test account bypass (+91 9999999999, code 123456) for 100% free testing without sending paid SMS.
- **Interactive Candidate Registration Wizard (`web/src/pages/Login.tsx`):**
  - Step 1: 10-digit mobile number input with clear country code.
  - Step 2: 6-digit verification code input.
  - Step 3 (for new candidates): Complete initial registration form:
    - Full Name (as per ID)
    - State & Union Territory (all 36 States/UTs with Hindi/Punjabi names)
    - Current City / District
    - 6-digit PIN code with instant advisory mismatch check
    - DRA Status (Certified, Training in Progress, Result Awaited, Not Certified)
    - Preferred Role (Field Collection, Telecalling, Backend, Team Leader, Supervisor, Manager, Other)
    - Age 18+ attestation checkbox (Decision D3)
    - Privacy Policy & Terms acceptance checkboxes
    - Recruitment contact consent checkbox
    - WhatsApp job notifications checkbox (optional)
    - Referral code input (prefilled from URL if referred)
- **Candidate Dashboard (`web/src/pages/CandidateDashboard.tsx`):**
  - Displays permanent random Candidate ID (e.g. `VRS-C-7K2M9P4X`).
  - Profile completion progress card.
  - Referral card: unique referral link (`?ref=RXXXXXX`), one-click Copy Link, and one-click Share on WhatsApp.
  - Quick action tiles for Jobs, Free Training, DRA Exam Prep, and Resume Builder.
  - Clean Sign Out button.
- **Multilingual Support:**
  - Complete English, Hindi, and Punjabi translations for all registration and dashboard screens.
- **Server-side Registration (`functions/src/registration.ts`):**
  - Single atomic Firestore transaction for candidate creation.
  - Generates permanent internal candidate ID and stable referral code.
  - Prevents duplicate accounts and enforces age & consent validation.

---

## Your Phase 2 Owner Demonstration Checklist

Follow these baby steps to test the newly built registration system:

### 1. Update your GitHub repository
1. Copy all updated files from `Anti_DRA_Career` into your `Github_clone` folder:
   - `functions/src/registration.ts`
   - `web/src/lib/firebase.ts`
   - `web/src/i18n/strings.ts`
   - `web/src/pages/Login.tsx`
   - `web/src/pages/CandidateDashboard.tsx`
   - `web/src/App.tsx`
   - `web/src/components/Layout.tsx`
2. Open **GitHub Desktop**:
   - Summary box: `Phase 2: candidate registration wizard, phone OTP and dashboard`
   - Click **Commit to main** → Click **Push origin**.
3. On github.com, open **Actions** and ensure the CI run is green ✅.

---

### 2. How to Test Registration (Free Test Account)
1. Open the portal URL in your browser (or run locally with `npm run preview` in `web`).
2. Click **Login / Register** in the top navigation.
3. You will see the **Candidate Login / Free Registration** screen with the blue test banner.
4. **Test Step 1:**
   - In the mobile box, enter: `9999999999`
   - Click **Send Verification OTP**.
5. **Test Step 2:**
   - In the OTP box, enter: `123456`
   - Click **Verify & Sign In**.
6. **Test Step 3:**
   - Because this test number has no profile yet, the registration wizard appears.
   - Enter your name: e.g. `Ramesh Kumar`
   - Select your State: e.g. `Punjab` (or any other State)
   - Enter City: e.g. `Ludhiana`
   - Enter PIN: `141001`
   - Select DRA Status: `DRA Certified` (or another status)
   - Select Preferred Role: `Field Collection`
   - Tick the **I confirm I am 18 years of age or older** box.
   - Tick the **Privacy Policy** and **Terms** boxes.
   - Click **Create Free Account**.
7. **Test Step 4:**
   - You are redirected to your **Candidate Dashboard**!
   - Verify that your permanent **Candidate ID** is displayed (e.g. `VRS-C-XXXXXXXX`).
   - Click **Copy Referral Link** or **Share on WhatsApp** to verify referral sharing.
   - Click **Sign Out** to verify clean logout.
