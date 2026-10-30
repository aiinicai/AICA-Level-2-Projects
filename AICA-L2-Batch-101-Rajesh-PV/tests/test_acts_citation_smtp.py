"""Tests for separate 1961 / 2025 Act sections, citation update in the register,
SMTP diagnosis, emails without recipients."""

import socket
import sqlite3
import threading

from judgment_analyzer.consistency import compare_runs, parse_json_object
from judgment_analyzer.email_composer import EmailContent, SenderProfile, render_email
from judgment_analyzer.mailer import MODE_EML, SmtpMailer, SmtpSettings, build_mime, deliver_batch
from judgment_analyzer.repository import (ACT_1961, ACT_2025, JudgmentRecord, RegisterError, Repository)
from judgment_analyzer.sections_act import (base_number, context_act, definite_act, has_letter_suffix,
                                            sort_sections, split_legacy)

HEADNOTE = ("I. Section 194C, read with section 201, of the Income-tax Act, 1961 / Section 393, read with section 398 "
            "of the Income-tax Act, 2025 - Deduction of tax at source. The assessee relied on section 194C(6) of "
            "the Act.")


# ------------------------------------------------------------------ Acts ---
def test_number_rules():
    assert base_number("194C(6)") == 194 and base_number("36(1)(va)") == 36 and base_number("80-IA") == 80
    assert has_letter_suffix("44AE") and has_letter_suffix("80-IA") and not has_letter_suffix("201(1A)")
    assert definite_act("393") == "2025" and definite_act("299") == "2025"
    assert definite_act("298") is None and definite_act("68") is None


def test_context_reads_the_act_named_after_the_section():
    assert context_act("194C", HEADNOTE) == "1961"
    assert context_act("201", HEADNOTE) == "1961"
    assert context_act("393", HEADNOTE) == "2025"
    assert context_act("398", HEADNOTE) == "2025"
    assert context_act("68", HEADNOTE) is None


def test_sort_moves_numbers_above_298_and_flags_doubtful():
    r = sort_sections(["194C(6)", "201", "393"], ["398", "194C"], HEADNOTE)
    assert r.sections_1961 == ["194C(6)", "201"]
    assert r.sections_2025 == ["393", "398", "194C"]
    assert r.moved == ["393"]
    assert any("194C" in n and "1961 Act style" in n for n in r.notes)
    assert any("393" in n and "moved" in n for n in r.notes)


def test_split_legacy_single_list():
    assert split_legacy(["194C", "393", "201"], HEADNOTE) == (["194C", "201"], ["393"])


def test_key_facts_have_separate_act_lists():
    facts = parse_json_object('{"sections": ["194C", "201", "393"], "sections_2025": ["398"]}')
    assert facts["sections"] == ["194C", "201"]
    assert facts["sections_2025"] == ["393", "398"]
    old = parse_json_object('{"sections": ["68", "400"]}')          # older single-list answer
    assert old["sections"] == ["68"] and old["sections_2025"] == ["400"]


def test_comparison_covers_both_acts():
    a = parse_json_object('{"sections": ["194C"], "sections_2025": ["393"]}')
    b = parse_json_object('{"sections": ["194C"], "sections_2025": []}')
    status = {c.key: c.status for c in compare_runs([a, b])}
    assert status["sections"] == "Agree" and status["sections_2025"] == "Runs disagree"


