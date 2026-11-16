# VRS Corporate Solutions – Production Go-Live & Launch Checklist

This guide provides plain-English, step-by-step instructions for the business owner to launch the **VRS Corporate Solutions DRA Career Portal** safely, cleanly, and under budget control.

---

## 1. Connect Your Custom Domain (e.g. `careers.vrscorporate.com` or `vrsdra.com`)

Firebase Hosting provides **free automatic SSL (HTTPS)** and global Google CDN caching.

1. Open the [Firebase Console](https://console.firebase.google.com/) and select your project (**vrs-dra-portal-staging** or production).
2. In the left navigation, click **Build** → **Hosting**.
3. Click the **"Add custom domain"** button.
4. Enter your domain name (e.g. `careers.vrscorporate.com` or `vrsdra.com`).
5. Firebase will provide two DNS records:
   - **Type**: `A` record (or `CNAME` for subdomains)
   - **Value**: Google Cloud IP addresses (e.g. `199.36.158.100`)
6. Log in to your domain registrar (GoDaddy, BigRock, Hostinger, Namecheap) and add the DNS records.
7. Within 1 to 24 hours, Google automatically provisions an SSL security certificate.

---

## 2. Set Up the ₹2,000 / Month Budget Alert (Decision D2)

Protect your business from unexpected cloud bills:

1. Open [Google Cloud Billing Console](https://console.cloud.google.com/billing).
2. Select your Billing Account linked to the portal.
3. In the left menu, click **Budgets & alerts** → **"CREATE BUDGET"**.
4. **Budget name**: `VRS Portal Monthly Safety Cap`.
5. **Projects**: Select `vrs-dra-portal-staging`.
6. **Amount type**: Target amount → Enter `2000` (₹2,000 INR).
7. **Threshold rules**:
   - 50% (₹1,000) – early informational notice.
   - 90% (₹1,800) – warning notice.
   - 100% (₹2,000) – maximum alert.
8. Check **"Email alerts to billing admins"** and click **Save**.

---

## 3. Configure Phone Authentication & Free Test Numbers (Decision D1)

To test the candidate login without incurring SMS charges:

1. In the [Firebase Console](https://console.firebase.google.com/), click **Build** → **Authentication** → **Sign-in method**.
2. Click **Phone**.
3. Under **"Phone numbers for testing (optional)"**, add:
   - **Phone number**: `+91 9999999999`
   - **Six-digit verification code**: `123456`
4. Click **Save**.
5. *Anyone using this number can test login and registration anytime for 100% free with zero SMS costs.*

---

## 4. Set Daily SMS Quota Caps in Google Cloud

To protect against SMS brute-force or abuse:

1. In the [Google Cloud Console](https://console.cloud.google.com/), search for **Identity Platform**.
2. Click **Settings** → **Security**.
3. Under **SMS Quotas**, set:
   - **Daily SMS quota**: `100` (adjust upwards as candidate traffic scales).
4. Click **Save**.

---

## 5. Bootstrap the Portal Owner-Administrator Account

To grant yourself full administrative access to the Recruiter Dashboard (`/admin/recruitment`) and CMS Settings (`/admin/settings`):

1. Register or log in to the portal once using your own phone number or email so your Firebase User ID (`uid`) is created.
2. In your local terminal or Google Cloud Shell, run:
   ```bash
   GOOGLE_CLOUD_PROJECT=vrs-dra-portal-staging npx tsx scripts/bootstrap-owner-admin.ts <your-email@vrscorporate.com> <your-firebase-uid>
   ```
3. This sets the cryptographically signed `owner_admin` role claim, granting you full control over recruitment pipelines, vacancy approvals, and site settings.

---

## 6. DLT Registration Checklist for Indian SMS (Before National Scale)

Under Telecom Regulatory Authority of India (TRAI) regulations, all business SMS sent to Indian numbers must be pre-approved on a DLT platform (Jio, Airtel, Vodafone-Idea, BSNL):

1. **Entity Registration**: Register **VRS Corporate Solutions** as a Principal Entity on the Jio DLT or Airtel DLT portal.
2. **Sender ID (Header)**: Register a 6-character alphabetic Header (e.g. `VRSCOR` or `VRSSOL`).
3. **Consent Template**: Register the OTP message template:
   > *"Your VRS Corporate Solutions verification OTP is {#var#}. Valid for 5 minutes. Do not share with anyone."*
4. Once approved, you can plug in an Indian transactional SMS provider (Fast2SMS, Textlocal, Gupshup) for nationwide low-cost delivery.

---

## 7. Connecting Google Gemini AI for Free Resume Polish (Optional)

To enable the automated AI summary enhancer in the Resume Builder:

1. Visit [Google AI Studio](https://aistudio.google.com/) and click **"Get API key"** (Free tier available).
2. Store the key securely in Google Cloud Secret Manager:
   ```bash
   gcloud secrets create GEMINI_API_KEY --data-file=- --project=vrs-dra-portal-staging
   ```
3. Grant access to your Cloud Functions service account.
4. In `/admin/settings`, turn the **AI Resume Summary Helper** toggle to **Enabled**.

---

## 8. Mobile PWA App Installation for Candidates

Class 10 and Class 12 candidates can install the portal directly onto their Android smartphones as a native-like app:

1. Open the portal URL in **Google Chrome** on any mobile phone.
2. Chrome will display an automatic prompt: **"Add VRS Careers to Home screen"** (or click the three dots menu ⋮ → **Install App**).
3. An official **VRS Careers** app icon appears on their phone home screen with full offline resilience and 0-byte installation overhead.
