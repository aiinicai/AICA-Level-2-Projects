from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone

kra_pin_validator=RegexValidator(regex=r'^[A-Z][0-9]{9}[A-Z]$',message='Expected Kenyan KRA PIN format: letter + 9 digits + letter.')

class Company(models.Model):
    code=models.CharField(max_length=12,unique=True)
    name=models.CharField(max_length=200)
    kra_pin=models.CharField(max_length=11,unique=True,validators=[kra_pin_validator])
    active=models.BooleanField(default=True)
    def __str__(self): return f'{self.code} — {self.name}'

class VendorProfile(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='vendor_profile')
    legal_name=models.CharField(max_length=200)
    kra_pin=models.CharField(max_length=11,validators=[kra_pin_validator])
    approved=models.BooleanField(default=False)
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='vendor_approvals')
    approved_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.legal_name

class Invoice(models.Model):
    class Status(models.TextChoices):
        REVIEW='REVIEW','Pending finance review'
        APPROVED='APPROVED','Approved'
        REJECTED='REJECTED','Rejected'
        EXPORTED='EXPORTED','Exported'
    reference=models.CharField(max_length=48,unique=True)
    vendor=models.ForeignKey(VendorProfile,on_delete=models.PROTECT,related_name='invoices')
    company=models.ForeignKey(Company,on_delete=models.PROTECT)
    invoice_number=models.CharField(max_length=100,blank=True)
    invoice_date=models.DateField(null=True,blank=True)
    currency=models.CharField(max_length=3,blank=True)
    net_amount=models.DecimalField(max_digits=17,decimal_places=2,null=True,blank=True)
    vat_amount=models.DecimalField(max_digits=17,decimal_places=2,null=True,blank=True)
    total_amount=models.DecimalField(max_digits=17,decimal_places=2,null=True,blank=True)
    po_number=models.CharField(max_length=100,blank=True)
    extracted_text=models.TextField(blank=True)
    extraction_notes=models.TextField(blank=True)
    vendor_notes=models.TextField(blank=True)
    finance_notes=models.TextField(blank=True)
    status=models.CharField(max_length=10,choices=Status.choices,default=Status.REVIEW)
    uploaded_at=models.DateTimeField(default=timezone.now)
    approved_at=models.DateTimeField(null=True,blank=True)
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,blank=True,on_delete=models.SET_NULL,related_name='approved_invoices')
    export_batch=models.ForeignKey('ExportBatch',null=True,blank=True,on_delete=models.SET_NULL)
    def __str__(self):return self.reference

class Document(models.Model):
    class Kind(models.TextChoices):
        INVOICE='INVOICE','Invoice'
        PO='PO','Purchase order'
        SUPPORT='SUPPORT','Supporting document'
    invoice=models.ForeignKey(Invoice,on_delete=models.CASCADE,related_name='documents')
    kind=models.CharField(max_length=10,choices=Kind.choices)
    original_name=models.CharField(max_length=255)
    stored_name=models.CharField(max_length=100)
    byte_size=models.PositiveIntegerField()
    sha256=models.CharField(max_length=64)
    created_at=models.DateTimeField(auto_now_add=True)

class ExportBatch(models.Model):
    created_at=models.DateTimeField(default=timezone.now)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    filename=models.CharField(max_length=150)
    count=models.PositiveIntegerField(default=0)

class AuditEvent(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.SET_NULL)
    action=models.CharField(max_length=60)
    subject=models.CharField(max_length=120)
    details=models.TextField(blank=True)
    created_at=models.DateTimeField(default=timezone.now)
    class Meta: ordering=['-created_at']
