"""The four changes of version 3.2, driven through the real application:

  1. the sample Excel template built into the Import page
  2. PDF letters, and sending a PDF (generated, or the client's signed scan)
  3. a reply that differs from the books is a Mismatch, never 'Agreed'
  4. the raised, shadowed interface in both themes
"""
import importlib.util, os, shutil, sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
WORK = "/home/claude/pytest/cwork"
shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK, exist_ok=True)
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "appdata")

spec = importlib.util.spec_from_file_location(
    "bcg", "/home/claude/balance_confirmation_generator.py")
bcg = importlib.util.module_from_spec(spec)
sys.modules["bcg"] = bcg
spec.loader.exec_module(bcg)

from PyQt6.QtWidgets import (QApplication, QMessageBox,
                             QGraphicsDropShadowEffect, QFrame)
from PyQt6.QtCore import QDate, QEvent
from PyQt6.QtGui import QColor
import openpyxl

PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name +
          ("" if cond or not detail else "  ->  " + str(detail)[:220]))

USER_FILE = ("/mnt/user-data/attachments/b472c9a3-3d4f-5cd5-8f82-4907e2f57523/"
             "e66dfb29-1794329099263_Sampled_listings.xlsx")
CLIENT = "Example Manufacturing Private Limited"

QMessageBox.exec = lambda self: QMessageBox.StandardButton.Ok
app = QApplication([])
app.setStyle("Fusion")
app.setPalette(bcg.qt_palette())
app.setStyleSheet(bcg.style_sheet())
win = bcg.MainWindow()
win.resize(1440, 900)
win.show()
win.ask = lambda *a, **k: True            # the confirm dialog says yes


def pump(n=6):
    for _ in range(n):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


pump()
win.cl_name.setText(CLIENT)
win.add_client()
win.active_client()["signatory_name"] = "Mr. R. Mehta"
win.active_client()["signatory_designation"] = "Director"
win.db["settings"]["firm_name"] = "Ankit & Associates"
win.fy_year.setText("2025-26")
win.fy_end.setDate(QDate(2026, 3, 31))
win.add_year()
win.aud_name.setText("Audit team")
win.aud_email.setText("audit@firm.example")
win.add_auditor()

# ======================================================================
print("\n== 1. The sample template ==")
check("the Import page offers the download",
      hasattr(win, "download_sample_template"))
template = win.download_sample_template(path=os.path.join(WORK, "template"))
check("saved with the .xlsx ending added",
      template and template.endswith(".xlsx") and os.path.exists(template),
      template)
book = openpyxl.load_workbook(template)
check("two sheets, the data sheet first",
      book.sheetnames == ["Party balances", "How to fill"], book.sheetnames)
sheet = book["Party balances"]
headers = [c.value for c in sheet[1]]
check("the headings follow the firm's own listing",
      headers == ["Name", "Address line 1", "Pincode", "State", "Country",
                  "Currency", "Closing balance", "Category", "Email ID",
                  "Contact person"], headers)
check("four example rows, one per category",
      sorted(sheet.cell(row=r, column=8).value for r in range(2, 6))
      == sorted(bcg.CATEGORIES))
validations = sheet.data_validations.dataValidation
check("category is a drop-down of the four categories",
      any("Trade Receivable" in (v.formula1 or "") and
          "Advance to Vendors" in (v.formula1 or "") for v in validations))
check("the header row is frozen", sheet.freeze_panes == "A2")
check("the instructions name every column",
      all(any(h == row[0].value for row in book["How to fill"].iter_rows())
          for h in headers))

win.load_file(template)
pump()
check("the application opens it on the data sheet",
      win.active_sheet == "Party balances", win.active_sheet)
missing = [k for k, v in win.mapping.items() if v["status"] != "detected"]
check("every column is recognised without mapping", not missing, missing)
checks = win.validation()
check("all four rows are ready to generate",
      len(checks["generable"]) == 4 and checks["ready"],
      (len(checks["generable"]), checks["ready"]))
