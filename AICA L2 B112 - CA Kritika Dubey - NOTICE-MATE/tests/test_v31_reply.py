"""V3.1 — multi-issue notice pack: issue titles/categories, content mapping, reply writing, document deletion."""
import pathlib

import pytest

from noticemate.core.errors import ValidationError
from noticemate.services import documents, drafting, intake, issues, mapping

PACK = pathlib.Path(__file__).parent / "fixtures" / "complex_pack"


@pytest.fixture(scope="module")
def pack(users):
    ca = users["ca"]
    nf = next(PACK.glob("00_*.docx"))
    r = intake.start_from_notice(ca, nf.name, nf.read_bytes())
    cid = r["case"]["id"]
    sg = r["suggestions"]
    intake.confirm_case(ca, cid, assessee_name=sg["assessee_name"]["value"], assessee_category="INDIVIDUAL",
                        pan=sg["pan"]["value"], assessment_year=sg["assessment_year"]["value"], case_ref="NIVARA-T")
    docs = [documents.upload(ca, cid, f.name, f.read_bytes()) for f in sorted(PACK.glob("0[1-8]_*.docx"))]
    iss = issues.generate_from_notice(ca, r["notice"]["id"])
    return {"ca": ca, "cid": cid, "notice": r["notice"], "docs": docs, "issues": iss}


def test_six_queries_titled_and_classified(pack):
    iss = pack["issues"]
    assert [i["category"] for i in iss] == ["UNSECURED_LOAN", "CASH_DEPOSITS", "SALES_GST_RECONCILIATION",
                                            "TRADE_CREDITORS", "PURCHASES", "FIXED_ASSETS"]
    assert iss[3]["title"].lower().startswith("trade creditors") and iss[4]["title"].lower().startswith("selected purchases")
    assert all(i["query_text"] and "Submission instructions" not in i["query_text"] for i in iss)


def test_documents_mapped_to_the_right_queries(pack):
    s = mapping.summary(pack["ca"], pack["cid"])
    names = {x["seq"]: " ".join(d["name"] for d in x["documents"]) for x in s["issues"]}
    assert "LOAN" in names[1] and "CASH_BOOK" in names[2] and "SALES_REGISTER" in names[3]
    assert "CREDITOR" in names[4] and "PURCHASE_INVOICES" in names[5] and "FIXED_ASSETS" in names[6]
    assert "CREDITOR" not in names[1]  # trade creditors are never treated as loans
    items = " ".join(c["item"] for c in s["contradictions"])
    assert "PM-24-25-118" in items and "Kaveri Paper" in items


def test_reply_is_point_wise_first_person_and_uses_record_facts(pack):
    d = drafting.build(pack["ca"], pack["cid"], pack["notice"]["id"])
    c = d["content_json"]
    txt = drafting.render_text(c, approved=False)
    assert len(c["issues"]) == 6
    for b in c["issues"]:
        assert b["heading"].startswith(f"Query No. ")
        assert len(" ".join(b["paragraphs"])) > 400, b["heading"]  # no one-line replies
    assert "UTR TEST24051501" in txt and "₹3,50,000" in txt and "PAN AAAAR1111A" in txt
    assert "₹8,20,000" in txt  # cash in hand before the first deposit, from the cash book
    assert "exempt/nil-rated" in txt and "Aria Textiles" in txt and "GRN-441A" in txt and "NH-FA-024" in txt
    replies = " ".join(p for b in c["issues"] for p in b["paragraphs"])
    assert "We " in replies and "the assessee" not in replies.lower()
    for bad in ("NOTICE-MATE", " AI ", "software", "[CA TO CONFIRM: add the factual explanation"):
        assert bad not in txt
    assert "unsecured loan" not in c["issues"][3]["heading"].lower() and "General" not in txt
    assert "enclosed" not in txt.lower() and not c["annexures"]  # nothing is called enclosed unless marked as annexure
    assert any("[CA REVIEW:" in p and "Kaveri" in p for p in drafting.placeholders(c))
    assert "Meera Nair" in txt and "Rs." not in txt


def test_annexure_reference_only_when_marked(pack):
    ca, cid = pack["ca"], pack["cid"]
    bank = next(d for d in pack["docs"] if "BANK_STATEMENT" in d["original_name"])
    documents.set_annexure(ca, bank["id"], True, "A-1")
    txt = drafting.render_text(drafting.build(ca, cid, pack["notice"]["id"])["content_json"], approved=False)
    assert "(Annexure A-1)" in txt and "Index of Annexures" in txt


def test_delete_reports_impact_and_protects_notice(pack):
    ca, cid = pack["ca"], pack["cid"]
    with pytest.raises(ValidationError):
        documents.delete(ca, pack["notice"]["document_id"])
    fa = next(d for d in pack["docs"] if "FIXED_ASSETS" in d["original_name"])
    imp = documents.delete_impact(ca, fa["id"])
    assert imp["issue_links"] > 0
    documents.delete(ca, fa["id"])
    s = mapping.summary(ca, cid)
    assert not any("FIXED_ASSETS" in d["name"] for x in s["issues"] for d in x["documents"])
    d = drafting.build(ca, cid, pack["notice"]["id"])  # still writes all six queries
    assert len(d["content_json"]["issues"]) == 6
