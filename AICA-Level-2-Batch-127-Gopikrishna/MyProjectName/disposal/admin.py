from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import DisposalRequest


@admin.register(DisposalRequest)
class DisposalRequestAdmin(SimpleHistoryAdmin):
    list_display = (
        "asset", "mode", "status", "sale_or_scrap_value", "profit_or_loss",
        "is_material_section_180", "requested_by", "approved_by",
    )
    list_filter = ("mode", "status", "is_material_section_180", "is_related_party")
    search_fields = ("asset__asset_id",)
