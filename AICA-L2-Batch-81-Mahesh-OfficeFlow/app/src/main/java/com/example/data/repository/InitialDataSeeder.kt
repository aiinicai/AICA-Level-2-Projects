package com.example.data.repository

import com.example.data.model.ActivityType
import com.example.data.model.OfficeActivityNotification
import com.example.data.model.Project
import com.example.data.model.ProjectStatus
import com.example.data.model.TaxDepartment
import com.example.data.model.TaxNotification
import com.example.data.model.TaxSeverity
import java.util.Calendar

object InitialDataSeeder {

    // The team roster now comes from Firebase Authentication onboarding, not seed data:
    // each member document is keyed by that user's Auth UID so security rules can resolve
    // their role. Sample tasks were removed with it, since they referenced seeded member ids.

    fun getDefaultProjects(): List<Project> {
        val now = System.currentTimeMillis()
        val day = 24L * 60 * 60 * 1000

        return listOf(
            Project(
                id = "seed-project-1",
                name = "FY25-26 Tax Planning & Corporate Filing",
                code = "PRJ-TAX-25",
                clientName = "Nexus Global Technologies Ltd",
                description = "Comprehensive advance tax computation, MAT calculations, transfer pricing documentation and ITR filing.",
                leadMemberName = "Rakshitha",
                startDateMillis = now - (15 * day),
                targetDateMillis = now + (20 * day),
                status = ProjectStatus.ACTIVE,
                progressPercentage = 68,
                category = "Income Tax",
                colorHex = "#2563EB",
                lastUpdateRemark = "Advance tax 2nd installment computation completed. AIS matching in progress."
            ),
            Project(
                id = "seed-project-2",
                name = "Pan-India GST Reconciliations & Audit",
                code = "PRJ-GST-08",
                clientName = "Zenith Retail Chains Pvt Ltd",
                description = "Monthly GSTR-1, GSTR-3B filings, ITC matching with GSTR-2B, Rule 37A reversal checks across 14 state registrations.",
                leadMemberName = "Rakshitha",
                startDateMillis = now - (10 * day),
                targetDateMillis = now + (12 * day),
                status = ProjectStatus.ACTIVE,
                progressPercentage = 82,
                category = "GST Compliance",
                colorHex = "#0D9488",
                lastUpdateRemark = "GSTR-2B vs purchase register reconciliation 95% cleared for July cycle."
            ),
            Project(
                id = "seed-project-3",
                name = "Statutory & Internal Audit Q2",
                code = "PRJ-AUD-02",
                clientName = "Apex Heavy Engineering Corp",
                description = "Fixed asset verification, inventory count test, internal financial controls (IFC) testing, statutory compliance audit.",
                leadMemberName = "Pavan",
                startDateMillis = now - (25 * day),
                targetDateMillis = now + (5 * day),
                status = ProjectStatus.CRITICAL,
                progressPercentage = 45,
                category = "Internal Audit",
                colorHex = "#E11D48",
                lastUpdateRemark = "Physical inventory discrepancies noted in plant #2; pending management clarification."
            ),
            Project(
                id = "seed-project-4",
                name = "Sec 43B(h) MSME Vendor Compliance Review",
                code = "PRJ-MSME-43",
                clientName = "Horizon Logistics Solutions",
                description = "Review of outstanding vendor balances to Micro & Small enterprises to ensure 45-day payment statutory adherence.",
                leadMemberName = "Mahesh",
                startDateMillis = now - (5 * day),
                targetDateMillis = now + (18 * day),
                status = ProjectStatus.ACTIVE,
                progressPercentage = 55,
                category = "Income Tax",
                colorHex = "#D97706",
                lastUpdateRemark = "Vendor categorization master updated. Verified 182 MSME Udyam certificates."
            )
        )
    }

