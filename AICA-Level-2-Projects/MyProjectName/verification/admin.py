from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import MaintenanceLog, PhysicalVerificationRecord, ScanEvent, VerificationCycle


@admin.register(ScanEvent)
class ScanEventAdmin(SimpleHistoryAdmin):
    list_display = ("asset", "purpose", "scanned_by", "scanned_at", "location_mismatch", "tag_was_disposed")
    list_filter = ("purpose", "location_mismatch", "tag_was_disposed")
    search_fields = ("asset__asset_id",)


@admin.register(VerificationCycle)
class VerificationCycleAdmin(SimpleHistoryAdmin):
    list_display = ("name", "entity", "scope_location", "start_date", "target_end_date", "status")
    list_filter = ("entity", "status")


@admin.register(PhysicalVerificationRecord)
class PhysicalVerificationRecordAdmin(SimpleHistoryAdmin):
    list_display = ("asset", "cycle", "verified_by", "verified_date", "condition", "discrepancy_resolved")
    list_filter = ("condition", "discrepancy_resolved")
    search_fields = ("asset__asset_id",)


@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ("asset", "logged_by", "logged_at", "cost", "vendor_name")
    search_fields = ("asset__asset_id",)
