"""Version 3.5: review a reply, accept it, and follow up the difference.

The case reported.  Requests went to ABC (79,60,098.48) and XYZ
(35,15,723.34).  Four replies came back, every one from the address on
record for ABC and every one as a reply to ABC's request:

    79,60,098.48   25,15,723.89   1,80,000   23,11,786

Nothing in any of them names XYZ, so the application cannot give one to
XYZ by itself.  The reviewer must be able to do it: open the reply, choose
XYZ, accept the value - and have every report follow.

Run:  python review_test.py      (needs the assembled application)
"""
import importlib.util, os, sys, tempfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get("BCG_APP") or os.path.join(
    HERE, "..", "balance_confirmation_generator.py")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# scratch files go to the system's temporary folder, never into the project
WORK = tempfile.mkdtemp(prefix="bcg-review-")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "appdata")
os.environ["APPDATA"] = os.path.join(WORK, "appdata")

spec = importlib.util.spec_from_file_location("bcg", APP)
bcg = importlib.util.module_from_spec(spec)
sys.modules["bcg"] = bcg
spec.loader.exec_module(bcg)

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name +
          ("" if cond or not detail else "  ->  " + str(detail)[:300]))


ABC_MAIL = "accounts@abc-test.example"
XYZ_MAIL = "finance@xyz-test.example"
ABC_BOOKS, XYZ_BOOKS = 7960098.48, 3515723.34