    fun getDefaultTaxNotifications(): List<TaxNotification> {
        val now = System.currentTimeMillis()
        val day = 24L * 60 * 60 * 1000

        return listOf(
            TaxNotification(
                id = 1,
                title = "GST Amnesty Scheme & Waiver of Penalty for Specified Notices",
                department = TaxDepartment.GST,
                circularOrNotificationNo = "Notification No. 21/2026 - Central Tax",
                issueDateFormatted = "August 20, 2026",
                effectiveDateFormatted = "Immediate effect",
                summary = "CBIC notifies special procedure for waiver of interest and penalty under Section 128A for tax demands pertaining to FY 2017-18, 2018-19, and 2019-20 where tax has been paid in full.",
                keyActionItems = "1. Review pending SCNs under Section 73.\n2. Verify eligible payments made before March 31, 2027.\n3. File Form GST SPL-01 on portal to claim waiver.",
                deadlineDateMillis = now + (15 * day),
                severity = TaxSeverity.CRITICAL_ACTION_REQUIRED,
                sourceAuthority = "CBIC - Ministry of Finance, GoI"
            ),
            TaxNotification(
                id = 2,
                title = "Mandatory E-Way Bill Generation Thresholds & E-Invoice Ver. 2.0 Integration",
                department = TaxDepartment.GST,
                circularOrNotificationNo = "Circular No. 218/12/2026-GST",
                issueDateFormatted = "August 14, 2026",
                effectiveDateFormatted = "September 1, 2026",
                summary = "Stricter validation rules implemented on the IRP portal. Blocking of E-Way Bill generation if GSTR-3B is pending for consecutive tax periods. Enhanced JSON schema for B2B e-Invoices.",
                keyActionItems = "1. Update ERP tax connector schemas.\n2. Ensure zero lag in GSTR-3B return filings.\n3. Validate 6-digit HSN codes across all outgoing tax invoices.",
                deadlineDateMillis = now + (3 * day),
                severity = TaxSeverity.IMPORTANT,
                sourceAuthority = "GST Network (GSTN) Advisory"
            ),
            TaxNotification(
                id = 3,
                title = "Income Tax Section 43B(h) MSME Compliance & Reporting in Tax Audit Form 3CD",
                department = TaxDepartment.INCOME_TAX,
                circularOrNotificationNo = "CBDT Notification No. 48/2026",
                issueDateFormatted = "August 10, 2026",
                effectiveDateFormatted = "Assessment Year 2026-27",
                summary = "Clarification regarding allowable deductions on payments to Micro and Small enterprises under MSMED Act, 2006. Sums paid beyond 45 days disallowed in year of accrual and taxed as business income.",
                keyActionItems = "1. Obtain Udyam Registration certificates from all suppliers.\n2. Flag payments made after agreed term.\n3. Prepare annexure for Clause 22 of Form 3CD Tax Audit Report.",
                deadlineDateMillis = now + (25 * day),
                severity = TaxSeverity.CRITICAL_ACTION_REQUIRED,
                sourceAuthority = "Central Board of Direct Taxes (CBDT)"
            ),
            TaxNotification(
                id = 4,
                title = "Advance Tax 2nd Installment Due Date Alert (45% of Total Estimated Tax)",
                department = TaxDepartment.INCOME_TAX,
                circularOrNotificationNo = "CBDT Statutory Calendar Reminder",
                issueDateFormatted = "August 25, 2026",
                effectiveDateFormatted = "September 15, 2026",
                summary = "All corporate and non-corporate assessees (excluding 44AD/44ADA presumptive schemes) must deposit at least 45% of cumulative advance tax liability on or before September 15 to avoid Section 234C penal interest.",
                keyActionItems = "1. Close provisional P&L statement up to August.\n2. Reconcile TDS credit in Form 26AS/AIS.\n3. Generate Challan 280 (ITNS 280) under Minor Head 100 on e-Filing portal.",
                deadlineDateMillis = now + (17 * day),
                severity = TaxSeverity.CRITICAL_ACTION_REQUIRED,
                sourceAuthority = "Income Tax Department Directorate"
            ),
            TaxNotification(
                id = 5,
                title = "GSTR-3B Monthly Return Filing Cycle & Input Tax Credit Lock In",
                department = TaxDepartment.GST,
                circularOrNotificationNo = "GSTN Advisory on Auto-Population",
                issueDateFormatted = "August 18, 2026",
                effectiveDateFormatted = "August 20, 2026",
                summary = "Reminder: Input Tax Credit in Table 4 of GSTR-3B is hard-locked to GSTR-2B. Downward adjustments permitted; upward variance above 10% requires justification in Form DRC-01C.",
                keyActionItems = "1. Finalize Purchase Register vs GSTR-2B.\n2. Verify reverse charge mechanism (RCM) tax payment in cash.\n3. File GSTR-3B before deadline to avoid late fee.",
                deadlineDateMillis = now + (8 * day),
                severity = TaxSeverity.IMPORTANT,
                sourceAuthority = "Central Board of Indirect Taxes & Customs"
            ),
            TaxNotification(
                id = 6,
                title = "Quarterly TDS/TCS Statement Filing (Form 24Q & 26Q) and Lower Deduction Certificates",
                department = TaxDepartment.INCOME_TAX,
                circularOrNotificationNo = "CBDT Circular No. 12/2026-IT",
                issueDateFormatted = "August 05, 2026",
                effectiveDateFormatted = "October 31, 2026",
                summary = "Mandatory PAN validation before uploading quarterly TDS returns. Validation of Section 197 Lower Deduction Certificates through TRACES API integration.",
                keyActionItems = "1. Confirm challan matching status on OLTAS.\n2. Rectify invalid PANs with 20% deduction rates.\n3. Upload .fvu file to TIN-NSDL / Protean portal.",
                deadlineDateMillis = now + (45 * day),
                severity = TaxSeverity.NORMAL,
                sourceAuthority = "CBDT Systems Division"
            )
        )
    }

