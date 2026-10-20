"""Tests for key facts never empty, two-level sign-off, update details, JSON export."""

import json
from types import SimpleNamespace

from judgment_analyzer.consistency import facts_without_ai, fill_missing, run_consistency
from judgment_analyzer.exporter import build_final_document, build_json, save_json
from judgment_analyzer.repository import (STATUS_DRAFT, STATUS_RETURNED, STATUS_VERIFIED, JudgmentRecord,
                                          RegisterError, Repository)
from judgment_analyzer.response_parser import parse_report

REPORT = """## 1. Case Details
- **Court or tribunal:** Income Tax Appellate Tribunal, 'C' Bench, Chennai
- **Case title:** Voltamp Transformers Ltd. v. DCIT
- **Citation or case number:** ITA No. 393/CHNY/2024
- **Date of judgment:** 14 September 2026
- **Judges or bench:** A. Member (JM)
- **Parties involved:** Voltamp Transformers Ltd. (Appellant); Deputy Commissioner of Income-tax, TDS (Respondent)

## 2. Executive Summary
[Court Finding] The appeal succeeds (para 18).
"""
SOURCE = ("IN THE INCOME TAX APPELLATE TRIBUNAL ... I.T.A. No. 393/Chny/2024 Assessment Year : 2021-22 ... "
          "In the result, the appeal of the assessee is partly allowed.")


class FailingClient:
    def __init__(self, good=0):
        self.good, self.calls = good, 0

    def generate(self, *a, **k):
        self.calls += 1
        if self.calls <= self.good:
            return SimpleNamespace(text='{"case_title": "X v. Y", "assessment_year": "2021-22"}', sources=[])
        raise RuntimeError("429 quota exceeded")


def test_facts_without_ai_reads_report_and_judgment():
    f = facts_without_ai(parse_report(REPORT), SOURCE)
    assert f["case_title"] == "Voltamp Transformers Ltd. v. DCIT"
    assert f["appellant"] == "Voltamp Transformers Ltd."
    assert f["respondent"].startswith("Deputy Commissioner")
    assert f["assessment_year"] == "2021-22"
    assert f["case_number"].startswith("I.T.A. No. 393/Chny/2024")
    assert f["judgment_date"] == "14-09-2026"
    assert f["outcome"] == "Partly allowed"
    assert "court" in f and "Chennai" in f["court"]


def test_fill_missing_only_fills_empty_fields():
    merged, filled = fill_missing({"case_title": "A v. B", "assessment_year": "Not stated", "appellant": ""},
                                  {"case_title": "Other", "assessment_year": "2021-22", "appellant": "A"})
    assert merged["case_title"] == "A v. B" and merged["assessment_year"] == "2021-22"
    assert sorted(filled) == ["appellant", "assessment_year"]


def test_one_good_reading_is_kept_when_the_second_fails():
    res = run_consistency(FailingClient(good=1), "text", "text", runs=2)
    assert res.has_facts and not res.ok and res.merged()["assessment_year"] == "2021-22"
    assert "only one AI reading" in res.summary_line()
    none = run_consistency(FailingClient(good=0), "text", "text", runs=2)
    assert not none.has_facts and "failed" in none.summary_line()


def test_maker_checker_flow(tmp_path):
    repo = Repository(tmp_path / "r.db")
    rec = repo.add(JudgmentRecord(case_title="A v. B", assessment_year="", created_by="Preparer"))
    repo.set_returned(rec.id, "Reviewer", "Assessment year missing")
    r = repo.get(rec.id)
    assert r.status == STATUS_RETURNED and r.return_reason == "Assessment year missing"
    r.assessment_year = "2021-22"
    assert repo.update_details(r, "Preparer") == STATUS_DRAFT            # corrected -> back to reviewer
    repo.set_verified(rec.id, "Reviewer")
    r = repo.get(rec.id)
    r.citation = "[2026] 1 ITD 1"
    assert repo.update_details(r, "Preparer") == STATUS_VERIFIED         # citation only: stays verified
    r = repo.get(rec.id)
    assert r.citation_updated_by == "Preparer"
    r.ratio = "changed"
    assert repo.update_details(r, "Preparer") == STATUS_DRAFT            # content changed: re-verify
    try:
        repo.set_returned(rec.id, "Reviewer", "")
        raise AssertionError("empty reason accepted")
    except RegisterError:
        pass
    assert repo.stats()["returned"] == 0


def test_json_export(tmp_path):
    facts = {"case_title": "A v. B", "sections": ["194C"], "sections_2025": ["393"], "assessment_year": "2021-22"}
    doc = build_final_document(parse_report(REPORT), facts, approved_by="R")
    data = build_json(doc, facts, "R", "17 Oct 2026", "JIA-2026-0001")
    assert data["key_facts"]["sections_income_tax_act_1961"] == ["194C"]
    assert data["key_facts"]["sections_income_tax_act_2025"] == ["393"]
    assert data["sections"] and "[Court Finding]" not in json.dumps(data)
    path = save_json(data, tmp_path / "a.json")
    assert json.loads(path.read_text(encoding="utf-8"))["register_ref"] == "JIA-2026-0001"


def test_return_with_items_to_correct(tmp_path):
    repo = Repository(tmp_path / "r.db")
    rec = repo.add(JudgmentRecord(case_title="A v. B", created_by="P"))
    repo.set_returned(rec.id, "Reviewer", "", ["Important Precedents Cited", "Assessment year"])
    r = repo.get(rec.id)
    assert r.status == STATUS_RETURNED and r.return_fields == ["Important Precedents Cited", "Assessment year"]
    try:
        repo.set_returned(rec.id, "Reviewer", "", [])
        raise AssertionError("nothing to correct accepted")
    except RegisterError:
        pass


def test_blank_draft_greeting_placeholder():
    from judgment_analyzer.email_composer import BLANK_GREETING, EmailContent, SenderProfile, render_email

    msg = render_email(EmailContent(subject="S", intro="I", body_markdown="## A\n\nB",
                                    sender=SenderProfile(name="R", email="r@x.com")), "", "", greeting=BLANK_GREETING)
    assert msg.text.startswith("Dear <<Recipient name>>,") and "&lt;&lt;Recipient name&gt;&gt;" in msg.html
    assert msg.to_email == ""


def test_returned_entry_goes_back_to_draft_whatever_was_corrected(tmp_path):
    repo = Repository(tmp_path / "r.db")
    for change in ({"citation": "[2026] 1 ITD 1"}, {"issue_tags": ["tds"]}, {"report_md": "## 11. Important "
                                                                                          "Precedents Cited\n\n- X"}, {}):
        rec = repo.add(JudgmentRecord(case_title="A v. B", created_by="P"))
        repo.set_returned(rec.id, "Reviewer", "fix it", ["Reported citation"])
        r = repo.get(rec.id)
        for k, v in change.items():
            setattr(r, k, v)
        assert repo.update_details(r, "P") == STATUS_DRAFT, change
        assert repo.get(rec.id).status == STATUS_DRAFT


def test_draft_stays_draft_and_verified_citation_stays_verified(tmp_path):
    repo = Repository(tmp_path / "r.db")
    rec = repo.add(JudgmentRecord(case_title="A v. B"))
    r = repo.get(rec.id)
    r.ratio = "new"
    assert repo.update_details(r, "P") == STATUS_DRAFT
    repo.set_verified(rec.id, "Rev")
    r = repo.get(rec.id)
    r.issue_tags = ["x"]
    assert repo.update_details(r, "P") == STATUS_VERIFIED
