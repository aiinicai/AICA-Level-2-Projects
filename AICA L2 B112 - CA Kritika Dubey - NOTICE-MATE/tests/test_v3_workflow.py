"""V3 — notice-first workflow end to end, with citation and approval safeguards."""
import pytest

from noticemate.core.db import ro
from noticemate.core.errors import ValidationError
from noticemate.services import authorities as A
from noticemate.services import drafting, intake, issues, notices, review

from .conftest import sample
from .test_v3_ocr import _blank_pdf, _mixed_pdf

FAKE_OFFICIAL = "https://incometaxindia.gov.in/fictional-test-only/section-x"


def test_intake_failed_and_partial(users):
    staff = users["staff"]
    r = intake.start_from_notice(staff, "blank.pdf", _blank_pdf())
    assert r["next_step"] == "FIX_OCR" and r["notice"] is None
    r = intake.start_from_notice(staff, "mixed.pdf", _mixed_pdf())
    assert r["next_step"] == "ACKNOWLEDGE_PARTIAL"
    r2 = intake.acknowledge_and_parse(staff, r["document"]["id"])
    assert r2["notice"]["id"]


def test_notice_first_end_to_end(users):
    staff, ca, admin = users["staff"], users["ca"], users["admin"]
    r = intake.start_from_notice(staff, "scan.pdf", sample("notice_143_2_PQR_scanned.pdf"))
    assert r["next_step"] == "CONFIRM_DETAILS" and r["document"]["extraction_status"] == "OCR"
    assert r["document"]["doc_type"] == "NOTICE"
    sug = r["suggestions"]
    assert sug["pan"]["value"] == "AAAFP1234Z" and sug["assessment_year"]["value"] == "2026-27"
    cid = r["case"]["id"]
    wf = intake.workflow_status(staff, cid)
    assert wf["next"] == "confirm"
    with pytest.raises(ValidationError):
        intake.confirm_case(staff, cid, assessee_name=intake.PROVISIONAL_NAME, assessee_category="FIRM", pan=None, assessment_year="2026-27")
    intake.confirm_case(staff, cid, assessee_name="PQR Traders", assessee_category="FIRM", pan="AAAFP1234Z",
                        assessment_year="2026-27", case_ref="V3-E2E")
    from noticemate.services import cases
    cases.add_member(users["admin"], cid, ca["id"])
    notices.verify_deadline(ca, r["notice"]["id"], "2026-11-25", "e-proceedings portal (fictional test)")
    assert intake.workflow_status(staff, cid)["next"] == "issues"

    iss = issues.generate_from_notice(staff, r["notice"]["id"])
    for i in iss:
        A.seed_issue_propositions(staff, i["id"])
        issues.update_analysis(ca, i["id"], {"concern_position": "NEED_CLIENT_INFO"})
        issues.set_strategy(staff, i["id"], "DISPUTE_FACTUAL", "Evidence available; respond factually subject to CA review.")

    # CA records and verifies one primary source; supports a proposition on issue 1
    src = A.add_source(ca, source_class="PRIMARY", source_type="ACT_SECTION", title="Fictional test provision",
                       act="IT_ACT_1961", provision="Section X (fictional)", citation="Section X of the Act (fictional test)",
                       official_url=FAKE_OFFICIAL)
    A.decide_source(ca, src["id"], decision="VERIFIED", checked_url=FAKE_OFFICIAL, checked_pinpoint="sub-section (1)",
                    applicability_confirmed=True)
    p = A.add_proposition(staff, cid, "The credit is examined with reference to the fictional provision", issue_id=iss[0]["id"])
    A.link_source(staff, p["id"], src["id"], stance="SUPPORTS")
    A.decide_proposition(ca, p["id"], decision="VERIFIED")

    dr = drafting.build(staff, cid, r["notice"]["id"])
    txt = drafting.render_text(dr["content_json"], approved=False)
    assert "Section X of the Act (fictional test), sub-section (1)" in txt
    assert drafting.cited_propositions(dr["content_json"])[0]["id"] == p["id"]
    sys_prop = A.seed_issue_propositions(staff, iss[0]["id"])[0]
    assert sys_prop["text"][:40] not in txt  # unverified system view stays out of the reply

    c = dr["content_json"]
    base_edits = {"background": "The assessee is a partnership firm engaged in trading (fictional test).",
                  "to_from": {"to": "National Faceless Assessment Centre"},
                  "reference": "Notice No./DIN: fictional; dated 2026-11-10.",
                  "subject": "Submission in response to notice under section 143(2) (fictional test)",
                  "signature": {"name": "Authorised Partner", "designation": "Partner", "date": "24-11-2026", "place": "Test City"}}
    paras = {str(b["issue_id"]): ["Response settled by CA (fictional test)."] + [x for x in b["paragraphs"] if "Reference in this regard" in x]
             for b in c["issues"]}
    bad = dict(paras)
    bad[str(c["issues"][1]["issue_id"])] = ["As held in ABC v. DCIT (2020) 400 ITR 12 (fictional), the addition fails."]
    dr2 = drafting.edit(admin, dr["id"], {**base_edits, "issues": bad})
    assert not dr2["unresolved_placeholders"], dr2["unresolved_placeholders"]
    for k, _ in review.CHECKLIST:
        review.tick(ca, dr2["id"], k, True)
    with pytest.raises(ValidationError) as e:
        review.approve(ca, dr2["id"], declaration_accepted=True)
    assert any("400 ITR 12" in x for x in e.value.details["problems"])

    dr3 = drafting.edit(admin, dr2["id"], {"issues": paras})
    for k, _ in review.CHECKLIST:
        review.tick(ca, dr3["id"], k, True)
    st = review.approve(ca, dr3["id"], declaration_accepted=True)
    assert st["approved"] and st["approved_version"] == dr3["version"]
    with ro() as conn:
        assert conn.execute("SELECT draft_version FROM approvals WHERE draft_id=? AND revoked=0", (dr3["id"],)).fetchone()[0] == dr3["version"]
    name, data = review.export(ca, cid)
    assert data[:2] == b"PK"
    assert intake.workflow_status(ca, cid)["steps"][-1]["done"]

    # A later change to the verified source withdraws the approval's legal basis
    A.update_source(ca, src["id"], {"excerpt": "edited after approval"})
    st = review.approval_status(ca, cid)
    assert not st["approved"] and st.get("problems")
    from noticemate.core.errors import PermissionDenied
    with pytest.raises(PermissionDenied):
        review.export(ca, cid)
