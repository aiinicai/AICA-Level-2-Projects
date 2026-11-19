"""Headless end-to-end exercise of the desktop application."""
import os, sys, shutil, tempfile, importlib.util
from datetime import date

os.environ["QT_QPA_PLATFORM"] = "offscreen"
WORK = "/home/claude/pytest/work"
shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK, exist_ok=True)
# keep the test's records out of the real application-data folder
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "appdata")

spec = importlib.util.spec_from_file_location(
    "bcg", "/home/claude/balance_confirmation_generator.py")
bcg = importlib.util.module_from_spec(spec)
sys.modules["bcg"] = bcg
spec.loader.exec_module(bcg)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QDate, Qt

PASS, FAIL = [], []
def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print(("  PASS  " if condition else "  FAIL  ") + name +
          ("" if condition or not detail else "  ->  " + str(detail)[:200]))

# ---------------------------------------------------------------- test data
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Balances"
for row in [
    ["Example Manufacturing Private Limited"],
    ["Party-wise balances as at 30.09.2026"],
    [],
    ["Sr No", "PARTY-NAME", "Address 1", "Address 2", "Closing Bal.", "CCY",
     "Nature", "E-mail ID", "Contact Person"],
    [1, "ABC Ltd", "12 MG Road", "Mumbai 400001", 125000, "INR",
     "Debtors", "ap@abc.example", "R. Rao"],
    [2, "XYZ Suppliers", "Plot 9", "Delhi 110001", "80,000", "INR",
     "Creditors", "ar@xyz.example", ""],
    [3, "Customer P Ltd", "Pune", "", 50000, "INR", "Advance Received",
     "fin@customerp.example", ""],
    [4, "Vendor Q Ltd", "Chennai", "", "₹ 30,000.00", "INR",
     "Advance Paid", "acc@vendorq.example", ""],
    [5, "Ambiguous Traders", "Nagpur", "", "1,20,000", "INR", "Advance", ""],
    [6, "No Balance Ltd", "Surat", "", "", "INR", "Trade Receivable",
     "x@nobal.example", ""],
]:
    ws.append(row)
SOURCE = os.path.join(WORK, "balances.xlsx")
wb.save(SOURCE)

OUTPUT = os.path.join(WORK, "output")
os.makedirs(OUTPUT, exist_ok=True)

# silence modal dialogs
QMessageBox.exec = lambda self: QMessageBox.StandardButton.Ok

app = QApplication([])
app.setStyle("Fusion")
app.setPalette(bcg.qt_palette())
app.setStyleSheet(bcg.style_sheet())
win = bcg.MainWindow()
win.show()

print("\n== Start-up ==")
check("window opens", win.isVisible())
geo = win.geometry()
check("window fits a 1366x768 screen", geo.width() <= 1380 and geo.height() <= 900,
      "%dx%d" % (geo.width(), geo.height()))
check("starts with empty records", win.db["clients"] == [])
check("database file path under app data", bcg.DB_PATH.startswith(WORK),
      bcg.DB_PATH)

print("\n== Client and financial year ==")
win.cl_name.setText("Example Manufacturing Private Limited")
win.cl_city.setText("Mumbai")
win.add_client()
win.active_client()["signatory_name"] = "Mr. R. Mehta"
win.active_client()["signatory_designation"] = "Director / CFO"
win.db["settings"]["partner_name"] = "CA Ankit Soni"
win.db["settings"]["letter_date"] = "2026-11-05"
check("client created", win.active_client()["name"].startswith("Example"))
win.fy_year.setText("2026-27")
win.fy_end.setDate(QDate(2027, 3, 31))
win.add_year()
year = win.active_fy()
check("financial year created", year and year["year"] == "2026-27")
check("defaults to Statutory Audit", bcg.fy_audit_type(year) == "Statutory Audit")
check("defaults to year-end basis", year["basis"] == "year")
check("as-at date is the year end",
      bcg.fy_as_at(year) == "2027-03-31", bcg.fy_as_at(year))

print("\n== Audit team ==")
for name, email in (("M. A", "a@gmail.com"), ("B", "b@gmail.com"),
                    ("C", "not-an-email")):
    win.aud_name.setText(name); win.aud_email.setText(email); win.add_auditor()
