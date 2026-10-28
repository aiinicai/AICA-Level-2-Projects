import pytest

from helpers import make_project, scenario_answers
from ct_tool.fx import default_settings, validate_settings
from ct_tool.mapping import map_all, infer_classes
from ct_tool.pipeline import run_analysis


def test_aed_needs_no_conversion_and_no_fx_sheet():
    p = make_project("AED")
    an = run_analysis(p)
    assert an.tr.diff_applicable is False
    assert an.st.profit_for_year == pytest.approx(4_210_500.0)
    assert an.applic["FX Rates"][0] is False


def test_usd_uses_peg_3_6725_everywhere():
    an = run_analysis(make_project("USD"))
    assert an.st.profit_for_year == pytest.approx(4_210_500.0 * 3.6725)
    assert all(a.rate == pytest.approx(3.6725) for a in an.tr.accounts)
    assert an.applic["FX Rates"][0] is True


def test_non_peg_currency_without_rates_is_an_error():
    fx = default_settings("EUR", "2025-01-01", "2025-12-31")
    msgs = validate_settings(fx)
    assert any(s == "ERROR" for s, _ in msgs)
    p = make_project("EUR")
    p.fx = fx
    with pytest.raises(ValueError):
        run_analysis(p)


def test_eur_manual_rates_translate_and_show_a_labelled_translation_difference():
    p = make_project("EUR", rates={"pl": 4.0, "closing": 4.2, "equity": 3.9})
    an = run_analysis(p)
    assert an.st.profit_for_year == pytest.approx(4_210_500.0 * 4.0)
    assert an.tr.diff_applicable
    # balance sheet must still balance, with the difference shown as its own derived equity line
    assert abs(an.st.bs_difference) < 0.5
    labels = [r.label for r in an.st.bs_rows]
    assert any("translation" in l.lower() for l in labels)
    assert any(c.id == "FS-03" for c in an.checks)


def test_pl_rate_changes_profit_but_not_the_tb_foot():
    a = run_analysis(make_project("EUR", rates={"pl": 4.0, "closing": 4.2, "equity": 3.9}))
    b = run_analysis(make_project("EUR", rates={"pl": 4.1, "closing": 4.2, "equity": 3.9}))
    assert b.st.profit_for_year > a.st.profit_for_year
    assert abs(b.st.bs_difference) < 0.5


def test_mapping_of_synthetic_accounts():
    p = make_project("USD")
    ms = {m.account.code: m.line for m in map_all(p.tb.accounts)}
    expect = {"1000": "A_CASH", "1110": "A_TRADE_REC", "1200": "A_RP", "1400": "A_SUB_INV", "1410": "A_FIN_INV", "1510": "A_PPE", "2200": "L_RP",
              "2400": "L_EOSB", "3000": "E_CAPITAL", "3100": "E_RE", "4200": "P_DIV", "4300": "P_FV", "6020": "P_ENT", "6030": "P_DON", "6040": "P_FINES",
              "6070": "P_FIN", "6090": "P_PROV", "6120": "P_GEN", "6140": "P_TAX", "6150": "P_GEN", "6160": "P_STAFF"}
    for code, line in expect.items():
        assert ms[code] == line, (code, ms[code])


def test_code_class_inference_only_when_balances_confirm_it():
    p = make_project("USD")
    assert infer_classes(p.tb.accounts)
    # scramble the signs so that the code convention is NOT confirmed by the balances
    for a in p.tb.accounts:
        a.net = -a.net
    assert infer_classes(p.tb.accounts) == {}


def test_override_wins_and_is_logged_as_override():
    p = make_project("USD")
    p.mapping_overrides["1900"] = "A_CASH"
    an = run_analysis(p)
    m = [x for x in an.mapped if x.account.code == "1900"][0]
    assert m.line == "A_CASH" and m.method == "override"


def test_unmapped_account_is_excluded_flagged_and_explains_bs_difference():
    p = make_project("USD")
    for a in p.tb.accounts:
        if a.code == "1900":
            a.name, a.code = "Zzz", ""
            a.name = "Qwerty clearing"
    an = run_analysis(p)
    if an.st.unmapped_accounts:
        assert any(c.id == "MAP-01" and c.status == "FAIL" for c in an.checks)
        assert any("explains the difference" in c.detail for c in an.checks if c.id == "FS-01")
