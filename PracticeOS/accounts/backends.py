from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend


class WorkspaceBackend(BaseBackend):
    """Authenticate with (workspace subdomain, email, password)."""

    def authenticate(self, request, subdomain=None, email=None, password=None, **kwargs):
        if not (subdomain and email and password):
            return None
        User = get_user_model()
        try:
            user = User.objects.select_related("firm").get(firm__subdomain=subdomain.strip().lower(), email=email.strip().lower())
        except User.DoesNotExist:
            User().set_password(password)  # burn comparable time so unknown logins aren't distinguishable
            return None
        return user if user.check_password(password) and user.is_active else None

    def get_user(self, user_id):
        User = get_user_model()
        return User.objects.select_related("firm").filter(pk=user_id, is_active=True).first()
