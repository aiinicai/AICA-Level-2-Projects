# Salary TDS Calculator & Advisor
## Live Demo: [Access the TDS Calculator App](https://aica-level-2-projects-tds-calculator-app-piyush.streamlit.app/)
**AICA Level 2 Capstone Project**
Prepared by: CA Piyush Makkar (ICAI Membership No. 079490) — AICA Level 2, Batch 77

## Problem Statement

At client offices, employees routinely approach the finance/accounts team every
month asking the same question: *"how is my TDS on salary calculated?"* This
creates repeated, avoidable interruptions for the finance team and leaves
employees dependent on someone else to understand a deduction from their own
salary.

## What This App Does

A self-service Streamlit web app where any employee can:

- Enter their salary components, rent details, and investments
- Instantly see their monthly TDS computed under **both** the Old Regime and
  the New Regime (Section 202 of the Income Tax Act, 2025)
- View a visual dashboard comparing both regimes and their salary breakup
- Ask an **AI panel (powered by Claude)** to explain their own numbers in
  plain language — grounded strictly in the figures already computed, never
  invented
- Ask general, **educational-only** tax questions (e.g. how capital gains are
  taxed) in a separate FAQ tab, which is explicitly restricted from computing
  personal liability
- Download a report of their computation
- Ask questions by voice and hear answers read aloud, both running free of any extra API cost

## Why This Is "AI for CAs," Not Just a Calculator

The core tax computation is deterministic, rule-based logic — that alone
would just be a calculator. The AI layer built on top of it is what makes
this an AI-enabled solution:

1. An AI panel that explains *why* the numbers came out the way they did,
   using the employee's own computed figures as grounding context
2. A separate, clearly-labeled educational FAQ panel with a hard-coded
   restriction against computing personal tax liability — a deliberate
   design choice reflecting professional responsibility

## Section References (Income Tax Act, 2025)

| Provision | 1961 Act | 2025 Act |
|---|---|---|
| TDS on salary | Section 192 | Section 392 |
| Standard deduction | Section 16(ia) | Section 19 |
| HRA exemption | Section 10(13A) | Section 11 r/w Sec 19 & Sch. II |
| Home loan interest (self-occupied) | Section 24(b) | Section 22(2) |
| 80C investments | Section 80C | Section 123 r/w Schedule XV |
| NPS additional deduction | Section 80CCD(1B) | Section 124 |
| Health insurance premium | Section 80D | Section 126 |
| Default new regime | Section 115BAC | Section 202 |
| Rebate (nil tax threshold) | Section 87A | Section 156 |

## Tech Stack

- **Streamlit** — UI framework
- **Pandas / Plotly** — data handling and charts
- **AI explanation and FAQ panels** — provider-agnostic: works with either
  the **Anthropic Claude API** or the **Google Gemini API**, whichever key
  is configured (see "Running Locally" below). This deployment uses Claude.

## Project Structure

```
tds-calculator-app/
├── app.py                      # Main Streamlit app
├── requirements.txt            # Python dependencies
├── run_app.bat                 # Windows double-click launcher (optional shortcut)
├── utils/
│   ├── tax_engine.py           # Core tax computation logic
│   ├── ai_assistant.py         # Provider-agnostic AI integration (Claude or Gemini)
│   └── audio_helper.py         # Voice input/output (speech-to-text, text-to-speech)
└── .streamlit/
    └── config.toml             # Theme configuration
```

(`.streamlit/secrets.toml`, containing the API key, is intentionally excluded
from this repository — see "Running Locally" below.)

## Running Locally

```bash
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` with **either one** of the following (not
both required — the app auto-detects whichever is present, checking for
an Anthropic key first):
```toml
ANTHROPIC_API_KEY = "your-claude-key-here"
```
or
```toml
GEMINI_API_KEY = "your-gemini-key-here"
```

Then run:
```bash
streamlit run app.py
```

**Windows shortcut:** once `secrets.toml` is set up, double-click
`run_app.bat` instead of using the commands above — it installs
dependencies and launches the app automatically.

## Known Limitations / Future Scope

This version handles cash salary components — Basic, HRA, Special Allowance,
and Bonus. Perquisites such as rent-free accommodation, company cars, and
ESOPs are deliberately out of scope for this release, since Rule 15 of the
Income Tax Rules, 2026 prescribes distinct valuation methods for each
category. This is flagged as a planned enhancement for the next development
phase, once each valuation method can be built and tested independently.

## Privacy

This app does not use a database and does not persist any data — figures
entered by a user exist only for that browser session. The employee's name
field is entirely optional and is not required to compute TDS; leaving it
blank avoids attaching any identifying detail to the salary figures entered.

## Disclaimer

This tool is for illustration and self-service estimation only. It is not a
substitute for professional tax advice from a qualified Chartered Accountant.
