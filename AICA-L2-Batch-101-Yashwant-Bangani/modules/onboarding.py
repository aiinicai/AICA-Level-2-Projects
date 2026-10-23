"""Candidate onboarding and system-clock-driven ICAI diet generator."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

import streamlit as st

# ICAI diets: January (5th), May (3rd), September (3rd). Dates follow the spec; always
# confirm the exact schedule on icai.org because ICAI may shift dates.
DIET_SCHEDULE: tuple[tuple[int, int], ...] = ((1, 5), (5, 3), (9, 3))


@dataclass(frozen=True)
class Diet:
    exam_date: date

    @property
    def label(self) -> str:
        return f"{calendar.month_name[self.exam_date.month]} {self.exam_date.year}"

    @property
    def full_label(self) -> str:
        return f"{self.label} (starts {self.exam_date.strftime('%d %b %Y')})"


def next_diets(today: date | None = None, count: int = 3) -> list[Diet]:
    """Return the next `count` future diets strictly after `today`."""
    today = today or date.today()
    candidates = [
        Diet(date(year, month, day))
        for year in range(today.year, today.year + 3)
        for month, day in DIET_SCHEDULE
    ]
    future = sorted((d for d in candidates if d.exam_date > today), key=lambda d: d.exam_date)
    return future[:count]


def days_remaining(target: date, today: date | None = None) -> int:
    return (target - (today or date.today())).days


@dataclass(frozen=True)
class Profile:
    name: str
    diet: Diet


def render_onboarding() -> Profile:
    """Sidebar onboarding block. Returns the active profile."""
    st.session_state.setdefault("candidate_name", "Candidate")
    st.session_state.setdefault("toast_shown_for", "")

    name = st.text_input("Candidate name", value=st.session_state["candidate_name"],
                         placeholder="e.g. Yashwant, Poonam").strip() or "Candidate"
    st.session_state["candidate_name"] = name

    if st.session_state["toast_shown_for"] != name:
        st.toast(f"CA {name} in the making", icon=None)
        st.session_state["toast_shown_for"] = name

    diets = next_diets()
    labels = [d.full_label for d in diets]
    choice = st.selectbox("Target exam diet", labels, index=0)
    diet = diets[labels.index(choice)]
    st.metric("Days to exam", days_remaining(diet.exam_date), help="Counted from today's system date.")
    st.caption("Exam window: 2:00 PM - 5:00 PM. Confirm dates on icai.org.")
    return Profile(name=name, diet=diet)