confs = [win.to_confirmation(r) for r in checks["generable"]]
first = confs[0]
check("address, pincode, state and country are joined",
      first["address_lines"] and "400057" in " ".join(first["address_lines"])
      and "Maharashtra" in " ".join(first["address_lines"]),
      first["address_lines"])
check("the pincode does not read as a decimal",
      "400057.0" not in " ".join(first["address_lines"]))
check("the contact person comes through",
      first["contact_person"] == "Mr. A. Shah", first["contact_person"])

win.load_file(USER_FILE)
pump()
own = win.validation()
check("the listing you attached reads the same way",
      len(own["generable"]) == 2 and
      [k for k, v in win.mapping.items()
       if v["status"] != "detected"] == ["contactPerson"],
      len(own["generable"]))
win.load_file(template)
pump()

# ======================================================================
print("\n== 2. PDF letters ==")
out = os.path.join(WORK, "out")
os.makedirs(out, exist_ok=True)
win.db["settings"]["output_folder"] = out
folder = win.run_output_folder()
os.makedirs(folder, exist_ok=True)
worker = bcg.GenerateWorker(confs, folder)
produced = []
worker.produced.connect(produced.append)
worker.run()
check("a PDF is written beside every Word letter",
      all(p["pdf_path"] and os.path.exists(p["pdf_path"]) and
          os.path.exists(p["path"]) for p in produced))
check("the PDF takes the letter's own name",
      all(p["pdf_filename"] == p["filename"][:-5] + ".pdf" for p in produced))
check("each is a real PDF",
      all(p["pdf_data"][:5] == b"%PDF-" for p in produced))
check("each sits on one page",
      all(bcg.pdf_page_count(p["pdf_data"]) == 1 for p in produced),
      [bcg.pdf_page_count(p["pdf_data"]) for p in produced])
tall = bcg.pdf_bytes(confs[0], top_space_cm=6.0)
check("still one page with 6 cm left for the letterhead",
      bcg.pdf_page_count(tall) == 1, bcg.pdf_page_count(tall))
long_conf = dict(confs[0])
long_conf["party_name"] = ("The Very Long Named International Trading and "
                           "Manufacturing Corporation Private Limited")
long_conf["address_lines"] = ["Line %d of a long address" % i
                              for i in range(1, 7)]
long_conf["basis"] = "period"
long_conf["period_start"] = "2025-04-01"
check("a long name and address still fit one page",
      bcg.pdf_page_count(bcg.pdf_bytes(long_conf, 4.0)) == 1)
try:
    from pypdf import PdfReader
    import io
    text = PdfReader(io.BytesIO(produced[0]["pdf_data"])).pages[0] \
        .extract_text()
    check("the PDF carries the letter's wording",
          "ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION" in text and
          "We hereby confirm that the amount payable by us" in text and
          confs[0]["reference"] in text, text[:120])
except ImportError:
    print("  SKIP  text check (pypdf not installed)")

win.generated = produced
win.save_run(folder)
check("the run records the PDF name",
      all(d.get("pdf_filename", "").endswith(".pdf")
          for d in win.db["runs"][0]["documents"]))

print("\n== 3. What is attached to the e-mail ==")
win.go("email")
pump()
check("PDF is the default attachment", win.attach_key() == "pdf")
check("the queue lists the PDF for each party",
      all(q["attachment"].endswith(".pdf") for q in win.queue.values()),
      [q["attachment"] for q in win.queue.values()])
name, payload, problem = win.attachment_for(produced[0])
draft = bcg.build_email_message(confs[0], name, payload, win.mail_options())
part = list(draft.iter_attachments())[0]
check("the message carries a PDF",
      part.get_content_type() == "application/pdf" and
      part.get_filename().endswith(".pdf") and
      part.get_payload(decode=True)[:5] == b"%PDF-", part.get_content_type())
