"""
Calibration tests for the v2 scorer.

The v1 scorer summed raw flag scores and produced ~1,945 against a RED threshold
of 45, so every engagement classified RED. These tests lock in the properties
that make the v2 score usable: boundedness, de-duplication, per-rule
suppression, a bounded governance overlay, and monotonicity.
"""
import pandas as pd
import pytest

from engine.scoring import (
    score_exceptions,
    deduplicate_exceptions,
    RED_THRESHOLD,
    YELLOW_THRESHOLD,
    _pervasiveness,
)


def _exc(rule_id, subject, fy, flag="red", weight=4, conf=1.0, value=1_000_000):
    return {
        "rule_id": rule_id, "rule_name": f"Rule {rule_id}", "module": rule_id.split("-")[0],
        "flag": flag, "weight": weight, "confidence": conf, "branch": "b", "scheme": "1",
        "source": "ICAI", "hypothesis": "", "procedure": [], "fy": fy, "subject": subject,
        "observed_value": value, "threshold_value": 500000, "exception_value": value,
        "detail": f"{rule_id} on {subject}",
    }


def _executed(rule_ids, flag="red", weight=4, conf=1.0):
    return [{"rule_id": r, "name": r, "module": r.split("-")[0], "flag": flag,
             "weight": weight, "confidence": conf} for r in rule_ids]


def test_score_is_bounded_zero_to_hundred():
    """Even with every rule firing at full materiality the score cannot exceed 100."""
    rows = [_exc(f"TB-{i:02d}", f"Ledger {j}", fy, value=10**9)
            for i in range(1, 15) for j in range(20) for fy in ("FY22", "FY23", "FY24")]
    res = score_exceptions(pd.DataFrame(rows), 500000.0, None, None,
                           executed_rules=_executed([f"TB-{i:02d}" for i in range(1, 15)]))
    assert 0 <= res["entity_score"] <= 100


def test_empty_exceptions_scores_green_zero():
    res = score_exceptions(pd.DataFrame(), 500000.0)
    assert res["entity_score"] == 0.0
    assert res["bucket"] == "GREEN"
    assert res["scored_exceptions"].empty


def test_deduplication_collapses_same_rule_same_subject_across_years():
    rows = [_exc("TB-03", "Suspense A/c", fy) for fy in ("FY22", "FY23", "FY24")]
    df = pd.DataFrame(rows)
    df["flag_score"] = [3.0, 4.0, 5.0]
    out = deduplicate_exceptions(df)
    assert len(out) == 1, "Three year-instances of one finding must collapse to one"
    assert out.iloc[0]["occurrences"] == 3
    assert out.iloc[0]["flag_score"] == 5.0, "The worst instance must be retained"
    assert set(out.iloc[0]["fy_span"].split(", ")) == {"FY22", "FY23", "FY24"}


def test_suppression_caps_subjects_per_rule():
    rows = [_exc("LG-08", f"Ledger {j}", "FY24", value=1_000_000 + j) for j in range(60)]
    res = score_exceptions(pd.DataFrame(rows), 500000.0, None, None,
                           executed_rules=_executed(["LG-08"]), max_instances_per_rule=15)
    assert res["stats"]["retained"] == 15
    assert res["stats"]["suppressed"] == 45
    assert len(res["suppressed_exceptions"]) == 45, "Suppressed rows must be preserved, not dropped"
    assert not res["suppression_summary"].empty, "Suppression must be disclosed"


def test_governance_overlay_is_bounded_and_monotonic():
    rows = [_exc("TB-03", "Suspense A/c", "FY24")]
    ex = _executed(["TB-03"])
    base = score_exceptions(pd.DataFrame(rows), 500000.0, None, None, executed_rules=ex)
    low = score_exceptions(pd.DataFrame(rows), 500000.0, {f"q{i}": 0 for i in range(1, 16)}, None, executed_rules=ex)
    high = score_exceptions(pd.DataFrame(rows), 500000.0, {f"q{i}": 2 for i in range(1, 16)}, None, executed_rules=ex)

    assert low["governance_factor"] == pytest.approx(0.85)
    assert high["governance_factor"] == pytest.approx(1.15)
    assert base["governance_factor"] == 1.0
    assert base["governance_status"] == "not assessed"
    assert low["entity_score"] < base["entity_score"] < high["entity_score"]


def test_buckets_partition_the_scale():
    assert YELLOW_THRESHOLD < RED_THRESHOLD
    for score, expected in [(0, "GREEN"), (17.9, "GREEN"), (18, "YELLOW"),
                            (39.9, "YELLOW"), (40, "RED"), (100, "RED")]:
        bucket = "RED" if score >= RED_THRESHOLD else ("YELLOW" if score >= YELLOW_THRESHOLD else "GREEN")
        assert bucket == expected