def as_the_bridge_sends(year, month, day):
    """Midnight local time on that day, as Google returns a date cell."""
    local_midnight = datetime(year, month, day).astimezone()
    return local_midnight.astimezone(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z")


QUOTED = ("\n\nOn Tue, Nov 10, 2026 at 10:04 PM Ankit & Associates "
          "<audit@firm.example> wrote:\n> Dear Sir/Madam,\n> Please find "
          "attached a balance confirmation request, being INR 79,60,098.48.")


def reply(number, day, words):
    return {"id": "m-%d" % number,
            "received_at": as_the_bridge_sends(2026, 11, day),
            "from_email": ABC_MAIL, "from_name": "Ankit Soni",
            "subject": "Re: Balance confirmation request as at 31 March "
                       "2027 — Unique Chains",
            "in_reply_to": "<req-abc@firm.example>",
            "message_link": "https://mail.example/#inbox/m-%d" % number,
            "body": words + QUOTED}


def the_four():
    return [
        reply(1, 10, "Helo,\n\nWe confirm the balance and it is correct and "
                     "matches Rs. 79,60,098.48."),
        reply(2, 10, "Our books show Rs. 25,15,723.89 as payable."),
        reply(3, 13, "Hello,We confirm the balance payable as per our books "
                     "is 180000 only"),
        reply(4, 13, "Hello,\n\nBalance as per our books payable is "
                     "23,11,786/-"),
    ]


# ======================================================================
print("\n== 1. Received dates are the reviewer's own calendar dates ==")
stamp = as_the_bridge_sends(2026, 11, 10)
check("midnight on 10 November, as Google returns it, reads 10 November",
      bcg.local_stamp(stamp) == "2026-11-10", (stamp, bcg.local_stamp(stamp)))
check("a plain date is left alone",
      bcg.local_stamp("2026-11-10") == "2026-11-10")
check("a date and time without a zone is left alone",
      bcg.local_stamp("2026-11-10 22:08") == "2026-11-10 22:08")
check("an empty value stays empty", bcg.local_stamp("") == "")

# ======================================================================
print("\n== 2. A figure the reviewer accepted is used exactly ==")
accepted = dict(the_four()[3], accepted_amount=2311786.0,
                decided_by="CA Reviewer")
found = bcg.extract_confirmation(accepted, XYZ_BOOKS)
check("the accepted value is the confirmed value",
      found["amount"] == 2311786.0 and found["confidence"] == 1.0, found)
check("the source names who accepted it",
      found["source"] == "accepted by CA Reviewer", found["source"])
check("the two statuses carry the wording asked for",
      bcg.STATUS_AGREED == "Matched" and bcg.STATUS_VARIANCE == "Mismatch"
      and bcg.STATUS_REVIEW == "Needs Review")

# ======================================================================
print("\n== 3. Through the application window ==")
from PyQt6.QtWidgets import (QApplication, QMessageBox, QComboBox, QLineEdit,
                             QPushButton, QLabel, QPlainTextEdit)
from PyQt6.QtCore import QDate, QEvent, QTimer
from PyQt6.QtGui import QColor
import openpyxl

QMessageBox.exec = lambda self: QMessageBox.StandardButton.Ok
app = QApplication([])
app.setStyle("Fusion")
app.setPalette(bcg.qt_palette())
app.setStyleSheet(bcg.style_sheet())
win = bcg.MainWindow()
win.resize(1500, 950)
win.show()
win.ask = lambda *a, **k: True


def pump(n=6):
    for _ in range(n):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def drive(action):
    """Act on the next modal window once it is open."""
    def look():
        window = app.activeModalWidget()
        if window is None:
            QTimer.singleShot(40, look)
            return
        if SHOTS:                      # keep a picture of each window
            app.processEvents()
            SHOT_COUNT.append(1)
            window.grab().save(os.path.join(
                SHOTS, "window-%d.png" % len(SHOT_COUNT)))
        action(window)
    QTimer.singleShot(60, look)


SHOTS = os.environ.get("BCG_SHOTS", "")
SHOT_COUNT = []


listing = os.path.join(WORK, "listing.xlsx")
book = openpyxl.Workbook()
sheet = book.active
sheet.append(["Name", "Address line 1", "Pincode", "State", "Country",
              "Currency", "Closing balance", "Category", "email id"])
sheet.append(["ABC Pvt Ltd", "Unit 12, 10th Road", 400057, "Maharashtra",
              "India", "INR", ABC_BOOKS, "Trade receivable", ABC_MAIL])
sheet.append(["XYZ Pvt Ltd", "Plot 4, Okhla", 110020, "Delhi", "India",
              "INR", XYZ_BOOKS, "Trade receivable", XYZ_MAIL])
book.save(listing)

pump()
win.cl_name.setText("Unique Chains & Jewels Pvt Ltd")
win.add_client()
win.active_client()["signatory_name"] = "Mr. R. Mehta"
win.db["settings"]["firm_name"] = "Ankit & Associates"
win.fy_year.setText("2026-27")
win.fy_end.setDate(QDate(2027, 3, 31))
win.add_year()
win.aud_name.setText("CA Reviewer")
win.aud_email.setText("audit@firm.example")
win.add_auditor()
win.load_file(listing)
pump()
out = os.path.join(WORK, "out")
os.makedirs(out)
win.db["settings"]["output_folder"] = out
confs = [win.to_confirmation(r) for r in win.validation()["generable"]]
folder = win.run_output_folder()
os.makedirs(folder, exist_ok=True)
worker = bcg.GenerateWorker(confs, folder)
produced = []
worker.produced.connect(produced.append)
worker.run()
win.generated = produced
win.save_run(folder)
for document in win.db["runs"][0]["documents"]:
    document.update(email_status="sent", sent_at="2026-11-10",
                    message_id="<req-%s@firm.example>"
                    % document["party_name"][:3].lower())
win.persist()
keys = {d["party_name"]: d["id"] for d in win.sent_documents()}
check("two requests on record", len(keys) == 2, keys)

win.go("recon")
win.merge_replies(the_four())
pump()


def rows():
    return {r["party_name"]: r for r in win.recon_rows}


def report(key):
    return bcg.build_report(key, win.recon_rows, win.recon_exceptions,
                            win.report_context())


def table_text(row, column):
    item = win.report_table.item(row, column)
    return item.text() if item else ""


def column_of(heading):
    return [win.report_table.horizontalHeaderItem(i).text()
            for i in range(win.report_table.columnCount())].index(heading)


print("\n-- 3a. As the screenshots show it")
check("ABC is Needs Review, XYZ is Pending",
      rows()["ABC Pvt Ltd"]["status"] == bcg.STATUS_REVIEW and
      rows()["XYZ Pvt Ltd"]["status"] == bcg.STATUS_PENDING,
      [(k, v["status"]) for k, v in rows().items()])
check("all four replies are in the Exception Queue",
      sorted(e["reply_id"] for e in win.recon_exceptions)
      == ["m-1", "m-2", "m-3", "m-4"], win.recon_exceptions)
check("received dates read 10 and 13 November, not the day before",
      sorted({e["received_at"] for e in win.recon_exceptions})
      == ["2026-11-10", "2026-11-13"],
      sorted({e["received_at"] for e in win.recon_exceptions}))
check("the page says replies are received but not yet counted",
      win.btn_queue.isVisible() and
      win.btn_queue.text().startswith("4 replies received but not yet "
                                      "counted"), win.btn_queue.text())
by_id = {e["reply_id"]: e for e in win.recon_exceptions}
check("the reply giving ABC's own balance is suggested for ABC",
      by_id["m-1"]["suggested_to"] == keys["ABC Pvt Ltd"] and
      "equals the balance requested from ABC Pvt Ltd"
      in by_id["m-1"]["suggestion"], by_id["m-1"])
check("no party is suggested for 23,11,786 - nothing identifies one",
      by_id["m-4"]["suggested_to"] == "" and
      by_id["m-4"]["candidates"] == "ABC Pvt Ltd", by_id["m-4"])
check("nobody was given a figure by guesswork",
      all(r["confirmed_amount"] is None for r in rows().values()))

win.btn_queue.click()
pump()
if SHOTS:
    win.grab().save(os.path.join(SHOTS, "queue.png"))
check("the notice opens the Exception Queue",
      win.report_combo.currentData() == bcg.REPORT_EXCEPTIONS)
check("each row has a Review link in the first column",
      win.report_table.horizontalHeaderItem(0).text() == "Action" and
      all(table_text(i, 0) == "Review" for i in range(4)),
      [table_text(i, 0) for i in range(4)])
check("the link is drawn as a link",
      win.report_table.item(0, 0).font().underline())

print("\n-- 3b. The real review window: it will not accept half a decision")
seen = {}


def cancel_after_trying(window):
    party = window.findChild(QComboBox, "review_party")
    amount = window.findChild(QLineEdit, "review_amount")
    problem = window.findChild(QLabel, "review_problem")
    accept = window.findChild(QPushButton, "review_accept")
    seen["offered"] = [party.itemText(i) for i in range(party.count())]
    seen["preselected"] = party.currentData()
    seen["amount"] = amount.text()
    seen["words"] = window.findChild(QPlainTextEdit).toPlainText()
    accept.click()
    seen["no_party"] = problem.text()
    party.setCurrentIndex(party.findData(keys["XYZ Pvt Ltd"]))
    amount.setText("not a number")
    accept.click()
    seen["bad_amount"] = problem.text()
    amount.setText("23,11,786")
    window.findChild(QComboBox, "review_by").setEditText("")
    accept.click()
    seen["no_name"] = problem.text()
    seen["still_open"] = window.isVisible()
    window.reject()


index = [e["reply_id"] for e in win.recon_exceptions].index("m-4")
drive(cancel_after_trying)
win.on_report_cell(index, 0)
pump()
check("clicking Review opens the window with the party's own words",
      "23,11,786/-" in seen.get("words", "") and
      "balance confirmation request" not in seen.get("words", ""),
      seen.get("words"))
check("both requests are offered, with reference and books balance",
      any("XYZ Pvt Ltd" in t and "35,15,723.34" in t
          for t in seen["offered"]) and
      any("ABC Pvt Ltd" in t and "BCG-" in t for t in seen["offered"]),
      seen["offered"])
check("no party is pre-selected when none can be suggested",
      seen["preselected"] is None, seen["preselected"])
check("the amount read is filled in for the reviewer",
      seen["amount"] == "2311786.00", seen["amount"])
check("it refuses with no party chosen", "Choose the party" in seen["no_party"],
      seen["no_party"])
check("it refuses an amount that is not a number",
      "Enter the confirmed value" in seen["bad_amount"], seen["bad_amount"])
check("it refuses without the reviewer's name",
      "name of the person" in seen["no_name"], seen["no_name"])
check("cancelling changes nothing",
      seen["still_open"] and rows()["XYZ Pvt Ltd"]["status"]
      == bcg.STATUS_PENDING)

print("\n-- 3c. Accept 23,11,786 for XYZ in the real window")


def accept_for_xyz(window):
    party = window.findChild(QComboBox, "review_party")
    party.setCurrentIndex(party.findData(keys["XYZ Pvt Ltd"]))
    window.findChild(QLineEdit, "review_amount").setText("23,11,786")
    window.findChild(QComboBox, "review_by").setEditText("CA Reviewer")
    window.findChild(QLineEdit, "review_note").setText(
        "Confirmed with XYZ by telephone")
    window.findChild(QPushButton, "review_accept").click()


index = [e["reply_id"] for e in win.recon_exceptions].index("m-4")
drive(accept_for_xyz)
win.on_report_cell(index, 0)
pump()
xyz = rows()["XYZ Pvt Ltd"]
expected_variance = round(2311786.0 - XYZ_BOOKS, 2)
check("XYZ is no longer Pending: Mismatch",
      xyz["status"] == bcg.STATUS_VARIANCE, xyz["status"])
check("confirmed balance 23,11,786.00", xyz["confirmed_amount"] == 2311786.0,
      xyz["confirmed_amount"])
check("variance %.2f (confirmed less books)" % expected_variance,
      round(xyz["variance"], 2) == expected_variance == -1203937.34,
      xyz["variance"])
check("the row records who accepted it, when and why",
      xyz["decided_by"] == "CA Reviewer" and xyz["decided_at"] and
      xyz["decision_note"] == "Confirmed with XYZ by telephone" and
      xyz["match_basis"].startswith("Accepted by CA Reviewer on "),
      (xyz["decided_by"], xyz["match_basis"]))
held = [r for r in win.db["replies"] if r["id"] == "m-4"][0]
check("the original e-mail can still be identified from the reply",
      held["id"] == "m-4" and held["from_email"] == ABC_MAIL and
      held["message_link"].endswith("m-4") and held["subject"] and
      held["received_at"] == "2026-11-13" and "23,11,786/-" in held["body"],
      {k: held.get(k) for k in ("id", "from_email", "received_at")})
check("the decision is kept on the reply",
      held["assigned_to"] == keys["XYZ Pvt Ltd"] and
      held["accepted_amount"] == 2311786.0 and
      held["decided_by"] == "CA Reviewer" and held["decided_at"])

received = report(bcg.REPORT_RECEIVED)
check("Confirmations received now lists XYZ",
      [(r["party_name"], r["confirmed_amount"]) for r in received["rows"]]
      == [("XYZ Pvt Ltd", 2311786.0)], received["rows"])
comparison = {r["party_name"]: r
              for r in report(bcg.REPORT_COMPARISON)["rows"]}
heads = [h for h, _k, _t in report(bcg.REPORT_COMPARISON)["columns"]]
check("Requested vs confirmed shows who confirmed and when",
      "Confirmed by (reply from)" in heads and "Reply received" in heads
      and comparison["XYZ Pvt Ltd"]["reply_from"] == ABC_MAIL and
      comparison["XYZ Pvt Ltd"]["confirmed_amount"] == 2311786.0 and
      round(comparison["XYZ Pvt Ltd"]["variance"], 2) == expected_variance,
      heads)
variance = report(bcg.REPORT_VARIANCE)
line = variance["rows"][0]
check("Consolidated variance: 1 mismatch, amount confirmed 23,11,786",
      line["variance"] == 1 and line["amount_confirmed"] == 2311786.0 and
      round(line["net_variance"], 2) == expected_variance and
      "Matched" in [h for h, _k, _t in variance["columns"]],
      line)
check("...and it ties: amount confirmed less books value counted = variance",
      round(line["amount_confirmed"] - line["confirmed_value"], 2)
      == expected_variance and line["confirmed_value"] == XYZ_BOOKS,
      (line["amount_confirmed"], line["confirmed_value"]))
check("ABC is still Needs Review, with the other three replies",
      rows()["ABC Pvt Ltd"]["status"] == bcg.STATUS_REVIEW and
      sorted(e["reply_id"] for e in win.recon_exceptions)
      == ["m-1", "m-2", "m-3"])

print("\n-- 3d. Accept ABC's own figure; the rest stay to be decided")


def accept_suggestion(window):
    seen["suggested"] = window.findChild(QComboBox,
                                         "review_party").currentData()
    window.findChild(QComboBox, "review_by").setEditText("CA Reviewer")
    window.findChild(QPushButton, "review_accept").click()


index = [e["reply_id"] for e in win.recon_exceptions].index("m-1")
drive(accept_suggestion)
win.on_report_cell(index, 0)
pump()
check("the suggested party (ABC) was pre-selected in the window",
      seen["suggested"] == keys["ABC Pvt Ltd"], seen["suggested"])
abc = rows()["ABC Pvt Ltd"]
check("ABC is Matched at 79,60,098.48, variance nil",
      abc["status"] == bcg.STATUS_AGREED == "Matched" and
      abc["confirmed_amount"] == ABC_BOOKS and abs(abc["variance"]) < 0.005,
      (abc["status"], abc["confirmed_amount"], abc["variance"]))
left = {e["reply_id"]: e for e in win.recon_exceptions}
check("the two undecided replies stay in the queue, not dropped",
      sorted(left) == ["m-2", "m-3"] and
      all(e["kind"] == bcg.EXCEPTION_LEFTOVER for e in left.values()) and
      "accepted from another reply" in left["m-2"]["reason"], left)
check("they no longer hold ABC back",
      rows()["ABC Pvt Ltd"]["status"] == bcg.STATUS_AGREED)

win.show_report(bcg.REPORT_COMPARISON)
pump()
status_column = column_of("Status")
party_column = column_of("Party")
shown = {table_text(i, party_column): win.report_table.item(i, status_column)
         for i in range(win.report_table.rowCount())}
check("on screen Matched is green",
      shown["ABC Pvt Ltd"].text() == "Matched" and
      shown["ABC Pvt Ltd"].foreground().color().name()
      == QColor(bcg.T["ok"]).name(),
      shown["ABC Pvt Ltd"].foreground().color().name())
check("on screen Mismatch is in the alert colour",
      shown["XYZ Pvt Ltd"].text() == "Mismatch" and
      shown["XYZ Pvt Ltd"].foreground().color().name()
      == QColor(bcg.T["err"]).name())

print("\n-- 3e. Set the last two aside")
for reply_id in ("m-2", "m-3"):
    win.assign_reply(reply_id, bcg.SET_ASIDE, by="CA Reviewer",
                     note="Superseded test replies")
pump()
check("the queue is empty and the notice is gone",
      win.recon_exceptions == [] and not win.btn_queue.isVisible())
check("the replies set aside are still on record, with the reason",
      len(win.recon_set_aside) == 2 and
      all(r["decided_by"] == "CA Reviewer" and
          r["decision_note"] == "Superseded test replies"
          for r in win.recon_set_aside))

print("\n-- 3f. Every report tells the same story")
status = {r["party_name"]: r["status"] for r in win.recon_rows}
for key in (bcg.REPORT_REGISTER, bcg.REPORT_COMPARISON, bcg.REPORT_RECEIVED):
    got = {r["party_name"]: r["status"] for r in report(key)["rows"]}
    check("%s agrees with the position" % key, got == status, got)
line = report(bcg.REPORT_VARIANCE)["rows"][0]
total_confirmed = round(ABC_BOOKS + 2311786.0, 2)
check("consolidated: 1 Matched, 1 Mismatch, nothing pending or in review",
      (line["agreed"], line["variance"], line["pending"], line["review"])
      == (1, 1, 0, 0), line)
check("consolidated amount confirmed by parties = %.2f" % total_confirmed,
      round(line["amount_confirmed"], 2) == total_confirmed,
      line["amount_confirmed"])
check("coverage is 100%: both balances answered",
      round(line["coverage_pct"], 2) == 100.0 and
      round(line["confirmed_value"], 2) == round(ABC_BOOKS + XYZ_BOOKS, 2),
      (line["coverage_pct"], line["confirmed_value"]))
check("consolidated net difference = XYZ's variance",
      round(line["net_variance"], 2) == expected_variance,
      line["net_variance"])

# ======================================================================
print("\n== 4. Audit-status records ==")
check("the Mismatch row offers 'Create record'; the Matched row offers none",
      rows()["XYZ Pvt Ltd"]["audit_state_link"] == "Create record" and
      rows()["XYZ Pvt Ltd"]["audit_state"] == "Not yet recorded" and
      rows()["ABC Pvt Ltd"]["audit_state_link"] == "",
      (rows()["XYZ Pvt Ltd"]["audit_state_link"],
       rows()["ABC Pvt Ltd"]["audit_state_link"]))
win.show_report(bcg.REPORT_COMPARISON)
pump()
audit_column = column_of("Audit status")
xyz_row = [i for i in range(win.report_table.rowCount())
           if table_text(i, party_column) == "XYZ Pvt Ltd"][0]
abc_row = [i for i in range(win.report_table.rowCount())
           if table_text(i, party_column) == "ABC Pvt Ltd"][0]
check("the link is on the Mismatch row only",
      table_text(xyz_row, audit_column) == "Create record" and
      table_text(abc_row, audit_column) == "")


def fill_audit(window):
    seen["audit_title"] = window.windowTitle()
    seen["audit_facts"] = window.findChildren(QLabel)[0].text()
    save = window.findChild(QPushButton, "audit_save")
    window.findChild(QComboBox, "audit_owner").setEditText("")
    save.click()
    seen["audit_problem"] = window.findChild(QLabel, "audit_problem").text()
    state = window.findChild(QComboBox, "audit_state")
    state.setCurrentIndex(state.findText("Under follow-up"))
    nature = window.findChild(QComboBox, "audit_nature")
    nature.setCurrentIndex(nature.findText("Disputed item"))
    window.findChild(QComboBox, "audit_owner").setEditText("CA Reviewer")
    window.findChild(QPlainTextEdit, "audit_notes").setPlainText(
        "Statement of account requested from XYZ.")
    save.click()


drive(fill_audit)
win.on_report_cell(xyz_row, audit_column)
pump()
check("the window is for XYZ and shows request, reply and figures",
      seen["audit_title"] == "Audit status - XYZ Pvt Ltd" and
      "BCG-" in seen["audit_facts"] and ABC_MAIL in seen["audit_facts"]
      and "23,11,786.00" in seen["audit_facts"] and
      "35,15,723.34" in seen["audit_facts"], seen.get("audit_facts"))
check("it will not save without an owner",
      "who owns" in seen["audit_problem"], seen["audit_problem"])
records = win.audit_records()
check("one record was created", len(records) == 1, records)
record = records[0]
check("it is tied to the party, the request and the reply",
      record["document_id"] == keys["XYZ Pvt Ltd"] and
      record["party_name"] == "XYZ Pvt Ltd" and
      record["reference"].startswith("BCG-") and
      record["reply_id"] == "m-4" and record["reply_from"] == ABC_MAIL and
      record["message_link"].endswith("m-4") and
      record["request_sent_at"] == "2026-11-10",
      {k: record.get(k) for k in ("document_id", "reference", "reply_id")})
check("it holds the figures and the follow-up",
      record["books_amount"] == XYZ_BOOKS and
      record["confirmed_amount"] == 2311786.0 and
      round(record["variance"], 2) == expected_variance and
      record["confirmation_status"] == "Mismatch" and
      record["state"] == "Under follow-up" and
      record["nature"] == "Disputed item" and record["owner"] == "CA Reviewer"
      and len(record["history"]) == 1, record)
win.show_report(bcg.REPORT_COMPARISON)
pump()
xyz_row = [i for i in range(win.report_table.rowCount())
           if table_text(i, party_column) == "XYZ Pvt Ltd"][0]
check("the link now opens the record and shows its state",
      table_text(xyz_row, audit_column) == "Open record: Under follow-up",
      table_text(xyz_row, audit_column))


def close_it(window):
    seen["reopened_notes"] = window.findChild(QPlainTextEdit,
                                              "audit_notes").toPlainText()
    state = window.findChild(QComboBox, "audit_state")
    state.setCurrentIndex(state.findText("Explained - no adjustment"))
    window.findChild(QPushButton, "audit_save").click()


drive(close_it)
win.on_report_cell(xyz_row, audit_column)
pump()
check("opening it again shows what was saved",
      seen["reopened_notes"] == "Statement of account requested from XYZ.")
check("an update keeps one record and adds to its history",
      len(win.audit_records()) == 1 and
      win.audit_records()[0]["state"] == "Explained - no adjustment" and
      [h["state"] for h in win.audit_records()[0]["history"]]
      == ["Under follow-up", "Explained - no adjustment"],
      win.audit_records()[0]["history"])
audit = report(bcg.REPORT_AUDIT)
check("the Audit status report lists it with the live position",
      len(audit["rows"]) == 1 and
      audit["rows"][0]["party_name"] == "XYZ Pvt Ltd" and
      audit["rows"][0]["confirmation_status"] == "Mismatch" and
      audit["rows"][0]["state"] == "Explained - no adjustment",
      audit["rows"])
before = len(win.audit_records())
win.show_report(bcg.REPORT_COMPARISON)
pump()
win.report_table.setCurrentCell(abc_row, 0)
win.audit_status_dialog = lambda row, record: (_ for _ in ()).throw(
    AssertionError("no record should be offered for a Matched row"))
win.audit_selected_row()
check("a Matched confirmation is not given a record",
      len(win.audit_records()) == before)

print("\n-- 4b. A reply in review gets a record too")
# hand two replies back to automatic matching: both are from ABC's address
# on ABC's request and they disagree, so ABC is in review again
win.assign_reply("m-1", "")
win.assign_reply("m-4", "")
pump()
check("ABC is Needs Review again and offers 'Create record'",
      rows()["ABC Pvt Ltd"]["status"] == bcg.STATUS_REVIEW and
      rows()["ABC Pvt Ltd"]["audit_state_link"] == "Create record",
      (rows()["ABC Pvt Ltd"]["status"],
       rows()["ABC Pvt Ltd"]["audit_state_link"]))
win.assign_reply("m-1", keys["ABC Pvt Ltd"], ABC_BOOKS, "CA Reviewer")
win.assign_reply("m-4", keys["XYZ Pvt Ltd"], 2311786.0, "CA Reviewer",
                 "Confirmed with XYZ by telephone")
pump()

# ======================================================================
print("\n== 5. On paper, and after closing the application ==")
xlsx = os.path.join(WORK, "reports.xlsx")
bcg.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (xlsx, ""))
win.export_reports_excel()
workbook = openpyxl.load_workbook(xlsx)
check("the workbook has an Audit status sheet",
      "Audit status" in workbook.sheetnames, workbook.sheetnames)
