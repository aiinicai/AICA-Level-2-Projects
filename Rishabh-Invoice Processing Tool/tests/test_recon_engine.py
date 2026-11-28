"""One test per status and per stage of docs/RECON_RULES.md, plus ambiguity."""
from datetime import date
from decimal import Decimal as D

from ipt.services.recon.engine import Rec, Settings, reconcile
from tests.pdfgen import gst

G1 = gst("08AAACS1111A1Z")
G2 = gst("08AAACT2222B1Z")
ST = Settings()
_ids = iter(range(1, 10 ** 6))


def r(src, no, d=date(2025, 10, 5), g=G1, tx="10000", c="250", s="250", i="0", doc_type="INV", **kw):
    return Rec(src=src, id=next(_ids), gstin=g, doc_no=no, doc_date=d, taxable=D(tx), cgst=D(c), sgst=D(s),
               igst=D(i), cess=D("0"), doc_type=doc_type, **kw)


def run(pr=(), b2b=(), ipt=(), mode="tally_2b", **kw):
    return reconcile({"pr": list(pr), "2b": list(b2b), "ipt": list(ipt)}, mode, ST, **kw)


def statuses(rows):
    return sorted(x.status for x in rows)


def test_stage_exact_matched():
    rows = run([r("pr", "ST/101")], [r("2b", "ST/101")])
    assert [(x.status, x.stage, x.confidence) for x in rows] == [("MATCHED", "exact", D("1.00"))]


def test_stage_normalised_matched():
    rows = run([r("pr", "ST-0101")], [r("2b", "st/101")])
    assert (rows[0].status, rows[0].stage) == ("MATCHED", "normalised")


def test_stage_financial_is_partially_matched():
    rows = run([r("pr", "ST/101")], [r("2b", "X-9")])
    assert (rows[0].status, rows[0].stage) == ("PARTIALLY_MATCHED", "financial")
    assert any("Invoice no. differs" in x for x in rows[0].reasons)


def test_stage_fuzzy_partially_matched():
    rows = run([r("pr", "SHREETRADERS1234", d=date(2025, 10, 5))], [r("2b", "SHREETRADERS1243", d=date(2025, 10, 9))])
    assert (rows[0].status, rows[0].stage) == ("PARTIALLY_MATCHED", "fuzzy")


def test_amount_mismatch_never_matched():
    rows = run([r("pr", "ST/101", c="250")], [r("2b", "ST/101", c="260")])
    assert rows[0].status == "AMOUNT_MISMATCH" and any("CGST differs by 10.00" in x for x in rows[0].reasons)


def test_within_tolerance_is_matched():
    rows = run([r("pr", "ST/101", c="250.00")], [r("2b", "ST/101", c="250.80")])
    assert rows[0].status == "MATCHED"


def test_not_in_2b_and_not_in_books():
    rows = run([r("pr", "A1")], [r("2b", "B2", tx="500", c="12.5", s="12.5")])
    assert statuses(rows) == ["NOT_IN_2B", "NOT_IN_BOOKS"]
    assert all(x.suggested_action for x in rows)


def test_gstin_mismatch():
    rows = run([r("pr", "ST/101", g=G1)], [r("2b", "ST/101", g=G2)])
    assert [x.status for x in rows] == ["GSTIN_MISMATCH"] and len(rows[0].recs) == 2


def test_cdn_difference():
    rows = run([r("pr", "CN-7", doc_type="CRN")], [r("2b", "CN-7", doc_type="DBN")])
    assert [x.status for x in rows] == ["CDN_DIFFERENCE"]


def test_duplicate_in_books():
    rows = run([r("pr", "ST/101"), r("pr", "ST-101")], [r("2b", "ST/101")])
    assert statuses(rows) == ["DUPLICATE", "DUPLICATE"]


def test_amended_in_2b_supersedes_original():
    orig = r("2b", "ST/90", section="B2B", tx="2000", c="50", s="50")
    amend = r("2b", "ST/90A", section="B2BA", original_no="ST/90", tx="2100", c="52.5", s="52.5")
    rows = run([r("pr", "ST/90", tx="2100", c="52.5", s="52.5")], [orig, amend])
    assert [x.status for x in rows] == ["AMENDED"] and rows[0].recs["2b"] is amend


def test_two_candidates_are_never_matched_automatically():
    a, b = r("2b", "X-1"), r("2b", "X-2")          # same amounts and date, different numbers
    rows = run([r("pr", "Z-9")], [a, b])
    assert "MATCHED" not in statuses(rows) and "PARTIALLY_MATCHED" not in statuses(rows)
    pr_row = next(x for x in rows if "pr" in x.recs)
    assert any("possible matches" in x for x in pr_row.reasons)


def test_three_way_and_not_in_ipt_ranking():
    pr, b2, ip = r("pr", "ST/101"), r("2b", "ST/101"), r("ipt", "ST/101")
    rows = run([pr], [b2], [ip], mode="three_way")
    assert [x.status for x in rows] == ["MATCHED"] and set(rows[0].recs) == {"pr", "2b", "ipt"}
    rows = run([r("pr", "ST/102")], [r("2b", "ST/102")], [], mode="three_way")
    assert rows[0].status == "NOT_IN_IPT"
    # a books-vs-2B amount difference is not hidden by 'not in IPT'
    rows = run([r("pr", "ST/103", c="250")], [r("2b", "ST/103", c="300")], [], mode="three_way")
    assert rows[0].status == "AMOUNT_MISMATCH" and any("Not found in IPT" in x for x in rows[0].reasons)


def test_ipt_vs_tally_mode():
    rows = run([r("pr", "ST/101")], [], [r("ipt", "ST/101", c="249.50")], mode="ipt_tally")
    assert [x.status for x in rows] == ["MATCHED"]


def test_manual_link_kept():
    p, b = r("pr", "AAA"), r("2b", "ZZZ", tx="9000", c="225", s="225")
    rows = run([p], [b], manual_links=[{"pr": p.id, "2b": b.id}])
    assert len(rows) == 1 and rows[0].is_manual and rows[0].stage == "manual"
    assert rows[0].status == "AMOUNT_MISMATCH"          # a manual link never hides differences