    fun getDefaultActivityNotifications(): List<OfficeActivityNotification> {
        val now = System.currentTimeMillis()
        val min = 60 * 1000L

        return listOf(
            OfficeActivityNotification(
                id = 1,
                title = "Statutory Alert: Section 43B(h) Guidance",
                message = "New CBDT Circular on MSME payment audit requirements pushed to statutory dashboard.",
                type = ActivityType.TAX_CIRCULAR_ALERT,
                timestampMillis = now - (12 * min),
                isRead = false,
                relatedEntityId = 3,
                actorName = "CBDT Broadcast Engine"
            ),
            OfficeActivityNotification(
                id = 2,
                title = "Progress Pushed: GST Reconciliations (82%)",
                message = "Rakshitha pushed project progress to 82%: 'GSTR-2B vs purchase register 95% reconciled.'",
                type = ActivityType.PROGRESS_PUSHED,
                timestampMillis = now - (45 * min),
                isRead = false,
                relatedEntityId = 2,
                actorName = "Rakshitha"
            ),
            OfficeActivityNotification(
                id = 3,
                title = "Urgent Task Assigned: Fixed Asset Physical Verification",
                message = "Task assigned to Pavan for Q2 Internal Audit with due date in 24 hours.",
                type = ActivityType.TASK_ASSIGNED,
                timestampMillis = now - (120 * min),
                isRead = true,
                relatedEntityId = 6,
                actorName = "Mahesh"
            ),
            OfficeActivityNotification(
                id = 4,
                title = "GST Return Deadline Approaching",
                message = "GSTR-1 filing deadline for Zenith Retail Chains is due in 48 hours.",
                type = ActivityType.DEADLINE_ALERT,
                timestampMillis = now - (180 * min),
                isRead = true,
                relatedEntityId = 1,
                actorName = "System Deadline Monitor"
            )
        )
    }

