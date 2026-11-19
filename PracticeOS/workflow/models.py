from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.choices import Frequency, Priority


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "TODO", "To Do"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        REVIEW = "REVIEW", "Review"
        COMPLETED = "COMPLETED", "Completed"

    firm = models.ForeignKey("accounts.Firm", on_delete=models.CASCADE, related_name="tasks")
    client = models.ForeignKey("crm.Client", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=6, choices=Priority.choices, default=Priority.MEDIUM)
    assignee = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_tasks")
    created_by = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL, related_name="created_tasks")
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True, editable=False)
    recurring_rule = models.ForeignKey("RecurringRule", null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    period_label = models.CharField(max_length=60, blank=True)  # e.g. "Oct 2026"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Makes recurring-task generation idempotent: one task per rule per due date.
            models.UniqueConstraint(fields=["recurring_rule", "due_date"], name="one_task_per_rule_occurrence"),
        ]
        indexes = [models.Index(fields=["firm", "status"]), models.Index(fields=["firm", "due_date"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.status == self.Status.COMPLETED:
            self.completed_at = self.completed_at or timezone.now()
        else:
            self.completed_at = None
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return bool(self.due_date and self.status != self.Status.COMPLETED and self.due_date < timezone.localdate())


class RecurringRule(models.Model):
    """Template that spawns a Task every period (monthly GSTR-3B, annual ITR, ...)."""

    firm = models.ForeignKey("accounts.Firm", on_delete=models.CASCADE, related_name="recurring_rules")
    client = models.ForeignKey("crm.Client", null=True, blank=True, on_delete=models.CASCADE, related_name="recurring_rules")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignee = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    priority = models.CharField(max_length=6, choices=Priority.choices, default=Priority.MEDIUM)
    frequency = models.CharField(max_length=12, choices=Frequency.choices)
    day_of_month = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)], help_text="Clamped to the month's length (31 → 28/29/30).")
    next_due_date = models.DateField()  # next occurrence not yet turned into a task
    lead_days = models.PositiveSmallIntegerField("Create task … days before due", default=7, validators=[MaxValueValidator(60)])
    is_active = models.BooleanField(default=True)
    last_generated = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["next_due_date"]

    def __str__(self):
        return self.title
