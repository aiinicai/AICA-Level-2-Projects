"""
Scoring, De-duplication and Risk Bucketing module for Red Flag Engine.

Design notes (v2 — calibrated):
---------------------------------
The v1 scorer summed raw flag scores across every fired instance. On a
437-ledger, three-year trial balance that produced ~1,100 exceptions and an
entity score of ~1,945 against a RED threshold of 45 — every engagement read
RED and the buckets carried no information.

v2 changes three things:

1. DE-DUPLICATION. The same rule firing on the same subject in FY22, FY23 and
   FY24 is one audit finding, not three. Instances are collapsed on
   (rule_id, subject); the worst instance is retained and `occurrences` /
   `fy_span` record the recurrence.

2. SUPPRESSION. A rule that fires on 120 ledgers is a systemic/structural
   observation, not 120 leads. Only the `max_instances_per_rule` highest-scoring
   subjects per rule are promoted to the lead sheet; the remainder are counted
   and disclosed (never silently dropped — ICAI Ch. 6 documentation principle).

3. NORMALISED ENTITY SCORE (0-100). The score is the weighted proportion of the
   executed rule battery that fired, scaled by monetary materiality and
   pervasiveness:

       entity_score = 100 x  SUM(w_r x c_r x materiality_r x pervasiveness_r)
                            ------------------------------------------------
                                SUM(w_r x c_r) over executed red/yellow rules

   This is bounded, comparable across engagements, and explainable to a
   reviewer: "38 means 38% of the weighted risk battery lit up".
"""
from typing import Dict, List, Any, Optional
import math
import pandas as pd
import numpy as np

# Bucket thresholds on the normalised 0-100 scale
RED_THRESHOLD = 40.0
YELLOW_THRESHOLD = 18.0

BUCKET_ACTIONS = {
    "RED": "Extend audit procedures; consider a separate forensic engagement",
    "YELLOW": "Design or strengthen preventive controls; targeted substantive testing",
    "GREEN": "No further work indicated; document the conclusion",
}


def _materiality_factor(exception_value: Any, performance_materiality: float) -> float:
    """Monetary weighting. Non-monetary (structural) exceptions default to 0.5."""
    if exception_value is not None and pd.notna(exception_value):
        try:
            val = float(exception_value)
        except (TypeError, ValueError):
            return 0.5
        if val > 0:
            return min(1.0, val / max(1.0, performance_materiality))
    return 0.5


def _pervasiveness(n_subjects: int) -> float:
    """
    A rule hitting many distinct ledgers is more pervasive than one isolated hit.
    Bounded [0.70, 1.00] so pervasiveness modulates but never dominates severity.
    """
    if n_subjects <= 1:
        return 0.70
    return min(1.0, 0.70 + 0.30 * (math.log1p(n_subjects - 1) / math.log1p(9)))


