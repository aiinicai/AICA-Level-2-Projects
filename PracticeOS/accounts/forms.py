import re
import secrets

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.db import transaction

from core.forms import StyledFormMixin, TenantModelForm
from crm.models import Client

from .models import Firm, User

SUBDOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,28}[a-z0-9]$")
RESERVED = {"www", "app", "api", "admin", "mail", "support", "billing", "static"}
MAX_FAILED_LOGINS = 10
LOCKOUT_SECONDS = 15 * 60


class LoginForm(StyledFormMixin, forms.Form):
    workspace = forms.CharField(label="Workspace address", widget=forms.TextInput(attrs={"placeholder": "yourfirm", "autofocus": True}))
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None
        self.style_widgets()

    def clean(self):
        data = super().clean()
        if self.errors:
            return data
        ip = self.request.META.get("REMOTE_ADDR", "?") if self.request else "?"
        key = f"login-fail:{ip}"
        fails = cache.get(key, 0)
        if fails >= MAX_FAILED_LOGINS:
            raise forms.ValidationError("Too many failed attempts. Please try again in 15 minutes.")
        self.user = authenticate(self.request, subdomain=data["workspace"], email=data["email"], password=data["password"])
        if self.user is None:
            cache.set(key, fails + 1, LOCKOUT_SECONDS)
            # Same message for every failure: don't reveal which workspaces or emails exist.
            raise forms.ValidationError("Invalid workspace, email or password.")
        cache.delete(key)
        return data


class SignupForm(StyledFormMixin, forms.Form):
    name = forms.CharField(label="Your name", min_length=2, max_length=150)
    email = forms.EmailField(label="Work email")
    password = forms.CharField(widget=forms.PasswordInput, help_text="At least 8 characters.")
    firm_name = forms.CharField(label="Firm / company name", min_length=2, max_length=150)
    firm_type = forms.ChoiceField(label="Type of entity", choices=Firm.Type.choices, initial=Firm.Type.PARTNERSHIP)
    firm_size = forms.ChoiceField(label="Firm size", choices=Firm.Size.choices, initial=Firm.Size.SMALL)
    subdomain = forms.CharField(label="Workspace address", max_length=30, help_text="Team members and clients sign in with this.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_widgets()

    @property
    def account_fields(self):
        return [self[n] for n in ("name", "email", "password")]

    @property
    def firm_fields(self):
        return [self[n] for n in ("firm_name", "firm_type", "firm_size")]

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean_subdomain(self):
        sub = self.cleaned_data["subdomain"].strip().lower()
        if not SUBDOMAIN_RE.match(sub):
            raise forms.ValidationError("Use 3-30 lowercase letters, numbers or hyphens.")
        if sub in RESERVED:
            raise forms.ValidationError("That address is reserved.")
        if Firm.objects.filter(subdomain=sub).exists():
            raise forms.ValidationError("That address is already taken.")
        return sub

    @transaction.atomic
    def save(self):
        d = self.cleaned_data
        firm = Firm.objects.create(name=d["firm_name"].strip(), type=d["firm_type"], size=d["firm_size"], subdomain=d["subdomain"])
        return User.objects.create_user(firm, d["email"], d["name"].strip(), d["password"], role=User.Role.ADMIN)


class InviteForm(TenantModelForm):
    """Admin creates a team-member or client-portal login with a one-time temporary password."""

    class Meta:
        model = User
        fields = ["name", "email", "role", "client", "hourly_rate"]
        labels = {"client": "Linked client (client logins only)", "hourly_rate": "Hourly billing rate (₹)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [(User.Role.TEAM_MEMBER, "Team member"), (User.Role.CLIENT, "Client (portal access)")]
        self.fields["client"].queryset = Client.objects.filter(firm=self.firm, is_active=True)
        self.temp_password = None

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(firm=self.firm, email=email).exists():
            raise forms.ValidationError("Someone in this workspace already uses that email.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("role") == User.Role.CLIENT and not data.get("client"):
            self.add_error("client", "Choose which client this login belongs to.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = f"{self.firm.subdomain}:{user.email}"
        if user.role != User.Role.CLIENT:
            user.client = None
        # MVP: shown once on screen. Production: email a set-password link instead.
        self.temp_password = secrets.token_urlsafe(8)
        user.set_password(self.temp_password)
        user.save()
        return user


class FirmSettingsForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Firm
        fields = [
            "name",
            "type",
            "size",
            "pan",
            "gstin",
            "phone",
            "email",
            "website",
            "address",
            "bank_name",
            "bank_account_name",
            "bank_account_no",
            "bank_ifsc",
            "bank_branch",
            "upi_id",
            "signatory_name",
            "signatory_designation",
            "signature_image",
        ]
        labels = {
            "pan": "Firm PAN",
            "gstin": "Firm GSTIN",
            "bank_account_name": "Account Beneficiary Name",
            "bank_account_no": "Account Number",
            "bank_ifsc": "IFSC Code",
            "upi_id": "UPI ID / VPA",
            "signatory_name": "Authorized Signatory Name",
            "signatory_designation": "Signatory Designation",
            "signature_image": "Signature or Stamp Image",
        }
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2, "placeholder": "Registered office address..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_widgets()

    def clean_pan(self):
        return (self.cleaned_data.get("pan") or "").strip().upper()

    def clean_gstin(self):
        return (self.cleaned_data.get("gstin") or "").strip().upper()
