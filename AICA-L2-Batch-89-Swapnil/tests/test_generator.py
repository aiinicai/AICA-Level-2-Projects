"""Golden tests 1–11 (brief §13, as corrected in docs/LEGAL_NOTES.md)."""
from dataclasses import replace
from datetime import date

import pytest

from engine import generate
from engine.types import EventIn, FactsIn, PersonIn

D = date


# ---------------------------------------------------------------- golden 1
def test_g01_alpha_first_year(gen):
    o = gen("alpha")
    assert o[("FIRST_BM", "ONCE")].due_date == D(2026, 2, 19)
    assert o[("FIRST_AUDITOR", "ONCE")].due_date == D(2026, 2, 19)
    # corrected: s.56(4)(a) "two months" -> 20-03-2026 (brief said 21-03-2026)
    assert o[("SHARE_CERT", "ONCE")].due_date == D(2026, 3, 20)
    assert o[("INC20A", "ONCE")].due_date == D(2026, 7, 19)
    dpt3 = o[("DPT3", "FY2025-26")]
    assert dpt3.due_date == D(2026, 6, 30)
    assert dpt3.due_date < D(2027, 3, 31)          # before the first FY closes
    assert o[("AGM", "FY2026-27")].due_date == D(2027, 12, 31)
    assert ("AGM", "FY2025-26") not in o           # the first FY is FY2026-27 (20-01-2026 to 31-03-2027)


def test_g01_first_auditor_adt1_setting(gen):
    o = gen("alpha")
    s = o[("ADT1_FIRST", "ONCE")]
    assert s.due_date == D(2026, 3, 6) and s.provisional and s.interpretation
    assert ("ADT1_FIRST", "ONCE") not in gen("alpha", settings={"adt1_for_first_auditor": False})
    ev = EventIn(9, "FIRST_AUDITOR_APPOINTED", D(2026, 2, 10))
    s2 = gen("alpha", events=[ev])[("ADT1_FIRST", "ONCE")]
    assert s2.due_date == D(2026, 2, 25) and not s2.provisional


# ---------------------------------------------------------------- golden 2
def test_g02_alpha_provisional_then_actual_agm(gen, demo):
    o = gen("alpha")
    aoc4, mgt7 = o[("AOC4", "FY2026-27")], o[("MGT7", "FY2026-27")]
    assert aoc4.due_date == D(2028, 1, 30) and aoc4.provisional
    assert mgt7.due_date == D(2028, 2, 29) and mgt7.provisional     # leap year
    assert mgt7.form == "MGT-7A"
    assert aoc4.anchor_type == "AGM_DEADLINE"

    facts = dict(demo["alpha"]["facts"])
    facts["FY2026-27"] = replace(facts["FY2026-27"], agm_date=D(2027, 9, 15))
    o2 = gen("alpha", facts=facts)
    assert o2[("AOC4", "FY2026-27")].due_date == D(2027, 10, 15)
    assert o2[("MGT7", "FY2026-27")].due_date == D(2027, 11, 14)
    assert o2[("ADT1", "FY2026-27")].due_date == D(2027, 9, 30)
    assert not o2[("AOC4", "FY2026-27")].provisional
    assert o2[("AOC4", "FY2026-27")].key == aoc4.key             # same stable key -> service keeps history


# ---------------------------------------------------------------- golden 3
def test_g03_alpha_directors_kyc(gen):
    o = gen("alpha")
    tri = o[("DIR3KYC_TRIENNIAL", "KYC-CYCLE-2026-27..2028-29", "10000101")]
    # corrected per MCA illustration (partner decision Q1): DIN allotted FY 2025-26 -> 30-06-2029
    assert tri.due_date == D(2029, 6, 30)
    assert tri.interpretation and tri.key == "person:10000101:DIR3KYC_TRIENNIAL:KYC-CYCLE-2026-27..2028-29"
    chg = o[("DIR3KYC_CHANGE", "CHG-2026-08-05", "10000101")]
    assert chg.due_date == D(2026, 9, 4)
    assert not any(k[0] == "DIR3KYC_ANNUAL" for k in o)


