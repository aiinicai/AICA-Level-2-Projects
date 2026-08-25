# Multi-Tenant Business Management Platform — Architecture, Technical Specifications & Limitations

This document outlines the multi-tenant architecture, role-based security model, data isolation strategies, financial modules, and technical trade-offs for the Multi-Tenant Business Management SaaS Platform.

---

## 1. Multi-Tenant Architecture & Data Isolation

- **Tenant Scoping (`company_id`)**: Every database record (Users, Clients, Vouchers, KYC Documents, Payments, Intelligence Feeds) is strictly partitioned and scoped by `company_id`.
- **Cross-Tenant Prevention**: Data layer queries and reactive state subscribers enforce strict row-level isolation so that no user or company can view, alter, or access records belonging to another tenant.
- **Dynamic Theming Engine**: Each registered company profile carries independent visual branding tokens (`primaryColor`, `secondaryColor`, `accentColor`, `fontFamily`, company logo, official stamp, and authorized signature). The application dynamically maps these tokens onto `--brand-primary`, `--brand-secondary`, and `--brand-font` CSS variables and injects them into vector PDF renderings.
- **Company Access Code**: Tenants have a unique alphanumeric company code (e.g. `KILI-7890`, `TWIGA-1042`) used by staff and contractors during sign-up to join existing organizations.

---

## 2. Role-Based Access Control (RBAC) & Client Portal

The platform enforces 5 distinct role profiles:

| Role | Permitted Modules & Capabilities | Restricted Actions |
|---|---|---|
| **Super Admin / Company Admin** | Full access to all 5 modules, company branding settings, user approvals, audit logs, and payments. | None |
| **Procurement** | Local Purchase Orders (LPOs), PDF Toolkit, Supplier & KYC docs. | Cannot generate Outbound Sales Invoices or edit Finance settings. |
| **Operations** | Sales Invoices, Proforma Invoices, Delivery Notes, CRM, PDF Toolkit, Global Intelligence. | Cannot create or authorize LPOs. |
| **Finance** | Invoices, Proforma, Credit Terms, Overdue Aging, Average Days-to-Pay Analytics, Payment Settlements. | None (restricted to financial governance). |
| **Client Portal** | Restricted view: only sees finalized Tax Invoices & Proformas issued to their specific client account. Access to PDF Toolkit for their own files. | Zero access to CRM, credit terms, other clients' records, staff signups, or Global Intelligence. |

---

## 3. Sign-up Approval Workflow & Transactional Email Queue

- **Admin Security Gatekeeper**: New registrations wishing to join an existing company are placed in a `pending` state.
- **Administrator Review**: Administrators review applicants in the **User Approvals** view. For Client Portal accounts, admins link the applicant to an existing CRM client record or create a contractor profile.
- **Simulated Transactional Outbound Email Queue**: In this cloud and preview environment, outgoing emails (approval confirmations, rejection notices with reason, and admin alerts) are logged to a live **Simulated Transactional Outbound Email Queue** for full visibility and audit trail verification. In a production deployment, this queue connects to an SMTP / SendGrid / AWS SES transport.

---

## 4. Invoicing, TRA Compliance & Financial Modules

- **Spelled-Out Amount in Words**: Every voucher automatically computes reactive, spelled-out currency text (e.g., *"Tanzania Shillings Sixty-Nine Million Six Hundred Twenty Thousand Only"* or *"US Dollars Four Hundred Fifty and Zero Cents Only"*) rendered on preview and stamped onto vector PDFs.
- **Proforma Validity Period**: Proforma Invoices enforce a validity period selector (3, 5, 7, or max 10 days), automatically calculating and stamping the expiration date (`expiresOn`).
- **TRA Tax Rules**:
  - Fuel products (Petrol, Diesel, Kerosene) are locked at **0% Non-Vatable** under Tanzania fuel excise law.
  - Bitumen products feature an optional 18% VAT toggle.
  - Transport & logistics apply standard 18% VAT.
- **Average Days-to-Pay & Credit Risk Analytics**:
  - Tracks historical days-to-pay per client against an industry benchmark of **21 Days**.
  - Real-time Credit Limit Utilization progress bars with Warning/Critical alerts when receivables approach or exceed approved limits.
  - Multi-channel payment settlement recording (Bank Transfer, Cheque, Mobile Money / M-Pesa, Cash) with real-time status transitions.

---

## 5. Desktop Installation & Packaging (Electron)

The platform is built with a dual-target architecture: it functions as a cloud-hosted web application and can be packaged as a cross-platform desktop application using **Electron**:

```bash
# 1. Install electron dependencies
npm install --save-dev electron electron-builder

# 2. Build web assets
npm run build

# 3. Package standalone desktop application
npx electron-builder --win --mac --linux
```

---

## 6. Known Environment Limitations & Equivalents

1. **Transactional Email Transport**: In the cloud preview environment, external SMTP ports (25, 465, 587) are restricted by sandboxing rules. To ensure 100% reliable functionality, outbound transactional emails are dispatched to an **in-app Transactional Email Queue** with full body preview, recipient routing, and timestamp verification.
2. **Cloud Database Persistence**: The application features a robust singleton `StorageService` that mirrors PostgreSQL multi-tenant schema isolation with `company_id` primary foreign keys, JSON cloud backup exports, and multi-tenant seed instances (KiliTrade, Twiga, Serengeti Logistics).
