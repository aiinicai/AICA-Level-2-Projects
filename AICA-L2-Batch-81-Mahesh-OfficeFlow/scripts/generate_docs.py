import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=120, bottom=120, left=160, right=160):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def set_table_borders(table, color="D3D3D3", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def create_document():
    doc = Document()

    # Page setup - Margins 1 inch
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Styles & Colors
    NAVY = RGBColor(30, 64, 175)     # #1E40AF
    SLATE = RGBColor(15, 23, 42)     # #0F172A
    MUTED = RGBColor(100, 116, 139)  # #64748B

    # ---------------------------------------------------------
    # COVER / HEADER TITLE
    # ---------------------------------------------------------
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(10)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run("OfficeFlow")
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(28)
    run_title.font.bold = True
    run_title.font.color.rgb = NAVY

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(10)
    run_sub = sub_p.add_run("Enterprise Practice & Statutory Compliance Management Platform")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(15)
    run_sub.font.color.rgb = SLATE
    run_sub.font.bold = True

    desc_p = doc.add_paragraph()
    desc_p.paragraph_format.space_after = Pt(16)
    run_desc = desc_p.add_run("Comprehensive Technical Documentation, System Architecture, Role-Based Access Control Matrix, and Project Submission Manual")
    run_desc.font.name = "Calibri"
    run_desc.font.size = Pt(10.5)
    run_desc.font.color.rgb = MUTED
    run_desc.font.italic = True

    # Metadata Banner Table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False
    
    col_widths = [Inches(2.0), Inches(4.5)]
    meta_data = [
        ("Project Submission:", "AICA Level II Certification Project"),
        ("System Version:", "v1.0.0 (Production-Ready Release)"),
        ("Supported Platforms:", "Android Native (Jetpack Compose), Windows Desktop (.NET), Web PWA"),
        ("Database & Security:", "Google Cloud Firestore, Firebase Auth, Declarative RBAC v2.0")
    ]

    for row_idx, (k, v) in enumerate(meta_data):
        row = meta_table.rows[row_idx]
        cell_k, cell_v = row.cells[0], row.cells[1]
        
        cell_k.width = col_widths[0]
        cell_v.width = col_widths[1]
        
        p_k = cell_k.paragraphs[0]
        p_k.paragraph_format.space_after = Pt(2)
        r_k = p_k.add_run(k)
        r_k.font.bold = True
        r_k.font.size = Pt(9.5)
        r_k.font.color.rgb = NAVY

        p_v = cell_v.paragraphs[0]
        p_v.paragraph_format.space_after = Pt(2)
        r_v = p_v.add_run(v)
        r_v.font.size = Pt(9.5)
        r_v.font.color.rgb = SLATE

        set_cell_background(cell_k, "F8FAFC")
        set_cell_background(cell_v, "F8FAFC")
        set_cell_margins(cell_k, top=80, bottom=80, left=120, right=120)
        set_cell_margins(cell_v, top=80, bottom=80, left=120, right=120)

    set_table_borders(meta_table, color="E2E8F0", sz="4")
    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ---------------------------------------------------------
    # HELPER FUNCTIONS
    # ---------------------------------------------------------
    def add_heading_1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(16)
        r.font.bold = True
        r.font.color.rgb = NAVY
        return p

    def add_heading_2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(12.5)
        r.font.bold = True
        r.font.color.rgb = SLATE
        return p

    def add_para(text, bold_prefix=""):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_b = p.add_run(bold_prefix)
            r_b.font.bold = True
            r_b.font.color.rgb = SLATE
        r = p.add_run(text)
        r.font.size = Pt(10)
        r.font.color.rgb = SLATE
        return p

    def add_bullet(text, bold_prefix=""):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_b = p.add_run(bold_prefix)
            r_b.font.bold = True
            r_b.font.color.rgb = SLATE
        r = p.add_run(text)
        r.font.size = Pt(10)
        r.font.color.rgb = SLATE
        return p

    def add_callout(text, title="NOTE"):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.rows[0].cells[0]
        cell.width = Inches(6.5)
        set_cell_background(cell, "EFF6FF")
        set_cell_margins(cell, top=90, bottom=90, left=140, right=140)
        
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:left w:val="single" w:sz="24" w:space="0" w:color="1E40AF"/>
                <w:top w:val="none"/>
                <w:right w:val="none"/>
                <w:bottom w:val="none"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)

        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r_t = p.add_run(f"[{title}] ")
        r_t.font.bold = True
        r_t.font.size = Pt(9.5)
        r_t.font.color.rgb = NAVY

        r_b = p.add_run(text)
        r_b.font.size = Pt(9.5)
        r_b.font.color.rgb = SLATE

        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # ---------------------------------------------------------
    # SECTION 1: EXECUTIVE SUMMARY & PROBLEM STATEMENT
    # ---------------------------------------------------------
    add_heading_1("1. Executive Summary & Problem Statement")
    
    add_para("Accounting firms, Chartered Accountancy (CA) practices, tax consultancies, and corporate compliance departments operate in a high-stakes, deadline-driven environment. Managing multi-client portfolios requires constant adherence to complex Indian statutory compliance schedules, including Goods and Services Tax (GST), Income Tax, TDS, ROC/MCA filings, Provident Fund (PF), ESIC, and Professional Tax.")
    
    add_para("Traditional offices struggle with fragmented tools: WhatsApp messages for task handoffs, static Excel sheets for compliance status, physical diaries for deadline tracking, and disparate government portals. This fragmentation results in missed statutory deadlines, substantial late fees/penalties, lack of operational workload visibility, and severe data security vulnerabilities.")
    
    add_para("OfficeFlow addresses these critical challenges by providing a unified, multi-platform, real-time practice management ecosystem. Built with a cloud-native architecture, OfficeFlow synchronizes work across Native Android mobile applications, Windows desktop clients, and Progressive Web Apps (PWAs), ensuring seamless collaboration between partners, managers, staff associates, and clients.")

    # ---------------------------------------------------------
    # SECTION 2: SYSTEM ARCHITECTURE & PLATFORM TOPOLOGY
    # ---------------------------------------------------------
    add_heading_1("2. System Architecture & Platform Topology")
    
    add_para("OfficeFlow follows a clean, layered architectural pattern designed for high responsiveness, offline resilience, and enterprise-grade security:")

    add_bullet(" Native Android Client (Kotlin + Jetpack Compose): Delivers an edge-to-edge, modern mobile experience built with Material 3, Android Architecture Components (ViewModel, StateFlow, Coroutines), Room Database for local caching, and native system notification channels.", "Mobile Layer:")
    add_bullet(" Standalone Windows Desktop Client (C# .NET Host): A lightweight desktop launcher binding strictly to 127.0.0.1 origin. It eliminates path traversal vulnerabilities, avoids intrusive firewall modifications, and delivers an ultra-fast desktop experience.", "Desktop Layer:")
    add_bullet(" Progressive Web App (Vanilla ES Modules + HTML5/CSS3 Grid): A zero-overhead, responsive single-page web client featuring persistent IndexedDB multi-tab caching, allowing full operational usage even under low or intermittent network connectivity.", "Web/PWA Layer:")
    add_bullet(" Google Cloud Backend (Firebase Auth + Cloud Firestore): Provides centralized identity verification, JWT token authorization, sub-second real-time NoSQL document synchronization, and declarative server-side Role-Based Access Control (RBAC).", "Cloud Infrastructure:")

    add_callout("All clients (Android, Windows Desktop, and PWA) connect directly to the shared Firebase Firestore instance (project: office-flow-integration). Changes made on any device reflect instantaneously across all team members.", "REAL-TIME SYNCHRONIZATION")

    # ---------------------------------------------------------
    # SECTION 3: IN-DEPTH FUNCTIONAL MODULE SPECIFICATIONS
    # ---------------------------------------------------------
    add_heading_1("3. Functional Module Specifications")

    add_heading_2("3.1 Executive Dashboard & Practice Pulse")
    add_para("The primary landing hub provides partners and managers with an instantaneous high-level snapshot of firm health and operational throughput:")
    add_bullet("Dynamic calculation of Pending Operations, Due Tax Notices, Active Client Projects, and Active Team Capacity.", "Real-Time KPIs:")
    add_bullet("Instant launch buttons to assign new tasks, create client projects, broadcast official tax circulars, and audit government portal integrations.", "Action Gateway:")
    add_bullet("Reverse-chronological audit log capturing task updates, progress submissions, notice conversions, and administrative changes.", "Activity Pulse:")

    add_heading_2("3.2 Granular Task Allocation & Execution Engine")
    add_para("The core workhorse of OfficeFlow handles daily operational assignments with rigorous detail:")
    add_bullet("Title, detailed instructions, assignee, project linkage, priority level (LOW, MEDIUM, HIGH, URGENT), category (GST_COMPLIANCE, INCOME_TAX, INTERNAL_AUDIT, PAYROLL, CLIENT_PROJECT, OPERATIONS, LEGAL_SECRETARIAL), due date, and custom tags (e.g., 'Audit2024, MSME, Statutory').", "Task Structuring:")
    add_bullet("Multi-item checklist allowing staff to tick off individual sub-deliverables with automatic progress percentage computation.", "Checklists:")
    add_bullet("Real-time 0% to 100% progress adjustments with mandatory or optional actor remarks, maintaining complete historical audit trails.", "Progress Slider:")
    add_bullet("Clear lifecycle stages (TODO -> IN_PROGRESS -> IN_REVIEW -> COMPLETED) reflecting real-world review workflows.", "Lifecycle Pipeline:")
    add_bullet("Instant client-side filtering by task status, priority level, department category, tag taxonomy, individual team member, or 'My Tasks' view.", "Search & Filter:")

    add_heading_2("3.3 Client Projects & Engagement Management")
    add_para("Manages multi-stage client engagements (e.g., Annual Statutory Audits, Due Diligence, Corporate Restructuring, Tax Planning):")
    add_bullet("Unique project codes (e.g., PRJ-GST-01, PRJ-AUDIT-24), client name, engagement lead, target completion date, and budget/health categorization.", "Project Metadata:")
    add_bullet("Aggregates all linked tasks to provide overall project completion percentages and status indicators (PLANNING, ACTIVE, ON_HOLD, COMPLETED, CRITICAL).", "Milestone Rollup:")

    add_heading_2("3.4 Indian Statutory Compliance Engine & Team Calendar")
    add_para("OfficeFlow contains a built-in statutory compliance calendar hardcoded with official legal deadlines under Indian commercial and taxation laws:")
    
    # Statutory Table
    stat_table = doc.add_table(rows=8, cols=4)
    stat_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    stat_table.autofit = False
    
    s_widths = [Inches(1.2), Inches(1.2), Inches(2.6), Inches(1.5)]
    s_headers = ["Authority", "Form / Section", "Obligation Description", "Due Frequency"]
    
    hdr_row = stat_table.rows[0]
    for idx, name in enumerate(s_headers):
        cell = hdr_row.cells[idx]
        cell.width = s_widths[idx]
        p = cell.paragraphs[0]
        r = p.add_run(name)
        r.font.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "1E40AF")
        set_cell_margins(cell, top=70, bottom=70, left=90, right=90)

    s_rows_data = [
        ("GST (CBIC)", "GSTR-1 / IFF", "Monthly outward supplies / QRMP invoice furnishing", "11th / 13th Monthly"),
        ("GST (CBIC)", "GSTR-3B", "Monthly summary return & tax payment", "20th Monthly"),
        ("Income Tax", "Challan 281", "Monthly TDS/TCS deposit to Central Govt", "7th Monthly"),
        ("Income Tax", "Form 24Q / 26Q", "Quarterly TDS return filing (Salary & Non-Salary)", "31st of next month"),
        ("Income Tax", "Advance Tax", "Quarterly advance tax installments (15%, 45%, 75%, 100%)", "15 Jun/Sep/Dec/Mar"),
        ("Labor / EPFO", "EPF ECR", "Monthly Electronic Challan-cum-Return for Provident Fund", "15th Monthly"),
        ("MCA / ROC", "AOC-4 & MGT-7", "Annual financial statements & annual return filing", "30/60 days from AGM")
    ]

    for r_idx, row_data in enumerate(s_rows_data):
        row = stat_table.rows[r_idx + 1]
        bg_col = "FFFFFF" if r_idx % 2 == 0 else "F8FAFC"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.width = s_widths[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            r.font.color.rgb = SLATE
            set_cell_background(cell, bg_col)
            set_cell_margins(cell, top=50, bottom=50, left=90, right=90)

    set_table_borders(stat_table, color="CBD5E1", sz="4")
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    add_heading_2("3.5 Client Master & Monthly Compliance Tracker")
    add_para("The Monthly Compliance Tracker provides a high-density, interactive operational grid mapping clients against their monthly recurring compliance checklist:")
    add_bullet("Tracks 7 standard obligations per client: TDS Payment (7th), GSTR-1 (13th), GSTR-3B (20th), Accounting Books Closure (Month End), Professional Tax (20th), EPF (15th), and ESIC (15th).", "Standard Checklist:")
    add_bullet("Clicking any cell cycles state immediately: Pending [·] -> Done [✓] -> Not Applicable [—]. Updates save instantaneously to Cloud Firestore.", "Tri-State Cycling:")
    add_bullet("Supports importing existing office spreadsheets (.xlsx, .xls, .csv). Features automated client matching on GSTN and client name, preventing duplicate entries.", "Excel / CSV Bulk Import:")
    add_bullet("One-click export of current period compliance statuses to CSV for partner review and client billing reports.", "Export Capability:")

    add_heading_2("3.6 Statutory Tax Desk & Notice-to-Task Conversion")
    add_para("A specialized hub for monitoring and acting upon regulatory circulars issued by CBIC, CBDT, MCA, and RBI:")
    add_bullet("Categorized by tax department, circular number, issue date, effective date, summary, and action points. Classified by severity: NORMAL, IMPORTANT, CRITICAL_ACTION_REQUIRED.", "Circular Repository:")
    add_bullet("A single click opens a pre-populated task creation dialog transferring the notice title, statutory deadline, and required action items into an actionable task assigned to a team member.", "1-Click Notice Conversion:")

    add_heading_2("3.7 Government Portal Integrations")
    add_para("Maintains a centralized registry of government portals (GST Portal, Income Tax e-Filing, MCA21, e-Way Bill, EPFO/ESIC, Custom Webhooks). Provides administrators with quick URLs, credential notes, endpoint configurations, and connection test simulations.")

    # ---------------------------------------------------------
    # SECTION 4: SECURITY ARCHITECTURE & RBAC MATRIX
    # ---------------------------------------------------------
    add_heading_1("4. Security Architecture & RBAC Permissions Matrix")
    
    add_para("Security is enforced at the database layer via Cloud Firestore Security Rules v2. Access permissions are strictly decoupled from client-side code and validated against user identity tokens issued by Firebase Authentication.")

    # RBAC Table
    rbac_table = doc.add_table(rows=5, cols=4)
    rbac_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    rbac_table.autofit = False
    
    r_widths = [Inches(1.2), Inches(1.5), Inches(2.3), Inches(1.5)]
    r_headers = ["Role", "Target Persona", "Database & Application Permissions", "Data Scope Visibility"]
    
    hdr_row = rbac_table.rows[0]
    for idx, name in enumerate(r_headers):
        cell = hdr_row.cells[idx]
        cell.width = r_widths[idx]
        p = cell.paragraphs[0]
        r = p.add_run(name)
        r.font.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "1E40AF")
        set_cell_margins(cell, top=70, bottom=70, left=90, right=90)

    rbac_rows_data = [
        ("ADMIN", "Managing Partner / IT Administrator", "Full CRUD on all collections (Tasks, Projects, Team Roster, Portals, Clients, Compliance). Can onboard/delete users and reset database.", "Firm-wide unrestricted read/write"),
        ("PARTNER", "Senior Partner / Practice Head", "Create projects, assign tasks, broadcast tax notices, approve filings, configure portals, view workload analytics. Cannot delete team members.", "Firm-wide unrestricted visibility"),
        ("MANAGER", "Department Manager / Reviewer", "Create projects, assign tasks, update progress on any task, convert notices to tasks, view team workload capacity. Cannot delete tasks or manage portals.", "Firm-wide read (scoped task list view)"),
        ("TEAM_MEMBER", "Staff Associate / Articled Assistant", "Read and update ONLY tasks assigned to their UID. Push progress % and remarks. Check off compliance items. Read circulars and roster.", "Strictly isolated to personal assigned tasks")
    ]

    for r_idx, row_data in enumerate(rbac_rows_data):
        row = rbac_table.rows[r_idx + 1]
        bg_col = "FFFFFF" if r_idx % 2 == 0 else "F8FAFC"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.width = r_widths[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            r.font.color.rgb = SLATE
            set_cell_background(cell, bg_col)
            set_cell_margins(cell, top=50, bottom=50, left=90, right=90)

    set_table_borders(rbac_table, color="CBD5E1", sz="4")
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    add_callout("Under Firestore Security Rules, if a Team Member attempts to query tasks without filtering by 'where assignedMemberId == request.auth.uid', the request is rejected outright by Google Cloud servers with PERMISSION_DENIED. Client data isolation is absolute.", "DATA PRIVACY ENFORCEMENT")

    # ---------------------------------------------------------
    # SECTION 5: DEMO TEST CREDENTIALS & EVALUATION MATRIX
    # ---------------------------------------------------------
    add_heading_1("5. Demo Test Credentials & Evaluation Scenarios")
    
    add_para("To evaluate the application across all 4 operational roles, use the pre-configured test credentials below:")

    cred_table = doc.add_table(rows=9, cols=5)
    cred_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cred_table.autofit = False
    
    c_widths = [Inches(1.0), Inches(1.8), Inches(0.9), Inches(1.1), Inches(1.7)]
    c_headers = ["Name", "Login Email", "Password", "Role", "Test Scenario"]
    
    hdr_row = cred_table.rows[0]
    for idx, name in enumerate(c_headers):
        cell = hdr_row.cells[idx]
        cell.width = c_widths[idx]
        p = cell.paragraphs[0]
        r = p.add_run(name)
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "1E40AF")
        set_cell_margins(cell, top=60, bottom=60, left=80, right=80)

    cred_data = [
        ("Mahesh C.", "maheshconsultantpro@gmail.com", "admin123", "ADMIN", "Admin control: Onboard staff, configure portals, delete tasks"),
        ("Arun Singhal", "arun.s@officeflow.internal", "partner123", "PARTNER", "Partner oversight: Monitor corporate projects & firm workload"),
        ("Priya Sharma", "priya.s@officeflow.internal", "manager123", "MANAGER", "GST Manager: Convert GSTR-3B circular to assigned task"),
        ("Rohit Verma", "rohit.v@officeflow.internal", "manager123", "MANAGER", "Tax Manager: Push Advance Tax project progress to 75%"),
        ("Ananya Rao", "ananya.r@officeflow.internal", "member123", "TEAM_MEMBER", "Staff: Update Statutory Audit checklist & add work remark"),
        ("Vikram Patel", "vikram.p@officeflow.internal", "member123", "TEAM_MEMBER", "Corporate Staff: Execute MCA AOC-4 / MGT-7 checklist"),
        ("Sneha Kulkarni", "sneha.k@officeflow.internal", "member123", "TEAM_MEMBER", "Payroll Staff: Complete TDS Form 26Q quarterly filing"),
        ("Apex Client", "client@apexholdings.com", "client123", "CLIENT", "Client Portal: Read-only view of active project milestones")
    ]

    for r_idx, row_data in enumerate(cred_data):
        row = cred_table.rows[r_idx + 1]
        bg_col = "FFFFFF" if r_idx % 2 == 0 else "F8FAFC"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.width = c_widths[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8)
            r.font.color.rgb = SLATE
            set_cell_background(cell, bg_col)
            set_cell_margins(cell, top=45, bottom=45, left=80, right=80)

    set_table_borders(cred_table, color="CBD5E1", sz="4")
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ---------------------------------------------------------
    # SECTION 6: CODEBASE ARCHITECTURE & DIRECTORY MAP
    # ---------------------------------------------------------
    add_heading_1("6. Codebase Architecture & Directory Map")
    
    add_para("The workspace is structured into clear, maintainable modules following modern software engineering conventions:")

    add_bullet("app/src/main/java/com/example/ui/screens/: Jetpack Compose screen composables (DashboardScreen, TasksScreen, ProjectsScreen, CalendarScreen, TaxAlertsScreen, SettingsAndPortalsScreen, LoginScreen, NotificationsScreen).", "Android Presentation Layer:")
    add_bullet("app/src/main/java/com/example/ui/components/: Reusable modular dialogs and bottom sheets (AssignTaskDialog, CreateProjectDialog, AddTaxNotificationDialog, ConvertNoticeToTaskDialog, PushProgressDialog, MemberFormDialog, ConfigurePortalDialog).", "Android Component Library:")
    add_bullet("app/src/main/java/com/example/data/: Clean Architecture domain models (TaskItem, Project, TeamMember, TaxNotification, PortalIntegration), Room DAO/Database, and OfficeRepository coordinating Cloud Firestore and local data streams.", "Data & Repository Layer:")
    add_bullet("desktop/OfficeFlowDesktop.cs: Compact C# standalone desktop host serving the embedded application with secure 127.0.0.1 loopback.", "Desktop Binary:")
    add_bullet("public/index.html & OfficeFlow.html: Standalone Progressive Web Application with integrated IndexedDB offline cache.", "Web / PWA Application:")
    add_bullet("firestore.rules: Declarative security rules enforcing strict role-based document access.", "Security Layer:")
    add_bullet("tests/rules.test.mjs: Comprehensive Mocha/Node.js security rules unit test suite covering 30+ authorization assertions against the Firebase emulator.", "Testing Suite:")
    add_bullet("scripts/verify-firestore-rules.ps1: End-to-end PowerShell script testing deployed Firestore REST API endpoints.", "DevOps & Verification:")

    # ---------------------------------------------------------
    # SECTION 7: STEP-BY-STEP EXECUTION & VERIFICATION GUIDE
    # ---------------------------------------------------------
    add_heading_1("7. Step-by-Step Execution & Deployment Guide")

    add_heading_2("7.1 Running the Windows Desktop Application")
    add_bullet("Navigate to the project root directory.", "Step 1:")
    add_bullet("Double-click OfficeFlow-desktop.exe (or desktop/OfficeFlow.exe).", "Step 2:")
    add_bullet("The desktop application will launch immediately and connect to the shared Cloud Firestore database. Sign in using any account from the credentials table.", "Step 3:")

    add_heading_2("7.2 Installing and Running on Android Devices")
    add_bullet("Direct APK: Transfer OfficeFlow-fixed.apk to your Android phone/tablet and tap to install.", "Method A (Fastest):")
    add_bullet("Android Studio: Open Android Studio -> Open Project -> Select project root directory -> Allow Gradle sync -> Select connected physical device or emulator (API 24+) -> Click Run (Shift + F10).", "Method B (Development):")

    add_heading_2("7.3 Running the Web Application / PWA")
    add_bullet("Double-click OfficeFlow.html or public/index.html in any modern web browser (Chrome, Edge, Firefox, Safari).", "Browser Launch:")
    add_bullet("The application operates with full offline support and instant cloud data synchronization.", "Zero Setup:")

    add_heading_2("7.4 Executing the Automated Security Rules Test Suite")
    add_para("To verify that the Firestore Security Rules correctly protect the database across all roles and collections:")
    add_bullet("Open PowerShell and navigate to the tests directory: cd tests", "1. Navigate:")
    add_bullet("Run the test runner: npm test", "2. Execute:")
    add_bullet("All 30+ assertions will execute against the local Firebase Emulator, verifying that unauthorized operations (e.g., Team Member reading others' tasks, unauthenticated writes, privilege escalation) are strictly denied.", "3. Output:")

    # ---------------------------------------------------------
    # SECTION 8: DELIVERABLES SUMMARY & SUBMISSION MANIFEST
    # ---------------------------------------------------------
    add_heading_1("8. Deliverables Summary & Submission Manifest")
    
    deliv_table = doc.add_table(rows=10, cols=3)
    deliv_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    deliv_table.autofit = False
    
    d_widths = [Inches(1.8), Inches(2.0), Inches(2.7)]
    d_headers = ["Deliverable Name", "File Artifact", "Description"]
    
    hdr_row = deliv_table.rows[0]
    for idx, name in enumerate(d_headers):
        cell = hdr_row.cells[idx]
        cell.width = d_widths[idx]
        p = cell.paragraphs[0]
        r = p.add_run(name)
        r.font.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "1E40AF")
        set_cell_margins(cell, top=60, bottom=60, left=80, right=80)

    deliv_data = [
        ("Android Mobile App (APK)", "OfficeFlow-fixed.apk", "Production signed, ready-to-install Android package"),
        ("Windows Desktop App", "OfficeFlow-desktop.exe", "Standalone executable desktop launcher for Windows"),
        ("Web / PWA Application", "OfficeFlow.html", "Self-contained Progressive Web App with offline caching"),
        ("Android Source Code", "app/src/main/java/", "Complete Kotlin 2.0+ & Jetpack Compose codebase"),
        ("Desktop Host Source", "desktop/OfficeFlowDesktop.cs", "C# .NET standalone host source code"),
        ("Firestore Security Rules", "firestore.rules", "Production declarative RBAC security rules"),
        ("Automated Test Suite", "tests/rules.test.mjs", "Complete Mocha unit test matrix for security validation"),
        ("Client Master Dataset", "desktop/clients-import.csv", "Sample 50-client database for spreadsheet import"),
        ("Master Credentials Sheet", "OfficeFlow_Test_Credentials.csv", "Complete role credentials and test scenario guide")
    ]

    for r_idx, row_data in enumerate(deliv_data):
        row = deliv_table.rows[r_idx + 1]
        bg_col = "FFFFFF" if r_idx % 2 == 0 else "F8FAFC"
        for c_idx, val in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.width = d_widths[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            r.font.color.rgb = SLATE
            set_cell_background(cell, bg_col)
            set_cell_margins(cell, top=45, bottom=45, left=80, right=80)

    set_table_borders(deliv_table, color="CBD5E1", sz="4")
    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # Closing signoff
    sign_p = doc.add_paragraph()
    sign_p.paragraph_format.space_before = Pt(8)
    r_sign = sign_p.add_run("OfficeFlow v1.0.0 — Prepared for AICA Level II Project Submission")
    r_sign.font.size = Pt(9.5)
    r_sign.font.italic = True
    r_sign.font.color.rgb = MUTED

    output_path = "OfficeFlow_Comprehensive_README.docx"
    doc.save(output_path)
    print(f"Document successfully created at: {output_path}")

if __name__ == "__main__":
    create_document()