def test_g03_legacy_din_and_override(gen, demo):
    o = gen("beta")
    assert o[("DIR3KYC_TRIENNIAL", "KYC-CYCLE-2025-26..2027-28", "10000201")].due_date == D(2028, 6, 30)
    p = replace(demo["alpha"]["persons"][1], kyc_override_first_due=D(2028, 6, 30))
    o2 = gen("alpha", persons=[p])
    s = o2[("DIR3KYC_TRIENNIAL", "KYC-CYCLE-2025-26..2027-28", "10000102")]
    assert s.due_date == D(2028, 6, 30) and "override" in " ".join(s.notes)


def test_director_on_three_boards_gets_one_kyc(rp, demo):
    p = PersonIn(900, "Shared Director", "10000900", D(2018, 1, 1), last_annual_kyc_fy="FY2024-25")
    keys = []
    for name in ("alpha", "gamma", "delta"):
        d = demo[name]
        keys += [s.key for s in generate(d["entity"], d["facts"], [], [p], rp, D(2026, 9, 25))
                 if s.rule_code == "DIR3KYC_TRIENNIAL"]
    assert len(set(keys)) == 1


# ---------------------------------------------------------------- golden 4
def test_g04_beta_opc(gen):
    o = gen("beta")
    assert o[("AOC4_OPC", "FY2025-26")].due_date == D(2026, 9, 27)
    m = o[("MGT7_OPC", "FY2025-26")]
    assert m.due_date == D(2026, 11, 29) and m.form == "MGT-7A" and m.interpretation
    assert not any(k[0] in ("AGM", "AOC4", "MGT7", "BOARD_MTGS", "FIRST_BM") for k in o)   # single-director OPC


# ---------------------------------------------------------------- golden 5
def test_g05_gamma_non_small(gen):
    o = gen("gamma")
    assert o[("MGT7", "FY2025-26")].form == "MGT-7"
    assert ("MGT8", "FY2025-26") in o
    assert o[("AOC4", "FY2025-26")].form == "AOC-4 XBRL"
    assert o[("AOC4", "FY2025-26")].due_date == D(2026, 10, 26)
    assert o[("MGT7", "FY2025-26")].due_date == D(2026, 11, 25)
    assert o[("ADT1", "FY2025-26")].due_date == D(2026, 10, 11)
    assert o[("PAS6", "H1-FY2026-27")].due_date == D(2026, 11, 29)
    assert o[("PAS6", "H2-FY2026-27")].due_date == D(2027, 5, 30)
    assert ("PAS6", "H2-FY2023-24") not in o                  # ISIN obtained 10-09-2024


def test_gamma_rule_9b_and_extension(gen):
    o = gen("gamma")
    d = o[("DEMAT_9B", "FY2022-23")]
    assert d.due_date == D(2025, 6, 30)                        # 30-09-2024 extended by PAS Amdt Rules 2025
    assert any("extended" in n for n in d.notes)
    assert d.facts_stale                                       # FY2022-23 facts not entered


def test_gamma_pre_engagement(gen):
    o = gen("gamma")
    assert o[("AOC4", "FY2019-20")].pre_engagement
    assert not o[("AOC4", "FY2025-26")].pre_engagement


# ---------------------------------------------------------------- golden 6
def test_g06_delta_small_under_new_limits(gen):
    o = gen("delta")
    assert o[("MGT7", "FY2025-26")].form == "MGT-7A"
    # extra consequences found in Phase 0 (C18)
    assert o[("AOC4", "FY2025-26")].form == "AOC-4 XBRL"
    assert ("MGT8", "FY2025-26") in o


