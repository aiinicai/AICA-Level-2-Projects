"""Home: what LedgerLens does and where to start."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui import ai, theme  # noqa: E402

st.markdown(f"""
<div class="ll-hero">
  <h1>{theme.APP_NAME}</h1>
  <p>{theme.TAGLINE}</p>
  <span class="ll-chip">Trial balance to Schedule III</span>
  <span class="ll-chip">Statements linked to their notes</span>
  <span class="ll-chip">Day Book red-flag tests</span>
  <span class="ll-chip">Reviewer's report</span>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("""<div class="ll-card"><h3>Financial Statements Builder</h3>
<p>Upload the trial balance exactly as Tally exports it. Get the Balance Sheet, Profit and Loss, AS 3 cash flow and
numbered notes in Word and Excel, with every figure linked to its note, plus a reviewer's report: casting and tie-outs,
the 11 Schedule III ratios, and a disclosure checklist.</p></div>""", unsafe_allow_html=True)
    theme.safe_link("ui/statements.py", "Open Financial Statements Builder", ":material/description:")
with c2:
    st.markdown("""<div class="ll-card"><h3>Day Book Audit</h3>
<p>Upload the Day Book. Cash limits, TDS and GST slips, duplicates, amounts that sit just under a limit (the 999 test),
repeated amounts, a Benford screen, and narrations that mention fraud, bribes, penalties, gifts, donations, suspense or
"as instructed".</p></div>""", unsafe_allow_html=True)
    theme.safe_link("ui/day_book.py", "Open Day Book Audit", ":material/fact_check:")

st.markdown("### How it works")
a, b, c = st.columns(3)
a.markdown("**1. Bring your books**  \nA trial balance or Day Book exported from Tally, or a sample to try the tool first.")
b.markdown("**2. Check what it decided**  \nEvery judgement call is marked for you to confirm or override. Nothing is hidden.")
c.markdown("**3. Take the files**  \nWord and Excel, ready to review. Information Tally cannot hold is listed, never invented.")

left, right = st.columns([3, 2])
with left:
    st.markdown("### What it is, and is not")
    st.markdown(
        "- A **drafting and review aid**. It produces draft statements and exception lists for a person to review; it is "
        "not an audit opinion.\n"
        "- Rules and arithmetic run **on this computer**. Casting, tie-outs, ratios and the Day Book tests are plain, "
        "reproducible code.\n"
        "- **AI is optional** and only drafts wording or raises leads. Anything it writes is labelled and must be checked.\n"
        "- Statutory references and thresholds are as understood for FY 2025-26; the Income-tax Act, 2025 renumbers "
        "sections from FY 2026-27, so verify before relying on them.")
with right:
    st.markdown("### AI status")
    ai.badge()
    st.caption("Set the Gemini key once on the Settings page and every tool uses it.")
    theme.safe_link("ui/settings.py", "Settings & AI", ":material/tune:")