check("two valid team members kept", len(win.auditors()) == 2,
      len(win.auditors()))

print("\n== Import ==")
win.load_file(SOURCE)
check("file loaded", bool(win.source_path))
check("header row 4 found under the title rows", win.header_index == 3,
      win.header_index)
check("header detected with confidence", win.header_confidence == "high")
check("6 data rows", len(win.data_rows) == 6, len(win.data_rows))
m = win.mapping
check("party column mapped", m["partyName"]["cols"] == [1], m["partyName"]["cols"])
check("address columns combined", m["address"]["cols"] == [2, 3],
      m["address"]["cols"])
check("serial number NOT treated as address", 0 not in m["address"]["cols"])
check("amount column mapped", m["amount"]["cols"] == [4], m["amount"]["cols"])
check("currency column mapped", m["currency"]["cols"] == [5])
check("category column mapped", m["category"]["cols"] == [6])
check("email column mapped", m["email"]["cols"] == [7])
check("contact column mapped", m["contactPerson"]["cols"] == [8])

by_name = {r["party_name"]: r for r in win.records}
check("Debtors -> Trade Receivable",
      by_name["ABC Ltd"]["category"] == "Trade Receivable")
check("Creditors -> Trade Payable",
      by_name["XYZ Suppliers"]["category"] == "Trade Payable")
check("Advance Received -> Advance from Customers",
      by_name["Customer P Ltd"]["category"] == "Advance from Customers")
check("Advance Paid -> Advance to Vendors",
      by_name["Vendor Q Ltd"]["category"] == "Advance to Vendors")
check("bare Advance flagged for review",
      by_name["Ambiguous Traders"]["category"] is None)
check('"80,000" parsed', by_name["XYZ Suppliers"]["amount"] == 80000.0,
      by_name["XYZ Suppliers"]["amount"])
check("rupee symbol amount parsed",
      by_name["Vendor Q Ltd"]["amount"] == 30000.0,
      by_name["Vendor Q Ltd"]["amount"])
check("missing balance kept as none",
      by_name["No Balance Ltd"]["amount"] is None)
check("address lines combined",
      by_name["ABC Ltd"]["address_lines"] == ["12 MG Road", "Mumbai 400001"],
      by_name["ABC Ltd"]["address_lines"])
check("one row flagged", win.flagged_count() == 1, win.flagged_count())

print("\n== 1. Statutory audit / year end, in the firm's own format ==")
win.go("preview")
html = win.paper.toPlainText()
check("debtor title", "ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION" in html)
check("letterhead note", "(on the letter head of the Company)" in html)
check("letter date", "Date: 5 November 2026" in html, html[:200])
check("opening sentence",
      "Our statutory auditors, Ankit Soni and Associates, are engaged in an "
      "audit of our financial statements." in html,
      html[html.find("Our Statutory"):][:170])
check("request clause",
      "the amount payable by you to us as at 31 March 2027" in html)
check("amount with words",
      "is INR 1,25,000.00 (In Words: Rupees One Lakh Twenty Five Thousand only)"
      in html, html[html.find("According to"):][:190])
check("auditor reply block",
      "CA Ankit Soni" in html
      and "Ankit Soni and Associates (Chartered Accountants)" in html
      and "Email ID: a@gmail.com; b@gmail.com" in html)
check("debtor-only payment clause",
      "This letter is not a request for payment" in html)
check("signed by the company officer",
      "Example Manufacturing Private Limited" in html
      and "Mr. R. Mehta" in html and "Director / CFO" in html)
check("audit firm does not sign", "For Ankit Soni and Associates" not in html)
check("confirmation slip",
      "We hereby confirm that the amount payable by us to Example Manufacturing "
      "Private Limited as on 31 March 2027 is INR" in html,
      html[html.find("We hereby"):][:170])
check("slip rows", all(r in html for r in
                       ("Name and Title", "Company / Firm", "Signature")))
win.grab().save(WORK + "/shot-preview-statutory.png")

print("\n== 2. Interim audit / period end ==")
win.go("settings")
win.set_audit_type.setCurrentIndex(
    win.set_audit_type.findData("Interim Audit"))
