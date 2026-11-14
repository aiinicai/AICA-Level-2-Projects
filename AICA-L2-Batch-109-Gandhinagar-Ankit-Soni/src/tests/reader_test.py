"""The application reads the PDF a party sends back.

The scenario that prompted it: a letter went out for 35,00,000; the party
returned the signed slip as a scanned PDF with 25,00,000 written on it and a
covering e-mail that states no figure.  The mismatch can only be found by
opening the PDF, so the application fetches it from the bridge, runs OCR on
this computer and takes the figure from the slip.
"""
import base64, importlib.util, json, os, shutil, ssl, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit, parse_qs

os.environ["QT_QPA_PLATFORM"] = "offscreen"
WORK = "/home/claude/pytest/rdwork"
shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK, exist_ok=True)
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "appdata")
sys.path.insert(0, "/home/claude/pytest")

spec = importlib.util.spec_from_file_location(
    "bcg", "/home/claude/balance_confirmation_generator.py")
bcg = importlib.util.module_from_spec(spec)
sys.modules["bcg"] = bcg
spec.loader.exec_module(bcg)
import slips

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QDate, QEvent

PASS, FAIL = [], []
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name +
          ("" if cond or not detail else "  ->  " + str(detail)[:260]))

CLIENT = "Example Manufacturing Private Limited"
STATE = {"replies": [], "files": {}, "old_script": False, "asked": []}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        query = parse_qs(urlsplit(self.path).query)
        if query.get("key") != ["secret"]:
            payload = {"error": "not authorised"}
        elif "message" in query and not STATE["old_script"]:
            message = query["message"][0]
            STATE["asked"].append(message)
            if message not in STATE["files"]:
                payload = {"error": "unknown message", "files": []}
            else:
                payload = {"message": message, "skipped": [], "files": [
                    {"index": i, "name": name, "type": kind, "size": len(data),
                     "data": base64.b64encode(data).decode()}
                    for i, (name, kind, data) in
                    enumerate(STATE["files"][message])]}
        else:
            payload = {"count": len(STATE["replies"]),
                       "replies": STATE["replies"]}
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


CERTS = os.path.join(WORK, "certs"); os.makedirs(CERTS)
KEY, CERT = os.path.join(CERTS, "key.pem"), os.path.join(CERTS, "cert.pem")
subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", KEY, "-out", CERT, "-days", "2", "-subj",
                "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1"],
               check=True, capture_output=True)
server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
server_context.load_cert_chain(CERT, KEY)
client_context = ssl.create_default_context(cafile=CERT)
ssl._create_default_https_context = lambda *a, **k: client_context
server = HTTPServer(("127.0.0.1", 0), Handler)
server.socket = server_context.wrap_socket(server.socket, server_side=True)
threading.Thread(target=server.serve_forever, daemon=True).start()
FEED = "https://127.0.0.1:%d/exec?key=secret" % server.server_address[1]

import openpyxl
book = openpyxl.Workbook(); sheet = book.active
for row in [["Name", "Address line 1", "Closing balance", "Category", "Email ID"],
            ["ABC Pvt Ltd", "Mumbai", 3500000, "Trade receivable", "ap@abc.example"],
            ["XYZ Pvt Ltd", "Mumbai", 1250000, "Trade receivable", "ar@xyz.example"],
            ["PQR Traders", "Pune", 800000, "Trade payable", "fin@pqr.example"],
            ["LMN Exports", "Surat", 640000, "Trade receivable", "ac@lmn.example"],
            ["DEF Metals", "Thane", 910000, "Trade payable", "ac@def.example"]]:
    sheet.append(row)
SOURCE = os.path.join(WORK, "balances.xlsx"); book.save(SOURCE)

QMessageBox.exec = lambda self: QMessageBox.StandardButton.Ok
app = QApplication([]); app.setStyle("Fusion")
win = bcg.MainWindow(); win.resize(1440, 900); win.show()

def pump(n=6):
    for _ in range(n):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

