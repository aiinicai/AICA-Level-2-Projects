"""The stage-one scenario: six dummy replies against four sent confirmations."""
import importlib.util, os, sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
spec = importlib.util.spec_from_file_location(
    "bcg", "/home/claude/balance_confirmation_generator.py")
bcg = importlib.util.module_from_spec(spec)
sys.modules["bcg"] = bcg
spec.loader.exec_module(bcg)

PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name +
          ("" if cond or not detail else "  ->  " + str(detail)[:200]))

CLIENT = "Example Manufacturing Private Limited"

DOCUMENTS = [
    {"id": "d1", "party_name": "ABC Ltd", "category": "Trade Receivable",
     "amount": 125000.0, "currency": "INR", "email": "ap@abc.example",
     "reference": "BCG-7F3K2A", "thread_id": "t-100", "message_id": "<m100@x>",
     "email_status": "sent", "sent_at": "2026-10-01",
     "filename": "ABC Ltd - Trade Receivable.docx"},
    {"id": "d2", "party_name": "XYZ Suppliers", "category": "Trade Payable",
     "amount": 80000.0, "currency": "INR", "email": "ar@xyz.example",
     "reference": "BCG-9Q4M1B", "thread_id": "t-101", "message_id": "<m101@x>",
     "email_status": "sent", "sent_at": "2026-10-01",
     "filename": "XYZ Suppliers - Trade Payable.docx"},
    {"id": "d3", "party_name": "Customer P Ltd",
     "category": "Advance from Customers", "amount": 50000.0, "currency": "INR",
     "email": "fin@customerp.example", "reference": "BCG-3H8T5C",
     "thread_id": "t-102", "message_id": "<m102@x>", "email_status": "sent",
     "sent_at": "2026-09-10", "filename": "Customer P Ltd - AFC.docx"},
    {"id": "d4", "party_name": "Vendor Q Ltd",
     "category": "Advance to Vendors", "amount": 30000.0, "currency": "INR",
     "email": "acc@vendorq.example", "reference": "BCG-5J2R7D",
     "thread_id": "t-103", "message_id": "<m103@x>", "email_status": "sent",
     "sent_at": "2026-10-01", "filename": "Vendor Q Ltd - ATV.docx"},
    {"id": "d5", "party_name": "Slow Payer Ltd", "category": "Trade Receivable",
     "amount": 45000.0, "currency": "INR", "email": "ap@slowpayer.example",
     "reference": "BCG-2K6W8E", "thread_id": "t-104", "message_id": "<m104@x>",
     "email_status": "sent", "sent_at": "2026-09-01",
     "filename": "Slow Payer Ltd - Trade Receivable.docx"},
]

REPLIES = [
    # a) matched by thread, agrees exactly
    {"id": "r1", "received_at": "2026-10-06", "from_email": "ap@abc.example",
     "from_name": "Accounts Payable", "subject": "Re: Balance confirmation",
     "thread_id": "t-100", "body": "Dear Sir, we agree with the balance.",
     "attachments": [{"name": "signed.pdf", "text":
      "We hereby confirm that amount payable by us to " + CLIENT +
      " as on 31 March 2026 is INR 1,25,000.00  Authorised Signatory"}]},
    # b) matched by reference code, confirms a different figure
    {"id": "r2", "received_at": "2026-10-08", "from_email": "finance@xyz-grp.example",
     "from_name": "XYZ Group Finance",
     "subject": "Balance confirmation [BCG-9Q4M1B]",
     "body": "Our records are not in agreement with yours.",
     "attachments": [{"name": "slip.pdf", "text":
      "We hereby confirm that amount receivable by us from " + CLIENT +
      " as on 31 March 2026 is INR 78,500.00"}]},
    # c) a bounce for Vendor Q
    {"id": "r3", "received_at": "2026-10-02",
     "from_email": "mailer-daemon@googlemail.com", "from_name": "Mail Delivery",
     "subject": "Delivery Status Notification (Failure)",
     "thread_id": "t-103",
     "body": "Address not found: acc@vendorq.example", "attachments": []},
    # d) unknown sender, no reference, no name we know
    {"id": "r4", "received_at": "2026-10-09", "from_email": "someone@unknown.example",
     "from_name": "Someone", "subject": "Balance confirmation",
     "body": "We hereby confirm that amount payable by us to you as on "
             "31 March 2026 is INR 44,000.00", "attachments": []},
    # e) another unknown sender with no figure at all
    {"id": "r5", "received_at": "2026-10-10", "from_email": "other@nowhere.example",
     "from_name": "Other", "subject": "balance confirmation",
     "body": "Please find our response attached.", "attachments": []},
    # f) Indian grouping and a bracketed negative, matched by sender
    {"id": "r6", "received_at": "2026-10-11", "from_email": "fin@customerp.example",
     "from_name": "Customer P", "subject": "Re: balance confirmation",
     "body": "We hereby confirm that advance amount paid by us to " + CLIENT +
             " as on 31 March 2026 is INR 12,34,567.00", "attachments": []},
]

print("\n== Matching ==")
results = {}
for reply in REPLIES:
    doc, method, conf = bcg.match_reply(reply, DOCUMENTS)
    results[reply["id"]] = (doc, method, conf)
    print("   %-4s -> %-16s %-14s %.2f"
          % (reply["id"], (doc or {}).get("party_name", "(none)"), method, conf))

check("thread match for ABC", results["r1"][0]["id"] == "d1"
      and results["r1"][1] == bcg.MATCH_THREAD)
check("reference match for XYZ from a different address",
      results["r2"][0]["id"] == "d2" and results["r2"][1] == bcg.MATCH_REFERENCE)
