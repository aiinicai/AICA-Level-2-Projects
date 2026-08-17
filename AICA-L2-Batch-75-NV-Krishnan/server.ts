import express from "express";
import path from "path";
import fs from "fs";
import multer from "multer";
import { createServer as createViteServer } from "vite";
import { initializeApp as initClientApp, getApps as getClientApps } from "firebase/app";
import { getAuth, signInWithEmailAndPassword } from "firebase/auth";
import {
  getFirestore as getClientFirestore,
  doc,
  setDoc,
  getDoc,
  getDocs,
  updateDoc,
  addDoc,
  collection,
  serverTimestamp as clientServerTimestamp,
} from "firebase/firestore";
import nodemailer from "nodemailer";
import dotenv from "dotenv";
import firebaseConfig from "./firebase-applet-config.json" with { type: "json" };
import { ensureAuthUserAndProfile, cleanupPlaceholderUsers } from "./server/authHelper";

dotenv.config();

// Initialize Firebase App for Firestore operations
const clientApp = !getClientApps().length ? initClientApp(firebaseConfig) : getClientApps()[0];
const serverAuth = getAuth(clientApp);
const db = getClientFirestore(clientApp, firebaseConfig.firestoreDatabaseId);

export async function ensureServerAuth() {
  try {
    if (!serverAuth.currentUser || serverAuth.currentUser.email !== "admin@abc-associates.com") {
      await signInWithEmailAndPassword(serverAuth, "admin@abc-associates.com", "Admin@123456");
      console.log(`[ServerAuth] Authenticated as admin (${serverAuth.currentUser.uid})`);
    }
  } catch (err: any) {
    console.warn("[ServerAuth] Server auth initialization warning:", err.message);
  }
}

const COMMON_CONSENT_FOOTER = "You have the right to withdraw this consent at any time, and to request correction or erasure of your personal data, subject to our legal retention obligations. To exercise these rights or raise a grievance, contact our Grievance Officer at CA Ritu Sharma, grievance@abcassociates.in (assumed name for demo purposes).";

// TOP-LEVEL 7 SERVICES DEFINITION
export const TOP_LEVEL_SERVICES = [
  {
    id: "statutory-audit",
    name: "Statutory Audit",
    consentTemplate: {
      body: `ABC & Associates, Chartered Accountants, acts as the Data Fiduciary under the Digital Personal Data Protection Act, 2023 (Section 2(i)) for this engagement. We are collecting your financial statements, accounting records, and supporting documents to conduct your statutory audit under the Companies Act, 2013. This data will be retained for 8 years from the end of the relevant financial year, as required under Section 128(5), Companies Act, 2013. It will not be used for any purpose beyond this engagement.

${COMMON_CONSENT_FOOTER}`,
      version: 1,
    },
    retentionPolicy: {
      basis: "from_date",
      years: 8,
      statute: "Companies Act 2013 s.128(5)",
    },
  },
  {
    id: "tax-audit",
    name: "Tax Audit",
    consentTemplate: {
      body: `ABC & Associates, Chartered Accountants, acts as the Data Fiduciary under the Digital Personal Data Protection Act, 2023 (Section 2(i)) for this engagement. We are collecting your books of account and supporting documents to conduct your tax audit under the Income-tax Act. This data will be retained for 7 tax years from the end of the relevant tax year, as prescribed under Section 62, Income-tax Act, 2025, read with Rule 46(9), Income-tax Rules, 2026. If the assessment for a year is reopened, records for that year are retained until the reopened assessment is finally disposed of.

${COMMON_CONSENT_FOOTER}`,
      version: 1,
    },
    retentionPolicy: {
      basis: "from_date",
      years: 7,
      statute: "Income-tax Act 2025, Section 62 read with Rule 46(9), Income-tax Rules 2026",
    },
  },
  {
    id: "income-tax-services",
    name: "Income Tax services",
    consentTemplate: {
      body: `ABC & Associates, Chartered Accountants, acts as the Data Fiduciary under the Digital Personal Data Protection Act, 2023 (Section 2(i)) for this engagement. We are collecting your income, investment, and transaction details to prepare and file your income tax return / represent you in income-tax assessment or appellate proceedings. This data will be retained for 7 tax years from the end of the relevant tax year, as prescribed under Section 62, Income-tax Act, 2025, read with Rule 46(9), Income-tax Rules, 2026. If a proceeding is pending at the end of that period, the relevant records are retained until one year after its final disposal.

${COMMON_CONSENT_FOOTER}`,
      version: 1,
    },
    retentionPolicy: {
      basis: "from_date",
      years: 7,
      statute: "Income-tax Act 2025, Section 62 read with Rule 46(9), Income-tax Rules 2026",
    },
  },
  {
    id: "gst-services",
    name: "GST services",
    consentTemplate: {
      body: `ABC & Associates, Chartered Accountants, acts as the Data Fiduciary under the Digital Personal Data Protection Act, 2023 (Section 2(i)) for this engagement. We are collecting your sales, purchase, and transaction records to prepare and file your GST returns / represent you in GST assessment or appellate proceedings. This data will be retained for 72 months from the due date of furnishing the annual return for the relevant year, as required under Section 36, CGST Act, 2017. If a proceeding is pending at the end of that period, the relevant records are retained until one year after its final disposal.

${COMMON_CONSENT_FOOTER}`,
      version: 1,
    },
    retentionPolicy: {
      basis: "from_date",
      years: 6,
      statute: "CGST Act 2017 s.36",
    },
  },
  {
    id: "accounting-services",
    name: "Accounting services",
    consentTemplate: {
      body: `ABC & Associates, Chartered Accountants, acts as a Data Processor under the Digital Personal Data Protection Act, 2023 (Section 2(k)) for the purpose of providing your bookkeeping and accounting services. We are collecting your transaction records and supporting vouchers solely to carry out this engagement. This data will be retained only for the duration of our engagement contract with you and will be erased within 60 days of the contract ending or being terminated, unless you engage us on a continuing basis, in which case retention continues for the duration of that continuing engagement.

${COMMON_CONSENT_FOOTER}`,
      version: 1,
    },
    retentionPolicy: {
      basis: "contract_tenure",
      years: null,
      statute: null,
    },
  },
  {
    id: "finance-consulting-services",
    name: "Finance-related consulting services",
    consentTemplate: {
      body: `ABC & Associates, Chartered Accountants, acts as a Data Processor under the Digital Personal Data Protection Act, 2023 (Section 2(k)) for the purpose of providing the consulting services described in our terms of engagement. We are collecting the financial and business information you share solely to carry out this engagement. This data will be retained only for the duration of our engagement contract with you and will be erased within 60 days of the contract ending or being terminated.

${COMMON_CONSENT_FOOTER}`,
      version: 1,
    },
    retentionPolicy: {
      basis: "contract_tenure",
      years: null,
      statute: null,
    },
  },
  {
    id: "internal-audit-services",
    name: "Internal audit services",
    consentTemplate: {
      body: `ABC & Associates, Chartered Accountants, acts as the Data Fiduciary under the Digital Personal Data Protection Act, 2023 (Section 2(i)) for this engagement. We are collecting your operational and financial records to conduct internal audit procedures as engaged. Where you are a company for which internal audit is mandatory under Section 138, Companies Act, 2013, these records are retained alongside your statutory books for 8 years under Section 128(5), Companies Act, 2013. For all other engagements, records are retained for 7 years from completion under our firm's ICAI SQC 1 retention policy, and erased thereafter.

${COMMON_CONSENT_FOOTER}`,
      version: 1,
    },
    retentionPolicy: {
      basis: "from_date",
      years: null,
      statute: "Companies Act 2013 s.138 (Mandatory company: 8 years) / Non-company or non-mandatory: 7 years under Income-tax Act 2025, Section 62 read with Rule 46(9)",
      entityDependent: true,
      conditionalRules: {
        companyMandatory: 8,
        nonCompanyOrNonMandatory: 7,
      },
      note: "Entity-dependent retention: 8 years for mandatory Companies Act s.138 audits, 7 years for non-company or non-mandatory internal audits.",
    },
  },
];

