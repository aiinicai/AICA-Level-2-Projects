from dataclasses import replace
from datetime import date

import pytest

from engine.generator import entity_fys, horizon_end
from engine.predicates import (AMBIGUOUS, Ctx, board_meeting_regime, classify_all, classify_aoc4, classify_csr,
                               classify_internal_audit, classify_llp_audit, classify_mgt8,
                               classify_secretarial_audit, classify_small_llp, classify_small_with, evaluate,
                               inr_short, is_small_company, rule_9b_trigger_fy, validate_expr)
from engine.types import FactsIn

D = date
CR, L = 10_000_000, 100_000


def ctx_for(rp, d, fy_key, as_of=D(2026, 9, 25), entity=None, facts=None, decisions=None):
    e = entity or d["entity"]
    fys = entity_fys(e, horizon_end(as_of))
    fy = next(f for f in fys if f.key == fy_key)
    return Ctx(e, rp, as_of, fys, d["facts"] if facts is None else facts, fy=fy, decisions=decisions or {})


# ----------------------------------------------------------- small company
def test_delta_small_new_not_small_old(rp, demo):
    c = is_small_company(ctx_for(rp, demo["delta"], "FY2025-26"))
    assert c.result is True and "G.S.R. 880(E)" in c.citation
    old = rp.threshold("SMALL_COMPANY", D(2025, 11, 30))
    assert classify_small_with(demo["delta"]["entity"], 8 * CR, 80 * CR, old).result is False


def test_delta_fy2024_25_ambiguous_until_decided(rp, demo):
    c = is_small_company(ctx_for(rp, demo["delta"], "FY2024-25"))
    assert c.result == AMBIGUOUS and c.ambiguous and "partner decision required" in c.reasons[-1]
    c2 = is_small_company(ctx_for(rp, demo["delta"], "FY2024-25", decisions={"SMALL:FY2024-25": "SMALL"}))
    assert c2.result is True and "partner decision" in c2.reasons[-1]


@pytest.mark.parametrize("flag,text", [("is_holding", "holding"), ("is_subsidiary", "subsidiary"),
                                       ("special_act", "special Act")])
def test_small_exclusions(rp, demo, flag, text):
    e = replace(demo["alpha"]["entity"], **{flag: True})
    c = is_small_company(ctx_for(rp, demo["alpha"], "FY2026-27", entity=e))
    assert c.result is False and text in c.reasons[0]


def test_public_never_small(rp, demo):
    assert is_small_company(ctx_for(rp, demo["epsilon"], "FY2025-26")).result is False


# ------------------------------------------------------ other classifiers
def test_gamma_panel(rp, demo):
    panel = {c.name: c for c in classify_all(ctx_for(rp, demo["gamma"], "FY2025-26"))}
    assert panel["small_company"].result is False
    assert panel["mgt7_variant"].result == "MGT-7"
    assert panel["mgt8_required"].result is True
    assert panel["aoc4_variant"].result == "AOC-4 XBRL"
    assert panel["rule_9b_applicable"].result is True
    assert panel["board_meeting_regime"].result == "REGULAR"
    assert all(c.citation for c in panel.values())


def test_board_regimes(rp, demo):
    assert board_meeting_regime(ctx_for(rp, demo["alpha"], "FY2026-27")).result == "RELAXED"
    assert board_meeting_regime(ctx_for(rp, demo["beta"], "FY2025-26")).result == "NA"
    two = replace(demo["beta"]["entity"], single_director=False)
    assert board_meeting_regime(ctx_for(rp, demo["beta"], "FY2025-26", entity=two)).result == "RELAXED"
    su = replace(demo["gamma"]["entity"], startup=True)
    assert "start-up" in board_meeting_regime(ctx_for(rp, demo["gamma"], "FY2025-26", entity=su)).reasons[0]
    dorm = replace(demo["epsilon"]["entity"], status="DORMANT")
    assert board_meeting_regime(ctx_for(rp, demo["epsilon"], "FY2025-26", entity=dorm)).result == "RELAXED"
    assert board_meeting_regime(ctx_for(rp, demo["delta"], "FY2024-25")).result == "REGULAR"   # ambiguous -> strict
    assert board_meeting_regime(ctx_for(rp, demo["zeta"], "FY2025-26")).result == "NA"


