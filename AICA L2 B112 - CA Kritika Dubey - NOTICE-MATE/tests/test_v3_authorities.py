"""V3 — legal sources, propositions, verification rules and reasoning trace."""
import sqlite3

import pytest

from noticemate.core.config import get_settings
from noticemate.core.errors import PermissionDenied, ValidationError
from noticemate.services import authorities as A
from noticemate.services import cases, documents, evidence, issues, notices

from .conftest import sample

# Fictional test URLs on an official-pattern domain; they do not refer to real documents.
FAKE_OFFICIAL = "https://incometaxindia.gov.in/fictional-test-only/circular-x"
FAKE_JUDGMENT = "https://itat.gov.in/fictional-test-only/order-y"


@pytest.fixture(scope="module")
def ctx(users):
    ca, staff = users["ca"], users["staff"]
    c = cases.create_case(ca, case_ref="V3-AUTH", assessee_name="PQR Traders", assessee_category="FIRM",
                          pan="AAAFP1234Z", assessment_year="2026-27")
    cases.add_member(ca, c["id"], staff["id"])
    d = documents.upload(staff, c["id"], "notice.docx", sample("notice_143_2_PQR.docx"))
    n = notices.create_from_document(staff, d["id"])
    iss = issues.generate_from_notice(staff, n["id"])
    return {"ca": ca, "staff": staff, "case": c, "doc": d, "issues": iss, "outsider": users["outsider"]}


def test_registry_import_is_unverified(ctx):
    A.import_registry()
    srcs = A.list_sources(q="Section 68")
    assert srcs and all(s["effective_status"] in ("UNVERIFIED", "NEEDS_CA_REVIEW") for s in srcs)
    assert A.import_registry() == 0  # idempotent


def test_seed_and_trace(ctx):
    i = ctx["issues"][0]
    props = A.seed_issue_propositions(ctx["staff"], i["id"])
    assert len(props) == 1 and props[0]["origin"] == "SYSTEM" and props[0]["effective_status"] == "UNVERIFIED"
    assert A.seed_issue_propositions(ctx["staff"], i["id"])[0]["id"] == props[0]["id"]  # idempotent
    t = A.issue_trace(ctx["staff"], i["id"])
    assert t["issue"]["id"] == i["id"] and t["propositions"] and t["evidence"]
    assert any("do not rely" in w for w in t["warnings"])
    notice_facts = [f for f in t["propositions"][0]["facts"] if f["fact_type"] == "NOTICE_TEXT"]
    assert notice_facts and notice_facts[0]["document_name"] == "notice.docx"
    with pytest.raises(PermissionDenied):
        A.issue_trace(ctx["outsider"], i["id"])


def test_fabricated_quote_rejected(ctx):
    p = A.add_proposition(ctx["staff"], ctx["case"]["id"], "Test proposition", issue_id=ctx["issues"][0]["id"], kind="FACTUAL")
    with pytest.raises(ValidationError):
        A.add_fact(ctx["staff"], p["id"], fact_type="DOCUMENT_SPAN", basis="ESTABLISHED", document_id=ctx["doc"]["id"],
                   quote="The assessee admitted undisclosed income of Rs 99 crore")
    with pytest.raises(ValidationError):
        A.add_fact(ctx["staff"], p["id"], fact_type="CLIENT_EXPLANATION", basis="ESTABLISHED", note="client says so")