check("the request marks itself as ours",
      draft["X-BCG-Request"] == confs[0]["reference"], draft["X-BCG-Request"])

win.attach_mode.setCurrentIndex(win.attach_mode.findData("docx"))
pump()
name, payload, problem = win.attachment_for(produced[0])
draft = bcg.build_email_message(confs[0], name, payload, win.mail_options())
part = list(draft.iter_attachments())[0]
check("Word can still be chosen",
      name.endswith(".docx") and "wordprocessingml" in part.get_content_type())

win.attach_mode.setCurrentIndex(win.attach_mode.findData("signed"))
pump()
check("the choice is remembered",
      win.db["settings"]["mail"]["attach_mode"] == "signed")
name, payload, problem = win.attachment_for(produced[0])
check("with nothing linked, nothing is substituted",
      not payload and "No signed PDF" in problem, problem)
check("the queue shows nothing linked",
      all(q["attachment"].startswith("—") for q in win.queue.values()))

# the client prints, signs and scans: three scans come back, named three ways
signed = os.path.join(WORK, "signed")
os.makedirs(signed)
scan = bcg.pdf_bytes(confs[0])                       # stands in for a scan
by_party = {p["conf"]["party_name"]: p for p in produced}
names = {
    "ABC Private Limited": "ABC Private Limited - Trade Receivable signed.pdf",
    "XYZ Suppliers LLP": "scan_%s.pdf"
                         % by_party["XYZ Suppliers LLP"]["conf"]["reference"],
    "Customer P Limited": "customer p limited (signed copy).PDF",
}
for filename in names.values():
    with open(os.path.join(signed, filename), "wb") as handle:
        handle.write(scan)
with open(os.path.join(signed, "unrelated invoice.pdf"), "wb") as handle:
    handle.write(scan)
with open(os.path.join(signed, "notes.pdf"), "wb") as handle:
    handle.write(b"this is not a pdf at all")
win.link_signed_folder(folder=signed)
pump()
linked = {p["conf"]["party_name"]: os.path.basename(p.get("signed_path") or "")
          for p in produced}
check("linked by the letter's file name",
      linked["ABC Private Limited"] == names["ABC Private Limited"], linked)
check("linked by the reference code",
      linked["XYZ Suppliers LLP"] == names["XYZ Suppliers LLP"], linked)
check("linked by the party name alone",
      linked["Customer P Limited"] == names["Customer P Limited"], linked)
check("a party with no scan stays unlinked",
      linked["Vendor Q Industries"] == "", linked)
check("the auditor is told the count",
      "3 signed PDFs linked" in win.status_strip.text() and
      "1 party still without one" in win.status_strip.text(),
      win.status_strip.text())
check("a file that is not a PDF is refused on a row",
      win.choose_signed_pdf(produced[3]["id"],
                            os.path.join(signed, "notes.pdf")) is None
      and not produced[3].get("signed_path"))

win.link_signed_folder(folder=folder)                # the output folder itself
pump()
check("the unsigned originals are never taken for signed copies",
      not by_party["Vendor Q Industries"].get("signed_path") and
      "unsigned original" in win.status_strip.text(),
      win.status_strip.text())

# send, with a stand-in for the mail server
SENT = []


class FakeServer:
    def send_message(self, message):
        SENT.append(message)

    def quit(self):
        pass


bcg.smtp_connect = lambda *a, **k: FakeServer()
win.mail_username.setText("audit@firm.example")
win.mail_password_edit.setText("app-password")
win.save_mail_settings()
win.delay_spin.setValue(0)
win.refresh_email()
win.start_send(False)
for _ in range(400):
    pump(2)
    if win.send_thread is None:
        break
    app.thread().msleep(10)
sent_to = sorted(m["To"] for m in SENT)
check("three signed letters go out", len(SENT) == 3, sent_to)
check("the party without a signed PDF is held back",
      "receivables@vendorq-example.com" not in sent_to, sent_to)
