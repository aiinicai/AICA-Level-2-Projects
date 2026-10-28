"""One place for the Gemini key, model and consent, shared by every page.

The key lives in the browser session (st.session_state) or in the environment / .env file. It is never written
to disk by the app.
"""
from __future__ import annotations

import os

import streamlit as st

from fsbuilder.reviewer.llm import DEFAULT_MODEL

KEY, MODEL, CONSENT = "gemini_key", "gemini_model", "ai_consent"


def config() -> tuple[str, str, bool]:
    """(key, model, consent). Session values win; the environment (.env) is the fallback for key and model."""
    ss = st.session_state
    key = (ss.get(KEY) or os.environ.get("GEMINI_API_KEY", "")).strip()
    model = (ss.get(MODEL) or os.environ.get("GEMINI_MODEL", "") or DEFAULT_MODEL).strip()
    return key, model, bool(ss.get(CONSENT))


def ready() -> bool:
    key, _, consent = config()
    return bool(key) and consent


def source() -> str:
    ss = st.session_state
    if ss.get(KEY):
        return "entered on the Settings page"
    return "the .env file or environment" if os.environ.get("GEMINI_API_KEY") else "not set"


def badge() -> None:
    """A small status chip plus a pointer to the Settings page."""
    key, model, consent = config()
    if key and consent:
        st.markdown(f"<span class='ll-badge on'>AI ready · {model}</span>", unsafe_allow_html=True)
    elif key:
        st.markdown("<span class='ll-badge off'>AI key found, consent not given</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span class='ll-badge off'>AI off, no key</span>", unsafe_allow_html=True)


def consent_box(what: str) -> None:
    """The consent tick, on the page that sends the data, so nobody has to leave to give it. Kept in step with Settings & AI."""
    ss = st.session_state
    if not config()[0]:
        return
    ticked = st.checkbox(f"I agree that {what} is sent to Google's Gemini API when I press Run AI review.",
                         value=bool(ss.get(CONSENT)), key="ai_consent_inline")
    if ticked != bool(ss.get(CONSENT)):
        ss[CONSENT] = ticked
        st.rerun()
