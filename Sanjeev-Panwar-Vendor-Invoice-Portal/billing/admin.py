from django.contrib import admin
from .models import Company,VendorProfile,Invoice,Document,ExportBatch,AuditEvent
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display=('code','name','kra_pin','active')
    search_fields=('code','name','kra_pin')
@admin.register(VendorProfile)
class VendorAdmin(admin.ModelAdmin):
    list_display=('legal_name','kra_pin','approved','user')
    list_filter=('approved',)
    search_fields=('legal_name','kra_pin','user__email')
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display=('reference','vendor','company','invoice_number','currency','total_amount','status','uploaded_at')
    list_filter=('status','company')
    search_fields=('reference','invoice_number')
for model in (Document,ExportBatch,AuditEvent):admin.site.register(model)
