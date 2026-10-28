"""Settings & AI: the Gemini key, model and consent, set once for every tool."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fsbuilder.reviewer import llm as llm_module  # noqa: E402
from ui import ai, theme  # noqa: E402

theme.header("Settings & AI", "Set the Gemini key once. Every tool in LedgerLens uses it.", "⚙️")
ss = st.session_state

st.subheader("Gemini API key")
key0, model0, _ = ai.config()
c1, c2 = st.columns([3, 2])
key = c1.text_input("API key", value=ss.get(ai.KEY, ""), type="password", placeholder="Paste your key, or leave blank to use the .env file",
                    help="Held in this browser session only. It is never saved by the app and never put in the files it writes.")
model = c2.text_input("Model", value=ss.get(ai.MODEL, "") or model0, help="Leave as is unless you want a specific Gemini model.")
consent = st.checkbox("I understand the data listed below is sent to Google's Gemini API when I run an AI feature.",
                      value=bool(ss.get(ai.CONSENT)))
ss[ai.KEY], ss[ai.MODEL], ss[ai.CONSENT] = key.strip(), model.strip(), consent

k, m, ok = ai.config()
l, r = st.columns([1, 3])
with l:
    ai.badge()
r.caption(f"Key source: {ai.source()}.")
st.caption("To avoid pasting the key each time, put `GEMINI_API_KEY=your_key` in the `.env` file in the project folder "
           "(already ignored by git) and restart the app.")

if st.button("Test the connection", disabled=not k):
    try:
        with st.spinner("Asking Gemini..."):
            reply = llm_module.GeminiLLM(k, m)('Reply with JSON only.', 'Return exactly {"ok": true}')
        st.success("Connected. The model answered.") if "true" in reply.lower() else st.warning(f"Connected, but the reply was unexpected: {reply[:120]}")
    except Exception as e:
        st.error(f"Could not connect: {e}")

st.subheader("Where the AI is used")
st.dataframe([
    {"Feature": "Ratio explanations", "Tool": "Financial Statements Builder", "What is sent": "Summary figures and labels, never ledger or party names",
     "Without a key": "Left as 'explanation required' for management"},
    {"Feature": "Analytical observations", "Tool": "Financial Statements Builder", "What is sent": "The same summary figures, each with an ID the model must cite",
     "Without a key": "Not run; the deterministic checks still run"},
    {"Feature": "Narration and voucher review", "Tool": "Day Book Audit", "What is sent": "For the vouchers you choose: ledger names, amounts and narrations",
     "Without a key": "Not run; the rule tests (including narration themes) still run"},
], hide_index=True, width="stretch")
st.caption("The model never writes the figures you see. It cites numbered facts and the app inserts the real figure; "
           "anything uncited or invented is labelled for checking.")

st.subheader("Getting the most from it")
st.markdown(
    "- **Day Book:** run the AI review on your largest vouchers after the rule tests. Rules catch known patterns; the model "
    "reads the narration against the ledger and catches things like a laptop booked as repairs.\n"
    "- **Statements:** run it last. It drafts the explanation Schedule III requires for ratios that move more than 25%, "
    "and raises points to ask the client.\n"
    "- **Keep the rule tests on.** They are the evidence; the AI only adds leads.")