// Calculate explicit Erasure Due Date according to exact statutory rules
export function calculateErasureDueDate(
  serviceId: string,
  entityType: "company" | "non_company",
  contractEndDateStr: string
): string {
  const endDate = new Date(contractEndDateStr);
  if (isNaN(endDate.getTime())) {
    return contractEndDateStr;
  }

  const service = TOP_LEVEL_SERVICES.find((s) => s.id === serviceId);
  const basis = service?.retentionPolicy.basis || "contract_tenure";

  if (basis === "contract_tenure") {
    // contractEndDate + 60 days
    const result = new Date(endDate);
    result.setDate(result.getDate() + 60);
    return result.toISOString().split("T")[0];
  } else {
    // from_date basis
    let years = service?.retentionPolicy.years || 7;
    if (serviceId === "internal-audit-services") {
      years = entityType === "company" ? 8 : 7;
    }

    const result = new Date(endDate);
    result.setFullYear(result.getFullYear() + years);
    result.setDate(result.getDate() + 60);
    return result.toISOString().split("T")[0];
  }
}

// Helper to send real single combined email with DPDP Notice and Login Credentials via real SMTP
export async function sendEngagementCombinedEmail({
  clientEmail,
  clientName,
  serviceName,
  consentNoticeBody,
  erasureDueDate,
  appLoginUrl,
}: {
  clientEmail: string;
  clientName: string;
  serviceName: string;
  consentNoticeBody: string;
  erasureDueDate: string;
  appLoginUrl: string;
}) {
  const smtpEmail = (
    process.env.SMTP_EMAIL ||
    process.env.SMTP_USER ||
    process.env.EMAIL_USER ||
    process.env.GMAIL_USER ||
    ""
  ).trim();

  const smtpPass = (
    process.env.SMTP_APP_PASSWORD ||
    process.env.SMTP_PASSWORD ||
    process.env.SMTP_PASS ||
    process.env.EMAIL_PASSWORD ||
    process.env.EMAIL_PASS ||
    process.env.GMAIL_APP_PASSWORD ||
    ""
  ).trim();

  const smtpHost = (process.env.SMTP_HOST || "smtp.gmail.com").trim();
  const smtpPort = parseInt(process.env.SMTP_PORT || "587", 10);

  if (!smtpEmail || !smtpPass) {
    throw new Error(
      `Real SMTP configuration is missing: SMTP_EMAIL and SMTP_APP_PASSWORD must be configured in environment variables or Settings Secrets. (Target host: ${smtpHost}:${smtpPort})`
    );
  }

  const subject = `Action Required: Document Access Setup — ${serviceName} Engagement`;

  const textBody = `Dear ${clientName},

ABC & Associates, Chartered Accountants, has set up a secure document folder for your ${serviceName} engagement with us.

Before any documents can be exchanged, please read the notice below, which explains what personal data we will collect for this engagement, why, and for how long we are required to keep it.

---
${consentNoticeBody}
---

This data is scheduled to be erased by ${erasureDueDate} unless the engagement continues or a legal proceeding requires longer retention.

To proceed, log in to your account using the credentials below, then click "I Consent" on your dashboard to unlock document upload for your folder:

Login Email: ${clientEmail}
Password: Client@2026

[Go to Login Page] -> ${appLoginUrl}

If you have any questions about this notice or how your data will be used, please contact our Grievance Officer at CA Ritu Sharma, grievance@abcassociates.in (assumed name for demo purposes).

Regards,
ABC & Associates, Chartered Accountants`;

  const htmlBody = `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 620px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff; color: #1e293b;">
      <div style="margin-bottom: 20px;">
        <span style="background-color: #4f46e5; color: #ffffff; font-weight: bold; font-size: 14px; padding: 6px 12px; border-radius: 6px; display: inline-block;">ABC</span>
        <span style="font-size: 16px; font-weight: bold; color: #0f172a; margin-left: 8px;">ABC & Associates</span>
        <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Chartered Accountants — Client Workflow Portal</div>
      </div>

      <p style="font-size: 15px; margin-top: 0;">Dear <strong>${clientName}</strong>,</p>

      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        ABC & Associates, Chartered Accountants, has set up a secure document folder for your <strong>${serviceName}</strong> engagement with us.
      </p>

      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        Before any documents can be exchanged, please read the notice below, which explains what personal data we will collect for this engagement, why, and for how long we are required to keep it.
      </p>

      <div style="background-color: #f8fafc; border-left: 4px solid #4f46e5; padding: 14px 18px; margin: 20px 0; border-radius: 0 8px 8px 0;">
        <div style="font-size: 11px; text-transform: uppercase; font-weight: bold; color: #64748b; margin-bottom: 6px;">DPDP Statutory Notice & Processing Purpose</div>
        <div style="font-size: 13px; line-height: 1.6; color: #1e293b; font-style: italic;">
          ${consentNoticeBody}
        </div>
      </div>

      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        This data is scheduled to be erased by <strong>${erasureDueDate}</strong> unless the engagement continues or a legal proceeding requires longer retention.
      </p>

      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        To proceed, log in to your account using the credentials below, then click "I Consent" on your dashboard to unlock document upload for your folder:
      </p>

      <div style="background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px 18px; margin: 20px 0;">
        <div style="font-size: 13px; margin-bottom: 6px;"><strong>Login Email:</strong> <code style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; color: #0f172a; font-weight: bold;">${clientEmail}</code></div>
        <div style="font-size: 13px;"><strong>Password:</strong> <code style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; color: #0f172a; font-weight: bold;">Client@2026</code></div>
      </div>

      <div style="text-align: center; margin: 26px 0;">
        <a href="${appLoginUrl}" style="background-color: #4f46e5; color: #ffffff; padding: 12px 28px; text-decoration: none; font-weight: 600; font-size: 14px; border-radius: 8px; display: inline-block;">Go to Login Page</a>
      </div>

      <p style="font-size: 12px; line-height: 1.6; color: #64748b;">
        If you have any questions about this notice or how your data will be used, please contact our Grievance Officer at CA Ritu Sharma, <a href="mailto:grievance@abcassociates.in" style="color: #4f46e5;">grievance@abcassociates.in</a> (assumed name for demo purposes).
      </p>

      <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0 16px 0;" />

      <p style="font-size: 13px; color: #475569; margin-bottom: 4px;">Regards,</p>
      <p style="font-size: 13px; font-weight: bold; color: #0f172a; margin-top: 0;">ABC & Associates, Chartered Accountants</p>
    </div>
  `;

  console.log(`[SMTP] Initializing real SMTP transport: ${smtpHost}:${smtpPort} (user: ${smtpEmail})...`);

  const transporter = nodemailer.createTransport({
    host: smtpHost,
    port: smtpPort,
    secure: smtpPort === 465,
    auth: {
      user: smtpEmail,
      pass: smtpPass,
    },
    tls: {
      rejectUnauthorized: false,
    },
  });

  const method = `smtp://${smtpHost}:${smtpPort} (${smtpEmail})`;

  const mailOptions = {
    from: `"ABC & Associates Chartered Accountants" <${smtpEmail}>`,
    to: clientEmail,
    subject,
    text: textBody,
    html: htmlBody,
  };

  const info = await transporter.sendMail(mailOptions);
  console.log(`[SMTP Real Delivery Confirmed] MessageId: ${info.messageId} to ${clientEmail} via ${smtpHost}:${smtpPort}`);

  return {
    sent: true,
    messageId: info.messageId,
    method,
    envelope: info.envelope,
    accepted: info.accepted,
    response: info.response,
  };
}

