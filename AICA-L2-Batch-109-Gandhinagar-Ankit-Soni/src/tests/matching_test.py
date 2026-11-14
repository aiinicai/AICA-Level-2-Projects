"""Version 3.4: every reply is tied to its party on evidence, never by order.

The case reported: letters to ABC (79,60,098.48) and XYZ (35,15,723.34).
ABC replied first confirming 79,60,098.48.  XYZ replied later with
1,80,000 - as a reply-all on ABC's request e-mail.  Version 3.3 recorded
1,80,000 against ABC and lost ABC's own reply.

Run:  python matching_test.py      (needs the assembled application)
"""
import importlib.util, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.environ.get("BCG_APP") or os.path.join(
    HERE, "..", "balance_confirmation_generator.py")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# scratch files go to the system's temporary folder, never into the project
WORK = tempfile.mkdtemp(prefix="bcg-matching-")
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
          ("" if cond or not detail else "  ->  " + str(detail)[:260]))


ABC_MAIL = "accounts@abc-test.example"
XYZ_MAIL = "finance@xyz-test.example"


def documents():
    return [
        {"id": "abc", "party_name": "ABC Pvt Ltd",
         "category": "Trade Receivable", "amount": 7960098.48,
         "currency": "INR", "email": ABC_MAIL, "reference": "BCG-ABCD23",
         "message_id": "<req-abc@firm.example>", "thread_id": "",
         "email_status": "sent", "sent_at": "2026-11-10"},
        {"id": "xyz", "party_name": "XYZ Pvt Ltd",
         "category": "Trade Receivable", "amount": 3515723.34,
         "currency": "INR", "email": XYZ_MAIL, "reference": "BCG-XYZW45",
         "message_id": "<req-xyz@firm.example>", "thread_id": "",
         "email_status": "sent", "sent_at": "2026-11-10"},
    ]


QUOTED_ABC = ("\n\nOn Tue, Nov 10, 2026 at 10:04 PM Ankit & Associates "
              "<audit@firm.example> wrote:\n> Dear Sir/Madam,\n> Please find "
              "attached a balance confirmation request issued by Unique "
              "Chains in respect of the Trade Receivable balance, being "
              "INR 79,60,098.48. Ref BCG-ABCD23\n> ABC Pvt Ltd")


def abc_reply(**extra):
    reply = {"id": "m-abc", "received_at": "2026-11-10 22:08",
             "from_email": ABC_MAIL, "from_name": "Ankit Soni",
             "subject": "Re: Balance confirmation request as at 31 March "
                        "2026 — Unique Chains",
             "in_reply_to": "<req-abc@firm.example>",
             "body": "Helo,\n\nWe confirm the balance and it is correct and "
                     "matches Rs. 79,60,098.48." + QUOTED_ABC}
    reply.update(extra)
    return reply


def xyz_reply(**extra):
    # a reply-all on ABC's request: thread and quoted letter both say ABC
    reply = {"id": "m-xyz", "received_at": "2026-11-13 20:16",
             "from_email": XYZ_MAIL, "from_name": "Ankit Soni",
             "subject": "Re: Balance confirmation request as at 31 March "
                        "2026 — Unique Chains",
             "in_reply_to": "<req-abc@firm.example>",
             "body": "Hello,We confirm the balance payable as per our books "
                     "is 180000 only" + QUOTED_ABC}
    reply.update(extra)
    return reply


def run(docs, replies):
    rows, exceptions = bcg.build_reconciliation(docs, replies,
                                                today="2026-11-14")
    return {r["party_name"]: r for r in rows}, exceptions


