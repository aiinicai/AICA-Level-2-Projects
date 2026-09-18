import os
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.core.exceptions import ValidationError


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'ADMIN')
        extra_fields.setdefault('must_change_password', False)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = [
        ('ADMIN', 'System Administrator'),
        ('STAFF', 'Audit Staff'),
        ('CLIENT', 'Client User'),
    ]

    email = models.EmailField('Email Address', unique=True, max_length=255)
    full_name = models.CharField('Full Name', max_length=150)
    user_type = models.CharField('User Type', max_length=10, choices=USER_TYPE_CHOICES, default='STAFF')
    
    must_change_password = models.BooleanField('Force Password Change', default=True)
    failed_login_attempts = models.PositiveIntegerField('Failed Login Attempts', default=0)
    is_locked = models.BooleanField('Account Locked', default=False)
    locked_at = models.DateTimeField('Locked At', null=True, blank=True)

    is_active = models.BooleanField('Active', default=True)
    is_staff = models.BooleanField('Staff Status', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['email']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.is_locked = False
        self.locked_at = None
        self.save(update_fields=['failed_login_attempts', 'is_locked', 'locked_at'])

    def record_failed_attempt(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.is_locked = True
            self.locked_at = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'is_locked', 'locked_at'])


class Client(models.Model):
    CONSTITUTION_CHOICES = [
        ('Pvt Ltd', 'Private Limited Company'),
        ('Public Ltd', 'Public Limited Company'),
        ('LLP', 'Limited Liability Partnership'),
        ('Firm', 'Partnership Firm'),
        ('Trust', 'Trust / Society'),
        ('Other', 'Other Entity'),
    ]

    INDUSTRY_CHOICES = [
        ('Manufacturing', 'Manufacturing'),
        ('Financial Services', 'Financial Services & Banking'),
        ('Retail', 'Retail & FMCG'),
        ('Healthcare', 'Healthcare & Pharmaceuticals'),
        ('Information Technology', 'Information Technology & SaaS'),
        ('Real Estate', 'Real Estate & Infrastructure'),
        ('Energy', 'Energy & Utilities'),
        ('Other', 'Other Industry'),
    ]

    RISK_CATEGORY_CHOICES = [
        ('High', 'High Risk'),
        ('Medium', 'Medium Risk'),
        ('Low', 'Low Risk'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    client_code = models.CharField('Client Code', max_length=20, unique=True, help_text="e.g. CL001")
    client_name = models.CharField('Client Name', max_length=200)
    group_name = models.CharField('Group / Conglomerate Name', max_length=200, blank=True)
    constitution = models.CharField('Constitution', max_length=30, choices=CONSTITUTION_CHOICES, default='Pvt Ltd')
    industry = models.CharField('Industry Sector', max_length=50, choices=INDUSTRY_CHOICES, default='Manufacturing')
    registered_address = models.TextField('Registered Address')
    city = models.CharField('City', max_length=100)
    state = models.CharField('State', max_length=100)
    financial_year_end = models.CharField('Financial Year End', max_length=50, default='31st March')
    listed_status = models.BooleanField('Is Listed Entity', default=False)
    risk_category = models.CharField('Risk Category', max_length=10, choices=RISK_CATEGORY_CHOICES, default='Medium')
    client_since = models.DateField('Client Since')
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='Active')
    remarks = models.TextField('Remarks', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_clients')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_clients')

    class Meta:
        ordering = ['client_code']

    def __str__(self):
        return f"{self.client_code} - {self.client_name}"


class ClientContact(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contacts')
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_contact')
    contact_name = models.CharField('Contact Person Name', max_length=150)
    designation = models.CharField('Designation', max_length=100)
    email = models.EmailField('Email', unique=True)
    mobile = models.CharField('Mobile Number', max_length=20)
    is_primary_coordinator = models.BooleanField('Is Primary Coordinator', default=False)
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='Active')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_contacts')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_contacts')

    class Meta:
        ordering = ['client', '-is_primary_coordinator', 'contact_name']

    def __str__(self):
        return f"{self.contact_name} ({self.designation}) - {self.client.client_name}"