// Helper to send generic notification email when a pending item is added
export async function sendPendingItemNotificationEmail({
  clientEmail,
  clientName,
  serviceName,
  appLoginUrl,
}: {
  clientEmail: string;
  clientName: string;
  serviceName: string;
  appLoginUrl: string;
}) {
  const smtpEmail = (
    process.env.SMTP_EMAIL ||
    process.env.SMTP_USER ||
    process.env.EMAIL_USER ||
    process.env.GMAIL_USER ||
    ""
  ).trim();

  const smtpPass = (
    process.env.SMTP_APP_PASSWORD ||
    process.env.SMTP_PASSWORD ||
    process.env.SMTP_PASS ||
    process.env.EMAIL_PASSWORD ||
    process.env.EMAIL_PASS ||
    process.env.GMAIL_APP_PASSWORD ||
    ""
  ).trim();

  const smtpHost = (process.env.SMTP_HOST || "smtp.gmail.com").trim();
  const smtpPort = parseInt(process.env.SMTP_PORT || "587", 10);

  if (!smtpEmail || !smtpPass) {
    throw new Error(
      `Real SMTP configuration is missing: SMTP_EMAIL and SMTP_APP_PASSWORD must be configured in environment variables or Settings Secrets. (Target host: ${smtpHost}:${smtpPort})`
    );
  }

  const subject = `Update on your ${serviceName} engagement — ABC & Associates`;

  const textBody = `Dear ${clientName},

There is a new update on your ${serviceName} engagement. Please log in to view details.

Access Portal: ${appLoginUrl}

Regards,
ABC & Associates, Chartered Accountants`;

  const htmlBody = `
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff; color: #1e293b;">
      <div style="margin-bottom: 20px;">
        <span style="background-color: #4f46e5; color: #ffffff; font-weight: bold; font-size: 14px; padding: 6px 12px; border-radius: 6px; display: inline-block;">ABC</span>
        <span style="font-size: 16px; font-weight: bold; color: #0f172a; margin-left: 8px;">ABC & Associates</span>
        <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Chartered Accountants — Client Workflow Portal</div>
      </div>

      <p style="font-size: 15px; margin-top: 0;">Dear <strong>${clientName}</strong>,</p>

      <p style="font-size: 14px; line-height: 1.6; color: #334155;">
        There is a new update on your <strong>${serviceName}</strong> engagement. Please log in to view details.
      </p>

      <div style="text-align: center; margin: 26px 0;">
        <a href="${appLoginUrl}" style="background-color: #4f46e5; color: #ffffff; padding: 12px 28px; text-decoration: none; font-weight: 600; font-size: 14px; border-radius: 8px; display: inline-block;">Log In to Portal</a>
      </div>

      <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0 16px 0;" />

      <p style="font-size: 13px; color: #475569; margin-bottom: 4px;">Regards,</p>
      <p style="font-size: 13px; font-weight: bold; color: #0f172a; margin-top: 0;">ABC & Associates, Chartered Accountants</p>
    </div>
  `;

  console.log(`[SMTP] Dispatching Pending Item generic notice to ${clientEmail}...`);

  const transporter = nodemailer.createTransport({
    host: smtpHost,
    port: smtpPort,
    secure: smtpPort === 465,
    auth: {
      user: smtpEmail,
      pass: smtpPass,
    },
    tls: {
      rejectUnauthorized: false,
    },
  });

  const mailOptions = {
    from: `"ABC & Associates Chartered Accountants" <${smtpEmail}>`,
    to: clientEmail,
    subject,
    text: textBody,
    html: htmlBody,
  };

  const info = await transporter.sendMail(mailOptions);
  console.log(`[SMTP Pending Item Notification Sent] MessageId: ${info.messageId} to ${clientEmail}`);

  return {
    sent: true,
    messageId: info.messageId,
  };
}