check("bounce matched to Vendor Q by thread", results["r3"][0]["id"] == "d4")
check("unknown sender stays unmatched", results["r4"][0] is None)
check("second unknown stays unmatched", results["r5"][0] is None)
check("sender-address match for Customer P",
      results["r6"][0]["id"] == "d3" and results["r6"][1] == bcg.MATCH_SENDER)

print("\n== Reading the figure ==")
e1 = bcg.extract_confirmation(REPLIES[0])
check("ABC amount read from the attachment", e1["amount"] == 125000.0, e1)
check("attachment preferred over the body", e1["source"] == "signed.pdf", e1)
check("ABC stance agreed", e1["stance"] == "agreed", e1)
check("signature detected", e1["signed"] is True, e1)
e2 = bcg.extract_confirmation(REPLIES[1])
check("XYZ amount read", e2["amount"] == 78500.0, e2)
check("XYZ stance not in agreement", e2["stance"] == "not in agreement", e2)
e6 = bcg.extract_confirmation(REPLIES[5])
check("Indian grouping 12,34,567 read", e6["amount"] == 1234567.0, e6)
neg = bcg.extract_confirmation({"body": "We hereby confirm that amount "
                                "payable by us to X as on 31 March 2026 is "
                                "INR (5,000.00)", "attachments": []})
check("bracketed negative read as negative", neg["amount"] == -5000.0, neg)
blank = bcg.extract_confirmation({"body": "We will revert shortly.",
                                  "attachments": []})
check("no figure gives None, never a guess", blank["amount"] is None, blank)

print("\n== Reconciliation ==")
rows, exceptions = bcg.build_reconciliation(DOCUMENTS, REPLIES,
                                            today="2026-10-20")
by_party = {r["party_name"]: r for r in rows}
for r in rows:
    print("   %-16s %-12s books %-12s confirmed %-12s variance %s"
          % (r["party_name"], r["status"],
             bcg.fmt_amount(r["books_amount"], "INR"),
             bcg.fmt_amount(r["confirmed_amount"], "INR") or "-",
             bcg.fmt_amount(r["variance"], "INR") or "-"))

check("ABC agreed", by_party["ABC Ltd"]["status"] == bcg.STATUS_AGREED)
check("ABC variance nil", by_party["ABC Ltd"]["variance"] == 0.0)
check("XYZ shows a variance",
      by_party["XYZ Suppliers"]["status"] == bcg.STATUS_VARIANCE)
check("XYZ variance is -1,500",
      by_party["XYZ Suppliers"]["variance"] == -1500.0,
      by_party["XYZ Suppliers"]["variance"])
check("XYZ variance pct ~1.88",
      abs(by_party["XYZ Suppliers"]["variance_pct"] - 1.875) < 0.01,
      by_party["XYZ Suppliers"]["variance_pct"])
check("Vendor Q returned",
      by_party["Vendor Q Ltd"]["status"] == bcg.STATUS_RETURNED)
check("Customer P matched, so not pending",
      by_party["Customer P Ltd"]["status"] == bcg.STATUS_VARIANCE,
      by_party["Customer P Ltd"]["status"])
check("two unmatched replies went to exceptions",
      len([e for e in exceptions
           if e["reason"].startswith("Nothing in the reply shows which "
                                      "party sent it")]) == 2,
      exceptions)
check("exception keeps the figure it read but does not post it",
      any(e["amount"] == 44000.0 for e in exceptions), exceptions)

print("\n== Ageing and reminders ==")
pending_doc = dict(DOCUMENTS[2])
pending_doc["id"] = "d9"
pending_doc["party_name"] = "Slow Payer Ltd"
pending_doc["sent_at"] = "2026-09-01"
rows2, _ = bcg.build_reconciliation([pending_doc], [], today="2026-10-20")
check("pending when no reply", rows2[0]["status"] == bcg.STATUS_PENDING)
check("age is 49 days", rows2[0]["age_days"] == 49, rows2[0]["age_days"])
check("third reminder due", rows2[0]["reminder_stage"] == 3,
      rows2[0]["reminder_stage"])
check("not-sent letters are not counted as pending",
      bcg.reconcile({"amount": 1, "email_status": "not sent"})["status"]
      == bcg.STATUS_NOT_SENT)

print("\n== Summary and coverage ==")
summary = bcg.summarise(rows)
print("   " + ", ".join("%s=%s" % (k, round(v, 2) if isinstance(v, float) else v)
                        for k, v in summary.items()))
check("5 sent", summary["sent"] == 5, summary)
check("3 received", summary["received"] == 3, summary)
check("1 still pending", summary["pending"] == 1, summary)
check("1 agreed", summary["agreed"] == 1, summary)
check("2 variances", summary["variance"] == 2, summary)
check("1 returned", summary["returned"] == 1, summary)
# coverage = value of balances for which a confirmation came back, over the
# value sent out: (125000 + 80000 + 50000) / (285000 + 45000)
check("coverage is value-weighted",
      abs(summary["coverage_pct"] - 255000 / 330000 * 100) < 0.01,
      summary["coverage_pct"])
cats = bcg.summarise_by_category(rows)
check("category split covers all four", len(cats) == 4, [c["category"] for c in cats])
# Trade Receivable now holds ABC (confirmed) and Slow Payer (pending)
check("receivable category coverage 125000/170000",
      abs([c for c in cats if c["category"] == "Trade Receivable"][0]
          ["coverage_pct"] - 125000 / 170000 * 100) < 0.01,
      [c for c in cats if c["category"] == "Trade Receivable"][0]["coverage_pct"])

print("\n" + "-" * 52)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("Failures: " + "; ".join(FAIL))
sys.exit(1 if FAIL else 0)
