import os
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.files.storage import FileSystemStorage
from django.core.validators import RegexValidator
from django.db import models
from django.conf import settings

PAN_VALIDATOR = RegexValidator(r"^[A-Z]{5}[0-9]{4}[A-Z]$", "Enter a valid PAN, e.g. ABCDE1234F.")
GSTIN_VALIDATOR = RegexValidator(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", "Enter a valid 15-character GSTIN.")


def private_storage():
    return FileSystemStorage(location=settings.UPLOAD_ROOT)


def firm_signature_path(instance, filename):
    return f"{instance.pk}/signature{os.path.splitext(filename)[1].lower()}"


class Firm(models.Model):
    """The tenant: one CA practice = one workspace."""

    class Type(models.TextChoices):
        PROPRIETORSHIP = "PROPRIETORSHIP", "Proprietary"
        PARTNERSHIP = "PARTNERSHIP", "Partnership"
        LLP = "LLP", "LLP"
        COMPANY = "COMPANY", "Company"

    class Size(models.TextChoices):
        SOLO = "SOLO", "Just me"
        SMALL = "SMALL", "2 – 10 people"
        MEDIUM = "MEDIUM", "11 – 50 people"
        LARGE = "LARGE", "50+ people"

    name = models.CharField(max_length=150)
    type = models.CharField(max_length=20, choices=Type.choices)
    size = models.CharField(max_length=10, choices=Size.choices)
    subdomain = models.SlugField(max_length=30, unique=True)  # simulated workspace address

    # Tax & Contact details for Invoicing & Communications
    pan = models.CharField("Firm PAN", max_length=10, blank=True, default="", validators=[PAN_VALIDATOR])
    gstin = models.CharField("Firm GSTIN", max_length=15, blank=True, default="", validators=[GSTIN_VALIDATOR])
    address = models.TextField("Office Address", blank=True, default="")
    phone = models.CharField("Phone Number", max_length=30, blank=True, default="")
    email = models.EmailField("Firm Email", blank=True, default="")
    website = models.URLField("Website", blank=True, default="")

    # Bank Details for Invoices
    bank_name = models.CharField("Bank Name", max_length=100, blank=True, default="")
    bank_account_name = models.CharField("Beneficiary / Account Name", max_length=150, blank=True, default="")
    bank_account_no = models.CharField("Account Number", max_length=50, blank=True, default="")
    bank_ifsc = models.CharField("IFSC Code", max_length=20, blank=True, default="")
    bank_branch = models.CharField("Branch", max_length=100, blank=True, default="")
    upi_id = models.CharField("UPI ID / VPA", max_length=100, blank=True, default="")

    # Invoice Signatory & Signature
    signatory_name = models.CharField("Authorized Signatory Name", max_length=150, blank=True, default="")
    signatory_designation = models.CharField("Designation / Title", max_length=100, blank=True, default="Chartered Accountant")
    signature_image = models.FileField(
        "Signature / Stamp Image",
        storage=private_storage,
        upload_to=firm_signature_path,
        null=True,
        blank=True,
        help_text="Upload scanned signature or firm stamp (PNG/JPG)."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def workspace_url(self):
        return f"https://{self.subdomain}.{settings.BASE_DOMAIN}"  # simulation: no DNS is created


class UserManager(BaseUserManager):
    def create_user(self, firm, email, name, password, role="TEAM_MEMBER", **extra):
        email = email.strip().lower()
        user = self.model(firm=firm, email=email, name=name, role=role, username=f"{firm.subdomain}:{email}", **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        TEAM_MEMBER = "TEAM_MEMBER", "Team member"
        CLIENT = "CLIENT", "Client"

    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name="users")
    # Django wants one globally-unique login key. Emails only need to be unique *within* a firm,
    # so the key is "<workspace>:<email>"; people log in with workspace + email (see WorkspaceBackend).
    username = models.CharField(max_length=255, unique=True, editable=False)
    email = models.EmailField()
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.TEAM_MEMBER)
    # Only for role=CLIENT: which client record this portal login belongs to
    client = models.ForeignKey("crm.Client", null=True, blank=True, on_delete=models.SET_NULL, related_name="portal_users")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS: list[str] = []
    objects = UserManager()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["firm", "email"], name="unique_email_per_firm")]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT
