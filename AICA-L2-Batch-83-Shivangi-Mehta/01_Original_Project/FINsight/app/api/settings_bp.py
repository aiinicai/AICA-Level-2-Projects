"""
Settings blueprint (Blueprint Section E, #18).

Stage 14 (Final UX & Application Polish): replaced the bare placeholder
with the About / Privacy content Stage 14 section 25 asks for. This was
static, informational content only at that point — no new setting was
actually editable here.

Stage 16 (LAN / Same Network Access), Section 28: adds exactly one real
editable setting — "Change LAN Access Password" — because it was easy
and safe within this existing screen (a single POST handler using the
same lan_access_service already built for first-run setup, no new
architecture). It is only ever shown when LAN mode is actually active
(`app.config["LAN_MODE_ENABLED"]`); in local/dev mode this section does
not render, since there is no LAN access password to change. Everything
else on this page (About, Privacy, Materiality) is unchanged from
Stage 14.
"""
from flask import Blueprint, current_app, render_template, request

from app.services import lan_access_service

# No formal release-versioning scheme exists yet anywhere in this
# codebase (no VERSION file, no packaging config with a version). This
# is stated plainly rather than inventing a "1.0.0"-style number that
# would imply a release process that doesn't exist.
APP_VERSION = "FinSight V1 (Development Build)"

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


@settings_bp.route("/", methods=["GET", "POST"])
def index():
    errors: dict[str, str] = {}
    password_changed = False
    lan_mode_active = bool(current_app.config.get("LAN_MODE_ENABLED"))

    if lan_mode_active and request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_new_password", "")

        if not lan_access_service.verify_password(current_password):
            errors["current_password"] = "Current password is incorrect."
        if not errors and len(new_password) < lan_access_service.MIN_PASSWORD_LENGTH:
            errors["new_password"] = f"New password must be at least {lan_access_service.MIN_PASSWORD_LENGTH} characters."
        if not errors and new_password != confirm_password:
            errors["confirm_new_password"] = "New passwords do not match."

        if not errors:
            lan_access_service.set_password(new_password)
            password_changed = True

    return render_template(
        "settings/index.html",
        section="Settings",
        app_version=APP_VERSION,
        lan_mode_active=lan_mode_active,
        errors=errors,
        password_changed=password_changed,
    )
