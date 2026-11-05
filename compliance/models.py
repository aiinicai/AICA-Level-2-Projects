"""
LexSecure India Pro - Django ORM Models
15 Core Enterprise Legal & Regulatory Intelligence Models
"""

import hashlib
import json
from django.db import models
from django.utils import timezone

class Organization(models.Model):
    INDUSTRY_CHOICES = [
        ('TECH', 'Technology & IT Services'),
        ('MANUFACTURING', 'Manufacturing & Heavy Industry'),
        ('RETAIL', 'Retail & FMCG'),
        ('HEALTHCARE', 'Healthcare & Pharmaceuticals'),
        ('FINANCE', 'Banking & Financial Services'),
        ('GENERAL', 'Conglomerate & General Operating Entity'),
    ]
    name = models.CharField(max_length=255)
    pan_number = models.CharField(max_length=10)
    cin_number = models.CharField(max_length=21)
    industry_type = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, default='GENERAL')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Entity(models.Model):
    ENTITY_CHOICES = [
        ('PVT_LTD', 'Private Limited Company'),
        ('PUBLIC_LTD', 'Public Limited Company'),
        ('LLP', 'Limited Liability Partnership'),
        ('PARTNERSHIP', 'Partnership Firm'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='entities')
    legal_name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=50, choices=ENTITY_CHOICES, default='PVT_LTD')
    registered_state = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.legal_name} ({self.registered_state})"


class Department(models.Model):
    DEPT_CHOICES = [
        ('LEGAL', 'Legal & Regulatory Compliance'),
        ('HR_LABOUR', 'Human Resources & Labour Law'),
        ('FINANCE_TAX', 'Finance, Treasury & Direct/Indirect Tax'),
        ('INFOSEC_TECH', 'Information Security & Data Protection'),
        ('OPERATIONS', 'Procurement & General Operations'),
    ]
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=50, choices=DEPT_CHOICES)

    def __str__(self):
        return f"{self.get_name_display()} - {self.entity.legal_name}"


class User(models.Model):
    ROLE_CHOICES = [
        ('GENERAL_COUNSEL', 'General Counsel / Legal Head'),
        ('COMPLIANCE_OFFICER', 'Chief Compliance Officer / Company Secretary'),
        ('DEPT_LEAD', 'Department Lead (HR/Finance/IT)'),
        ('AUDITOR', 'External Statutory / Regulatory Auditor'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='users')
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    pin = models.CharField(max_length=20, default='1234')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"


class AccessMatrixRule(models.Model):
    RESOURCE_CHOICES = [
        ('CONTRACT', 'Commercial Contracts & Agreements'),
        ('PLAYBOOK', 'Corporate Playbooks & Clauses'),
        ('REGULATORY', 'Regulatory Feeds & Impact Assessments'),
        ('TASKS', 'Department Compliance Tasks'),
        ('AUDIT', 'Cryptographic Audit Trail & Dossier'),
    ]
    role = models.CharField(max_length=50, choices=User.ROLE_CHOICES)
    resource = models.CharField(max_length=50, choices=RESOURCE_CHOICES)
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=True)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_signoff = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'resource')

    def __str__(self):
        return f"{self.role} -> {self.resource}"


class Playbook(models.Model):
    CONTRACT_TYPE_CHOICES = [
        ('MSA', 'Master Services Agreement'),
        ('NDA', 'Non-Disclosure Agreement'),
        ('VENDOR_PROCUREMENT', 'Vendor Supply & Procurement Agreement'),
        ('EMPLOYMENT_CONTRACT', 'Executive Employment Agreement'),
        ('CROSS_BORDER_FEMA', 'Cross-Border Technology & License Agreement'),
        ('DATA_PROCESSING_DPA', 'Data Processing Agreement (DPDP 2023)'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='playbooks')
    contract_type = models.CharField(max_length=50, choices=CONTRACT_TYPE_CHOICES)
    version = models.CharField(max_length=20, default='1.0')

    def __str__(self):
        return f"{self.get_contract_type_display()} (v{self.version})"


class PlaybookRule(models.Model):
    CLAUSE_TYPE_CHOICES = [
        ('LIABILITY_CAP', 'Limitation of Liability & Indemnity'),
        ('INDEMNITY', 'Asymmetrical Third-Party Indemnity'),
        ('NON_COMPETE_SEC27', 'Non-Compete Restraint (Section 27 Contract Act)'),
        ('FEMA_REMITTANCE', 'Foreign Currency Remittance & ECB Limits'),
        ('MSME_PAYMENT', 'MSME 15/45 Days Payment Term (Section 43B(h))'),
        ('DPDP_PRIVACY', 'Digital Personal Data Protection (DPDP Act 2023)'),
        ('GOVERNING_LAW', 'Indian Jurisdiction & Dispute Resolution'),
    ]
    playbook = models.ForeignKey(Playbook, on_delete=models.CASCADE, related_name='rules')
    clause_type = models.CharField(max_length=50, choices=CLAUSE_TYPE_CHOICES)
    standard_clause = models.TextField()
    fallback_clause = models.TextField()
    dealbreaker_conditions = models.TextField()
    statutory_citation_india = models.TextField()

    def __str__(self):
        return f"{self.get_clause_type_display()} - {self.playbook}"


class Document(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Intake'),
        ('ANALYZING', 'AI Parsing & Heuristic Review'),
        ('REVIEWED', 'Review Complete'),
        ('FLAGGED', 'Critical Statutory Flags Detected'),
    ]
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to='contracts/', null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=100)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    overall_health_score = models.IntegerField(default=100)
    liability_score = models.IntegerField(default=100)
    statutory_score = models.IntegerField(default=100)
    labour_fema_score = models.IntegerField(default=100)
    ocr_applied = models.BooleanField(default=False)
    raw_content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} (Score: {self.overall_health_score})"


