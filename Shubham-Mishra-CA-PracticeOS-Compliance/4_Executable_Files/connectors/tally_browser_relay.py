"""
Tiny local CORS relay for the CA PracticeOS Compliance app's in-browser
Tally Connector.

Why this exists: a browser cannot POST XML directly to Tally Prime's XML/HTTP
gateway, because Tally doesn't answer the browser's CORS preflight check, so
the browser blocks the request before it's even sent. This script sits in
between: the browser talks to this relay (which does answer CORS preflight
requests correctly), and the relay forwards the request to Tally over a
plain server-to-server connection, which isn't subject to browser CORS at
all.

Run:
    python tally_browser_relay.py

Then in the app's "Tally Connector" section, set "Tally Server URL" to:
    http://localhost:9001
(Tally itself stays on its usual port 9000 - no change needed there.)

No third-party packages required - uses only the Python standard library.
"""
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

TALLY_URL = "http://localhost:9000"
RELAY_PORT = 9001


class RelayHandler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        self._forward(b"")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        self._forward(body)

    def _forward(self, body):
        try:
            req = urllib.request.Request(
                TALLY_URL,
                data=body if body else None,
                headers={"Content-Type": "text/xml"},
                method="POST" if body else "GET",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            self.send_response(200)
            self._cors_headers()
            self.send_header("Content-Type", "text/xml")
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.URLError as exc:
            self.send_response(502)
            self._cors_headers()
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Could not reach Tally at {TALLY_URL}: {exc}".encode())

    def log_message(self, fmt, *args):
        print("[relay]", fmt % args)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        TALLY_URL = sys.argv[1]
    server = HTTPServer(("localhost", RELAY_PORT), RelayHandler)
    print(f"Tally CORS relay running at http://localhost:{RELAY_PORT}")
    print(f"Forwarding to Tally at {TALLY_URL}")
    print("In the CA PracticeOS app's Tally Connector, set 'Tally Server URL' to the relay address above.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