def test_aoc4_variants(rp, demo):
    d = demo["alpha"]
    base = {"FY2026-27": FactsIn("FY2026-27", paid_up_capital=1 * L, turnover=1 * CR, ind_as=True)}
    e = d["entity"]
    assert classify_aoc4(ctx_for(rp, d, "FY2026-27", facts=base)).result == "AOC-4 XBRL"          # Ind AS
    assert classify_aoc4(ctx_for(rp, d, "FY2026-27", facts=base, entity=replace(e, nbfc=True))).result == "AOC-4 NBFC (Ind AS)"
    assert classify_aoc4(ctx_for(rp, d, "FY2026-27", facts=base, entity=replace(e, excluded_sector=True))).result == "AOC-4"
    big = {"FY2026-27": FactsIn("FY2026-27", paid_up_capital=1 * L, turnover=120 * CR)}
    assert classify_aoc4(ctx_for(rp, d, "FY2026-27", facts=big)).result == "AOC-4 XBRL"
    assert classify_aoc4(ctx_for(rp, d, "FY2026-27", entity=replace(e, listed_subsidiary=True))).result == "AOC-4 XBRL"
    hfc = replace(e, hfc=True, paid_up_capital=6 * CR)
    c = classify_aoc4(ctx_for(rp, d, "FY2026-27", facts={}, entity=hfc))
    assert c.result == "AOC-4" and "excluded sector" in c.reasons[-1]
    assert classify_aoc4(ctx_for(rp, d, "FY2026-27")).result == "AOC-4"


def test_mgt8_delta(rp, demo):
    assert classify_mgt8(ctx_for(rp, demo["delta"], "FY2025-26")).result is True        # turnover ₹80 cr ≥ ₹50 cr
    assert classify_mgt8(ctx_for(rp, demo["alpha"], "FY2026-27")).result is False


def test_csr(rp, demo):
    d = demo["gamma"]
    assert classify_csr(ctx_for(rp, d, "FY2025-26")).result is False                 # prev net profit ₹4 cr
    f = dict(d["facts"])
    f["FY2024-25"] = replace(f["FY2024-25"], net_profit=5 * CR)
    assert classify_csr(ctx_for(rp, d, "FY2025-26", facts=f)).result is True
    f["FY2025-26"] = replace(f["FY2025-26"], csr_override=False)
    c = classify_csr(ctx_for(rp, d, "FY2025-26", facts=f))
    assert c.result is False and "overridden" in c.reasons[-1]


def test_secretarial_audit_uses_fy_end_borrowings(rp, demo):
    d = demo["gamma"]
    f = dict(d["facts"])
    f["FY2024-25"] = replace(f["FY2024-25"], bank_borrowings_max=150 * CR, bank_borrowings_at_fy_end=90 * CR)
    assert classify_secretarial_audit(ctx_for(rp, d, "FY2025-26", facts=f)).result is False   # correction C10
    f["FY2024-25"] = replace(f["FY2024-25"], bank_borrowings_at_fy_end=100 * CR)
    assert classify_secretarial_audit(ctx_for(rp, d, "FY2025-26", facts=f)).result is True
    e = demo["epsilon"]
    ef = {"FY2024-25": FactsIn("FY2024-25", paid_up_capital=50 * CR), "FY2025-26": FactsIn("FY2025-26")}
    assert classify_secretarial_audit(ctx_for(rp, e, "FY2025-26", facts=ef)).result is True
    assert classify_secretarial_audit(ctx_for(rp, e, "FY2025-26")).result is False


