from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import TransferRequest


@admin.register(TransferRequest)
class TransferRequestAdmin(SimpleHistoryAdmin):
    list_display = ("asset", "from_location", "to_location", "status", "requested_by", "signed_off_by")
    list_filter = ("status",)
    search_fields = ("asset__asset_id",)
