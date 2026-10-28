"""Behaviour taken from the ICAI Guidance Note on Division I (Revised January 2022). Paragraph numbers are its own."""
import copy
import io
import sys
import zipfile
from pathlib import Path

import pytest
from docx import Document
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from daybook_auditor import narration as N  # noqa: E402
from daybook_auditor.fs_format import check_file  # noqa: E402
from fsbuilder import pipeline as P  # noqa: E402
from fsbuilder.format import CRORE, UNITS, allowed_units, as_unit, choose_unit, rnd  # noqa: E402
from fsbuilder.mapping import map_ledgers  # noqa: E402
from fsbuilder.model import build_model, ratio_note  # noqa: E402
from fsbuilder.render import write_all  # noqa: E402
from fsbuilder.reviewer import run_review  # noqa: E402
from fsbuilder.reviewer.checklist import evaluate_checklist  # noqa: E402
from fsbuilder.reviewer.ratios import compute_ratios  # noqa: E402
from fsbuilder.reviewer.tieouts import run_tieouts  # noqa: E402
from fsbuilder.tb import normalise  # noqa: E402
from test_links import Calc  # noqa: E402


@pytest.fixture(scope="module")
def parts():
    tb = normalise(P.load_sample())
    return tb, map_ledgers(tb)


def model(parts, unit=None):
    return build_model(parts[0], parts[1], unit=unit)


# ------------------------------------------------------------------ para 6.15: rounding off is compulsory
def test_permitted_units_depend_on_total_income():
    small = [u.key for u in allowed_units(99 * CRORE)]
    big = [u.key for u in allowed_units(100 * CRORE)]
    assert small == ["hundreds", "thousands", "lakhs", "millions"] and big == ["lakhs", "millions", "crores"]
    assert "rupees" not in small + big                                   # full figures are no longer allowed
    assert choose_unit(1.2 * CRORE).key == "lakhs" and choose_unit(150 * CRORE).key == "crores"


def test_unit_formatting():
    assert UNITS["lakhs"].fmt(15_086_000) == "150.86" and UNITS["lakhs"].fmt(-2_489_000) == "(24.89)"
    assert UNITS["thousands"].fmt(15_086_000) == "15,086" and UNITS["crores"].fmt(150_860_000) == "15.09"
    assert UNITS["lakhs"].fmt(0) == "-" and UNITS["lakhs"].fmt(None) == "-"
    assert UNITS["lakhs"].fmt(1_234_567_000) == "12,345.67"              # Indian grouping holds in any unit
    assert as_unit(None).key == "rupees" and as_unit("lakhs") is UNITS["lakhs"]


def test_rounding_goes_to_a_multiple_of_the_step():
    assert rnd(2_489_415.93, 1000) == 2_489_000 and rnd(-2_489_415.93, 1000) == -2_489_000 and rnd(2_500, 1000) == 3_000
    assert rnd(2_489_415.93) == 2_489_416                                # step 1 is the old whole-rupee behaviour


@pytest.mark.parametrize("unit", ["hundreds", "thousands", "lakhs", "millions"])
def test_statements_balance_and_every_figure_is_a_multiple_of_the_unit_in_each_permitted_unit(parts, unit):
    m = model(parts, unit)
    step = UNITS[unit].step
    amounts = [r.cur for r in m.bs + m.pl + m.cashflow if r.cur is not None] + [r.prev for r in m.bs if r.prev is not None]
    assert all(a % step == 0 for a in amounts), "a figure is not rounded to the unit"
    tot = {r.label: r for r in m.bs if r.kind == "total"}
    assert tot["TOTAL ASSETS"].cur == tot["TOTAL EQUITY AND LIABILITIES"].cur
    assert tot["TOTAL ASSETS"].prev == tot["TOTAL EQUITY AND LIABILITIES"].prev
    assert not any("does not agree" in b or "does not reconcile" in b for b in m.basis)


@pytest.mark.parametrize("unit", ["thousands", "lakhs", "millions"])
def test_every_tie_out_still_passes_in_each_unit(parts, unit):
    m = model(parts, unit)
    failed = [c for c in run_tieouts(m, parts[1]) if c.status == "Fail"]
    assert failed == [], [(c.id, c.expected, c.actual) for c in failed]


def test_a_rounding_difference_is_absorbed_and_disclosed_at_the_unit_not_the_rupee(parts):
    m = model(parts, "lakhs")
    assert m.rounding and "absorbed" in m.rounding[0]
    assert abs(int(m.rounding[0].split("Rs (")[1].split(")")[0].replace(",", ""))) <= 25 * 1000


def test_word_and_excel_state_the_unit_and_show_scaled_figures(parts, tmp_path):
    m = model(parts, "lakhs")
    docx, xlsx = write_all(m, tmp_path)
    text = "\n".join(p.text for p in Document(docx).paragraphs) + "\n".join(
        c.text for t in Document(docx).tables for row in t.rows for c in row.cells)
    assert "Rs in lakhs, rounded off as required by Schedule III" in text and "150.86" in text and "1,50,86,416" not in text
    ws = load_workbook(xlsx, data_only=True)["Balance Sheet"]
    assert ws["A3"].value.startswith("(Rs in lakhs")
    ta = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == "TOTAL ASSETS")
    assert ws.cell(ta, 3).value == pytest.approx(150.86) and ws.cell(ta, 3).number_format.startswith("#,##0.00")