# ======================================================================
print("\n== 1. The case reported ==")
for label, docs, replies in (
        ("ABC first, docs in order", documents(), [abc_reply(), xyz_reply()]),
        ("XYZ first, docs in order", documents(), [xyz_reply(), abc_reply()]),
        ("ABC first, docs reversed", documents()[::-1],
         [abc_reply(), xyz_reply()]),
        ("XYZ first, docs reversed", documents()[::-1],
         [xyz_reply(), abc_reply()])):
    rows, exceptions = run(docs, replies)
    abc, xyz = rows["ABC Pvt Ltd"], rows["XYZ Pvt Ltd"]
    check("%s: ABC confirmed 79,60,098.48 and Agreed" % label,
          abc["confirmed_amount"] == 7960098.48 and
          abc["status"] == bcg.STATUS_AGREED,
          (abc["confirmed_amount"], abc["status"]))
    check("%s: XYZ confirmed 1,80,000, a Mismatch" % label,
          xyz["confirmed_amount"] == 180000.0 and
          xyz["status"] == bcg.STATUS_VARIANCE,
          (xyz["confirmed_amount"], xyz["status"]))
    check("%s: each row keeps its own reply" % label,
          abc["reply_id"] == "m-abc" and xyz["reply_id"] == "m-xyz",
          (abc["reply_id"], xyz["reply_id"]))

rows, exceptions = run(documents(), [abc_reply(), xyz_reply()])
xyz = rows["XYZ Pvt Ltd"]
check("XYZ's variance is 1,80,000 less 35,15,723.34",
      round(xyz["variance"], 2) == round(180000.0 - 3515723.34, 2),
      xyz["variance"])
check("XYZ was matched on its sender address",
      xyz["match_method"] == bcg.MATCH_SENDER, xyz["match_method"])
check("the remark says it answered ABC's request and asks for a check",
      "reply to the request sent to ABC Pvt Ltd" in xyz["note"] and
      "confirm before relying on it" in xyz["note"], xyz["note"])
check("the basis names both pieces of evidence",
      XYZ_MAIL in xyz["match_basis"] and "ABC Pvt Ltd" in xyz["match_basis"],
      xyz["match_basis"])
check("ABC's basis: its own address and a reply to its own request",
      ABC_MAIL in rows["ABC Pvt Ltd"]["match_basis"] and
      "reply to the request sent to ABC" in rows["ABC Pvt Ltd"]["match_basis"],
      rows["ABC Pvt Ltd"]["match_basis"])
check("nothing left in the exception queue", exceptions == [], exceptions)

# ======================================================================
print("\n== 2. The same reply from an address not on the party list ==")
stranger = xyz_reply(from_email="someone.else@unlisted.example")
rows, exceptions = run(documents(), [abc_reply(), stranger])
abc = rows["ABC Pvt Ltd"]
check("ABC is NOT given 1,80,000", abc["confirmed_amount"] != 180000.0,
      abc["confirmed_amount"])
check("ABC goes to Needs review: two replies, two figures",
      abc["status"] == bcg.STATUS_REVIEW and
      "give different figures" in abc["note"], (abc["status"], abc["note"]))
check("both figures are quoted for the reviewer",
      "79,60,098.48" in abc["note"] and "1,80,000.00" in abc["note"],
      abc["note"])
check("both replies are in the exception queue",
      sorted(e["reply_id"] for e in exceptions) == ["m-abc", "m-xyz"],
      exceptions)
check("XYZ is still Pending - not guessed",
      rows["XYZ Pvt Ltd"]["status"] == bcg.STATUS_PENDING)
rows2, _ = run(documents(), [stranger, abc_reply()])
check("the outcome does not depend on arrival order",
      rows2["ABC Pvt Ltd"]["status"] == bcg.STATUS_REVIEW and
      rows2["ABC Pvt Ltd"]["note"] == abc["note"])

# ======================================================================
print("\n== 3. A reply with no evidence at all ==")
blank = {"id": "m-none", "received_at": "2026-11-12",
         "from_email": "unknown@nowhere.example", "from_name": "Accounts",
         "subject": "balance confirmation",
         "body": "We confirm the balance payable as per our books is "
                 "4,50,000 only"}
for docs in (documents(), documents()[::-1]):
    rows, exceptions = run(docs, [blank])
    check("the first party on the list does not get it (%s)" %
          docs[0]["party_name"],
          all(r["confirmed_amount"] is None for r in rows.values()),
          [(r["party_name"], r["confirmed_amount"]) for r in rows.values()])
