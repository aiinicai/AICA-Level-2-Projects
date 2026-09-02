from django.conf import settings
from django.db import models

from locations.models import Entity

User = settings.AUTH_USER_MODEL


class FinancialYear(models.Model):
    """Indian FY (1 Apr – 31 Mar) used to scope every compliance report."""

    entity = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="financial_years")
    label = models.CharField(max_length=16, help_text="e.g. FY 2025-26")
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        unique_together = [("entity", "label")]

    def __str__(self):
        return f"{self.entity} — {self.label}"


class BenamiDeclaration(models.Model):
    """CARO 3(i)(e) — disclosure of proceedings under the Benami Transactions (Prohibition) Act."""

    entity = models.ForeignKey(Entity, on_delete=models.PROTECT, related_name="benami_declarations")
    financial_year = models.ForeignKey(FinancialYear, on_delete=models.PROTECT, related_name="benami_declarations")
    proceedings_exist = models.BooleanField(default=False)
    details = models.TextField(blank=True)
    declared_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="benami_declarations")
    declared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-declared_at"]
        unique_together = [("entity", "financial_year")]

    def __str__(self):
        return f"Benami declaration — {self.entity} — {self.financial_year.label}"
