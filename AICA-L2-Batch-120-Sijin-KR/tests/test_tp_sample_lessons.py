"""Checks added from the ABC COMPANY KMP-remuneration sample report (PDF)."""
import types
import yaml
from pathlib import Path
from auditsignoff import rules_tp as T

P = yaml.safe_load(open(Path(__file__).parent.parent / "rules" / "params.yaml"))
ENG = {"fy": 2024, "client": {"name": "ABC COMPANY", "authority": "DSO-IFZA", "shareholders": ["TWO LTD"], "signatories_legal": ["PQR", "XYZ"]}}


def ctx(text, rows=()):
    tables = [types.SimpleNamespace(loc="Page 1 table 1", rows=[list(r) for r in rows])] if rows else []
    doc = types.SimpleNamespace(kind="pdf", all_text=text, text=text, pages=[text], tables=tables)
    return T.TPCtx(doc, None, ENG, P, path=None)


def test_placeholders_and_titles():
    c = ctx("trade license no. XXXXXX issued on January. Mr. Mr. XYZ and Total Compensation [FY 2024] ok")
    f = T.tp60_placeholders(c)
    assert {x.found for x in f} >= {"XXXXXX"} and not any("FY 2024" in x.found for x in f)
    assert T.tp61_doubled(c)[0].found.startswith("Mr. Mr.")


def test_funnel_and_geography():
    rows = [("A, B", "Alpha plc (LSE:ALP)", "CEO", "1,500.0", "1,000,000")] * 0
    text = "Total potential comparables 63 Total manual review rejections 36 Accepted companies 28 search results consisting of 36 comparables MENA region"
    c = ctx(text)
    titles = [x.title for x in T.tp65_funnel(c)]
    assert any("does not add up" in t for t in titles) and any("search results" in t for t in titles)


def test_adjustment_not_quantified_and_aed_stats():
    text = ("interquartile range of AED 1,103,333 (25th percentile) to AED 2,775,669 (75th percentile), with a median of AED 1,525,809. "
            "Mr. Mr. XYZ – 20,439,284 the excess may be considered non-arm's length")
    c = ctx(text)
    f = T.tp68_adjustment(c)
    assert f and f[0].severity == "High" and "not quantified" in f[0].title
    # unit-aware stats: no '25%' false capture
    assert all(v > 1000 or k not in ("q1", "q3") for k, v, _ in T.report_stats(c))


def test_authority_people():
    c = ctx("licensed by the Dubai Integrated Economic Zones Authority at DSO-IFZA. Mr. SRK and Mr. XYZ. TWO LTD is the sole shareholder")
    f = T.tp69_authority_people(c)
    assert any("licensing authority" in x.title for x in f) and any(x.found == "SRK" for x in f)


def test_page_reference_added_and_na_status(tmp_path):
    import tempfile
    from tp_fixtures import make_report, make_workbook
    from auditsignoff.rules_tp import run_tp
    make_workbook(tmp_path / "GOLDEN_CREST_FY2025_benchmark.xlsx")
    make_report(tmp_path / "r.docx", name="GOLDEN CREST TRADING DMC", count=7)
    eng = {"fy": 2025, "client": {"name": "GOLDEN CREST TRADING DMCC", "authority": "DMCC", "shareholders": ["Mohammed Al Hashmi"], "signatories_legal": []}}
    res, _ = run_tp(tmp_path / "r.docx", tmp_path / "GOLDEN_CREST_FY2025_benchmark.xlsx", eng, P)
    by = {r.check_id: r for r in res}
    assert by["TP-60"].status == "NA"                       # not a Financial Update: not listed as 'not checked'
    f = by["TP-45"].findings[0]
    assert "heading" in f.location or "p." in f.location     # reviewer is told where to look
    assert by["TP-04"].status == "REVIEW"
