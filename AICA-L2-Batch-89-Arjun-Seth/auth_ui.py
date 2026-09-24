# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Page guard and small UI helpers (UI layer - deliberately NOT in core/).

EVALUATION EDITION: there is no sign-in. The application opens directly as a built-in "Evaluator" profile with every
right, so that all features can be tried. (The full build has user IDs, passwords and five access levels.)

* ``require_login()`` goes at the top of EVERY page in /pages: it loads the Evaluator profile, applies the theme and
  navigation, and returns the profile as a dict.
* ``set_flash()`` / ``show_flash()`` show a message that survives a rerun.
"""
import streamlit as st
from sqlalchemy import select

from core import permissions
from core.workflow import get_user_preferences, workspace_id_for
from db.database import get_session, init_db
from db.models import User
from ui_theme import apply_appearance

EVALUATOR_LOGIN = "evaluator"
EVALUATOR_NAME = "Evaluator"


def _evaluator_profile() -> dict:
    """The built-in Evaluator (created on first use) as the dict every page expects."""
    init_db()
    with get_session() as session:
        user = session.scalars(select(User).where(User.email == EVALUATOR_LOGIN)).first()
        if user is None:
            # "!" is not a valid password hash, so this account can never be signed in to: it only exists to own the data.
            user = User(email=EVALUATOR_LOGIN, full_name=EVALUATOR_NAME, password_hash="!", role="Admin", access_level="admin", is_active=True)
            session.add(user)
            session.commit()
        preferences = get_user_preferences(session, user.user_id)
        level = permissions.level_for(user.access_level, user.role)
        return {
            "user_id": user.user_id,
            "email": user.email,
            "login": user.email,
            "name": user.full_name or EVALUATOR_NAME,
            "role": user.role,
            "number_format": preferences["number_format"],
            "default_currency": preferences["default_currency"],
            "theme": preferences["theme"],
            "dashboard_layout": preferences["dashboard_layout"],
            "access_level": level,
            "rights": sorted(permissions.rights_of(level)),
            "workspace_id": workspace_id_for(session, user.user_id),
        }


def require_login(right: str = None):
    """Page guard. Returns the Evaluator profile dict (and stores it in st.session_state["user"])."""
    user = _evaluator_profile()
    st.session_state["user"] = user
    apply_appearance(user)  # the saved theme + layout, navigation and footer
    if right and right not in user["rights"]:  # never true for the Evaluator; kept so every page still states what it needs
        st.error("You do not have access to this page.")
        st.stop()
    return user


def set_flash(kind: str, message: str) -> None:
    """Remember a message ('success', 'error', 'info' or 'warning') for the next run."""
    st.session_state["_flash"] = (kind, message)


def show_flash() -> None:
    flash = st.session_state.pop("_flash", None)
    if flash:
        kind, message = flash
        getattr(st, kind)(message)