win.set_basis.setCurrentIndex(win.set_basis.findData("period"))
win.set_period_start.setDate(QDate(2026, 4, 1))
win.set_period_end.setDate(QDate(2026, 9, 30))
year = win.active_fy()
check("basis switched to period", year["basis"] == "period")
check("as-at follows the period end", bcg.fy_as_at(year) == "2026-09-30")
check("period fields shown", win.period_box.isVisibleTo(win))
check("year-end field hidden", not win.year_end_box.isVisibleTo(win))
check("settings echo line",
      "Our auditors, Ankit Soni and Associates, are engaged in an interim "
      "audit" in win.engagement_echo.text()
      and "as on 30 September 2026" in win.engagement_echo.text(),
      win.engagement_echo.text())
win.grab().save(WORK + "/shot-settings-interim.png")

win.go("preview")
html = win.paper.toPlainText()
check("interim opening",
      "Our auditors, Ankit Soni and Associates, are engaged in an interim "
      "audit of our financial statements." in html,
      html[html.find("Our auditors"):][:170])
check("interim: period end is the as-of date",
      "as at 30 September 2026" in html)
check("interim: no stale year-end date", "31 March 2027" not in html)
win.grab().save(WORK + "/shot-preview-interim.png")

print("\n== 3. Special purpose audit / period without a start date ==")
win.go("settings")
win.set_audit_type.setCurrentIndex(
    win.set_audit_type.findData("Special Purpose Audit"))
check("designation follows the audit type",
      win.db["settings"]["firm_designation"] == "Auditor",
      win.db["settings"]["firm_designation"])
win.clear_period_start()
win.go("preview")
html = win.paper.toPlainText()
check("special purpose wording",
      "are engaged in a special purpose audit of our financial statements."
      in html, html[html.find("Our auditors"):][:180])

print("\n== 4. Other (free text) ==")
win.go("settings")
win.set_audit_type.setCurrentIndex(win.set_audit_type.findData("Other"))
check("free-text box appears", win.audit_other_box.isVisibleTo(win))
check("blank description blocks generation",
      not win.validation()["ready"])
win.set_audit_other.setText("Agreed-upon procedures engagement")
check("description clears the gate", win.validation()["ready"],
      [i["title"] for i in win.validation()["hard"]])
win.go("preview")
check("free text folded into the engagement phrase",
      "are engaged in an agreed-upon procedures engagement of our financial "
      "statements." in win.paper.toPlainText(),
      win.paper.toPlainText()[:400])

print("\n== 5. Fix the flagged row, then generate ==")
win.go("settings")
win.set_audit_type.setCurrentIndex(
    win.set_audit_type.findData("Interim Audit"))
win.set_period_start.setDate(QDate(2026, 4, 1))
win.go("review")
rec = by_name["Ambiguous Traders"]
rec["category"] = "Advance to Vendors"
rec["category_edited"] = True
win.compute_issues(rec)
win.refresh_all()
check("no rows flagged now", win.flagged_count() == 0)

win.db["settings"]["output_folder"] = OUTPUT
win.go("generate")
check("ready to generate", win.validation()["ready"],
      [i["title"] for i in win.validation()["hard"]])
check("generate button enabled", win.btn_generate.isEnabled())

confs = [win.to_confirmation(r) for r in win.validation()["generable"]]
folder = win.run_output_folder()
os.makedirs(folder, exist_ok=True)
worker = bcg.GenerateWorker(confs, folder)
produced = []
worker.produced.connect(produced.append)
worker.run()
win.generated = produced
win.save_run(folder)
win.refresh_generate()
check("6 documents produced",
      len([g for g in produced if g["status"] == "ok"]) == 6,
      len(produced))
files = sorted(f for f in os.listdir(folder) if f.endswith(".docx"))
print("        files -> " + " | ".join(files))
expected = sorted(["ABC Ltd - Trade Receivable.docx",
                   "XYZ Suppliers - Trade Payable.docx",
                   "Customer P Ltd - Advance from Customers.docx",
                   "Vendor Q Ltd - Advance to Vendors.docx",
                   "Ambiguous Traders - Advance to Vendors.docx",
                   "No Balance Ltd - Trade Receivable.docx"])
check("file names as expected", files == expected)
check("sub-folder named for client and year",
      os.path.basename(folder).startswith("Example Manufacturing Private "
                                          "Limited - Balance Confirmations"),
      os.path.basename(folder))