held = [q for q in win.queue.values() if q["party"] == "Vendor Q Industries"][0]
check("and says why", held["status"] == "pending" and
      "No signed PDF linked" in held["detail"], held)
attached = {m["To"]: list(m.iter_attachments())[0].get_filename()
            for m in SENT}
check("each party gets its own scan",
      attached["accounts@abc-example.com"] == names["ABC Private Limited"] and
      attached["finance@xyz-example.com"] == names["XYZ Suppliers LLP"],
      attached)
documents = {d["party_name"]: d for d in win.db["runs"][0]["documents"]}
check("the Message-ID is kept for matching the reply",
      documents["ABC Private Limited"].get("message_id", "").startswith("<"),
      documents["ABC Private Limited"].get("message_id"))

# ======================================================================
print("\n== 4. A different figure is a Mismatch ==")
check("the status is called Mismatch", bcg.STATUS_VARIANCE == "Mismatch")
LETTER = (
    "ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION\nRef: BCG-7F3K2A\n"
    "XYZ Pvt Ltd\nXYZ 11th road, Jogeshwari, Mumbai 400002\n"
    "Our statutory auditors, Ankit & Associates, are engaged in an audit. "
    "According to our records, the amount due from you as at 31 March 2026 "
    "is INR 35,00,000.00 (In Words: Rupees Thirty Five Lakh Only)\n"
    "If the amount is not in agreement with your records, please notify our "
    "auditors directly, with a copy to us, of the amount shown by your "
    "records and provide full particulars of the difference.\n"
    "We hereby confirm that the amount payable by us to Client Ltd as on "
    "31 March 2026 is INR %s\nName and Title : ____\nSignature : ____")
BLANK, FILLED_SAME, FILLED_LESS = ("______________", "35,00,000.00",
                                   "25,00,000.00")
QUOTE = ("\n\nOn Tue, 10 Nov 2026 at 14:05, Audit <audit@firm.example> wrote:\n"
         "> Please find attached a balance confirmation request in respect "
         "of the Trade Receivable balance appearing in its books as at 31 "
         "March 2026, being INR 35,00,000.00.\n> Should the amount not agree "
         "with your records, please let us know the balance as per your "
         "books together with particulars of the difference.\n")
doc = {"id": "d1", "party_name": "XYZ Pvt Ltd", "email": "p@xyz.example",
       "amount": 3500000.0, "currency": "INR", "reference": "BCG-7F3K2A",
       "email_status": "sent", "sent_at": "2026-11-01", "thread_id": "t1",
       "message_id": "<sent-1@firm.example>"}


def outcome(body, attachment=None, **extra):
    reply = {"id": "r", "thread_id": "t1", "from_email": "p@xyz.example",
             "subject": "Re: Balance confirmation", "in_reply_to": "<sent-1>",
             "received_at": "2026-11-10", "body": body + QUOTE,
             "attachments": [{"name": "scan.pdf", "text": attachment}]
             if attachment else []}
    reply.update(extra)
    rows, exceptions = bcg.build_reconciliation([doc], [reply])
    return rows[0], exceptions