class Staff(models.Model):
    DESIGNATION_CHOICES = [
        ('Partner', 'Audit Partner'),
        ('Manager', 'Audit Manager'),
        ('Senior', 'Audit Senior'),
        ('Article Assistant', 'Article Assistant'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    staff_code = models.CharField('Staff Code', max_length=20, unique=True, help_text="e.g. EMP001")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_profile')
    full_name = models.CharField('Full Name', max_length=150)
    email = models.EmailField('Official Email', unique=True)
    designation = models.CharField('Designation', max_length=20, choices=DESIGNATION_CHOICES)
    membership_no = models.CharField('ICAI Membership No.', max_length=30, blank=True, null=True)
    date_of_joining = models.DateField('Date of Joining')
    reporting_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='Active')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_staff')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_staff')

    class Meta:
        ordering = ['designation', 'staff_code']
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff Members'

    def __str__(self):
        return f"{self.staff_code} - {self.full_name} ({self.designation})"


class Engagement(models.Model):
    AUDIT_TYPE_CHOICES = [
        ('Statutory Audit', 'Statutory Audit'),
        ('Internal Audit', 'Internal Audit'),
        ('IFC Testing', 'IFC Testing (Internal Financial Controls)'),
        ('Tax Audit', 'Tax Audit'),
        ('Limited Review', 'Limited Review'),
        ('Other', 'Other Special Audit'),
    ]

    AUDIT_TYPE_CODE_MAP = {
        'Statutory Audit': 'SA',
        'Internal Audit': 'IA',
        'IFC Testing': 'IFC',
        'Tax Audit': 'TA',
        'Limited Review': 'LR',
        'Other': 'OTH',
    }

    STATUS_CHOICES = [
        ('Planned', 'Planned'),
        ('In Progress', 'In Progress'),
        ('Queries Closed', 'Queries Closed'),
        ('Memo Issued', 'Memo Issued'),
        ('Archived', 'Archived'),
    ]

    engagement_code = models.CharField('Engagement Code', max_length=50, unique=True, help_text="e.g. CL001/FY2526/SA")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='engagements')
    financial_year = models.CharField('Financial Year', max_length=20, help_text="e.g. 2024-25 or 2025-26")
    audit_type = models.CharField('Audit Type', max_length=30, choices=AUDIT_TYPE_CHOICES)
    period_from = models.DateField('Audit Period From')
    period_to = models.DateField('Audit Period To')
    planned_start = models.DateField('Planned Start Date')
    target_completion = models.DateField('Target Completion Date')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='Planned')
    client_coordinator_review_enabled = models.BooleanField(
        'Client Coordinator Review Enabled',
        default=False,
        help_text="If enabled, client responses require client coordinator approval before reaching audit team."
    )
    memo_generated_on = models.DateTimeField('Memo Generated On', null=True, blank=True)
    memo_signed_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='signed_engagements')
    memo_version = models.CharField('Memo Version', max_length=10, default='v1.0')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_engagements')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_engagements')

    class Meta:
        unique_together = ('client', 'financial_year', 'audit_type')
        ordering = ['-financial_year', 'engagement_code']

    def __str__(self):
        return f"{self.engagement_code} - {self.client.client_name}"

    @classmethod
    def generate_code(cls, client_code, financial_year, audit_type):
        fy_clean = financial_year.replace('20', '').replace('-', '')
        fy_formatted = f"FY{fy_clean}"
        type_code = cls.AUDIT_TYPE_CODE_MAP.get(audit_type, 'AUD')
        return f"{client_code}/{fy_formatted}/{type_code}"

    def clean(self):
        if not self.engagement_code:
            self.engagement_code = self.generate_code(self.client.client_code, self.financial_year, self.audit_type)

    def get_lead_partner(self):
        lead = self.team_members.filter(role_on_engagement='Partner', is_reviewer=False, is_active=True).first()
        return lead.staff if lead else None

    def get_reviewer_partner(self):
        reviewer = self.team_members.filter(role_on_engagement='Partner', is_reviewer=True, is_active=True).first()
        return reviewer.staff if reviewer else None


class EngagementTeam(models.Model):
    ROLE_CHOICES = [
        ('Partner', 'Audit Partner'),
        ('Manager', 'Audit Manager'),
        ('Senior', 'Audit Senior'),
        ('Article Assistant', 'Article Assistant'),
    ]

    engagement = models.ForeignKey(Engagement, on_delete=models.CASCADE, related_name='team_members')
    staff = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name='engagement_assignments')
    role_on_engagement = models.CharField('Role on Engagement', max_length=20, choices=ROLE_CHOICES)
    is_reviewer = models.BooleanField('EQCR / Reviewer Only', default=False, help_text="Read-only partner review slot")
    assigned_on = models.DateField('Assigned On', default=timezone.now)
    released_on = models.DateField('Released On', null=True, blank=True)
    is_active = models.BooleanField('Is Active', default=True)

    independence_declared = models.BooleanField('Independence & Conflict of Interest Declared', default=False)
    independence_declared_on = models.DateTimeField('Independence Declared On', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_assignments')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_assignments')

    class Meta:
        ordering = ['engagement', 'role_on_engagement', 'staff__full_name']

    def __str__(self):
        return f"{self.staff.full_name} as {self.role_on_engagement} on {self.engagement.engagement_code}"

    def clean(self):
        if self.staff and self.staff.designation == 'Article Assistant' and self.role_on_engagement in ['Partner', 'Manager']:
            raise ValidationError(f"Staff member {self.staff.full_name} is an Article Assistant and cannot be assigned as a {self.role_on_engagement}.")