win.grab().save(WORK + "/shot-generate.png")

print("\n== 6. Email queue ==")
win.go("email")
check("queue built from the documents", len(win.queue) == 6, len(win.queue))
states = {q["party"]: q["status"] for q in win.queue.values()}
check("row without an address flagged",
      states["Ambiguous Traders"] == "no email", states)
check("others pending", states["ABC Ltd"] == "pending")
check("send blocked until the mailbox is set up",
      not win.btn_send.isEnabled())
ready, missing = win.mail_ready()
check("missing mail settings reported (host comes from the preset)",
      not ready and set(missing) == {"the username", "the app password"},
      missing)
win.mail_host.setText("smtp.zoho.in"); win.mail_username.setText("me@firm.example")
win.mail_password_edit.setText("app-password"); win.save_mail_settings()
win.refresh_email()
check("send enabled once the mailbox is complete", win.btn_send.isEnabled())
body = win.mail_body.toPlainText()
check("template keeps its placeholders",
      "{audittype_article}" in body and "{period}" in body)
draft = bcg.build_email_message(
    confs[0], produced[0]["filename"], produced[0]["data"],
    win.mail_options())
check("draft addressed to the party", draft["To"] == "ap@abc.example")
check("audit team in Cc", "a@gmail.com" in (draft["Cc"] or ""))
check("reply-to set", "b@gmail.com" in (draft["Reply-To"] or ""))
mail_text = draft.get_body(preferencelist=("plain",)).get_content()
check("covering mail describes the engagement",
      "carrying out an interim audit of its financial statements for the "
      "period from 1 April 2026 to 30 September 2026" in mail_text,
      mail_text.split("\n")[2])
check("covering mail says the letter is the client's",
      "issued by Example Manufacturing Private Limited" in mail_text)
attachments = list(draft.iter_attachments())
check("word file attached", len(attachments) == 1
      and attachments[0].get_filename().endswith(".docx"))
check("attachment is a real zip",
      attachments[0].get_payload(decode=True)[:2] == b"PK")
win.grab().save(WORK + "/shot-email.png")

print("\n== 7. Saved runs and persistence ==")
win.go("runs")
check("run recorded", win.runs_table.rowCount() == 1)
texts = [win.runs_table.item(0, c).text() for c in range(7)]
check("run shows the audit type", "Interim Audit" in texts, texts)
check("run shows the period",
      any("Period from 1 April 2026 to 30 September 2026" in t for t in texts),
      texts)
win.grab().save(WORK + "/shot-runs.png")
win.go("dashboard")
win.grab().save(WORK + "/shot-dashboard.png")
win.go("clients")
win.grab().save(WORK + "/shot-clients.png")
win.go("import")
win.grab().save(WORK + "/shot-import.png")
win.go("review")
win.grab().save(WORK + "/shot-review.png")

win.persist()
win2 = bcg.MainWindow()
y2 = win2.active_fy()
check("engagement restored after restart",
      bcg.fy_audit_type(y2) == "Interim Audit" and y2["basis"] == "period"
      and bcg.fy_as_at(y2) == "2026-09-30",
      (bcg.fy_audit_type(y2), y2.get("basis"), bcg.fy_as_at(y2)))
check("clients restored", len(win2.db["clients"]) == 1)
check("team restored", len(win2.auditors()) == 2)
check("saved run restored", len(win2.db["runs"]) == 1)

print("\n== 8. Legacy records upgrade ==")
old = {"clients": [{"id": "x1", "name": "Old Client",
                    "financialYears": [{"id": "y1", "year": "2024-25",
                                        "yearEnd": "2025-03-31"}]}],
       "runs": [],
       "settings": {"mail": {"body": "We are conducting the statutory audit "
                                     "of {client} for the year ended {date}."}}}
upgraded = bcg.normalise_db(old)
uy = upgraded["clients"][0]["financial_years"][0]
check("old year end carried over", uy["year_end"] == "2025-03-31")
check("audit type defaulted", uy["audit_type"] == "Statutory Audit")
check("basis defaulted", uy["basis"] == "year")
check("old email sentence upgraded",
      "{audittype}" in upgraded["settings"]["mail"]["body"])

print("\n" + "-" * 55)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("Failures: " + "; ".join(FAIL))
sys.exit(1 if FAIL else 0)
