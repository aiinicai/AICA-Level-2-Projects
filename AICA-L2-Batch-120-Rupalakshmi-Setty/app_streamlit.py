"""
Ledger Sentinel - Streamlit Interface (Step 11)

Run with:   streamlit run app_streamlit.py

Screens:
  1. Upload - drop in a Tally Day Book export (.xlsx/.csv)
  2. Risk dashboard - headline numbers (total entries, flagged, avg score)
  3. Top suspicious entries - ranked table with reasons
  4. Vendor structured-disbursement screen (Rule 11 - separate from the
     ranked list, see score_dataframe() below)
  5. Round-amount / digit-pattern chart (a simple Benford-style check)
  6. Download button - exports the working paper as .xlsx

This file is self-contained: it re-implements the same rule functions as
rules_engine.py so the app works standalone on any uploaded file, without
requiring the answer key (which you would never have in a real engagement).
"""

import io
from collections import Counter
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ledger Sentinel", layout="wide")

APPROVAL_LIMIT = 25000
NEAR_LIMIT_BAND = 0.04
PERIOD_END_WINDOW_DAYS = 5

REQUIRED_COLUMNS = [
    "voucher_id", "date", "time", "day_of_week", "created_by", "created_by_name",
    "altered_by", "altered_date", "debit_account", "credit_account", "amount", "narration",
]


