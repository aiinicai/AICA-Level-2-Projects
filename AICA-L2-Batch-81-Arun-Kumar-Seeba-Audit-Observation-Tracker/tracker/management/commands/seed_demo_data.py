from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
from tracker.models import (
    User, Client, ClientContact, Staff, Engagement, EngagementTeam,
    Query, QueryResponse, Attachment, ExceptionApproval, AuditTrail
)

class Command(BaseCommand):
    help = 'Seeds database with realistic demo data for viva walkthrough'

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding...")

        # Clear existing data
        QueryResponse.objects.all().delete()
        Attachment.objects.all().delete()
        ExceptionApproval.objects.all().delete()
        Query.objects.all().delete()
        EngagementTeam.objects.all().delete()
        Engagement.objects.all().delete()
        Staff.objects.all().delete()
        ClientContact.objects.all().delete()
        Client.objects.all().delete()
        AuditTrail.objects.all().delete()
        User.objects.all().delete()

        # 1. Create Admin
        admin_user = User.objects.create_superuser(
            email='admin@firm.com',
            password='Admin@123',
            full_name='Firm Administrator'
        )
        admin_user.must_change_password = False
        admin_user.save()

        # 2. Create Staff & Users
        staff_data = [
            ('EMP001', 'partner1@firm.com', 'CA Rajesh Sharma', 'Partner', '104522', 'Partner@123', None),
            ('EMP002', 'partner2@firm.com', 'CA Meera Nair', 'Partner', '108934', 'Partner@123', None),
            ('EMP003', 'manager1@firm.com', 'CA Amit Verma', 'Manager', '521908', 'Manager@123', 'EMP001'),
            ('EMP004', 'manager2@firm.com', 'CA Sneha Iyer', 'Manager', '534120', 'Manager@123', 'EMP002'),
            ('EMP005', 'senior1@firm.com', 'Rohan Deshmukh', 'Senior', None, 'Senior@123', 'EMP003'),
            ('EMP006', 'senior2@firm.com', 'Priya Sundaram', 'Senior', None, 'Senior@123', 'EMP004'),
            ('EMP007', 'article1@firm.com', 'Vikram Malhotra', 'Article Assistant', None, 'Article@123', 'EMP005'),
            ('EMP008', 'article2@firm.com', 'Ananya Rao', 'Article Assistant', None, 'Article@123', 'EMP006'),
        ]

        staff_map = {}
        for scode, email, name, desig, mem_no, pwd, rep_code in staff_data:
            user = User.objects.create_user(
                email=email,
                password=pwd,
                full_name=name,
                user_type='STAFF',
                must_change_password=False
            )
            staff = Staff.objects.create(
                staff_code=scode,
                user=user,
                full_name=name,
                email=email,
                designation=desig,
                membership_no=mem_no,
                date_of_joining=date(2022, 4, 1),
                status='Active',
                created_by=admin_user
            )
            staff_map[scode] = staff

        # Set reporting hierarchy
        for scode, email, name, desig, mem_no, pwd, rep_code in staff_data:
            if rep_code and rep_code in staff_map:
                st = staff_map[scode]
                st.reporting_to = staff_map[rep_code]
                st.save()

        # 3. Create Clients & Contacts
        clients_data = [
            ('CL001', 'Apex Industries Limited', 'Apex Group', 'Public Ltd', 'Manufacturing', 'Plot 42, MIDC Industrial Area', 'Mumbai', 'Maharashtra', True, 'High', date(2018, 5, 10)),
            ('CL002', 'Horizon Healthcare Pvt Ltd', 'Horizon Care', 'Pvt Ltd', 'Healthcare', '88, Bannerghatta Road', 'Bengaluru', 'Karnataka', False, 'Medium', date(2020, 8, 15)),
            ('CL003', 'Zenith Finserve LLP', 'Zenith Capital', 'LLP', 'Financial Services', 'BKC Finance Centre, Tower B', 'Mumbai', 'Maharashtra', False, 'High', date(2021, 1, 20)),
            ('CL004', 'Stellar Retail Solutions Pvt Ltd', 'Stellar Group', 'Pvt Ltd', 'Retail', '12, Connaught Place', 'New Delhi', 'Delhi', False, 'Low', date(2019, 11, 5)),
            ('CL005', 'GreenPower Infrastructure Trust', 'GreenPower InvIT', 'Trust', 'Energy', 'Sector 62, Cyber City', 'Gurugram', 'Haryana', True, 'Medium', date(2022, 6, 1)),
        ]

        client_map = {}
        for code, name, grp, const, ind, addr, city, state, listed, risk, csince in clients_data:
            client = Client.objects.create(
                client_code=code,
                client_name=name,
                group_name=grp,
                constitution=const,
                industry=ind,
                registered_address=addr,
                city=city,
                state=state,
                financial_year_end='31st March',
                listed_status=listed,
                risk_category=risk,
                client_since=csince,
                status='Active',
                created_by=admin_user
            )
            client_map[code] = client

        # Contacts with login
        contacts_data = [
            ('CL001', 'Suresh Menon', 'Chief Financial Officer', 'cfo@apexindustries.com', '+91 98201 11223', True, 'Client@123'),
            ('CL001', 'Kavita Nair', 'GM - Finance & Accounts', 'kavita.nair@apexindustries.com', '+91 98201 44556', False, 'Client@123'),
            ('CL002', 'Dr. Arvind Swamy', 'Finance Controller', 'finance.head@horizonhealth.com', '+91 98450 77889', True, 'Client@123'),
            ('CL002', 'Ramesh Babu', 'Accounts Manager', 'accounts@horizonhealth.com', '+91 98450 99001', False, 'Client@123'),
            ('CL003', 'Neha Singhania', 'Head of Compliance', 'compliance@zenithfin.com', '+91 99302 33445', True, 'Client@123'),
            ('CL004', 'Manoj Gupta', 'Finance Manager', 'accounts@stellarretail.com', '+91 98110 55667', True, 'Client@123'),
            ('CL005', 'Raghavan Iyer', 'VP - Taxation & Audit', 'trustee.rep@greenpowertrust.com', '+91 97170 88990', True, 'Client@123'),
        ]

        contact_map = {}
        for ccode, cname, desig, email, mobile, is_coord, pwd in contacts_data:
            c_user = User.objects.create_user(
                email=email,
                password=pwd,
                full_name=cname,
                user_type='CLIENT',
                must_change_password=False
            )
            contact = ClientContact.objects.create(
                client=client_map[ccode],
                user=c_user,
                contact_name=cname,
                designation=desig,
                email=email,
                mobile=mobile,
                is_primary_coordinator=is_coord,
                status='Active',
                created_by=admin_user
            )
            contact_map[email] = contact

        # 4. Create Engagements
        today = timezone.localdate()
        engagements_data = [
            ('CL001', '2024-25', 'Statutory Audit', date(2024, 4, 1), date(2025, 3, 31), date(2025, 4, 15), date(2025, 6, 30), 'In Progress', False),
            ('CL001', '2025-26', 'Statutory Audit', date(2025, 4, 1), date(2026, 3, 31), date(2026, 4, 10), date(2026, 7, 31), 'In Progress', False),
            ('CL002', '2025-26', 'Internal Audit', date(2025, 4, 1), date(2026, 3, 31), date(2026, 5, 1), date(2026, 8, 15), 'In Progress', True),
            ('CL003', '2025-26', 'IFC Testing', date(2025, 4, 1), date(2026, 3, 31), date(2026, 6, 1), date(2026, 9, 30), 'Planned', False),
        ]

        eng_map = {}
        for ccode, fy, atype, pfrom, pto, pstart, tcomp, status, coord_toggle in engagements_data:
            eng = Engagement.objects.create(
                engagement_code=Engagement.generate_code(ccode, fy, atype),
                client=client_map[ccode],
                financial_year=fy,
                audit_type=atype,
                period_from=pfrom,
                period_to=pto,
                planned_start=pstart,
                target_completion=tcomp,
                status=status,
                client_coordinator_review_enabled=coord_toggle,
                created_by=admin_user
            )
            eng_map[eng.engagement_code] = eng

        # Assign Teams
        e1 = eng_map['CL001/FY2425/SA']
        EngagementTeam.objects.create(engagement=e1, staff=staff_map['EMP001'], role_on_engagement='Partner', is_reviewer=False, independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e1, staff=staff_map['EMP002'], role_on_engagement='Partner', is_reviewer=True, independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e1, staff=staff_map['EMP003'], role_on_engagement='Manager', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e1, staff=staff_map['EMP005'], role_on_engagement='Senior', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e1, staff=staff_map['EMP007'], role_on_engagement='Article Assistant', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)

        e2 = eng_map['CL001/FY2526/SA']
        EngagementTeam.objects.create(engagement=e2, staff=staff_map['EMP001'], role_on_engagement='Partner', is_reviewer=False, independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e2, staff=staff_map['EMP003'], role_on_engagement='Manager', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e2, staff=staff_map['EMP005'], role_on_engagement='Senior', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e2, staff=staff_map['EMP007'], role_on_engagement='Article Assistant', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)

        e3 = eng_map['CL002/FY2526/IA']
        EngagementTeam.objects.create(engagement=e3, staff=staff_map['EMP002'], role_on_engagement='Partner', is_reviewer=False, independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e3, staff=staff_map['EMP004'], role_on_engagement='Manager', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e3, staff=staff_map['EMP006'], role_on_engagement='Senior', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e3, staff=staff_map['EMP008'], role_on_engagement='Article Assistant', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)

        e4 = eng_map['CL003/FY2526/IFC']
        EngagementTeam.objects.create(engagement=e4, staff=staff_map['EMP001'], role_on_engagement='Partner', is_reviewer=False, independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)
        EngagementTeam.objects.create(engagement=e4, staff=staff_map['EMP004'], role_on_engagement='Manager', independence_declared=True, independence_declared_on=timezone.now(), created_by=admin_user)

        # 5. Create Realistic Queries
        self.stdout.write("Seeding queries across engagements...")

        # E1 Queries (Apex FY2425)
        q_e1_defs = [
            (
                'Observation', 'Revenue', 'Unbilled Revenue Recognition in ERP Without Delivery Challan',
                'Testing of Q4 revenue revealed ₹ 18.5 Lakhs booked without signed delivery challans or customer acceptance.',
                'Signed PODs / Customer confirmations for 12 sampled invoices.', Decimal('1850000.00'), 'High', 'High',
                staff_map['EMP005'], contact_map['cfo@apexindustries.com'],
                'Revenue recognized prior to transfer of control to customer.',
                'Ind AS 115 (Revenue from Contracts with Customers) - Control transfer criteria.',
                'Sales team booked billing to meet year-end targets before dispatch verification.',
                'Premature revenue recognition resulting in material misstatement of Q4 revenue.',
                'Implement automated 3-way match between Invoice, E-way bill, and signed POD before revenue posting in SAP.',
                'Closed', staff_map['EMP003'], 'Management provided signed PODs for ₹ 16.2L; remaining ₹ 2.3L reversed in ledger with journal voucher #JV-2025-0891. Verified.'
            ),
            (
                'Observation', 'Fixed Assets', 'Physical Verification Discrepancies in Plant Machinery',
                'Annual physical verification report noted 4 unserviceable CNC machines still carried in Gross Block.',
                'FAR register and disposal work order.', Decimal('4500000.00'), 'Medium', 'Medium',
                staff_map['EMP007'], contact_map['kavita.nair@apexindustries.com'],
                'Obsolete machinery not derecognized or impaired in the books.',
                'Ind AS 16 - Property, Plant & Equipment and Ind AS 36 - Impairment.',
                'Delay in disposal committee approvals and asset capitalization reconciliations.',
                'Overstatement of fixed assets carrying value and non-provision of impairment.',
                'Scrap/write-off obsolete CNC units and update fixed asset register.',
                'Closed', staff_map['EMP003'], 'Scrap sale approved by Board; write-off of ₹ 4.5 Lakhs booked. Fixed asset register updated.'
            ),
            (
                'Control Deficiency', 'Statutory Dues', 'Delay in Remittance of Withholding Tax (TDS on Contracts)',
                'TDS deducted under Section 194C for February was deposited on 15th April resulting in mandatory interest liability.',
                'Challan 281 copies and Form 26Q return.', Decimal('85000.00'), 'Low', 'Low',
                staff_map['EMP005'], contact_map['kavita.nair@apexindustries.com'],
                'Delayed statutory payment past the 7th day of succeeding month.',
                'Income Tax Act 1961 - Section 200 & 201(1A).',
                'Finance team bottleneck during financial year-end closing.',
                'Interest penalty under Section 201(1A) and potential disallowance under Section 40(a)(ia).',
                'Automate monthly statutory calendar alerts and integrate TDS payment with banking portal.',
                'Closed', staff_map['EMP001'], 'Interest of ₹ 2,550 deposited via challan #IT-98214. Checked and closed.'
            ),
            (
                'Information Request', 'Purchases', 'Vendor Balance Confirmation for Top 10 Suppliers',
                'Independent balance confirmation letters requested for suppliers having balances exceeding ₹ 50 Lakhs.',
                'Direct balance confirmation letters on vendor letterheads.', Decimal('52000000.00'), 'Medium', 'Medium',
                staff_map['EMP005'], contact_map['cfo@apexindustries.com'],
                '', '', '', '', '',
                'Closed', staff_map['EMP003'], '9 out of 10 direct confirmations received with zero variance; 1 reconciled with transit goods.'
            ),
            (
                'Observation', 'Inventory', 'Non-Provision for Slow-Moving Raw Material Inventory',
                'Raw materials aging over 365 days amounting to ₹ 32 Lakhs without inventory obsolescence allowance.',
                'Inventory aging schedule and NRV assessment sheet.', Decimal('3200000.00'), 'High', 'High',
                staff_map['EMP005'], contact_map['cfo@apexindustries.com'],
                'Inventory carried at historical cost without testing for Net Realisable Value (NRV).',
                'Ind AS 2 - Inventories (Lower of Cost and NRV).',
                'Absence of a quarterly automated slow-moving inventory classification report in ERP.',
                'Inventory overstated by estimated ₹ 12 Lakhs.',
                'Establish policy for gradual provisioning on inventory stagnant for over 180 and 365 days.',
                'Closed - Exception Approved', staff_map['EMP001'], 'Approved under EX-202505-0001: Material utilized in batch production in May 2025.'
            ),
            (
                'Observation', 'Purchases', 'Duplicate Vendor Invoices Sampled in Sub-ledger',
                'Query raised regarding two apparent duplicate invoice entries for M/s Delta Logistics.',
                'Ledger extract and invoice copies.', Decimal('120000.00'), 'Low', 'Low',
                staff_map['EMP007'], contact_map['kavita.nair@apexindustries.com'],
                'Apparent duplicate entry in accounts payable sub-ledger.',
                'Standard internal voucher verification procedures.',
                'Two separate shipments billed under similar invoice numbers.',
                'Risk of double payment.',
                'Implement duplicate invoice check on vendor code + invoice number in ERP.',
                'Withdrawn', staff_map['EMP001'], 'Withdrawn: Verified as separate billings for two distinct consignment waybills.'
            ),
        ]

        prior_year_q_ref = None
        for q_idx, (qtype, area, title, desc, doc_req, amt, prio, risk, r_by, c_contact, cond, crit, cause, eff, rec, stat, cl_by, cl_rem) in enumerate(q_e1_defs, start=1):
            q_obj = Query.objects.create(
                query_no=f"{e1.engagement_code}/{q_idx:04d}",
                serial_no=q_idx,
                engagement=e1,
                query_type=qtype,
                area=area,
                title=title,
                description=desc,
                document_requested=doc_req,
                amount_involved=amt,
                priority=prio,
                risk_rating=risk,
                raised_by=r_by,
                raised_on=timezone.now() - timedelta(days=90 - q_idx*2),
                issued_on=timezone.now() - timedelta(days=88 - q_idx*2),
                due_date=timezone.localdate() - timedelta(days=70 - q_idx*2),
                assigned_to_client_contact=c_contact,
                condition=cond,
                criteria=crit,
                cause=cause,
                effect_risk=eff,
                recommendation=rec,
                status=stat,
                closed_by=cl_by,
                closed_on=timezone.now() - timedelta(days=40 - q_idx*2),
                closure_remarks=cl_rem,
                created_by=r_by.user
            )
            if q_idx == 1:
                prior_year_q_ref = q_obj

            QueryResponse.objects.create(
                query=q_obj,
                response_text=f"Management explanation submitted regarding {title}. Necessary documentation attached and reconciled with ledger.",
                responded_by_type='Client',
                responded_by_user=c_contact.user,
                responded_on=timezone.now() - timedelta(days=80 - q_idx*2),
                is_client_submission=True,
                sequence_no=1
            )
            QueryResponse.objects.create(
                query=q_obj,
                response_text="Audit team verified the supporting documents and reconciliation entries.",
                responded_by_type='Staff',
                responded_by_user=cl_by.user,
                responded_on=timezone.now() - timedelta(days=45 - q_idx*2),
                is_client_submission=False,
                sequence_no=2
            )

        # Exception on E1
        ExceptionApproval.objects.create(
            reference_no='EX-202505-0001',
            engagement=e1,
            query=Query.objects.get(query_no=f"{e1.engagement_code}/0005"),
            exception_type='EX-01',
            requested_by=staff_map['EMP003'],
            requested_on=timezone.now() - timedelta(days=45),
            justification="The slow moving inventory of ₹ 32 Lakhs was verified as fully consumed in special production run batch #PR-901 in May 2025 before final signing. Valuation impact is immaterial on FY25 statements.",
            approved_by=staff_map['EMP001'],
            approved_on=timezone.now() - timedelta(days=44),
            decision='Approved',
            partner_remarks="Reviewed batch consumption records and physical output. Approved closure under exception.",
            is_self_approved=False
        )

        # Eng 2 (Apex FY2526)
        q_e2_defs = [
            (
                'Observation', 'Revenue', 'Repeat Observation: Revenue Recognition Without Delivery Challan in Q2',
                'Sample testing of Q2 exports showed billing of ₹ 24 Lakhs before Bill of Lading generation.',
                'Bill of Lading and shipping bills.', Decimal('2400000.00'), 'High', 'Critical',
                staff_map['EMP005'], contact_map['cfo@apexindustries.com'],
                'Invoices booked on factory gate exit rather than FOB vessel boarding date.',
                'Ind AS 115 - Incoterms FOB criteria.',
                'ERP allowed manual bypass of export milestone tracking.',
                'Overstatement of export revenue in interim period.',
                'Lock invoice generation until custom shipping bill and BL are uploaded.',
                'Responded', None, '', True, prior_year_q_ref,
                today - timedelta(days=5)
            ),
            (
                'Information Request', 'Payroll', 'Actuarial Valuation Report for Gratuity and Leave Encashment',
                'Full actuarial valuation report for employee benefit obligations as on 30th September 2025.',
                'Actuary certificate and employee demographic data.', Decimal('14500000.00'), 'Medium', 'Medium',
                staff_map['EMP005'], contact_map['kavita.nair@apexindustries.com'],
                '', '', '', '', '',
                'Issued', None, '', False, None,
                today - timedelta(days=2) # Overdue by 2 days
            ),
            (
                'Control Deficiency', 'ITGC', 'Privileged User Access Reviews in SAP Not Performed Quarterly',
                'Superuser (SAP_ALL) access assigned to 4 contract developers without quarterly access reviews.',
                'SAP User authorization logs and access review sign-off sheets.', None, 'High', 'High',
                staff_map['EMP005'], contact_map['cfo@apexindustries.com'],
                'Excessive administrative privileges granted in production ERP.',
                'ICAI Guidance Note on Internal Financial Controls (ITGC domain).',
                'Absence of formal identity and access management (IAM) workflow.',
                'Risk of unauthorized configuration or master data alterations.',
                'Revoke SAP_ALL profiles and enforce least privilege role-based access.',
                'Closed', staff_map['EMP003'], 'Privileges revoked for 4 contractors on 12th Aug; restricted roles assigned.',
                False, None,
                today + timedelta(days=10)
            ),
            (
                'Observation', 'Purchases', 'Non-Deduction of TDS under Section 194Q on High-Value Purchases',
                'TDS not withheld on purchase of scrap metal exceeding ₹ 50 Lakhs threshold from M/s Metal Trade.',
                'Purchase invoices and Form 26AS of seller.', Decimal('6800000.00'), 'High', 'Medium',
                staff_map['EMP007'], contact_map['kavita.nair@apexindustries.com'],
                'Section 194Q compliance missing in buyer automated TDS matrix.',
                'Income Tax Act Section 194Q / 206C(1H).',
                'ERP tax code mapping error on scrap inventory category.',
                'Disallowance of 30% of expenditure under Section 40(a)(ia).',
                'Correct tax rate configuration in SAP for purchase threshold above ₹ 50L.',
                'Draft', None, '', False, None,
                today + timedelta(days=15)
            )
        ]

        for q_idx, (qtype, area, title, desc, doc_req, amt, prio, risk, r_by, c_contact, cond, crit, cause, eff, rec, stat, cl_by, cl_rem, is_rep, p_ref, d_date) in enumerate(q_e2_defs, start=1):
            q_no = f"{e2.engagement_code}/{q_idx:04d}" if stat != 'Draft' else None
            q_obj = Query.objects.create(
                query_no=q_no,
                serial_no=q_idx if q_no else None,
                engagement=e2,
                query_type=qtype,
                area=area,
                title=title,
                description=desc,
                document_requested=doc_req,
                amount_involved=amt,
                priority=prio,
                risk_rating=risk,
                raised_by=r_by,
                raised_on=timezone.now() - timedelta(days=25 - q_idx*3),
                issued_on=(timezone.now() - timedelta(days=22 - q_idx*3)) if stat != 'Draft' else None,
                due_date=d_date,
                assigned_to_client_contact=c_contact,
                condition=cond,
                criteria=crit,
                cause=cause,
                effect_risk=eff,
                recommendation=rec,
                status=stat,
                closed_by=cl_by,
                closed_on=(timezone.now() - timedelta(days=5)) if cl_by else None,
                closure_remarks=cl_rem,
                is_repeat_observation=is_rep,
                prior_year_query_ref=p_ref,
                created_by=r_by.user
            )

            if stat == 'Responded':
                QueryResponse.objects.create(
                    query=q_obj,
                    response_text="We have obtained the Bill of Lading dated 14-Oct from the shipping line. Customs clearance was completed on 12-Oct. Reconciliation statement attached.",
                    responded_by_type='Client',
                    responded_by_user=c_contact.user,
                    responded_on=timezone.now() - timedelta(days=3),
                    is_client_submission=True,
                    sequence_no=1
                )

        # Eng 3 Queries (Horizon Healthcare)
        q_e3_defs = [
            (
                'Observation', 'Inventory', 'Discrepancy in High-Cost Oncology Drugs Physical Stock',
                'Physical verification in main hospital pharmacy revealed variance of ₹ 4.2 Lakhs in oncology vials.',
                'Batch registers and CCTV logs.', Decimal('420000.00'), 'High', 'Critical',
                staff_map['EMP006'], contact_map['finance.head@horizonhealth.com'],
                'Physical stock less than ERP book stock by 14 vials of Trastuzumab.',
                'Hospital SOP on high-value drug dispensing & reconciliation.',
                'Dispensing without real-time barcode scanning in HIS (Hospital Information System).',
                'Financial loss and potential pilferage exposure.',
                'Install biometric lock on oncology refrigerator and mandate barcode scan before dispatch.',
                'Pending Client Review', None, '', today + timedelta(days=7)
            ),
            (
                'Observation', 'Revenue', 'Discounts Given Beyond Authorized Thresholds in Billing',
                'Patient billing analysis indicated discounts exceeding 15% approved by junior billing executives.',
                'Billing discount authorization logs.', Decimal('780000.00'), 'Medium', 'Medium',
                staff_map['EMP008'], contact_map['accounts@horizonhealth.com'],
                'Bypassing of billing delegation of authority (DOA).',
                'Hospital Corporate Governance DOA Policy.',
                'Billing software allowed overriding discount without OTP validation.',
                'Revenue leakage across inpatient billing.',
                'Enforce strict system block on discounts above 10% without Medical Director approval.',
                'Pending Internal Review', None, '', today + timedelta(days=12)
            ),
            (
                'Information Request', 'Payroll', 'Doctors Retainership Agreement and TDS 194J Compliance',
                'Sample contracts for top 20 consultant doctors and monthly invoice vouchers.',
                'Agreements, monthly TDS computation sheets.', Decimal('8500000.00'), 'Medium', 'Medium',
                staff_map['EMP006'], contact_map['finance.head@horizonhealth.com'],
                '', '', '', '', '',
                'Issued', None, '', today - timedelta(days=1)
            )
        ]

        for q_idx, (qtype, area, title, desc, doc_req, amt, prio, risk, r_by, c_contact, cond, crit, cause, eff, rec, stat, cl_by, cl_rem, d_date) in enumerate(q_e3_defs, start=1):
            q_no = f"{e3.engagement_code}/{q_idx:04d}" if stat not in ['Draft', 'Pending Internal Review'] else None
            q_obj = Query.objects.create(
                query_no=q_no,
                serial_no=q_idx if q_no else None,
                engagement=e3,
                query_type=qtype,
                area=area,
                title=title,
                description=desc,
                document_requested=doc_req,
                amount_involved=amt,
                priority=prio,
                risk_rating=risk,
                raised_by=r_by,
                raised_on=timezone.now() - timedelta(days=10 - q_idx*2),
                issued_on=(timezone.now() - timedelta(days=8 - q_idx*2)) if q_no else None,
                due_date=d_date,
                assigned_to_client_contact=c_contact,
                condition=cond,
                criteria=crit,
                cause=cause,
                effect_risk=eff,
                recommendation=rec,
                status=stat,
                closed_by=cl_by,
                closure_remarks=cl_rem,
                created_by=r_by.user
            )
            if stat == 'Pending Client Review':
                QueryResponse.objects.create(
                    query=q_obj,
                    response_text="Pharmacy staff submitted preliminary explanation that 10 vials were returned to oncology ward emergency cart. Awaiting final coordinator sign-off.",
                    responded_by_type='Client',
                    responded_by_user=contact_map['accounts@horizonhealth.com'].user,
                    responded_on=timezone.now() - timedelta(days=1),
                    is_client_submission=True,
                    is_approved_by_coordinator=False,
                    sequence_no=1
                )

        # Eng 4 Queries (Zenith Finserve IFC)
        q_e4_defs = [
            (
                'Control Deficiency', 'Treasury & Banking', 'Bank Account Reconciliation Pending Over 60 Days',
                'Three current bank accounts with Axis Bank showed unreconciled debit entries older than 60 days.',
                'BRS statements and bank confirmation certificates.', Decimal('1420000.00'), 'High', 'Critical',
                staff_map['EMP005'], contact_map['compliance@zenithfin.com'],
                'Unreconciled bank float items carried over month-ends.',
                'RBI NBFC Master Directions & Internal Treasury Manual.',
                'Lack of auto-matching tool for high volume RTGS settlements.',
                'Potential risk of unrecorded bank charges or fraudulent debit entries.',
                'Mandate daily automated bank statement ingestion and weekly review by Head of Treasury.',
                'Info Awaited', None, '', today + timedelta(days=5)
            ),
            (
                'Control Deficiency', 'Related Parties', 'Related Party Loan Sanctions Without Audit Committee Prior Approval',
                'Inter-corporate deposit of ₹ 5 Crores given to group entity without omnibus approval.',
                'Board minutes and Section 188 compliance checklist.', Decimal('50000000.00'), 'High', 'Critical',
                staff_map['EMP005'], contact_map['compliance@zenithfin.com'],
                'Non-compliance with Companies Act Section 177 / 188 prior approval mandate.',
                'Companies Act 2013 - Section 177 & 188.',
                'Urgent liquidity support extended on executive approval prior to quarterly meeting.',
                'Regulatory non-compliance and penalty under Section 188(5).',
                'Implement hard stop in treasury disbursement system for any related entity without approved resolution ref.',
                'Issued', None, '', today - timedelta(days=4)
            )
        ]

        for q_idx, (qtype, area, title, desc, doc_req, amt, prio, risk, r_by, c_contact, cond, crit, cause, eff, rec, stat, cl_by, cl_rem, d_date) in enumerate(q_e4_defs, start=1):
            q_no = f"{e4.engagement_code}/{q_idx:04d}"
            q_obj = Query.objects.create(
                query_no=q_no,
                serial_no=q_idx,
                engagement=e4,
                query_type=qtype,
                area=area,
                title=title,
                description=desc,
                document_requested=doc_req,
                amount_involved=amt,
                priority=prio,
                risk_rating=risk,
                raised_by=r_by,
                raised_on=timezone.now() - timedelta(days=20),
                issued_on=timezone.now() - timedelta(days=18),
                due_date=d_date,
                assigned_to_client_contact=c_contact,
                condition=cond,
                criteria=crit,
                cause=cause,
                effect_risk=eff,
                recommendation=rec,
                status=stat,
                created_by=r_by.user
            )

        self.stdout.write(self.style.SUCCESS("Demo database successfully seeded!"))
        self.stdout.write(self.style.SUCCESS("Summary:"))
        self.stdout.write(f"  - Admin: admin@firm.com (Pass: Admin@123)")
        self.stdout.write(f"  - Partners: partner1@firm.com, partner2@firm.com (Pass: Partner@123)")
        self.stdout.write(f"  - Managers: manager1@firm.com, manager2@firm.com (Pass: Manager@123)")
        self.stdout.write(f"  - Seniors: senior1@firm.com, senior2@firm.com (Pass: Senior@123)")
        self.stdout.write(f"  - Articles: article1@firm.com, article2@firm.com (Pass: Article@123)")
        self.stdout.write(f"  - Clients: cfo@apexindustries.com, finance.head@horizonhealth.com, compliance@zenithfin.com (Pass: Client@123)")
        self.stdout.write(f"  - Engagements: 4 engagements across 5 clients, with Apex FY2425 ready for memo generation and Apex FY2526 demonstrating gate blocking.")
