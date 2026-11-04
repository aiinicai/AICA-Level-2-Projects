"""
GST Toolkit for Chartered Accountants
--------------------------------------
Modules:
  1. GSTIN Validator (Mod-36) + Reverse-lookup suggestions
  2. HSN / SAC Search (code->desc, desc->code)
  3. GSTR-1 JSON Validator / Rectifier / Excel exporter
  4. GSTR-2B vs Books Reconciler (B2B sheet only) + Multi-file merger

Requirements:
    pip install PyQt6 openpyxl rapidfuzz pandas python-docx reportlab xlsxwriter
"""

import os
import sys
import json
import re
import copy
import math
import traceback
from datetime import datetime
from collections import defaultdict

# ---- Third party ----
try:
    import pandas as pd
    from rapidfuzz import process, fuzz
    from openpyxl import load_workbook, Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
        QFileDialog, QMessageBox, QComboBox, QCheckBox, QSplitter, QPlainTextEdit,
        QHeaderView, QAbstractItemView, QGroupBox, QFormLayout, QSpinBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QGuiApplication, QAction
except ImportError as e:
    print("Missing dependency:", e)
    print("Run: pip install PyQt6 openpyxl rapidfuzz pandas python-docx reportlab xlsxwriter")
    sys.exit(1)

# =============================================================
# SECTION 1 : GSTIN MOD-36 ENGINE
# =============================================================

GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def gstin_check_digit(first14: str) -> str:
    """
    Compute the 15th checksum character using the official GST Mod-36
    (Luhn mod-36 variant) algorithm.

    Algorithm (per GSTN spec):
      1. Each character has value = index in 0..9A..Z (base 36).
      2. Weights alternate 1, 2, 1, 2, ... across the first 14 chars.
      3. product = value * weight
      4. fold = (product // 36) + (product % 36)   # sum quotient + remainder
      5. total = sum of all folds
      6. check digit = CHARSET[(36 - total % 36) % 36]
    """
    first14 = first14.upper()
    if len(first14) != 14:
        raise ValueError("Need exactly 14 characters")
    total = 0
    for idx, ch in enumerate(first14):
        try:
            code = GSTIN_CHARS.index(ch)
        except ValueError:
            raise ValueError(f"Illegal character '{ch}' in GSTIN")
        weight = 1 if idx % 2 == 0 else 2
        product = code * weight
        total += (product // 36) + (product % 36)
    return GSTIN_CHARS[(36 - total % 36) % 36]


def gstin_format_ok(gstin: str) -> bool:
    """Structural (regex) check: 2 digits + 5 letters + 4 digits + 1 letter + 1 alnum + 'Z' + 1 alnum."""
    if not isinstance(gstin, str):
        return False
    return bool(re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", gstin.upper()))

def validate_gstin(gstin: str):
    """Returns (status, message). status in {'OK','FORMAT','CHECKSUM'}."""
    if not gstin:
        return "FORMAT", "Empty GSTIN"
    g = gstin.upper().strip()
    if not gstin_format_ok(g):
        return "FORMAT", "Structural format invalid (expected 15 chars, e.g. 22AAAAA0000A1Z5)"
    expected = gstin_check_digit(g[:14])
    if expected != g[14]:
        return "CHECKSUM", f"Checksum mismatch (last char should be '{expected}')"
    return "OK", "Valid GSTIN"

def suggest_gstin_corrections(bad: str, max_single_char_options: int = 400):
    """
    Returns dict:
      {
        'fix_last_char':   corrected_gstin or None,   # assume first 14 are right
        'fix_one_of_14':   [list of corrected gstins] # assume 15th is right; try all single-char swaps in first 14
      }
    """
    bad = (bad or "").upper().strip()
    out = {"fix_last_char": None, "fix_one_of_14": []}
    if len(bad) != 15:
        return out

    first14, last = bad[:14], bad[14]

    # Strategy A: first 14 assumed correct → recompute last char
    try:
        if all(c in GSTIN_CHARS for c in first14):
            corrected_last = gstin_check_digit(first14)
            out["fix_last_char"] = first14 + corrected_last
    except Exception:
        pass

    # Strategy B: last char assumed correct → try swapping each of first 14 to another char
    # For each position, compute the required character such that checksum matches
    # Because checksum is linear-ish over positions, we can invert by brute force
    results = []
    if len(first14) == 14:
        for pos in range(14):
            for alt in GSTIN_CHARS:
                if alt == first14[pos]:
                    continue
                candidate = first14[:pos] + alt + first14[pos+1:]
                # Structural quick check
                if not gstin_format_ok(candidate + last):
                    continue
                try:
                    if gstin_check_digit(candidate) == last:
                        results.append(candidate + last)
                except Exception:
                    continue
    # de-dup & cap
    seen = set()
    dedup = []
    for r in results:
        if r not in seen:
            seen.add(r)
            dedup.append(r)
    out["fix_one_of_14"] = dedup[:max_single_char_options]
    return out


# =============================================================
# SECTION 2 : HSN/SAC SEARCH
# =============================================================

class HSNSACSearch:
    """
    Loads HSN & SAC data from an Excel (HSN_SAC (3).xlsx) once and caches to JSON.
    The Excel must have two sheets 'HSN_MSTR' and 'SAC_MSTR' with headers:
        HSN_CD | HSN_Description   (or SAC_CD | SAC_Description)
    """
    def __init__(self, cache_path: str = "hsn_cache.json"):
        self.cache_path = cache_path
        self.hsn = []  # list of (code, desc)
        self.sac = []
        self._load()

    def _load(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.hsn = [tuple(x) for x in data.get("hsn", [])]
                self.sac = [tuple(x) for x in data.get("sac", [])]
                return
            except Exception:
                pass
        # No cache → build from Excel if we can find it next to script
        for guess in ["HSN_SAC (3).xlsx", "HSN_SAC.xlsx", "HSN_SAC3.xlsx"]:
            if os.path.exists(guess):
                try:
                    self.build_from_excel(guess)
                    return
                except Exception:
                    continue

    def build_from_excel(self, path: str):
        wb = load_workbook(path, read_only=True, data_only=True)
        def read_sheet(name, code_key, desc_key):
            if name not in wb.sheetnames:
                return []
            ws = wb[name]
            rows = []
            header_seen = False
            for row in ws.iter_rows(values_only=True):
                if row is None:
                    continue
                r0 = str(row[0]).strip() if row[0] is not None else ""
                r1 = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
                if not header_seen:
                    if r0.upper() == code_key.upper():
                        header_seen = True
                    continue
                if not r0 or not r1:
                    continue
                rows.append((r0, r1))
            return rows
        self.hsn = read_sheet("HSN_MSTR", "HSN_CD", "HSN_Description")
        self.sac = read_sheet("SAC_MSTR", "SAC_CD", "SAC_Description")
        wb.close()
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump({"hsn": self.hsn, "sac": self.sac}, f, ensure_ascii=False)
        return len(self.hsn), len(self.sac)

    def search(self, query: str, kind: str = "both", limit: int = 50):
        """kind: 'hsn' | 'sac' | 'both'."""
        q = (query or "").strip()
        if not q:
            return []
        datasets = []
        if kind in ("hsn", "both"):
            datasets.append(("HSN", self.hsn))
        if kind in ("sac", "both"):
            datasets.append(("SAC", self.sac))
        results = []
        q_upper = q.upper()
        for label, rows in datasets:
            # 1) exact code
            for code, desc in rows:
                if code == q:
                    results.append((label, code, desc, 100.0))
            # 2) startswith code (partial code search)
            if q.isdigit():
                for code, desc in rows:
                    if code != q and code.startswith(q):
                        results.append((label, code, desc, 95.0))
            # 3) fuzzy description
            if not q.isdigit() or len(results) < 5:
                strings = [d[1] for d in rows]
                matches = process.extract(q_upper, strings, scorer=fuzz.partial_ratio,
                                          limit=limit)
                for m, score, idx in matches:
                    if score >= 60:
                        code, desc = rows[idx]
                        results.append((label, code, desc, float(score)))
        # dedup by (label, code) keeping highest score
        best = {}
        for lbl, code, desc, sc in results:
            k = (lbl, code)
            if k not in best or sc > best[k][2]:
                best[k] = (lbl, code, desc, sc)
        out = sorted(best.values(), key=lambda x: (-x[3], x[1]))
        return out[:limit]


# =============================================================
# SECTION 3 : GSTR-1 JSON VALIDATOR / RECTIFIER / EXPORTER
# =============================================================

class GSTR1Validator:
    """
    Validates GSTINs and HSN/SAC codes in a GSTR-1 style JSON.
    Works on the attached 'April.json' style (b2b invoices with ctin, inum, itms.itm_det).
    Also handles b2cs, hsn(optional), b2ba etc. loosely.
    """

    def __init__(self, hsn_engine: HSNSACSearch):
        self.hsn_engine = hsn_engine
        # Build fast lookup sets
        self.valid_hsn = set(c for c, _ in hsn_engine.hsn)
        self.valid_sac = set(c for c, _ in hsn_engine.sac)

    # ---------- HSN validation ----------
    def hsn_status(self, code: str):
        """Returns ('OK'|'UNKNOWN', message). We accept 2-8 digit prefixes."""
        if code is None:
            return "UNKNOWN", "Missing HSN/SAC"
        c = str(code).strip()
        if not c.isdigit():
            return "UNKNOWN", "HSN/SAC must be numeric"
        # Try longest-to-shortest prefix present in our master
        for L in range(len(c), 1, -1):
            if c[:L] in self.valid_hsn or c[:L] in self.valid_sac:
                return "OK", f"Matched prefix {c[:L]}"
        return "UNKNOWN", "Not found in HSN/SAC master"

    # ---------- Iterate & validate ----------
    def scan(self, data: dict):
        """
        Returns list of issue dicts:
          {
            'path': 'b2b[0].inv[1].itms[0].itm_det.hsn',
            'type': 'GSTIN' | 'HSN',
            'value': '...',
            'message': '...',
            'suggestions': {...}   # for GSTIN
          }
        """
        issues = []
        self._scan_b2b(data, issues)
        self._scan_b2b_amend(data, issues)
        self._scan_b2cs(data, issues)
        self._scan_hsn_section(data, issues)
        return issues

    def _scan_b2b(self, data, issues):
        b2b = data.get("b2b") or []
        for i, party in enumerate(b2b):
            ctin = party.get("ctin", "")
            status, msg = validate_gstin(ctin)
            if status != "OK":
                sug = suggest_gstin_corrections(ctin)
                issues.append({
                    "path": f"b2b[{i}].ctin",
                    "type": "GSTIN",
                    "value": ctin,
                    "message": msg,
                    "suggestions": sug,
                })
            for j, inv in enumerate(party.get("inv") or []):
                for k, it in enumerate(inv.get("itms") or []):
                    det = it.get("itm_det") or {}
                    hsn = det.get("hsn_sc") or det.get("hsn") or det.get("hsn_code")
                    if hsn is not None:
                        st, m = self.hsn_status(hsn)
                        if st != "OK":
                            issues.append({
                                "path": f"b2b[{i}].inv[{j}].itms[{k}].itm_det.hsn",
                                "type": "HSN",
                                "value": str(hsn),
                                "message": m,
                                "suggestions": self._hsn_suggestions(str(hsn)),
                            })

    def _scan_b2b_amend(self, data, issues):
        for sec in ("b2ba",):
            lst = data.get(sec) or []
            for i, party in enumerate(lst):
                ctin = party.get("ctin", "")
                status, msg = validate_gstin(ctin)
                if status != "OK":
                    sug = suggest_gstin_corrections(ctin)
                    issues.append({
                        "path": f"{sec}[{i}].ctin",
                        "type": "GSTIN",
                        "value": ctin,
                        "message": msg,
                        "suggestions": sug,
                    })

    def _scan_b2cs(self, data, issues):
        # b2cs typically has no GSTIN/HSN in invoice; skip.
        pass

    def _scan_hsn_section(self, data, issues):
        hsn_sec = data.get("hsn") or {}
        data_rows = hsn_sec.get("data") or []
        for i, row in enumerate(data_rows):
            code = row.get("hsn_sc") or row.get("hsn") or row.get("num")
            if code:
                st, m = self.hsn_status(code)
                if st != "OK":
                    issues.append({
                        "path": f"hsn.data[{i}].hsn_sc",
                        "type": "HSN",
                        "value": str(code),
                        "message": m,
                        "suggestions": self._hsn_suggestions(str(code)),
                    })

    def _hsn_suggestions(self, code: str):
        """Find closest HSN/SAC by fuzzy description or numeric prefix."""
        code = str(code).strip()
        # first try prefix matching
        prefix_hits = []
        for c, d in self.hsn_engine.hsn:
            if c.startswith(code[:4]) or code.startswith(c[:4]):
                prefix_hits.append((c, d))
                if len(prefix_hits) >= 20:
                    break
        # fallback fuzzy on code as text
        if len(prefix_hits) < 5:
            strings = [c for c, _ in self.hsn_engine.hsn]
            matches = process.extract(code, strings, scorer=fuzz.ratio, limit=10)
            for m, sc, idx in matches:
                prefix_hits.append(self.hsn_engine.hsn[idx])
        # dedup
        seen = set()
        out = []
        for c, d in prefix_hits:
            if c in seen:
                continue
            seen.add(c)
            out.append((c, d))
        return out[:10]

    # ---------- Rectify ----------
    def apply_corrections(self, data: dict, corrections: dict):
        """
        corrections: mapping path -> new value.
        Path e.g. 'b2b[0].ctin' or 'b2b[0].inv[1].itms[0].itm_det.hsn'
        """
        new_data = copy.deepcopy(data)
        for path, new_val in corrections.items():
            if new_val in (None, ""):
                continue
            self._set_path(new_data, path, new_val)
        return new_data

    def _set_path(self, root, path: str, value):
        # very small path parser: segments like name[index]
        parts = []
        for seg in path.split("."):
            m = re.match(r"^([A-Za-z_]+)(?:\[(\d+)\])?$", seg)
            if not m:
                raise ValueError(f"Unparsable segment '{seg}'")
            name, idx = m.group(1), m.group(2)
            parts.append((name, int(idx) if idx is not None else None))
        cur = root
        for i, (name, idx) in enumerate(parts):
            last = (i == len(parts) - 1)
            if idx is None:
                if last:
                    cur[name] = value
                else:
                    cur = cur[name]
            else:
                if name not in cur or cur[name] is None:
                    cur[name] = []
                lst = cur[name]
                while len(lst) <= idx:
                    lst.append({})
                if last:
                    lst[idx] = value
                else:
                    cur = lst[idx]

    # ---------- Excel export ----------
    def to_excel(self, data: dict, out_path: str):
        """
        Flatten JSON into sheets: B2B Invoices, B2B Amendments, HSN Summary.
        """
        with pd.ExcelWriter(out_path, engine="xlsxwriter") as xl:
            # B2B
            rows = []
            for p in data.get("b2b") or []:
                ctin = p.get("ctin", "")
                for inv in p.get("inv") or []:
                    base = {
                        "ctin": ctin,
                        "inum": inv.get("inum"),
                        "idt": inv.get("idt"),
                        "val": inv.get("val"),
                        "pos": inv.get("pos"),
                        "rchrg": inv.get("rchrg"),
                        "inv_typ": inv.get("inv_typ"),
                        "itms_count": len(inv.get("itms") or []),
                    }
                    # flatten first item tax values; add tax columns
                    tx_total = 0; tamt_total = 0
                    for it in inv.get("itms") or []:
                        det = it.get("itm_det") or {}
                        tx_total += det.get("txval", 0) or 0
                        tamt_total += det.get("tamt", 0) or 0
                    base["taxable_value"] = tx_total
                    base["tax_amount"] = tamt_total
                    rows.append(base)
            pd.DataFrame(rows).to_excel(xl, sheet_name="B2B Invoices", index=False)

            # B2BA
            rows = []
            for p in data.get("b2ba") or []:
                ctin = p.get("ctin", "")
                for inv in p.get("inv") or []:
                    rows.append({
                        "ctin": ctin,
                        "orig_inum": inv.get("oinum"),
                        "orig_idt": inv.get("oidt"),
                        "inum": inv.get("inum"),
                        "idt": inv.get("idt"),
                        "val": inv.get("val"),
                    })
            if rows:
                pd.DataFrame(rows).to_excel(xl, sheet_name="B2BA", index=False)

            # HSN summary (if present)
            hsn_rows = []
            for row in (data.get("hsn", {}) or {}).get("data") or []:
                hsn_rows.append({
                    "hsn_sc": row.get("hsn_sc") or row.get("num"),
                    "desc": row.get("desc"),
                    "uqc": row.get("uqc"),
                    "qty": row.get("qty"),
                    "txval": row.get("txval"),
                    "iamt": row.get("iamt"),
                    "camt": row.get("camt"),
                    "samt": row.get("samt"),
                    "csamt": row.get("csamt"),
                })
            if hsn_rows:
                pd.DataFrame(hsn_rows).to_excel(xl, sheet_name="HSN Summary", index=False)

            # B2CS
            b2cs_rows = []
            for row in data.get("b2cs") or []:
                b2cs_rows.append({
                    "sply_ty": row.get("sply_ty"),
                    "pos": row.get("pos"),
                    "typ": row.get("typ"),
                    "txval": row.get("txval"),
                    "rt": row.get("rt"),
                    "tamt": row.get("tamt"),
                })
            if b2cs_rows:
                pd.DataFrame(b2cs_rows).to_excel(xl, sheet_name="B2CS", index=False)
        return out_path


# =============================================================
# SECTION 4 : GSTR-2B vs BOOKS RECONCILIATION
# =============================================================

class GSTR2BReconciler:
    """
    - Reads GSTR-2B Excel → uses ONLY the 'B2B' sheet (title of sheet must be exactly 'B2B').
    - Books excel: columns as in books_gstr2.xlsx → GSTN, PARTY NAME, VOUCHER TYPE,
      INVOICE NO, INVOICE DATE, TAXABLE VALUE, IGST, CGST, SGST, INVOICE VALUE
    - Tolerance applies on tax amounts.
    """

    TOL_DEFAULT = 1.0  # rupees

    # -------------------- Template creators --------------------
    @staticmethod
    def create_books_template(path: str):
        cols = ["GSTN", "PARTY NAME", "VOUCHER TYPE", "INVOICE NO", "INVOICE DATE",
                "TAXABLE VALUE", "IGST", "CGST", "SGST", "INVOICE VALUE"]
        df = pd.DataFrame(columns=cols)
        with pd.ExcelWriter(path, engine="xlsxwriter") as xl:
            df.to_excel(xl, sheet_name="GSTR2", index=False)
        return path

    # -------------------- Readers --------------------
    @staticmethod
    def read_books(path: str) -> pd.DataFrame:
        # Books file uses sheet name 'GSTR2' in sample
        try:
            df = pd.read_excel(path, sheet_name="GSTR2")
        except Exception:
            df = pd.read_excel(path)
        df.columns = [str(c).strip() for c in df.columns]
        # normalize
        for c in ["GSTN", "INVOICE NO", "PARTY NAME"]:
            if c in df.columns:
                df[c] = df[c].astype(str).str.strip()
        for c in ["TAXABLE VALUE", "IGST", "CGST", "SGST", "INVOICE VALUE"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        return df

    @staticmethod
    def read_gstr2b_b2b(path: str) -> pd.DataFrame:
        """
        Reads the GSTR-2B workbook, ONLY the 'B2B' sheet.
        Layout: 2-3 header rows, then data begins. Actual data columns:
            A: GSTIN of supplier
            B: Trade/Legal name
            C: Invoice number
            D: Invoice type
            E: Invoice Date
            F: Invoice Value
            G: Place of supply
            H: Supply Attract Reverse Charge
            I: Taxable Value
            J: Integrated Tax
            K: Central Tax
            L: State/UT Tax
            M: Cess
            N: GSTR-1 Period
            O: Filing Date
            P: ITC Availability
            Q: Reason
            R: Applicable % of Tax Rate
            S: Source
            T: IRN
            U: IRN Date
        We skip rows until we find one whose col A matches GSTIN pattern (15 chars).
        """
        wb = load_workbook(path, read_only=True, data_only=True)
        if "B2B" not in wb.sheetnames:
            raise ValueError("Workbook does not contain a sheet named 'B2B'")
        ws = wb["B2B"]

        rows = list(ws.iter_rows(values_only=True))
        wb.close()

        # Find the header row: contains "GSTIN of supplier" in col A
        header_idx = None
        for i, r in enumerate(rows[:30]):
            if r and r[0] and "gstin of supplier" in str(r[0]).lower():
                header_idx = i
                break
        if header_idx is None:
            # fallback: first row where col A looks like a GSTIN
            for i, r in enumerate(rows[:30]):
                if r and r[0] and re.fullmatch(r"[0-9]{2}[A-Z0-9]{10}[0-9A-Z]{3}", str(r[0]).upper()):
                    header_idx = i
                    break
        if header_idx is None:
            raise ValueError("Could not locate header row in B2B sheet of GSTR-2B")

        # Data starts at header_idx + 2 typically (because of two-line header).
        # We'll just skip rows until we hit a row whose col A looks like a GSTIN.
        data = []
        for r in rows[header_idx + 1:]:
            if r is None or r[0] is None:
                continue
            g = str(r[0]).strip().upper()
            if not re.fullmatch(r"[0-9]{2}[A-Z0-9]{10}[0-9A-Z]{3}", g):
                continue
            rec = {
                "GSTN": g,
                "SUPPLIER_NAME": (str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""),
                "INVOICE NO": (str(r[2]).strip() if len(r) > 2 and r[2] is not None else ""),
                "INVOICE TYPE": (str(r[3]).strip() if len(r) > 3 and r[3] is not None else ""),
                "INVOICE DATE": (str(r[4]).strip() if len(r) > 4 and r[4] is not None else ""),
                "INVOICE VALUE": _num(r[5] if len(r) > 5 else None),
                "POS": (str(r[6]).strip() if len(r) > 6 and r[6] is not None else ""),
                "RCHRG": (str(r[7]).strip() if len(r) > 7 and r[7] is not None else ""),
                "TAXABLE VALUE": _num(r[8] if len(r) > 8 else None),
                "IGST": _num(r[9] if len(r) > 9 else None),
                "CGST": _num(r[10] if len(r) > 10 else None),
                "SGST": _num(r[11] if len(r) > 11 else None),
                "CESS": _num(r[12] if len(r) > 12 else None),
                "GSTR1_PERIOD": (str(r[13]).strip() if len(r) > 13 and r[13] is not None else ""),
                "ITC_AVAILABILITY": (str(r[15]).strip() if len(r) > 15 and r[15] is not None else ""),
            }
            data.append(rec)
        return pd.DataFrame(data)

    # -------------------- Merge multiple 2B files --------------------
    @staticmethod
    def merge_2b(files):
        frames = [GSTR2BReconciler.read_gstr2b_b2b(f) for f in files]
        if not frames:
            return pd.DataFrame()
        merged = pd.concat(frames, ignore_index=True)
        return merged

    # -------------------- Reconciliation --------------------
    @staticmethod
    def reconcile(books: pd.DataFrame, twob: pd.DataFrame, tol: float = 1.0) -> dict:
        """
        Match strategy:
         1. By (GSTIN, Invoice No) exact
         2. Fallback: By (GSTIN, last 6 alnum of invoice no)
        Categories:
         - matched
         - amount_mismatch
         - only_in_books
         - only_in_2b
         - gstin_invalid_books
         - gstin_invalid_2b
        """
        b = books.copy()
        t = twob.copy()

        # Normalize invoice numbers (strip .0, spaces)
        def norm_inv(x):
            s = str(x).strip()
            if s.endswith(".0"):
                s = s[:-2]
            return s.upper()

        b["INV_KEY"] = b["INVOICE NO"].map(norm_inv)
        t["INV_KEY"] = t["INVOICE NO"].map(norm_inv)
        b["GSTN"] = b["GSTN"].astype(str).str.upper().str.strip()
        t["GSTN"] = t["GSTN"].astype(str).str.upper().str.strip()

        # GSTIN validation flags
        b["_gstin_ok"] = b["GSTN"].map(lambda g: validate_gstin(g)[0] == "OK")
        t["_gstin_ok"] = t["GSTN"].map(lambda g: validate_gstin(g)[0] == "OK")

        matched = []
        amount_mismatch = []
        only_books = []
        only_2b = []

        b_index = defaultdict(list)
        for i, r in b.iterrows():
            b_index[(r["GSTN"], r["INV_KEY"])].append(i)
        t_index = defaultdict(list)
        for i, r in t.iterrows():
            t_index[(r["GSTN"], r["INV_KEY"])].append(i)

        used_b = set()
        used_t = set()

        # Pass 1: exact key
        for key in list(set(b_index) & set(t_index)):
            bs = b_index[key]
            ts = t_index[key]
            for bi in bs:
                if bi in used_b:
                    continue
                # find best t match by total tax closeness
                best = None
                best_diff = None
                for ti in ts:
                    if ti in used_t:
                        continue
                    diff = _tax_diff(b.loc[bi], t.loc[ti])
                    if best_diff is None or diff < best_diff:
                        best_diff = diff
                        best = ti
                if best is None:
                    continue
                used_b.add(bi); used_t.add(best)
                if best_diff <= tol:
                    matched.append(_pair(b.loc[bi], t.loc[best]))
                else:
                    amount_mismatch.append(_pair(b.loc[bi], t.loc[best], diff=best_diff))

        for bi, r in b.iterrows():
            if bi not in used_b:
                only_books.append(r.to_dict())
        for ti, r in t.iterrows():
            if ti not in used_t:
                only_2b.append(r.to_dict())

        # GSTIN invalid lists
        invalid_books = [r.to_dict() for _, r in b[~b["_gstin_ok"]].iterrows()]
        invalid_2b = [r.to_dict() for _, r in t[~t["_gstin_ok"]].iterrows()]

        return {
            "matched": matched,
            "amount_mismatch": amount_mismatch,
            "only_in_books": only_books,
            "only_in_2b": only_2b,
            "gstin_invalid_books": invalid_books,
            "gstin_invalid_2b": invalid_2b,
        }

    # -------------------- Export --------------------
    @staticmethod
    def export_excel(recon: dict, path: str):
        with pd.ExcelWriter(path, engine="xlsxwriter") as xl:
            for name, rows in [
                ("Matched", recon["matched"]),
                ("Amount Mismatch", recon["amount_mismatch"]),
                ("Only in Books", recon["only_in_books"]),
                ("Only in 2B", recon["only_in_2b"]),
                ("GSTIN Invalid (Books)", recon["gstin_invalid_books"]),
                ("GSTIN Invalid (2B)", recon["gstin_invalid_2b"]),
            ]:
                df = pd.DataFrame(rows)
                df.to_excel(xl, sheet_name=name[:31], index=False)

    @staticmethod
    def export_word(recon: dict, path: str):
        from docx import Document
        doc = Document()
        doc.add_heading("GSTR-2B vs Books Reconciliation", level=0)
        doc.add_paragraph(f"Generated: {datetime.now():%d-%m-%Y %H:%M}")
        sections = [
            ("Matched", recon["matched"]),
            ("Amount Mismatch", recon["amount_mismatch"]),
            ("Only in Books", recon["only_in_books"]),
            ("Only in 2B", recon["only_in_2b"]),
            ("GSTIN Invalid (Books)", recon["gstin_invalid_books"]),
            ("GSTIN Invalid (2B)", recon["gstin_invalid_2b"]),
        ]
        for name, rows in sections:
            doc.add_heading(name, level=1)
            if not rows:
                doc.add_paragraph("None.")
                continue
            df = pd.DataFrame(rows)
            cols = list(df.columns)
            table = doc.add_table(rows=1, cols=len(cols))
            table.style = "Light Grid Accent 1"
            for j, c in enumerate(cols):
                table.rows[0].cells[j].text = str(c)
            for _, r in df.head(200).iterrows():
                cells = table.add_row().cells
                for j, c in enumerate(cols):
                    cells[j].text = str(r[c])
        doc.save(path)
        return path

    @staticmethod
    def export_pdf(recon: dict, path: str):
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(path, pagesize=landscape(A4))
        story = [Paragraph("GSTR-2B vs Books Reconciliation", styles["Title"]),
                 Paragraph(f"Generated: {datetime.now():%d-%m-%Y %H:%M}", styles["Normal"]),
                 Spacer(1, 12)]
        sections = [
            ("Matched", recon["matched"]),
            ("Amount Mismatch", recon["amount_mismatch"]),
            ("Only in Books", recon["only_in_books"]),
            ("Only in 2B", recon["only_in_2b"]),
            ("GSTIN Invalid (Books)", recon["gstin_invalid_books"]),
            ("GSTIN Invalid (2B)", recon["gstin_invalid_2b"]),
        ]
        for name, rows in sections:
            story.append(Paragraph(f"<b>{name}</b> — {len(rows)} records", styles["Heading2"]))
            if rows:
                df = pd.DataFrame(rows).head(100)
                data = [list(df.columns)] + df.astype(str).values.tolist()
                tbl = Table(data, repeatRows=1)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]))
                story.append(tbl)
            else:
                story.append(Paragraph("None.", styles["Normal"]))
            story.append(Spacer(1, 10))
        doc.build(story)
        return path


def _num(v):
    if v is None or v == "":
        return 0.0
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return 0.0

def _tax_diff(brow, trow) -> float:
    return abs(_num(brow.get("IGST", 0)) - _num(trow.get("IGST", 0))) + \
           abs(_num(brow.get("CGST", 0)) - _num(trow.get("CGST", 0))) + \
           abs(_num(brow.get("SGST", 0)) - _num(trow.get("SGST", 0)))

def _pair(brow, trow, diff=None):
    d = {
        "BOOKS_GSTN": brow.get("GSTN"),
        "2B_GSTN": trow.get("GSTN"),
        "BOOKS_INVOICE": brow.get("INVOICE NO"),
        "2B_INVOICE": trow.get("INVOICE NO"),
        "BOOKS_TAXABLE": _num(brow.get("TAXABLE VALUE", 0)),
        "2B_TAXABLE": _num(trow.get("TAXABLE VALUE", 0)),
        "BOOKS_IGST": _num(brow.get("IGST", 0)),
        "2B_IGST": _num(trow.get("IGST", 0)),
        "BOOKS_CGST": _num(brow.get("CGST", 0)),
        "2B_CGST": _num(trow.get("CGST", 0)),
        "BOOKS_SGST": _num(brow.get("SGST", 0)),
        "2B_SGST": _num(trow.get("SGST", 0)),
        "BOOKS_PARTY": brow.get("PARTY NAME"),
        "2B_PARTY": trow.get("SUPPLIER_NAME"),
    }
    if diff is not None:
        d["TAX_DIFF"] = round(diff, 2)
    return d


# =============================================================
# SECTION 5 : PYQT UI
# =============================================================

APP_FONT = "Segoe UI"


class GSTINWidget(QWidget):
    def __init__(self):
        super().__init__()
        v = QVBoxLayout(self)

        v.addWidget(QLabel("<b>GSTIN Validator (Mod-36) + Reverse correction</b>"))
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Enter 15-character GSTIN, e.g. 22AAAAA0000A1Z5")
        self.inp.setFont(QFont("Consolas", 12))
        row.addWidget(self.inp)
        btn = QPushButton("Validate")
        btn.clicked.connect(self.validate)
        row.addWidget(btn)
        paste_btn = QPushButton("Paste")
        paste_btn.clicked.connect(lambda: self.inp.setText(QGuiApplication.clipboard().text().strip()))
        row.addWidget(paste_btn)
        v.addLayout(row)

        self.status = QLabel("")
        self.status.setStyleSheet("font-size:14px; padding:6px;")
        v.addWidget(self.status)

        v.addWidget(QLabel("<b>Fix #1: Assume first 14 chars are correct → corrected 15th char</b>"))
        self.fix1 = QLineEdit(); self.fix1.setReadOnly(True); self.fix1.setFont(QFont("Consolas", 12))
        h1 = QHBoxLayout(); h1.addWidget(self.fix1)
        cp1 = QPushButton("Copy"); cp1.clicked.connect(lambda: self._copy(self.fix1.text()))
        h1.addWidget(cp1)
        v.addLayout(h1)

        v.addWidget(QLabel("<b>Fix #2: Assume 15th char is correct → single-character swap in first 14</b>"))
        self.fix2_table = QTableWidget(0, 3)
        self.fix2_table.setHorizontalHeaderLabels(["#", "Candidate GSTIN", "Copy"])
        self.fix2_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fix2_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        v.addWidget(self.fix2_table, 1)

        self.fix2_table.cellDoubleClicked.connect(self._copy_cell)

    def _copy(self, text):
        if not text:
            return
        QGuiApplication.clipboard().setText(text)
        QMessageBox.information(self, "Copied", f"Copied:\n{text}")

    def _copy_cell(self, r, c):
        if c == 2:
            item = self.fix2_table.item(r, 1)
            if item:
                self._copy(item.text())

    def validate(self):
        g = self.inp.text().strip().upper()
        self.inp.setText(g)
        st, msg = validate_gstin(g)
        if st == "OK":
            self.status.setText(f"✅ {msg}")
            self.status.setStyleSheet("color:#0a7a0a; font-size:14px; padding:6px;")
        else:
            self.status.setText(f"❌ {msg}")
            self.status.setStyleSheet("color:#a00; font-size:14px; padding:6px;")

        # Fix #1
        self.fix1.setText("")
        # Fix #2
        self.fix2_table.setRowCount(0)

        if len(g) != 15:
            return
        sug = suggest_gstin_corrections(g)
        if sug["fix_last_char"]:
            self.fix1.setText(sug["fix_last_char"])
        for i, cand in enumerate(sug["fix_one_of_14"], 1):
            r = self.fix2_table.rowCount()
            self.fix2_table.insertRow(r)
            self.fix2_table.setItem(r, 0, QTableWidgetItem(str(i)))
            self.fix2_table.setItem(r, 1, QTableWidgetItem(cand))
            btn = QPushButton("Copy")
            btn.clicked.connect(lambda _, c=cand: self._copy(c))
            self.fix2_table.setCellWidget(r, 2, btn)


class HSNSACWidget(QWidget):
    def __init__(self, engine: HSNSACSearch):
        super().__init__()
        self.engine = engine
        v = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("<b>HSN / SAC Search</b>"))
        self.kind = QComboBox(); self.kind.addItems(["Both", "HSN", "SAC"])
        top.addWidget(QLabel("Dataset:")); top.addWidget(self.kind)
        self.q = QLineEdit()
        self.q.setPlaceholderText("Type HSN/SAC code OR any keyword (e.g. 'rice', 'shampoo', 1006)")
        self.q.returnPressed.connect(self.search)
        top.addWidget(self.q, 1)
        b = QPushButton("Search"); b.clicked.connect(self.search); top.addWidget(b)
        lb = QPushButton("Load HSN/SAC Excel...")
        lb.clicked.connect(self.load_excel)
        top.addWidget(lb)
        v.addLayout(top)

        self.info = QLabel("")
        v.addWidget(self.info)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Dataset", "Code", "Description", "Score"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        v.addWidget(self.tbl, 1)

        self.tbl.itemSelectionChanged.connect(self._on_select)
        self.sel = QLineEdit(); self.sel.setReadOnly(True)
        h = QHBoxLayout(); h.addWidget(QLabel("Selected:")); h.addWidget(self.sel, 1)
        cpb = QPushButton("Copy Selected Code"); cpb.clicked.connect(self._copy_sel)
        h.addWidget(cpb)
        v.addLayout(h)

        self.update_info()

    def update_info(self):
        self.info.setText(f"Loaded: HSN={len(self.engine.hsn):,}  |  SAC={len(self.engine.sac):,}")

    def load_excel(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select HSN_SAC master excel", "", "Excel (*.xlsx *.xlsm)")
        if not f:
            return
        try:
            n_hsn, n_sac = self.engine.build_from_excel(f)
            self.update_info()
            QMessageBox.information(self, "Loaded",
                f"Loaded HSN rows: {n_hsn:,}\nLoaded SAC rows: {n_sac:,}\nCached to {self.engine.cache_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load:\n{e}")

    def search(self):
        q = self.q.text().strip()
        k = self.kind.currentText().lower()
        if not q:
            return
        res = self.engine.search(q, kind=k, limit=200)
        self.tbl.setRowCount(0)
        for lbl, code, desc, score in res:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(lbl))
            self.tbl.setItem(r, 1, QTableWidgetItem(code))
            self.tbl.setItem(r, 2, QTableWidgetItem(desc))
            self.tbl.setItem(r, 3, QTableWidgetItem(f"{score:.0f}"))

    def _on_select(self):
        items = self.tbl.selectedItems()
        if items:
            self.sel.setText(items[1].text() if len(items) > 1 else items[0].text())

    def _copy_sel(self):
        if self.sel.text():
            QGuiApplication.clipboard().setText(self.sel.text())
            QMessageBox.information(self, "Copied", self.sel.text())