class Query(models.Model):
    QUERY_TYPE_CHOICES = [
        ('Information Request', 'Information Request / PBC'),
        ('Observation', 'Audit Observation'),
        ('Control Deficiency', 'Internal Control Deficiency'),
    ]

    AREA_CHOICES = [
        ('Revenue', 'Revenue & Receivables'),
        ('Purchases', 'Purchases & Payables'),
        ('Payroll', 'Payroll & Employee Benefits'),
        ('Fixed Assets', 'Property, Plant & Equipment / Fixed Assets'),
        ('Inventory', 'Inventory & Valuation'),
        ('Statutory Dues', 'Statutory Dues & Compliance (GST, TDS, PF)'),
        ('Related Parties', 'Related Party Transactions'),
        ('ITGC', 'IT General Controls & Cyber Security'),
        ('Treasury & Banking', 'Treasury, Cash & Bank Operations'),
        ('Financial Reporting', 'Financial Statements & Disclosures'),
        ('Other', 'Other Audit Area'),
    ]

    PRIORITY_CHOICES = [
        ('High', 'High Priority'),
        ('Medium', 'Medium Priority'),
        ('Low', 'Low Priority'),
    ]

    RISK_RATING_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]

    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Pending Internal Review', 'Pending Internal Review'),
        ('Issued', 'Issued to Client'),
        ('Pending Client Review', 'Pending Client Coordinator Review'),
        ('Responded', 'Responded by Client'),
        ('Info Awaited', 'Info Awaited (Re-issued)'),
        ('Closed', 'Closed'),
        ('Closed - Exception Approved', 'Closed – Exception Approved'),
        ('Withdrawn', 'Withdrawn'),
    ]

    query_no = models.CharField('Query Number', max_length=60, unique=True, null=True, blank=True, help_text="Auto-generated on issue, e.g. CL001/FY2526/SA/0001")
    serial_no = models.PositiveIntegerField('Serial Number', null=True, blank=True)
    engagement = models.ForeignKey(Engagement, on_delete=models.CASCADE, related_name='queries')
    query_type = models.CharField('Query Type', max_length=25, choices=QUERY_TYPE_CHOICES, default='Observation')
    area = models.CharField('Audit Area', max_length=40, choices=AREA_CHOICES)
    title = models.CharField('Title / Subject', max_length=255)
    description = models.TextField('Description')
    document_requested = models.TextField('Documents / Information Requested', blank=True)
    amount_involved = models.DecimalField('Amount Involved (₹)', max_digits=15, decimal_places=2, null=True, blank=True)
    priority = models.CharField('Priority', max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    risk_rating = models.CharField('Risk Rating', max_length=10, choices=RISK_RATING_CHOICES, default='Medium')

    # Structured 5-element fields
    condition = models.TextField('Condition (What was found)', blank=True)
    criteria = models.TextField('Criteria (What should be / Accounting standard)', blank=True)
    cause = models.TextField('Cause (Why it occurred / Root cause)', blank=True)
    effect_risk = models.TextField('Effect / Risk (Financial impact or exposure)', blank=True)
    recommendation = models.TextField('Recommendation (Corrective action)', blank=True)

    raised_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name='raised_queries')
    raised_on = models.DateTimeField('Raised On', default=timezone.now)
    issued_on = models.DateTimeField('Issued On', null=True, blank=True)
    due_date = models.DateField('Due Date')
    assigned_to_client_contact = models.ForeignKey(ClientContact, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_queries')

    status = models.CharField('Status', max_length=30, choices=STATUS_CHOICES, default='Draft')
    closed_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='closed_queries')
    closed_on = models.DateTimeField('Closed On', null=True, blank=True)
    closure_remarks = models.TextField('Closure Remarks', blank=True)

    is_repeat_observation = models.BooleanField('Is Repeat Observation', default=False)
    prior_year_query_ref = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subsequent_repeats')
    carry_to_memo = models.BooleanField('Carry to Summary Memo', default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_queries')
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_queries')

    class Meta:
        ordering = ['-raised_on']
        verbose_name = 'Query / Observation'
        verbose_name_plural = 'Queries & Observations'

    def __str__(self):
        return f"{self.query_no or 'Draft'} - {self.title}"

    @property
    def is_terminal(self):
        return self.status in ['Closed', 'Closed - Exception Approved', 'Withdrawn']

    @property
    def is_structured(self):
        return self.query_type in ['Observation', 'Control Deficiency']

    @property
    def is_overdue(self):
        if not self.is_terminal and self.due_date:
            return timezone.localdate() > self.due_date
        return False

    @property
    def days_open(self):
        start_date = self.issued_on.date() if self.issued_on else self.raised_on.date()
        end_date = self.closed_on.date() if self.closed_on else timezone.localdate()
        return (end_date - start_date).days

    @property
    def ageing_bucket(self):
        days = self.days_open
        if days <= 7:
            return '0-7 days'
        elif days <= 15:
            return '8-15 days'
        elif days <= 30:
            return '16-30 days'
        else:
            return '>30 days'

    def generate_next_query_no(self):
        last_query = Query.objects.filter(engagement=self.engagement, serial_no__isnull=False).order_by('-serial_no').first()
        next_serial = (last_query.serial_no + 1) if last_query and last_query.serial_no else 1
        self.serial_no = next_serial
        self.query_no = f"{self.engagement.engagement_code}/{next_serial:04d}"
        return self.query_no


class QueryResponse(models.Model):
    RESPONDED_BY_CHOICES = [
        ('Staff', 'Audit Staff'),
        ('Client', 'Client User'),
    ]

    query = models.ForeignKey(Query, on_delete=models.CASCADE, related_name='responses')
    response_text = models.TextField('Response Text')
    responded_by_type = models.CharField('Responded By Type', max_length=10, choices=RESPONDED_BY_CHOICES)
    responded_by_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='query_responses')
    responded_on = models.DateTimeField('Responded On', default=timezone.now)
    is_client_submission = models.BooleanField('Is Client Submission', default=False)
    is_approved_by_coordinator = models.BooleanField('Approved by Client Coordinator', default=True)
    sequence_no = models.PositiveIntegerField('Sequence No', default=1)
    status_at_response = models.CharField('Query Status At Response', max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sequence_no', 'responded_on']

    def __str__(self):
        return f"Response #{self.sequence_no} on {self.query.query_no or 'Draft'}"


def attachment_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join('attachments', f"eng_{instance.query.engagement_id}", unique_name)


class Attachment(models.Model):
    query = models.ForeignKey(Query, on_delete=models.CASCADE, related_name='attachments')
    response = models.ForeignKey(QueryResponse, on_delete=models.SET_NULL, null=True, blank=True, related_name='attachments')
    file = models.FileField('File', upload_to=attachment_upload_path)
    file_name = models.CharField('Original File Name', max_length=255)
    file_type = models.CharField('MIME / File Type', max_length=100)
    file_size = models.PositiveIntegerField('File Size (Bytes)')
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='uploaded_attachments')
    uploaded_on = models.DateTimeField('Uploaded On', default=timezone.now)
    is_active = models.BooleanField('Is Active', default=True)

    class Meta:
        ordering = ['-uploaded_on']

    def __str__(self):
        return self.file_name