CASES = [
    ("the case reported: 35,00,000 sent, 25,00,000 confirmed in the reply",
     "As per our books the balance payable is Rs. 25,00,000.", None,
     "Mismatch", 2500000.0),
    ("the same, with the letter attached back",
     "Our balance is INR 25,00,000.00, not as stated.", LETTER % BLANK,
     "Mismatch", 2500000.0),
    ("the slip completed with a lower figure",
     "PFA signed confirmation.", LETTER % FILLED_LESS, "Mismatch", 2500000.0),
    ("no currency sign", "We confirm 25,00,000 only.", None,
     "Mismatch", 2500000.0),
    ("in lakhs", "Balance in our books is Rs 25 lakhs.", None,
     "Mismatch", 2500000.0),
    ("a bare number", "Outstanding as per our ledger is 2500000.", None,
     "Mismatch", 2500000.0),
    ("the slip completed with the same figure",
     "PFA.", LETTER % FILLED_SAME, bcg.STATUS_AGREED, 3500000.0),
    ("agreed in the party's own words",
     "We confirm the balance of Rs. 35,00,000 is correct.", None,
     bcg.STATUS_AGREED, 3500000.0),
    ("the letter merely returned, slip unread",
     "PFA.", LETTER % BLANK, bcg.STATUS_REVIEW, None),
    ("disputed without a figure",
     "The balance is not in agreement with our records.", LETTER % BLANK,
     bcg.STATUS_REVIEW, None),
    ("dates, pincodes and phone numbers are not figures",
     "Received on 10.11.2026 at our office (400002). Call 9876543210. "
     "Will revert on the balance as on 31 March 2026.", None,
     bcg.STATUS_REVIEW, None),
]
for label, body, attachment, status, amount in CASES:
    row, _ = outcome(body, attachment)
    check(label + " -> " + status,
          row["status"] == status and row["confirmed_amount"] == amount,
          (row["status"], row["confirmed_amount"], row["note"]))

row, _ = outcome("As per our books the balance payable is Rs. 25,00,000.")
check("the variance is confirmed less books", row["variance"] == -1000000.0,
      row["variance"])
check("the remark says so in words",
      "less than the books by" in row["note"] and "10,00,000" in row["note"],
      row["note"])
row, _ = outcome("PFA.", LETTER % BLANK)
check("a returned letter is explained, not guessed",
      "could not be read" in row["note"], row["note"])
quoted_only, _ = outcome("Noted, will revert.")
check("the figure in our own quoted e-mail is never read back",
      quoted_only["status"] == bcg.STATUS_REVIEW and
      quoted_only["confirmed_amount"] is None)

print("\n== 5. Our own request is not a reply ==")
own_copy = {"id": "own", "thread_id": "t1", "from_email": "audit@firm.example",
            "subject": "Balance confirmation request [BCG-7F3K2A]",
            "in_reply_to": "", "received_at": "2026-11-01",
            "body": "Please find attached ... being INR 35,00,000.00.",
            "attachments": [{"name": "letter.pdf", "text": LETTER % BLANK}]}
ignored = []
rows, _ = bcg.build_reconciliation([doc], [own_copy],
                                   own_addresses=("audit@firm.example",),
                                   ignored=ignored)
check("the copy sent to the team does not agree the balance",
      rows[0]["status"] == "Pending" and len(ignored) == 1,
      rows[0]["status"])
flagged = dict(own_copy, from_email="someone@else.example", own_request=True)
rows, _ = bcg.build_reconciliation([doc], [flagged])
check("nor one the bridge marked as ours", rows[0]["status"] == "Pending")
by_id = dict(own_copy, from_email="x@y.example",
             message_id="<sent-1@firm.example>")
rows, _ = bcg.build_reconciliation([doc], [by_id])
check("nor one carrying the Message-ID we sent", rows[0]["status"] == "Pending")
real = {"id": "real", "thread_id": "t1", "from_email": "p@xyz.example",
        "subject": "Re: Balance confirmation", "in_reply_to": "<sent-1>",
        "received_at": "2026-11-09",
        "body": "Balance as per our books is Rs. 25,00,000." + QUOTE,
        "attachments": []}
rows, _ = bcg.build_reconciliation([doc], [real, own_copy],
                                   own_addresses=("audit@firm.example",))
check("with both on record the party's reply decides",
      rows[0]["status"] == "Mismatch" and rows[0]["variance"] == -1000000.0,
      (rows[0]["status"], rows[0]["variance"]))
self_test = dict(real, from_email="audit@firm.example")
rows, _ = bcg.build_reconciliation([doc], [self_test],
                                   own_addresses=("audit@firm.example",))
