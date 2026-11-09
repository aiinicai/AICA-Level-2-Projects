"""Checks that the right email version goes to the right people.

Each group always receives its own version (clients the Client version, employees the Team version);
the app never swaps them. What can still go wrong is the *content*: team material pasted into the
Client version (register reference, the internal subject or opening), or a person in the wrong list
(a colleague in the client list, an outsider in the employee list). These checks find both.
"""

from __future__ import annotations

import re

from .email_composer import DEFAULT_INTERNAL_INTRO, DEFAULT_INTRO

PUBLIC_DOMAINS = {"gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "outlook.com", "hotmail.com",
                  "live.com", "rediffmail.com", "icloud.com", "proton.me", "protonmail.com", "zoho.com", "aol.com"}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def team_markers_in_client(subject: str, intro: str, body: str) -> list[str]:
    """Signs that the Client version contains Team (internal) material. Each is a reason to stop."""
    found = []
    if _norm(subject).startswith("[precedent register]"):
        found.append("the subject starts with '[Precedent register]' (the team subject)")
    if _norm(DEFAULT_INTERNAL_INTRO)[:60] in _norm(intro) or "precedent register" in _norm(intro):
        found.append("the opening paragraph is the team opening (it mentions the precedent register)")
    if re.search(r"precedent register reference|\bJIA-\d{4}-\d{4}\b", body or "", re.IGNORECASE):
        found.append("the content includes the internal precedent register reference (JIA-…)")
    return found


def client_markers_in_team(subject: str, intro: str, body: str) -> list[str]:
    """Signs that the Team version contains the Client version (less serious - it goes to colleagues)."""
    found = []
    if _norm(DEFAULT_INTRO)[:60] in _norm(intro):
        found.append("the opening paragraph is the client opening")
    return found


def domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].strip().lower() if "@" in (email or "") else ""


def recipient_warnings(clients: list, employees: list, sender_email: str) -> list[str]:
    """People who look like they are in the wrong list, judged by the firm's email domain."""
    firm = domain(sender_email)
    if not firm or firm in PUBLIC_DOMAINS:
        return []           # personal sender address: the firm's domain is unknown
    out = []
    inside = [r for r in clients if domain(r.email) == firm]
    if inside:
        names = ", ".join(f"{r.name} <{r.email}>" for r in inside[:4])
        out.append(f"{len(inside)} person(s) in the CLIENT list use the firm's own domain @{firm} - are they "
                   f"employees? {names}")
    outside = [r for r in employees if domain(r.email) != firm]
    if outside:
        names = ", ".join(f"{r.name} <{r.email}>" for r in outside[:4])
        out.append(f"{len(outside)} person(s) in the EMPLOYEE list are outside @{firm} - they would receive the "
                   f"internal Team version: {names}")
    return out
