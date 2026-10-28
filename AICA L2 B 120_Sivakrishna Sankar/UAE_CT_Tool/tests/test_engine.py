import copy

import pytest

from helpers import confirm_all, make_project, make_scaled_project, scenario_answers
from ct_tool.pipeline import run_analysis
from ct_tool.questionnaire import RB_OPTIONS

FX = 3.6725


def analysed(rb="A", **extra):
    p = make_project("USD")
    p.answers = scenario_answers(rb)
    p.answers.update(extra)
    return p, run_analysis(p)


def test_nothing_is_in_the_computation_until_it_is_confirmed():
    p, an = analysed()
    assert an.adjs and all(a.status == "Proposed" for a in an.adjs)
    assert an.comp.B == 0 and an.comp.C == 0
    assert an.comp.E == pytest.approx(an.st.profit_for_year)
    assert an.pending_impact()["count"] == len(an.adjs)


def test_confirm_one_adjustment_moves_only_that_amount():
    p, an = analysed()
    ent = [a for a in an.adjs if a.row == "a_entertainment"][0]
    assert ent.amount == pytest.approx(96_000 * FX * 0.5)
    p.decisions[ent.adj_id] = {"status": "Confirmed", "reviewer": "T", "support_ref": "x"}
    an2 = run_analysis(p)
    assert an2.comp.C == pytest.approx(ent.amount)
    assert an2.comp.E == pytest.approx(an.comp.E + ent.amount)


def test_blocked_adjustment_cannot_be_confirmed_without_an_override_note():
    p, an = analysed()
    blocked = [a for a in an.adjs if a.blocking][0]
    p.decisions[blocked.adj_id] = {"status": "Confirmed"}
    an2 = run_analysis(p)
    assert [a for a in an2.adjs if a.adj_id == blocked.adj_id][0].status == "Proposed"
    assert an2.warnings
    p.decisions[blocked.adj_id]["override_note"] = "Evidence received 1 Oct"
    an3 = run_analysis(p)
    assert [a for a in an3.adjs if a.adj_id == blocked.adj_id][0].status == "Confirmed"


def test_rejected_adjustment_stays_on_record_but_out_of_the_figures():
    p, an = analysed()
    a0 = an.adjs[0]
    p.decisions[a0.adj_id] = {"status": "Rejected"}
    an2 = run_analysis(p)
    assert any(a.adj_id == a0.adj_id and a.status == "Rejected" for a in an2.adjs)
    assert an2.comp.B == 0 and an2.comp.C == 0


def test_user_amount_override_is_applied():
    p, an = analysed()
    ent = [a for a in an.adjs if a.row == "a_entertainment"][0]
    p.decisions[ent.adj_id] = {"status": "Confirmed", "amount": 1000.0}
    an2 = run_analysis(p)
    assert an2.comp.C == pytest.approx(1000.0)


def test_tax_is_9_percent_above_375000_and_nil_below():
    p, an = analysed()
    an = confirm_all(p, an)
    c = an.comp
    assert c.tax_9 == pytest.approx(round((c.E - 375_000) * 0.09))
    small = make_scaled_project(__import__("tempfile").mkdtemp(), "AED", 0.0005)
    small.answers = scenario_answers("none")
    a2 = run_analysis(small)
    if a2.comp.E <= 375_000:
        assert a2.comp.payable == 0


def test_realisation_basis_scopes_change_only_the_unrealised_items():
    res = {}
    for rb in ("none", "A", "B"):
        p, an = analysed(rb)
        an = confirm_all(p, an)
        res[rb] = an.comp
    assert res["none"].B == pytest.approx(1_101_750)                 # dividend exemption only (this adjustment is not an election item)
    assert res["A"].B == pytest.approx(1_101_750 + 85_000 * FX)       # + unrealised FV gain deducted
    assert res["A"].C > res["none"].C                                 # + provision charge added back under scope A
    assert res["B"].B <= res["A"].B


def test_election_needs_first_period_and_documentation():
    p, an = analysed(first_period="Subsequent tax period", realisation_evidence="Unknown")
    rb = [a for a in an.adjs if a.category == "Realisation basis"]
    assert rb and all(a.blocking for a in rb)


def test_unknown_election_is_not_applied_automatically():
    p, an = analysed(realisation_basis=RB_OPTIONS[3])
    assert not [a for a in an.adjs if a.category == "Realisation basis" and not a.blocking]
    assert any(o["topic"] == "Realisation basis" for o in an.open_items)