class DocumentClause(models.Model):
    RISK_CHOICES = [
        ('HIGH', 'High Risk / Dealbreaker'),
        ('CAUTION', 'Caution / Deviation'),
        ('COMPLIANT', 'Compliant / Playbook Aligned'),
    ]
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='clauses')
    page_number = models.IntegerField(default=1)
    clause_type = models.CharField(max_length=50)
    raw_text = models.TextField()
    risk_tier = models.CharField(max_length=50, choices=RISK_CHOICES)
    flag_reason = models.TextField(null=True, blank=True)
    indian_law_violation = models.TextField(null=True, blank=True)
    suggested_redline = models.TextField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.clause_type} [{self.risk_tier}] - Doc #{self.document_id}"


class RegulatoryUpdate(models.Model):
    STATUTORY_BODY_CHOICES = [
        ('MCA', 'Ministry of Corporate Affairs'),
        ('RBI_FEMA', 'Reserve Bank of India (FEMA Division)'),
        ('LABOUR_MINISTRY', 'Ministry of Labour & Employment'),
        ('SEBI', 'Securities and Exchange Board of India'),
        ('DPDPB', 'Data Protection Board of India'),
        ('CERT_IN', 'Indian Computer Emergency Response Team'),
        ('GSTN', 'Goods and Services Tax Network'),
    ]
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical Statutory Change'),
        ('HIGH', 'High Compliance Impact'),
        ('ADVISORY', 'General Regulatory Advisory'),
    ]
    statutory_body = models.CharField(max_length=50, choices=STATUTORY_BODY_CHOICES)
    title = models.CharField(max_length=500)
    circular_number = models.CharField(max_length=150)
    official_date = models.DateField()
    raw_text = models.TextField()
    severity = models.CharField(max_length=50, choices=SEVERITY_CHOICES, default='HIGH')
    source_url = models.URLField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.statutory_body}] {self.title[:60]}"


class ImpactAssessment(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Assessment Drafted'),
        ('APPROVED', 'Approved by General Counsel'),
        ('DISPATCHED', 'Dispatched to Department Heads'),
    ]
    regulatory_update = models.ForeignKey(RegulatoryUpdate, on_delete=models.CASCADE, related_name='impact_assessments')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='DRAFT')
    executive_summary = models.TextField()
    affected_departments = models.CharField(max_length=255)
    statutory_deadline = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Impact Assessment #{self.id} for Circular #{self.regulatory_update_id}"


class ComplianceTask(models.Model):
    PRIORITY_CHOICES = [
        ('CRITICAL', 'Critical Immediate Action'),
        ('HIGH', 'High Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('LOW', 'Low Advisory'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending Assignment'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Compliance Achieved'),
        ('OVERDUE', 'Statutory Deadline Exceeded'),
    ]
    impact_assessment = models.ForeignKey(ImpactAssessment, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    deadline = models.DateField()
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='HIGH')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} [{self.status}]"


class TaskEvidence(models.Model):
    task = models.ForeignKey(ComplianceTask, on_delete=models.CASCADE, related_name='evidences')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    evidence_file = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence for Task #{self.task_id}"


class StatutoryCalendarEvent(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='calendar_events')
    statutory_body = models.CharField(max_length=100)
    compliance_name = models.CharField(max_length=255)
    due_date = models.DateField()
    recurring_freq = models.CharField(max_length=50)
    penalty_clause = models.TextField()

    def __str__(self):
        return f"{self.compliance_name} ({self.due_date})"


class TamperAuditLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_logs')
    actor_id = models.IntegerField(null=True, blank=True)
    actor_name = models.CharField(max_length=255, null=True, blank=True)
    event_type = models.CharField(max_length=100)
    target_model = models.CharField(max_length=100)
    target_id = models.IntegerField(null=True, blank=True)
    details_json = models.TextField()
    ip_address = models.GenericIPAddressField(default='127.0.0.1')
    timestamp = models.DateTimeField(default=timezone.now)
    prev_hash = models.CharField(max_length=64)
    current_hash = models.CharField(max_length=64)

    def save(self, *args, **kwargs):
        """
        Cryptographic SHA-256 Chained Event Logger.
        Ensures immutability by linking each log entry to the previous record's hash.
        """
        if not self.prev_hash:
            last_log = TamperAuditLog.objects.filter(organization=self.organization).order_by('-id').first()
            if last_log and last_log.current_hash:
                self.prev_hash = last_log.current_hash
            else:
                self.prev_hash = '0' * 64

        now_str = self.timestamp.isoformat() if self.timestamp else timezone.now().isoformat()
        raw_payload = f"{self.prev_hash}|{now_str}|{self.actor_id}|{self.actor_name}|{self.event_type}|{self.target_model}|{self.target_id}|{self.details_json}"
        self.current_hash = hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.timestamp}] {self.event_type} - Hash: {self.current_hash[:16]}..."
