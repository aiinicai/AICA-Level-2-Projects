from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class TimeEntry(models.Model):
    firm = models.ForeignKey("accounts.Firm", on_delete=models.CASCADE, related_name="time_entries")
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="time_entries")
    client = models.ForeignKey("crm.Client", on_delete=models.CASCADE, related_name="time_entries")
    task = models.ForeignKey("workflow.Task", null=True, blank=True, on_delete=models.SET_NULL, related_name="time_entries")
    work_date = models.DateField("Date")
    minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    description = models.TextField("What did you do?", blank=True)
    billable = models.BooleanField("Billable to the client", default=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # overrides the user's rate
    invoice = models.ForeignKey("Invoice", null=True, blank=True, on_delete=models.SET_NULL, related_name="time_entries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-work_date", "-created_at"]
        indexes = [models.Index(fields=["firm", "user", "work_date"]), models.Index(fields=["firm", "client"])]


class Invoice(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    firm = models.ForeignKey("accounts.Firm", on_delete=models.CASCADE, related_name="invoices")
    client = models.ForeignKey("crm.Client", on_delete=models.PROTECT, related_name="invoices")
    number = models.CharField(max_length=30)  # INV/2026-27/0001
    issue_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issue_date", "-id"]
        constraints = [models.UniqueConstraint(fields=["firm", "number"], name="unique_invoice_number_per_firm")]
        indexes = [models.Index(fields=["firm", "status"])]

    def __str__(self):
        return self.number

    @property
    def paid_amount(self) -> Decimal:
        return sum((p.amount for p in self.payments.all()), Decimal("0"))  # uses prefetch when available

    @property
    def balance(self) -> Decimal:
        return self.total - self.paid_amount

    @property
    def is_overdue(self) -> bool:
        return self.status == self.Status.PENDING and self.due_date < timezone.localdate()

    @property
    def status_key(self) -> str:
        return "OVERDUE" if self.is_overdue else self.status

    @property
    def status_label(self) -> str:
        return "Overdue" if self.is_overdue else self.get_status_display()


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=300)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField("GST %", max_digits=5, decimal_places=2, default=18)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # quantity × rate, before tax


class Payment(models.Model):
    firm = models.ForeignKey("accounts.Firm", on_delete=models.CASCADE, related_name="payments")
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_on = models.DateField()
    method = models.CharField(max_length=30, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["paid_on", "id"]


class InvoiceCounter(models.Model):
    """Gap-free invoice numbering per firm per financial year."""

    firm = models.ForeignKey("accounts.Firm", on_delete=models.CASCADE, related_name="invoice_counters")
    fy = models.CharField(max_length=9)
    seq = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["firm", "fy"], name="one_counter_per_firm_fy")]