def wait(attribute, limit=4000):
    for _ in range(limit):
        pump(2)
        if getattr(win, attribute, None) is None:
            return True
        QApplication.instance().thread().msleep(25)
    return False

def settle():
    ok = wait("bridge_thread"); pump()
    return wait("reader_thread") and ok

pump()
win.cl_name.setText(CLIENT); win.add_client()
win.active_client()["signatory_name"] = "Mr. R. Mehta"
win.db["settings"]["firm_name"] = "Ankit & Associates"
win.fy_year.setText("2025-26"); win.fy_end.setDate(QDate(2026, 3, 31)); win.add_year()
win.aud_name.setText("Audit"); win.aud_email.setText("audit@firm.example"); win.add_auditor()
win.load_file(SOURCE); pump()
out = os.path.join(WORK, "out"); os.makedirs(out)
win.db["settings"]["output_folder"] = out
confs = [win.to_confirmation(r) for r in win.validation()["generable"]]
folder = win.run_output_folder(); os.makedirs(folder, exist_ok=True)
worker = bcg.GenerateWorker(confs, folder); produced = []
worker.produced.connect(produced.append); worker.run()
win.generated = produced; win.save_run(folder)
letters = {g["conf"]["party_name"]: g["pdf_data"] for g in produced}
docs = {d["party_name"]: d for d in win.db["runs"][0]["documents"]}
for n, d in enumerate(docs.values(), 1):
    d.update(email_status="sent", thread_id="t-%d" % n, sent_at="2026-11-08")
win.persist()

print("\n== 1. The reader ==")
ready, words = bcg.reader_status()
check("PDF reading and OCR are available", ready, words)
check("five letters were issued", len(win.sent_documents()) == 5)

def reply(n, party, body, files, text=""):
    rid = "m-%d" % n
    STATE["files"][rid] = files
    return {"id": rid, "received_at": "2026-11-09",
            "from_email": docs[party]["email"], "from_name": party,
            "subject": "Re: Balance confirmation request", "reference": "",
            "thread_id": docs[party]["thread_id"], "in_reply_to": "",
            "body": body, "bounced": False, "bridge_status": "needs review",
            "files": [f[0] for f in files],
            "attachments": ([{"name": "; ".join(f[0] for f in files),
                              "text": text}] if text else [])}

print("\n== 2. The case reported: 35,00,000 sent, 25,00,000 on the scanned slip ==")
abc_pdf, _ = slips.scanned(letters["ABC Pvt Ltd"], "25,00,000", handwritten=True)
STATE["replies"] = [reply(1, "ABC Pvt Ltd",
                          "Dear Sir,\nPlease find the signed confirmation attached.\nRegards",
                          [("ABC confirmation.pdf", "application/pdf", abc_pdf)])]
win.db["settings"]["bridge_feed_url"] = FEED
win.go("recon"); pump()
win.sync_bridge()
check("the sync and the reading both finished", settle())
check("the application asked the bridge for the PDF", STATE["asked"] == ["m-1"],
      STATE["asked"])
stored = win.db["replies"][0]
check("the reply is marked as read", stored.get("files_read") is True,
      stored.get("files_error"))
read = [a for a in stored["attachments"] if a.get("read_by") == "application"]
check("what was read is kept with the reply", len(read) == 1 and
      "25,00,000" in read[0]["text"], read and read[0]["text"][-200:])
check("it was read by OCR, the scan having no text layer",
      read and read[0]["method"] == "OCR", read and read[0]["method"])
rows = {r["party_name"]: r for r in win.recon_rows}
abc = rows["ABC Pvt Ltd"]
check("the status is Mismatch, not Agreed", abc["status"] == bcg.STATUS_VARIANCE,
      (abc["status"], abc["note"]))
check("confirmed 25,00,000", abc["confirmed_amount"] == 2500000.0,
      abc["confirmed_amount"])
