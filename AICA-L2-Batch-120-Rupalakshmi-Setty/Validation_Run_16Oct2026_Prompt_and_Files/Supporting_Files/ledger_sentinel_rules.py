"""
Ledger Sentinel - Shared Rules Module
--------------------------------------
The 10 weighted, single-entry red-flag rules used throughout the capstone
project (originally written inline in rules_engine.py), pulled out into one
shared module so BOTH the full-dataset scorer (rules_engine.py) and the
live-Tally scorer (run_live_fraud_scan.py) score vouchers with IDENTICAL
logic. PLUS Rule 11 (below), a fundamentally different KIND of rule added
after a live walkthrough exposed a real gap: every rule above looks at one
voucher in isolation, so a seasoned insider who deliberately keeps each
individual payment small, non-round, and unremarkable - splitting one large
sum across many months to one destination - is invisible to all 10 of them,
by design. Rule 11 instead watches the RELATIONSHIP over time: the
cumulative total flowing to one vendor ledger, compared to that same
vendor's own established baseline.

All rule functions are hardened to handle missing/blank fields safely
(returning "rule did not fire" instead of crashing) because a live Tally
Day Book pull does NOT include time, created_by, altered_by or altered_date
(see tally_mcp_server.py's limitation_note). On the full synthetic dataset,
where every field IS populated, this hardening changes nothing.
"""

import pandas as pd
from collections import Counter
from datetime import datetime

APPROVAL_LIMIT = 25000          # same limit used when the fraud data was planted
NEAR_LIMIT_BAND = 0.04          # "just under" = within 4% below the limit
PERIOD_END_WINDOW_DAYS = 5      # how close to year-end counts as "near period end"