def deduplicate_exceptions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse repeat firings of the same rule on the same subject into a single
    finding, retaining the worst instance and recording recurrence.
    """
    if df.empty:
        return df

    df = df.copy()
    df["_subject_key"] = df["subject"].astype(str).str.strip().str.lower()

    # Worst instance per (rule_id, subject)
    order = df.sort_values("flag_score", ascending=False)
    keep = order.drop_duplicates(subset=["rule_id", "_subject_key"], keep="first").copy()

    grp = df.groupby(["rule_id", "_subject_key"])
    occ = grp["fy"].count().rename("occurrences")
    span = grp["fy"].apply(lambda s: ", ".join(sorted({str(x) for x in s}))).rename("fy_span")
    tot = grp["flag_score"].sum().rename("recurrence_score")

    keep = keep.merge(occ, on=["rule_id", "_subject_key"], how="left")
    keep = keep.merge(span, on=["rule_id", "_subject_key"], how="left")
    keep = keep.merge(tot, on=["rule_id", "_subject_key"], how="left")
    return keep.drop(columns=["_subject_key"])


def score_exceptions(
    exceptions_df: pd.DataFrame,
    performance_materiality: float = 500000.0,
    governance_scores: Optional[Dict[str, int]] = None,
    ml_outlier_df: Optional[pd.DataFrame] = None,
    executed_rules: Optional[List[Dict[str, Any]]] = None,
    max_instances_per_rule: int = 15,
) -> Dict[str, Any]:
    """
    Score, de-duplicate and bucket all fired exceptions.

    Returns a dict containing the retained lead sheet (`scored_exceptions`), the
    suppressed tail (`suppressed_exceptions`), rollups, and the normalised
    entity risk score with a full audit trail of how it was computed.
    """
    empty_shell = {
        "entity_score": 0.0,
        "raw_weighted_sum": 0.0,
        "green_score": 0.0,
        "bucket": "GREEN",
        "bucket_action": BUCKET_ACTIONS["GREEN"],
        "scored_exceptions": pd.DataFrame(),
        "suppressed_exceptions": pd.DataFrame(),
        "all_exceptions": pd.DataFrame(),
        "rollup_by_ledger": pd.DataFrame(),
        "rollup_by_group": pd.DataFrame(),
        "rollup_by_year": pd.DataFrame(),
        "rule_contributions": pd.DataFrame(),
        "governance_status": "not assessed" if governance_scores is None else "assessed",
        "governance_factor": 1.0,
        "stats": {
            "raw_instances": 0,
            "after_dedup": 0,
            "retained": 0,
            "suppressed": 0,
            "distinct_rules_fired": 0,
            "distinct_subjects": 0,
        },
    }

    if exceptions_df is None or exceptions_df.empty:
        return empty_shell

    df = exceptions_df.copy()
    raw_instances = len(df)

    # ---------------------------------------------------------------- 1. score
    weights = df.get("weight", pd.Series(3, index=df.index)).astype(float).fillna(3.0)
    confs = df.get("confidence", pd.Series(1.0, index=df.index)).astype(float).fillna(1.0)
    mat = df.get("exception_value", pd.Series(None, index=df.index)).apply(
        lambda v: _materiality_factor(v, performance_materiality)
    )
    df["weight"] = weights
    df["confidence"] = confs
    df["materiality_factor"] = mat.round(4)
    df["flag_score"] = (weights * confs * mat).round(3)

    # ML outlier tiebreaker
    if ml_outlier_df is not None and not ml_outlier_df.empty:
        outlier_map = dict(zip(ml_outlier_df["ledger_name"], ml_outlier_df["ml_outlier_score"]))
        df["ml_outlier_score"] = df["subject"].map(outlier_map).fillna(0.0)
    else:
        df["ml_outlier_score"] = 0.0

    all_scored = df.sort_values(
        by=["flag_score", "ml_outlier_score"], ascending=[False, False]
    ).reset_index(drop=True)

    # ------------------------------------------------------------ 2. dedupe
    dedup = deduplicate_exceptions(all_scored)
    dedup = dedup.sort_values(
        by=["flag_score", "recurrence_score", "ml_outlier_score"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    after_dedup = len(dedup)

    # --------------------------------------------------------- 3. suppression
    dedup["_rank_in_rule"] = dedup.groupby("rule_id")["flag_score"].rank(
        method="first", ascending=False
    )
    retained = dedup[dedup["_rank_in_rule"] <= max_instances_per_rule].copy()
    suppressed = dedup[dedup["_rank_in_rule"] > max_instances_per_rule].copy()
    retained = retained.drop(columns=["_rank_in_rule"]).reset_index(drop=True)
    suppressed = suppressed.drop(columns=["_rank_in_rule"]).reset_index(drop=True)

    suppression_rows = []
    if not suppressed.empty:
        for rid, sub in suppressed.groupby("rule_id"):
            suppression_rows.append({
                "rule_id": rid,
                "rule_name": sub.iloc[0]["rule_name"],
                "subjects_suppressed": len(sub),
                "max_suppressed_score": round(float(sub["flag_score"].max()), 3),
                "note": (
                    f"{len(sub)} further subjects fired this rule below the top "
                    f"{max_instances_per_rule}. Retained in the working paper "
                    f"'Suppressed' sheet; treat as a systemic observation."
                ),
            })

    # --------------------------------------------- 4. normalised entity score
    # Denominator: weighted universe of executed red/yellow rules
    if executed_rules:
        denom_rows = [
            r for r in executed_rules
            if str(r.get("flag", "red")).lower() in ("red", "yellow")
        ]
        denominator = sum(
            float(r.get("weight", 3)) * float(r.get("confidence", 1.0)) for r in denom_rows
        )
        green_denominator = sum(
            float(r.get("weight", 3)) * float(r.get("confidence", 1.0))
            for r in executed_rules if str(r.get("flag", "")).lower() == "green"
        )
    else:
        uniq = dedup.drop_duplicates(subset=["rule_id"])
        ry = uniq[uniq["flag"].str.lower().isin(["red", "yellow"])]
        denominator = float((ry["weight"] * ry["confidence"]).sum())
        gn = uniq[uniq["flag"].str.lower() == "green"]
        green_denominator = float((gn["weight"] * gn["confidence"]).sum())

    contrib_rows = []
    for rid, sub in dedup.groupby("rule_id"):
        w = float(sub.iloc[0]["weight"])
        c = float(sub.iloc[0]["confidence"])
        flag = str(sub.iloc[0]["flag"]).lower()
        n_subjects = sub["subject"].nunique()
        mat_max = float(sub["materiality_factor"].max())
        perv = _pervasiveness(n_subjects)
        contribution = w * c * mat_max * perv
        contrib_rows.append({
            "rule_id": rid,
            "rule_name": sub.iloc[0]["rule_name"],
            "module": sub.iloc[0].get("module"),
            "flag": flag.upper(),
            "weight": w,
            "confidence": c,
            "subjects_hit": n_subjects,
            "materiality_factor": round(mat_max, 3),
            "pervasiveness": round(perv, 3),
            "contribution": round(contribution, 3),
            "max_possible": round(w * c, 3),
        })

    contrib_df = pd.DataFrame(contrib_rows).sort_values("contribution", ascending=False)

    ry_contrib = contrib_df[contrib_df["flag"].isin(["RED", "YELLOW"])]["contribution"].sum() \
        if not contrib_df.empty else 0.0
    green_contrib = contrib_df[contrib_df["flag"] == "GREEN"]["contribution"].sum() \
        if not contrib_df.empty else 0.0

    raw_weighted_sum = float(ry_contrib)
    entity_pre = 100.0 * raw_weighted_sum / denominator if denominator > 0 else 0.0
    green_score = 100.0 * float(green_contrib) / green_denominator if green_denominator > 0 else 0.0

    # ---------------------------------------------------- 5. governance overlay
    governance_status = "not assessed"
    governance_factor = 1.0
    if governance_scores:
        governance_status = "assessed"
        gov_sum = sum(int(v) for v in governance_scores.values())
        gov_max = 2 * len(governance_scores) if governance_scores else 30
        # Modest, documented +/-15% overlay
        governance_factor = 0.85 + 0.30 * (gov_sum / gov_max if gov_max else 0)

    entity_score = round(min(100.0, entity_pre * governance_factor), 2)
    green_score = round(min(100.0, green_score), 2)

    if entity_score >= RED_THRESHOLD:
        bucket = "RED"
    elif entity_score >= YELLOW_THRESHOLD:
        bucket = "YELLOW"
    else:
        bucket = "GREEN"
    bucket_action = BUCKET_ACTIONS[bucket]

    # ------------------------------------------------------------- 6. rollups
    base = retained if not retained.empty else dedup

    rollup_ledger = base.groupby(["subject"]).agg(
        module=("module", lambda x: ", ".join(sorted(set(map(str, x))))),
        total_flags=("rule_id", "count"),
        total_score=("flag_score", "sum"),
        worst_flag=("flag", lambda x: "RED" if "red" in [str(i).lower() for i in x]
                    else ("YELLOW" if "yellow" in [str(i).lower() for i in x] else "GREEN")),
        rules=("rule_id", lambda x: ", ".join(sorted(set(x)))),
        years=("fy_span", lambda x: ", ".join(sorted({p.strip() for v in x for p in str(v).split(",")}))),
        ml_score=("ml_outlier_score", "max"),
    ).reset_index()
    rollup_ledger["total_score"] = rollup_ledger["total_score"].round(2)
    rollup_ledger = rollup_ledger.sort_values(
        by=["total_score", "ml_score"], ascending=[False, False]
    ).reset_index(drop=True)

    rollup_group = base.groupby(["module", "flag"]).agg(
        flags_count=("rule_id", "count"),
        total_score=("flag_score", "sum"),
        rules=("rule_id", lambda x: ", ".join(sorted(set(x)))),
    ).reset_index().sort_values(by="total_score", ascending=False)
    rollup_group["total_score"] = rollup_group["total_score"].round(2)

    rollup_year = all_scored.groupby("fy").agg(
        flags_count=("rule_id", "count"),
        total_score=("flag_score", "sum"),
        distinct_rules=("rule_id", "nunique"),
        distinct_subjects=("subject", "nunique"),
    ).reset_index().sort_values(by="fy")
    rollup_year["total_score"] = rollup_year["total_score"].round(2)

    return {
        "entity_score": entity_score,
        "entity_score_pre_governance": round(entity_pre, 2),
        "raw_weighted_sum": round(raw_weighted_sum, 2),
        "score_denominator": round(float(denominator), 2),
        "green_score": green_score,
        "bucket": bucket,
        "bucket_action": bucket_action,
        "scored_exceptions": retained,
        "suppressed_exceptions": suppressed,
        "suppression_summary": pd.DataFrame(suppression_rows),
        "all_exceptions": all_scored,
        "rollup_by_ledger": rollup_ledger,
        "rollup_by_group": rollup_group,
        "rollup_by_year": rollup_year,
        "rule_contributions": contrib_df.reset_index(drop=True),
        "governance_status": governance_status,
        "governance_factor": round(governance_factor, 3),
        "thresholds": {"red": RED_THRESHOLD, "yellow": YELLOW_THRESHOLD},
        "stats": {
            "raw_instances": raw_instances,
            "after_dedup": after_dedup,
            "retained": len(retained),
            "suppressed": len(suppressed),
            "distinct_rules_fired": int(dedup["rule_id"].nunique()),
            "distinct_subjects": int(dedup["subject"].nunique()),
            "max_instances_per_rule": max_instances_per_rule,
        },
    }