def test_the_linked_excel_still_agrees_with_an_independent_recalculation_in_lakhs(parts, tmp_path):
    _, xlsx = write_all(model(parts, "lakhs"), tmp_path)
    calc, cached = Calc(xlsx), load_workbook(xlsx, data_only=True)
    n = 0
    for ws in calc.wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    n += 1
                    assert calc.value(ws.title, c.coordinate) == pytest.approx(cached[ws.title][c.coordinate].value, abs=0.011)
    assert n >= 70


def test_scaled_files_still_pass_the_formatting_checker(parts, tmp_path):
    for f in write_all(model(parts, "lakhs"), tmp_path):
        findings, _ = check_file(f.name, f.read_bytes())
        assert findings.empty, findings.to_string()


def test_the_checklist_flags_full_rupees_and_accepts_a_permitted_unit(parts):
    def p4(unit):
        m = model(parts, unit)
        return {i.id: i for i in evaluate_checklist(m, run_tieouts(m, parts[1]))}["P4"]
    assert p4("rupees").status == "Observation" and "6.15" in p4("rupees").evidence
    assert p4("lakhs").status == "Complete"
    assert p4("crores").status == "Observation" and "not a permitted unit" in p4("crores").evidence


def test_the_builder_picks_a_permitted_default_unit(parts):
    units, default = P.unit_choices(parts[1])
    assert default.key == "lakhs" and [u.key for u in units] == ["hundreds", "thousands", "lakhs", "millions"]


# ------------------------------------------------------------------ Annexure B: the ratio definitions
def test_dscr_starts_from_profit_before_tax(parts):
    m = model(parts)
    m.figures["pl"].update(pbt=1_000_000, pat=700_000, dep=100_000, fin=50_000, lt_repaid=150_000)
    r = {x.id: x for x in compute_ratios(m)}["dscr"]
    assert r.cur == pytest.approx((1_000_000 + 100_000 + 50_000) / (50_000 + 150_000))     # not (700,000 + ...)
    assert "before tax" in r.formula


def test_net_capital_turnover_uses_average_working_capital(parts):
    m = model(parts)
    r = {x.id: x for x in compute_ratios(m)}["net_capital_turnover"]
    cur, prev = m.figures["cur"], m.figures["prev"]
    average = ((cur["ca"] - cur["cl"]) + (prev["ca"] - prev["cl"])) / 2
    assert r.cur == pytest.approx(m.figures["pl"]["revenue"] / average) and "average working capital" in r.formula


# ------------------------------------------------------------------ para 8.9.12: ratios are a note to the accounts
def test_the_ratios_are_a_numbered_note_with_numerators_and_denominators(parts):
    m = model(parts)
    n = m.notes[-1]
    assert n.title == "Analytical ratios" and n.kind == "text" and len(n.rows) == 11
    assert n.header[-1] == "Reason for change over 25%"
    defs = {r[0]: r for r in n.movement["rows"]}
    assert defs["Current ratio"][1:] == ["Current assets", "current liabilities"]
    assert defs["Debt service coverage ratio"][1].startswith("(Profit before tax")
    reasons = {r[0]: r[-1] for r in n.rows}
    assert "Management to explain" in reasons["Current ratio"] and "Management to explain" in reasons["Debt-equity ratio"]
    assert "profit and loss" in reasons["Return on equity"] and reasons["Return on investment"] == "Not applicable"


def test_the_ratios_note_is_in_both_files_and_does_not_disturb_the_tie_outs(parts, tmp_path):
    m = model(parts)
    assert [c for c in run_tieouts(m, parts[1]) if c.status == "Fail"] == []
    docx, xlsx = write_all(m, tmp_path)
    text = "\n".join(c.text for t in Document(docx).tables for row in t.rows for c in row.cells)
    assert "Analytical ratios" in "\n".join(p.text for p in Document(docx).paragraphs)
    assert "Current ratio" in text and "Items included in the numerator and denominator" in "\n".join(
        p.text for p in Document(docx).paragraphs)
    notes = load_workbook(xlsx)["Notes"]
    assert any(c.value == "Note 17: Analytical ratios" for row in notes.iter_rows(min_col=1, max_col=1) for c in row)


def test_ai_drafted_reasons_reach_the_ratios_note_marked_as_drafts(parts):
    m = model(parts)
    review = run_review(m, parts[1])
    cr = next(r for r in review.ratios if r.id == "current_ratio")
    cr.explanation, cr.explanation_source = "Receivables grew faster than payables.", "AI draft"
    m2 = P.with_ratio_reasons(m, review)
    row = next(r for r in m2.notes[-1].rows if r[0] == "Current ratio")
    assert "Receivables grew faster" in row[-1] and "(AI draft)" in row[-1]
    assert "Management to explain" in next(r for r in m.notes[-1].rows if r[0] == "Current ratio")[-1]     # original untouched
    other = next(r for r in m2.notes[-1].rows if r[0] == "Debt-equity ratio")
    assert "Management to explain" in other[-1]                                                            # no draft, no text


