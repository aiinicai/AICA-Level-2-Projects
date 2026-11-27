import json, os, mimetypes, secrets, time, threading, socket, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from . import paths, framework as F
from modules import ALL

MODS = {m.MANIFEST["key"]: m for m in ALL}
SECRET_KEYS = ("pass", "pw", "key")


def clean(body):
    return {k: ("***" if any(s in k.lower() for s in SECRET_KEYS) else v) for k, v in body.items()} if isinstance(body, dict) else body


class Handler(BaseHTTPRequestHandler):
    server_version = "CATaskMitra"

    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_PUT(self): self.route("PUT")
    def do_DELETE(self): self.route("DELETE")

    def route(self, method):
        u = urlparse(self.path)
        p = unquote(u.path)
        if p.startswith("/api/"):
            return self.api(method, p[5:], parse_qs(u.query))
        if method != "GET":
            return self.send(405, b"")
        rel = "index.html" if p == "/" else p[len("/static/"):] if p.startswith("/static/") else None
        full = os.path.normpath(os.path.join(paths.WEB, rel)) if rel else None
        if not full or not full.startswith(os.path.normpath(paths.WEB)) or not os.path.isfile(full):
            return self.send(404, b"Not found", "text/plain")
        with open(full, "rb") as f:
            data = f.read()
        self.send(200, data, mimetypes.guess_type(full)[0] or "application/octet-stream", {"Cache-Control": "no-cache"})

    def user_of(self, db):
        c = self.headers.get("Cookie", "")
        tok = next((x.split("=", 1)[1] for x in c.split(";") if x.strip().startswith("wd=")), None)
        if not tok:
            return None
        return db.one("select u.* from sessions s join users u on u.id=s.user_id where s.token=? and s.expires>? and u.active=1",
                      (tok.strip(), time.time()))

    def api(self, method, path, query):
        db = F.DB()
        headers = {}
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            q = {k: v[0] for k, v in query.items()}
            mod, _, rest = path.partition("/")
            rest = "/" + rest
            user = self.user_of(db)
            if mod == "auth":
                res = self.auth(db, method, rest, body, user, headers)
            else:
                if not user:
                    raise F.HttpError(401, "Please sign in")
                res = self.dispatch(db, user, mod, method, rest, body, q)
                if method != "GET":
                    F.log(db, user["username"], f"{method} {path}", "(uploaded CSV data)" if "/import" in path else json.dumps(clean(body))[:300])
            db.commit()
            if isinstance(res, F.Response):
                h = {"Content-Disposition": f'attachment; filename="{res.filename}"'} if res.filename else {}
                return self.send(200, res.body, res.ctype, h)
            return self.send(200, json.dumps(res, default=str).encode(), extra=headers)
        except F.HttpError as e:
            db.c.rollback()
            self.send(e.code, json.dumps({"error": e.msg}).encode())
        except Exception as e:
            db.c.rollback()
            import traceback; traceback.print_exc()
            self.send(500, json.dumps({"error": "Server error: %s" % e}).encode())
        finally:
            db.close()

    def dispatch(self, db, user, mod, method, rest, body, q):
        m = MODS.get(mod)
        if not m:
            raise F.HttpError(404, "Unknown module")
        if not F.mod_on(db, mod):
            raise F.HttpError(403, "This module is switched off")
        for meth, rx, fn, roles, sub in m.R.routes:
            if meth != method:
                continue
            mt = rx.match(rest)
            if not mt:
                continue
            if sub and not F.sub_on(db, mod, sub):
                raise F.HttpError(403, "This feature is switched off")
            if roles and user["role"] not in roles:
                raise F.HttpError(403, "Not allowed for your role")
            return fn(F.Ctx(db, user, body, q, mt.groupdict()))
        raise F.HttpError(404, "Not found")

    # ----- authentication -----
    def auth(self, db, method, rest, body, user, headers):
        if rest == "/status":
            n = db.one("select count(*) c from users")["c"]
            return {"setup_needed": n == 0, "firm": F.get_setting(db, "firm_name", "CA Task Mitra"),
                    "hint": F.get_setting(db, "login_hint")}
        if rest == "/setup" and method == "POST":
            if db.one("select count(*) c from users")["c"]:
                raise F.HttpError(403, "Already set up")
            firm, name, uname, pw = (body.get(k, "").strip() for k in ("firm", "name", "username", "password"))
            if not (firm and uname and len(pw) >= 6):
                raise F.HttpError(400, "Enter firm name, username and a password of 6+ characters")
            F.set_setting(db, "firm_name", firm)
            db.x("insert into users(username,name,role,pw) values(?,?,?,?)", (uname, name or uname, "ca", F.hash_pw(pw)))
            for m in ALL:
                if hasattr(m, "seed"):
                    m.seed(db)
            if body.get("demo"):
                from modules import admin
                admin.load_demo(db)
            return {"ok": True}
        if rest == "/login" and method == "POST":
            u = db.one("select * from users where username=? and active=1", (body.get("username", "").strip(),))
            if not u or not F.check_pw(body.get("password", ""), u["pw"]):
                raise F.HttpError(401, "Wrong username or password")
            tok = secrets.token_hex(24)
            db.x("insert into sessions(token,user_id,expires) values(?,?,?)", (tok, u["id"], time.time() + 12 * 3600))
            headers["Set-Cookie"] = f"wd={tok}; Path=/; HttpOnly; SameSite=Lax"
            F.log(db, u["username"], "login")
            return {"ok": True}
        if rest == "/logout":
            headers["Set-Cookie"] = "wd=; Path=/; Max-Age=0"
            return {"ok": True}
        if rest == "/session":
            if not user:
                raise F.HttpError(401, "Please sign in")
            mods = []
            for m in ALL:
                man = m.MANIFEST
                st = {r["key"]: bool(r["enabled"]) for r in db.q("select key,enabled from sub_state where mod=?", (man["key"],))}
                mods.append({"key": man["key"], "name": man["name"], "core": man.get("core", False), "status": man["status"],
                             "enabled": F.mod_on(db, man["key"]), "subs": st})
            return {"user": {k: user[k] for k in ("id", "username", "name", "role")},
                    "firm": F.get_setting(db, "firm_name", "CA Task Mitra"), "modules": mods}
        raise F.HttpError(404, "Not found")


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ticker():
    while True:
        time.sleep(30)
        try:
            db = F.DB()
            for m in ALL:
                if hasattr(m, "TICK") and F.mod_on(db, m.MANIFEST["key"]):
                    m.TICK(db)
            db.commit()
            db.close()
        except Exception as e:
            print("ticker error", e)


