# Phase 8: DPDP Privacy Workflows, Security Rules Tests & Backups

## Overview
Phase 8 implements compliance with the **Digital Personal Data Protection (DPDP) Act, 2023**, an automated candidate data rights self-service center, expanded Firestore security rules test cases, an authoritative database backup utility, and disaster recovery procedures for **VRS Corporate Solutions**.

---

## What Was Built

### 1. DPDP Act Candidate Privacy Center (`web/src/pages/PrivacyCenter.tsx`)
- **Right to Correction**: Candidates can submit requests to rectify inaccurate personal, contact, or qualification records.
- **Right to Account Closure & Erasure**: 1-click account closure immediately stops job matching, marketing messages, and recruiter outreach.
- **Granular Consent Controls**: Independent toggles for WhatsApp job alerts, third-party employer sharing, and public training certificate verification.
- **Request Ledger & Audit History**: Displays all submitted data rights requests with status tracking (`received`, `in_review`, `completed`).
- **Grievance Officer Contact**: Explicit statutory contact details for the VRS Corporate Solutions Data Protection Officer.

### 2. Privileged Privacy Function (`functions/src/privacy.ts` & `functions/src/index.ts`)
- **`requestDataRights`**:
  - Authenticates candidate, validates request type (`correction`, `closure`, `deletion`, `consent_withdrawal`).
  - Writes to immutable `data_requests/{requestId}` ledger.
  - Automatically transitions candidate status to `closed` on closure requests.
  - Generates tamper-evident audit log entries (`account.closure`, `consent.change`, `account.deletion`).

### 3. Expanded Firestore Security Rules Tests (`tests/rules/firestore.rules.test.ts`)
- Added automated assertions verifying:
  - Browser clients cannot forge writes to `contact_messages` (must use Cloud Function).
  - Candidates can only inspect their own `data_requests` and cannot forge staff resolution states.
  - Candidates cannot read another candidate's private job applications.

### 4. Database Backup Script & Disaster Recovery Runbook
- **`scripts/backup-firestore.ts`**: Backs up critical portal collections (`candidates`, `vacancies`, `applications`, `certificates`, `contact_messages`, `audit_logs`) to structured JSON with manifest summaries.
- **`docs/05-BACKUP-RUNBOOK.md`**: Step-by-step restoration procedures, retention schedules, and disaster recovery protocol.

---

## Step-by-Step Verification Checklist

1. **Verify Candidate Privacy Center**:
   - Log in and navigate to `/privacy-center` (or click *Privacy & Data Rights* on `/dashboard`).
   - Review your Candidate ID and active consent toggles.
   - Toggle consent preferences and click **"Save Preferences"**.

2. **Submit a Data Rights Request**:
   - Select **"Data Correction"** or **"Account Closure"** in the request nature dropdown.
   - Enter your request details and click **"Submit Request →"**.
   - Verify the confirmation message and observe the new entry in your request history.

3. **Verify Security Rules & Backups**:
   - Review `tests/rules/firestore.rules.test.ts` for comprehensive security coverage.
   - Review `docs/05-BACKUP-RUNBOOK.md` for disaster recovery procedures.
