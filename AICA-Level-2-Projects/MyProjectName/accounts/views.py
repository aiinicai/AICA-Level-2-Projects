import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import User


@login_required
@require_POST
def set_theme(request):
    """
    Persists the signed-in user's UI theme choice server-side, so it follows
    them across devices/browsers. The page also applies the theme instantly
    client-side (see base.html) — this call just makes that choice durable.
    """
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}
    theme = payload.get("theme") or request.POST.get("theme")
    valid_themes = {choice for choice, _ in User.Theme.choices}
    if theme not in valid_themes:
        return JsonResponse({"ok": False, "error": "Unknown theme."}, status=400)
    request.user.theme = theme
    request.user.save(update_fields=["theme"])
    return JsonResponse({"ok": True, "theme": theme})
