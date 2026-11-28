"""
RealEstate 360 — Standalone Desktop Application & Embedded Offline Server
Runs a self-contained local HTTP + REST API + SQLite server on 127.0.0.1
and opens the RealEstate 360 workspace inside PySide6 Qt WebEngine (no Node.js required).
"""
import argparse
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import secrets
import shutil
import socket
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def get_resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def resolve_web_dist(res_dir: Path) -> Path:
    candidates = [
        res_dir / "web_dist",
        res_dir / "dist",
        res_dir.parent / "dist",
        res_dir.parent / "desktop" / "web_dist",
    ]
    for c in candidates:
        if (c / "index.html").is_file():
            return c
    raise FileNotFoundError(
        "Could not locate compiled frontend bundle (web_dist/index.html or dist/index.html)."
    )


def resolve_seed_file(res_dir: Path) -> Path | None:
    candidates = [
        res_dir / "seed_dataset.json",
        res_dir.parent / "desktop" / "seed_dataset.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def get_app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    data_dir = base / "RealEstate360" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "backups").mkdir(parents=True, exist_ok=True)
    return data_dir


def find_free_port(preferred: int = 3000) -> int:
    for port in (preferred, 3360, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return 0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii"))


SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)


def sign_token(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    data_b64 = b64url_encode(raw)
    sig = hmac.new(SESSION_SECRET.encode("utf-8"), data_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{data_b64}.{b64url_encode(sig)}"


def verify_token(auth_header: str | None) -> dict | None:
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    parts = token.split(".")
    if len(parts) != 2:
        return None
    data_b64, sig_b64 = parts
    expected = b64url_encode(
        hmac.new(SESSION_SECRET.encode("utf-8"), data_b64.encode("ascii"), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(sig_b64, expected):
        return None
    try:
        payload = json.loads(b64url_decode(data_b64).decode("utf-8"))
        if int(time.time() * 1000) > int(payload.get("exp", 0)):
            return None
        return payload
    except Exception:
        return None


class DesktopDatabase:
    def __init__(self, data_dir: Path, seed_path: Path | None):
        self.data_dir = data_dir
        self.backup_dir = data_dir / "backups"
        self.db_path = data_dir / "realestate360.db"
        self.seed_path = seed_path
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=64)
        return f"{salt.hex()}:{derived.hex()}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        try:
            salt_hex, key_hex = stored_hash.split(":")
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(key_hex)
            derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=64)
            return hmac.compare_digest(derived, expected)
        except Exception:
            return False

    def _init_db(self):
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS app_state (
                        key TEXT PRIMARY KEY,
                        json_value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL UNIQUE,
                        role TEXT NOT NULL,
                        company_scope TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        active INTEGER NOT NULL DEFAULT 1
                    );
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        actor TEXT NOT NULL,
                        role TEXT NOT NULL,
                        action TEXT NOT NULL,
                        entity TEXT NOT NULL,
                        details TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS backups (
                        id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        checksum TEXT NOT NULL
                    );
                    """
                )
                row = conn.execute("SELECT json_value FROM app_state WHERE key = 'dataset'").fetchone()
                if row is None:
                    if self.seed_path and self.seed_path.is_file():
                        seed = json.loads(self.seed_path.read_text(encoding="utf-8"))
                    else:
                        raise FileNotFoundError("Missing seed_dataset.json for first-time initialization.")
                    conn.execute(
                        "INSERT INTO app_state (key, json_value, updated_at) VALUES (?, ?, ?)",
                        ("dataset", json.dumps(seed), utc_now_iso()),
                    )
                    for log in seed.get("auditLogs", []):
                        conn.execute(
                            "INSERT OR REPLACE INTO audit_logs (id, timestamp, actor, role, action, entity, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (log["id"], log["timestamp"], log["actor"], log["role"], log["action"], log["entity"], log["details"]),
                        )
                    for bak in seed.get("backups", []):
                        conn.execute(
                            "INSERT OR REPLACE INTO backups (id, filename, created_at, size_bytes, type, checksum) VALUES (?, ?, ?, ?, ?, ?)",
                            (bak["id"], bak["filename"], bak["createdAt"], bak["sizeBytes"], bak["type"], bak["checksum"]),
                        )

                cnt = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
                if cnt == 0:
                    default_pass = os.environ.get("ADMIN_PASSCODE") or "RealEstate360!2026"
                    users = [
                        ("usr-cfo", "Nasser Al Harthy", "nasser.cfo@almajd.om", "CFO_Admin", "ALL"),
                        ("usr-ctrl", "Tariq Al Maskari", "tariq.ctrl@almajd.om", "Finance_Controller", "ALL"),
                        ("usr-pd", "Khalid Al Riyami", "khalid.pd@almajd.om", "Project_Director", "ALL"),
                        ("usr-board", "Sheikh Hamad Al Busaidi", "hamad.board@almajd.om", "Board_Viewer", "ALL"),
                    ]
                    for uid, name, email, role, scope in users:
                        conn.execute(
                            "INSERT INTO users (id, name, email, role, company_scope, password_hash, active) VALUES (?, ?, ?, ?, ?, ?, 1)",
                            (uid, name, email, role, scope, self._hash_password(default_pass)),
                        )
                conn.commit()
            finally:
                conn.close()

    def get_dataset(self) -> dict:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT json_value FROM app_state WHERE key = 'dataset'").fetchone()
                ds = json.loads(row["json_value"])
                logs = [
                    dict(r)
                    for r in conn.execute(
                        "SELECT id, timestamp, actor, role, action, entity, details FROM audit_logs ORDER BY timestamp DESC LIMIT 200"
                    ).fetchall()
                ]
                baks = [
                    dict(r)
                    for r in conn.execute(
                        "SELECT id, filename, created_at as createdAt, size_bytes as sizeBytes, type, checksum FROM backups ORDER BY created_at DESC LIMIT 50"
                    ).fetchall()
                ]
                ds["auditLogs"] = logs
                ds["backups"] = baks
                return ds
            finally:
                conn.close()

    def save_dataset(self, ds: dict):
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO app_state (key, json_value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET json_value=excluded.json_value, updated_at=excluded.updated_at",
                    ("dataset", json.dumps(ds), utc_now_iso()),
                )
                conn.commit()
            finally:
                conn.close()

    def get_users(self) -> list[dict]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT id, name, email, role, company_scope as companyScope, active FROM users"
                ).fetchall()
                return [{**dict(r), "active": bool(r["active"])} for r in rows]
            finally:
                conn.close()

    def find_user_with_hash(self, user_id: str) -> dict | None:
        with self._lock:
            conn = self._connect()
            try:
                r = conn.execute(
                    "SELECT id, name, email, role, company_scope as companyScope, password_hash as passwordHash, active FROM users WHERE id = ?",
                    (user_id,),
                ).fetchone()
                return dict(r) if r else None
            finally:
                conn.close()

    def insert_audit_log(self, entry: dict):
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO audit_logs (id, timestamp, actor, role, action, entity, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (entry["id"], entry["timestamp"], entry["actor"], entry["role"], entry["action"], entry["entity"], entry["details"]),
                )
                conn.commit()
            finally:
                conn.close()

    def integrity_check(self) -> dict:
        with self._lock:
            conn = self._connect()
            try:
                res = conn.execute("PRAGMA integrity_check").fetchone()[0]
                return {
                    "ok": res == "ok",
                    "result": res,
                    "dbPath": str(self.db_path),
                    "sizeBytes": self.db_path.stat().st_size,
                }
            finally:
                conn.close()

    def create_backup(self, bak_type: str = "Manual") -> dict:
        with self._lock:
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
            filename = f"realestate360_{bak_type.lower()}_{stamp}.db"
            dest = (self.backup_dir / filename).resolve()
            if not str(dest).startswith(str(self.backup_dir.resolve()) + os.sep):
                raise ValueError("Invalid backup path")
            shutil.copy2(self.db_path, dest)
            raw = dest.read_bytes()
            checksum = "sha256:" + hashlib.sha256(raw).hexdigest()[:12]
            rec = {
                "id": f"bak-{int(time.time() * 1000)}",
                "filename": filename,
                "createdAt": utc_now_iso(),
                "sizeBytes": len(raw),
                "type": bak_type,
                "checksum": checksum,
            }
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO backups (id, filename, created_at, size_bytes, type, checksum) VALUES (?, ?, ?, ?, ?, ?)",
                    (rec["id"], rec["filename"], rec["createdAt"], rec["sizeBytes"], rec["type"], rec["checksum"]),
                )
                conn.commit()
            finally:
                conn.close()
            return rec

    def restore_backup(self, filename: str) -> bool:
        with self._lock:
            safe_name = os.path.basename(filename)
            src = (self.backup_dir / safe_name).resolve()
            if not str(src).startswith(str(self.backup_dir.resolve()) + os.sep) or not src.is_file():
                return False
            shutil.copy2(src, self.db_path)
            return True

    def reset_seed(self) -> dict:
        if not self.seed_path or not self.seed_path.is_file():
            raise FileNotFoundError("Seed dataset file missing")
        seed = json.loads(self.seed_path.read_text(encoding="utf-8"))
        self.save_dataset(seed)
        return self.get_dataset()


def make_handler(db: DesktopDatabase, web_dist: Path):
    web_dist_resolved = web_dist.resolve()

    class RequestHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args):
            # Quiet standard console output for clean desktop UX
            pass

        def _send_json(self, status: int, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            return json.loads(raw.decode("utf-8"))

        def _require_auth(self, allowed_roles: list[str] | None = None) -> dict | None:
            payload = verify_token(self.headers.get("Authorization"))
            if not payload:
                self._send_json(401, {"error": "Authentication required"})
                return None
            if allowed_roles and payload.get("role") not in allowed_roles:
                self._send_json(403, {"error": f"Role {payload.get('role')} lacks permission for this action"})
                return None
            return payload

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            req_path = parsed.path

            if req_path == "/api/health":
                self._send_json(200, {"status": "ok", "integrity": db.integrity_check(), "runtime": "python-desktop"})
                return

            if req_path == "/api/bootstrap":
                self._send_json(
                    200,
                    {
                        "dataset": db.get_dataset(),
                        "users": db.get_users(),
                        "integrity": db.integrity_check(),
                    },
                )
                return

            # Serve static frontend files safely
            rel = req_path.lstrip("/") or "index.html"
            candidate = (web_dist_resolved / rel).resolve()
            if not str(candidate).startswith(str(web_dist_resolved) + os.sep) and candidate != web_dist_resolved:
                candidate = web_dist_resolved / "index.html"
            if not candidate.is_file():
                candidate = web_dist_resolved / "index.html"

            ctype, _ = mimetypes.guess_type(str(candidate))
            data = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            req_path = parsed.path
            try:
                body = self._read_json()
            except Exception:
                self._send_json(400, {"error": "Invalid JSON body"})
                return

            if req_path == "/api/auth/session":
                uid = body.get("userId") or "usr-cfo"
                users = db.get_users()
                target = next((u for u in users if u["id"] == uid), None)
                if not target:
                    self._send_json(404, {"error": "User not found"})
                    return
                if "password" in body and body["password"] is not None:
                    full_u = db.find_user_with_hash(uid)
                    if not full_u or not db._verify_password(str(body["password"]), full_u["passwordHash"]):
                        self._send_json(401, {"error": "Invalid credentials"})
                        return
                token = sign_token(
                    {
                        "userId": target["id"],
                        "name": target["name"],
                        "role": target["role"],
                        "exp": int(time.time() * 1000) + 1000 * 60 * 60 * 12,
                    }
                )
                self._send_json(200, {"token": token, "user": target})
                return

            if req_path == "/api/upload/trial-balance":
                user = self._require_auth(["CFO_Admin", "Finance_Controller"])
                if not user:
                    return
                company_id = body.get("companyId")
                period = body.get("period")
                rows = body.get("rows")
                if not company_id or not period or not isinstance(rows, list) or len(rows) == 0:
                    self._send_json(400, {"error": "companyId, period, and non-empty rows are required"})
                    return
                ds = db.get_dataset()
                ds["trialBalance"] = [
                    r for r in ds["trialBalance"] if not (r["companyId"] == company_id and r["period"] == period)
                ] + rows
                for wf in ds["workflows"]:
                    if wf["period"] == period:
                        wf["tbUploaded"] = True
                        if wf["stage"] == "Open":
                            wf["stage"] = "Uploaded"
                db.save_dataset(ds)
                db.insert_audit_log(
                    {
                        "id": f"aud-{int(time.time() * 1000)}",
                        "timestamp": utc_now_iso(),
                        "actor": user["name"],
                        "role": user["role"],
                        "action": "TB_UPLOADED",
                        "entity": f"{company_id} / {period}",
                        "details": f"Uploaded {len(rows)} GL lines for period {period}.",
                    }
                )
                self._send_json(200, {"dataset": db.get_dataset()})
                return

            if req_path == "/api/mappings":
                user = self._require_auth(["CFO_Admin", "Finance_Controller"])
                if not user:
                    return
                if not body.get("accountCode") or not body.get("targetClass"):
                    self._send_json(400, {"error": "accountCode and targetClass are required"})
                    return
                body["approvedBy"] = user["name"]
                body["updatedAt"] = utc_now_iso()[:10]
                ds = db.get_dataset()
                idx = next((i for i, m in enumerate(ds["glMappings"]) if m["accountCode"] == body["accountCode"]), -1)
                if idx >= 0:
                    ds["glMappings"][idx] = body
                else:
                    ds["glMappings"].append(body)
                for row in ds["trialBalance"]:
                    if row["accountCode"] == body["accountCode"]:
                        row["accountClass"] = body["targetClass"]
                db.save_dataset(ds)
                db.insert_audit_log(
                    {
                        "id": f"aud-{int(time.time() * 1000)}",
                        "timestamp": utc_now_iso(),
                        "actor": user["name"],
                        "role": user["role"],
                        "action": "GL_MAPPING_SAVED",
                        "entity": body["accountCode"],
                        "details": f"Mapped account {body['accountCode']} to {body['targetClass']}.",
                    }
                )
                self._send_json(200, {"dataset": db.get_dataset()})
                return

            if req_path == "/api/workflow/transition":
                user = self._require_auth(["CFO_Admin", "Finance_Controller", "Project_Director"])
                if not user:
                    return
                period = body.get("period")
                next_stage = body.get("nextStage")
                comment = body.get("comment")
                dept = body.get("department")
                ds = db.get_dataset()
                wf = next((w for w in ds["workflows"] if w["period"] == period), None)
                if not wf:
                    self._send_json(404, {"error": "Period workflow not found"})
                    return
                if comment and dept:
                    wf["departmentalComments"].append(
                        {"department": dept, "author": user["name"], "comment": comment, "timestamp": utc_now_iso()}
                    )
                if next_stage:
                    if next_stage in ("Approved", "Published", "Locked") and user["role"] != "CFO_Admin":
                        self._send_json(403, {"error": "Only CFO_Admin can approve, publish, or lock MIS periods."})
                        return
                    if wf["stage"] == "Locked" and user["role"] != "CFO_Admin":
                        self._send_json(403, {"error": "Only CFO_Admin can reopen a locked MIS period."})
                        return
                    if next_stage in ("Published", "Locked"):
                        p_rows = [r for r in ds["trialBalance"] if r["period"] == period]
                        tot_dr = sum(float(r.get("periodDebit", 0)) for r in p_rows)
                        tot_cr = sum(float(r.get("periodCredit", 0)) for r in p_rows)
                        threshold = float(ds["policies"].get("materialityThresholdOMR", 500))
                        if abs(tot_dr - tot_cr) > threshold:
                            self._send_json(400, {"error": f"Publication blocked: TB variance OMR {abs(tot_dr - tot_cr):.3f}"})
                            return
                    wf["stage"] = next_stage
                    if next_stage in ("Approved", "Published"):
                        wf["approvedBy"] = user["name"]
                    if next_stage == "Locked":
                        wf["lockedAt"] = utc_now_iso()
                    if next_stage == "Open":
                        wf["lockedAt"] = None
                db.save_dataset(ds)
                db.insert_audit_log(
                    {
                        "id": f"aud-{int(time.time() * 1000)}",
                        "timestamp": utc_now_iso(),
                        "actor": user["name"],
                        "role": user["role"],
                        "action": f"WORKFLOW_{next_stage.upper()}" if next_stage else "WORKFLOW_COMMENT",
                        "entity": f"Period {period}",
                        "details": f"Transitioned {period} to {next_stage}." if next_stage else f"Posted note ({dept}).",
                    }
                )
                self._send_json(200, {"dataset": db.get_dataset()})
                return

            if req_path == "/api/adjustments":
                user = self._require_auth(["CFO_Admin", "Finance_Controller"])
                if not user:
                    return
                if not body.get("description") or float(body.get("amountOMR", 0)) <= 0:
                    self._send_json(400, {"error": "Valid description and positive amountOMR required"})
                    return
                adj = {
                    **body,
                    "id": f"adj-{int(time.time() * 1000)}",
                    "preparedBy": user["name"],
                    "approvedBy": None,
                    "status": "Pending Approval",
                    "createdAt": utc_now_iso(),
                }
                ds = db.get_dataset()
                ds["adjustments"].insert(0, adj)
                db.save_dataset(ds)
                self._send_json(200, {"dataset": db.get_dataset()})
                return

            if req_path.startswith("/api/adjustments/") and req_path.endswith("/approve"):
                user = self._require_auth(["CFO_Admin"])
                if not user:
                    return
                adj_id = req_path.split("/")[3]
                ds = db.get_dataset()
                for a in ds["adjustments"]:
                    if a["id"] == adj_id:
                        a["status"] = "Approved"
                        a["approvedBy"] = user["name"]
                db.save_dataset(ds)
                self._send_json(200, {"dataset": db.get_dataset()})
                return

            if req_path == "/api/policies":
                user = self._require_auth(["CFO_Admin"])
                if not user:
                    return
                ds = db.get_dataset()
                ds["policies"] = body
                db.save_dataset(ds)
                self._send_json(200, {"dataset": db.get_dataset()})
                return

            if req_path == "/api/backups/create":
                user = self._require_auth(["CFO_Admin", "Finance_Controller"])
                if not user:
                    return
                bak = db.create_backup("Manual")
                self._send_json(200, {"backup": bak, "dataset": db.get_dataset()})
                return

            if req_path == "/api/backups/restore":
                user = self._require_auth(["CFO_Admin"])
                if not user:
                    return
                if not db.restore_backup(str(body.get("filename", ""))):
                    self._send_json(404, {"error": "Backup file not found"})
                    return
                self._send_json(200, {"dataset": db.get_dataset()})
                return

            if req_path == "/api/admin/reset-seed":
                user = self._require_auth(["CFO_Admin"])
                if not user:
                    return
                self._send_json(200, {"dataset": db.reset_seed()})
                return

            if req_path == "/api/license/activate":
                user = self._require_auth(["CFO_Admin"])
                if not user:
                    return
                lkey = str(body.get("licenseKey", "")).strip()
                if len(lkey) < 10:
                    self._send_json(400, {"error": "Valid signed license key required (min 10 chars)."})
                    return
                ds = db.get_dataset()
                lic = ds["license"]
                sig = hashlib.sha256(f"{lic['deviceId']}:{lkey}:{body.get('licensedTo', '')}".encode()).hexdigest()[:14].upper()
                lic["edition"] = body.get("edition") or "Permanent"
                lic["status"] = "Active"
                lic["licensedTo"] = body.get("licensedTo") or lic["licensedTo"]
                lic["signatureHash"] = f"SIG-SHA256-{sig}"
                db.save_dataset(ds)
                self._send_json(200, {"dataset": db.get_dataset()})
                return

            if req_path == "/api/ai/commentary":
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    self._send_json(
                        503,
                        {
                            "error": "Offline desktop mode active (GEMINI_API_KEY not set). Use the verified Offline Rule-Based CFO Engine above."
                        },
                    )
                    return
                # Optional online Gemini REST call using verified KPI context
                question = body.get("question")
                verified_ctx = body.get("verifiedContext", {})
                prompt = (
                    "You are the Group CFO AI Management Analyst. Use ONLY the verified JSON numbers below; never invent figures.\n"
                    + (f"Address: {question}\n" if question else "")
                    + json.dumps(verified_ctx)
                )
                req_payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-4-hydrogen:generateContent"
                req = urllib.request.Request(
                    url,
                    data=req_payload,
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=25) as resp:
                        out = json.loads(resp.read().decode("utf-8"))
                        text = (
                            out.get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")
                        )
                        self._send_json(200, {"commentary": text})
                except Exception as exc:
                    self._send_json(500, {"error": f"Online Gemini call failed: {exc}"})
                return

            self._send_json(404, {"error": f"Unknown API endpoint: {req_path}"})

    return RequestHandler


def wait_for_server(port: int, timeout_sec: float = 10.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.05)
    return False


def main():
    parser = argparse.ArgumentParser(description="RealEstate 360 Desktop Launcher")
    parser.add_argument("--server-only", action="store_true", help="Run embedded HTTP/SQLite server without Qt GUI")
    parser.add_argument("--port", type=int, default=0, help="Bind port (default: auto select free port starting 3000)")
    args = parser.parse_args()

    res_dir = get_resource_dir()
    web_dist = resolve_web_dist(res_dir)
    seed_file = resolve_seed_file(res_dir)
    data_dir = get_app_data_dir()

    db = DesktopDatabase(data_dir, seed_file)
    port = args.port if args.port > 0 else find_free_port(3000)

    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(db, web_dist))
    actual_port = server.server_address[1]
    srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
    srv_thread.start()

    if not wait_for_server(actual_port, 10.0):
        print("Failed to bind local RealEstate 360 server.", file=sys.stderr)
        sys.exit(1)

    app_url = f"http://127.0.0.1:{actual_port}/?autostart=1"
    print(f"RealEstate 360 Desktop Server active at {app_url}")
    print(f"SQLite Database: {data_dir / 'realestate360.db'}")

    if args.server_only:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.shutdown()
            return

    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWidgets import QApplication, QMainWindow
    except ImportError:
        import webbrowser

        print("PySide6 not installed; opening RealEstate 360 in default web browser...")
        webbrowser.open(app_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.shutdown()
            return

    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("RealEstate 360 — Financial & Project Intelligence System")
    win.resize(1440, 900)
    view = QWebEngineView()
    view.setUrl(QUrl(app_url))
    win.setCentralWidget(view)
    win.show()
    exit_code = app.exec()
    server.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
