#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 BankDoc Processor & Renamer   -   an OFFLINE desk tool for a CA office
==============================================================================
 Feature 1 : read bank NEFT / RTGS / IMPS acknowledgement files (PDF or image
             only), extract the details with a LOCAL LLM (LM Studio, Ollama...),
             let you check / correct them, export to Excel / PDF and rename the
             files in a format of your choice (with backup, log and undo).

 HOW TO INSTALL (once, on a computer that has Python 3.9 or newer):

        pip install customtkinter pymupdf pillow openpyxl reportlab

 HOW TO RUN:

        python bankdoc_processor.py
==============================================================================
"""

import os
import sys
import re
import io
import csv
import json
import time
import uuid
import shutil
import base64
import hashlib
import queue
import socket
import threading
import traceback
import http.client
import datetime as dt
import urllib.request
import urllib.error
import urllib.parse
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

# --------------------------------------------------------------------------
# Dependency check - gives a friendly message instead of a scary traceback
# --------------------------------------------------------------------------
_MISSING: List[str] = []
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except Exception:  # pragma: no cover
    _MISSING.append("tkinter (on Linux: sudo apt install python3-tk)")
try:
    import customtkinter as ctk
except Exception:  # pragma: no cover
    _MISSING.append("customtkinter  ->  pip install customtkinter")
try:
    try:
        import pymupdf as fitz
    except Exception:
        import fitz  # type: ignore
    if not hasattr(fitz, "open"):
        raise ImportError("wrong 'fitz' package")
except Exception:  # pragma: no cover
    _MISSING.append("pymupdf  ->  pip install pymupdf")
try:
    from PIL import Image, ImageTk, ImageOps
except Exception:  # pragma: no cover
    _MISSING.append("pillow  ->  pip install pillow")
try:
    import openpyxl  # noqa: F401
except Exception:  # pragma: no cover
    _MISSING.append("openpyxl  ->  pip install openpyxl")
try:
    import reportlab  # noqa: F401
except Exception:  # pragma: no cover
    _MISSING.append("reportlab  ->  pip install reportlab")

if _MISSING:  # pragma: no cover
    _msg = ("BankDoc Processor cannot start because some parts are missing:\n\n  - "
            + "\n  - ".join(_MISSING)
            + "\n\nInstall them with:\n  pip install customtkinter pymupdf pillow openpyxl reportlab")
    print(_msg)
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb
        _r = _tk.Tk()
        _r.withdraw()
        _mb.showerror("Missing components", _msg)
    except Exception:
        pass
    sys.exit(1)

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
APP_NAME = "BankDoc Processor & Renamer"
APP_VERSION = "1.0"
PDF_EXTS = {".pdf"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
SESSION_FILE = "rename_session.json"
LOG_FILE_NAME = "bankdoc_processing_log.txt"
IGNORED_NAMES = {"thumbs.db", "desktop.ini", ".ds_store", SESSION_FILE}
IGNORED_PREFIXES = ("bankdoc_", "~$", ".")
WARNING_PASSWORD = ("⚠️ Security Warning: Do not share highly sensitive or primary banking "
                    "passwords here. They may be cached in memory during the session. "
                    "Use at your own risk.")
SUPPORTED_TEXT = "PDF (.pdf) and image files (.jpg .jpeg .png .tif .tiff .bmp .webp) ONLY"

FIELD_KEYS = ["date", "payee", "amount", "remarks", "txn_id", "payer", "mode"]
FIELD_LABELS = {
    "date": "Date", "payee": "Recipient / Payee name", "amount": "Amount",
    "remarks": "Remarks / Narration", "txn_id": "Transaction ID",
    "payer": "Payer / Sender name", "mode": "Mode",
}
CORE_FIELDS = ["date", "amount", "payee"]
MON_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Row status texts
S_VERIFIED = "Verified (matches PDF text)"
S_UNVERIFIED = "Check visually (scan/image)"
S_MISMATCH = "Value not found in file - Review"
S_INCOMPLETE = "Incomplete - Manual Review"
S_AMBIG = "Ambiguous - Manual Review Required"
S_FAILED = "Failed - Manual Review Required"
S_NOTRECEIPT = "Not a transfer receipt - Manual Review"
S_EDITED = "Edited manually"
BLOCKED_STATUSES = {S_AMBIG, S_FAILED, S_NOTRECEIPT}


# --------------------------------------------------------------------------
# Logger  (never receives passwords - nothing in this program passes one)
# --------------------------------------------------------------------------
class AppLogger:
    """Thread-safe logger. Keeps lines in memory, feeds the on-screen log box and,
    once a working folder is set, appends to bankdoc_processing_log.txt there."""

    def __init__(self):
        self._lock = threading.Lock()
        self.lines: List[str] = []
        self.ui_queue: "queue.Queue[str]" = queue.Queue()
        self.file_path: Optional[str] = None
        self._flushed = 0

    def set_folder(self, folder: str):
        with self._lock:
            new_path = os.path.join(folder, LOG_FILE_NAME)
            if new_path != self.file_path:
                self.file_path = new_path
                self._flushed = 0
            self._flush_locked()

    def _flush_locked(self):
        if not self.file_path:
            return
        try:
            with open(self.file_path, "a", encoding="utf-8") as fh:
                for line in self.lines[self._flushed:]:
                    fh.write(line + "\n")
            self._flushed = len(self.lines)
        except OSError:
            pass

    def _write(self, level: str, msg: str):
        ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = "[%s] [%s] %s" % (ts, level, msg)
        with self._lock:
            self.lines.append(line)
            self.ui_queue.put(line)
            self._flush_locked()

    def info(self, msg: str):
        self._write("INFO", msg)

    def warning(self, msg: str):
        self._write("WARNING", msg)

    def error(self, msg: str):
        self._write("ERROR", msg)

    def exception(self, context: str):
        self._write("ERROR", "%s\n%s" % (context, traceback.format_exc()))


LOG = AppLogger()


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------
def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return ("%d %s" % (size, unit)) if unit == "B" else ("%.1f %s" % (size, unit))
        size /= 1024.0
    return "%d B" % n


def stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def now_text() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sha256_file(path: str, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def atomic_write_json(path: str, obj) -> None:
    """Write JSON safely: temp file + flush + fsync + atomic replace."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass
    os.replace(tmp, path)


def safe_rename(src: str, dst: str) -> None:
    """Rename WITHOUT ever overwriting an existing file (raises FileExistsError)."""
    if os.path.exists(dst):
        try:
            same = os.path.samefile(src, dst)
        except OSError:
            same = False
        if not same:
            raise FileExistsError("Target already exists: %s" % dst)
        if src == dst:
            return
        tmp = os.path.join(os.path.dirname(dst), ".bankdoc_tmp_%s" % uuid.uuid4().hex[:8])
        os.rename(src, tmp)
        try:
            os.rename(tmp, dst)
        except Exception:
            os.rename(tmp, src)
            raise
        return
    if os.name == "nt":
        os.rename(src, dst)
        return
    try:
        os.link(src, dst)
    except FileExistsError:
        raise
    except OSError:
        if os.path.exists(dst):
            raise FileExistsError("Target already exists: %s" % dst)
        os.rename(src, dst)
        return
    try:
        os.unlink(src)
    except Exception:
        try:
            os.unlink(dst)
        except OSError:
            pass
        raise


def short_err(e: BaseException, limit: int = 220) -> str:
    text = "%s: %s" % (type(e).__name__, e)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit] + "..."


# --------------------------------------------------------------------------
# Date parsing  (Indian convention: DD/MM/YYYY)
# --------------------------------------------------------------------------
_MON_RE = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
_RX_ISO = re.compile(r"(?<!\d)(\d{4})([/\-.])(\d{1,2})\2(\d{1,2})(?!\d)")
_RX_DMY_NAME = re.compile(
    r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?[\s\-/.,]*" + _MON_RE + r"\.?[\s\-/.,]*(\d{4}|\d{2})(?![\d:])",
    re.I)
_RX_NAME_DMY = re.compile(
    r"(?<![a-z])" + _MON_RE + r"\.?[\s\-/.,]*(\d{1,2})(?:st|nd|rd|th)?[\s\-/.,]+(\d{4})(?!\d)", re.I)
_RX_DMY_NUM = re.compile(r"(?<!\d)(\d{1,2})([/\-.])(\d{1,2})\2(\d{4}|\d{2})(?![\d:])")


def _make_date(y: int, m: int, d: int) -> Optional[dt.date]:
    if y < 100:
        y += 2000
    if y < 1990 or y > 2100:
        return None
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def find_dates(text: str) -> List[dt.date]:
    """Find every valid date written in `text` (several common Indian formats)."""
    found: List[dt.date] = []
    if not text:
        return found
    work = text

    def add(d: Optional[dt.date]):
        if d is not None and d not in found:
            found.append(d)

    def r_iso(m):
        add(_make_date(int(m.group(1)), int(m.group(3)), int(m.group(4))))
        return " " * len(m.group(0))

    def r_dmy_name(m):
        mon = MON_ABBR.index(m.group(2).capitalize()) + 1
        add(_make_date(int(m.group(3)), mon, int(m.group(1))))
        return " " * len(m.group(0))

    def r_name_dmy(m):
        mon = MON_ABBR.index(m.group(1).capitalize()) + 1
        add(_make_date(int(m.group(3)), mon, int(m.group(2))))
        return " " * len(m.group(0))

    def r_dmy_num(m):
        add(_make_date(int(m.group(4)), int(m.group(3)), int(m.group(1))))
        return " " * len(m.group(0))

    work = _RX_ISO.sub(r_iso, work)
    work = _RX_DMY_NAME.sub(r_dmy_name, work)
    work = _RX_NAME_DMY.sub(r_name_dmy, work)
    work = _RX_DMY_NUM.sub(r_dmy_num, work)
    return found


def parse_date_text(s: str) -> Optional[str]:
    """Return ISO 'YYYY-MM-DD' for the FIRST date found in s, else None."""
    ds = find_dates(s or "")
    return ds[0].isoformat() if ds else None


def fmt_date_display(iso: str) -> str:
    if not iso:
        return ""
    try:
        d = dt.date.fromisoformat(iso)
    except ValueError:
        return iso
    return "%02d-%s-%04d" % (d.day, MON_ABBR[d.month - 1], d.year)


def fmt_date_code(iso: str, code: str) -> Optional[str]:
    if not iso:
        return None
    try:
        d = dt.date.fromisoformat(iso)
    except ValueError:
        return None
    dd, mm, yy = "%02d" % d.day, "%02d" % d.month, "%02d" % (d.year % 100)
    mmm = MON_ABBR[d.month - 1]
    if code == "ddmmyy":
        return dd + mm + yy
    if code == "ddmmmyy":
        return dd + mmm + yy
    if code == "yymmdd":
        return yy + mm + dd
    if code == "yymmmdd":
        return yy + mmm + dd
    return None


# --------------------------------------------------------------------------
# Amount parsing  ("Rs.1000" for whole numbers, decimals only if really present)
# --------------------------------------------------------------------------
_RX_NUM = re.compile(r"(?<!\d)\d[\d,]*(?:\.\d+)?")


def _canon_number(n: str) -> Optional[str]:
    n = n.strip().rstrip(",").replace(",", "")
    if not n:
        return None
    if "." in n:
        ip, fp = n.split(".", 1)
    else:
        ip, fp = n, ""
    if not ip.isdigit() or (fp and not fp.isdigit()):
        return None
    ip = ip.lstrip("0") or "0"
    if fp.strip("0") == "":
        fp = ""
    text = ip + ("." + fp if fp else "")
    try:
        if Decimal(text) <= 0:
            return None
    except InvalidOperation:
        return None
    return text


def parse_amount_text(s) -> Optional[str]:
    """'Rs. 1,00,000.00' -> '100000' ; 'INR 1,000.25' -> '1000.25' ; ambiguous -> None."""
    if s is None:
        return None
    nums = _RX_NUM.findall(str(s))
    if len(nums) != 1:
        return None
    return _canon_number(nums[0])


def all_amounts_in_text(text: str) -> set:
    out = set()
    for n in _RX_NUM.findall(text or ""):
        c = _canon_number(n)
        if c:
            out.add(c)
    return out


def fmt_amount_for_name(a: str) -> str:
    return "Rs." + a


# --------------------------------------------------------------------------
# File-name safety
# --------------------------------------------------------------------------
_INVALID_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
_INVISIBLE_RE = re.compile("[\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")
_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {"COM%d" % i for i in range(1, 10)} | {"LPT%d" % i for i in range(1, 10)}


def sanitize_component(s: str) -> Tuple[str, bool]:
    """Collapse spaces and replace unusable characters by '+'. Returns (clean, changed)."""
    s = _INVISIBLE_RE.sub("", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    clean = _INVALID_CHARS_RE.sub("+", s)
    return clean, clean != s


def collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# ==========================================================================
#  FILE ACCESS CHECKS, IN-MEMORY UNLOCKED COPIES, SCANNING
# ==========================================================================
@dataclass
class FileEntry:
    path: str
    rel: str            # folder relative to the chosen root ("" = root itself)
    name: str
    ext: str
    size: int
    mtime_ns: int
    kind: str           # 'pdf' | 'image' | 'other'
    accessible: bool = False
    locked: bool = False
    reason: str = ""
    unlocked_this_session: bool = False


class DecryptedCache:
    """Holds unlocked copies of password-protected PDFs IN MEMORY ONLY.
    The password itself is never stored - only the decrypted bytes."""

    def __init__(self):
        self._d: Dict[str, Tuple[int, int, bytes]] = {}
        self._lock = threading.Lock()

    def put(self, path: str, data: bytes) -> None:
        st = os.stat(path)
        with self._lock:
            self._d[path] = (st.st_size, st.st_mtime_ns, data)

    def get(self, path: str) -> Optional[bytes]:
        with self._lock:
            item = self._d.get(path)
        if item is None:
            return None
        try:
            st = os.stat(path)
        except OSError:
            return None
        if st.st_size != item[0] or st.st_mtime_ns != item[1]:
            return None
        return item[2]

    def rekey(self, old: str, new: str) -> None:
        with self._lock:
            if old in self._d:
                self._d[new] = self._d.pop(old)

    def clear(self) -> None:
        with self._lock:
            self._d.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._d)


def open_pdf_document(path: str, cache: Optional[DecryptedCache]):
    data = cache.get(path) if cache is not None else None
    if data is not None:
        return fitz.open(stream=data, filetype="pdf")
    return fitz.open(path)


def kind_of(ext: str) -> str:
    e = ext.lower()
    if e in PDF_EXTS:
        return "pdf"
    if e in IMAGE_EXTS:
        return "image"
    return "other"


def _is_ignored_name(name: str) -> bool:
    low = name.lower()
    if low in IGNORED_NAMES:
        return True
    return low.startswith(IGNORED_PREFIXES)


def list_candidate_files(root: str, include_sub: bool) -> List[str]:
    paths: List[str] = []

    def on_err(err):
        LOG.warning("Could not read folder: %s" % short_err(err))

    if include_sub:
        for dp, dn, fn in os.walk(root, onerror=on_err):
            dn[:] = sorted(d for d in dn if not d.startswith("."))
            for f in sorted(fn):
                if not _is_ignored_name(f):
                    paths.append(os.path.join(dp, f))
    else:
        try:
            names = sorted(os.listdir(root))
        except OSError as e:
            raise RuntimeError("Cannot read the folder: %s" % short_err(e))
        for f in names:
            p = os.path.join(root, f)
            if os.path.isfile(p) and not _is_ignored_name(f):
                paths.append(p)
    return paths


def check_file(entry: FileEntry, cache: Optional[DecryptedCache]) -> None:
    """Fill entry.accessible / entry.locked / entry.reason. Never raises."""
    entry.accessible = False
    entry.locked = False
    entry.reason = ""
    entry.unlocked_this_session = False
    try:
        if entry.kind == "other":
            entry.reason = "Unsupported file type (only PDF and image files are processed)"
            return
        if not os.path.isfile(entry.path):
            entry.reason = "File not found (moved or deleted)"
            return
        if entry.size == 0:
            entry.reason = "File is empty (0 bytes)"
            return
        try:
            with open(entry.path, "rb") as fh:
                head = fh.read(2048)
        except PermissionError:
            entry.reason = "No permission to read the file (access denied or file in use)"
            return
        except OSError as e:
            entry.reason = "Cannot read the file: %s" % short_err(e)
            return

        if entry.kind == "pdf":
            if b"%PDF" not in head:
                entry.reason = "Not a valid PDF (wrong or damaged file, or wrongly named)"
                return
            doc = None
            try:
                doc = open_pdf_document(entry.path, cache)
                if doc.needs_pass:
                    entry.locked = True
                    entry.reason = "Password protected"
                    return
                if doc.page_count < 1:
                    entry.reason = "PDF has no pages"
                    return
                page = doc.load_page(0)
                page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2), alpha=False)
                entry.accessible = True
                if cache is not None and cache.get(entry.path) is not None:
                    entry.unlocked_this_session = True
            except Exception as e:
                entry.accessible = False
                entry.reason = "Corrupt or unreadable PDF: %s" % short_err(e, 120)
            finally:
                if doc is not None:
                    try:
                        doc.close()
                    except Exception:
                        pass
            return

        # image
        try:
            with Image.open(entry.path) as im:
                im.verify()
            with Image.open(entry.path) as im2:
                im2.load()
            entry.accessible = True
        except Exception as e:
            entry.reason = "Corrupt or unreadable image: %s" % short_err(e, 120)
    except Exception as e:
        LOG.exception("Unexpected error while checking %s" % entry.path)
        entry.accessible = False
        entry.locked = False
        entry.reason = "Unexpected error: %s" % short_err(e, 120)


def scan_folder(root: str, include_sub: bool, cache: DecryptedCache, progress: Callable) -> List[FileEntry]:
    paths = list_candidate_files(root, include_sub)
    total = len(paths)
    out: List[FileEntry] = []
    last = 0.0
    for i, p in enumerate(paths, 1):
        name = os.path.basename(p)
        ext = os.path.splitext(name)[1]
        rel = os.path.relpath(os.path.dirname(p), root)
        rel = "" if rel == "." else rel
        try:
            st = os.stat(p)
            size, mtime = st.st_size, st.st_mtime_ns
            stat_err = ""
        except OSError as e:
            size, mtime = 0, 0
            stat_err = "Cannot read file details: %s" % short_err(e)
        entry = FileEntry(path=p, rel=rel, name=name, ext=ext, size=size, mtime_ns=mtime, kind=kind_of(ext))
        if stat_err:
            entry.reason = stat_err
        else:
            check_file(entry, cache)
        out.append(entry)
        now = time.time()
        if now - last > 0.05 or i == total:
            progress(i, total, name)
            last = now
    return out


def apply_password_to_files(paths: List[str], password: str, cache: DecryptedCache) -> Dict[str, Tuple[bool, str]]:
    """Try one password on several PDFs. On success keep ONLY the decrypted bytes
    (in memory). The password is not stored or logged anywhere."""
    results: Dict[str, Tuple[bool, str]] = {}
    for p in paths:
        doc = None
        try:
            doc = fitz.open(p)
            if not doc.needs_pass:
                results[p] = (True, "File was not locked")
                continue
            ok = doc.authenticate(password)
            if not ok:
                results[p] = (False, "Wrong password")
                continue
            try:
                data = doc.tobytes(encryption=fitz.PDF_ENCRYPT_NONE)
            except Exception as e:
                results[p] = (False, "Password accepted but the file could not be unlocked in memory: %s"
                              % short_err(e, 100))
                continue
            test = fitz.open(stream=data, filetype="pdf")
            try:
                if test.needs_pass or test.page_count < 1:
                    results[p] = (False, "Password accepted but the unlocked copy is not readable")
                    continue
            finally:
                test.close()
            cache.put(p, data)
            results[p] = (True, "Unlocked (in memory only)")
        except Exception as e:
            results[p] = (False, "Could not open file: %s" % short_err(e, 100))
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass
    return results


# ==========================================================================
#  LOCAL LLM  (strictly loopback)
# ==========================================================================
LOOPBACK_HOSTS = ("127.0.0.1", "localhost")


class LLMError(Exception):
    pass


class LoopbackViolation(Exception):
    pass


