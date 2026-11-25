import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from locations.models import Entity, Location

User = settings.AUTH_USER_MODEL


# ==========================================================================
# Reference data — Schedule II asset-class master (blueprint §04)
# ==========================================================================

class AssetClass(models.Model):
    """
    Schedule II asset-class master. Seeded from the blueprint's reference
    table (management command `seed_reference_data`) so depreciation
    calculates correctly out of the box; editable later if the company's
    accounting policy justifies a different life.
    """

    class Method(models.TextChoices):
        SLM = "SLM", "Straight Line Method"
        WDV = "WDV", "Written Down Value"

    name = models.CharField(max_length=150, unique=True)
    useful_life_years = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Schedule II useful life in years. Leave blank for 'per Ind AS 38' intangibles.",
    )
    default_method = models.CharField(max_length=8, choices=Method.choices, default=Method.SLM)
    is_intangible = models.BooleanField(default=False)
    residual_value_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("5.00"),
        help_text="Residual value as % of original cost. Schedule II caps this at 5% unless justified.",
    )
    notes = models.CharField(max_length=255, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Asset classes"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Vendor(models.Model):
    name = models.CharField(max_length=255)
    gstin = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    is_related_party = models.BooleanField(
        default=False,
        help_text="Section 188 related-party flag — auto-flags asset transactions with this vendor for disclosure.",
    )

    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ==========================================================================
# Capex requisition -> CWIP -> Capitalisation (blueprint §02, stages 1-3)
# ==========================================================================

class CapexRequisition(models.Model):
    """Stage 1 — Section 179 capex approval before a PO is released."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending board/committee approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    entity = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="capex_requisitions")
    title = models.CharField(max_length=255)
    justification = models.TextField(blank=True)
    estimated_cost = models.DecimalField(max_digits=16, decimal_places=2)
    delegated_authority_threshold = models.DecimalField(
        max_digits=16, decimal_places=2, default=Decimal("0"),
        help_text="Approval threshold in force at request time, for audit reference.",
    )
    requires_board_approval = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="capex_requested")
    approved_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="capex_approved"
    )
    board_resolution_reference = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if self.delegated_authority_threshold and self.estimated_cost > self.delegated_authority_threshold:
            self.requires_board_approval = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} (₹{self.estimated_cost:,.0f})"


class CWIP(models.Model):
    """
    Stage 2 — Capital work-in-progress. Goods receipt + invoice booked here;
    freight, duty, installation cost accumulate until the asset is ready
    for use (Ind AS 16.16).
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open — accumulating cost"
        READY = "READY", "Ready for capitalisation"
        CAPITALISED = "CAPITALISED", "Capitalised"
        CANCELLED = "CANCELLED", "Cancelled"

    entity = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="cwip_items")
    requisition = models.ForeignKey(
        CapexRequisition, on_delete=models.PROTECT, null=True, blank=True, related_name="cwip_items"
    )
    reference = models.CharField(max_length=64, unique=True, help_text="CWIP reference number.")
    description = models.CharField(max_length=255)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="cwip_items")
    po_number = models.CharField("PO number", max_length=64, blank=True)
    grn_number = models.CharField("GRN number", max_length=64, blank=True)
    invoice_number = models.CharField(max_length=64, blank=True)
    invoice_date = models.DateField(null=True, blank=True)

    base_cost = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    freight_cost = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    duty_cost = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    installation_cost = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    borrowing_cost = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    other_cost = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="cwip_created")
    created_at = models.DateTimeField(auto_now_add=True)

    documents = GenericRelation("assets.Document")
    history = HistoricalRecords()

    class Meta:
        verbose_name = "CWIP item"
        verbose_name_plural = "CWIP items"
        ordering = ["-created_at"]

    def total_cost(self):
        return (
            self.base_cost + self.freight_cost + self.duty_cost
            + self.installation_cost + self.borrowing_cost + self.other_cost
        )

    def __str__(self):
        return f"{self.reference} — {self.description}"


# ==========================================================================
# Asset master (blueprint §03) — Stage 3 onward
# ==========================================================================

def generate_asset_id():
    return f"AST-{uuid.uuid4().hex[:8].upper()}"