check("it is in the exception queue with the reason",
      len(exceptions) == 1 and "Nothing in the reply shows which party"
      in exceptions[0]["reason"], exceptions)
check("the figure it carries is shown to the reviewer",
      exceptions[0]["amount"] == 450000.0, exceptions[0]["amount"])

# ======================================================================
print("\n== 4. The party names itself ==")
named = dict(blank, id="m-named",
             body="XYZ Pvt Ltd confirms the balance payable as per our books "
                  "is 1,80,000 only")
rows, exceptions = run(documents(), [named])
check("matched to XYZ on the name in its own words",
      rows["XYZ Pvt Ltd"]["confirmed_amount"] == 180000.0 and
      rows["XYZ Pvt Ltd"]["match_method"] == bcg.MATCH_NAME,
      (rows["XYZ Pvt Ltd"]["confirmed_amount"],
       rows["XYZ Pvt Ltd"]["match_method"]))
check("ABC untouched", rows["ABC Pvt Ltd"]["status"] == bcg.STATUS_PENDING)

quoted_only = dict(blank, id="m-quoted",
                   body="We confirm the balance is 2,00,000 only" + QUOTED_ABC)
found = bcg.assess_reply(quoted_only, documents())
check("a name or code only in OUR quoted letter does not say who replied",
      found["method"] in (bcg.MATCH_REFERENCE,) and
      found["confidence"] <= 0.80, found)

# ======================================================================
print("\n== 5. Evidence that disagrees goes to review ==")
clash = xyz_reply(id="m-clash", in_reply_to="",
                  body="ABC Pvt Ltd confirms the balance is 1,80,000 only")
rows, exceptions = run(documents(), [clash])
check("sent from XYZ's address but naming ABC: nobody gets the figure",
      all(r["confirmed_amount"] is None for r in rows.values()))
check("the reason sets out both sides",
      exceptions and "disagrees" in exceptions[0]["reason"] and
      XYZ_MAIL in exceptions[0]["reason"] and "ABC Pvt Ltd"
      in exceptions[0]["reason"], exceptions and exceptions[0]["reason"])
check("both parties are offered as possibilities",
      "ABC Pvt Ltd" in exceptions[0]["candidates"] and
      "XYZ Pvt Ltd" in exceptions[0]["candidates"], exceptions[0]["candidates"])

two_codes = dict(blank, id="m-codes",
                 subject="Re: Balance confirmation — Ref BCG-ABCD23",
                 body="Our figure for BCG-XYZW45 is 1,80,000 only")
rows, exceptions = run(documents(), [two_codes])
check("two of our reference codes in its own words: review",
      all(r["confirmed_amount"] is None for r in rows.values()) and
      exceptions and "more than one letter" in exceptions[0]["reason"],
      exceptions)

# ======================================================================
print("\n== 6. Shared addresses and repeat parties ==")
group = documents()
group[1]["email"] = ABC_MAIL                 # one mailbox for both companies
coded = dict(abc_reply(id="m-g1", in_reply_to=""),
             subject="Re: Balance confirmation — Ref BCG-XYZW45",
             body="We confirm 1,80,000 only")
rows, exceptions = run(group, [coded])
check("shared mailbox + XYZ's reference code in the subject: XYZ",
      rows["XYZ Pvt Ltd"]["confirmed_amount"] == 180000.0,
      (rows["XYZ Pvt Ltd"]["confirmed_amount"], exceptions))
plain = dict(abc_reply(id="m-g2", in_reply_to=""), body="We confirm 1,80,000")
rows, exceptions = run(group, [plain])
check("shared mailbox and nothing else: review, not the first party",
      all(r["confirmed_amount"] is None for r in rows.values()) and
      exceptions and "more than one party" in exceptions[0]["reason"],
      exceptions)

two_categories = documents()[:1] + [dict(
    documents()[0], id="abc-adv", category="Advance from Customers",
    amount=250000.0, reference="BCG-ADVN67",
    message_id="<req-abc-adv@firm.example>")]
on_advance = abc_reply(id="m-adv", in_reply_to="<req-abc-adv@firm.example>",
                       body="We confirm the advance of 2,50,000 is correct")