def validate_loopback_url(url: str) -> str:
    """Return a clean http(s)://127.0.0.1:port[/path] URL or raise LoopbackViolation.
    ONLY localhost / 127.0.0.1 are allowed. The URL is rebuilt from validated parts."""
    raw = (url or "").strip()
    if not raw:
        raise LoopbackViolation("SECURITY BLOCK: empty server address.")
    if not re.match(r"^https?://", raw, re.I):
        raw = "http://" + raw
    try:
        parts = urllib.parse.urlsplit(raw)
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        raise LoopbackViolation("SECURITY BLOCK: the address '%s' is not valid." % url)
    if parts.username or parts.password:
        raise LoopbackViolation("SECURITY BLOCK: addresses with a user name/password are not allowed.")
    if host not in LOOPBACK_HOSTS:
        raise LoopbackViolation(
            "SECURITY BLOCK: '%s' is not a local address. For your safety this tool only talks to "
            "localhost or 127.0.0.1 - your bank documents never leave this computer." % (host or url))
    netloc = "127.0.0.1" + (":%d" % port if port else "")
    path = parts.path.rstrip("/")
    for suffix in ("/v1", "/api"):
        if path.lower().endswith(suffix):
            path = path[: -len(suffix)]
    return "%s://%s%s" % (parts.scheme.lower(), netloc, path)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def http_json(method: str, base_url: str, path: str, payload=None, timeout: float = 10.0):
    base = validate_loopback_url(base_url)
    url = base + path
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        try:
            detail = e.read(600).decode("utf-8", "replace")
        except Exception:
            detail = ""
        raise LLMError("The model server answered with HTTP %s. %s" % (e.code, collapse_ws(detail)[:300]))
    except urllib.error.URLError as e:
        raise LLMError("Cannot connect to the model server (%s)." % (getattr(e, "reason", e),))
    except (socket.timeout, TimeoutError):
        raise LLMError("The model server took too long to answer (timeout).")
    except (OSError, http.client.HTTPException) as e:
        raise LLMError("Connection problem: %s" % short_err(e, 150))
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        raise LLMError("The model server returned something that is not JSON.")


@dataclass
class ModelInfo:
    server: str
    base_url: str
    kind: str                 # 'openai' (LM Studio, llama.cpp, Jan...) or 'ollama'
    model_id: str
    vision: Optional[bool] = None
    state: str = ""

    @property
    def label(self) -> str:
        v = {True: "vision: YES", False: "vision: no", None: "vision: unknown"}[self.vision]
        st = ("  |  %s" % self.state) if self.state else ""
        return "%s  -  %s   [%s%s]   (%s)" % (self.server, self.model_id, v, st, self.base_url)


KNOWN_SERVERS = [
    ("LM Studio", "http://127.0.0.1:1234", "lmstudio"),
    ("Ollama", "http://127.0.0.1:11434", "ollama"),
    ("llama.cpp / OpenAI-compatible", "http://127.0.0.1:8080", "openai"),
    ("Jan", "http://127.0.0.1:1337", "openai"),
    ("GPT4All", "http://127.0.0.1:4891", "openai"),
]


def _probe_server(name: str, base: str, kind: str) -> List[ModelInfo]:
    found: List[ModelInfo] = []
    if kind in ("ollama", "auto"):
        try:
            data = http_json("GET", base, "/api/tags", timeout=3)
            if isinstance(data, dict) and isinstance(data.get("models"), list):
                for m in data["models"]:
                    if not isinstance(m, dict):
                        continue
                    mid = m.get("name") or m.get("model")
                    if not mid:
                        continue
                    vision: Optional[bool] = None
                    skip = False
                    try:
                        info = http_json("POST", base, "/api/show", {"model": mid, "name": mid}, timeout=6)
                        caps = info.get("capabilities") if isinstance(info, dict) else None
                        if isinstance(caps, list):
                            vision = "vision" in caps
                            if "embedding" in caps and "completion" not in caps:
                                skip = True
                    except LLMError:
                        pass
                    if "embed" in str(mid).lower():
                        skip = True
                    if not skip:
                        found.append(ModelInfo("Ollama" if kind == "ollama" else name, base, "ollama", str(mid), vision))
                return found
        except LLMError:
            if kind == "ollama":
                return found
    if kind in ("lmstudio", "auto"):
        try:
            data = http_json("GET", base, "/api/v0/models", timeout=3)
            if isinstance(data, dict) and isinstance(data.get("data"), list):
                for m in data["data"]:
                    if not isinstance(m, dict) or not m.get("id"):
                        continue
                    mtype = str(m.get("type", ""))
                    if mtype == "embeddings" or "embed" in str(m["id"]).lower():
                        continue
                    found.append(ModelInfo(name, base, "openai", str(m["id"]),
                                           True if mtype == "vlm" else (False if mtype == "llm" else None),
                                           str(m.get("state", ""))))
                if found:
                    return found
        except LLMError:
            pass
    try:
        data = http_json("GET", base, "/v1/models", timeout=3)
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            for m in data["data"]:
                if isinstance(m, dict) and m.get("id") and "embed" not in str(m["id"]).lower():
                    found.append(ModelInfo(name, base, "openai", str(m["id"]), None))
    except LLMError:
        pass
    return found


def detect_models(extra_urls: List[str], progress: Callable) -> Tuple[List[ModelInfo], List[str]]:
    """Look for local model servers. Returns (models, notes)."""
    models: List[ModelInfo] = []
    notes: List[str] = []
    servers = list(KNOWN_SERVERS)
    for u in extra_urls:
        try:
            clean = validate_loopback_url(u)
            servers.append(("Custom server", clean, "auto"))
        except LoopbackViolation as e:
            notes.append(str(e))
    seen = set()
    for i, (name, base, kind) in enumerate(servers, 1):
        progress("Checking %s at %s ..." % (name, base))
        try:
            for m in _probe_server(name, base, kind):
                key = (m.base_url, m.kind, m.model_id)
                if key not in seen:
                    seen.add(key)
                    models.append(m)
        except LoopbackViolation as e:
            notes.append(str(e))
        except Exception as e:
            LOG.exception("Unexpected error probing %s" % base)
            notes.append("Unexpected problem checking %s: %s" % (name, short_err(e, 100)))
    return models, notes


SYSTEM_PROMPT = (
    "You are a careful data-extraction engine for Indian bank transfer acknowledgements "
    "(NEFT, RTGS, IMPS, UPI). You never guess and never invent. Pay special attention to "
    "distinguishing PAYER (sender / debited account holder) from PAYEE (receiver / beneficiary / "
    "credited account holder) — NEVER swap or confuse them. If a detail is not clearly "
    "visible in the document you return null for it. You answer with ONE JSON object and nothing else."
)

USER_PROMPT = """Read the bank transfer document and return exactly this JSON object:

{
  "is_bank_transfer_receipt": true or false,
  "transaction_id": "UTR / reference no. / transaction id / UID exactly as printed, or null",
  "date_candidates": ["every distinct date that could be the transaction date, copied exactly as printed"],
  "amount_candidates": ["every distinct amount that could be the transferred amount, copied exactly as printed"],
  "payee_name": "name of the person/company RECEIVING the money (Beneficiary / Paid to / To), or null",
  "payer_name": "name of the person/company SENDING the money (Remitter / From / Debited from), or null",
  "remarks": "remarks / narration / purpose text exactly as printed, or null",
  "mode": "NEFT or RTGS or IMPS or UPI or OTHER, or null"
}

STRICT RULES (CRITICAL FOR IMAGES / SCREENSHOTS - DO NOT SWAP PAYER AND PAYEE):
1. HOW TO DISTINGUISH PAYEE vs PAYER:
   - payee_name (RECEIVER / BENEFICIARY): Look for labels such as "To", "Paid to", "Beneficiary Name",
     "Payee Name", "Credited to", "Receiver", "Transfer to", or "Sent to". In mobile payment/bank app
     screenshots (GPay, PhonePe, Paytm, HDFC, ICICI, SBI, Axis, etc.), the prominent name at the TOP
     right under "Paid to" or near the amount is almost always the PAYEE (receiver), NOT the payer.
   - payer_name (SENDER / REMITTER): Look for labels such as "From", "Debited from", "Remitter Name",
     "Sender", "Payer Name", "Source Account Name", or "Paid by". If the screenshot only shows the
     recipient's name ("Paid to X") and only shows a bank name + masked account number for "Debited from"
     without the sender's personal/company name, then payer_name MUST be null! NEVER copy payee_name
     into payer_name.
2. NEVER put a BANK name, branch, IFSC code or account number in payee_name or payer_name.
3. Copy text EXACTLY as printed (same spelling). Do not translate, correct, shorten or reformat.
4. date_candidates: dates only as printed (do not convert). Skip dates that are clearly not the
   transaction date (for example a statement-print date or a cheque date). If the document shows
   two different possible transaction dates, list both.
5. amount_candidates: only amounts that could be the transferred amount. Not balances, charges, GST,
   limits or fees. If two different transfer amounts seem possible, list both.
6. Use null (not an empty string) for anything not clearly present. Do not guess.
7. Output the JSON object only - no explanation, no markdown."""


def build_user_message(text: Optional[str]) -> str:
    if text is not None:
        return USER_PROMPT + "\n\nDOCUMENT TEXT (between the lines):\n-----\n" + text + "\n-----"
    return (USER_PROMPT + "\n\nThe attached image(s) are the page(s) of ONE bank/payment receipt. "
            "Read the labels ('To'/'Paid to'/'Beneficiary' vs 'From'/'Debited from'/'Remitter') "
            "carefully so you NEVER put the Payee (receiver) name into payer_name.")