async function startServer() {
  const app = express();

  // CORS and Preflight Handling for iframe and cross-origin environments
  app.use((req, res, next) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Authorization, x-user-role");
    res.header("Access-Control-Expose-Headers", "Content-Type, Content-Length, Content-Disposition, *");
    if (req.method === "OPTIONS") {
      return res.sendStatus(204);
    }
    next();
  });

  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ extended: true, limit: "50mb" }));

  const PORT = 3000;

  // Initialize server-side auth session
  await ensureServerAuth();

  // Health route
  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok", timestamp: new Date().toISOString() });
  });

  // BOOTSTRAP ENDPOINT: Seeds Services, Admin & Staff Auth Users ONLY (NO AUTO-CREATED ENGAGEMENTS)
  app.post("/api/bootstrap", async (_req, res) => {
    try {
      console.log("[Bootstrap] Running database seed check...");

      // 1. Seed 7 Services
      const servicesSnapshot = await getDocs(collection(db, "services"));
      const existingServiceIds = new Set(servicesSnapshot.docs.map((d) => d.id));

      const seededServices: string[] = [];
      for (const service of TOP_LEVEL_SERVICES) {
        const { id, ...data } = service;
        await setDoc(doc(db, "services", id), data);
        if (!existingServiceIds.has(id)) {
          seededServices.push(service.name);
        }
      }

      // 2. Ensure Real Firebase Auth Users with exact matching UIDs
      await cleanupPlaceholderUsers();

      const adminEmail = "admin@abc-associates.com";
      const adminAuthRes = await ensureAuthUserAndProfile(
        adminEmail,
        "Admin@123456",
        "full_admin",
        "Senior Partner (Admin)"
      );

      const staffEmail = "auditor@abc-associates.com";
      const staffAuthRes = await ensureAuthUserAndProfile(
        staffEmail,
        "Audit@123456",
        "team_member",
        "Audit Manager (Staff)"
      );

      // Explicitly NO auto-creation of engagements or folders here.
      // Engagements are created on demand by explicit admin action only.

      res.json({
        success: true,
        message: "Database initialized successfully (Services & Staff accounts ready)",
        servicesCount: TOP_LEVEL_SERVICES.length,
        seededServices,
        adminUser: {
          email: adminEmail,
          role: "full_admin",
          uid: adminAuthRes.uid,
        },
        staffUser: {
          email: staffEmail,
          role: "team_member",
          uid: staffAuthRes.uid,
        },
      });
    } catch (err: any) {
      console.error("[Bootstrap Error]", err);
      res.status(500).json({ success: false, error: err.message });
    }
  });

  // CREATE USER ENDPOINT (Admin creates Client or Staff User with real Firebase Auth)
  app.post("/api/admin/create-user", async (req, res) => {
    try {
      const { email, password, role, displayName, linkedClientId } = req.body;

      if (!email || !role) {
        return res.status(400).json({ success: false, error: "email and role are required" });
      }

      const defaultPass = role === "client" ? "Client@2026" : "Audit@123456";
      const userPass = password || defaultPass;

      const authRes = await ensureAuthUserAndProfile(
        email.trim(),
        userPass,
        role,
        displayName || email.split("@")[0],
        linkedClientId
      );

      res.json({
        success: true,
        uid: authRes.uid,
        isExistingAccount: authRes.isExistingAccount,
        user: {
          uid: authRes.uid,
          email,
          role,
          linkedClientId: linkedClientId || null,
          isActive: true,
        },
      });
    } catch (err: any) {
      console.error("[Create User Error]", err);
      res.status(500).json({ success: false, error: err.message });
    }
  });

  // CREATE ENGAGEMENT & SEND COMBINED EMAIL (Admin creates engagement, real SMTP email fires ONCE)
  app.post("/api/engagements/create-and-notify", async (req, res) => {
    let engagementId = "";
    try {
      await ensureServerAuth();
      const {
        clientId,
        serviceId,
        contractStartDate,
        contractEndDate,
        actorUid,
        actorEmail,
        assignedTeamMemberIds,
      } = req.body;

      if (!clientId || !serviceId || !contractStartDate || !contractEndDate) {
        return res.status(400).json({
          success: false,
          error: "clientId, serviceId, contractStartDate, and contractEndDate are required",
        });
      }

      // 1. Fetch Client Details
      const clientSnap = await getDoc(doc(db, "clients", clientId));
      if (!clientSnap.exists()) {
        return res.status(404).json({ success: false, error: "Client not found" });
      }
      const clientData = clientSnap.data();
      const clientEmail = clientData.email;
      const clientName = clientData.name;
      const entityType = clientData.entityType || "company";

      // 2. Fetch Service Details
      const serviceSnap = await getDoc(doc(db, "services", serviceId));
      let serviceName = serviceId;
      let consentNoticeBody = "Consent for processing engagement data and compliance documents under statutory frameworks.";

      if (serviceSnap.exists()) {
        const sData = serviceSnap.data();
        serviceName = sData.name || serviceId;
        consentNoticeBody = sData.consentTemplate?.body || consentNoticeBody;
      } else {
        const fallbackService = TOP_LEVEL_SERVICES.find((s) => s.id === serviceId);
        if (fallbackService) {
          serviceName = fallbackService.name;
          consentNoticeBody = fallbackService.consentTemplate.body;
        }
      }

      // 3. Calculate Statutory Erasure Due Date
      const erasureDueDate = calculateErasureDueDate(serviceId, entityType, contractEndDate);

      // 4. Ensure Real Firebase Auth User Account for Client with FIXED Password "Client@2026"
      const authRes = await ensureAuthUserAndProfile(
        clientEmail,
        "Client@2026",
        "client",
        clientName,
        clientId
      );

      // Re-ensure server is operating under admin credentials for creating engagement & logs
      await ensureServerAuth();

      // 5. Determine assigned team members
      let teamIds: string[] = [];
      if (Array.isArray(assignedTeamMemberIds) && assignedTeamMemberIds.length > 0) {
        teamIds = assignedTeamMemberIds.filter((id) => typeof id === "string" && id.trim().length > 0);
      } else if (actorUid) {
        teamIds = [actorUid];
      }

      // 6. Create Engagement in Firestore initially with "PENDING"
      const engRef = doc(collection(db, "engagements"));
      engagementId = engRef.id;

      const engagementPayload: any = {
        clientId,
        serviceId,
        assignedTeamMemberIds: teamIds,
        status: "WIP",
        consentStatus: "PENDING",
        contractStartDate,
        contractEndDate,
        erasureDueDate,
        createdAt: clientServerTimestamp(),
        updatedAt: clientServerTimestamp(),
      };

      await setDoc(engRef, engagementPayload);

      // 6. Send SINGLE Combined Email (DPDP Consent Notice + Login Credentials) via Real SMTP
      const host = process.env.APP_URL || `${req.protocol}://${req.get("host")}`;
      const appLoginUrl = `${host}/`;

      let emailResult;
      try {
        emailResult = await sendEngagementCombinedEmail({
          clientEmail,
          clientName,
          serviceName,
          consentNoticeBody,
          erasureDueDate,
          appLoginUrl,
        });

        // 7. On confirmed success: mark "SENT"
        await updateDoc(engRef, {
          consentStatus: "SENT",
          emailDelivery: {
            status: "SENT",
            method: emailResult.method,
            messageId: emailResult.messageId,
            timestamp: new Date().toISOString(),
          },
          updatedAt: clientServerTimestamp(),
        });

        // 8. Log in append-only consentLog
        await addDoc(collection(db, "consentLog"), {
          engagementId,
          clientId,
          serviceId,
          serviceName,
          action: "SENT",
          timestamp: clientServerTimestamp(),
          actorUid: actorUid || "system_admin",
          actorEmail: actorEmail || "admin@abc-associates.com",
          clientEmail,
          notes: `Combined setup & DPDP consent notice sent via ${emailResult.method} (MessageId: ${emailResult.messageId})`,
        });

        res.json({
          success: true,
          engagementId,
          engagement: {
            id: engagementId,
            ...engagementPayload,
            consentStatus: "SENT",
          },
          clientUser: {
            uid: authRes.uid,
            email: clientEmail,
            fixedPassword: "Client@2026",
            isExistingAccount: authRes.isExistingAccount,
          },
          emailResult,
        });
      } catch (emailErr: any) {
        console.error("[Email Dispatch Error in Engagement Creation]", emailErr);
        // Mark as SEND_FAILED so UI never shows false positive
        await updateDoc(engRef, {
          consentStatus: "SEND_FAILED",
          emailDelivery: {
            status: "FAILED",
            error: emailErr.message || "Failed to send email via SMTP transporter",
            timestamp: new Date().toISOString(),
          },
          updatedAt: clientServerTimestamp(),
        });

        await addDoc(collection(db, "consentLog"), {
          engagementId,
          clientId,
          serviceId,
          serviceName,
          action: "SEND_FAILED",
          timestamp: clientServerTimestamp(),
          actorUid: actorUid || "system_admin",
          actorEmail: actorEmail || "admin@abc-associates.com",
          clientEmail,
          notes: `Email dispatch failed: ${emailErr.message}`,
        });

        return res.status(500).json({
          success: false,
          engagementId,
          error: `Engagement folder created, but email dispatch failed: ${emailErr.message}`,
          emailDeliveryFailed: true,
        });
      }
    } catch (err: any) {
      console.error("[Create Engagement & Notify Error]", err);
      res.status(500).json({ success: false, error: err.message, engagementId });
    }
  });

  // ASSIGN TEAM MEMBERS ENDPOINT
  app.post("/api/engagements/:id/assign-team", async (req, res) => {
    const { id } = req.params;
    const { assignedTeamMemberIds, actorUid, actorEmail } = req.body;

    if (!Array.isArray(assignedTeamMemberIds)) {
      return res.status(400).json({ success: false, error: "assignedTeamMemberIds array is required" });
    }

    try {
      const engRef = doc(db, "engagements", id);
      const engSnap = await getDoc(engRef);
      if (!engSnap.exists()) {
        return res.status(404).json({ success: false, error: "Engagement not found" });
      }

      const teamIds = assignedTeamMemberIds.filter((tId) => typeof tId === "string" && tId.trim().length > 0);

      await updateDoc(engRef, {
        assignedTeamMemberIds: teamIds,
        updatedAt: clientServerTimestamp(),
      });

      res.json({
        success: true,
        engagementId: id,
        assignedTeamMemberIds: teamIds,
      });
    } catch (err: any) {
      console.error("[Assign Team Error]", err);
      res.status(500).json({ success: false, error: err.message });
    }
  });

  // UPLOAD STORAGE CONFIGURATION
  const uploadsBaseDir = path.join(process.cwd(), "uploads");
  if (!fs.existsSync(uploadsBaseDir)) {
    fs.mkdirSync(uploadsBaseDir, { recursive: true });
  }

  const upload = multer({
    storage: multer.memoryStorage(),
    limits: {
      fileSize: 50 * 1024 * 1024, // 50 MB limit
    },
  });

  // REAL ENGAGEMENT DOCUMENT UPLOAD ENDPOINT
  app.post("/api/engagements/:id/upload-document", (req, res, next) => {
    upload.single("file")(req, res, (err: any) => {
      if (err) {
        console.error("[Multer Upload Error]", err);
        return res.status(400).json({
          success: false,
          error: err instanceof multer.MulterError ? `Upload Error: ${err.message}` : (err.message || "File upload failed"),
        });
      }
      next();
    });
  }, async (req, res) => {
    const { id } = req.params;
    const { uploadedByUid, uploadedByName, uploadedByRole, actorEmail } = req.body;

    console.log(`[Upload Request Received] Engagement: ${id} | Role: ${uploadedByRole} | UID: ${uploadedByUid} | Name: ${uploadedByName} | Email: ${actorEmail} | File: ${req.file?.originalname} (${req.file?.size} bytes)`);

    if (!req.file) {
      console.warn(`[Upload Rejected: No File] Engagement: ${id}`);
      return res.status(400).json({ success: false, error: "No file was attached for upload." });
    }

    try {
      await ensureServerAuth();
      // 1. Fetch Engagement
      const engRef = doc(db, "engagements", id);
      const engSnap = await getDoc(engRef);
      if (!engSnap.exists()) {
        console.warn(`[Upload Rejected: Not Found] Engagement ${id} does not exist`);
        return res.status(404).json({ success: false, error: "Engagement folder not found." });
      }
      const engData = engSnap.data();

      // 2. Fetch User Profile to verify role & access control
      let userRole = uploadedByRole;
      let linkedClientId = "";
      let resolvedName = uploadedByName || actorEmail || "User";

      if (uploadedByUid) {
        const userSnap = await getDoc(doc(db, "users", uploadedByUid));
        if (userSnap.exists()) {
          const uData = userSnap.data();
          userRole = uData.role || userRole;
          linkedClientId = uData.linkedClientId || "";
          resolvedName = uData.displayName || uData.email || resolvedName;
        }
      }

      // 3. Strict Access Control Verification:
      // Allow only:
      // - full_admin (firm partners can upload to any engagement)
      // - assigned team members (team members explicitly assigned in assignedTeamMemberIds)
      // - client who owns this engagement
      let isAuthorized = false;
      let authReason = "";

      if (userRole === "full_admin") {
        isAuthorized = true;
        authReason = "Full administrator privileges";
      } else if (userRole === "team_member") {
        if (Array.isArray(engData.assignedTeamMemberIds) && engData.assignedTeamMemberIds.includes(uploadedByUid)) {
          isAuthorized = true;
          authReason = "Assigned team member on engagement";
        } else {
          authReason = `Team member (${uploadedByUid}) is not assigned to engagement (assigned: ${JSON.stringify(engData.assignedTeamMemberIds || [])})`;
        }
      } else if (userRole === "client") {
        if (linkedClientId === engData.clientId || engData.clientId === req.body.clientId) {
          isAuthorized = true;
          authReason = "Client owner of engagement";
        } else {
          authReason = `Client (${linkedClientId}) does not match engagement client (${engData.clientId})`;
        }
      }

      if (!isAuthorized) {
        console.warn(`[Upload Denied 403] Engagement: ${id} | Role: ${userRole} | UID: ${uploadedByUid} | Reason: ${authReason}`);
        return res.status(403).json({
          success: false,
          error: `Access denied: Only the client owner, assigned team members, or administrators can upload to this engagement. (${authReason})`,
        });
      }

      // 4. Create Document in Engagement Subcollection
      const docsColRef = collection(db, "engagements", id, "documents");
      const newDocRef = doc(docsColRef);
      const docId = newDocRef.id;

      // Scoped path in storage
      const sanitizedFilename = req.file.originalname.replace(/[^a-zA-Z0-9._-]/g, "_");
      const storagePath = `engagements/${id}/documents/${docId}/${sanitizedFilename}`;

      // Save file to engagement-scoped filesystem directory
      const engagementDir = path.join(uploadsBaseDir, "engagements", id);
      if (!fs.existsSync(engagementDir)) {
        fs.mkdirSync(engagementDir, { recursive: true });
      }

      const localFilePath = path.join(engagementDir, `${docId}_${sanitizedFilename}`);
      fs.writeFileSync(localFilePath, req.file.buffer);

      const downloadUrl = `/api/engagements/${id}/documents/${docId}/download`;

      const documentRecord = {
        id: docId,
        name: req.file.originalname,
        fileName: req.file.originalname,
        storagePath: storagePath,
        url: downloadUrl,
        uploadedBy: resolvedName,
        uploadedByUid: uploadedByUid || "",
        uploadedByName: resolvedName,
        uploadedByRole: userRole || "client",
        uploadedAt: clientServerTimestamp(),
        fileType: req.file.mimetype || "application/octet-stream",
        fileSize: req.file.size,
      };

      await setDoc(newDocRef, documentRecord);
      console.log(`[Upload Confirmed 200 OK] Document ID: ${docId} | Engagement: ${id} | File: ${req.file.originalname} | Uploaded By: ${resolvedName} (${userRole}) | Auth: ${authReason}`);

      res.json({
        success: true,
        document: documentRecord,
      });
    } catch (err: any) {
      console.error("[Document Upload Error]", err);
      res.status(500).json({ success: false, error: err.message });
    }
  });

  // REAL ENGAGEMENT DOCUMENT DOWNLOAD / STREAMING ENDPOINT
  app.get("/api/engagements/:id/documents/:docId/download", async (req, res) => {
    const { id, docId } = req.params;
    const requesterRole = (req.query.role as string) || (req.headers["x-user-role"] as string);

    try {
      await ensureServerAuth();
      const docRef = doc(db, "engagements", id, "documents", docId);
      const docSnap = await getDoc(docRef);

      if (!docSnap.exists()) {
        return res.status(404).send("Document not found in database.");
      }

      const docData = docSnap.data();

      // Enforce data-layer document visibility rule:
      // If the caller is identified as a client and the document was NOT uploaded by client, reject access.
      if (requesterRole === "client" && docData.uploadedByRole !== "client") {
        return res.status(403).send("Access Denied: Internal working papers are confidential to firm staff and not accessible to clients.");
      }

      const sanitizedFilename = (docData.fileName || docData.name || "document.pdf").replace(/[^a-zA-Z0-9._-]/g, "_");
      const localFilePath = path.join(uploadsBaseDir, "engagements", id, `${docId}_${sanitizedFilename}`);

      if (fs.existsSync(localFilePath)) {
        res.setHeader("Content-Disposition", `attachment; filename="${docData.fileName || docData.name}"`);
        res.setHeader("Content-Type", docData.fileType || "application/octet-stream");
        return res.sendFile(localFilePath);
      }

      // Fallback: If dummy URL or external
      if (docData.url && docData.url.startsWith("http")) {
        return res.redirect(docData.url);
      }

      res.status(404).send("Physical file not found on server.");
    } catch (err: any) {
      console.error("[Download Error]", err);
      res.status(500).send(`Download failed: ${err.message}`);
    }
  });

  // REAL EMAIL SENDING VIA SMTP / NODEMAILER (standalone re-send or manual trigger)
  app.post("/api/send-consent-email", async (req, res) => {
    const { engagementId, clientEmail, clientName, serviceName, erasureDueDate } = req.body;
    if (!engagementId || !clientEmail) {
      return res.status(400).json({ success: false, error: "engagementId and clientEmail are required" });
    }

    const engRef = doc(db, "engagements", engagementId);
    let currentServiceName = serviceName || "Statutory Audit";
    let currentClientId = "";
    let currentServiceId = "";

    try {
      const host = process.env.APP_URL || `${req.protocol}://${req.get("host")}`;
      const appLoginUrl = `${host}/`;

      // Fetch service consent notice body
      const engSnap = await getDoc(engRef);
      let consentNoticeBody = "Consent for processing statutory and regulatory compliance records.";

      if (engSnap.exists()) {
        const engData = engSnap.data();
        currentClientId = engData.clientId || "";
        currentServiceId = engData.serviceId || "";
        const sSnap = await getDoc(doc(db, "services", engData.serviceId));
        if (sSnap.exists()) {
          const sData = sSnap.data();
          currentServiceName = sData.name || currentServiceName;
          consentNoticeBody = sData.consentTemplate?.body || consentNoticeBody;
        }
      }

      const emailResult = await sendEngagementCombinedEmail({
        clientEmail,
        clientName: clientName || "Valued Client",
        serviceName: currentServiceName,
        consentNoticeBody,
        erasureDueDate: erasureDueDate || "Per engagement terms",
        appLoginUrl,
      });

      // Update engagement consentStatus to "SENT" ONLY on genuine success
      await updateDoc(engRef, {
        consentStatus: "SENT",
        emailDelivery: {
          status: "SENT",
          method: emailResult.method,
          messageId: emailResult.messageId,
          timestamp: new Date().toISOString(),
        },
        updatedAt: clientServerTimestamp(),
      });

      // Log in consentLog
      await addDoc(collection(db, "consentLog"), {
        engagementId,
        clientId: currentClientId,
        serviceId: currentServiceId,
        serviceName: currentServiceName,
        action: "SENT",
        timestamp: clientServerTimestamp(),
        actorUid: "system_admin",
        actorEmail: "admin@abc-associates.com",
        clientEmail,
        notes: `Combined notice re-sent via ${emailResult.method} (MessageId: ${emailResult.messageId})`,
      });

      res.json({
        success: true,
        engagementId,
        emailResult,
        updatedStatus: "SENT",
      });
    } catch (err: any) {
      console.error("[Email Error in send-consent-email]", err);
      // Mark as SEND_FAILED on failure
      try {
        await updateDoc(engRef, {
          consentStatus: "SEND_FAILED",
          emailDelivery: {
            status: "FAILED",
            error: err.message || "SMTP transmission error",
            timestamp: new Date().toISOString(),
          },
          updatedAt: clientServerTimestamp(),
        });

        await addDoc(collection(db, "consentLog"), {
          engagementId,
          clientId: currentClientId,
          serviceId: currentServiceId,
          serviceName: currentServiceName,
          action: "SEND_FAILED",
          timestamp: clientServerTimestamp(),
          actorUid: "system_admin",
          actorEmail: "admin@abc-associates.com",
          clientEmail,
          notes: `System send failure: ${err.message}`,
        });
      } catch (dbErr) {
        console.error("Failed to log SEND_FAILED to db:", dbErr);
      }

      res.status(500).json({ success: false, error: err.message });
    }
  });

  // CREATE PENDING ITEM & SEND GENERIC EMAIL NOTIFICATION (team_member / full_admin)
  app.post("/api/engagements/:id/pending-items", async (req, res) => {
    const { id } = req.params;
    const { text, authorId, authorName, authorRole } = req.body;

    if (!text || typeof text !== "string" || !text.trim()) {
      return res.status(400).json({ success: false, error: "Text is required for pending item." });
    }

    if (authorRole !== "full_admin" && authorRole !== "team_member") {
      return res.status(403).json({ success: false, error: "Only firm staff and administrators can create pending items." });
    }

    try {
      const engRef = doc(db, "engagements", id);
      const engSnap = await getDoc(engRef);
      if (!engSnap.exists()) {
        return res.status(404).json({ success: false, error: "Engagement not found." });
      }
      const engData = engSnap.data();

      // Fetch Client Info
      let clientEmail = "";
      let clientName = "Client";
      if (engData.clientId) {
        const clientSnap = await getDoc(doc(db, "clients", engData.clientId));
        if (clientSnap.exists()) {
          const cData = clientSnap.data();
          clientEmail = cData.email || "";
          clientName = cData.name || clientName;
        }
      }

      // Fetch Service Name
      let serviceName = "Engagement";
      if (engData.serviceId) {
        const serviceSnap = await getDoc(doc(db, "services", engData.serviceId));
        if (serviceSnap.exists()) {
          serviceName = serviceSnap.data().name || serviceName;
        }
      }

      // Insert doc into pendingItems subcollection
      const itemsCol = collection(db, "engagements", id, "pendingItems");
      const newItemRef = await addDoc(itemsCol, {
        authorId: authorId || "system",
        authorName: authorName || "Firm Staff",
        authorRole: authorRole || "team_member",
        text: text.trim(),
        status: "open",
        timestamp: clientServerTimestamp(),
      });

      // Send Generic Email Notification via real SMTP
      let emailResult = null;
      let emailError = null;

      if (clientEmail) {
        try {
          const host = process.env.APP_URL || `${req.protocol}://${req.get("host")}`;
          const appLoginUrl = `${host}/`;
          emailResult = await sendPendingItemNotificationEmail({
            clientEmail,
            clientName,
            serviceName,
            appLoginUrl,
          });
        } catch (mailErr: any) {
          console.error("[Pending Item Email Notification Error]", mailErr);
          emailError = mailErr.message;
        }
      }

      res.json({
        success: true,
        itemId: newItemRef.id,
        emailResult,
        emailError,
      });
    } catch (err: any) {
      console.error("[Create Pending Item Error]", err);
      res.status(500).json({ success: false, error: err.message });
    }
  });

  // UPDATE PENDING ITEM STATUS (e.g. resolve or reopen)
  app.patch("/api/engagements/:id/pending-items/:itemId", async (req, res) => {
    const { id, itemId } = req.params;
    const { status, actorId, actorName, actorRole } = req.body;

    if (status !== "open" && status !== "resolved") {
      return res.status(400).json({ success: false, error: "Status must be 'open' or 'resolved'." });
    }

    if (actorRole !== "full_admin" && actorRole !== "team_member") {
      return res.status(403).json({ success: false, error: "Only firm staff and administrators can update pending items." });
    }

    try {
      const itemRef = doc(db, "engagements", id, "pendingItems", itemId);
      const itemSnap = await getDoc(itemRef);
      if (!itemSnap.exists()) {
        return res.status(404).json({ success: false, error: "Pending item not found." });
      }

      const updateData: any = {
        status,
        updatedAt: clientServerTimestamp(),
      };

      if (status === "resolved") {
        updateData.resolvedAt = clientServerTimestamp();
        updateData.resolvedBy = actorId || "staff";
        updateData.resolvedByName = actorName || "Staff Member";
      } else {
        updateData.resolvedAt = null;
        updateData.resolvedBy = null;
        updateData.resolvedByName = null;
      }

      await updateDoc(itemRef, updateData);

      res.json({
        success: true,
        itemId,
        status,
      });
    } catch (err: any) {
      console.error("[Update Pending Item Error]", err);
      res.status(500).json({ success: false, error: err.message });
    }
  });

  // Explicit 404 handler for unmatched /api/* routes (prevents falling back to HTML index.html)
  app.all("/api/*", (req, res) => {
    res.status(404).json({
      success: false,
      error: `API route not found: ${req.method} ${req.originalUrl}`,
    });
  });

  // Global Express Error Handling Middleware (guarantees JSON response for any server exception)
  app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
    console.error("[Global Server Error Caught]", err);
    if (res.headersSent) {
      return next(err);
    }
    res.status(err.status || 500).json({
      success: false,
      error: err.message || "An unexpected internal server error occurred",
    });
  });

  // Vite development middleware
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[Server] ABC & Associates Portal running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
