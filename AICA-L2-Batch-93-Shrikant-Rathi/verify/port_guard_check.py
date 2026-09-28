"""A second or stale bridge must never share the port silently (Windows SO_REUSEADDR trap).

1. Bridge A serves on a test port; bridge B started on the same port must NOT bind it: it reports "already running" and exits.
2. A fake OLD bridge (no sign-in, binds with SO_REUSEADDR like the stock server) holds the port: the new bridge must refuse
   with the "older bridge" message rather than bind alongside it.
Runs with an isolated LOOKTHROUGH_USER_DIR; never touches data/user.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
PORT = 8791
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))


def launch(port):
    code = ("import sys; sys.path.insert(0, r'%s'); import lookthrough_bridge as b; b.serve(%d, open_browser=False)"
            % (ROOT / "bridge", port))
    return subprocess.Popen([PY, "-c", code], cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def wait_listening(port, secs=20):
    end = time.time() + secs
    while time.time() < end:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.2)
    return False


tmp = tempfile.mkdtemp(prefix="lt_port_")
ENV = dict(os.environ, LOOKTHROUGH_USER_DIR=tmp)

# 1. two current bridges on one port
a = launch(PORT)
try:
    check("bridge A listens", wait_listening(PORT))
    b = launch(PORT)
    try:
        out, _ = b.communicate(timeout=30)
        check("bridge B exits instead of binding the same port", b.returncode == 0, out[-300:])
        check("bridge B says the app is already running", "already running" in out, out[-300:])
    except subprocess.TimeoutExpired:
        b.kill()
        check("bridge B exits instead of binding the same port", False, "still running: it bound the port")
finally:
    a.kill(); a.wait()


# 2. an old bridge (no /api/auth-state) holding the port the stock way
class Old(BaseHTTPRequestHandler):
    def do_GET(self):
        body, code = (json.dumps({"ok": True, "version": "3.0"}).encode(), 200) if self.path == "/api/status" else (b'{"error": "not found"}', 404)
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


PORT += 1  # the killed bridge A may hold its exclusive port briefly
old = ThreadingHTTPServer(("127.0.0.1", PORT), Old)  # allow_reuse_address = 1, exactly like the pre-sign-in bridge
threading.Thread(target=old.serve_forever, daemon=True).start()
try:
    n = launch(PORT)
    try:
        out, _ = n.communicate(timeout=30)
        check("new bridge refuses to start beside an old one", n.returncode not in (0, None), out[-300:])
        check("the refusal names the older bridge", "OLDER LookThrough Data Bridge" in out, out[-300:])
    except subprocess.TimeoutExpired:
        n.kill()
        check("new bridge refuses to start beside an old one", False, "still running: it bound the port")
finally:
    old.shutdown()


# 3. an EARLIER BUILD of the current bridge (has sign-in, but different code) must not be reused as if current
class Stale(BaseHTTPRequestHandler):
    def do_GET(self):
        ok = self.path == "/api/auth-state"
        body = json.dumps({"setup_needed": False, "signed_in": False, "user": None, "role": None} if ok else {"error": "not found"}).encode()
        self.send_response(200 if ok else 404); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


PORT += 1
stale = ThreadingHTTPServer(("127.0.0.1", PORT), Stale)
threading.Thread(target=stale.serve_forever, daemon=True).start()
try:
    n = launch(PORT)
    try:
        out, _ = n.communicate(timeout=30)
        check("new bridge refuses to reuse an earlier build of itself (code fingerprint differs)", n.returncode not in (0, None) and "EARLIER BUILD" in out, out[-300:])
    except subprocess.TimeoutExpired:
        n.kill()
        check("new bridge refuses to reuse an earlier build of itself (code fingerprint differs)", False, "still running")
finally:
    stale.shutdown()

print(f"\n{sum(RESULTS)}/{len(RESULTS)} passed")
(ROOT / "verify" / "port_guard_result.txt").write_text(f"{sum(RESULTS)}/{len(RESULTS)} passed\n", encoding="utf-8")
sys.exit(0 if all(RESULTS) else 1)
