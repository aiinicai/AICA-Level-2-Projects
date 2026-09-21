"""Presentation helpers. All document-derived HTML is escaped before rendering."""
from html import escape
from pathlib import Path
import streamlit as st
from utils.helpers import deadline_label


def apply_styles() -> None:
    css = (Path(__file__).resolve().parents[1] / "assets" / "styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_header(has_analysis: bool) -> None:
    st.markdown('''<div class="brandbar"><div class="brand-lockup"><div class="monogram" aria-hidden="true">VJ</div><div><div class="brand-name">1-Click Tax Notice Decoder</div><div class="brand-author"><strong>Vaibhav Jain</strong> · Chartered Accountant</div></div></div><span class="edition">THE CA WORKSPACE</span></div>
<section class="hero"><div class="hero-kicker"><span class="light-dot" aria-hidden="true"></span>AI-assisted Income Tax &amp; GST Notice Analysis</div><h1>Decode any Tax Notice<br>in <mark>seconds.</mark></h1><p>Upload an Income Tax or GST notice. Get the allegations, sections, deadline and a professionally drafted reply.</p><div class="hero-tags"><span>Income Tax</span><span>GST</span><span>Editable Word reply</span></div></section>''', unsafe_allow_html=True)
    steps = [("01", "Upload notice"), ("02", "Understand the issues"), ("03", "Client documents"), ("04", "Applicable law"), ("05", "Case law"), ("06", "Response strategy"), ("07", "Review your reply")]
    active = 0 if not has_analysis else 2
    if has_analysis and st.session_state.get("case_files"):
        active = 3
    if st.session_state.get("case_research"):
        active = 5
    if st.session_state.get("case_strategy"):
        active = 6
    html = '<div class="step-rail" aria-label="Notice workflow">'
    for index, (number, label) in enumerate(steps):
        state = "done" if index < active else ("active" if index == active else "")
        html += f'<div class="step {state}"><span class="step-index">{number}</span><span>{label}</span></div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)


def render_metadata(metadata: list[tuple[str, str | None]]) -> None:
    cells = ''.join(f'<div class="meta-item"><small>{escape(label)}</small><strong>{escape(value)}</strong></div>' for label, value in metadata if value)
    if cells:
        st.markdown(f'<div class="meta-grid">{cells}</div>', unsafe_allow_html=True)


def render_deadline(deadline) -> None:
    if deadline.exact_date:
        label, severity = deadline_label(deadline.exact_date)
        state = "critical" if severity == "error" else ""
        st.markdown(f'<div class="deadline {state}"><div><small>Reply Due</small><strong>{escape(deadline.exact_date.strftime("%d %B %Y"))}</strong></div><span class="deadline-status">{escape(label)}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="deadline"><div><small>Response deadline</small><strong>Requires verification</strong></div></div>', unsafe_allow_html=True)
        st.text(deadline.deadline_text or "No response deadline could be identified. Check the original notice.")
        if deadline.deadline_text:
            st.caption("An exact due date could not be established. Verify any receipt/service date and response-period wording before filing.")


def render_summary(items: list[str]) -> None:
    rows = ''.join(f'<div class="summary-item"><b>{index:02d}</b><span>{escape(item)}</span></div>' for index, item in enumerate(items[:6], 1))
    st.markdown(f'<div class="summary-list">{rows}</div>', unsafe_allow_html=True)


def render_issue_heading(index: int, title: str) -> None:
    st.markdown(f'<div class="issue-title"><span>{index:02d}</span>{escape(title)}</div>', unsafe_allow_html=True)


def render_amount(amount: str) -> None:
    st.markdown(f'<div class="amount-line">Amount involved <mark>{escape(amount)}</mark></div>', unsafe_allow_html=True)


def render_section(text: str) -> None:
    st.markdown(f'<span class="section-pill">{escape(text)}</span>', unsafe_allow_html=True)