def call_llm(model: ModelInfo, user_text: str, images_b64: List[str], timeout: float = 420.0) -> str:
    """One chat request to the local model (loopback only). Returns the reply text."""
    if model.kind == "ollama":
        msg = {"role": "user", "content": user_text}
        if images_b64:
            msg["images"] = images_b64
        payload = {
            "model": model.model_id, "stream": False, "format": "json",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, msg],
            "options": {"temperature": 0, "num_ctx": 8192},
        }
        resp = http_json("POST", model.base_url, "/api/chat", payload, timeout=timeout)
        content = ((resp or {}).get("message") or {}).get("content") if isinstance(resp, dict) else None
    else:
        if images_b64:
            content_list = [{"type": "text", "text": user_text}]
            for b in images_b64:
                content_list.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + b}})
            user_msg = {"role": "user", "content": content_list}
        else:
            user_msg = {"role": "user", "content": user_text}
        payload = {
            "model": model.model_id, "temperature": 0, "max_tokens": 1500, "stream": False,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, user_msg],
        }
        resp = http_json("POST", model.base_url, "/v1/chat/completions", payload, timeout=timeout)
        content = None
        try:
            content = resp["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = None
        if isinstance(content, list):
            content = "".join(str(c.get("text", "")) for c in content if isinstance(c, dict))
    if not content or not str(content).strip():
        raise LLMError("The model returned an empty answer.")
    return str(content)


def parse_llm_json(reply: str) -> dict:
    s = re.sub(r"<think>.*?</think>", "", reply, flags=re.S | re.I).strip()
    s = re.sub(r"^```(?:json)?", "", s, flags=re.I).strip()
    s = re.sub(r"```$", "", s).strip()
    start = s.find("{")
    if start < 0:
        raise ValueError("The model's answer did not contain a JSON object.")
    try:
        obj, _end = json.JSONDecoder().raw_decode(s[start:])
    except ValueError:
        end = s.rfind("}")
        if end <= start:
            raise ValueError("The model's answer was not valid JSON.")
        try:
            obj = json.loads(s[start:end + 1])
        except ValueError:
            raise ValueError("The model's answer was not valid JSON.")
    if not isinstance(obj, dict):
        raise ValueError("The model's answer was not a JSON object.")
    return obj


# --------------------------------------------------------------------------
# Reading a document for the LLM (text layer or page images) + page viewer
# --------------------------------------------------------------------------
def _to_rgb(img):
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg
    return img.convert("RGB")


def _png_b64(img, max_side: int = 1800) -> str:
    img = _to_rgb(img)
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def extract_document_payload(path: str, kind: str, cache: Optional[DecryptedCache]) -> dict:
    """Returns {'mode': 'text'|'image', 'text': str, 'images': [b64...], 'pages': n}."""
    if kind == "pdf":
        doc = open_pdf_document(path, cache)
        try:
            if doc.needs_pass:
                raise RuntimeError("The PDF is still password protected.")
            pages = doc.page_count
            texts = []
            for i in range(min(pages, 6)):
                texts.append(doc.load_page(i).get_text("text") or "")
            text = "\n".join(texts)
            if len(re.sub(r"\s", "", text)) >= 40:
                return {"mode": "text", "text": text[:8000], "images": [], "pages": pages}
            images = []
            for i in range(min(pages, 3)):
                page = doc.load_page(i)
                rect = page.rect
                scale = min(2.5, 1800.0 / max(rect.width, rect.height, 1.0))
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                images.append(base64.b64encode(pix.tobytes("png")).decode("ascii"))
            return {"mode": "image", "text": "", "images": images, "pages": pages}
        finally:
            doc.close()
    images = []
    with Image.open(path) as im:
        n = getattr(im, "n_frames", 1)
        for i in range(min(n, 3)):
            im.seek(i)
            frame = ImageOps.exif_transpose(im) if i == 0 else im.copy()
            images.append(_png_b64(frame))
    return {"mode": "image", "text": "", "images": images, "pages": max(1, n)}


def get_page_count(path: str, kind: str, cache: Optional[DecryptedCache]) -> int:
    if kind == "pdf":
        doc = open_pdf_document(path, cache)
        try:
            return max(1, doc.page_count)
        finally:
            doc.close()
    with Image.open(path) as im:
        return max(1, getattr(im, "n_frames", 1))


def render_page_image(path: str, kind: str, page_index: int, zoom: float,
                      cache: Optional[DecryptedCache]):
    """Return (PIL image, natural_width_at_zoom_1). zoom 1.0 = 'actual size'."""
    if kind == "pdf":
        doc = open_pdf_document(path, cache)
        try:
            page = doc.load_page(max(0, min(page_index, doc.page_count - 1)))
            rect = page.rect
            base = 96.0 / 72.0
            nat_w = rect.width * base
            scale = zoom * base
            longest = max(rect.width, rect.height) * scale
            if longest > 7000:
                scale *= 7000.0 / longest
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            return img, nat_w
        finally:
            doc.close()
    with Image.open(path) as im:
        n = getattr(im, "n_frames", 1)
        im.seek(max(0, min(page_index, n - 1)))
        frame = ImageOps.exif_transpose(im) if page_index == 0 else im.copy()
        frame = _to_rgb(frame)
        nat_w = float(frame.width)
        w, h = max(1, int(frame.width * zoom)), max(1, int(frame.height * zoom))
        if max(w, h) > 7000:
            f = 7000.0 / max(w, h)
            w, h = max(1, int(w * f)), max(1, int(h * f))
        if (w, h) != frame.size:
            frame = frame.resize((w, h), Image.LANCZOS)
        return frame, nat_w


# ==========================================================================
#  EXTRACTED-DATA MODEL, VALIDATION, FILE-NAME BUILDING
# ==========================================================================
NULL_WORDS = {"null", "none", "n/a", "na", "unknown", "not available", "not found", "-", "--", "nil", "undefined"}


def as_str(v) -> str:
    if v is None or isinstance(v, (dict, list, bool)):
        return ""
    s = collapse_ws(str(v))
    s = s.strip("\"'`").strip()
    if s.lower() in NULL_WORDS:
        return ""
    return s


def as_list(v) -> List[str]:
    if isinstance(v, list):
        return [as_str(x) for x in v if as_str(x)]
    s = as_str(v)
    return [s] if s else []


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def text_contains_phrase(norm_text: str, phrase: str) -> bool:
    p = _norm(phrase)
    if not p:
        return True
    if p in norm_text:
        return True
    if p.replace(" ", "") in norm_text.replace(" ", ""):
        return True
    tokens = [t for t in re.findall(r"\w+", p, re.U) if len(t) >= 2 or t.isdigit()]
    if not tokens:
        return False
    return all(t in norm_text for t in tokens)


def looks_like_bank_name(s: str) -> bool:
    return bool(re.search(r"\b(bank|ifsc|a/c|account\s*(no|number))\b", s, re.I))


@dataclass
class Row:
    path: str
    rel: str
    name: str
    ext: str
    size: int
    mtime_ns: int
    kind: str
    source_mode: str = ""
    fields: Dict[str, str] = field(default_factory=lambda: {k: "" for k in FIELD_KEYS})
    extracted: Dict[str, str] = field(default_factory=lambda: {k: "" for k in FIELD_KEYS})
    edited: set = field(default_factory=set)
    date_cands: List[str] = field(default_factory=list)      # ISO strings
    amount_cands: List[str] = field(default_factory=list)    # canonical strings
    verify_fail: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: str = ""
    not_receipt: bool = False
    status: str = ""
    amb_msgs: List[str] = field(default_factory=list)
    approved: bool = False
    # naming
    proposed_override: Optional[str] = None
    auto_stem: str = ""
    final_name: str = ""
    system_name: str = ""
    name_flags: List[str] = field(default_factory=list)
    name_missing: List[str] = field(default_factory=list)
    unchanged: bool = False

    # ---- status logic -------------------------------------------------
    def recompute(self) -> None:
        amb: List[str] = []
        if len(self.date_cands) > 1 and "date" not in self.edited:
            amb.append("Several different dates found: " + ", ".join(fmt_date_display(d) for d in self.date_cands))
        if len(self.amount_cands) > 1 and "amount" not in self.edited:
            amb.append("Several different amounts found: " + ", ".join("Rs." + a for a in self.amount_cands))
        self.amb_msgs = amb
        core_missing = [f for f in CORE_FIELDS if not self.fields.get(f)]
        if amb:
            self.status = S_AMBIG
        elif (self.error or self.not_receipt) and not (self.edited and not core_missing):
            self.status = S_FAILED if self.error else S_NOTRECEIPT
        elif core_missing:
            self.status = S_INCOMPLETE
        elif self.verify_fail:
            self.status = S_MISMATCH
        elif self.edited:
            self.status = S_EDITED
        elif self.source_mode == "text":
            self.status = S_VERIFIED
        else:
            self.status = S_UNVERIFIED
        if self.status in BLOCKED_STATUSES:
            self.approved = False

    def set_field(self, key: str, value: str) -> bool:
        """Manual edit. Returns True if a manual proposed file name had to be reset."""
        self.fields[key] = value
        self.edited.add(key)
        self.verify_fail.pop(key, None)
        reset = self.proposed_override is not None
        self.proposed_override = None
        self.recompute()
        return reset

    def notes_text(self) -> str:
        items: List[str] = []
        if self.error:
            items.append("ERROR: " + self.error)
        if self.not_receipt:
            items.append("AI says this is not a bank transfer receipt")
        items.extend(self.amb_msgs)
        for k, msg in self.verify_fail.items():
            items.append("%s: %s" % (FIELD_LABELS.get(k, k), msg))
        items.extend(self.warnings)
        items.extend(self.name_flags)
        return " | ".join(items)


def row_from_entry(e: FileEntry) -> Row:
    return Row(path=e.path, rel=e.rel, name=e.name, ext=e.ext, size=e.size, mtime_ns=e.mtime_ns, kind=e.kind)


def apply_llm_result(row: Row, data: dict, payload: dict) -> None:
    """Turn the model's JSON into validated fields. Never invents anything."""
    row.source_mode = payload["mode"]
    text_mode = payload["mode"] == "text"
    text = payload.get("text", "") if text_mode else ""
    norm_text = _norm(text)
    text_dates = set(find_dates(text)) if text_mode else set()
    text_amounts = all_amounts_in_text(text) if text_mode else set()

    isr = data.get("is_bank_transfer_receipt")
    if isr is False or (isinstance(isr, str) and isr.strip().lower() == "false"):
        row.not_receipt = True

    # ---- dates
    raw_dates = as_list(data.get("date_candidates")) or as_list(data.get("date"))
    isos: List[str] = []
    for rd in raw_dates:
        found = find_dates(rd)
        if not found:
            row.warnings.append("Date text '%s' could not be understood" % rd)
            continue
        for d in found:
            if text_mode and d not in text_dates:
                row.warnings.append("Date %s given by AI was NOT found in the PDF text - ignored"
                                    % fmt_date_display(d.isoformat()))
                continue
            if d.isoformat() not in isos:
                isos.append(d.isoformat())
    if text_mode and isos:
        extra = [d.isoformat() for d in sorted(text_dates) if d.isoformat() not in isos]
        if extra:
            isos.extend(extra)
            row.warnings.append("Other date(s) also appear in the document: "
                                + ", ".join(fmt_date_display(x) for x in extra))
    row.date_cands = isos
    if len(isos) == 1:
        row.fields["date"] = isos[0]
        if isos[0] > dt.date.today().isoformat():
            row.warnings.append("The date is in the future - please check it")

    # ---- amounts
    raw_amts = as_list(data.get("amount_candidates")) or as_list(data.get("amount"))
    amts: List[str] = []
    for ra in raw_amts:
        c = parse_amount_text(ra)
        if c is None:
            row.warnings.append("Amount text '%s' could not be understood" % ra)
            continue
        if text_mode and c not in text_amounts:
            row.warnings.append("Amount Rs.%s given by AI was NOT found in the PDF text - ignored" % c)
            continue
        if c not in amts:
            amts.append(c)
    row.amount_cands = amts
    if len(amts) == 1:
        row.fields["amount"] = amts[0]

    # ---- text fields
    row.fields["txn_id"] = as_str(data.get("transaction_id") or data.get("txn_id"))
    row.fields["payee"] = as_str(data.get("payee_name") or data.get("payee"))
    row.fields["payer"] = as_str(data.get("payer_name") or data.get("payer"))
    row.fields["remarks"] = as_str(data.get("remarks") or data.get("narration"))
    mode = as_str(data.get("mode")).upper()
    if mode not in ("NEFT", "RTGS", "IMPS", "UPI", "OTHER"):
        mode = ""
    if mode and mode != "OTHER" and text_mode and mode not in text.upper():
        row.warnings.append("Payment mode '%s' not found in PDF text - left blank" % mode)
        mode = ""
    row.fields["mode"] = mode

    if text_mode:
        for key in ("txn_id", "payee", "payer", "remarks"):
            val = row.fields[key]
            if val and not text_contains_phrase(norm_text, val):
                row.verify_fail[key] = "'%s' was not found in the PDF text (AI may have made it up)" % val
    if row.fields["payee"] and looks_like_bank_name(row.fields["payee"]):
        row.verify_fail["payee"] = "looks like a BANK name, not a person/company - please check"
    if row.fields["payer"] and looks_like_bank_name(row.fields["payer"]):
        row.warnings.append("Payer name looks like a bank/account label - cleared")
        row.fields["payer"] = ""
    if (row.fields["payee"] and row.fields["payer"]
            and _norm(row.fields["payee"]) == _norm(row.fields["payer"])):
        if not text_mode:
            row.fields["payer"] = ""
            row.warnings.append("AI returned the same name for Payer and Payee on image - Payer cleared")
        else:
            row.warnings.append("Payee and payer names are identical - please check")
    if not text_mode:
        row.warnings.append("Scanned/image file: details could not be machine-verified - compare with the original")
    row.extracted = dict(row.fields)
    row.recompute()


def failed_row(row: Row, message: str) -> Row:
    row.error = message
    row.recompute()
    return row


def process_one_file(entry: FileEntry, model: ModelInfo, cache: DecryptedCache) -> Row:
    """Full pipeline for one file. Never raises: problems become a 'Failed' row."""
    row = row_from_entry(entry)
    try:
        payload = extract_document_payload(entry.path, entry.kind, cache)
    except Exception as e:
        LOG.exception("Could not read %s" % entry.path)
        return failed_row(row, "Could not read the file: %s" % short_err(e, 150))
    user_text = build_user_message(payload["text"] if payload["mode"] == "text" else None)
    last_err = ""
    for attempt in (1, 2):
        try:
            reply = call_llm(model, user_text, payload["images"])
        except LLMError as e:
            if (payload["mode"] == "image" and model.vision is False
                    and not str(e).startswith(("Cannot connect", "The model server took too long"))):
                return failed_row(row, "This file needs a vision-capable model but '%s' is text-only. %s"
                                  % (model.model_id, e))
            LOG.error("LLM error for %s: %s" % (entry.name, e))
            return failed_row(row, "LLM problem: %s" % e)
        except Exception as e:
            LOG.exception("Unexpected LLM failure for %s" % entry.path)
            return failed_row(row, "Unexpected error while asking the model: %s" % short_err(e, 150))
        try:
            data = parse_llm_json(reply)
        except ValueError as e:
            last_err = str(e)
            LOG.warning("Attempt %d: unreadable answer for %s (%s)" % (attempt, entry.name, e))
            continue
        try:
            apply_llm_result(row, data, payload)
        except Exception as e:
            LOG.exception("Could not interpret answer for %s" % entry.path)
            return failed_row(row, "Could not interpret the model's answer: %s" % short_err(e, 150))
        return row
    return failed_row(row, "The model's answer could not be understood twice (%s)" % last_err)


def process_files(entries: List[FileEntry], model: ModelInfo, cache: DecryptedCache,
                  cancel: threading.Event, progress: Callable) -> int:
    total = len(entries)
    done = 0
    for i, e in enumerate(entries, 1):
        if cancel.is_set():
            LOG.warning("Processing cancelled by the user after %d of %d files." % (done, total))
            break
        progress("start", i, total, e.name, None)
        row = process_one_file(e, model, cache)
        done += 1
        progress("row", i, total, e.name, row)
    return done


# --------------------------------------------------------------------------
# Rename-format building
# --------------------------------------------------------------------------
PART_CHOICES: List[Tuple[str, str]] = [
    ("(leave blank)", ""),
    ("ddmmyy", "ddmmyy"),
    ("ddmmmyy", "ddmmmyy"),
    ("yymmdd", "yymmdd"),
    ("yymmmdd", "yymmmdd"),
    ("Payee / Recipient name", "payee"),
    ("Amount (Rs.xx)", "amount"),
    ("Remarks / Narration", "remarks"),
    ("Transaction ID", "txn_id"),
    ("Payer / Sender name", "payer"),
    ("Payment mode (NEFT/RTGS/IMPS)", "mode"),
]
DATE_CODES = {"ddmmyy", "ddmmmyy", "yymmdd", "yymmmdd"}
CODE_LABEL = {
    "ddmmyy": "Date", "ddmmmyy": "Date", "yymmdd": "Date", "yymmmdd": "Date",
    "payee": "Payee name", "amount": "Amount", "remarks": "Remarks",
    "txn_id": "Transaction ID", "payer": "Payer name", "mode": "Payment mode",
}


def part_text(fields: Dict[str, str], code: str) -> Optional[str]:
    if code in DATE_CODES:
        return fmt_date_code(fields.get("date", ""), code)
    if code == "amount":
        a = fields.get("amount", "")
        return fmt_amount_for_name(a) if a else None
    v = collapse_ws(fields.get(code, ""))
    return v or None


def stem_from_fields(fields: Dict[str, str], codes: List[str]) -> Tuple[str, List[str], bool]:
    """Returns (stem, missing_labels, chars_replaced). Parts are joined with ' - '."""
    parts: List[str] = []
    missing: List[str] = []
    replaced = False
    for code in codes:
        if not code:
            continue
        t = part_text(fields, code)
        if not t:
            missing.append(CODE_LABEL.get(code, code))
            continue
        clean, ch = sanitize_component(t)
        replaced = replaced or ch
        parts.append(clean)
    if missing or not parts:
        return "", missing, replaced
    return " - ".join(parts), [], replaced


def _fit_stem(stem: str, ext: str, dirpath: str) -> Tuple[str, List[str]]:
    flags: List[str] = []
    s = stem.rstrip(" .")
    if s != stem:
        flags.append("Trailing space/dot removed")
    if s.split(".")[0].strip().upper() in _RESERVED:
        s = s + "+"
        flags.append("Reserved system name - '+' added")
    limit_bytes = 235
    limit_chars = 10 ** 6
    if os.name == "nt":
        limit_chars = 250 - len(dirpath) - 1 - len(ext) - 5
    cut = s
    while cut and (len((cut + ext).encode("utf-8")) > limit_bytes or len(cut) > limit_chars):
        cut = cut[:-1]
    cut = cut.rstrip(" .")
    if cut != s:
        flags.append("Name shortened to fit the system limit")
    if len(cut) < 1 or (os.name == "nt" and limit_chars < 8):
        return "", flags + ["Folder path too long - rename not possible"]
    return cut, flags


def compute_names(rows: List[Row], codes: List[str]) -> None:
    """Compute proposed names for all rows (system proposal + manual overrides),
    handle unusable characters, over-long names and duplicates."""
    listing_cache: Dict[str, set] = {}

    def listing(d: str) -> set:
        key = os.path.normcase(d)
        if key not in listing_cache:
            try:
                listing_cache[key] = {n.lower() for n in os.listdir(d)}
            except OSError:
                listing_cache[key] = set()
        return listing_cache[key]

    cand: List[Tuple[Row, str]] = []
    for r in rows:
        r.name_flags = []
        r.name_missing = []
        r.final_name = ""
        r.system_name = ""
        r.unchanged = False
        r.auto_stem = ""
        d = os.path.dirname(r.path)
        stem, missing, replaced = stem_from_fields(r.fields, codes)
        r.name_missing = missing
        if stem:
            fitted, _f = _fit_stem(stem, r.ext, d)
            r.auto_stem = fitted
            r.system_name = (fitted + r.ext) if fitted else ""
        if r.proposed_override is not None:
            ov = r.proposed_override
            if r.ext and ov.lower().endswith(r.ext.lower()):
                ov = ov[: -len(r.ext)]
            clean, ch = sanitize_component(ov)
            if not clean:
                r.name_flags.append("Manual name is empty - manual review")
                continue
            fitted, fl = _fit_stem(clean, r.ext, d)
            r.name_flags.extend(fl)
            if ch:
                r.name_flags.append("Unusable characters replaced with '+'")
            if not fitted:
                continue
            cand.append((r, fitted))
            continue
        if not stem:
            if missing:
                r.name_flags.append("Manual review: missing " + ", ".join(missing))
            else:
                r.name_flags.append("Manual review: nothing to build a name from")
            continue
        fitted, fl = _fit_stem(stem, r.ext, d)
        r.name_flags.extend(fl)
        if replaced:
            r.name_flags.append("Unusable characters replaced with '+'")
        if not fitted:
            continue
        cand.append((r, fitted))

    reserved: set = set()
    pending: List[Tuple[Row, str]] = []
    for r, stem in cand:
        d = os.path.dirname(r.path)
        if (stem + r.ext) == r.name:
            r.final_name = r.name
            r.unchanged = True
            r.name_flags.append("No change - already has this name")
            reserved.add((os.path.normcase(d), r.name.lower()))
        else:
            pending.append((r, stem))
    for r, stem in pending:
        d = os.path.dirname(r.path)
        nd = os.path.normcase(d)
        ex = listing(d)
        n = 0
        name = stem + r.ext
        while (nd, name.lower()) in reserved or name.lower() in ex:
            n += 1
            name = "%s_%d%s" % (stem, n, r.ext)
        reserved.add((nd, name.lower()))
        r.final_name = name
        if n:
            r.name_flags.append("Duplicate name - number _%d added" % n)


def block_reason(r: Row) -> str:
    """Empty string = this row may be renamed. Otherwise the reason it may not."""
    if not r.approved:
        return "Not approved"
    if r.status in BLOCKED_STATUSES:
        return "Manual review required (%s)" % r.status
    if not r.final_name:
        if r.name_missing:
            return "Missing details: " + ", ".join(r.name_missing)
        return "No usable proposed name"
    if r.unchanged:
        return "No change needed (already has this name)"
    return ""


# ==========================================================================
#  RENAME SESSION (rename_session.json), BACKUP, RENAME, UNDO
# ==========================================================================
class SessionCorrupt(Exception):
    pass


def session_path(root: str) -> str:
    return os.path.join(root, SESSION_FILE)


def load_session(root: str) -> Optional[dict]:
    p = session_path(root)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise SessionCorrupt(short_err(e))
    if not isinstance(data, dict) or not isinstance(data.get("batches"), list):
        raise SessionCorrupt("unexpected structure")
    return data


def new_session(root: str) -> dict:
    return {"app": APP_NAME, "version": 1, "root_folder": root, "created": now_text(), "batches": []}


def reconcile_session(data: dict) -> int:
    """After a crash: look at the disk and fix 'pending' / 'in_progress' entries."""
    changes = 0
    for batch in data.get("batches", []):
        for e in batch.get("entries", []):
            if e.get("status") in ("pending", "in_progress"):
                new_exists = os.path.exists(e.get("new_path", ""))
                old_exists = os.path.exists(e.get("original_path", ""))
                if new_exists and not old_exists:
                    e["status"] = "renamed"
                    e["note"] = "Recovered after an interruption: file found under the new name"
                elif old_exists and not new_exists:
                    e["status"] = "not_renamed"
                    e["note"] = "Interrupted before this file was renamed"
                else:
                    e["status"] = "needs_attention"
                    e["note"] = "Interrupted - please check this file manually"
                changes += 1
        if batch.get("status") == "running":
            batch["status"] = "interrupted"
            changes += 1
    return changes


def last_undoable_batch(data: Optional[dict]) -> Optional[dict]:
    if not data:
        return None
    for batch in reversed(data.get("batches", [])):
        if not batch.get("undone") and any(e.get("status") == "renamed" for e in batch.get("entries", [])):
            return batch
    return None


def is_inside(child: str, parent: str) -> bool:
    try:
        c = os.path.normcase(os.path.realpath(child))
        p = os.path.normcase(os.path.realpath(parent))
        return os.path.commonpath([c, p]) == p
    except ValueError:
        return False


def run_backup(plan: List[dict], root: str, session_dir: str, progress: Callable) -> Tuple[List[Tuple[str, str]], Dict[str, str]]:
    """Copy every file about to be renamed into session_dir (keeps sub-folders).
    Returns (failures, {original_path: backup_path}). Each copy is verified by SHA-256."""
    failures: List[Tuple[str, str]] = []
    bpaths: Dict[str, str] = {}
    if is_inside(session_dir, root):
        return [("(all files)", "The backup folder must be OUTSIDE the folder being renamed.")], bpaths
    try:
        os.makedirs(session_dir, exist_ok=True)
        probe = os.path.join(session_dir, ".bankdoc_write_test_%s" % uuid.uuid4().hex[:6])
        with open(probe, "wb") as fh:
            fh.write(b"ok")
        os.remove(probe)
    except OSError as e:
        return [("(all files)", "Cannot write to the backup folder: %s" % short_err(e, 120))], bpaths
    total = sum(p["size"] for p in plan)
    try:
        free = shutil.disk_usage(session_dir).free
        if free < total * 1.05 + 10 * 1024 * 1024:
            return [("(all files)", "Not enough free disk space for the backup (needs about %s, only %s free)."
                     % (human_size(int(total * 1.05)), human_size(free)))], bpaths
    except OSError:
        pass
    n = len(plan)
    for i, p in enumerate(plan, 1):
        progress("backup", i, n, p["name"])
        src = p["path"]
        try:
            rel = os.path.relpath(src, root)
            if rel.startswith(".."):
                rel = os.path.basename(src)
            dest = os.path.join(session_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if os.path.exists(dest) and sha256_file(dest) == p["sha256"]:
                bpaths[src] = dest
                continue
            part = dest + ".part"
            shutil.copy2(src, part)
            if sha256_file(part) != p["sha256"]:
                os.remove(part)
                raise IOError("Backup copy did not match the original (verification failed)")
            os.replace(part, dest)
            bpaths[src] = dest
        except Exception as e:
            failures.append((p["path"], short_err(e, 160)))
    return failures, bpaths


def preflight_check(plan: List[dict]) -> List[Tuple[str, str]]:
    problems: List[Tuple[str, str]] = []
    seen_targets: Dict[str, str] = {}
    for p in plan:
        src, dst = p["path"], p["new_path"]
        if not os.path.isfile(src):
            problems.append((src, "File no longer exists at its original location"))
            continue
        try:
            st = os.stat(src)
            if st.st_size != p["size"] or st.st_mtime_ns != p["mtime_ns"]:
                problems.append((src, "File was changed after it was scanned - please scan again"))
                continue
            with open(src, "rb") as fh:
                fh.read(1)
        except OSError as e:
            problems.append((src, "File cannot be read (maybe open in another program): %s" % short_err(e, 100)))
            continue
        d = os.path.dirname(dst)
        if not os.access(d, os.W_OK | os.X_OK):
            problems.append((src, "No permission to rename files in this folder"))
            continue
        if os.path.exists(dst):
            problems.append((src, "A file named '%s' already exists" % os.path.basename(dst)))
            continue
        key = os.path.normcase(dst)
        if key in seen_targets:
            problems.append((src, "Same new name as another file in this batch"))
            continue
        seen_targets[key] = src
    return problems


def _csv_safe(v) -> str:
    s = "" if v is None else str(v)
    if s[:1] in ("=", "+", "-", "@"):
        return "'" + s
    return s


def write_rename_log(root: str, batch_id: str, items: List[dict]) -> str:
    path = os.path.join(root, "bankdoc_rename_log_%s.csv" % stamp())
    headers = ["Batch ID", "Time", "Result", "Folder", "Original file name", "System proposed name",
               "Name changed manually in preview?", "Final name used", "Reason / error", "Backup copy",
               "SHA-256 of file", "Date", "Recipient", "Amount (Rs.)", "Remarks", "Transaction ID",
               "Payer", "Mode", "Fields edited manually", "Notes"]
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for it in items:
            f = it.get("fields", {})
            w.writerow([_csv_safe(x) for x in [
                batch_id, it.get("time", ""), it.get("result", ""), os.path.dirname(it["path"]),
                it["name"], it.get("system_name", ""),
                "YES - manually changed" if it.get("manual_name") else "No",
                it.get("final_name", ""), it.get("reason", ""), it.get("backup", ""), it.get("sha256", ""),
                fmt_date_display(f.get("date", "")), f.get("payee", ""), f.get("amount", ""),
                f.get("remarks", ""), f.get("txn_id", ""), f.get("payer", ""), f.get("mode", ""),
                ", ".join(it.get("edited_fields", [])), it.get("notes", "")]])
    return path


def run_rename_batch(plan: List[dict], skipped: List[dict], root: str, backup_session_dir: Optional[str],
                     save_log: bool, progress: Callable) -> dict:
    """The whole safe rename procedure (runs in a background thread).
    Order: pre-flight checks -> fingerprints -> backup -> session file -> rename."""
    res = {"stage": "", "failures": [], "entries": [], "log_path": "", "log_error": "", "backup_dir": backup_session_dir}
    n = len(plan)

    problems = preflight_check(plan)
    if problems:
        res["stage"] = "preflight_failed"
        res["failures"] = problems
        return res

    for i, p in enumerate(plan, 1):
        progress("hash", i, n, p["name"])
        try:
            p["sha256"] = sha256_file(p["path"])
        except OSError as e:
            res["stage"] = "preflight_failed"
            res["failures"] = [(p["path"], "Could not read the file: %s" % short_err(e, 120))]
            return res

    bpaths: Dict[str, str] = {}
    if backup_session_dir:
        failures, bpaths = run_backup(plan, root, backup_session_dir, progress)
        if failures:
            res["stage"] = "backup_failed"
            res["failures"] = failures
            return res

    # ---- session file (so a crash never leaves us guessing)
    try:
        try:
            data = load_session(root)
        except SessionCorrupt as e:
            sp = session_path(root)
            moved = sp + ".corrupt-" + stamp()
            os.replace(sp, moved)
            LOG.warning("rename_session.json was unreadable (%s); kept as %s and started a new one." % (e, moved))
            data = None
        if data is None:
            data = new_session(root)
        reconcile_session(data)
        batch_id = "B" + stamp() + "_" + uuid.uuid4().hex[:4]
        batch = {"batch_id": batch_id, "started": now_text(), "finished": "", "status": "running",
                 "backup_folder": backup_session_dir or "", "undone": False, "entries": []}
        for p in plan:
            batch["entries"].append({
                "original_path": p["path"], "original_name": p["name"],
                "new_path": p["new_path"], "new_name": p["new_name"],
                "status": "pending", "error": "", "sha256": p["sha256"],
                "backup_copy": bpaths.get(p["path"], ""), "time": ""})
        data["batches"].append(batch)
        atomic_write_json(session_path(root), data)
    except Exception as e:
        LOG.exception("Could not write the session file")
        res["stage"] = "session_failed"
        res["failures"] = [("(session file)", "Cannot write %s in the folder: %s. Nothing was renamed."
                            % (SESSION_FILE, short_err(e, 120)))]
        return res
    res["batch_id"] = batch_id

    # ---- the renaming itself
    stopped_reason = ""
    for i, (p, ent) in enumerate(zip(plan, batch["entries"]), 1):
        item = dict(p)
        item["time"] = now_text()
        item["backup"] = bpaths.get(p["path"], "")
        if stopped_reason:
            ent["status"] = "not_attempted"
            ent["error"] = "Batch stopped earlier"
            item["result"] = "NOT RENAMED"
            item["reason"] = "Batch stopped earlier: " + stopped_reason
            item["final_name"] = ""
            res["entries"].append(item)
            continue
        progress("rename", i, n, p["name"])
        ent["status"] = "in_progress"
        try:
            atomic_write_json(session_path(root), data)
            safe_rename(p["path"], p["new_path"])
            ent["status"] = "renamed"
            ent["time"] = now_text()
            item["result"] = "RENAMED"
            item["reason"] = ""
            item["final_name"] = p["new_name"]
        except Exception as e:
            ent["status"] = "failed"
            ent["error"] = short_err(e, 200)
            item["result"] = "FAILED"
            item["reason"] = short_err(e, 200)
            item["final_name"] = ""
            stopped_reason = "%s could not be renamed (%s)" % (p["name"], short_err(e, 120))
            LOG.error("Rename stopped: %s" % stopped_reason)
        try:
            atomic_write_json(session_path(root), data)
        except Exception as e:
            LOG.exception("Could not update session file")
            if not stopped_reason:
                stopped_reason = "session file could not be updated (%s)" % short_err(e, 100)
        res["entries"].append(item)
    batch["finished"] = now_text()
    batch["status"] = "stopped" if stopped_reason else "completed"
    try:
        atomic_write_json(session_path(root), data)
    except Exception:
        LOG.exception("Could not write final session state")
    res["stage"] = "stopped" if stopped_reason else "done"
    res["stop_reason"] = stopped_reason

    if save_log:
        items = list(res["entries"])
        for s in skipped:
            s2 = dict(s)
            s2["time"] = now_text()
            s2["result"] = "SKIPPED"
            s2["final_name"] = ""
            items.append(s2)
        try:
            res["log_path"] = write_rename_log(root, batch_id, items)
        except Exception as e:
            LOG.exception("Could not save the rename log")
            res["log_error"] = short_err(e, 150)
    return res


def run_undo(root: str, progress: Callable) -> dict:
    """Undo the most recent batch, but ONLY for files whose current state is exactly
    what we left: new name exists, original name is free and the SHA-256 matches."""
    out = {"status": "", "restored": [], "skipped": [], "message": ""}
    try:
        data = load_session(root)
    except SessionCorrupt as e:
        out["status"] = "error"
        out["message"] = "rename_session.json cannot be read (%s)." % e
        return out
    if data is None:
        out["status"] = "nothing"
        out["message"] = "No rename session found in this folder."
        return out
    reconcile_session(data)
    batch = last_undoable_batch(data)
    if batch is None:
        out["status"] = "nothing"
        out["message"] = "There is no batch left to undo."
        return out
    entries = [e for e in batch["entries"] if e.get("status") == "renamed"]
    n = len(entries)
    for i, e in enumerate(reversed(entries), 1):
        progress("undo", i, n, e["new_name"])
        new, old = e["new_path"], e["original_path"]
        if not os.path.isfile(new):
            out["skipped"].append((new, "The renamed file is not there any more (moved, renamed or deleted by hand)"))
            continue
        if os.path.exists(old):
            out["skipped"].append((new, "The original name '%s' is now used by another file" % e["original_name"]))
            continue
        want = e.get("sha256", "")
        if not want:
            out["skipped"].append((new, "No fingerprint stored - cannot verify it is the same file"))
            continue
        try:
            if sha256_file(new) != want:
                out["skipped"].append((new, "File content differs from what was renamed - not touched"))
                continue
            safe_rename(new, old)
            e["status"] = "undone"
            e["undone_at"] = now_text()
            out["restored"].append((new, old))
        except Exception as ex:
            LOG.exception("Undo failed for %s" % new)
            out["skipped"].append((new, "Could not undo: %s" % short_err(ex, 120)))
    if not any(e.get("status") == "renamed" for e in batch["entries"]):
        batch["undone"] = True
        batch["status"] = "undone"
    else:
        batch["status"] = "partially_undone"
    batch["undo_time"] = now_text()
    try:
        atomic_write_json(session_path(root), data)
    except Exception as ex:
        LOG.exception("Could not save session after undo")
        out["message"] = "Undo done, but the session file could not be updated: %s" % short_err(ex, 100)
    out["status"] = "done"
    return out


# ==========================================================================
#  EXPORTS  (Excel + PDF)  -  passwords are never part of any row
# ==========================================================================
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _xl_text(v) -> str:
    return _CTRL_RE.sub("", "" if v is None else str(v))


def export_excel(rows: List[Row], path: str, root: str, codes: List[str], show_proposed: bool) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Extracted data"
    headers = ["Sr", "Original file name", "Folder", "Status", "Approved", "Date", "Recipient / Payee",
               "Amount (Rs.)", "Remarks / Narration", "Transaction ID", "Payer / Sender", "Mode",
               "Fields edited manually", "Warnings / notes"]
    if show_proposed:
        headers += ["Proposed new name", "Proposed name edited manually?"]
    ws.append(headers)
    head_fill = PatternFill("solid", fgColor="2B2D6E")
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)

    def put(r_idx, c_idx, value):
        cell = ws.cell(row=r_idx, column=c_idx)
        if isinstance(value, str):
            cell.value = _xl_text(value)
            cell.data_type = "s"
        else:
            cell.value = value
        return cell

    for i, r in enumerate(rows, 1):
        ri = i + 1
        put(ri, 1, i)
        put(ri, 2, r.name)
        put(ri, 3, r.rel)
        put(ri, 4, r.status)
        put(ri, 5, "Yes" if r.approved else "No")
        if r.fields["date"]:
            c = put(ri, 6, dt.date.fromisoformat(r.fields["date"]))
            c.number_format = "dd-mmm-yyyy"
        else:
            put(ri, 6, "")
        amt = r.fields["amount"]
        if amt:
            if "." in amt:
                c = put(ri, 8, float(Decimal(amt)))
                c.number_format = '"Rs."0.00'
            else:
                c = put(ri, 8, int(amt))
                c.number_format = '"Rs."0'
        else:
            put(ri, 8, "")
        put(ri, 7, r.fields["payee"])
        put(ri, 9, r.fields["remarks"])
        put(ri, 10, r.fields["txn_id"])
        put(ri, 11, r.fields["payer"])
        put(ri, 12, r.fields["mode"])
        put(ri, 13, ", ".join(FIELD_LABELS[k] for k in FIELD_KEYS if k in r.edited))
        put(ri, 14, r.notes_text())
        if show_proposed:
            put(ri, 15, r.final_name)
            put(ri, 16, "YES" if r.proposed_override is not None else "No")
    widths = [5, 38, 18, 30, 9, 13, 28, 14, 36, 24, 28, 8, 22, 60, 44, 16]
    for idx, w in enumerate(widths[:len(headers)], 1):
        ws.column_dimensions[get_column_letter(idx)].width = w
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(headers)), max(1, len(rows) + 1))

    s = wb.create_sheet("Summary")
    s.append(["BankDoc Processor & Renamer - export summary"])
    s.append(["Created", now_text()])
    s.append(["Source folder", _xl_text(root)])
    s.append(["Files listed", len(rows)])
    s.append(["Approved", sum(1 for r in rows if r.approved)])
    s.append(["Need manual review", sum(1 for r in rows if r.status in BLOCKED_STATUSES or r.status in (S_INCOMPLETE, S_MISMATCH))])
    s.column_dimensions["A"].width = 28
    s.column_dimensions["B"].width = 60
    s["A1"].font = Font(bold=True, size=13)
    wb.save(path)


