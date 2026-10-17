# Ledger Sentinel — AICA Level 2 Capstone Project

AI-assisted journal-entry fraud screening for Tally Prime data.
Prepared by Rupalakshmi for ICAI AICA Level 2.

## The 11 rules

10 single-entry red flags, each scored independently and combined into one weighted `risk_score`, plus one aggregate rule (Rule 11) reported as its own separate flag, never blended in. All 11 live in `ledger_sentinel_rules.py`.

| # | Rule | Weight | What it catches |
|---|---|---|---|
| 1 | Weekend / after-hours posting | 1.1 | Entry posted on Fri/Sat and/or 20:00–05:00 |
| 2 | Near period end | 1.2 | Posted within 5 days of year-end, or altered after it ("post-closing entry") |
| 3 | Round amount | 1.1 | Round-thousand amount, especially to Suspense/Misc Expense |
| 4 | Near approval limit | 1.1 | Amount sits just under the AED 25,000 approval threshold |
| 5 | Rare account pair | 0.5 | Debit/credit account combination used in ≤0.2% of all vouchers |
| 6 | Vague narration | 0.7 | Narration is blank, "N/A", "Entry", "Adjustment", etc. |
| 7 | Duplicate pattern | 1.2 | Same user/accounts/amount-band repeated — possible double claim |
| 8 | Same user create/alter | 1.3 | Same person created AND altered the entry — no segregation of duties |
| 9 | Old voucher late edit | 1.4 | Altered 60+ days after the original posting date |
| 10 | Vendor bank-detail change | 1.3 | Narration flags a bank-detail change ahead of a large payment |
| **11** | **Vendor structured-disbursement screen** | *separate flag, not weighted in* | One vendor's rolling 270-day payment total runs >2x above that vendor's own 60-day baseline rate — catches a payment deliberately split into many small, individually-unremarkable entries over months. See "Vendor ledgers and Rule 11" below. |

## What's in this folder

| File | What it is |
|---|---|
| `SOP_and_Audit_Trail.docx` | **Start here.** Standard Operating Procedure for running the project, plus how to keep an audit trail for the project itself. |
| `Ledger_Sentinel_Explained_Simply.docx` | The whole project explained in plain language — good background reading or for a non-technical examiner. |
| `Master_Capstone_Prompt.docx` | The complete build spec, written as a single prompt. Use this to rebuild the project from scratch with any AI assistant, or as your methodology write-up. |
| `generate_data.py` | Step 1: generates the synthetic company data with planted fraud, including a realistic per-vendor chart-of-accounts structure (see "Vendor ledgers and Rule 11" below). |
| `tally_daybook_export.xlsx` | The "input" file — 7,778 vouchers, no fraud labels. This is what the tool processes. |
| `fraud_answer_key.xlsx` | Hidden answer key — 278 planted fraud entries across 9 fraud types. **Read-only. Only used to score results, never fed into detection.** |
| `ledger_sentinel_rules.py` | The 10 weighted single-entry red-flag rules, PLUS Rule 11 (the vendor structured-disbursement screen), and the scoring function — shared by `rules_engine.py`, `run_live_fraud_scan.py` and `app_streamlit.py` so every interface scores identically. |
| `rules_engine.py` | Step 2: runs the rules engine on `tally_daybook_export.xlsx`, ranks every voucher, runs the separate Rule 11 vendor screen, and validates both against the hidden answer key. |
| `risk_scored_vouchers.xlsx` | Output of the rules engine — all 7,778 vouchers ranked by `risk_score` (the 10 single-entry rules), plus a separate `vendor_flag_score` / `vendor_flag_reason` pair of columns for Rule 11. |
| `ai_explainer.py` | Step 3: AI explanation layer. Explains the top-ranked entries by `risk_score`, UNION any voucher Rule 11 flagged — so a structuring payment that ranks low on `risk_score` by design still gets written up. |
| `Auditor_Working_Paper.xlsx` | Output of the AI layer — the top entries by risk score plus every Rule 11 vendor flag, with explanations, follow-up questions, and sign-off columns for your reviewer. |
| `app_streamlit.py` | Step 4: interactive dashboard. Run locally with Streamlit. Shows the ranked list, the Rule 11 vendor screen as its own section, and Benford's Law — three independent views, not blended into one score. |
| `tally_mcp_server.py` | Step 10 (stretch goal): live, read-only MCP integration — pulls the Day Book directly from a running Tally Prime instance. **Verified live on 2026-10-15 (see below).** |
| `import_ledger_masters.py` | One-time seed script: pushes the chart-of-accounts ledgers — including one ledger per vendor — into a Tally company, so it can accept the synthetic vouchers. Run once, before the voucher import. |
| `import_vouchers_to_tally.py` | One-time seed script: pushes `tally_daybook_export.xlsx` into Tally as real "Journal" vouchers, for a genuine live demo. Safe to re-run (skips vouchers already present). |
| `pull_live_daybook.py` | Calls the real `export_daybook_to_excel()` function from `tally_mcp_server.py` directly, saving a live Day Book pull to `live_daybook_export.xlsx`. |
| `live_daybook_export.xlsx` | A real, live pull from Tally captured during verification — evidence the round trip genuinely works end to end. |
| `run_live_fraud_scan.py` | **The one-click version of the live integration.** Pulls the Day Book live from Tally *and* scores it with the rules engine (including Rule 11) *and* writes a ready-to-review Excel file, all in a single command. See below. |
| `Live_Flagged_Vouchers.xlsx` | Output of `run_live_fraud_scan.py` — real, live-pulled vouchers, ranked and flagged, from the 2026-10-15 closing re-verification. |
| `Tally_MCP_Integration_SOP.docx` | Exact, ordered, step-by-step SOP for setting up and running the Tally ↔ MCP live integration — written from an actual verified run, not a theoretical one. |
| `requirements.txt` | Python packages needed to run everything. |

