from decimal import Decimal

from django import forms
from django.db.models import Q
from django.utils import timezone

from core.forms import StyledFormMixin, TenantModelForm, date_input
from crm.models import Client
from workflow.models import Task

from .models import Invoice, TimeEntry
from .services import items_from_time


class TaskChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, t):
        return f"{t.client.name} – {t.title}" if t.client else t.title


class TimeEntryForm(TenantModelForm):
    hours = forms.IntegerField(min_value=0, max_value=24, initial=1)
    mins = forms.IntegerField(label="Minutes", min_value=0, max_value=59, initial=0)

    class Meta:
        model = TimeEntry
        fields = ["client", "task", "work_date", "hours", "mins", "description", "billable"]
        widgets = {"work_date": date_input(), "description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.filter(firm=self.firm, is_active=True)
        keep = Q(pk=self.instance.task_id) if self.instance.task_id else Q(pk__in=[])
        open_tasks = Task.objects.filter(Q(firm=self.firm), ~Q(status=Task.Status.COMPLETED) | keep).select_related("client")
        self.fields["task"] = TaskChoiceField(queryset=open_tasks, required=False, label="Task (optional)", empty_label="— General work —")
        self.fields["task"].widget.attrs["class"] = "input"
        self.fields["work_date"].widget.attrs["max"] = timezone.localdate().isoformat()
        if self.instance.pk:
            self.initial["hours"], self.initial["mins"] = divmod(self.instance.minutes, 60)
        else:
            self.initial.setdefault("work_date", timezone.localdate())

    def clean(self):
        data = super().clean()
        if "hours" in data and "mins" in data:
            total = data["hours"] * 60 + data["mins"]
            if total < 1:
                self.add_error("hours", "Enter the time spent.")
            elif total > 24 * 60:
                self.add_error("hours", "A day has only 24 hours.")
            else:
                self.instance.minutes = total
        if data.get("work_date") and data["work_date"] > timezone.localdate():
            self.add_error("work_date", "You can't log time in the future.")
        task, client = data.get("task"), data.get("client")
        if task and client and task.client_id and task.client_id != client.pk:
            self.add_error("task", "That task belongs to a different client.")
        return data


class InvoiceForm(TenantModelForm):
    class Meta:
        model = Invoice
        fields = ["client", "issue_date", "due_date", "notes"]
        widgets = {"issue_date": date_input(), "due_date": date_input(), "notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.filter(firm=self.firm, is_active=True)
        self.fields["due_date"].required = False
        self.fields["due_date"].help_text = "Defaults to 15 days after the issue date."
        self.initial.setdefault("issue_date", timezone.localdate())

    def clean(self):
        data = super().clean()
        if data.get("issue_date") and data.get("due_date") and data["due_date"] < data["issue_date"]:
            self.add_error("due_date", "Due date can't be before the issue date.")
        return data


class ItemForm(StyledFormMixin, forms.Form):
    description = forms.CharField(min_length=2, max_length=300, widget=forms.TextInput(attrs={"placeholder": "e.g. GSTR-3B filing – Oct 2026"}))
    quantity = forms.DecimalField(min_value=Decimal("0.01"), max_digits=10, decimal_places=2, initial=1)
    rate = forms.DecimalField(label="Rate (₹)", min_value=0, max_digits=12, decimal_places=2)
    tax_rate = forms.DecimalField(label="GST %", min_value=0, max_value=100, max_digits=5, decimal_places=2, initial=18)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_widgets()


class FromTimeForm(StyledFormMixin, forms.Form):
    entries = forms.ModelMultipleChoiceField(queryset=TimeEntry.objects.none(), widget=forms.CheckboxSelectMultiple, error_messages={"required": "Select at least one time entry."})
    default_rate = forms.DecimalField(label="Fallback hourly rate (₹)", required=False, min_value=0, max_digits=10, decimal_places=2,
                                      help_text="Used when neither the entry nor the staff member has a rate.")
    tax_rate = forms.DecimalField(label="GST %", min_value=0, max_value=100, max_digits=5, decimal_places=2, initial=18)
    due_date = forms.DateField(required=False, widget=date_input())

    def __init__(self, *args, firm, client, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["entries"].queryset = TimeEntry.objects.filter(firm=firm, client=client, billable=True, invoice__isnull=True).select_related("user", "task")
        self.style_widgets()

    def items(self):
        d = self.cleaned_data
        return items_from_time(d["entries"], d.get("default_rate") or Decimal("0"), d["tax_rate"])


class PaymentForm(StyledFormMixin, forms.Form):
    METHODS = [(m, m) for m in ["UPI", "NEFT / RTGS", "IMPS", "Cheque", "Cash", "Card"]]
    amount = forms.DecimalField(label="Amount received (₹)", min_value=Decimal("0.01"), max_digits=12, decimal_places=2)
    paid_on = forms.DateField(label="Date received", widget=date_input())
    method = forms.ChoiceField(label="Mode", choices=METHODS)
    reference = forms.CharField(label="Reference / UTR", required=False, max_length=100)

    def __init__(self, *args, invoice, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        self.initial.setdefault("amount", invoice.balance)
        self.initial.setdefault("paid_on", timezone.localdate())
        self.style_widgets()

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount > self.invoice.balance:
            raise forms.ValidationError(f"Can't exceed the outstanding balance of ₹{self.invoice.balance}.")
        return amount

    def clean_paid_on(self):
        if self.cleaned_data["paid_on"] > timezone.localdate():
            raise forms.ValidationError("Payment date can't be in the future.")
        return self.cleaned_data["paid_on"]