rows, _ = bcg.build_reconciliation(two_categories, [on_advance])
by_cat = {r["category"]: r for r in rows}
check("same party, two letters: the reply goes to the one it answers",
      by_cat["Advance from Customers"]["confirmed_amount"] == 250000.0 and
      by_cat["Trade Receivable"]["confirmed_amount"] is None,
      [(r["category"], r["confirmed_amount"]) for r in rows])
vague = abc_reply(id="m-vague", in_reply_to="", body="We confirm 2,50,000")
rows, exceptions = bcg.build_reconciliation(two_categories, [vague])
check("same party, two letters, no pointer: review with the categories",
      all(r["confirmed_amount"] is None for r in rows) and exceptions and
      "Advance from Customers" in exceptions[0]["reason"], exceptions)

# ======================================================================
print("\n== 7. Names and domains are read carefully ==")
similar = [dict(documents()[0], id="a1", party_name="ABC Pvt Ltd"),
           dict(documents()[1], id="a2", party_name="ABC Exports Pvt Ltd",
                email="ap@abcexports.example")]
both = dict(blank, id="m-sim",
            body="ABC Exports Pvt Ltd confirms the balance at 5,00,000")
rows, _ = run(similar, [both])
check("'ABC Exports Pvt Ltd' is not taken as 'ABC Pvt Ltd'",
      rows["ABC Exports Pvt Ltd"]["confirmed_amount"] == 500000.0 and
      rows["ABC Pvt Ltd"]["confirmed_amount"] is None,
      [(k, v["confirmed_amount"]) for k, v in rows.items()])
wordy = [dict(documents()[0], party_name="Balance Pvt Ltd")]
found = bcg.assess_reply(dict(blank, body="We confirm the balance is "
                                          "1,00,000"), wordy)
check("a one-word name in ordinary text is not a match",
      found["document"] is None, found)
colleague = dict(blank, id="m-dom", from_email="cfo@abc-test.example")
found = bcg.assess_reply(colleague, documents())
check("another person at the party's own domain is matched, with care",
      found["document"] and found["document"]["id"] == "abc" and
      found["method"] == bcg.MATCH_DOMAIN and found["confidence"] < 0.8,
      found)
public = [dict(documents()[0], email="abc.test.only@gmail.com")]
found = bcg.assess_reply(dict(blank, from_email="other.test.only@gmail.com"),
                         public)
check("a shared mail service (gmail.com) is never evidence",
      found["document"] is None, found)

# ======================================================================
print("\n== 8. Two replies that agree, and bounces ==")
again = abc_reply(id="m-abc2", received_at="2026-11-12",
                  body="Reconfirming: Rs. 79,60,098.48 is correct.")
rows, exceptions = run(documents(), [abc_reply(), again])
abc = rows["ABC Pvt Ltd"]
check("two replies with the same figure: Agreed, both on record",
      abc["status"] == bcg.STATUS_AGREED and abc["replies_count"] == 2 and
      abc["reply_ids"] == "m-abc, m-abc2", (abc["status"], abc["reply_ids"]))
bounce = {"id": "m-b", "received_at": "2026-11-10 22:05",
          "from_email": "mailer-daemon@googlemail.com",
          "from_name": "Mail Delivery Subsystem",
          "subject": "Delivery Status Notification (Failure)",
          "body": "Address not found: %s" % XYZ_MAIL}
rows, _ = run(documents(), [bounce])
check("a bounce with no thread is placed by the failed address",
      rows["XYZ Pvt Ltd"]["status"] == bcg.STATUS_RETURNED and
      rows["ABC Pvt Ltd"]["status"] == bcg.STATUS_PENDING,
      [(k, v["status"]) for k, v in rows.items()])

# ======================================================================
print("\n== 9. The decision by hand ==")
manual = dict(blank, assigned_to="xyz")
rows, exceptions = run(documents(), [manual])
check("assigned by hand to XYZ: recorded against XYZ",
      rows["XYZ Pvt Ltd"]["confirmed_amount"] == 450000.0 and
      rows["XYZ Pvt Ltd"]["match_method"] == bcg.MATCH_MANUAL and
      exceptions == [], (rows["XYZ Pvt Ltd"], exceptions))
