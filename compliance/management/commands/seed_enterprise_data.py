from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
import json
from compliance.models import (
    Organization, Entity, Department, User, AccessMatrixRule,
    Playbook, PlaybookRule, Document, DocumentClause,
    RegulatoryUpdate, ImpactAssessment, ComplianceTask,
    TaskEvidence, StatutoryCalendarEvent, TamperAuditLog
)

class Command(BaseCommand):
    help = "Seed Comprehensive Enterprise Legal & Regulatory Data for LexSecure India Pro"

    def handle(self, *args, **options):
        self.stdout.write("Initializing LexSecure India Pro Enterprise Data...")

        # 1. Organization
        org, _ = Organization.objects.get_or_create(
            id=1,
            defaults={
                'name': 'Apex Enterprises India Holdings Ltd.',
                'pan_number': 'AAACA1234F',
                'cin_number': 'L74999KA2015PLC089123',
                'industry_type': 'GENERAL'
            }
        )

        # 2. Operating Subsidiaries
        tech_entity, _ = Entity.objects.get_or_create(
            id=1,
            defaults={
                'organization': org,
                'legal_name': 'Apex Global India Tech Private Limited',
                'entity_type': 'PVT_LTD',
                'registered_state': 'Karnataka'
            }
        )
        mfg_entity, _ = Entity.objects.get_or_create(
            id=2,
            defaults={
                'organization': org,
                'legal_name': 'Apex Precision Forge India Limited',
                'entity_type': 'PUBLIC_LTD',
                'registered_state': 'Maharashtra'
            }
        )

        # 3. Departments
        depts_list = ['LEGAL', 'HR_LABOUR', 'FINANCE_TAX', 'INFOSEC_TECH', 'OPERATIONS']
        for d in depts_list:
            Department.objects.get_or_create(entity=tech_entity, name=d)
            Department.objects.get_or_create(entity=mfg_entity, name=d)

        legal_dept = Department.objects.filter(entity=tech_entity, name='LEGAL').first()
        hr_dept = Department.objects.filter(entity=tech_entity, name='HR_LABOUR').first()
        fin_dept = Department.objects.filter(entity=tech_entity, name='FINANCE_TAX').first()
        tech_dept = Department.objects.filter(entity=tech_entity, name='INFOSEC_TECH').first()

        # 4. Users
        users_data = [
            (1, 'general.counsel@apexindia.com', 'Adv. Vikramaditya Sen', 'GENERAL_COUNSEL', legal_dept, '1234'),
            (2, 'compliance.lead@apexindia.com', 'Sunita Krishnamurthy, FCS', 'COMPLIANCE_OFFICER', legal_dept, '1234'),
            (3, 'hr.director@apexindia.com', 'Rajesh K. Sharma', 'DEPT_LEAD', hr_dept, '1234'),
            (4, 'cfo.office@apexindia.com', 'Suresh Nambiar, CA', 'DEPT_LEAD', fin_dept, '1234'),
            (5, 'auditor@statutoryaudit.in', 'Pooja Hegde, Partner', 'AUDITOR', None, '1234'),
        ]
        for uid, email, name, role, dept, pin in users_data:
            User.objects.update_or_create(
                id=uid,
                defaults={
                    'organization': org,
                    'email': email,
                    'full_name': name,
                    'role': role,
                    'department': dept,
                    'pin': pin,
                    'is_active': True
                }
            )

        # 5. Access Matrix Rules
        resources = ['CONTRACT', 'PLAYBOOK', 'REGULATORY', 'TASKS', 'AUDIT']
        for res in resources:
            AccessMatrixRule.objects.update_or_create(
                role='GENERAL_COUNSEL', resource=res,
                defaults={'can_create': True, 'can_read': True, 'can_update': True, 'can_delete': True, 'can_signoff': True}
            )
            AccessMatrixRule.objects.update_or_create(
                role='COMPLIANCE_OFFICER', resource=res,
                defaults={'can_create': True, 'can_read': True, 'can_update': True, 'can_delete': False, 'can_signoff': True}
            )
            AccessMatrixRule.objects.update_or_create(
                role='DEPT_LEAD', resource=res,
                defaults={'can_create': False, 'can_read': True, 'can_update': (res == 'TASKS'), 'can_delete': False, 'can_signoff': False}
            )
            AccessMatrixRule.objects.update_or_create(
                role='AUDITOR', resource=res,
                defaults={'can_create': False, 'can_read': True, 'can_update': False, 'can_delete': False, 'can_signoff': False}
            )

        # 6. Playbook & Rules
        playbook, _ = Playbook.objects.get_or_create(
            id=1,
            defaults={'organization': org, 'contract_type': 'MSA', 'version': '2.1'}
        )
        rules = [
            (
                'NON_COMPETE_SEC27',
                'No post-termination restraint of trade shall be imposed. Confidentiality of proprietary IP and 12-month non-solicitation permissible.',
                'Non-solicitation of active customers for 6 months post departure.',
                'Any 1-year or 2-year post-employment prohibition against working with competitors across India.',
                'Section 27 Indian Contract Act 1872; Percept D\'Mark v. Zaheer Khan (2006).'
            ),
            (
                'MSME_PAYMENT',
                'Payment terms to Micro and Small enterprises must not exceed 45 days where agreed in writing, or 15 days in absence of agreement.',
                '30-day payment cycle with electronic receipt acknowledgement.',
                'Payment terms exceeding 45 days (e.g. 60, 90 or 120 days).',
                'Section 15 & 16 MSMED Act 2006, Section 43B(h) Income Tax Act (tax deduction disallowance + 3x RBI bank rate compound interest).'
            ),
            (
                'LIABILITY_CAP',
                'Aggregate liability capped at 100% of fees paid in preceding 12 months. Consequential, punitive damages excluded.',
                'Cap set at 1.5x annual contract value with standard carve-outs for confidentiality and gross negligence.',
                'Uncapped indemnification or unlimited general liability for indirect damages.',
                'Indian Contract Act 1872 Section 73 & 74 (Hadley v. Baxendale principle applied in India).'
            ),
            (
                'DPDP_PRIVACY',
                'Data Processor shall process digital personal data solely on documented instructions of Data Fiduciary and maintain reasonable security safeguards.',
                'Mandatory notification within 24 hours of data breach.',
                'Processor disclaiming liability for customer data security breaches.',
                'Section 6 & Section 8 of Digital Personal Data Protection Act 2023 (Penalty exposure up to ₹250 Crores).'
            ),
            (
                'FEMA_REMITTANCE',
                'Cross-border payments subject to RBI Liberalised Remittance Scheme and Form A2 declarations under FEMA 1999.',
                'Authorized Dealer Category-1 Bank certification clause.',
                'Automatic offshore equity transfer without RBI FC-TRS compounding or prior approvals.',
                'Foreign Exchange Management Act 1999 & Foreign Exchange Management (Overseas Investment) Rules 2022.'
            )
        ]
        for ctype, std, fall, deal, cit in rules:
            PlaybookRule.objects.update_or_create(
                playbook=playbook, clause_type=ctype,
                defaults={
                    'standard_clause': std,
                    'fallback_clause': fall,
                    'dealbreaker_conditions': deal,
                    'statutory_citation_india': cit
                }
            )

        # 7. Statutory Calendar Events
        now = datetime.now().date()
        cal_events = [
            (tech_entity, 'MCA', 'MCA Form AOC-4 (Financial Statements Filing)', now + timedelta(days=12), 'ANNUAL', 'Section 137 Companies Act 2013: Rs. 100 per day default fee without upper ceiling.'),
            (tech_entity, 'LABOUR_MINISTRY', 'PoSH Annual Report Filing with District Officer', now + timedelta(days=24), 'ANNUAL', 'Section 26 PoSH Act 2013: Up to Rs. 50,000 fine and cancellation of business license on repeated non-compliance.'),
            (tech_entity, 'RBI_FEMA', 'RBI Foreign Liabilities & Assets (FLA) Annual Return', now + timedelta(days=45), 'ANNUAL', 'FEMA 1999 Section 13: Compounding penalties up to 300% of sum involved in unauthorized foreign exchange reporting delay.'),
            (tech_entity, 'LABOUR_MINISTRY', 'EPFO & ESIC Monthly Contribution & ECR Filing', now + timedelta(days=7), 'MONTHLY', 'EPF & MP Act 1952: 12% mandatory contribution; damages up to 25% p.a. + IPC 406/409 criminal breach of trust risk.'),
            (tech_entity, 'GSTN', 'GSTR-3B Monthly Summary Tax Return', now + timedelta(days=9), 'MONTHLY', 'CGST Act 2017: Late fee of Rs. 50/day and 18% p.a. interest on unpaid net tax liability.'),
            (tech_entity, 'CERT_IN', 'CERT-In Incident Log Review & 180-Day System Log Audit', now + timedelta(days=18), 'QUARTERLY', 'IT (The Indian Computer Emergency Response Team) Rules 2013 & Cyber Directives: Non-compliance carries imprisonment up to 1 year under Section 70B(7) IT Act.')
        ]
        for ent, body, cname, ddate, freq, pen in cal_events:
            StatutoryCalendarEvent.objects.update_or_create(
                entity=ent, compliance_name=cname,
                defaults={'statutory_body': body, 'due_date': ddate, 'recurring_freq': freq, 'penalty_clause': pen}
            )

        # 8. Regulatory Circulars
        circulars = [
            ('DPDPB', 'DPDP Rules 2026: Multilingual Notice Specifications & Minor Consent Guidelines', 'DPDPB/NOTIF/2026/004', now - timedelta(days=8), 'Data Protection Board of India notifies standard consent notice formats under Section 6 of DPDP Act 2023. Multi-language format mandatory across Schedule VIII Indian languages. Penalties up to ₹250 Cr for data processing violations.', 'CRITICAL', 'https://meity.gov.in'),
            ('RBI_FEMA', 'Master Direction - External Commercial Borrowings (ECB) All-in-Cost Ceiling Revision', 'RBI/FED/2026-27/112', now - timedelta(days=14), 'Reserve Bank of India updates all-in-cost ceiling for foreign currency External Commercial Borrowings. Mandatory Form ECB reporting within 7 days of loan draw down.', 'HIGH', 'https://rbi.org.in'),
            ('LABOUR_MINISTRY', 'Unified National Wage Floor & Overtime Normalization Advisory under Code on Wages', 'MOLE/WAGES/2026/089', now - timedelta(days=19), 'Ministry of Labour & Employment directive regarding basic pay threshold maintaining minimum 50% of total CTC to prevent gratuity and PF wage evasion.', 'HIGH', 'https://labour.gov.in'),
            ('MCA', 'Companies (Significant Beneficial Ownership) Amendment Rules 2026', 'MCA/DIR/2026/033', now - timedelta(days=27), 'MCA issues clarification on reporting indirect foreign shareholding in Form BEN-2 to curb round-tripping and unverified nominee shareholdings.', 'ADVISORY', 'https://mca.gov.in')
        ]
        reg_objs = []
        for body, title, cnum, odate, raw, sev, url in circulars:
            reg, _ = RegulatoryUpdate.objects.update_or_create(
                circular_number=cnum,
                defaults={'statutory_body': body, 'title': title, 'official_date': odate, 'raw_text': raw, 'severity': sev, 'source_url': url}
            )
            reg_objs.append(reg)

        # 9. Impact Assessment & Compliance Tasks
        first_reg = reg_objs[0]
        ia, _ = ImpactAssessment.objects.update_or_create(
            regulatory_update=first_reg,
            defaults={
                'approved_by': User.objects.get(id=1),
                'status': 'DISPATCHED',
                'executive_summary': 'DPDP Act 2023 requires all enterprise customer interfaces, mobile apps, and employee portals to feature bilingual/multilingual consent notices in compliant formats before collection of personal data.',
                'affected_departments': 'LEGAL, INFOSEC_TECH, OPERATIONS',
                'statutory_deadline': now + timedelta(days=30)
            }
        )

        tasks = [
            (tech_dept, 'Audit Digital Consent Architecture for DPDP Act 2023', 'Implement granular consent checkboxes and withdrawal mechanisms across all Indian web endpoints.', now + timedelta(days=14), 'CRITICAL', 'PENDING'),
            (legal_dept, 'Revise Data Processing Agreements (DPA) with Third-Party Cloud Vendors', 'Ensure cross-border transfer complies with central government whitelist under Section 16 DPDP Act.', now + timedelta(days=21), 'HIGH', 'IN_PROGRESS'),
            (hr_dept, 'Update Employee Privacy Notice & Jan 31 PoSH Compliance Docket', 'Verify statutory employee consent documentation and annual ICC report filings.', now + timedelta(days=10), 'HIGH', 'COMPLETED')
        ]
        for d, t_title, t_desc, t_dl, t_pri, t_stat in tasks:
            ComplianceTask.objects.update_or_create(
                impact_assessment=ia, title=t_title,
                defaults={'department': d, 'assigned_to': User.objects.get(id=1), 'description': t_desc, 'deadline': t_dl, 'priority': t_pri, 'status': t_stat}
            )

        # 10. Sample Document with Highlighted Clauses
        sample_contract_text = """MASTER SERVICES & PLATFORM LICENSE AGREEMENT
Between: CloudCore Technologies India Pvt. Ltd. ("Vendor") and Apex Global India Tech Pvt. Ltd. ("Customer")
Jurisdiction: Bengaluru, Karnataka, India

1. SCOPE AND SERVICES
Vendor agrees to deliver enterprise cloud hosting and regulatory compute pipelines as specified in Exhibit A.

2. PAYMENT TERMS AND INVOICING
Customer shall pay all undisputed invoice amounts within ninety (90) days of invoice date. Vendor waives any right to penal interest regardless of supplier MSME registration status.

3. LIMITATION OF LIABILITY AND INDEMNITY
Customer agrees to indemnify, defend, and hold harmless Vendor without any monetary cap for all third-party IP or indirect operational claims arising out of this Agreement.

4. POST-TERMINATION NON-COMPETE RESTRICTION
For a period of eighteen (18) months following termination of this Agreement, neither party nor its key engineering executives shall engage, consult, or provide software services to any competing technology entity operating anywhere within the territory of India.

5. CROSS-BORDER DATA TRANSFERS & DPDP ALIGNMENT
Vendor acknowledges that Customer Personal Data shall be processed under the Digital Personal Data Protection Act 2023. Vendor will notify Customer within 24 hours of any confirmed security vulnerability or data breach.

6. GOVERNING LAW AND DISPUTE RESOLUTION
This Agreement shall be governed by and construed in accordance with the laws of India. Courts at Bengaluru, Karnataka shall have exclusive jurisdiction."""

        doc, _ = Document.objects.update_or_create(
            id=1,
            defaults={
                'entity': tech_entity,
                'uploaded_by': User.objects.get(id=1),
                'original_filename': 'Master_Services_Agreement_CloudCore_2026.docx',
                'doc_type': 'MSA',
                'status': 'REVIEWED',
                'overall_health_score': 58,
                'liability_score': 45,
                'statutory_score': 52,
                'labour_fema_score': 78,
                'ocr_applied': False,
                'raw_content': sample_contract_text
            }
        )

        sample_clauses = [
            (
                'NON_COMPETE_SEC27',
                'For a period of eighteen (18) months following termination of this Agreement, neither party nor its key engineering executives shall engage, consult, or provide software services to any competing technology entity operating anywhere within the territory of India.',
                'HIGH',
                'Post-employment negative covenants in restraint of trade are void ab initio in India.',
                'Section 27 Indian Contract Act 1872; Supreme Court of India in Percept D\'Mark (India) v. Zaheer Khan (2006) 4 SCC 227.',
                'Standard Playbook Redline: Delete post-termination non-compete completely. Replace with standard 12-month customer non-solicitation and strict non-disclosure of proprietary trade secrets.',
                False
            ),
            (
                'MSME_PAYMENT',
                'Customer shall pay all undisputed invoice amounts within ninety (90) days of invoice date. Vendor waives any right to penal interest regardless of supplier MSME registration status.',
                'HIGH',
                'Payment period exceeds 45 days. Statutory rights under MSMED Act cannot be contractually waived.',
                'Section 15 & 16 of MSMED Act 2006 and Section 43B(h) Income Tax Act 1961 (Buyer loses tax deduction and owes 3x RBI bank rate compound interest).',
                'Standard Playbook Redline: "Payment shall be made within forty-five (45) days of receipt of invoice or delivery of services, strictly conforming to Section 15 of the MSMED Act 2006."',
                False
            ),
            (
                'LIABILITY_CAP',
                'Customer agrees to indemnify, defend, and hold harmless Vendor without any monetary cap for all third-party IP or indirect operational claims arising out of this Agreement.',
                'CAUTION',
                'Uncapped third-party indemnity exposes entity to asymmetrical liability without mutual defense or threshold.',
                'Section 73 & Section 74 Indian Contract Act 1872 (Unreasonable punitive indemnities subject to judicial mitigation).',
                'Standard Playbook Redline: "Each party\'s aggregate liability under this Agreement shall not exceed the total fees paid or payable in the twelve (12) months preceding the claim."',
                False
            ),
            (
                'DPDP_PRIVACY',
                'Vendor acknowledges that Customer Personal Data shall be processed under the Digital Personal Data Protection Act 2023. Vendor will notify Customer within 24 hours of any confirmed security vulnerability or data breach.',
                'COMPLIANT',
                'Complies with DPDP Act 2023 fiduciary obligations.',
                'Section 8 DPDP Act 2023.',
                None,
                True
            )
        ]
        for ctype, raw, tier, reason, law, redline, res in sample_clauses:
            DocumentClause.objects.update_or_create(
                document=doc, clause_type=ctype,
                defaults={
                    'raw_text': raw,
                    'risk_tier': tier,
                    'flag_reason': reason,
                    'indian_law_violation': law,
                    'suggested_redline': redline,
                    'is_resolved': res,
                    'page_number': 1
                }
            )

        # 11. Chained SHA-256 Audit Trail
        TamperAuditLog.objects.filter(organization=org).delete()
        genesis = TamperAuditLog.objects.create(
            organization=org,
            actor_id=1,
            actor_name='Adv. Vikramaditya Sen',
            event_type='GENESIS_INIT',
            target_model='Organization',
            target_id=org.id,
            details_json=json.dumps({"initialized": True, "pan": org.pan_number, "state": "Karnataka"})
        )
        TamperAuditLog.objects.create(
            organization=org,
            actor_id=1,
            actor_name='Adv. Vikramaditya Sen',
            event_type='CONTRACT_UPLOAD',
            target_model='Document',
            target_id=doc.id,
            details_json=json.dumps({"doc_name": doc.original_filename, "score": doc.overall_health_score})
        )
        TamperAuditLog.objects.create(
            organization=org,
            actor_id=2,
            actor_name='Sunita Krishnamurthy, FCS',
            event_type='IMPACT_ASSESSMENT_DISPATCHED',
            target_model='ImpactAssessment',
            target_id=ia.id,
            details_json=json.dumps({"circular_number": first_reg.circular_number, "tasks_created": 3})
        )

        self.stdout.write(self.style.SUCCESS("Enterprise Legal & Regulatory Data Seeded Successfully with 100% Chained Cryptographic Ledger!"))