check("a reply sent from the same mailbox still counts as a reply",
      rows[0]["status"] == "Mismatch", rows[0]["status"])

print("\n== 6. The reports show it ==")
for index, d in enumerate(win.db["runs"][0]["documents"]):
    d["email_status"] = "sent"
    d["sent_at"] = "2026-10-20"
    d["thread_id"] = "t%d" % index
xyz = documents["XYZ Suppliers LLP"]
abc = documents["ABC Private Limited"]
win.db["replies"] = [
    {"id": "a", "thread_id": abc["thread_id"],
     "from_email": "accounts@abc-example.com", "subject": "Re: confirmation",
     "in_reply_to": "<x>", "received_at": "2026-11-02",
     "body": "We confirm the balance of INR 79,60,098.48 is correct.",
     "attachments": []},
    {"id": "b", "thread_id": xyz["thread_id"],
     "from_email": "finance@xyz-example.com", "subject": "Re: confirmation",
     "in_reply_to": "<y>", "received_at": "2026-11-03",
     "body": "As per our books the balance is Rs. 25,00,000 only.",
     "attachments": []},
    {"id": "c", "thread_id": xyz["thread_id"],
     "from_email": "audit@firm.example",
     "subject": "Balance confirmation request", "in_reply_to": "",
     "received_at": "2026-10-20", "body": "being INR 35,15,723.34",
     "attachments": [{"name": "l.pdf", "text": LETTER % BLANK}]},
]
win.persist()
win.go("recon")
pump()
rows = {r["party_name"]: r for r in win.recon_rows}
check("XYZ shows as a Mismatch on the page",
      rows["XYZ Suppliers LLP"]["status"] == "Mismatch",
      rows["XYZ Suppliers LLP"]["status"])
check("with the variance against the client's books",
      abs(rows["XYZ Suppliers LLP"]["variance"] - (2500000 - 3515723.34))
      < 0.01, rows["XYZ Suppliers LLP"]["variance"])
check("ABC still agrees", rows["ABC Private Limited"]["status"] == bcg.STATUS_AGREED)
check("the summary counts one mismatch", win.recon_summary["variance"] == 1)
check("the copy of our own request is set aside and said so",
      len(win.recon_ignored) == 1 and
      "own request ignored" in win.recon_scope.text(), win.recon_scope.text())
report = bcg.build_report(bcg.REPORT_COMPARISON, win.recon_rows,
                          win.recon_exceptions)
heads = [h for h, _k, _t in report["columns"]]
check("Requested vs confirmed has the variance columns",
      "As per client's books" in heads and "Confirmed by party" in heads and
      "Variance (confirmed less books)" in heads and "Variance %" in heads
      and "Remark" in heads, heads)
check("mismatches are listed first",
      report["rows"][0]["party_name"] == "XYZ Suppliers LLP" and
      report["rows"][0]["status"] == "Mismatch")
check("the total variance is carried",
      abs(report["totals"]["variance"] - (2500000 - 3515723.34)) < 0.01,
      report["totals"]["variance"])
xlsx = os.path.join(WORK, "reports.xlsx")
bcg.write_reports_xlsx(xlsx, win.current_reports(), win.report_heading())
cells = [str(c.value) for row in
         openpyxl.load_workbook(xlsx)["Requested vs confirmed"].iter_rows()
         for c in row if c.value is not None]
check("the Excel report says Mismatch and gives the remark",
      "Mismatch" in cells and any("less than the books by" in c
                                  for c in cells), cells[:12])
pdf = os.path.join(WORK, "reports.pdf")
bcg.write_reports_pdf(pdf, win.current_reports(), win.report_heading())
check("the PDF report is written", bcg.looks_like_pdf(pdf))

# ======================================================================
print("\n== 7. The raised interface ==")


