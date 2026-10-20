import csv
import email
import threading
from types import SimpleNamespace

import pytest
from conftest import SAMPLE_REPORT

from judgment_analyzer import mailer
from judgment_analyzer.email_composer import (EmailContent, SenderProfile, build_client_body, clean_for_client,
                                              default_subject, extract_case_title, find_review_items,
                                              load_sender_profile, render_email, save_sender_profile)
from judgment_analyzer.pdf_processor import CancelledError
from judgment_analyzer.recipients import (RecipientFileError, create_template, is_valid_email,
                                          load_recipients)
from judgment_analyzer.response_parser import parse_report


# ------------------------------------------------------------- cleaning ---
@pytest.mark.parametrize("raw,expected", [
    ("Appeal allowed (p. 3).", "Appeal allowed."),
    ("Facts found (pp. 3, 6, 7) and noted.", "Facts found and noted."),
    ("Held (pp. 3-5; p. 9).", "Held."),
    ("Discussed (pages 12 to 14).", "Discussed."),
    ("See (see p. 4) here", "See here"),
    ("Ruling [p. 2].", "Ruling."),
    ("[Court Finding] Section 9 does not apply.", "Section 9 does not apply."),
    ("- **[AI Observation]** Impact likely.", "- Impact likely."),
    ("{AI Observation} Impact likely.", "Impact likely."),
    ("Section 9(2) and Article 5 (1) remain (para 12).", "Section 9(2) and Article 5 (1) remain (para 12)."),
    ("**Bold** **text** stays", "**Bold** **text** stays"),
])
def test_clean_for_client(raw, expected):
    assert clean_for_client(raw) == expected


def test_review_items_block_on_uncertain_only():
    text = "Line one\n- [Uncertain] related-party point\n- Date: Not stated in the judgment"
    items = find_review_items(text)
    assert [(i.line_no, i.blocking) for i in items] == [(2, True), (3, False)]


def test_client_body_from_report():
    report = parse_report(SAMPLE_REPORT)
    body = build_client_body(report, [1, 2, 12])
    assert body.startswith("## Case Details")
    assert "## Practical Implications" in body
    # page references removed; labels kept in the editor for the reviewer (removed when sent)
    assert "(p." not in body and "[AI Observation]" in body
    assert "Civil Appeal No. 123 of 2024" in body
    assert extract_case_title(report) == "Alpha Traders Pvt Ltd v. Beta Revenue Authority"
    assert default_subject("X v. Y") == "Judgment update: X v. Y"


def test_render_email_personalised_and_escaped():
    sender = SenderProfile(name="R. Analyst", designation="Manager", firm="ABC & Associates", email="r@example.com")
    content = EmailContent("Judgment update: A <b> v. B", "Intro line", "## 1. Case Details\n\n- **Court:** X & Y",
                           sender)
    msg = render_email(content, "Asha Rao", "asha@example.com", salutation="Ms")
    assert msg.html.count("Dear Ms Asha Rao,") == 1 and "Dear Ms Asha Rao," in msg.text
    assert "X &amp; Y" in msg.html and "<b>Court:</b>" in msg.html
    assert "R. Analyst" in msg.html and "not constitute" not in msg.html  # no disclaimer unless a note is given
    assert "##" not in msg.text and "text-align:justify" in msg.html
    test = render_email(content, "Me", "r@example.com", subject_prefix="[TEST] ")
    assert test.subject.startswith("[TEST] ")
    assert content.fingerprint() == content.fingerprint()
    content.body_markdown += " edit"
    assert content.fingerprint() != EmailContent("Judgment update: A <b> v. B", "Intro line",
                                                 "## 1. Case Details\n\n- **Court:** X & Y", sender).fingerprint()


def test_sender_profile_validation_and_storage():
    assert SenderProfile().validate()
    p = SenderProfile(name="A", email="a@example.com", firm="ABC & Associates")
    assert p.validate() == []
    save_sender_profile(p)
    assert load_sender_profile() == p


# ----------------------------------------------------------- recipients ---
def test_email_validation():
    assert is_valid_email("a.b+c@sub.example.co.in")
    for bad in ("", "a@", "@b.com", "a b@c.com", "a@b", "a@@b.com"):
        assert not is_valid_email(bad)


def test_template_round_trip(tmp_path):
    path = create_template(tmp_path / "clients.xlsx")
    result = load_recipients(path)
    assert [r.email for r in result.recipients] == ["client@example.com", "second@example.com",
                                                     "colleague@example.com"]
    assert result.recipients[0].salutation == "Mr"
    assert [r.group for r in result.recipients] == ["Client", "Client", "Employee"]