check("variance -10,00,000", abc["variance"] == -1000000.0, abc["variance"])
check("the source document is named", abc["extract_source"] == "ABC confirmation.pdf",
      abc["extract_source"])
check("the remark says it was read by OCR", "OCR" in abc["note"], abc["note"])
report = bcg.build_report(bcg.REPORT_COMPARISON, win.recon_rows,
                          win.recon_exceptions, {})
line = [r for r in report["rows"] if r["party_name"] == "ABC Pvt Ltd"][0]
check("Requested vs confirmed carries books, confirmed and variance",
      (line["books_amount"], line["confirmed_amount"], line["variance"]) ==
      (3500000.0, 2500000.0, -1000000.0), line)

print("\n== 3. The covering e-mail says 'confirmed', the slip says otherwise ==")
xyz_pdf, _ = slips.scanned(letters["XYZ Pvt Ltd"], "11,00,000.00")
STATE["replies"].append(reply(2, "XYZ Pvt Ltd",
    "Balance confirmed. Signed copy attached.",
    [("XYZ signed.pdf", "application/pdf", xyz_pdf)]))
win.sync_bridge(); settle()
xyz = {r["party_name"]: r for r in win.recon_rows}["XYZ Pvt Ltd"]
check("the slip outranks the covering words", xyz["status"] == bcg.STATUS_VARIANCE
      and xyz["confirmed_amount"] == 1100000.0, (xyz["status"], xyz["confirmed_amount"]))
check("variance -1,50,000", xyz["variance"] == -150000.0, xyz["variance"])

print("\n== 4. A slip that agrees ==")
pqr_pdf = slips.typed(letters["PQR Traders"], "8,00,000.00")
STATE["replies"].append(reply(3, "PQR Traders", "PFA",
    [("PQR.pdf", "application/pdf", pqr_pdf)]))
win.sync_bridge(); settle()
pqr = {r["party_name"]: r for r in win.recon_rows}["PQR Traders"]
check("a matching figure on the slip is Agreed", pqr["status"] == bcg.STATUS_AGREED
      and pqr["confirmed_amount"] == 800000.0, (pqr["status"], pqr["note"]))

print("\n== 5. A slip returned blank is not taken as agreement ==")
lmn_pdf, _ = slips.scanned(letters["LMN Exports"], None,
                           extra=[(0, 40, "S Patel"), (0, 95, "12/11/2026")])
STATE["replies"].append(reply(4, "LMN Exports", "Signed and attached.",
    [("LMN.pdf", "application/pdf", lmn_pdf)]))
win.sync_bridge(); settle()
lmn = {r["party_name"]: r for r in win.recon_rows}["LMN Exports"]
check("the pre-printed figure coming back is not a confirmation",
      lmn["status"] == bcg.STATUS_REVIEW and lmn["confirmed_amount"] is None,
      (lmn["status"], lmn["confirmed_amount"], lmn["note"]))

print("\n== 6. A figure OCR cannot read whole is never recorded ==")
broken = {"name": "x.pdf", "method": "OCR", "read_by": "application",
          "text": "We hereby confirm that the amount payable by us to X as on "
                  "31 March\n2026 is INR25, 00,0.00\nName and Title"}
got = bcg.extract_confirmation({"body": "PFA", "attachments": [broken]}, 3500000.0)
check("no amount is taken from a broken reading", got["amount"] is None, got)
check("and the auditor is shown what was seen", "25, 00,0.00" in got["note"],
      got["note"])
wild = dict(broken, text=broken["text"].replace("25, 00,0.00", "2,500"))
got = bcg.extract_confirmation({"body": "PFA", "attachments": [wild]}, 3500000.0)
check("a figure out of all proportion is not taken either",
      got["amount"] is None, got)
typed_text = dict(broken, method="text",
                  text=broken["text"].replace("25, 00,0.00", "25,00,000.00"))
got = bcg.extract_confirmation({"body": "PFA", "attachments": [typed_text]}, 3500000.0)
check("a clean figure in a text layer is taken", got["amount"] == 2500000.0, got)