def _clean_str(value):
    """Returns a stripped string, or '' for NaN/empty/None - never crashes."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    return "" if s.lower() == "nan" else s


# ---------------------------------------------------------------------------
# Rule functions - each takes a row (+ shared context), returns (score, reason)
# ---------------------------------------------------------------------------

def rule_weekend_or_afterhours(row, ctx):
    time_str = _clean_str(row.get("time"))
    day = _clean_str(row.get("day_of_week"))
    if not time_str:
        return 0, None  # live Tally data has no time field - rule can't fire
    try:
        hour = int(time_str.split(":")[0])
    except (ValueError, IndexError):
        return 0, None
    is_weekend = day in ("Friday", "Saturday")
    is_afterhours = hour >= 20 or hour <= 5
    if is_weekend and is_afterhours:
        return 95, "Posted on a weekend and outside normal business hours"
    if is_weekend:
        return 65, "Posted on a weekend (Fri/Sat)"
    if is_afterhours:
        return 65, "Posted outside normal business hours"
    return 0, None


def rule_vendor_bank_detail_change(row, ctx):
    narr = _clean_str(row.get("narration")).lower()
    keywords = ("bank detail", "bank details", "account details updated", "new bank account", "updated bank")
    if any(k in narr for k in keywords):
        large_payment = row["amount"] >= 30000
        return (90 if large_payment else 60), (
            "Narration references a vendor bank-detail change" +
            (" immediately before a large payment" if large_payment else "")
        )
    return 0, None


def rule_near_period_end(row, ctx):
    days_to_year_end = (ctx["year_end"] - row["date"]).days
    if 0 <= days_to_year_end <= PERIOD_END_WINDOW_DAYS:
        return 70, f"Posted within {PERIOD_END_WINDOW_DAYS} days of year-end close"
    if pd.notna(row.get("altered_date_parsed")) and row["altered_date_parsed"] > ctx["year_end"]:
        return 85, "Altered after the year-end close date (post-closing entry)"
    return 0, None


def rule_round_amount(row, ctx):
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


def rule_near_approval_limit(row, ctx):
    amt = row["amount"]
    lower_band = APPROVAL_LIMIT * (1 - NEAR_LIMIT_BAND)
    if lower_band <= amt < APPROVAL_LIMIT:
        return 80, f"Amount just below the {APPROVAL_LIMIT:,.0f} approval limit"
    return 0, None


def rule_rare_account_pair(row, ctx):
    pair = (row["debit_account"], row["credit_account"])
    if ctx["account_pair_counts"][pair] <= ctx["rare_pair_threshold"]:
        return 35, "Unusual combination of debit/credit accounts"
    return 0, None


def rule_vague_narration(row, ctx):
    narr = _clean_str(row.get("narration")).lower()
    vague_set = {"", "n/a", "entry", "adjustment", "as discussed", "misc entry"}
    if narr in vague_set:
        return 45, "Missing or vague narration"
    return 0, None


def rule_duplicate_pattern(row, ctx):
    created_by = _clean_str(row.get("created_by"))
    if not created_by:
        return 0, None  # live Tally data has no created_by field - rule can't fire
    key = (created_by, row["debit_account"], row["credit_account"], int(row["amount"] // 50))
    if ctx["dup_key_counts"][key] >= 2:
        return 70, "Matches another entry with same user, accounts and similar amount (possible duplicate)"
    return 0, None


def rule_same_user_create_alter(row, ctx):
    created_by = _clean_str(row.get("created_by"))
    altered_by = _clean_str(row.get("altered_by"))
    if not created_by or not altered_by:
        return 0, None  # live Tally data has no altered_by field - rule can't fire
    if altered_by == created_by:
        return 85, "Same user both created and altered this entry (no segregation of duties)"
    return 0, None


def rule_old_voucher_late_edit(row, ctx):
    if pd.notna(row.get("altered_date_parsed")):
        gap_days = (row["altered_date_parsed"] - row["date"]).days
        if gap_days >= 60:
            return 85, f"Edited {gap_days} days after original posting (long after likely review)"
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


# ---------------------------------------------------------------------------
# Rule 11 - structured disbursement to a single vendor (an AGGREGATE rule,
# not a single-entry one - see module docstring)
# ---------------------------------------------------------------------------
# This is Rule 11's THIRD design, kept honest rather than hidden:
#   v1 grouped by a vendor name guessed from narration text - only worked
#      because a test planted an obvious fake name; real narrations never
#      name a vendor, so this would almost never fire for real.
#   v2 compared a vendor's current volume to a FIXED dollar threshold, then
#      to that vendor's own whole-year average - both failed because either
#      there's no single "a lot" that works for every vendor, or the
#      baseline is contaminated by the very anomaly it's trying to measure.
#   v3 (this version) compares a vendor's current rolling total to that
#      SAME vendor's own EARLIEST activity in the dataset - two
#      non-overlapping periods, so a later anomaly can't pollute the
#      baseline used to catch it.
# HONEST LIMITATION: this only works because the data spans a full year
# and an anomaly happening to appear after an early quiet period. A real
# engagement would need a full PRIOR year's Day Book to build a trustworthy
# baseline ahead of the period under review - flagged as a "next steps"
# item in the project docs, not glossed over.
#
# Shown as its OWN separate flag (vendor_flag_score / vendor_flag_reason),
# never blended into risk_score - the same way Benford's Law is its own
# screen rather than folded into the weighted average. A single powerful
# relationship-level signal would otherwise get diluted to near-invisible
# next to ten single-entry rules, exactly what happened when this was
# tried in the first prototype.
RULE11_WINDOW_DAYS = 270       # ~9 months trailing window for the "current" total
RULE11_BASELINE_DAYS = 60      # the vendor's own early period, used as its baseline
RULE11_THRESHOLD_MULTIPLIER = 2.0   # current total must exceed 2x the scaled-up baseline
RULE11_MAX_SCORE_MULTIPLIER = 5.0   # multiplier at which the score saturates at 100
RULE11_MIN_BASELINE_TXNS = 1


def is_vendor_ledger(account_name) -> bool:
    return isinstance(account_name, str) and account_name.startswith("Accounts Payable - ")


def compute_rule11_scores(df: pd.DataFrame) -> dict:
    """
    df must have a parsed 'date' column (datetime64), plus 'voucher_id',
    'amount', 'debit_account', 'credit_account'. Returns
    {voucher_id: (score 0-100, reason_or_None)} for every row.
    """
    out = {vid: (0, None) for vid in df["voucher_id"]}

    vendors = sorted({
        a for a in pd.concat([df["debit_account"], df["credit_account"]]).unique()
        if is_vendor_ledger(a)
    })

    for vendor in vendors:
        mask = (df["debit_account"] == vendor) | (df["credit_account"] == vendor)
        sub = df[mask].sort_values("date").reset_index(drop=True)
        if sub.empty:
            continue

        earliest_date = sub["date"].min()
        baseline_end = earliest_date + pd.Timedelta(days=RULE11_BASELINE_DAYS)
        baseline_rows = sub[sub["date"] <= baseline_end]
        if len(baseline_rows) < RULE11_MIN_BASELINE_TXNS:
            continue
        baseline_daily_rate = baseline_rows["amount"].sum() / RULE11_BASELINE_DAYS
        expected_rolling_total = baseline_daily_rate * RULE11_WINDOW_DAYS
        if expected_rolling_total <= 0:
            continue

        dates = sub["date"].values
        amounts = sub["amount"].values
        voucher_ids = sub["voucher_id"].values

        for i in range(len(sub)):
            window_start = dates[i] - pd.Timedelta(days=RULE11_WINDOW_DAYS)
            in_window = (dates >= window_start) & (dates <= dates[i])
            rolling_total = amounts[in_window].sum()
            ratio = rolling_total / expected_rolling_total

            if ratio > RULE11_THRESHOLD_MULTIPLIER:
                span = RULE11_MAX_SCORE_MULTIPLIER - RULE11_THRESHOLD_MULTIPLIER
                score = min(100, 40 + ((ratio - RULE11_THRESHOLD_MULTIPLIER) / span) * 60)
                reason = (
                    f"'{vendor}' received AED {rolling_total:,.0f} over the trailing "
                    f"{RULE11_WINDOW_DAYS}-day window - {ratio:.1f}x this vendor's own "
                    f"early-period baseline rate (AED {expected_rolling_total:,.0f} expected, "
                    f"based on its first {RULE11_BASELINE_DAYS} days of activity) - no single "
                    f"payment in this window is unusual on its own"
                )
                out[voucher_ids[i]] = (round(score, 1), reason)

    return out


def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes a voucher DataFrame in the standard 12-column Day Book layout
    (voucher_id, date, time, day_of_week, created_by, created_by_name,
    altered_by, altered_date, debit_account, credit_account, amount,
    narration) and returns a risk-scored, ranked DataFrame - same shape
    as risk_scored_vouchers.xlsx.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["altered_date_parsed"] = pd.to_datetime(df.get("altered_date"), errors="coerce")

    ctx = {}
    ctx["year_end"] = datetime(df["date"].dt.year.max(), 12, 31)
    ctx["account_pair_counts"] = Counter(zip(df["debit_account"], df["credit_account"]))
    ctx["rare_pair_threshold"] = df.shape[0] * 0.002
    ctx["dup_key_counts"] = Counter(
        zip(
            df.get("created_by", pd.Series([""] * len(df))).map(_clean_str),
            df["debit_account"],
            df["credit_account"],
            (df["amount"] // 50).astype(int),
        )
    )

    results = []
    for _, row in df.iterrows():
        fired = []
        weighted_total = 0.0
        weight_sum = 0.0
        for name, fn, weight in RULES:
            score, reason = fn(row, ctx)
            weight_sum += weight * 100
            if score > 0:
                weighted_total += score * weight
                fired.append(f"{name}: {reason}")
        risk_score = round((weighted_total / weight_sum) * 100, 1) if weight_sum else 0.0
        results.append({
            "voucher_id": row["voucher_id"],
            "date": row["date"].strftime("%Y-%m-%d"),
            "created_by_name": row.get("created_by_name", ""),
            "debit_account": row["debit_account"],
            "credit_account": row["credit_account"],
            "amount": row["amount"],
            "narration": row["narration"],
            "risk_score": risk_score,
            "num_flags": len(fired),
            "reasons": " | ".join(fired) if fired else "No red flags",
        })

    # kind="stable" + an explicit tie-break on voucher_id: without this, Python/
    # pandas versions can break ties between equal-scoring vouchers differently
    # (observed: the same data scored 186-190 caught-in-top-N across
    # environments purely from sort tie-order, not from any real difference in
    # the rules). This makes the ranking - and the catch-rate it is measured on -
    # fully reproducible regardless of platform or library version.
    scored = pd.DataFrame(results).sort_values(
        ["risk_score", "voucher_id"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
    scored.insert(0, "rank", range(1, len(scored) + 1))

    # Rule 11 is deliberately NOT blended into risk_score above (see its
    # own docstring for why) - it's attached here as a separate pair of
    # columns, the same way a dashboard would show Benford's Law as its
    # own screen rather than folding it into the weighted average.
    rule11_scores = compute_rule11_scores(df)
    scored["vendor_flag_score"] = scored["voucher_id"].map(lambda v: rule11_scores[v][0])
    scored["vendor_flag_reason"] = scored["voucher_id"].map(lambda v: rule11_scores[v][1])
    return scored