def test_g06_delta_fy2024_25_ambiguous(gen):
    o = gen("delta")
    m = o[("MGT7", "FY2024-25")]
    assert m.needs_decision == "SMALL:FY2024-25" and "decision" in m.form
    o2 = gen("delta", decisions={"SMALL:FY2024-25": "NOT_SMALL"})
    assert o2[("MGT7", "FY2024-25")].form == "MGT-7" and o2[("MGT7", "FY2024-25")].needs_decision is None
    o3 = gen("delta", decisions={"SMALL:FY2024-25": "SMALL"})
    assert o3[("MGT7", "FY2024-25")].form == "MGT-7A"
    # evaluated before 01-12-2025 there is no ambiguity: old limits -> not small
    assert gen("delta", as_of=D(2025, 11, 15))[("MGT7", "FY2024-25")].form == "MGT-7"


# ---------------------------------------------------------------- golden 7
def test_g07_epsilon_events(gen):
    o = gen("epsilon", as_of=D(2026, 10, 15))
    assert o[("DIR12", "EVT-2026-10-10", 505)].due_date == D(2026, 11, 9)
    assert o[("PAS3_PP", "EVT-2026-10-01", 501)].due_date == D(2026, 10, 16)
    assert o[("PAS3", "EVT-2026-10-01", 502)].due_date == D(2026, 10, 31)
    assert ("PAS3", "EVT-2026-10-01", 501) not in o and ("PAS3_PP", "EVT-2026-10-01", 502) not in o
    assert o[("MGT14", "EVT-2026-10-05", 504)].due_date == D(2026, 11, 4)
    assert o[("CHG1", "EVT-2026-10-03", 503)].due_date == D(2026, 11, 2)
    assert ("DIR_APPT_CHECKLIST", "EVT-2026-10-10", 505) in o
    assert o[("PAS6", "H1-FY2026-27")].due_date == D(2026, 11, 29)      # Rule 9A unlisted public


def test_md_appointment_mr1_only_for_public(gen, demo):
    ev = EventIn(77, "MD_WTD_APPOINTED", D(2026, 10, 1))
    assert ("MR1", "EVT-2026-10-01", 77) in gen("epsilon", events=[ev])
    assert ("MR1", "EVT-2026-10-01", 77) not in gen("gamma", events=[ev])
    sub = replace(demo["gamma"]["entity"], subsidiary_of_public=True)
    assert ("MR1", "EVT-2026-10-01", 77) in gen("gamma", events=[ev], entity=sub)


# ---------------------------------------------------------------- golden 8
def test_g08_eta_llp_election(gen, demo):
    o = gen("eta")
    assert o[("LLP_FORM3_INC", "ONCE")].due_date == D(2025, 12, 15)
    assert o[("LLP_FORM11", "FY2026-27")].due_date == D(2027, 5, 30)
    assert o[("LLP_FORM8", "FY2026-27")].due_date == D(2027, 10, 30)
    assert ("LLP_FORM11", "FY2025-26") not in o
    short = replace(demo["eta"]["entity"], llp_elect_longer_first_fy=False)
    o2 = gen("eta", entity=short)
    assert o2[("LLP_FORM11", "FY2025-26")].due_date == D(2026, 5, 30)
    assert o2[("LLP_FORM8", "FY2025-26")].due_date == D(2026, 10, 30)


def test_llp_audit_only_when_both_limits_crossed(gen, demo):
    assert not any(k[0] == "LLP_AUDIT" for k in gen("zeta"))
    facts = {"FY2025-26": FactsIn("FY2025-26", turnover=50 * 100_000, llp_contribution=8 * 100_000)}
    assert ("LLP_AUDIT", "FY2025-26") not in gen("zeta", facts=facts)       # contribution ≤ 25 L -> exempt
    facts = {"FY2025-26": FactsIn("FY2025-26", turnover=50 * 100_000, llp_contribution=30 * 100_000)}
    assert gen("zeta", facts=facts)[("LLP_AUDIT", "FY2025-26")].due_date == D(2026, 9, 30)


