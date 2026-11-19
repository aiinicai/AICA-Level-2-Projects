from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

from core.choices import Frequency

PAN_VALIDATOR = RegexValidator(r"^[A-Z]{5}[0-9]{4}[A-Z]$", "Enter a valid PAN, e.g. ABCDE1234F.")
GSTIN_VALIDATOR = RegexValidator(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", "Enter a valid 15-character GSTIN.")


class Client(models.Model):
    class Type(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        HUF = "HUF", "HUF"
        PROPRIETORSHIP = "PROPRIETORSHIP", "Proprietorship"
        PARTNERSHIP = "PARTNERSHIP", "Partnership"
        LLP = "LLP", "LLP"
        COMPANY = "COMPANY", "Company"
        TRUST = "TRUST", "Trust"
        OTHER = "OTHER", "Other"

    firm = models.ForeignKey("accounts.Firm", on_delete=models.CASCADE, related_name="clients")
    name = models.CharField(max_length=200)
    type = models.CharField("Constitution", max_length=20, choices=Type.choices, default=Type.INDIVIDUAL)
    pan = models.CharField("PAN", max_length=10, null=True, blank=True, validators=[PAN_VALIDATOR])
    gstin = models.CharField("GSTIN", max_length=15, null=True, blank=True, validators=[GSTIN_VALIDATOR])
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    contact_person = models.CharField(max_length=150, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField("Internal notes", blank=True)
    is_active = models.BooleanField(default=True)  # archive instead of delete: financial history must survive
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["firm", "pan"], condition=Q(pan__isnull=False), name="unique_pan_per_firm"),
        ]
        indexes = [models.Index(fields=["firm", "name"])]

    def __str__(self):
        return self.name


class ClientService(models.Model):
    """An engagement the firm provides to a client, e.g. 'GST Returns', 'Statutory Audit'."""

    firm = models.ForeignKey("accounts.Firm", on_delete=models.CASCADE, related_name="client_services")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="services")
    name = models.CharField("Service", max_length=150)
    fee = models.DecimalField("Fee (₹)", max_digits=12, decimal_places=2, null=True, blank=True)
    billing_frequency = models.CharField("Billed", max_length=12, choices=Frequency.choices, blank=True, help_text="Leave blank for one-off work.")
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} – {self.client}"
