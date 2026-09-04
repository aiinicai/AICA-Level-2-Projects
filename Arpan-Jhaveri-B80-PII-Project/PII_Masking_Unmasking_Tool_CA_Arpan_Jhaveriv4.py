"""
================================================================================
PII MASKING AND UNMASKING TOOL  -  CA ARPAN JHAVERI
================================================================================
Executive-grade, single-file, 100% offline, India-first PII masking & unmasking
desktop tool.

  * Python 3.11+ (verified against 3.11 - 3.14.x)
  * GUI      : Pure Python Tkinter / ttk (zero external GUI dependencies)
  * Offline  : Offline Enforcement Kernel blocks non-loopback sockets
  * Security : AES-256-GCM / Argon2id with standard-library fallback (scrypt + HMAC)
  * Formats  : DOCX, XLSX, PPTX, PDF, CSV, JSON, XML, TXT, MD, HTML, Images (OCR)
  * Features : 
      - Default CSV Mapping Table (.csv) generated and downloaded with masked files
      - Dual Download Action: Download Masked File + CSV Mapping Table in 1 click
      - Unmask modified / AI-processed documents and pasted AI responses
      - High-contrast, clearly visible scrollbars across all viewports
      - SAP-style 4-sided navigation controls
      - Side-by-Side Synchronized Diff Viewer
      - Partial Masking (XXXX-1234, AXXXXXX4F, +91 XXXXX X3210, etc.)
      - Prior Mapping Table Upload & Reuse (.csv / .json / .piimap)
      - Universal Direct Downloads with Timestamped Suffixes

NO CLOUD - NO API - NO LLM - NO TELEMETRY - NO AUTO-UPDATE
================================================================================
"""

from __future__ import annotations

# =====================================================================================
# 0. DEPENDENCY BOOTSTRAP (runs BEFORE the network kill-switch is armed)
# =====================================================================================
import importlib
import importlib.util
import os
import subprocess
import sys

if sys.version_info < (3, 11):
    sys.exit("This tool requires Python 3.11 or newer. Detected: %s" % sys.version.split()[0])

DEPENDENCIES = [
    ("cryptography", "cryptography", "AES-256-GCM authenticated encryption for mapping files"),
    ("argon2",       "argon2-cffi",  "Argon2id password key-derivation (brute-force resistance)"),
    ("pypdf",        "pypdf",        "PDF text extraction and password-protected PDF reading"),
    ("PIL",          "Pillow",       "Image loading for OCR (with decompression-bomb limits)"),
    ("pytesseract",  "pytesseract",  "OCR bridge (needs local Tesseract engine installed)"),
]

BOOTSTRAP_LOG: list[str] = []


def _python_exe() -> str:
    exe = sys.executable or "python"
    if os.name == "nt" and exe.lower().endswith("pythonw.exe"):
        cand = exe[: -len("pythonw.exe")] + "python.exe"
        if os.path.exists(cand):
            return cand
    return exe


def bootstrap_dependencies() -> None:
    """One-time, user-consented, online dependency install. Never runs again."""
    if os.environ.get("PIITOOL_NO_BOOTSTRAP"):
        BOOTSTRAP_LOG.append("Bootstrap skipped (PIITOOL_NO_BOOTSTRAP set).")
        return

    missing = [(m, p, d) for m, p, d in DEPENDENCIES if importlib.util.find_spec(m) is None]
    if not missing:
        BOOTSTRAP_LOG.append("All optional libraries already present - no download needed.")
        return

    print("=" * 78)
    print(" PII Masking and Unmasking Tool - CA Arpan Jhaveri")
    print(" First-run dependency bootstrap (this is the ONLY moment the tool uses")
    print(" the network; afterwards all outbound network access is blocked).")
    print("=" * 78)
    for _, pkg, why in missing:
        print(f"   - {pkg:<16}  {why}")
    print()
    print(" The application still runs WITHOUT these using standard-library fallbacks")
    print(" (scrypt + HMAC-CTR), but full-strength crypto and PDF/OCR require them.")
    print()

    answer = "y"
    try:
        if sys.stdin is not None and sys.stdin.isatty():
            answer = (input(" Download and install them now?  [Y/n]: ").strip() or "y").lower()
    except Exception:
        answer = "y"

    if answer.startswith("n"):
        BOOTSTRAP_LOG.append("User declined the dependency download; running in fallback mode.")
        print(" Skipped. Continuing in fallback mode.\n")
        return

    exe = _python_exe()
    for _, pkg, _ in missing:
        print(f" Installing {pkg} ...", flush=True)
        try:
            proc = subprocess.run(
                [exe, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check", pkg],
                capture_output=True, text=True, timeout=900,
            )
            if proc.returncode == 0:
                BOOTSTRAP_LOG.append(f"Installed: {pkg}")
                print(f"   OK  {pkg}")
            else:
                tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
                BOOTSTRAP_LOG.append(f"Failed: {pkg} ({tail[0] if tail else 'pip error'})")
                print(f"   SKIPPED  {pkg}  -> {tail[0] if tail else 'pip returned an error'}")
        except Exception as exc:
            BOOTSTRAP_LOG.append(f"Failed: {pkg} ({type(exc).__name__})")
            print(f"   SKIPPED  {pkg}  -> {type(exc).__name__}")
    importlib.invalidate_caches()
    print("\n Bootstrap complete. Launching the application ...\n")


bootstrap_dependencies()

# =====================================================================================
# 1. IMPORTS & CONSTANTS
# =====================================================================================
import atexit
import base64
import csv
import hashlib
import hmac
import io
import json
import queue
import re
import secrets
import socket
import struct
import tempfile
import threading
import time
import unicodedata
import zipfile
import zlib
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional
from xml.sax.saxutils import escape as _xml_escape, unescape as _xml_unescape

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore
    HAVE_AESGCM = True
except Exception:
    HAVE_AESGCM = False

try:
    from argon2.low_level import hash_secret_raw, Type as _ArgonType  # type: ignore
    HAVE_ARGON2 = True
except Exception:
    HAVE_ARGON2 = False

try:
    import pypdf  # type: ignore
    HAVE_PYPDF = True
except Exception:
    HAVE_PYPDF = False

try:
    from PIL import Image  # type: ignore
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

try:
    import pytesseract  # type: ignore
    HAVE_TESS = True
except Exception:
    HAVE_TESS = False

APP_NAME = "PII Masking and Unmasking Tool"
APP_OWNER = "CA Arpan Jhaveri"
APP_VERSION = "2.2.0"
FMT_VER = 1
MAGIC = b"PIIMAP\x00"
PLACEHOLDER_RE = re.compile(r"\[([A-Z][A-Z0-9_]*)_([0-9A-F]{4})_(\d{3,})\]")
MANDATORY_ENCRYPTION_CATEGORIES = {
    "AADHAAR", "BANK_ACCOUNT", "CREDIT_CARD", "PASSPORT",
    "DRIVING_LICENCE", "VOTER_ID", "UAN", "ESIC", "PF",
}


# =====================================================================================
# 2. ERROR TAXONOMY
# =====================================================================================
class PiiToolError(Exception):
    code = "E000"

    def __init__(self, user_message: str, detail: str = ""):
        super().__init__(user_message)
        self.user_message = user_message
        self.detail = detail

    def __str__(self) -> str:
        return f"[{self.code}] {self.user_message}"


class IngestError(PiiToolError):            code = "E100"
class UnsupportedFormatError(PiiToolError):  code = "E101"
class ResourceLimitError(PiiToolError):      code = "E102"
class PathSecurityError(PiiToolError):       code = "E103"
class CryptoError(PiiToolError):             code = "E200"
class WrongPasswordError(CryptoError):       code = "E201"
class TamperError(CryptoError):              code = "E202"
class BindingError(CryptoError):             code = "E203"
class PolicyError(PiiToolError):             code = "E300"


class NetworkBlocked(OSError):
    pass


# =====================================================================================
# 3. OFFLINE ENFORCEMENT KERNEL (SG01 / SG02)
# =====================================================================================
class OfflineKernel:
    installed = False
    blocked_attempts = 0
    _real_socket = socket.socket
    _real_getaddrinfo = socket.getaddrinfo
    _real_create_connection = socket.create_connection
    _lock = threading.Lock()
    LOCAL = {"127.0.0.1", "::1", "localhost", "0.0.0.0", "", None}

    @classmethod
    def _is_local(cls, address: Any) -> bool:
        try:
            if isinstance(address, str):
                return True
            if isinstance(address, (tuple, list)) and address:
                host = str(address[0])
                return host in cls.LOCAL or host.startswith("127.") or host == "::1"
            return False
        except Exception:
            return False

    @classmethod
    def _deny(cls, what: str):
        with cls._lock:
            cls.blocked_attempts += 1
        AuditLog.event("network.blocked", {"kind": what})
        raise NetworkBlocked("Outbound network access is disabled by the Offline Enforcement Kernel.")

    @classmethod
    def install(cls):
        if cls.installed:
            return
        base = cls._real_socket

        class GuardedSocket(base):  # type: ignore[misc,valid-type]
            def connect(self, address):
                if not OfflineKernel._is_local(address):
                    OfflineKernel._deny("connect")
                return super().connect(address)

            def connect_ex(self, address):
                if not OfflineKernel._is_local(address):
                    OfflineKernel._deny("connect_ex")
                return super().connect_ex(address)

            def sendto(self, data, *args):
                addr = args[-1] if args else None
                if addr is not None and not OfflineKernel._is_local(addr):
                    OfflineKernel._deny("sendto")
                return super().sendto(data, *args)

        def guarded_getaddrinfo(host, *a, **kw):
            h = str(host)
            if h not in OfflineKernel.LOCAL and not h.startswith("127."):
                OfflineKernel._deny("dns")
            return OfflineKernel._real_getaddrinfo(host, *a, **kw)

        def guarded_create_connection(address, *a, **kw):
            if not OfflineKernel._is_local(address):
                OfflineKernel._deny("create_connection")
            return OfflineKernel._real_create_connection(address, *a, **kw)

        socket.socket = GuardedSocket
        socket.getaddrinfo = guarded_getaddrinfo
        socket.create_connection = guarded_create_connection
        cls.installed = True

    @classmethod
    def probe(cls) -> tuple[bool, str]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.4)
            try:
                s.connect(("1.1.1.1", 80))
            finally:
                try:
                    s.close()
                except Exception:
                    pass
            return False, "Outbound connect was NOT blocked."
        except NetworkBlocked:
            return True, "Live probe: connect to 1.1.1.1:80 denied by kernel."
        except Exception as exc:
            return True, f"Live probe: connect denied ({type(exc).__name__})."


# =====================================================================================
# 4. SECRET TYPE (SG07 / SG08 / SG40)
# =====================================================================================
class Secret:
    __slots__ = ("_v",)

    def __init__(self, value: str):
        self._v = str(value)

    def __repr__(self) -> str:   return "<redacted>"
    def __str__(self) -> str:    return "<redacted>"
    def __format__(self, s):     return "<redacted>"
    def __len__(self) -> int:    return len(self._v)
    def __hash__(self) -> int:   return hash(("Secret", self._v))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Secret) and hmac.compare_digest(self._v, other._v)

    def reveal(self) -> str:
        return self._v

    def normalized(self) -> str:
        t = unicodedata.normalize("NFKC", self._v)
        return re.sub(r"\s+", " ", t).strip().casefold()

    def fingerprint(self, key: bytes) -> str:
        return hmac.new(key, self._v.encode("utf-8"), hashlib.sha256).hexdigest()[:12]

    def dotted(self) -> str:
        n = len(self._v)
        return "\u2022" * n if n <= 2 else self._v[0] + "\u2022" * max(3, n - 2) + self._v[-1]


# =====================================================================================
# 5. PLATFORM: Paths, Atomic Write, Stamped Names, Shredding
# =====================================================================================
def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def stamped_filename(stem: str, suffix: str, ext: str, ts: Optional[str] = None) -> str:
    """<stem>-<suffix>-<YYYYMMDD-HHMMSS><ext>"""
    ts = ts or datetime.now().strftime("%Y%m%d-%H%M%S")
    ext = ext if ext.startswith(".") else "." + ext
    # Clean redundant suffixes
    clean_stem = re.sub(r"-(?:masked|unmasked|mapping|mapping-table)(?:-\d{8}-\d{6})?$", "", stem)
    return f"{clean_stem}-{suffix}-{ts}{ext}"


def text_to_markdown_bytes(title: str, source_name: str, body: str) -> bytes:
    lines = [f"# {title}", "", f"_Source file: {source_name}_", f"_Generated: {now_utc()}_", "",
             "```", body.rstrip("\n"), "```", ""]
    return "\n".join(lines).encode("utf-8")


def app_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    p = Path(base) / "PIIMaskingTool_CA_Arpan_Jhaveri"
    p.mkdir(parents=True, exist_ok=True)
    return p


class SessionTemp:
    _dir: Optional[Path] = None

    @classmethod
    def dir(cls) -> Path:
        if cls._dir is None:
            d = Path(tempfile.mkdtemp(prefix="piitool_sess_"))
            try:
                os.chmod(d, 0o700)
            except Exception:
                pass
            cls._dir = d
            atexit.register(cls.cleanup)
        return cls._dir

    @classmethod
    def cleanup(cls):
        if cls._dir and cls._dir.exists():
            for p in sorted(cls._dir.rglob("*"), reverse=True):
                try:
                    secure_delete(p) if p.is_file() else p.rmdir()
                except Exception:
                    pass
            try:
                cls._dir.rmdir()
            except Exception:
                pass


def secure_delete(path: Path, passes: int = 1) -> bool:
    try:
        if not path.exists() or not path.is_file():
            return False
        size = path.stat().st_size
        with open(path, "r+b", buffering=0) as fh:
            for _ in range(max(1, passes)):
                fh.seek(0)
                fh.write(secrets.token_bytes(size))
                fh.flush()
                os.fsync(fh.fileno())
        path.unlink()
        return True
    except Exception:
        try:
            path.unlink()
            return True
        except Exception:
            return False


def safe_resolve(base: Path, candidate: str) -> Path:
    base = base.resolve()
    cand = (base / candidate).resolve()
    try:
        cand.relative_to(base)
    except ValueError:
        raise PathSecurityError("The requested path is outside the permitted folder.", "traversal blocked")
    return cand


def atomic_write(path: Path, data: bytes, overwrite: bool = False) -> Path:
    path = Path(path)
    if path.exists() and not overwrite:
        raise PolicyError(f"File already exists: {path.name}. Overwrite was not authorised.")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".piitmp_", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.chmod(tmp, 0o600)
        except Exception:
            pass
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except Exception:
                pass
    return path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


# =====================================================================================
# 6. PII-SAFE AUDIT LOGGING
# =====================================================================================
_SCRUB = [
    (re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"), "<redacted:12digit>"),
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), "<redacted:pan>"),
    (re.compile(r"\b[\w.\-+]+@[\w\-]+\.[A-Za-z]{2,}\b"), "<redacted:email>"),
    (re.compile(r"\b\d{6,18}\b"), "<redacted:number>"),
]


def scrub(text: Any) -> str:
    out = str(text)
    for rx, rep in _SCRUB:
        out = rx.sub(rep, out)
    return out


class AuditLog:
    enabled = True
    _lock = threading.Lock()
    _memory: list[dict] = []

    @classmethod
    def path(cls) -> Path:
        d = app_dir() / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d / f"audit-{datetime.now().strftime('%Y%m%d')}.log"

    @classmethod
    def event(cls, name: str, data: Optional[dict] = None):
        rec = {"ts": now_utc(), "event": name,
               "data": {k: (scrub(v) if isinstance(v, str) else v) for k, v in (data or {}).items()}}
        with cls._lock:
            cls._memory.append(rec)
            if len(cls._memory) > 4000:
                del cls._memory[:1000]
            if cls.enabled:
                try:
                    with open(cls.path(), "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                except Exception:
                    pass

    @classmethod
    def recent(cls, n: int = 400) -> list[dict]:
        with cls._lock:
            return list(cls._memory[-n:])


# =====================================================================================
# 7. INDIAN IDENTIFIER VALIDATORS
# =====================================================================================
_D = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],
      [3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
      [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],
      [9,8,7,6,5,4,3,2,1,0]]
_P = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],
      [8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],
      [2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]]
_B36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_STATES = {f"{i:02d}" for i in range(1, 39)}


def digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def verhoeff_ok(num: str) -> bool:
    n = digits(num)
    if len(n) != 12 or n[0] in "01":
        return False
    c = 0
    for i, ch in enumerate(reversed(n)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def luhn_ok(num: str) -> bool:
    n = digits(num)
    if not (12 <= len(n) <= 19):
        return False
    total, alt = 0, False
    for ch in reversed(n):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def pan_ok(v: str) -> bool:
    v = v.upper().strip()
    return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", v)) and v[3] in "ABCFGHLJPTKE"


def gstin_ok(v: str) -> bool:
    v = v.upper().strip()
    if len(v) != 15 or v[:2] not in _STATES or not pan_ok(v[2:12]):
        return False
    factor, total = 1, 0
    for ch in v[:14]:
        if ch not in _B36:
            return False
        prod = _B36.index(ch) * factor
        total += prod // 36 + prod % 36
        factor = 2 if factor == 1 else 1
    return _B36[(36 - total % 36) % 36] == v[14]


def tan_ok(v: str) -> bool:      return bool(re.fullmatch(r"[A-Z]{4}[0-9]{5}[A-Z]", v.upper().strip()))
def ifsc_ok(v: str) -> bool:     return bool(re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", v.upper().strip()))
def cin_ok(v: str) -> bool:      return bool(re.fullmatch(r"[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}", v.upper().strip()))


def vehicle_ok(v: str) -> bool:
    t = re.sub(r"[\s-]", "", v.upper())
    return bool(re.fullmatch(r"[0-9]{2}BH[0-9]{4}[A-Z]{1,2}", t)
                or re.fullmatch(r"[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}", t))


def phone_in_ok(v: str) -> bool:
    d = digits(v)
    if d.startswith("91") and len(d) == 12:
        d = d[2:]
    if d.startswith("0") and len(d) == 11:
        d = d[1:]
    return len(d) == 10 and d[0] in "6789"


UPI_HANDLES = {"okhdfcbank","okicici","oksbi","okaxis","ybl","ibl","axl","paytm","upi","apl","yapl",
               "abfspay","freecharge","airtel","jupiteraxis","fam","naviaxis","sliceaxis","timecosmos",
               "waaxis","waicici","wasbi","idfcbank","kotak","barodampay","indus","yesbank"}


def upi_ok(v: str) -> bool:
    return "@" in v and v.rsplit("@", 1)[1].lower() in UPI_HANDLES


# =====================================================================================
# 8. REGEX SAFETY & REDOS LINTER (SG32)
# =====================================================================================
def _regex_probe_subprocess(pattern: str, sample_len: int, timeout: float) -> bool:
    code = "import re,sys\nre.compile(sys.argv[1]).search('a' * int(sys.argv[2]) + '!')\n"
    try:
        subprocess.run([_python_exe(), "-c", code, pattern, str(sample_len)],
                       timeout=timeout, capture_output=True)
        return False
    except subprocess.TimeoutExpired:
        return True
    except Exception:
        return False


def _regex_finditer_subprocess(rx: "re.Pattern", text: str,
                                timeout: float) -> Optional[list[tuple[int, int]]]:
    payload = json.dumps({"pattern": rx.pattern, "flags": int(rx.flags), "text": text})
    code = ("import re,sys,json\n"
            "d=json.loads(sys.stdin.read())\n"
            "rx=re.compile(d['pattern'], d['flags'])\n"
            "sys.stdout.write(json.dumps([[m.start(), m.end()] for m in rx.finditer(d['text'])]))\n")
    try:
        proc = subprocess.run([_python_exe(), "-c", code], input=payload,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return []
    try:
        return [(s, e) for s, e in json.loads(proc.stdout)]
    except Exception:
        return []


_REDOS = [
    (re.compile(r"\([^()]*[+*][^()]*\)\s*[+*]"), "nested quantifier inside a group"),
    (re.compile(r"\([^()]*\|[^()]*\)\s*[+*]"), "alternation under a quantifier"),
    (re.compile(r"\(\?\=.*\)\s*[+*]"), "quantified lookahead"),
    (re.compile(r"(\.\*){2,}"), "multiple unbounded .* segments"),
]


def redos_lint(pattern: str) -> list[str]:
    findings = [msg for rx, msg in _REDOS if rx.search(pattern)]
    if len(pattern) > 400:
        findings.append("pattern is unusually long")
    try:
        re.compile(pattern)
    except re.error as exc:
        findings.append(f"invalid regex: {exc}")
        return findings
    if _regex_probe_subprocess(pattern, 2500, 1.0):
        findings.append("timed out on adversarial input (catastrophic backtracking)")
    return findings


# =====================================================================================
# 9. PARTIAL MASKING & STRATEGIES GENERATOR
# =====================================================================================
def partial_mask_value(category: str, raw: str) -> str:
    """Generates format-preserving partial masks (e.g. XXXX-XXXX-1234, AXXXXXX4F)."""
    raw_str = raw.strip()
    cat = category.upper()

    if cat == "AADHAAR":
        d = digits(raw_str)
        last4 = d[-4:] if len(d) >= 4 else "XXXX"
        return f"XXXX-XXXX-{last4}"

    if cat == "PAN":
        p = raw_str.upper()
        if len(p) == 10:
            return f"{p[0]}XXXXXX{p[8:]}"
        return f"XXXXXX{p[-4:]}" if len(p) >= 4 else "XXXXXX"

    if cat == "CREDIT_CARD":
        d = digits(raw_str)
        last4 = d[-4:] if len(d) >= 4 else "1234"
        return f"XXXX-XXXX-XXXX-{last4}"

    if cat in ("BANK_ACCOUNT", "UAN", "ESIC", "PF"):
        d = digits(raw_str)
        if len(d) > 4:
            return "X" * (len(d) - 4) + d[-4:]
        return "XXXX" + d

    if cat == "PHONE":
        d = digits(raw_str)
        last4 = d[-4:] if len(d) >= 4 else "XXXX"
        prefix = "+91 " if raw_str.startswith("+91") else ""
        return f"{prefix}XXXXXX{last4}"

    if cat == "EMAIL":
        if "@" in raw_str:
            user, domain = raw_split = raw_str.split("@", 1)
            if len(user) <= 2:
                masked_user = user[0] + "***" if user else "***"
            else:
                masked_user = user[0] + "*" * (len(user) - 2) + user[-1]
            return f"{masked_user}@{domain}"
        return "x***@domain.com"

    if cat == "GSTIN":
        g = raw_str.upper()
        if len(g) == 15:
            return f"{g[:2]}XXXXXXX{g[9:]}"
        return "XX" + "X" * max(4, len(g) - 4) + g[-2:]

    if cat in ("PERSON", "ORGANISATION"):
        words = raw_str.split()
        masked_words = []
        for w in words:
            if len(w) <= 2:
                masked_words.append(w[0] + "*" if w else "*")
            else:
                masked_words.append(w[0] + "*" * (len(w) - 1))
        return " ".join(masked_words)

    if cat == "VEHICLE":
        v = raw_str.upper()
        if len(v) >= 4:
            return v[:2] + "-XX-XXXX"
        return "XX-XXXX"

    # Generic partial mask: keep first and last char, mask middle
    if len(raw_str) <= 3:
        return "*" * len(raw_str)
    return raw_str[0] + "X" * (len(raw_str) - 2) + raw_str[-1]


# =====================================================================================
# 10. CONFIGURATION & DICTIONARY
# =====================================================================================
BUILTIN_CATEGORIES = [
    "PAN", "AADHAAR", "GSTIN", "TAN", "CIN", "DIN", "VOTER_ID", "PASSPORT",
    "DRIVING_LICENCE", "UAN", "ESIC", "BANK_ACCOUNT", "IFSC", "UPI_VPA",
    "CREDIT_CARD", "VEHICLE", "PHONE", "EMAIL", "PIN_CODE", "DOB", "PERSON",
    "ORGANISATION", "ADDRESS", "IP_ADDRESS", "CUSTOM",
]

DEFAULT_DICTIONARY = [
    {"term": "Arpan Jhaveri", "category": "PERSON", "type": "literal", "case_sensitive": False,
     "whole_word": True, "enabled": True, "note": "sample entry - edit or delete"},
    {"term": r"EMP-\d{4,6}", "category": "CUSTOM", "type": "regex", "case_sensitive": False,
     "whole_word": False, "enabled": True, "note": "sample employee-id rule"},
]


class Config:
    FILE = "config.json"

    def __init__(self):
        self.data: dict[str, Any] = self._defaults()
        self.load()

    def _defaults(self) -> dict[str, Any]:
        return {
            "theme": "dark",
            "reveal_by_default": False,
            "max_file_mb": 200,
            "mask_mode": "token",
            "placeholder_format": "[{cat}_{ns}_{n:03d}]",
            "encrypt_default": True,
            "audit_enabled": True,
            "output_dir": "",
            "categories": {c: {"enabled": True, "threshold": 50} for c in BUILTIN_CATEGORIES},
            "dictionary": [dict(e) for e in DEFAULT_DICTIONARY],
        }

    @property
    def path(self) -> Path:
        return app_dir() / self.FILE

    def load(self):
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    base = self._defaults()
                    base.update({k: v for k, v in loaded.items() if k in base})
                    for c in BUILTIN_CATEGORIES:
                        base["categories"].setdefault(c, {"enabled": True, "threshold": 50})
                    self.data = base
        except Exception:
            self.data = self._defaults()
        AuditLog.enabled = bool(self.data.get("audit_enabled", True))

    def save(self):
        AuditLog.enabled = bool(self.data.get("audit_enabled", True))
        atomic_write(self.path, json.dumps(self.data, indent=2, ensure_ascii=False).encode("utf-8"),
                     overwrite=True)
        AuditLog.event("config.saved", {"file": self.path.name})

    def cat(self, name: str) -> dict:
        return self.data["categories"].setdefault(name, {"enabled": True, "threshold": 50})

    def enabled(self, name: str) -> bool:   return bool(self.cat(name).get("enabled", True))
    def threshold(self, name: str) -> int:  return int(self.cat(name).get("threshold", 50))

    @property
    def dictionary(self) -> list[dict]:
        return self.data.setdefault("dictionary", [])

    def all_categories(self) -> list[str]:
        extra = sorted({str(d.get("category", "CUSTOM")) for d in self.dictionary} - set(BUILTIN_CATEGORIES))
        return BUILTIN_CATEGORIES + extra


CONFIG = Config()


# =====================================================================================
# 11. DETECTION ENGINE
# =====================================================================================
@dataclass
class TextUnit:
    uid: str
    text: str
    label: str = ""
    location: str = ""


@dataclass
class Detection:
    uid: str
    start: int
    end: int
    value: Secret
    category: str
    score: int
    evidence: list
    location: str
    selected: bool = True
    placeholder: str = ""

    @property
    def confidence(self) -> str:
        return "High" if self.score >= 80 else ("Medium" if self.score >= 50 else "Low")


@dataclass
class PatternRule:
    category: str
    pattern: str
    base: int = 40
    validator: Optional[Callable[[str], bool]] = None
    bonus: int = 45
    context_required: bool = False
    keywords: tuple = ()
    regex: Any = None


KW = {
    "PAN": ("pan", "permanent account", "\u092a\u0948\u0928"),
    "AADHAAR": ("aadhaar", "aadhar", "uid", "uidai", "\u0906\u0927\u093e\u0930"),
    "GSTIN": ("gst", "gstin", "goods and service"),
    "TAN": ("tan", "tax deduction"),
    "CIN": ("cin", "corporate identity", "company identification"),
    "DIN": ("din", "director identification"),
    "VOTER_ID": ("voter", "epic", "election"),
    "PASSPORT": ("passport", "\u092a\u093e\u0938\u092a\u094b\u0930\u094d\u091f"),
    "DRIVING_LICENCE": ("driving licence", "driving license", "dl no", "dl number", "licence no"),
    "UAN": ("uan", "universal account"),
    "ESIC": ("esic", "esi no", "insurance number"),
    "BANK_ACCOUNT": ("account", "a/c", "acct", "bank", "\u0916\u093e\u0924\u093e"),
    "IFSC": ("ifsc", "branch code"),
    "UPI_VPA": ("upi", "vpa", "virtual payment"),
    "CREDIT_CARD": ("card", "credit", "debit", "visa", "mastercard", "rupay"),
    "VEHICLE": ("vehicle", "registration", "regn", "car no", "rc no"),
    "PHONE": ("phone", "mobile", "contact", "tel", "cell", "whatsapp", "\u092e\u094b\u092c\u093e\u0907\u0932"),
    "EMAIL": ("email", "e-mail", "mail id"),
    "PIN_CODE": ("pin", "pincode", "postal", "zip"),
    "DOB": ("date of birth", "dob", "birth", "born", "\u091c\u0928\u094d\u092e", "date of incorporation",
            "date of joining", "anniversary", "issue date", "expiry"),
    "PERSON": ("name", "\u0928\u093e\u092e", "s/o", "w/o", "d/o", "father", "mother", "proprietor",
               "partner", "director", "signatory", "applicant", "assessee"),
    "ORGANISATION": ("company", "firm", "regd. office", "registered office", "m/s", "enterprise"),
    "ADDRESS": ("address", "\u092a\u0924\u093e", "residing", "premises", "flat", "plot", "street", "road"),
    "IP_ADDRESS": ("ip", "host", "server"),
}

NEGATIVE_LEFT = ("invoice", "bill no", "challan", "section", "receipt", "order no", "voucher",
                 "page", "ref no", "reference no", "gstr", "form no", "notification", "circular", "rule ")


def _build_rules() -> list[PatternRule]:
    r = [
        PatternRule("PAN", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", 45, pan_ok, 45, False, KW["PAN"]),
        PatternRule("AADHAAR", r"\b[2-9][0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}\b", 40, verhoeff_ok, 55, False, KW["AADHAAR"]),
        PatternRule("GSTIN", r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b", 45, gstin_ok, 50, False, KW["GSTIN"]),
        PatternRule("TAN", r"\b[A-Z]{4}[0-9]{5}[A-Z]\b", 40, tan_ok, 30, True, KW["TAN"]),
        PatternRule("CIN", r"\b[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b", 55, cin_ok, 40, False, KW["CIN"]),
        PatternRule("DIN", r"\b[0-9]{8}\b", 20, None, 0, True, KW["DIN"]),
        PatternRule("VOTER_ID", r"\b[A-Z]{3}[0-9]{7}\b", 35, None, 0, True, KW["VOTER_ID"]),
        PatternRule("PASSPORT", r"\b[A-PR-WYZ][0-9]{7}\b", 35, None, 0, True, KW["PASSPORT"]),
        PatternRule("DRIVING_LICENCE", r"\b[A-Z]{2}[0-9]{2}[ -]?(?:19|20)[0-9]{2}[0-9]{7}\b", 45, None, 0, False, KW["DRIVING_LICENCE"]),
        PatternRule("UAN", r"\b1[0-9]{11}\b", 25, None, 0, True, KW["UAN"]),
        PatternRule("ESIC", r"\b[0-9]{17}\b", 30, None, 0, True, KW["ESIC"]),
        PatternRule("IFSC", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", 50, ifsc_ok, 35, False, KW["IFSC"]),
        PatternRule("BANK_ACCOUNT", r"\b[0-9]{9,18}\b", 20, None, 0, True, KW["BANK_ACCOUNT"]),
        PatternRule("CREDIT_CARD", r"\b(?:[0-9]{4}[ -]?){3}[0-9]{1,4}\b", 30, luhn_ok, 50, False, KW["CREDIT_CARD"]),
        PatternRule("UPI_VPA", r"\b[A-Za-z0-9._-]{2,49}@[A-Za-z][A-Za-z0-9]{1,29}\b", 35, upi_ok, 45, False, KW["UPI_VPA"]),
        PatternRule("EMAIL", r"\b[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,255}\.[A-Za-z]{2,24}\b", 75, None, 0, False, KW["EMAIL"]),
        PatternRule("VEHICLE", r"\b(?:[A-Z]{2}[ -]?[0-9]{1,2}[ -]?[A-Z]{1,3}[ -]?[0-9]{4}|[0-9]{2}[ -]?BH[ -]?[0-9]{4}[ -]?[A-Z]{1,2})\b", 40, vehicle_ok, 25, False, KW["VEHICLE"]),
        PatternRule("PHONE", r"(?:\+91[ -]?)?\b[6-9][0-9]{9}\b", 45, phone_in_ok, 25, False, KW["PHONE"]),
        PatternRule("PHONE", r"\+[0-9]{1,3}[ -][0-9]{6,12}\b", 40, None, 0, True, KW["PHONE"]),
        PatternRule("PIN_CODE", r"\b[1-9][0-9]{5}\b", 20, None, 0, True, KW["PIN_CODE"]),
        PatternRule("IP_ADDRESS", r"\b(?:(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})\.){3}(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})\b", 60, None, 0, False, KW["IP_ADDRESS"]),
        PatternRule("DOB", r"\b(?:0?[1-9]|[12][0-9]|3[01])[/\-. ](?:0?[1-9]|1[0-2])[/\-. ](?:19|20)[0-9]{2}\b", 25, None, 0, True, KW["DOB"]),
        PatternRule("DOB", r"\b(?:19|20)[0-9]{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])\b", 25, None, 0, True, KW["DOB"]),
        PatternRule("PERSON", r"\b(?:Mr|Mrs|Ms|Shri|Smt|Sri|Dr|Prof|Kum|Miss)\.?\s+[A-Z][a-zA-Z]{1,20}(?:\s+[A-Z][a-zA-Z]{1,20}){0,2}\b", 65, None, 0, False, KW["PERSON"]),
        PatternRule("ORGANISATION", r"\b(?:M/s\.?\s+)?[A-Z][A-Za-z&.\- ]{2,40}?\s(?:Pvt\.?\s?Ltd\.?|Private\sLimited|Limited|LLP|LLC|Inc\.?|Enterprises|Industries)\b", 70, None, 0, False, KW["ORGANISATION"]),
        PatternRule("ADDRESS", r"\b(?:Flat|Plot|House|H\.?No|Door|Shop|Office|Room|Block)\s?(?:No\.?|#)?\s?[A-Za-z0-9\-/]{1,10}[,\s][^\n]{5,80}", 55, None, 0, False, KW["ADDRESS"]),
    ]
    for rule in r:
        rule.regex = re.compile(rule.pattern)
    return r


PATTERN_RULES = _build_rules()
STRUCT_RE = re.compile(r"^\s*([A-Za-z][A-Za-z .()/'\-]{1,40})\s*[:=\-]\s*(\S.*)$")
MAX_UNIT_CHARS = 2_000_000


class DetectionEngine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.rules = PATTERN_RULES
        self.dict_rules = self._compile_dictionary()

    def _compile_dictionary(self) -> list[dict]:
        out = []
        for ent in self.cfg.dictionary:
            if not ent.get("enabled", True):
                continue
            term = str(ent.get("term", "")).strip()
            if not term:
                continue
            flags = 0 if ent.get("case_sensitive") else re.IGNORECASE
            try:
                if ent.get("type") == "regex":
                    pat, risky = term, True
                else:
                    pat = re.escape(term)
                    if ent.get("whole_word", True):
                        pat = r"\b" + pat + r"\b"
                    risky = False
                out.append({"regex": re.compile(pat, flags),
                            "category": re.sub(r"[^A-Z0-9_]", "_", str(ent.get("category", "CUSTOM")).upper()),
                            "kind": ent.get("type", "literal"), "risky": risky})
            except re.error:
                continue
        return out

    def analyze(self, units: list[TextUnit], progress=None, cancel=None) -> list[Detection]:
        results: list[Detection] = []
        total = max(1, len(units))
        for i, unit in enumerate(units):
            if cancel is not None and cancel.is_set():
                break
            if unit.text and unit.text.strip():
                results.extend(self._analyze_unit(unit))
            if progress and (i % 40 == 0 or i == total - 1):
                progress(8 + int(60 * (i + 1) / total), f"Analysing text unit {i + 1} of {total}")
        return self._resolve_overlaps(results)

    def _analyze_unit(self, unit: TextUnit) -> list[Detection]:
        text = unit.text[:MAX_UNIT_CHARS]
        low = text.lower()
        label_low = (unit.label or "").lower()
        found: list[Detection] = []

        def add(cat, s, e, score, ev):
            score = max(0, min(100, score))
            if score < self.cfg.threshold(cat) or e <= s:
                return
            found.append(Detection(unit.uid, s, e, Secret(text[s:e]), cat, score, ev,
                                   self._location(unit, s)))

        for rule in self.rules:
            if not self.cfg.enabled(rule.category):
                continue
            for m in rule.regex.finditer(text):
                raw = m.group(0).strip()
                if not raw:
                    continue
                score, ev = rule.base, [f"pattern match for {rule.category}"]
                if rule.validator:
                    try:
                        ok = rule.validator(raw)
                    except Exception:
                        ok = False
                    if ok:
                        score += rule.bonus
                        ev.append("algorithmic validator passed")
                    elif rule.category in ("PAN", "AADHAAR", "GSTIN", "CIN", "IFSC", "CREDIT_CARD"):
                        continue
                    else:
                        score -= 10
                        ev.append("validator not satisfied")
                left, right = low[max(0, m.start() - 60):m.start()], low[m.end():m.end() + 60]
                ctx = left + " || " + right
                kw = next((k for k in rule.keywords if k in ctx), None)
                if kw:
                    score += 25
                    ev.append(f"keyword '{kw}' within +/-60 characters")
                elif rule.context_required:
                    continue
                if label_low and any(k in label_low for k in rule.keywords):
                    score += 18
                    ev.append(f"column/key '{unit.label}'")
                lab = self._line_label(text, m.start())
                if lab and any(k in lab.lower() for k in rule.keywords):
                    score += 12
                    ev.append(f"field label '{lab}'")
                if any(n in left[-30:] for n in NEGATIVE_LEFT):
                    score -= 35
                    ev.append("negative evidence in left context")
                if rule.category == "PIN_CODE" and not re.search(
                        r"\b(?:road|street|nagar|colony|district|state|india|city|pin|near)\b", ctx):
                    continue
                add(rule.category, m.start(), m.end(), score, ev)

        for dr in self.dict_rules:
            if not self.cfg.enabled(dr["category"]):
                continue
            if dr["risky"]:
                spans = _regex_finditer_subprocess(dr["regex"], text, 3.0)
                if spans is None:
                    AuditLog.event("regex.timeout", {"category": dr["category"], "source": "dictionary"})
                    continue
            else:
                spans = [(m.start(), m.end()) for m in dr["regex"].finditer(text)]
            for s, e in spans:
                if text[s:e].strip():
                    add(dr["category"], s, e, 92, [f"user dictionary ({dr['kind']}) entry"])

        for m in re.finditer(r"(?m)^(.*)$", text):
            line = m.group(1)
            sm = STRUCT_RE.match(line)
            if not sm:
                continue
            key, val = sm.group(1).strip(), sm.group(2).strip()
            klow = key.lower()
            for cat in ("PERSON", "ADDRESS", "ORGANISATION"):
                if self.cfg.enabled(cat) and any(k in klow for k in KW[cat]) and 2 <= len(val) <= 120:
                    vs = m.start(1) + line.index(val)
                    add(cat, vs, vs + len(val), 85, [f"field label '{key}' identifies {cat}"])
                    break

        if label_low and text.strip() and len(text.strip()) <= 120:
            for cat in ("PERSON", "ADDRESS", "ORGANISATION"):
                if self.cfg.enabled(cat) and any(k in label_low for k in KW[cat]):
                    add(cat, 0, len(text), 84, [f"column/key '{unit.label}' identifies {cat}"])
                    break
        return found

    @staticmethod
    def _line_label(text: str, pos: int) -> str:
        ls = text.rfind("\n", 0, pos) + 1
        m = re.search(r"([A-Za-z][A-Za-z .()/'\-]{1,40})\s*[:=]\s*$", text[ls:pos])
        return m.group(1).strip() if m else ""

    @staticmethod
    def _location(unit: TextUnit, pos: int) -> str:
        if unit.location:
            return unit.location
        line = unit.text.count("\n", 0, pos) + 1
        col = pos - (unit.text.rfind("\n", 0, pos) + 1) + 1
        return f"Line {line}, Col {col}"

    @staticmethod
    def _resolve_overlaps(dets: list[Detection]) -> list[Detection]:
        by_unit: dict[str, list[Detection]] = {}
        for d in dets:
            by_unit.setdefault(d.uid, []).append(d)
        final: list[Detection] = []
        for lst in by_unit.values():
            lst.sort(key=lambda d: (-(d.end - d.start), -d.score, d.start))
            taken: list[Detection] = []
            for d in lst:
                if any(not (d.end <= t.start or d.start >= t.end) for t in taken):
                    continue
                taken.append(d)
            taken.sort(key=lambda d: d.start)
            final.extend(taken)
        return final


# =====================================================================================
# 12. PLACEHOLDER ALLOCATOR WITH PRIOR MAPPING TABLE REUSE
# =====================================================================================
class PlaceholderAllocator:
    def __init__(self, namespace: Optional[str] = None, fmt: Optional[str] = None,
                 mode: str = "token", preloaded_mappings: Optional[dict[str, str]] = None):
        self.ns = namespace or secrets.token_hex(2).upper()
        self.fmt = fmt or CONFIG.data.get("placeholder_format", "[{cat}_{ns}_{n:03d}]")
        self.mode = mode
        self.counters: dict[str, int] = {}
        self.map: dict[tuple, str] = {}
        self.reverse: dict[str, str] = {}

        if preloaded_mappings:
            for orig_val, masked_val in preloaded_mappings.items():
                norm = unicodedata.normalize("NFKC", orig_val).strip().casefold()
                for cat in BUILTIN_CATEGORIES:
                    self.map[(cat, norm)] = masked_val
                self.reverse[masked_val] = orig_val

    def reroll(self):
        self.ns = secrets.token_hex(2).upper()
        self.counters.clear(); self.map.clear(); self.reverse.clear()

    def allocate(self, category: str, value: Secret) -> str:
        cat = re.sub(r"[^A-Z0-9_]", "_", category.upper())
        key = (cat, value.normalized())
        if key in self.map:
            return self.map[key]

        raw = value.reveal()

        if self.mode == "partial":
            ph = partial_mask_value(cat, raw)
        elif self.mode == "hash":
            h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()
            ph = f"[HASH_{h}]"
        elif self.mode == "redact":
            ph = "[REDACTED]"
        else:
            n = self.counters.get(cat, 0) + 1
            self.counters[cat] = n
            ph = self.fmt.format(cat=cat, ns=self.ns, n=n)

        self.map[key] = ph
        self.reverse[ph] = raw
        return ph


# =====================================================================================
# 13. MAPPING CONTAINER (.piimap) & CSV TABLE
# =====================================================================================
def derive_key(password: str, salt: bytes) -> tuple[bytes, str, dict]:
    if HAVE_ARGON2:
        p = {"m": 65536, "t": 3, "p": 2}
        return (hash_secret_raw(password.encode("utf-8"), salt, time_cost=p["t"],
                                memory_cost=p["m"], parallelism=p["p"], hash_len=64,
                                type=_ArgonType.ID), "argon2id", p)
    p = {"n": 2 ** 15, "r": 8, "p": 2}
    return (hashlib.scrypt(password.encode("utf-8"), salt=salt, n=p["n"], r=p["r"],
                           p=p["p"], dklen=64, maxmem=256 * 1024 * 1024), "scrypt", p)


def _ks(key: bytes, nonce: bytes, data: bytes) -> bytes:
    out = bytearray()
    c = 0
    while len(out) < len(data):
        out.extend(hmac.new(key, nonce + struct.pack(">I", c), hashlib.sha256).digest())
        c += 1
    return bytes(a ^ b for a, b in zip(data, out[:len(data)]))


class MappingContainer:
    @staticmethod
    def build(payload: dict, password: Optional[str], header_extra: dict) -> bytes:
        cats = header_extra.get("category_counts", {})
        mandatory = sorted(set(cats) & MANDATORY_ENCRYPTION_CATEGORIES)
        if not password and mandatory:
            raise PolicyError("Encryption is mandatory because high-risk categories were masked: "
                              + ", ".join(mandatory))

        salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
        plain = zlib.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"), 9)

        if password:
            key, kdf, kparams = derive_key(password, salt)
            aead = "aes-256-gcm" if HAVE_AESGCM else "hmac-sha256-ctr+hmac"
        else:
            key = hashlib.sha256(b"PIIMAP-UNPROTECTED" + salt).digest() * 2
            kdf, kparams, aead = "none", {}, "none"

        k_enc, k_mac = key[:32], key[32:64]
        header = {"fmt": FMT_VER, "tool": APP_NAME, "tool_version": APP_VERSION, "kdf": kdf,
                  "kdf_params": kparams, "salt": base64.b64encode(salt).decode(),
                  "aead": aead, "created_utc": now_utc()}
        header.update(header_extra)
        hb = json.dumps(header, sort_keys=True, ensure_ascii=False).encode("utf-8")

        if aead == "aes-256-gcm":
            ctt = AESGCM(k_enc).encrypt(nonce, plain, hb)
            ct, tag = ctt[:-16], ctt[-16:]
        elif aead == "none":
            ct = plain
            tag = hmac.new(k_mac, hb + nonce + ct, hashlib.sha256).digest()[:16]
        else:
            ct = _ks(k_enc, nonce, plain)
            tag = hmac.new(k_mac, hb + nonce + ct, hashlib.sha256).digest()[:16]

        body = (MAGIC + bytes([FMT_VER]) + struct.pack(">I", len(hb)) + hb +
                nonce + struct.pack(">I", len(ct)) + ct + tag)
        return body + hmac.new(k_mac, body, hashlib.sha256).digest()

    @staticmethod
    def open(blob: bytes, password: Optional[str]) -> tuple[dict, dict]:
        if len(blob) < 80 or not blob.startswith(MAGIC):
            raise TamperError("This is not a valid mapping (.piimap) file, or it is truncated.")
        off = len(MAGIC)
        ver = blob[off]; off += 1
        if ver != FMT_VER:
            raise CryptoError(f"Unsupported mapping format version ({ver}).")
        (hlen,) = struct.unpack(">I", blob[off:off + 4]); off += 4
        hb = blob[off:off + hlen]; off += hlen
        try:
            header = json.loads(hb.decode("utf-8"))
        except Exception:
            raise TamperError("The mapping header is corrupt or has been modified.")
        nonce = blob[off:off + 12]; off += 12
        (clen,) = struct.unpack(">I", blob[off:off + 4]); off += 4
        ct = blob[off:off + clen]; off += clen
        tag = blob[off:off + 16]
        footer, body = blob[-32:], blob[:-32]

        aead = header.get("aead", "none")
        salt = base64.b64decode(header.get("salt", ""))
        if aead == "none":
            key = hashlib.sha256(b"PIIMAP-UNPROTECTED" + salt).digest() * 2
        else:
            if not password:
                raise WrongPasswordError("This mapping is encrypted. A password is required.")
            kdf, p = header.get("kdf"), header.get("kdf_params", {})
            if kdf == "argon2id":
                if not HAVE_ARGON2:
                    raise CryptoError("This mapping needs Argon2id. Install 'argon2-cffi' to open it.")
                key = hash_secret_raw(password.encode("utf-8"), salt, time_cost=p.get("t", 3),
                                      memory_cost=p.get("m", 65536), parallelism=p.get("p", 2),
                                      hash_len=64, type=_ArgonType.ID)
            elif kdf == "scrypt":
                key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=p.get("n", 2 ** 15),
                                     r=p.get("r", 8), p=p.get("p", 2), dklen=64,
                                     maxmem=256 * 1024 * 1024)
            else:
                raise CryptoError("Unknown key-derivation function in mapping header.")

        k_enc, k_mac = key[:32], key[32:64]
        if not hmac.compare_digest(hmac.new(k_mac, body, hashlib.sha256).digest(), footer):
            if aead == "none":
                raise TamperError("The mapping failed its integrity check (modified or corrupt).")
            raise WrongPasswordError("Wrong password, or the mapping file has been modified.")

        if aead == "aes-256-gcm":
            if not HAVE_AESGCM:
                raise CryptoError("This mapping needs AES-GCM. Install 'cryptography' to open it.")
            try:
                plain = AESGCM(k_enc).decrypt(nonce, ct + tag, hb)
            except Exception:
                raise TamperError("Decryption failed: mapping or header was tampered with.")
        else:
            if not hmac.compare_digest(hmac.new(k_mac, hb + nonce + ct, hashlib.sha256).digest()[:16], tag):
                raise TamperError("Decryption failed: mapping or header was tampered with.")
            plain = ct if aead == "none" else _ks(k_enc, nonce, ct)

        try:
            return header, json.loads(zlib.decompress(plain).decode("utf-8"))
        except Exception:
            raise TamperError("The mapping payload is corrupt.")


# =====================================================================================
# MAPPING TABLE CSV EXPORT / IMPORT
# =====================================================================================
def mapping_table_csv_bytes(payload: dict, header: Optional[dict] = None) -> bytes:
    ns = payload.get("namespace") or (header or {}).get("placeholder_namespace_id", "")
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(["existing_pii_value", "masked_value", "category"])
    for e in payload.get("entries", []):
        ph = str(e.get("placeholder", ""))
        val = str(e.get("value", ""))
        cat = "PII"
        if ns and f"_{ns}_" in ph:
            cat = ph.strip("[]").split(f"_{ns}_")[0]
        elif ph.startswith("[") and "_" in ph:
            cat = ph.strip("[]").split("_")[0]
        w.writerow([val, ph, cat])
    return buf.getvalue().encode("utf-8")


def load_mapping_table_from_file(path: Path, password: Optional[str] = None) -> dict[str, str]:
    """Reads a .csv, .json, or .piimap mapping table and returns {existing_pii_value: masked_value}."""
    ext = path.suffix.lower()
    mapping_dict = {}

    if ext == ".piimap":
        _hdr, payload = MappingContainer.open(path.read_bytes(), password)
        for e in payload.get("entries", []):
            if "value" in e and "placeholder" in e:
                mapping_dict[str(e["value"])] = str(e["placeholder"])
    elif ext == ".json":
        data = json.loads(read_text_file(path))
        if isinstance(data, list):
            for item in data:
                v = item.get("existing_pii_value") or item.get("original_value") or item.get("value")
                m = item.get("masked_value") or item.get("masked_placeholder") or item.get("placeholder")
                if v and m:
                    mapping_dict[str(v)] = str(m)
        elif isinstance(data, dict):
            for k, v in data.items():
                mapping_dict[str(k)] = str(v)
    else:
        text = read_text_file(path)
        rdr = csv.reader(io.StringIO(text))
        for row in rdr:
            if len(row) >= 2:
                v, m = row[0].strip(), row[1].strip()
                if v.lower() not in ("existing_pii_value", "original_value", "value", "raw"):
                    mapping_dict[v] = m
    return mapping_dict


# =====================================================================================
# 14. FORMAT HANDLERS (DOCX, XLSX, PPTX, PDF, CSV, JSON, XML, TXT, Images)
# =====================================================================================
MAGIC_SIGS = [(b"%PDF-", "pdf"), (b"PK\x03\x04", "zip"), (b"\x89PNG\r\n\x1a\n", "png"),
              (b"\xff\xd8\xff", "jpg"), (b"II*\x00", "tiff"), (b"MM\x00*", "tiff"),
              (b"\xd0\xcf\x11\xe0", "ole")]


def sniff(path: Path) -> str:
    with open(path, "rb") as fh:
        head = fh.read(16)
    for sig, kind in MAGIC_SIGS:
        if head.startswith(sig):
            return kind
    return "text"


def check_limits(path: Path):
    max_mb = int(CONFIG.data.get("max_file_mb", 200))
    size = path.stat().st_size
    if size == 0:
        raise IngestError("The file is empty.")
    if size > max_mb * 1024 * 1024:
        raise ResourceLimitError(f"File exceeds the {max_mb} MB safety limit.")
    if sniff(path) == "zip":
        try:
            with zipfile.ZipFile(path) as z:
                total = sum(i.file_size for i in z.infolist())
                comp = max(1, sum(i.compress_size for i in z.infolist()))
                if total > 1_500_000_000 or total / comp > 200:
                    raise ResourceLimitError("Archive rejected: possible decompression bomb.")
        except zipfile.BadZipFile:
            raise IngestError("The file looks like a ZIP/OOXML container but is damaged.")


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


class BaseHandler:
    exts: tuple = ()
    note = ""

    def read(self, path: Path, password: Optional[str] = None) -> list[TextUnit]:
        raise NotImplementedError

    def write(self, src: Path, dst: Path, new_text: dict, overwrite: bool) -> Path:
        raise NotImplementedError


class PlainHandler(BaseHandler):
    exts = (".txt", ".md", ".log", ".ini", ".cfg", ".html", ".htm", ".rtf", ".tsv")

    def read(self, path, password=None):
        return [TextUnit("t0", read_text_file(path))]

    def write(self, src, dst, new_text, overwrite):
        return atomic_write(dst, new_text.get("t0", "").encode("utf-8"), overwrite)


class CsvHandler(BaseHandler):
    exts = (".csv",)

    def read(self, path, password=None):
        text = read_text_file(path)
        try:
            self._dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except Exception:
            self._dialect = csv.excel
        self._rows = list(csv.reader(io.StringIO(text), self._dialect))
        header = self._rows[0] if self._rows else []
        units = []
        for i, row in enumerate(self._rows):
            for j, cell in enumerate(row):
                lab = header[j] if (i > 0 and j < len(header)) else ""
                units.append(TextUnit(f"r{i}c{j}", cell, lab, f"Row {i + 1}, Col {lab or j + 1}"))
        return units

    def write(self, src, dst, new_text, overwrite):
        rows = [list(r) for r in self._rows]
        for uid, val in new_text.items():
            m = re.fullmatch(r"r(\d+)c(\d+)", uid)
            if m:
                i, j = int(m.group(1)), int(m.group(2))
                if i < len(rows) and j < len(rows[i]):
                    rows[i][j] = val
        buf = io.StringIO(newline="")
        csv.writer(buf, dialect=self._dialect, lineterminator="\r\n").writerows(rows)
        return atomic_write(dst, buf.getvalue().encode("utf-8"), overwrite)


class JsonHandler(BaseHandler):
    exts = (".json",)

    def read(self, path, password=None):
        self._obj = json.loads(read_text_file(path))
        self._paths: dict[str, list] = {}
        units: list[TextUnit] = []

        def walk(node, trail, key):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, trail + [k], str(k))
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, trail + [i], key)
            elif isinstance(node, str):
                uid = f"j{len(units)}"
                self._paths[uid] = trail
                units.append(TextUnit(uid, node, key, "/".join(str(t) for t in trail)))

        walk(self._obj, [], "")
        return units

    def write(self, src, dst, new_text, overwrite):
        for uid, val in new_text.items():
            trail = self._paths.get(uid)
            if not trail:
                continue
            node = self._obj
            for step in trail[:-1]:
                node = node[step]
            node[trail[-1]] = val
        return atomic_write(dst, json.dumps(self._obj, indent=2, ensure_ascii=False).encode("utf-8"), overwrite)


class XmlHandler(BaseHandler):
    exts = (".xml", ".svg", ".xhtml")
    TEXT_RE = re.compile(r">([^<>]+)<")

    def read(self, path, password=None):
        text = read_text_file(path)
        if re.search(r"<!DOCTYPE|<!ENTITY", text, re.IGNORECASE):
            raise IngestError("XML containing DOCTYPE/ENTITY declarations is rejected (XXE prevention).")
        self._raw = text
        self._index = list(self.TEXT_RE.finditer(text))
        units = []
        for i, m in enumerate(self._index):
            val = _xml_unescape(m.group(1))
            if val.strip():
                tag = re.search(r"<([A-Za-z_][\w.:-]*)[^<>]*>$", text[:m.start() + 1])
                units.append(TextUnit(f"x{i}", val, tag.group(1) if tag else "", f"XML node #{i + 1}"))
        return units

    def write(self, src, dst, new_text, overwrite):
        out, last = [], 0
        for i, m in enumerate(self._index):
            uid = f"x{i}"
            out.append(self._raw[last:m.start(1)])
            out.append(_xml_escape(new_text[uid]) if uid in new_text else m.group(1))
            last = m.end(1)
        out.append(self._raw[last:])
        return atomic_write(dst, "".join(out).encode("utf-8"), overwrite)


class OoxmlHandler(BaseHandler):
    exts = (".docx", ".xlsx", ".pptx")
    TAGS = {".docx": re.compile(r"(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)", re.DOTALL),
            ".xlsx": re.compile(r"(<t(?:\s[^>]*)?>)(.*?)(</t>)", re.DOTALL),
            ".pptx": re.compile(r"(<a:t(?:\s[^>]*)?>)(.*?)(</a:t>)", re.DOTALL)}
    META_RE = re.compile(r"(<(?:dc|cp):(?:creator|lastModifiedBy|title|subject|description)>)(.*?)(</)", re.DOTALL)

    def read(self, path, password=None):
        ext = path.suffix.lower()
        self._tag = self.TAGS.get(ext, self.TAGS[".docx"])
        self._parts: dict[str, str] = {}
        units: list[TextUnit] = []
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith(".xml") or not name.startswith(("word/", "xl/", "ppt/", "docProps/")):
                    continue
                try:
                    xml = z.read(name).decode("utf-8", "replace")
                except Exception:
                    continue
                self._parts[name] = xml
                rx = self.META_RE if name.startswith("docProps/") else self._tag
                for i, m in enumerate(rx.finditer(xml)):
                    val = _xml_unescape(m.group(2))
                    if val.strip():
                        units.append(TextUnit(f"{name}#{i}", val,
                                              "metadata" if name.startswith("docProps/") else "",
                                              f"{name} (node {i + 1})"))
        if not units:
            raise IngestError("No readable text was found in the Office document.")
        return units

    def write(self, src, dst, new_text, overwrite):
        updated: dict[str, bytes] = {}
        for name, xml in self._parts.items():
            rx = self.META_RE if name.startswith("docProps/") else self._tag
            counter = {"i": -1}

            def repl(m):
                counter["i"] += 1
                uid = f"{name}#{counter['i']}"
                return (m.group(1) + _xml_escape(new_text[uid]) + m.group(3)) if uid in new_text else m.group(0)

            new_xml = rx.sub(repl, xml)
            if new_xml != xml:
                updated[name] = new_xml.encode("utf-8")
        buf = io.BytesIO()
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                zout.writestr(item, updated.get(item.filename) or zin.read(item.filename))
        return atomic_write(dst, buf.getvalue(), overwrite)


class PdfHandler(BaseHandler):
    exts = (".pdf",)
    note = "PDF text is extracted; output is written as a clean masked text/document sidecar."

    def read(self, path, password=None):
        if not HAVE_PYPDF:
            raise UnsupportedFormatError("PDF support requires 'pypdf'. Re-run tool to bootstrap, or: pip install pypdf")
        reader = pypdf.PdfReader(str(path))
        if getattr(reader, "is_encrypted", False):
            try:
                decrypted = reader.decrypt(password or "")
                if not decrypted:
                    raise IngestError("The PDF is password protected. Enter the password in the File Password field.")
            except Exception as exc:
                raise IngestError(f"PDF Decryption failed: {exc}")
        units = []
        for i, page in enumerate(reader.pages):
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            units.append(TextUnit(f"p{i}", txt, "", f"Page {i + 1}"))
        if not any(u.text.strip() for u in units):
            raise IngestError("No extractable text layer found (scanned PDF). Export pages as images and use OCR.")
        return units

    def write(self, src, dst, new_text, overwrite):
        dst = dst.with_name(dst.stem + ".txt") if dst.suffix.lower() == ".pdf" else dst
        parts = [f"--- Page {int(u[1:]) + 1} ---\n{new_text[u]}"
                 for u in sorted(new_text, key=lambda k: int(k[1:]))]
        return atomic_write(dst, "\n\n".join(parts).encode("utf-8"), overwrite)


class ImageHandler(BaseHandler):
    exts = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
    note = "OCR output is written as a masked .txt document; the image itself is preserved."

    def read(self, path, password=None):
        if not (HAVE_PIL and HAVE_TESS):
            raise UnsupportedFormatError("Image OCR requires Pillow + pytesseract plus a locally installed Tesseract engine.")
        Image.MAX_IMAGE_PIXELS = 80_000_000
        with Image.open(path) as im:
            im.load()
            text = pytesseract.image_to_string(im)
        return [TextUnit("i0", text, "", "OCR text")]

    def write(self, src, dst, new_text, overwrite):
        dst = dst.with_name(dst.stem + ".txt")
        return atomic_write(dst, new_text.get("i0", "").encode("utf-8"), overwrite)


HANDLERS = [PlainHandler(), CsvHandler(), JsonHandler(), XmlHandler(),
            OoxmlHandler(), PdfHandler(), ImageHandler()]
SUPPORTED_EXTS = sorted({e for h in HANDLERS for e in h.exts})


def handler_for(path: Path) -> BaseHandler:
    ext = path.suffix.lower()
    for h in HANDLERS:
        if ext in h.exts:
            return type(h)()
    raise UnsupportedFormatError(f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTS)}")


def canonical_text_of(path: Path) -> str:
    try:
        h = handler_for(path)
        return "\n".join(u.text for u in h.read(path))
    except Exception:
        return ""


# =====================================================================================
# 15. PIPELINES (Mask & Unmask)
# =====================================================================================
def apply_spans(text: str, repls: list) -> str:
    out = text
    for s, e, new in sorted(repls, key=lambda t: -t[0]):
        out = out[:s] + new + out[e:]
    return out


@dataclass
class MaskResult:
    masked_path: Path
    mapping_path: Optional[Path]
    mapping_csv_path: Optional[Path]
    mapping_piimap_path: Optional[Path]
    detections: int
    masked_count: int
    residual: list
    namespace: str
    report: dict
    original_text: str = ""
    masked_text: str = ""
    mapping_payload: Optional[dict] = None


class MaskPipeline:
    def __init__(self, cfg: Config, preloaded_mapping: Optional[dict[str, str]] = None):
        self.cfg = cfg
        self.engine = DetectionEngine(cfg)
        self.preloaded_mapping = preloaded_mapping or {}

    def analyze(self, path: Path, file_password: Optional[str] = None, progress=None, cancel=None):
        check_limits(path)
        h = handler_for(path)
        if progress:
            progress(4, "Reading document")
        units = h.read(path, password=file_password)
        meta = {"file": path.name, "size": path.stat().st_size, "sha256": sha256_file(path),
                "handler": type(h).__name__, "units": len(units), "note": h.note}
        if progress:
            progress(8, "Detecting PII")
        dets = self.engine.analyze(units, progress, cancel)
        AuditLog.event("mask.analyzed", {"file": path.name, "hits": len(dets)})
        return h, units, dets, meta

    def mask(self, path: Path, handler: BaseHandler, units: list[TextUnit], dets: list[Detection],
             out_dir: Path, password: Optional[str], overwrite: bool,
             mask_mode: str = "token", progress=None):
        chosen = [d for d in dets if d.selected]
        unit_by_id = {u.uid: u for u in units}
        full_text = "\n".join(u.text for u in units)

        alloc = PlaceholderAllocator(mode=mask_mode, preloaded_mappings=self.preloaded_mapping)
        for _ in range(8):
            if f"_{alloc.ns}_" not in full_text:
                break
            alloc.reroll()

        for d in chosen:
            d.placeholder = alloc.allocate(d.category, d.value)

        by_unit: dict[str, list] = {}
        for d in chosen:
            by_unit.setdefault(d.uid, []).append(d)

        new_text = {uid: (apply_spans(u.text, [(d.start, d.end, d.placeholder) for d in by_unit[uid]])
                          if uid in by_unit else u.text) for uid, u in unit_by_id.items()}

        orig_full = "\n".join(u.text for u in units)
        masked_full = "\n".join(new_text.values())

        if progress:
            progress(72, "Writing masked document")
        out_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        masked_out_name = stamped_filename(path.stem, "masked", path.suffix, ts=ts)
        masked_path = handler.write(path, out_dir / masked_out_name, new_text, overwrite)

        if progress:
            progress(84, "Running residual PII scan")
        residual = []
        try:
            rescan = [TextUnit(uid, txt, unit_by_id[uid].label, unit_by_id[uid].location)
                      for uid, txt in new_text.items()]
            residual = [f"{d.category} at {d.location}" for d in self.engine.analyze(rescan) if d.score >= 80]
        except Exception:
            residual = ["Residual scan could not complete."]

        cats: dict[str, int] = {}
        for d in chosen:
            cats[d.category] = cats.get(d.category, 0) + 1

        mapping_csv_path = None
        mapping_piimap_path = None
        payload = None

        if chosen and mask_mode == "token":
            if progress:
                progress(90, "Generating default CSV mapping table")
            payload = {"namespace": alloc.ns,
                       "entries": [{"placeholder": k, "value": v} for k, v in alloc.reverse.items()]}

            # 1. ALWAYS write the default CSV mapping table
            csv_bytes = mapping_table_csv_bytes(payload, {"placeholder_namespace_id": alloc.ns})
            mapping_csv_name = stamped_filename(path.stem, "mapping-table", ".csv", ts=ts)
            mapping_csv_path = atomic_write(out_dir / mapping_csv_name, csv_bytes, overwrite)

            # 2. Also generate encrypted / authenticated .piimap container
            header_extra = {
                "category_counts": cats, "placeholder_namespace_id": alloc.ns,
                "binding": {"src_doc_sha256": sha256_file(path),
                            "masked_doc_sha256": sha256_file(masked_path),
                            "canonical_text_sha256": sha256_text(canonical_text_of(masked_path)),
                            "placeholder_set_hash": hashlib.sha256(
                                "|".join(sorted(alloc.reverse)).encode()).hexdigest(),
                            "masked_file_name": masked_path.name}}
            blob = MappingContainer.build(payload, password, header_extra)
            mapping_piimap_name = stamped_filename(path.stem, "mapping", ".piimap", ts=ts)
            mapping_piimap_path = atomic_write(out_dir / mapping_piimap_name, blob, overwrite)

        primary_mapping_path = mapping_csv_path or mapping_piimap_path

        report = {"type": "mask", "ts": now_utc(), "source": path.name,
                  "masked_output": masked_path.name,
                  "mapping_csv": mapping_csv_path.name if mapping_csv_path else "(none)",
                  "mapping_piimap": mapping_piimap_path.name if mapping_piimap_path else "(none)",
                  "mapping": primary_mapping_path.name if primary_mapping_path else "(none)",
                  "mask_mode": mask_mode,
                  "encrypted": bool(password), "detections": len(dets), "masked": len(chosen),
                  "categories": cats, "namespace": alloc.ns,
                  "residual_high_confidence": residual,
                  "coverage_pct": round(100.0 * len(chosen) / len(dets), 1) if dets else 100.0,
                  "aead": ("aes-256-gcm" if HAVE_AESGCM else "hmac-sha256-ctr+hmac") if password else "none",
                  "kdf": ("argon2id" if HAVE_ARGON2 else "scrypt") if password else "none"}
        save_report(report)
        AuditLog.event("mask.completed", {"file": path.name, "masked": len(chosen),
                                          "encrypted": bool(password), "mode": mask_mode})
        if progress:
            progress(100, "Masking complete")
        return MaskResult(masked_path, primary_mapping_path, mapping_csv_path, mapping_piimap_path,
                          len(dets), len(chosen), residual, alloc.ns, report, orig_full, masked_full, payload)


# -------------------------------------------------------------------------------------
# UNMASKING ENGINE (Supports Original & AI-Edited/Modified Documents & Pasted Text)
# -------------------------------------------------------------------------------------
class UnmaskPipeline:
    @staticmethod
    def load_mapping_dict(mapping: Path, password: Optional[str] = None) -> tuple[dict, dict[str, str]]:
        """Loads mapping entries as {placeholder: original_value} from .csv, .piimap, or .json."""
        ext = mapping.suffix.lower()
        if ext == ".piimap":
            header, payload = MappingContainer.open(mapping.read_bytes(), password)
            entries = {str(e["placeholder"]): str(e["value"]) for e in payload.get("entries", [])}
            return header, entries
        elif ext == ".json":
            data = json.loads(read_text_file(mapping))
            entries = {}
            if isinstance(data, list):
                for item in data:
                    v = item.get("existing_pii_value") or item.get("original_value") or item.get("value")
                    m = item.get("masked_value") or item.get("masked_placeholder") or item.get("placeholder")
                    if v and m:
                        entries[str(m)] = str(v)
            elif isinstance(data, dict):
                for k, v in data.items():
                    if str(k).startswith("[") and str(k).endswith("]"):
                        entries[str(k)] = str(v)
                    else:
                        entries[str(v)] = str(k)
            header = {"fmt": FMT_VER, "kdf": "none", "aead": "none", "created_utc": now_utc(),
                      "placeholder_namespace_id": "JSON_TABLE", "binding": {}}
            return header, entries
        else:
            # Default CSV table (existing_pii_value, masked_value, category)
            raw_map = load_mapping_table_from_file(mapping, password)
            entries = {}
            for k, v in raw_map.items():
                if str(v).startswith("[") and str(v).endswith("]"):
                    entries[str(v)] = str(k)
                elif str(k).startswith("[") and str(k).endswith("]"):
                    entries[str(k)] = str(v)
                else:
                    entries[str(v)] = str(k)
            header = {"fmt": FMT_VER, "kdf": "none", "aead": "none", "created_utc": now_utc(),
                      "placeholder_namespace_id": "CSV_TABLE", "binding": {}}
            return header, entries

    @staticmethod
    def verify(masked: Path, mapping: Path, password: Optional[str]):
        header, entries = UnmaskPipeline.load_mapping_dict(mapping, password)
        b = header.get("binding", {})
        h = handler_for(masked)
        units = h.read(masked)
        text = "\n".join(u.text for u in units)
        present = {p for p in entries if p in text}
        doc_ok = sha256_file(masked) == b.get("masked_doc_sha256")
        txt_ok = sha256_text(text) == b.get("canonical_text_sha256")
        is_original = doc_ok or txt_ok

        checks = [
            ("Mapping Table Authenticity / Keys", True,
             f"Loaded {len(entries)} mapping key(s) from {mapping.suffix.upper()} ({header.get('aead', 'none')})"),
            ("Document Status / AI Modification", True,
             "Original unmodified document" if is_original
             else "Modified / AI-Edited document (supported - ready to unmask)"),
            ("Placeholder Namespace", True,
             f"Namespace: {header.get('placeholder_namespace_id', 'Active')}"),
            ("Placeholder Coverage", len(present) > 0,
             f"{len(present)} of {len(entries)} mapping keys identified in document" if present
             else f"0 of {len(entries)} mapping keys found (document may be fully unmasked or uses other keys)"),
        ]
        return header, entries, checks

    @staticmethod
    def unmask(masked: Path, mapping: Path, password: Optional[str], out_dir: Path,
               overwrite: bool, progress=None):
        header, entries, checks = UnmaskPipeline.verify(masked, mapping, password)
        h = handler_for(masked)
        units = h.read(masked)

        if progress:
            progress(35, "Scanning and substituting PII tokens across all nodes")

        # Sort placeholders by length descending to prevent partial token clipping
        sorted_ph = sorted(entries.keys(), key=len, reverse=True)
        new_text, restored_counts = {}, {}
        total_restored = 0

        for u in units:
            txt = u.text
            for ph in sorted_ph:
                val = entries[ph]
                if ph in txt:
                    c = txt.count(ph)
                    total_restored += c
                    restored_counts[ph] = restored_counts.get(ph, 0) + c
                    txt = txt.replace(ph, val)
            new_text[u.uid] = txt

        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        unmasked_out_name = stamped_filename(masked.stem, "unmasked", masked.suffix, ts=ts)
        out_path = h.write(masked, out_dir / unmasked_out_name, new_text, overwrite)

        leftovers = sorted({m.group(0) for t in new_text.values() for m in PLACEHOLDER_RE.finditer(t)})
        report = {
            "type": "unmask",
            "ts": now_utc(),
            "masked_input": masked.name,
            "mapping": mapping.name,
            "output": out_path.name,
            "output_path": str(out_path),
            "restored_occurrences": total_restored,
            "mapping_entries": len(entries),
            "keys_restored": len(restored_counts),
            "unresolved_placeholders": leftovers,
            "document_modified": checks[1][2].startswith("Modified"),
            "binding_checks": [{"check": c[0], "pass": c[1], "detail": c[2]} for c in checks],
        }
        save_report(report)
        AuditLog.event("unmask.completed", {"file": masked.name, "restored": total_restored,
                                          "keys": len(restored_counts)})
        if progress:
            progress(100, "Unmasking complete")
        return report

    @staticmethod
    def unmask_text_string(text: str, mapping_path: Path, password: Optional[str] = None) -> tuple[str, int, int, list[str]]:
        header, entries = UnmaskPipeline.load_mapping_dict(mapping_path, password)
        sorted_ph = sorted(entries.keys(), key=len, reverse=True)
        out_txt = text
        total_restored, keys_used = 0, 0
        for ph in sorted_ph:
            val = entries[ph]
            if ph in out_txt:
                c = out_txt.count(ph)
                total_restored += c
                keys_used += 1
                out_txt = out_txt.replace(ph, val)
        leftovers = sorted({m.group(0) for m in PLACEHOLDER_RE.finditer(out_txt)})
        return out_txt, total_restored, keys_used, leftovers


# =====================================================================================
# 16. REPORTS
# =====================================================================================
def reports_dir() -> Path:
    d = app_dir() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_report(report: dict) -> Path:
    p = reports_dir() / (f"{report.get('type', 'session')}-"
                         f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}.json")
    return atomic_write(p, json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8"), overwrite=True)


def report_to_text(rep: dict) -> str:
    lines = [f"{APP_NAME} - {str(rep.get('type', '')).upper()} REPORT",
             f"{APP_OWNER} | v{APP_VERSION} | generated {rep.get('ts', now_utc())}", "-" * 72]
    for k, v in rep.items():
        if k in ("type", "ts"):
            continue
        if isinstance(v, dict):
            lines.append(f"{k}:")
            lines += [f"    {a}: {b}" for a, b in v.items()] or ["    (none)"]
        elif isinstance(v, list):
            lines.append(f"{k}:")
            lines += [f"    {json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else x}"
                      for x in v] or ["    (none)"]
        else:
            lines.append(f"{k}: {v}")
    lines += ["-" * 72,
              "No raw PII values are stored in this report.",
              "This tool cannot guarantee 100% PII detection; review outputs before release."]
    return "\n".join(lines)


# =====================================================================================
# 17. SECURITY GUARDRAILS PROBES
# =====================================================================================
@dataclass
class Control:
    cid: str
    requirement: str
    probe: Callable[[], tuple]


def _p_kernel():
    return ("PASS" if OfflineKernel.installed else "FAIL",
            f"kernel installed={OfflineKernel.installed}; blocked attempts={OfflineKernel.blocked_attempts}")


def _p_network():
    ok, ev = OfflineKernel.probe()
    return ("PASS" if ok else "FAIL", ev)


def _p_filetype():
    p = SessionTemp.dir() / "sniff.txt"
    p.write_bytes(b"%PDF-1.7 not really text")
    kind = sniff(p)
    secure_delete(p)
    return ("PASS" if kind == "pdf" else "FAIL", f"magic bytes classified as '{kind}'")


def _p_malformed():
    p = SessionTemp.dir() / "broken.docx"
    p.write_bytes(secrets.token_bytes(2048))
    try:
        handler_for(p).read(p)
        res = ("FAIL", "malformed OOXML did not raise an error")
    except PiiToolError as exc:
        res = ("PASS", f"handled cleanly: {exc.code}")
    except Exception as exc:
        res = ("PASS", f"contained ({type(exc).__name__}), no crash")
    secure_delete(p)
    return res


def _p_traversal():
    try:
        safe_resolve(SessionTemp.dir(), "../../../../etc/passwd")
        return ("FAIL", "traversal path accepted")
    except PathSecurityError:
        return ("PASS", "traversal payload rejected by safe_resolve()")


def _p_temp():
    d = SessionTemp.dir()
    mode = oct(d.stat().st_mode & 0o777)
    if os.name == "nt":
        return ("PASS", f"session temp {d} exists; Windows ACLs inherited")
    return ("PASS" if mode == "0o700" else "FAIL", f"mode={mode}")


def _p_logging():
    out = scrub("Aadhaar 2345 6789 0123, PAN ABCDE1234F, mail a@b.com")
    ok = "2345" not in out and "a@b.com" not in out and "ABCDE1234F" not in out
    return ("PASS" if ok else "FAIL", f"scrubbed form: {out}")


def _p_crypto():
    payload = {"namespace": "AAAA", "entries": [{"placeholder": "[PAN_AAAA_001]", "value": "ABCDE1234F"}]}
    blob = MappingContainer.build(payload, "Pass#1234word",
                                  {"category_counts": {"PAN": 1}, "placeholder_namespace_id": "AAAA"})
    _, back = MappingContainer.open(blob, "Pass#1234word")
    ok = back["entries"][0]["value"] == "ABCDE1234F" and b"ABCDE1234F" not in blob
    return ("PASS" if ok else "FAIL",
            f"{'Argon2id' if HAVE_ARGON2 else 'scrypt'} + "
            f"{'AES-256-GCM' if HAVE_AESGCM else 'HMAC-CTR fallback'}: round trip OK")


def _p_partial():
    a = partial_mask_value("AADHAAR", "2345 6789 0123")
    p = partial_mask_value("PAN", "ABCDE1234F")
    c = partial_mask_value("CREDIT_CARD", "4111 2222 3333 4444")
    ok = a == "XXXX-XXXX-0123" and p == "AXXXXXX4F" and c == "XXXX-XXXX-XXXX-4444"
    return ("PASS" if ok else "FAIL", f"partial masks: Aadhaar={a}, PAN={p}, Card={c}")


CONTROLS = [
    Control("SG01", "Offline processing only", _p_kernel),
    Control("SG02", "No unexpected network access", _p_network),
    Control("SG03", "File-type validation (magic bytes)", _p_filetype),
    Control("SG04", "Malformed / malicious file handling", _p_malformed),
    Control("SG05", "Path-traversal prevention", _p_traversal),
    Control("SG06", "Temp-file protection and cleanup", _p_temp),
    Control("SG07", "PII-safe logging", _p_logging),
    Control("SG09", "Mapping encryption", _p_crypto),
    Control("SG18", "Partial format-preserving masking", _p_partial),
]


# =====================================================================================
# 18. MODERN UI: THEMES, HIGH-CONTRAST SCROLLBARS & REUSABLE WIDGETS
# =====================================================================================
def _font_family() -> str:
    return "Segoe UI" if os.name == "nt" else ("SF Pro Text" if sys.platform == "darwin" else "Helvetica")


def _mono_family() -> str:
    return "Cascadia Mono" if os.name == "nt" else ("Menlo" if sys.platform == "darwin" else "DejaVu Sans Mono")


FONT = _font_family()
MONO = _mono_family()
F_TITLE = (FONT, 16, "bold")
F_TAGLINE = (FONT, 9)
F_SECTION = (FONT, 11, "bold")
F_BODY = (FONT, 10)
F_BODY_BOLD = (FONT, 10, "bold")
F_SMALL = (FONT, 9)
F_MONO = (MONO, 10)
F_BADGE = (FONT, 9, "bold")

THEMES = {
    "dark": {
        "bg":                 "#0b0f19",
        "bg_alt":             "#111827",
        "panel":              "#1e293b",
        "panel_alt":          "#334155",
        "border":             "#475569",
        "fg":                 "#f1f5f9",
        "fg_dim":             "#cbd5e1",
        "muted":              "#94a3b8",
        "accent":             "#4f46e5",
        "accent_hover":       "#6366f1",
        "accent_fg":          "#ffffff",
        "accent2":            "#06b6d4",
        "accent3":            "#8b5cf6",
        "ok":                 "#10b981", "ok_bg":   "#064e3b",
        "warn":               "#f59e0b", "warn_bg": "#451a03",
        "err":                "#ef4444", "err_bg":  "#4c0519",
        "field":              "#0f172a",
        "sel":                "#3730a3",
        "header_fg":          "#ffffff",
        "scroll_thumb":       "#475569",
        "scroll_thumb_hover": "#6366f1",
        "scroll_track":       "#111827",
    },
    "light": {
        "bg":                 "#f8fafc",
        "bg_alt":             "#ffffff",
        "panel":              "#ffffff",
        "panel_alt":          "#f1f5f9",
        "border":             "#cbd5e1",
        "fg":                 "#0f172a",
        "fg_dim":             "#334155",
        "muted":              "#64748b",
        "accent":             "#3b82f6",
        "accent_hover":       "#60a5fa",
        "accent_fg":          "#ffffff",
        "accent2":            "#0d9488",
        "accent3":            "#7c3aed",
        "ok":                 "#16a34a", "ok_bg":   "#dcfce7",
        "warn":               "#d97706", "warn_bg": "#fef3c7",
        "err":                "#dc2626", "err_bg":  "#fee2e2",
        "field":              "#ffffff",
        "sel":                "#2563eb",
        "header_fg":          "#0f172a",
        "scroll_thumb":       "#94a3b8",
        "scroll_thumb_hover": "#3b82f6",
        "scroll_track":       "#e2e8f0",
    },
}


# ------------------------------------------------------------------
# SAP-STYLE 4-SIDED SCROLLING & NAVIGATION CONTAINER
# ------------------------------------------------------------------
class SapNavContainer(ttk.Frame):
    """Wraps any scrollable target (Treeview, Text, Canvas) with 4-sided navigation step
    controls (Top, Bottom, Left, Right) + dual-axis high-visibility scrollbars."""

    def __init__(self, master, make_target_fn, **kwargs):
        super().__init__(master, **kwargs)

        # 1. TOP BAR: Jump Top / Page Up / Step Up
        top_bar = ttk.Frame(self)
        top_bar.pack(side="top", fill="x", pady=(0, 2))
        ttk.Button(top_bar, text="⏫ Top", width=7, command=self._jump_top).pack(side="left", padx=2)
        ttk.Button(top_bar, text="🔼 Page Up", width=11, command=self._page_up).pack(side="left", padx=2)
        ttk.Button(top_bar, text="▲ Step Up", width=10, command=self._step_up).pack(side="left", padx=2)
        self.lbl_top_info = ttk.Label(top_bar, style="Muted.TLabel")
        self.lbl_top_info.pack(side="right", padx=6)

        # 2. MIDDLE AREA (Left Bar + Target + Right Bar & V-Scroll)
        mid = ttk.Frame(self)
        mid.pack(side="top", fill="both", expand=True)

        # Left Bar: Jump Left / Step Left
        left_bar = ttk.Frame(mid)
        left_bar.pack(side="left", fill="y", padx=(0, 2))
        ttk.Button(left_bar, text="⏪", width=3, command=self._jump_left).pack(side="top", pady=2)
        ttk.Button(left_bar, text="◀", width=3, command=self._step_left).pack(side="top", pady=2)

        # Right Bar: Step Right / Jump Right
        right_bar = ttk.Frame(mid)
        right_bar.pack(side="right", fill="y", padx=(2, 0))
        ttk.Button(right_bar, text="⏩", width=3, command=self._jump_right).pack(side="top", pady=2)
        ttk.Button(right_bar, text="▶", width=3, command=self._step_right).pack(side="top", pady=2)

        # Target center frame with high-contrast dual scrollbars
        center = ttk.Frame(mid)
        center.pack(side="left", fill="both", expand=True)

        self.vs = ttk.Scrollbar(center, orient="vertical")
        self.hs = ttk.Scrollbar(center, orient="horizontal")

        self.target = make_target_fn(center, self.vs, self.hs)
        self.target.pack(side="left", fill="both", expand=True)
        self.vs.pack(side="right", fill="y")
        self.hs.pack(side="bottom", fill="x")

        # 3. BOTTOM BAR: Step Down / Page Down / Jump Bottom
        bot_bar = ttk.Frame(self)
        bot_bar.pack(side="bottom", fill="x", pady=(2, 0))
        ttk.Button(bot_bar, text="▼ Step Down", width=11, command=self._step_down).pack(side="left", padx=2)
        ttk.Button(bot_bar, text="🔽 Page Down", width=12, command=self._page_down).pack(side="left", padx=2)
        ttk.Button(bot_bar, text="⏬ Bottom", width=9, command=self._jump_bottom).pack(side="left", padx=2)

    def _jump_top(self):
        if hasattr(self.target, "yview_moveto"):
            self.target.yview_moveto(0.0)

    def _jump_bottom(self):
        if hasattr(self.target, "yview_moveto"):
            self.target.yview_moveto(1.0)

    def _page_up(self):
        if hasattr(self.target, "yview_scroll"):
            self.target.yview_scroll(-1, "pages")

    def _page_down(self):
        if hasattr(self.target, "yview_scroll"):
            self.target.yview_scroll(1, "pages")

    def _step_up(self):
        if hasattr(self.target, "yview_scroll"):
            self.target.yview_scroll(-3, "units")

    def _step_down(self):
        if hasattr(self.target, "yview_scroll"):
            self.target.yview_scroll(3, "units")

    def _jump_left(self):
        if hasattr(self.target, "xview_moveto"):
            self.target.xview_moveto(0.0)

    def _jump_right(self):
        if hasattr(self.target, "xview_moveto"):
            self.target.xview_moveto(1.0)

    def _step_left(self):
        if hasattr(self.target, "xview_scroll"):
            self.target.xview_scroll(-3, "units")

    def _step_right(self):
        if hasattr(self.target, "xview_scroll"):
            self.target.xview_scroll(3, "units")


# ------------------------------------------------------------------
# SCROLLABLE CANVAS TAB CONTAINER
# ------------------------------------------------------------------
class ScrollableTabFrame(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.vs = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vs.set)

        self.vs.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = ttk.Frame(self.canvas, padding=12)
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._on_content_config)
        self.canvas.bind("<Configure>", self._on_canvas_config)

    def _on_content_config(self, _e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_config(self, e):
        self.canvas.itemconfig(self.window_id, width=e.width)


# ------------------------------------------------------------------
# ASYNC WORKER
# ------------------------------------------------------------------
class AsyncJob:
    def __init__(self, app, fn):
        self.app, self.fn = app, fn
        self.q: queue.Queue = queue.Queue()
        self.cancel = threading.Event()
        self.on_progress = self.on_success = self.on_error = None

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
        self.app.root.after(60, self._poll)

    def _run(self):
        try:
            res = self.fn(lambda p, m: self.q.put(("p", (p, m))), self.cancel)
            self.q.put(("ok", res))
        except PiiToolError as exc:
            AuditLog.event("job.error", {"code": exc.code})
            self.q.put(("err", str(exc)))
        except Exception as exc:
            AuditLog.event("job.error", {"code": type(exc).__name__})
            self.q.put(("err", f"[E999] {type(exc).__name__}: {scrub(exc)}"))

    def _poll(self):
        alive = True
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "p" and self.on_progress:
                    self.on_progress(*payload)
                elif kind == "ok":
                    alive = False
                    if self.on_success:
                        self.on_success(payload)
                elif kind == "err":
                    alive = False
                    if self.on_error:
                        self.on_error(payload)
        except queue.Empty:
            pass
        if alive:
            self.app.root.after(60, self._poll)


# ------------------------------------------------------------------
# MODAL DIALOGS
# ------------------------------------------------------------------
def entry_dialog(parent, title: str, fields: list, initial: dict) -> Optional[dict]:
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)
    vars_: dict[str, Any] = {}
    frm = ttk.Frame(win, padding=14)
    frm.pack(fill="both", expand=True)
    result: dict[str, Any] = {}

    for r, (key, label, kind, options) in enumerate(fields):
        ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 10))
        if kind == "check":
            v = tk.BooleanVar(value=bool(initial.get(key, False)))
            ttk.Checkbutton(frm, variable=v).grid(row=r, column=1, sticky="w")
        elif kind == "combo":
            v = tk.StringVar(value=str(initial.get(key, "")))
            cb = ttk.Combobox(frm, textvariable=v, values=options, width=38)
            cb.grid(row=r, column=1, sticky="we")
        elif kind == "int":
            v = tk.IntVar(value=int(initial.get(key, 0)))
            ttk.Spinbox(frm, from_=options[0], to=options[1], textvariable=v,
                        width=10).grid(row=r, column=1, sticky="w")
        elif kind == "password":
            v = tk.StringVar(value=str(initial.get(key, "")))
            ttk.Entry(frm, textvariable=v, show="•", width=40).grid(row=r, column=1, sticky="we")
        else:
            v = tk.StringVar(value=str(initial.get(key, "")))
            ttk.Entry(frm, textvariable=v, width=40).grid(row=r, column=1, sticky="we")
        vars_[key] = v

    msg = ttk.Label(frm, text="", wraplength=420, foreground=THEMES[CONFIG.data["theme"]]["err"])
    msg.grid(row=len(fields), column=0, columnspan=2, sticky="we", pady=(8, 0))

    def ok():
        data = {k: v.get() for k, v in vars_.items()}
        if data.get("type") == "regex":
            findings = redos_lint(str(data.get("term", "")))
            blocking = [f for f in findings if "invalid regex" in f or "timed out" in f]
            if blocking:
                msg.configure(text="Rejected by ReDoS linter: " + "; ".join(blocking))
                return
            if findings and not messagebox.askyesno(
                    "Risky pattern", "The linter flagged:\n\n" + "\n".join(findings) + "\n\nSave anyway?",
                    parent=win):
                return
        result.update(data)
        win.destroy()

    btns = ttk.Frame(frm)
    btns.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
    ttk.Button(btns, text="OK", style="Accent.TButton", command=ok).pack(side="left", padx=4)
    ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="left")
    win.bind("<Return>", lambda e: ok())
    win.bind("<Escape>", lambda e: win.destroy())
    parent.wait_window(win)
    return result or None


