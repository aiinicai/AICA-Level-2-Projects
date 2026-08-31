# Personal Finance & Debt Impact Calculator

**AICA Level 2 — Capstone Project**
Author: CA Parth Mody · Version 2.6

A deterministic personal-finance engine that answers one question honestly:
**which of your loans are worth keeping, and which are destroying value?**

It amortises every loan month by month, computes each one's effective post-tax
cost, and judges it against what the same money could actually earn over that
loan's own remaining life — after tax and after a risk haircut. It then projects
income, expenses, goals and net worth across a 3–30 year horizon.

Everything runs locally. No data leaves the machine.

---

## Running it

### Option 1 — the packaged Windows app (no Python needed)

**[Download FinancePlanner.zip](https://github.com/parthmody14-code/AICA-Level-2-Projects/releases/download/v2.6/FinancePlanner.zip)** (128 MB) — or browse the
[release page](https://github.com/parthmody14-code/AICA-Level-2-Projects/releases/tag/v2.6) — then extract it and run
`FinancePlanner\FinancePlanner.exe`.

Requires 64-bit Windows 10/11. Nothing is installed; delete the folder to remove
it. Keep the console window open while using the app — it is the engine. The
browser opens automatically at `http://localhost:8501`.

> The exe is unsigned, so Windows SmartScreen shows "Windows protected your PC"
> on first run — choose **More info → Run anyway**. Extract the **whole** zip:
> the exe needs the `_internal` folder beside it.

Verify any copy is intact with:

```
FinancePlanner.exe --selftest
```

which runs the engine, all eight audit identities and the Excel export.

### Option 2 — from source

```bash
pip install -r requirements.txt
streamlit run Finance.py
```

Python 3.10+. Running `python Finance.py` directly also works — it installs any
missing dependencies and opens the browser itself.

---

## What it does

**Debt.** A full monthly amortisation schedule per loan. Converts flat/add-on
rates to their true reducing-balance equivalent (a "9% flat" car loan is really
about 16.5%). Applies Section 24(b), 80E and business-interest shields to get an
effective post-tax cost, and flags loans worth refinancing.

**The verdict.** Each loan's post-tax cost is compared against the risk-adjusted,
post-tax return your money could earn *over that loan's own remaining life*.
Capital-gains tax is charged once at exit, as it really is — not annually — and
the volatility haircut is scaled by the decision horizon, because the spread of
an annualised outcome narrows with the square root of time. This is why a cheap,
long, secured loan reads as healthy leverage while a card balance does not.

**Goals.** Inflated at their own rate to a future cost, funded from a sinking
fund. New borrowing is capped by your EMI-to-income ceiling, so a goal is never
marked ON TRACK on the strength of debt you could not service. Replacement
purchases are modelled properly: the asset being replaced is sold, the loan
secured on it is settled from the proceeds, the freed EMI restores borrowing
capacity *before* the new loan is sized, and what you buy is capitalised onto the
balance sheet. Section 54 rollover is applied on a home-to-home upgrade.

**Every rupee is traced.** For each goal the report names every source drawn on —
which holding, its class, gross realised, the tax and exit load paid on the way,
and what actually reached the goal.

**Excel round-trip.** Download a pre-filled input template with dropdowns and a
notes row explaining every column, fill it offline, upload it back. The report
exports as a formatted workbook with native charts, one amortisation sheet per
loan, and a full goal-funding detail sheet.

**Audit.** Eight arithmetic identity tests run on the engine's own output and are
shown to you, so the numbers do not have to be taken on trust:

| Test |
|---|
| Loan ledger: Opening − Principal − Prepayment = Closing |
| Loan totals: Opening − Closing = Principal + Prepayments |
| Monthly cash: inflows = outflows |
| Emergency fund: Open + Interest + Top-up − Drawdown = Close |
| Goal corpus: Open + Growth + Funding − Drawn = Close |
| Portfolio: Open + Growth + Contributions − Redemptions = Close |
| Net worth = Assets + EF + Goal corpus − Debt |
| Goals: Funded + Shortfall = Inflated cost |

---

## Files

| File | Purpose |
|---|---|
| `Finance.py` | The entire application — engine, UI, Excel I/O, audit |
| `launcher.py` | Entry point for the packaged build |
| `FinancePlanner.spec` | PyInstaller build specification |
| `requirements.txt` | Runtime dependencies |
| `DEVELOPMENT_LOG.md` | Defects found and fixed, with evidence, v2.1 → v2.6 |

Rebuild the Windows application with:

```bash
pip install pyinstaller
pyinstaller FinancePlanner.spec --noconfirm
```

---

## What this engine does not do

It does not forecast markets. Returns are **your** inputs compounded
deterministically — a 12% equity assumption held for ten years is an assumption,
not a fact, and the risk haircut exists to keep it honest.

It does not compute income tax; you enter post-tax figures. It applies no
statutory contribution caps (PPF ₹1.5 lakh a year, for instance). It assumes you
never miss a payment.

Section 54 relief is modelled as a simple full rollover to the extent reinvested;
the real provision has holding-period, timing and one-house conditions. A
replacement purchase is assumed to complete in a single month, with no bridging
finance and no rent in between.

The tax layer is a **planning simplification**. Before executing any large
redemption, have the actual gain and holding period computed by your CA — the
difference between short and long-term treatment alone can move the answer
materially.
