from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

ADMIN, TEAM, CLIENT = "ADMIN", "TEAM_MEMBER", "CLIENT"


def role_required(*roles):
    """Gate a view by role. Anonymous -> login page; a client login hitting a staff page -> their
    portal; any other mismatch -> 403."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                if request.user.role == CLIENT:
                    return redirect("portal")
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


staff_required = role_required(ADMIN, TEAM)
admin_required = role_required(ADMIN)
any_role_required = role_required(ADMIN, TEAM, CLIENT)