aside = dict(blank, assigned_to=bcg.SET_ASIDE)
held = []
rows, exceptions = bcg.build_reconciliation(documents(), [aside],
                                            set_aside=held)
check("set aside: not counted, not in the queue, still on record",
      exceptions == [] and len(held) == 1 and
      all(r["confirmed_amount"] is None for r in rows))
picked = dict(stranger, assigned_to="abc")
rows, exceptions = run(documents(), [abc_reply(), picked])
check("a hand decision outranks an automatic match for the same party",
      rows["ABC Pvt Ltd"]["confirmed_amount"] == 180000.0 and
      rows["ABC Pvt Ltd"]["replies_count"] == 2,
      (rows["ABC Pvt Ltd"]["confirmed_amount"], exceptions))
check("the subject template now carries the reference",
      "{reference}" in bcg.DEFAULT_SUBJECT and
      bcg.fill_template(bcg.DEFAULT_SUBJECT, {"reference": "BCG-ABCD23",
                                              "client_name": "Unique"})
      .endswith("Ref BCG-ABCD23"),
      bcg.DEFAULT_SUBJECT)

# ======================================================================
print("\n== 10. Through the application window ==")
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QDate, QEvent
import openpyxl

QMessageBox.exec = lambda self: QMessageBox.StandardButton.Ok
app = QApplication([])
app.setStyle("Fusion")
app.setPalette(bcg.qt_palette())
app.setStyleSheet(bcg.style_sheet())
win = bcg.MainWindow()
win.resize(1440, 900)
win.show()
win.ask = lambda *a, **k: True


def pump(n=6):
    for _ in range(n):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


stock = bcg.blank_db()
stock["settings"]["mail"]["subject"] = bcg.LEGACY_SUBJECT
own = bcg.blank_db()
own["settings"]["mail"]["subject"] = "Our own words"
check("the stock subject is migrated, a written one is kept",
      bcg.normalise_db(stock)["settings"]["mail"]["subject"]
      == bcg.DEFAULT_SUBJECT and
      bcg.normalise_db(own)["settings"]["mail"]["subject"] == "Our own words")

listing = os.path.join(WORK, "listing.xlsx")
book = openpyxl.Workbook()
sheet = book.active
sheet.append(["Name", "Address line 1", "Pincode", "State", "Country",
              "Currency", "Closing balance", "Category", "email id"])
sheet.append(["ABC Pvt Ltd", "Unit 12, 10th Road", 400057, "Maharashtra",
              "India", "INR", 7960098.48, "Trade receivable", ABC_MAIL])
sheet.append(["XYZ Pvt Ltd", "Plot 4, Okhla", 110020, "Delhi", "India",
              "INR", 3515723.34, "Trade receivable", XYZ_MAIL])
book.save(listing)

pump()
win.cl_name.setText("Unique Chains & Jewels Pvt Ltd")
win.add_client()
win.active_client()["signatory_name"] = "Mr. R. Mehta"
win.db["settings"]["firm_name"] = "Ankit & Associates"
win.fy_year.setText("2026-27")
win.fy_end.setDate(QDate(2027, 3, 31))
win.add_year()
win.aud_name.setText("Audit team")
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
sent = {d["party_name"]: d for d in win.db["runs"][0]["documents"]}
for party, document in sent.items():
    document.update(email_status="sent", sent_at="2026-11-10",
                    message_id="<req-%s@firm.example>" % party[:3].lower())
win.persist()
check("two letters issued", len(win.sent_documents()) == 2)

replies = [abc_reply(), xyz_reply()]
replies[1]["subject"] = replies[0]["subject"]
win.go("recon")
pump()
added, offered = win.merge_replies(replies)
pump()
rows = {r["party_name"]: r for r in win.recon_rows}
check("on screen: ABC 79,60,098.48 Agreed",
      rows["ABC Pvt Ltd"]["confirmed_amount"] == 7960098.48 and
      rows["ABC Pvt Ltd"]["status"] == bcg.STATUS_AGREED,
      (rows["ABC Pvt Ltd"]["confirmed_amount"], rows["ABC Pvt Ltd"]["status"]))
