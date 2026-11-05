"""
LexSecure India Pro - Enterprise Seed Data Engine
Pre-populates Conglomerate, Operating Subsidiaries, Playbooks, Statutory Calendar & Circulars
"""

import os
import sys
from pathlib import Path

# Ensure root package directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from datetime import datetime, timedelta
from database.db_engine import DatabaseEngine

def seed_enterprise_data(reset: bool = True):
    db = DatabaseEngine.get_instance()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Check if already seeded
        cursor.execute("SELECT COUNT(*) FROM organizations")
        if cursor.fetchone()[0] > 0 and not reset:
            print("[LexSecure Seed] Database already populated.")
            return

        print("[LexSecure Seed] Initializing Enterprise Legal & Regulatory Data...")

        # 1. Clear existing tables if reset
        if reset:
            tables = [
                "task_evidences", "compliance_tasks", "impact_assessments",
                "regulatory_updates", "statutory_calendar_events", "document_clauses",
                "documents", "playbook_rules", "playbooks", "access_matrix_rules",
                "users", "departments", "entities", "tamper_audit_logs", "organizations"
            ]
            for t in tables:
                cursor.execute(f"DELETE FROM {t};")
            conn.commit()

        # 2. Seed 1 Parent Conglomerate
        cursor.execute("""
            INSERT INTO organizations (id, name, pan_number, cin_number, industry_type)
            VALUES (1, 'Apex Enterprises India Holdings Ltd.', 'AAACA1234F', 'L74999KA2015PLC089123', 'GENERAL')
        """)
        org_id = 1

        # 3. Seed 2 Operating Subsidiaries (1 Tech, 1 Manufacturing)
        cursor.execute("""
            INSERT INTO entities (id, organization_id, legal_name, entity_type, registered_state)
            VALUES 
            (1, 1, 'Apex Global India Tech Private Limited', 'PVT_LTD', 'Karnataka'),
            (2, 1, 'Apex Precision Forge India Limited', 'PUBLIC_LTD', 'Maharashtra')
        """)

        # 4. Seed Departments for each Entity
        depts = [
            # Entity 1 (Tech)
            (1, 1, 'LEGAL'),
            (2, 1, 'HR_LABOUR'),
            (3, 1, 'FINANCE_TAX'),
            (4, 1, 'INFOSEC_TECH'),
            (5, 1, 'OPERATIONS'),
            # Entity 2 (Manufacturing)
            (6, 2, 'LEGAL'),
            (7, 2, 'HR_LABOUR'),
            (8, 2, 'FINANCE_TAX'),
            (9, 2, 'INFOSEC_TECH'),
            (10, 2, 'OPERATIONS')
        ]
        cursor.executemany("INSERT INTO departments (id, entity_id, name) VALUES (?, ?, ?)", depts)

        # 5. Seed 5 Users across Roles and Departments
        users = [
            (1, 1, 'general.counsel@apexindia.com', 'Adv. Vikramaditya Sen', 'GENERAL_COUNSEL', 1),
            (2, 1, 'compliance.lead@apexindia.com', 'Sunita Krishnamurthy, FCS', 'COMPLIANCE_OFFICER', 1),
            (3, 1, 'hr.director@apexindia.com', 'Rajesh K. Sharma', 'DEPT_LEAD', 2),
            (4, 1, 'cfo@apexindia.com', 'Meera Venkatesh, FCA', 'DEPT_LEAD', 3),
            (5, 1, 'statutory.auditor@deloitte-partner.com', 'Arjun Singhania', 'AUDITOR', 1)
        ]
        cursor.executemany("""
            INSERT INTO users (id, organization_id, email, full_name, role, department_id, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, users)

        # 6. Seed Granular Access Matrix Rules
        matrix_rules = [
            # GENERAL_COUNSEL
            ('GENERAL_COUNSEL', 'CONTRACT', 1, 1, 1, 1, 1),
            ('GENERAL_COUNSEL', 'PLAYBOOK', 1, 1, 1, 1, 1),
            ('GENERAL_COUNSEL', 'REGULATORY', 1, 1, 1, 1, 1),
            ('GENERAL_COUNSEL', 'TASKS', 1, 1, 1, 1, 1),
            ('GENERAL_COUNSEL', 'AUDIT', 1, 1, 1, 0, 1),
            # COMPLIANCE_OFFICER
            ('COMPLIANCE_OFFICER', 'CONTRACT', 1, 1, 1, 0, 1),
            ('COMPLIANCE_OFFICER', 'PLAYBOOK', 0, 1, 1, 0, 1),
            ('COMPLIANCE_OFFICER', 'REGULATORY', 1, 1, 1, 0, 1),
            ('COMPLIANCE_OFFICER', 'TASKS', 1, 1, 1, 1, 1),
            ('COMPLIANCE_OFFICER', 'AUDIT', 0, 1, 0, 0, 1),
            # DEPT_LEAD
            ('DEPT_LEAD', 'CONTRACT', 1, 1, 0, 0, 0),
            ('DEPT_LEAD', 'PLAYBOOK', 0, 1, 0, 0, 0),
            ('DEPT_LEAD', 'REGULATORY', 0, 1, 0, 0, 0),
            ('DEPT_LEAD', 'TASKS', 0, 1, 1, 0, 0),
            ('DEPT_LEAD', 'AUDIT', 0, 1, 0, 0, 0),
            # AUDITOR
            ('AUDITOR', 'CONTRACT', 0, 1, 0, 0, 0),
            ('AUDITOR', 'PLAYBOOK', 0, 1, 0, 0, 0),
            ('AUDITOR', 'REGULATORY', 0, 1, 0, 0, 0),
            ('AUDITOR', 'TASKS', 0, 1, 0, 0, 0),
            ('AUDITOR', 'AUDIT', 0, 1, 0, 0, 0)
        ]
        cursor.executemany("""
            INSERT INTO access_matrix_rules (role, resource, can_create, can_read, can_update, can_delete, can_signoff)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, matrix_rules)

        # 7. Seed Playbooks
        playbooks = [
            (1, 1, 'MSA', '2.1'),
            (2, 1, 'VENDOR_PROCUREMENT', '1.5'),
            (3, 1, 'EMPLOYMENT_CONTRACT', '3.0'),
            (4, 1, 'CROSS_BORDER_FEMA', '2.0')
        ]
        cursor.executemany("INSERT INTO playbooks (id, organization_id, contract_type, version) VALUES (?, ?, ?, ?)", playbooks)

        # 8. Seed Playbook Rules (FEMA, MSME, Section 27, DPDP, Liability)
        playbook_rules = [
            # Rule 1: Section 27 Indian Contract Act (Non-compete)
            (
                1, 3, 'NON_COMPETE_SEC27',
                'No post-termination restraint of trade shall be imposed. Confidentiality of proprietary intellectual property and non-solicitation of clients/personnel for 12 months is permissible.',
                'The Employee shall not solicit Company customers with whom they had direct commercial interface for 6 months post departure.',
                'Any clause imposing a 1-year, 2-year, or indefinite post-employment prohibition against working with competitors across India.',
                'Section 27 of Indian Contract Act 1872; Percept D\'Mark v. Zaheer Khan (2006); Superintendence Co. v. Krishan Murgai (1980).'
            ),
            # Rule 2: MSMED Act 2006 & Section 43B(h)
            (
                2, 2, 'MSME_PAYMENT',
                'Payment terms for registered Micro and Small enterprises shall not exceed forty-five (45) days from invoice acceptance.',
                'Payment within 30 days from invoice submission upon electronic verification of delivery challan.',
                'Payment terms specified as Net 60, Net 90, or Net 120 days for MSME vendors.',
                'Section 15 & 16 of MSMED Act 2006 read with Section 43B(h) Income Tax Act 1961 (Penal compound interest at 3x RBI Bank Rate + IT deduction disallowance).'
            ),
            # Rule 3: FEMA 1999 & RBI Regulations
            (
                3, 4, 'FEMA_REMITTANCE',
                'All cross-border remittances must be routed through RBI Authorised Dealer Category-I banks, backed by Form 15CA/15CB tax certification and compliant with current Master Directions.',
                'Remittances subject to furnishing of Permanent Account Number (PAN) and tax residence certificate (TRC).',
                'Unregulated foreign currency escrow or direct offshore settlement bypassing Authorised Dealer reporting.',
                'FEMA 1999 Section 10(6), Section 15 Compounding Rules, and RBI Master Direction on Foreign Remittances.'
            ),
            # Rule 4: DPDP Act 2023
            (
                4, 1, 'DPDP_PRIVACY',
                'Data Processor shall process personal data solely on documented instructions of Data Fiduciary, implement ISO 27001 safeguards, and report incidents within 6 hours.',
                'Data Processor shall notify security events within 12 hours and facilitate data principal erasure requests.',
                'Unrestricted third-party sub-processing without prior written consent or unauthorized offshore transfers to blacklisted territories.',
                'Digital Personal Data Protection Act 2023 (DPDP Act) Sections 6, 8(5), 16, and Schedule 1 (Penalties up to Rs. 250 Crores).'
            ),
            # Rule 5: Liability Cap & Indemnity
            (
                5, 1, 'LIABILITY_CAP',
                'Each party aggregate liability shall be capped at 100% of the total fees paid or payable in the 12 months preceding the occurrence. Consequential damages expressly excluded.',
                'Liability capped at 1.5x annual contract value, excluding IP infringement and gross negligence.',
                'Uncapped unlimited liability or indemnity covering indirect, punitive, or loss of profits.',
                'Section 73 and 74 of the Indian Contract Act 1872.'
            )
        ]
        cursor.executemany("""
            INSERT INTO playbook_rules (id, playbook_id, clause_type, standard_clause, fallback_clause, dealbreaker_conditions, statutory_citation_india)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, playbook_rules)

        # 9. Seed 6 Recurring Statutory Calendar Events
        now = datetime.now()
        calendar_events = [
            (
                1, 1, 'MCA', 'MCA Form AOC-4 (Financial Statements Filing)',
                (now + timedelta(days=12)).strftime('%Y-%m-%d'), 'ANNUAL',
                'Section 137 Companies Act 2013: Rs. 100 per day default fee without upper ceiling; Director disqualification risk under Section 164(2).'
            ),
            (
                2, 1, 'LABOUR_MINISTRY', 'PoSH Act Annual Report to District Officer (ICC Compliance)',
                (now + timedelta(days=28)).strftime('%Y-%m-%d'), 'ANNUAL',
                'Section 21 & 22 Sexual Harassment of Women at Workplace Act 2013: Fine up to Rs. 50,000; repeat violation causes cancellation of corporate operating license.'
            ),
            (
                3, 1, 'RBI_FEMA', 'FEMA Form FLA (Foreign Liabilities and Assets Annual Return)',
                (now + timedelta(days=45)).strftime('%Y-%m-%d'), 'ANNUAL',
                'Section 13 FEMA 1999: Late Submission Fee (LSF) of up to Rs. 1,00,000 + 300% compounding penalty for continued default.'
            ),
            (
                4, 1, 'LABOUR_MINISTRY', 'EPF & ESI Monthly ECR Electronic Challan Filing',
                (now + timedelta(days=8)).strftime('%Y-%m-%d'), 'MONTHLY',
                'EPF & MP Act 1952 Section 14B: Damages from 5% to 25% per annum + penal interest at 12% p.a. under Section 7Q.'
            ),
            (
                5, 1, 'GSTN', 'GSTR-3B Monthly Return Filing',
                (now + timedelta(days=16)).strftime('%Y-%m-%d'), 'MONTHLY',
                'CGST Act Section 47: Late fee Rs. 50/day (Rs. 20 for nil return) + 18% p.a. interest on net tax liability under Section 50.'
            ),
            (
                6, 1, 'CERT_IN', 'CERT-In Mandatory 180-Day System & Network Log Audit',
                (now + timedelta(days=5)).strftime('%Y-%m-%d'), 'QUARTERLY',
                'Section 70B(7) Information Technology Act 2000: Imprisonment up to 1 year and fine up to Rs. 1,00,000 for failing to furnish log telemetry.'
            ),
            (
                7, 2, 'MCA', 'Form MGT-7 (Annual Return of Company)',
                (now + timedelta(days=22)).strftime('%Y-%m-%d'), 'ANNUAL',
                'Section 92(5) Companies Act 2013: Fine of Rs. 10,000 + Rs. 100/day for company and each officer in default.'
            )
        ]
        cursor.executemany("""
            INSERT INTO statutory_calendar_events (id, entity_id, statutory_body, compliance_name, due_date, recurring_freq, penalty_clause)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, calendar_events)

        # 10. Seed 4 Pre-loaded Regulatory Circulars
        circulars = [
            (
                1, 'RBI_FEMA', 'RBI Master Direction – External Commercial Borrowings (ECB) All-in-Cost Ceiling Revision',
                'RBI/2026-27/42 A.P. (DIR Series) Circular No. 12', (now - timedelta(days=15)).strftime('%Y-%m-%d'),
                'All Category-I Authorised Dealer banks are advised that the benchmark rate for Foreign Currency ECBs has been updated to SOFR + 550 bps. Mandatory reporting of loan registration number (LRN) on Form ECB within 7 days of agreement execution is strictly enforced. Violations are subject to compounding under Section 15 of FEMA 1999.',
                'HIGH', 'https://rbi.org.in'
            ),
            (
                2, 'DPDPB', 'DPDP Rules 2026: Notice Specifications & Child Consent Age Verification Guidelines',
                'DPDPB/NOTIF/2026/004', (now - timedelta(days=8)).strftime('%Y-%m-%d'),
                'The Data Protection Board of India notifies standard consent notice formats under Section 6 of DPDP Act 2023. Data fiduciaries must present notices in English and all 22 Eighth Schedule languages. Explicit parental consent mechanisms required for minors under 18; behavioral tracking prohibited. Penalty up to Rs. 250 Crores per infraction.',
                'CRITICAL', 'https://www.meity.gov.in'
            ),
            (
                3, 'LABOUR_MINISTRY', 'Code on Wages 2019: 50% Basic Wage Allowance Ceiling Harmonization Circular',
                'MOLE/CW-2026/CIRC-18', (now - timedelta(days=20)).strftime('%Y-%m-%d'),
                'Clarification on wage definition under Section 2(y) of the Code on Wages. Allowances exceeding 50% of total remuneration must be deemed part of wages for calculation of Provident Fund, Gratuity, and ESI contributions. Immediate payroll restructuring mandatory for all covered establishments.',
                'CRITICAL', 'https://labour.gov.in'
            ),
            (
                4, 'MCA', 'MCA Clarification: Form AOC-4 XBRL & MGT-7 Filing Deadlines & Mandatory Share Demat',
                'MCA/ROC/GEN/CIRC-08/2026', (now - timedelta(days=5)).strftime('%Y-%m-%d'),
                'Ministry of Corporate Affairs reminds all Private Limited companies that share capital must be fully dematerialised. Form AOC-4 must be filed within 30 days of AGM and Form MGT-7 within 60 days. Penalty of Rs. 100 per day of default applies without upper ceiling.',
                'HIGH', 'https://mca.gov.in'
            )
        ]
        cursor.executemany("""
            INSERT INTO regulatory_updates (id, statutory_body, title, circular_number, official_date, raw_text, severity, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, circulars)

        # 11. Seed 1 Sample Impact Assessment & Dispatched Tasks
        cursor.execute("""
            INSERT INTO impact_assessments (id, regulatory_update_id, approved_by, status, executive_summary, affected_departments, statutory_deadline)
            VALUES (1, 2, 1, 'DISPATCHED', 
            'DPDP Rules 2026 mandate multilingual consent notices (English + 22 Schedule VIII languages) and parental consent for minors under 18. Exposes entity to Rs. 250 Crore penalty exposure.',
            'INFOSEC_TECH, LEGAL, OPERATIONS', ?)
        """, ((now + timedelta(days=14)).strftime('%Y-%m-%d'),))

        compliance_tasks = [
            (1, 1, 4, 1, 'Deploy Multilingual Consent Notices on Web/Mobile Apps', 'Implement DPDP Schedule VIII consent notices across all registration funnels.', (now + timedelta(days=10)).strftime('%Y-%m-%d'), 'CRITICAL', 'IN_PROGRESS'),
            (2, 1, 4, 1, 'Implement Parental Consent Verification for Users under 18', 'Configure verifiable parental verification prior to data processing of minors.', (now + timedelta(days=12)).strftime('%Y-%m-%d'), 'CRITICAL', 'PENDING'),
            (3, 1, 1, 2, 'Update Standard Data Processing Agreements (DPA) with Vendors', 'Mandate 6-hour CERT-In breach notification in vendor agreements.', (now + timedelta(days=14)).strftime('%Y-%m-%d'), 'HIGH', 'COMPLETED'),
            (4, None, 2, 3, 'Compile Annual PoSH ICC Committee Report for District Officer', 'Collate annual tally of complaints, awareness workshops, and recommendations for Jan 31 filing.', (now + timedelta(days=18)).strftime('%Y-%m-%d'), 'HIGH', 'IN_PROGRESS'),
            (5, None, 3, 4, 'MSME Section 43B(h) Vendor Outstandings Reconciliation', 'Audit all outstanding accounts payable to verify no payments exceed 45 days.', (now + timedelta(days=7)).strftime('%Y-%m-%d'), 'CRITICAL', 'PENDING')
        ]
        cursor.executemany("""
            INSERT INTO compliance_tasks (id, impact_assessment_id, department_id, assigned_to, title, description, deadline, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, compliance_tasks)

        # 12. Seed Task Evidence for completed task
        cursor.execute("""
            INSERT INTO task_evidences (id, task_id, uploaded_by, evidence_file, notes)
            VALUES (1, 3, 2, 'DPDP_Vendor_DPA_Amendment_Signed.pdf', 'All Tier-1 cloud providers and data processors have signed the updated DPA with mandatory 6-hour breach notification covenants.')
        """)

        # 13. Pre-load 1 Sample Reviewed Contract with Clause Findings
        sample_path = ROOT_DIR / 'data' / 'sample_contracts' / 'Master_Services_Agreement_HighRisk_Sample.txt'
        sample_raw = sample_path.read_text(encoding='utf-8') if sample_path.exists() else ''

        cursor.execute("""
            INSERT INTO documents (
                id, entity_id, uploaded_by, original_filename, doc_type, status,
                overall_health_score, liability_score, statutory_score, labour_fema_score, ocr_applied, raw_content
            ) VALUES (1, 1, 1, 'Master_Services_Agreement_Apex_Global_2026.docx', 'MSA', 'REVIEWED', 58, 65, 45, 60, 0, ?)
        """, (sample_raw,))

        clauses = [
            (
                1, 1, 2, 'NON_COMPETE_SEC27',
                'For a period of twenty-four (24) months following termination of employment or engagement for any reason, the Individual/Contractor shall not directly or indirectly engage in, advise, or be employed by any business competing with the Company in India.',
                'HIGH', 'Post-employment non-compete is void under Indian jurisprudence.',
                'Direct violation of Section 27, Indian Contract Act 1872; Percept D\'Mark v. Zaheer Khan (2006).',
                'During the term of this Agreement, Contractor shall devote full business time to Company. Following termination, Contractor is bound solely by perpetual confidentiality of Trade Secrets and 12-month non-solicitation of key personnel.',
                0
            ),
            (
                2, 1, 1, 'MSME_PAYMENT',
                'Payment for all validated invoices shall be disbursed by Buyer within ninety (90) days from the end of the calendar month in which the invoice is submitted.',
                'HIGH', 'Exceeds 45-day statutory payment ceiling for MSME vendors.',
                'Section 15 & 16 of MSMED Act 2006 read with Section 43B(h) Income Tax Act 1961 (Penal compound interest at 3x RBI rate + tax deduction disallowance).',
                'Payment shall be made within forty-five (45) days of invoice date, or within fifteen (15) days in the absence of written agreement, in strict compliance with Section 15 MSMED Act 2006.',
                0
            ),
            (
                3, 1, 3, 'FEMA_REMITTANCE',
                'All payments shall be made directly in foreign currency to Overseas Vendor offshore account without deduction of Indian withholding taxes or compliance with RBI Authorized Dealer approvals.',
                'HIGH', 'Unregulated foreign currency outflow bypassing Authorized Dealer Category-I certification.',
                'Section 10(6) & Section 15 of FEMA 1999 read with Section 195 Income Tax Act (Form 15CA/15CB mandate).',
                'Cross-border remittances shall be routed through an RBI Authorized Dealer Category-I bank, subject to TDS under Section 195 and Form 15CA/15CB clearance.',
                0
            ),
            (
                4, 1, 4, 'LIABILITY_CAP',
                'Contractor shall indemnify, defend, and hold harmless the Client against any and all claims, indirect damages, lost profits, or statutory penalties without any financial cap.',
                'HIGH', 'Uncapped liability covering consequential losses contradicts Section 73/74.',
                'Section 73 & Section 74 of Indian Contract Act 1872 (Remote and indirect damages are non-recoverable).',
                'Aggregate liability shall be capped at 100% of fees paid or payable in the 12 months preceding the claim. Consequential damages excluded.',
                0
            ),
            (
                5, 1, 5, 'GOVERNING_LAW',
                'This Agreement is governed by the laws of India, subject to exclusive jurisdiction of courts in Bengaluru, Karnataka.',
                'COMPLIANT', 'Standard Indian jurisdiction clause.',
                'Fully compliant with Section 28 Indian Contract Act 1872.',
                'Clause is compliant with standard Indian Playbook.',
                1
            )
        ]
        cursor.executemany("""
            INSERT INTO document_clauses (id, document_id, page_number, clause_type, raw_text, risk_tier, flag_reason, indian_law_violation, suggested_redline, is_resolved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, clauses)

        conn.commit()

    # 14. Initialize Cryptographic SHA-256 Audit Trail
    print("[LexSecure Seed] Generating Cryptographic SHA-256 Chained Audit Trail...")
    audit_events = [
        ("GENESIS_INIT", "System", "Organization", 1, {"action": "LexSecure India Pro initialized", "cin": "L74999KA2015PLC089123"}),
        ("PLAYBOOK_ESTABLISHED", "Adv. Vikramaditya Sen", "Playbook", 1, {"contract_type": "MSA", "version": "2.1", "statutes": ["Sec 27 Contract Act", "MSMED Act", "DPDP 2023"]}),
        ("CIRCULAR_INGESTED", "System Ingestion Engine", "RegulatoryUpdate", 2, {"source": "DPDPB", "circular": "DPDPB/NOTIF/2026/004", "severity": "CRITICAL"}),
        ("IMPACT_ASSESSMENT_DISPATCHED", "Sunita Krishnamurthy, FCS", "ImpactAssessment", 1, {"circular_id": 2, "tasks_created": 3, "deadline": (now + timedelta(days=14)).strftime('%Y-%m-%d')}),
        ("CONTRACT_ANALYZED", "Adv. Vikramaditya Sen", "Document", 1, {"filename": "Master_Services_Agreement_Apex_Global_2026.docx", "health_score": 58, "dealbreakers": 4}),
        ("TASK_EVIDENCE_ATTACHED", "Sunita Krishnamurthy, FCS", "ComplianceTask", 3, {"evidence_file": "DPDP_Vendor_DPA_Amendment_Signed.pdf", "notes": "Tier-1 vendors signed DPA"})
    ]

    for event_type, actor, target_model, target_id, details in audit_events:
        db.log_tamper_evident_event(
            organization_id=1,
            actor_id=1 if actor != "System" else None,
            actor_name=actor,
            event_type=event_type,
            target_model=target_model,
            target_id=target_id,
            details_dict=details
        )

    print("[LexSecure Seed] Enterprise Legal & Regulatory Data Seeded Successfully!")

if __name__ == "__main__":
    seed_enterprise_data()