def _pdf_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    candidates = [
        r"C:\Windows\Fonts\Nirmala.ttf", r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("BankDocFont", p))
                return "BankDocFont"
            except Exception:
                continue
    return "Helvetica"


def export_pdf(rows: List[Row], path: str, root: str, show_proposed: bool) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    font = _pdf_font()
    cell = ParagraphStyle("cell", fontName=font, fontSize=7, leading=8.6)
    head = ParagraphStyle("head", fontName=font, fontSize=7.5, leading=9, textColor=colors.white)
    title = ParagraphStyle("title", fontName=font, fontSize=14, leading=18, textColor=colors.HexColor("#2B2D6E"))
    small = ParagraphStyle("small", fontName=font, fontSize=8, leading=10)

    def P(t, st=cell):
        return Paragraph(xml_escape(_xl_text(t)).replace("\n", "<br/>"), st)

    heads = ["#", "Original file", "Date", "Recipient / Payee", "Amount", "Remarks", "Txn ID", "Payer", "Status"]
    widths = [8, 50, 19, 42, 20, 42, 32, 36, 36]
    if show_proposed:
        heads.append("Proposed name")
        widths.append(46)
    total_w = sum(widths)
    avail = landscape(A4)[0] - 20 * mm
    col_w = [w / total_w * avail for w in widths]
    data = [[P(h, head) for h in heads]]
    for i, r in enumerate(rows, 1):
        line = [P(str(i)), P(r.name), P(fmt_date_display(r.fields["date"])), P(r.fields["payee"]),
                P(("Rs." + r.fields["amount"]) if r.fields["amount"] else ""), P(r.fields["remarks"]),
                P(r.fields["txn_id"]), P(r.fields["payer"]), P(r.status + ("" if r.approved else " (not approved)"))]
        if show_proposed:
            line.append(P(r.final_name))
        data.append(line)
    doc = SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title="Bank transaction extract",
                            author=APP_NAME)
    tbl = Table(data, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B2D6E")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F3FF")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8BEE6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story = [Paragraph(xml_escape(APP_NAME + " - extracted transactions"), title),
             Paragraph(xml_escape("Created %s | Source folder: %s | Files: %d" % (now_text(), root, len(rows))), small),
             Spacer(1, 4 * mm), tbl]

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont(font, 7)
        canvas.drawRightString(landscape(A4)[0] - 10 * mm, 6 * mm, "Page %d" % d.page)
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


# ==========================================================================
#  GUI  (CustomTkinter)
# ==========================================================================
C = {
    "indigo": "#2B2D6E", "indigo2": "#3B3F9E", "magenta": "#E6007E", "teal": "#00A99D",
    "orange": "#FF8A00", "blue": "#2F6BFF", "green": "#1FA463", "red": "#E5383B",
    "bg": "#EEF1FF", "card": "#FFFFFF", "text": "#1B1E3D", "muted": "#5B6094",
    "yellow": "#FFC21A", "purple": "#7B4DFF", "pink_bg": "#FFE3E3",
}
FONT = "Segoe UI"


def setup_ttk_style(master) -> None:
    st = ttk.Style(master)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    st.configure("Treeview", rowheight=28, font=(FONT, 10), background="#FFFFFF",
                 fieldbackground="#FFFFFF", foreground=C["text"], bordercolor="#C9CEF2")
    st.configure("Treeview.Heading", font=(FONT, 10, "bold"), background=C["indigo2"],
                 foreground="white", relief="flat", padding=(6, 6))
    st.map("Treeview.Heading", background=[("active", C["magenta"])])

    def fixed_map(option):
        return [e for e in st.map("Treeview", query_opt=option) if e[:2] != ("!disabled", "!selected")]
    st.map("Treeview", foreground=fixed_map("foreground") + [("selected", "white")],
           background=fixed_map("background") + [("selected", C["indigo2"])])


def show_help(widget, title: str, text: str) -> None:
    messagebox.showinfo(title, text, parent=widget.winfo_toplevel())


def help_button(parent, title: str, text: str):
    """Small orange '?' button that explains a feature in plain English."""
    return ctk.CTkButton(parent, text="?", width=26, height=26, corner_radius=13,
                         fg_color=C["orange"], hover_color="#E07600", text_color="white",
                         font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
                         command=lambda: show_help(parent, title, text))


def make_card(parent, title: str, color: str):
    outer = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=12, border_width=1, border_color="#D5DAFF")
    outer.grid_columnconfigure(0, weight=1)
    outer.grid_rowconfigure(1, weight=1)
    head = ctk.CTkFrame(outer, fg_color=color, corner_radius=10, height=34)
    head.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
    ctk.CTkLabel(head, text=title, text_color="white",
                 font=ctk.CTkFont(family=FONT, size=14, weight="bold")).pack(side="left", padx=12, pady=4)
    body = ctk.CTkFrame(outer, fg_color="transparent")
    body.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 10))
    return outer, body, head


def make_tree(parent, columns, headings, widths, height=5, selectmode="extended"):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode=selectmode, height=height)
    for c in columns:
        tree.heading(c, text=headings[c])
        tree.column(c, width=widths[c], minwidth=40, anchor="w", stretch=False)
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    return frame, tree


def big_button(parent, text, command, color, hover=None, width=200, height=38, state="normal"):
    return ctk.CTkButton(parent, text=text, command=command, fg_color=color,
                         hover_color=hover or color, text_color="white", width=width, height=height,
                         corner_radius=10, state=state,
                         font=ctk.CTkFont(family=FONT, size=13, weight="bold"))


# --------------------------------------------------------------------------
# Background task runner  (keeps the window responsive)
# --------------------------------------------------------------------------
class TaskRunner:
    def __init__(self):
        self.q: "queue.Queue" = queue.Queue()

    def run(self, fn, on_done=None, on_error=None, on_progress=None):
        def progress(*a):
            if on_progress is not None:
                self.q.put((on_progress, a))

        def target():
            try:
                res = fn(progress)
            except BaseException as e:  # noqa
                LOG.exception("Background task failed")
                self.q.put((on_error or self._default_error, (e,)))
            else:
                if on_done is not None:
                    self.q.put((on_done, (res,)))

        threading.Thread(target=target, daemon=True).start()

    @staticmethod
    def _default_error(e):
        messagebox.showerror("Unexpected error",
                             "Something unexpected went wrong:\n\n%s\n\nDetails are saved in the processing log."
                             % short_err(e, 300))

    def drain(self):
        while True:
            try:
                cb, args = self.q.get_nowait()
            except queue.Empty:
                return
            try:
                cb(*args)
            except Exception:
                LOG.exception("Error while updating the screen")


# --------------------------------------------------------------------------
# Input normalisation for manual edits
# --------------------------------------------------------------------------
def normalize_field_input(key: str, text: str) -> Tuple[bool, str, str]:
    """Returns (ok, normalised_value, error_message)."""
    t = collapse_ws(text)
    if key == "date":
        if not t:
            return True, "", ""
        iso = parse_date_text(t)
        if not iso:
            return False, "", ("That is not a date I understand. Use for example 05-01-2024, 05/01/2024 "
                               "or 05-Jan-2024 (day first).")
        return True, iso, ""
    if key == "amount":
        if not t:
            return True, "", ""
        a = parse_amount_text(t)
        if a is None:
            return False, "", "That is not a valid amount. Type one number, for example 1000 or 1000.25"
        return True, a, ""
    if key == "mode":
        return True, t.upper(), ""
    return True, t, ""


def page_natural_width(path: str, kind: str, page_index: int, cache: Optional[DecryptedCache]) -> float:
    if kind == "pdf":
        doc = open_pdf_document(path, cache)
        try:
            page = doc.load_page(max(0, min(page_index, doc.page_count - 1)))
            return float(page.rect.width) * 96.0 / 72.0
        finally:
            doc.close()
    with Image.open(path) as im:
        return float(im.width)


# --------------------------------------------------------------------------
# Dialogs
# --------------------------------------------------------------------------
class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, master, names: List[str]):
        super().__init__(master)
        self.title("Enter PDF password")
        self.geometry("600x560")
        self.minsize(520, 480)
        self.configure(fg_color=C["bg"])
        self.result: Optional[str] = None
        self.transient(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        banner = ctk.CTkFrame(self, fg_color=C["pink_bg"], border_color=C["red"], border_width=2, corner_radius=10)
        banner.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        ctk.CTkLabel(banner, text=WARNING_PASSWORD, text_color="#9B1C1F", wraplength=530, justify="left",
                     font=ctk.CTkFont(family=FONT, size=13, weight="bold")).pack(padx=12, pady=10)

        ctk.CTkLabel(self, text="This ONE password will be tried on the %d selected file(s) below:" % len(names),
                     text_color=C["text"], font=ctk.CTkFont(family=FONT, size=13)
                     ).grid(row=1, column=0, sticky="w", padx=16, pady=(4, 2))
        box = ctk.CTkTextbox(self, height=150, fg_color="white", text_color=C["text"], border_width=1,
                             border_color="#C9CEF2")
        box.grid(row=2, column=0, sticky="nsew", padx=14, pady=4)
        box.insert("end", "\n".join(names))
        box.configure(state="disabled")

        ctk.CTkLabel(self, text="Password:", text_color=C["text"],
                     font=ctk.CTkFont(family=FONT, size=13, weight="bold")).grid(row=3, column=0, sticky="w", padx=16)
        self.entry = ctk.CTkEntry(self, show="•", height=38, placeholder_text="type the password here")
        self.entry.grid(row=4, column=0, sticky="ew", padx=14, pady=4)
        self.show_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(self, text="Show the password while typing", variable=self.show_var,
                        command=self._toggle_show, text_color=C["text"]).grid(row=5, column=0, sticky="w", padx=16, pady=4)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=6, column=0, sticky="ew", padx=14, pady=12)
        btns.grid_columnconfigure((0, 1), weight=1)
        big_button(btns, "🔓 Apply to selected files", self._ok, C["green"], "#168A50", width=240).grid(row=0, column=0, padx=6)
        big_button(btns, "Cancel", self._cancel, C["muted"], "#444A80", width=140).grid(row=0, column=1, padx=6)
        self.entry.bind("<Return>", lambda e: self._ok())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.after(150, self._grab)

    def _grab(self):
        try:
            self.grab_set()
            self.entry.focus_set()
        except tk.TclError:
            pass

    def _toggle_show(self):
        self.entry.configure(show="" if self.show_var.get() else "•")

    def _ok(self):
        pw = self.entry.get()
        if not pw:
            messagebox.showwarning("Password needed", "Please type the password first.", parent=self)
            return
        self.result = pw
        self.entry.delete(0, "end")
        self.destroy()

    def _cancel(self):
        try:
            self.entry.delete(0, "end")
        except Exception:
            pass
        self.result = None
        self.destroy()


def ask_password(master, names: List[str]) -> Optional[str]:
    dlg = PasswordDialog(master, names)
    master.wait_window(dlg)
    pw = dlg.result
    dlg.result = None
    return pw


class ProblemDialog(ctk.CTkToplevel):
    """Shows a list of affected files + reasons. Result True = user pressed Retry."""

    def __init__(self, master, title: str, intro: str, items: List[Tuple[str, str]], allow_retry: bool):
        super().__init__(master)
        self.title(title)
        self.geometry("780x520")
        self.minsize(560, 380)
        self.configure(fg_color=C["bg"])
        self.result = False
        self.transient(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text=intro, text_color="#9B1C1F", wraplength=730, justify="left",
                     font=ctk.CTkFont(family=FONT, size=13, weight="bold")).grid(row=0, column=0, sticky="w", padx=16, pady=12)
        box = ctk.CTkTextbox(self, fg_color="white", text_color=C["text"], border_width=1, border_color="#C9CEF2")
        box.grid(row=1, column=0, sticky="nsew", padx=14, pady=4)
        for f, why in items:
            box.insert("end", "• %s\n    Reason: %s\n\n" % (f, why))
        box.configure(state="disabled")
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, pady=12)
        if allow_retry:
            big_button(btns, "🔁 Retry", self._retry, C["green"], "#168A50", width=160).pack(side="left", padx=8)
        big_button(btns, "Cancel / Close", self._close, C["red"], "#C0272A", width=170).pack(side="left", padx=8)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(150, self._grab)

    def _grab(self):
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _retry(self):
        self.result = True
        self.destroy()

    def _close(self):
        self.result = False
        self.destroy()


def show_problems(master, title: str, intro: str, items: List[Tuple[str, str]], allow_retry: bool) -> bool:
    dlg = ProblemDialog(master, title, intro, items, allow_retry)
    master.wait_window(dlg)
    return dlg.result


