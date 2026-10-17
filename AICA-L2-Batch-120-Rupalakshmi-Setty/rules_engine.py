"""
Ledger Sentinel - Rules Engine (Step 6 & 7)
Scores every voucher in tally_daybook_export.xlsx against 10 single-entry
red-flag rules drawn from SA 240 journal-entry testing guidance, PLUS Rule
11 (a vendor-level aggregate rule - see ledger_sentinel_rules.py), combines
the 10 single-entry rules into one weighted risk score, ranks entries, and
(for build/test purposes only) checks the result against
fraud_answer_key.xlsx to report catch rate and false positives.

In a real engagement you would NOT have the answer key - that file only
exists here because this is synthetic/planted data for the capstone demo.

The actual rule definitions live in ledger_sentinel_rules.py, shared with
run_live_fraud_scan.py so the full-dataset run and the live-Tally run score
vouchers with identical logic.

NOTE on methodology (found and fixed during live-test closeout):
A simple "take the top N ranked entries" cutoff (N = number of planted
fraud, chosen for a clean read) is unreliable whenever many vouchers land
on the exact same risk score straddling that cutoff line - which rounded
rule weights made very likely on this dataset. This script reports catch
rate honestly in two tiers instead: vouchers that clear the cutoff
UNAMBIGUOUSLY (strictly above the tied score), and the rate if the full
tied/borderline band is also included. Ties within each tier are still
broken deterministically (risk_score desc, then voucher_id asc) inside
score_dataframe(), so the Excel ranking itself is reproducible - this is
purely about how the catch-rate *summary* is reported.

NOTE on Rule 11 (added after a live walkthrough of what a seasoned insider
with admin access could get away with): the 10 rules above only ever look
at one voucher at a time, so a payment deliberately kept small, non-round
and unremarkable - split across many months to one destination - is
invisible to all of them, BY DESIGN. Rule 11 catches this by watching the
cumulative total paid to one vendor ledger over time, relative to that
vendor's own baseline. It is reported SEPARATELY below, never folded into
risk_score, because blending a powerful relationship-level signal into the
same weighted average as 10 single-entry rules drowns it out (an earlier
prototype measured this directly - it reached rank 414 of 7,778 even while
firing correctly). The combined totals below show what the ranked list
plus the vendor-flag screen catch TOGETHER.
"""

import pandas as pd
from ledger_sentinel_rules import score_dataframe

IN_PATH = "tally_daybook_export.xlsx"
ANSWER_KEY_PATH = "fraud_answer_key.xlsx"

df = pd.read_excel(IN_PATH)
scored = score_dataframe(df)
scored.to_excel("risk_scored_vouchers.xlsx", index=False, engine="openpyxl")

TOP_N = (pd.read_excel(ANSWER_KEY_PATH)["is_fraud"] == 1).sum()  # = total fraud planted

# ---------------------------------------------------------------------------
# Validation against the hidden answer key (BUILD/TEST ONLY)
# ---------------------------------------------------------------------------
answer = pd.read_excel(ANSWER_KEY_PATH)
merged = scored.merge(answer, on="voucher_id")
total_fraud = answer["is_fraud"].sum()

# The score value sitting exactly at the TOP_N cutoff line
cutoff_score = merged.sort_values("risk_score", ascending=False).iloc[TOP_N - 1]["risk_score"]
tie_band = merged[merged["risk_score"] == cutoff_score]

unambiguous = merged[merged["risk_score"] > cutoff_score]
inclusive = merged[merged["risk_score"] >= cutoff_score]

print(f"Total vouchers scored: {len(scored)}")
print(f"Total planted fraud entries: {total_fraud}  (9 distinct fraud types)")
print(f"\nScore value sitting at the top-{TOP_N} cutoff line: {cutoff_score}")
print(f"Vouchers tied on that exact score (the 'borderline band'): {len(tie_band)}")

