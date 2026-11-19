"""Drives the running app: generate letters, import replies, read the reports."""
import importlib.util, json, os, shutil, sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
WORK = "/home/claude/pytest/rwork"
shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK, exist_ok=True)
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "appdata")

spec = importlib.util.spec_from_file_location(
    "bcg", "/home/claude/balance_confirmation_generator.py")
bcg = importlib.util.module_from_spec(spec)
sys.modules["bcg"] = bcg
spec.loader.exec_module(bcg)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QDate, QEvent

PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name +
          ("" if cond or not detail else "  ->  " + str(detail)[:200]))

# ------------------------------------------------------------- a workbook
import openpyxl
book = openpyxl.Workbook()
sheet = book.active
sheet.title = "Balances"
for row in [["Example Manufacturing Private Limited"],
            ["Party-wise balances as at 31.03.2026"], [],
            ["Party Name", "Address", "Closing Bal.", "CCY", "Nature",
             "E-mail ID"],
            ["ABC Ltd", "Mumbai", 125000, "INR", "Debtors", "ap@abc.example"],
            ["XYZ Suppliers", "Delhi", 80000, "INR", "Creditors",
             "ar@xyz.example"],
            ["Customer P Ltd", "Pune", 50000, "INR", "Advance Received",
             "fin@customerp.example"],
            ["Vendor Q Ltd", "Chennai", 30000, "INR", "Advance Paid",
             "acc@vendorq.example"]]:
    sheet.append(row)
SOURCE = os.path.join(WORK, "balances.xlsx")
book.save(SOURCE)

QMessageBox.exec = lambda self: QMessageBox.StandardButton.Ok
app = QApplication([])
app.setStyle("Fusion")
app.setPalette(bcg.qt_palette())
app.setStyleSheet(bcg.style_sheet())
win = bcg.MainWindow()
win.resize(1440, 900)
win.show()
def pump(n=4):
    for _ in range(n):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
pump()

print("\n== Set-up ==")
win.cl_name.setText("Example Manufacturing Private Limited")
win.add_client()
win.active_client()["signatory_name"] = "Mr. R. Mehta"
win.active_client()["signatory_designation"] = "Director / CFO"
win.db["settings"]["partner_name"] = "CA Ankit Soni"
win.fy_year.setText("2025-26")
win.fy_end.setDate(QDate(2026, 3, 31))
win.add_year()
for name, email in (("M. A", "a@gmail.com"), ("B", "b@gmail.com")):
    win.aud_name.setText(name)
    win.aud_email.setText(email)
    win.add_auditor()
win.load_file(SOURCE)
pump()
check("4 parties imported", len(win.records) == 4, len(win.records))
check("navigation shows the new page",
      any(key == "recon" for key in win.nav_keys.values()))

print("\n== Generate, then mark as sent ==")
out = os.path.join(WORK, "out")
os.makedirs(out, exist_ok=True)
win.db["settings"]["output_folder"] = out
confs = [win.to_confirmation(r) for r in win.validation()["generable"]]
check("every letter carries a reference",
      all(bcg.REFERENCE_RE.search(c["reference"]) for c in confs),
      [c["reference"] for c in confs])
check("references are unique",
      len({c["reference"] for c in confs}) == len(confs))
folder = win.run_output_folder()
os.makedirs(folder, exist_ok=True)
worker = bcg.GenerateWorker(confs, folder)
produced = []
worker.produced.connect(produced.append)
worker.run()
win.generated = produced
win.save_run(folder)
check("4 documents produced", len(produced) == 4)

run = win.db["runs"][0]
by_party = {d["party_name"]: d for d in run["documents"]}
check("run stores the reference",
      all(d.get("reference") for d in run["documents"]),
      [d.get("reference") for d in run["documents"]])
# pretend the three letters went out and one bounced
for party, thread in (("ABC Ltd", "t-1"), ("XYZ Suppliers", "t-2"),
                      ("Customer P Ltd", "t-3"), ("Vendor Q Ltd", "t-4")):
    document = by_party[party]
    document["email_status"] = "sent"
    document["thread_id"] = thread
    document["message_id"] = "<%s@firm.example>" % thread
    document["sent_at"] = "2026-09-20"
win.persist()

print("\n== Replies arrive ==")
CLIENT = "Example Manufacturing Private Limited"
replies = [
    {"id": "m1", "received_at": "2026-09-28", "thread_id": "t-1",
     "from_email": "ap@abc.example", "from_name": "ABC Accounts",
     "subject": "Re: Balance confirmation request",
     "body": "We agree with the balance. Signed copy attached.",
     "attachments": [{"name": "abc-signed.pdf", "text":
      "We hereby confirm that amount payable by us to " + CLIENT +
      " as on 31 March 2026 is INR 1,25,000.00 Authorised Signatory"}]},
    {"id": "m2", "received_at": "2026-09-29",
     "from_email": "group.finance@xyz.example", "from_name": "XYZ Finance",
     "subject": "Balance confirmation [%s]" % by_party["XYZ Suppliers"]["reference"],
     "body": "Our books are not in agreement.",
     "attachments": [{"name": "xyz.pdf", "text":
      "We hereby confirm that amount receivable by us from " + CLIENT +
      " as on 31 March 2026 is INR 78,500.00"}]},
    {"id": "m3", "received_at": "2026-09-21", "thread_id": "t-4",
     "from_email": "mailer-daemon@googlemail.com",
     "from_name": "Mail Delivery Subsystem",
     "subject": "Delivery Status Notification (Failure)",
     "body": "Address not found: acc@vendorq.example", "attachments": []},
    {"id": "m4", "received_at": "2026-09-30", "from_email": "x@unknown.example",
     "from_name": "Unknown", "subject": "balance confirmation",
     "body": "We hereby confirm that amount payable by us to you as on "
             "31 March 2026 is INR 99,000.00", "attachments": []},
]
path = os.path.join(WORK, "replies.json")
with open(path, "w", encoding="utf-8") as handle:
    json.dump({"replies": replies}, handle)