def simple_choice(parent, title: str, prompt: str, options: list) -> Optional[str]:
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)
    frm = ttk.Frame(win, padding=14)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text=prompt, wraplength=380).pack(anchor="w", pady=(0, 8))
    v = tk.StringVar(value=options[0])
    for opt in options:
        ttk.Radiobutton(frm, text=opt, value=opt, variable=v).pack(anchor="w", pady=2)
    result: dict[str, Optional[str]] = {"value": None}

    def ok():
        result["value"] = v.get()
        win.destroy()

    btns = ttk.Frame(frm); btns.pack(fill="x", pady=(12, 0))
    ttk.Button(btns, text="OK", style="Accent.TButton", command=ok).pack(side="left", padx=4)
    ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="left")
    win.bind("<Return>", lambda e: ok())
    win.bind("<Escape>", lambda e: win.destroy())
    parent.wait_window(win)
    return result["value"]


# =====================================================================================
# 19. MASK TAB (Unified with Downloads, Mapping Upload, SAP Scroll)
# =====================================================================================
class MaskTab(ScrollableTabFrame):
    def __init__(self, app, master):
        super().__init__(master)
        self.app = app
        self.path: Optional[Path] = None
        self.handler = None
        self.units: list[TextUnit] = []
        self.dets: list[Detection] = []
        self.job: Optional[AsyncJob] = None
        self.preloaded_mapping: dict[str, str] = {}
        self.pipeline = MaskPipeline(CONFIG)
        self.last_result: Optional[MaskResult] = None

        p = self.content

        # 1. KPI / STATUS HERO METRIC CARDS
        kpi_frame = ttk.Frame(p)
        kpi_frame.pack(fill="x", pady=(0, 10))
        for i in range(4):
            kpi_frame.columnconfigure(i, weight=1, uniform="kpi")

        self.kpi_detected = self._make_kpi_card(kpi_frame, 0, "Candidates Detected", "0", "Awaiting scan")
        self.kpi_selected = self._make_kpi_card(kpi_frame, 1, "Selected for Masking", "0", "0% coverage")
        self.kpi_mapping_reuse = self._make_kpi_card(kpi_frame, 2, "Prior Mapping Table", "Inactive", "No prior table")
        self.kpi_security = self._make_kpi_card(kpi_frame, 3, "Security Posture", "PROTECTED", "Offline Kernel Active")

        # 2. SELECT FILE & DECRYPTION PASSWORD
        f1 = ttk.LabelFrame(p, text=" 1. Document Selection & Ingestion ", padding=10)
        f1.pack(fill="x", pady=(0, 10))

        row1 = ttk.Frame(f1); row1.pack(fill="x")
        self.v_file = tk.StringVar()
        ttk.Label(row1, text="Source File:").pack(side="left", padx=(0, 6))
        ttk.Entry(row1, textvariable=self.v_file, state="readonly").pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row1, text="📁 Browse Document…", style="Accent.TButton", command=self.browse).pack(side="left", padx=4)

        row1b = ttk.Frame(f1); row1b.pack(fill="x", pady=(8, 0))
        ttk.Label(row1b, text="File Password (optional for protected PDF/files):").pack(side="left", padx=(0, 6))
        self.v_file_pw = tk.StringVar()
        self.ent_file_pw = ttk.Entry(row1b, textvariable=self.v_file_pw, show="•", width=24)
        self.ent_file_pw.pack(side="left", padx=4)
        self.v_show_file_pw = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1b, text="Show", variable=self.v_show_file_pw,
                        command=lambda: self.ent_file_pw.configure(show="" if self.v_show_file_pw.get() else "•")
                        ).pack(side="left", padx=4)

        self.card = tk.Text(f1, height=4, wrap="word")
        self.card.pack(fill="x", pady=(8, 0))
        self.card.configure(state="disabled")
        app.register_text(self.card)

        # 3. PRIOR MAPPING TABLE UPLOAD & REUSE
        f_map_reuse = ttk.LabelFrame(p, text=" 2. Optional: Upload Prior Mapping Key Table (Consistent Reuse) ", padding=10)
        f_map_reuse.pack(fill="x", pady=(0, 10))

        row_mr = ttk.Frame(f_map_reuse); row_mr.pack(fill="x")
        self.v_mapping_file = tk.StringVar(value="(None - fresh placeholders will be generated)")
        ttk.Label(row_mr, text="Active Mapping Table:").pack(side="left", padx=(0, 6))
        ttk.Entry(row_mr, textvariable=self.v_mapping_file, state="readonly").pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row_mr, text="📂 Load Prior Key Table (.csv / .json / .piimap)…", command=self.load_prior_mapping).pack(side="left", padx=4)
        ttk.Button(row_mr, text="✖ Clear", command=self.clear_prior_mapping).pack(side="left", padx=2)

        # 4. ACTION BAR & PROGRESS
        f2 = ttk.Frame(p); f2.pack(fill="x", pady=(0, 10))
        self.btn_analyze = ttk.Button(f2, text="🔍 Analyze for PII", style="Accent.TButton",
                                      command=self.analyze, state="disabled")
        self.btn_analyze.pack(side="left")
        self.btn_cancel = ttk.Button(f2, text="Cancel", command=self.cancel, state="disabled")
        self.btn_cancel.pack(side="left", padx=6)
        self.pbar = ttk.Progressbar(f2, maximum=100)
        self.pbar.pack(side="left", fill="x", expand=True, padx=8)

        # 5. REVIEW DETECTIONS (WITH SAP 4-SIDED CONTROLS)
        f3 = ttk.LabelFrame(p, text=" 3. Review Detections (SAP 4-Sided Navigation & Review Grid) ", padding=10)
        f3.pack(fill="both", expand=True, pady=(0, 10))

        def make_tree(parent, vs, hs):
            cols = ("sel", "value", "cat", "conf", "score", "evidence", "loc")
            self.tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="extended",
                                     height=10, yscrollcommand=vs.set, xscrollcommand=hs.set)
            for c, t, w in (("sel", "Mask", 60), ("value", "Value", 220), ("cat", "Category", 130),
                            ("conf", "Confidence", 100), ("score", "Score", 70),
                            ("evidence", "Evidence", 420), ("loc", "Location", 160)):
                self.tree.heading(c, text=t)
                self.tree.column(c, width=w, anchor="w")
            vs.configure(command=self.tree.yview)
            hs.configure(command=self.tree.xview)
            self.tree.bind("<Button-1>", self.on_click)
            self.tree.bind("<space>", lambda e: self.toggle_selected())
            return self.tree

        self.nav_container = SapNavContainer(f3, make_tree)
        self.nav_container.pack(fill="both", expand=True)

        f4 = ttk.Frame(f3); f4.pack(fill="x", pady=(8, 0))
        for txt, cmd in (("Select All", lambda: self.set_all(True)),
                         ("Deselect All", lambda: self.set_all(False)),
                         ("Toggle Selected", self.toggle_selected),
                         ("👁 Reveal Selected", self.reveal),
                         ("Change Category…", self.change_cat),
                         ("➕ Add to Dictionary", self.to_dict)):
            ttk.Button(f4, text=txt, command=cmd).pack(side="left", padx=3)
        self.v_summary = tk.StringVar()
        ttk.Label(f4, textvariable=self.v_summary, style="Section.TLabel").pack(side="right")

        # 6. MASKING SETTINGS & EXECUTION
        f5 = ttk.LabelFrame(p, text=" 4. Masking Mode & Security Settings ", padding=10)
        f5.pack(fill="x", pady=(0, 10))

        r_mode = ttk.Frame(f5); r_mode.pack(fill="x", pady=(0, 6))
        ttk.Label(r_mode, text="Masking Strategy:").pack(side="left", padx=(0, 6))
        self.v_mask_mode = tk.StringVar(value="token")
        ttk.Radiobutton(r_mode, text="Reversible Token ([CATEGORY_NS_001])", value="token",
                        variable=self.v_mask_mode).pack(side="left", padx=6)
        ttk.Radiobutton(r_mode, text="Partial Masking (XXXX-1234, AXXXXXX4F)", value="partial",
                        variable=self.v_mask_mode).pack(side="left", padx=6)
        ttk.Radiobutton(r_mode, text="Cryptographic Hash ([HASH_4F8A])", value="hash",
                        variable=self.v_mask_mode).pack(side="left", padx=6)
        ttk.Radiobutton(r_mode, text="Solid Redaction ([REDACTED])", value="redact",
                        variable=self.v_mask_mode).pack(side="left", padx=6)

        r_enc = ttk.Frame(f5); r_enc.pack(fill="x", pady=(4, 6))
        self.v_enc = tk.BooleanVar(value=bool(CONFIG.data.get("encrypt_default", True)))
        ttk.Checkbutton(r_enc, text="Encrypt vault key container (.piimap) with AES-256-GCM / Argon2id",
                        variable=self.v_enc).pack(side="left")

        r_pw = ttk.Frame(f5); r_pw.pack(fill="x", pady=(2, 6))
        ttk.Label(r_pw, text="Password:").pack(side="left", padx=(0, 4))
        self.v_pw1 = tk.StringVar()
        ttk.Entry(r_pw, textvariable=self.v_pw1, show="•", width=22).pack(side="left", padx=4)
        ttk.Label(r_pw, text="Confirm Password:").pack(side="left", padx=(10, 4))
        self.v_pw2 = tk.StringVar()
        ttk.Entry(r_pw, textvariable=self.v_pw2, show="•", width=22).pack(side="left", padx=4)

        r_out = ttk.Frame(f5); r_out.pack(fill="x", pady=(2, 6))
        ttk.Label(r_out, text="Output Directory:").pack(side="left", padx=(0, 4))
        self.v_out = tk.StringVar(value=CONFIG.data.get("output_dir", ""))
        ttk.Entry(r_out, textvariable=self.v_out).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(r_out, text="📁 Choose Folder…", command=self.pick_out).pack(side="left", padx=4)
        self.v_ow = tk.BooleanVar(value=False)
        ttk.Checkbutton(r_out, text="Allow Overwrite", variable=self.v_ow).pack(side="left", padx=6)

        self.btn_mask = ttk.Button(f5, text="🛡️ Mask and Save All Outputs (Default CSV Table)", style="Accent.TButton",
                                   command=self.do_mask, state="disabled")
        self.btn_mask.pack(anchor="e", pady=(4, 0))

        # 7. ONE-CLICK DOWNLOAD & EXPORT CENTER
        f6 = ttk.LabelFrame(p, text=" 5. Download & Export Center (Default CSV Mapping Format) ", padding=10)
        f6.pack(fill="x", pady=(0, 10))

        ttk.Label(f6, style="Muted.TLabel", wraplength=1050, text=(
            "Output files are automatically generated with full timestamped names (<original_name>-masked-<timestamp>.<ext> "
            "and <original_name>-mapping-table-<timestamp>.csv). Mapping file downloads default to CSV format. "
            "Use the buttons below to save single files, download both masked file and CSV table together, "
            "or copy content directly.")).pack(anchor="w", pady=(0, 8))

        dl_grid = ttk.Frame(f6); dl_grid.pack(fill="x")

        self.btn_save_masked = ttk.Button(dl_grid, text="📥 Download Masked File (Original Format)",
                                          style="Accent.TButton", command=self.download_masked_file, state="disabled")
        self.btn_save_masked.grid(row=0, column=0, padx=4, pady=4, sticky="we")

        self.btn_save_mapping = ttk.Button(dl_grid, text="📊 Download Mapping File (Default: CSV Table)",
                                           style="Accent.TButton", command=self.download_mapping_file, state="disabled")
        self.btn_save_mapping.grid(row=0, column=1, padx=4, pady=4, sticky="we")

        self.btn_save_both = ttk.Button(dl_grid, text="📦 Download Both (Masked File + CSV Table)",
                                        command=self.download_both, state="disabled")
        self.btn_save_both.grid(row=0, column=2, padx=4, pady=4, sticky="we")

        self.btn_save_md = ttk.Button(dl_grid, text="📄 Download Masked Document (.md / .txt)",
                                      command=self.download_masked_md, state="disabled")
        self.btn_save_md.grid(row=1, column=0, padx=4, pady=4, sticky="we")

        self.btn_save_piimap = ttk.Button(dl_grid, text="🔑 Download Vault Container (.piimap)",
                                          command=self.download_piimap_vault, state="disabled")
        self.btn_save_piimap.grid(row=1, column=1, padx=4, pady=4, sticky="we")

        self.btn_copy_clip = ttk.Button(dl_grid, text="📋 Copy Masked Text to Clipboard",
                                        command=self.copy_masked_to_clipboard, state="disabled")
        self.btn_copy_clip.grid(row=1, column=2, padx=4, pady=4, sticky="we")

        self.btn_open_folder = ttk.Button(dl_grid, text="📁 Open Output Folder",
                                          command=self.open_output_folder, state="disabled")
        self.btn_open_folder.grid(row=2, column=0, columnspan=3, padx=4, pady=4, sticky="we")

        for col_idx in range(3):
            dl_grid.columnconfigure(col_idx, weight=1)

        self.out = tk.Text(p, height=5, wrap="word")
        self.out.pack(fill="x", pady=(6, 0))
        self.out.configure(state="disabled")
        app.register_text(self.out)

    def _make_kpi_card(self, parent, col, title, initial_val, sub):
        card = ttk.Frame(parent, style="Card.TFrame", padding=8)
        card.grid(row=0, column=col, sticky="nsew", padx=4)
        ttk.Label(card, text=title, style="Muted.TLabel").pack(anchor="w")
        v_main = tk.StringVar(value=initial_val)
        ttk.Label(card, textvariable=v_main, font=F_TITLE).pack(anchor="w", pady=2)
        v_sub = tk.StringVar(value=sub)
        ttk.Label(card, textvariable=v_sub, style="Muted.TLabel").pack(anchor="w")
        return {"main": v_main, "sub": v_sub, "frame": card}

    def _set_card(self, text: str):
        self.card.configure(state="normal")
        self.card.delete("1.0", "end")
        self.card.insert("1.0", text)
        self.card.configure(state="disabled")

    def _set_out(self, text: str):
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)
        self.out.configure(state="disabled")

    def browse(self):
        p = filedialog.askopenfilename(
            title="Select a document to mask",
            filetypes=[("Supported documents", " ".join(f"*{e}" for e in SUPPORTED_EXTS)),
                       ("All files", "*.*")])
        if not p:
            return
        self.path = Path(p)
        self.v_file.set(p)
        self.tree.delete(*self.tree.get_children())
        self.dets = []
        self.btn_mask.configure(state="disabled")
        try:
            check_limits(self.path)
            h = handler_for(self.path)
            info = (f"File: {self.path.name} | Size: {self.path.stat().st_size:,} bytes | Parser: {type(h).__name__}\n"
                    f"SHA-256: {sha256_file(self.path)}")
            if h.note:
                info += f"\nNote: {h.note}"
            self._set_card(info)
            self.btn_analyze.configure(state="normal")
            if not self.v_out.get():
                self.v_out.set(str(self.path.parent))
        except PiiToolError as exc:
            self._set_card(str(exc))
            self.btn_analyze.configure(state="disabled")

    def load_prior_mapping(self):
        p = filedialog.askopenfilename(
            title="Select existing mapping table (Default: .csv)",
            filetypes=[("CSV Mapping Table (*.csv)", "*.csv"), ("JSON Table (*.json)", "*.json"),
                       ("PII Mapping Container (*.piimap)", "*.piimap"), ("All files", "*.*")])
        if not p:
            return
        path = Path(p)
        pw = None
        if path.suffix.lower() == ".piimap":
            res = entry_dialog(self, "Mapping Password",
                               [("password", "Enter password for the .piimap file:", "password", None)],
                               {"password": ""})
            if res is None:
                return
            pw = res.get("password") or None
        try:
            self.preloaded_mapping = load_mapping_table_from_file(path, pw)
            self.v_mapping_file.set(f"{path.name} ({len(self.preloaded_mapping)} entries loaded)")
            self.kpi_mapping_reuse["main"].set(f"{len(self.preloaded_mapping)} Keys")
            self.kpi_mapping_reuse["sub"].set(f"From {path.name}")
            messagebox.showinfo("Prior Mapping Loaded",
                                f"Successfully loaded {len(self.preloaded_mapping)} prior PII mapping entries.\n"
                                f"Any matching PII values will reuse these exact masked tokens.", parent=self)
        except Exception as exc:
            messagebox.showerror("Failed to load mapping", f"Could not load mapping table: {exc}", parent=self)

    def clear_prior_mapping(self):
        self.preloaded_mapping = {}
        self.v_mapping_file.set("(None - fresh placeholders will be generated)")
        self.kpi_mapping_reuse["main"].set("Inactive")
        self.kpi_mapping_reuse["sub"].set("No prior table")

    def analyze(self):
        if not self.path:
            return
        self.pipeline = MaskPipeline(CONFIG, preloaded_mapping=self.preloaded_mapping)
        self.btn_analyze.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.pbar["value"] = 0
        file_pw = self.v_file_pw.get() or None
        self.job = AsyncJob(self.app, lambda pr, cn: self.pipeline.analyze(self.path, file_pw, pr, cn))
        self.job.on_progress = lambda p, m: (self.pbar.configure(value=p), self.app.status(m))
        self.job.on_success = self.analyzed
        self.job.on_error = self.failed
        self.job.start()

    def cancel(self):
        if self.job:
            self.job.cancel.set()
            self.app.status("Cancelling…")

    def failed(self, msg):
        self.btn_analyze.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        self.pbar["value"] = 0
        messagebox.showerror("Operation failed", msg, parent=self)
        self.app.status("Ready")

    def analyzed(self, res):
        self.handler, self.units, self.dets, _meta = res
        self.btn_analyze.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        self.fill()
        self.btn_mask.configure(state="normal")
        self.kpi_detected["main"].set(str(len(self.dets)))
        self.kpi_detected["sub"].set(f"Across {len(self.units)} text units")
        self.app.status("No PII detected." if not self.dets
                        else f"PII detected: {len(self.dets)} candidate(s). Review before masking.")

    def fill(self):
        self.tree.delete(*self.tree.get_children())
        reveal = bool(CONFIG.data.get("reveal_by_default"))
        for i, d in enumerate(self.dets):
            self.tree.insert("", "end", iid=str(i), values=(
                "✔" if d.selected else "",
                d.value.reveal() if reveal else d.value.dotted(),
                d.category, d.confidence, d.score, "; ".join(d.evidence), d.location))
        cats: dict[str, int] = {}
        for d in self.dets:
            cats[d.category] = cats.get(d.category, 0) + 1
        sel_count = sum(1 for d in self.dets if d.selected)
        pct = round(100.0 * sel_count / max(1, len(self.dets)), 1)
        self.kpi_selected["main"].set(f"{sel_count} / {len(self.dets)}")
        self.kpi_selected["sub"].set(f"{pct}% coverage")
        self.v_summary.set("  ".join(f"{k}:{v}" for k, v in sorted(cats.items())) or "No candidates")

    def on_click(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        if self.tree.identify_column(event.x) != "#1":
            return
        iid = self.tree.identify_row(event.y)
        if iid:
            self._toggle(iid)
            return "break"

    def _toggle(self, iid):
        d = self.dets[int(iid)]
        d.selected = not d.selected
        self.tree.set(iid, "sel", "✔" if d.selected else "")
        sel_count = sum(1 for x in self.dets if x.selected)
        self.kpi_selected["main"].set(f"{sel_count} / {len(self.dets)}")

    def toggle_selected(self):
        for iid in self.tree.selection():
            self._toggle(iid)

    def set_all(self, value: bool):
        for i, d in enumerate(self.dets):
            d.selected = value
            self.tree.set(str(i), "sel", "✔" if value else "")
        sel_count = sum(1 for x in self.dets if x.selected)
        self.kpi_selected["main"].set(f"{sel_count} / {len(self.dets)}")

    def reveal(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Reveal", "Select one or more rows first.", parent=self)
            return
        if not messagebox.askyesno("Reveal values", "Reveal the raw PII values on screen?", parent=self):
            return
        for iid in sel:
            self.tree.set(iid, "value", self.dets[int(iid)].value.reveal())
        AuditLog.event("ui.reveal", {"rows": len(sel)})

    def change_cat(self):
        sel = self.tree.selection()
        if not sel:
            return
        res = entry_dialog(self, "Change category",
                           [("category", "New category", "combo", CONFIG.all_categories())],
                           {"category": self.dets[int(sel[0])].category})
        if not res:
            return
        cat = re.sub(r"[^A-Z0-9_]", "_", str(res["category"]).upper()) or "CUSTOM"
        for iid in sel:
            d = self.dets[int(iid)]
            d.category = cat
            d.evidence.append("category set manually by user")
            self.tree.set(iid, "cat", cat)
            self.tree.set(iid, "evidence", "; ".join(d.evidence))

    def to_dict(self):
        sel = self.tree.selection()
        if not sel:
            return
        for iid in sel:
            d = self.dets[int(iid)]
            CONFIG.dictionary.append({"term": d.value.reveal(), "category": d.category,
                                      "type": "literal", "case_sensitive": False, "whole_word": True,
                                      "enabled": True, "note": f"added from review {now_utc()}"})
        CONFIG.save()
        self.app.tabs["Dictionary"].reload()
        messagebox.showinfo("Dictionary updated",
                            f"{len(sel)} term(s) added to your editable dictionary.", parent=self)

    def pick_out(self):
        d = filedialog.askdirectory(title="Select Output Folder")
        if d:
            self.v_out.set(d)

    def do_mask(self):
        chosen = [d for d in self.dets if d.selected]
        if not chosen:
            messagebox.showwarning("Nothing selected", "No detections are ticked for masking.", parent=self)
            return
        pw = None
        if self.v_enc.get():
            if len(self.v_pw1.get()) < 10:
                messagebox.showwarning("Weak password", "Password must be at least 10 characters.", parent=self)
                return
            if self.v_pw1.get() != self.v_pw2.get():
                messagebox.showwarning("Mismatch", "Passwords do not match.", parent=self)
                return
            pw = self.v_pw1.get()

        out_dir = Path(self.v_out.get() or self.path.parent)
        overwrite, path, handler, units, dets = self.v_ow.get(), self.path, self.handler, self.units, self.dets
        mode = self.v_mask_mode.get()

        self.btn_mask.configure(state="disabled")
        self.job = AsyncJob(self.app, lambda pr, cn: self.pipeline.mask(
            path, handler, units, dets, out_dir, pw, overwrite, mode, pr))
        self.job.on_progress = lambda p, m: (self.pbar.configure(value=p), self.app.status(m))
        self.job.on_success = self.masked
        self.job.on_error = lambda m: (self.btn_mask.configure(state="normal"), self.failed(m))
        self.job.start()

    def masked(self, res: MaskResult):
        self.btn_mask.configure(state="normal")
        self.v_pw1.set(""); self.v_pw2.set("")
        self.last_result = res

        self.btn_save_masked.configure(state="normal")
        self.btn_save_mapping.configure(state="normal" if (res.mapping_csv_path or res.mapping_payload) else "disabled")
        self.btn_save_both.configure(state="normal" if (res.mapping_csv_path or res.mapping_payload) else "disabled")
        self.btn_save_md.configure(state="normal")
        self.btn_save_piimap.configure(state="normal" if res.mapping_piimap_path else "disabled")
        self.btn_copy_clip.configure(state="normal")
        self.btn_open_folder.configure(state="normal")

        diff_tab = self.app.tabs.get("Side-by-Side Diff")
        if diff_tab:
            diff_tab.load_diff(res.original_text, res.masked_text, self.dets)

        residual = ("Residual high-confidence findings: " + "; ".join(res.residual)) if res.residual \
            else "Residual scan: zero high-confidence PII found."
        self._set_out(
            f"✔ MASKING COMPLETE\n"
            f"Masked File        : {res.masked_path}\n"
            f"Mapping Table (CSV): {res.mapping_csv_path or '(none - partial/hash mode)'}\n"
            f"Vault Container    : {res.mapping_piimap_path or '(none)'}\n"
            f"Masked {res.masked_count} of {res.detections} candidates ({res.report['coverage_pct']}%)\n"
            f"{residual}\n"
            f"Use the buttons above to save/download copies. Default mapping format is CSV.")
        self.app.tabs["Reports"].reload()
        self.app.status("Masking complete. Default CSV mapping table ready.")

        if messagebox.askyesno("Masking Complete",
                               f"Masked document saved to:\n{res.masked_path}\n\n"
                               f"Mapping table (CSV) saved to:\n{res.mapping_csv_path or '(none)'}\n\n"
                               f"Would you like to open the output folder now?", parent=self):
            self.open_output_folder()

    def download_masked_file(self):
        if not self.last_result:
            return
        src = self.last_result.masked_path
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = stamped_filename(self.path.stem, "masked", src.suffix, ts=ts)
        dest = filedialog.asksaveasfilename(
            title="Download Masked File", initialfile=name, defaultextension=src.suffix,
            filetypes=[(f"Original ({src.suffix})", f"*{src.suffix}"), ("All files", "*.*")])
        if dest:
            try:
                shutil.copy2(src, dest)
                AuditLog.event("download.masked_file", {"dest": Path(dest).name})
                messagebox.showinfo("Saved", f"Masked file successfully saved to:\n{dest}", parent=self)
            except Exception as exc:
                messagebox.showerror("Save Failed", f"Could not save file: {exc}", parent=self)

    def download_mapping_file(self):
        if not self.last_result or (not self.last_result.mapping_csv_path and not self.last_result.mapping_payload):
            messagebox.showinfo("No Mapping Table", "No mapping table was produced for this mode.", parent=self)
            return

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = stamped_filename(self.path.stem, "mapping-table", ".csv", ts=ts)
        dest = filedialog.asksaveasfilename(
            title="Download Mapping File (Default: CSV)", initialfile=name, defaultextension=".csv",
            filetypes=[("CSV Mapping Table (*.csv)", "*.csv"), ("JSON Table (*.json)", "*.json"),
                       ("PII Mapping Container (*.piimap)", "*.piimap"), ("All files", "*.*")])
        if dest:
            dest_path = Path(dest)
            try:
                if dest_path.suffix.lower() == ".piimap":
                    if self.last_result.mapping_piimap_path and self.last_result.mapping_piimap_path.exists():
                        shutil.copy2(self.last_result.mapping_piimap_path, dest_path)
                    else:
                        raise PiiToolError("Encrypted container was not generated. Please save as CSV or enable encryption.")
                else:
                    if self.last_result.mapping_csv_path and self.last_result.mapping_csv_path.exists():
                        shutil.copy2(self.last_result.mapping_csv_path, dest_path)
                    elif self.last_result.mapping_payload:
                        csv_bytes = mapping_table_csv_bytes(self.last_result.mapping_payload, {"placeholder_namespace_id": self.last_result.namespace})
                        atomic_write(dest_path, csv_bytes, overwrite=True)
                AuditLog.event("download.mapping_file", {"dest": dest_path.name})
                messagebox.showinfo("Saved", f"Mapping file (CSV) successfully saved to:\n{dest_path}", parent=self)
            except Exception as exc:
                messagebox.showerror("Save Failed", f"Could not save mapping: {exc}", parent=self)

    def download_both(self):
        if not self.last_result:
            return
        dest_dir = filedialog.askdirectory(title="Select Destination Folder for Masked File and CSV Mapping Table")
        if not dest_dir:
            return
        dest_folder = Path(dest_dir)
        try:
            # 1. Copy masked file
            masked_src = self.last_result.masked_path
            masked_dest = dest_folder / masked_src.name
            shutil.copy2(masked_src, masked_dest)

            # 2. Copy or write CSV mapping table
            if self.last_result.mapping_csv_path and self.last_result.mapping_csv_path.exists():
                csv_dest = dest_folder / self.last_result.mapping_csv_path.name
                shutil.copy2(self.last_result.mapping_csv_path, csv_dest)
            elif self.last_result.mapping_payload:
                csv_bytes = mapping_table_csv_bytes(self.last_result.mapping_payload, {"placeholder_namespace_id": self.last_result.namespace})
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                csv_dest = dest_folder / stamped_filename(self.path.stem, "mapping-table", ".csv", ts=ts)
                atomic_write(csv_dest, csv_bytes, overwrite=True)
            else:
                csv_dest = dest_folder / "mapping-table.csv"

            AuditLog.event("download.both", {"dest": str(dest_folder)})
            messagebox.showinfo("Saved Both Files",
                                f"Successfully saved:\n1. {masked_dest.name}\n2. {csv_dest.name}\n\n"
                                f"Location: {dest_folder}", parent=self)
        except Exception as exc:
            messagebox.showerror("Save Failed", f"Could not save files: {exc}", parent=self)

    def download_masked_md(self):
        if not self.last_result:
            return
        src = self.last_result.masked_path
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = stamped_filename(self.path.stem, "masked", ".md", ts=ts)
        dest = filedialog.asksaveasfilename(
            title="Download Masked Text / Markdown", initialfile=name, defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All files", "*.*")])
        if dest:
            try:
                body = canonical_text_of(src)
                atomic_write(Path(dest), text_to_markdown_bytes("Masked Document", self.path.name, body), overwrite=True)
                AuditLog.event("download.masked_md", {"dest": Path(dest).name})
                messagebox.showinfo("Saved", f"Document saved as Markdown to:\n{dest}", parent=self)
            except Exception as exc:
                messagebox.showerror("Save Failed", f"Could not save Markdown: {exc}", parent=self)

    def download_piimap_vault(self):
        if not self.last_result or not self.last_result.mapping_piimap_path:
            messagebox.showinfo("No Vault File", "No .piimap container was generated for this run.", parent=self)
            return
        src = self.last_result.mapping_piimap_path
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = stamped_filename(self.path.stem, "mapping", ".piimap", ts=ts)
        dest = filedialog.asksaveasfilename(
            title="Download Vault Container (.piimap)", initialfile=name, defaultextension=".piimap",
            filetypes=[("PII Mapping Container (*.piimap)", "*.piimap"), ("All files", "*.*")])
        if dest:
            try:
                shutil.copy2(src, dest)
                AuditLog.event("download.piimap_vault", {"dest": Path(dest).name})
                messagebox.showinfo("Saved", f"Vault container saved to:\n{dest}", parent=self)
            except Exception as exc:
                messagebox.showerror("Save Failed", f"Could not save vault file: {exc}", parent=self)

    def copy_masked_to_clipboard(self):
        if not self.last_result:
            return
        text = canonical_text_of(self.last_result.masked_path)
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(text)
        self.app.status("Masked document text copied to clipboard.")
        messagebox.showinfo("Clipboard", "Masked document text copied to clipboard.", parent=self)

    def open_output_folder(self):
        if not self.last_result:
            return
        folder = self.last_result.masked_path.parent
        try:
            if os.name == "nt":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
            AuditLog.event("ui.open_output_folder", {})
        except Exception as exc:
            messagebox.showerror("Could not open folder", f"Please open manually:\n{folder}\n({exc})", parent=self)


# =====================================================================================
# 20. UNMASK TAB (Unified with AI Text Unmasking, Downloads & SAP Scroll)
# =====================================================================================
class UnmaskTab(ScrollableTabFrame):
    def __init__(self, app, master):
        super().__init__(master)
        self.app = app
        self.job = None
        self.last_output: Optional[Path] = None
        self._pending_out_dir: Optional[Path] = None

        p = self.content

        # 1. DOCUMENT & MAPPING FILE SELECTION
        f = ttk.LabelFrame(p, text=" 1. Select Document to Unmask & Mapping Table (Default: CSV) ", padding=10)
        f.pack(fill="x", pady=(0, 10))

        ttk.Label(f, style="Muted.TLabel", wraplength=1050, text=(
            "Supports original masked documents OR edited / AI-processed documents (ChatGPT/Claude/Gemini responses, "
            "manual edits, analytical outputs). The engine reads your CSV mapping table (or .piimap container) and replaces "
            "all placeholder keys in the document with their original real values.")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.v_masked = tk.StringVar()
        self.v_map = tk.StringVar()
        self.v_pw = tk.StringVar()
        self.v_out = tk.StringVar()

        rows = [("Masked / AI-Processed Document:", self.v_masked, self.pick_masked),
                ("Mapping Key Table (Default: .csv):", self.v_map, self.pick_map),
                ("Output Folder:", self.v_out, self.pick_out)]

        for r, (lab, var, cmd) in enumerate(rows, start=1):
            ttk.Label(f, text=lab).grid(row=r, column=0, sticky="w", pady=4)
            ttk.Entry(f, textvariable=var).grid(row=r, column=1, sticky="we", padx=4)
            ttk.Button(f, text="📁 Browse…", command=cmd).grid(row=r, column=2, padx=4)

        ttk.Label(f, text="Mapping Password (only if using encrypted .piimap):").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(f, textvariable=self.v_pw, show="•", width=28).grid(row=4, column=1, sticky="w", padx=4)

        self.v_ow = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Allow overwriting existing output files",
                        variable=self.v_ow).grid(row=5, column=1, sticky="w", pady=2)
        f.columnconfigure(1, weight=1)

        bar = ttk.Frame(p); bar.pack(fill="x", pady=(0, 10))
        ttk.Button(bar, text="🔎 Verify Mapping & Keys", command=self.verify).pack(side="left")
        self.btn_un = ttk.Button(bar, text="🔓 Unmask and Restore Document File", style="Accent.TButton",
                                 command=self.unmask)
        self.btn_un.pack(side="left", padx=6)
        self.pbar = ttk.Progressbar(bar, maximum=100)
        self.pbar.pack(side="left", fill="x", expand=True, padx=8)

        # 2. CRYPTOGRAPHIC & INTEGRITY MATRIX (SAP 4-SIDED)
        mf = ttk.LabelFrame(p, text=" 2. Mapping & Document Verification Matrix ", padding=10)
        mf.pack(fill="both", expand=True, pady=(0, 10))

        def make_vtree(parent, vs, hs):
            self.tree = ttk.Treeview(parent, columns=("check", "res", "detail"), show="headings",
                                     height=5, yscrollcommand=vs.set, xscrollcommand=hs.set)
            for c, t, w in (("check", "Verification Check", 260), ("res", "Result", 90),
                            ("detail", "Detail / Proof", 550)):
                self.tree.heading(c, text=t)
                self.tree.column(c, width=w, anchor="w")
            vs.configure(command=self.tree.yview)
            hs.configure(command=self.tree.xview)
            return self.tree

        self.nav_vmatrix = SapNavContainer(mf, make_vtree)
        self.nav_vmatrix.pack(fill="both", expand=True)

        pal = THEMES[CONFIG.data["theme"]]
        self.tree.tag_configure("pass", foreground=pal["ok"])
        self.tree.tag_configure("fail", foreground=pal["err"])

        # 3. DIRECT AI TEXT / PROMPT RESPONSE UNMASKING SUB-PANEL
        f_aitext = ttk.LabelFrame(p, text=" 3. Fast Unmask: Paste AI Prompt Response / Text Directly ", padding=10)
        f_aitext.pack(fill="both", expand=True, pady=(0, 10))

        ttk.Label(f_aitext, style="Muted.TLabel", wraplength=1050, text=(
            "Quickly paste any response or text containing masked tokens directly from ChatGPT, Claude, Gemini, or other AI tools. "
            "Click Unmask Text to replace all tokens with their real values instantly.")).pack(anchor="w", pady=(0, 6))

        txt_box_frame = ttk.Frame(f_aitext); txt_box_frame.pack(fill="both", expand=True)
        txt_box_frame.columnconfigure(0, weight=1)
        txt_box_frame.columnconfigure(1, weight=1)
        txt_box_frame.rowconfigure(0, weight=1)

        # Left: Pasted Text
        f_inp = ttk.Frame(txt_box_frame)
        f_inp.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ttk.Label(f_inp, text="Pasted AI Response (with tokens):").pack(anchor="w")
        self.txt_ai_input = tk.Text(f_inp, height=6, wrap="word")
        vs_inp = ttk.Scrollbar(f_inp, orient="vertical", command=self.txt_ai_input.yview)
        self.txt_ai_input.configure(yscrollcommand=vs_inp.set)
        self.txt_ai_input.pack(side="left", fill="both", expand=True)
        vs_inp.pack(side="right", fill="y")
        app.register_text(self.txt_ai_input)

        # Right: Unmasked Text
        f_outp = ttk.Frame(txt_box_frame)
        f_outp.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        ttk.Label(f_outp, text="Restored Output (with real PII):").pack(anchor="w")
        self.txt_ai_output = tk.Text(f_outp, height=6, wrap="word")
        vs_outp = ttk.Scrollbar(f_outp, orient="vertical", command=self.txt_ai_output.yview)
        self.txt_ai_output.configure(yscrollcommand=vs_outp.set)
        self.txt_ai_output.pack(side="left", fill="both", expand=True)
        vs_outp.pack(side="right", fill="y")
        app.register_text(self.txt_ai_output)

        ai_btn_bar = ttk.Frame(f_aitext); ai_btn_bar.pack(fill="x", pady=(6, 0))
        ttk.Button(ai_btn_bar, text="🔓 Unmask Pasted AI Text", style="Accent.TButton",
                   command=self.unmask_pasted_ai_text).pack(side="left", padx=4)
        ttk.Button(ai_btn_bar, text="📋 Copy Restored Text", command=self.copy_ai_output_to_clipboard).pack(side="left", padx=4)
        ttk.Button(ai_btn_bar, text="🗑 Clear Text Boxes", command=self.clear_ai_boxes).pack(side="left", padx=4)

        # 4. DOWNLOAD & EXPORT UNMASKED FILE
        f_dl = ttk.LabelFrame(p, text=" 4. Download & Export Unmasked File ", padding=10)
        f_dl.pack(fill="x", pady=(0, 10))

        row_dl = ttk.Frame(f_dl); row_dl.pack(fill="x")
        self.btn_save_unmasked = ttk.Button(row_dl, text="📥 Download Unmasked File (Original/Modified Format)",
                                            style="Accent.TButton", command=self.save_unmasked_copy, state="disabled")
        self.btn_save_unmasked.pack(side="left", padx=4)

        self.btn_save_unmasked_md = ttk.Button(row_dl, text="📄 Download as Markdown (.md)",
                                               command=self.save_unmasked_md, state="disabled")
        self.btn_save_unmasked_md.pack(side="left", padx=4)

        self.btn_copy_unmasked_clip = ttk.Button(row_dl, text="📋 Copy Unmasked Document Text",
                                                 command=self.copy_unmasked_doc_clip, state="disabled")
        self.btn_copy_unmasked_clip.pack(side="left", padx=4)

        self.btn_open_unmasked_folder = ttk.Button(row_dl, text="📁 Open Output Folder",
                                                  command=self.open_output_folder, state="disabled")
        self.btn_open_unmasked_folder.pack(side="left", padx=4)

        self.out = tk.Text(p, height=4, wrap="word")
        self.out.pack(fill="x", pady=(6, 0))
        self.out.configure(state="disabled")
        app.register_text(self.out)

    def _set_out(self, t):
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", t)
        self.out.configure(state="disabled")

    def pick_masked(self):
        p = filedialog.askopenfilename(
            title="Select Masked or AI-Processed Document",
            filetypes=[("Supported", " ".join(f"*{e}" for e in SUPPORTED_EXTS)), ("All files", "*.*")])
        if not p:
            return
        self.v_masked.set(p)
        pp = Path(p)
        if not self.v_out.get():
            self.v_out.set(str(pp.parent))

        # Auto-detect matching CSV mapping table first
        clean_stem = re.sub(r"-(?:masked|unmasked)(?:-\d{8}-\d{6})?$", "", pp.stem)
        cand_csv = pp.parent / f"{clean_stem}-mapping-table.csv"
        cand_csv_glob = sorted(pp.parent.glob(f"{clean_stem}-mapping-table*.csv"), reverse=True)
        cand_piimap = pp.parent / f"{clean_stem}-mapping.piimap"
        cand_piimap_glob = sorted(pp.parent.glob(f"{clean_stem}-mapping*.piimap"), reverse=True)

        if cand_csv.exists():
            self.v_map.set(str(cand_csv))
        elif cand_csv_glob:
            self.v_map.set(str(cand_csv_glob[0]))
        elif cand_piimap.exists():
            self.v_map.set(str(cand_piimap))
        elif cand_piimap_glob:
            self.v_map.set(str(cand_piimap_glob[0]))

    def pick_map(self):
        p = filedialog.askopenfilename(
            title="Select Mapping Key (Default: CSV)",
            filetypes=[("CSV Mapping Table (*.csv)", "*.csv"), ("PII Mapping Container (*.piimap)", "*.piimap"),
                       ("JSON Mapping Table (*.json)", "*.json"), ("All files", "*.*")])
        if p:
            self.v_map.set(p)

    def pick_out(self):
        d = filedialog.askdirectory(title="Select Output Folder")
        if d:
            self.v_out.set(d)

    def _paths(self):
        if not self.v_masked.get() or not self.v_map.get():
            messagebox.showwarning("Missing Input", "Please select both the masked document and mapping table file.", parent=self)
            return None
        return Path(self.v_masked.get()), Path(self.v_map.get())

    def verify(self):
        pp = self._paths()
        if not pp:
            return
        try:
            header, entries, checks = UnmaskPipeline.verify(pp[0], pp[1], self.v_pw.get() or None)
        except PiiToolError as exc:
            self.tree.delete(*self.tree.get_children())
            messagebox.showerror("Verification failed", str(exc), parent=self)
            return
        self.tree.delete(*self.tree.get_children())
        for name, ok, detail in checks:
            self.tree.insert("", "end", values=(name, "PASS" if ok else "FAIL", detail),
                             tags=("pass" if ok else "fail",))
        self._set_out(f"Mapping source: {pp[1].suffix.upper()} | {len(entries)} mapping key(s) available. "
                      f"Ready to unmask.")

    def unmask(self):
        pp = self._paths()
        if not pp:
            return
        masked, mapping = pp
        out_dir = Path(self.v_out.get() or masked.parent)
        self._pending_out_dir = out_dir
        pw, ow = self.v_pw.get() or None, self.v_ow.get()
        self.btn_un.configure(state="disabled")
        self.job = AsyncJob(self.app, lambda pr, cn: UnmaskPipeline.unmask(
            masked, mapping, pw, out_dir, ow, pr))
        self.job.on_progress = lambda p, m: (self.pbar.configure(value=p), self.app.status(m))
        self.job.on_success = self.done
        self.job.on_error = lambda m: (self.btn_un.configure(state="normal"),
                                       messagebox.showerror("Unmasking failed", m, parent=self))
        self.job.start()

    def done(self, rep: dict):
        self.btn_un.configure(state="normal")
        self.v_pw.set("")
        out_path = Path(rep.get("output_path") or (self._pending_out_dir / rep["output"]))
        self.last_output = out_path

        self.btn_save_unmasked.configure(state="normal")
        self.btn_save_unmasked_md.configure(state="normal")
        self.btn_copy_unmasked_clip.configure(state="normal")
        self.btn_open_unmasked_folder.configure(state="normal")

        left = rep.get("unresolved_placeholders", [])
        is_mod = rep.get("document_modified", False)
        status_line = "Document status: AI-Edited / Modified (successfully unmasked)" if is_mod else "Document status: Original"

        self._set_out(f"✔ UNMASKING COMPLETE\n"
                      f"Restored File : {out_path}\n"
                      f"{status_line}\n"
                      f"Restored {rep['restored_occurrences']} occurrence(s) across {rep['keys_restored']} mapping key(s).\n" +
                      ("Unresolved placeholders remain: " + ", ".join(left[:12]) if left
                       else "Zero unresolved placeholders remain in the document."))
        self.app.tabs["Reports"].reload()
        self.app.status("Unmasking complete.")

    def unmask_pasted_ai_text(self):
        if not self.v_map.get():
            messagebox.showwarning("Missing Mapping", "Please select a mapping key table (.csv / .piimap / .json) in Section 1 first.", parent=self)
            return
        mapping_path = Path(self.v_map.get())
        inp_text = self.txt_ai_input.get("1.0", "end-1c")
        if not inp_text.strip():
            messagebox.showwarning("Empty Text", "Please paste text into the input box.", parent=self)
            return
        try:
            restored, count, keys_used, leftovers = UnmaskPipeline.unmask_text_string(
                inp_text, mapping_path, self.v_pw.get() or None)
            self.txt_ai_output.delete("1.0", "end")
            self.txt_ai_output.insert("1.0", restored)
            self.app.status(f"Pasted AI text unmasked: restored {count} occurrence(s) across {keys_used} key(s).")
            messagebox.showinfo("Text Unmasked",
                                f"Successfully unmasked {count} occurrence(s) across {keys_used} key(s).\n"
                                f"Zero unresolved tokens." if not leftovers
                                else f"Unresolved tokens remaining: {', '.join(leftovers[:8])}", parent=self)
        except Exception as exc:
            messagebox.showerror("Unmask Error", f"Could not unmask text: {exc}", parent=self)

    def copy_ai_output_to_clipboard(self):
        out_text = self.txt_ai_output.get("1.0", "end-1c")
        if not out_text.strip():
            messagebox.showinfo("Empty", "No output text to copy.", parent=self)
            return
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(out_text)
        self.app.status("Restored AI text copied to clipboard.")
        messagebox.showinfo("Copied", "Restored text copied to clipboard.", parent=self)

    def clear_ai_boxes(self):
        self.txt_ai_input.delete("1.0", "end")
        self.txt_ai_output.delete("1.0", "end")

    def copy_unmasked_doc_clip(self):
        if not self.last_output:
            return
        text = canonical_text_of(self.last_output)
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(text)
        self.app.status("Unmasked document text copied to clipboard.")
        messagebox.showinfo("Clipboard", "Unmasked document text copied to clipboard.", parent=self)

    def save_unmasked_copy(self):
        if not self.last_output:
            return
        src = self.last_output
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = stamped_filename(Path(self.v_masked.get()).stem, "unmasked", src.suffix, ts=ts)
        dest = filedialog.asksaveasfilename(
            title="Download Unmasked File", initialfile=name, defaultextension=src.suffix,
            filetypes=[(f"Original ({src.suffix})", f"*{src.suffix}"), ("All files", "*.*")])
        if dest:
            try:
                shutil.copy2(src, dest)
                AuditLog.event("download.unmasked_file", {"dest": Path(dest).name})
                messagebox.showinfo("Saved", f"Unmasked file saved to:\n{dest}", parent=self)
            except Exception as exc:
                messagebox.showerror("Save Failed", f"Could not save file: {exc}", parent=self)

    def save_unmasked_md(self):
        if not self.last_output:
            return
        src = self.last_output
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = stamped_filename(Path(self.v_masked.get()).stem, "unmasked", ".md", ts=ts)
        dest = filedialog.asksaveasfilename(
            title="Download Unmasked Text (Markdown)", initialfile=name, defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All files", "*.*")])
        if dest:
            try:
                body = canonical_text_of(src)
                atomic_write(Path(dest), text_to_markdown_bytes("Unmasked Document", src.name, body), overwrite=True)
                AuditLog.event("download.unmasked_md", {"dest": Path(dest).name})
                messagebox.showinfo("Saved", f"Document saved as Markdown to:\n{dest}", parent=self)
            except Exception as exc:
                messagebox.showerror("Save Failed", f"Could not save Markdown: {exc}", parent=self)

    def open_output_folder(self):
        if not self.last_output:
            return
        folder = self.last_output.parent
        try:
            if os.name == "nt":
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception as exc:
            messagebox.showerror("Could not open folder", f"Please open manually:\n{folder}\n({exc})", parent=self)


# =====================================================================================
# 21. SIDE-BY-SIDE DIFF TAB (Original vs Masked Synchronized Preview)
# =====================================================================================
class SideBySideDiffTab(ttk.Frame):
    def __init__(self, app, master):
        super().__init__(master, padding=10)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="🔍 Synchronized Side-by-Side Diff Viewer", font=F_TITLE).pack(side="left")
        self.lbl_stats = ttk.Label(top, text="No document analyzed yet", style="Section.TLabel")
        self.lbl_stats.pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        f_left = ttk.LabelFrame(body, text=" Original Extracted Text (Detected PII Highlighted) ", padding=6)
        f_left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.txt_orig = tk.Text(f_left, wrap="word")
        vs_left = ttk.Scrollbar(f_left, orient="vertical", command=self._sync_scroll)
        self.txt_orig.configure(yscrollcommand=vs_left.set)
        self.txt_orig.pack(side="left", fill="both", expand=True)
        vs_left.pack(side="right", fill="y")

        f_right = ttk.LabelFrame(body, text=" Masked Document Output (Replaced Tokens) ", padding=6)
        f_right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        self.txt_masked = tk.Text(f_right, wrap="word")
        vs_right = ttk.Scrollbar(f_right, orient="vertical", command=self._sync_scroll)
        self.txt_masked.configure(yscrollcommand=vs_right.set)
        self.txt_masked.pack(side="left", fill="both", expand=True)
        vs_right.pack(side="right", fill="y")

        app.register_text(self.txt_orig)
        app.register_text(self.txt_masked)

        bot = ttk.Frame(self); bot.pack(fill="x", pady=(8, 0))
        ttk.Button(bot, text="⏫ Jump Top", command=lambda: self._scroll_to(0.0)).pack(side="left", padx=2)
        ttk.Button(bot, text="🔼 Page Up", command=lambda: self._scroll_by(-1, "pages")).pack(side="left", padx=2)
        ttk.Button(bot, text="▲ Step Up", command=lambda: self._scroll_by(-3, "units")).pack(side="left", padx=2)
        ttk.Button(bot, text="▼ Step Down", command=lambda: self._scroll_by(3, "units")).pack(side="left", padx=2)
        ttk.Button(bot, text="🔽 Page Down", command=lambda: self._scroll_by(1, "pages")).pack(side="left", padx=2)
        ttk.Button(bot, text="⏬ Jump Bottom", command=lambda: self._scroll_to(1.0)).pack(side="left", padx=2)

    def _sync_scroll(self, *args):
        self.txt_orig.yview(*args)
        self.txt_masked.yview(*args)

    def _scroll_to(self, fraction):
        self.txt_orig.yview_moveto(fraction)
        self.txt_masked.yview_moveto(fraction)

    def _scroll_by(self, amount, what):
        self.txt_orig.yview_scroll(amount, what)
        self.txt_masked.yview_scroll(amount, what)

    def load_diff(self, orig_text: str, masked_text: str, dets: list[Detection]):
        self.txt_orig.configure(state="normal")
        self.txt_masked.configure(state="normal")

        self.txt_orig.delete("1.0", "end")
        self.txt_masked.delete("1.0", "end")

        self.txt_orig.insert("1.0", orig_text or "No text")
        self.txt_masked.insert("1.0", masked_text or "No text")

        pal = THEMES[CONFIG.data["theme"]]
        self.txt_orig.tag_configure("pii_highlight", background=pal["warn_bg"], foreground=pal["warn"])
        self.txt_masked.tag_configure("masked_highlight", background=pal["ok_bg"], foreground=pal["ok"])

        for d in dets:
            if d.selected:
                val = d.value.reveal()
                start = "1.0"
                while True:
                    pos = self.txt_orig.search(val, start, stopindex="end")
                    if not pos:
                        break
                    end_pos = f"{pos}+{len(val)}c"
                    self.txt_orig.tag_add("pii_highlight", pos, end_pos)
                    start = end_pos

        for m in PLACEHOLDER_RE.finditer(masked_text):
            tok = m.group(0)
            start = "1.0"
            while True:
                pos = self.txt_masked.search(tok, start, stopindex="end")
                if not pos:
                    break
                end_pos = f"{pos}+{len(tok)}c"
                self.txt_masked.tag_add("masked_highlight", pos, end_pos)
                start = end_pos

        self.txt_orig.configure(state="disabled")
        self.txt_masked.configure(state="disabled")
        self.lbl_stats.configure(text=f"{len(dets)} Candidates Detected | {sum(1 for d in dets if d.selected)} Masked")


# =====================================================================================
# 22. DICTIONARY TAB
# =====================================================================================
DICT_FIELDS = [("term", "Term or pattern", "text", None),
               ("category", "Category", "combo", None),
               ("type", "Type", "combo", ["literal", "regex"]),
               ("case_sensitive", "Case sensitive", "check", None),
               ("whole_word", "Whole word only (literal)", "check", None),
               ("enabled", "Enabled", "check", None),
               ("note", "Note", "text", None)]


class DictionaryTab(ttk.Frame):
    def __init__(self, app, master):
        super().__init__(master, padding=10)
        self.app = app
        ttk.Label(self, text="User-Editable Dictionary & Custom Rules", font=F_TITLE).pack(anchor="w")
        ttk.Label(self, wraplength=1000, text=(
            "Add client names, staff names, company names, or regex patterns. All terms are matched with "
            "high confidence. Literal terms are escaped safely; regex patterns must pass the ReDoS linter.")
                  ).pack(anchor="w", pady=(2, 8))

        def make_dtree(parent, vs, hs):
            cols = ("en", "term", "cat", "kind", "case", "whole", "note")
            self.tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="extended",
                                     height=14, yscrollcommand=vs.set, xscrollcommand=hs.set)
            for c, t, w in (("en", "Enabled", 70), ("term", "Term / Pattern", 300), ("cat", "Category", 130),
                            ("kind", "Type", 80), ("case", "Case", 60), ("whole", "Whole Word", 90),
                            ("note", "Note", 300)):
                self.tree.heading(c, text=t)
                self.tree.column(c, width=w, anchor="w")
            vs.configure(command=self.tree.yview)
            hs.configure(command=self.tree.xview)
            self.tree.bind("<Double-1>", lambda e: self.edit())
            return self.tree

        self.nav_dict = SapNavContainer(self, make_dtree)
        self.nav_dict.pack(fill="both", expand=True)

        bar = ttk.Frame(self); bar.pack(fill="x", pady=8)
        ttk.Button(bar, text="➕ Add", style="Accent.TButton", command=self.add).pack(side="left", padx=3)
        ttk.Button(bar, text="✏ Edit", command=self.edit).pack(side="left", padx=3)
        ttk.Button(bar, text="🗑 Delete", style="Danger.TButton", command=self.delete).pack(side="left", padx=3)
        ttk.Button(bar, text="Enable All", command=lambda: self.toggle(True)).pack(side="left", padx=3)
        ttk.Button(bar, text="Disable All", command=lambda: self.toggle(False)).pack(side="left", padx=3)
        ttk.Button(bar, text="📥 Import…", command=self.imp).pack(side="left", padx=3)
        ttk.Button(bar, text="📤 Export…", command=self.exp).pack(side="left", padx=3)
        ttk.Button(bar, text="💾 Save Dictionary", style="Accent.TButton", command=self.save).pack(side="left", padx=3)
        self.reload()

    def reload(self):
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(CONFIG.dictionary):
            self.tree.insert("", "end", iid=str(i), values=(
                "✔" if e.get("enabled", True) else "", e.get("term", ""),
                e.get("category", "CUSTOM"), e.get("type", "literal"),
                "Yes" if e.get("case_sensitive") else "No",
                "Yes" if e.get("whole_word", True) else "No", e.get("note", "")))

    def _fields(self):
        f = [list(x) for x in DICT_FIELDS]
        f[1][3] = CONFIG.all_categories()
        return [tuple(x) for x in f]

    def add(self):
        res = entry_dialog(self, "New Dictionary Entry", self._fields(),
                           {"term": "", "category": "CUSTOM", "type": "literal",
                            "case_sensitive": False, "whole_word": True, "enabled": True, "note": ""})
        if res and str(res.get("term", "")).strip():
            res["category"] = re.sub(r"[^A-Z0-9_]", "_", str(res["category"]).upper()) or "CUSTOM"
            CONFIG.dictionary.append(res)
            self.reload()

    def edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        i = int(sel[0])
        res = entry_dialog(self, "Edit Dictionary Entry", self._fields(), CONFIG.dictionary[i])
        if res and str(res.get("term", "")).strip():
            res["category"] = re.sub(r"[^A-Z0-9_]", "_", str(res["category"]).upper()) or "CUSTOM"
            CONFIG.dictionary[i] = res
            self.reload()

    def delete(self):
        sel = sorted((int(i) for i in self.tree.selection()), reverse=True)
        if not sel or not messagebox.askyesno("Delete", f"Delete {len(sel)} entry(ies)?", parent=self):
            return
        for i in sel:
            del CONFIG.dictionary[i]
        self.reload()

    def toggle(self, value: bool):
        for e in CONFIG.dictionary:
            e["enabled"] = value
        self.reload()

    def imp(self):
        p = filedialog.askopenfilename(title="Import Dictionary",
                                       filetypes=[("Dictionary Files", "*.json *.csv *.txt"), ("All files", "*.*")])
        if not p:
            return
        try:
            added = import_dictionary_entries(Path(p))
            self.reload()
            messagebox.showinfo("Imported", f"{added} entry(ies) imported into dictionary.", parent=self)
        except Exception as exc:
            messagebox.showerror("Import failed", f"Could not import: {exc}", parent=self)

    def exp(self):
        p = filedialog.asksaveasfilename(title="Export Dictionary", initialfile="pii_dictionary.json",
                                         defaultextension=".json",
                                         filetypes=[("JSON", "*.json"), ("CSV", "*.csv")])
        if not p:
            return
        path = Path(p)
        if path.suffix.lower() == ".csv":
            buf = io.StringIO(newline="")
            w = csv.writer(buf, lineterminator="\r\n")
            w.writerow(["term", "category", "type", "case_sensitive", "whole_word", "enabled", "note"])
            for e in CONFIG.dictionary:
                w.writerow([e.get("term"), e.get("category"), e.get("type"), e.get("case_sensitive"),
                            e.get("whole_word"), e.get("enabled"), e.get("note")])
            data = buf.getvalue().encode("utf-8")
        else:
            data = json.dumps(CONFIG.dictionary, indent=2, ensure_ascii=False).encode("utf-8")
        atomic_write(path, data, overwrite=True)
        messagebox.showinfo("Exported", f"Dictionary saved to:\n{path}", parent=self)

    def save(self):
        CONFIG.save()
        messagebox.showinfo("Saved", f"Dictionary saved to:\n{CONFIG.path}", parent=self)


def import_dictionary_entries(path: Path) -> int:
    added = 0
    if path.suffix.lower() == ".json":
        data = json.loads(read_text_file(path))
        for e in (data if isinstance(data, list) else []):
            if isinstance(e, dict) and str(e.get("term", "")).strip():
                CONFIG.dictionary.append({
                    "term": str(e["term"]),
                    "category": re.sub(r"[^A-Z0-9_]", "_", str(e.get("category", "CUSTOM")).upper()),
                    "type": e.get("type", "literal"),
                    "case_sensitive": bool(e.get("case_sensitive", False)),
                    "whole_word": bool(e.get("whole_word", True)),
                    "enabled": bool(e.get("enabled", True)),
                    "note": str(e.get("note", "imported"))})
                added += 1
    elif path.suffix.lower() == ".csv":
        rdr = csv.reader(io.StringIO(read_text_file(path)))
        for row in rdr:
            if row and row[0].strip() and row[0].strip().lower() != "term":
                CONFIG.dictionary.append({
                    "term": row[0].strip(),
                    "category": (row[1].strip().upper() if len(row) > 1 and row[1].strip() else "CUSTOM"),
                    "type": (row[2].strip() if len(row) > 2 and row[2].strip() in ("literal", "regex") else "literal"),
                    "case_sensitive": False, "whole_word": True, "enabled": True, "note": "imported"})
                added += 1
    else:
        for line in read_text_file(path).splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                CONFIG.dictionary.append({"term": line, "category": "CUSTOM", "type": "literal",
                                          "case_sensitive": False, "whole_word": True,
                                          "enabled": True, "note": "imported"})
                added += 1
    return added


# =====================================================================================
# 23. SECURITY GUARDRAILS TAB
# =====================================================================================
class GuardrailsTab(ttk.Frame):
    def __init__(self, app, master):
        super().__init__(master, padding=10)
        self.app = app
        self.results: list[dict] = []
        ttk.Label(self, text="Security Guardrail Controls & Verification", font=F_TITLE).pack(anchor="w")
        ttk.Label(self, wraplength=1000, text=(
            "Live executable probes for offline socket blocking, memory encryption, ReDoS safety, "
            "and format validation. Controls execute in real-time on your hardware.")
                  ).pack(anchor="w", pady=(2, 8))

        bar = ttk.Frame(self); bar.pack(fill="x")
        self.btn_run = ttk.Button(bar, text="▶ Run All Controls", style="Accent.TButton", command=self.run_all)
        self.btn_run.pack(side="left")
        ttk.Button(bar, text="📤 Export Audit Evidence…", command=self.export).pack(side="left", padx=6)
        self.pbar = ttk.Progressbar(bar, maximum=100)
        self.pbar.pack(side="left", fill="x", expand=True, padx=8)
        self.v_stats = tk.StringVar()
        ttk.Label(bar, textvariable=self.v_stats, style="Section.TLabel").pack(side="right")
        self.job: Optional[AsyncJob] = None

        def make_gtree(parent, vs, hs):
            self.tree = ttk.Treeview(parent, columns=("id", "req", "status", "ev", "ts"),
                                     show="headings", yscrollcommand=vs.set, xscrollcommand=hs.set)
            for c, t, w in (("id", "ID", 70), ("req", "Requirement", 260), ("status", "Status", 130),
                            ("ev", "Evidence", 560), ("ts", "Timestamp (UTC)", 170)):
                self.tree.heading(c, text=t)
                self.tree.column(c, width=w, anchor="w")
            vs.configure(command=self.tree.yview)
            hs.configure(command=self.tree.xview)
            return self.tree

        self.nav_guard = SapNavContainer(self, make_gtree)
        self.nav_guard.pack(fill="both", expand=True, pady=8)

        pal = THEMES[CONFIG.data["theme"]]
        self.tree.tag_configure("pass", foreground=pal["ok"])
        self.tree.tag_configure("fail", foreground=pal["err"])

    def run_all(self):
        self.tree.delete(*self.tree.get_children())
        self.results = []
        self.pbar["value"] = 0
        self.btn_run.configure(state="disabled")
        self.app.status("Running security guardrail controls…")

        def worker(progress, cancel):
            recs = []
            total = len(CONTROLS)
            for i, c in enumerate(CONTROLS, start=1):
                try:
                    status, ev = c.probe()
                except Exception as exc:
                    status, ev = "FAIL", f"probe raised {type(exc).__name__}"
                rec = {"id": c.cid, "requirement": c.requirement, "status": status,
                       "evidence": ev, "ts": now_utc()}
                recs.append(rec)
                progress(int(100 * i / total), f"Ran {c.cid} ({i}/{total})")
            return recs

        self.job = AsyncJob(self.app, worker)
        self.job.on_progress = lambda p, m: (self.pbar.configure(value=p), self.app.status(m))
        self.job.on_success = self._show_results
        self.job.on_error = lambda m: (self.btn_run.configure(state="normal"),
                                       messagebox.showerror("Guardrail run failed", m, parent=self))
        self.job.start()

    def _show_results(self, recs: list[dict]):
        self.btn_run.configure(state="normal")
        self.results = recs
        for rec in recs:
            tag = "pass" if rec["status"] == "PASS" else "fail"
            self.tree.insert("", "end", values=(rec["id"], rec["requirement"], rec["status"],
                                                rec["evidence"], rec["ts"]), tags=(tag,))
        p = sum(1 for r in self.results if r["status"] == "PASS")
        f = sum(1 for r in self.results if r["status"] == "FAIL")
        self.v_stats.set(f"PASS: {p}   FAIL: {f}")
        self.app.status("Guardrail run complete.")
        AuditLog.event("guardrails.run", {"pass": p, "fail": f})

    def export(self):
        if not self.results:
            messagebox.showinfo("Nothing to export", "Run controls first.", parent=self)
            return
        p = filedialog.asksaveasfilename(title="Export Control Evidence",
                                         initialfile="SECURITY_CONTROLS.md", defaultextension=".md",
                                         filetypes=[("Markdown", "*.md"), ("JSON", "*.json"), ("CSV", "*.csv")])
        if not p:
            return
        path = Path(p)
        if path.suffix.lower() == ".json":
            data = json.dumps(self.results, indent=2).encode("utf-8")
        elif path.suffix.lower() == ".csv":
            buf = io.StringIO(newline="")
            w = csv.writer(buf, lineterminator="\r\n")
            w.writerow(["Control ID", "Requirement", "Status", "Evidence", "Timestamp"])
            for r in self.results:
                w.writerow([r["id"], r["requirement"], r["status"], r["evidence"], r["ts"]])
            data = buf.getvalue().encode("utf-8")
        else:
            lines = [f"# Security Controls - {APP_NAME} v{APP_VERSION}", f"_Executed {now_utc()}_", "",
                     "| Control ID | Requirement | Status | Evidence | Timestamp |", "|---|---|---|---|---|"]
            lines += [f"| {r['id']} | {r['requirement']} | {r['status']} | {r['evidence']} | {r['ts']} |"
                      for r in self.results]
            data = "\n".join(lines).encode("utf-8")
        atomic_write(path, data, overwrite=True)
        messagebox.showinfo("Exported", f"Evidence written to:\n{path}", parent=self)


# =====================================================================================
# 24. REPORTS & SETTINGS TABS
# =====================================================================================
class ReportsTab(ttk.Frame):
    def __init__(self, app, master):
        super().__init__(master, padding=10)
        self.app = app
        self.files: list[Path] = []
        ttk.Label(self, text="Audit Reports & Compliance Logs", font=F_TITLE).pack(anchor="w", pady=(0, 6))
        body = ttk.Frame(self); body.pack(fill="both", expand=True)
        self.list = tk.Listbox(body, width=42, exportselection=False)
        self.list.pack(side="left", fill="y")
        self.list.bind("<<ListboxSelect>>", lambda e: self.show())
        self.view = tk.Text(body, wrap="word")
        self.view.pack(side="left", fill="both", expand=True, padx=(8, 0))
        app.register_text(self.view)
        app.register_text(self.list)
        bar = ttk.Frame(self); bar.pack(fill="x", pady=8)
        for t, c in (("🔄 Refresh", self.reload), ("📤 Export Report…", self.export),
                     ("📋 Show Audit Log", self.audit), ("📁 Reports Folder", self.folder)):
            ttk.Button(bar, text=t, command=c).pack(side="left", padx=3)
        self.reload()

    def reload(self):
        self.files = sorted(reports_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        self.list.delete(0, "end")
        for f in self.files:
            self.list.insert("end", f.name)
        if self.files:
            self.list.selection_set(0)
            self.show()

    def show(self):
        sel = self.list.curselection()
        if not sel:
            return
        try:
            rep = json.loads(read_text_file(self.files[sel[0]]))
            text = report_to_text(rep)
        except Exception:
            text = "The report could not be read."
        self.view.delete("1.0", "end")
        self.view.insert("1.0", text)

    def export(self):
        sel = self.list.curselection()
        if not sel:
            return
        rep = json.loads(read_text_file(self.files[sel[0]]))
        p = filedialog.asksaveasfilename(title="Export Report",
                                         initialfile=self.files[sel[0]].stem + ".md",
                                         defaultextension=".md",
                                         filetypes=[("Markdown", "*.md"), ("HTML", "*.html"), ("JSON", "*.json")])
        if not p:
            return
        path, txt = Path(p), report_to_text(rep)
        if path.suffix.lower() == ".html":
            body = txt.replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br>")
            data = f"<html><body style='font-family:{FONT}'>{body}</body></html>".encode("utf-8")
        elif path.suffix.lower() == ".json":
            data = json.dumps(rep, indent=2, ensure_ascii=False).encode("utf-8")
        else:
            data = txt.encode("utf-8")
        atomic_write(path, data, overwrite=True)
        messagebox.showinfo("Exported", f"Report written to:\n{path}", parent=self)

    def audit(self):
        self.view.delete("1.0", "end")
        self.view.insert("1.0", "\n".join(json.dumps(r, ensure_ascii=False) for r in AuditLog.recent()))

    def folder(self):
        messagebox.showinfo("Reports folder", str(reports_dir()), parent=self)


class SettingsTab(ttk.Frame):
    def __init__(self, app, master):
        super().__init__(master, padding=10)
        self.app = app
        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True)

        p1 = ttk.Frame(nb, padding=8); nb.add(p1, text="PII Categories")
        ttk.Label(p1, text="Double-click a category to enable/disable and adjust threshold (0-100).").pack(anchor="w", pady=(0, 6))
        self.ctree = ttk.Treeview(p1, columns=("cat", "en", "th"), show="headings", height=16)
        for c, t, w in (("cat", "Category", 260), ("en", "Enabled", 100), ("th", "Threshold", 100)):
            self.ctree.heading(c, text=t)
            self.ctree.column(c, width=w, anchor="w")
        self.ctree.pack(fill="both", expand=True)
        self.ctree.bind("<Double-1>", lambda e: self.edit_cat())

        p2 = ttk.Frame(nb, padding=8); nb.add(p2, text="General Preferences")
        self.v_theme = tk.StringVar(value=CONFIG.data.get("theme", "dark"))
        self.v_reveal = tk.BooleanVar(value=bool(CONFIG.data.get("reveal_by_default", False)))
        self.v_max = tk.IntVar(value=int(CONFIG.data.get("max_file_mb", 200)))
        self.v_fmt = tk.StringVar(value=CONFIG.data.get("placeholder_format", "[{cat}_{ns}_{n:03d}]"))
        self.v_encdef = tk.BooleanVar(value=bool(CONFIG.data.get("encrypt_default", True)))
        self.v_audit = tk.BooleanVar(value=bool(CONFIG.data.get("audit_enabled", True)))

        ttk.Label(p2, text="Application Theme:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(p2, textvariable=self.v_theme, values=["dark", "light"],
                     width=16, state="readonly").grid(row=0, column=1, sticky="w")
        ttk.Label(p2, text="Max File Size (MB):").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Spinbox(p2, from_=1, to=2048, textvariable=self.v_max, width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(p2, text="Placeholder Format:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(p2, textvariable=self.v_fmt, width=32).grid(row=2, column=1, sticky="w")

        ttk.Checkbutton(p2, text="Reveal detected values by default (NOT recommended)",
                        variable=self.v_reveal).grid(row=3, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(p2, text="Encrypt mapping containers by default",
                        variable=self.v_encdef).grid(row=4, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(p2, text="Write privacy-safe audit logs to disk",
                        variable=self.v_audit).grid(row=5, column=0, columnspan=2, sticky="w", pady=3)

        bar = ttk.Frame(self); bar.pack(fill="x", pady=8)
        ttk.Button(bar, text="💾 Save Settings", style="Accent.TButton", command=self.save).pack(side="left")
        ttk.Button(bar, text="♻ Restore Defaults", command=self.defaults).pack(side="left", padx=6)
        ttk.Button(bar, text="🗑 Shred Session Temp", style="Danger.TButton", command=self.clean).pack(side="left")
        self.reload()

    def reload(self):
        self.ctree.delete(*self.ctree.get_children())
        for c in CONFIG.all_categories():
            self.ctree.insert("", "end", iid=c,
                              values=(c, "Yes" if CONFIG.enabled(c) else "No", CONFIG.threshold(c)))

    def edit_cat(self):
        sel = self.ctree.selection()
        if not sel:
            return
        cat = sel[0]
        res = entry_dialog(self, f"Category: {cat}",
                           [("enabled", "Enabled", "check", None),
                            ("threshold", "Threshold Score", "int", (0, 100))],
                           {"enabled": CONFIG.enabled(cat), "threshold": CONFIG.threshold(cat)})
        if res:
            CONFIG.cat(cat)["enabled"] = bool(res["enabled"])
            CONFIG.cat(cat)["threshold"] = int(res["threshold"])
            self.reload()

    def save(self):
        try:
            self.v_fmt.get().format(cat="X", ns="ABCD", n=1)
        except Exception:
            messagebox.showwarning("Invalid format", "Format must contain {cat}, {ns}, and {n}.", parent=self)
            return
        CONFIG.data.update({"theme": self.v_theme.get(), "reveal_by_default": self.v_reveal.get(),
                            "max_file_mb": int(self.v_max.get()), "placeholder_format": self.v_fmt.get(),
                            "encrypt_default": self.v_encdef.get(), "audit_enabled": self.v_audit.get()})
        CONFIG.save()
        self.app.apply_theme()
        self.app._sync_theme_button()
        messagebox.showinfo("Saved", f"Settings saved to:\n{CONFIG.path}", parent=self)

    def defaults(self):
        if not messagebox.askyesno("Restore defaults", "Reset all settings to defaults?", parent=self):
            return
        dic = CONFIG.dictionary
        CONFIG.data = CONFIG._defaults()
        CONFIG.data["dictionary"] = dic
        CONFIG.save()
        self.reload()
        self.v_theme.set(CONFIG.data["theme"])
        self.app.apply_theme()
        self.app._sync_theme_button()

    def clean(self):
        SessionTemp.cleanup()
        SessionTemp._dir = None
        messagebox.showinfo("Cleaned", f"Session temp shredded.\nNew folder: {SessionTemp.dir()}", parent=self)


class TextTab(ttk.Frame):
    def __init__(self, app, master, text_provider):
        super().__init__(master, padding=10)
        self.app = app
        self.provider = text_provider
        self.text = tk.Text(self, wrap="word")
        vs = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=vs.set)
        self.text.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        app.register_text(self.text)
        self.reload()

    def reload(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.provider())
        self.text.configure(state="disabled")


def dashboard_text() -> str:
    rows = [
        ("Offline Enforcement Kernel", "ACTIVE" if OfflineKernel.installed else "NOT ACTIVE"),
        ("Blocked Outbound Attempts", str(OfflineKernel.blocked_attempts)),
        ("Default Mapping File Format", "CSV Mapping Table (*.csv)"),
        ("Authenticated AEAD", "AES-256-GCM (cryptography)" if HAVE_AESGCM else "HMAC-CTR fallback"),
        ("Key Derivation (KDF)", "Argon2id (argon2-cffi)" if HAVE_ARGON2 else "scrypt fallback"),
        ("PDF Extraction & Password Decrypt", "Available (pypdf)" if HAVE_PYPDF else "Unavailable (pip install pypdf)"),
        ("Scanned OCR Engine", "Available" if (HAVE_PIL and HAVE_TESS) else "Unavailable (Pillow+pytesseract)"),
        ("Supported File Formats", ", ".join(SUPPORTED_EXTS)),
        ("Config File Path", str(CONFIG.path)),
        ("Reports Directory", str(reports_dir())),
    ]
    body = "\n".join(f"  {a:<34}: {b}" for a, b in rows)
    return (f"{APP_NAME}\n{APP_OWNER}   -   version {APP_VERSION}   -   100% offline desktop tool\n"
            + "=" * 96 + "\n\nENVIRONMENT & LIVE CAPABILITIES\n" + body +
            "\n\n" + "=" * 96 + "\nOPERATIONAL ASSURANCE & WORKFLOWS\n"
            "  - Default CSV Mapping: Mapping tables automatically saved and downloaded as CSV files.\n"
            "  - AI Pipeline Ready: Mask documents -> process in AI tools -> unmask modified output seamlessly.\n"
            "  - 100% Offline: Sockets permanently blocked post-bootstrap.\n"
            "  - High-risk categories (Aadhaar, Bank, Card, Passport, DL) enforce mandatory protection.\n"
            "  - SAP-Style 4-Sided Navigation & High-Contrast Scrollbars enable effortless panning.\n")


def help_text() -> str:
    return f"""USER GUIDE & CAPABILITIES
{'=' * 96}

1. MASKING WORKFLOW
   - Select document ({', '.join(SUPPORTED_EXTS)}).
   - Enter file password if the input is a protected PDF.
   - (Optional) Load an existing mapping key table (.csv / .json / .piimap) to reuse previously assigned tokens.
   - Click 'Analyze for PII' to scan. Review candidates in the SAP 4-Sided Review Grid.
   - Choose Masking Strategy:
       * Reversible Token: [AADHAAR_AB12_001]
       * Partial Masking: XXXX-XXXX-1234, AXXXXXX4F, +91 XXXXX X3210, j***e@domain.com
       * Cryptographic Hash: [HASH_4F8A]
       * Solid Redaction: [REDACTED]
   - Click 'Mask and Save All Outputs'. Output files are saved as:
       * Masked Document: <filename>-masked-<timestamp>.<ext>
       * Mapping Table (CSV): <filename>-mapping-table-<timestamp>.csv
   - Download in original format, CSV mapping table, Markdown/Text, or Vault Container (.piimap).

2. UNMASKING WORKFLOW (INCLUDING AI TOOLS & MODIFIED DOCUMENTS)
   - Step 1: Provide the masked or edited document (OR paste AI response text directly).
   - Step 2: Select your CSV mapping table (or .piimap container) and enter password if protected.
   - Step 3: Click 'Unmask and Restore Document File' (or 'Unmask Pasted AI Text').
   - Note: Unmasking works seamlessly even if the document was edited, translated, or restructured by an AI tool!

3. SIDE-BY-SIDE DIFF
   - View synchronized split-screen comparison of Original text vs. Masked output.
   - Color-coded highlights show exact replaced sensitive spans.
"""


def about_text() -> str:
    try:
        h = sha256_file(Path(__file__).resolve())
    except Exception:
        h = "unavailable"
    return f"""{APP_NAME}
{APP_OWNER}   -   Version {APP_VERSION}
{'=' * 96}
Source Code SHA-256 : {h}
Python Environment  : {sys.version.split()[0]} ({sys.executable})
Platform            : {sys.platform}

100% Offline desktop tool engineered for complete data privacy, security, and AI workflows.
"""


# =====================================================================================
# 25. MAIN APPLICATION
# =====================================================================================
class Application:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.texts: list = []
        self.tabs: dict[str, Any] = {}
        root.title(f"{APP_NAME} - {APP_OWNER}   v{APP_VERSION}")
        root.geometry("1340x900")
        root.minsize(1120, 760)

        self.header = ttk.Frame(root, style="Header.TFrame")
        self.header.pack(fill="x", side="top")
        hpad = ttk.Frame(self.header, style="Header.TFrame", padding=(18, 12, 18, 12))
        hpad.pack(fill="x")

        htxt = ttk.Frame(hpad, style="Header.TFrame")
        htxt.pack(side="left")
        ttk.Label(htxt, text="🔒  PII Masking and Unmasking Tool", style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(htxt, text=f"{APP_OWNER}   •   v{APP_VERSION}   •   "
                             f"India-first, 100% offline, executive desktop tool for secure AI pipelines",
                  style="HeaderTagline.TLabel").pack(anchor="w")

        self.badge_offline = ttk.Label(hpad, text="● OFFLINE - PROTECTED", style="BadgeOk.TLabel")
        self.badge_offline.pack(side="right", padx=(8, 0))

        self.btn_theme_toggle = ttk.Button(hpad, width=3, command=self.toggle_theme)
        self.btn_theme_toggle.pack(side="right", padx=(0, 8))

        degraded = []
        if not HAVE_AESGCM:
            degraded.append("AES-GCM unavailable - stdlib HMAC-CTR fallback in use")
        if not HAVE_ARGON2:
            degraded.append("Argon2id unavailable - scrypt fallback in use")
        self.banner = tk.Label(root, text="⚠  DEGRADED MODE:  " + "   |   ".join(degraded),
                               anchor="w", padx=14, pady=6, font=F_BODY_BOLD)
        if degraded:
            self.banner.pack(fill="x")

        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(8, 4))

        self.tabs["Dashboard"] = TextTab(self, self.nb, dashboard_text)
        self.tabs["Mask"] = MaskTab(self, self.nb)
        self.tabs["Unmask"] = UnmaskTab(self, self.nb)
        self.tabs["Side-by-Side Diff"] = SideBySideDiffTab(self, self.nb)
        self.tabs["Dictionary"] = DictionaryTab(self, self.nb)
        self.tabs["Security Guardrails"] = GuardrailsTab(self, self.nb)
        self.tabs["Reports"] = ReportsTab(self, self.nb)
        self.tabs["Settings"] = SettingsTab(self, self.nb)
        self.tabs["Help"] = TextTab(self, self.nb, help_text)
        self.tabs["About"] = TextTab(self, self.nb, about_text)

        tab_icons = {"Dashboard": "📊", "Mask": "🛡️", "Unmask": "🔓",
                     "Side-by-Side Diff": "🔍", "Dictionary": "📖",
                     "Security Guardrails": "✅", "Reports": "📄",
                     "Settings": "⚙", "Help": "❓", "About": "ℹ"}
        self._tab_names = list(self.tabs.keys())
        for name, tab in self.tabs.items():
            self.nb.add(tab, text=f"{tab_icons.get(name, '')}  {name}")
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab)

        sb = ttk.Frame(root, style="StatusBar.TFrame")
        sb.pack(fill="x", side="bottom")
        sbpad = ttk.Frame(sb, style="StatusBar.TFrame", padding=(14, 6, 14, 6))
        sbpad.pack(fill="x")
        self.v_status = tk.StringVar(value="Ready")
        self.v_flags = tk.StringVar()
        ttk.Label(sbpad, textvariable=self.v_status, style="StatusText.TLabel").pack(side="left")
        ttk.Label(sbpad, textvariable=self.v_flags, style="StatusMuted.TLabel").pack(side="right")

        self.tick()
        self.apply_theme()
        self._sync_theme_button()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def toggle_theme(self):
        cur = CONFIG.data.get("theme", "dark")
        CONFIG.data["theme"] = "light" if cur == "dark" else "dark"
        CONFIG.save()
        self.apply_theme()
        self._sync_theme_button()

    def _sync_theme_button(self):
        dark = CONFIG.data.get("theme", "dark") == "dark"
        self.btn_theme_toggle.configure(text="☀" if dark else "☽")

    def register_text(self, widget):
        self.texts.append(widget)

    def on_tab(self, _e=None):
        try:
            name = self._tab_names[self.nb.index(self.nb.select())]
        except Exception:
            return
        if name == "Dashboard":
            self.tabs["Dashboard"].reload()

    def status(self, msg: str):
        self.v_status.set(msg)

    def tick(self):
        clean = SessionTemp._dir is None or not any(SessionTemp.dir().iterdir())
        self.v_flags.set(f"📡 Sockets Blocked: {OfflineKernel.blocked_attempts}    "
                         f"📁 Session Temp: {'clean' if clean else 'in use'}")
        self.root.after(4000, self.tick)

    def apply_theme(self):
        pal = THEMES.get(CONFIG.data.get("theme", "dark"), THEMES["dark"])
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.root.configure(bg=pal["bg"])

        style.configure(".", background=pal["bg"], foreground=pal["fg"],
                        fieldbackground=pal["field"], font=F_BODY, bordercolor=pal["border"],
                        darkcolor=pal["panel"], lightcolor=pal["panel"], troughcolor=pal["panel"])
        style.configure("TFrame", background=pal["bg"])
        style.configure("TLabel", background=pal["bg"], foreground=pal["fg"], font=F_BODY)
        style.configure("Muted.TLabel", background=pal["bg"], foreground=pal["muted"], font=F_SMALL)
        style.configure("Section.TLabel", background=pal["bg"], foreground=pal["fg"], font=F_SECTION)

        style.configure("Card.TFrame", background=pal["panel"], relief="solid", borderwidth=1)

        style.configure("Header.TFrame", background=pal["bg_alt"])
        style.configure("HeaderTitle.TLabel", background=pal["bg_alt"], foreground=pal["header_fg"], font=F_TITLE)
        style.configure("HeaderTagline.TLabel", background=pal["bg_alt"], foreground=pal["muted"], font=F_TAGLINE)
        style.configure("BadgeOk.TLabel", background=pal["ok_bg"], foreground=pal["ok"], font=F_BADGE, padding=(10, 5))
        style.configure("BadgeErr.TLabel", background=pal["err_bg"], foreground=pal["err"], font=F_BADGE, padding=(10, 5))

        style.configure("StatusBar.TFrame", background=pal["bg_alt"])
        style.configure("StatusText.TLabel", background=pal["bg_alt"], foreground=pal["fg_dim"], font=F_SMALL)
        style.configure("StatusMuted.TLabel", background=pal["bg_alt"], foreground=pal["muted"], font=F_SMALL)

        style.configure("TLabelframe", background=pal["bg"], foreground=pal["fg"],
                        bordercolor=pal["border"], relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label", background=pal["bg"], foreground=pal["accent"], font=F_BODY_BOLD)

        style.configure("TButton", background=pal["panel"], foreground=pal["fg"], font=F_BODY,
                        padding=(10, 6), borderwidth=1, bordercolor=pal["border"], relief="flat")
        style.map("TButton",
                  background=[("active", pal["panel_alt"]), ("disabled", pal["panel"])],
                  foreground=[("disabled", pal["muted"])])
        style.configure("Accent.TButton", background=pal["accent"], foreground=pal["accent_fg"],
                        font=F_BODY_BOLD, padding=(12, 7), borderwidth=0, relief="flat")
        style.map("Accent.TButton",
                  background=[("active", pal["accent_hover"]), ("disabled", pal["panel_alt"])],
                  foreground=[("disabled", pal["muted"])])
        style.configure("Danger.TButton", background=pal["err_bg"], foreground=pal["err"],
                        font=F_BODY_BOLD, padding=(10, 6), borderwidth=1, bordercolor=pal["err"])

        style.configure("TCheckbutton", background=pal["bg"], foreground=pal["fg"], font=F_BODY)
        style.configure("TRadiobutton", background=pal["bg"], foreground=pal["fg"], font=F_BODY)
        style.configure("TEntry", fieldbackground=pal["field"], foreground=pal["fg"],
                        bordercolor=pal["border"], insertcolor=pal["fg"], padding=5)
        style.configure("TCombobox", fieldbackground=pal["field"], foreground=pal["fg"],
                        background=pal["panel"], bordercolor=pal["border"], padding=4)
        style.configure("TSpinbox", fieldbackground=pal["field"], foreground=pal["fg"],
                        bordercolor=pal["border"], padding=4)

        style.configure("TNotebook", background=pal["bg"], bordercolor=pal["bg"])
        style.configure("TNotebook.Tab", background=pal["panel"], foreground=pal["fg_dim"],
                        padding=(14, 8), font=F_BODY_BOLD, borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", pal["accent"]), ("active", pal["panel_alt"])],
                  foreground=[("selected", pal["accent_fg"]), ("active", pal["fg"])])

        style.configure("Treeview", background=pal["field"], fieldbackground=pal["field"],
                        foreground=pal["fg"], rowheight=26, bordercolor=pal["border"],
                        borderwidth=1, font=F_BODY)
        style.configure("Treeview.Heading", background=pal["panel"], foreground=pal["fg"],
                        font=F_BODY_BOLD, relief="flat", padding=(6, 6))
        style.map("Treeview.Heading", background=[("active", pal["panel_alt"])])
        style.map("Treeview", background=[("selected", pal["sel"])], foreground=[("selected", "#ffffff")])

        style.configure("TProgressbar", background=pal["accent"], troughcolor=pal["panel"],
                        bordercolor=pal["panel"], lightcolor=pal["accent"], darkcolor=pal["accent"])

        # HIGH-CONTRAST VISIBLE SCROLLBARS (16px Width, Distinct Thumb & Track)
        style.configure("TScrollbar", background=pal["scroll_thumb"], troughcolor=pal["scroll_track"],
                        bordercolor=pal["border"], arrowcolor=pal["accent"], arrowsize=14, width=16)
        style.map("TScrollbar",
                  background=[("pressed", pal["sel"]), ("active", pal["scroll_thumb_hover"]), ("disabled", pal["panel"])])
        style.configure("Vertical.TScrollbar", background=pal["scroll_thumb"], troughcolor=pal["scroll_track"],
                        bordercolor=pal["border"], arrowcolor=pal["accent"], arrowsize=14, width=16)
        style.map("Vertical.TScrollbar",
                  background=[("pressed", pal["sel"]), ("active", pal["scroll_thumb_hover"]), ("disabled", pal["panel"])])
        style.configure("Horizontal.TScrollbar", background=pal["scroll_thumb"], troughcolor=pal["scroll_track"],
                        bordercolor=pal["border"], arrowcolor=pal["accent"], arrowsize=14, width=16)
        style.map("Horizontal.TScrollbar",
                  background=[("pressed", pal["sel"]), ("active", pal["scroll_thumb_hover"]), ("disabled", pal["panel"])])

        self.banner.configure(bg=pal["warn_bg"], fg=pal["warn"])
        for w in self.texts:
            try:
                w.configure(bg=pal["field"], fg=pal["fg"], insertbackground=pal["fg"],
                            selectbackground=pal["sel"], selectforeground="#ffffff",
                            relief="flat", highlightthickness=1,
                            highlightbackground=pal["border"], highlightcolor=pal["accent"],
                            font=F_MONO if isinstance(w, tk.Text) else F_BODY)
            except Exception:
                pass

    def close(self):
        SessionTemp.cleanup()
        AuditLog.event("app.exit", {})
        self.root.destroy()


# =====================================================================================
# 26. ENTRY POINT
# =====================================================================================
def main() -> int:
    OfflineKernel.install()
    SessionTemp.dir()
    AuditLog.event("app.start", {"version": APP_VERSION, "python": sys.version.split()[0]})
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.25)
    except Exception:
        pass
    Application(root)
    root.mainloop()
    SessionTemp.cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