def test_excel_validation_rules(tmp_path):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Clients list"])  # title row above the header
    ws.append(["Name", "E-mail", "Company", "Consent"])
    rows = [
        ["Good One", "good@example.com", "A", "Yes"],
        ["Dup", "GOOD@example.com", "A", ""],
        ["Bad Email", "not-an-email", "B", ""],
        ["No Email", None, "C", ""],
        [None, "noname@example.com", "D", ""],
        ["Opted Out", "out@example.com", "E", "No"],
        [None, None, None, None],
        ["Second", "mailto:second@example.com", "F", None],
    ]
    for r in rows:
        ws.append(r)
    path = tmp_path / "c.xlsx"
    wb.save(path)
    result = load_recipients(path)
    assert [r.email for r in result.recipients] == ["good@example.com", "second@example.com"]
    assert len(result.errors) == 3
    assert any("duplicate" in s for s in result.skipped) and any("opted out" in s for s in result.skipped)


def test_csv_and_bad_files(tmp_path):
    p = tmp_path / "c.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows([["Client Name", "Email ID"], ["Ravi", "ravi@example.com"]])
    assert load_recipients(p).recipients[0].name == "Ravi"
    bad = tmp_path / "x.csv"
    bad.write_text("foo,bar\n1,2\n")
    with pytest.raises(RecipientFileError, match="Client Name"):
        load_recipients(bad)
    with pytest.raises(RecipientFileError, match=".xls"):
        (tmp_path / "old.xls").write_bytes(b"x")
        load_recipients(tmp_path / "old.xls")


# --------------------------------------------------------------- mailer ---
def _messages(n=2):
    sender = SenderProfile(name="R", email="r@example.com")
    content = EmailContent("Subj", "Intro", "## 1. Case Details\n\n- X", sender)
    return [render_email(content, f"Client {i}", f"c{i}@example.com") for i in range(n)]


class FakeMail:
    def __init__(self, box):
        self.box = box

    def Save(self):
        self.box.append(("draft", self.To, self.Subject))

    def Send(self):
        self.box.append(("sent", self.To, self.Subject))


def fake_outlook(box, fail_on=None):
    account = SimpleNamespace(SmtpAddress="R@Example.com")

    calls = {"n": 0}

    class App:
        Session = SimpleNamespace(Accounts=[SimpleNamespace(SmtpAddress="other@x.com"), account])

        def CreateItem(self, kind):
            assert kind == 0
            calls["n"] += 1
            if fail_on is not None and calls["n"] - 1 == fail_on:
                raise RuntimeError("boom")
            return FakeMail(box)

    return lambda progid: App()


AUDIT_BASE = {"Approved by": "R", "Sender email": "r@example.com", "Judgment file": "j.pdf",
              "Case title": "A v B", "Content fingerprint": "abc"}


def test_outlook_drafts_and_audit(monkeypatch):
    box = []
    outlook = mailer.OutlookMailer("r@example.com", dispatch=fake_outlook(box))
    results = mailer.deliver_batch(_messages(2), mailer.MODE_DRAFT, AUDIT_BASE, outlook=outlook, pause_s=0)
    assert all(r.ok for r in results) and [b[0] for b in box] == ["draft", "draft"]
    assert outlook.account_matched
    with mailer.audit_log_path().open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["Recipient email"] for r in rows] == ["c0@example.com", "c1@example.com"]
    assert rows[0]["Status"] == "OK" and rows[0]["Delivery"] == mailer.MODE_DRAFT


def test_outlook_send_continues_after_single_failure():
    box = []
    outlook = mailer.OutlookMailer("r@example.com", dispatch=fake_outlook(box, fail_on=0))
    results = mailer.deliver_batch(_messages(3), mailer.MODE_SEND, AUDIT_BASE, outlook=outlook, pause_s=0)
    assert [r.ok for r in results] == [False, True, True]
    assert "Outlook error" in results[0].error


def test_outlook_not_startable():
    def broken(progid):
        raise OSError("no outlook")
    results = mailer.deliver_batch(_messages(3), mailer.MODE_DRAFT, AUDIT_BASE,
                                   outlook=mailer.OutlookMailer(dispatch=broken), pause_s=0)
    assert len(results) == 1 and "Could not start Outlook" in results[0].error


def test_eml_export(tmp_path):
    results = mailer.deliver_batch(_messages(2), mailer.MODE_EML, AUDIT_BASE, eml_folder=tmp_path, pause_s=0)
    assert all(r.ok for r in results)
    files = sorted(tmp_path.glob("*.eml"))
    assert len(files) == 2
    msg = email.message_from_bytes(files[0].read_bytes())
    assert msg["To"].endswith("<c0@example.com>") and msg["X-Unsent"] == "1"
    assert {p.get_content_type() for p in msg.walk()} >= {"text/plain", "text/html"}