def test_internal_audit(rp, demo):
    d = demo["gamma"]
    f = dict(d["facts"])
    assert classify_internal_audit(ctx_for(rp, d, "FY2025-26", facts=f)).result is False    # ₹140 cr turnover
    f["FY2024-25"] = replace(f["FY2024-25"], bank_borrowings_max=100 * CR)
    assert classify_internal_audit(ctx_for(rp, d, "FY2025-26", facts=f)).result is True
    e = demo["epsilon"]
    ef = {"FY2024-25": FactsIn("FY2024-25", deposits_max=25 * CR)}
    assert classify_internal_audit(ctx_for(rp, e, "FY2025-26", facts=ef)).result is True
    listed = replace(e["entity"], entity_type="PUBLIC_LISTED")
    assert classify_internal_audit(ctx_for(rp, e, "FY2025-26", entity=listed)).result is True


def test_rule_9b(rp, demo, gen):
    fy, c = rule_9b_trigger_fy(ctx_for(rp, demo["theta"], "FY2025-26"))
    assert fy is None and "small company at every FY end" in c.reasons[0]
    fy, c = rule_9b_trigger_fy(ctx_for(rp, demo["delta"], "FY2025-26"))
    assert fy.key == "FY2022-23"                             # ₹8 cr paid-up > ₹4 cr limit then
    spec = gen("delta")[("DEMAT_9B", "FY2022-23")]
    assert spec.needs_decision == "9B_REVERSION"             # small again from FY 2025-26 (I6)
    assert gen("delta", decisions={"9B_REVERSION": "CONTINUE"})[("DEMAT_9B", "FY2022-23")].needs_decision is None
    fy, c = rule_9b_trigger_fy(ctx_for(rp, demo["epsilon"], "FY2025-26"))
    assert fy is None and "private" in c.reasons[0]
    gov = replace(demo["gamma"]["entity"], government=True)
    assert rule_9b_trigger_fy(ctx_for(rp, demo["gamma"], "FY2025-26", entity=gov))[0] is None


def test_llp_classifications(rp, demo):
    z = demo["zeta"]
    assert classify_small_llp(ctx_for(rp, z, "FY2025-26")).result is True
    assert classify_llp_audit(ctx_for(rp, z, "FY2025-26")).result is False
    old = classify_small_llp(ctx_for(rp, z, "FY2021-22"))
    assert old.result is False and "before 01-04-2022" in old.reasons[0]
    names = [c.name for c in classify_all(ctx_for(rp, z, "FY2025-26"))]
    assert names == ["small_llp", "llp_audit_required"]


def test_fact_fallbacks_mark_stale(rp, demo):
    d = demo["gamma"]
    c = ctx_for(rp, d, "FY2026-27")                          # no FY2026-27 facts
    assert c.fact("paid_up_capital") == 12 * CR and c.stale
    c = ctx_for(rp, d, "FY2025-26")
    assert c.fact("turnover") == 150 * CR and not c.stale
    assert c.fact("agm_date", stale_ok=False) == D(2026, 9, 26)
    c = ctx_for(rp, d, "FY2025-26", facts={})
    assert c.fact("paid_up_capital") == 12 * CR and c.stale       # entity master
    c = ctx_for(rp, d, "FY2025-26", facts={})
    assert c.fact("net_worth") is None and c.stale
    c = ctx_for(rp, d, "FY2013-14", facts={"FY2014-15": FactsIn("FY2014-15", turnover=5 * CR)})
    assert c.fact("turnover") == 5 * CR and c.stale                # nearest later FY
    c = ctx_for(rp, d, "FY2025-26", facts={"FY2025-26": FactsIn("FY2025-26")})
    assert c.fact("net_worth") is None and not c.stale             # row exists, field blank, nothing to borrow


def test_expressions(rp, demo):
    c = ctx_for(rp, demo["alpha"], "FY2026-27")
    assert evaluate({"any_of": ["public_company", "has_share_capital"]}, c)
    assert evaluate({"not": "public_company"}, c)
    assert not evaluate({"all_of": ["always", "public_company"]}, c)
    validate_expr({"all_of": ["always", {"not": "is_dormant"}]})
    for bad in ["nope", {"all_of": []}, {"xor": ["always"]}, {"not": "nope"}, 5]:
        with pytest.raises(ValueError):
            validate_expr(bad)


def test_inr_short():
    assert inr_short(None) == "not entered"
    assert inr_short(12 * CR) == "₹12 cr" and inr_short(8 * L) == "₹8 lakh"
