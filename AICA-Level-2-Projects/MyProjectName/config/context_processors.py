from django.conf import settings

from accounts.models import User


def far_globals(request):
    """Make FAR policy constants, role flags, and the current theme available in every template."""
    ctx = {
        "FAR_SETTINGS": settings.FAR_SETTINGS,
        "COMPANY_NAME": settings.FAR_SETTINGS["COMPANY_NAME"],
        "THEME_CHOICES": User.Theme.choices,
    }
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        group_names = set(user.groups.values_list("name", flat=True))
        ctx.update(
            {
                "is_data_entry": user.is_superuser or "Data Entry" in group_names,
                "is_verifier": user.is_superuser or "Verifier" in group_names,
                "is_approver": user.is_superuser or "Approver" in group_names,
                "is_admin_cfo": user.is_superuser or "Admin/CFO" in group_names,
                "is_auditor": user.is_superuser or "Auditor (Read-only)" in group_names,
                "current_theme": user.theme,
            }
        )
    else:
        ctx["current_theme"] = None
    return ctx