## How to run it yourself

```bash
pip install -r requirements.txt

# 1. Generate fresh synthetic data (optional — the files above are already generated)
python generate_data.py

# 2. Run the rules engine
python rules_engine.py

# 3. Generate the AI-explained working paper
python ai_explainer.py

# 4. Launch the live dashboard
streamlit run app_streamlit.py
```

`ai_explainer.py` works with **zero configuration** (it uses a built-in template). To use real AI explanations instead:

- **Local, private (recommended for the demo):** install [LM Studio](https://lmstudio.ai), load a model, start its local server, then set:
  `set LM_STUDIO_URL=http://localhost:1234/v1` (Windows) before running the script.
- **Cloud (Claude API):** set `ANTHROPIC_API_KEY=your-key-here` before running the script.

## Vendor ledgers and Rule 11 — catching structuring, not just single bad entries

Every rule up to this point looks at **one voucher at a time**. That's a real gap: a dishonest insider with posting access can split a large, deliberate payment into many individually-small, individually-unremarkable entries to one destination, spread across months — never tripping a threshold, never looking round, never posted at an odd hour. None of the 10 single-entry rules can ever catch this, by construction, however they're tuned.

Rule 11 closes that gap by watching the **cumulative total paid to each vendor ledger over time**, not single entries:

- The chart of accounts now gives **every vendor its own ledger** (`Accounts Payable - <Vendor Name>`), matching how a real TallyPrime company is actually set up — not a single shared generic payable account, which would make vendor-level analysis impossible.
- For each vendor, Rule 11 compares its **trailing 270-day rolling total** against that *same vendor's own* early-period baseline (its first 60 days of activity). If the rolling total runs more than 2x that baseline rate, the voucher that pushed it over the line is flagged, with a score that rises the further past the threshold it goes.
- The result (`vendor_flag_score`, `vendor_flag_reason`) is reported as its **own, separate flag** — never blended into `risk_score`. An earlier prototype proved why: folding a vendor-level signal into the same weighted average as 10 single-entry rules drowns it out (it measured rank 414 of 7,778 despite firing correctly). Shown separately, like Benford's Law, it stays visible instead of being averaged away.

**Proof, planted and tested on this dataset:** a 13-payment structuring scenario (AED 9,000–19,500 each, spread May–November, to a single vendor ledger) was planted and scored:
- The 10 single-entry rules alone: **0 of 13 caught** — confirming the gap is real, not theoretical.
- Rule 11: **10 of 13 caught**, with **zero false positives** against the 15 other, genuinely busy vendor ledgers in the file.
- The 3 missed are the earliest payments in the sequence, before the rolling total had risen far enough above baseline to cross the threshold — an honest, expected limitation of any ramp-up detector, not a bug.

**Honest limitation:** this design only works because the synthetic dataset spans a full year with a genuine quiet period before the structuring begins, giving Rule 11 a clean early baseline to compare against. A real engagement starting mid-stream would need at least a full prior year of a vendor's history before Rule 11 can calibrate a baseline for it — this is stated plainly, not glossed over.

## Results summary (already generated, in `risk_scored_vouchers.xlsx`)

Tested against the hidden answer key, with a fully reproducible ranking (see the methodology note below):

- **57.9% of planted fraud caught unambiguously by the 10 single-entry rules** — 161 of 278, from 165 vouchers that score clearly above the noise floor, with only 4 false positives.
- **Up to 72.3% if a large tied/borderline score band is also reviewed** — 201 of 278, from 328 flagged vouchers (163 of them tied on one exact score). In an engagement, the unambiguous 161 go straight to the working paper; the extra 163 are a batch for the auditor to review separately, not a number to silently include or exclude.
- **Rule 11 adds 10 more catches with zero false positives** — all 10 are structuring payments the single-entry rules missed entirely, so they're pure upside, not overlap.
- **Combined: 61.5% (unambiguous tier + Rule 11) to 75.9% (borderline tier + Rule 11).**
- **6 of 9 fraud types caught at a perfect 100%** once the borderline band is included — 5 of those (backdated, round-to-suspense, same-user, old-voucher-edit, vendor-bank-detail) hit 100% unambiguously; the 6th (amount just under approval limit) lands entirely inside the borderline band itself (0% unambiguous → 100% inclusive), so it needs that band reviewed to reach 100%.

Full breakdown by fraud type, and the honest discussion of the weaker-performing types, is in `SOP_and_Audit_Trail.docx`, Section 6.

> **Methodology note:** an earlier version of the ranking used an unstable sort, so re-running the scorer on identical data could report different catch rates purely from how tied vouchers happened to land relative to a hard cutoff — not from any real difference in detection. This is fixed: `ledger_sentinel_rules.py` breaks ties deterministically (risk score, then voucher ID), so the ranking is reproducible. The numbers above were independently re-verified by running the full pipeline three times on freshly regenerated data with identical results each time.

## Suggested presentation flow

1. Hook: "Fraud hides in entries nobody looks at — and some fraud is deliberately designed so no single entry ever looks wrong."
2. Problem: sampling misses things (SA 240 context); and a patient insider can structure a payment to beat any single-entry threshold.
3. Live demo: upload `tally_daybook_export.xlsx` into the Streamlit app, show the ranked list, the red flags, and the separate Rule 11 vendor screen catching the structuring pattern the ranked list missed.
4. Results: ~58% of fraud caught unambiguously by the single-entry rules, up to 72% including a borderline band, plus 10 more structuring catches from Rule 11 with zero false positives — 100% on 6 of 9 fraud types — shown honestly, including what was missed and why.
5. Limitations and ethics: rules prioritise for human review, they don't prove fraud; the AI only explains, never decides; Rule 11 needs a real baseline period to work.
6. Next steps: expanding the rule set, tuning thresholds with a real client's actual approval limits, giving Rule 11 a full prior year of history in a live engagement, and extending the live Tally MCP integration's audit-log coverage.

## Live Tally integration (Step 10, stretch goal) — VERIFIED LIVE 2026-10-15, RE-VERIFIED 2026-10-15

`tally_mcp_server.py` lets Claude pull the Day Book directly from a running Tally Prime instance instead of a manual Export > Excel step — strictly read-only (it only ever sends "Export Data" requests, never "Import Data"). Full, exact setup and verification steps are in `Tally_MCP_Integration_SOP.docx`.

This was tested end to end against a real TallyPrime instance ("Gulf Emirates Trading & Distribution LLC", an EDU/practice company):

1. Chart-of-accounts ledgers pushed into Tally (`import_ledger_masters.py`), including the per-vendor payable ledgers — all created, zero errors.
2. Synthetic vouchers pushed into Tally as real "Journal" entries (`import_vouchers_to_tally.py`).
3. Day Book pulled back live through the exact logic in `tally_mcp_server.py` (`pull_live_daybook.py`) — real XML parsed, real rows recovered into `live_daybook_export.xlsx`.
4. That live-pulled file uploaded into the Streamlit dashboard — real flagged entries appeared (e.g. two genuine "near approval limit" vouchers, correctly scored from live data the rules engine had never seen before).

**Then closed out with the one-click version:** `run_live_fraud_scan.py` combines steps 3 and the scoring step — including Rule 11 — into a single command: pull, score, and write a ready-to-review Excel file, no manual upload step. Re-run live on 2026-10-15: 76 vouchers pulled, all 76 flagged — but explained honestly, not alarming. Every one of the 76 happened to be dated 31-Dec (year-end), which trips the "near period end" rule on all of them (scores 7.7–15.8, none high-risk); the earlier verification run the same day returned a different 72-row slice dated 1-Jan instead. Both are genuine samples of whatever Tally's row-export cap happens to return on a given call. Rule 11 correctly reported nothing on either slice — too short a pull, and too few vendor ledgers represented, to form a baseline, which is exactly the honest limitation documented above.

**What this proved, and what it didn't:**
- The connection, request format, and read/write round trip to a real Tally instance are all genuinely working — not theoretical. The full chain (Tally → MCP → Rules Engine (10 rules + Rule 11) → auditor-ready Excel) now runs as one command.
- TallyPrime's Educational edition appears to cap how many vouchers can be created per day, independent of request size (a repeatable ~624-created result was observed across two full-dataset import attempts). This is a license-tier limit, not a bug in the integration. It also appears to cap how many rows a single report export returns (72 rows one call, 76 another) — a separate, variable ceiling, not a data-integrity issue.
- The standard Day Book export does **not** include `altered_by` / `altered_date` / exact `time`, so on live-pulled data only the rules that depend on amount, narration, accounts and date can fire correctly (e.g. near-approval-limit, round-amount, vague-narration, rare-account-pair, near-period-end). The rules needing user/edit-log fields (weekend/after-hours, duplicate pattern, same-user create/alter, old-voucher late-edit) will under-fire on live data until a version-specific audit-log export is added — state this openly if you demo it live. Rule 11 needs enough live-pulled history per vendor to form a baseline, which a short demo pull won't have.
- TallyPrime's XML responses contain characters that are technically invalid under the XML spec (both raw control bytes and literal `&#N;` references); `tally_mcp_server.py` now sanitizes these before parsing.
