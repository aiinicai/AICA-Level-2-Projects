"""The desktop half of the Gmail bridge: the app reads the Apps Script feed.

A small HTTP server stands in for the deployed web app, serving the same JSON
the Apps Script publishes.  What is tested is that the application reads it
off the interface thread, records each reply once, reconciles the figures it
brings across, refuses an address that is not HTTPS, and survives every way
the feed can go wrong (a sign-in page, an HTTP error, a feed that is not a
list, a host that is not there).
"""
import importlib.util, json, os, shutil, ssl, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ["QT_QPA_PLATFORM"] = "offscreen"
WORK = "/home/claude/pytest/bwork"
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
          ("" if cond or not detail else "  ->  " + str(detail)[:220]))

CLIENT = "Example Manufacturing Private Limited"

# =========================================================== the fake feed
STATE = {"mode": "ok", "replies": [], "hits": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):          # keep the test output clean
        pass

    def do_GET(self):
        # the application now also asks for each reply's own PDF; those
        # requests are not reads of the feed and are not counted as such
        if "message=" not in self.path:
            STATE["hits"] += 1
        mode = STATE["mode"]
        if mode == "signin":               # Google's own sign-in page
            body = b"<html><body>Sign in to continue</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if mode == "forbidden":
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if mode == "not_a_list":
            payload = {"generated_at": "2026-11-04T06:00:00", "replies": {}}
        else:
            payload = {"generated_at": "2026-11-04T06:00:00",
                       "last_poll": "2026-11-04T05:50:00",
                       "count": len(STATE["replies"]),
                       "replies": STATE["replies"]}
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# The application reads the feed over HTTPS only, so the stand-in serves
# HTTPS too: a certificate is minted here and trusted for this process alone,
# which lets the test drive the application's own method unmodified.
CERTS = os.path.join(WORK, "certs")
os.makedirs(CERTS, exist_ok=True)
KEY = os.path.join(CERTS, "key.pem")
CERT = os.path.join(CERTS, "cert.pem")
subprocess.run(
    ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
     "-keyout", KEY, "-out", CERT, "-days", "2", "-subj", "/CN=127.0.0.1",
     "-addext", "subjectAltName=IP:127.0.0.1"],
    check=True, capture_output=True)

server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
server_context.load_cert_chain(CERT, KEY)
client_context = ssl.create_default_context(cafile=CERT)
ssl._create_default_https_context = lambda *a, **k: client_context

