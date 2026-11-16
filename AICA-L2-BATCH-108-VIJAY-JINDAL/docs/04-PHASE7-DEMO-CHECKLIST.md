# Phase 7: Admin CMS, Settings & Contact Handling

## Overview
Phase 7 delivers dynamic site configuration, public announcement banners, a multi-category contact inquiry workflow, authoritative server-side message handling, an IIBF DRA training institute directory, and a dedicated internal CMS management dashboard for portal administrators.

---

## What Was Built

### 1. Site Configuration & Banner Architecture (`cms_public/site`)
- **Operator Details**: Dynamically loads operator name (`VRS Corporate Solutions`), registered headquarters address lines, official helpline phone, WhatsApp support link, and email.
- **Top Announcement Banners**: Enables owner-administrators to broadcast urgent notifications (e.g. *150+ DRA Certified Openings across Punjab & Haryana*) directly on the homepage.
- **Operational Switches**:
  - Emergency Maintenance Mode with customizable visitor notice.
  - Candidate registration switch (Open / Paused).
  - Referral program switch (Active / Paused / Disabled).
  - AI resume polish tool toggle.

### 2. Multi-Category Contact Inquiry System (`web/src/pages/Contact.tsx` & `functions/src/contact.ts`)
- **Client Form**:
  - Supports 5 inquiry categories: Candidate Assistance, Employer & Banking Partner Hiring, Training Institute Listing, Certificate Verification Query, and Grievance / Privacy Feedback.
  - Strict validation on full name, 10-digit Indian mobile number, email format, subject, and message length.
  - Confirmation card displaying unique inquiry reference ID (`msg_...`).
- **Privileged Backend (`functions/src/contact.ts`)**:
  - `submitContactForm`: Validates data server-side, generates unguessable message ID, writes to private `contact_messages/{messageId}`, and logs audit trail.
  - `updateContactMessageStatus`: Allows owner administrators and CMS managers to update message status (`unread`, `in_progress`, `resolved`), append internal notes, and record resolution timestamp.

### 3. Training Institutes Directory (`web/src/pages/Institutes.tsx`)
- Comprehensive directory of regional and national DRA preparation centers across Punjab, Chandigarh, Haryana, Delhi NCR, and Uttar Pradesh.
- Filter toolbar by state and real-time search by city or institute name.
- Badges for **"VRS Preferred"** and **"Verified IIBF Accredited Center"**.
- **Prominent Transparency Notice**: Clarifies that listings are informational and candidates must confirm accreditation on `iibf.org.in` before paying fees.

### 4. Admin CMS Settings Console (`web/src/pages/admin/CmsSettings.tsx`)
- Route: `/admin/settings` (linked directly from Recruitment Pipeline).
- **Tab 1 (Site Configuration)**: Edit operator information, address lines, emergency maintenance toggle, and announcement banners.
- **Tab 2 (Inquiries & Messages)**: View all incoming messages with real-time status badges, filter by status, and 1-click status transitions.
- **Tab 3 (Institutes Management)**: Publish and manage authorized training centers and listing notes.

---

## Step-by-Step Verification Checklist

1. **Verify Contact Inquiry Submission**:
   - Navigate to `/contact`.
   - Select an inquiry category (e.g. *Candidate Assistance & Registration*).
   - Enter your name, 10-digit mobile number, email, subject, and message.
   - Click **"Submit Message →"**.
   - Verify the confirmation screen displays your inquiry reference ID.

2. **Verify Training Institutes Directory**:
   - Navigate to `/institutes`.
   - Filter by state (e.g. *Punjab* or *Delhi NCR*).
   - Search for *"IIBF"* or *"Ludhiana"*.
   - Verify that accreditation badges, contact details, and statutory warnings are clearly displayed.

3. **Verify Admin CMS & Settings Console**:
   - Navigate to `/admin/settings`.
   - On **Site Configuration**, review the operator branding and feature switches.
   - Switch to the **Inquiries & Messages** tab and view submitted inquiries.
   - Click **"Mark In Progress"** or **"✓ Mark Resolved"** on a message to verify state transitions.
   - Switch to the **Training Institutes Directory** tab and review active listings.

4. **Verify Dynamic Homepage Banners**:
   - Navigate to `/`.
   - Observe the top announcement banner (e.g. *🚀 Immediate Urgent Openings: 150+ DRA Certified Field Agents...*).
   - Click the banner to verify it routes directly to `/jobs`.