check("on screen: XYZ 1,80,000 Mismatch",
      rows["XYZ Pvt Ltd"]["confirmed_amount"] == 180000.0 and
      rows["XYZ Pvt Ltd"]["status"] == bcg.STATUS_VARIANCE,
      (rows["XYZ Pvt Ltd"]["confirmed_amount"], rows["XYZ Pvt Ltd"]["status"]))

register = bcg.build_report(bcg.REPORT_REGISTER, win.recon_rows,
                            win.recon_exceptions)
heads = [h for h, _k, _t in register["columns"]]
check("the register shows reply, date, basis and amount confirmed",
      all(h in heads for h in ("Reply from", "Reply received", "Matched on",
                               "Amount confirmed")), heads)

# the unlisted sender: ABC to review, decided by hand through the window
win.db["replies"] = []
win.merge_replies([abc_reply(), stranger])
pump()
rows = {r["party_name"]: r for r in win.recon_rows}
check("unlisted sender: ABC Needs review in the window",
      rows["ABC Pvt Ltd"]["status"] == bcg.STATUS_REVIEW)
labels = [win.recon_stats.itemAt(i).widget()
          for i in range(win.recon_stats.count())
          if win.recon_stats.itemAt(i).widget()]
texts = [" ".join(lbl.text() for lbl in w.findChildren(bcg.QLabel))
         for w in labels]
check("a Review card counts the replies to decide",
      any("review 2" in t.lower() for t in texts), texts)
index = win.report_combo.findData(bcg.REPORT_EXCEPTIONS)
win.report_combo.setCurrentIndex(index)
pump()
check("Assign reply is offered on the exception queue",
      win.btn_assign.isVisible())
check("the queue lists both replies",
      win.report_table.rowCount() == 2, win.report_table.rowCount())
xyz_key = [d for d in win.sent_documents()
           if d["party_name"] == "XYZ Pvt Ltd"][0]["id"]
win.choose_party_dialog = lambda entry: xyz_key
win.report_table.setCurrentCell(
    [i for i, e in enumerate(win.recon_exceptions)
     if e["reply_id"] == "m-xyz"][0], 0)
win.assign_selected_reply()
pump()
rows = {r["party_name"]: r for r in win.recon_rows}
check("after assigning the stranger's reply to XYZ: ABC Agreed",
      rows["ABC Pvt Ltd"]["status"] == bcg.STATUS_AGREED,
      rows["ABC Pvt Ltd"]["status"])
check("...and XYZ 1,80,000, marked as assigned by hand",
      rows["XYZ Pvt Ltd"]["confirmed_amount"] == 180000.0 and
      rows["XYZ Pvt Ltd"]["match_method"] == bcg.MATCH_MANUAL,
      (rows["XYZ Pvt Ltd"]["confirmed_amount"],
       rows["XYZ Pvt Ltd"]["match_method"]))
held = [r for r in win.db["replies"] if r["id"] == "m-xyz"][0]
check("the decision and its time are kept on the reply",
      held.get("assigned_to") == xyz_key and held.get("assigned_at"))
win.report_combo.setCurrentIndex(win.report_combo.findData(
    bcg.REPORT_REGISTER))
pump()
check("Assign reply is hidden on the other reports",
      not win.btn_assign.isVisible())
win.assign_reply("m-xyz", "")
check("handed back to automatic matching: ABC returns to review",
      {r["party_name"]: r for r in win.recon_rows}["ABC Pvt Ltd"]["status"]
      == bcg.STATUS_REVIEW)

shot = os.path.join(WORK, "recon.png")
win.report_combo.setCurrentIndex(index)
pump()
win.grab().save(shot)
print("   screenshot:", shot)

print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
if FAIL:
    print("FAILED:", FAIL)
sys.exit(1 if FAIL else 0)