def find_chrome():
    import shutil
    c = [os.path.join(os.environ.get(k, ""), r"Google\Chrome\Application\chrome.exe") for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
    c += [shutil.which("chrome"), shutil.which("google-chrome"), "/usr/bin/google-chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    return next((p for p in c if p and os.path.exists(p)), None)


def open_app_window(url):
    """Open as a desktop-style window (Chrome --app mode: no tabs/address bar). Falls back to Chrome tab, then default browser."""
    import subprocess
    chrome = find_chrome()
    if chrome:
        try:
            prof = os.path.join(paths.DATA, "chrome_profile")
            subprocess.Popen([chrome, f"--app={url}", f"--user-data-dir={prof}", "--window-size=1366,850", "--no-first-run", "--no-default-browser-check"])
            return
        except Exception:
            pass
    webbrowser.open(url)


def run(port=8765, open_browser=True):
    db = F.DB()
    db.c.execute("PRAGMA journal_mode=WAL")
    F.load(db)
    db.close()
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=ticker, daemon=True).start()
    ip = lan_ip()
    print("=" * 60)
    print(" CA Task Mitra is running. Keep this window open.")
    print(f" This PC     : http://localhost:{port}")
    print(f" Other PCs   : http://{ip}:{port}   (same Wi-Fi / LAN)")
    print(f" Data folder : {paths.DATA}")
    print("=" * 60)
    if open_browser:
        threading.Timer(1.0, lambda: open_app_window(f"http://localhost:{port}")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
