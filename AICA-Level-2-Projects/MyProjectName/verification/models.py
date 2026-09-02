from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

from assets.models import Asset
from locations.models import Location

User = settings.AUTH_USER_MODEL


class ScanEvent(models.Model):
    """
    One QR/barcode scan against the register. The blueprint is explicit
    that "the same code is scanned for physical verification, transfer,
    maintenance logging, and disposal" — one event log, differentiated by
    `purpose`, rather than a separate table per workflow.
    """

    class Purpose(models.TextChoices):
        TAG_CONFIRM = "TAG_CONFIRM", "Tag affix & confirm"
        VERIFICATION = "VERIFICATION", "Physical verification"
        TRANSFER = "TRANSFER", "Transfer"
        MAINTENANCE = "MAINTENANCE", "Maintenance log"
        DISPOSAL_CHECK = "DISPOSAL_CHECK", "Disposal check"
        GENERAL = "GENERAL", "General lookup"

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="scan_events")
    purpose = models.CharField(max_length=16, choices=Purpose.choices)
    scanned_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="scan_events")
    scanned_at = models.DateTimeField(auto_now_add=True)

    device_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    device_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    confirmed_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="scan_events", null=True, blank=True,
        help_text="Hierarchy node the scanning user confirmed.",
    )
    location_mismatch = models.BooleanField(
        default=False,
        help_text="True if confirmed_location differs from the asset's last registered node at scan time.",
    )
    mismatch_resolved = models.BooleanField(default=False)
    mismatch_resolution_notes = models.TextField(blank=True)

    condition_notes = models.CharField(max_length=255, blank=True)
    tag_was_disposed = models.BooleanField(
        default=False, help_text="Raised when a disposed asset's tag is scanned — an exception, not a success."
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["-scanned_at"]

    def __str__(self):
        return f"{self.get_purpose_display()} scan — {self.asset.asset_id} — {self.scanned_at:%Y-%m-%d %H:%M}"


class VerificationCycle(models.Model):
    """
    A rotational physical-verification programme — "full coverage at least
    once every 3 years, rotational" (CARO 3(i)(b) market practice).
    """

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        CLOSED = "CLOSED", "Closed"

    entity = models.ForeignKey("locations.Entity", on_delete=models.PROTECT, related_name="verification_cycles")
    name = models.CharField(max_length=150)
    scope_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, null=True, blank=True, related_name="verification_cycles",
        help_text="Leave blank to scope the whole entity.",
    )
    start_date = models.DateField()
    target_end_date = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="verification_cycles_created")

    history = HistoricalRecords()

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    def in_scope_assets(self):
        if self.scope_location_id:
            location_ids = self.scope_location.descendant_ids()
            return Asset.objects.filter(entity=self.entity, location_id__in=location_ids)
        return Asset.objects.filter(entity=self.entity)

    def coverage_pct(self):
        total = self.in_scope_assets().count()
        if not total:
            return 0
        done = PhysicalVerificationRecord.objects.filter(cycle=self).values("asset_id").distinct().count()
        return round(done / total * 100, 1)


class PhysicalVerificationRecord(models.Model):
    """CARO 3(i)(b) evidence — one asset checked once within a cycle."""

    class Condition(models.TextChoices):
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"
        DAMAGED = "DAMAGED", "Damaged"
        NOT_FOUND = "NOT_FOUND", "Not found"

    cycle = models.ForeignKey(VerificationCycle, on_delete=models.PROTECT, related_name="records")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="verification_records")
    scan_event = models.ForeignKey(ScanEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name="verification_record")
    verified_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="verifications_done")
    verified_date = models.DateField()
    condition = models.CharField(max_length=16, choices=Condition.choices)
    discrepancy_notes = models.TextField(blank=True)
    discrepancy_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-verified_date"]
        unique_together = [("cycle", "asset")]

    def __str__(self):
        return f"Verification — {self.asset.asset_id} — {self.verified_date}"


class MaintenanceLog(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="maintenance_logs")
    scan_event = models.ForeignKey(ScanEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_log")
    logged_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="maintenance_logs")
    logged_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    vendor_name = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-logged_at"]

    def __str__(self):
        return f"Maintenance — {self.asset.asset_id} — {self.logged_at:%Y-%m-%d}"