class Asset(models.Model):
    """
    The Asset Master. Created once at capitalisation; drives every future
    depreciation run, verification cycle, and disposal.
    """

    class OwnershipStatus(models.TextChoices):
        OWNED = "OWNED", "Owned"
        LEASED = "LEASED", "Leased"
        ROU = "ROU", "Right-of-use (Ind AS 116)"

    class LifeStatus(models.TextChoices):
        IN_USE = "IN_USE", "In use"
        IDLE = "IDLE", "Idle"
        UNDER_MAINTENANCE = "UNDER_MAINTENANCE", "Under maintenance"
        HELD_FOR_DISPOSAL = "HELD_FOR_DISPOSAL", "Held for disposal"
        DISPOSED = "DISPOSED", "Disposed"

    class TagStatus(models.TextChoices):
        UNTAGGED = "UNTAGGED", "Untagged"
        TAGGED = "TAGGED", "Tagged"
        REISSUED = "REISSUED", "Reissued"
        DEACTIVATED = "DEACTIVATED", "Deactivated"

    # --- Identity & classification -----------------------------------
    asset_id = models.CharField(max_length=32, unique=True, default=generate_asset_id, editable=False)
    entity = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="assets")
    description = models.CharField(max_length=255)
    make_model = models.CharField("Make / model / spec", max_length=255, blank=True)
    asset_class = models.ForeignKey(AssetClass, on_delete=models.PROTECT, related_name="assets")
    serial_number = models.CharField("Serial / chassis number", max_length=128, blank=True)
    parent_asset = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="components",
        help_text="Set for a component/sub-assembly with a distinct useful life.",
    )

    # --- Acquisition & cost --------------------------------------------
    cwip_source = models.ForeignKey(
        CWIP, null=True, blank=True, on_delete=models.SET_NULL, related_name="capitalised_assets"
    )
    acquisition_date = models.DateField(help_text="Date of purchase.")
    put_to_use_date = models.DateField(help_text="Depreciation starts here.")
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="assets_supplied")
    po_reference = models.CharField(max_length=64, blank=True)
    grn_reference = models.CharField(max_length=64, blank=True)
    invoice_reference = models.CharField(max_length=64, blank=True)
    capitalised_cost = models.DecimalField(
        max_digits=16, decimal_places=2,
        help_text="Purchase price plus freight, duty, installation, borrowing cost.",
    )

    # --- Depreciation policy (books — Schedule II) ----------------------
    depreciation_method = models.CharField(max_length=8, choices=AssetClass.Method.choices)
    useful_life_years = models.DecimalField(max_digits=5, decimal_places=2)
    residual_value_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))

    # --- Tax block (Income Tax Act) -------------------------------------
    tax_block_code = models.CharField(max_length=16, blank=True, help_text="Income Tax Act block-of-assets code.")
    tax_wdv_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # --- Location & custody ----------------------------------------------
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="assets")
    department = models.CharField(max_length=128, blank=True)
    custodian = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="assets_in_custody", null=True, blank=True
    )
    ownership_status = models.CharField(max_length=8, choices=OwnershipStatus.choices, default=OwnershipStatus.OWNED)
    title_deed_in_company_name = models.BooleanField(
        null=True, blank=True,
        help_text="CARO 3(i)(c) — for immovable property, is the title deed held in the company's own name?",
    )
    title_deed_reference = models.CharField(max_length=128, blank=True)
    encumbrance_details = models.TextField(blank=True, help_text="Charges, liens, or hypothecation against the asset.")
    is_immovable_property = models.BooleanField(default=False)

    last_scan_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_scan_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_scan_at = models.DateTimeField(null=True, blank=True)

    # --- Revaluation & impairment (summary; detail in RevaluationRecord) --
    is_revalued = models.BooleanField(default=False)
    last_revaluation_date = models.DateField(null=True, blank=True)
    accumulated_revaluation_surplus = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    impairment_loss_to_date = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))

    # --- Insurance ---------------------------------------------------------
    insurance_policy_number = models.CharField(max_length=64, blank=True)
    insurer_name = models.CharField(max_length=128, blank=True)
    insurance_sum_insured = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    insurance_renewal_date = models.DateField(null=True, blank=True)
    amc_provider = models.CharField(max_length=128, blank=True)
    amc_renewal_date = models.DateField(null=True, blank=True)

    # --- Verification ---------------------------------------------------
    last_verified_date = models.DateField(null=True, blank=True)
    last_verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets_last_verified"
    )
    last_verification_condition = models.CharField(max_length=32, blank=True)

    # --- Status / QR -------------------------------------------------------
    life_status = models.CharField(max_length=24, choices=LifeStatus.choices, default=LifeStatus.IN_USE)
    tag_status = models.CharField(max_length=16, choices=TagStatus.choices, default=TagStatus.UNTAGGED)
    qr_uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    tagged_at = models.DateTimeField(null=True, blank=True)
    tagged_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets_tagged"
    )

    # --- Maker-checker (Asset master creation itself is a checked action) -
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="assets_created")
    approved_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="assets_approved"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    documents = GenericRelation("assets.Document")
    approval_requests = GenericRelation("assets.ApprovalRequest")
    history = HistoricalRecords()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.asset_id} — {self.description}"

    def get_absolute_url(self):
        return reverse("assets:detail", args=[self.asset_id])

    def gross_block(self):
        return self.capitalised_cost + self.accumulated_revaluation_surplus

    def residual_value(self):
        return (self.capitalised_cost * self.residual_value_pct / Decimal("100")).quantize(Decimal("0.01"))

    def accumulated_depreciation(self):
        total = self.book_depreciation_entries.aggregate(total=models.Sum("depreciation_amount"))["total"]
        return total or Decimal("0")

    def net_book_value(self):
        return self.gross_block() - self.accumulated_depreciation() - self.impairment_loss_to_date

    def tax_wdv(self):
        last = self.tax_depreciation_entries.order_by("-period_end").first()
        return last.closing_wdv if last else self.capitalised_cost

    def is_component(self):
        return self.parent_asset_id is not None

    def verification_due(self):
        from django.conf import settings as dj_settings
        from django.utils import timezone
        import datetime

        cycle_years = dj_settings.FAR_SETTINGS["VERIFICATION_CYCLE_YEARS"]
        if not self.last_verified_date:
            return True
        return self.last_verified_date <= (timezone.now().date() - datetime.timedelta(days=365 * cycle_years))