bcg.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (path, ""))
win.go("recon")
pump()
win.import_replies()
pump()
check("replies stored once", len(win.db["replies"]) == 4,
      len(win.db["replies"]))
win.import_replies()          # the same file again
pump()
check("re-importing the same file adds nothing",
      len(win.db["replies"]) == 4, len(win.db["replies"]))

print("\n== The position ==")
summary = win.recon_summary
print("   " + ", ".join("%s=%s" % (k, round(v, 2) if isinstance(v, float)
                                   else v) for k, v in summary.items()))
rows = {r["party_name"]: r for r in win.recon_rows}
check("ABC agreed", rows["ABC Ltd"]["status"] == bcg.STATUS_AGREED)
check("ABC matched by thread",
      rows["ABC Ltd"]["match_method"] == bcg.MATCH_THREAD)
check("XYZ matched by its reference code",
      rows["XYZ Suppliers"]["match_method"] == bcg.MATCH_REFERENCE)
check("XYZ variance -1,500", rows["XYZ Suppliers"]["variance"] == -1500.0)
check("Vendor Q returned",
      rows["Vendor Q Ltd"]["status"] == bcg.STATUS_RETURNED)
check("Customer P pending",
      rows["Customer P Ltd"]["status"] == bcg.STATUS_PENDING)
check("unknown sender went to the exception queue",
      len(win.recon_exceptions) == 1, win.recon_exceptions)
check("the unmatched figure is not in the totals",
      summary["confirmed_value"] == 205000.0, summary["confirmed_value"])
check("coverage 205000/285000",
      abs(summary["coverage_pct"] - 205000 / 285000 * 100) < 0.01,
      summary["coverage_pct"])

print("\n== Every report renders ==")
for index in range(win.report_combo.count()):
    win.report_combo.setCurrentIndex(index)
    pump(2)
    title = win.report_combo.currentText()
    rows_shown = win.report_table.rowCount()
    columns = win.report_table.columnCount()
    print("   %-32s %d rows x %d columns" % (title, rows_shown, columns))
    check("%s renders" % title, columns > 1)
expected = {"Confirmation register": 4, "Confirmations received": 2,
            "Pending confirmations": 2, "Requested vs confirmed": 4,
            "Consolidated variance report": 4, "Exception queue": 1,
            "Audit status": 0}
for index in range(win.report_combo.count()):
    win.report_combo.setCurrentIndex(index)
    pump(2)
    title = win.report_combo.currentText()
    check("%s has %d rows" % (title, expected[title]),
          win.report_table.rowCount() == expected[title],
          win.report_table.rowCount())

print("\n== Exports ==")
xlsx = os.path.join(WORK, "reports.xlsx")
pdf = os.path.join(WORK, "reports.pdf")
bcg.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (xlsx, ""))
win.export_reports_excel()
check("workbook written", os.path.exists(xlsx) and os.path.getsize(xlsx) > 6000,
      os.path.getsize(xlsx) if os.path.exists(xlsx) else "missing")
bcg.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (pdf, ""))
win.export_reports_pdf()
check("pdf written", os.path.exists(pdf) and os.path.getsize(pdf) > 5000,
      os.path.getsize(pdf) if os.path.exists(pdf) else "missing")

workbook = openpyxl.load_workbook(xlsx)
check("one sheet per report plus a cover",
      len(workbook.sheetnames) == len(bcg.REPORT_TITLES) + 1,
      workbook.sheetnames)
comparison = workbook["Requested vs confirmed"]
check("headings frozen", comparison.freeze_panes == "A5",
      comparison.freeze_panes)
values = [r for r in comparison.iter_rows(min_row=5, values_only=True)
          if r[0]]
check("workbook holds every party", len(values) == 5, values)   # 4 + total
total_row = values[-1]
check("workbook total ties to the screen",
      total_row[3] == 285000.0, total_row)

print("\n== Both themes, with data on screen ==")
for mode in ("dark", "light"):
    win.set_mode(mode)
    pump(4)
    win.go("recon")
    win.show_report(bcg.REPORT_COMPARISON)
    pump(3)
    win.grab().save(os.path.join(WORK, "recon-%s.png" % mode))
    win.go("dashboard")
    pump(3)
    win.grab().save(os.path.join(WORK, "dashboard-%s.png" % mode))
    check("%s mode renders the reports page" % mode,
          win.report_table.rowCount() > 0)

print("\n" + "-" * 54)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("Failures: " + "; ".join(FAIL))
sys.exit(1 if FAIL else 0)