print("\n== 7. Nothing is read twice ==")
before = list(STATE["asked"])
win.sync_bridge(); settle()
check("a second sync fetches no document again", STATE["asked"] == before,
      STATE["asked"])

print("\n== 8. An older bridge script is explained, not hidden ==")
STATE["old_script"] = True
def_pdf, _ = slips.scanned(letters["DEF Metals"], "9,10,000.00")
STATE["replies"].append(reply(5, "DEF Metals", "Attached.",
    [("DEF.pdf", "application/pdf", def_pdf)]))
win.sync_bridge(); settle()
held = [r for r in win.db["replies"] if r["id"] == "m-5"][0]
check("the reply is kept", held is not None)
check("the reason is recorded", "older version" in held.get("files_error", ""),
      held.get("files_error"))
row = {r["party_name"]: r for r in win.recon_rows}["DEF Metals"]
check("the party goes for review with the reason",
      row["status"] == bcg.STATUS_REVIEW and "older version" in row["note"],
      (row["status"], row["note"]))
STATE["old_script"] = False
win.read_reply_documents(retry=True); wait("reader_thread")
row = {r["party_name"]: r for r in win.recon_rows}["DEF Metals"]
check("once the script is updated, the button reads it",
      row["status"] == bcg.STATUS_AGREED and row["confirmed_amount"] == 910000.0,
      (row["status"], row["note"]))

print("\n== 9. A confirmation received as a file ==")
win.db["replies"] = [r for r in win.db["replies"] if r["id"] != "m-1"]
win.persist(); win.refresh_recon()
check("ABC is pending again",
      {r["party_name"]: r for r in win.recon_rows}["ABC Pvt Ltd"]["status"]
      == bcg.STATUS_PENDING)
path = os.path.join(WORK, "received by post.pdf")
open(path, "wb").write(abc_pdf)
added = win.add_reply_from_file(path)
check("the file was read", added is not None)
check("the reference code was read off the letter",
      added and added["reference"] == docs["ABC Pvt Ltd"]["reference"],
      added and added["reference"])
abc = {r["party_name"]: r for r in win.recon_rows}["ABC Pvt Ltd"]
check("it was matched to its party by the reference",
      abc["match_method"] == bcg.MATCH_REFERENCE, abc["match_method"])
check("and shows the mismatch", abc["status"] == bcg.STATUS_VARIANCE and
      abc["variance"] == -1000000.0, (abc["status"], abc["variance"]))
photo = os.path.join(WORK, "phone photo.jpg")
open(photo, "wb").write(slips.scanned(letters["LMN Exports"], "6,40,000",
                                      handwritten=True, seed=4)[1])
win.db["replies"] = [r for r in win.db["replies"] if r["id"] != "m-4"]
added = win.add_reply_from_file(photo)
lmn = {r["party_name"]: r for r in win.recon_rows}["LMN Exports"]
check("a photograph is read the same way", lmn["status"] == bcg.STATUS_AGREED
      and lmn["confirmed_amount"] == 640000.0, (lmn["status"], lmn["note"]))

print("\n== 10. The files themselves ==")
check("a password-protected or broken PDF is reported, not crashed on",
      bool(bcg.read_document(b"%PDF-1.4 broken", "x.pdf")["error"]))
check("an empty file is reported", bool(bcg.read_document(b"", "x.pdf")["error"]))
check("the address asks for one message, keeping the key",
      bcg.attachment_url("https://h/exec?key=K", "m 1") ==
      "https://h/exec?key=K&message=m+1", bcg.attachment_url("https://h/exec?key=K", "m 1"))
check("a Word file is not something to OCR",
      bcg.is_readable_file("a.docx") is False and bcg.is_readable_file("a.PDF"))

win.close(); pump(); server.shutdown()
print("\n" + "-" * 54)
print("PASSED %d   FAILED %d" % (len(PASS), len(FAIL)))
if FAIL:
    print("Failed: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