queue_heads = [c.value for c in workbook["Exception queue"][4]]
check("the screen-only Review column is not printed",
      "Action" not in queue_heads, queue_heads)
paper = workbook["Requested vs confirmed"]
paper_heads = [c.value for c in paper[4]]
paper_rows = {r[0]: dict(zip(paper_heads, r))
              for r in paper.iter_rows(min_row=5, values_only=True) if r[0]}
check("on paper: XYZ confirmed, variance, status, who and audit status",
      paper_rows["XYZ Pvt Ltd"]["Confirmed by party"] == 2311786.0 and
      round(paper_rows["XYZ Pvt Ltd"]["Variance (confirmed less books)"], 2)
      == expected_variance and
      paper_rows["XYZ Pvt Ltd"]["Status"] == "Mismatch" and
      paper_rows["XYZ Pvt Ltd"]["Confirmed by (reply from)"] == ABC_MAIL and
      paper_rows["XYZ Pvt Ltd"]["Audit status"]
      == "Explained - no adjustment", paper_rows["XYZ Pvt Ltd"])
check("on paper: ABC is Matched", paper_rows["ABC Pvt Ltd"]["Status"]
      == "Matched", paper_rows["ABC Pvt Ltd"]["Status"])
pdf = os.path.join(WORK, "reports.pdf")
bcg.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (pdf, ""))
win.export_reports_pdf()
check("the PDF is written", os.path.exists(pdf) and
      os.path.getsize(pdf) > 5000)

saved, load_error = bcg.load_db()
check("decisions and the audit record survive a restart",
      len(saved["audit_status"]) == 1 and
      saved["audit_status"][0]["state"] == "Explained - no adjustment" and
      [r for r in saved["replies"] if r["id"] == "m-4"][0]["accepted_amount"]
      == 2311786.0 and
      [r for r in saved["replies"] if r["id"] == "m-2"][0]["assigned_to"]
      == bcg.SET_ASIDE,
      (load_error, [(a["party_name"], a["state"])
                    for a in saved["audit_status"]],
       [(r["id"], r.get("assigned_to"), r.get("accepted_amount"))
        for r in saved["replies"]]))

win.show_report(bcg.REPORT_COMPARISON)
pump()
shot = os.path.join(WORK, "review-comparison.png")
win.grab().save(shot)
print("   screenshot:", shot)

print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
if FAIL:
    print("FAILED:", FAIL)
sys.exit(1 if FAIL else 0)