# ---------------------------------------------------------------- golden 9
def test_g09_msme1(gen):
    o = gen("alpha", flags={"H1-FY2026-27": {"msme_over_45": True}})
    assert o[("MSME1_H1", "H1-FY2026-27")].due_date == D(2026, 10, 31)
    assert not any(k[0].startswith("MSME1") and k[1] != "H1-FY2026-27" for k in o)
    assert not any(k[0].startswith("MSME1") for k in gen("alpha", flags={}))     # no nil return
    o2 = gen("alpha", flags={"H2-FY2026-27": {"msme_over_45": True}})
    assert o2[("MSME1_H2", "H2-FY2026-27")].due_date == D(2027, 4, 30)


# --------------------------------------------------------------- golden 10
def test_g10_rollover_and_idempotence(rp, demo):
    for d in demo.values():
        before = {s.key for s in generate(d["entity"], d["facts"], d["events"], d["persons"], rp, D(2026, 3, 31),
                                          period_flags=d["flags"])}
        after = generate(d["entity"], d["facts"], d["events"], d["persons"], rp, D(2027, 4, 1), period_flags=d["flags"])
        keys = {s.key for s in after}
        e = d["entity"]
        code = "LLP_FORM11" if e.is_llp else ("AOC4_OPC" if e.entity_type == "OPC" else "AOC4")
        assert f"{e.id}:{code}:FY2026-27" in keys, e.name
        assert f"{e.id}:{code}:FY2027-28" in keys and f"{e.id}:{code}:FY2027-28" not in before
        again = generate(d["entity"], d["facts"], d["events"], d["persons"], rp, D(2027, 4, 1), period_flags=d["flags"])
        assert [(s.key, s.due_date) for s in again] == [(s.key, s.due_date) for s in after]
        assert len(keys) == len(after)                                            # no duplicate keys


def test_facts_stale_for_future_fy(gen):
    o = gen("gamma")
    assert o[("MGT7", "FY2026-27")].facts_stale
    assert not o[("MGT7", "FY2025-26")].facts_stale


def test_agm_not_held_runs_from_deadline(gen):
    o = gen("theta")
    a = o[("AOC4", "FY2023-24")]
    assert a.due_date == D(2024, 10, 30) and a.agm_not_held and not a.provisional
    assert o[("MGT7", "FY2023-24")].due_date == D(2024, 11, 29)


# --------------------------------------------------------------- golden 11
def test_g11_law_change_annual_to_triennial(gen, demo):
    p = replace(demo["beta"]["persons"][0], last_annual_kyc_fy="FY2023-24")
    o = gen("beta", persons=[p])
    assert o[("DIR3KYC_ANNUAL", "FY2024-25", "10000201")].due_date == D(2025, 9, 30)
    assert ("DIR3KYC_ANNUAL", "FY2025-26", "10000201") not in o          # no 30-09-2026 annual KYC
    assert not any(s.due_date == D(2026, 9, 30) and s.rule_code.startswith("DIR3KYC") for s in o.values())
    assert o[("DIR3KYC_TRIENNIAL", "KYC-CYCLE-2025-26..2027-28", "10000201")].due_date == D(2028, 6, 30)


def test_detail_change_before_triennial_rule_ignored(gen, demo):
    p = replace(demo["alpha"]["persons"][0], detail_changes=[D(2026, 2, 1)])
    assert not any(k[0] == "DIR3KYC_CHANGE" for k in gen("alpha", persons=[p]))


# --------------------------------------------------------- other coverage
def test_spec_carries_traceability(gen, rp):
    s = gen("gamma")[("AOC4", "FY2025-26")]
    assert s.rule_version == rp.version and s.rule_hash == rp.rule("AOC4").content_hash
    assert s.law.startswith("s.137(1)") and s.fee_regime == "PER_DAY_100" and s.verified is False


