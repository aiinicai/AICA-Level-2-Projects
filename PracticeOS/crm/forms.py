from django import forms

from core.forms import TenantModelForm, date_input

from .models import Client, ClientService


class ClientForm(TenantModelForm):
    class Meta:
        model = Client
        fields = ["name", "type", "contact_person", "pan", "gstin", "email", "phone", "address", "notes"]
        widgets = {"address": forms.Textarea(attrs={"rows": 2}), "notes": forms.Textarea(attrs={"rows": 2})}

    def clean_pan(self):
        pan = (self.cleaned_data.get("pan") or "").strip().upper() or None
        if pan and Client.objects.filter(firm=self.firm, pan=pan).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("You already have a client with this PAN.")
        return pan

    def clean_gstin(self):
        return (self.cleaned_data.get("gstin") or "").strip().upper() or None


class ServiceForm(TenantModelForm):
    class Meta:
        model = ClientService
        fields = ["name", "fee", "billing_frequency", "start_date", "is_active"]
        widgets = {"start_date": date_input(), "name": forms.TextInput(attrs={"list": "service-suggestions"})}