def test_more_rules_firing_raises_the_score():
    ex = _executed([f"TB-{i:02d}" for i in range(1, 11)])
    few = score_exceptions(pd.DataFrame([_exc("TB-01", "A", "FY24")]), 500000.0, None, None, executed_rules=ex)
    many = score_exceptions(
        pd.DataFrame([_exc(f"TB-{i:02d}", "A", "FY24") for i in range(1, 9)]),
        500000.0, None, None, executed_rules=ex)
    assert many["entity_score"] > few["entity_score"]


def test_green_flags_are_never_netted_against_risk():
    rows = [_exc("TB-01", "A", "FY24", flag="red"),
            _exc("GF-01", "B", "FY24", flag="green")]
    ex = _executed(["TB-01"]) + _executed(["GF-01"], flag="green")
    res = score_exceptions(pd.DataFrame(rows), 500000.0, None, None, executed_rules=ex)
    assert res["entity_score"] > 0
    assert res["green_score"] > 0
    assert res["entity_score"] == res["entity_score_pre_governance"], \
        "Green score must not reduce the risk score"


def test_materiality_scales_the_score():
    rows = [_exc("TB-01", "A", "FY24", value=100_000)]
    ex = _executed(["TB-01"])
    tight = score_exceptions(pd.DataFrame(rows), 100_000.0, None, None, executed_rules=ex)
    loose = score_exceptions(pd.DataFrame(rows), 10_000_000.0, None, None, executed_rules=ex)
    assert tight["entity_score"] > loose["entity_score"], \
        "A lower materiality must make the same exception weigh more"


def test_pervasiveness_bounds():
    assert _pervasiveness(0) == pytest.approx(0.70)
    assert _pervasiveness(1) == pytest.approx(0.70)
    assert _pervasiveness(10) == pytest.approx(1.00)
    assert _pervasiveness(500) == pytest.approx(1.00)
    assert _pervasiveness(3) > _pervasiveness(2) > _pervasiveness(1)


# ---------------------------------------------------------------------------
# Hypothesis rendering
# ---------------------------------------------------------------------------
import re  # noqa: E402

from reporting.hypotheses import build_hypothesis_text, _hypothesis_context  # noqa: E402

PLACEHOLDER = re.compile(r"\{[A-Za-z_0-9]+\}")


def _row(**over):
    base = {
        "rule_id": "TB-99", "rule_name": "R", "flag": "red", "fy": "FY24",
        "subject": "Suspense A/c", "observed_value": 1000.0, "threshold_value": 0.0,
        "detail": "Balance of 1,000.00 carried forward", "context": {},
        "hypothesis": "",
    }
    base.update(over)
    return pd.Series(base)


def test_missing_placeholders_never_leak_braces_to_the_ui():
    """The original formatter raised on the first missing key and dumped the raw
    template on screen — 78 of 125 leads showed literal {placeholders}."""
    row = _row(hypothesis="Ledger '{ledger_name}' had turnover {turnover_dr} in {fy}.")
    text = build_hypothesis_text(row)
    assert not PLACEHOLDER.search(text), text
    assert "Suspense A/c" in text and "FY24" in text


def test_unresolved_values_append_the_factual_detail():
    row = _row(hypothesis="Turnover was {turnover_dr}.")
    text = build_hypothesis_text(row)
    assert "Observed: Balance of 1,000.00 carried forward." in text


def test_fully_resolved_hypothesis_does_not_append_detail():
    row = _row(hypothesis="Ledger '{ledger_name}' shows {observed_value} in {fy}.")
    text = build_hypothesis_text(row)
    assert "Observed:" not in text


def test_em_dash_in_a_ledger_name_does_not_trigger_the_detail_appendix():
    """Indian ledger names routinely contain em dashes; detecting unresolved
    values by searching the rendered text produced false positives."""
    row = _row(subject="Sundry Creditors — Ravi Trading Co",
               hypothesis="Ledger '{ledger_name}' in {fy}.")
    assert "Observed:" not in build_hypothesis_text(row)


def test_rule_supplied_context_wins_over_aliases():
    row = _row(context={"group": "Trade Payables"},
               hypothesis="Group '{group}' flagged.")
    assert "Trade Payables" in build_hypothesis_text(row)


def test_turnover_total_is_not_aliased_to_observed_value():
    """The old alias made TB-07 state 'turnover of 0.0' when 0.0 was the closing
    balance, not the turnover."""
    ctx = _hypothesis_context(_row(observed_value=0.0))
    ctx["turnover_total"]
    assert "turnover_total" in ctx.missing


def test_blank_hypothesis_falls_back_to_a_readable_sentence():
    text = build_hypothesis_text(_row(hypothesis=""))
    assert "TB-99" in text and "Suspense A/c" in text and "carried forward" in text