def test_board_approval_anchor_public(gen, demo):
    o = gen("epsilon")
    s = o[("MGT14_FS", "FY2025-26")]
    assert s.provisional
    facts = dict(demo["epsilon"]["facts"])
    facts["FY2025-26"] = replace(facts["FY2025-26"], board_approval_date=D(2026, 8, 20))
    s2 = gen("epsilon", facts=facts)[("MGT14_FS", "FY2025-26")]
    assert s2.due_date == D(2026, 9, 19) and not s2.provisional


def test_dormant_and_cost_audit_and_csr(gen, demo):
    e = replace(demo["gamma"]["entity"], status="DORMANT")
    assert ("MSC3", "FY2025-26") in gen("gamma", entity=e)
    facts = dict(demo["gamma"]["facts"])
    facts["FY2025-26"] = replace(facts["FY2025-26"], cost_audit_applicable=True, has_subs_assoc_jv=True)
    o = gen("gamma", facts=facts)
    assert o[("CRA2", "FY2025-26")].due_date == D(2025, 9, 28)
    assert ("CRA4", "FY2025-26") in o and ("AOC4_CFS", "FY2025-26") in o
    facts["FY2024-25"] = replace(facts["FY2024-25"], net_profit=6 * 10_000_000)
    assert gen("gamma", facts=facts)[("CSR2", "FY2025-26")].due_date == D(2026, 10, 26)


def test_other_company_events(gen):
    evs = [EventIn(1, "CHARGE_SATISFIED", D(2026, 5, 1)), EventIn(2, "AUDITOR_CASUAL_VACANCY", D(2026, 5, 1), {"cause": "RESIGNATION"}),
           EventIn(3, "BEN1_RECEIVED", D(2026, 5, 1)), EventIn(4, "RO_SHIFT_SAME_CITY", D(2026, 5, 1)),
           EventIn(5, "DIRECTOR_RESIGNED", D(2026, 5, 1))]
    o = gen("gamma", events=evs)
    assert o[("CHG4", "EVT-2026-05-01", 1)].due_date == D(2026, 5, 31)
    assert o[("CASUAL_VACANCY_GM", "EVT-2026-05-01", 2)].due_date == D(2026, 8, 31)
    assert ("BEN2", "EVT-2026-05-01", 3) in o and ("INC22", "EVT-2026-05-01", 4) in o
    assert ("DIR11", "EVT-2026-05-01", 5) in o and ("DIR12", "EVT-2026-05-01", 5) in o


def test_llp_events(gen):
    evs = [EventIn(1, "PARTNER_CHANGE", D(2026, 6, 1)), EventIn(2, "LLP_BENEFICIAL_DECL_RECEIVED", D(2026, 6, 1))]
    o = gen("zeta", events=evs)
    assert o[("LLP_FORM4", "EVT-2026-06-01", 1)].due_date == D(2026, 7, 1)
    assert ("LLP_4D", "EVT-2026-06-01", 2) in o


def test_small_status_judged_on_filing_date(rp, demo):
    """I5: an FY is judged under the limits in force when its return was actually filed."""
    d = demo["delta"]

    def mgt7(filing_dates):
        specs = generate(d["entity"], d["facts"], [], [], rp, D(2026, 9, 25), filing_dates=filing_dates)
        return next(s for s in specs if s.rule_code == "MGT7" and s.period_key == "FY2024-25")

    assert mgt7({"FY2024-25": D(2025, 11, 15)}).form == "MGT-7"                     # filed under old limits
    assert mgt7({"FY2024-25": D(2026, 1, 10)}).needs_decision == "SMALL:FY2024-25"  # filed after 01-12-2025
    assert mgt7({}).needs_decision == "SMALL:FY2024-25"                              # unfiled: judged today
    old = next(s for s in generate(d["entity"], d["facts"], [], [], rp, D(2026, 9, 25),
                                   filing_dates={"FY2017-18": D(2018, 11, 20)})
               if s.rule_code == "MGT7" and s.period_key == "FY2017-18")
    assert old.needs_decision is None and old.form == "MGT-7"
