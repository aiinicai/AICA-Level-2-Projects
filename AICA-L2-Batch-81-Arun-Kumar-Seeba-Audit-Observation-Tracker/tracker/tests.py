import os
import datetime
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from tracker.models import (
    User, Client, ClientContact, Staff, Engagement, EngagementTeam,
    Query, QueryResponse, ExceptionApproval, Memo, AuditTrail
)
from tracker.services.state_machine import transition_query
from tracker.services.permissions import (
    get_user_role_for_engagement, can_issue_query, can_close_query,
    can_request_exception, can_approve_exception, can_signoff_memo, can_generate_memo
)
from tracker.services.memo_generator import generate_docx_memo, check_memo_gate
from tracker.services.audit_service import log_audit


class AuditTrackerCoreTests(TestCase):
    """
    Comprehensive tests for the Audit Observation Tracker:
    - User creation & roles
    - State machine transitions & Maker-Checker rules
    - Exception approval workflow with step-up verification
    - Terminal-status Memo generation gate (FR-11)
    - Append-only Audit Trail (FR-14)
    """

    def setUp(self):
        # 1. Create Users
        self.partner_user = User.objects.create_user(
            email='partner@firm.test',
            password='Password@123',
            full_name='CA Anand Sharma',
            user_type='STAFF',
            must_change_password=False
        )
        self.manager_user = User.objects.create_user(
            email='manager@firm.test',
            password='Password@123',
            full_name='CA Priya Nair',
            user_type='STAFF',
            must_change_password=False
        )
        self.senior_user = User.objects.create_user(
            email='senior@firm.test',
            password='Password@123',
            full_name='Rahul Verma',
            user_type='STAFF',
            must_change_password=False
        )
        self.article_user = User.objects.create_user(
            email='article@firm.test',
            password='Password@123',
            full_name='Kavita Iyer',
            user_type='STAFF',
            must_change_password=False
        )
        self.client_user = User.objects.create_user(
            email='cfo@apex.test',
            password='Password@123',
            full_name='Ramesh Gupta',
            user_type='CLIENT',
            must_change_password=False
        )

        # 2. Staff Records
        self.staff_partner = Staff.objects.create(
            user=self.partner_user,
            staff_code='STF001',
            full_name='CA Anand Sharma',
            email='partner@firm.test',
            designation='Partner',
            date_of_joining=datetime.date(2020, 1, 1),
            membership_no='123456',
            status='Active'
        )
        self.staff_manager = Staff.objects.create(
            user=self.manager_user,
            staff_code='STF002',
            full_name='CA Priya Nair',
            email='manager@firm.test',
            designation='Manager',
            date_of_joining=datetime.date(2021, 6, 1),
            membership_no='234567',
            status='Active'
        )
        self.staff_senior = Staff.objects.create(
            user=self.senior_user,
            staff_code='STF003',
            full_name='Rahul Verma',
            email='senior@firm.test',
            designation='Senior',
            date_of_joining=datetime.date(2023, 2, 1),
            membership_no='345678',
            status='Active'
        )
        self.staff_article = Staff.objects.create(
            user=self.article_user,
            staff_code='STF004',
            full_name='Kavita Iyer',
            email='article@firm.test',
            designation='Article Assistant',
            date_of_joining=datetime.date(2024, 4, 1),
            status='Active'
        )

        # 3. Client & Contact
        self.client_obj = Client.objects.create(
            client_code='CL001',
            client_name='Apex Enterprises Ltd',
            constitution='Public Ltd',
            industry='Manufacturing',
            registered_address='Plot 42, MIDC, Andheri East, Mumbai',
            city='Mumbai',
            state='Maharashtra',
            client_since=datetime.date(2020, 1, 1),
            status='Active'
        )
        self.contact = ClientContact.objects.create(
            client=self.client_obj,
            user=self.client_user,
            contact_name='Ramesh Gupta',
            designation='Chief Financial Officer',
            email='cfo@apex.test',
            mobile='9876543214',
            is_primary_coordinator=True,
            status='Active'
        )

        # 4. Engagement
        self.engagement = Engagement.objects.create(
            engagement_code='CL001/FY2526/SA',
            client=self.client_obj,
            financial_year='2025-26',
            audit_type='Statutory Audit',
            period_from=datetime.date(2025, 4, 1),
            period_to=datetime.date(2026, 3, 31),
            planned_start=datetime.date(2026, 4, 15),
            target_completion=datetime.date(2026, 6, 30),
            status='In Progress'
        )

        # 5. Team Assignment
        EngagementTeam.objects.create(
            engagement=self.engagement,
            staff=self.staff_partner,
            role_on_engagement='Partner'
        )
        EngagementTeam.objects.create(
            engagement=self.engagement,
            staff=self.staff_manager,
            role_on_engagement='Manager'
        )
        EngagementTeam.objects.create(
            engagement=self.engagement,
            staff=self.staff_senior,
            role_on_engagement='Senior'
        )
        EngagementTeam.objects.create(
            engagement=self.engagement,
            staff=self.staff_article,
            role_on_engagement='Article Assistant'
        )

    def test_engagement_role_resolution(self):
        """Verify role resolution on engagement."""
        self.assertEqual(get_user_role_for_engagement(self.partner_user, self.engagement), 'Partner')
        self.assertEqual(get_user_role_for_engagement(self.manager_user, self.engagement), 'Manager')
        self.assertEqual(get_user_role_for_engagement(self.senior_user, self.engagement), 'Senior')
        self.assertEqual(get_user_role_for_engagement(self.article_user, self.engagement), 'Article Assistant')
        self.assertEqual(get_user_role_for_engagement(self.client_user, self.engagement), 'Client Coordinator')

    def test_query_creation_and_maker_checker_rule(self):
        """
        Verify Maker-Checker Rule (BR-02):
        1. Article creates Draft query.
        2. Article CANNOT submit directly for issuance without review, or issue it directly.
        3. Manager can review and issue.
        """
        query = Query.objects.create(
            engagement=self.engagement,
            query_type='Observation',
            title='Inadequate Revenue Cutoff Controls',
            description='Invoices dated March 31 recorded in April.',
            area='Revenue',
            due_date=timezone.localdate() + datetime.timedelta(days=7),
            risk_rating='High',
            status='Draft',
            raised_by=self.staff_article,
            condition='Invoices dated March 31 recorded in April.',
            criteria='Ind AS 115 Revenue Recognition.',
            cause='Lack of automated cutoff checks.',
            effect_risk='Revenue understated by INR 15,00,000.',
            recommendation='Implement ERP automated sales invoice cutoff lock.'
        )

        # Article cannot issue
        can_issue = can_issue_query(self.article_user, query)
        self.assertFalse(can_issue)

        # Article submits for review
        transition_query(query, 'Pending Internal Review', self.article_user)
        query.refresh_from_db()
        self.assertEqual(query.status, 'Pending Internal Review')

        # Maker-checker: Article who raised it cannot issue it
        self.assertFalse(can_issue_query(self.article_user, query))

        # Manager can issue
        can_issue = can_issue_query(self.manager_user, query)
        self.assertTrue(can_issue)

        # Manager issues the query to client
        transition_query(query, 'Issued', self.manager_user)
        query.refresh_from_db()
        self.assertEqual(query.status, 'Issued')
        self.assertIsNotNone(query.issued_on)
        self.assertIsNotNone(query.query_no)

    def test_query_lifecycle_to_closure(self):
        """
        Full lifecycle: Draft -> Pending Review -> Issued -> Client Responded -> Closed
        """
        query = Query.objects.create(
            engagement=self.engagement,
            query_type='Information Request',
            title='Bank Confirmation from State Bank of India',
            description='Direct bank confirmation statement for year end.',
            area='Treasury & Banking',
            due_date=timezone.localdate() + datetime.timedelta(days=5),
            risk_rating='Medium',
            status='Draft',
            raised_by=self.staff_senior
        )

        # Submit & Issue
        transition_query(query, 'Pending Internal Review', self.senior_user)
        transition_query(query, 'Issued', self.manager_user)
        query.refresh_from_db()
        self.assertEqual(query.status, 'Issued')

        # Client submits response
        QueryResponse.objects.create(
            query=query,
            response_text='Direct bank confirmation statement attached and verified.',
            responded_by_type='Client',
            responded_by_user=self.client_user,
            is_client_submission=True,
            status_at_response='Responded'
        )
        transition_query(query, 'Responded', self.client_user, remarks='Response submitted by CFO')
        query.refresh_from_db()
        self.assertEqual(query.status, 'Responded')
        self.assertEqual(query.responses.count(), 1)

        # Manager closes query
        can_close = can_close_query(self.manager_user, query)
        self.assertTrue(can_close)

        transition_query(
            query, 'Closed', self.manager_user,
            remarks='Received direct confirmation from SBI and reconciled.'
        )
        query.refresh_from_db()
        self.assertEqual(query.status, 'Closed')
        self.assertTrue(query.is_terminal)

    def test_memo_generation_gate_blocks_open_queries(self):
        """
        FR-11 Gate: Word Memo generation MUST fail if there is any non-terminal query
        without an approved Partner exception.
        """
        Query.objects.create(
            engagement=self.engagement,
            query_type='Observation',
            title='Fixed Asset Register Mismatch',
            description='Differences between FAR and general ledger.',
            area='Fixed Assets',
            due_date=timezone.localdate() + datetime.timedelta(days=7),
            risk_rating='Critical',
            status='Issued',
            raised_by=self.staff_senior
        )

        # Check gate
        is_allowed, open_queries, has_ex03 = check_memo_gate(self.engagement)
        self.assertFalse(is_allowed)
        self.assertEqual(len(open_queries), 1)

        # Attempt to generate memo -> Must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            generate_docx_memo(self.engagement, self.staff_partner)
        
        self.assertIn('Cannot generate memo', str(ctx.exception))

    def test_exception_approval_unblocks_memo_gate(self):
        """
        EX-03: When an open query has an approved EX-03 exception,
        it unblocks Memo generation.
        """
        query = Query.objects.create(
            engagement=self.engagement,
            query_type='Information Request',
            title='Pending Foreign Vendor Confirmation',
            description='Confirmation from overseas vendor.',
            area='Purchases',
            due_date=timezone.localdate() + datetime.timedelta(days=7),
            risk_rating='Low',
            status='Issued',
            raised_by=self.staff_senior
        )

        # Manager requests EX-03 exception
        can_req = can_request_exception(self.manager_user, self.engagement)
        self.assertTrue(can_req)

        exception_obj = ExceptionApproval.objects.create(
            reference_no=ExceptionApproval.generate_reference_no(),
            engagement=self.engagement,
            query=query,
            requested_by=self.staff_manager,
            exception_type='EX-03',
            justification='Alternative audit procedures performed via subsequent bank payments verification.' * 2,
            decision='Pending'
        )

        # Partner approves exception
        can_appr = can_approve_exception(self.partner_user, exception_obj)
        self.assertTrue(can_appr)

        exception_obj.decision = 'Approved'
        exception_obj.approved_by = self.staff_partner
        exception_obj.approved_on = timezone.now()
        exception_obj.partner_remarks = 'Approved based on verified subsequent disbursements.'
        exception_obj.save()

        # Gate check should now pass via EX-03 override
        is_allowed, open_queries, has_ex03 = check_memo_gate(self.engagement)
        self.assertTrue(is_allowed)
        self.assertTrue(has_ex03)

        # Memo generation should now succeed
        memo_record, file_path = generate_docx_memo(self.engagement, self.staff_partner, is_draft=True)
        self.assertIsNotNone(memo_record)
        self.assertEqual(memo_record.status, 'Draft')
        self.assertTrue(os.path.exists(file_path))

    def test_memo_partner_signoff_permissions(self):
        """
        FR-12: Partner signs off memo -> Memo permissions check.
        """
        can_partner_sign = can_signoff_memo(self.partner_user, self.engagement)
        self.assertTrue(can_partner_sign)

        can_manager_sign = can_signoff_memo(self.manager_user, self.engagement)
        self.assertFalse(can_manager_sign)

    def test_audit_trail_immutability(self):
        """
        FR-14: AuditTrail records logging.
        """
        log_audit(
            entity_type='Query',
            entity_id='1',
            action='Status Change',
            user=self.partner_user,
            field_changed='status',
            old_value='Draft',
            new_value='Pending Internal Review'
        )
        self.assertEqual(AuditTrail.objects.filter(entity_type='Query').count(), 1)
        log_entry = AuditTrail.objects.filter(entity_type='Query').first()
        self.assertIsNotNone(log_entry.id)
        self.assertEqual(log_entry.performed_by.email, 'partner@firm.test')
