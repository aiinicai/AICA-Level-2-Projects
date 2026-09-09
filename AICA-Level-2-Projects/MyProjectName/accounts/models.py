from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user so RBAC (Section 3(1) maker-checker, CARO evidence) can carry
    company-specific identity fields, not just username/password.

    Role is expressed through Django Groups (see accounts.roles / the
    bootstrap_roles management command), keeping permissions data-driven and
    editable from the admin rather than hard-coded — but every group a user
    belongs to is still visible here for quick reference.
    """

    class Theme(models.TextChoices):
        NAVY = "navy", "Corporate Navy"
        MIDNIGHT = "midnight", "Midnight Dark"
        EMERALD = "emerald", "Emerald"
        SLATE = "slate", "Slate Steel"
        INDIGO = "indigo", "Royal Indigo"
        AMBER = "amber", "Amber Sunset"

    employee_id = models.CharField(max_length=32, blank=True)
    designation = models.CharField(max_length=128, blank=True)
    department = models.CharField(max_length=128, blank=True)
    is_active_custodian = models.BooleanField(
        default=True,
        help_text="Whether this user can currently be assigned as an asset custodian.",
    )
    theme = models.CharField(
        max_length=16, choices=Theme.choices, default=Theme.NAVY,
        help_text="UI theme preference — persists across devices once signed in.",
    )

    def role_names(self):
        return list(self.groups.values_list("name", flat=True))

    def __str__(self):
        full = self.get_full_name()
        return f"{full} ({self.username})" if full else self.username