server = HTTPServer(("127.0.0.1", 0), Handler)
server.socket = server_context.wrap_socket(server.socket, server_side=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
FEED = "https://127.0.0.1:%d/exec" % server.server_address[1]

# ============================================================== a workbook
import openpyxl
book = openpyxl.Workbook()
sheet = book.active
sheet.title = "Balances"
for row in [[CLIENT], ["Party-wise balances as at 31.03.2026"], [],
            ["Party Name", "Address", "Closing Bal.", "CCY", "Nature",
             "E-mail ID"],
            ["ABC Ltd", "Mumbai", 125000, "INR", "Debtors", "ap@abc.example"],
            ["XYZ Suppliers", "Delhi", 80000, "INR", "Creditors",
             "ar@xyz.example"],
            ["Customer P Ltd", "Pune", 50000, "INR", "Advance Received",
             "fin@customerp.example"]]:
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


def pump(n=6):
    for _ in range(n):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def wait_for_sync(limit=400):
    """The read runs on its own thread; spin the loop until it is done."""
    for _ in range(limit):
        pump(2)
        if getattr(win, "bridge_thread", None) is None:
            return True
        QApplication.instance().thread().msleep(10)
    return False


pump()

print("\n== 1. Defaults ==")
check("the feed address starts empty",
      win.db["settings"].get("bridge_feed_url") == "")
check("syncing on start is on by default",
      win.db["settings"].get("bridge_sync_on_start") is True)
check("the settings page has the field", hasattr(win, "bridge_url"))
check("the reconciliation page has the note", hasattr(win, "bridge_note"))
check("the note says it is not connected",
      win.bridge_note.text() == "Gmail bridge not connected",
      win.bridge_note.text())
check("the settings status says the same",
      win.bridge_status.text() == "not connected", win.bridge_status.text())

print("\n== 2. An address that is refused ==")
before = STATE["hits"]
win.sync_bridge()
pump()
check("nothing is read without an address", STATE["hits"] == before)
check("the auditor is told where to put it",
      "Settings" in win.status_strip.text(), win.status_strip.text())

win.bridge_url.setText("http://insecure.example/exec")
pump()
win.sync_bridge()
pump()
check("plain HTTP is refused", STATE["hits"] == before)
check("and the reason is given", "https://" in win.status_strip.text(),
      win.status_strip.text())
check("the address is still saved for correction",
      win.db["settings"]["bridge_feed_url"] == "http://insecure.example/exec")

print("\n== 3. The engagement ==")
win.bridge_url.setText("")
pump()
win.cl_name.setText(CLIENT)
win.add_client()
win.active_client()["signatory_name"] = "Mr. R. Mehta"
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
out = os.path.join(WORK, "out")
os.makedirs(out, exist_ok=True)
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
by_party = {d["party_name"]: d for d in win.db["runs"][0]["documents"]}
for index, party in enumerate(("ABC Ltd", "XYZ Suppliers",
                               "Customer P Ltd"), start=1):
    document = by_party[party]
    document["email_status"] = "sent"
    document["thread_id"] = "t-%d" % index
    document["message_id"] = "<t-%d@firm.example>" % index
    document["sent_at"] = "2026-09-20"
win.persist()
check("3 confirmations issued", len(win.sent_documents()) == 3,
      len(win.sent_documents()))

print("\n== 4. The bridge is read ==")
# exactly what the Apps Script publishes, field for field
STATE["replies"] = [
    {"id": "m-1", "received_at": "2026-09-28",
     "from_email": "ap@abc.example", "from_name": "ABC Accounts",
     "subject": "Re: Balance confirmation request",
     "reference": "", "thread_id": "t-1", "in_reply_to": "<t-1@firm.example>",
     "body": "We agree with the balance; the signed copy is attached.",
     "bounced": False, "bridge_status": "recorded", "bridge_note": "",
     "message_link": "https://mail.google.com/mail/u/0/#all/m-1",
     "attachments": [{"name": "abc-signed.pdf", "text":
      "We hereby confirm that the amount payable by us to " + CLIENT +
      " as on 31 March 2026 is INR 1,25,000.00  Authorised Signatory"}]},
    {"id": "m-2", "received_at": "2026-09-29",
     "from_email": "group.finance@xyz.example", "from_name": "XYZ Finance",
     "subject": "Balance confirmation [%s]" % by_party["XYZ Suppliers"]["reference"],
     "reference": by_party["XYZ Suppliers"]["reference"], "thread_id": "t-9",
     "in_reply_to": "", "bounced": False, "bridge_status": "recorded",
     "bridge_note": "",
     "body": "Our books are not in agreement with your statement.",
     "message_link": "https://mail.google.com/mail/u/0/#all/m-2",
     "attachments": [{"name": "xyz.pdf", "text":
      "We hereby confirm that the amount receivable by us from " + CLIENT +
      " as on 31 March 2026 is INR 78,500.00"}]},
]
win.bridge_url.setText(FEED)
pump()
win.go("recon")
pump()
hits = STATE["hits"]
win.sync_bridge()
check("the window is not blocked while it reads",
      getattr(win, "bridge_thread", None) is not None)
check("the read finished", wait_for_sync())
check("the feed was called once", STATE["hits"] == hits + 1,
      STATE["hits"] - hits)
check("2 replies recorded", len(win.db["replies"]) == 2,
      len(win.db["replies"]))
check("the sync time is saved",
      bool(win.db["settings"].get("bridge_last_sync")))
check("the auditor is told what came in",
      "2 new replies" in win.status_strip.text(), win.status_strip.text())
check("the note now reports the read",
      win.bridge_note.text().startswith("Bridge last read"),
      win.bridge_note.text())

print("\n== 5. Reconciled against what was sent ==")
rows = {r["party_name"]: r for r in win.recon_rows}
check("ABC matched on the thread", rows["ABC Ltd"]["match_method"] ==
      bcg.MATCH_THREAD, rows["ABC Ltd"]["match_method"])
check("ABC agreed", rows["ABC Ltd"]["status"] == bcg.STATUS_AGREED,
      rows["ABC Ltd"]["status"])
check("ABC's confirmed figure came across",
      rows["ABC Ltd"]["confirmed_amount"] == 125000.0,
      rows["ABC Ltd"]["confirmed_amount"])
check("the source attachment is named",
      rows["ABC Ltd"]["extract_source"] == "abc-signed.pdf",
      rows["ABC Ltd"]["extract_source"])
check("the signature was noticed", rows["ABC Ltd"]["signed"] is True)
check("XYZ matched on the reference code",
      rows["XYZ Suppliers"]["match_method"] == bcg.MATCH_REFERENCE,
      rows["XYZ Suppliers"]["match_method"])
check("XYZ shows the variance",
      rows["XYZ Suppliers"]["status"] == bcg.STATUS_VARIANCE and
      # confirmed less books: 78,500 - 80,000, so the party is short by 1,500
      abs(rows["XYZ Suppliers"]["variance"] + 1500.0) < 0.01,
      (rows["XYZ Suppliers"]["status"], rows["XYZ Suppliers"]["variance"]))
check("Customer P is still pending",
      rows["Customer P Ltd"]["status"] == bcg.STATUS_PENDING,
      rows["Customer P Ltd"]["status"])
check("the summary agrees", win.recon_summary["received"] == 2 and
      win.recon_summary["pending"] == 1, win.recon_summary)

print("\n== 6. Reading it again records nothing twice ==")
win.sync_bridge()
wait_for_sync()
check("still 2 replies", len(win.db["replies"]) == 2, len(win.db["replies"]))
check("the auditor is told nothing is new",
      "0 new replies" in win.status_strip.text(), win.status_strip.text())

print("\n== 7. A reply the bridge collected while the app was closed ==")
STATE["replies"].append(
    {"id": "m-3", "received_at": "2026-10-02",
     "from_email": "mailer-daemon@googlemail.com",
     "from_name": "Mail Delivery Subsystem",
     "subject": "Delivery Status Notification (Failure)",
     "reference": "", "thread_id": "t-3", "in_reply_to": "",
     "body": "Address not found: fin@customerp.example", "bounced": True,
     "bridge_status": "recorded", "bridge_note": "", "attachments": []})
win.sync_bridge()
wait_for_sync()
check("the new reply is added", len(win.db["replies"]) == 3,
      len(win.db["replies"]))
rows = {r["party_name"]: r for r in win.recon_rows}
check("the bounce is reported as returned",
      rows["Customer P Ltd"]["status"] == bcg.STATUS_RETURNED,
      rows["Customer P Ltd"]["status"])
check("the register no longer calls it pending",
      win.recon_summary["pending"] == 0, win.recon_summary)

print("\n== 8. Every way the feed can go wrong ==")
for mode, fragment, label in (
        ("signin", "sign in", "a sign-in page is explained"),
        ("forbidden", "HTTP 403", "an HTTP error names the code"),
        ("not_a_list", "list of replies", "a malformed feed is reported")):
    STATE["mode"] = mode
    win.status_strip.setText("")
    win.sync_bridge()
    wait_for_sync()
    check(label, fragment.lower() in win.status_strip.text().lower(),
          win.status_strip.text())
    check("nothing was recorded from a %s" % mode,
          len(win.db["replies"]) == 3, len(win.db["replies"]))
STATE["mode"] = "ok"

print("\n== 9. A host that is not there ==")
win.db["settings"]["bridge_feed_url"] = "https://127.0.0.1:9/exec"
win.status_strip.setText("")
win.sync_bridge()
check("the read finished without hanging", wait_for_sync())
check("the failure is reported", "bridge" in win.status_strip.text().lower(),
      win.status_strip.text())
check("the application is still usable",
      win.isVisible() and len(win.db["replies"]) == 3)

print("\n== 10. A quiet read says nothing when there is nothing ==")
win.db["settings"]["bridge_feed_url"] = FEED
win.status_strip.setText("")
win.sync_bridge(quiet=True)
wait_for_sync()
check("no message for a quiet read with no news",
      win.status_strip.text() == "", win.status_strip.text())
check("the sync time is still refreshed",
      bool(win.db["settings"].get("bridge_last_sync")))

print("\n== 11. Saved across a restart ==")
win.db["settings"]["bridge_sync_on_start"] = False
win.persist()
win.close()
pump()
again = bcg.MainWindow()
again.show()
pump()
check("the address survives a restart",
      again.db["settings"]["bridge_feed_url"] == FEED,
      again.db["settings"]["bridge_feed_url"])
check("the field is filled in", again.bridge_url.text() == FEED,
      again.bridge_url.text())
check("the choice not to sync on start survives",
      again.bridge_start.isChecked() is False)
check("the replies survive", len(again.db["replies"]) == 3,
      len(again.db["replies"]))
check("the status line reports the last read",
      again.bridge_status.text().startswith("last read"),
      again.bridge_status.text())
again.close()
pump()

server.shutdown()
print("\n" + "-" * 54)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("Failed: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
