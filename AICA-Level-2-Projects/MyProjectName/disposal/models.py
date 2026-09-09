from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from simple_history.models import HistoricalRecords

from assets.models import Asset

User = settings.AUTH_USER_MODEL


class DisposalRequest(models.Model):
    """
    Stage 6 — dispose, scrap or sell (blueprint §02). Approval-matrix
    driven; computes profit/loss on sale; flags Section 180 board approval
    when the disposal could constitute selling a substantial part of an
    undertaking (extra weight for a listed company, blueprint §08). The
    underlying Asset record is never deleted — see `apply()`.
    """

    class Mode(models.TextChoices):
        SALE = "SALE", "Sale"
        SCRAP = "SCRAP", "Scrap"
        WRITE_OFF = "WRITE_OFF", "Write-off (no proceeds)"
        DAMAGE = "DAMAGE", "Damaged / destroyed"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
        APPROVED = "APPROVED", "Approved & posted"
        REJECTED = "REJECTED", "Rejected"

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="disposal_requests")
    mode = models.CharField(max_length=12, choices=Mode.choices)
    reason = models.TextField(blank=True)
    requested_disposal_date = models.DateField()

    net_book_value_at_request = models.DecimalField(max_digits=16, decimal_places=2)
    sale_or_scrap_value = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    disposal_costs = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    profit_or_loss = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))

    is_material_section_180 = models.BooleanField(
        default=False,
        help_text="Could this disposal constitute selling a substantial part of an undertaking? Needs shareholder approval.",
    )
    section_180_threshold_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        help_text="Disposal value as % of total net PP&E at the time of request, for the Section 180 test.",
    )
    board_resolution_reference = models.CharField(max_length=120, blank=True)
    buyer_or_scrap_vendor = models.CharField(max_length=255, blank=True)
    is_related_party = models.BooleanField(default=False, help_text="Section 188 related-party disclosure flag.")

    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="disposals_requested")
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="disposals_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    documents = GenericRelation("assets.Document")
    approval_requests = GenericRelation("assets.ApprovalRequest")
    history = HistoricalRecords()

    class Meta:
        ordering = ["-requested_at"]

    def compute_profit_loss(self):
        self.profit_or_loss = (self.sale_or_scrap_value - self.disposal_costs) - self.net_book_value_at_request
        return self.profit_or_loss

    def __str__(self):
        return f"Disposal — {self.asset.asset_id} ({self.get_mode_display()})"