# --------------------------------------------------------------------------
# Split-screen document viewer  (zoom, pan, page flipping)
# --------------------------------------------------------------------------
class DocViewer(ctk.CTkFrame):
    def __init__(self, master, app, on_close, on_pick):
        super().__init__(master, fg_color=C["card"], corner_radius=12, border_width=1, border_color="#D5DAFF")
        self.app = app
        self.on_close = on_close
        self.on_pick = on_pick
        self.row: Optional[Row] = None
        self.page = 0
        self.pages = 1
        self.zoom = 1.0
        self._photo = None
        self._auto_fit_pending = False
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Row 2 (canvas) now gets all the vertical space

        # Row 0: Header bar with filename and Close button
        head = ctk.CTkFrame(self, fg_color=C["purple"], corner_radius=10)
        head.grid(row=0, column=0, sticky="ew", padx=6, pady=4)
        head.grid_columnconfigure(0, weight=1)
        self.title_lbl = ctk.CTkLabel(head, text="Original document", text_color="white", anchor="w",
                                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"))
        self.title_lbl.grid(row=0, column=0, sticky="ew", padx=10, pady=4)
        ctk.CTkButton(head, text="✖ Close", width=70, height=24, fg_color="#FFFFFF", text_color=C["purple"],
                      hover_color="#E8E0FF", command=self.on_close).grid(row=0, column=1, padx=8, pady=4)

        # Row 1: Page & Zoom toolbar (status label and candidate frame completely removed)
        bar = ctk.CTkFrame(self, fg_color="#F1F3FF", corner_radius=8)
        bar.grid(row=1, column=0, sticky="ew", padx=6, pady=2)
        mk = lambda t, cmd, w=32: ctk.CTkButton(bar, text=t, width=w, height=26, command=cmd, fg_color=C["blue"],
                                                hover_color=C["indigo2"], text_color="white")
        mk("◀", self.prev_page).pack(side="left", padx=(6, 2), pady=3)
        self.page_lbl = ctk.CTkLabel(bar, text="Page 1 / 1", width=76, text_color=C["text"])
        self.page_lbl.pack(side="left")
        mk("▶", self.next_page).pack(side="left", padx=2)
        mk("−", lambda: self.zoom_by(1 / 1.25)).pack(side="left", padx=(10, 2))
        self.zoom_lbl = ctk.CTkLabel(bar, text="100%", width=48, text_color=C["text"])
        self.zoom_lbl.pack(side="left")
        mk("+", lambda: self.zoom_by(1.25)).pack(side="left", padx=2)
        mk("Fit width", self.fit_width, 74).pack(side="left", padx=(8, 2))
        mk("100%", self.actual_size, 48).pack(side="left", padx=2)

        # Row 2: Full-size Document Canvas
        cf = ctk.CTkFrame(self, fg_color="transparent")
        cf.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        cf.grid_rowconfigure(0, weight=1)
        cf.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(cf, bg="#52567A", highlightthickness=0, cursor="fleur")
        vs = ttk.Scrollbar(cf, orient="vertical", command=self.canvas.yview)
        hs = ttk.Scrollbar(cf, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<ButtonPress-1>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B1-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", self._on_wheel)
        self.canvas.bind("<Button-5>", self._on_wheel)
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event):
        if self._auto_fit_pending and event.width > 80 and self.row is not None:
            self._auto_fit_pending = False
            self.fit_width()

    # ---- loading ------------------------------------------------------
    def load(self, row: Row):
        self.row = row
        self.page = 0
        self.title_lbl.configure(text="Original: " + row.name)
        try:
            self.pages = get_page_count(row.path, row.kind, self.app.cache)
        except Exception as e:
            LOG.exception("Viewer could not open %s" % row.path)
            self.pages = 1
            self._show_message("Cannot display this file:\n%s" % short_err(e, 200))
            self.refresh_header()
            return
        self.refresh_header()
        self._auto_fit_pending = True
        self.fit_width()

    def refresh_header(self):
        if self.row is not None:
            self.page_lbl.configure(text="Page %d / %d" % (self.page + 1, self.pages))
    # ---- drawing ------------------------------------------------------
    def _show_message(self, text: str):
        self.canvas.delete("all")
        self._photo = None
        self.canvas.create_text(20, 20, anchor="nw", text=text, fill="white", width=420, font=(FONT, 11))

    def _render(self, reset_scroll: bool = False):
        r = self.row
        if r is None:
            return
        try:
            x0 = 0.0 if reset_scroll else self.canvas.xview()[0]
            y0 = 0.0 if reset_scroll else self.canvas.yview()[0]
            img, _nat = render_page_image(r.path, r.kind, self.page, self.zoom, self.app.cache)
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self._photo, anchor="nw")
            self.canvas.configure(scrollregion=(0, 0, img.width, img.height))
            self.canvas.xview_moveto(x0)
            self.canvas.yview_moveto(y0)
        except Exception as e:
            LOG.exception("Viewer could not draw %s" % r.path)
            self._show_message("Cannot display this page:\n%s" % short_err(e, 200))
        self.page_lbl.configure(text="Page %d / %d" % (self.page + 1, self.pages))
        self.zoom_lbl.configure(text="%d%%" % int(round(self.zoom * 100)))

    def fit_width(self):
        r = self.row
        if r is None:
            return
        try:
            nat = page_natural_width(r.path, r.kind, self.page, self.app.cache)
            cw = self.canvas.winfo_width()
            if cw < 80:
                cw = 480
            w = max(cw - 24, 240)
            self.zoom = max(0.15, min(6.0, w / max(nat, 1.0)))
        except Exception:
            self.zoom = 1.0
        self._render(reset_scroll=True)

    def actual_size(self):
        self.zoom = 1.0
        self._render()

    def zoom_by(self, factor: float):
        self.zoom = max(0.15, min(6.0, self.zoom * factor))
        self._render()

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._render(reset_scroll=True)

    def next_page(self):
        if self.page < self.pages - 1:
            self.page += 1
            self._render(reset_scroll=True)

    def _on_wheel(self, event):
        if getattr(event, "num", 0) == 4:
            delta = 120
        elif getattr(event, "num", 0) == 5:
            delta = -120
        else:
            delta = event.delta
        if event.state & 0x0004:      # Ctrl held -> zoom
            self.zoom_by(1.15 if delta > 0 else 1 / 1.15)
        elif event.state & 0x0001:    # Shift held -> sideways
            self.canvas.xview_scroll(-3 if delta > 0 else 3, "units")
        else:
            self.canvas.yview_scroll(-3 if delta > 0 else 3, "units")
        return "break"


# ==========================================================================
#  PAGE 1 - choose folder, check files, passwords
# ==========================================================================
class PageFiles(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=C["bg"])
        self.app = app
        self.path_var = tk.StringVar(value="")
        self.sub_var = tk.BooleanVar(value=False)
        self.entries: List[FileEntry] = []
        self.bad_map: Dict[str, FileEntry] = {}
        self.scanned_root = ""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ---- card 1 : folder
        c1, b1, h1 = make_card(self, "①  Choose the folder that has your bank NEFT / RTGS / IMPS files", C["blue"])
        c1.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        b1.grid_columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(b1, textvariable=self.path_var, height=38,
                                       placeholder_text="No folder chosen yet - click 'Browse...'")
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=(4, 4))
        big_button(b1, "📁 Browse...", self.browse, C["blue"], C["indigo2"], width=130).grid(row=0, column=1, padx=4)
        help_button(b1, "Folder", "Pick the folder where you saved the bank payment acknowledgements "
                    "(NEFT / RTGS / IMPS). The tool only READS this folder until you choose to rename files "
                    "in a later step.").grid(row=0, column=2, padx=4)
        sw = ctk.CTkSwitch(b1, text="Include files inside sub-folders too (optional)", variable=self.sub_var,
                           progress_color=C["teal"], text_color=C["text"])
        sw.grid(row=1, column=0, sticky="w", pady=4)
        help_button(b1, "Sub-folders", "OFF = only files directly inside the chosen folder.\n"
                    "ON = also every folder inside it (and the folders inside those).").grid(row=1, column=1, sticky="w", padx=4)
        ctk.CTkLabel(b1, text="Supported files: " + SUPPORTED_TEXT + ". Any other file type is listed below as "
                     "'not accessible' and will be skipped.", text_color=C["muted"], justify="left", wraplength=900,
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold")).grid(row=2, column=0, columnspan=3, sticky="w", pady=2)
        self.scan_btn = big_button(b1, "🔍 Check all files", self.start_scan, C["magenta"], "#BF006A", width=190)
        self.scan_btn.grid(row=3, column=0, sticky="w", pady=(6, 2))
        help_button(b1, "Check files", "The tool opens every PDF/image just enough to see if it can be read. "
                    "It tells you which files are locked with a password, damaged, empty, or not a PDF/image.").grid(
            row=3, column=1, sticky="w", padx=4)
        self.prog = ctk.CTkProgressBar(b1, progress_color=C["teal"])
        self.prog.set(0)
        self.prog.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self.status_lbl = ctk.CTkLabel(b1, text="Nothing checked yet.", text_color=C["muted"], anchor="w")
        self.status_lbl.grid(row=5, column=0, columnspan=3, sticky="ew")

        # ---- banner (shown ONLY when password-protected files are found)
        self.ban = ctk.CTkFrame(self, fg_color=C["pink_bg"], border_color=C["red"], border_width=2, corner_radius=10)
        ctk.CTkLabel(self.ban, text=WARNING_PASSWORD, text_color="#9B1C1F", wraplength=1000, justify="left",
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold")).pack(padx=12, pady=6, anchor="w")

        # ---- side-by-side container for NOT accessible (left) and Accessible (right)
        split = ctk.CTkFrame(self, fg_color="transparent")
        split.grid(row=2, column=0, sticky="nsew", padx=14, pady=4)
        split.grid_columnconfigure(0, weight=1, uniform="panes")
        split.grid_columnconfigure(1, weight=1, uniform="panes")
        split.grid_rowconfigure(0, weight=1)

        # ---- card 2 : non accessible (LEFT)
        c2, b2, h2 = make_card(split, "②  NOT accessible files  (with the reason)", C["red"])
        c2.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)
        b2.grid_columnconfigure(0, weight=1)
        b2.grid_rowconfigure(0, weight=1)
        f, self.bad_tree = make_tree(
            b2, ("file", "folder", "reason"),
            {"file": "File name", "folder": "Sub-folder", "reason": "Why it cannot be used"},
            {"file": 210, "folder": 120, "reason": 360}, height=8)
        f.grid(row=0, column=0, sticky="nsew")
        self.bad_tree.tag_configure("locked", background="#FFF1D6")
        self.bad_tree.tag_configure("broken", background="#FFE0E2")
        bar = ctk.CTkFrame(b2, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        big_button(bar, "☑ Select locked", self.select_locked, C["purple"], "#5B35D6", width=140, height=32).pack(side="left", padx=(0, 4))
        big_button(bar, "🔑 Enter password...", self.enter_password, C["orange"], "#E07600", width=170, height=32).pack(side="left", padx=4)
        big_button(bar, "🔄 Re-check", self.start_scan, C["teal"], "#008A80", width=115, height=32).pack(side="left", padx=4)
        help_button(bar, "Passwords", "1. Click one locked file (or hold Ctrl / Shift to pick several, or press "
                    "'Select locked').\n2. Click 'Enter password...' and type the password once. "
                    "It is tried on every selected file.\n3. The lists refresh automatically. Files that open "
                    "move to the accessible list.\n\nYour password is NOT saved anywhere (not on disk, not in logs). "
                    "The unlocked copy is kept in computer memory only until you close this program. The original "
                    "PDF on disk is never changed.").pack(side="left", padx=4)

        # ---- card 3 : accessible (RIGHT)
        c3, b3, h3 = make_card(split, "③  Accessible files  (ready to be read)", C["green"])
        c3.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)
        b3.grid_columnconfigure(0, weight=1)
        b3.grid_rowconfigure(0, weight=1)
        f2, self.good_tree = make_tree(
            b3, ("file", "folder", "type", "size", "note"),
            {"file": "File name", "folder": "Sub-folder", "type": "Type", "size": "Size", "note": "Note"},
            {"file": 230, "folder": 120, "type": 60, "size": 80, "note": 240}, height=8)
        f2.grid(row=0, column=0, sticky="nsew")
        self.good_tree.tag_configure("unlocked", background="#E3F8EC")

        # ---- bottom bar
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 12))
        bot.grid_columnconfigure(0, weight=1)
        self.count_lbl = ctk.CTkLabel(bot, text="", text_color=C["text"], anchor="w",
                                      font=ctk.CTkFont(family=FONT, size=13, weight="bold"))
        self.count_lbl.grid(row=0, column=0, sticky="w")
        self.skip_lbl = ctk.CTkLabel(bot, text="", text_color=C["red"], anchor="w",
                                     font=ctk.CTkFont(family=FONT, size=13, weight="bold"))
        self.skip_lbl.grid(row=1, column=0, sticky="w")
        self.next_btn = big_button(bot, "Proceed to Step 2  ▶", self.proceed,
                                   C["green"], "#168A50", width=260, height=44, state="disabled")
        self.next_btn.grid(row=0, column=1, rowspan=2, sticky="e")

    # ---- folder -------------------------------------------------------
    def on_show(self):
        pass

    def browse(self):
        d = filedialog.askdirectory(title="Choose the folder with bank transaction PDFs / images", mustexist=True)
        if d:
            self.path_var.set(os.path.normpath(d))

    def start_scan(self):
        if self.app.busy:
            messagebox.showinfo("Please wait", "Another task is still running.", parent=self.winfo_toplevel())
            return
        root = self.path_var.get().strip().strip('"')
        if not root or not os.path.isdir(root):
            messagebox.showwarning("Folder needed", "Please choose a valid folder first (click 'Browse...').",
                                   parent=self.winfo_toplevel())
            return
        root = os.path.normpath(root)
        if self.scanned_root and os.path.normcase(self.scanned_root) != os.path.normcase(root):
            p3 = self.app.pages.get(3)
            if p3 is not None and p3.rows and not messagebox.askyesno(
                    "Different folder",
                    "You chose a different folder. The table already built in Step 3 belongs to the previous folder and "
                    "will be cleared.\n\nContinue?", parent=self.winfo_toplevel()):
                return
            self.app.cache.clear()
            self.app.good_entries = []
            if p3 is not None:
                p3.reset()
        self.scanned_root = root
        include = bool(self.sub_var.get())
        self.app.root_folder = root
        self.app.include_sub = include
        self.app.busy = True
        self.scan_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")
        self.prog.set(0)
        self.status_lbl.configure(text="Checking files...", text_color=C["muted"])
        LOG.info("Checking folder: %s (sub-folders: %s)" % (root, "yes" if include else "no"))
        cache = self.app.cache
        self.app.runner.run(lambda progress: scan_folder(root, include, cache, progress),
                            on_done=self._scan_done, on_error=self._scan_error, on_progress=self._scan_progress)

    def _scan_progress(self, i, total, name):
        self.prog.set(i / max(total, 1))
        self.status_lbl.configure(text="Checked %d of %d:  %s" % (i, total, name))

    def _scan_error(self, e):
        self.app.busy = False
        self.scan_btn.configure(state="normal")
        self.status_lbl.configure(text="Could not check the folder.", text_color=C["red"])
        messagebox.showerror("Cannot read folder", "The folder could not be checked:\n\n%s" % short_err(e, 300),
                             parent=self.winfo_toplevel())

    def _scan_done(self, entries: List[FileEntry]):
        self.app.busy = False
        self.scan_btn.configure(state="normal")
        self.entries = entries
        self.prog.set(1)
        self.bad_tree.delete(*self.bad_tree.get_children())
        self.good_tree.delete(*self.good_tree.get_children())
        self.bad_map = {}
        n_good = n_bad = n_lock = 0
        for i, e in enumerate(entries):
            if e.accessible:
                n_good += 1
                self.good_tree.insert("", "end", iid="g%d" % i, tags=("unlocked",) if e.unlocked_this_session else (),
                                      values=(e.name, e.rel or "(main folder)", e.ext.lower().lstrip(".") or "?",
                                              human_size(e.size),
                                              "Unlocked with password (in memory only)" if e.unlocked_this_session else ""))
            else:
                n_bad += 1
                if e.locked:
                    n_lock += 1
                iid = "b%d" % i
                self.bad_map[iid] = e
                self.bad_tree.insert("", "end", iid=iid, tags=("locked" if e.locked else "broken",),
                                     values=(e.name, e.rel or "(main folder)", ("🔒 " if e.locked else "") + e.reason))
        if n_lock > 0:
            self.ban.grid(row=1, column=0, sticky="ew", padx=14, pady=4)
        else:
            self.ban.grid_forget()

        self.count_lbl.configure(text="Accessible: %d     Not accessible: %d  (password-protected: %d)" % (n_good, n_bad, n_lock))
        if n_bad > 0:
            self.skip_lbl.configure(text="⚠ %d non-accessible file(s) will be SKIPPED if you proceed." % n_bad)
            self.next_btn.configure(text="Skip %d non-accessible file(s) & proceed to Step 2  ▶" % n_bad, width=420)
        else:
            self.skip_lbl.configure(text="")
            self.next_btn.configure(text="Proceed to Step 2  ▶", width=260)
        self.status_lbl.configure(text="Done. Checked %d file(s)." % len(entries), text_color=C["green"])
        self.next_btn.configure(state="normal" if n_good else "disabled")
        LOG.info("Check finished: %d accessible, %d not accessible (%d locked)." % (n_good, n_bad, n_lock))
        if not entries:
            messagebox.showinfo("No files", "No files were found in this folder.\n\nRemember: only %s are used."
                                % SUPPORTED_TEXT, parent=self.winfo_toplevel())

    # ---- passwords ----------------------------------------------------
    def select_locked(self):
        ids = [i for i, e in self.bad_map.items() if e.locked]
        self.bad_tree.selection_set(ids)
        if not ids:
            messagebox.showinfo("None", "There are no password-protected files in the list.", parent=self.winfo_toplevel())

    def enter_password(self):
        if self.app.busy:
            messagebox.showinfo("Please wait", "Another task is still running.", parent=self.winfo_toplevel())
            return
        sel = self.bad_tree.selection()
        if not sel:
            messagebox.showinfo("Select files first",
                                "Please click one or more password-protected files in the 'NOT accessible' list "
                                "(Ctrl+click or Shift+click for several), then press this button again.",
                                parent=self.winfo_toplevel())
            return
        ents = [self.bad_map[i] for i in sel if i in self.bad_map]
        locked = [e for e in ents if e.locked]
        if not locked:
            messagebox.showinfo("Not password-protected",
                                "None of the selected files is password-protected, so a password cannot help.\n"
                                "See the 'reason' column for what is wrong with them.", parent=self.winfo_toplevel())
            return
        pw = ask_password(self.winfo_toplevel(), [e.name for e in locked])
        if pw is None:
            return
        holder = [pw]
        pw = None
        paths = [e.path for e in locked]
        cache = self.app.cache

        def job(progress):
            p = holder[0]
            try:
                return apply_password_to_files(paths, p, cache)
            finally:
                holder[0] = None
                p = None

        self.app.busy = True
        self.scan_btn.configure(state="disabled")
        self.status_lbl.configure(text="Trying the password on %d file(s)..." % len(paths), text_color=C["muted"])
        self.app.runner.run(job, on_done=self._password_done, on_error=self._password_error)

    def _password_error(self, e):
        self.app.busy = False
        self.scan_btn.configure(state="normal")
        messagebox.showerror("Password step failed", "Could not apply the password:\n\n%s" % short_err(e, 300),
                             parent=self.winfo_toplevel())

    def _password_done(self, results: Dict[str, Tuple[bool, str]]):
        self.app.busy = False
        okc = sum(1 for v in results.values() if v[0])
        bad = [(os.path.basename(p), v[1]) for p, v in results.items() if not v[0]]
        LOG.info("Password attempt: %d file(s) unlocked, %d failed." % (okc, len(bad)))
        msg = "%d file(s) unlocked." % okc
        if bad:
            msg += "\n\n%d file(s) NOT unlocked:\n" % len(bad) + "\n".join("• %s - %s" % b for b in bad[:15])
            if len(bad) > 15:
                msg += "\n... and %d more" % (len(bad) - 15)
        messagebox.showinfo("Password result", msg, parent=self.winfo_toplevel())
        self.start_scan()

    # ---- next step ----------------------------------------------------
    def proceed(self):
        good = [e for e in self.entries if e.accessible]
        bad = [e for e in self.entries if not e.accessible]
        if not good:
            messagebox.showwarning("Nothing to process", "There are no accessible files to process.",
                                   parent=self.winfo_toplevel())
            return
        if bad:
            if not messagebox.askyesno(
                    "Skip non-accessible files?",
                    "%d file(s) are NOT accessible and will be SKIPPED (they will not be read or renamed).\n\n"
                    "Tip: password-protected files can still be unlocked first.\n\n"
                    "Skip them and continue with the %d accessible file(s)?" % (len(bad), len(good)),
                    parent=self.winfo_toplevel()):
                return
        LOG.info("Proceeding with %d accessible file(s); %d skipped as non-accessible." % (len(good), len(bad)))
        for e in bad:
            LOG.info("SKIPPED (not accessible): %s - %s" % (e.path, e.reason))
        self.app.good_entries = good
        self.app.skipped_entries = bad
        self.app.show_page(2)