class Document(models.Model):
    """
    Generic attachment (PO, GRN, invoice, title deed, valuation report,
    insurance policy...) linkable to Asset, CWIP, RevaluationRecord, or
    DisposalRequest without a separate table per parent.
    """

    class DocType(models.TextChoices):
        PO = "PO", "Purchase order"
        GRN = "GRN", "Goods receipt note"
        INVOICE = "INVOICE", "Invoice"
        TITLE_DEED = "TITLE_DEED", "Title deed"
        VALUATION_REPORT = "VALUATION_REPORT", "Valuation report"
        INSURANCE_POLICY = "INSURANCE_POLICY", "Insurance policy"
        BOARD_RESOLUTION = "BOARD_RESOLUTION", "Board/committee resolution"
        OTHER = "OTHER", "Other"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    doc_type = models.CharField(max_length=20, choices=DocType.choices, default=DocType.OTHER)
    file = models.FileField(upload_to="documents/%Y/%m/")
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.file.name.split('/')[-1]}"


# ==========================================================================
# Maker-checker (blueprint §05, §06) — generic approval workflow
# ==========================================================================

class ApprovalRequest(models.Model):
    """
    Generic two-step maker-checker record. Any workflow that must post to
    the books (asset creation, disposal, revaluation...) creates one of
    these; the checker must be a different user than the maker, and the
    action only takes effect on APPROVED.
    """

    class Action(models.TextChoices):
        ASSET_CREATE = "ASSET_CREATE", "Create asset"
        ASSET_EDIT = "ASSET_EDIT", "Edit asset"
        CAPITALISATION = "CAPITALISATION", "Capitalise CWIP"
        DISPOSAL = "DISPOSAL", "Disposal / write-off / sale"
        TRANSFER = "TRANSFER", "Transfer"
        REVALUATION = "REVALUATION", "Revaluation"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending approval"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    action = models.CharField(max_length=20, choices=Action.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    payload_summary = models.TextField(blank=True, help_text="Human-readable summary of what's being approved.")

    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="approval_requests_made")
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="approval_requests_decided"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.get_action_display()} — {self.get_status_display()}"

    def can_be_decided_by(self, user):
        """Maker-checker rule: the approver cannot be the same person who made the request."""
        return user.id != self.requested_by_id


# ==========================================================================
# Depreciation — dual engine: Schedule II (books) & Income Tax Act (tax)
# (blueprint §01, §05 — "Dual depreciation engine")
# ==========================================================================

class DepreciationRun(models.Model):
    """
    A frozen, re-creatable snapshot of one period's depreciation run —
    "treat every depreciation run ... as a frozen, re-creatable snapshot
    for regulatory scrutiny years later" (blueprint §08). Individual
    BookDepreciationEntry / TaxDepreciationEntry rows point back to the run
    that produced them and are never edited after posting.
    """

    class Book(models.TextChoices):
        SCHEDULE_II = "SCHEDULE_II", "Schedule II (books)"
        INCOME_TAX = "INCOME_TAX", "Income Tax Act (tax block/WDV)"

    entity = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="depreciation_runs")
    book = models.CharField(max_length=16, choices=Book.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    run_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="depreciation_runs")
    run_at = models.DateTimeField(auto_now_add=True)
    is_posted = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-period_end"]
        unique_together = [("entity", "book", "period_start", "period_end")]

    def __str__(self):
        return f"{self.get_book_display()} run {self.period_start} → {self.period_end}"