def luminance(colour):
    c = QColor(colour)
    def channel(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return (0.2126 * channel(c.redF()) + 0.7152 * channel(c.greenF())
            + 0.0722 * channel(c.blueF()))


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


sheet_text = bcg.style_sheet()
check("surfaces are graded, not flat", sheet_text.count("qlineargradient") >= 8,
      sheet_text.count("qlineargradient"))
check("buttons travel when pressed", "QPushButton:pressed" in sheet_text)
for mode in ("dark", "light"):
    t = bcg.THEMES[mode]
    for stop in ("accent_top", "accent_bot"):
        check("%s: button text on %s >= 4.5:1" % (mode, stop),
              contrast(t["accent_text"], t[stop]) >= 4.5,
              round(contrast(t["accent_text"], t[stop]), 2))
    for stop in ("card_hi", "card_lo"):
        check("%s: muted text on %s >= 4.5:1" % (mode, stop),
              contrast(t["text_mute"], t[stop]) >= 4.5,
              round(contrast(t["text_mute"], t[stop]), 2))
        for tone in ("ok", "warn", "err", "info"):
            check("%s: %s on %s >= 4.5:1" % (mode, tone, stop),
                  contrast(t[tone], t[stop]) >= 4.5,
                  round(contrast(t[tone], t[stop]), 2))
    for stop in ("btn_hi", "btn_lo"):
        check("%s: button caption on %s >= 7:1" % (mode, stop),
              contrast(t["text"], t[stop]) >= 7,
              round(contrast(t["text"], t[stop]), 2))
    check("%s: text in a field >= 7:1" % mode,
          contrast(t["text"], t["well"]) >= 7,
          round(contrast(t["text"], t["well"]), 2))

cards = [w for w in win.findChildren(QFrame)
         if w.objectName() in ("CardDark", "CardLight", "StatCard")]
check("there are cards to lift", len(cards) > 10, len(cards))
check("every card casts a shadow",
      all(isinstance(c.graphicsEffect(), QGraphicsDropShadowEffect)
          for c in cards))
dark_shadow = cards[0].graphicsEffect().color().getRgb()
win.toggle_theme()
pump()
light_shadow = cards[0].graphicsEffect().color().getRgb()
check("the shadow follows the theme", dark_shadow != light_shadow and
      light_shadow == tuple(bcg.THEMES["light"]["shadow_rgba"]),
      (dark_shadow, light_shadow))
for page in ("dashboard", "import", "generate", "email", "recon", "settings"):
    win.go(page)
    pump(8)
check("every page still draws in light mode", win.isVisible())
win.toggle_theme()
pump()

print("\n== Rupee notation and a figure standing alone ==")
_f = bcg.find_figures("Rs 25,00,000/-", "email body")
check("'Rs 25,00,000/-' is read as money", bool(_f) and _f[0]["amount"] == 2500000.0, _f)
_f = bcg.find_figures("Thanks\n25,00,000\nRegards", "email body")
check("a figure alone on its line is read", bool(_f) and _f[0]["amount"] == 2500000.0, _f)
check("a date with slashes is still not money", bcg.find_figures("dated 31/03/2026", "email body") == [])
check("a pincode in an address is still not money", bcg.find_figures("Mumbai 400001, India", "email body") == [])
_doc = {"id": "z", "party_name": "Z", "amount": 3500000.0, "currency": "INR", "email_status": "sent", "sent_at": "2026-11-08", "thread_id": "tz"}
_rows, _ = bcg.build_reconciliation([_doc], [{"id": "rz", "thread_id": "tz", "from_email": "z@z.in", "subject": "Re:", "received_at": "2026-11-09", "body": "25,00,000", "attachments": []}])
check("35 lakh sent, 25 lakh confirmed is a Mismatch", _rows[0]["status"] == bcg.STATUS_VARIANCE and _rows[0]["variance"] == -1000000.0, (_rows[0]["status"], _rows[0]["variance"]))

print("\n" + "-" * 54)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("Failed: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
