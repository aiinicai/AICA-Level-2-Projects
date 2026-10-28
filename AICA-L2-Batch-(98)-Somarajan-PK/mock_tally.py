"""Tiny MOCK of Tally's XML server for testing the connector without Tally (SYNTHETIC sample data only).
Run: python mock_tally.py  -> listens on localhost:9000 (stop real Tally first, or use --port 9100)."""
import argparse, json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from xml.sax.saxutils import escape


def build(sample):
    j = json.loads(Path(sample).read_text(encoding="utf-8"))
    led = "".join(f'<LEDGER NAME="{escape(b["name"])}"><PARENT>Bank Accounts</PARENT>'
                  f'<OPENINGBALANCE>{-b["opening_balance"]:.2f}</OPENINGBALANCE></LEDGER>' for b in j["banks"])
    vouchers = []
    for b in j["banks"]:
        for n, r in enumerate(b["rows"], 1):
            rec, pay = float(r["Receipt"] or 0), float(r["Payment"] or 0)
            amt = -rec if rec else pay
            ds = datetime.strptime(r["Date"], "%d-%m-%Y").strftime("%Y%m%d")
            vouchers.append(
                f"<VOUCHER><DATE>{ds}</DATE><VOUCHERTYPENAME>{'Receipt' if rec else 'Payment'}</VOUCHERTYPENAME>"
                f"<VOUCHERNUMBER>{n}</VOUCHERNUMBER><NARRATION>{escape(r['Narration'])}</NARRATION>"
                f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{escape(b['name'])}</LEDGERNAME><AMOUNT>{amt:.2f}</AMOUNT>"
                f"<BANKALLOCATIONS.LIST><INSTRUMENTNUMBER>{escape(r['Voucher_Ref'])}</INSTRUMENTNUMBER></BANKALLOCATIONS.LIST>"
                f"</ALLLEDGERENTRIES.LIST><ALLLEDGERENTRIES.LIST><LEDGERNAME>Sundry Party</LEDGERNAME><AMOUNT>{-amt:.2f}</AMOUNT>"
                f"</ALLLEDGERENTRIES.LIST></VOUCHER>")
    wrap = lambda inner: f"<ENVELOPE><BODY><DATA>{inner}</DATA></BODY></ENVELOPE>"
    return {"ReconCompanies": wrap(f'<COLLECTION><COMPANY NAME="{escape(j["company"])}"/></COLLECTION>'),
            "ReconBankLedgers": wrap(f"<COLLECTION>{led}</COLLECTION>"),
            "Day Book": wrap("<TALLYMESSAGE>" + "".join(vouchers) + "</TALLYMESSAGE>")}


def serve(port=9000, sample=None):
    sample = sample or Path(__file__).parent / "sample_data" / "tally_bank_books.json"
    resp = build(sample)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8")
            key = next((k for k in resp if k in body), None)
            out = (resp[key] if key else "<ENVELOPE/>").encode("utf-8")
            self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
    return HTTPServer(("127.0.0.1", port), H)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=9000); a = ap.parse_args()
    print(f"Mock Tally (synthetic) on localhost:{a.port} - Ctrl+C to stop"); serve(a.port).serve_forever()