class GSTR1Widget(QWidget):
    def __init__(self, hsn_engine):
        super().__init__()
        self.validator = GSTR1Validator(hsn_engine)
        self.data = None
        self.json_path = None
        self.issues = []

        v = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.load_btn = QPushButton("Load GSTR-1 JSON...")
        self.load_btn.clicked.connect(self.load_json)
        bar.addWidget(self.load_btn)
        self.scan_btn = QPushButton("Validate GSTIN & HSN")
        self.scan_btn.clicked.connect(self.scan)
        self.scan_btn.setEnabled(False)
        bar.addWidget(self.scan_btn)
        self.fix_btn = QPushButton("Apply Corrections & Export JSON")
        self.fix_btn.clicked.connect(self.apply_and_export)
        self.fix_btn.setEnabled(False)
        bar.addWidget(self.fix_btn)
        self.xls_btn = QPushButton("Export JSON → Excel")
        self.xls_btn.clicked.connect(self.export_excel)
        self.xls_btn.setEnabled(False)
        bar.addWidget(self.xls_btn)
        bar.addStretch(1)
        v.addLayout(bar)

        self.info = QLabel("No file loaded.")
        v.addWidget(self.info)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Type", "Path", "Current Value", "Issue"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        splitter.addWidget(self.tbl)

        # Correction panel
        gb = QGroupBox("Correction panel (select a row to edit)")
        g = QVBoxLayout(gb)
        row = QHBoxLayout()
        self.correction_input = QLineEdit()
        self.correction_input.setPlaceholderText("New GSTIN or HSN code")
        self.correction_input.setFont(QFont("Consolas", 11))
        row.addWidget(self.correction_input, 1)
        self.validate_btn = QPushButton("Validate & Stage")
        self.validate_btn.clicked.connect(self.stage_correction)
        row.addWidget(self.validate_btn)
        g.addLayout(row)
        self.sugg = QTextEdit(); self.sugg.setReadOnly(True); self.sugg.setMaximumHeight(120)
        g.addWidget(self.sugg)
        splitter.addWidget(gb)
        v.addWidget(splitter, 1)

        self.corrections = {}  # path -> new value
        self.tbl.itemSelectionChanged.connect(self.on_row_select)

    # ------------- actions -------------
    def load_json(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select GSTR-1 JSON", "", "JSON (*.json)")
        if not f:
            return
        try:
            with open(f, "r", encoding="utf-8") as fh:
                self.data = json.load(fh)
            self.json_path = f
            self.info.setText(f"Loaded: {os.path.basename(f)}   (GSTIN: {self.data.get('gstin','?')}, FP: {self.data.get('fp','?')})")
            self.scan_btn.setEnabled(True)
            self.xls_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def scan(self):
        if not self.data:
            return
        self.issues = self.validator.scan(self.data)
        self.tbl.setRowCount(0)
        for iss in self.issues:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, QTableWidgetItem(iss["type"]))
            self.tbl.setItem(r, 1, QTableWidgetItem(iss["path"]))
            self.tbl.setItem(r, 2, QTableWidgetItem(str(iss["value"])))
            self.tbl.setItem(r, 3, QTableWidgetItem(iss["message"]))
        self.info.setText(f"Issues found: {len(self.issues)}")
        self.fix_btn.setEnabled(len(self.issues) > 0)

    def on_row_select(self):
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() else []
        if not rows:
            return
        r = rows[0].row()
        iss = self.issues[r]
        txt = [f"Path: {iss['path']}", f"Current: {iss['value']}", f"Issue: {iss['message']}"]
        if iss["type"] == "GSTIN":
            sug = iss.get("suggestions") or {}
            if sug.get("fix_last_char"):
                txt.append(f"Suggestion (fix last char): {sug['fix_last_char']}")
            if sug.get("fix_one_of_14"):
                txt.append("Suggestion (fix one of first 14):")
                for s in sug["fix_one_of_14"][:15]:
                    txt.append(f"   {s}")
        elif iss["type"] == "HSN":
            txt.append("Possible replacements:")
            for c, d in iss.get("suggestions", [])[:15]:
                txt.append(f"   {c} - {d[:80]}")
        self.sugg.setPlainText("\n".join(txt))

    def stage_correction(self):
        rows = self.tbl.selectionModel().selectedRows() if self.tbl.selectionModel() else []
        if not rows:
            QMessageBox.warning(self, "Select", "Select a row first")
            return
        r = rows[0].row()
        iss = self.issues[r]
        new_val = self.correction_input.text().strip().upper()
        if not new_val:
            QMessageBox.warning(self, "Input", "Enter a replacement value")
            return
        if iss["type"] == "GSTIN":
            st, m = validate_gstin(new_val)
            if st != "OK":
                QMessageBox.warning(self, "Invalid GSTIN", f"'{new_val}' is not a valid GSTIN.\n{m}")
                return
        else:
            st, m = self.validator.hsn_status(new_val)
            if st != "OK":
                if QMessageBox.question(self, "Unknown HSN/SAC",
                    f"'{new_val}' is not in the HSN/SAC master.\n{m}\n\nAccept anyway?") != QMessageBox.StandardButton.Yes:
                    return
        self.corrections[iss["path"]] = new_val
        # reflect in table
        self.tbl.item(r, 3).setText(f"STAGED → {new_val}")
        self.correction_input.clear()

    def apply_and_export(self):
        if not self.data:
            return
        try:
            new_data = self.validator.apply_corrections(self.data, self.corrections)
            out, _ = QFileDialog.getSaveFileName(self, "Save corrected JSON",
                (self.json_path or "gstr1").replace(".json", "_corrected.json"),
                "JSON (*.json)")
            if not out:
                return
            with open(out, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "Saved", f"Corrected JSON saved to:\n{out}\n\nStaged corrections: {len(self.corrections)}")
            os.startfile(out) if hasattr(os, "startfile") else None
        except Exception as e:
            QMessageBox.critical(self, "Error", traceback.format_exc())

    def export_excel(self):
        if not self.data:
            return
        try:
            out, _ = QFileDialog.getSaveFileName(self, "Save Excel",
                (self.json_path or "gstr1").replace(".json", ".xlsx"),
                "Excel (*.xlsx)")
            if not out:
                return
            self.validator.to_excel(self.data, out)
            QMessageBox.information(self, "Saved", f"Excel saved to:\n{out}")
            if hasattr(os, "startfile"):
                os.startfile(out)
        except Exception as e:
            QMessageBox.critical(self, "Error", traceback.format_exc())


class ReconcileWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.books_path = None
        self.books_df = None
        self.twob_df = None
        self.recon = None

        v = QVBoxLayout(self)
        note = QLabel("<b>GSTR-2B vs Books Reconciliation</b> — <i>only the 'B2B' sheet of GSTR-2B is considered.</i>")
        note.setStyleSheet("padding:6px; background:#eef7ff; border:1px solid #b6d7ff;")
        v.addWidget(note)

        # Books group
        gb1 = QGroupBox("Step 1: Books / Purchase Register")
        g1 = QHBoxLayout(gb1)
        self.books_lbl = QLabel("No file selected.")
        g1.addWidget(self.books_lbl, 1)
        b1 = QPushButton("Select Books File")
        b1.clicked.connect(self.select_books)
        g1.addWidget(b1)
        b2 = QPushButton("Create Books Template")
        b2.clicked.connect(self.create_template)
        g1.addWidget(b2)
        v.addWidget(gb1)

        # 2B group
        gb2 = QGroupBox("Step 2: GSTR-2B file(s) — multiple allowed (merged on B2B sheet)")
        g2 = QHBoxLayout(gb2)
        self.twob_lbl = QLabel("No file selected.")
        g2.addWidget(self.twob_lbl, 1)
        b3 = QPushButton("Select Single 2B")
        b3.clicked.connect(self.select_2b_single)
        g2.addWidget(b3)
        b4 = QPushButton("Select Multiple 2B (merge)")
        b4.clicked.connect(self.select_2b_multi)
        g2.addWidget(b4)
        v.addWidget(gb2)

        # Tolerance + reconcile
        gb3 = QGroupBox("Step 3: Reconcile")
        g3 = QHBoxLayout(gb3)
        g3.addWidget(QLabel("Tax tolerance (₹):"))
        self.tol = QSpinBox(); self.tol.setRange(0, 10000); self.tol.setValue(1)
        g3.addWidget(self.tol)
        rb = QPushButton("Run Reconciliation")
        rb.clicked.connect(self.run_recon)
        g3.addWidget(rb)
        g3.addStretch(1)
        v.addWidget(gb3)

        # Summary table
        self.summary = QTableWidget(0, 2)
        self.summary.setHorizontalHeaderLabels(["Category", "Count"])
        self.summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.summary.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        v.addWidget(self.summary, 1)

        # Export
        gb4 = QGroupBox("Step 4: Export")
        g4 = QHBoxLayout(gb4)
        e1 = QPushButton("Export Excel"); e1.clicked.connect(lambda: self.export("excel"))
        e2 = QPushButton("Export Word"); e2.clicked.connect(lambda: self.export("word"))
        e3 = QPushButton("Export PDF"); e3.clicked.connect(lambda: self.export("pdf"))
        g4.addWidget(e1); g4.addWidget(e2); g4.addWidget(e3)
        g4.addStretch(1)
        v.addWidget(gb4)

    # ------------- actions -------------
    def select_books(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Books Excel", "", "Excel (*.xlsx *.xlsm *.xls)")
        if not f:
            return
        try:
            self.books_df = GSTR2BReconciler.read_books(f)
            self.books_path = f
            self.books_lbl.setText(f"{os.path.basename(f)}  ({len(self.books_df)} rows)")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def create_template(self):
        out, _ = QFileDialog.getSaveFileName(self, "Save Books template", "Books_GSTR2_Template.xlsx", "Excel (*.xlsx)")
        if not out:
            return
        try:
            GSTR2BReconciler.create_books_template(out)
            QMessageBox.information(self, "Created", f"Template saved:\n{out}")
            if hasattr(os, "startfile"):
                os.startfile(out)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def select_2b_single(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select GSTR-2B Excel", "", "Excel (*.xlsx *.xlsm *.xls)")
        if not f:
            return
        try:
            self.twob_df = GSTR2BReconciler.read_gstr2b_b2b(f)
            self.twob_lbl.setText(f"{os.path.basename(f)}  ({len(self.twob_df)} B2B rows)")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def select_2b_multi(self):
        fs, _ = QFileDialog.getOpenFileNames(self, "Select multiple GSTR-2B files", "", "Excel (*.xlsx *.xlsm *.xls)")
        if not fs:
            return
        try:
            self.twob_df = GSTR2BReconciler.merge_2b(fs)
            self.twob_lbl.setText(f"{len(fs)} files merged — {len(self.twob_df)} B2B rows total")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def run_recon(self):
        if self.books_df is None or self.twob_df is None:
            QMessageBox.warning(self, "Missing", "Please select Books and GSTR-2B files first.")
            return
        try:
            self.recon = GSTR2BReconciler.reconcile(self.books_df, self.twob_df, tol=float(self.tol.value()))
            data = [
                ("Matched", len(self.recon["matched"])),
                ("Amount Mismatch", len(self.recon["amount_mismatch"])),
                ("Only in Books", len(self.recon["only_in_books"])),
                ("Only in 2B", len(self.recon["only_in_2b"])),
                ("GSTIN Invalid (Books)", len(self.recon["gstin_invalid_books"])),
                ("GSTIN Invalid (2B)", len(self.recon["gstin_invalid_2b"])),
            ]
            self.summary.setRowCount(0)
            for k, v in data:
                r = self.summary.rowCount()
                self.summary.insertRow(r)
                self.summary.setItem(r, 0, QTableWidgetItem(k))
                self.summary.setItem(r, 1, QTableWidgetItem(str(v)))
            QMessageBox.information(self, "Done", "Reconciliation complete. You can now export.")
        except Exception:
            QMessageBox.critical(self, "Error", traceback.format_exc())

    def export(self, kind):
        if not self.recon:
            QMessageBox.warning(self, "Missing", "Run reconciliation first.")
            return
        if kind == "excel":
            out, _ = QFileDialog.getSaveFileName(self, "Save Excel", "Reconciliation.xlsx", "Excel (*.xlsx)")
            if out:
                GSTR2BReconciler.export_excel(self.recon, out)
        elif kind == "word":
            out, _ = QFileDialog.getSaveFileName(self, "Save Word", "Reconciliation.docx", "Word (*.docx)")
            if out:
                GSTR2BReconciler.export_word(self.recon, out)
        elif kind == "pdf":
            out, _ = QFileDialog.getSaveFileName(self, "Save PDF", "Reconciliation.pdf", "PDF (*.pdf)")
            if out:
                GSTR2BReconciler.export_pdf(self.recon, out)
        else:
            return
        if out:
            QMessageBox.information(self, "Saved", f"Saved to:\n{out}")
            if hasattr(os, "startfile"):
                os.startfile(out)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GST Toolkit for Chartered Accountants")
        self.resize(1280, 800)

        self.hsn_engine = HSNSACSearch(cache_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "hsn_cache.json"))

        tabs = QTabWidget()
        tabs.addTab(GSTINWidget(), "GSTIN Validator")
        tabs.addTab(HSNSACWidget(self.hsn_engine), "HSN / SAC Search")
        tabs.addTab(GSTR1Widget(self.hsn_engine), "GSTR-1 JSON Check")
        tabs.addTab(ReconcileWidget(), "GSTR-2B Reconciliation")
        self.setCentralWidget(tabs)

        # Menu
        mb = self.menuBar()
        h = mb.addMenu("Help")
        a = QAction("About", self)
        a.triggered.connect(self.about)
        h.addAction(a)

    def about(self):
        QMessageBox.information(self, "About GST Toolkit",
            "GST Toolkit for Chartered Accountants\n\n"
            "• Mod-36 GSTIN validator with reverse suggestions\n"
            "• HSN/SAC search (code <-> description)\n"
            "• GSTR-1 JSON validator, rectifier & Excel exporter\n"
            "• GSTR-2B (B2B only) vs Books reconciliation with multi-file merge\n\n"
            "Tip: Load the HSN/SAC master once from the HSN tab; it will be cached as hsn_cache.json.")


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont(APP_FONT, 10))
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
