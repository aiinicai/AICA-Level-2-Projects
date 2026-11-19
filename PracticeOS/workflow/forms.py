from django import forms
from django.db.models import Q

from accounts.models import User
from core.forms import TenantModelForm, date_input
from crm.models import Client

from .models import RecurringRule, Task
from .recurrence import first_due_date


class TaskForm(TenantModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "client", "assignee", "status", "priority", "due_date"]
        widgets = {"due_date": date_input()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = User.objects.filter(firm=self.firm, is_active=True).exclude(role=User.Role.CLIENT)
        self.fields["assignee"].empty_label = "Unassigned"
        keep = Q(pk=self.instance.client_id) if self.instance.client_id else Q(pk__in=[])
        self.fields["client"].queryset = Client.objects.filter(Q(firm=self.firm), Q(is_active=True) | keep)


class RuleForm(TenantModelForm):
    month = forms.IntegerField(
        label="Anchor month (1–12)", required=False, min_value=1, max_value=12,
        help_text="For quarterly/half-yearly/annual rules: the first month it falls due (e.g. 7 for July).",
    )

    class Meta:
        model = RecurringRule
        fields = ["title", "description", "client", "assignee", "priority", "frequency", "day_of_month", "month", "lead_days"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = User.objects.filter(firm=self.firm, is_active=True).exclude(role=User.Role.CLIENT)
        self.fields["assignee"].empty_label = "Unassigned"
        self.fields["client"].queryset = Client.objects.filter(firm=self.firm, is_active=True)
        self.fields["client"].empty_label = "— All / none —"

    def save(self, commit=True):
        rule = super().save(commit=False)
        rule.next_due_date = first_due_date(rule.frequency, rule.day_of_month, self.cleaned_data.get("month"))
        rule.save()
        return rule
