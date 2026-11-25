from decimal import Decimal

from django import forms

from .models import (
    Asset,
    AssetClass,
    CapexRequisition,
    CWIP,
    Document,
    RevaluationRecord,
    Vendor,
)


class BootstrapModelForm(forms.ModelForm):
    """Applies Bootstrap form-control classes to every field automatically."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class CapexRequisitionForm(BootstrapModelForm):
    class Meta:
        model = CapexRequisition
        fields = [
            "entity", "title", "justification", "estimated_cost",
            "delegated_authority_threshold", "board_resolution_reference",
        ]
        widgets = {"justification": forms.Textarea(attrs={"rows": 3})}


class CWIPForm(BootstrapModelForm):
    class Meta:
        model = CWIP
        fields = [
            "entity", "requisition", "reference", "description", "vendor",
            "po_number", "grn_number", "invoice_number", "invoice_date",
            "base_cost", "freight_cost", "duty_cost", "installation_cost",
            "borrowing_cost", "other_cost",
        ]
        widgets = {"invoice_date": forms.DateInput(attrs={"type": "date"})}


class CapitaliseForm(forms.Form):
    """Fields needed to spin a Ready CWIP item into a live Asset Master record."""

    description = forms.CharField(max_length=255)
    make_model = forms.CharField(max_length=255, required=False, label="Make / model / spec")
    asset_class = forms.ModelChoiceField(queryset=AssetClass.objects.all())
    serial_number = forms.CharField(max_length=128, required=False)
    acquisition_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    put_to_use_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    depreciation_method = forms.ChoiceField(choices=AssetClass.Method.choices)
    useful_life_years = forms.DecimalField(max_digits=5, decimal_places=2)
    residual_value_pct = forms.DecimalField(max_digits=5, decimal_places=2, initial=5)
    tax_block_code = forms.CharField(max_length=16, required=False)
    tax_wdv_rate_pct = forms.DecimalField(max_digits=5, decimal_places=2, required=False)
    location = forms.ModelChoiceField(queryset=None)
    department = forms.CharField(max_length=128, required=False)
    custodian = forms.ModelChoiceField(queryset=None, required=False)
    ownership_status = forms.ChoiceField(choices=Asset.OwnershipStatus.choices)
    is_immovable_property = forms.BooleanField(required=False)
    title_deed_in_company_name = forms.NullBooleanField(required=False)
    title_deed_reference = forms.CharField(max_length=128, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        from locations.models import Location

        self.fields["location"].queryset = Location.objects.filter(is_active=True)
        self.fields["custodian"].queryset = get_user_model().objects.filter(is_active=True)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class AssetEditForm(BootstrapModelForm):
    class Meta:
        model = Asset
        fields = [
            "description", "make_model", "serial_number", "location", "department",
            "custodian", "ownership_status", "title_deed_in_company_name", "title_deed_reference",
            "encumbrance_details", "is_immovable_property", "insurance_policy_number", "insurer_name",
            "insurance_sum_insured", "insurance_renewal_date", "amc_provider", "amc_renewal_date",
            "life_status",
        ]
        widgets = {
            "insurance_renewal_date": forms.DateInput(attrs={"type": "date"}),
            "amc_renewal_date": forms.DateInput(attrs={"type": "date"}),
            "encumbrance_details": forms.Textarea(attrs={"rows": 2}),
        }


class DocumentUploadForm(BootstrapModelForm):
    class Meta:
        model = Document
        fields = ["doc_type", "file", "description"]


class VendorForm(BootstrapModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "gstin", "address", "contact_email", "contact_phone", "is_related_party"]


class RevaluationForm(BootstrapModelForm):
    class Meta:
        model = RevaluationRecord
        fields = [
            "asset", "valuer_name", "valuer_registration_number", "valuation_date",
            "methodology", "fair_value", "carrying_value_before",
        ]
        widgets = {"valuation_date": forms.DateInput(attrs={"type": "date"})}

    def clean(self):
        cleaned = super().clean()
        fair_value = cleaned.get("fair_value")
        carrying = cleaned.get("carrying_value_before")
        if fair_value is not None and carrying is not None and carrying:
            surplus = fair_value - carrying
            movement_pct = (surplus / carrying) * 100

            # movement_pct is computed here rather than declared as a form field, so
            # ModelForm validation never checks it against the model field's max_digits —
            # without this check a very small carrying value (e.g. an asset depreciated
            # almost to nil) can produce a percentage the field can't store, which used to
            # save "successfully" and then crash the next time anything read this row back
            # (a raw-database bug, not something a form resubmission could fix). Validate
            # explicitly against the field's own capacity so it surfaces as a normal form
            # error instead.
            field = self.instance._meta.get_field("movement_pct")
            limit = Decimal(10) ** (field.max_digits - field.decimal_places) - 1
            if abs(movement_pct) > limit:
                raise forms.ValidationError(
                    "The carrying value is too small relative to the fair value — this "
                    "would produce an implausible percentage movement (%.2f%%). Please "
                    "double-check both figures." % movement_pct
                )

            cleaned["surplus_or_deficit"] = surplus
            cleaned["movement_pct"] = movement_pct
        return cleaned


class BulkImportForm(forms.Form):
    file = forms.FileField(help_text="CSV file matching the downloadable template.")