def test_batch_cancel():
    ev = threading.Event()
    ev.set()
    with pytest.raises(CancelledError):
        mailer.deliver_batch(_messages(2), mailer.MODE_EML, AUDIT_BASE, eml_folder=".", cancel_event=ev)


def test_outlook_available_off_windows(monkeypatch):
    monkeypatch.setattr(mailer.sys, "platform", "linux")
    assert mailer.outlook_available()[0] is False


def test_subject_with_citation_and_date():
    from judgment_analyzer.email_composer import extract_citation, extract_judgment_date, format_judgment_date
    md = ("## 1. Case Details\n- Court or tribunal: ITAT Bangalore (pp. 1, 2)\n"
          "- Case title: Sreenivas Narayan v. Income-tax Officer (pp. 1, 2)\n"
          "- Citation or case number: IT Appeal No. 924 (Bang) of 2026; [2026] 190 taxmann.com 964 "
          "(Bangalore - Trib.) (p. 1)\n- Date of judgment: September 21, 2026 (p. 1)\n"
          "- Parties involved (identify each party's role): A (Assessee)\n")
    r = parse_report(md)
    assert extract_citation(r) == "[2026] 190 taxmann.com 964 (Bangalore - Trib.)"
    assert extract_judgment_date(r) == "21-09-2026"
    assert default_subject(extract_case_title(r), extract_citation(r), extract_judgment_date(r)) == (
        "Judgment update: Sreenivas Narayan v. Income-tax Officer - "
        "[2026] 190 taxmann.com 964 (Bangalore - Trib.)[21-09-2026]")
    assert "identify each" not in r.sections[1] and "- Parties involved: A (Assessee)" in r.sections[1]
    for raw, out in [("21st September, 2026", "21-09-2026"), ("21.09.2026", "21-09-2026"),
                     ("3 Jan 2025", "03-01-2025"), ("Not stated in the judgment", ""), ("2026", "")]:
        assert format_judgment_date(raw) == out
    # no citation / date -> subject still sensible
    assert default_subject("A v. B") == "Judgment update: A v. B"
    assert default_subject("A v. B", "", "01-02-2026") == "Judgment update: A v. B [01-02-2026]"
    # case number only (no law report) is used as-is
    r2 = parse_report("## 1. Case Details\n- Citation or case number: W.P. No. 12 of 2025\n")
    assert extract_citation(r2) == "W.P. No. 12 of 2025"


def test_audit_log_location_default_custom_and_carry_over(tmp_path, monkeypatch):
    from judgment_analyzer.config import user_config_dir

    # default -> Downloads (redirected to a temp folder in tests)
    assert mailer.audit_log_path().parent.name == "Downloads"
    custom = tmp_path / "OneDrive" / "Audit"
    assert mailer.audit_log_path(custom) == custom / "email_audit_log.csv"

    # rows written by an earlier version are carried over once, never overwritten
    old = user_config_dir() / "email_audit_log.csv"
    old.write_text("Timestamp,Status\nold,OK\n", encoding="utf-8-sig")
    dest = mailer.audit_log_path(custom)
    assert mailer.carry_over_audit(dest) == old
    assert "old,OK" in dest.read_text(encoding="utf-8-sig")
    assert mailer.carry_over_audit(dest) is None

    # a batch appends to the chosen file
    mailer.deliver_batch(_messages(1), mailer.MODE_EML, AUDIT_BASE, eml_folder=tmp_path / "eml",
                         pause_s=0, audit_path=dest)
    assert "c0@example.com" in dest.read_text(encoding="utf-8-sig")


def test_audit_log_locked_falls_back_with_warning(tmp_path):
    from judgment_analyzer.config import user_config_dir

    locked = tmp_path / "locked.csv"
    locked.mkdir()  # opening a directory as a file fails, like a file locked by Excel
    warnings = []
    results = mailer.deliver_batch(_messages(1), mailer.MODE_EML, AUDIT_BASE, eml_folder=tmp_path / "eml",
                                   pause_s=0, audit_path=locked, on_warning=warnings.append)
    assert results[0].ok  # the email itself is not reported as failed
    assert warnings and "open in Excel" in warnings[0]
    assert "c0@example.com" in (user_config_dir() / "email_audit_log.csv").read_text(encoding="utf-8-sig")


def test_downloads_dir_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(mailer.sys, "platform", "linux")
    monkeypatch.setattr(mailer.Path, "home", classmethod(lambda cls: tmp_path))
    assert mailer.downloads_dir() == tmp_path  # no Downloads folder -> home
    (tmp_path / "Downloads").mkdir()
    assert mailer.downloads_dir() == tmp_path / "Downloads"