def test_source_verification_rules(ctx):
    ca, staff = ctx["ca"], ctx["staff"]
    s = A.add_source(staff, source_class="PRIMARY", source_type="CIRCULAR", title="Fictional test circular",
                     document_number="FICTIONAL-1/2026", date_issued="2026-05-01", official_url="http://example.com/x")
    assert s["effective_status"] == "UNVERIFIED" and not s["url_is_official"]
    with pytest.raises(PermissionDenied):
        A.decide_source(staff, s["id"], decision="VERIFIED", checked_url=s["official_url"], applicability_confirmed=True)
    with pytest.raises(ValidationError) as e:
        A.decide_source(ca, s["id"], decision="VERIFIED", checked_url=s["official_url"], checked_pinpoint="para 2",
                        applicability_confirmed=True)
    assert any("official" in p for p in e.value.details["problems"])
    s = A.update_source(staff, s["id"], {"official_url": FAKE_OFFICIAL})
    assert s["url_is_official"]
    with pytest.raises(ValidationError):  # applicability not confirmed
        A.decide_source(ca, s["id"], decision="VERIFIED", checked_url=FAKE_OFFICIAL, checked_pinpoint="para 2")
    s = A.decide_source(ca, s["id"], decision="VERIFIED", checked_url=FAKE_OFFICIAL, checked_pinpoint="para 2",
                        applicability_confirmed=True, note="Checked for AY 2026-27 under the 1961 Act.")
    assert s["effective_status"] == "VERIFIED" and s["verification_history"][0]["decision"] == "VERIFIED"
    # editing a verified source sends it back for review
    s2 = A.update_source(staff, s["id"], {"excerpt": "changed text"})
    assert s2["effective_status"] == "NEEDS_CA_REVIEW"
    ctx["circular"] = A.decide_source(ca, s["id"], decision="VERIFIED", checked_url=FAKE_OFFICIAL,
                                      checked_pinpoint="para 2", applicability_confirmed=True)


def test_ai_suggestion_never_verifiable(ctx):
    p = A.record_ai_suggestion(ctx["staff"], ctx["case"]["id"], issue_id=ctx["issues"][0]["id"],
                               proposition_text="AI says X", claimed_citation="Some case (fictional)", claimed_url=FAKE_JUDGMENT)
    src = p["sources"][0]
    assert src["source_class"] == "AI_SUGGESTION" and src["citation"].startswith("AS CLAIMED BY AI")
    with pytest.raises(ValidationError):
        A.decide_source(ctx["ca"], src["id"], decision="VERIFIED", checked_url=FAKE_JUDGMENT, checked_pinpoint="p1",
                        applicability_confirmed=True)
    with pytest.raises(ValidationError):
        A.decide_proposition(ctx["ca"], p["id"], decision="VERIFIED", note="x" * 30)


def test_proposition_verification_and_decay(ctx):
    ca, staff = ctx["ca"], ctx["staff"]
    p = A.add_proposition(staff, ctx["case"]["id"], "Fictional legal proposition for testing", issue_id=ctx["issues"][0]["id"])
    with pytest.raises(ValidationError):
        A.decide_proposition(ca, p["id"], decision="VERIFIED")
    A.link_source(staff, p["id"], ctx["circular"]["id"], stance="SUPPORTS", pinpoint="para 2")
    with pytest.raises(PermissionDenied):
        A.decide_proposition(staff, p["id"], decision="VERIFIED")
    j = A.add_source(staff, source_class="PRIMARY", source_type="CASE_LAW", title="Fictional v. Fictional (test only)",
                     citation="FICTIONAL CITATION (test)", court_level="ITAT", date_issued="2025-01-01", official_url=FAKE_JUDGMENT)
    A.link_source(staff, p["id"], j["id"], stance="DIFFERS")
    with pytest.raises(ValidationError):  # differing authority needs a CA note
        A.decide_proposition(ca, p["id"], decision="VERIFIED", note="ok")
    v = A.decide_proposition(ca, p["id"], decision="VERIFIED",
                             note="The differing ITAT order is distinguishable on facts; see para 5 of draft note.")
    assert v["effective_status"] == "VERIFIED"
    A.edit_proposition(staff, p["id"], "Fictional legal proposition for testing (edited)")
    assert A.proposition_view(staff, p["id"])["effective_status"] == "NEEDS_CA_REVIEW"
    # outdated supporting source also demotes
    A.decide_proposition(ca, p["id"], decision="VERIFIED", note="Re-checked after edit; differing order distinguished.")
    A.update_source(staff, ctx["circular"]["id"], {"effective_to": "2020-01-01"})
    assert A.get_source(ctx["circular"]["id"])["effective_status"] == "OUTDATED"
    assert A.proposition_view(staff, p["id"])["effective_status"] == "NEEDS_CA_REVIEW"


def test_verification_log_append_only(ctx):
    conn = sqlite3.connect(get_settings().db_path)
    try:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("UPDATE verification_log SET decision='X'")
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM verification_log")
    finally:
        conn.close()