# -------------------------------------------------------------- register ---
def test_register_act_filter_and_citation_update(tmp_path):
    repo = Repository(tmp_path / "reg.db")
    a = repo.add(JudgmentRecord(case_title="A v. ITO", sections=["194C", "201"], sections_2025=["393"]))
    repo.add(JudgmentRecord(case_title="B v. DCIT", sections=["68"]))
    assert [r.case_title for r in repo.search(section="393", act=ACT_2025)] == ["A v. ITO"]
    assert repo.search(section="393", act=ACT_1961) == []
    assert [r.case_title for r in repo.search(section="194C")] == ["A v. ITO"]       # either Act
    assert repo.get(a.id).sections_display == "194C, 201 (1961); 393 (2025)"
    repo.update_citation(a.id, "[2026] 190 taxmann.com 1 (Trib.)", "RR")
    rec = repo.get(a.id)
    assert rec.citation.startswith("[2026]") and rec.citation_updated_by == "RR" and rec.citation_updated_at
    try:
        repo.update_citation(a.id, "", "RR")
        raise AssertionError("empty citation accepted")
    except RegisterError:
        pass
    assert ("393 (2025)", 1) in repo.stats()["top_sections"]


def test_old_register_is_upgraded(tmp_path):
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.executescript("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);"
                      "INSERT INTO meta VALUES ('schema_version', '1');"
                      "CREATE TABLE judgments (id INTEGER PRIMARY KEY AUTOINCREMENT, ref TEXT UNIQUE NOT NULL, "
                      "pdf_sha256 TEXT, file_name TEXT, pdf_copy TEXT, court TEXT, bench TEXT, case_title TEXT, "
                      "citation TEXT, case_number TEXT, judgment_date TEXT, assessment_year TEXT, appellant TEXT, "
                      "respondent TEXT, sections TEXT, issues TEXT, issue_tags TEXT, outcome TEXT, in_favour_of TEXT, "
                      "ratio TEXT, executive_summary TEXT, report_md TEXT, source_check_score REAL, "
                      "source_check_summary TEXT, consistency_summary TEXT, model TEXT, analysed_at TEXT, "
                      "status TEXT NOT NULL DEFAULT 'Draft', reviewed_by TEXT, reviewed_at TEXT, review_notes TEXT, "
                      "created_by TEXT, created_at TEXT, updated_at TEXT);"
                      "INSERT INTO judgments (ref, case_title, sections) VALUES ('JIA-2026-0001', 'Old', '[\"68\"]');")
    con.commit()
    con.close()
    repo = Repository(path)
    rec = repo.search()[0]
    assert rec.sections == ["68"] and rec.sections_2025 == []
    repo.update_citation(rec.id, "(2026) 1 ITD 1", "RR")


# ----------------------------------------------------------------- email ---
def _content():
    return EmailContent(subject="Ruling", intro="Please see below.", body_markdown="## Summary\n\nText.",
                        sender=SenderProfile(name="R", email="r@example.com"))


def test_email_without_recipient_has_no_to_header(tmp_path):
    msg = render_email(_content(), "", "")
    msg.to_name = "(no recipient - Team version)"
    assert "Dear Sir/Madam" in msg.text
    assert build_mime(msg, "R", "r@example.com", unsent=True)["To"] is None
    results = deliver_batch([msg], MODE_EML, {"Approved by": "R", "Sender email": "r@example.com"},
                            eml_folder=tmp_path, audit_path=tmp_path / "audit.csv", pause_s=0)
    assert results[0].ok and list(tmp_path.glob("*.eml"))


def test_smtp_diagnosis_names_the_failing_step():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    port = srv.getsockname()[1]

    def accept_and_close():           # behaves like an antivirus 'mail shield' dropping the connection
        for _ in range(4):
            try:
                c, _ = srv.accept()
                c.close()
            except OSError:
                return

    threading.Thread(target=accept_and_close, daemon=True).start()
    m = SmtpMailer(SmtpSettings(host="127.0.0.1", port=port, security="SSL", username="x@gmail.com"), "pw", "X",
                   "x@gmail.com", timeout=5)
    steps = m.diagnose()
    srv.close()
    assert steps[0][1] is True                                   # name lookup worked
    assert any("connect" in s and ok for s, ok, _ in steps)      # port open
    failed = [d for s, ok, d in steps if not ok]
    assert failed and "password was not checked" in failed[0]
    assert "FAIL" in SmtpMailer.diagnosis_text(steps)