# ==========================================================================
#  PAGE 2 - detect local LLM models
# ==========================================================================
class PageLLM(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=C["bg"])
        self.app = app
        self.models: List[ModelInfo] = []
        self.extra_urls: List[str] = []
        self.sel_var = tk.IntVar(value=-1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        c1, b1, h1 = make_card(self, "④  Find the AI model running on THIS computer", C["purple"])
        c1.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))
        b1.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(b1, justify="left", wraplength=1000, text_color=C["text"], anchor="w",
                     text="1) Start LM Studio (turn on its 'Local Server') or Ollama, and load a model.\n"
                          "2) Click 'Detect LLM models'. Pick one model from the list.\n"
                          "Scanned PDFs and photos need a VISION model (for example Gemma 3, Qwen2.5-VL, Llama 3.2 "
                          "Vision). Normal text PDFs also work with ordinary text models."
                     ).grid(row=0, column=0, columnspan=3, sticky="w", pady=4)
        row = ctk.CTkFrame(b1, fg_color="transparent")
        row.grid(row=1, column=0, columnspan=3, sticky="w", pady=4)
        self.detect_btn = big_button(row, "🔎 Detect LLM models", self.detect, C["magenta"], "#BF006A", width=220)
        self.detect_btn.pack(side="left", padx=(0, 8))
        help_button(row, "Detect models", "The tool looks ONLY on this computer (127.0.0.1) for LM Studio "
                    "(port 1234), Ollama (11434), llama.cpp (8080), Jan (1337) and GPT4All (4891) and lists the "
                    "models they offer. Nothing is sent to the internet.\n\nIf your list is empty: make sure the "
                    "server is switched ON inside LM Studio / Ollama and a model is downloaded.").pack(side="left", padx=4)
        self.status = ctk.CTkLabel(b1, text="Not detected yet.", text_color=C["muted"], anchor="w")
        self.status.grid(row=2, column=0, columnspan=3, sticky="ew")
        row2 = ctk.CTkFrame(b1, fg_color="transparent")
        row2.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(6, 2))
        ctk.CTkLabel(row2, text="Other local server address (optional):", text_color=C["text"]).pack(side="left", padx=(0, 6))
        self.url_entry = ctk.CTkEntry(row2, width=300, placeholder_text="http://127.0.0.1:5000")
        self.url_entry.pack(side="left", padx=4)
        big_button(row2, "Add", self.add_url, C["blue"], C["indigo2"], width=70, height=30).pack(side="left", padx=4)
        help_button(row2, "Custom address", "Only addresses on THIS computer (localhost or 127.0.0.1) are "
                    "accepted. Anything else is blocked for your safety - your bank documents never leave "
                    "this computer.").pack(side="left", padx=4)
        ctk.CTkLabel(b1, text="🔒 Security: connections are restricted to localhost / 127.0.0.1. Proxies and "
                     "redirects are disabled.", text_color=C["green"],
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold")).grid(row=4, column=0, sticky="w", pady=2)

        c2, b2, h2 = make_card(self, "Models found - choose ONE", C["teal"])
        c2.grid(row=1, column=0, sticky="nsew", padx=14, pady=6)
        b2.grid_columnconfigure(0, weight=1)
        b2.grid_rowconfigure(0, weight=1)
        self.list_frame = ctk.CTkScrollableFrame(b2, fg_color="#F7F8FF")
        self.list_frame.grid(row=0, column=0, sticky="nsew")
        self.chosen_lbl = ctk.CTkLabel(b2, text="No model chosen.", text_color=C["muted"], anchor="w",
                                       font=ctk.CTkFont(family=FONT, size=13, weight="bold"))
        self.chosen_lbl.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 12))
        bot.grid_columnconfigure(0, weight=1)
        big_button(bot, "◀ Back", lambda: self.app.show_page(1), C["muted"], "#444A80", width=110, height=44).grid(row=0, column=0, sticky="w")
        self.next_btn = big_button(bot, "Proceed to Process & Preview  ▶", self.proceed, C["green"], "#168A50",
                                   width=330, height=44, state="disabled")
        self.next_btn.grid(row=0, column=1, sticky="e")

    def on_show(self):
        pass

    def add_url(self):
        text = self.url_entry.get().strip()
        if not text:
            return
        try:
            clean = validate_loopback_url(text)
        except LoopbackViolation as e:
            LOG.warning("Blocked non-local server address: %s" % text)
            messagebox.showwarning("⛔ Security warning - address blocked", str(e), parent=self.winfo_toplevel())
            return
        if clean not in self.extra_urls:
            self.extra_urls.append(clean)
        self.url_entry.delete(0, "end")
        self.status.configure(text="Added %s. Click 'Detect LLM models' to include it." % clean, text_color=C["muted"])

    def detect(self):
        if self.app.busy:
            messagebox.showinfo("Please wait", "Another task is still running.", parent=self.winfo_toplevel())
            return
        self.app.busy = True
        self.detect_btn.configure(state="disabled")
        self.status.configure(text="Looking for local model servers...", text_color=C["muted"])
        urls = list(self.extra_urls)
        self.app.runner.run(lambda progress: detect_models(urls, progress), on_done=self._detected,
                            on_error=self._detect_error,
                            on_progress=lambda text: self.status.configure(text=text))

    def _detect_error(self, e):
        self.app.busy = False
        self.detect_btn.configure(state="normal")
        self.status.configure(text="Detection failed.", text_color=C["red"])
        messagebox.showerror("Detection failed", short_err(e, 300), parent=self.winfo_toplevel())

    def _detected(self, result):
        self.app.busy = False
        self.detect_btn.configure(state="normal")
        models, notes = result
        self.models = models
        self.sel_var.set(-1)
        self.app.selected_model = None
        self.next_btn.configure(state="disabled")
        self.chosen_lbl.configure(text="No model chosen.", text_color=C["muted"])
        for w in self.list_frame.winfo_children():
            w.destroy()
        for i, m in enumerate(models):
            ctk.CTkRadioButton(self.list_frame, text=m.label, variable=self.sel_var, value=i,
                               command=self._chosen, text_color=C["text"],
                               fg_color=C["magenta"], hover_color=C["purple"]).pack(anchor="w", padx=8, pady=5)
        if models:
            self.status.configure(text="Found %d model(s). Pick one below." % len(models), text_color=C["green"])
        else:
            self.status.configure(text="No models found. Start LM Studio's server or Ollama, load a model, then "
                                       "click Detect again.", text_color=C["red"])
        LOG.info("Model detection: %d model(s) found." % len(models))
        if notes:
            messagebox.showwarning("⛔ Security warning", "\n\n".join(notes), parent=self.winfo_toplevel())

    def _chosen(self):
        i = self.sel_var.get()
        if i < 0 or i >= len(self.models):
            return
        m = self.models[i]
        self.app.selected_model = m
        self.chosen_lbl.configure(text="Chosen: %s  (%s)" % (m.model_id, m.server), text_color=C["green"])
        self.next_btn.configure(state="normal")
        if m.vision is False:
            messagebox.showinfo("Text-only model",
                                "This model looks TEXT-ONLY. Normal PDFs with selectable text will work, but scanned "
                                "PDFs and photos will be marked 'Failed - Manual Review' unless you pick a vision model.",
                                parent=self.winfo_toplevel())

    def proceed(self):
        if self.app.selected_model is None:
            messagebox.showwarning("Choose a model", "Please choose one model from the list first.",
                                   parent=self.winfo_toplevel())
            return
        self.app.show_page(3)


