from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from simple_history.models import HistoricalRecords

from assets.models import Asset
from locations.models import Location

User = settings.AUTH_USER_MODEL


class TransferRequest(models.Model):
    """
    Inter-location / inter-department transfer with custodian sign-off —
    "keeping the situation field current" (blueprint §05). Every completed
    transfer also writes a row to Asset's movement trail via the linked
    scan event, not an overwrite of the asset's location field alone.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending sign-off"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="transfers")
    from_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="transfers_out")
    to_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="transfers_in")
    from_custodian = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="transfers_handed_over")
    to_custodian = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="transfers_received")
    from_department = models.CharField(max_length=128, blank=True)
    to_department = models.CharField(max_length=128, blank=True)
    reason = models.CharField(max_length=255, blank=True)

    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="transfers_requested")
    requested_at = models.DateTimeField(auto_now_add=True)
    signed_off_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="transfers_signed_off")
    signed_off_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)

    scan_event = models.ForeignKey(
        "verification.ScanEvent", on_delete=models.SET_NULL, null=True, blank=True, related_name="transfer_request"
    )
    triggered_by_mismatch = models.BooleanField(
        default=False, help_text="True if this transfer was nudged into existence by a location-mismatch scan."
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Transfer {self.asset.asset_id}: {self.from_location} → {self.to_location}"