@st.cache_data(show_spinner=False)
def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["altered_date_parsed"] = pd.to_datetime(df["altered_date"], errors="coerce")
    year_end = datetime(df["date"].dt.year.max(), 12, 31)

    account_pair_counts = Counter(zip(df["debit_account"], df["credit_account"]))
    rare_pair_threshold = max(df.shape[0] * 0.002, 1)
    dup_key_counts = Counter(
        zip(df["created_by"], df["debit_account"], df["credit_account"], (df["amount"] // 50).astype(int))
    )

    def rule_weekend_or_afterhours(row):
        is_weekend = row["day_of_week"] in ("Friday", "Saturday")
        hour = int(str(row["time"]).split(":")[0])
        is_afterhours = hour >= 20 or hour <= 5
        if is_weekend and is_afterhours:
            return 95, "Posted on a weekend and outside normal business hours"
        if is_weekend:
            return 65, "Posted on a weekend (Fri/Sat)"
        if is_afterhours:
            return 65, "Posted outside normal business hours"
        return 0, None

    def rule_near_period_end(row):
        days_to_year_end = (year_end - row["date"]).days
        if 0 <= days_to_year_end <= PERIOD_END_WINDOW_DAYS:
            return 70, f"Posted within {PERIOD_END_WINDOW_DAYS} days of year-end close"
        if pd.notna(row["altered_date_parsed"]) and row["altered_date_parsed"] > year_end:
            return 85, "Altered after the year-end close date (post-closing entry)"
        return 0, None

    def rule_round_amount(row):
        amt = row["amount"]
        if amt == 0:
            return 0, None
        if amt % 1000 == 0 and amt >= 1000:
            suspense_like = row["debit_account"] in ("Suspense Account", "Miscellaneous Expense")
            return (95 if suspense_like else 40), (
                "Round amount posted to a suspense/miscellaneous account" if suspense_like
                else "Suspiciously round amount"
            )
        return 0, None

    def rule_near_approval_limit(row):
        amt = row["amount"]
        lower_band = APPROVAL_LIMIT * (1 - NEAR_LIMIT_BAND)
        if lower_band <= amt < APPROVAL_LIMIT:
            return 80, f"Amount just below the {APPROVAL_LIMIT:,.0f} approval limit"
        return 0, None

    def rule_rare_account_pair(row):
        pair = (row["debit_account"], row["credit_account"])
        if account_pair_counts[pair] <= rare_pair_threshold:
            return 35, "Unusual combination of debit/credit accounts"
        return 0, None

    def rule_vague_narration(row):
        narr = str(row["narration"]).strip().lower()
        vague_set = {"", "n/a", "entry", "adjustment", "as discussed", "misc entry", "nan"}
        if narr in vague_set:
            return 45, "Missing or vague narration"
        return 0, None

    def rule_duplicate_pattern(row):
        key = (row["created_by"], row["debit_account"], row["credit_account"], int(row["amount"] // 50))
        if dup_key_counts[key] >= 2:
            return 70, "Matches another entry with same user, accounts and similar amount (possible duplicate)"
        return 0, None

    def rule_same_user_create_alter(row):
        if row["altered_by"] and row["altered_by"] == row["created_by"]:
            return 85, "Same user both created and altered this entry (no segregation of duties)"
        return 0, None

    def rule_old_voucher_late_edit(row):
        if pd.notna(row["altered_date_parsed"]):
            gap_days = (row["altered_date_parsed"] - row["date"]).days
            if gap_days >= 60:
                return 85, f"Edited {gap_days} days after original posting (long after likely review)"
        return 0, None

    def rule_vendor_bank_detail_change(row):
        narr = str(row["narration"]).lower()
        keywords = ("bank detail", "bank details", "account details updated", "new bank account", "updated bank")
        if any(k in narr for k in keywords):
            large_payment = row["amount"] >= 30000
            return (90 if large_payment else 60), (
                "Narration references a vendor bank-detail change" +
                (" immediately before a large payment" if large_payment else "")
            )
        return 0, None

    RULES = [
        ("Weekend/After-hours", rule_weekend_or_afterhours, 1.1),
        ("Near period end", rule_near_period_end, 1.2),
        ("Round amount", rule_round_amount, 1.1),
        ("Near approval limit", rule_near_approval_limit, 1.1),
        ("Rare account pair", rule_rare_account_pair, 0.5),
        ("Vague narration", rule_vague_narration, 0.7),
        ("Duplicate pattern", rule_duplicate_pattern, 1.2),
        ("Same user create/alter", rule_same_user_create_alter, 1.3),
        ("Old voucher late edit", rule_old_voucher_late_edit, 1.4),
        ("Vendor bank-detail change", rule_vendor_bank_detail_change, 1.3),
    ]

    weight_sum = sum(w * 100 for _, _, w in RULES)
    results = []
    for _, row in df.iterrows():
        fired, weighted_total = [], 0.0
        for name, fn, weight in RULES:
            score, reason = fn(row)
            if score > 0:
                weighted_total += score * weight
                fired.append(f"{name}: {reason}")
        risk_score = round((weighted_total / weight_sum) * 100, 1) if weight_sum else 0.0
        results.append({
            "voucher_id": row["voucher_id"], "date": row["date"].strftime("%Y-%m-%d"),
            "created_by_name": row["created_by_name"], "debit_account": row["debit_account"],
            "credit_account": row["credit_account"], "amount": row["amount"],
            "narration": row["narration"], "risk_score": risk_score,
            "num_flags": len(fired), "reasons": " | ".join(fired) if fired else "No red flags",
        })
    # kind="stable" + an explicit voucher_id tiebreak: without this, ties
    # between equal-scoring vouchers can break differently across
    # pandas/Python versions, making the ranking (and anything measured
    # against it) non-reproducible. See rules_engine.py / ledger_sentinel_rules.py.
    scored = pd.DataFrame(results).sort_values(
        ["risk_score", "voucher_id"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
    scored.insert(0, "rank", range(1, len(scored) + 1))

    # Rule 11 - vendor structured-disbursement screen. A fundamentally
    # different KIND of rule from the 10 above: those look at one voucher
    # at a time, so a seasoned insider who deliberately keeps each payment
    # small, non-round and unremarkable - splitting one large sum across
    # many months to one destination - is invisible to all of them, by
    # design. This instead watches the cumulative total paid to one vendor
    # ledger over time, relative to that SAME vendor's own early-period
    # baseline (two non-overlapping periods, so a later anomaly can't
    # contaminate the baseline used to catch it). Shown as its OWN separate
    # flag below, never blended into risk_score, for the same reason
    # Benford's Law gets its own screen rather than folding into the
    # weighted average: blending a powerful relationship-level signal into
    # ten single-entry rules drowns it out.
    vendor_scores = _compute_rule11_scores(df)
    scored["vendor_flag_score"] = scored["voucher_id"].map(lambda v: vendor_scores[v][0])
    scored["vendor_flag_reason"] = scored["voucher_id"].map(lambda v: vendor_scores[v][1])
    return scored


def _is_vendor_ledger(account_name) -> bool:
    return isinstance(account_name, str) and account_name.startswith("Accounts Payable - ")


def _compute_rule11_scores(df: pd.DataFrame, window_days=270, baseline_days=60,
                            threshold_multiplier=2.0, max_score_multiplier=5.0) -> dict:
    out = {vid: (0, None) for vid in df["voucher_id"]}
    vendors = sorted({
        a for a in pd.concat([df["debit_account"], df["credit_account"]]).unique()
        if _is_vendor_ledger(a)
    })
    for vendor in vendors:
        mask = (df["debit_account"] == vendor) | (df["credit_account"] == vendor)
        sub = df[mask].sort_values("date").reset_index(drop=True)
        if sub.empty:
            continue
        earliest_date = sub["date"].min()
        baseline_rows = sub[sub["date"] <= earliest_date + pd.Timedelta(days=baseline_days)]
        if baseline_rows.empty:
            continue
        expected_rolling_total = (baseline_rows["amount"].sum() / baseline_days) * window_days
        if expected_rolling_total <= 0:
            continue
        dates, amounts, voucher_ids = sub["date"].values, sub["amount"].values, sub["voucher_id"].values
        for i in range(len(sub)):
            in_window = (dates >= dates[i] - pd.Timedelta(days=window_days)) & (dates <= dates[i])
            ratio = amounts[in_window].sum() / expected_rolling_total
            if ratio > threshold_multiplier:
                span = max_score_multiplier - threshold_multiplier
                score = min(100, 40 + ((ratio - threshold_multiplier) / span) * 60)
                reason = (
                    f"'{vendor}' received AED {amounts[in_window].sum():,.0f} over the trailing "
                    f"{window_days}-day window - {ratio:.1f}x this vendor's own early-period "
                    f"baseline - no single payment in this window is unusual on its own"
                )
                out[voucher_ids[i]] = (round(score, 1), reason)
    return out


def first_digit_distribution(amounts: pd.Series) -> pd.DataFrame:
    """Simple Benford's-Law style first-digit check (screen, not proof)."""
    digits = amounts[amounts > 0].astype(str).str.replace(".", "", regex=False).str[0].astype(int)
    observed = digits.value_counts(normalize=True).sort_index() * 100
    # Benford expected %: log10(1+1/d)*100
    import math
    benford_expected = {d: math.log10(1 + 1 / d) * 100 for d in range(1, 10)}
    out = pd.DataFrame({
        "digit": list(range(1, 10)),
        "observed_%": [round(observed.get(d, 0.0), 2) for d in range(1, 10)],
        "benford_expected_%": [round(benford_expected[d], 2) for d in range(1, 10)],
    })
    return out


st.title("🔎 Ledger Sentinel")
st.caption("AI-assisted journal-entry fraud screening for Tally Prime data (SA 240 journal-entry testing support tool)")

uploaded = st.file_uploader("Upload a Tally Day Book export (.xlsx or .csv)", type=["xlsx", "csv"])

if uploaded is None:
    st.info("Upload a Day Book export to begin. Expected columns: " + ", ".join(REQUIRED_COLUMNS))
    st.stop()

if uploaded.name.endswith(".csv"):
    raw_df = pd.read_csv(uploaded)
else:
    raw_df = pd.read_excel(uploaded)

missing = [c for c in REQUIRED_COLUMNS if c not in raw_df.columns]
if missing:
    st.error(f"Uploaded file is missing required columns: {missing}")
    st.stop()

scored_df = score_dataframe(raw_df)

st.header("Risk Dashboard")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total entries", f"{len(scored_df):,}")
col2.metric("Flagged (score > 0)", f"{(scored_df['risk_score'] > 0).sum():,}")
col3.metric("High risk (score ≥ 50)", f"{(scored_df['risk_score'] >= 50).sum():,}")
col4.metric("Average risk score", f"{scored_df['risk_score'].mean():.1f}")

st.header("Top Suspicious Entries")
top_n = st.slider("How many top-ranked entries to show", 10, 200, 50, step=10)
st.dataframe(
    scored_df.head(top_n)[["rank", "voucher_id", "date", "created_by_name", "debit_account",
                            "credit_account", "amount", "risk_score", "reasons"]],
    use_container_width=True, height=420,
)

st.header("Vendor Structured-Disbursement Screen (Rule 11)")
st.caption(
    "Separate from the ranked list above - catches a destination vendor whose cumulative "
    "payments have ramped up well beyond its own early-period baseline, even when every "
    "individual payment looks unremarkable on its own."
)
vendor_flags = scored_df[scored_df["vendor_flag_score"] > 0].sort_values("vendor_flag_score", ascending=False)
if len(vendor_flags):
    st.dataframe(
        vendor_flags[["voucher_id", "date", "debit_account", "credit_account", "amount",
                       "vendor_flag_score", "vendor_flag_reason"]],
        use_container_width=True, height=min(300, 60 + 35 * len(vendor_flags)),
    )
else:
    st.caption(
        "No vendor-level structuring pattern detected in this file (or there isn't enough "
        "per-vendor history yet to form a baseline)."
    )

st.header("First-Digit Pattern Check (Benford's Law screen)")
st.caption("A screen, not proof - recommended only when the dataset has 5,000+ records.")
benford_table = first_digit_distribution(scored_df["amount"])
st.bar_chart(benford_table.set_index("digit")[["observed_%", "benford_expected_%"]])

st.header("Download Working Paper")
# Union the top-N ranked rows with any Rule 11 vendor flags, so a vendor
# flagged on the separate structuring screen - which deliberately isn't
# blended into risk_score - doesn't get silently left out of the working
# paper just for not ranking high enough on its own.
working_paper_ids = set(scored_df.head(top_n)["voucher_id"]) | set(vendor_flags["voucher_id"])
working_paper_df = scored_df[scored_df["voucher_id"].isin(working_paper_ids)].sort_values(
    ["rank"]
)
buffer = io.BytesIO()
working_paper_df.to_excel(buffer, index=False, engine="openpyxl")
st.download_button(
    "Download top flagged entries as Excel working paper",
    data=buffer.getvalue(),
    file_name="ledger_sentinel_working_paper.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.caption(
    "Note: this tool prioritises entries for human review - it does not conclude that fraud "
    "has occurred. Rules-based flags require auditor judgement and corroborating evidence."
)
