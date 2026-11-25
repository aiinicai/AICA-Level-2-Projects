from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    ApprovalRequest,
    Asset,
    AssetClass,
    BookDepreciationEntry,
    CapexRequisition,
    CWIP,
    DepreciationRun,
    Document,
    ImpairmentCheck,
    RevaluationRecord,
    TaxDepreciationEntry,
    Vendor,
)


@admin.register(AssetClass)
class AssetClassAdmin(SimpleHistoryAdmin):
    list_display = ("name", "useful_life_years", "default_method", "is_intangible", "residual_value_pct")
    search_fields = ("name",)


@admin.register(Vendor)
class VendorAdmin(SimpleHistoryAdmin):
    list_display = ("name", "gstin", "is_related_party")
    search_fields = ("name", "gstin")
    list_filter = ("is_related_party",)


@admin.register(CapexRequisition)
class CapexRequisitionAdmin(SimpleHistoryAdmin):
    list_display = ("title", "entity", "estimated_cost", "status", "requires_board_approval", "requested_by")
    list_filter = ("status", "entity", "requires_board_approval")
    search_fields = ("title",)


class DocumentInline(GenericTabularInline):
    model = Document
    extra = 0


@admin.register(CWIP)
class CWIPAdmin(SimpleHistoryAdmin):
    list_display = ("reference", "description", "entity", "vendor", "status", "total_cost")
    list_filter = ("status", "entity")
    search_fields = ("reference", "description", "po_number", "invoice_number")
    inlines = [DocumentInline]


@admin.register(Asset)
class AssetAdmin(SimpleHistoryAdmin):
    list_display = (
        "asset_id", "description", "asset_class", "entity", "location",
        "life_status", "tag_status", "custodian", "capitalised_cost", "net_book_value",
    )
    list_filter = ("entity", "asset_class", "life_status", "tag_status", "ownership_status")
    search_fields = ("asset_id", "description", "serial_number")
    autocomplete_fields = ("location", "vendor", "parent_asset", "cwip_source")
    readonly_fields = ("asset_id", "qr_uid", "created_at", "updated_at")
    inlines = [DocumentInline]

    def net_book_value(self, obj):
        return obj.net_book_value()


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ("action", "status", "requested_by", "requested_at", "decided_by", "decided_at")
    list_filter = ("action", "status")


@admin.register(DepreciationRun)
class DepreciationRunAdmin(admin.ModelAdmin):
    list_display = ("book", "entity", "period_start", "period_end", "run_by", "run_at", "is_posted")
    list_filter = ("book", "entity")


@admin.register(BookDepreciationEntry)
class BookDepreciationEntryAdmin(admin.ModelAdmin):
    list_display = ("asset", "run", "opening_wdv", "depreciation_amount", "closing_wdv")
    search_fields = ("asset__asset_id",)


@admin.register(TaxDepreciationEntry)
class TaxDepreciationEntryAdmin(admin.ModelAdmin):
    list_display = ("asset", "run", "opening_wdv", "depreciation_amount", "closing_wdv", "is_half_rate")
    search_fields = ("asset__asset_id",)


@admin.register(RevaluationRecord)
class RevaluationRecordAdmin(SimpleHistoryAdmin):
    list_display = ("asset", "valuation_date", "fair_value", "surplus_or_deficit", "exceeds_10pct_threshold")
    inlines = [DocumentInline]


@admin.register(ImpairmentCheck)
class ImpairmentCheckAdmin(SimpleHistoryAdmin):
    list_display = ("asset", "check_date", "indicators_present", "impairment_loss")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("doc_type", "content_type", "object_id", "uploaded_by", "uploaded_at")
    list_filter = ("doc_type",)