    fun getDefaultPortalIntegrations(): List<com.example.data.model.PortalIntegration> {
        val now = System.currentTimeMillis()
        val hour = 60L * 60 * 1000
        return listOf(
            com.example.data.model.PortalIntegration(
                id = 1,
                name = "GST Common Portal (GSTN)",
                type = com.example.data.model.IntegrationType.GST,
                portalUrl = "https://www.gst.gov.in",
                webhookUrl = "https://api.gst.gov.in/returns/v2/gstr1",
                apiKeyOrClientId = "GSTN-PROD-AUTH-882194",
                isEnabled = true,
                statusText = "Sync Active • 200 OK",
                lastSyncMillis = now - (2 * hour),
                description = "Direct portal access for GSTR-1, GSTR-3B filings, Challan payments, and GSTR-2B download."
            ),
            com.example.data.model.PortalIntegration(
                id = 2,
                name = "Income Tax e-Filing Portal 2.0",
                type = com.example.data.model.IntegrationType.INCOME_TAX,
                portalUrl = "https://www.incometax.gov.in/iec/foportal/",
                webhookUrl = "https://eportal.incometax.gov.in/iec/services/api/v1/taxpayer",
                apiKeyOrClientId = "ITD-CLIENT-773921-KEY",
                isEnabled = true,
                statusText = "Sync Active • AIS/TIS Connected",
                lastSyncMillis = now - (4 * hour),
                description = "ITR Form 1-7 e-filing, 26AS verification, AIS/TIS compliance and statutory audit reports submission."
            ),
            com.example.data.model.PortalIntegration(
                id = 3,
                name = "MCA21 V3 Company Master & Filings",
                type = com.example.data.model.IntegrationType.MCA,
                portalUrl = "https://www.mca.gov.in/mcafoportal/",
                webhookUrl = "https://www.mca.gov.in/v3/api/company/filing-status",
                apiKeyOrClientId = "MCA-DIN-SRN-SECRET",
                isEnabled = true,
                statusText = "Connected • V3 Auth Active",
                lastSyncMillis = now - (12 * hour),
                description = "ROC annual returns (AOC-4, MGT-7), Director KYC (DIR-3), and incorporation statutory filings."
            ),
            com.example.data.model.PortalIntegration(
                id = 4,
                name = "National e-Way Bill System",
                type = com.example.data.model.IntegrationType.EWAY_BILL,
                portalUrl = "https://ewaybillgst.gov.in",
                webhookUrl = "https://ewaybillgst.gov.in/api/ewayapi/v1.0",
                apiKeyOrClientId = "EWB-API-GW-09941",
                isEnabled = true,
                statusText = "Connected • Live Transit Tracking",
                lastSyncMillis = now - (1 * hour),
                description = "Generation, cancellation, and vehicle number updates for interstate and intrastate consignments."
            ),
            com.example.data.model.PortalIntegration(
                id = 5,
                name = "EPFO Unified Employer Portal",
                type = com.example.data.model.IntegrationType.EPFO,
                portalUrl = "https://unifiedportal-emp.epfindia.gov.in/epfo/",
                webhookUrl = "https://unifiedportal-emp.epfindia.gov.in/api/ecr/upload",
                apiKeyOrClientId = "EPFO-EST-BLR-00482",
                isEnabled = true,
                statusText = "Connected • ECR Filing Ready",
                lastSyncMillis = now - (24 * hour),
                description = "Monthly ECR challan generation, PF returns, UAN member linking, and wage compliance."
            ),
            com.example.data.model.PortalIntegration(
                id = 6,
                name = "OfficeFlow ERP Webhook & Client API",
                type = com.example.data.model.IntegrationType.CUSTOM_WEBHOOK,
                portalUrl = "https://webhook.site",
                webhookUrl = "https://webhook.site/officeflow-tax-sync",
                apiKeyOrClientId = "OF-WEBHOOK-TOKEN-9948",
                isEnabled = true,
                statusText = "Connected • Real-time Dispatch",
                lastSyncMillis = now - (10 * 60 * 1000),
                description = "Bi-directional webhook event dispatcher for task milestones, audit reports, and tax notices."
            )
        )
    }
}