class ExceptionApproval(models.Model):
    EXCEPTION_TYPE_CHOICES = [
        ('EX-01', 'EX-01: Close query without a satisfactory client response'),
        ('EX-02', 'EX-02: Withdraw an issued query'),
        ('EX-03', 'EX-03: Generate the summary memo while queries remain open'),
        ('EX-04', 'EX-04: Reopen a closed query'),
        ('EX-05', 'EX-05: Reopen an engagement after memo issuance'),
        ('EX-06', 'EX-06: Extend due date beyond standard threshold'),
        ('EX-07', 'EX-07: Activate an engagement with an incomplete team'),
    ]

    DECISION_CHOICES = [
        ('Pending', 'Pending Partner Review'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    reference_no = models.CharField('Reference Number', max_length=40, unique=True)
    query = models.ForeignKey(Query, on_delete=models.SET_NULL, null=True, blank=True, related_name='exceptions')
    engagement = models.ForeignKey(Engagement, on_delete=models.CASCADE, related_name='exceptions')
    exception_type = models.CharField('Exception Type', max_length=10, choices=EXCEPTION_TYPE_CHOICES)
    requested_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name='requested_exceptions')
    requested_on = models.DateTimeField('Requested On', default=timezone.now)
    justification = models.TextField('Justification (Min 100 chars)')

    approved_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='decided_exceptions')
    approved_on = models.DateTimeField('Decided On', null=True, blank=True)
    decision = models.CharField('Decision', max_length=15, choices=DECISION_CHOICES, default='Pending')
    partner_remarks = models.TextField('Partner Remarks / Instructions', blank=True)
    is_self_approved = models.BooleanField('Self-Approved by Sole Partner Flag', default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_on']

    def __str__(self):
        return f"{self.reference_no} - {self.exception_type} ({self.decision})"

    @classmethod
    def generate_reference_no(cls):
        now = timezone.now()
        prefix = f"EX-{now.strftime('%Y%m')}"
        last_item = cls.objects.filter(reference_no__startswith=prefix).order_by('-reference_no').first()
        if last_item:
            try:
                last_seq = int(last_item.reference_no.split('-')[-1])
                seq = last_seq + 1
            except Exception:
                seq = 1
        else:
            seq = 1
        return f"{prefix}-{seq:04d}"


class AuditTrail(models.Model):
    ACTION_CHOICES = [
        ('Create', 'Create'),
        ('Update', 'Update'),
        ('Status Change', 'Status Change'),
        ('Issue', 'Issue to Client'),
        ('Close', 'Close Query'),
        ('Exception Request', 'Exception Requested'),
        ('Exception Approve', 'Exception Approved'),
        ('Exception Reject', 'Exception Rejected'),
        ('Login', 'User Login'),
        ('Logout', 'User Logout'),
        ('Failed Login', 'Failed Login Attempt'),
        ('Lockout', 'Account Locked'),
        ('Unlock', 'Account Unlocked'),
        ('Password Change', 'Password Changed'),
        ('Memo Generate', 'Memo Generated'),
        ('Memo Sign-off', 'Memo Signed Off'),
        ('Team Change', 'Team Assignment Modified'),
    ]

    entity_type = models.CharField('Entity Type', max_length=50)
    entity_id = models.CharField('Entity ID / Key', max_length=100)
    action = models.CharField('Action', max_length=30, choices=ACTION_CHOICES)
    field_changed = models.CharField('Field Changed', max_length=100, blank=True)
    old_value = models.TextField('Old Value', blank=True)
    new_value = models.TextField('New Value', blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_records')
    performed_by_name = models.CharField('Performed By Name', max_length=150, blank=True)
    performed_on = models.DateTimeField('Performed On', default=timezone.now)
    ip_address = models.CharField('IP Address', max_length=50, blank=True)

    class Meta:
        ordering = ['-performed_on']
        verbose_name = 'Audit Trail Log'
        verbose_name_plural = 'Audit Trail Logs'

    def __str__(self):
        return f"[{self.performed_on.strftime('%d-%b-%Y %H:%M')}] {self.action} on {self.entity_type} {self.entity_id} by {self.performed_by_name}"


class Memo(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft (Watermarked)'),
        ('Signed', 'Final Signed Off'),
    ]

    engagement = models.ForeignKey(Engagement, on_delete=models.CASCADE, related_name='memos')
    version_no = models.CharField('Version No', max_length=15, default='v1.0')
    generated_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name='generated_memos')
    generated_on = models.DateTimeField('Generated On', default=timezone.now)
    file_path = models.CharField('Stored File Path', max_length=300)
    status = models.CharField('Status', max_length=15, choices=STATUS_CHOICES, default='Draft')
    signed_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='signed_memos')
    signed_on = models.DateTimeField('Signed On', null=True, blank=True)
    open_query_count_at_generation = models.PositiveIntegerField('Open Queries at Generation', default=0)
    exception_count = models.PositiveIntegerField('Exceptions Count', default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_on']

    def __str__(self):
        return f"Memo {self.version_no} ({self.status}) - {self.engagement.engagement_code}"


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField('Title', max_length=200)
    message = models.TextField('Message')
    link = models.CharField('Action Link', max_length=255, blank=True)
    is_read = models.BooleanField('Is Read', default=False)
    created_at = models.DateTimeField('Created At', default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification to {self.recipient.email}: {self.title}"