def test_a_ratio_with_a_reason_supplied_replaces_the_placeholder(parts):
    n = ratio_note(model(parts), 17, {"current_ratio": "Reason given by the director."})
    assert next(r for r in n.rows if r[0] == "Current ratio")[-1] == "Reason given by the director."


# ------------------------------------------------------------------ the disclosure checklist after the guidance note
def checklist(parts):
    m = model(parts)
    return {i.id: i for i in evaluate_checklist(m, run_tieouts(m, parts[1]))}


def test_items_the_guidance_note_adds_are_present_with_their_references(parts):
    items = checklist(parts)
    for id_, ref in [("R7", "8.9.7"), ("R8", "8.9.11"), ("R9", "8.9.13"), ("P6", "8.9.12"), ("L10", "182(3)"),
                     ("A10", "186(4)"), ("AS7", "129(5)"), ("L11", "5(vi)")]:
        assert id_ in items and ref in items[id_].ref, id_


def test_the_new_items_follow_what_the_books_contain(parts):
    items = checklist(parts)
    assert items["R7"].status == "Information required" and "quarterly" in items["R7"].requirement.lower()   # the sample has a term loan
    assert items["L10"].status == "Not applicable"                                                            # no donation ledger
    assert items["P6"].status == "Partly provided" and "need management's reason" in items["P6"].evidence
    assert items["L11"].status == "Complete" and "Repairs to machinery" in items["L11"].evidence


def test_a_donation_ledger_switches_the_political_contribution_item_on(parts):
    m = model(parts)
    m.mapping = m.mapping.copy()
    m.mapping.loc[m.mapping["ledger"] == "Telephone Expenses", "sub"] = "Donations / CSR"
    m.mapping.loc[m.mapping["ledger"] == "Telephone Expenses", "line"] = "EXP.OTH"
    assert {i.id: i for i in evaluate_checklist(m, run_tieouts(m, parts[1]))}["L10"].status == "Information required"


def test_ageing_is_measured_from_the_due_date_and_promoters_at_both_dates(parts):
    items = checklist(parts)
    for id_ in ("T1", "A5"):
        assert "due date of payment" in items[id_].requirement and "due dates" in items[id_].ask
    assert "beginning" in items["S5"].requirement


def test_receivables_ageing_buckets_follow_the_guidance_note(parts):
    m = model(parts)
    gaps = " ".join(g for n in m.notes for g in n.gaps)
    assert "under 6 months, 6 months to 1 year, 1-2, 2-3, over 3 years" in gaps
    assert "MSME, others and disputed dues" in gaps and "at the end and at the beginning of the year" in gaps


# ------------------------------------------------------------------ Note 5(vi): repairs to buildings and machinery separately
def test_repairs_are_split_between_machinery_buildings_and_others(parts):
    tb, mp = parts
    L = tb.ledgers.copy()
    row = L[L["name"] == "Telephone Expenses"].index[0]
    from dataclasses import replace
    for name, expected in [("Repairs to Factory Building", "Repairs to buildings"), ("Repairs of Plant Machinery", "Repairs to machinery"),
                           ("Repairs - Vehicles", "Repairs and maintenance (others)")]:
        L.loc[row, "name"] = name
        got = map_ledgers(replace(tb, ledgers=L)).set_index("ledger").loc[name, "sub"]
        assert got == expected, (name, got)


def test_the_sample_machinery_repairs_are_shown_as_repairs_to_machinery(parts):
    assert parts[1].set_index("ledger").loc["Repairs & Maintenance - Machinery", "sub"] == "Repairs to machinery"


# ------------------------------------------------------------------ Annexure C and the narration references
def test_the_donation_theme_cites_the_political_contribution_disclosure():
    theme = N.THEME_BY_ID["donation"]
    assert "182(3)" in theme.reference and "name of the party" in theme.reference


# ------------------------------------------------------------------ the checker must not mistake clause numbers for dates
def test_clause_numbers_are_not_dates_but_real_dotted_dates_still_are():
    from docx import Document as D
    from daybook_auditor.fs_format import check_docx

    def findings(text):
        d = D()
        d.add_paragraph(text)
        buf = io.BytesIO()
        d.save(buf)
        df, _ = check_docx(buf.getvalue())
        return df[df["check"] == "Date format"]
    for ok in ("GN 8.9.13", "see para 6.15.2", "Note 6.2.1", "Annexure 8.9.7", "Sec 8.9.13"):
        assert findings(ok).empty, ok
    for bad in ("approved on 15.05.26", "signed on 8.9.13", "dated 31.03.26"):
        assert len(findings(bad)) == 1, bad