def test_dividend_exemption_not_applied_when_conditions_unmet():
    p, an = analysed(dividends=[{"account": "4200", "payer": "X", "jurisdiction": "Foreign company", "ownership": 2, "cost": 100, "months": 3, "subject_tax": "No"}])
    assert not [a for a in an.adjs if a.row in ("d_participating", "d_dividends_resident")]
    assert any(o["topic"] == "Exempt income" for o in an.open_items)


def test_loss_relief_capped_at_75_percent_of_taxable_income():
    p, an = analysed(opening_losses=500_000_000.0)
    an = confirm_all(p, an)
    c = an.comp
    assert c.relief_cf == pytest.approx(0.75 * c.D)
    assert c.E == pytest.approx(0.25 * c.D)
    assert c.loss_closing == pytest.approx(500_000_000.0 - c.relief_cf)


def test_a_loss_year_produces_no_tax_and_carries_the_loss_forward():
    p = make_project("USD")
    p.answers = scenario_answers("none")
    for a in p.tb.accounts:
        if a.code == "4000":                                      # cut sales so the year makes a loss; keep the TB balanced via cash
            a.net += 20_000_000
            a.credit -= 20_000_000
        if a.code == "1000":
            a.net -= 20_000_000
            a.debit -= 20_000_000
    an = run_analysis(p)
    assert an.comp.E < 0 and an.comp.payable == 0
    assert an.comp.loss_closing == pytest.approx(-an.comp.E)


def test_foreign_tax_credit_needs_proof_and_non_exempt_income_and_is_capped():
    base = scenario_answers("A")["foreign_taxes"][0]
    for proof, exempt, expect in (("Yes", "Yes", 0.0), ("Yes", "Unknown", 0.0), ("No", "No", 0.0)):
        p, an = analysed(foreign_taxes=[{**base, "proof": proof, "exempt_income": exempt}])
        assert confirm_all(p, an).comp.credit == expect
    p, an = analysed(foreign_taxes=[{**base, "proof": "Yes", "exempt_income": "No"}])
    c = confirm_all(p, an).comp
    assert c.credit == pytest.approx(0.09 * base["income"])           # 10% paid, but credit capped at the 9% UAE tax on that income


def test_sbr_applied_only_when_elected_and_conditions_met():
    import tempfile
    small = make_scaled_project(tempfile.mkdtemp(), "AED", 0.03)
    small.answers = {**scenario_answers("none"), "sbr_elect": "Yes", "mne_group": "No", "revenue_previous": 0.0}
    an = run_analysis(small)
    assert an.comp.sbr["potential"] and an.comp.basis == "SBR" and an.comp.payable == 0
    # elected but revenue above AED 3m -> relief refused with an explanation
    p, an2 = analysed(sbr_elect="Yes", mne_group="No")
    assert an2.comp.basis != "SBR" and an2.comp.payable > 0
    assert any("Small Business Relief" in n for n in an2.comp.notes)
    # eligible but NOT elected -> not applied automatically
    small.answers["sbr_elect"] = "No"
    assert run_analysis(small).comp.basis != "SBR"


def test_qfzp_claim_without_substance_is_not_given_the_qfzp_rate():
    p, an = analysed(entity_status="Free Zone", qfzp_claimed="Yes", qfzp_substance="Unknown", qfzp_audited="Yes", qfzp_domestic_pe="No")
    assert an.comp.basis != "QFZP"
    assert any("QFZP" in n for n in an.comp.notes)


def test_interest_limitation_proposed_when_net_interest_exceeds_threshold():
    p = make_project("USD")
    p.answers = scenario_answers("none")
    for a in p.tb.accounts:
        if a.code == "6070":
            a.net += 5_000_000
            a.debit += 5_000_000
        if a.code == "1000":
            a.net -= 5_000_000
            a.debit -= 5_000_000
    an = run_analysis(p)
    it = an.comp.interest_test
    assert it["net_interest"] > 12_000_000
    assert it["excess"] >= 0
    if it["excess"] > 0:
        assert any(a.row == "a_interest_excess" and a.status == "Proposed" for a in an.adjs)


def test_scenarios_compare_three_options_and_do_not_pick_one():
    p, an = analysed()
    assert [s["option"] for s in an.scenarios] == ["Option 1 - scope A", "Option 2 - scope B", "Option 3 - current basis"]


def test_only_confirmed_adjustments_drive_sheet_applicability():
    p, an = analysed()
    assert an.applic["Disallowed Expenses"][0] is False and an.applic["Adjustments"][0] is False
    an = confirm_all(p, an)
    assert an.applic["Disallowed Expenses"][0] is True and an.applic["Adjustments"][0] is True
    assert an.applic["Freezone"][0] is False and an.applic["Tax Loss Carried Forward"][0] is False
