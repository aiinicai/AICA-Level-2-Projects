# Phase 6: Training Platform, IIBF Mock Exams & Certificate Registry

## Overview
Phase 6 delivers a complete, nationwide debt recovery learning management system, IIBF DRA statutory mock exam simulator, authoritative backend assessment scoring engine, branded printable certificates, and a public certificate verification registry.

---

## What Was Built

### 1. Authoritative Server-Side Scoring & Issuance (`functions/src/training.ts`)
- **`startAssessmentAttempt`**:
  - Validates candidate authentication and retake cooldown rules.
  - Draws questions and performs Fisher-Yates shuffle on question order and multiple-choice options.
  - Strips answer keys and explanations before serving questions to client to eliminate inspect-element cheating.
- **`submitAssessmentAttempt`**:
  - Computes authoritative score against server-side answer keys.
  - If score meets or exceeds `passPercent` (60%+), automatically mints an unguessable certificate ID (`VRS-TC-YYYY-XXXX-XXXX`).
  - Writes private certificate to `certificates/{certId}` and public verification record to `certificate_verification/{certId}` (complying with DPDP Act minimization).
  - Logs `certificate.issue` to tamper-evident audit logs.

### 2. 9 Interactive Training Courses (`web/src/pages/Training.tsx`)
1. **Ethical & Fair Debt Collection Practices** (RBI Fair Practices Code, permissible calling hours 08:00 AM - 07:00 PM, borrower dignity).
2. **Respectful Borrower Communication & Grievance Escalation** (active listening, de-escalation, grievance handling).
3. **Data Protection, Borrower Privacy & DPDP Act 2023** (customer confidentiality, no third-party contact disclosure).
4. **Field Visit Safety, Verification & Evidence Standards** (safety protocols, identification cards, receipt issuance).
5. **Retail & Banking Loan Products** (Credit cards, personal loans, auto loans, secured home loans, NPA stages).
6. **Collection Operations, Call Scripts & Dialers** (PTP recording, call etiquette, CRM updates).
7. **Legal & Regulatory Frameworks** (SARFAESI Act, Lok Adalat, DRT, Section 138 NI Act).
8. **Negotiation Strategies, Settlements & Waivers** (OTS one-time settlements, restructuring, loan rescheduling).
9. **Skip Tracing & Digital Tracing Ethics** (ethical tracing, social media privacy rules, tracing limits).

### 3. IIBF DRA Timed Mock Exam Simulator (`web/src/pages/DraPrep.tsx`)
- Timed practice test simulating official IIBF DRA exam conditions.
- Interactive question navigation grid (Flagged, Answered, Unanswered).
- Post-exam detailed scorecard with percentage, pass/fail indication, and in-depth regulatory explanation for every question.

### 4. Branded Printable Training Certificate (`web/src/pages/CertificateView.tsx`)
- High-trust, printable A4 certificate layout with VRS Corporate Solutions insignia.
- Displays candidate name, unique certificate ID, course curriculum, score percentage, and issue date.
- One-click print/PDF generator (`window.print()`).
- Shareable public verification link.
- **Mandatory Statutory Notice**: Prominently states this is an internal free training award and does NOT substitute for official IIBF DRA statutory examinations.

### 5. Public Certificate Verification Registry (`web/src/pages/PublicCertificateVerification.tsx`)
- URL: `/verify/:certificateId` or `/verify` with search bar.
- Allows partner NBFCs, banks, and agency employers to instantly verify authenticity.
- Protects candidate privacy per DPDP Act (displays only consented minimal identifier e.g., `Rajesh K.`).

---

## Step-by-Step Verification Checklist

1. **Verify Training Courses**:
   - Navigate to `/training`.
   - Click on any course (e.g. *Ethical & Fair Debt Collection Practices*).
   - Read module lessons and click **"Take Knowledge Assessment"**.
   - Answer the quiz questions and click **"Submit Assessment"**.
   - Observe score calculation and click **"View & Download Branded Certificate"**.

2. **Verify Printable Certificate**:
   - Navigate to `/certificates?preview=true` or view the certificate earned from the quiz.
   - Verify candidate name, course title, certificate ID, and statutory IIBF disclaimer.
   - Click **"Print / Save as PDF"** to verify clean A4 print preview.

3. **Verify Public Registry**:
   - Navigate to `/verify/VRS-TC-2026-DEMO-8F3K` or use the search bar on `/verify`.
   - Verify that authentic badges, masked names, and course details load properly.
   - Enter a non-existent ID (e.g. `INVALID-123`) and verify the helpful error state.

4. **Verify DRA Mock Exam**:
   - Navigate to `/dra-exam-preparation`.
   - Click **"Start Timed Mock Exam"**.
   - Answer questions, review the timer countdown, and click **"Finish & View Results"**.
   - Verify comprehensive score breakdown and detailed question explanations.