# ==========================================================================
#  PAGE 3 - process, preview / edit, export, rename, undo
# ==========================================================================
class PageProcess(ctk.CTkFrame):
    COLS = ("ok", "file", "status", "date", "payee", "amount", "remarks", "txn", "payer", "mode",
            "proposed", "manual", "notes")
    HEAD = {"ok": "✔", "file": "Original file name", "status": "Status", "date": "Date",
            "payee": "Recipient / Payee", "amount": "Amount", "remarks": "Remarks / Narration",
            "txn": "Transaction ID", "payer": "Payer / Sender", "mode": "Mode",
            "proposed": "Proposed new name (double-click to edit)", "manual": "Name edited?",
            "notes": "Warnings / notes"}
    WID = {"ok": 40, "file": 230, "status": 220, "date": 100, "payee": 180, "amount": 90, "remarks": 190,
           "txn": 150, "payer": 160, "mode": 62, "proposed": 360, "manual": 90, "notes": 420}
    FIELD_OF_COL = {"date": "date", "payee": "payee", "amount": "amount", "remarks": "remarks",
                    "txn": "txn_id", "payer": "payer", "mode": "mode"}
    BASE_COLS = ["ok", "file", "status", "date", "payee", "amount", "remarks", "txn", "payer", "mode", "notes"]
    PREVIEW_COLS = ["ok", "file", "status", "date", "payee", "amount", "remarks", "txn", "payer", "mode",
                    "proposed", "manual", "notes"]
    STATUS_TAG = {S_VERIFIED: "ok", S_UNVERIFIED: "warn", S_MISMATCH: "orange", S_INCOMPLETE: "orange",
                  S_AMBIG: "bad", S_FAILED: "bad", S_NOTRECEIPT: "bad", S_EDITED: "edited"}

    def __init__(self, master, app):
        super().__init__(master, fg_color=C["bg"])
        self.app = app
        self.rows: List[Row] = []
        self.preview_active = False
        self.viewer: Optional[DocViewer] = None
        self.viewer_shown = False
        self._edit = None
        self.cancel_event = threading.Event()
        self.backup_dir = ""
        self._backup_session_dir: Optional[str] = None
        self.display_cols = list(self.BASE_COLS)
        self.label_to_code = {lab: code for lab, code in PART_CHOICES}
        self.active_filter = "all"
        self.filter_btns: Dict[str, Tuple[ctk.CTkButton, str]] = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ---- top control bar
        top = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=12, border_width=1, border_color="#D5DAFF")
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        top.grid_columnconfigure(3, weight=1)
        self.start_btn = big_button(top, "▶ Start reading the files", self.start, C["magenta"], "#BF006A", width=220, height=34)
        self.start_btn.grid(row=0, column=0, padx=10, pady=(6, 2))
        self.cancel_btn = big_button(top, "■ Stop", self.cancel, C["red"], "#C0272A", width=85, height=34, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=4, pady=(6, 2))
        help_button(top, "Reading files", "The tool now shows each accessible file to your LOCAL AI model, one by one, "
                    "and fills the table below. Nothing leaves this computer.\n\nThe AI is never trusted blindly: "
                    "for normal PDFs every value is cross-checked against the PDF's own text. Anything doubtful, "
                    "missing or conflicting is marked for manual review and will NOT be renamed until you fix or "
                    "approve it.").grid(row=0, column=2, padx=4, pady=(6, 2))
        self.info_lbl = ctk.CTkLabel(top, text="", text_color=C["text"], anchor="w",
                                     font=ctk.CTkFont(family=FONT, size=12, weight="bold"))
        self.info_lbl.grid(row=0, column=3, sticky="ew", padx=10, pady=(6, 2))
        self.prog = ctk.CTkProgressBar(top, progress_color=C["teal"], height=8)
        self.prog.set(0)
        self.prog.grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=2)
        self.status_lbl = ctk.CTkLabel(top, text="Ready.", text_color=C["muted"], anchor="w")
        self.status_lbl.grid(row=2, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 4))

        # ---- vertical pane: table area / tabs
        self.vpane = tk.PanedWindow(self, orient="vertical", sashwidth=8, bg=C["bg"], bd=0, sashrelief="flat")
        self.vpane.grid(row=1, column=0, sticky="nsew", padx=14, pady=2)
        upper = ctk.CTkFrame(self.vpane, fg_color=C["bg"])
        upper.grid_columnconfigure(0, weight=1)
        upper.grid_rowconfigure(1, weight=1)
        self.vpane.add(upper, stretch="always", minsize=180)

        tb = ctk.CTkFrame(upper, fg_color="transparent")
        tb.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        big_button(tb, "✅ Approve all verified", self.approve_all_verified, C["green"], "#168A50", width=175, height=30).pack(side="left", padx=(0, 4))
        big_button(tb, "✔ Approve selected", self.approve_selected, C["blue"], C["indigo2"], width=150, height=30).pack(side="left", padx=3)
        big_button(tb, "✖ Un-approve selected", self.unapprove_selected, C["muted"], "#444A80", width=160, height=30).pack(side="left", padx=3)
        help_button(tb, "Approving & Filtering", "Only APPROVED rows (☑) are ever renamed.\n\n• 'Approve all verified' approves rows "
                    "whose details were confirmed against the PDF text (or that you corrected yourself).\n"
                    "• Scanned/image files and doubtful rows must be checked by you: click the row to see the "
                    "original on the right, then use 'Approve selected'.\n• Rows marked Ambiguous / Failed cannot "
                    "be approved until you pick or type the correct values.\n• Click any status button on the right "
                    "to filter the table.\n\nTo change any value: double-click "
                    "the cell and type. Click a row to see the original file beside the table.").pack(side="left", padx=4)

        # Interactive filter buttons on top right
        flt_bar = ctk.CTkFrame(tb, fg_color="transparent")
        flt_bar.pack(side="right", padx=2)
        filters = [
            ("all", "All", C["indigo2"]),
            ("ok", "🟩 Verified", C["green"]),
            ("warn", "🟨 Check visually", "#C89600"),
            ("orange", "🟧 Review", C["orange"]),
            ("bad", "🟥 Ambiguous / Failed", C["red"]),
            ("edited", "🟦 Edited by you", C["blue"]),
        ]
        for fkey, flab, fcol in filters:
            b = ctk.CTkButton(
                flt_bar, text=flab, height=28, width=10, corner_radius=8,
                fg_color=fcol if fkey == "all" else "#DCE1FF",
                hover_color=fcol,
                text_color="white" if fkey == "all" else C["text"],
                font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
                command=lambda k=fkey: self.set_filter(k)
            )
            b.pack(side="left", padx=2)
            self.filter_btns[fkey] = (b, fcol)

        self.hpane = tk.PanedWindow(upper, orient="horizontal", sashwidth=8, bg=C["bg"], bd=0, sashrelief="flat")
        self.hpane.grid(row=1, column=0, sticky="nsew")
        left = ctk.CTkFrame(self.hpane, fg_color="transparent")
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        self.hpane.add(left, stretch="always", minsize=400)
        f, self.tree = make_tree(left, self.COLS, self.HEAD, self.WID, height=6)
        f.grid(row=0, column=0, sticky="nsew")
        self.tree["displaycolumns"] = tuple(self.display_cols)
        for tag, color in (("ok", "#E3F8EC"), ("warn", "#FFF6D6"), ("orange", "#FFE6CC"),
                           ("bad", "#FFD9DC"), ("edited", "#DDE7FF")):
            self.tree.tag_configure(tag, background=color)
        self.tree.bind("<Button-1>", self._on_click, add="+")
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Control-a>", self._select_all)
        self.tree.bind("<Control-A>", self._select_all)

        # ---- tabs: export / rename / log  (sized so everything fits without scrolling)
        self.tabs = ctk.CTkTabview(self.vpane, height=340, fg_color=C["card"],
                                   segmented_button_selected_color=C["magenta"],
                                   segmented_button_selected_hover_color="#BF006A")
        self.vpane.add(self.tabs, stretch="never", minsize=310)
        t_exp = self.tabs.add("📤 Export data")
        t_ren = self.tabs.add("✏️ Rename files")
        t_log = self.tabs.add("📜 Processing log")
        self._build_export(t_exp)
        self._build_rename(t_ren)
        self._build_log(t_log)
        self.after(300, self._place_vsash)

    def _place_vsash(self):
        try:
            h = self.vpane.winfo_height()
            if h > 250:
                self.vpane.sash_place(0, 0, max(190, h - 340))
        except Exception:
            pass

    def set_filter(self, fkey: str):
        self._end_edit(True)
        self.active_filter = fkey
        for k, (btn, col) in self.filter_btns.items():
            if k == fkey:
                btn.configure(fg_color=col, text_color="white")
            else:
                btn.configure(fg_color="#DCE1FF", text_color=C["text"])
        self._rebuild_tree()

    def _row_matches_filter(self, r: Row) -> bool:
        if self.active_filter == "all":
            return True
        tag = self.STATUS_TAG.get(r.status, "")
        return tag == self.active_filter

    def _rebuild_tree(self):
        sel = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children())
        for idx, r in enumerate(self.rows):
            if self._row_matches_filter(r):
                iid = str(idx)
                self.tree.insert("", "end", iid=iid, values=self._values(r), tags=self._tags(r))
                if iid in sel:
                    self.tree.selection_add(iid)

    # ------------------------------------------------------------------
    # tabs
    # ------------------------------------------------------------------
    def _build_export(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Save the table (as shown above, including your corrections) to a file you choose:",
                     text_color=C["text"], anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=(8, 4))
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.grid(row=1, column=0, sticky="w", padx=6, pady=6)
        ctk.CTkLabel(row, text="Rows to export:", text_color=C["text"]).pack(side="left", padx=(0, 6))
        self.scope_var = tk.StringVar(value="All rows")
        ctk.CTkOptionMenu(row, values=["All rows", "Approved rows only"], variable=self.scope_var, width=190,
                          fg_color=C["blue"], button_color=C["indigo2"]).pack(side="left", padx=4)
        help_button(row, "Export", "Excel and PDF contain exactly what you see in the table: original file name, "
                    "status, date, recipient, amount, remarks, transaction ID and warnings. If you have used "
                    "'Preview before renaming', the proposed names are included too. You choose where to save.").pack(side="left", padx=8)
        row2 = ctk.CTkFrame(tab, fg_color="transparent")
        row2.grid(row=2, column=0, sticky="w", padx=6, pady=8)
        big_button(row2, "📊 Save as Excel (.xlsx)...", lambda: self.export("xlsx"), C["green"], "#168A50", width=240).pack(side="left", padx=(0, 10))
        big_button(row2, "📄 Save as PDF...", lambda: self.export("pdf"), C["red"], "#C0272A", width=200).pack(side="left", padx=10)

    def _build_rename(self, tab):
        body = ctk.CTkFrame(tab, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=6, pady=2)
        body.grid_columnconfigure(0, weight=1)
        r0 = ctk.CTkFrame(body, fg_color="transparent")
        r0.grid(row=0, column=0, sticky="w", pady=(0, 2))
        ctk.CTkLabel(r0, text="File-name format (new name = Part 1 - Part 2 - Part 3 - Part 4):",
                     text_color=C["text"], font=ctk.CTkFont(family=FONT, size=12, weight="bold")).pack(side="left", padx=(0, 6))
        help_button(r0, "Name format", "Choose what each part of the new file name should be. Parts are joined "
                    "with ' - ' (space hyphen space). You MUST choose at least one part; leave the others "
                    "'(leave blank)' if you wish.\n\nExample: yymmdd | Payee | Amount | Remarks gives\n"
                    "240105 - Ramesh Kumar - Rs.1000 - Rent.pdf\n\nWhole-rupee amounts show as Rs.1000 (never "
                    ".00); decimals appear only if the document has them (Rs.1000.25). The file extension (.pdf, "
                    ".jpg ...) is always kept. If a chosen detail is missing for a file, that file is NOT renamed "
                    "- it is marked for manual review.").pack(side="left", padx=(0, 14))
        self.example_lbl = ctk.CTkLabel(r0, text="", text_color=C["green"], anchor="w",
                                        font=ctk.CTkFont(family=FONT, size=12, weight="bold"))
        self.example_lbl.pack(side="left", padx=8)

        r1 = ctk.CTkFrame(body, fg_color="transparent")
        r1.grid(row=1, column=0, sticky="w", pady=2)
        self.part_vars = []
        defaults = ["yymmdd", "Payee / Recipient name", "Amount (Rs.xx)", "Remarks / Narration"]
        for i in range(4):
            v = tk.StringVar(value=defaults[i])
            self.part_vars.append(v)
            col = ctk.CTkFrame(r1, fg_color="transparent")
            col.pack(side="left", padx=(0, 4))
            ctk.CTkLabel(col, text="Part %d" % (i + 1), text_color=C["muted"],
                         font=ctk.CTkFont(family=FONT, size=11, weight="bold")).pack(anchor="w")
            ctk.CTkOptionMenu(col, values=[lab for lab, _ in PART_CHOICES], variable=v, width=210, height=28,
                              fg_color=[C["blue"], C["purple"], C["teal"], C["orange"]][i],
                              button_color=C["indigo2"], command=lambda _val: self._on_format_change()).pack()
            if i < 3:
                ctk.CTkLabel(r1, text=" - ", text_color=C["text"],
                             font=ctk.CTkFont(family=FONT, size=16, weight="bold")).pack(side="left", pady=(14, 0))
        self._last_labels = [v.get() for v in self.part_vars]

        r3 = ctk.CTkFrame(body, fg_color="transparent")
        r3.grid(row=2, column=0, sticky="w", pady=3)
        self.backup_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(r3, text="Take a backup copy before renaming", variable=self.backup_var,
                        command=self._on_backup_toggle, text_color=C["text"], height=22).pack(side="left", padx=(0, 4))
        help_button(r3, "Backup", "If ticked, a copy of every file that is about to be renamed is saved in a folder "
                    "you choose (it must be OUTSIDE the folder being renamed). Each copy is verified. If even ONE "
                    "backup fails (disk full, permission...), NOTHING is renamed and you can retry or cancel.").pack(side="left", padx=2)
        self.backup_lbl = ctk.CTkLabel(r3, text="(no backup folder)", text_color=C["muted"])
        self.backup_lbl.pack(side="left", padx=6)
        ctk.CTkButton(r3, text="Choose backup folder...", width=160, height=26, fg_color=C["teal"],
                      hover_color="#008A80", command=self._choose_backup).pack(side="left", padx=(2, 18))

        self.log_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(r3, text="Save a detailed rename log (CSV)", variable=self.log_var,
                        text_color=C["text"], height=22).pack(side="left", padx=(0, 4))
        help_button(r3, "Rename log", "A spreadsheet-readable log saved next to your files: original name, name proposed "
                    "by the tool, whether you edited the name, final name, result, backup location and a file "
                    "fingerprint. Untick to skip saving it. (The technical file rename_session.json is always "
                    "kept - it is what makes Undo and crash-recovery possible.)").pack(side="left", padx=2)

        r5 = ctk.CTkFrame(body, fg_color="transparent")
        r5.grid(row=3, column=0, sticky="w", pady=(4, 2))
        self.preview_btn = big_button(r5, "👁 Preview before renaming", self.preview, C["blue"], C["indigo2"],
                                      width=220, height=34, state="disabled")
        self.preview_btn.pack(side="left", padx=(0, 6))
        help_button(r5, "Preview", "Adds a 'Proposed new name' column to the table so you can see - and edit - every "
                    "new name before anything is touched. Duplicate names get _1, _2... and unusable characters "
                    "( * ? : etc.) are replaced by '+'. Both are shown in the notes column.").pack(side="left", padx=4)
        self.rename_btn = big_button(r5, "✅ RENAME NOW", self.do_rename, C["green"], "#168A50", width=180, height=34, state="disabled")
        self.rename_btn.pack(side="left", padx=(14, 6))
        self.undo_btn = big_button(r5, "↩ Undo last batch", self.undo, C["red"], "#C0272A", width=170, height=34, state="disabled")
        self.undo_btn.pack(side="left", padx=(14, 6))
        help_button(r5, "Undo", "Puts the files of the most recent rename batch back to their original names. "
                    "Before touching a file the tool checks that it still exists under the new name, that the "
                    "old name is free and that the file content is unchanged (SHA-256 fingerprint). Files that "
                    "fail the check are left alone and listed.").pack(side="left", padx=4)
        ctk.CTkLabel(body, text="⚠ Undo verifies both file existence and SHA-256 hash before restoring names, skipping any modified or manually renamed file.",
                     text_color=C["red"], justify="left", wraplength=980, anchor="w",
                     font=ctk.CTkFont(family=FONT, size=11, weight="bold")
                     ).grid(row=4, column=0, sticky="w", pady=(2, 2))
        self._update_example()

    def _build_log(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        self.log_box = ctk.CTkTextbox(tab, fg_color="#F7F8FF", text_color=C["text"], wrap="word",
                                      font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.log_box.configure(state="disabled")
        ctk.CTkLabel(tab, text="Errors and events are also saved in 'bankdoc_processing_log.txt' inside the chosen folder.",
                     text_color=C["muted"], anchor="w").grid(row=1, column=0, sticky="w", padx=6)

    def drain_log(self):
        lines = []
        while True:
            try:
                lines.append(LOG.ui_queue.get_nowait())
            except queue.Empty:
                break
        if lines:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", "\n".join(lines) + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

    # ------------------------------------------------------------------
    # page lifecycle
    # ------------------------------------------------------------------
    def on_show(self):
        a = self.app
        m = a.selected_model.model_id if a.selected_model else "-"
        self.info_lbl.configure(text="%d file(s) to read   |   model: %s   |   folder: %s"
                                % (len(a.good_entries), m, a.root_folder))
        self.refresh_undo_state()
        self.update_rename_buttons()
        self.after(100, self._place_vsash)

    def reset(self):
        """Forget the table (used when the user switches to another folder)."""
        self._end_edit(False)
        self.rows = []
        self.tree.delete(*self.tree.get_children())
        self.preview_active = False
        self._set_display(False)
        self._close_viewer()
        self._backup_session_dir = None
        self.prog.set(0)
        self.status_lbl.configure(text="Ready.", text_color=C["muted"])
        self.update_rename_buttons()

    def _codes(self) -> List[str]:
        return [self.label_to_code.get(v.get(), "") for v in self.part_vars]

    # ------------------------------------------------------------------
    # processing
    # ------------------------------------------------------------------
    def start(self):
        a = self.app
        if a.busy:
            messagebox.showinfo("Please wait", "Another task is still running.", parent=self.winfo_toplevel())
            return
        if not a.good_entries or a.selected_model is None:
            messagebox.showwarning("Not ready", "Please finish Step 1 (files) and Step 2 (model) first.",
                                   parent=self.winfo_toplevel())
            return
        if self.rows and not messagebox.askyesno(
                "Read again?", "This will discard the current table and any manual changes you made.\n\nContinue?",
                parent=self.winfo_toplevel()):
            return
        LOG.set_folder(a.root_folder)
        LOG.info("Processing started: %d file(s) with model %s (%s)" % (len(a.good_entries), a.selected_model.model_id,
                                                                       a.selected_model.base_url))
        self.rows = []
        self.tree.delete(*self.tree.get_children())
        self.preview_active = False
        self._set_display(False)
        self._close_viewer()
        self.cancel_event = threading.Event()
        cancel_event = self.cancel_event
        model = a.selected_model
        entries = list(a.good_entries)
        cache = a.cache
        a.busy = True
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.prog.set(0)

        def job(progress):
            http_json("GET", model.base_url, "/api/tags" if model.kind == "ollama" else "/v1/models", timeout=6)
            return process_files(entries, model, cache, cancel_event, progress)

        a.runner.run(job, on_done=self._proc_done, on_error=self._proc_error, on_progress=self._proc_progress)
        self.update_rename_buttons()

    def cancel(self):
        self.cancel_event.set()
        self.status_lbl.configure(text="Stopping after the current file...", text_color=C["orange"])

    def _proc_progress(self, kind, i, total, name, row):
        if kind == "start":
            self.prog.set((i - 1) / max(total, 1))
            self.status_lbl.configure(text="Reading file %d of %d:  %s   (local AI is working - please wait)" % (i, total, name),
                                      text_color=C["muted"])
        else:
            self._add_row(row)
            self.prog.set(i / max(total, 1))

    def _proc_error(self, e):
        self.app.busy = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.status_lbl.configure(text="Stopped because of a problem.", text_color=C["red"])
        extra = ""
        if isinstance(e, (LLMError, LoopbackViolation)):
            extra = "\n\nIs the model server (LM Studio / Ollama) still running with the model loaded?"
        messagebox.showerror("Could not read the files", "%s%s" % (short_err(e, 400), extra), parent=self.winfo_toplevel())
        self.update_rename_buttons()

    def _proc_done(self, done_count):
        self.app.busy = False
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        total = len(self.app.good_entries)
        n_ok = sum(1 for r in self.rows if r.status == S_VERIFIED)
        n_chk = sum(1 for r in self.rows if r.status == S_UNVERIFIED)
        n_bad = len(self.rows) - n_ok - n_chk
        self.status_lbl.configure(text="Finished %d of %d file(s):  %d verified, %d to check visually, %d need manual review."
                                  % (done_count, total, n_ok, n_chk, n_bad), text_color=C["green"])
        LOG.info("Processing finished: %d of %d file(s). Verified %d, check visually %d, manual review %d."
                 % (done_count, total, n_ok, n_chk, n_bad))
        self.prog.set(1 if done_count >= total else done_count / max(total, 1))
        self.update_rename_buttons()
        messagebox.showinfo(
            "Reading finished",
            "Finished %d of %d file(s).\n\n• %d verified against the PDF text\n• %d scanned/image files - please check them "
            "against the original\n• %d need manual review (missing, conflicting or doubtful details)\n\n"
            "Click any row to see the original file next to the table. Double-click a cell to correct it."
            % (done_count, total, n_ok, n_chk, n_bad), parent=self.winfo_toplevel())

    # ------------------------------------------------------------------
    # table helpers
    # ------------------------------------------------------------------
    def _values(self, r: Row):
        amt = ("Rs." + r.fields["amount"]) if r.fields["amount"] else ""
        return ("☑" if r.approved else "☐", r.name, r.status, fmt_date_display(r.fields["date"]),
                r.fields["payee"], amt, r.fields["remarks"], r.fields["txn_id"], r.fields["payer"],
                r.fields["mode"], r.final_name if self.preview_active else "",
                ("YES" if r.proposed_override is not None else "") if self.preview_active else "",
                r.notes_text())

    def _tags(self, r: Row):
        return (self.STATUS_TAG.get(r.status, ""),)

    def _add_row(self, r: Row):
        idx = len(self.rows)
        self.rows.append(r)
        if self._row_matches_filter(r):
            self.tree.insert("", "end", iid=str(idx), values=self._values(r), tags=self._tags(r))

    def _refresh_row(self, idx: int):
        r = self.rows[idx]
        iid = str(idx)
        if self._row_matches_filter(r):
            if self.tree.exists(iid):
                self.tree.item(iid, values=self._values(r), tags=self._tags(r))
            else:
                self._rebuild_tree()
        else:
            if self.tree.exists(iid):
                self.tree.delete(iid)

    def _refresh_all(self):
        self._rebuild_tree()

    def _index_of(self, r: Row) -> int:
        for i, x in enumerate(self.rows):
            if x is r:
                return i
        return -1

    def _set_display(self, preview: bool):
        self.display_cols = list(self.PREVIEW_COLS if preview else self.BASE_COLS)
        self.tree["displaycolumns"] = tuple(self.display_cols)

    def _recompute_names(self):
        compute_names(self.rows, self._codes())

    def _select_all(self, event=None):
        self.tree.selection_set(self.tree.get_children())
        return "break"

    # ------------------------------------------------------------------
    # viewer (split screen)
    # ------------------------------------------------------------------
    def _on_select(self, event=None):
        sel = self.tree.selection()
        if len(sel) != 1:
            return
        try:
            r = self.rows[int(sel[0])]
        except (ValueError, IndexError):
            return
        self._open_viewer(r)

    def _open_viewer(self, r: Row):
        if self.viewer is None:
            self.viewer = DocViewer(self.hpane, self.app, self._close_viewer, self._pick_candidate)
        first = not self.viewer_shown
        if first:
            self.hpane.add(self.viewer, minsize=340, stretch="always")
            self.viewer_shown = True
            self.update_idletasks()
            self._place_hsash()
            self.update_idletasks()
        self.viewer.load(r)

    def _place_hsash(self):
        try:
            w = self.hpane.winfo_width()
            if w > 600:
                self.hpane.sash_place(0, int(w * 0.52), 0)
        except Exception:
            pass

    def _close_viewer(self):
        if self.viewer is not None and self.viewer_shown:
            try:
                self.hpane.forget(self.viewer)
            except Exception:
                pass
            self.viewer_shown = False

    def _pick_candidate(self, r: Row, key: str, value: str):
        idx = self._index_of(r)
        if idx < 0:
            return
        r.set_field(key, value)
        LOG.info("Manual choice: %s -> %s for %s" % (FIELD_LABELS[key], value, r.name))
        self._after_edit(idx)

    # ------------------------------------------------------------------
    # click / edit handling
    # ------------------------------------------------------------------
    def _on_click(self, event):
        self._end_edit(True)
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        iid = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if iid and col == "#1":
            self._toggle_approve(int(iid))

    def _on_double(self, event):
        if self.tree.identify("region", event.x, event.y) != "cell":
            return "break"
        iid = self.tree.identify_row(event.y)
        cidx = int(self.tree.identify_column(event.x).lstrip("#")) - 1
        if not iid or cidx < 0 or cidx >= len(self.display_cols):
            return "break"
        col = self.display_cols[cidx]
        if col in self.FIELD_OF_COL or col == "proposed":
            self._begin_edit(iid, col)
        return "break"

    def _edit_text(self, r: Row, col: str) -> str:
        if col == "proposed":
            return r.final_name[: -len(r.ext)] if (r.ext and r.final_name.lower().endswith(r.ext.lower())) else r.final_name
        key = self.FIELD_OF_COL[col]
        if key == "date":
            return fmt_date_display(r.fields["date"])
        return r.fields[key]

    def _begin_edit(self, iid: str, col: str):
        self._end_edit(True)
        r = self.rows[int(iid)]
        bbox = self.tree.bbox(iid, "#%d" % (self.display_cols.index(col) + 1))
        if not bbox:
            return
        x, y, w, h = bbox
        ent = tk.Entry(self.tree, font=(FONT, 10), relief="solid", bd=1, bg="#FFFBE6")
        ent.insert(0, self._edit_text(r, col))
        ent.select_range(0, "end")
        ent.place(x=x, y=y, width=max(w, 80), height=h)
        ent.focus_set()
        ent.bind("<Return>", lambda e: self._end_edit(True))
        ent.bind("<Escape>", lambda e: self._end_edit(False))
        ent.bind("<FocusOut>", lambda e: self._end_edit(True))
        self._edit = (ent, iid, col)

    def _end_edit(self, commit: bool):
        if not self._edit:
            return
        ent, iid, col = self._edit
        self._edit = None
        value = ent.get()
        try:
            ent.destroy()
        except Exception:
            pass
        if commit:
            self._commit(iid, col, value)

    def _commit(self, iid: str, col: str, text: str):
        idx = int(iid)
        r = self.rows[idx]
        if col == "proposed":
            t = collapse_ws(text)
            cur = self._edit_text(r, col)
            if t == cur:
                return
            r.proposed_override = t if t else None
            LOG.info("Manual proposed name for %s: '%s'" % (r.name, t))
            self._after_edit(idx)
            return
        key = self.FIELD_OF_COL[col]
        ok, val, err = normalize_field_input(key, text)
        if not ok:
            messagebox.showerror("Not accepted", err, parent=self.winfo_toplevel())
            return
        if val == r.fields[key]:
            return
        old = r.fields[key]
        reset = r.set_field(key, val)
        LOG.info("Manual edit: %s of %s changed from '%s' to '%s'" % (FIELD_LABELS[key], r.name, old, val))
        if reset:
            self.status_lbl.configure(text="Note: the hand-typed proposed name of this file was reset because its details changed.",
                                      text_color=C["orange"])
        self._after_edit(idx)

    def _after_edit(self, idx: int):
        if self.preview_active:
            self._recompute_names()
            self._refresh_all()
        else:
            self._refresh_row(idx)
        if self.viewer is not None and self.viewer_shown and self.viewer.row is self.rows[idx]:
            self.viewer.refresh_header()
        self.update_rename_buttons()

    # ------------------------------------------------------------------
    # approval
    # ------------------------------------------------------------------
    @staticmethod
    def _approval_block_text(r: Row) -> str:
        if r.status == S_AMBIG:
            return ("%s\n\nThis file has conflicting details. Click the row, look at the original on the right, then "
                    "pick the correct value with the orange buttons or type it in the table." % "; ".join(r.amb_msgs))
        if r.status == S_FAILED:
            return "This file could not be read automatically (%s).\n\nType the details by hand in the table to continue." % r.error
        if r.status == S_NOTRECEIPT:
            return ("The AI thinks this is not a bank transfer receipt.\n\nIf it is, type the date, amount and "
                    "recipient by hand in the table to continue.")
        return ""

    def _toggle_approve(self, idx: int):
        r = self.rows[idx]
        if r.approved:
            r.approved = False
        else:
            block = self._approval_block_text(r)
            if block:
                messagebox.showwarning("Cannot approve yet", block, parent=self.winfo_toplevel())
                return
            if r.status == S_MISMATCH and not messagebox.askyesno(
                    "Values not confirmed",
                    "Some values of this file could not be confirmed in the document:\n\n%s\n\nHave you compared them with "
                    "the original and are they correct?" % r.notes_text(), parent=self.winfo_toplevel()):
                return
            r.approved = True
        self._refresh_row(idx)
        self.update_rename_buttons()

    def approve_all_verified(self):
        n = 0
        for i, r in enumerate(self.rows):
            if r.status in (S_VERIFIED, S_EDITED) and not r.approved and all(r.fields[f] for f in CORE_FIELDS):
                r.approved = True
                n += 1
        self._refresh_all()
        self.update_rename_buttons()
        messagebox.showinfo("Approved", "%d row(s) approved.\n\nRows marked 'check visually' or 'review' still need your "
                            "own check (click the row, compare, then use 'Approve selected')." % n,
                            parent=self.winfo_toplevel())

    def approve_selected(self):
        sel = [int(i) for i in self.tree.selection()]
        if not sel:
            messagebox.showinfo("Select rows", "Please select one or more rows first.", parent=self.winfo_toplevel())
            return
        blocked, mism, todo = [], [], []
        for i in sel:
            r = self.rows[i]
            if r.approved:
                continue
            if self._approval_block_text(r):
                blocked.append(r)
            elif r.status == S_MISMATCH:
                mism.append(i)
            else:
                todo.append(i)
        if mism and messagebox.askyesno(
                "Values not confirmed",
                "%d selected row(s) have values that could not be confirmed in the document.\n\nHave you compared them with "
                "the originals and are they correct?" % len(mism), parent=self.winfo_toplevel()):
            todo.extend(mism)
        for i in todo:
            self.rows[i].approved = True
        self._refresh_all()
        self.update_rename_buttons()
        if blocked:
            messagebox.showwarning("Some rows were not approved",
                                   "%d row(s) were NOT approved because they are ambiguous / failed. Fix them first:\n\n%s"
                                   % (len(blocked), "\n".join("• " + b.name for b in blocked[:12])),
                                   parent=self.winfo_toplevel())

    def unapprove_selected(self):
        for i in self.tree.selection():
            self.rows[int(i)].approved = False
        self._refresh_all()
        self.update_rename_buttons()

    # ------------------------------------------------------------------
    # export
    # ------------------------------------------------------------------
    def export(self, kind: str):
        if self.app.busy:
            messagebox.showinfo("Please wait", "Another task is still running.", parent=self.winfo_toplevel())
            return
        if not self.rows:
            messagebox.showinfo("Nothing to export", "The table is empty. Read the files first.", parent=self.winfo_toplevel())
            return
        rows = [r for r in self.rows if self.scope_var.get() == "All rows" or r.approved]
        if not rows:
            messagebox.showinfo("Nothing to export", "No rows are approved yet.", parent=self.winfo_toplevel())
            return
        ext = ".xlsx" if kind == "xlsx" else ".pdf"
        types = [("Excel workbook", "*.xlsx")] if kind == "xlsx" else [("PDF document", "*.pdf")]
        path = filedialog.asksaveasfilename(parent=self.winfo_toplevel(), title="Where do you want to save it?",
                                            defaultextension=ext, filetypes=types,
                                            initialfile="BankDoc_extract_%s%s" % (stamp(), ext),
                                            initialdir=self.app.root_folder or None)
        if not path:
            return
        import copy
        snapshot = copy.deepcopy(rows)
        root = self.app.root_folder
        codes = self._codes()
        show_prop = self.preview_active

        def job(progress):
            if kind == "xlsx":
                export_excel(snapshot, path, root, codes, show_prop)
            else:
                export_pdf(snapshot, path, root, show_prop)
            return path

        def done(p):
            self.app.busy = False
            LOG.info("Exported %d row(s) to %s" % (len(snapshot), p))
            messagebox.showinfo("Saved", "Saved:\n%s" % p, parent=self.winfo_toplevel())

        def err(e):
            self.app.busy = False
            LOG.error("Export failed: %s" % short_err(e))
            messagebox.showerror("Could not save", "The file could not be saved:\n\n%s\n\nIf it is open in Excel/PDF "
                                 "viewer, close it and try again." % short_err(e, 300), parent=self.winfo_toplevel())

        self.app.busy = True
        self.status_lbl.configure(text="Saving...", text_color=C["muted"])
        self.app.runner.run(job, on_done=done, on_error=err)

    # ------------------------------------------------------------------
    # rename UI
    # ------------------------------------------------------------------
    def _update_example(self):
        sample = {"date": "2024-01-05", "payee": "Ramesh Kumar", "amount": "1000", "remarks": "Rent",
                  "txn_id": "UTR123456", "payer": "Sita Devi", "mode": "NEFT"}
        stem, _m, _r = stem_from_fields(sample, self._codes())
        if stem:
            self.example_lbl.configure(text="Example:  %s.pdf" % stem, text_color=C["green"])
        else:
            self.example_lbl.configure(text="Please choose at least ONE part.", text_color=C["red"])

    def _on_format_change(self):
        if self.preview_active and any(r.proposed_override is not None for r in self.rows):
            if not messagebox.askyesno("Change the format?",
                                       "Some proposed names were edited by hand. Changing the format will reset "
                                       "those hand-typed names.\n\nContinue?", parent=self.winfo_toplevel()):
                for v, lab in zip(self.part_vars, self._last_labels):
                    v.set(lab)
                return
            for r in self.rows:
                r.proposed_override = None
        self._last_labels = [v.get() for v in self.part_vars]
        self._update_example()
        if self.preview_active:
            self._recompute_names()
            self._refresh_all()
        self.update_rename_buttons()

    def _on_backup_toggle(self):
        if self.backup_var.get():
            if not self.backup_dir:
                self._choose_backup()
            if not self.backup_dir:
                self.backup_var.set(False)
        self.update_rename_buttons()

    def _choose_backup(self):
        d = filedialog.askdirectory(title="Choose the folder where backup copies should be saved", mustexist=True,
                                    parent=self.winfo_toplevel())
        if not d:
            return
        d = os.path.normpath(d)
        if self.app.root_folder and is_inside(d, self.app.root_folder):
            messagebox.showerror("Choose another folder",
                                 "The backup folder must be OUTSIDE the folder whose files are being renamed.",
                                 parent=self.winfo_toplevel())
            return
        self.backup_dir = d
        self._backup_session_dir = None
        self.backup_lbl.configure(text=d, text_color=C["green"])
        self.update_rename_buttons()

    def update_rename_buttons(self):
        a = self.app
        any_part = any(self._codes())
        backup_ok = (not self.backup_var.get()) or bool(self.backup_dir)
        can_prev = bool(self.rows) and any_part and backup_ok and not a.busy
        self.preview_btn.configure(state="normal" if can_prev else "disabled")
        ready = self.preview_active and any(not block_reason(r) for r in self.rows) and not a.busy
        self.rename_btn.configure(state="normal" if ready else "disabled")

    def preview(self):
        if not self.rows:
            messagebox.showinfo("Nothing to rename", "Read the files first.", parent=self.winfo_toplevel())
            return
        if not any(self._codes()):
            messagebox.showwarning("Choose a format", "Please choose at least ONE part for the new file name.",
                                   parent=self.winfo_toplevel())
            return
        if self.backup_var.get() and not self.backup_dir:
            messagebox.showwarning("Backup folder", "You ticked 'backup' - please choose the backup folder first.",
                                   parent=self.winfo_toplevel())
            return
        self.preview_active = True
        self._set_display(True)
        self._recompute_names()
        self._refresh_all()
        n_ready = sum(1 for r in self.rows if not block_reason(r))
        n_appr = sum(1 for r in self.rows if r.approved)
        n_dup = sum(1 for r in self.rows if any("Duplicate" in f for f in r.name_flags))
        n_chr = sum(1 for r in self.rows if any("Unusable" in f for f in r.name_flags))
        self.status_lbl.configure(
            text="Preview ready. %d approved row(s), %d ready to rename. Duplicates fixed: %d. Names with unusable characters fixed: %d. "
                 "Double-click a 'Proposed new name' cell to edit it." % (n_appr, n_ready, n_dup, n_chr),
            text_color=C["green"])
        self.update_rename_buttons()

    def _plan_item(self, r: Row) -> dict:
        return {
            "path": r.path, "name": r.name, "rel": r.rel, "size": r.size, "mtime_ns": r.mtime_ns,
            "new_name": r.final_name, "new_path": os.path.join(os.path.dirname(r.path), r.final_name) if r.final_name else "",
            "system_name": r.system_name, "manual_name": r.proposed_override is not None,
            "final_name": r.final_name, "fields": dict(r.fields),
            "edited_fields": [FIELD_LABELS[k] for k in FIELD_KEYS if k in r.edited], "notes": r.notes_text(),
        }

    def do_rename(self, confirmed: bool = False):
        a = self.app
        if a.busy:
            messagebox.showinfo("Please wait", "Another task is still running.", parent=self.winfo_toplevel())
            return
        if not self.preview_active:
            messagebox.showinfo("Preview first", "Please click 'Preview before renaming' first.", parent=self.winfo_toplevel())
            return
        if not any(self._codes()):
            messagebox.showwarning("Choose a format", "Please choose at least ONE part for the new file name.",
                                   parent=self.winfo_toplevel())
            return
        self._recompute_names()
        self._refresh_all()
        ready = [r for r in self.rows if not block_reason(r)]
        if not ready:
            messagebox.showinfo("Nothing to rename", "No approved row is ready to rename. Check the notes column.",
                                parent=self.winfo_toplevel())
            self.update_rename_buttons()
            return
        root = a.root_folder
        backup_on = bool(self.backup_var.get())
        if backup_on:
            if not self.backup_dir:
                messagebox.showwarning("Backup folder", "Please choose the backup folder first.", parent=self.winfo_toplevel())
                return
            if is_inside(self.backup_dir, root):
                messagebox.showerror("Backup folder", "The backup folder must be OUTSIDE the folder being renamed.",
                                     parent=self.winfo_toplevel())
                return
        skipped_rows = [r for r in self.rows if block_reason(r)]
        if not confirmed:
            msg = ("%d file(s) will be RENAMED.\n%d file(s) will be left untouched (not approved, or need manual review).\n\n"
                   "Backup first: %s\nSave rename log: %s\n\nThe original file extensions are kept. You can undo this batch "
                   "afterwards.\n\nStart renaming?" % (len(ready), len(skipped_rows),
                                                      ("YES -> " + self.backup_dir) if backup_on else "NO",
                                                      "yes" if self.log_var.get() else "no"))
            if not messagebox.askyesno("Confirm renaming", msg, parent=self.winfo_toplevel()):
                return
        plan = [self._plan_item(r) for r in ready]
        skipped = []
        for r in skipped_rows:
            it = self._plan_item(r)
            it["reason"] = block_reason(r)
            it["final_name"] = ""
            skipped.append(it)
        if backup_on and self._backup_session_dir is None:
            self._backup_session_dir = os.path.join(self.backup_dir, "BankDoc_Backup_" + stamp())
        sess = self._backup_session_dir if backup_on else None
        save_log = bool(self.log_var.get())
        LOG.set_folder(root)
        LOG.info("Rename batch started: %d file(s); backup=%s" % (len(plan), sess or "no"))
        a.busy = True
        self.update_rename_buttons()
        self.undo_btn.configure(state="disabled")
        self.start_btn.configure(state="disabled")
        self.prog.set(0)
        a.runner.run(lambda progress: run_rename_batch(plan, skipped, root, sess, save_log, progress),
                     on_done=lambda res: self._rename_done(res), on_error=self._rename_error,
                     on_progress=self._rename_progress)

    def _rename_progress(self, phase, i, n, name):
        label = {"hash": "Checking file fingerprints", "backup": "Backing up", "rename": "Renaming"}.get(phase, phase)
        self.prog.set(i / max(n, 1))
        self.status_lbl.configure(text="%s: %d of %d  -  %s" % (label, i, n, name), text_color=C["muted"])

    def _rename_error(self, e):
        self.app.busy = False
        self.start_btn.configure(state="normal")
        self.update_rename_buttons()
        self.refresh_undo_state()
        messagebox.showerror("Renaming stopped",
                             "An unexpected problem stopped the renaming:\n\n%s\n\nThe file rename_session.json in the "
                             "folder records exactly which files were renamed. Details are in the processing log."
                             % short_err(e, 300), parent=self.winfo_toplevel())

    def _rename_done(self, res: dict):
        a = self.app
        a.busy = False
        self.start_btn.configure(state="normal")
        stage = res.get("stage", "")
        if stage in ("preflight_failed", "backup_failed", "session_failed"):
            titles = {"preflight_failed": "Rename NOT started - problem with some files",
                      "backup_failed": "Rename NOT started - backup problem",
                      "session_failed": "Rename NOT started - cannot write the session file"}
            LOG.error("%s: %s" % (titles[stage], "; ".join("%s (%s)" % f for f in res["failures"][:20])))
            self.status_lbl.configure(text="Nothing was renamed: " + titles[stage], text_color=C["red"])
            self.update_rename_buttons()
            self.refresh_undo_state()
            retry = show_problems(
                self.winfo_toplevel(), titles[stage],
                "NOTHING was renamed. These files/problems stopped the batch. Fix them (for example free disk space, "
                "close the file in other programs) and press Retry, or Cancel.",
                [(os.path.basename(f) if os.path.sep in f else f, why) for f, why in res["failures"]], allow_retry=True)
            if retry:
                self.do_rename(confirmed=True)
            else:
                self._backup_session_dir = None
            return
        by_path = {r.path: r for r in self.rows}
        renamed = failed = 0
        for item in res.get("entries", []):
            if item.get("result") == "RENAMED":
                r = by_path.get(item["path"])
                if r is not None:
                    a.cache.rekey(r.path, item["new_path"])
                    r.path = item["new_path"]
                    r.name = item["new_name"]
                    r.proposed_override = None
                renamed += 1
            elif item.get("result") == "FAILED":
                failed += 1
        self._backup_session_dir = None
        self._recompute_names()
        self._refresh_all()
        self.update_rename_buttons()
        self.refresh_undo_state()
        self.prog.set(1)
        left = len([1 for i in res.get("entries", []) if i.get("result") == "NOT RENAMED"])
        extra = ""
        if res.get("backup_dir"):
            extra += "\nBackup copies: %s" % res["backup_dir"]
        if res.get("log_path"):
            extra += "\nDetailed log: %s" % res["log_path"]
        if res.get("log_error"):
            extra += "\n⚠ The log could not be saved: %s" % res["log_error"]
        extra += "\nSession record: %s" % session_path(a.root_folder)
        if stage == "done":
            LOG.info("Rename batch finished: %d renamed." % renamed)
            self.status_lbl.configure(text="Renamed %d file(s)." % renamed, text_color=C["green"])
            messagebox.showinfo("Renaming complete", "Renamed %d file(s).%s" % (renamed, extra), parent=self.winfo_toplevel())
        else:
            LOG.error("Rename batch STOPPED: %s" % res.get("stop_reason", ""))
            self.status_lbl.configure(text="Renaming STOPPED after %d file(s)." % renamed, text_color=C["red"])
            messagebox.showwarning(
                "Renaming stopped",
                "The batch was stopped to stay safe:\n%s\n\nRenamed before the stop: %d\nNot renamed (left as they were): %d%s\n\n"
                "You can fix the problem and run the batch again, or use 'Undo last batch'."
                % (res.get("stop_reason", ""), renamed, left + failed, extra), parent=self.winfo_toplevel())

    # ------------------------------------------------------------------
    # undo
    # ------------------------------------------------------------------
    def refresh_undo_state(self):
        root = self.app.root_folder
        state = "disabled"
        if root and os.path.isdir(root):
            try:
                data = load_session(root)
                if data is not None:
                    reconcile_session(data)
                    if last_undoable_batch(data) is not None:
                        state = "normal"
            except SessionCorrupt as e:
                LOG.warning("rename_session.json cannot be read: %s" % e)
        if self.app.busy:
            state = "disabled"
        self.undo_btn.configure(state=state)

    def undo(self):
        a = self.app
        if a.busy:
            messagebox.showinfo("Please wait", "Another task is still running.", parent=self.winfo_toplevel())
            return
        try:
            data = load_session(a.root_folder)
        except SessionCorrupt as e:
            messagebox.showerror("Cannot undo", "rename_session.json cannot be read: %s" % e, parent=self.winfo_toplevel())
            return
        if data is None:
            messagebox.showinfo("Nothing to undo", "No rename session found in this folder.", parent=self.winfo_toplevel())
            return
        reconcile_session(data)
        batch = last_undoable_batch(data)
        if batch is None:
            messagebox.showinfo("Nothing to undo", "There is no batch left to undo.", parent=self.winfo_toplevel())
            self.refresh_undo_state()
            return
        n = sum(1 for e in batch["entries"] if e.get("status") == "renamed")
        if not messagebox.askyesno(
                "Undo last batch?",
                "Batch %s (%s)\n%d renamed file(s) will be put back to their original names.\n\nEach file is verified first "
                "(still there, old name free, content unchanged). Files that do not pass are left alone and listed.\n\n"
                "Continue?" % (batch.get("batch_id", "?"), batch.get("started", ""), n), parent=self.winfo_toplevel()):
            return
        root = a.root_folder
        LOG.set_folder(root)
        a.busy = True
        self.undo_btn.configure(state="disabled")
        self.update_rename_buttons()
        a.runner.run(lambda progress: run_undo(root, progress), on_done=self._undo_done, on_error=self._rename_error,
                     on_progress=lambda phase, i, nn, name: self.status_lbl.configure(
                         text="Undoing %d of %d - %s" % (i, nn, name), text_color=C["muted"]))

    def _undo_done(self, out: dict):
        a = self.app
        a.busy = False
        by_path = {r.path: r for r in self.rows}
        for new, old in out.get("restored", []):
            r = by_path.get(new)
            if r is not None:
                a.cache.rekey(new, old)
                r.path = old
                r.name = os.path.basename(old)
                r.proposed_override = None
        if self.preview_active:
            self._recompute_names()
        self._refresh_all()
        self.update_rename_buttons()
        self.refresh_undo_state()
        n_ok = len(out.get("restored", []))
        skipped = out.get("skipped", [])
        LOG.info("Undo finished: %d restored, %d skipped." % (n_ok, len(skipped)))
        for f, why in skipped:
            LOG.warning("Undo skipped %s: %s" % (f, why))
        if out.get("status") in ("nothing", "error"):
            messagebox.showinfo("Undo", out.get("message", ""), parent=self.winfo_toplevel())
            return
        self.status_lbl.configure(text="Undo finished: %d restored, %d left alone." % (n_ok, len(skipped)),
                                  text_color=C["green"] if not skipped else C["orange"])
        msg = "%d file(s) restored to their original names." % n_ok
        if out.get("message"):
            msg += "\n\n" + out["message"]
        if skipped:
            msg += "\n\n%d file(s) were NOT touched:\n" % len(skipped) + "\n".join(
                "• %s\n   %s" % (os.path.basename(f), why) for f, why in skipped[:12])
        messagebox.showinfo("Undo result", msg, parent=self.winfo_toplevel())


# ==========================================================================
#  MAIN WINDOW
# ==========================================================================
class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title("%s  v%s   -   offline CA office tool" % (APP_NAME, APP_VERSION))
        self.geometry("1380x900")
        self.minsize(1050, 700)
        self.configure(fg_color=C["bg"])
        try:
            self.state("zoomed")
        except Exception:
            pass

        # ---- shared state
        self.busy = False
        self.root_folder = ""
        self.include_sub = False
        self.good_entries: List[FileEntry] = []
        self.skipped_entries: List[FileEntry] = []
        self.selected_model: Optional[ModelInfo] = None
        self.cache = DecryptedCache()
        self.runner = TaskRunner()
        self.unlocked = {1: True, 2: False, 3: False}
        self.current = 1

        setup_ttk_style(self)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- sidebar
        side = ctk.CTkFrame(self, fg_color=C["indigo"], corner_radius=0, width=250)
        side.grid(row=0, column=0, sticky="nsw")
        side.grid_propagate(False)
        ctk.CTkLabel(side, text="🏦 BankDoc", text_color="white",
                     font=ctk.CTkFont(family=FONT, size=26, weight="bold")).pack(anchor="w", padx=18, pady=(22, 0))
        ctk.CTkLabel(side, text="Processor & Renamer", text_color="#FFC21A",
                     font=ctk.CTkFont(family=FONT, size=15, weight="bold")).pack(anchor="w", padx=18)
        ctk.CTkLabel(side, text="Offline desk tool for CA offices", text_color="#B9BEF0",
                     font=ctk.CTkFont(family=FONT, size=11)).pack(anchor="w", padx=18, pady=(0, 20))
        self.step_btns = {}
        steps = [(1, "1   Upload files", C["blue"]), (2, "2   Choose offline LLM", C["purple"]),
                 (3, "3   Review, Extract & Rename", C["magenta"])]
        for n, text, color in steps:
            b = ctk.CTkButton(side, text=text, anchor="w", height=44, corner_radius=10, fg_color="transparent",
                              hover_color=color, text_color="white",
                              font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
                              command=lambda k=n: self.goto(k))
            b.pack(fill="x", padx=12, pady=4)
            self.step_btns[n] = (b, color)
        ctk.CTkLabel(side, text="", height=10).pack()
        help_button(side, "How this tool works",
                    "STEP 1  Choose the folder of bank NEFT/RTGS/IMPS acknowledgements (PDF or image). Locked PDFs "
                    "can be unlocked with a password.\n\nSTEP 2  Pick the AI model that runs on this computer "
                    "(LM Studio / Ollama).\n\nSTEP 3  The AI reads each file. You check the table, fix anything, "
                    "export to Excel/PDF and rename the files (with optional backup and undo).\n\nEverything stays on "
                    "this computer. Nothing is uploaded anywhere.").pack(anchor="w", padx=18, pady=6)
        sp = ctk.CTkLabel(side, text="")
        sp.pack(expand=True)
        ctk.CTkButton(side, text="🧹 Clear unlocked-PDF copies\n    from memory", height=46, fg_color="#4A4EA8",
                      hover_color=C["magenta"], text_color="white", command=self.clear_cache).pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(side, text="🔒 Offline utility\nTalks only with offline LLM", text_color="#8FF0D8", justify="left",
                     font=ctk.CTkFont(family=FONT, size=12, weight="bold")).pack(anchor="w", padx=18, pady=(4, 16))

        # ---- pages
        container = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        container.grid(row=0, column=1, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        self.pages = {1: PageFiles(container, self), 2: PageLLM(container, self), 3: PageProcess(container, self)}
        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")
        self.show_page(1)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(80, self._poll)
        LOG.info("%s started. Offline mode - only localhost connections are allowed." % APP_NAME)

    # ---- navigation
    def goto(self, n: int):
        if not self.unlocked.get(n):
            messagebox.showinfo("Not yet", "Please finish the previous step first.", parent=self)
            return
        self.show_page(n)

    def show_page(self, n: int):
        self.unlocked[n] = True
        self.current = n
        self.pages[n].tkraise()
        for k, (b, color) in self.step_btns.items():
            b.configure(fg_color=color if k == n else "transparent")
        self.pages[n].on_show()

    def clear_cache(self):
        n = self.cache.count()
        self.cache.clear()
        messagebox.showinfo("Cleared", "%d unlocked PDF copy(ies) removed from memory.\n\nLocked files will need their "
                            "password again if you want to read them." % n, parent=self)

    # ---- housekeeping
    def _poll(self):
        try:
            self.runner.drain()
            self.pages[3].drain_log()
        except Exception:
            pass
        self.after(80, self._poll)

    def report_callback_exception(self, exc, val, tb):
        LOG.error("Unexpected error in the window:\n%s" % "".join(traceback.format_exception(exc, val, tb)))
        try:
            messagebox.showerror("Unexpected error",
                                 "Something unexpected happened:\n\n%s: %s\n\nIt has been recorded in the processing log. "
                                 "Your files were not changed by this error." % (exc.__name__, val), parent=self)
        except Exception:
            pass

    def on_close(self):
        if self.busy and not messagebox.askyesno(
                "Task running", "A task is still running. Closing now may stop it halfway.\n\nClose anyway?", parent=self):
            return
        self.cache.clear()
        self.destroy()


def main():
    def _hook(exc_type, exc, tb):
        LOG.error("Unhandled error:\n%s" % "".join(traceback.format_exception(exc_type, exc, tb)))
    sys.excepthook = _hook
    try:
        threading.excepthook = lambda a: LOG.error("Unhandled thread error:\n%s" % "".join(
            traceback.format_exception(a.exc_type, a.exc_value, a.exc_traceback)))
    except Exception:
        pass
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()