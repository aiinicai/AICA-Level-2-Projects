"""Who may see which clients, tasks. Mirrors the web version's role rules."""
from functools import wraps

from flask import abort, flash, g, redirect, request, url_for

from . import perms
from .models import Client, Task, client_staff, db


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapper


def manager_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        if not (g.user.is_manager_or_above or perms.granted_elevated(g.user, request.blueprint)):
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        if not (g.user.is_admin_or_partner or perms.granted_elevated(g.user, request.blueprint)):
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def visible_clients(user, include_archived: bool = False):
    q = Client.query
    if not include_archived:
        q = q.filter(Client.archived.is_(False))
    if user.is_manager_or_above:
        return q
    shared = db.select(client_staff.c.client_id).where(client_staff.c.user_id == user.id)
    return q.filter(db.or_(Client.assigned_to_id == user.id, Client.id.in_(shared)))


def visible_client_ids(user) -> list[int]:
    return [c.id for c in visible_clients(user).with_entities(Client.id).all()]


def can_access_client(user, client: Client) -> bool:
    if client is None:
        return False
    if user.is_manager_or_above:
        return True
    return client.assigned_to_id == user.id or any(s.id == user.id for s in client.staff)


def get_client_or_403(user, client_id: int) -> Client:
    client = db.get_or_404(Client, client_id)
    if not can_access_client(user, client):
        abort(403)
    return client


def visible_tasks(user):
    q = Task.query
    if user.is_manager_or_above:
        return q
    return q.filter(db.or_(Task.assigned_to_id == user.id, Task.created_by_id == user.id))