class BookDepreciationEntry(models.Model):
    """One asset's Schedule II depreciation charge for one posted run."""

    run = models.ForeignKey(DepreciationRun, on_delete=models.PROTECT, related_name="book_entries")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="book_depreciation_entries")
    opening_wdv = models.DecimalField(max_digits=16, decimal_places=2)
    depreciable_amount = models.DecimalField(max_digits=16, decimal_places=2)
    depreciation_amount = models.DecimalField(max_digits=16, decimal_places=2)
    closing_wdv = models.DecimalField(max_digits=16, decimal_places=2)
    days_in_period = models.PositiveIntegerField()
    days_used = models.PositiveIntegerField(help_text="Proration for mid-year additions/deletions.")
    method = models.CharField(max_length=8, choices=AssetClass.Method.choices)

    class Meta:
        unique_together = [("run", "asset")]
        ordering = ["asset__asset_id"]

    def __str__(self):
        return f"{self.asset.asset_id} — ₹{self.depreciation_amount:,.2f} ({self.run})"


class TaxDepreciationEntry(models.Model):
    """One asset's Income Tax Act block/WDV depreciation charge for one posted run."""

    run = models.ForeignKey(DepreciationRun, on_delete=models.PROTECT, related_name="tax_entries")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="tax_depreciation_entries")
    tax_block_code = models.CharField(max_length=16, blank=True)
    opening_wdv = models.DecimalField(max_digits=16, decimal_places=2)
    additions = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    rate_pct = models.DecimalField(max_digits=5, decimal_places=2)
    is_half_rate = models.BooleanField(
        default=False, help_text="Asset held < 180 days in the year — half the normal WDV rate applies."
    )
    depreciation_amount = models.DecimalField(max_digits=16, decimal_places=2)
    closing_wdv = models.DecimalField(max_digits=16, decimal_places=2)
    period_end = models.DateField()

    class Meta:
        unique_together = [("run", "asset")]
        ordering = ["asset__asset_id"]

    def __str__(self):
        return f"{self.asset.asset_id} — ₹{self.depreciation_amount:,.2f} tax ({self.run})"


# ==========================================================================
# Revaluation & impairment (blueprint §01 CARO 3(i)(d), Ind AS 16 para 77 / 36)
# ==========================================================================

class RevaluationRecord(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="revaluations")
    valuer_name = models.CharField(max_length=255, help_text="Registered Valuer per Section 247.")
    valuer_registration_number = models.CharField(max_length=64)
    valuation_date = models.DateField()
    methodology = models.CharField(max_length=255)
    fair_value = models.DecimalField(max_digits=16, decimal_places=2)
    carrying_value_before = models.DecimalField(max_digits=16, decimal_places=2)
    surplus_or_deficit = models.DecimalField(max_digits=16, decimal_places=2)
    movement_pct = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="(fair value − carrying value) / carrying value × 100. Widened beyond a "
        "typical percentage range because a near-zero carrying value (e.g. an asset "
        "depreciated almost to nil) can produce a legitimately huge swing.",
    )
    exceeds_10pct_threshold = models.BooleanField(default=False)
    valuation_report = GenericRelation("assets.Document")

    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="revaluations_requested")
    approved_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="revaluations_approved"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    approval_requests = GenericRelation("assets.ApprovalRequest")
    history = HistoricalRecords()

    class Meta:
        ordering = ["-valuation_date"]

    def save(self, *args, **kwargs):
        threshold = Decimal("10.00")
        self.exceeds_10pct_threshold = abs(self.movement_pct) >= threshold
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Revaluation of {self.asset.asset_id} on {self.valuation_date}"


class ImpairmentCheck(models.Model):
    """Ind AS 36 impairment indicator checklist, run at each reporting date."""

    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="impairment_checks")
    check_date = models.DateField()
    indicators_present = models.BooleanField(default=False)
    indicator_notes = models.TextField(blank=True)
    recoverable_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    carrying_amount = models.DecimalField(max_digits=16, decimal_places=2)
    impairment_loss = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    checked_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="impairment_checks")

    history = HistoricalRecords()

    class Meta:
        ordering = ["-check_date"]

    def __str__(self):
        return f"Impairment check — {self.asset.asset_id} — {self.check_date}"