print(f"\n--- Tier 1: UNAMBIGUOUS flags, from the 10 single-entry rules (score > {cutoff_score}) ---")
caught_u = set(unambiguous[unambiguous["is_fraud"] == 1]["voucher_id"])
fp_u = len(unambiguous) - len(caught_u)
print(f"Flagged: {len(unambiguous)} | Fraud caught: {len(caught_u)}/{total_fraud} "
      f"({len(caught_u)/total_fraud*100:.1f}%) | False positives: {fp_u} "
      f"({fp_u/len(unambiguous)*100:.1f}% of flagged)" if len(unambiguous) else "Flagged: 0")

print(f"\n--- Tier 2: INCLUDING the borderline band, 10 single-entry rules (score >= {cutoff_score}) ---")
caught_i = set(inclusive[inclusive["is_fraud"] == 1]["voucher_id"])
fp_i = len(inclusive) - len(caught_i)
print(f"Flagged: {len(inclusive)} | Fraud caught: {len(caught_i)}/{total_fraud} "
      f"({len(caught_i)/total_fraud*100:.1f}%) | False positives: {fp_i} "
      f"({fp_i/len(inclusive)*100:.1f}% of flagged)")

# ---------------------------------------------------------------------------
# Rule 11 - the separate vendor-level structuring screen
# ---------------------------------------------------------------------------
vendor_flagged = merged[merged["vendor_flag_score"] > 0]
caught_r11 = set(vendor_flagged[vendor_flagged["is_fraud"] == 1]["voucher_id"])
fp_r11 = len(vendor_flagged) - len(caught_r11)
print(f"\n--- Rule 11: vendor structured-disbursement screen (separate from the ranked list) ---")
print(f"Vendor ledgers flagged on: {vendor_flagged['debit_account'].where(vendor_flagged['debit_account'].str.startswith('Accounts Payable -'), vendor_flagged['credit_account']).nunique()}")
print(f"Vouchers flagged: {len(vendor_flagged)} | Fraud caught: {len(caught_r11)}/{total_fraud} "
      f"({len(caught_r11)/total_fraud*100:.1f}%) | False positives: {fp_r11}")

print(f"\n--- Combined: ranked list (Tier 1) + Rule 11 together ---")
combined_u = caught_u | caught_r11
print(f"Fraud caught: {len(combined_u)}/{total_fraud} ({len(combined_u)/total_fraud*100:.1f}%)")

print(f"\n--- Combined: ranked list (Tier 2) + Rule 11 together ---")
combined_i = caught_i | caught_r11
print(f"Fraud caught: {len(combined_i)}/{total_fraud} ({len(combined_i)/total_fraud*100:.1f}%)")

print(f"\n(In an engagement, Tier 1 entries and any Rule 11 vendor flags go")
print(f"straight to the auditor's working paper; Tier 2's extra {len(tie_band)} borderline")
print(f"entries are a judgement call - review them as a batch rather than")
print(f"silently including or excluding them by an arbitrary cutoff.)")

# Catch rate by fraud type (ranked-list Tier 2 UNION Rule 11, so every
# type's true combined detection ceiling is visible)
print(f"\n--- Catch rate by fraud type (Tier 2 + Rule 11 combined) ---")
for ftype in answer[answer["is_fraud"] == 1]["fraud_type"].unique():
    total_this_type = (answer["fraud_type"] == ftype).sum()
    caught_this_type = len({
        *inclusive[inclusive["fraud_type"] == ftype]["voucher_id"],
        *vendor_flagged[vendor_flagged["fraud_type"] == ftype]["voucher_id"],
    })
    print(f"  {ftype}: {caught_this_type}/{total_this_type}")

# Missed fraud (in bottom of the ranking, and not caught by Rule 11 either)
still_missed = merged[(merged["is_fraud"] == 1) & (~merged["voucher_id"].isin(combined_i))]
print(f"\n--- Fraud entries missed by BOTH the ranked list (Tier 2) and Rule 11 ({len(still_missed)}) ---")
print(still_missed.sort_values("risk_score")[["voucher_id", "risk_score", "fraud_type"]].head(10).to_string(index=False))
