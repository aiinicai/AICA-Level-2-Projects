"""
Ledger Sentinel - ONE-CLICK Live Fraud Scan
---------------------------------------------
This is the "close the loop" script: run it once and it

  1. Pulls the Day Book LIVE from the running Tally Prime instance
     (via the exact same read-only export_daybook_to_excel() function
     defined in tally_mcp_server.py - strictly "Export Data" only, never
     writes anything to Tally),
  2. Scores every voucher it got back using the identical rules engine
     logic used on the full 7,765-voucher synthetic dataset, and
  3. Saves a ranked, flagged Excel file ready for an auditor to open
     and review - no manual steps in between.

This is the automation the live-integration stretch goal was always
aiming at: Tally -> MCP -> Rules Engine -> Auditor-ready Excel, in one
command, instead of separate export / upload / review steps.

Requirements: TallyPrime must be open with the company loaded, and the
company's XML/HTTP gateway must be enabled (same setup as every other
live step in Tally_MCP_Integration_SOP.docx).

Run with:
    C:\\Python314\\python.exe run_live_fraud_scan.py
"""

import sys
import pandas as pd
import tally_mcp_server as mcp_tools
from ledger_sentinel_rules import score_dataframe

FROM_DATE = "20260101"
TO_DATE = "20261231"
COMPANY_NAME = "Gulf Emirates Trading & Distribution LLC"
RAW_PULL_PATH = "live_daybook_export.xlsx"
FLAGGED_OUTPUT_PATH = "Live_Flagged_Vouchers.xlsx"
HIGH_RISK_THRESHOLD = 50

print("=" * 70)
print("STEP 1 of 2 - Pulling Day Book LIVE from Tally (read-only)")
print("=" * 70)
print(f"Date range: {FROM_DATE} to {TO_DATE}")
print(f"Company:    {COMPANY_NAME}\n")

import json
pull_result_raw = mcp_tools.export_daybook_to_excel(
    FROM_DATE, TO_DATE, RAW_PULL_PATH, COMPANY_NAME
)
pull_result = json.loads(pull_result_raw)

if "error" in pull_result:
    print("LIVE PULL FAILED:")
    print(pull_result_raw)
    print("\nCheck: is TallyPrime open with the company loaded, and is the")
    print("company's XML/HTTP gateway switched on? See Tally_MCP_Integration_SOP.docx.")
    sys.exit(1)

print(f"Pulled {pull_result['rows_written']} real vouchers from Tally.")
print(f"Saved raw pull to: {RAW_PULL_PATH}")
print(f"Limitation note: {pull_result['limitation_note']}\n")

if pull_result["rows_written"] == 0:
    print("No vouchers came back - nothing to score. Stopping here.")
    sys.exit(0)

print("=" * 70)
print("STEP 2 of 2 - Scoring every pulled voucher with the rules engine")
print("=" * 70)

df = pd.read_excel(RAW_PULL_PATH)
scored = score_dataframe(df)
scored.to_excel(FLAGGED_OUTPUT_PATH, index=False, engine="openpyxl")

total = len(scored)
flagged = int((scored["risk_score"] > 0).sum())
high_risk = int((scored["risk_score"] >= HIGH_RISK_THRESHOLD).sum())
avg_score = round(scored["risk_score"].mean(), 1) if total else 0.0

print(f"\nSaved flagged, ranked results to: {FLAGGED_OUTPUT_PATH}\n")
print("--- Summary ---")
print(f"Total vouchers scored:        {total}")
print(f"Flagged (risk_score > 0):     {flagged}")
print(f"High risk (risk_score >= {HIGH_RISK_THRESHOLD}): {high_risk}")
print(f"Average risk score:           {avg_score}")

if flagged:
    print("\n--- Flagged entries needing auditor attention ---")
    top = scored[scored["risk_score"] > 0].head(20)
    for _, r in top.iterrows():
        print(f"  #{r['rank']:>3}  {r['voucher_id']}  {r['date']}  "
              f"{r['debit_account']} -> {r['credit_account']}  "
              f"AED {r['amount']:,}  score={r['risk_score']}")
        print(f"        reasons: {r['reasons']}")
else:
    print("\nNo entries were flagged in this live pull.")

# Rule 11 - the separate vendor structured-disbursement screen (see
# ledger_sentinel_rules.py). score_dataframe() always computes this; it
# only has something to say if this Tally company's chart of accounts has
# per-vendor ledgers named "Accounts Payable - <vendor>" (see
# generate_data.py) AND enough history per vendor to form a baseline - a
# short live pull from a fresh/demo company may show nothing here even
# when everything is working correctly.
vendor_flagged = scored[scored["vendor_flag_score"] > 0]
print(f"\n--- Rule 11: vendor structured-disbursement screen ---")
if len(vendor_flagged):
    print(f"{len(vendor_flagged)} voucher(s) flagged - a vendor is receiving an unusual")
    print("cumulative total relative to its own earlier activity:")
    for _, r in vendor_flagged.iterrows():
        print(f"  {r['voucher_id']}  {r['date']}  score={r['vendor_flag_score']}")
        print(f"    {r['vendor_flag_reason']}")
else:
    print("No vendor-level structuring pattern detected in this pull (or this")
    print("company's chart of accounts doesn't have per-vendor ledgers yet, or")
    print("there isn't enough history per vendor to establish a baseline).")

print("\nDone. Open Live_Flagged_Vouchers.xlsx, or upload it into the")
print("Streamlit dashboard (streamlit run app_streamlit.py) to review visually.")
