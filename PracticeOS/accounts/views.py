from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_GET, require_POST

from core.decorators import admin_required, any_role_required
from core.utils import firm_object_or_404

from .forms import RESERVED, SUBDOMAIN_RE, FirmSettingsForm, InviteForm, LoginForm, SignupForm
from .models import Firm, User


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = LoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        return redirect(request.GET.get("next") or "home")
    return render(request, "registration/login.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")


def signup_view(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="accounts.backends.WorkspaceBackend")
        return render(request, "accounts/signup_done.html", {"firm": user.firm})
    return render(request, "accounts/signup.html", {"form": form})


@require_GET
def subdomain_check(request):
    """Live availability check used by the signup page (workspace-address simulation)."""
    candidate = slugify(request.GET.get("name", ""))[:30].strip("-")
    ok = bool(SUBDOMAIN_RE.match(candidate)) and candidate not in RESERVED and not Firm.objects.filter(subdomain=candidate).exists()
    return JsonResponse({"subdomain": candidate, "available": ok})


# ── Team management (admin) ──


@admin_required  # staff don't need the roster, and it shows billing rates
def team_list(request):
    users = User.objects.filter(firm=request.firm).select_related("client")
    return render(request, "accounts/team.html", {"users": users})


@admin_required
def team_invite(request):
    form = InviteForm(request.POST or None, firm=request.firm)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        return render(request, "accounts/invite_done.html", {"new_user": user, "temp_password": form.temp_password})
    return render(request, "form.html", {"form": form, "title": "Add a login", "cancel_url": "team_list", "submit": "Create login"})


def _guard_last_admin(target):
    return not User.objects.filter(firm=target.firm, role=User.Role.ADMIN, is_active=True).exclude(pk=target.pk).exists()


@admin_required
@require_POST
def team_toggle_active(request, pk):
    target = firm_object_or_404(User, request, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, "You can't disable your own login.")
    elif target.is_active and target.role == User.Role.ADMIN and _guard_last_admin(target):
        messages.error(request, "At least one active admin is required.")
    else:
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        messages.success(request, f"{target.name} {'enabled' if target.is_active else 'disabled'}.")
    return redirect("team_list")


@admin_required
@require_POST
def team_toggle_role(request, pk):
    target = firm_object_or_404(User, request, pk=pk)
    if target.role == User.Role.CLIENT or target.pk == request.user.pk:
        messages.error(request, "That role can't be changed here.")
    elif target.role == User.Role.ADMIN and _guard_last_admin(target):
        messages.error(request, "At least one active admin is required.")
    else:
        target.role = User.Role.TEAM_MEMBER if target.role == User.Role.ADMIN else User.Role.ADMIN
        target.save(update_fields=["role"])
        messages.success(request, f"{target.name} is now {target.get_role_display().lower()}.")
    return redirect("team_list")


@admin_required
def firm_settings(request):
    firm = request.firm
    form = FirmSettingsForm(request.POST or None, request.FILES or None, instance=firm)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Firm details and invoice settings saved.")
        return redirect("firm_settings")
    return render(request, "accounts/settings.html", {"form": form, "firm": firm})


@any_role_required
@require_GET
def firm_signature(request):
    if not request.firm.signature_image:
        raise Http404
    return FileResponse(request.firm.signature_image.open("rb"))
