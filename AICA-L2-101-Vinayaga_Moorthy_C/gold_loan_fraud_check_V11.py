#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 GOLD LOAN INTERNAL CONTROL AND FRAUD CONTROL CHECK
 Text analytics of Gold Loan Audit Incident Reports (.docx / .doc / .pdf)
===============================================================================
 HOW TO RUN (Windows, Python 3.12 or later):
     Double-click this file, or open Command Prompt and type:
         python gold_loan_fraud_check.py
     No installation needed - only Python's built-in (standard library)
     modules are used: tkinter for the window, plus zipfile / xml / zlib /
     re / csv etc. for reading Word & PDF files.

 WHAT CHANGED IN V1.1  (file reading only - the analytics are untouched)
   * Headings stacked in ONE table cell (Branch / Region / Area on three lines, with the three
     values on three lines of the next cell) are now split into separate columns.
   * Title line "Incident Report - 19-01-2026   10/2026" is split into Report Date and Report No
     (the date is no longer mistaken for the report number).
   * Also understood: heading row followed by a value row, "Branch / Region / Area" on one line,
     blank values inside stacked cells, Word 2003 XML saved as .doc, wrong file extensions.
   * If a file still reads poorly it is re-read through MS Word or LibreOffice (when installed)
     and the better reading is kept.  Files open in Word are read from a temporary copy.
   * Files are read in natural order (6, 10, 13, 256) and Word/LibreOffice lock files are skipped.
   * Check the reading without the window:
         python gold_loan_fraud_check.py --read-only "C:\\path\\to\\folder" result.csv

 WHAT IT DOES
   1. You browse and select a folder that holds the incident reports.
   2. Every Word (.docx, .docm, .doc) and PDF (.pdf) file is read.
   3. One row is created per file. Column 1 = file name, then one column per
      report heading (Branch, Region, Narration, What Happened ...).
      Headings with spelling / format differences are auto-corrected to a
      uniform column name (see "File Read Log" tab for every correction).
   4. Text analytics (rule-based NLP + TF-IDF / K-Means machine learning,
      all written in pure Python) is run from a gold-ornament-verification
      fraud-risk perspective.
   5. Results are shown in one window with tabs for the CFO and can be
      exported to CSV (opens in Excel) and to an HTML report.
===============================================================================
"""

import os
import re
import io
import sys
import csv
import math
import zlib
import html
import queue
import base64
import struct
import zipfile
import shutil
import random
import tempfile
import threading
import traceback
import subprocess
import webbrowser
import datetime as dt
from bisect import bisect_right
from collections import Counter, defaultdict, OrderedDict
from html.parser import HTMLParser
import xml.etree.ElementTree as ET

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import tkinter.font as tkfont
except Exception:  # tkinter missing only on very unusual installs
    tk = None

    class _NoTk:
        Frame = object
    ttk = _NoTk

APP_TITLE = "Gold Loan Internal Control and Fraud Control Check"
APP_VERSION = "1.3"
SUPPORTED_EXT = (".docx", ".docm", ".doc", ".pdf")

# =============================================================================
#  SECTION 1 - REPORT SCHEMA (uniform column names and the spellings accepted)
# =============================================================================
FIELD_SPECS = OrderedDict([
    ("Incident Report No", ["incident report", "incident report no", "incident report number",
                            "incident no", "incident number", "report no", "report number",
                            "ir no", "incident ref", "incident reference", "reference no", "ref no"]),
    ("Report Date", ["report date", "date of report", "reporting date", "date of reporting",
                     "reported on", "report dated"]),
    ("Branch", ["branch", "branch name", "branch code", "branch name code", "branch code name",
                "name of branch", "name of the branch", "branch details", "branch id"]),
    ("Region", ["region", "region name", "regional office", "zone", "zonal office"]),
    ("Area", ["area", "area name", "area office", "cluster", "division"]),
    ("Narration", ["narration", "narration of incident", "narration of the incident", "brief narration",
                   "brief", "summary", "incident summary", "brief description", "brief of incident"]),
    ("What Happened", ["what happened", "what has happened", "what had happened", "incident details",
                       "details of incident", "details of the incident", "description of incident",
                       "nature of incident", "incident description"]),
    ("How Discovered", ["how discovered", "how was it discovered", "how it was discovered",
                        "how detected", "how it was detected", "how identified", "mode of detection",
                        "detection", "discovery", "how the abnormality discovered",
                        "how abnormality discovered", "how the abnormality was discovered",
                        "method of detection"]),
    ("People Involved", ["people involved", "persons involved", "person involved", "staff involved",
                         "whether people involved", "whether staff involved", "involvement",
                         "people involvement", "accused", "persons responsible",
                         "whether any people involved", "individuals involved"]),
    ("Modus Operandi", ["modus operandi", "modus", "mode of operation", "method used",
                        "modus operendi", "modus oprandi"]),
    ("Since When", ["since when", "since", "period of incident", "incident period",
                    "since when it is happening", "date of commencement", "from when",
                    "period", "since what date"]),
    ("Financial Impact", ["financial impact", "financial loss", "financial implication",
                          "financial implications", "amount involved", "loss amount", "impact",
                          "amount of loss", "exposure", "loss", "financial exposure",
                          "amount at risk", "financial impact rs"]),
    ("Recovery", ["recovery", "recovery status", "amount recovered", "recovery made",
                  "status of recovery", "recovery position", "recovery details"]),
    ("Action Taken", ["action taken on incident", "action taken", "actions taken",
                      "action taken on the incident", "immediate action", "action initiated",
                      "action taken on incidents"]),
    ("Control Failures", ["control failures", "control failure", "control lapses", "control lapse",
                          "control gaps", "control gap", "control weakness", "control weaknesses",
                          "lapses", "process gaps", "process lapses", "control failures observed"]),
    ("Steps Taken to Tighten Control", ["steps taken to tighten control", "steps taken to tighten controls",
                                        "steps to tighten control", "steps to tighten controls",
                                        "steps taken to strengthen control", "steps taken to strengthen controls",
                                        "corrective action", "corrective actions", "preventive action",
                                        "preventive actions", "preventive measures", "control tightening",
                                        "remedial measures", "remedial action", "remedial actions",
                                        "steps taken to tighten the control"]),
    ("Any Other Observation", ["any other observation", "any other observations", "other observation",
                               "other observations", "other remarks", "remarks", "additional observation",
                               "additional observations", "observation", "observations", "comments",
                               "any other remarks"]),
    ("Date Observed", ["date observed", "date of observation", "date of detection", "observed on",
                       "date of incident observed", "date of incident", "incident date", "detected on",
                       "date of identification", "date incident observed", "observation date"]),
])
GENERIC_DATE_LABELS = ["date", "dated", "dt"]
FIELD_NAMES = list(FIELD_SPECS.keys())
SHORT_FIELDS = {"Incident Report No", "Report Date", "Branch", "Region", "Area", "Since When", "Date Observed"}
CORE_FIELDS = {"Narration", "What Happened", "How Discovered", "People Involved", "Modus Operandi",
               "Since When", "Financial Impact", "Recovery", "Action Taken", "Control Failures",
               "Steps Taken to Tighten Control", "Any Other Observation"}
KEY_FIELDS_FOR_QUALITY = ["Branch", "Region", "Narration", "What Happened", "How Discovered",
                          "People Involved", "Modus Operandi", "Since When", "Financial Impact",
                          "Recovery", "Action Taken", "Control Failures", "Steps Taken to Tighten Control",
                          "Date Observed"]
FILLER_WORDS = {"the", "of", "in", "rs", "inr", "details", "detail", "if", "any", "whether", "s",
                "on", "for", "a", "an", "is", "was", "to", "be", "by", "amount", "in rs"}


def norm_label(s):
    s = (s or "").replace("\xa0", " ").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def strip_fillers(n):
    return " ".join(w for w in n.split() if w not in FILLER_WORDS)


LABEL_INDEX = {}
for _canon, _syns in FIELD_SPECS.items():
    LABEL_INDEX[norm_label(_canon)] = _canon
    for _s in _syns:
        LABEL_INDEX[norm_label(_s)] = _canon
for _s in GENERIC_DATE_LABELS:
    LABEL_INDEX[_s] = "_DATE"
LABEL_INDEX2 = {}
for _k, _v in LABEL_INDEX.items():
    _k2 = strip_fillers(_k)
    if _k2 and _k2 not in LABEL_INDEX2:
        LABEL_INDEX2[_k2] = _v
CAUTIOUS_SINGLE = {"impact", "loss", "period", "exposure", "detection", "discovery", "involvement", "summary",
                   "brief", "remarks", "comments", "observation", "observations", "lapses", "accused", "modus"}
PREFIX_SYNS = sorted([k for k in LABEL_INDEX if len(k.split()) >= 2 or len(k) >= 6],
                     key=lambda x: -len(x))

NUM_PREFIX = re.compile(r"^\s*(?:[\(\[]?\s*(?:\d{1,2}|[a-hA-H]|[ivxIVX]{1,4})\s*[\)\]\.:\-]\s*|\d{1,2}\s+(?=[A-Za-z]))")
MARKER_LOOSE = re.compile(r"^\s*[\(\[]?\s*(?:\d{1,2}|[a-zA-Z]|[ivxIVX]{1,4})\s*[\)\]\.:]?\s*$")
MARKER_STRICT = re.compile(r"^\s*(?:[\(\[]\s*(?:\d{1,2}|[a-zA-Z]|[ivxIVX]{1,4})\s*[\)\]]|(?:\d{1,2}|[a-zA-Z]|[ivxIVX]{1,4})\s*[\)\.])\s*$")
PLACEHOLDER_RE = re.compile(r"^[\sxX\.\-_/\\()\[\],:;*#]*$")


def is_marker(s, loose=False):
    s = (s or "").strip()
    if not s:
        return True
    if s in ("-", "--", ":", "•", "*", "–", "—"):
        return True
    return bool((MARKER_LOOSE if loose else MARKER_STRICT).match(s))


def is_placeholder(s):
    """True when a value carries no information (blank, 'xxxx', '(a)', '-')."""
    s = (s or "").strip()
    if not s:
        return True
    s2 = re.sub(r"\(\s*[a-zA-Z0-9]{1,3}\s*\)", " ", s)
    s2 = re.sub(r"\b(?:rs|inr|nil|na|n/a)\b\.?", " ", s2, flags=re.I)
    return bool(PLACEHOLDER_RE.match(s2))


def osa_distance(a, b):
    """Optimal-string-alignment edit distance (handles typos and swapped letters)."""
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev2 = None
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                v = min(v, prev2[j - 2] + 1)
            cur[j] = v
        prev2, prev = prev, cur
    return prev[lb]


def match_label(raw, strict=False, allow_prefix=True):
    """Return (canonical_field, method) if the text is a report heading, else (None, None)."""
    t = (raw or "").replace("\xa0", " ").strip()
    t = t.strip(":-–—#*•|").strip()
    t = NUM_PREFIX.sub("", t, count=1).strip().strip(":-–—#*").strip()
    n = norm_label(t)
    if not n or len(n) > 60 or len(n.split()) > 9:
        return None, None
    if n in LABEL_INDEX:
        return LABEL_INDEX[n], "exact"
    n2 = strip_fillers(n)
    if n2 and n2 in LABEL_INDEX2:
        return LABEL_INDEX2[n2], "normalised"
    best = None
    for cand in (n, n2):
        if not cand:
            continue
        for syn, canon in LABEL_INDEX.items():
            L = len(syn)
            if L < 4 or syn[0] != cand[0]:
                continue
            if abs(len(cand) - L) > max(2, L // 4):
                continue
            thr = 1 if L <= 8 else (2 if L <= 14 else 3)
            if strict:
                thr = min(thr, 1 if L <= 10 else 2)
            d = osa_distance(cand, syn)
            if d <= thr and (best is None or d < best[0]):
                best = (d, canon)
    if best:
        return best[1], "spelling corrected"
    if allow_prefix and not strict:
        for syn in PREFIX_SYNS:
            if n.startswith(syn + " ") and len(n.split()) - len(syn.split()) <= 3:
                canon = LABEL_INDEX[syn]
                if canon != "_DATE":
                    return canon, "prefix match"
    return None, None


def _build_inline_regex():
    pats = []
    for syn in sorted(LABEL_INDEX.keys(), key=lambda x: -len(x)):
        if len(syn) < 4 and syn not in ("date",):
            continue
        words = syn.split()
        pats.append(r"[\s\-_.]*".join(re.escape(w) for w in words))
    return re.compile(r"(?i)(?<![A-Za-z0-9])(" + "|".join(pats) + r")\s*(?:#|no\.?|number)?\s*[:：#]")


INLINE_LABEL_RE = _build_inline_regex()


def looks_like_label(s):
    s = (s or "").strip().rstrip(":").strip()
    if not (2 <= len(s) <= 45):
        return False
    if len(s.split()) > 6 or not s[0].isalpha() or s.endswith("."):
        return False
    if re.search(r"\d{3,}", s) or is_placeholder(s):
        return False
    digits = sum(ch.isdigit() for ch in s)
    return digits <= len(s) * 0.2


def split_label_text(text, allow_prefix=False):
    """Detect heading(s) in a line of text.
    Returns list of (canonical, raw_label, method, value) or None."""
    if not text or not text.strip():
        return None
    line = text.strip()
    first_line = line.split("\n")[0].strip()
    rest_lines = "\n".join(line.split("\n")[1:])
    # 1) whole first line is a heading
    if len(first_line) <= 70:
        c, m = match_label(first_line, allow_prefix=False)
        if c:
            return [(c, first_line, m, rest_lines)]
    # 2) one or more "Label: value" pairs
    found = list(INLINE_LABEL_RE.finditer(first_line))
    if found:
        lead = NUM_PREFIX.sub("", first_line[:found[0].start()], count=1).strip(" \t-*•|")
        if not lead:
            segs = []
            for i, mt in enumerate(found):
                end = found[i + 1].start() if i + 1 < len(found) else len(first_line)
                val = first_line[mt.end():end].strip(" \t|;,")
                segs.append((mt.group(1), val))
            long_vals = any(len(v) > 70 for _, v in segs[:-1])
            if long_vals:
                mt = found[0]
                segs = [(mt.group(1), first_line[mt.end():].strip())]
            out = []
            for raw, val in segs:
                c, m = match_label(raw, allow_prefix=False)
                if c:
                    out.append((c, raw, m, val))
            if out:
                last = out[-1]
                out[-1] = (last[0], last[1], last[2], (last[3] + ("\n" + rest_lines if rest_lines else "")).strip())
                return out
    # 2b) "Incident Report No. 257/2026" (no colon)
    mrep = re.match(r"^\s*(incident\s*report\s*(?:no\.?|number|#)?|report\s*no\.?|ir\s*no\.?)\s*[:#\-.]?\s*([A-Za-z]{0,6}[\s\-/]?\d[\w/\-]*)\s*(.*)$", first_line, re.I)
    if mrep:
        out = [("Incident Report No", mrep.group(1).strip(), "pattern match", mrep.group(2).strip())]
        tail = mrep.group(3).strip()
        if tail:
            more = split_label_text(tail)
            if more:
                out.extend(more)
        return out
    # 3) "Label : value" / "Label - value" / "Label<TAB>value" with a mis-spelt label
    mt = re.match(r"^(.{2,55}?)\s*(?::|：|\t| - | – | — )\s*(.*)$", first_line)
    if mt:
        c, m = match_label(mt.group(1), allow_prefix=False)
        if c:
            val = (mt.group(2) + ("\n" + rest_lines if rest_lines else "")).strip()
            return [(c, mt.group(1).strip(), m, val)]
    # 4) PDF lines: "Label value" written on the same line without separator
    if allow_prefix:
        n_line = first_line.lower()
        for syn in PREFIX_SYNS:
            words = syn.split()
            pat = r"^\s*(?:[\(\[]?\s*(?:\d{1,2}|[a-h])\s*[\)\]\.]\s*)?" + r"[\s\-_.]*".join(re.escape(w) for w in words) + r"\b[\s:\-–]*"
            mm = re.match(pat, n_line)
            if mm and len(words) == 1:
                canon0 = LABEL_INDEX[syn]
                tail_words = len(first_line[mm.end():].split())
                if (canon0 in SHORT_FIELDS or canon0 == "_DATE" or syn in CAUTIOUS_SINGLE) and tail_words > 4:
                    mm = None
            if mm:
                canon = LABEL_INDEX[syn]
                val = (first_line[mm.end():] + ("\n" + rest_lines if rest_lines else "")).strip()
                return [(canon, first_line[:mm.end()].strip(" :-–"), "prefix match", val)]
    return None


def clean_value(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\r", "\n")
    lines = []
    for ln in text.split("\n"):
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if not ln or is_marker(ln, loose=False) or ln in ("(a)", "(b)", "(c)"):
            continue
        lines.append(ln)
    return "\n".join(lines).strip()

# =============================================================================
#  SECTION 2 - FILE READERS  (pure standard library)
#  Each reader returns a list of "rows":  {"kind": "p"|"t", "cells": [...]}
#  "p" = free paragraph, "t" = table row (list of cell texts, in order)
# =============================================================================
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC_NS = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
CHECKED_SYMS = {"F0FE", "F0FD", "F078", "F0FC", "F0FB", "F052", "F054", "F053", "F0D6", "2612", "2611", "2714", "2713"}
UNCHECKED_SYMS = {"F0A8", "F06F", "F0A3", "F071", "F072", "F0A1", "F0A2", "2610", "F030", "F0A4"}
CHECKED_GLYPHS = "☒☑✔✓■▣\uf0fe\uf0fd\uf078\uf0fc"
UNCHECKED_GLYPHS = "☐□▢\uf0a8\uf06f\uf0a3"


def _glyph_fix(s):
    for g in CHECKED_GLYPHS:
        s = s.replace(g, "[X] ")
    for g in UNCHECKED_GLYPHS:
        s = s.replace(g, "[ ] ")
    return s


def _raw_value(text):
    """Like clean_value() but keeps blank lines in place (marker lines such as '(a)' become blank).
    Used to line up stacked headings with their values."""
    text = (text or "").replace("\xa0", " ").replace("\u200b", "").replace("\r", "\n")
    lines = []
    for ln in text.split("\n"):
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        lines.append("" if is_marker(ln) else ln)
    return "\n".join(lines).strip("\n")


def _row(kind, cells, **kw):
    d = {"kind": kind, "cells": cells}
    d.update(kw)
    return d


def _para_rows_from_text(text, kind="p"):
    """Convert a plain paragraph to row(s); tab-separated paragraphs become table-like rows."""
    text = _glyph_fix(text.replace("\xa0", " "))
    if not text.strip():
        return []
    if "\t" in text.strip():
        cells = [c.strip() for c in re.split(r"\t+", text.strip())]
        cells = [c for c in cells if c]
        if len(cells) >= 2:
            return [_row("t", cells, src="tab")]
    return [_row(kind, [text.strip()])]


# ----------------------------------------------------------------------------- DOCX
def _docx_ptext(el, out):
    for c in el:
        tag = c.tag
        if tag == W_NS + "t":
            out.append(c.text or "")
        elif tag == W_NS + "tab":
            out.append("\t")
        elif tag in (W_NS + "br", W_NS + "cr"):
            out.append("\n")
        elif tag == W_NS + "noBreakHyphen":
            out.append("-")
        elif tag == W_NS + "sym":
            ch = (c.get(W_NS + "char") or "").upper()
            if ch in CHECKED_SYMS:
                out.append("[X] ")
            elif ch in UNCHECKED_SYMS:
                out.append("[ ] ")
            else:
                out.append(" ")
        elif tag == W_NS + "checkBox":
            val = None
            for sub in c:
                if sub.tag in (W_NS + "checked", W_NS + "default"):
                    v = sub.get(W_NS + "val")
                    v = True if v is None else v in ("1", "true", "on")
                    if sub.tag == W_NS + "checked" or val is None:
                        val = v
            out.append("[X] " if val else "[ ] ")
        elif tag in (MC_NS + "Fallback", W_NS + "instrText", W_NS + "delText", W_NS + "del",
                     W_NS + "rPr", W_NS + "pPr", W_NS + "fldData"):
            continue
        else:
            _docx_ptext(c, out)


def _docx_para_text(p):
    out = []
    _docx_ptext(p, out)
    return _glyph_fix("".join(out))


def _docx_cell_text(tc, nested_rows, keep_blank=False):
    """Text of a table cell.  keep_blank=True keeps empty lines in place (needed to line up the
    values of stacked headings such as Branch / Region / Area when one of them is blank)."""
    lines = []
    for ch in tc:
        if ch.tag == W_NS + "p":
            t = _docx_para_text(ch).replace("\t", " ")
            if keep_blank:
                lines.extend(("" if is_marker(x) else x.strip()) for x in t.split("\n"))
            elif t.strip():
                lines.append(t.strip())
        elif ch.tag == W_NS + "tbl":
            _docx_table(ch, nested_rows)
        elif ch.tag in (W_NS + "sdt", W_NS + "customXml"):
            content = ch.find(W_NS + "sdtContent") if ch.tag == W_NS + "sdt" else ch
            if content is not None:
                lines.append(_docx_cell_text(content, nested_rows, keep_blank))
    if keep_blank:
        return "\n".join(lines).strip("\n")
    return "\n".join(l for l in lines if l)


def _docx_table(tbl, rows):
    trs = []
    for ch in tbl:
        if ch.tag == W_NS + "tr":
            trs.append(ch)
        elif ch.tag == W_NS + "sdt":
            sc = ch.find(W_NS + "sdtContent")
            if sc is not None:
                trs.extend(x for x in sc if x.tag == W_NS + "tr")
    for tr in trs:
        tcs = []
        for ch in tr:
            if ch.tag == W_NS + "tc":
                tcs.append(ch)
            elif ch.tag in (W_NS + "sdt", W_NS + "customXml"):
                sc = ch.find(W_NS + "sdtContent") if ch.tag == W_NS + "sdt" else ch
                if sc is not None:
                    tcs.extend(x for x in sc if x.tag == W_NS + "tc")
        cells, raws, nested = [], [], []
        for tc in tcs:
            vm = tc.find(W_NS + "tcPr/" + W_NS + "vMerge")
            cont = vm is not None and (vm.get(W_NS + "val") in (None, "continue"))
            txt = _docx_cell_text(tc, nested)
            raw = _docx_cell_text(tc, [], True)
            cells.append("" if cont else txt)
            raws.append("" if cont else raw)
        if any(c.strip() for c in cells):
            rows.append(_row("t", cells, raw=raws))
        rows.extend(nested)


def _docx_block(el, rows):
    for ch in el:
        tag = ch.tag
        if tag == W_NS + "p":
            rows.extend(_para_rows_from_text(_docx_para_text(ch)))
        elif tag == W_NS + "tbl":
            _docx_table(ch, rows)
        elif tag == W_NS + "sdt":
            sc = ch.find(W_NS + "sdtContent")
            if sc is not None:
                _docx_block(sc, rows)
        elif tag in (W_NS + "customXml", W_NS + "ins", W_NS + "smartTag"):
            _docx_block(ch, rows)
        elif tag == MC_NS + "AlternateContent":
            choice = ch.find(MC_NS + "Choice")
            if choice is not None:
                _docx_block(choice, rows)


def read_docx(path):
    rows = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        main = "word/document.xml"
        if main not in names:
            cands = [n for n in names if re.match(r"word/document\d*\.xml$", n)]
            if not cands:
                raise ValueError("Not a valid Word document (document.xml missing)")
            main = cands[0]
        headers = sorted(n for n in names if re.match(r"word/header\d*\.xml$", n))
        seen = set()
        for h in headers:
            try:
                hroot = ET.fromstring(z.read(h))
                hrows = []
                _docx_block(hroot, hrows)
                for r in hrows:
                    key = "|".join(r["cells"])
                    if key not in seen:
                        seen.add(key)
                        r["src"] = "header"
                        rows.append(r)
            except Exception:
                pass
        root = ET.fromstring(z.read(main))
        body = root.find(W_NS + "body")
        if body is None:
            body = root
        _docx_block(body, rows)
    return rows


# ----------------------------------------------------------------------------- DOC (Word 97-2003)
class CompoundFile:
    """Minimal OLE2 / Compound File Binary reader."""
    SIG = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"

    def __init__(self, data):
        if data[:8] != self.SIG:
            raise ValueError("Not an OLE2 compound file")
        self.data = data
        u16 = lambda o: struct.unpack_from("<H", data, o)[0]
        u32 = lambda o: struct.unpack_from("<I", data, o)[0]
        self.ss = 1 << u16(0x1E)
        self.mss = 1 << u16(0x20)
        nfat = u32(0x2C)
        dir_start = u32(0x30)
        self.cutoff = u32(0x38)
        minifat_start = u32(0x3C)
        difat_start = u32(0x44)
        ndifat = u32(0x48)
        difat = list(struct.unpack_from("<109I", data, 0x4C))
        sec, guard = difat_start, 0
        per = self.ss // 4
        while sec < 0xFFFFFFFA and ndifat > 0 and guard < 10000:
            off = (sec + 1) * self.ss
            if off + self.ss > len(data):
                break
            vals = struct.unpack_from("<%dI" % per, data, off)
            difat.extend(vals[:-1])
            sec = vals[-1]
            ndifat -= 1
            guard += 1
        fat = []
        for s in difat[:nfat]:
            if s >= 0xFFFFFFFA:
                continue
            off = (s + 1) * self.ss
            if off + self.ss <= len(data):
                fat.extend(struct.unpack_from("<%dI" % per, data, off))
        self.fat = fat
        dir_data = self._chain(dir_start)
        self.entries = []
        for i in range(len(dir_data) // 128):
            e = dir_data[i * 128:(i + 1) * 128]
            nlen = struct.unpack_from("<H", e, 0x40)[0]
            name = e[:max(0, min(64, nlen) - 2)].decode("utf-16-le", "ignore")
            typ = e[0x42]
            start = struct.unpack_from("<I", e, 0x74)[0]
            size = struct.unpack_from("<I", e, 0x78)[0]
            self.entries.append((name, typ, start, size))
        if not self.entries:
            raise ValueError("Empty compound file directory")
        root = self.entries[0]
        self.ministream = self._chain(root[2])[:root[3]]
        mf = self._chain(minifat_start) if minifat_start < 0xFFFFFFFA else b""
        self.minifat = list(struct.unpack_from("<%dI" % (len(mf) // 4), mf, 0)) if mf else []

    def _chain(self, start):
        out, sec, seen = [], start, set()
        while sec < 0xFFFFFFFA and sec < len(self.fat) + 1 and sec not in seen:
            seen.add(sec)
            off = (sec + 1) * self.ss
            out.append(self.data[off:off + self.ss])
            if sec >= len(self.fat):
                break
            sec = self.fat[sec]
        return b"".join(out)

    def _minichain(self, start, size):
        out, sec, seen = [], start, set()
        while sec < 0xFFFFFFFA and sec not in seen and sec < len(self.minifat) + 1:
            seen.add(sec)
            off = sec * self.mss
            out.append(self.ministream[off:off + self.mss])
            if sec >= len(self.minifat):
                break
            sec = self.minifat[sec]
        return b"".join(out)[:size]

    def stream(self, name):
        for (n, typ, start, size) in self.entries:
            if typ == 2 and n.lower() == name.lower():
                if size < self.cutoff:
                    return self._minichain(start, size)
                return self._chain(start)[:size]
        return None


def _sprm_props(g):
    props = {"intable": False, "ttp": False, "itap": 0, "inner_cell": False, "inner_ttp": False}
    i, n = 0, len(g)
    while i + 2 <= n:
        op = struct.unpack_from("<H", g, i)[0]
        i += 2
        spra = op >> 13
        if spra in (0, 1):
            sz = 1
        elif spra in (2, 4, 5):
            sz = 2
        elif spra == 3:
            sz = 4
        elif spra == 7:
            sz = 3
        else:
            if i >= n:
                break
            if op == 0xD608:
                if i + 2 > n:
                    break
                sz = struct.unpack_from("<H", g, i)[0] - 1
                i += 2
            elif op == 0xC615:
                cb = g[i]
                if cb == 255:
                    break
                i += 1
                sz = cb
            else:
                sz = g[i]
                i += 1
        val = g[i:i + sz]
        if op == 0x2416 and val:
            props["intable"] = val[0] != 0
        elif op == 0x2417 and val:
            props["ttp"] = val[0] != 0
        elif op == 0x6649 and len(val) >= 4:
            props["itap"] = struct.unpack_from("<I", val, 0)[0]
        elif op == 0x244B and val:
            props["inner_cell"] = val[0] != 0
        elif op == 0x244C and val:
            props["inner_ttp"] = val[0] != 0
        i += sz
    return props


def read_doc_binary(data):
    cfb = CompoundFile(data)
    wd = cfb.stream("WordDocument")
    if not wd:
        raise ValueError("WordDocument stream not found")
    ident = struct.unpack_from("<H", wd, 0)[0]
    if ident != 0xA5EC:
        raise ValueError("Unsupported (pre-Word-97) .doc format")
    flags = struct.unpack_from("<H", wd, 0x0A)[0]
    if flags & 0x0100:
        raise ValueError("Document is password protected / encrypted")
    table = cfb.stream("1Table" if flags & 0x0200 else "0Table")
    if not table:
        raise ValueError("Table stream not found")
    pos = 32
    csw = struct.unpack_from("<H", wd, pos)[0]
    pos += 2 + csw * 2
    cslw = struct.unpack_from("<H", wd, pos)[0]
    lw = pos + 2
    ccp = [struct.unpack_from("<i", wd, lw + 4 * k)[0] for k in range(min(cslw, 12))]
    ccp_text = ccp[3] if len(ccp) > 3 else None
    ccp_ftn = ccp[4] if len(ccp) > 4 else 0
    ccp_hdd = ccp[5] if len(ccp) > 5 else 0
    pos += 2 + cslw * 4
    pos += 2
    fcl = pos

    def fl(k):
        return struct.unpack_from("<II", wd, fcl + k * 8)

    fc_clx, lcb_clx = fl(33)
    fc_pap, lcb_pap = fl(13)
    clx = table[fc_clx:fc_clx + lcb_clx]
    i, pieces = 0, []
    while i < len(clx):
        t = clx[i]
        if t == 1:
            cb = struct.unpack_from("<h", clx, i + 1)[0]
            i += 3 + cb
        elif t == 2:
            lcb = struct.unpack_from("<I", clx, i + 1)[0]
            plc = clx[i + 5:i + 5 + lcb]
            npcd = (lcb - 4) // 12
            cps = struct.unpack_from("<%di" % (npcd + 1), plc, 0)
            for k in range(npcd):
                fcv = struct.unpack_from("<I", plc, (npcd + 1) * 4 + k * 8 + 2)[0]
                comp = bool(fcv & 0x40000000)
                fcb = (fcv & 0x3FFFFFFF) // 2 if comp else (fcv & 0x3FFFFFFF)
                pieces.append((cps[k], cps[k + 1], fcb, comp))
            break
        else:
            break
    if not pieces:
        raise ValueError("Piece table not found")
    chars, fcs = [], []
    for cp0, cp1, fcb, comp in pieces:
        n = cp1 - cp0
        if n <= 0:
            continue
        if comp:
            raw = wd[fcb:fcb + n]
            txt = raw.decode("cp1252", "replace")
            for k, ch in enumerate(txt):
                chars.append(ch)
                fcs.append(fcb + k)
        else:
            raw = wd[fcb:fcb + 2 * n]
            txt = raw.decode("utf-16-le", "replace")
            for k, ch in enumerate(txt):
                chars.append(ch)
                fcs.append(fcb + 2 * k)
    # paragraph properties (to know table cell / row ends)
    paps = []
    try:
        plc = table[fc_pap:fc_pap + lcb_pap]
        n = (len(plc) - 4) // 8
        for k in range(n):
            pn = struct.unpack_from("<I", plc, 4 * (n + 1) + 4 * k)[0] & 0x3FFFFF
            fkp = wd[pn * 512:(pn + 1) * 512]
            if len(fkp) < 512:
                continue
            crun = fkp[511]
            rgfc = struct.unpack_from("<%dI" % (crun + 1), fkp, 0)
            for r in range(crun):
                boff = fkp[4 * (crun + 1) + 13 * r] * 2
                props = {"intable": False, "ttp": False, "itap": 0}
                if boff:
                    cb = fkp[boff]
                    if cb == 0:
                        cb2 = fkp[boff + 1]
                        st, size = boff + 2, 2 * cb2
                    else:
                        st, size = boff + 1, 2 * cb - 1
                    props = _sprm_props(fkp[st + 2:st + size])
                paps.append((rgfc[r], rgfc[r + 1], props))
        paps.sort(key=lambda x: x[0])
    except Exception:
        paps = []
    pap_starts = [p[0] for p in paps]

    def props_at(fc):
        if not paps:
            return None
        j = bisect_right(pap_starts, fc) - 1
        if 0 <= j < len(paps) and paps[j][0] <= fc < paps[j][1]:
            return paps[j][2]
        return None

    def build(c0, c1):
        rows, cells, raws, buf = [], [], [], []
        field_stack = []
        prev7 = False
        for cp in range(c0, min(c1, len(chars))):
            ch = chars[cp]
            o = ord(ch)
            if o == 0x13:
                field_stack.append({"code": [], "res": False})
                continue
            if o == 0x14:
                if field_stack:
                    field_stack[-1]["res"] = True
                    code = "".join(field_stack[-1]["code"]).upper()
                    if "FORMCHECKBOX" in code:
                        buf.append("[?] ")
                continue
            if o == 0x15:
                if field_stack:
                    fsd = field_stack.pop()
                    code = "".join(fsd["code"]).upper()
                    if not fsd["res"] and "FORMCHECKBOX" in code:
                        buf.append("[?] ")
                continue
            if field_stack and not field_stack[-1]["res"]:
                field_stack[-1]["code"].append(ch)
                continue
            if ch == "\x07":
                pr = props_at(fcs[cp])
                if pr is not None:
                    is_row_end = pr.get("ttp")
                else:
                    is_row_end = prev7 and not "".join(buf).strip()
                if is_row_end:
                    if any(c.strip() for c in cells):
                        rows.append(_row("t", [_glyph_fix(c) for c in cells], raw=[_glyph_fix(c) for c in raws]))
                    cells, raws, buf = [], [], []
                else:
                    cells.append(clean_value("".join(buf)))
                    raws.append(_raw_value("".join(buf)))
                    buf = []
                prev7 = True
                continue
            prev7 = False
            if ch in "\r\x0c":
                pr = props_at(fcs[cp])
                in_tbl = bool(pr and (pr.get("intable") or pr.get("itap", 0) >= 1))
                if pr is None:
                    in_tbl = bool(cells)
                if in_tbl:
                    buf.append("\n")
                else:
                    rows.extend(_para_rows_from_text("".join(buf)))
                    buf = []
                continue
            if ch == "\x0b":
                buf.append("\n")
            elif ch == "\t":
                buf.append("\t")
            elif ch in "\x1e":
                buf.append("-")
            elif ch == "\xa0":
                buf.append(" ")
            elif o < 0x20 or ch in "\x1f":
                continue
            else:
                buf.append(ch)
        if buf and "".join(buf).strip():
            rows.extend(_para_rows_from_text("".join(buf)))
        if cells:
            rows.append(_row("t", cells, raw=raws))
        return rows

    main_end = ccp_text if (ccp_text and 0 < ccp_text <= len(chars)) else len(chars)
    rows = build(0, main_end)
    if ccp_hdd and ccp_hdd > 0:
        h0 = main_end + max(0, ccp_ftn)
        hrows = build(h0, h0 + ccp_hdd)
        hrows = [r for r in hrows if r["kind"] == "p" and re.search(r"report|incident|#|date", r["cells"][0], re.I)]
        for r in hrows:
            r["src"] = "header"
        rows = hrows + rows
    return rows


def read_rtf(data):
    """Simple RTF reader (some '.doc' files are really RTF)."""
    text = data.decode("latin-1", "ignore")
    rows, cells, buf = [], [], []
    stack = []
    skip = False
    uc = 1
    in_tbl = False
    skip_dest = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "object", "themedata",
                 "colorschememapping", "datastore", "latentstyles", "listtable", "listoverridetable",
                 "rsidtbl", "generator", "xmlnstbl", "mmathpr", "filetbl", "revtbl", "header",
                 "footer", "headerl", "headerr", "footerl", "footerr", "fldinst", "bkmkstart", "bkmkend",
                 "pgdsctbl", "listpicture", "wgrffmtfilter", "nonshppict", "shppict"}
    i, n = 0, len(text)
    pending_skip_unicode = 0
    while i < n:
        c = text[i]
        if c == "{":
            stack.append((skip, uc))
            i += 1
            continue
        if c == "}":
            if stack:
                skip, uc = stack.pop()
            i += 1
            continue
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+)(-?\d+)? ?", text[i:])
            if m:
                word, arg = m.group(1), m.group(2)
                i += m.end()
                if word in skip_dest:
                    skip = True
                    continue
                if skip:
                    continue
                if word == "uc" and arg:
                    uc = int(arg)
                elif word == "u" and arg:
                    v = int(arg)
                    if v < 0:
                        v += 65536
                    buf.append(chr(v))
                    pending_skip_unicode = uc
                    while pending_skip_unicode > 0 and i < n:
                        if text[i] == "\\" and text[i + 1:i + 2] == "'":
                            i += 4
                        elif text[i] in "{}":
                            break
                        else:
                            i += 1
                        pending_skip_unicode -= 1
                elif word in ("par", "sect"):
                    if in_tbl:
                        buf.append("\n")
                    else:
                        rows.extend(_para_rows_from_text("".join(buf)))
                        buf = []
                elif word in ("line",):
                    buf.append("\n")
                elif word == "tab":
                    buf.append("\t")
                elif word == "intbl":
                    in_tbl = True
                elif word == "pard":
                    in_tbl = False
                elif word in ("cell",):
                    cells.append(clean_value("".join(buf)))
                    buf = []
                elif word in ("nestcell",):
                    buf.append("\n")
                elif word == "row":
                    if any(x.strip() for x in cells):
                        rows.append(_row("t", [_glyph_fix(x) for x in cells]))
                    cells, buf = [], []
                    in_tbl = False
                elif word in ("emdash",):
                    buf.append("—")
                elif word in ("endash",):
                    buf.append("–")
                elif word in ("bullet",):
                    buf.append("•")
                elif word in ("lquote", "rquote"):
                    buf.append("'")
                elif word in ("ldblquote", "rdblquote"):
                    buf.append('"')
                continue
            nxt = text[i + 1:i + 2]
            if nxt == "'":
                if not skip:
                    try:
                        buf.append(bytes([int(text[i + 2:i + 4], 16)]).decode("cp1252", "replace"))
                    except Exception:
                        pass
                i += 4
                continue
            if nxt == "*":
                skip = True
                i += 2
                continue
            if nxt in "\\{}":
                if not skip:
                    buf.append(nxt)
                i += 2
                continue
            if nxt == "~":
                buf.append(" ")
            i += 2
            continue
        if c in "\r\n":
            i += 1
            continue
        if not skip:
            buf.append(c)
        i += 1
    if "".join(buf).strip():
        rows.extend(_para_rows_from_text("".join(buf)))
    return rows


class _HTMLRows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.cells, self.buf = [], None, []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "title"):
            self.skip += 1
        elif tag == "tr":
            self.cells = []
            self.buf = []
        elif tag in ("td", "th"):
            self.buf = []
        elif tag == "br":
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "title"):
            self.skip = max(0, self.skip - 1)
        elif tag in ("td", "th"):
            if self.cells is not None:
                self.cells.append(clean_value("".join(self.buf)))
                self.buf = []
        elif tag == "tr":
            if self.cells and any(c.strip() for c in self.cells):
                self.rows.append(_row("t", self.cells))
            self.cells, self.buf = None, []
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "li"):
            if self.cells is None:
                self.rows.extend(_para_rows_from_text("".join(self.buf)))
                self.buf = []
            else:
                self.buf.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data.replace("\r", " ").replace("\n", " "))


def read_html_doc(data):
    if data[:200].lstrip().upper().startswith(b"MIME-VERSION"):
        import email
        msg = email.message_from_bytes(data)
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                data = part.get_payload(decode=True) or b""
                break
    txt = data.decode("utf-8", "ignore")
    if "\ufffd" in txt[:2000]:
        txt = data.decode("cp1252", "ignore")
    p = _HTMLRows()
    p.feed(txt)
    if "".join(p.buf).strip():
        p.rows.extend(_para_rows_from_text("".join(p.buf)))
    return p.rows


def read_wordml_xml(data):
    """Word 2003 XML (WordprocessingML) or a flat-OPC Word file that was saved with a .doc / .xml name."""
    root = ET.fromstring(data)

    def ln(t):
        return t.rsplit("}", 1)[-1] if isinstance(t, str) else ""

    def ptext(p):
        out = []
        for el in p.iter():
            n = ln(el.tag)
            if n == "t":
                out.append(el.text or "")
            elif n == "tab":
                out.append("\t")
            elif n in ("br", "cr"):
                out.append("\n")
        return _glyph_fix("".join(out))

    rows = []

    def table(tbl):
        for tr in tbl:
            if ln(tr.tag) != "tr":
                continue
            cells, raws = [], []
            for tc in tr:
                if ln(tc.tag) != "tc":
                    continue
                paras = [ptext(p).replace("\t", " ") for p in tc if ln(p.tag) == "p"]
                cells.append(clean_value("\n".join(paras)))
                raws.append(_raw_value("\n".join(paras)))
            if any(c.strip() for c in cells):
                rows.append(_row("t", cells, raw=raws))

    def walk(el):
        for ch in el:
            n = ln(ch.tag)
            if n == "p":
                rows.extend(_para_rows_from_text(ptext(ch)))
            elif n == "tbl":
                table(ch)
            else:
                walk(ch)

    walk(root)
    return rows


def read_doc(path):
    """Read any Word-type file by looking at what is INSIDE it (the extension is often wrong)."""
    with open(path, "rb") as f:
        data = f.read()
    if not data:
        raise ValueError("File is empty (0 bytes)")
    head = data[:16]
    if head.startswith(b"PK"):
        try:
            return read_docx(path), "DOCX (saved as .doc)"
        except zipfile.BadZipFile:
            raise ValueError("File is damaged (not a valid Word/zip file)")
    if head.startswith(b"{\\rtf"):
        return read_rtf(data), "RTF (saved as .doc)"
    if head.startswith(CompoundFile.SIG):
        return read_doc_binary(data), "Word 97-2003 DOC"
    low = data[:2000].lower()
    if (b"<w:worddocument" in low or b"<w:document" in low or b"urn:schemas-microsoft-com:office:word" in low
            or b"schemas.microsoft.com/office/2006/xmlpackage" in low):
        return read_wordml_xml(data), "Word XML (saved as .doc)"
    if b"<html" in low or b"mime-version" in low or b"<!doctype" in low:
        return read_html_doc(data), "HTML/MHT (saved as .doc)"
    raise ValueError("Unrecognised .doc format")


# ----------------------------------------------------------------------------- PDF
class PDFName(str):
    pass


class PDFKeyword(str):
    pass


class PDFRef:
    __slots__ = ("num", "gen")

    def __init__(self, num, gen):
        self.num, self.gen = num, gen


class PDFStream:
    __slots__ = ("dict", "raw", "_dec")

    def __init__(self, d, raw):
        self.dict, self.raw, self._dec = d, raw, None


PDF_WS = b" \t\r\n\x0c\x00"
PDF_DELIM = b"()<>[]{}/%"
_REGULAR_END = set(PDF_WS + PDF_DELIM)
_NUM_RE = re.compile(rb"^[+-]?(?:\d+\.?\d*|\.\d+)$")
_INT_RE = re.compile(rb"\d+")


def _pdf_skip(d, i):
    n = len(d)
    while i < n:
        c = d[i]
        if c in PDF_WS:
            i += 1
        elif c == 37:
            while i < n and d[i] not in (10, 13):
                i += 1
        else:
            break
    return i


def _pdf_parse(d, i, refs=True, depth=0):
    i = _pdf_skip(d, i)
    n = len(d)
    if i >= n:
        raise EOFError
    c = d[i]
    if depth > 60:
        raise ValueError("too deep")
    if c == 60:  # <
        if i + 1 < n and d[i + 1] == 60:
            i += 2
            res = {}
            while True:
                i = _pdf_skip(d, i)
                if i >= n:
                    return res, i
                if d[i] == 62 and i + 1 < n and d[i + 1] == 62:
                    return res, i + 2
                k, i = _pdf_parse(d, i, refs, depth + 1)
                v, i = _pdf_parse(d, i, refs, depth + 1)
                if isinstance(k, str):
                    res[str(k)] = v
        j = d.find(b">", i)
        if j < 0:
            j = n
        hx = re.sub(rb"[^0-9A-Fa-f]", b"", d[i + 1:j])
        if len(hx) % 2:
            hx += b"0"
        return bytes.fromhex(hx.decode()), j + 1
    if c == 91:  # [
        i += 1
        arr = []
        while True:
            i = _pdf_skip(d, i)
            if i >= n:
                return arr, i
            if d[i] == 93:
                return arr, i + 1
            v, i = _pdf_parse(d, i, refs, depth + 1)
            arr.append(v)
    if c == 40:  # (
        i += 1
        depth_p, out = 1, bytearray()
        while i < n:
            ch = d[i]
            if ch == 92:
                i += 1
                if i >= n:
                    break
                e = d[i]
                mp = {110: 10, 114: 13, 116: 9, 98: 8, 102: 12, 40: 40, 41: 41, 92: 92}
                if e in mp:
                    out.append(mp[e])
                elif 48 <= e <= 55:
                    o = d[i:i + 3]
                    m = re.match(rb"[0-7]{1,3}", o)
                    out.append(int(m.group(0), 8) & 0xFF)
                    i += len(m.group(0)) - 1
                elif e == 13:
                    if i + 1 < n and d[i + 1] == 10:
                        i += 1
                elif e == 10:
                    pass
                else:
                    out.append(e)
            elif ch == 40:
                depth_p += 1
                out.append(ch)
            elif ch == 41:
                depth_p -= 1
                if depth_p == 0:
                    return bytes(out), i + 1
                out.append(ch)
            else:
                out.append(ch)
            i += 1
        return bytes(out), i
    if c == 47:  # /
        j = i + 1
        while j < n and d[j] not in _REGULAR_END:
            j += 1
        raw = d[i + 1:j]
        raw = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), raw)
        return PDFName(raw.decode("latin-1")), j
    if c in (41, 62, 93, 123, 125):
        return PDFKeyword(chr(c)), i + 1
    j = i
    while j < n and d[j] not in _REGULAR_END:
        j += 1
    tok = d[i:j]
    if not tok:
        return PDFKeyword(chr(c)), i + 1
    if _NUM_RE.match(tok):
        if refs and _INT_RE.fullmatch(tok):
            k = _pdf_skip(d, j)
            m = _INT_RE.match(d, k)
            if m:
                k2 = _pdf_skip(d, m.end())
                if k2 < n and d[k2] == 82 and (k2 + 1 >= n or d[k2 + 1] in _REGULAR_END):
                    return PDFRef(int(tok), int(m.group(0))), k2 + 1
        try:
            return (float(tok) if (b"." in tok) else int(tok)), j
        except ValueError:
            return 0, j
    if tok == b"true":
        return True, j
    if tok == b"false":
        return False, j
    if tok == b"null":
        return None, j
    return PDFKeyword(tok.decode("latin-1")), j


def _lzw_decode(data):
    out = bytearray()
    table = [bytes([i]) for i in range(256)] + [None, None]
    bits, buf, nbits, prev = 9, 0, 0, None
    for byte in data:
        buf = (buf << 8) | byte
        nbits += 8
        while nbits >= bits:
            code = (buf >> (nbits - bits)) & ((1 << bits) - 1)
            nbits -= bits
            if code == 256:
                table = table[:258]
                bits, prev = 9, None
                continue
            if code == 257:
                return bytes(out)
            if prev is None:
                entry = table[code]
            elif code < len(table) and table[code] is not None:
                entry = table[code]
                table.append(prev + entry[:1])
            else:
                entry = prev + prev[:1]
                table.append(entry)
            out += entry
            prev = entry
            if len(table) >= (1 << bits) - 1 and bits < 12:
                bits += 1
    return bytes(out)


def _inflate(data):
    try:
        return zlib.decompress(data)
    except Exception:
        pass
    for wb in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
        try:
            d = zlib.decompressobj(wb)
            return d.decompress(data)
        except Exception:
            continue
    return b""


GLYPH_NAMES = {
    "space": " ", "exclam": "!", "quotedbl": '"', "numbersign": "#", "dollar": "$", "percent": "%",
    "ampersand": "&", "quotesingle": "'", "parenleft": "(", "parenright": ")", "asterisk": "*",
    "plus": "+", "comma": ",", "hyphen": "-", "minus": "-", "period": ".", "slash": "/", "colon": ":",
    "semicolon": ";", "less": "<", "equal": "=", "greater": ">", "question": "?", "at": "@",
    "bracketleft": "[", "backslash": "\\", "bracketright": "]", "asciicircum": "^", "underscore": "_",
    "grave": "`", "braceleft": "{", "bar": "|", "braceright": "}", "asciitilde": "~",
    "quoteright": "'", "quoteleft": "'", "quotedblleft": '"', "quotedblright": '"', "endash": "–",
    "emdash": "—", "bullet": "•", "fi": "fi", "fl": "fl", "nbspace": " ", "sfthyphen": "-",
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "rupee": "₹", "ellipsis": "...", "degree": "°",
}


def _glyph_to_char(name):
    if name in GLYPH_NAMES:
        return GLYPH_NAMES[name]
    if len(name) == 1:
        return name
    m = re.match(r"^uni([0-9A-Fa-f]{4})", name)
    if m:
        return chr(int(m.group(1), 16))
    m = re.match(r"^u([0-9A-Fa-f]{4,6})$", name)
    if m:
        return chr(int(m.group(1), 16))
    base = name.split(".")[0]
    if base != name:
        return _glyph_to_char(base)
    return ""


class PDFFont:
    def __init__(self, reader, fdict):
        self.r = reader
        fdict = fdict if isinstance(fdict, dict) else {}
        self.subtype = str(reader.res(fdict.get("Subtype")) or "")
        self.two_byte = self.subtype == "Type0"
        self.cmap = {}
        self.code_len = 2 if self.two_byte else 1
        self.widths = {}
        self.default_w = 500.0
        self.enc = {}
        tu = reader.res(fdict.get("ToUnicode"))
        if isinstance(tu, PDFStream):
            try:
                self._parse_cmap(reader.decode(tu) or b"")
            except Exception:
                pass
        if self.two_byte:
            try:
                desc = reader.res(fdict.get("DescendantFonts"))
                desc = reader.res(desc[0]) if isinstance(desc, list) and desc else {}
                self.default_w = float(reader.res(desc.get("DW", 1000)) or 1000)
                w = reader.res(desc.get("W")) or []
                k = 0
                while k < len(w):
                    first = reader.res(w[k])
                    nxt = reader.res(w[k + 1]) if k + 1 < len(w) else None
                    if isinstance(nxt, list):
                        for off, val in enumerate(nxt):
                            self.widths[int(first) + off] = float(reader.res(val) or 0)
                        k += 2
                    else:
                        last = nxt
                        val = float(reader.res(w[k + 2]) or 0) if k + 2 < len(w) else 0
                        if isinstance(first, (int, float)) and isinstance(last, (int, float)) and last - first < 70000:
                            for code in range(int(first), int(last) + 1):
                                self.widths[code] = val
                        k += 3
            except Exception:
                pass
        else:
            try:
                fc = int(reader.res(fdict.get("FirstChar", 0)) or 0)
                ws = reader.res(fdict.get("Widths")) or []
                for off, val in enumerate(ws):
                    self.widths[fc + off] = float(reader.res(val) or 0)
                fd = reader.res(fdict.get("FontDescriptor"))
                if isinstance(fd, dict) and "MissingWidth" in fd:
                    self.default_w = float(reader.res(fd.get("MissingWidth")) or 500) or 500.0
            except Exception:
                pass
            enc = reader.res(fdict.get("Encoding"))
            base = "WinAnsiEncoding"
            diffs = []
            if isinstance(enc, str):
                base = str(enc)
            elif isinstance(enc, dict):
                base = str(reader.res(enc.get("BaseEncoding")) or "WinAnsiEncoding")
                diffs = reader.res(enc.get("Differences")) or []
            codec = "mac_roman" if "Mac" in base else "cp1252"
            for code in range(256):
                try:
                    self.enc[code] = bytes([code]).decode(codec)
                except Exception:
                    self.enc[code] = ""
            cur = 0
            for item in diffs:
                item = reader.res(item)
                if isinstance(item, (int, float)):
                    cur = int(item)
                elif isinstance(item, str):
                    ch = _glyph_to_char(str(item))
                    if ch or cur not in self.enc:
                        self.enc[cur] = ch
                    cur += 1

    def _parse_cmap(self, s):
        lens = set()
        for blk in re.findall(rb"begincodespacerange(.*?)endcodespacerange", s, re.S):
            for a, b in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
                lens.add(len(a) // 2)
        if len(lens) == 1:
            self.code_len = lens.pop()

        def dst_str(h):
            h = re.sub(rb"\s", b"", h)
            if len(h) % 2:
                h += b"0"
            try:
                return bytes.fromhex(h.decode()).decode("utf-16-be", "ignore")
            except Exception:
                return ""

        for blk in re.findall(rb"beginbfchar(.*?)endbfchar", s, re.S):
            for a, b in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f\s]*)>", blk):
                self.cmap[int(a, 16)] = dst_str(b)
        for blk in re.findall(rb"beginbfrange(.*?)endbfrange", s, re.S):
            for a, b, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f\s]*>|\[[^\]]*\])", blk):
                lo, hi = int(a, 16), int(b, 16)
                if hi - lo > 65535 or hi < lo:
                    continue
                if dst.startswith(b"<"):
                    h = re.sub(rb"[\s<>]", b"", dst)
                    if len(h) % 2:
                        h += b"0"
                    base = int(h, 16) if h else 0
                    blen = max(2, len(h) // 2)
                    for code in range(lo, hi + 1):
                        try:
                            self.cmap[code] = (base + code - lo).to_bytes(blen, "big").decode("utf-16-be", "ignore")
                        except Exception:
                            pass
                else:
                    items = re.findall(rb"<([0-9A-Fa-f\s]*)>", dst)
                    for off, h in enumerate(items):
                        self.cmap[lo + off] = dst_str(h)

    def decode(self, b):
        out = []
        cl = self.code_len if self.code_len in (1, 2, 3, 4) else (2 if self.two_byte else 1)
        k = 0
        while k < len(b):
            code = int.from_bytes(b[k:k + cl], "big")
            k += cl
            if code in self.cmap:
                ch = self.cmap[code]
            elif self.two_byte:
                ch = chr(code) if 32 <= code < 0xD800 and not self.cmap else ""
            else:
                ch = self.enc.get(code, chr(code) if code < 256 else "")
            w = self.widths.get(code, self.default_w) / 1000.0
            out.append((ch, w, cl == 1 and code == 32))
        return out


class PDFReader:
    def __init__(self, data):
        self.data = data
        self.objs = {}
        self.font_cache = {}
        self.encrypted = False
        self._scan()

    def _scan(self):
        d = self.data
        pending = []
        skip_until = -1
        for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj\b", d):
            if m.start() < skip_until:
                continue
            num = int(m.group(1))
            try:
                val, j = _pdf_parse(d, m.end())
            except Exception:
                continue
            k = _pdf_skip(d, j)
            if isinstance(val, dict) and d.startswith(b"stream", k):
                k += 6
                if d[k:k + 2] == b"\r\n":
                    k += 2
                elif d[k:k + 1] in (b"\n", b"\r"):
                    k += 1
                e = d.find(b"endstream", k)
                if e < 0:
                    e = len(d)
                skip_until = e
                pending.append((num, val, k, e))
            else:
                self.objs[num] = val
        for num, dct, k, e in pending:
            length = dct.get("Length")
            if isinstance(length, PDFRef):
                length = self.objs.get(length.num)
            raw = None
            if isinstance(length, int) and 0 <= length and k + length <= len(d):
                tail = d[k + length:k + length + 32]
                if b"endstream" in tail:
                    raw = d[k:k + length]
            if raw is None:
                raw = d[k:e].rstrip(b"\r\n")
            self.objs[num] = PDFStream(dct, raw)
        for num, obj in list(self.objs.items()):
            if isinstance(obj, PDFStream) and str(obj.dict.get("Type")) == "ObjStm":
                try:
                    dec = self.decode(obj) or b""
                    nobj = int(self.res(obj.dict.get("N")))
                    first = int(self.res(obj.dict.get("First")))
                    nums = [int(x) for x in re.findall(rb"\d+", dec[:first])]
                    for q in range(min(nobj, len(nums) // 2)):
                        onum, off = nums[2 * q], nums[2 * q + 1]
                        try:
                            v, _ = _pdf_parse(dec, first + off)
                            self.objs.setdefault(onum, v)
                        except Exception:
                            pass
                except Exception:
                    pass
        self.trailers = []
        for m in re.finditer(rb"trailer", d):
            try:
                v, _ = _pdf_parse(d, m.end())
                if isinstance(v, dict):
                    self.trailers.append(v)
            except Exception:
                pass
        for obj in self.objs.values():
            if isinstance(obj, PDFStream) and str(obj.dict.get("Type")) == "XRef":
                self.trailers.append(obj.dict)
        self.encrypted = any("Encrypt" in t for t in self.trailers)

    def res(self, v, depth=0):
        while isinstance(v, PDFRef) and depth < 20:
            v = self.objs.get(v.num)
            depth += 1
        return v

    def decode(self, s):
        if s._dec is not None:
            return s._dec
        filt = self.res(s.dict.get("Filter"))
        filters = filt if isinstance(filt, list) else ([filt] if filt else [])
        data = s.raw
        for f in filters:
            f = str(self.res(f))
            if f in ("FlateDecode", "Fl"):
                data = _inflate(data)
            elif f in ("ASCIIHexDecode", "AHx"):
                hx = re.sub(rb"[^0-9A-Fa-f]", b"", data.split(b">")[0])
                if len(hx) % 2:
                    hx += b"0"
                data = bytes.fromhex(hx.decode())
            elif f in ("ASCII85Decode", "A85"):
                t = data.strip()
                if t.startswith(b"<~"):
                    t = t[2:]
                t = t.split(b"~>")[0]
                try:
                    data = base64.a85decode(re.sub(rb"\s", b"", t))
                except Exception:
                    data = b""
            elif f in ("LZWDecode", "LZW"):
                data = _lzw_decode(data)
            elif f in ("RunLengthDecode", "RL"):
                out, k = bytearray(), 0
                while k < len(data):
                    L = data[k]
                    if L == 128:
                        break
                    if L < 128:
                        out += data[k + 1:k + 2 + L]
                        k += L + 2
                    else:
                        out += data[k + 1:k + 2] * (257 - L)
                        k += 2
                data = bytes(out)
            else:
                data = b""
                break
        s._dec = data
        return data

    def pages(self):
        root = None
        for t in self.trailers:
            if "Root" in t:
                root = self.res(t["Root"])
                if isinstance(root, dict):
                    break
        if not isinstance(root, dict):
            for o in self.objs.values():
                if isinstance(o, dict) and str(o.get("Type")) == "Catalog":
                    root = o
                    break
        out, seen = [], set()

        def walk(node, inh, depth=0):
            if depth > 50 or not isinstance(node, dict) or id(node) in seen:
                return
            seen.add(id(node))
            resources = self.res(node.get("Resources")) or inh
            kids = self.res(node.get("Kids"))
            if isinstance(kids, list):
                for k in kids:
                    walk(self.res(k), resources, depth + 1)
            elif str(node.get("Type")) == "Page" or "Contents" in node:
                out.append((node, resources))

        if isinstance(root, dict):
            walk(self.res(root.get("Pages")), {})
        if not out:
            nums = sorted(k for k, o in self.objs.items() if isinstance(o, dict) and str(o.get("Type")) == "Page")
            out = [(self.objs[k], self.res(self.objs[k].get("Resources")) or {}) for k in nums]
        return out

    def get_font(self, ref_or_dict):
        key = ref_or_dict.num if isinstance(ref_or_dict, PDFRef) else id(ref_or_dict)
        if key not in self.font_cache:
            self.font_cache[key] = PDFFont(self, self.res(ref_or_dict))
        return self.font_cache[key]


def _mmul(m1, m2):
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2, c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)


def _pdf_run(reader, content, resources, ctm, chunks, depth=0, rules=None):
    if depth > 8:
        return
    if rules is None:
        rules = {"h": [], "v": []}
    cur_pt = [0.0, 0.0]

    def tp(x, y):
        a, b, c, d, e, f = ctm
        return (x * a + y * c + e, x * b + y * d + f)

    def seg(p1, p2):
        (x1, y1), (x2, y2) = p1, p2
        if abs(y1 - y2) < 1.0 and abs(x1 - x2) > 4:
            rules["h"].append((y1, min(x1, x2), max(x1, x2)))
        elif abs(x1 - x2) < 1.0 and abs(y1 - y2) > 4:
            rules["v"].append((x1, min(y1, y2), max(y1, y2)))
    resources = reader.res(resources) or {}
    fonts = reader.res(resources.get("Font")) or {}
    xobjs = reader.res(resources.get("XObject")) or {}
    I = (1, 0, 0, 1, 0, 0)
    gstack = []
    Tm = Tlm = I
    Tc = Tw = 0.0
    Th = 1.0
    TL = 0.0
    rise = 0.0
    fs = 10.0
    font = None
    stack = []
    i, n = 0, len(content)

    def num(v, dflt=0.0):
        return float(v) if isinstance(v, (int, float)) else dflt

    def show(items):
        nonlocal Tm
        if font is None:
            return
        trm = _mmul((fs * Th, 0, 0, fs, 0, rise), _mmul(Tm, ctm))
        x0, y0 = trm[4], trm[5]
        size = math.hypot(trm[2], trm[3]) or fs
        text = []
        for it in items:
            if isinstance(it, (int, float)):
                tx = -it / 1000.0 * fs * Th
                Tm = _mmul((1, 0, 0, 1, tx, 0), Tm)
                if -it > 180 and text and not text[-1].endswith(" "):
                    text.append(" ")
                continue
            for ch, w, is_space in font.decode(it):
                text.append(ch)
                tx = (w * fs + Tc + (Tw if is_space else 0)) * Th
                Tm = _mmul((1, 0, 0, 1, tx, 0), Tm)
        trm2 = _mmul((fs * Th, 0, 0, fs, 0, rise), _mmul(Tm, ctm))
        s = "".join(text)
        if s:
            chunks.append({"x": x0, "y": y0, "x2": trm2[4], "size": size, "text": s})

    while i < n:
        i = _pdf_skip(content, i)
        if i >= n:
            break
        try:
            tok, i = _pdf_parse(content, i, refs=False)
        except Exception:
            i += 1
            continue
        if not isinstance(tok, PDFKeyword):
            stack.append(tok)
            if len(stack) > 200:
                stack = stack[-50:]
            continue
        op = str(tok)
        try:
            if op == "q":
                gstack.append(ctm)
            elif op == "Q":
                if gstack:
                    ctm = gstack.pop()
            elif op == "cm" and len(stack) >= 6:
                ctm = _mmul(tuple(num(v) for v in stack[-6:]), ctm)
            elif op == "BT":
                Tm = Tlm = I
            elif op == "Tf" and len(stack) >= 2:
                fs = num(stack[-1], 10.0)
                fref = fonts.get(str(stack[-2])) if isinstance(fonts, dict) else None
                font = reader.get_font(fref) if fref is not None else None
            elif op == "Tc" and stack:
                Tc = num(stack[-1])
            elif op == "Tw" and stack:
                Tw = num(stack[-1])
            elif op == "Tz" and stack:
                Th = num(stack[-1], 100.0) / 100.0
            elif op == "TL" and stack:
                TL = num(stack[-1])
            elif op == "Ts" and stack:
                rise = num(stack[-1])
            elif op in ("Td", "TD") and len(stack) >= 2:
                tx, ty = num(stack[-2]), num(stack[-1])
                if op == "TD":
                    TL = -ty
                Tlm = _mmul((1, 0, 0, 1, tx, ty), Tlm)
                Tm = Tlm
            elif op == "Tm" and len(stack) >= 6:
                Tlm = Tm = tuple(num(v) for v in stack[-6:])
            elif op == "T*":
                Tlm = _mmul((1, 0, 0, 1, 0, -TL), Tlm)
                Tm = Tlm
            elif op == "Tj" and stack and isinstance(stack[-1], bytes):
                show([stack[-1]])
            elif op == "TJ" and stack and isinstance(stack[-1], list):
                show([x for x in stack[-1] if isinstance(x, (bytes, int, float))])
            elif op == "'" and stack:
                Tlm = _mmul((1, 0, 0, 1, 0, -TL), Tlm)
                Tm = Tlm
                if isinstance(stack[-1], bytes):
                    show([stack[-1]])
            elif op == '"' and len(stack) >= 3:
                Tw, Tc = num(stack[-3]), num(stack[-2])
                Tlm = _mmul((1, 0, 0, 1, 0, -TL), Tlm)
                Tm = Tlm
                if isinstance(stack[-1], bytes):
                    show([stack[-1]])
            elif op == "Do" and stack and isinstance(xobjs, dict):
                xo = reader.res(xobjs.get(str(stack[-1])))
                if isinstance(xo, PDFStream) and str(xo.dict.get("Subtype")) == "Form":
                    mtx = reader.res(xo.dict.get("Matrix")) or [1, 0, 0, 1, 0, 0]
                    m2 = _mmul(tuple(num(reader.res(v)) for v in mtx[:6]), ctm)
                    _pdf_run(reader, reader.decode(xo) or b"", xo.dict.get("Resources") or resources,
                             m2, chunks, depth + 1, rules)
            elif op == "m" and len(stack) >= 2:
                cur_pt[:] = [num(stack[-2]), num(stack[-1])]
            elif op == "l" and len(stack) >= 2:
                nx, ny = num(stack[-2]), num(stack[-1])
                seg(tp(cur_pt[0], cur_pt[1]), tp(nx, ny))
                cur_pt[:] = [nx, ny]
            elif op == "re" and len(stack) >= 4:
                x, y, w, h = (num(v) for v in stack[-4:])
                p1, p2, p3, p4 = tp(x, y), tp(x + w, y), tp(x + w, y + h), tp(x, y + h)
                if abs(p1[1] - p4[1]) < 2.5 and abs(p1[0] - p2[0]) > 4:
                    rules["h"].append(((p1[1] + p4[1]) / 2, min(p1[0], p2[0]), max(p1[0], p2[0])))
                elif abs(p1[0] - p2[0]) < 2.5 and abs(p1[1] - p4[1]) > 4:
                    rules["v"].append(((p1[0] + p2[0]) / 2, min(p1[1], p4[1]), max(p1[1], p4[1])))
                else:
                    seg(p1, p2)
                    seg(p4, p3)
                    seg(p1, p4)
                    seg(p2, p3)
            elif op == "BI":
                e = content.find(b"ID", i)
                if e >= 0:
                    m = re.search(rb"\sEI(?:\s|$)", content[e + 2:])
                    i = e + 2 + (m.end() if m else len(content))
        except Exception:
            pass
        stack = []


def _join_items(items):
    items = sorted(items, key=lambda c: c["x"])
    parts, prev = [], None
    for c in items:
        if prev is not None:
            gap = c["x"] - prev["x2"]
            sz = max(prev["size"], c["size"], 1.0)
            if gap > 1.4 * sz:
                parts.append("\t")
            elif gap > 0.12 * sz and parts and not parts[-1].endswith(" ") and not c["text"].startswith(" "):
                parts.append(" ")
        parts.append(c["text"])
        prev = c
    return _glyph_fix("".join(parts))


def _merge_close(vals, tol):
    out = []
    for v in sorted(vals):
        if out and abs(v - out[-1]) <= tol:
            continue
        out.append(v)
    return out


def _pdf_layout(chunks, rules=None):
    chunks = [c for c in chunks if c["text"].strip()]
    if not chunks:
        return []
    chunks.sort(key=lambda c: (-round(c["y"], 1), c["x"]))
    lines = []
    for c in chunks:
        tol = max(1.5, 0.35 * c["size"])
        if lines and abs(lines[-1]["y"] - c["y"]) <= tol:
            lines[-1]["items"].append(c)
        else:
            lines.append({"y": c["y"], "items": [c]})
    rules = rules or {"h": [], "v": []}
    hys = _merge_close([h[0] for h in rules["h"]], 1.5)
    hys.sort(reverse=True)
    bands = []
    for k in range(len(hys) - 1):
        top, bot = hys[k], hys[k + 1]
        if top - bot < 4:
            continue
        mid = (top + bot) / 2.0
        xs = _merge_close([v[0] for v in rules["v"] if v[1] - 1.5 <= mid <= v[2] + 1.5], 2.0)
        if len(xs) >= 2:
            bands.append((top, bot, xs))
    rows = []
    used = set()
    band_of_line = {}
    for li, ln in enumerate(lines):
        for bi, (top, bot, xs) in enumerate(bands):
            if bot < ln["y"] < top:
                band_of_line[li] = bi
                break
    emitted_band = set()
    for li, ln in enumerate(lines):
        bi = band_of_line.get(li)
        if bi is not None:
            if bi in emitted_band:
                continue
            emitted_band.add(bi)
            top, bot, xs = bands[bi]
            ncol = len(xs) - 1
            cols = [[] for _ in range(max(1, ncol))]
            for lj, ln2 in enumerate(lines):
                if band_of_line.get(lj) != bi:
                    continue
                per = defaultdict(list)
                for c in ln2["items"]:
                    ci = bisect_right(xs, c["x"] + 0.5) - 1
                    ci = min(max(ci, 0), len(cols) - 1)
                    per[ci].append(c)
                for ci, its in per.items():
                    cols[ci].append(_join_items(its).replace("\t", " "))
            cells = ["\n".join(x.strip() for x in col if x.strip()) for col in cols]
            if any(cells):
                rows.append(_row("t", cells, src="pdf"))
            continue
        txt = _join_items(ln["items"])
        if "\t" in txt.strip():
            cells = [x.strip() for x in txt.split("\t") if x.strip()]
            if len(cells) >= 2:
                rows.append(_row("t", cells, src="pdf"))
                continue
        if txt.strip():
            rows.append(_row("p", [txt.strip()], prefix=True, src="pdf"))
    return rows


def read_pdf(path):
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"%PDF") and b"%PDF" not in data[:1024]:
        raise ValueError("Not a PDF file")
    rd = PDFReader(data)
    if rd.encrypted:
        raise ValueError("PDF is encrypted / password protected")
    rows = []
    for page, resources in rd.pages():
        contents = rd.res(page.get("Contents"))
        streams = contents if isinstance(contents, list) else [contents]
        buf = b""
        for s in streams:
            s = rd.res(s)
            if isinstance(s, PDFStream):
                buf += (rd.decode(s) or b"") + b"\n"
        chunks = []
        rules = {"h": [], "v": []}
        _pdf_run(rd, buf, resources, (1, 0, 0, 1, 0, 0), chunks, 0, rules)
        rows.extend(_pdf_layout(chunks, rules))
    return rows


# ----------------------------------------------------------------------------- Office converters (fallback)
def find_libreoffice():
    for name in ("soffice", "libreoffice", "soffice.exe"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
              "/usr/bin/soffice", "/usr/local/bin/soffice",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if os.path.exists(p):
            return p
    return None


def word_convert_to_docx(path, timeout=150):
    """Use the installed Microsoft Word (if any) to convert .doc/.pdf to .docx. Windows only."""
    if os.name != "nt":
        return None
    out_dir = tempfile.mkdtemp(prefix="glfc_")
    dst = os.path.join(out_dir, "converted.docx")
    src = os.path.abspath(path).replace("'", "''")
    dsts = dst.replace("'", "''")
    ps = ("$ErrorActionPreference='Stop';"
          "$w=New-Object -ComObject Word.Application;$w.Visible=$false;$w.DisplayAlerts=0;"
          "try{$d=$w.Documents.Open('%s',$false,$true,$false);$d.SaveAs2('%s',16);$d.Close($false)}"
          "finally{$w.Quit()}" % (src, dsts))
    try:
        flags = 0x08000000 if os.name == "nt" else 0
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-Command", ps], timeout=timeout, capture_output=True, creationflags=flags)
    except Exception:
        pass
    if os.path.exists(dst):
        return dst
    shutil.rmtree(out_dir, ignore_errors=True)
    return None


def libreoffice_convert_to_docx(path, timeout=180):
    """Use LibreOffice (if installed) to convert .doc/.docx to .docx - works on any OS."""
    exe = find_libreoffice()
    if not exe:
        return None
    work = tempfile.mkdtemp(prefix="glfc_lo_")
    src = os.path.join(work, "src" + (os.path.splitext(path)[1].lower() or ".doc"))
    out = os.path.join(work, "out")
    try:
        shutil.copyfile(path, src)
        uri = "file:///" + os.path.join(work, "profile").replace("\\", "/").lstrip("/")
        flags = 0x08000000 if os.name == "nt" else 0
        subprocess.run([exe, "-env:UserInstallation=" + uri, "--headless", "--convert-to", "docx",
                        "--outdir", out, src], timeout=timeout, capture_output=True, creationflags=flags)
        dst = os.path.join(out, "src.docx")
        if os.path.exists(dst):
            return dst
    except Exception:
        pass
    shutil.rmtree(work, ignore_errors=True)
    return None


def convert_to_docx_candidates(path, ext):
    """Yield (docx_path, converter_name, cleanup_dir) for each converter that is available."""
    for name, fn, exts in (("MS Word", word_convert_to_docx, (".doc", ".docx", ".docm", ".pdf")),
                           ("LibreOffice", libreoffice_convert_to_docx, (".doc", ".docx", ".docm"))):
        if ext in exts:
            dst = fn(path)
            if dst:
                top = os.path.dirname(dst)
                if os.path.basename(top) == "out":
                    top = os.path.dirname(top)
                yield dst, name, top


def rows_text_len(rows):
    return sum(len(c) for r in rows for c in r["cells"])


MIN_FIELDS_OK = 8       # a report with fewer recognised headings than this is re-read with another converter


def rows_quality(rows):
    """How many report headings are found in the rows (used to choose the best reading of a file)."""
    try:
        rec = build_record(rows, "")
    except Exception:
        return 0
    found = {canon for _raw, canon, _m in rec["_mapping"] if canon in FIELD_NAMES}
    found.update(f for f in ("Incident Report No", "Report Date") if rec.get(f, "").strip())
    return len(found)


def _read_native(path, ext):
    if ext in (".docx", ".docm", ".doc"):
        rows, fmt = read_doc(path)       # looks inside the file, so a wrong extension does not matter
        if ext != ".doc" and fmt.startswith("DOCX (saved"):
            fmt = "DOCX"
        elif ext != ".doc" and fmt.startswith("Word 97"):
            fmt = "Word 97-2003 (saved as %s)" % ext
        return rows, fmt
    if ext == ".pdf":
        return read_pdf(path), "PDF"
    raise ValueError("Unsupported file type")


def read_any(path, use_word=True):
    """Return (rows, format_label, note).
    1) read the file natively; 2) if the result looks poor (few report headings found, little text,
    or an error) and use_word is on, re-read it through MS Word / LibreOffice and keep the better one."""
    ext = os.path.splitext(path)[1].lower()
    note = ""
    rows, fmt, err = [], ext.upper().strip("."), None
    tmp_copy = None
    try:
        try:
            rows, fmt = _read_native(path, ext)
        except PermissionError:
            # file is open / locked by Word or another program - read a temporary copy instead
            tmp_dir = tempfile.mkdtemp(prefix="glfc_cp_")
            tmp_copy = os.path.join(tmp_dir, "copy" + ext)
            shutil.copyfile(path, tmp_copy)
            rows, fmt = _read_native(tmp_copy, ext)
            note = "File was open in another program - read from a copy"
    except Exception as e:
        err = str(e) or e.__class__.__name__
    finally:
        if tmp_copy:
            shutil.rmtree(os.path.dirname(tmp_copy), ignore_errors=True)
    q = rows_quality(rows) if rows else 0
    poor = bool(err) or rows_text_len(rows) < 40 or (ext != ".pdf" and q < MIN_FIELDS_OK)
    if poor and use_word and ext in (".doc", ".docx", ".docm", ".pdf"):
        for conv, cname, cleanup in convert_to_docx_candidates(path, ext):
            try:
                r2 = read_docx(conv)
                q2 = rows_quality(r2)
                if q2 > q or (not rows and rows_text_len(r2) > 0):
                    rows, fmt, q, err = r2, fmt + " (converted via %s)" % cname, q2, None
                    note = (note + "; " if note else "") + "Read through %s conversion" % cname
            except Exception:
                pass
            finally:
                shutil.rmtree(cleanup, ignore_errors=True)
            if q >= MIN_FIELDS_OK:
                break
    if err and not rows:
        raise ValueError(err)
    if rows_text_len(rows) < 20:
        note = (note + "; " if note else "") + ("Very little text found - file may be scanned image"
                                                 if ext == ".pdf" else "Very little text found")
    return rows, fmt, note


# =============================================================================
#  SECTION 3 - CONVERT ROWS TO ONE UNIFORM RECORD PER FILE
# =============================================================================
def _title_label(raw):
    t = NUM_PREFIX.sub("", (raw or "").strip(), count=1).strip(" :-–—#*•|")
    t = re.sub(r"\s+", " ", t)
    return t[:1].upper() + t[1:] if t else t


OPTIONAL_SPECS = OrderedDict([
    ("Customer Name", ["customer name", "name of customer", "name of the customer", "borrower name", "customer"]),
    ("Customer ID", ["customer id", "cust id", "customer code", "cif", "cif no"]),
    ("Loan Account No", ["loan account no", "loan account number", "loan a c no", "loan ac no", "loan no",
                         "loan number", "account no", "account number", "gl no", "gold loan no", "pledge no"]),
    ("Staff Name / Employee ID", ["staff name", "name of staff", "employee name", "employee id", "emp id",
                                  "emp code", "staff id", "appraiser name", "name of appraiser"]),
    ("Gold Weight", ["gold weight", "gross weight", "net weight", "weight of gold", "weight", "weight in grams"]),
    ("No. of Packets", ["no of packets", "number of packets", "packet no", "packet number", "no of loans",
                        "number of loans", "no of accounts"]),
    ("Loan Amount", ["loan amount", "amount sanctioned", "sanctioned amount", "disbursed amount", "principal"]),
    ("Purity", ["purity", "declared purity", "carat", "karat"]),
    ("Date of Loan", ["date of loan", "loan date", "date of pledge", "pledge date", "date of sanction"]),
])
OPT_INDEX = {}
for _c, _ss in OPTIONAL_SPECS.items():
    for _s in _ss:
        OPT_INDEX[norm_label(_s)] = _c


def match_optional(text):
    """Optional headings that some report formats carry (Customer name, Loan a/c ...).
    Returns (canonical, raw, value) or None."""
    first = (text or "").strip().split("\n")[0].strip()
    rest = "\n".join((text or "").strip().split("\n")[1:])
    cands = [(first, rest)]
    mt = re.match(r"^(.{2,40}?)\s*(?::|：|\t| - )\s*(.*)$", first)
    if mt:
        cands.append((mt.group(1), (mt.group(2) + ("\n" + rest if rest else "")).strip()))
    for raw, val in cands:
        t = NUM_PREFIX.sub("", raw.strip(), count=1).strip(" :-–#*?")
        n = norm_label(t)
        if not n or len(n) > 40:
            continue
        if n in OPT_INDEX:
            return OPT_INDEX[n], raw, val
        n2 = strip_fillers(n)
        if n2 in OPT_INDEX:
            return OPT_INDEX[n2], raw, val
        for syn, canon in OPT_INDEX.items():
            if len(syn) >= 8 and syn[0] == n[0] and abs(len(syn) - len(n)) <= 2 and osa_distance(n, syn) <= 1:
                return canon, raw, val
    return None


# ---------------------------------------------------------------------------
#  Helpers for the layouts seen in the real reports
#    * title line   :  "Incident Report - 19-01-2026   10/2026"
#    * stacked cell :  "Branch / Region / Area" on 3 lines of ONE cell, with the
#                      3 values on 3 lines of the NEXT cell
#    * column heads :  a row of headings followed by a row of values
# ---------------------------------------------------------------------------
_MONTHS_RX = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
DATE_TOKEN_RE = re.compile(
    r"(?<![\d/])\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*(?:\d{4}|\d{2})(?![\d/])"
    r"|(?<!\d)\d{1,2}(?:st|nd|rd|th)?[\s\-.,]*(?:%s)[a-z]*[\s\-.,]*\d{2,4}(?!\d)" % _MONTHS_RX, re.I)
TITLE_RE = re.compile(r"^\s*(?:gold\s*loans?\s*[-–—:|]?\s*)?inc\w{3,7}\s*rep\w{2,6}\b(.*)$", re.I | re.S)
REPNO_YEAR_RE = re.compile(r"(?<![\d/])(\d{1,6})\s*[/\-_]\s*((?:19|20)\d{2})(?!\d)")
REPNO_ONLY_RE = re.compile(r"^[A-Za-z]{0,6}[\s\-/]?\d{1,6}\s*/\s*(?:19|20)?\d{2}$")
DELIM_RE = re.compile(r"\s*(?:[/,&|;]|\band\b)\s*", re.I)


def _is_date_or_no_line(line):
    """True when the line holds only a date and/or a report number (e.g. '19-01-2026', 'Date: 19.01.2026')."""
    if not (DATE_TOKEN_RE.search(line) or REPNO_YEAR_RE.search(line)):
        return False
    t = DATE_TOKEN_RE.sub(" ", line)
    t = REPNO_YEAR_RE.sub(" ", t)
    t = re.sub(r"(?i)\b(?:no|number|dated?|dt|on|ref)\b", " ", t)
    return not re.search(r"[A-Za-z0-9]", t)


_BR_SEP_RE = re.compile(r"[\s\-‐-―−_./,;:|\\()\[\]*#]+")
_BR_EMPTY_RE = re.compile(r"(?:na|n a|nil|none|not stated|not available|not applicable)", re.I)


def clean_branch_line(text):
    """One branch description in ONE uniform spelling: spaces, hyphens / dashes (single, double, en-dash),
    slashes, dots and brackets all collapse to a single space; upper case.
    'HA-7314', 'HA - 7314', 'HA--7314', 'HA– 7314', 'ha  7314.' -> 'HA 7314'."""
    t = (text or "").replace("\xa0", " ").replace("​", "")
    t = _BR_SEP_RE.sub(" ", t).strip().upper()
    if _BR_EMPTY_RE.fullmatch(t.lower()):
        return ""
    return t


def clean_branch(text):
    """Clean every line of a Branch value (the first line is the branch itself)."""
    lines = [clean_branch_line(l) for l in (text or "").split("\n")]
    return "\n".join(l for l in lines if l)


def _branch_code(name):
    """('ADYAR', '101') for 'ADYAR 101' / '101 ADYAR'; code = 3-6 digits at the end or the start."""
    m = re.match(r"^(.*?)\s*\b(\d{3,6})$", name)
    if m:
        return m.group(1).strip(), m.group(2)
    m = re.match(r"^(\d{3,6})\s+(.*)$", name)
    if m:
        return m.group(2).strip(), m.group(1)
    return name, ""


def unify_branches(records):
    """After all files are read: spellings of the same branch are made identical.
    Names that carry the same branch code (e.g. 7314) become the most frequently written name."""
    first = lambda r: (r.get("Branch") or "").split("\n")[0]
    cnt = Counter(first(r) for r in records if first(r))
    by_code = defaultdict(list)
    for nm, c in cnt.items():
        code = _branch_code(nm)[1]
        if code:
            by_code[code].append((nm, c))
    canon = {}
    for code, lst in by_code.items():
        best = max(lst, key=lambda x: (x[1], len(x[0])))[0]
        for nm, _ in lst:
            canon[nm] = best
    for r in records:
        f = first(r)
        if f and canon.get(f, f) != f:
            old = f
            r["Branch"] = "\n".join([canon[f]] + (r["Branch"].split("\n")[1:]))
            r["_mapping"].append((old, "Branch", "branch spelling made uniform -> " + canon[old]))
    return records


def parse_title_line(text):
    """'Incident Report - 19-01-2026   10/2026' -> ('10/2026', '19-01-2026').
    Also copes with 'Incident Report #: 256/2026' and 'Incident Report - 20-01-2026' (no number).
    Returns None when the text is not such a title line."""
    lines = [l.strip() for l in (text or "").replace("\r", "\n").split("\n") if l.strip()]
    if not lines:
        return None
    m = TITLE_RE.match(lines[0])
    if not m:
        return None
    rest = m.group(1)
    # the report number / date may be typed on the next line(s) of the same cell (user pressed Enter)
    for extra in lines[1:3]:
        if len(extra) <= 40 and _is_date_or_no_line(extra):
            rest += "   " + extra
    dm = DATE_TOKEN_RE.search(rest)
    date = re.sub(r"\s+", "", dm.group(0)) if dm and re.match(r"\d{1,2}\s*[-/.]", dm.group(0)) else (dm.group(0).strip() if dm else "")
    rest2 = (rest[:dm.start()] + " " + rest[dm.end():]) if dm else rest
    rest2 = re.sub(r"(?i)\b(?:no|number|dated?|dt|on|ref)\b\.?", " ", rest2)
    rest2 = rest2.strip(" \t:#-–—|.,()")
    num = ""
    mn = REPNO_YEAR_RE.search(rest2)
    if mn:
        num = "%s/%s" % (mn.group(1), mn.group(2))
    elif rest2 and len(rest2) <= 25:
        mn = re.search(r"[A-Za-z]{0,6}[\s\-/]?\d[\w/\-]*", rest2)
        if mn:
            num = mn.group(0).strip()
    if not date and not num:
        return None
    return num, date


def _trim_lines(text):
    lines = [l.strip() for l in (text or "").replace("\r", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def parse_stacked_labels(text):
    """Every non-blank line of the text is a heading (Branch / Region / Area on 3 lines).
    Returns [(canonical, raw, method, line_index)] or None."""
    lines = _trim_lines(text)
    if len(lines) < 2:
        return None
    out = []
    for i, s in enumerate(lines):
        if not s or is_marker(s):
            continue
        c, m = match_label(s, allow_prefix=False)
        if not c:
            return None
        out.append((c, s, m, i))
    if len(out) >= 2 and len({o[0] for o in out}) == len(out):
        return out
    return None


def parse_delimited_labels(text):
    """'Branch / Region / Area' written on one line.  Returns ([(canon, raw, method, idx)], regex) or None."""
    s = (text or "").strip()
    if not s or "\n" in s or len(s) > 80:
        return None
    parts = [p for p in DELIM_RE.split(s) if p and p.strip()]
    if len(parts) < 2:
        return None
    out = []
    for i, p in enumerate(parts):
        c, m = match_label(p, strict=True, allow_prefix=False)
        if not c:
            return None
        out.append((c, p.strip(), m, i))
    if len({o[0] for o in out}) != len(out):
        return None
    return out, DELIM_RE


def align_stacked(labels, label_nlines, raw_val, clean_val=None):
    """Spread the lines of a value cell over the stacked headings, keeping blank lines in place
    (so a blank Region does not shift Area's value into Region)."""
    n = len(labels)
    vals_raw = _trim_lines(raw_val)
    if len(vals_raw) == label_nlines:
        return [vals_raw[l[3]] for l in labels]
    vals = [x.strip() for x in (clean_val if clean_val is not None else raw_val or "").replace("\r", "\n").split("\n")
            if x.strip() and not is_marker(x)]
    if len(vals) == n:
        return vals
    vals = [x for x in vals_raw if x and not is_marker(x)] or vals
    if len(vals) < n:
        return vals + [""] * (n - len(vals))
    return vals[:n - 1] + ["\n".join(vals[n - 1:])]


def build_record(rows, file_name):
    fields = OrderedDict((k, []) for k in FIELD_NAMES)
    extras = OrderedDict()
    mapping = []
    unassigned = []
    state = {"cur": None, "core": False, "pending": None, "hdr": None, "resolving": False, "want_date": False}

    def flush_pending():
        pend, state["pending"] = state["pending"], None
        if pend:
            apply_stacked(pend["labels"], [""] * len(pend["labels"]))

    def apply_stacked(labels, vals):
        state["resolving"] = True
        try:
            for (canon, raw, method, _i), v in zip(labels, vals):
                open_field(canon, raw, method + " (stacked heading)")
                add_value(v)
        finally:
            state["resolving"] = False

    def resolve_pending(raw_val, clean_val=None):
        pend, state["pending"] = state["pending"], None
        nl = pend["nlines"]
        if pend.get("rx") is not None:
            parts = [p.strip() for p in pend["rx"].split(clean_val if clean_val is not None else raw_val)]
            if len(parts) == len(pend["labels"]):
                raw_val = clean_val = "\n".join(parts)
        apply_stacked(pend["labels"], align_stacked(pend["labels"], nl, raw_val, clean_val))

    def open_field(canon, raw, method, is_extra=False, raw_written=None):
        if state["pending"] and not state["resolving"]:
            flush_pending()
        if is_extra:
            name = _title_label(raw)
            if name not in extras:
                extras[name] = []
            if raw_written is not None:
                mapping.append((raw_written.strip(), name, "optional heading (extra column)"))
            else:
                mapping.append((raw.strip(), name, "new heading (kept as extra column)"))
            state["cur"] = ("X", name)
            return
        if canon == "_DATE":
            if not fields["Report Date"] and not state["core"]:
                canon = "Report Date"
            else:
                canon = "Date Observed"
            method = method + " / generic 'Date' -> " + canon
        if canon in CORE_FIELDS:
            state["core"] = True
        if canon in SHORT_FIELDS and fields[canon] and canon not in ("Since When",):
            # a second occurrence of a short field - keep the first, park the new one
            mapping.append((raw.strip(), canon, method + " (duplicate - kept first)"))
            state["cur"] = ("DUP", canon)
            return
        mapping.append((raw.strip(), canon, method))
        state["cur"] = canon

    def add_value(text, kind=None):
        if state["pending"] and not state["resolving"] and clean_value(text):
            resolve_pending(text)
            return
        text = clean_value(text)
        if not text:
            return
        cur = state["cur"]
        if cur is None:
            unassigned.append(text)
            return
        if isinstance(cur, tuple):
            if cur[0] == "X":
                extras[cur[1]].append(text)
            else:
                unassigned.append("%s: %s" % (cur[1], text))
            return
        tgt = fields[cur]
        if kind == "p" and cur in SHORT_FIELDS and tgt:
            unassigned.append(text)
            return
        tgt.append(text)

    def try_bare_date(t):
        """Report date typed alone in the row/cell that follows the 'Incident Report ...' title."""
        if not state["want_date"]:
            return False
        state["want_date"] = False
        s_ = re.sub(r"(?i)^\s*dated?\s*[:\-]?\s*", "", (t or "").strip()).strip(" .")
        if s_ and DATE_TOKEN_RE.fullmatch(s_) and not fields["Report Date"]:
            fields["Report Date"].append(s_)
            mapping.append((t.strip()[:40], "Report Date", "date on line after title"))
            return True
        return False

    def apply_title(ti, raw_txt):
        num, date = ti
        state["want_date"] = not date and not fields["Report Date"]
        if state["pending"]:
            flush_pending()
        if num and not fields["Incident Report No"]:
            fields["Incident Report No"].append(num)
        if date and not fields["Report Date"]:
            fields["Report Date"].append(date)
        mapping.append((raw_txt.split("\n")[0].strip()[:70], "Incident Report No / Report Date",
                        "title line split"))

    def process_cells(cs):
        """Cells after the first one: more 'Label: value' pairs, headings or plain values."""
        for c in cs:
            cc = c.strip()
            canon, method = (None, None)
            if len(cc) <= 40 and "\n" not in cc:
                canon, method = match_label(cc, strict=True, allow_prefix=False)
                if canon is None:
                    mt = re.match(r"^(.{2,40}?)\s*[:：]\s*(.*)$", cc, re.S)
                    if mt:
                        c2, m2 = match_label(mt.group(1), strict=True, allow_prefix=False)
                        if c2:
                            open_field(c2, mt.group(1), m2)
                            add_value(mt.group(2))
                            continue
            if canon:
                open_field(canon, cc, method)
            else:
                add_value(c, "t")

    def cell_label(c):
        c = c.strip()
        if len(c) <= 40 and "\n" not in c:
            return match_label(c, strict=True, allow_prefix=False)
        return (None, None)

    for row in rows:
        cells = [c if isinstance(c, str) else "" for c in row.get("cells", [])]
        raws = [c if isinstance(c, str) else "" for c in (row.get("raw") or cells)]
        if row["kind"] == "p":
            txt = cells[0] if cells else ""
            if re.fullmatch(r"\s*gold\s*loans?\s*(?:audit|division|department)?\s*", txt, re.I):
                continue
            if not state["core"] and try_bare_date(txt):
                continue
            if not state["core"]:
                ti = parse_title_line(txt)
                if ti:
                    apply_title(ti, txt)
                    continue
            st = parse_stacked_labels(txt)
            dl = None if st else parse_delimited_labels(txt)
            if st or dl:
                if state["pending"]:
                    flush_pending()
                state["pending"] = ({"labels": st, "nlines": len(_trim_lines(txt)), "rx": None} if st else
                                    {"labels": dl[0], "nlines": len(dl[0]), "rx": dl[1]})
                continue
            segs = split_label_text(txt, allow_prefix=row.get("prefix", False))
            if segs:
                for canon, raw, method, val in segs:
                    open_field(canon, raw, method)
                    add_value(val)
            else:
                opt = match_optional(txt) if len(txt.split("\n")[0]) <= 60 or ":" in txt[:42] else None
                if opt:
                    open_field(None, opt[0], "", is_extra=True, raw_written=opt[1])
                    add_value(opt[2])
                else:
                    add_value(txt, "p")
            continue
        # ---- table row
        k = 0
        while k < len(cells) and (not cells[k].strip() or is_marker(cells[k], loose=True)):
            k += 1
        items = [(j + k, c) for j, c in enumerate(cells[k:]) if c.strip() and (j == 0 or not is_marker(c))]
        # remove duplicated neighbouring cells (merged cells in some formats)
        dedup = []
        for idx, c in items:
            if not dedup or dedup[-1][1].strip() != c.strip():
                dedup.append((idx, c))
        items = dedup
        if not items:
            continue
        rest = [c for _, c in items]
        rest_raw = [(raws[i] if i < len(raws) and raws[i].strip() else c) for i, c in items]
        first = rest[0]
        if re.fullmatch(r"\s*gold\s*loans?\s*", first, re.I) and len(rest) == 1:
            continue
        # ---- (1) title line  "Incident Report - 19-01-2026   10/2026"
        if not state["core"] and len(rest) == 1 and try_bare_date(first):
            continue
        if not state["core"]:
            ti = parse_title_line(first)
            if ti:
                num, date = ti
                if not num:
                    for c in rest[1:]:
                        if REPNO_ONLY_RE.match(c.strip()):
                            num = c.strip()
                            break
                if not date:
                    for c in rest[1:]:
                        c2 = re.sub(r"(?i)^\s*dated?\s*[:\-]?\s*", "", c.strip()).strip(" .")
                        if DATE_TOKEN_RE.fullmatch(c2):
                            date = c2
                            break
                apply_title((num, date), first)
                continue
        # ---- (2) a row of column headings followed by a row of values
        hdr, state["hdr"] = state["hdr"], None
        lm = [cell_label(c) for c in rest]
        all_labels = len(rest) >= 2 and all(l[0] for l in lm) and len({l[0] for l in lm}) == len(lm)
        if hdr and len(rest) == len(hdr) and not all_labels:
            for (canon, raw, method), c in zip(hdr, rest):
                open_field(canon, raw, method + " (column heading)")
                add_value(c)
            continue
        if all_labels:
            if state["pending"]:
                flush_pending()
            state["hdr"] = [(l[0], c.strip(), l[1]) for l, c in zip(lm, rest)]
            continue
        # ---- (3) several headings stacked in ONE cell  (Branch / Region / Area on 3 lines)
        st = parse_stacked_labels(rest_raw[0])
        dl = None if st else parse_delimited_labels(first)
        if st or dl:
            if state["pending"]:
                flush_pending()
            pend = ({"labels": st, "nlines": len(_trim_lines(rest_raw[0])), "rx": None} if st else
                    {"labels": dl[0], "nlines": len(dl[0]), "rx": dl[1]})
            state["pending"] = pend
            if len(rest) >= 2:
                resolve_pending(rest_raw[1], rest[1])
                process_cells(rest[2:])
            continue
        # ---- (4) ordinary 'Label | value' row
        if state["pending"] and not split_label_text(first) and not match_optional(first):
            resolve_pending(first, first)       # values for stacked headings sitting in the next row
            process_cells(rest[1:])
            continue
        segs = split_label_text(first)
        consumed = False
        if segs:
            for canon, raw, method, val in segs:
                open_field(canon, raw, method)
                add_value(val)
            consumed = True
        else:
            opt = match_optional(first)
            if opt:
                open_field(None, opt[0], "", is_extra=True, raw_written=opt[1])
                add_value(opt[2])
                consumed = True
            elif len(rest) >= 2 and looks_like_label(first) and k == 0 and row.get("src") != "pdf":
                open_field(None, first, "", is_extra=True)
                consumed = True
        if not consumed:
            add_value("\n".join(rest), "t")
            continue
        process_cells(rest[1:])
    if state["pending"]:
        flush_pending()

    rec = OrderedDict()
    rec["File Name"] = file_name
    for k in FIELD_NAMES:
        rec[k] = "\n".join(fields[k]).strip()
    # date columns: keep just the date itself (drops trailing '.', ',', stray text)
    for f_ in ("Report Date", "Date Observed"):
        v_ = rec[f_].strip()
        if v_:
            dm_ = DATE_TOKEN_RE.search(v_)
            rec[f_] = re.sub(r"\s+", "", dm_.group(0)) if dm_ and re.match(r"\d{1,2}\s*[-/.]", dm_.group(0)) \
                else (dm_.group(0).strip() if dm_ else v_.strip(" .,;:-–—"))
    # a date must never sit in the report-number column
    no = rec["Incident Report No"].strip()
    if no and DATE_TOKEN_RE.fullmatch(no):
        if not rec["Report Date"]:
            rec["Report Date"] = no
        rec["Incident Report No"] = ""
    # fall-backs for report number: title area of the document, then the file name
    if not rec["Incident Report No"] or is_placeholder(rec["Incident Report No"]):
        head_txt = "\n".join(" ".join(r["cells"]) for r in rows[:8])
        cand = ""
        for m in re.finditer(r"inc\w{3,7}\s*rep\w{2,6}\s*(?:no\.?|number|#)?\s*[:#\-]?\s*([A-Za-z0-9][\w/\-]*)",
                             head_txt, re.I):
            g = m.group(1)
            if any(ch.isdigit() for ch in g) and not DATE_TOKEN_RE.fullmatch(g):
                cand = g
                break
        if cand:
            rec["Incident Report No"] = cand
        else:
            m = re.search(r"(\d{1,6})\s*[_\-/ ]+\s*((?:19|20)\d{2})", os.path.splitext(file_name)[0])
            if m:
                rec["Incident Report No"] = "%s/%s (from file name)" % (m.group(1), m.group(2))
    raw_branch = rec["Branch"]
    rec["Branch"] = clean_branch(raw_branch)
    if raw_branch.strip() and rec["Branch"] != raw_branch.strip():
        mapping.append((raw_branch.strip().split("\n")[0][:60], "Branch", "branch text cleaned -> " + rec["Branch"].split("\n")[0]))
    rec["_extras"] = OrderedDict((k, "\n".join(v).strip()) for k, v in extras.items())
    rec["_unassigned"] = "\n".join(unassigned).strip()
    rec["_mapping"] = mapping
    return rec


def merge_extra_columns(records):
    """Make extra (non-standard) heading names uniform across files."""
    names = []
    for r in records:
        for k in r["_extras"]:
            if k not in names:
                names.append(k)
    canon_of = {}
    reps = []
    for nm in names:
        n = norm_label(nm)
        hit = None
        for rp in reps:
            rn = norm_label(rp)
            if n == rn or (n and rn and n[0] == rn[0] and osa_distance(n, rn) <= (1 if len(rn) <= 8 else 2)):
                hit = rp
                break
        if hit is None:
            reps.append(nm)
            canon_of[nm] = nm
        else:
            canon_of[nm] = hit
    counts = Counter()
    for r in records:
        new = OrderedDict()
        for k, v in r["_extras"].items():
            ck = canon_of[k]
            new[ck] = (new.get(ck, "") + "\n" + v).strip() if ck in new else v
            if ck != k:
                r["_mapping"].append((k, ck, "extra heading made uniform"))
        r["_extras"] = new
        for k in new:
            counts[k] += 1
    return [k for k in reps if counts[k] > 0]


# =============================================================================
#  SECTION 4 - VALUE PARSERS (Rupees, dates, weights, counts)
# =============================================================================
_AMT_RE = re.compile(
    r"(?:(?:\brs|\binr|\brupees|\brs\.)\s*\.?\s*|₹\s*)(\d[\d,]*(?:\.\d+)?)\s*(?:/-)?\s*"
    r"(lakhs?\b|lacs?\b|lakh\b|crores?\b|crs?\b\.?|thousands?\b|k\b|mn\b|millions?\b|l\b)?", re.I)
_UNIT_RE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*(lakhs?|lacs?|crores?|crs?)\b", re.I)


def _unit_mult(u):
    u = (u or "").lower().strip(". ")
    if u.startswith(("lakh", "lac")) or u == "l":
        return 1e5
    if u.startswith("cr"):
        return 1e7
    if u.startswith("thousand") or u == "k":
        return 1e3
    if u.startswith(("mn", "million")):
        return 1e6
    return 1.0


def _num(s):
    try:
        return float(s.replace(",", ""))
    except Exception:
        return None


def parse_amounts(text):
    """All rupee amounts in the text, as (value_in_rupees, start_pos)."""
    out, spans = [], []
    for m in _AMT_RE.finditer(text or ""):
        v = _num(m.group(1))
        if v is None:
            continue
        out.append((v * _unit_mult(m.group(2)), m.start()))
        spans.append((m.start(), m.end()))
    for m in _UNIT_RE.finditer(text or ""):
        if any(a <= m.start() < b for a, b in spans):
            continue
        v = _num(m.group(1))
        if v is not None:
            out.append((v * _unit_mult(m.group(2)), m.start()))
    return out


def money_value(text, sum_all=False):
    """Best single rupee figure in a field.  Returns (rupees or None, basis).
    sum_all=True (used for Financial Impact): several Rs figures are ADDED UP (unless a total is stated)."""
    if not text or is_placeholder(text):
        return None, "not stated"
    amts = parse_amounts(text)
    if amts:
        tm = re.search(r"\b(?:total|aggregate|overall|net)\b", text, re.I)
        if tm:
            after = [a for a in amts if a[1] >= tm.start()]
            if after:
                return after[0][0], "total stated"
        if len(amts) == 1:
            return amts[0][0], "stated"
        if sum_all:
            # ignore figures that describe recovery ("... recovered Rs 5,000") - they are not loss
            amts_s = sorted(amts, key=lambda a: a[1])
            keep = []
            for i, a in enumerate(amts_s):
                nxt = amts_s[i + 1][1] if i + 1 < len(amts_s) else len(text)
                before = re.split(r"[.\n;,]", text[:a[1]])[-1]      # same clause, before the figure
                after = re.split(r"[.\n;]", text[a[1]:nxt])[0]       # same clause, after the figure
                if not re.search(r"recover|recoup", before + " " + after, re.I):
                    keep.append(a)
            keep = keep or amts
            vals = [a[0] for a in keep]
            if len(vals) == 1:
                return vals[0], "stated"
            for i, v in enumerate(vals):          # one figure equals the sum of the others -> it is the total
                others = vals[:i] + vals[i + 1:]
                if len(others) >= 2 and abs(v - sum(others)) < 1:
                    return v, "total stated (equals sum of parts)"
            return sum(vals), "sum of %d Rs figures" % len(vals)
        return max(a[0] for a in amts), "largest of %d figures" % len(amts)
    bare = []
    for m in re.finditer(r"(?<![\w./-])(\d{1,3}(?:,\d{2,3})+|\d{4,9})(?:\.\d+)?(?![\w/-])", text):
        tail = text[m.end():m.end() + 8].lower()
        if re.match(r"\s*(g\b|gm|gms|gram|%|ct|kt|carat|karat)", tail):
            continue
        v = _num(m.group(0))
        if v and v >= 1000 and not (1900 <= v <= 2100):
            bare.append(v)
    if bare:
        return max(bare), "number without Rs symbol"
    return None, "not quantified"


# Rs amounts whose number contains a "." (decimal point or dot used as a separator), kept EXACTLY as written
_DOT_AMT = re.compile(r"(?:(?:\u20b9|\b(?:rs|inr|rupees)\b\.?)\s*)?(\d[\d,]*(?:\.\d+)+)\s*(?:/-)?"
                      r"(?:\s*(?:lakhs?|lacs?|crores?|crs?)\b)?", re.I)


def dotted_raw_at(text, pos):
    """The amount that starts at pos, exactly as written, when its number contains a '.'; else ''."""
    m = _DOT_AMT.match(text or "", pos)
    return m.group(0).strip() if m else ""


def dotted_amounts(text):
    """All Rs amounts in the text whose number contains a '.', exactly as written (needs Rs / lakh etc. next to it)."""
    out = []
    for m in _DOT_AMT.finditer(text or ""):
        g = m.group(0).strip()
        if re.search(r"\u20b9|\b(?:rs|inr|rupees)\b|lakh|lac|crore|\bcrs?\b", g, re.I) and g not in out:
            out.append(g)
    return out


def to_lakhs(rupees):
    return None if rupees is None else rupees / 1e5


def fmt_l(rupees, dash="-"):
    if rupees is None:
        return dash
    return "%.2f" % (rupees / 1e5)


def fmt_rsl(rupees):
    if rupees is None:
        return "Not quantified"
    return "Rs %.2f L" % (rupees / 1e5)


# ---- Total pledge value / loan amount, read from the free text of "What Happened"
_BARE_RE = re.compile(r"(?<![\w./-])(\d{1,3}(?:,\d{2,3})+|\d{4,9})(?:\.\d+)?(?:\s*/-)?(?![\w/-])")
_CLAUSE_SPLIT = re.compile(r"[;\n\u2022]|(?<![Rr][Ss])(?<![Nn][Oo])\.\s+(?=[A-Z])")
# tier 1 = value of the pledged gold;  tier 2 = loan amount / similar
_PLEDGE_KW = re.compile(
    r"(?:pledge[sd]?\s*(?:gold\s*)?(?:total\s*)?(?:value|amount|worth)"
    r"|(?:total|aggregate|gross|net|overall)\s+(?:pledge[sd]?|gold|ornaments?|jewel\w*|collateral|security)"
    r"(?:\s+(?:value|worth))?"
    r"|value\s+of\s+(?:the\s+|all\s+|such\s+|these\s+)?(?:pledged\s+|gold\s+)?"
    r"(?:gold|ornaments?|jewel\w*|pledge\w*|articles?|packets?|security|collateral)"
    r"|(?:gold|ornaments?|jewel\w*|appraised|appraisal|market|security|collateral)\s+(?:value|worth)"
    r"|worth\s+of\s+(?:gold|ornaments?|jewel\w*))", re.I)
_LOAN_KW = re.compile(
    r"(?:loans?\s*(?:amount|value|outstanding|balance|of|for|against|a/?c\s*amount)"
    r"|loans?\s+(?:sanctioned|disbursed|availed|granted|released|given)"
    r"|(?:amount\s+)?(?:sanctioned|disbursed|advanced|lent|availed)|principal|outstanding|borrowed"
    r"|exposure|facility|advance[sd]?)", re.I)
_EXCL_KW = re.compile(r"(?:loss|lost|shortfall|short\s*fall|deficit|recover\w*|recoup\w*|interest|penal|overdue|"
                      r"difference|excess|fees?|charges?|insurance|auction|reserve\s+price|cash|penalty)", re.I)
_TOTAL_KW = re.compile(r"\b(?:total|aggregate|gross|overall|combined|in\s+all|sum\s+of)\b", re.I)
_BARE_OK = re.compile(r"(?:value|amount|worth|sanctioned|disbursed|outstanding|principal|total)\s*"
                      r"(?:is|was|of|as|being|rs\.?|inr)?\s*[:\-=]?\s*(?:is|was|of|rs\.?|inr)?\s*$", re.I)


def _amount_spans(text):
    """Every rupee amount in the text as [value, start, end, is_bare_number]."""
    sp = []
    for m in _AMT_RE.finditer(text):
        v = _num(m.group(1))
        if v is not None:
            sp.append([v * _unit_mult(m.group(2)), m.start(), m.end(), False])
    for m in _UNIT_RE.finditer(text):
        if any(a[1] <= m.start() < a[2] for a in sp):
            continue
        v = _num(m.group(1))
        if v is not None:
            sp.append([v * _unit_mult(m.group(2)), m.start(), m.end(), False])
    for m in _BARE_RE.finditer(text):
        if any(a[1] <= m.start() < a[2] or m.start() <= a[1] < m.end() for a in sp):
            continue
        v = _num(m.group(1))
        tail = text[m.end():m.end() + 8].lower()
        if v and v >= 1000 and not (1900 <= v <= 2100) and not re.match(r"\s*(g\b|gm|gms|gram|%|ct|kt|carat|karat)", tail):
            sp.append([v, m.start(), m.end(), True])
    sp.sort(key=lambda a: a[1])
    return sp


def _last_end(rx, s):
    ms = list(rx.finditer(s))
    return ms[-1].end() if ms else -1


def _pledge_in_text(text, raw_out=None):
    """-> (tier, rupees, basis) or None.  Reads all amounts that are described as pledge value /
    loan amount (many values with other text in between), ignores loss / recovery / interest figures."""
    if not text or not text.strip():
        return None
    sp = _amount_spans(text)
    bounds = [m.end() for m in _CLAUSE_SPLIT.finditer(text)]
    found = {1: [], 2: []}          # tier -> [(value, is_total)]
    raws = {1: [], 2: []}           # tier -> amount text as written, when it contains a '.'
    prev_tier = None
    for i, (v, st, en, bare) in enumerate(sp):
        cs = max([b for b in bounds if b <= st] or [0])
        nxt = sp[i + 1][1] if i + 1 < len(sp) else len(text)
        ce = min([b for b in bounds if b >= en] or [len(text)])
        before = text[max(cs, sp[i - 1][2] if i else 0):st][-80:]
        after = text[en:min(ce, nxt)][:40]
        if re.match(r"\s*(?:/-)?\s*(?:/|per)\s*(?:gm|gram|g\b)", after, re.I):      # a rate per gram, not a value
            continue
        if bare and not (_BARE_OK.search(before[-30:]) or
                         (prev_tier and re.match(r"^\s*(?:and|&|\+|plus|,|,\s*and)\s*$", before))):
            continue
        t1, t2, ex = _last_end(_PLEDGE_KW, before), _last_end(_LOAN_KW, before), _last_end(_EXCL_KW, before)
        tier = None
        if max(t1, t2, ex) == -1:
            if re.match(r"^\s*(?:and|&|\+|plus|,|,\s*and)?\s*$", before) and prev_tier:
                tier = prev_tier                                    # "... Rs 1,50,000 and Rs 2,00,000"
            else:
                a = after[:30]
                if _PLEDGE_KW.search(a):
                    tier = 1
                elif _LOAN_KW.search(a):
                    tier = 2
        elif ex > max(t1, t2):
            tier = None
        else:
            tier = 1 if t1 >= t2 else 2
        if tier and re.search(r"recover|recoup|loss|lost|shortfall|interest|overdue|penal", after[:25], re.I):
            tier = None
        prev_tier = tier
        if tier:
            is_total = bool(_TOTAL_KW.search(before[-60:]) or re.match(r"\s*(?:in\s+total|in\s+all|total)\b", after, re.I))
            found[tier].append((v, is_total))
            raws[tier].append(dotted_raw_at(text, st))
    for tier in (1, 2):
        items = found[tier]
        if not items:
            continue
        name = "pledge value" if tier == 1 else "loan amount"
        if raw_out is not None:
            raw_out.extend(x for x in raws[tier] if x and x not in raw_out)
        totals = [v for v, t in items if t]
        if totals:
            return tier, max(totals), "total %s stated" % name
        vals = [v for v, _ in items]
        if len(vals) == 1:
            return tier, vals[0], "%s stated" % name
        for k, v in enumerate(vals):
            others = vals[:k] + vals[k + 1:]
            if len(others) >= 2 and abs(v - sum(others)) < 1:
                return tier, v, "total %s stated (equals sum of parts)" % name
        return tier, sum(vals), "sum of %d %s figures" % (len(vals), name)
    return None


def pledge_value(what_happened, narration="", raw_out=None):
    """Total pledge value (or loan amount / similar) in rupees from the 'What Happened' text;
    falls back to the Narration.  Returns (rupees or None, basis)."""
    for label, txt in (("What Happened", what_happened), ("Narration", narration)):
        res = _pledge_in_text(txt or "", raw_out)
        if res:
            return res[1], res[2] + ("" if label == "What Happened" else " (from narration)")
    return None, "not stated"


MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
                                          "oct", "nov", "dec"])}


def _mk_date(y, m, d):
    try:
        y = int(y)
        if y < 100:
            y += 2000
        if not (1990 <= y <= 2100):
            return None
        return dt.date(y, int(m), int(d))
    except Exception:
        return None


def parse_date(text, ref=None):
    if not text:
        return None
    t = text.strip()
    m = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", t)
    if m:
        d = _mk_date(m.group(1), m.group(2), m.group(3))
        if d:
            return d
    m = re.search(r"\b(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{2,4})\b", t)
    if m:
        d = _mk_date(m.group(3), m.group(2), m.group(1)) or _mk_date(m.group(3), m.group(1), m.group(2))
        if d:
            return d
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?[-/ ]?\s*([A-Za-z]{3,9})\.?[-/,\s]+'?(\d{2,4})\b", t)
    if m and m.group(2)[:3].lower() in MONTHS:
        d = _mk_date(m.group(3), MONTHS[m.group(2)[:3].lower()], m.group(1))
        if d:
            return d
    m = re.search(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", t)
    if m and m.group(1)[:3].lower() in MONTHS:
        d = _mk_date(m.group(3), MONTHS[m.group(1)[:3].lower()], m.group(2))
        if d:
            return d
    m = re.search(r"\b([A-Za-z]{3,9})\.?[\s,\-']+(\d{4})\b", t)
    if m and m.group(1)[:3].lower() in MONTHS:
        d = _mk_date(m.group(2), MONTHS[m.group(1)[:3].lower()], 1)
        if d:
            return d
    if ref:
        m = re.search(r"(\d+)\s*(day|week|month|year)s?\b", t, re.I)
        if m:
            k = int(m.group(1))
            unit = m.group(2).lower()
            days = {"day": 1, "week": 7, "month": 30, "year": 365}[unit] * k
            return ref - dt.timedelta(days=days)
    return None


def fmt_date(d):
    return d.strftime("%d-%m-%Y") if d else ""


_WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
             "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20}


def gold_weight(text):
    vals = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:gms?|grams?|gm\.?|grm?s?|g)\b", text or "", re.I):
        v = _num(m.group(1))
        if v is not None and 0 < v < 100000:
            vals.append(v)
    return max(vals) if vals else None


def count_units(text):
    best = 0
    for m in re.finditer(r"\b(\d{1,4}|" + "|".join(_WORD_NUM) + r")\s+(?:nos?\.?\s+(?:of\s+)?)?"
                         r"(?:gold\s+)?(packets?|loans?|loan\s+accounts?|accounts?|a/cs?|pledges?|customers?|"
                         r"borrowers?|ornaments?|items?|bangles?|chains?|rings?)\b", text or "", re.I):
        g = m.group(1).lower()
        v = _WORD_NUM.get(g) if g in _WORD_NUM else int(g)
        if v and v < 5000:
            best = max(best, v)
    return best or None

# =============================================================================
#  SECTION 5 - GOLD-LOAN FRAUD & CONTROL KNOWLEDGE BASE (text-mining lexicons)
#  '*' at the end of a word = any ending (e.g. apprais* -> appraiser, appraisal)
# =============================================================================
def _compile(words):
    pats = []
    for w in words:
        w = w.strip().lower()
        if not w:
            continue
        stem = w.endswith("*")
        w = w.rstrip("*")
        p = r"[\s\-]*".join(re.escape(x) for x in w.split())
        pats.append(r"(?<![a-z0-9])" + p + (r"[a-z]*" if stem else r"(?![a-z0-9])"))
    return re.compile("|".join(pats), re.I)


FRAUD_TYPOLOGIES = OrderedDict([
    ("Spurious / Fake Gold Pledged", ["spurious", "fake gold", "fake ornament*", "imitation", "duplicate gold",
                                      "non gold", "not gold", "not genuine", "base metal", "brass", "copper",
                                      "gold plated", "gold coated", "gold covering", "covering ornament*",
                                      "plating", "plated", "one gram gold", "1 gram gold", "1gm gold",
                                      "rolled gold", "fake", "counterfeit", "white metal", "panchaloha"]),
    ("Low Purity / Karat Misstatement", ["low purity", "lower purity", "purity less", "less purity",
                                         "inferior purity", "low carat*", "low karat*", "less than 22",
                                         "below 22", "18 carat", "18 karat", "18k", "14 carat", "14k",
                                         "purity mismatch", "purity difference", "impure", "purity variation",
                                         "lesser purity", "purity shortfall", "low fineness"]),
    ("Weight Manipulation / Filler Inside Ornament", ["wax", "lac", "lacquer", "filler", "filled", "hollow",
                                                     "excess stone", "inner core", "tungsten", "lead filled",
                                                     "iron", "silver core", "copper core", "inserted", "soldered",
                                                     "solder", "pipe", "weight difference", "weight mismatch",
                                                     "less weight", "weight short*", "excess weight", "stone weight",
                                                     "net weight variation", "screw", "spring", "magnet"]),
    ("Ornament Substitution / Swapping", ["swap*", "substitut*", "replaced", "replacement of", "exchanged",
                                          "switched", "interchanged", "replaced with"]),
    ("Missing Gold / Packet Tampering / Pilferage", ["missing", "shortage", "short in", "pilfer*", "theft",
                                                    "stolen from", "not found", "empty packet", "packet tamper*",
                                                    "seal broken", "seal tamper*", "tamper*", "found short",
                                                    "removed from packet", "packet opened"]),
    ("Over-valuation / Excess LTV Sanction", ["over valu*", "overvalu*", "excess loan", "excess ltv", "higher ltv",
                                              "ltv breach", "inflated", "excess disbursement", "over financ*",
                                              "higher rate", "excess eligibility", "excess amount sanctioned",
                                              "loan to value breach", "above ltv"]),
    ("Fictitious / Benami / KYC Fraud", ["fictitious", "benami", "dummy", "ghost", "fake kyc", "forged",
                                         "forgery", "impersonat*", "proxy", "fake identity", "fake id",
                                         "kyc not", "without kyc", "name lending", "same customer",
                                         "multiple loans", "fake documents", "fabricated"]),
    ("Unauthorised Release / Redemption Fraud", ["unauthori* release", "released without", "without repayment",
                                                 "without closure", "release without", "premature release",
                                                 "wrong release", "released to third", "released to another",
                                                 "release of gold without", "delivered without"]),
    ("Re-pledge / Takeover Abuse", ["repledg*", "re pledg*", "pledged elsewhere", "pledged with another",
                                    "another financ*", "takeover", "take over", "other bank", "other nbfc"]),
    ("Cash / Interest Misappropriation", ["misappropriat*", "embezzl*", "diverted", "not remitted", "not credited",
                                          "cash short*", "personal use", "collected cash", "fund diversion",
                                          "unaccounted cash", "siphon*"]),
    ("Stolen Gold Pledged by Customer", ["stolen gold", "stolen ornament*", "stolen property", "police", "fir",
                                         "robbery", "chain snatch*", "burglary", "theft case"]),
])
TYPOLOGY_SEVERITY = {
    "Ornament Substitution / Swapping": 5, "Missing Gold / Packet Tampering / Pilferage": 5,
    "Fictitious / Benami / KYC Fraud": 5, "Unauthorised Release / Redemption Fraud": 5,
    "Cash / Interest Misappropriation": 5, "Over-valuation / Excess LTV Sanction": 4,
    "Re-pledge / Takeover Abuse": 4, "Spurious / Fake Gold Pledged": 3,
    "Weight Manipulation / Filler Inside Ornament": 3, "Low Purity / Karat Misstatement": 3,
    "Stolen Gold Pledged by Customer": 3, "Spurious / Low-Purity Gold (inferred from tests)": 3,
}
INSIDER_TYPOLOGIES = {"Ornament Substitution / Swapping", "Missing Gold / Packet Tampering / Pilferage",
                      "Unauthorised Release / Redemption Fraud", "Cash / Interest Misappropriation",
                      "Over-valuation / Excess LTV Sanction"}
CUSTOMER_TYPOLOGIES = {"Spurious / Fake Gold Pledged", "Low Purity / Karat Misstatement",
                       "Weight Manipulation / Filler Inside Ornament", "Stolen Gold Pledged by Customer",
                       "Fictitious / Benami / KYC Fraud", "Spurious / Low-Purity Gold (inferred from tests)",
                       "Re-pledge / Takeover Abuse"}

CONTROL_CATEGORIES = OrderedDict([
    ("Appraisal & Purity Testing", ["apprais*", "purity", "acid", "touchstone", "touch stone", "xrf", "karat*",
                                    "carat*", "not tested", "improper test*", "testing", "assay*", "hallmark*",
                                    "valuer", "gold valuer", "fineness"]),
    ("Weighing & Weight Verification", ["weigh*", "weight", "scale", "calibrat*", "stone deduct*", "gross weight",
                                        "net weight"]),
    ("KYC & Customer Due Diligence", ["kyc", "know your customer", "identity", "id proof", "address proof",
                                      "aadhaar", "aadhar", "pan card", "photograph", "due diligence",
                                      "customer profile", "ckyc", "introduc*", "customer verification"]),
    ("Dual Custody, Vault & Key Control", ["dual custody", "joint custody", "joint custodian*", "custodian*",
                                           "key", "keys", "vault", "strong room", "strongroom", "safe", "locker",
                                           "custody"]),
    ("Packet Sealing & Tamper Evidence", ["packet*", "seal*", "pouch*", "tamper*", "envelope", "tag", "tags",
                                          "packing"]),
    ("Sanction, Valuation & LTV", ["ltv", "loan to value", "sanction*", "valuation", "rate per gram",
                                   "per gram rate", "eligib*", "over valu*", "overvalu*", "excess loan"]),
    ("Maker-Checker & Authorisation", ["maker", "checker", "authori*", "approv*", "override", "dual control",
                                       "second level", "sign off", "countersign*", "four eyes"]),
    ("Periodic / Surprise Verification & Audit", ["surprise", "periodic", "audit*", "verification", "inspection",
                                                  "concurrent", "not verified", "physical verification",
                                                  "stock verification", "re-appraisal", "reappraisal"]),
    ("Release, Renewal & Auction Control", ["release*", "redemption", "closure", "renewal", "auction*",
                                            "delivery", "handover", "hand over"]),
    ("Monitoring, MIS, CCTV & System Alerts", ["cctv", "camera", "system", "software", "mis", "alert*",
                                               "exception report*", "monitor*", "dashboard", "red flag*"]),
    ("Staff Competence & Training", ["training", "trained", "untrained", "inexperienc*", "new appraiser",
                                     "new staff", "awareness", "competen*", "skill*", "knowledge"]),
    ("Staff Rotation & Segregation of Duties", ["rotation", "rotat*", "transfer*", "long tenure", "segregation",
                                                "same person", "single person", "one person", "same staff",
                                                "alone", "single handed*"]),
    ("Linked Accounts & Customer Concentration", ["multiple loans", "same customer", "related", "relative*",
                                                  "family", "linked", "group of customers", "same address",
                                                  "same mobile", "same phone", "repeat customer", "introducer"]),
])

DETECTION_METHODS = OrderedDict([
    ("Gold Audit / Surprise Verification", ["audit*", "surprise", "physical verification", "verification",
                                            "inspection", "re-appraisal", "reappraisal", "re appraisal"]),
    ("Purity Test (Acid / Touchstone / XRF)", ["acid", "touchstone", "touch stone", "xrf", "karat meter",
                                              "karatmeter", "carat meter", "caratmeter", "purity test*",
                                              "salt solution", "specific gravity", "density"]),
    ("Cutting / Melting / Drilling", ["cutting", "cut open", "melt*", "drill*", "scratch*", "broke open"]),
    ("Customer Complaint", ["complain*", "customer approached", "grievance", "customer reported"]),
    ("Auction Process", ["auction*"]),
    ("Whistle-blower / Tip-off", ["whistle*", "tip off", "anonymous", "informant", "source information"]),
    ("CCTV / System / MIS Alert", ["cctv", "camera", "system alert", "exception report*", "mis report", "alert"]),
    ("Release / Renewal / Closure", ["at the time of release", "during release", "renewal", "redemption",
                                     "closure", "takeover"]),
    ("Police / External Intimation", ["police", "fir", "external agency", "court"]),
])

PURITY_TESTS = OrderedDict([
    ("Acid Test", ["acid", "nitric"]),
    ("Salt Solution / Specific Gravity Test", ["salt solution", "salt water", "specific gravity", "density"]),
    ("Touchstone Test", ["touchstone", "touch stone", "touch test"]),
    ("XRF / Karatmeter", ["xrf", "karat meter", "karatmeter", "carat meter", "caratmeter", "spectro*"]),
    ("Magnet Test", ["magnet*"]),
    ("Cutting / Drilling Test", ["cutting", "cut test", "drill*", "cut open"]),
    ("Melting Test", ["melt*"]),
    ("Weight Re-verification", ["re weigh*", "reweigh*", "weight verification", "weighed again", "re-weigh*"]),
])

ORNAMENTS = OrderedDict([
    ("Chain", ["chain*"]), ("Necklace / Haram", ["necklace*", "haram", "neck lace"]),
    ("Bangle / Kada", ["bangle*", "kada*", "kangan"]), ("Bracelet", ["bracelet*"]),
    ("Ring", ["ring", "rings", "finger ring*"]), ("Ear-ring / Stud / Jhumka", ["ear ring*", "earring*", "stud*", "jhumk*", "tops"]),
    ("Pendant / Dollar", ["pendant*", "dollar*", "locket*"]), ("Mangalsutra / Thali", ["mangal sutra*", "mangalsutra*", "thali*", "tali"]),
    ("Anklet", ["anklet*", "payal"]), ("Coin / Bar", ["coin*", "gold bar*", "biscuit*"]),
    ("Nose Pin", ["nose pin*", "nosepin*"]), ("Waist Belt / Oddiyanam", ["oddiyanam", "waist belt*", "vaddanam"]),
])

STAFF_WORDS = ["staff", "employee*", "branch manager", "manager", "appraiser*", "cashier*", "officer*",
               "custodian*", "bm", "abm", "teller", "executive*", "clerk", "insider*", "sales officer",
               "branch head", "joint custodian", "gold loan officer", "relationship manager", "valuer"]
CUSTOMER_WORDS = ["customer*", "borrower*", "pledger*", "pledgor*", "applicant*", "account holder*", "client*"]
EXTERNAL_WORDS = ["agent*", "broker*", "middleman", "middle man", "introducer*", "outsider*", "gang*",
                  "third party", "dsa", "goldsmith*", "jeweller*", "racket", "syndicate", "organised group"]
COLLUSION_WORDS = ["collusion", "collude*", "colluded", "connivance", "connive*", "in league", "nexus",
                   "hand in glove", "in connivance", "known to staff", "relative of staff", "relative of the staff",
                   "friend of", "introduced by staff", "introduced by the staff", "staff and customer",
                   "with the help of staff", "with the help of the staff", "aided by", "abetted", "staff s relative",
                   "insider help", "joint fraud"]
PROCESS_WORDS = ["error", "mistake", "inadvertent*", "oversight", "negligence", "negligent", "lapse",
                 "clerical", "human error", "non adherence", "non-adherence", "non compliance", "deviation"]
INTENT_WORDS = ["deliberate*", "intentional*", "knowingly", "absconded", "not traceable", "untraceable",
                "fraudulent*", "cheat*", "deceiv*", "deceit", "mala fide", "malafide", "dishonest*", "planned",
                "repeated", "fake", "forged", "spurious", "stolen", "tamper*", "swap*"]
NEGATION_STAFF = re.compile(
    r"(?:\b(?:no|not|none|nil|without)\b[^.;\n]{0,25}\b(?:staff|employee|official|insider)s?\b)|"
    r"(?:\b(?:staff|employee|official)s?\b[^.;\n]{0,25}\b(?:not|no)\s+(?:involved|found|role|involvement|complicity))",
    re.I)
NEGATION_CUSTOMER = re.compile(r"\b(?:no|not)\b[^.;\n]{0,15}\bcustomers?\b[^.;\n]{0,15}\binvolved\b", re.I)

RX = {}
for _grp in (FRAUD_TYPOLOGIES, CONTROL_CATEGORIES, DETECTION_METHODS, PURITY_TESTS, ORNAMENTS):
    for _k, _v in _grp.items():
        RX[_k] = _compile(_v)
RX_STAFF = _compile(STAFF_WORDS)
RX_CUST = _compile(CUSTOMER_WORDS)
RX_EXT = _compile(EXTERNAL_WORDS)
RX_COLL = _compile(COLLUSION_WORDS)
RX_PROC = _compile(PROCESS_WORDS)
RX_INTENT = _compile(INTENT_WORDS)

PERP_ORDER = ["Staff-Customer Collusion", "Staff (Insider)", "External Agent / Third Party", "Customer",
              "Process Lapse (no clear intent)", "Undetermined"]
PERP_COLORS = {"Staff-Customer Collusion": "#8E44AD", "Staff (Insider)": "#C0392B",
               "External Agent / Third Party": "#D35400", "Customer": "#2E86C1",
               "Process Lapse (no clear intent)": "#16A085", "Undetermined": "#95A5A6"}
RATING_ORDER = ["Critical", "High", "Medium", "Low"]
RATING_COLORS = {"Critical": "#C0392B", "High": "#E67E22", "Medium": "#D4AC0D", "Low": "#27AE60"}

STOPWORDS = set("""a about above after again against all also am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had has have having he
her here hers him his how i if in into is it its itself just me more most my no nor not now of off on once only or
other our out over own same she should so some such than that the their them then there these they this those
through to too under until up very was we were what when where which while who whom why will with would you your
yours shall may might must per via etc said also further thereof therein upon within without whether since
been being has have had one two three four five six seven eight nine ten was were rs inr nil na
branch customer customers gold loan loans incident report observed found date due noted xxx xxxx
""".split())


def fold_text(*parts):
    return "\n".join(p for p in parts if p and not is_placeholder(p))


def hits(rx, text):
    return len(rx.findall(text or ""))


def tokens(text):
    out = []
    for w in re.findall(r"[a-z][a-z\-]{2,}", (text or "").lower()):
        w = w.strip("-")
        if len(w) < 3 or w in STOPWORDS or re.fullmatch(r"x+", w):
            continue
        out.append(w)
    return out


# =============================================================================
#  SECTION 6 - ANALYTICS ENGINE
# =============================================================================
METRIC_COLUMNS = [
    "Loss (Rs L)", "Loss Basis", "Total Pledge Value (Rs L)", "Pledge Value Basis", "Gross Loss %",
    "Recovery Status", "Recovered (Rs L)", "Net Exposure (Rs L)",
    "Since (parsed)", "Observed (parsed)", "Detection Lag (days)", "Lag Bucket",
    "Primary Perpetrator", "Perpetrator Evidence", "Staff Involvement", "Staff Collusion Indicator",
    "Customer Intent to Defraud", "Fraud Typology", "Control Failure Categories", "No. of Control Gaps",
    "Detection Method", "Purity Tests Conducted", "Gold Weight (g)", "Accounts / Packets Involved",
    "Ornament Types", "Branch Repeat Count", "Similar Incidents (ML)", "Theme Cluster (ML)",
    "Red Flags", "Risk Score (0-100)", "Risk Rating", "Data Completeness %", "Read Status",
]


class Analyzer:
    def __init__(self, records, extra_cols):
        self.records = records
        self.extra_cols = extra_cols
        self.agg = {}

    # ------------------------------------------------------------------ per record
    def _perpetrator(self, r):
        weights = {"People Involved": 3.0, "Modus Operandi": 2.0, "What Happened": 1.5, "Narration": 1.2,
                   "How Discovered": 0.5, "Any Other Observation": 0.8}
        s = Counter()
        evidence = []
        for f, w in weights.items():
            t = r.get(f, "")
            if is_placeholder(t):
                continue
            neg_staff = bool(NEGATION_STAFF.search(t))
            st = hits(RX_STAFF, t)
            if neg_staff:
                st = max(0, st - len(NEGATION_STAFF.findall(t)))
                s["neg_staff"] += 1
            s["staff"] += st * w
            cu = hits(RX_CUST, t)
            if NEGATION_CUSTOMER.search(t):
                cu = 0
            s["cust"] += cu * w
            s["ext"] += hits(RX_EXT, t) * w
            s["coll"] += hits(RX_COLL, t) * w
            s["proc"] += hits(RX_PROC, t) * w
        if s["coll"] > 0:
            p = "Staff-Customer Collusion"
            evidence.append("collusion language")
        elif s["staff"] >= 1.5 and s["staff"] >= s["cust"] * 0.8 and not (s["neg_staff"] and s["staff"] < 3):
            p = "Staff (Insider)"
            if s["cust"] >= 3 and s["staff"] >= 3:
                p = "Staff-Customer Collusion"
                evidence.append("both staff and customer named as actors")
            else:
                evidence.append("staff named as actor")
        elif s["ext"] > 0 and s["ext"] >= s["cust"] * 0.5:
            p = "External Agent / Third Party"
            evidence.append("agent / third-party references")
        elif s["cust"] > 0:
            p = "Customer"
            evidence.append("customer named as actor")
        elif s["proc"] > 0:
            p = "Process Lapse (no clear intent)"
            evidence.append("error / negligence language")
        else:
            p = "Undetermined"
        if s["neg_staff"]:
            evidence.append("report states no staff involvement")
        return p, s, "; ".join(evidence)

    def analyse_record(self, r):
        m = OrderedDict()
        narrative = fold_text(r.get("Narration"), r.get("What Happened"), r.get("Modus Operandi"),
                              r.get("How Discovered"), r.get("People Involved"), r.get("Any Other Observation"),
                              r.get("_unassigned"))
        control_txt = fold_text(r.get("Control Failures"))
        steps_txt = fold_text(r.get("Steps Taken to Tighten Control"), r.get("Action Taken"))
        all_txt = fold_text(narrative, control_txt, steps_txt, r.get("Financial Impact"), r.get("Recovery"),
                            *[v for v in r.get("_extras", {}).values()])
        r["_narr"] = narrative
        r["_all"] = all_txt
        # money
        loss, basis = money_value(r.get("Financial Impact", ""), sum_all=True)
        if loss is None:
            amts = parse_amounts(narrative)
            if amts:
                loss, basis = max(a[0] for a in amts), "taken from narrative"
        rec_txt = r.get("Recovery", "")
        rec_amt, _ = money_value(rec_txt)
        tl = (rec_txt or "").lower()
        status = "Not stated"
        if re.search(r"\b(nil|none|zero|na|n/a)\b", tl) and not re.search(r"\d", tl):
            status = "Pending"
        elif not is_placeholder(rec_txt):
            if re.search(r"partial|partly|part recover|balance|remaining", tl):
                status = "Partial"
            elif re.search(r"\bpending\b|\bnil\b|not\s+(?:yet\s+)?recovered|no recovery|yet to|outstanding|"
                           r"under process|in progress|awaited|initiated|to be recovered|not recovered", tl):
                status = "Pending"
            elif re.search(r"fully|full recovery|recovered in full|entire|completely|closed|settled|recovered|"
                           r"realised|realized|repaid", tl):
                status = "Recovered"
            elif rec_amt:
                status = "Recovered"
            else:
                status = "Pending" if re.search(r"\bno\b|\bnot\b", tl) else "Not stated"
            if status == "Recovered" and rec_amt and loss and rec_amt < loss * 0.98:
                status = "Partial"
        if status == "Recovered":
            recovered = rec_amt if rec_amt is not None else loss
        elif status == "Partial":
            recovered = rec_amt
        else:
            recovered = 0.0 if loss is not None else None
        net = None
        if loss is not None:
            net = max(0.0, loss - (recovered or 0.0))
        r["_loss"], r["_recovered"], r["_net"] = loss, recovered, net
        m["Loss (Rs L)"] = fmt_l(loss)
        m["Loss Basis"] = basis
        # total pledge value / loan amount quoted in 'What Happened' (Rs lakhs)
        dot_p = []
        pv, pv_basis = pledge_value(r.get("What Happened", ""), r.get("Narration", ""), dot_p)
        r["_pledge"] = pv
        r["_dot_pledge"] = dot_p                                  # pledge amounts written with a '.' (as in the Word file)
        r["_dot_fin"] = dotted_amounts(r.get("Financial Impact", ""))
        m["Total Pledge Value (Rs L)"] = fmt_l(pv)
        m["Pledge Value Basis"] = pv_basis
        m["Gross Loss %"] = ("%.1f%%" % (100.0 * loss / pv)) if (loss is not None and pv) else "-"
        m["Recovery Status"] = status
        m["Recovered (Rs L)"] = fmt_l(recovered)
        m["Net Exposure (Rs L)"] = fmt_l(net)
        # dates
        observed = parse_date(r.get("Date Observed", "")) or parse_date(r.get("Report Date", ""))
        report_d = parse_date(r.get("Report Date", ""))
        since = parse_date(r.get("Since When", ""), ref=observed or report_d)
        lag = None
        if since and observed:
            lag = (observed - since).days
            if lag < 0:
                lag = None
        r["_since"], r["_obs"], r["_rep"], r["_lag"] = since, observed, report_d, lag
        m["Since (parsed)"] = fmt_date(since)
        m["Observed (parsed)"] = fmt_date(observed)
        m["Detection Lag (days)"] = "" if lag is None else str(lag)
        m["Lag Bucket"] = lag_bucket(lag)
        # perpetrator
        perp, sc, ev = self._perpetrator(r)
        # typology
        typ = [k for k in FRAUD_TYPOLOGIES if RX[k].search(narrative + "\n" + control_txt)]
        tests_txt = r.get("How Discovered", "") + "\n" + fold_text(r.get("What Happened"), r.get("Narration"))
        tests = self._tests(tests_txt)
        if not typ and any(t in tests for t in ("Acid Test", "Salt Solution / Specific Gravity Test",
                                                 "Touchstone Test", "XRF / Karatmeter", "Magnet Test")):
            typ = ["Spurious / Low-Purity Gold (inferred from tests)"]
        if not typ:
            typ = ["Other / Unclassified Abnormality"]
        # refine perpetrator using typology knowledge
        if perp == "Undetermined":
            if any(t in INSIDER_TYPOLOGIES for t in typ):
                perp, ev = "Staff (Insider)", "insider-type abnormality (custody/release/cash)"
            elif any(t in CUSTOMER_TYPOLOGIES for t in typ):
                perp, ev = "Customer", "customer-type abnormality (pledged gold not genuine)"
        r["_perp"] = perp
        m["Primary Perpetrator"] = perp
        m["Perpetrator Evidence"] = ev
        staff_neg = sc["neg_staff"] > 0
        if perp in ("Staff (Insider)", "Staff-Customer Collusion"):
            staff_inv = "Yes - indicated in report"
        elif staff_neg:
            staff_inv = "No - stated in report"
        elif sc["staff"] > 0:
            staff_inv = "Mentioned - role unclear"
        else:
            staff_inv = "Not stated"
        m["Staff Involvement"] = staff_inv
        cust_typ = any(t in CUSTOMER_TYPOLOGIES for t in typ)
        if perp == "Staff-Customer Collusion":
            coll = "Strong"
        elif perp == "Staff (Insider)" and sc["cust"] > 0:
            coll = "Possible - insider act involving customer accounts"
        elif cust_typ and hits(RX["Appraisal & Purity Testing"], control_txt + narrative) > 0:
            coll = ("Possible - non-genuine gold passed appraisal; validate appraiser"
                    if not staff_neg else "Low - report denies staff role; validate appraiser")
        elif cust_typ:
            coll = ("Possible - non-genuine gold accepted at pledge; validate appraiser"
                    if not staff_neg else "Low - report denies staff role; validate appraiser")
        else:
            coll = "Not indicated"
        r["_coll"] = coll
        m["Staff Collusion Indicator"] = coll
        intent_hits = hits(RX_INTENT, narrative)
        if perp in ("Customer", "Staff-Customer Collusion", "External Agent / Third Party") and (cust_typ or intent_hits >= 2):
            cint = "Strong"
        elif cust_typ or (sc["cust"] > 0 and intent_hits > 0):
            cint = "Indicative"
        else:
            cint = "Not indicated"
        r["_cint"] = cint
        m["Customer Intent to Defraud"] = cint
        r["_typ"] = typ
        m["Fraud Typology"] = "; ".join(typ)
        # control failures
        cats = []
        for k in CONTROL_CATEGORIES:
            score = hits(RX[k], control_txt) * 1.0 + hits(RX[k], steps_txt) * 0.5 + hits(RX[k], narrative) * 0.3
            if score >= 0.9:
                cats.append((k, score))
        cats.sort(key=lambda x: -x[1])
        catnames = [c[0] for c in cats]
        if not catnames and not is_placeholder(control_txt):
            catnames = ["Other / General Control Lapse"]
        r["_cats"] = catnames
        m["Control Failure Categories"] = "; ".join(catnames) if catnames else "Not stated"
        m["No. of Control Gaps"] = str(len(catnames))
        det = [k for k in DETECTION_METHODS if RX[k].search(r.get("How Discovered", "") or "")]
        if not det:
            det = [k for k in DETECTION_METHODS if RX[k].search(narrative)]
        if not det:
            det = ["Gold Audit / Surprise Verification (default - audit team report)"]
        r["_det"] = det
        m["Detection Method"] = "; ".join(det)
        r["_tests"] = tests
        m["Purity Tests Conducted"] = "; ".join(tests) if tests else "None recorded"
        wt = gold_weight(all_txt)
        r["_wt"] = wt
        m["Gold Weight (g)"] = "" if wt is None else ("%.2f" % wt)
        cnt = count_units(all_txt)
        r["_cnt"] = cnt
        m["Accounts / Packets Involved"] = "" if cnt is None else str(cnt)
        orn = [k for k in ORNAMENTS if RX[k].search(all_txt)]
        r["_orn"] = orn
        m["Ornament Types"] = "; ".join(orn)
        # completeness
        filled = sum(1 for f in KEY_FIELDS_FOR_QUALITY if not is_placeholder(r.get(f, "")))
        r["_complete"] = round(100.0 * filled / len(KEY_FIELDS_FOR_QUALITY))
        r["_missing"] = [f for f in KEY_FIELDS_FOR_QUALITY if is_placeholder(r.get(f, ""))]
        m["Data Completeness %"] = str(r["_complete"])
        r["_m"] = m

    def _tests(self, txt):
        """Purity tests actually conducted. Honours tick-boxes ([X] / [ ]) and ignores negated mentions
        such as 'without touchstone test' or 'did not perform acid test'."""
        found = []
        if "[X]" in txt or "[ ]" in txt:
            segs = re.split(r"(\[X\]|\[ \])", txt)
            state = None
            for seg in segs:
                if seg in ("[X]", "[ ]"):
                    state = seg
                    continue
                for k in PURITY_TESTS:
                    if RX[k].search(seg) and k not in found:
                        if state == "[ ]":
                            continue
                        found.append(k)
                state = None
            return found
        for k in PURITY_TESTS:
            for mt in RX[k].finditer(txt):
                pre = txt[max(0, mt.start() - 35):mt.start()].lower()
                if re.search(r"\b(without|not|no|never|failed to|skipped|instead of)\b[^.;\n]*$", pre):
                    continue
                found.append(k)
                break
        return found

    # ------------------------------------------------------------------ scoring
    def score_record(self, r):
        loss = r["_loss"]
        L = to_lakhs(loss if loss is not None else r.get("_pledge"))   # pledge value = exposure proxy if loss not stated
        if L is None:
            fin = 12
        elif L < 0.5:
            fin = 6
        elif L < 1:
            fin = 10
        elif L < 5:
            fin = 16
        elif L < 10:
            fin = 22
        elif L < 25:
            fin = 26
        else:
            fin = 30
        perp = {"Staff-Customer Collusion": 25, "Staff (Insider)": 22, "External Agent / Third Party": 16,
                "Customer": 13, "Process Lapse (no clear intent)": 6, "Undetermined": 10}[r["_perp"]]
        if r["_coll"].startswith("Possible"):
            perp = min(25, perp + 4)
        n = len(r["_cats"])
        ctrl = min(15, 5 * n) if n else 4
        st = r["_m"]["Recovery Status"]
        rec = {"Pending": 15, "Partial": 9, "Recovered": 2, "Not stated": 10}[st]
        lag = r["_lag"]
        if lag is None:
            lg = 5
        elif lag <= 7:
            lg = 2
        elif lag <= 30:
            lg = 4
        elif lag <= 90:
            lg = 6
        elif lag <= 180:
            lg = 8
        else:
            lg = 10
        ty = max([TYPOLOGY_SEVERITY.get(t, 1) for t in r["_typ"]] or [1])
        total = fin + perp + ctrl + rec + lg + ty
        if r.get("_branch_repeat", 1) > 1:
            total += 3
        if r.get("_similar"):
            total += 2
        total = int(min(100, total))
        rating = "Critical" if total >= 70 else "High" if total >= 55 else "Medium" if total >= 40 else "Low"
        r["_score"], r["_rating"] = total, rating
        r["_score_parts"] = OrderedDict([("Financial severity", fin), ("Perpetrator / intent", perp),
                                         ("Control gaps", ctrl), ("Recovery position", rec),
                                         ("Detection lag", lg), ("Typology severity", ty)])
        flags = []
        if r["_perp"] in ("Staff (Insider)", "Staff-Customer Collusion"):
            flags.append("Staff involvement indicated")
        if r["_perp"] == "Staff-Customer Collusion":
            flags.append("Possible staff-customer collusion")
        if "apprais" in r["_coll"] and not r["_coll"].startswith("Not"):
            flags.append("Non-genuine gold accepted at appraisal - appraiser role to be examined")
        if L is not None and L >= 5:
            flags.append("High value loss (>= Rs 5 L)")
        if L is None:
            flags.append("Financial impact not quantified")
        if st == "Pending":
            flags.append("Recovery pending")
        if lag is not None and lag > 90:
            flags.append("Undetected for %d days" % lag)
        if r["_cnt"] and r["_cnt"] >= 3:
            flags.append("Multiple accounts/packets (%d)" % r["_cnt"])
        if r.get("_branch_repeat", 1) > 1:
            flags.append("Repeat incident at same branch (%d)" % r["_branch_repeat"])
        if r.get("_similar"):
            flags.append("Similar MO in other report(s)")
        if any(t in ("Missing Gold / Packet Tampering / Pilferage", "Ornament Substitution / Swapping") for t in r["_typ"]):
            flags.append("Custody breach - packet/ornament integrity")
        if r["_complete"] < 60:
            flags.append("Report incomplete (%d%% fields)" % r["_complete"])
        r["_flags"] = flags

    # ------------------------------------------------------------------ ML: TF-IDF, similarity, k-means
    def _tfidf(self):
        docs = []
        for r in self.records:
            toks = tokens(fold_text(r.get("Narration"), r.get("What Happened"), r.get("Modus Operandi"),
                                    r.get("How Discovered"), r.get("Control Failures"), r.get("People Involved")))
            bigr = [toks[i] + " " + toks[i + 1] for i in range(len(toks) - 1)]
            docs.append(toks + bigr)
        N = len(docs)
        df = Counter()
        for d in docs:
            df.update(set(d))
        vecs = []
        for d in docs:
            tf = Counter(d)
            v = {}
            for t, c in tf.items():
                if df[t] == N and N > 3:
                    continue
                v[t] = (1 + math.log(c)) * (math.log((1 + N) / (1 + df[t])) + 1)
            if len(v) > 80:
                v = dict(sorted(v.items(), key=lambda kv: -kv[1])[:80])
            nrm = math.sqrt(sum(x * x for x in v.values())) or 1.0
            vecs.append({t: x / nrm for t, x in v.items()})
        return docs, df, vecs

    @staticmethod
    def _cos(a, b):
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(t, 0.0) for t, x in a.items())

    def _kmeans(self, vecs, k, iters=30):
        rnd = random.Random(7)
        idx = [i for i, v in enumerate(vecs) if v]
        if len(idx) < k:
            return None, None
        cents = [dict(vecs[rnd.choice(idx)])]
        while len(cents) < k:
            d2 = []
            for i in idx:
                best = max(self._cos(vecs[i], c) for c in cents)
                d2.append(max(0.0, 1 - best) ** 2)
            tot = sum(d2)
            if tot <= 0:
                break
            x = rnd.random() * tot
            acc = 0
            for i, w in zip(idx, d2):
                acc += w
                if acc >= x:
                    cents.append(dict(vecs[i]))
                    break
        k = len(cents)
        assign = {}
        for _ in range(iters):
            changed = False
            for i in idx:
                sims = [self._cos(vecs[i], c) for c in cents]
                a = max(range(k), key=lambda j: sims[j])
                if assign.get(i) != a:
                    assign[i] = a
                    changed = True
            new = []
            for j in range(k):
                mem = [vecs[i] for i in idx if assign[i] == j]
                c = Counter()
                for v in mem:
                    for t, x in v.items():
                        c[t] += x
                nrm = math.sqrt(sum(x * x for x in c.values())) or 1.0
                new.append({t: x / nrm for t, x in c.items()} if mem else cents[j])
            cents = new
            if not changed:
                break
        return assign, cents

    # ------------------------------------------------------------------ run everything
    def run(self):
        recs = self.records
        for r in recs:
            self.analyse_record(r)
        # branch repeats
        bcount = Counter(branch_key(r) for r in recs if branch_key(r) != "Not stated")
        for r in recs:
            r["_branch_repeat"] = bcount.get(branch_key(r), 1)
        # ML
        docs, df, vecs = self._tfidf()
        self.agg["vecs_nonempty"] = sum(1 for v in vecs if v)
        pairs = []
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                if vecs[i] and vecs[j]:
                    s = self._cos(vecs[i], vecs[j])
                    if s >= 0.30:
                        pairs.append((s, i, j))
        pairs.sort(reverse=True)
        sim_of = defaultdict(list)
        for s, i, j in pairs:
            sim_of[i].append((s, j))
            sim_of[j].append((s, i))
        for i, r in enumerate(recs):
            lst = sorted(sim_of.get(i, []), reverse=True)[:3]
            r["_similar"] = [(recs[j]["File Name"], s) for s, j in lst]
            r["_m"]["Similar Incidents (ML)"] = "; ".join("%s (%.0f%%)" % (f, s * 100) for f, s in r["_similar"])
        self.agg["pairs"] = [(s, recs[i], recs[j]) for s, i, j in pairs[:100]]
        n_ok = self.agg["vecs_nonempty"]
        clusters = []
        if n_ok >= 4:
            k = max(2, min(6, int(round(math.sqrt(n_ok / 2.0)))))
            assign, cents = self._kmeans(vecs, k)
            if assign:
                for j, c in enumerate(cents):
                    terms = [t for t, _ in sorted(c.items(), key=lambda x: -x[1]) if " " not in t][:5]
                    members = [i for i, a in assign.items() if a == j]
                    if not members:
                        continue
                    label = "C%d: %s" % (len(clusters) + 1, ", ".join(terms[:4]) if terms else "misc")
                    clusters.append({"label": label, "terms": terms, "members": members})
                    for i in members:
                        recs[i]["_cluster"] = label
        for r in recs:
            r["_m"]["Theme Cluster (ML)"] = r.get("_cluster", "Insufficient text" if n_ok < 4 else "Unclustered")
        self.agg["clusters"] = clusters
        # scoring after context
        for r in recs:
            self.score_record(r)
            m = r["_m"]
            m["Branch Repeat Count"] = str(r["_branch_repeat"])
            m["Red Flags"] = "; ".join(r["_flags"]) if r["_flags"] else "None"
            m["Risk Score (0-100)"] = str(r["_score"])
            m["Risk Rating"] = r["_rating"]
            m["Read Status"] = r.get("_status", "OK")
        self._aggregate(docs, df)
        return self.agg

    def _aggregate(self, docs, df):
        recs = self.records
        A = self.agg
        A["n"] = len(recs)
        A["branches"] = sorted(set(branch_key(r) for r in recs))
        A["regions"] = sorted(set(clean_one(r.get("Region")) for r in recs))
        A["total_loss"] = sum(r["_loss"] or 0 for r in recs)
        A["total_rec"] = sum(r["_recovered"] or 0 for r in recs)
        A["total_net"] = sum(r["_net"] or 0 for r in recs)
        A["quantified"] = sum(1 for r in recs if r["_loss"] is not None)
        A["total_pledge"] = sum(r.get("_pledge") or 0 for r in recs)
        A["pledge_n"] = sum(1 for r in recs if r.get("_pledge") is not None)
        _both = [(r["_loss"], r["_pledge"]) for r in recs if r["_loss"] is not None and r.get("_pledge")]
        A["loss_pct_pledge"] = (100.0 * sum(a for a, b in _both) / sum(b for a, b in _both)) if _both else None
        # Gross loss % = financial impact / pledge value involved (reports that state both)
        A["gl_n"] = len(_both)
        A["gl_loss"] = sum(a for a, b in _both)
        A["gl_pledge"] = sum(b for a, b in _both)
        A["gl_pct"] = A["loss_pct_pledge"]
        A["perp"] = Counter(r["_perp"] for r in recs)
        A["perp_loss"] = Counter()
        for r in recs:
            A["perp_loss"][r["_perp"]] += r["_loss"] or 0
        A["rating"] = Counter(r["_rating"] for r in recs)
        A["typ"] = Counter(t for r in recs for t in r["_typ"])
        A["typ_loss"] = Counter()
        for r in recs:
            for t in r["_typ"]:
                A["typ_loss"][t] += (r["_loss"] or 0) / max(1, len(r["_typ"]))
        A["cats"] = Counter(c for r in recs for c in r["_cats"])
        A["cat_loss"] = Counter()
        A["cat_branches"] = defaultdict(set)
        for r in recs:
            for c in r["_cats"]:
                A["cat_loss"][c] += r["_loss"] or 0
                A["cat_branches"][c].add(branch_key(r))
        A["det"] = Counter(d for r in recs for d in r["_det"])
        A["tests"] = Counter(t for r in recs for t in r["_tests"])
        A["orn"] = Counter(o for r in recs for o in r["_orn"])
        A["recovery"] = Counter(r["_m"]["Recovery Status"] for r in recs)
        A["lagb"] = Counter(r["_m"]["Lag Bucket"] for r in recs)
        lags = sorted(r["_lag"] for r in recs if r["_lag"] is not None)
        A["lags"] = lags
        A["median_lag"] = lags[len(lags) // 2] if lags else None
        A["coll"] = Counter(r["_coll"].split(" - ")[0] for r in recs)
        A["cint"] = Counter(r["_cint"] for r in recs)
        heat = defaultdict(Counter)
        for r in recs:
            for c in (r["_cats"] or ["Not stated"]):
                heat[r["_perp"]][c] += 1
        A["heat"] = heat
        month = Counter()
        for r in recs:
            d = r["_obs"] or r["_rep"] or r["_since"]
            month[d.strftime("%Y-%m") if d else "Undated"] += 1
        A["month"] = month
        rm = {}
        for r in recs:
            rm.setdefault(month_key(r), Counter())[r["_rating"]] += 1
        A["rating_month"] = rm
        gl_month = OrderedDict()
        for r in recs:
            if r["_loss"] is not None and r.get("_pledge"):
                d = r["_obs"] or r["_rep"] or r["_since"]
                kk = d.strftime("%Y-%m") if d else "Undated"
                e_ = gl_month.setdefault(kk, [0.0, 0.0, 0])
                e_[0] += r["_loss"]
                e_[1] += r["_pledge"]
                e_[2] += 1
        A["gl_month"] = gl_month
        gl_branch = OrderedDict()
        for r in recs:
            if r["_loss"] is not None and r.get("_pledge"):
                e_ = gl_branch.setdefault(branch_key(r), [0.0, 0.0, 0])
                e_[0] += r["_loss"]
                e_[1] += r["_pledge"]
                e_[2] += 1
        A["gl_branch"] = gl_branch
        gl_bm = OrderedDict()
        gl_lag = OrderedDict()
        for r in recs:
            if is_paired(r):
                for dct, key in ((gl_bm.setdefault(branch_key(r), OrderedDict()), month_key(r)),):
                    e_ = dct.setdefault(key, [0.0, 0.0, 0])
                    e_[0] += r["_loss"]
                    e_[1] += r["_pledge"]
                    e_[2] += 1
                e_ = gl_lag.setdefault(lag_bucket(r.get("_lag")), [0.0, 0.0, 0])
                e_[0] += r["_loss"]
                e_[1] += r["_pledge"]
                e_[2] += 1
        A["gl_bm"] = gl_bm
        A["gl_lag"] = gl_lag
        # branch / region tables
        bt = OrderedDict()
        for r in recs:
            b = branch_key(r)
            e = bt.setdefault(b, {"n": 0, "loss": 0.0, "net": 0.0, "score": 0, "max": "Low", "region": clean_one(r.get("Region")),
                                  "area": clean_one(r.get("Area")), "perp": Counter(), "pending": 0, "pledge": 0.0,
                                  "gl_loss": 0.0, "gl_pledge": 0.0})
            e["n"] += 1
            e["loss"] += r["_loss"] or 0
            e["pledge"] += r.get("_pledge") or 0
            if r["_loss"] is not None and r.get("_pledge"):
                e["gl_loss"] += r["_loss"]
                e["gl_pledge"] += r["_pledge"]
            e["net"] += r["_net"] or 0
            e["score"] += r["_score"]
            e["perp"][r["_perp"]] += 1
            if r["_m"]["Recovery Status"] == "Pending":
                e["pending"] += 1
            if RATING_ORDER.index(r["_rating"]) < RATING_ORDER.index(e["max"]):
                e["max"] = r["_rating"]
        A["branch_tbl"] = bt
        rt = OrderedDict()
        for r in recs:
            g = clean_one(r.get("Region"))
            e = rt.setdefault(g, {"n": 0, "loss": 0.0, "branches": set(), "score": 0, "staff": 0, "pledge": 0.0})
            e["n"] += 1
            e["loss"] += r["_loss"] or 0
            e["pledge"] += r.get("_pledge") or 0
            e["branches"].add(branch_key(r))
            e["score"] += r["_score"]
            if r["_perp"] in ("Staff (Insider)", "Staff-Customer Collusion"):
                e["staff"] += 1
        A["region_tbl"] = rt
        # Pareto
        bl = sorted((e["loss"] for e in bt.values()), reverse=True)
        tot = sum(bl)
        if tot > 0 and bl:
            top = max(1, int(math.ceil(len(bl) * 0.2)))
            A["pareto"] = (top, len(bl), 100.0 * sum(bl[:top]) / tot)
        else:
            A["pareto"] = None
        # keywords
        A["top_terms"] = [(t, c) for t, c in df.most_common(400) if " " not in t][:30]
        A["top_bigrams"] = [(t, c) for t, c in df.most_common(800) if " " in t][:20]
        perp_terms = {}
        for p in PERP_ORDER:
            c = Counter()
            for r, d in zip(recs, docs):
                if r["_perp"] == p:
                    c.update(t for t in set(d) if " " not in t)
            if c:
                perp_terms[p] = c.most_common(8)
        A["perp_terms"] = perp_terms
        # entity link analysis
        A["links"] = entity_links(recs)
        # data quality
        fq = OrderedDict()
        for f in FIELD_NAMES:
            fq[f] = sum(1 for r in recs if not is_placeholder(r.get(f, "")))
        A["field_quality"] = fq
        A["avg_complete"] = (sum(r["_complete"] for r in recs) / len(recs)) if recs else 0
        A["staff_share"] = (100.0 * (A["perp"]["Staff (Insider)"] + A["perp"]["Staff-Customer Collusion"]) / len(recs)) if recs else 0
        A["test_effect"] = Counter()
        for r in recs:
            for t in r["_tests"]:
                A["test_effect"][t] += 1


def lag_bucket(lag):
    if lag is None:
        return "Unknown"
    if lag <= 7:
        return "0-7 days"
    if lag <= 30:
        return "8-30 days"
    if lag <= 90:
        return "31-90 days"
    if lag <= 180:
        return "91-180 days"
    return "> 180 days"


LAG_ORDER = ["0-7 days", "8-30 days", "31-90 days", "91-180 days", "> 180 days", "Unknown"]


# ---- Gross loss % helpers  (Gross loss % = financial impact / pledge value involved)
def month_key(r):
    d = r.get("_obs") or r.get("_rep") or r.get("_since")
    return d.strftime("%Y-%m") if d else "Undated"


def rating_month_items(A, max_months=12):
    """[(month label, {rating: count})] for the last months (+ Undated) - used by the stacked risk-rating chart."""
    ms = sorted(k for k in A["rating_month"] if k != "Undated")[-max_months:]
    items = [(month_label(k), dict(A["rating_month"][k])) for k in ms]
    if A["rating_month"].get("Undated"):
        items.append(("Undated", dict(A["rating_month"]["Undated"])))
    return items


STACK_ORDER = ["Low", "Medium", "High", "Critical"]      # bottom -> top of each stacked bar


def month_label(k):
    try:
        return dt.datetime.strptime(k, "%Y-%m").strftime("%b-%y")
    except Exception:
        return k


def is_paired(r):
    """Report that states BOTH a financial impact and a pledge value (needed for Gross loss %)."""
    return r.get("_loss") is not None and (r.get("_pledge") or 0) > 0


def pct_of(loss, pledge):
    return 100.0 * loss / pledge if pledge else None


def nice_step(x):
    """Round a step size up to 1 / 2 / 2.5 / 5 x 10^k."""
    if x <= 0:
        return 1.0
    e = math.floor(math.log10(x))
    for m_ in (1, 2, 2.5, 5, 10):
        if m_ * 10 ** e >= x * 0.999:
            return m_ * 10 ** e
    return 10 ** (e + 1)


def dynamic_bins(values, n):
    """Band edges built from the data itself: about n equal bands with round boundaries."""
    vals = [v for v in values if v is not None]
    if not vals:
        return []
    lo, hi = min(vals), max(vals)
    n = max(1, int(n))
    if hi - lo < 1e-9:
        base = nice_step(abs(hi) / 2.0 or 1.0)
        return [math.floor(lo / base) * base, math.floor(lo / base) * base + base]
    step = nice_step((hi - lo) / n)
    start = math.floor(lo / step + 1e-9) * step
    edges = [start]
    while edges[-1] < hi - 1e-9:
        edges.append(round(edges[-1] + step, 10))
    if len(edges) < 2:
        edges.append(edges[0] + step)
    return edges


def band_index(edges, v):
    return max(0, min(bisect_right(edges, v + 1e-12) - 1, len(edges) - 2))


def band_labels(edges, unit=""):
    step = min((edges[i + 1] - edges[i]) for i in range(len(edges) - 1))
    dec = 0 if step >= 1 and all(abs(e - round(e)) < 1e-9 for e in edges) else (1 if step >= 0.1 else 2)
    f = "%%.%df" % dec
    return [(f % edges[i]) + " - " + (f % edges[i + 1]) + unit for i in range(len(edges) - 1)]


def auto_range(values, n=5):
    """Suggested (min, max, bin size) taken from the data - used to pre-fill the Min / Max / Bin inputs."""
    e = dynamic_bins(values, n)
    if len(e) < 2:
        return 0.0, 1.0, 1.0
    return e[0], e[-1], round(e[1] - e[0], 10)


def fixed_edges(lo, hi, step):
    """Band edges lo, lo+step, ... up to hi (the last band is cut at hi)."""
    edges = [lo]
    while edges[-1] < hi - 1e-9:
        edges.append(min(round(edges[-1] + step, 10), hi))
    return edges


def fixed_labels(edges, unit=""):
    """['<Min', 'a - b', ..., '>Max'] - values below Min and above Max get their own groups."""
    dec = 0 if all(abs(e - round(e)) < 1e-9 for e in edges) else (1 if all(abs(e * 10 - round(e * 10)) < 1e-9 for e in edges) else 2)
    f = lambda v: ("%%.%df" % dec) % v
    return (["<" + f(edges[0]) + unit] + [f(edges[i]) + " - " + f(edges[i + 1]) + unit for i in range(len(edges) - 1)] +
            [">" + f(edges[-1]) + unit])


def fixed_index(edges, v):
    """0 = below Min, 1..n = regular bands (Max itself stays in the last band), n+1 = above Max."""
    if v < edges[0] - 1e-9:
        return 0
    if v > edges[-1] + 1e-9:
        return len(edges)
    return min(bisect_right(edges, v + 1e-12) - 1, len(edges) - 2) + 1


def build_crosstab(recs, prange=None, grange=None):
    """Count of reports by Total Pledge Value band (rows, Rs L) x Gross loss % band (columns).
    prange / grange = (Min, Max, Bin size); None = suggested from the data.  Reports below Min are grouped in
    '<Min', above Max in '>Max'.  Only reports stating both loss and pledge value are included."""
    base = [r for r in recs if is_paired(r)]
    if not base:
        return None
    pv = [r["_pledge"] / 1e5 for r in base]
    gl = [100.0 * r["_loss"] / r["_pledge"] for r in base]
    prange = prange or auto_range(pv)
    grange = grange or auto_range(gl)
    pe, ge = fixed_edges(*prange), fixed_edges(*grange)
    rows, cols = fixed_labels(pe, " L"), fixed_labels(ge, " %")
    cells = {}
    for r, v, g in zip(base, pv, gl):
        cells.setdefault((fixed_index(pe, v), fixed_index(ge, g)), []).append(r)
    return {"rows": rows, "cols": cols, "cells": cells, "n": len(base), "pledge_edges": pe, "loss_edges": ge,
            "prange": prange, "grange": grange}


def gl_bm_grid(A, top=None, max_months=None, sort="pledge", desc=True):
    """Branch x month Gross loss % grid: rows, month columns, cell / row / column totals, grand total."""
    bm_tot = {b: [sum(v[0] for v in d.values()), sum(v[1] for v in d.values()), sum(v[2] for v in d.values())]
              for b, d in A["gl_bm"].items()}
    keyf = {"loss": lambda v: pct_of(v[0], v[1]) or 0, "impact": lambda v: v[0], "count": lambda v: v[2],
            "pledge": lambda v: v[1]}[sort]
    rows = sorted(bm_tot, key=lambda b: b)                      # name order for ties
    rows.sort(key=lambda b: keyf(bm_tot[b]), reverse=desc)
    if top:
        rows = rows[:top]
    cols = sorted({k for d in A["gl_bm"].values() for k in d if k != "Undated"})
    if max_months:
        cols = cols[-max_months:]
    cells = {(b, k): (pct_of(v[0], v[1]), v[2]) for b in rows for k, v in A["gl_bm"][b].items() if k in cols and v[1]}
    row_tot = {b: (pct_of(bm_tot[b][0], bm_tot[b][1]), bm_tot[b][2]) for b in rows}
    col_tot = {}
    for k in cols:
        L = sum(d[k][0] for d in A["gl_bm"].values() if k in d)
        P = sum(d[k][1] for d in A["gl_bm"].values() if k in d)
        n_ = sum(d[k][2] for d in A["gl_bm"].values() if k in d)
        if P:
            col_tot[k] = (pct_of(L, P), n_)
    grand = (A["gl_pct"], A["gl_n"]) if A["gl_pct"] is not None else None
    return rows, cols, cells, row_tot, col_tot, grand


def lag_commentary(A):
    """Plain-language reading of the detection-lag chart and the Gross loss % in each lag bucket."""
    tot = sum(A["lagb"].values())
    if not tot:
        return "No reports to comment on."
    out = []
    unknown = A["lagb"].get("Unknown", 0)
    known = tot - unknown
    if known:
        top = max((k for k in LAG_ORDER if k != "Unknown"), key=lambda k: A["lagb"].get(k, 0))
        late = A["lagb"].get("91-180 days", 0) + A["lagb"].get("> 180 days", 0)
        t = "%d of %d reports have a measurable lag; most (%d) are in the %s band" % (known, tot, A["lagb"].get(top, 0), top)
        t += ", and %d (%.0f%%) were detected after 90 days" % (late, 100.0 * late / known)
        if A.get("median_lag") is not None:
            t += " (median lag %d days)" % A["median_lag"]
        out.append(t + ".")
    if unknown:
        out.append("%d report(s) have no usable 'Since when' date, so their lag could not be measured." % unknown)
    gl = {k: (pct_of(v[0], v[1]), v[2]) for k, v in A["gl_lag"].items() if v[1]}
    if gl and A.get("gl_pct") is not None:
        hi = max(gl, key=lambda k: gl[k][0])
        out.append("Gross loss %% is highest in the %s band (%.1f%%, %d report(s)) against %.1f%% overall." %
                   (hi, gl[hi][0], gl[hi][1], A["gl_pct"]))

        def pool(keys):
            L = sum(A["gl_lag"][k][0] for k in keys if k in A["gl_lag"])
            P = sum(A["gl_lag"][k][1] for k in keys if k in A["gl_lag"])
            return pct_of(L, P)
        e_, l_ = pool(("0-7 days", "8-30 days")), pool(("91-180 days", "> 180 days"))
        if e_ is not None and l_ is not None:
            if l_ > e_:
                out.append("Cases found after 90 days lose %.1f%% of pledge value against %.1f%% for those caught within "
                           "30 days - late detection goes with larger losses, so earlier verification should cut the loss." % (l_, e_))
            else:
                out.append("Cases found after 90 days lose %.1f%% of pledge value against %.1f%% for those caught within "
                           "30 days - no sign here that delay alone drives the loss ratio." % (l_, e_))
        out.append("Gross loss %% uses the %d report(s) stating both loss and pledge value; bands with fewer than 3 reports "
                   "are indicative only." % A["gl_n"])
    else:
        out.append("Gross loss % cannot be shown: no report states both a financial impact and a pledge value.")
    return "\n".join("• " + x for x in out)


def open_file(path):
    """Open a file with its default program (Word for .doc / .docx)."""
    try:
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False


def clean_one(v):
    v = (v or "").split("\n")[0].strip()
    return v if v and not is_placeholder(v) else ("Not stated" if not v else v)


def branch_key(r):
    v = clean_branch_line((r.get("Branch") or "").split("\n")[0])
    return v or "Not stated"


def entity_links(recs):
    """Same person / ID / phone / account appearing in more than one report => possible ring."""
    occ = defaultdict(set)
    kinds = {}
    skip = set()
    for r in recs:
        skip.add(branch_key(r))
        skip.add(branch_key(r).split(" ")[0])
        for v in (r.get("Incident Report No", ""),):
            skip.add(v.strip().upper())
    for idx, r in enumerate(recs):
        text = r.get("_all", "")
        for m in re.finditer(r"\b(?:Mr|Mrs|Ms|Miss|Shri|Smt|Sri|Kum|Dr)\.?\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]*\.?){0,2})", text):
            key = m.group(1).strip().upper()
            occ[key].add(idx)
            kinds[key] = "Person name"
        for m in re.finditer(r"(?<!\d)([6-9]\d{9})(?!\d)", text):
            occ[m.group(1)].add(idx)
            kinds[m.group(1)] = "Mobile number"
        for m in re.finditer(r"\b(?=[A-Z0-9/\-]*\d)(?=[A-Z0-9/\-]*[A-Z])[A-Z0-9][A-Z0-9/\-]{5,}\b", text):
            key = m.group(0).strip("-/")
            if key in skip or re.fullmatch(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", key):
                continue
            occ[key].add(idx)
            kinds.setdefault(key, "Account / ID / Code")
        for m in re.finditer(r"\b(?:emp(?:loyee)?\.?\s*(?:id|code|no)\.?\s*[:\-]?\s*)(\w+)", text, re.I):
            key = "EMP " + m.group(1).upper()
            occ[key].add(idx)
            kinds[key] = "Employee ID"
    out = []
    for key, s in occ.items():
        if len(s) >= 2:
            out.append((kinds.get(key, ""), key, [recs[i]["File Name"] for i in sorted(s)],
                        sorted(set(branch_key(recs[i]) for i in s))))
    out.sort(key=lambda x: (-len(x[2]), x[1]))
    return out[:200]

# =============================================================================
#  SECTION 7 - INSIGHTS AND RECOMMENDATIONS (generated from the data)
# =============================================================================
CONTROL_RECOS = {
    "Appraisal & Purity Testing": [
        "Make a two-stage appraisal mandatory: branch appraiser + independent second appraiser (or regional "
        "rover) for every loan above a threshold (for example Rs 2 L or 50 g) and for every first-time customer.",
        "Use XRF / karatmeter at hub branches and make the acid + touchstone + salt-solution (specific gravity) "
        "tests compulsory, with the test result recorded in the system before sanction.",
        "Track appraiser-wise exception rates (spurious / low-purity found later) and link them to incentives, "
        "re-certification and penalty for repeated failures.",
    ],
    "Weighing & Weight Verification": [
        "Calibrate weighing scales monthly with certified weights; keep the calibration log at branch and audit it.",
        "Record gross weight, stone deduction and net weight separately with photographs of the scale reading.",
        "Flag loans where net weight / gross weight ratio is unusually high for stone-studded ornaments.",
    ],
    "KYC & Customer Due Diligence": [
        "Enforce full KYC with Aadhaar / CKYC verification and live photograph before disbursement; block "
        "disbursement in the system when KYC is incomplete.",
        "Run de-duplication on mobile number, address and ID across customers to detect name-lending and benami loans.",
        "Apply enhanced due diligence for walk-in customers pledging large weight on the first visit.",
    ],
    "Dual Custody, Vault & Key Control": [
        "Enforce dual custody (two key holders) for strong room / safe; key handover register to be signed with time.",
        "Prohibit a single staff member from accessing gold packets; CCTV coverage of strong room with 90-day storage.",
        "Surprise key-register and packet-count checks by area manager at least once a month.",
    ],
    "Packet Sealing & Tamper Evidence": [
        "Use serially numbered tamper-evident pouches; record pouch number, weight and photograph in the system.",
        "Re-weigh the sealed packet at every audit and at release; any variance to trigger an immediate incident report.",
        "Customer and appraiser signature across the seal; packet opening only under dual custody with reason logged.",
    ],
    "Sanction, Valuation & LTV": [
        "System-enforced LTV cap (as per RBI norms) with the gold rate auto-fed daily; no manual override of rate.",
        "Exception report of loans sanctioned at > 90% of eligible amount, and of loans renewed with top-up, "
        "for daily review by the regional office.",
    ],
    "Maker-Checker & Authorisation": [
        "Separate the roles of appraiser, sanctioning officer and cash payer; system to block same-user maker-checker.",
        "Overrides and manual sanctions to need second-level approval with mandatory remarks; review weekly.",
    ],
    "Periodic / Surprise Verification & Audit": [
        "Increase the frequency of surprise gold audits for high-risk branches (repeat incidents / high value) to monthly.",
        "Use risk-based sampling: 100% verification of high-value, first-time-customer and recently renewed packets.",
        "Rotate gold auditors across regions so that the same auditor does not audit the same branch repeatedly.",
    ],
    "Release, Renewal & Auction Control": [
        "Release only after full repayment reflects in the system, with OTP / biometric of the customer.",
        "Re-test purity and weight at renewal/top-up and before auction; auction lots to be re-appraised by a third party.",
    ],
    "Monitoring, MIS, CCTV & System Alerts": [
        "Build daily exception MIS: same-day pledge and release, frequent renewals, high LTV, high weight per customer, "
        "multiple loans on the same mobile/address, and staff-introduced customers.",
        "Integrate CCTV health monitoring and retain footage for at least 90 days; review footage for every incident.",
    ],
    "Staff Competence & Training": [
        "Conduct periodic hands-on training on spurious gold detection (plated, filled, hollow, tungsten/copper core).",
        "Certify appraisers annually; share a 'modus operandi bulletin' of new fraud techniques with all branches.",
    ],
    "Staff Rotation & Segregation of Duties": [
        "Mandatory rotation of branch manager / appraiser / custodian every 2-3 years and compulsory leave of "
        "at least 10 consecutive days, during which another person handles gold custody.",
        "No staff member to hold appraisal, custody and cash roles simultaneously.",
    ],
    "Linked Accounts & Customer Concentration": [
        "Link analysis of customers by mobile, address, introducer and nominee; cap the exposure per linked group.",
        "Customers introduced by staff or their relatives to be flagged and verified by another branch.",
    ],
    "Other / General Control Lapse": [
        "Map each incident to the SOP clause that failed and update the SOP / checklist accordingly.",
    ],
}
PERP_RECOS = {
    "Staff (Insider)": "Insider cases: initiate staff accountability review, forensic review of the staff member's "
                       "other loans, lifestyle check, and consider police complaint where misappropriation is proven.",
    "Staff-Customer Collusion": "Collusion cases: review all loans sanctioned / appraised by the same staff for the "
                                "same customer group; block the customer group; independent re-appraisal of their "
                                "live packets; vigilance investigation.",
    "Customer": "Customer-driven cases: flag the customer and linked KYC (mobile/address/ID) in a negative list "
                "shared across branches; recall the loan and file police complaint for spurious gold (cheating).",
    "External Agent / Third Party": "Agent / gang cases: share alert with all branches in the region, check CCTV, "
                                    "and trace other loans with the same introducer or same pattern.",
    "Process Lapse (no clear intent)": "Process lapses: re-train the branch and add a system control so that the "
                                       "lapse cannot be repeated manually.",
    "Undetermined": "Undetermined cases: incident reports should clearly state 'People involved' and 'Modus operandi'; "
                    "make these fields mandatory in the reporting template.",
}


def generate_insights(an):
    A, recs = an.agg, an.records
    out = []
    if not recs:
        return ["No records found."]
    n = A["n"]
    out.append("%d incident report(s) analysed covering %d branch(es) and %d region(s)." %
               (n, len([b for b in A["branches"] if b != "Not stated"]) or len(A["branches"]),
                len([g for g in A["regions"] if g != "Not stated"]) or len(A["regions"])))
    if A["quantified"]:
        pend = A["total_net"]
        out.append("Quantified financial impact: Rs %.2f L in %d report(s); recovered Rs %.2f L; net exposure "
                   "Rs %.2f L (%.0f%% of the impact)." % (A["total_loss"] / 1e5, A["quantified"], A["total_rec"] / 1e5,
                                                       pend / 1e5, 100.0 * pend / A["total_loss"] if A["total_loss"] else 0))
    if A["pledge_n"]:
        line = "Total pledge value / loan amount quoted in 'What happened': Rs %.2f L across %d report(s)" % (
            A["total_pledge"] / 1e5, A["pledge_n"])
        out.append(line + ".")
        if A["gl_pct"] is not None:
            gb = [(b, 100.0 * v[0] / v[1], v[2]) for b, v in A["gl_branch"].items() if v[1]]
            line = ("Gross loss %% (financial impact / pledge value involved): %.1f%% - Rs %.2f L impact on Rs %.2f L "
                    "pledge value, %d report(s) stating both" % (A["gl_pct"], A["gl_loss"] / 1e5, A["gl_pledge"] / 1e5, A["gl_n"]))
            if gb:
                b, pct, c = max(gb, key=lambda x: x[1])
                line += "; highest at branch %s (%.1f%%)" % (b, pct)
            out.append(line + ".")
    nq = n - A["quantified"]
    if nq:
        out.append("%d report(s) do not quantify the financial impact in rupees - this weakens loss provisioning." % nq)
    if A["perp"]:
        top, c = A["perp"].most_common(1)[0]
        out.append("Primary possible perpetrator: %s in %d of %d case(s) (%.0f%%). Staff / collusion share is %.0f%%." %
                   (top, c, n, 100.0 * c / n, A["staff_share"]))
    possible = sum(v for k, v in A["coll"].items() if k.startswith("Possible") or k == "Strong")
    if possible:
        out.append("%d case(s) carry a staff-collusion indicator (strong or possible) - non-genuine gold cannot "
                   "pass a proper appraisal without negligence or connivance; appraiser roles need validation." % possible)
    if A["typ"]:
        t, c = A["typ"].most_common(1)[0]
        out.append("Dominant abnormality pattern: %s (%d case(s))." % (t, c))
    if A["cats"]:
        cat, c = A["cats"].most_common(1)[0]
        out.append("Most frequent control lapse: %s - %d case(s), loss involved Rs %.2f L, %d branch(es)." %
                   (cat, c, A["cat_loss"][cat] / 1e5, len(A["cat_branches"][cat])))
    if A["median_lag"] is not None:
        long_ = sum(1 for x in A["lags"] if x > 90)
        out.append("Median detection lag (start of abnormality to observation): %d day(s); %d case(s) ran "
                   "undetected for more than 90 days." % (A["median_lag"], long_))
    rep = [(b, e["n"]) for b, e in A["branch_tbl"].items() if e["n"] > 1 and b != "Not stated"]
    if rep:
        rep.sort(key=lambda x: -x[1])
        out.append("Repeat-incident branches: " + ", ".join("%s (%d)" % x for x in rep[:6]) + ".")
    cross = [p for p in A["pairs"] if branch_key(p[1]) != branch_key(p[2])]
    if cross:
        out.append("%d pair(s) of reports from different branches show a similar modus operandi (text similarity "
                   ">= 30%%) - possible organised group moving across branches." % len(cross))
    if A["links"]:
        out.append("%d name / ID / phone / account reference(s) appear in more than one report - see Deeper "
                   "Analysis > Entity Links." % len(A["links"]))
    if A["pareto"]:
        top, tot, pct = A["pareto"]
        out.append("Concentration: top %d of %d branch(es) account for %.0f%% of the quantified loss." % (top, tot, pct))
    crit = A["rating"].get("Critical", 0) + A["rating"].get("High", 0)
    out.append("%d case(s) rated Critical/High on the composite risk score; average report completeness %.0f%%." %
               (crit, A["avg_complete"]))
    return out


def generate_recommendations(an):
    A, recs = an.agg, an.records
    recos = []
    if not recs:
        return recos
    n = A["n"]
    for cat, c in A["cats"].most_common():
        share = 100.0 * c / n
        pr = "HIGH" if (share >= 30 or A["cat_loss"][cat] >= 10e5) else ("MEDIUM" if share >= 10 else "LOW")
        why = "%d case(s) (%.0f%%), loss involved Rs %.2f L, %d branch(es)" % (c, share, A["cat_loss"][cat] / 1e5,
                                                                            len(A["cat_branches"][cat]))
        for txt in CONTROL_RECOS.get(cat, []):
            recos.append((pr, "Control gap: " + cat, txt, why))
    for p, c in A["perp"].most_common():
        if p in PERP_RECOS:
            pr = "HIGH" if p in ("Staff (Insider)", "Staff-Customer Collusion") else ("MEDIUM" if c / n >= 0.2 else "LOW")
            recos.append((pr, "Perpetrator: " + p, PERP_RECOS[p], "%d case(s)" % c))
    possible = sum(v for k, v in A["coll"].items() if k.startswith("Possible") or k == "Strong")
    if possible:
        recos.append(("HIGH", "Staff collusion risk",
                      "For every case where spurious / low-purity gold was accepted, obtain the appraiser's "
                      "explanation, review all other loans appraised by the same appraiser in the last 12 months "
                      "and re-test a sample of live packets.", "%d case(s) with collusion indicator" % possible))
    if A["recovery"].get("Pending", 0):
        recos.append(("HIGH", "Recovery", "Set a recovery timeline per case (notice, auction of other pledges of the "
                      "customer, staff liability, insurance claim); CFO review of pending recovery fortnightly.",
                      "%d case(s) pending, net exposure Rs %.2f L" % (A["recovery"]["Pending"], A["total_net"] / 1e5)))
    if A["lags"] and any(x > 90 for x in A["lags"]):
        recos.append(("HIGH", "Detection speed", "Abnormalities stayed undetected beyond 90 days. Increase audit "
                      "frequency for high-risk branches, add re-appraisal at renewal, and run monthly analytics "
                      "on exception MIS.", "median lag %s day(s)" % A["median_lag"]))
    rep = [b for b, e in A["branch_tbl"].items() if e["n"] > 1 and b != "Not stated"]
    if rep:
        recos.append(("HIGH", "Branch focus", "Place these branches under enhanced monitoring (monthly surprise audit, "
                      "staff rotation review, 100% re-appraisal of high-value packets): " + ", ".join(rep[:15]),
                      "repeat incidents"))
    cross = [p for p in A["pairs"] if branch_key(p[1]) != branch_key(p[2])]
    if cross or A["links"]:
        recos.append(("HIGH", "Organised fraud", "Similar MO / common identifiers across branches - issue a regional "
                      "fraud alert with the MO, and run a portfolio scan for loans matching the same pattern.",
                      "%d similar pairs, %d shared identifiers" % (len(cross), len(A["links"]))))
    if A["quantified"] < n:
        recos.append(("MEDIUM", "Reporting quality", "Make 'Financial impact (Rs)', 'People involved', 'Modus "
                      "operandi' and 'Since when' mandatory structured fields in the incident template "
                      "(drop-downs / numeric) so that loss and risk can be measured consistently.",
                      "%d report(s) without rupee figure; avg completeness %.0f%%" % (n - A["quantified"], A["avg_complete"])))
    if not A["tests"] or sum(A["tests"].values()) < n:
        recos.append(("MEDIUM", "Testing evidence", "Record every purity test performed (acid, touchstone, salt "
                      "solution / specific gravity, XRF, cutting) with result in the incident report.",
                      "tests recorded in %d report(s)" % sum(1 for r in recs if r["_tests"])))
    recos.append(("MEDIUM", "Continuous monitoring (Key Risk Indicators)",
                  "Track monthly KRIs: incidents per 1,000 gold loans, spurious-gold rate by appraiser, net exposure, "
                  "detection lag, repeat branches, and % of packets re-appraised. Re-run this tool every month on the "
                  "incident folder and present the dashboard to the Audit Committee.", "governance"))
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    seen, final = set(), []
    for r in sorted(recos, key=lambda x: order[x[0]]):
        if r[2] not in seen:
            seen.add(r[2])
            final.append(r)
    return final


# =============================================================================
#  SECTION 8 - EXPORTS (CSV for Excel, HTML report)
# =============================================================================
def consolidated_columns(extra_cols):
    return ["File Name"] + FIELD_NAMES + ["Extra: " + c for c in extra_cols] + ["Unmapped Text"] + METRIC_COLUMNS


def record_row(r, extra_cols):
    vals = [r["File Name"]] + [r.get(f, "") for f in FIELD_NAMES]
    vals += [r["_extras"].get(c, "") for c in extra_cols]
    vals.append(r.get("_unassigned", ""))
    vals += [r["_m"].get(c, "") for c in METRIC_COLUMNS]
    return vals


def export_csv(path, an):
    cols = consolidated_columns(an.extra_cols)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in an.records:
            w.writerow(record_row(r, an.extra_cols))


def _bars_html(items, fmt=lambda v: str(v), color="#C9A227"):
    if not items:
        return "<p class='muted'>No data</p>"
    mx = max(v for _, v in items) or 1
    rows = []
    for k, v in items:
        rows.append("<div class='bar'><span class='lbl'>%s</span><span class='trk'><span class='fill' "
                    "style='width:%.1f%%;background:%s'></span></span><span class='val'>%s</span></div>" %
                    (html.escape(str(k)), 100.0 * v / mx, color, html.escape(fmt(v))))
    return "\n".join(rows)


def _svg_vbar(items, color="#13315C", fmt=lambda v: "%g" % v, w=640, h=250):
    """Vertical bar chart as inline SVG (items = [(label, value)])."""
    items = [(str(k), v) for k, v in items]
    if not items or not any(v for _, v in items):
        return "<p class='muted'>No data</p>"
    L, R, T, B = 40, 10, 22, 44
    mx = max(v for _, v in items) or 1
    slot = (w - L - R) / len(items)
    bw = min(46, slot * 0.62)
    o = ["<svg viewBox='0 0 %d %d' class='svg'>" % (w, h)]
    for g in range(5):
        y = h - B - (h - B - T) * g / 4
        o.append("<line x1='%d' x2='%d' y1='%.1f' y2='%.1f' stroke='#E5E7EB'/><text x='%d' y='%.1f' font-size='9' fill='#6B7280' "
                 "text-anchor='end'>%s</text>" % (L, w - R, y, y, L - 4, y + 3, html.escape(fmt(mx * g / 4))))
    for i, (k, v) in enumerate(items):
        cx = L + slot * (i + 0.5)
        y = h - B - (h - B - T) * v / mx
        o.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s'/>" % (cx - bw / 2, y, bw, h - B - y, color))
        if v:
            o.append("<text x='%.1f' y='%.1f' font-size='10' font-weight='bold' fill='#0B2545' text-anchor='middle'>%s</text>"
                     % (cx, y - 4, html.escape(fmt(v))))
        o.append("<text x='%.1f' y='%d' font-size='10' fill='#1F2937' text-anchor='middle'>%s</text>"
                 % (cx, h - B + 15, html.escape(k)))
    o.append("</svg>")
    return "".join(o)


def _svg_stacked(items, order, colors, w=900, h=300):
    """Stacked vertical bar chart (month on month, one segment per rating) as inline SVG."""
    if not items or not any(sum(d.values()) for _, d in items):
        return "<p class='muted'>No data</p>"
    L, R, T, B = 40, 10, 34, 44
    mx = max(sum(d.values()) for _, d in items) or 1
    slot = (w - L - R) / len(items)
    bw = min(56, slot * 0.62)
    o = ["<svg viewBox='0 0 %d %d' class='svg'>" % (w, h)]
    lx = w - R
    for k in reversed(order):
        lx -= 22 + 7 * len(k)
        o.append("<rect x='%d' y='8' width='11' height='11' fill='%s'/><text x='%d' y='18' font-size='11' fill='#1F2937'>%s</text>"
                 % (lx, colors[k], lx + 15, html.escape(k)))
    for g in range(5):
        y = h - B - (h - B - T) * g / 4
        o.append("<line x1='%d' x2='%d' y1='%.1f' y2='%.1f' stroke='#E5E7EB'/><text x='%d' y='%.1f' font-size='9' fill='#6B7280' "
                 "text-anchor='end'>%.0f</text>" % (L, w - R, y, y, L - 4, y + 3, mx * g / 4))
    for i, (k, d) in enumerate(items):
        cx = L + slot * (i + 0.5)
        y1 = h - B
        for r_ in order:
            v = d.get(r_, 0)
            if not v:
                continue
            y0 = y1 - (h - B - T) * v / mx
            o.append("<rect x='%.1f' y='%.1f' width='%.1f' height='%.1f' fill='%s' stroke='#fff'/>" % (cx - bw / 2, y0, bw, y1 - y0, colors[r_]))
            if y1 - y0 >= 14:
                o.append("<text x='%.1f' y='%.1f' font-size='10' font-weight='bold' fill='%s' text-anchor='middle'>%d</text>"
                         % (cx, (y0 + y1) / 2 + 4, "#0B2545" if r_ == "Medium" else "#fff", v))
            y1 = y0
        o.append("<text x='%.1f' y='%.1f' font-size='10' font-weight='bold' fill='#0B2545' text-anchor='middle'>%d</text>"
                 % (cx, y1 - 4, sum(d.values())))
        o.append("<text x='%.1f' y='%d' font-size='10' fill='#1F2937' text-anchor='middle'>%s</text>" % (cx, h - B + 15, html.escape(str(k))))
    o.append("</svg>")
    return "".join(o)


def _gl_band(v):
    return "#C0392B" if v >= 50 else ("#E67E22" if v >= 25 else "#E8EEF5")


def _gl_grid_html(rows, cols, cells, row_tot, col_tot, grand):
    e = html.escape

    def td(val):
        if not val or val[0] is None:
            return "<td class='c' style='background:#F7F8FA'></td>"
        return "<td class='c' style='background:%s;color:%s'>%.1f%% (%d)</td>" % (
            _gl_band(val[0]), "#0B2545" if val[0] < 25 else "#fff", val[0], val[1])
    o = ["<table class='grid'><tr><th>Branch</th>" + "".join("<th class='c'>%s</th>" % e(month_label(c)) for c in cols) +
         "<th class='c'>All months</th></tr>"]
    for b in rows:
        o.append("<tr><td>%s</td>%s%s</tr>" % (e(b), "".join(td(cells.get((b, c))) for c in cols), td(row_tot.get(b))))
    o.append("<tr><td><b>All branches</b></td>%s%s</tr></table>" % ("".join(td(col_tot.get(c)) for c in cols), td(grand)))
    o.append("<p class='muted'>Cell = financial impact / pledge value of the reports of that branch in that month; (n) = reports. "
             "<span class='sw' style='background:#C0392B'></span> 50% or more &nbsp; <span class='sw' style='background:#E67E22'></span> "
             "25% to below 50% &nbsp; <span class='sw' style='background:#E8EEF5'></span> below 25%.</p>")
    return "".join(o)


def export_html(path, an, folder=None):
    """CFO report.  The folder path is deliberately NOT written into the report."""
    A, recs = an.agg, an.records
    ins = generate_insights(an)
    recos = generate_recommendations(an)
    e = html.escape
    parts = ["<!DOCTYPE html><html><head><meta charset='utf-8'><title>%s</title><style>"
             "body{font-family:Segoe UI,Arial;background:#F4F6FA;color:#1F2937;margin:0}"
             "header{background:#0B2545;color:#fff;padding:18px 28px;border-bottom:4px solid #C9A227}"
             "h1{margin:0;font-size:22px}h2{color:#0B2545;border-left:5px solid #C9A227;padding-left:8px;margin-top:28px}"
             "h3{color:#13315C;margin:18px 0 4px}"
             ".wrap{padding:10px 28px}.kpis{display:flex;flex-wrap:wrap;gap:12px}"
             ".kpi{background:#fff;border-radius:8px;padding:12px 16px;min-width:170px;box-shadow:0 1px 3px #0002}"
             ".kpi b{display:block;font-size:22px;color:#0B2545}.kpi span{color:#6B7280;font-size:12px}"
             ".card{background:#fff;border-radius:8px;padding:10px 16px;box-shadow:0 1px 3px #0002;margin:10px 0}"
             ".two{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:12px}"
             ".svg{width:100%%;height:auto;max-width:900px}"
             "table{border-collapse:collapse;width:100%%;background:#fff;font-size:12px}"
             "th{background:#13315C;color:#fff;padding:6px;text-align:left}td{border-bottom:1px solid #E5E7EB;padding:5px;vertical-align:top}"
             ".grid td.c,.grid th.c{text-align:center}.grid td{border:1px solid #fff}"
             ".tot td{background:#F7EBC3;font-weight:bold}"
             ".sw{display:inline-block;width:12px;height:12px;vertical-align:middle;margin-right:3px}"
             ".bar{display:flex;align-items:center;margin:3px 0}.lbl{width:300px;font-size:12px}"
             ".trk{flex:1;background:#E5E7EB;height:14px;border-radius:7px;margin:0 8px}"
             ".fill{display:block;height:14px;border-radius:7px}.val{width:90px;font-size:12px}"
             ".muted{color:#6B7280;font-size:12px}</style></head><body>" % e(APP_TITLE)]
    parts.append("<header><h1>%s</h1><div>Generated: %s &nbsp;|&nbsp; Amounts in Rs lakhs (L)"
                 "</div></header><div class='wrap'>" % (e(APP_TITLE), dt.datetime.now().strftime("%d-%m-%Y %H:%M")))
    k = [("Reports analysed", str(A["n"])), ("Branches", str(len(A["branches"]))),
         ("Financial impact", "Rs %.2f L" % (A["total_loss"] / 1e5)),
         ("Pledge value involved", "Rs %.2f L" % (A["total_pledge"] / 1e5)),
         ("Gross loss %", ("%.1f%%" % A["gl_pct"]) if A["gl_pct"] is not None else "n/a"), ("Recovered", "Rs %.2f L" % (A["total_rec"] / 1e5)),
         ("Net exposure", "Rs %.2f L" % (A["total_net"] / 1e5)),
         ("Critical + High", str(A["rating"].get("Critical", 0) + A["rating"].get("High", 0))),
         ("Staff / collusion share", "%.0f%%" % A["staff_share"]),
         ("Median detection lag", "%s days" % A["median_lag"] if A["median_lag"] is not None else "n/a")]
    parts.append("<h2>Executive Summary</h2><div class='kpis'>" + "".join(
        "<div class='kpi'><b>%s</b><span>%s</span></div>" % (e(v), e(t)) for t, v in k) + "</div><ul>")
    parts += ["<li>%s</li>" % e(x) for x in ins]
    parts.append("</ul>")

    # ---- risk rating, month on month (replaces the risk register)
    parts.append("<h2>Risk Rating Distribution - Month on Month</h2><div class='card'>" +
                 _svg_stacked(rating_month_items(A), STACK_ORDER, RATING_COLORS) +
                 "<p class='muted'>Number of reports per month (date observed) by composite risk rating: " +
                 ", ".join("%s %d" % (r_, A["rating"].get(r_, 0)) for r_ in RATING_ORDER) + ".</p></div>")

    # ---- the charts of the Diagrammatic View
    def card(title, body, sub=None):
        return "<div class='card'><h3>%s</h3>%s%s</div>" % (e(title), ("<p class='muted'>%s</p>" % e(sub)) if sub else "", body)
    pc = lambda v: "%.1f%%" % v
    l2 = lambda v: "%.2f" % v
    parts.append("<h2>Diagrammatic View</h2><div class='two'>")
    parts.append(card("Primary possible fraud perpetrator", _bars_html([(p_, A["perp"][p_]) for p_ in PERP_ORDER if A["perp"].get(p_)], color="#C0392B"),
                      "Number of incident cases by the most likely perpetrator"))
    parts.append(card("Loss by perpetrator (Rs L)", _bars_html([(p_, A["perp_loss"].get(p_, 0) / 1e5) for p_ in PERP_ORDER if A["perp_loss"].get(p_)],
                                                               fmt=l2, color="#13315C"), "Quantified financial impact"))
    parts.append(card("Control lapse pattern", _bars_html(A["cats"].most_common(), color="#13315C"), "Incidents per control category"))
    parts.append(card("Abnormality pattern - fraud typology", _bars_html(A["typ"].most_common()), "Nature of the abnormality found"))
    parts.append("</div>")
    hrows = [p_ for p_ in PERP_ORDER if p_ in A["heat"]]
    hcols = [c_ for c_, _ in A["cats"].most_common(9)] or ["Not stated"]
    hmx = max([A["heat"].get(r_, {}).get(c_, 0) for r_ in hrows for c_ in hcols] or [1]) or 1
    ht = ["<table class='grid'><tr><th>Perpetrator \\ Control lapse</th>" + "".join("<th class='c'>%s</th>" % e(c_) for c_ in hcols) + "</tr>"]
    for r_ in hrows:
        cells_ = ""
        for c_ in hcols:
            v = A["heat"].get(r_, {}).get(c_, 0)
            t = v / hmx
            colr = "#%02X%02X%02X" % (int(255 - (255 - 0xC0) * t), int(255 - (255 - 0x39) * t), int(255 - (255 - 0x2B) * t)) if v else "#F7F8FA"
            cells_ += "<td class='c' style='background:%s;color:%s'>%s</td>" % (colr, "#fff" if t > 0.55 else "#0B2545", v or "")
        ht.append("<tr><td>%s</td>%s</tr>" % (e(r_), cells_))
    parts.append(card("Pattern matrix - perpetrator x control lapse", "".join(ht) + "</table>", "Darker = more incidents"))
    bl = sorted(((b, v["loss"] / 1e5) for b, v in A["branch_tbl"].items()), key=lambda x: -x[1])
    parts.append("<div class='two'>")
    parts.append(card("Financial impact by branch - top 10 (Rs L)", _bars_html([x for x in bl if x[1] > 0][:10], fmt=l2, color="#C0392B"), "Quantified impact"))
    months = sorted(k_ for k_ in A["month"] if k_ != "Undated")[-12:]
    mitems = [(month_label(k_), A["month"][k_]) for k_ in months] + ([("Undated", A["month"]["Undated"])] if A["month"].get("Undated") else [])
    parts.append(card("Incident trend by month (date observed)", _svg_vbar(mitems, "#13315C", lambda v: "%.0f" % v), "Count of incidents"))
    gm = [(month_label(k_), 100.0 * v[0] / v[1]) for k_, v in sorted(A["gl_month"].items()) if v[1] and k_ != "Undated"][-12:]
    parts.append(card("Gross loss % - month on month", _svg_vbar(gm, "#C0392B", pc),
                      "Financial impact / pledge value involved, by month of observation (reports stating both)"))
    parts.append("</div>")
    top_br, mset, cells, row_tot, col_tot, grand = gl_bm_grid(A, top=10, max_months=12)
    if top_br and mset:
        parts.append(card("Gross loss % - branch x month (top 10 branches by pledge value)",
                          _gl_grid_html(top_br, mset, cells, row_tot, col_tot, grand)))
    glb = {k_: (pct_of(v[0], v[1]), v[2]) for k_, v in A["gl_lag"].items() if v[1]}
    lag_items = [(k_ + ("  (GL %.1f%%)" % glb[k_][0] if k_ in glb else ""), A["lagb"].get(k_, 0)) for k_ in LAG_ORDER]
    parts.append(card("Detection lag profile", _bars_html(lag_items, color="#13315C") +
                      "<ul>%s</ul>" % "".join("<li>%s</li>" % e(x.strip()) for x in lag_commentary(A).split("\u2022") if x.strip()),
                      "Reports by days between 'Since when' and date observed; GL = Gross loss % of those reports"))
    parts.append("<div class='two'>")
    parts.append(card("How the abnormality was discovered", _bars_html(A["det"].most_common(), color="#16A085"), "Detection method"))
    rec_items = [(k_, A["recovery"].get(k_, 0)) for k_ in ("Recovered", "Partial", "Pending", "Not stated")]
    parts.append(card("Recovery status", _bars_html(rec_items, color="#27AE60"),
                      "Recovered Rs %.2f L of Rs %.2f L" % (A["total_rec"] / 1e5, A["total_loss"] / 1e5)))
    parts.append(card("Ornament types involved", _bars_html(A["orn"].most_common(), color="#8E44AD"), "Mentions across reports"))
    parts.append(card("Purity tests recorded", _bars_html(A["tests"].most_common(), color="#D35400"), "Tests conducted to confirm the finding"))
    rt = sorted(((g_, v["n"]) for g_, v in A["region_tbl"].items()), key=lambda x: -x[1])
    parts.append(card("Incidents by region", _bars_html(rt, color="#34495E"), "Concentration of incidents"))
    parts.append("</div>")

    # ---- Pledge value vs Gross loss % summary (default bands: pledge 0-10 step 1, Gross loss % 10-50 step 5)
    parts.append("<h2>Pledge Value vs Gross Loss % - Summary</h2>")
    xt = build_crosstab(recs, (0, 10, 1), (10, 50, 5))
    if not xt:
        parts.append("<p class='muted'>No report states both a financial impact and a pledge value.</p>")
    else:
        rows_, cols_, cl = xt["rows"], xt["cols"], xt["cells"]
        t = ["<table class='grid'><tr><th>Pledge value (Rs L) \\ Gross loss %</th>" + "".join("<th class='c'>%s</th>" % e(c_) for c_ in cols_) +
             "<th class='c'>Total</th></tr>"]
        for i, lab in enumerate(rows_):
            cnt = [len(cl.get((i, j), [])) for j in range(len(cols_))]
            if not sum(cnt):
                continue
            t.append("<tr><td>%s</td>%s<td class='c'><b>%d</b></td></tr>" % (
                e(lab), "".join("<td class='c'>%s</td>" % (c_ or "-") for c_ in cnt), sum(cnt)))
        cs = [sum(len(cl.get((i, j), [])) for i in range(len(rows_))) for j in range(len(cols_))]
        t.append("<tr class='tot'><td>Total</td>%s<td class='c'>%d</td></tr></table>" % ("".join("<td class='c'>%d</td>" % c_ for c_ in cs), sum(cs)))
        parts.append("<div class='card'>" + "".join(t) +
                     "<p class='muted'>Count of reports stating both financial impact and pledge value (%d of %d). Pledge value bands: 0 to 10 Rs L "
                     "in steps of 1; Gross loss %% bands: 10 to 50 in steps of 5; below the minimum is grouped as '&lt;Min', above the maximum as "
                     "'&gt;Max'. Rows with no report are not shown.</p></div>" % (xt["n"], len(recs)))

    parts.append("<h2>Recommendations</h2><table><tr><th>Priority</th><th>Area</th><th>Recommendation</th>"
                 "<th>Evidence</th></tr>")
    for pr, area, txt, why in recos:
        parts.append("<tr><td><b>%s</b></td><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(pr), e(area), e(txt), e(why)))
    parts.append("</table><p class='muted'>Generated by %s v%s. Rule-based NLP and machine-learning (TF-IDF, cosine "
                 "similarity, K-Means) indicators are analytical pointers for audit follow-up and not conclusions "
                 "of fraud.</p></div></body></html>" % (e(APP_TITLE), APP_VERSION))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


# =============================================================================
#  SECTION 9 - PIPELINE: folder -> records -> analytics
# =============================================================================
def _natural_key(path):
    """6, 10, 13, 256 instead of 10, 13, 256, 6."""
    base = os.path.basename(path).lower()
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", base)]


def _is_report_file(fname):
    low = fname.lower()
    if not low.endswith(SUPPORTED_EXT):
        return False
    # skip Word / LibreOffice lock files, hidden files and temp files
    return not (fname.startswith("~$") or fname.startswith(".~lock") or fname.startswith(".")
                or fname.startswith("~WRL") or low.endswith(".tmp"))


def list_report_files(folder, include_sub=False):
    out = []
    if include_sub:
        for dp, dn, fn in os.walk(folder):
            dn[:] = [d for d in dn if not d.startswith(".")]
            for f in fn:
                if _is_report_file(f):
                    out.append(os.path.join(dp, f))
    else:
        for f in os.listdir(folder):
            p = os.path.join(folder, f)
            if os.path.isfile(p) and _is_report_file(f):
                out.append(p)
    return sorted(out, key=lambda x: (os.path.dirname(x).lower(), _natural_key(x)))


def read_folder_records(folder, include_sub=False, use_word=True, progress=None):
    """Read every report in the folder -> one uniform record per file (no analytics).
    Returns (records, failed, log, extra_cols, files)."""
    files = list_report_files(folder, include_sub)
    records, failed, log = [], [], []
    for i, path in enumerate(files):
        name = os.path.relpath(path, folder) if include_sub else os.path.basename(path)
        if progress:
            progress(i, len(files), name)
        try:
            rows, fmt, note = read_any(path, use_word=use_word)
            rec = build_record(rows, name)
            n_found = sum(1 for f in FIELD_NAMES if rec.get(f, "").strip())
            status = "OK" if n_found >= 3 else ("PARTIAL - few headings recognised" if n_found else
                                                "NO HEADINGS FOUND")
            rec["_status"] = status + ((" | " + note) if note else "")
            rec["_format"] = fmt
            rec["_chars"] = rows_text_len(rows)
            records.append(rec)
            log.append({"file": name, "format": fmt, "status": rec["_status"], "chars": rec["_chars"],
                        "found": n_found, "mapping": rec["_mapping"], "note": note})
        except Exception as e:
            err = "ERROR - " + (str(e) or e.__class__.__name__)
            rec = OrderedDict([("File Name", name)] + [(f, "") for f in FIELD_NAMES])
            rec["_extras"], rec["_unassigned"], rec["_mapping"] = OrderedDict(), "", []
            rec["_status"], rec["_format"], rec["_chars"] = err, os.path.splitext(name)[1].upper(), 0
            failed.append(rec)
            log.append({"file": name, "format": rec["_format"], "status": err, "chars": 0, "found": 0,
                        "mapping": [], "note": ""})
    unify_branches(records)
    extra_cols = merge_extra_columns(records)
    return records, failed, log, extra_cols, files


def process_folder(folder, include_sub=False, use_word=True, progress=None):
    records, failed, log, extra_cols, files = read_folder_records(folder, include_sub, use_word, progress)
    if progress:
        progress(len(files), len(files), "Analysing text ...")
    an = Analyzer(records, extra_cols)
    an.run()
    for r in failed:
        r["_m"] = OrderedDict((c, "") for c in METRIC_COLUMNS)
        r["_m"]["Read Status"] = r["_status"]
    return {"an": an, "failed": failed, "log": log, "folder": folder, "files": files}


def read_only_cli(folder, out_csv=None, include_sub=False, use_word=True):
    """Command line check of the file reading:  python gold_loan_fraud_check.py --read-only <folder> [out.csv]
    Prints the tabulated result and (optionally) writes it to CSV - no window, no analytics."""
    records, failed, log, extra_cols, files = read_folder_records(folder, include_sub, use_word)
    cols = ["File Name"] + FIELD_NAMES + list(extra_cols)
    table = []
    for r in records + failed:
        row = [r["File Name"]] + [r.get(f, "") for f in FIELD_NAMES] + [r["_extras"].get(c, "") for c in extra_cols]
        table.append(row + [r.get("_status", ""), r.get("_format", "")])
    cols += ["Read Status", "Format"]
    print("Folder: %s   files found: %d   read OK: %d   failed: %d" % (folder, len(files), len(records), len(failed)))
    for row in table:
        print("-" * 100)
        for c, v in zip(cols, row):
            if v and str(v).strip():
                print("  %-30s: %s" % (c, str(v).replace("\n", " // ")[:160]))
    if out_csv:
        with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(table)
        print("\nSaved:", out_csv)
    return table



# =============================================================================
#  SECTION 10 - USER INTERFACE (tkinter)
# =============================================================================
NAVY = "#0B2545"
NAVY2 = "#13315C"
GOLD = "#C9A227"
GOLD_L = "#F7EBC3"
BG = "#EEF1F6"
CARD = "#FFFFFF"
TXT = "#1F2937"
MUTED = "#6B7280"
GRID = "#E5E7EB"
PALETTE = ["#13315C", "#C9A227", "#C0392B", "#2E86C1", "#16A085", "#8E44AD", "#D35400", "#7F8C8D",
           "#27AE60", "#E74C3C", "#1ABC9C", "#F39C12", "#34495E", "#9B59B6"]
RATING_BG = {"Critical": "#FADBD8", "High": "#FDEBD0", "Medium": "#FCF3CF", "Low": "#D5F5E3"}
PRIORITY_COL = {"HIGH": "#C0392B", "MEDIUM": "#E67E22", "LOW": "#27AE60"}


def short(s, n=140):
    s = (s or "").replace("\n", " | ")
    return s if len(s) <= n else s[:n - 1] + "…"


def _num_key(v):
    s = str(v).replace(",", "").replace("%", "").strip()
    try:
        return (0, float(s.split()[0]))
    except Exception:
        return (1, s.lower())


class ScrollFrame(ttk.Frame):
    """A frame with vertical scrolling (used for dashboards and chart pages)."""
    _all = []
    _bound = False

    def __init__(self, parent, bg=BG, h=False):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        if h:                                   # wide content: also scroll sideways
            self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
            self.canvas.configure(xscrollcommand=self.hsb.set)
            self.hsb.pack(side="bottom", fill="x")
        else:
            self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        ScrollFrame._all.append(self)
        if not ScrollFrame._bound:
            self.bind_all("<MouseWheel>", ScrollFrame._wheel, add="+")
            ScrollFrame._bound = True

    @staticmethod
    def _wheel(e):
        try:
            w = e.widget.winfo_containing(e.x_root, e.y_root)
        except Exception:
            return
        if w is None or isinstance(w, (ttk.Treeview, tk.Text)):
            return
        ScrollFrame._all[:] = [sf for sf in ScrollFrame._all if sf.winfo_exists()]
        while w is not None:
            for sf in ScrollFrame._all:
                if w is sf or w is sf.canvas:
                    sf.canvas.yview_scroll(int(-1 * (e.delta / 120)) if e.delta else 0, "units")
                    return
            w = w.master


# ----------------------------------------------------------------------------- charts on Canvas
class Chart:
    def __init__(self, parent, w, h, sc):
        self.sc = sc
        self.W, self.H = int(w * sc), int(h * sc)
        self.cv = tk.Canvas(parent, width=self.W, height=self.H, bg=CARD, highlightthickness=1,
                            highlightbackground=GRID)

    def f(self, size, bold=False):
        return ("Segoe UI Semibold" if bold else "Segoe UI", size)

    def title(self, t, sub=None):
        self.cv.create_rectangle(0, 0, self.W, 4 * self.sc, fill=GOLD, outline="")
        self.cv.create_text(14 * self.sc, 14 * self.sc, text=t, anchor="nw", font=self.f(11, True), fill=NAVY)
        if sub:
            self.cv.create_text(14 * self.sc, 34 * self.sc, text=sub, anchor="nw", font=self.f(8), fill=MUTED)

    def empty(self):
        self.cv.create_text(self.W / 2, self.H / 2, text="No data available", font=self.f(10), fill=MUTED)

    def donut(self, title, items, colors=None, sub=None, center_label="cases", value_fmt=None):
        s = self.sc
        self.title(title, sub)
        items = [(k, v) for k, v in items if v]
        tot = sum(v for _, v in items)
        if not tot:
            return self.empty()
        cx, cy = self.W * 0.27, self.H * 0.57
        R = min(self.W * 0.21, self.H * 0.34)
        start = 90.0
        for i, (k, v) in enumerate(items):
            col = (colors or {}).get(k, PALETTE[i % len(PALETTE)])
            ext = -360.0 * v / tot
            if abs(ext) >= 359.9:
                self.cv.create_oval(cx - R, cy - R, cx + R, cy + R, fill=col, outline="white", width=2)
            else:
                self.cv.create_arc(cx - R, cy - R, cx + R, cy + R, start=start, extent=ext, fill=col,
                                   outline="white", width=2, style="pieslice")
            start += ext
        r2 = R * 0.56
        self.cv.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, fill="white", outline="white")
        self.cv.create_text(cx, cy - 8 * s, text=(value_fmt(tot) if value_fmt else str(int(tot) if float(tot).is_integer() else round(tot, 2))),
                            font=self.f(15, True), fill=NAVY)
        self.cv.create_text(cx, cy + 13 * s, text=center_label, font=self.f(8), fill=MUTED)
        lx = self.W * 0.53
        ly = self.H * 0.22
        step = min(26 * s, (self.H * 0.74) / max(1, len(items)))
        for i, (k, v) in enumerate(items):
            col = (colors or {}).get(k, PALETTE[i % len(PALETTE)])
            y = ly + i * step
            self.cv.create_rectangle(lx, y, lx + 12 * s, y + 12 * s, fill=col, outline="")
            vt = value_fmt(v) if value_fmt else str(v)
            self.cv.create_text(lx + 18 * s, y - 1 * s, anchor="nw", text=short(k, 34), font=self.f(9), fill=TXT)
            self.cv.create_text(self.W - 12 * s, y - 1 * s, anchor="ne", text="%s  (%.0f%%)" % (vt, 100.0 * v / tot),
                                font=self.f(9, True), fill=NAVY)

    def hbar(self, title, items, color=NAVY2, sub=None, value_fmt=str, max_items=10, colors=None):
        s = self.sc
        self.title(title, sub)
        items = [(k, v) for k, v in items if v][:max_items]
        if not items:
            return self.empty()
        top = 56 * s
        lw = self.W * 0.42
        right = self.W - 70 * s
        avail = self.H - top - 14 * s
        bh = min(24 * s, avail / len(items))
        mx = max(v for _, v in items) or 1
        for i, (k, v) in enumerate(items):
            y = top + i * bh
            self.cv.create_text(lw - 8 * s, y + bh / 2, text=short(k, int(lw / (6.2 * s))), anchor="e",
                                font=self.f(9), fill=TXT)
            self.cv.create_rectangle(lw, y + bh * 0.18, right, y + bh * 0.82, fill="#F1F3F7", outline="")
            x2 = lw + (right - lw) * v / mx
            col = (colors or {}).get(k, color)
            self.cv.create_rectangle(lw, y + bh * 0.18, max(lw + 2, x2), y + bh * 0.82, fill=col, outline="")
            self.cv.create_text(right + 6 * s, y + bh / 2, text=value_fmt(v), anchor="w", font=self.f(9, True), fill=NAVY)

    def vbar(self, title, items, color=GOLD, sub=None, value_fmt=str, colors=None):
        s = self.sc
        self.title(title, sub)
        items = [(k, v) for k, v in items]
        if not items or not any(v for _, v in items):
            return self.empty()
        left, right = 46 * s, self.W - 16 * s
        top, bottom = 62 * s, self.H - 44 * s
        mx = max(v for _, v in items) or 1
        for g in range(5):
            y = bottom - (bottom - top) * g / 4
            self.cv.create_line(left, y, right, y, fill=GRID)
            self.cv.create_text(left - 6 * s, y, text=value_fmt(mx * g / 4) if value_fmt is not str else "%.0f" % (mx * g / 4),
                                anchor="e", font=self.f(7), fill=MUTED)
        n = len(items)
        slot = (right - left) / n
        bw = min(46 * s, slot * 0.62)
        for i, (k, v) in enumerate(items):
            cx = left + slot * (i + 0.5)
            y = bottom - (bottom - top) * v / mx
            col = (colors or {}).get(k, color)
            self.cv.create_rectangle(cx - bw / 2, y, cx + bw / 2, bottom, fill=col, outline="")
            if v:
                self.cv.create_text(cx, y - 8 * s, text=value_fmt(v), font=self.f(8, True), fill=NAVY)
            self.cv.create_text(cx, bottom + 12 * s, text=short(str(k), max(6, int(slot / (6 * s)))),
                                font=self.f(8), fill=TXT)

    def stacked(self, title, items, order, colors, sub=None):
        """Stacked vertical bars: items = [(label, {series: count})]; order = bottom -> top."""
        s = self.sc
        self.title(title, sub)
        if not items or not any(sum(d.values()) for _, d in items):
            return self.empty()
        lx = self.W - 14 * s
        for k in reversed(order):                       # legend, top-right
            lx -= 14 * s + 7 * s * len(k) + 12 * s
            self.cv.create_rectangle(lx, 14 * s, lx + 11 * s, 25 * s, fill=colors[k], outline="")
            self.cv.create_text(lx + 15 * s, 19.5 * s, text=k, anchor="w", font=self.f(8), fill=TXT)
        left, right = 46 * s, self.W - 16 * s
        top, bottom = 62 * s, self.H - 44 * s
        mx = max(sum(d.values()) for _, d in items) or 1
        for g in range(5):
            y = bottom - (bottom - top) * g / 4
            self.cv.create_line(left, y, right, y, fill=GRID)
            self.cv.create_text(left - 6 * s, y, text="%.0f" % (mx * g / 4), anchor="e", font=self.f(7), fill=MUTED)
        slot = (right - left) / len(items)
        bw = min(46 * s, slot * 0.62)
        for i, (k, d) in enumerate(items):
            cx = left + slot * (i + 0.5)
            y1 = bottom
            for r_ in order:
                v = d.get(r_, 0)
                if not v:
                    continue
                y0 = y1 - (bottom - top) * v / mx
                self.cv.create_rectangle(cx - bw / 2, y0, cx + bw / 2, y1, fill=colors[r_], outline="white")
                if y1 - y0 >= 13 * s:
                    self.cv.create_text(cx, (y0 + y1) / 2, text=str(v), font=self.f(8, True),
                                        fill="white" if r_ != "Medium" else NAVY)
                y1 = y0
            self.cv.create_text(cx, y1 - 8 * s, text=str(sum(d.values())), font=self.f(8, True), fill=NAVY)
            self.cv.create_text(cx, bottom + 12 * s, text=short(str(k), max(6, int(slot / (6 * s)))),
                                font=self.f(8), fill=TXT)

    def heatmap(self, title, rows, cols, mat, sub=None):
        s = self.sc
        self.title(title, sub)
        if not rows or not cols:
            return self.empty()
        left = 190 * s
        top = 150 * s
        right = self.W - 12 * s
        bottom = self.H - 12 * s
        cw = (right - left) / len(cols)
        rh = min(30 * s, (bottom - top) / len(rows))
        mx = max([mat.get(r, {}).get(c, 0) for r in rows for c in cols] or [1]) or 1
        for j, c in enumerate(cols):
            x = left + cw * (j + 0.5)
            self.cv.create_text(x, top - 6 * s, text=short(c, 30), angle=55, anchor="w", font=self.f(8), fill=TXT)
        for i, r in enumerate(rows):
            y = top + i * rh
            self.cv.create_text(left - 8 * s, y + rh / 2, text=short(r, 30), anchor="e", font=self.f(8), fill=TXT)
            for j, c in enumerate(cols):
                v = mat.get(r, {}).get(c, 0)
                t = v / mx
                rr = int(255 - (255 - 0xC0) * t)
                gg = int(255 - (255 - 0x39) * t)
                bb = int(255 - (255 - 0x2B) * t)
                fill = "#%02X%02X%02X" % (rr, gg, bb) if v else "#F7F8FA"
                x0 = left + j * cw
                self.cv.create_rectangle(x0 + 1, y + 1, x0 + cw - 1, y + rh - 1, fill=fill, outline="white")
                if v:
                    self.cv.create_text(x0 + cw / 2, y + rh / 2, text=str(v), font=self.f(8, True),
                                        fill="white" if t > 0.55 else NAVY)


def _chart_gl_heatmap(self, title, rows, cols, cells, row_tot, col_tot, grand, sub=None, banded=False, extra=None):
    """Branch x month grid of Gross loss % (sum of financial impact / sum of pledge value in each cell)."""
    s = self.sc
    self.title(title, sub)
    if not rows or not cols:
        return self.empty()
    left, top = 190 * s, 74 * s
    right, bottom = self.W - 12 * s, self.H - 12 * s
    nc = len(cols) + 1
    extra = extra or []                      # [(heading, {row: text}, total text)] drawn right of 'All months'
    ew = 104 * s
    cw = (right - ew * len(extra) - left) / nc
    rh = min(28 * s, (bottom - top) / (len(rows) + 1))
    mx = max([v[0] for v in cells.values()] + [v[0] for v in row_tot.values()] + [1e-9])
    heads = [month_label(c) for c in cols] + ["All months"]
    for j, h in enumerate(heads):
        self.cv.create_text(left + cw * (j + 0.5), top - 12 * s, text=h, font=self.f(8, j == len(cols)), fill=TXT)

    if banded:      # legend
        lx = 360 * s
        for lab, colr in (("< 25%", "#E8EEF5"), ("25% to < 50%", "#E67E22"), (">= 50%", "#C0392B")):
            self.cv.create_rectangle(lx, 14 * s, lx + 12 * s, 26 * s, fill=colr, outline=GRID)
            self.cv.create_text(lx + 16 * s, 20 * s, text=lab, anchor="w", font=self.f(8), fill=TXT)
            lx += (16 + 7 * len(lab) + 18) * s

    def box(x0, y0, val, bold=False):
        if val is None:
            fill, txt, fg = "#F7F8FA", "", NAVY
        elif banded:
            fill = "#C0392B" if val[0] >= 50 else ("#E67E22" if val[0] >= 25 else "#E8EEF5")
            txt, fg = "%.1f%%  (%d)" % (val[0], val[1]), ("white" if val[0] >= 25 else NAVY)
        else:
            t = min(1.0, val[0] / mx)
            fill = "#%02X%02X%02X" % (int(255 - (255 - 0xC0) * t), int(255 - (255 - 0x39) * t), int(255 - (255 - 0x2B) * t))
            txt, fg = "%.1f%%  (%d)" % (val[0], val[1]), ("white" if t > 0.55 else NAVY)
        self.cv.create_rectangle(x0 + 1, y0 + 1, x0 + cw - 1, y0 + rh - 1, fill=fill, outline="white")
        if txt:
            self.cv.create_text(x0 + cw / 2, y0 + rh / 2, text=txt, font=self.f(8, bold), fill=fg)

    for i, r in enumerate(rows + ["All branches"]):
        y = top + i * rh
        tot_row = i == len(rows)
        self.cv.create_text(left - 8 * s, y + rh / 2, text=short(r, 30), anchor="e", font=self.f(8, tot_row), fill=TXT)
        for j, c in enumerate(cols):
            box(left + j * cw, y, (col_tot.get(c) if tot_row else cells.get((r, c))), tot_row)
        box(left + len(cols) * cw, y, grand if tot_row else row_tot.get(r), True)
        for k_, (hd, dd, tt) in enumerate(extra):
            x0 = left + nc * cw + k_ * ew
            self.cv.create_rectangle(x0 + 1, y + 1, x0 + ew - 1, y + rh - 1, fill=GOLD_L if tot_row else "#F3F4F6", outline="white")
            self.cv.create_text(x0 + ew / 2, y + rh / 2, text=tt if tot_row else dd.get(r, ""), font=self.f(8, tot_row), fill=NAVY)
    for k_, (hd, dd, tt) in enumerate(extra):
        self.cv.create_text(left + nc * cw + (k_ + 0.5) * ew, top - 12 * s, text=hd, font=self.f(8, True), fill=NAVY)


def _chart_lag(self, title, items, gl, note, sub=None):
    """Detection-lag bars (count of reports) with the Gross loss % of every bar and a commentary box."""
    s = self.sc
    self.title(title, sub)
    if not items or not any(v for _, v in items):
        return self.empty()
    left, right = 46 * s, self.W * 0.56
    top, bottom = 66 * s, self.H - 62 * s
    mx = max(v for _, v in items) or 1
    for g in range(5):
        y = bottom - (bottom - top) * g / 4
        self.cv.create_line(left, y, right, y, fill=GRID)
        self.cv.create_text(left - 6 * s, y, text="%.0f" % (mx * g / 4), anchor="e", font=self.f(7), fill=MUTED)
    slot = (right - left) / len(items)
    bw = min(46 * s, slot * 0.62)
    for i, (k, v) in enumerate(items):
        cx = left + slot * (i + 0.5)
        y = bottom - (bottom - top) * v / mx
        self.cv.create_rectangle(cx - bw / 2, y, cx + bw / 2, bottom, fill="#2E86C1", outline="")
        if v:
            self.cv.create_text(cx, y - 8 * s, text=str(v), font=self.f(8, True), fill=NAVY)
        self.cv.create_text(cx, bottom + 11 * s, text=short(str(k), max(6, int(slot / (6 * s)))), font=self.f(8), fill=TXT)
        g = gl.get(k)
        txt = ("GL %.1f%%" % g[0]) if g and g[0] is not None else "GL n/a"
        self.cv.create_rectangle(cx - slot * 0.44, bottom + 24 * s, cx + slot * 0.44, bottom + 42 * s,
                                 fill="#FADBD8" if g and g[0] is not None else "#F3F4F6", outline="")
        self.cv.create_text(cx, bottom + 33 * s, text=txt, font=self.f(8, True), fill="#C0392B" if g and g[0] is not None else MUTED)
        if g and g[0] is not None:
            self.cv.create_text(cx, bottom + 52 * s, text="n=%d" % g[1], font=self.f(7), fill=MUTED)
    # commentary box
    x0, y0, x1, y1 = right + 26 * s, top - 6 * s, self.W - 14 * s, self.H - 14 * s
    self.cv.create_rectangle(x0, y0, x1, y1, fill=GOLD_L, outline=GOLD)
    self.cv.create_text(x0 + 10 * s, y0 + 8 * s, text="Commentary", anchor="nw", font=self.f(10, True), fill=NAVY)
    self.cv.create_text(x0 + 10 * s, y0 + 30 * s, text=note, anchor="nw", width=x1 - x0 - 20 * s,
                        font=self.f(9), fill=TXT)
    self.cv.create_text(left, bottom + 33 * s, text="", anchor="e")
    self.cv.create_text(left - 36 * s, bottom + 33 * s, text="Gross\nloss %", anchor="w", font=self.f(7, True), fill="#C0392B")


def _chart_text_w(self, text, size):
    try:
        return tkfont.Font(family="Segoe UI", size=size).measure(text)
    except Exception:
        return 7 * len(text)


Chart.cv_text_w = _chart_text_w
Chart.gl_heatmap = _chart_gl_heatmap
Chart.lag_chart = _chart_lag


class SubTabs(tk.Frame):
    """Scrollable tab strip for crowded sub-tabs.  The selected tab always shows its FULL title; when the strip is
    too narrow the other tabs are shortened, and the left / right arrows (or mouse wheel) scroll to tabs that are
    outside the visible area."""
    SHORT = 16

    def __init__(self, parent, sc=1.0):
        super().__init__(parent, bg=BG)
        self.titles, self.pages, self.labels = [], [], []
        self.cur = None
        self.font = tkfont.Font(family="Segoe UI Semibold", size=9)
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x")
        kw = dict(relief="flat", bd=0, bg="#C9D2E0", activebackground=GOLD_L, fg=NAVY, disabledforeground="#9AA4B5",
                  font=("Segoe UI", 10, "bold"), cursor="hand2", padx=10)
        self.btn_l = tk.Button(bar, text="\u25C0", command=lambda: self._scroll(-1), **kw)
        self.btn_l.pack(side="left", fill="y", padx=(0, 2))
        self.btn_r = tk.Button(bar, text="\u25B6", command=lambda: self._scroll(1), **kw)
        self.btn_r.pack(side="right", fill="y", padx=(2, 0))
        self.cv = tk.Canvas(bar, height=int(34 * sc), bg=BG, highlightthickness=0, xscrollincrement=40)
        self.cv.pack(side="left", fill="x", expand=True)
        self.strip = tk.Frame(self.cv, bg=BG)
        self.cv.create_window((0, 0), window=self.strip, anchor="nw")
        self.strip.bind("<Configure>", lambda e: self._update())
        self.cv.bind("<Configure>", lambda e: self._relayout())
        self.cv.bind("<MouseWheel>", self._wheel)
        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True)

    def add(self, title):
        page = ttk.Frame(self.body, padding=6)
        lab = tk.Label(self.strip, text="  %s  " % title, font=("Segoe UI Semibold", 9), cursor="hand2", padx=6, pady=6)
        i = len(self.titles)
        lab.pack(side="left", padx=(0, 2), pady=(2, 0))
        lab.bind("<Button-1>", lambda e, i=i: self.select(i))
        lab.bind("<MouseWheel>", self._wheel)
        self.titles.append(title)
        self.pages.append(page)
        self.labels.append(lab)
        if self.cur is None:
            self.select(0)
        else:
            self._relayout()
        return page

    def select(self, i):
        if self.cur is not None:
            self.pages[self.cur].pack_forget()
        self.cur = i
        self.pages[i].pack(fill="both", expand=True)
        self._relayout()
        self.after(30, lambda: self._see(i))
        self.after(200, self._update)

    def index(self):
        return self.cur

    def _short(self, t):
        return t if len(t) <= self.SHORT else t[:self.SHORT - 1].rstrip() + "\u2026"

    def _relayout(self):
        avail = self.cv.winfo_width()
        if avail <= 1:
            self.after(60, self._relayout)
            return
        full = sum(self.font.measure("  %s  " % t) + 12 + 2 for t in self.titles)
        compact = full > avail
        for k, (lab, t) in enumerate(zip(self.labels, self.titles)):
            sel = k == self.cur
            lab.configure(text="  %s  " % (t if (sel or not compact) else self._short(t)),
                          bg=NAVY if sel else "#DDE3EC", fg="white" if sel else TXT)
        self.after_idle(self._update)
        self.after(150, self._update)

    def _update(self):
        try:
            self.cv.configure(scrollregion=(0, 0, self.strip.winfo_reqwidth(), self.strip.winfo_reqheight()),
                              height=self.strip.winfo_reqheight() + 2)
            a, b = self.cv.xview()
            self.btn_l.configure(state="normal" if a > 0.001 else "disabled")
            self.btn_r.configure(state="normal" if b < 0.999 else "disabled")
        except Exception:
            pass

    def _scroll(self, d):
        self.cv.xview_scroll(d * 5, "units")
        self._update()

    def _wheel(self, e):
        self._scroll(-1 if e.delta > 0 else 1)

    def _see(self, i):
        """Scroll so that tab i is fully visible."""
        try:
            self.update_idletasks()
            lab = self.labels[i]
            total = max(1, self.strip.winfo_reqwidth())
            left = self.cv.canvasx(0)
            right = left + self.cv.winfo_width()
            x0, x1 = lab.winfo_x(), lab.winfo_x() + lab.winfo_width()
            if x1 <= self.cv.winfo_width():
                self.cv.xview_moveto(0)
            elif x0 < left:
                self.cv.xview_moveto(x0 / total)
            elif x1 > right:
                self.cv.xview_moveto(max(0, (x1 - self.cv.winfo_width())) / total)
            self._update()
        except Exception:
            pass


# ----------------------------------------------------------------------------- main application
class App:
    def __init__(self, root):
        self.root = root
        self.result = None
        self.q = queue.Queue()
        self.sc = max(1.0, root.winfo_fpixels("1i") / 96.0)
        root.title("%s  v%s" % (APP_TITLE, APP_VERSION))
        try:
            root.state("zoomed")
        except Exception:
            root.geometry("1400x860")
        root.minsize(1100, 700)
        root.configure(bg=BG)
        self._style()
        self._build()

    # .................................................................. style
    def _style(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure(".", font=("Segoe UI", 10), background=BG, foreground=TXT)
        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=CARD)
        st.configure("TLabel", background=BG, foreground=TXT)
        st.configure("Card.TLabel", background=CARD)
        st.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 9))
        st.configure("H.TLabel", background=BG, foreground=NAVY, font=("Segoe UI Semibold", 12))
        st.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(6, 6, 6, 0))
        st.configure("TNotebook.Tab", padding=(14, 7), font=("Segoe UI Semibold", 10), background="#D9DFE9",
                     foreground=NAVY, borderwidth=0)
        st.map("TNotebook.Tab", background=[("selected", NAVY)], foreground=[("selected", "white")])
        st.configure("Sub.TNotebook.Tab", padding=(10, 5), font=("Segoe UI", 9))
        st.configure("Treeview", rowheight=int(24 * self.sc), font=("Segoe UI", 9), background=CARD,
                     fieldbackground=CARD, foreground=TXT, borderwidth=0)
        st.configure("Treeview.Heading", font=("Segoe UI Semibold", 9), background=NAVY2, foreground="white",
                     relief="flat", padding=(4, 5))
        st.map("Treeview.Heading", background=[("active", GOLD)], foreground=[("active", NAVY)])
        st.map("Treeview", background=[("selected", "#2E86C1")], foreground=[("selected", "white")])
        st.configure("Gold.TButton", background=GOLD, foreground=NAVY, font=("Segoe UI Semibold", 10),
                     padding=(16, 6), borderwidth=0)
        st.map("Gold.TButton", background=[("active", "#E0B93A"), ("disabled", "#E5E7EB")])
        st.configure("Navy.TButton", background=NAVY2, foreground="white", font=("Segoe UI Semibold", 10),
                     padding=(12, 6), borderwidth=0)
        st.map("Navy.TButton", background=[("active", NAVY)])
        st.configure("TCheckbutton", background=CARD, font=("Segoe UI", 9))
        st.configure("gold.Horizontal.TProgressbar", troughcolor="#E5E7EB", background=GOLD, borderwidth=0)
        st.configure("TEntry", padding=5)

    # .................................................................. layout
    def _build(self):
        s = self.sc
        hdr = tk.Frame(self.root, bg=NAVY, height=int(64 * s))
        hdr.pack(fill="x")
        tk.Frame(self.root, bg=GOLD, height=int(4 * s)).pack(fill="x")
        tk.Label(hdr, text="◆", bg=NAVY, fg=GOLD, font=("Segoe UI", 22)).pack(side="left", padx=(18, 6), pady=8)
        tbox = tk.Frame(hdr, bg=NAVY)
        tbox.pack(side="left", pady=6)
        tk.Label(tbox, text=APP_TITLE, bg=NAVY, fg="white", font=("Segoe UI Semibold", 16)).pack(anchor="w")
        tk.Label(tbox, text="Text analytics of Gold Loan audit incident reports  •  Collateral (gold ornament) "
                             "verification lens  •  Amounts in Rs lakhs (L)", bg=NAVY, fg="#C8D3E6",
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(hdr, text="CFO Dashboard", bg=NAVY, fg=GOLD, font=("Segoe UI Semibold", 11)).pack(side="right", padx=20)

        bar = ttk.Frame(self.root, style="Card.TFrame", padding=(14, 10))
        bar.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(bar, text="Incident reports folder:", style="Card.TLabel",
                  font=("Segoe UI Semibold", 10)).grid(row=0, column=0, sticky="w")
        self.folder_var = tk.StringVar()
        ent = ttk.Entry(bar, textvariable=self.folder_var, width=80)
        ent.grid(row=0, column=1, sticky="we", padx=8)
        ttk.Button(bar, text="Browse…", style="Navy.TButton", command=self.browse).grid(row=0, column=2, padx=4)
        self.run_btn = ttk.Button(bar, text="▶  Run Analysis", style="Gold.TButton", command=self.run)
        self.run_btn.grid(row=0, column=3, padx=4)
        self.sub_var = tk.BooleanVar(value=False)
        self.word_var = tk.BooleanVar(value=True)
        opt = ttk.Frame(bar, style="Card.TFrame")
        opt.grid(row=1, column=1, sticky="w", padx=8, pady=(6, 0))
        ttk.Checkbutton(opt, text="Include sub-folders", variable=self.sub_var).pack(side="left")
        ttk.Checkbutton(opt, text="Use MS Word (if installed) as back-up reader for difficult .doc / .pdf files",
                        variable=self.word_var).pack(side="left", padx=14)
        self.prog = ttk.Progressbar(bar, style="gold.Horizontal.TProgressbar", mode="determinate", length=260)
        self.prog.grid(row=1, column=2, columnspan=2, sticky="we", padx=4, pady=(6, 0))
        self.status = ttk.Label(bar, text="Select the folder containing the Word / PDF incident reports, then click "
                                          "Run Analysis.  Only .docx, .doc and .pdf files are read.", style="Muted.TLabel")
        self.status.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        bar.columnconfigure(1, weight=1)

        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(4, 10))
        self.tabs = OrderedDict()
        for name in ["Executive Summary", "1. Control Flaws", "2. Possible Fraud Risk", "3. Diagrammatic View",
                     "4. Deeper Analysis", "5. Recommendations", "Consolidated Data", "File Read Log", "Methodology"]:
            fr = ttk.Frame(self.nb, padding=8)
            self.nb.add(fr, text="  %s  " % name)
            self.tabs[name] = fr
            if name != "Methodology":
                ttk.Label(fr, text="Results will appear here after you select a folder and click ‘Run Analysis’.",
                          foreground=MUTED).pack(pady=40)
        self._methodology(self.tabs["Methodology"])

    # .................................................................. helpers
    def clear(self, fr):
        for w in fr.winfo_children():
            w.destroy()

    def card(self, parent, title=None, **pack):
        outer = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=GRID)
        if pack:
            outer.pack(**pack)
        if title:
            tk.Label(outer, text=title, bg=CARD, fg=NAVY, font=("Segoe UI Semibold", 11), anchor="w").pack(
                fill="x", padx=12, pady=(8, 2))
            tk.Frame(outer, bg=GOLD, height=2).pack(fill="x", padx=12, pady=(0, 6))
        return outer

    def tree(self, parent, cols, widths=None, height=10, on_open=None):
        frm = tk.Frame(parent, bg=CARD)
        tv = ttk.Treeview(frm, columns=cols, show="headings", height=height)
        vsb = ttk.Scrollbar(frm, orient="vertical", command=tv.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=tv.xview)
        tv.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        for i, c in enumerate(cols):
            w = widths[i] if widths and i < len(widths) else 140
            tv.heading(c, text=c, command=lambda c=c: self.sort_tree(tv, c))
            tv.column(c, width=int(w * self.sc), minwidth=40, anchor="w", stretch=False)
        tv.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frm.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)
        for r, colr in RATING_BG.items():
            tv.tag_configure(r, background=colr)
        tv.tag_configure("odd", background="#F8F9FB")
        tv.tag_configure("bold", font=("Segoe UI Semibold", 9))
        if on_open:
            tv.bind("<Double-1>", lambda e: on_open(tv))
        return frm, tv

    def sort_tree(self, tv, col):
        rev = getattr(tv, "_rev_" + col, False)
        data = [(tv.set(k, col), k) for k in tv.get_children("")]
        data.sort(key=lambda x: _num_key(x[0]), reverse=rev)
        for i, (_, k) in enumerate(data):
            tv.move(k, "", i)
        setattr(tv, "_rev_" + col, not rev)

    def fill(self, tv, rows, tags=None):
        for i, r in enumerate(rows):
            t = tags[i] if tags else ("odd",) if i % 2 else ()
            if isinstance(t, str):
                t = (t,)
            tv.insert("", "end", values=[short(str(x), 300) for x in r], tags=t)

    def text_box(self, parent, height=10):
        frm = tk.Frame(parent, bg=CARD)
        tx = tk.Text(frm, wrap="word", height=height, font=("Segoe UI", 10), bg=CARD, fg=TXT, relief="flat",
                     padx=12, pady=8, spacing1=2, spacing3=4)
        sb = ttk.Scrollbar(frm, orient="vertical", command=tx.yview)
        tx.configure(yscrollcommand=sb.set)
        tx.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        tx.tag_configure("h1", font=("Segoe UI Semibold", 13), foreground=NAVY, spacing1=10, spacing3=4)
        tx.tag_configure("h2", font=("Segoe UI Semibold", 11), foreground=NAVY2, spacing1=8)
        tx.tag_configure("b", font=("Segoe UI Semibold", 10))
        tx.tag_configure("muted", foreground=MUTED, font=("Segoe UI", 9))
        tx.tag_configure("bullet", lmargin1=14, lmargin2=30)
        tx.tag_configure("gold", foreground="#9A7B12", font=("Segoe UI Semibold", 10))
        for k, c in PRIORITY_COL.items():
            tx.tag_configure("P_" + k, foreground="white", background=c, font=("Segoe UI Semibold", 9))
        return frm, tx

    # .................................................................. actions
    def browse(self):
        d = filedialog.askdirectory(title="Select folder containing Gold Loan incident reports")
        if d:
            self.folder_var.set(os.path.normpath(d))
            try:
                n = len(list_report_files(d, self.sub_var.get()))
                self.status.configure(text="%d Word / PDF file(s) found in the selected folder. Click ‘Run Analysis’." % n)
            except Exception:
                pass

    def run(self):
        folder = self.folder_var.get().strip().strip('"')
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning(APP_TITLE, "Please select a valid folder first (use the Browse button).")
            return
        files = list_report_files(folder, self.sub_var.get())
        if not files:
            messagebox.showinfo(APP_TITLE, "No .docx / .doc / .pdf files were found in:\n\n%s" % folder)
            return
        self.run_btn.state(["disabled"])
        self.prog.configure(maximum=len(files) + 1, value=0)
        sub, word = self.sub_var.get(), self.word_var.get()

        def work():
            try:
                res = process_folder(folder, sub, word, progress=lambda i, n, nm: self.q.put(("p", i, n, nm)))
                self.q.put(("done", res))
            except Exception:
                self.q.put(("err", traceback.format_exc()))

        threading.Thread(target=work, daemon=True).start()
        self.root.after(100, self.poll)

    def poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "p":
                    _, i, n, nm = msg
                    self.prog.configure(value=i)
                    self.status.configure(text="Reading %d of %d:  %s" % (min(i + 1, n), n, nm) if i < n else nm)
                elif msg[0] == "done":
                    self.result = msg[1]
                    self.prog.configure(value=self.prog["maximum"])
                    try:
                        self.populate()
                        an = self.result["an"]
                        self.status.configure(text="Done: %d file(s) read, %d analysed, %d could not be read.  "
                                                   "Double-click any row to see full details." %
                                                   (len(self.result["files"]), len(an.records), len(self.result["failed"])))
                    except Exception:
                        messagebox.showerror(APP_TITLE, "Display error:\n" + traceback.format_exc()[-1500:])
                    self.run_btn.state(["!disabled"])
                    return
                elif msg[0] == "err":
                    self.run_btn.state(["!disabled"])
                    messagebox.showerror(APP_TITLE, "Processing error:\n" + msg[1][-1500:])
                    return
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    # .................................................................. populate all tabs
    def populate(self):
        an = self.result["an"]
        for name, fr in self.tabs.items():
            if name != "Methodology":
                self.clear(fr)
        if not an.records:
            for name, fr in self.tabs.items():
                if name not in ("Methodology", "File Read Log"):
                    ttk.Label(fr, text="No file could be read. See ‘File Read Log’.", foreground=MUTED).pack(pady=40)
            self._log(self.tabs["File Read Log"])
            return
        self._summary(self.tabs["Executive Summary"])
        self._controls(self.tabs["1. Control Flaws"])
        self._fraud(self.tabs["2. Possible Fraud Risk"])
        self._charts(self.tabs["3. Diagrammatic View"])
        self._deeper(self.tabs["4. Deeper Analysis"])
        self._recos(self.tabs["5. Recommendations"])
        self._data(self.tabs["Consolidated Data"])
        self._log(self.tabs["File Read Log"])

    def rec_by_file(self, fname):
        for r in self.result["an"].records + self.result["failed"]:
            if r["File Name"] == fname:
                return r
        return None

    def open_detail(self, tv):
        sel = tv.selection()
        if not sel:
            return
        cols = tv["columns"]
        vals = tv.item(sel[0], "values")
        fname = None
        for c, v in zip(cols, vals):
            if c in ("File Name", "File", "File A"):
                fname = v
                break
        r = self.rec_by_file(fname) if fname else None
        if r:
            self.detail(r)

    def detail(self, r):
        top = tk.Toplevel(self.root)
        top.title("Incident detail - %s" % r["File Name"])
        top.geometry("%dx%d" % (int(900 * self.sc), int(720 * self.sc)))
        top.configure(bg=BG)
        frm, tx = self.text_box(top, 30)
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        tx.insert("end", r["File Name"] + "\n", "h1")
        if "_rating" in r:
            tx.insert("end", "Risk score %d / 100  -  %s\n" % (r["_score"], r["_rating"]), "gold")
            tx.insert("end", "Score build-up: " + ", ".join("%s %d" % kv for kv in r["_score_parts"].items()) + "\n", "muted")
        tx.insert("end", "\nREPORT CONTENT (uniform headings)\n", "h2")
        for f in FIELD_NAMES:
            tx.insert("end", f + ":  ", "b")
            tx.insert("end", (r.get(f) or "—") + "\n")
        for k, v in r.get("_extras", {}).items():
            tx.insert("end", k + ":  ", "b")
            tx.insert("end", v + "\n")
        if r.get("_unassigned"):
            tx.insert("end", "Unmapped text:  ", "b")
            tx.insert("end", r["_unassigned"] + "\n")
        tx.insert("end", "\nANALYTICS OUTCOME\n", "h2")
        for k, v in r.get("_m", {}).items():
            tx.insert("end", k + ":  ", "b")
            tx.insert("end", (v or "—") + "\n")
        tx.configure(state="disabled")

    # .................................................................. Executive summary
    def _summary(self, fr):
        an = self.result["an"]
        A = an.agg
        sf = ScrollFrame(fr)
        sf.pack(fill="both", expand=True)
        body = sf.inner
        kp = tk.Frame(body, bg=BG)
        kp.pack(fill="x", pady=(2, 8))
        kpis = [
            ("Reports analysed", str(A["n"]), "%d failed to read" % len(self.result["failed"]), NAVY2),
            ("Branches / Regions", "%d / %d" % (len(A["branches"]), len(A["regions"])), "covered", NAVY2),
            ("Financial impact", "Rs %.2f L" % (A["total_loss"] / 1e5), "%d of %d quantified" % (A["quantified"], A["n"]), "#C0392B"),
            ("Pledge value involved", "Rs %.2f L" % (A["total_pledge"] / 1e5), "%d of %d stated in report" % (A["pledge_n"], A["n"]), NAVY2),
            ("Gross loss %", ("%.1f%%" % A["gl_pct"]) if A["gl_pct"] is not None else "n/a",
             "impact / pledge value, %d report(s)" % A["gl_n"], "#C0392B"),
            ("Recovered", "Rs %.2f L" % (A["total_rec"] / 1e5), "%d pending case(s)" % A["recovery"].get("Pending", 0), "#27AE60"),
            ("Net exposure", "Rs %.2f L" % (A["total_net"] / 1e5), "impact less recovery", "#C0392B"),
            ("Critical + High", str(A["rating"].get("Critical", 0) + A["rating"].get("High", 0)), "composite risk score", "#E67E22"),
            ("Staff / collusion", "%.0f%%" % A["staff_share"], "of cases (primary perpetrator)", "#8E44AD"),
            ("Median detection lag", ("%d days" % A["median_lag"]) if A["median_lag"] is not None else "n/a",
             "abnormality start to observation", NAVY2),
        ]
        for i, (t, v, sub, col) in enumerate(kpis):
            c = tk.Frame(kp, bg=CARD, highlightthickness=1, highlightbackground=GRID)
            c.grid(row=i // 4, column=i % 4, sticky="nsew", padx=5, pady=5)
            tk.Frame(c, bg=col, width=int(5 * self.sc)).pack(side="left", fill="y")
            inner = tk.Frame(c, bg=CARD)
            inner.pack(side="left", fill="both", expand=True, padx=12, pady=8)
            tk.Label(inner, text=t.upper(), bg=CARD, fg=MUTED, font=("Segoe UI Semibold", 8)).pack(anchor="w")
            tk.Label(inner, text=v, bg=CARD, fg=NAVY, font=("Segoe UI Semibold", 18)).pack(anchor="w")
            tk.Label(inner, text=sub, bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        for j in range(4):
            kp.columnconfigure(j, weight=1)
        mid = tk.Frame(body, bg=BG)
        mid.pack(fill="x")
        left = self.card(mid, "Key insights for the CFO")
        left.pack(side="left", fill="both", expand=True, padx=5)
        frm, tx = self.text_box(left, 14)
        frm.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        for line in generate_insights(an):
            tx.insert("end", "●  ", "gold")
            tx.insert("end", line + "\n", "bullet")
        tx.configure(state="disabled")
        right = tk.Frame(mid, bg=BG)
        right.pack(side="left", fill="y", padx=5)
        ch = Chart(right, 520, 300, self.sc)
        ch.cv.pack()
        ch.donut("Primary possible fraud perpetrator", [(p, A["perp"].get(p, 0)) for p in PERP_ORDER], PERP_COLORS,
                 sub="Share of incident cases")
        c2 = self.card(body, "Top high-risk incidents (double-click for full details)")
        c2.pack(fill="both", expand=True, padx=5, pady=8)
        cols = ["File Name", "Branch", "Region", "Primary Perpetrator", "Fraud Typology", "Loss (Rs L)",
                "Pledge Value (Rs L)", "Recovery Status", "Risk Score", "Risk Rating", "Red Flags"]
        frm, tv = self.tree(c2, cols, [170, 120, 110, 170, 260, 85, 110, 100, 75, 80, 420], height=10, on_open=self.open_detail)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        recs = sorted(an.records, key=lambda r: -r["_score"])[:15]
        self.fill(tv, [[r["File Name"], branch_key(r), clean_one(r.get("Region")), r["_perp"], "; ".join(r["_typ"]),
                        fmt_l(r["_loss"]), fmt_l(r.get("_pledge")), r["_m"]["Recovery Status"], r["_score"], r["_rating"],
                        "; ".join(r["_flags"])] for r in recs], [r["_rating"] for r in recs])

    # .................................................................. 1. Control flaws
    def _controls(self, fr):
        an = self.result["an"]
        A = an.agg
        n = A["n"]
        pw = ttk.PanedWindow(fr, orient="vertical")
        pw.pack(fill="both", expand=True)
        top = self.card(pw, "Control lapse categories (text-mined from ‘Control failures’, ‘Steps taken’ and narrative)")
        pw.add(top, weight=1)
        cols = ["Control Lapse Category", "Incidents", "% of Incidents", "Loss Involved (Rs L)", "Branches Affected",
                "Typical Perpetrator", "Corrective Steps Documented"]
        frm, tv = self.tree(top, cols, [320, 80, 100, 140, 120, 200, 190], height=8)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        rows = []
        for cat, c in A["cats"].most_common():
            perps = Counter(r["_perp"] for r in an.records if cat in r["_cats"])
            steps = sum(1 for r in an.records if cat in r["_cats"] and not is_placeholder(r.get("Steps Taken to Tighten Control")))
            rows.append([cat, c, "%.0f%%" % (100.0 * c / n), fmt_l(A["cat_loss"][cat]), len(A["cat_branches"][cat]),
                         perps.most_common(1)[0][0] if perps else "", "%d of %d" % (steps, c)])
        self.fill(tv, rows)
        no_steps = [r for r in an.records if not is_placeholder(r.get("Control Failures")) and
                    is_placeholder(r.get("Steps Taken to Tighten Control"))]
        no_cf = [r for r in an.records if is_placeholder(r.get("Control Failures"))]
        note = ("Process-gap observations:  %d report(s) do not describe the control failure;  %d report(s) describe a "
                "control failure but no step to tighten the control;  average control gaps per incident: %.1f." %
                (len(no_cf), len(no_steps), sum(len(r["_cats"]) for r in an.records) / max(1, n)))
        tk.Label(top, text=note, bg=CARD, fg="#9A7B12", font=("Segoe UI Semibold", 9), anchor="w",
                 wraplength=int(1300 * self.sc), justify="left").pack(fill="x", padx=12, pady=(0, 8))
        bot = self.card(pw, "Incident-wise control failures (as reported) and mapped categories")
        pw.add(bot, weight=2)
        cols = ["File Name", "Branch", "Control Failure Categories", "No. of Gaps", "Control Failures (as reported)",
                "Steps Taken to Tighten Control", "Risk Rating"]
        frm, tv = self.tree(bot, cols, [170, 120, 330, 80, 420, 360, 80], height=12, on_open=self.open_detail)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        recs = sorted(an.records, key=lambda r: -len(r["_cats"]))
        self.fill(tv, [[r["File Name"], branch_key(r), "; ".join(r["_cats"]) or "Not stated", len(r["_cats"]),
                        r.get("Control Failures") or "—", r.get("Steps Taken to Tighten Control") or "—", r["_rating"]]
                       for r in recs], [r["_rating"] for r in recs])

    # .................................................................. 2. Fraud risk
    def _fraud(self, fr):
        an = self.result["an"]
        A = an.agg
        n = A["n"]
        upper = tk.Frame(fr, bg=BG)
        upper.pack(fill="x")
        c1 = self.card(upper, "Primary possible perpetrator")
        c1.pack(side="left", fill="both", expand=True, padx=4)
        frm, tv = self.tree(c1, ["Perpetrator", "Cases", "% Cases", "Loss (Rs L)"], [220, 60, 70, 90], height=6)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[p, A["perp"][p], "%.0f%%" % (100.0 * A["perp"][p] / n), fmt_l(A["perp_loss"][p])]
                       for p in PERP_ORDER if A["perp"].get(p)])
        c2 = self.card(upper, "Staff collusion indicator")
        c2.pack(side="left", fill="both", expand=True, padx=4)
        frm, tv = self.tree(c2, ["Indicator", "Cases"], [300, 70], height=6)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[k, v] for k, v in A["coll"].most_common()])
        c3 = self.card(upper, "Customer intent to defraud")
        c3.pack(side="left", fill="both", expand=True, padx=4)
        frm, tv = self.tree(c3, ["Intent", "Cases"], [200, 70], height=6)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[k, v] for k, v in A["cint"].most_common()])
        c4 = self.card(fr, "Fraud typology / abnormality pattern in gold ornament verification")
        c4.pack(fill="x", padx=4, pady=6)
        frm, tv = self.tree(c4, ["Fraud Typology", "Cases", "% Cases", "Loss (Rs L, apportioned)", "Most Likely Perpetrator",
                                 "Branches"], [380, 70, 80, 160, 220, 400], height=6)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        rows = []
        for t, c in A["typ"].most_common():
            pp = Counter(r["_perp"] for r in an.records if t in r["_typ"])
            br = sorted(set(branch_key(r) for r in an.records if t in r["_typ"]))
            rows.append([t, c, "%.0f%%" % (100.0 * c / n), fmt_l(A["typ_loss"][t]), pp.most_common(1)[0][0], ", ".join(br)])
        self.fill(tv, rows)
        c5 = self.card(fr, "Fraud risk register - every incident scored 0-100 (double-click for details)")
        c5.pack(fill="both", expand=True, padx=4, pady=4)
        cols = ["File Name", "Branch", "Primary Perpetrator", "Staff Involvement", "Staff Collusion Indicator",
                "Customer Intent", "Fraud Typology", "Loss (Rs L)", "Net Exposure (Rs L)", "Detection Lag (days)",
                "Risk Score", "Risk Rating", "Red Flags"]
        frm, tv = self.tree(c5, cols, [170, 110, 170, 160, 300, 100, 300, 80, 110, 110, 70, 80, 500], height=10,
                            on_open=self.open_detail)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        recs = sorted(an.records, key=lambda r: -r["_score"])
        self.fill(tv, [[r["File Name"], branch_key(r), r["_perp"], r["_m"]["Staff Involvement"], r["_coll"], r["_cint"],
                        "; ".join(r["_typ"]), fmt_l(r["_loss"]), fmt_l(r["_net"]),
                        "" if r["_lag"] is None else r["_lag"], r["_score"], r["_rating"], "; ".join(r["_flags"])]
                       for r in recs], [r["_rating"] for r in recs])

    # .................................................................. 3. Charts
    def _charts(self, fr):
        an = self.result["an"]
        A = an.agg
        sf = ScrollFrame(fr)
        sf.pack(fill="both", expand=True)
        g = sf.inner
        W, H = 640, 370
        specs = []

        def add(fn, span=1):
            specs.append((fn, span))

        add(lambda c: c.donut("Primary possible fraud perpetrator (Staff / Customer / Collusion / Others)",
                              [(p, A["perp"].get(p, 0)) for p in PERP_ORDER], PERP_COLORS,
                              sub="Number of incident cases by the most likely perpetrator"))
        add(lambda c: c.donut("Loss by perpetrator (Rs L)", [(p, round(A["perp_loss"].get(p, 0) / 1e5, 2)) for p in PERP_ORDER],
                              PERP_COLORS, sub="Quantified financial impact", center_label="Rs lakhs",
                              value_fmt=lambda v: "%.2f" % v))
        add(lambda c: c.hbar("Control lapse pattern - incidents per category", A["cats"].most_common(), NAVY2,
                             sub="Which controls failed most often"))
        add(lambda c: c.hbar("Abnormality pattern - fraud typology", A["typ"].most_common(), GOLD,
                             sub="Nature of the abnormality found in gold verification"))
        hrows = [p for p in PERP_ORDER if p in A["heat"]]
        hcols = [k for k, _ in A["cats"].most_common(9)] or ["Not stated"]
        add(lambda c: c.heatmap("Pattern matrix - perpetrator × control lapse", hrows, hcols, A["heat"],
                                sub="Darker = more incidents"))
        bl = sorted(((b, e["loss"] / 1e5) for b, e in A["branch_tbl"].items()), key=lambda x: -x[1])
        add(lambda c: c.hbar("Financial impact by branch - top 10 (Rs L)", [x for x in bl if x[1] > 0], "#C0392B",
                             sub="Quantified impact", value_fmt=lambda v: "%.2f" % v))
        months = sorted(k for k in A["month"] if k != "Undated")
        mitems = [(k, A["month"][k]) for k in months[-12:]] + ([("Undated", A["month"]["Undated"])] if A["month"].get("Undated") else [])
        add(lambda c: c.vbar("Incident trend by month (date observed)", mitems, NAVY2, sub="Count of incidents"))
        gm = [(k, 100.0 * v[0] / v[1]) for k, v in sorted(A["gl_month"].items()) if v[1] and k != "Undated"][-12:]
        add(lambda c: c.vbar("Gross loss % - month on month", gm, "#C0392B",
                             sub="Financial impact / pledge value involved, by month of observation (reports stating both)",
                             value_fmt=lambda v: "%.1f%%" % v))
        # Gross loss % by branch AND month (sum of impact / sum of pledge value inside each cell)
        top_br, mset, cells, row_tot, col_tot, grand = gl_bm_grid(A, top=10, max_months=12)
        add(lambda c: c.gl_heatmap("Gross loss % - branch x month (top 10 branches by pledge value)", top_br, mset, cells,
                                   row_tot, col_tot, grand,
                                   sub="Each cell = sum of financial impact / sum of pledge value of the reports of that branch "
                                       "in that month; (n) = reports. Darker = higher loss %. Last row / column = totals."), 2)
        glb = {k: (pct_of(v[0], v[1]), v[2]) for k, v in A["gl_lag"].items() if v[1]}
        lag_note = lag_commentary(A)
        add(lambda c: c.lag_chart("Detection lag profile", [(k, A["lagb"].get(k, 0)) for k in LAG_ORDER], glb, lag_note,
                                  sub="Bars = number of reports by days between ‘Since when’ and date observed; "
                                      "GL = Gross loss % of those reports"), 2)
        add(lambda c: c.stacked("Risk rating - month on month", rating_month_items(A), STACK_ORDER, RATING_COLORS,
                                sub="Number of reports per month (date observed) by composite risk rating"))
        add(lambda c: c.hbar("How the abnormality was discovered", A["det"].most_common(), "#16A085",
                             sub="Detection method"))
        rec_items = [(k, A["recovery"].get(k, 0)) for k in ("Recovered", "Partial", "Pending", "Not stated")]
        add(lambda c: c.donut("Recovery status", rec_items, {"Recovered": "#27AE60", "Partial": "#F1C40F",
                                                             "Pending": "#C0392B", "Not stated": "#95A5A6"},
                              sub="Recovered Rs %.2f L of Rs %.2f L" % (A["total_rec"] / 1e5, A["total_loss"] / 1e5)))
        add(lambda c: c.hbar("Ornament types involved", A["orn"].most_common(), "#8E44AD", sub="Mentions across reports"))
        add(lambda c: c.hbar("Purity tests recorded", A["tests"].most_common(), "#D35400",
                             sub="Tests conducted to confirm the finding"))
        rt = sorted(((g_, e["n"]) for g_, e in A["region_tbl"].items()), key=lambda x: -x[1])
        add(lambda c: c.hbar("Incidents by region", rt, "#34495E", sub="Concentration of incidents"))
        grow = gcol = 0
        for fn, span in specs:
            if span == 2 and gcol == 1:
                grow, gcol = grow + 1, 0
            ch = Chart(g, W * span + (16 if span == 2 else 0), H, self.sc)
            ch.cv.grid(row=grow, column=gcol, columnspan=span, padx=8, pady=8, sticky="n")
            try:
                fn(ch)
            except Exception as e:
                ch.cv.create_text(20, 40, anchor="nw", text="Chart error: %s" % e, fill="red")
            gcol += span
            if gcol >= 2:
                grow, gcol = grow + 1, 0
        g.columnconfigure(0, weight=1)
        g.columnconfigure(1, weight=1)

    # .................................................................. 4. Deeper analysis
    # .................................................................. Gross loss %: all branches x months
    def _branch_month(self, p):
        A = self.result["an"].agg
        rows0, cols0, *_ = gl_bm_grid(A)
        if not rows0 or not cols0:
            tk.Label(p, text="No report states both a financial impact and a pledge value (and a date), so the "
                             "branch x month Gross loss % cannot be shown.", bg=BG, fg=MUTED).pack(pady=40)
            return
        state = {"by": "pledge", "desc": True}
        names = {"pledge": "Pledge value", "impact": "Financial impact", "loss": "Loss %", "count": "Incident count"}
        bar = tk.Frame(p, bg=BG)
        bar.pack(fill="x", pady=(2, 2))
        tk.Label(bar, text="Sort branches by:", bg=BG, fg=NAVY, font=("Segoe UI Semibold", 10)).pack(side="left", padx=(6, 6))
        btns = {}

        def mk(key, label, group):
            b = tk.Button(bar, text=label, relief="flat", bd=0, padx=12, pady=4, cursor="hand2", font=("Segoe UI Semibold", 9),
                          command=lambda: choose(group, key))
            b.pack(side="left", padx=2)
            btns[(group, key)] = b
        for k in ("pledge", "impact", "loss", "count"):
            mk(k, names[k], "by")
        tk.Label(bar, text="  Order:", bg=BG, fg=NAVY, font=("Segoe UI Semibold", 10)).pack(side="left", padx=(14, 4))
        mk(False, "Ascend", "desc")
        mk(True, "Descend", "desc")
        holder = tk.Frame(p, bg=BG)
        holder.pack(fill="both", expand=True)

        def paint():
            for (g_, k_), b in btns.items():
                on = state[g_] == k_
                b.configure(bg=NAVY if on else "#DDE3EC", fg="white" if on else TXT, activebackground=GOLD_L)

        def choose(group, key):
            state[group] = key
            render()

        def render():
            paint()
            for w in holder.winfo_children():
                w.destroy()
            rows, cols, cells, row_tot, col_tot, grand = gl_bm_grid(A, sort=state["by"], desc=state["desc"])
            tot = {b: [sum(v[0] for v in d.values()), sum(v[1] for v in d.values()), sum(v[2] for v in d.values())]
                   for b, d in A["gl_bm"].items()}
            gL, gP, gN = (sum(t[i] for t in tot.values()) for i in range(3))
            extra = [("Pledge (Rs L)", {b: "%.2f" % (tot[b][1] / 1e5) for b in rows}, "%.2f" % (gP / 1e5)),
                     ("Impact (Rs L)", {b: "%.2f" % (tot[b][0] / 1e5) for b in rows}, "%.2f" % (gL / 1e5)),
                     ("Incidents", {b: str(tot[b][2]) for b in rows}, str(gN))]
            undated = sum(v["Undated"][2] for v in A["gl_bm"].values() if "Undated" in v)
            tk.Label(holder, text="Gross loss %% of every branch (%d) by month of observation. Sorted by %s, %s order; "
                                  "pledge value, financial impact and incident count are of the reports stating both loss and pledge "
                                  "value.%s" % (len(rows), names[state["by"]], "descending" if state["desc"] else "ascending",
                                                ("  %d undated report(s) appear only in the totals." % undated) if undated else ""),
                     bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=int(1250 * self.sc), justify="left").pack(anchor="w", padx=6, pady=(2, 4))
            sf = ScrollFrame(holder, h=True)
            sf.pack(fill="both", expand=True)
            W = max(1296, 190 + (len(cols) + 1) * 100 + 104 * len(extra) + 24)
            H = max(300, 74 + (len(rows) + 1) * 28 + 24)
            ch = Chart(sf.inner, W, H, self.sc)
            ch.cv.pack(anchor="nw", padx=6, pady=6)
            ch.gl_heatmap("Gross loss %% - branch x month (all %d branches)" % len(rows), rows, cols, cells, row_tot, col_tot, grand,
                          sub="Each cell = sum of financial impact / sum of pledge value of the reports of that branch in that month; "
                              "(n) = reports. Red = 50% or more, orange = 25% to below 50%.",
                          banded=True, extra=extra)
        render()

    # .................................................................. Pledge value x Gross loss % matrix
    def _pledge_matrix(self, p):
        an = self.result["an"]
        ctl = tk.Frame(p, bg=BG)
        ctl.pack(fill="x", pady=(2, 4))
        tk.Label(ctl, text="Branch:", bg=BG, fg=NAVY, font=("Segoe UI Semibold", 10)).pack(side="left", padx=(6, 4))
        br_var = tk.StringVar(value="All branches")
        cb = ttk.Combobox(ctl, textvariable=br_var, state="readonly", width=30,
                          values=["All branches"] + sorted({branch_key(r) for r in an.records}))
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda _e: render())
        base = [r for r in an.records if is_paired(r)]
        pr0 = (0, 10, 1)          # pledge value (Rs L): Min, Max, Bin size - the user may change these
        gr0 = (10, 50, 5)         # Gross loss %: Min, Max, Bin size
        ent = {}

        def inputs(label, key, vals):
            tk.Label(ctl, text=label, bg=BG, fg=NAVY, font=("Segoe UI Semibold", 10)).pack(side="left", padx=(10, 4))
            for nm, v in zip(("Min", "Max", "Bin size"), vals):
                tk.Label(ctl, text=nm, bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(4, 2))
                sv = tk.StringVar(value="%g" % v)
                e_ = ttk.Entry(ctl, textvariable=sv, width=7, justify="right")
                e_.pack(side="left")
                e_.bind("<Return>", lambda _e: render())
                ent[(key, nm)] = sv
        inputs("Pledge value (Rs L):", "p", pr0)
        inputs("      Gross loss (%):", "g", gr0)
        card = self.card(p, "Number of reports by Total Pledge Value (rows) and Gross loss % (columns) - "
                            "double-click any number or total to list the cases")
        card.pack(fill="both", expand=True, pady=4)
        holder = tk.Frame(card, bg=CARD)
        holder.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        note = tk.Label(card, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 9), justify="left", anchor="w")
        note.pack(fill="x", padx=10, pady=(0, 8))

        def render():
            for w in holder.winfo_children():
                w.destroy()
            def rng(key, what):
                try:
                    lo, hi, st = (float(ent[(key, nm)].get().replace(",", "")) for nm in ("Min", "Max", "Bin size"))
                except Exception:
                    return None, "%s: Min, Max and Bin size must be numbers." % what
                if st <= 0 or hi <= lo:
                    return None, "%s: Max must be greater than Min and Bin size above zero." % what
                if (hi - lo) / st > 60:
                    return None, "%s: too many bands (%d) - increase the Bin size." % (what, math.ceil((hi - lo) / st))
                return (lo, hi, st), None
            prg, e1 = rng("p", "Pledge value")
            grg, e2 = rng("g", "Gross loss %")
            if e1 or e2:
                note.configure(text=" ".join(x for x in (e1, e2) if x), fg="#C0392B")
                return
            sel = br_var.get()
            recs_b = an.records if sel == "All branches" else [r for r in an.records if branch_key(r) == sel]
            xt = build_crosstab(recs_b, prg, grg)
            if not xt:
                tk.Label(holder, text="No report %sstates both a financial impact and a pledge value, so Gross loss % "
                                      "cannot be tabulated." % ("" if sel == "All branches" else "of this branch "),
                         bg=CARD, fg=MUTED).pack(pady=30)
                note.configure(text="", fg=MUTED)
                return
            rows, cols, cells = xt["rows"], xt["cols"], xt["cells"]
            head = "Pledge value (Rs L)  \\  Gross loss %"
            frm, tv = self.tree(holder, [head] + cols + ["Total"], [250] + [110] * len(cols) + [90], height=min(16, len(rows) + 3))
            frm.pack(fill="both", expand=True)
            for c_ in [head] + cols + ["Total"]:
                tv.heading(c_, text=c_, command="")          # keep the row order fixed
            tv.tag_configure("tot", background=GOLD_L, font=("Segoe UI Semibold", 9))
            for c_ in cols + ["Total"]:
                tv.column(c_, anchor="center")
            for i, lab in enumerate(rows):
                cnt = [len(cells.get((i, j), [])) for j in range(len(cols))]
                tv.insert("", "end", iid="r%d" % i, values=[lab] + [c_ if c_ else "-" for c_ in cnt] + [sum(cnt)],
                          tags=("odd",) if i % 2 else ())
            colsum = [sum(len(cells.get((i, j), [])) for i in range(len(rows))) for j in range(len(cols))]
            tv.insert("", "end", iid="total", values=["Total"] + colsum + [sum(colsum)], tags=("tot",))

            def on_dc(ev):
                iid = tv.identify_row(ev.y)
                ci = tv.identify_column(ev.x)
                if not iid or not ci:
                    return
                cidx = int(ci.replace("#", "")) - 1                     # 0 = band label, 1..n = columns, n+1 = Total
                ridx = len(rows) if iid == "total" else int(iid[1:])
                rsel = list(range(len(rows))) if ridx >= len(rows) else [ridx]
                csel = list(range(len(cols))) if (cidx < 1 or cidx > len(cols)) else [cidx - 1]
                cases = [r for i in rsel for j in csel for r in cells.get((i, j), [])]
                if not cases:
                    return
                t_r = "all pledge values" if ridx >= len(rows) else "pledge value " + rows[ridx]
                t_c = "all Gross loss %" if (cidx < 1 or cidx > len(cols)) else "Gross loss " + cols[cidx - 1]
                self.case_window("%s%s  |  %s" % ("" if sel == "All branches" else sel + "  |  ", t_r, t_c), cases)
            tv.bind("<Double-1>", on_dc)
            excluded = len(recs_b) - xt["n"]
            note.configure(fg=MUTED, text="%s: %d report(s) tabulated (those stating both financial impact and pledge value); %d report(s) left out. "
                                "Values below Min are grouped in '<Min' and values above Max in '>Max'; each band includes its lower "
                                "limit. Change Min / Max / Bin size and press Refresh (or Enter)." % (sel, xt["n"], excluded))
        ttk.Button(ctl, text="Refresh table", command=render).pack(side="left", padx=14)
        render()

    def case_window(self, title, cases):
        """New window listing the cases of a table cell; double-click a case to open the incident report."""
        top = tk.Toplevel(self.root)
        top.title("Cases - %s" % title)
        top.geometry("%dx%d" % (int(1180 * self.sc), int(520 * self.sc)))
        top.configure(bg=BG)
        tk.Label(top, text="%d case(s):  %s" % (len(cases), title), bg=BG, fg=NAVY,
                 font=("Segoe UI Semibold", 11)).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(top, text="Double-click a case to open the incident report (Word file).", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=12)
        cols = ["File Name", "Branch", "Region", "Report Date", "Date Observed", "Pledge Value (Rs L)", "Loss (Rs L)",
                "Gross Loss %", "Primary Perpetrator", "Risk Rating"]
        card = tk.Frame(top, bg=CARD)
        card.pack(fill="both", expand=True, padx=10, pady=8)
        frm, tv = self.tree(card, cols, [170, 130, 110, 100, 110, 130, 100, 100, 190, 90], height=14)
        frm.pack(fill="both", expand=True, padx=6, pady=6)
        cases = sorted(cases, key=lambda r: -(pct_of(r["_loss"], r["_pledge"]) or 0))
        self.fill(tv, [[r["File Name"], branch_key(r), clean_one(r.get("Region")), r.get("Report Date", ""), r.get("Date Observed", ""),
                        fmt_l(r["_pledge"]), fmt_l(r["_loss"]), "%.1f%%" % pct_of(r["_loss"], r["_pledge"]),
                        r["_perp"], r["_rating"]] for r in cases], [r["_rating"] for r in cases])

        def selected():
            sel = tv.selection()
            return tv.item(sel[0], "values")[0] if sel else None

        def open_it(_=None):
            f = selected()
            if f:
                self.open_report(f)

        def detail_it():
            f = selected()
            r = self.rec_by_file(f) if f else None
            if r:
                self.detail(r)
        tv.bind("<Double-1>", open_it)
        bar = tk.Frame(top, bg=BG)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bar, text="Open incident report", command=open_it).pack(side="left")
        ttk.Button(bar, text="Analysis detail", command=detail_it).pack(side="left", padx=8)
        ttk.Button(bar, text="Close", command=top.destroy).pack(side="right")

    def _open_selected(self, tv):
        sel = tv.selection()
        if sel:
            self.open_report(tv.item(sel[0], "values")[0])

    def open_report(self, fname):
        """Open the original incident report file in Word (or the default program)."""
        path = os.path.join(self.result.get("folder", ""), fname)
        if not os.path.exists(path):
            messagebox.showwarning(APP_TITLE, "The file was not found:\n\n%s" % path)
            return
        if not open_file(path):
            messagebox.showwarning(APP_TITLE, "Could not open the file:\n\n%s" % path)

    def _deeper(self, fr):
        an = self.result["an"]
        A = an.agg
        nb = SubTabs(fr, self.sc)
        nb.pack(fill="both", expand=True)

        def page(title):
            return nb.add(title)

        # Hotspots
        p = page("Branch & Region Hotspots")
        c = self.card(p, "Branch hotspot table (sorted by risk)")
        c.pack(fill="both", expand=True, pady=4)
        cols = ["Branch", "Region", "Area", "Incidents", "Loss (Rs L)", "Pledge Value (Rs L)", "Gross Loss %", "Net Exposure (Rs L)", "Recovery Pending",
                "Avg Risk Score", "Highest Rating", "Perpetrator Mix", "Repeat Branch"]
        frm, tv = self.tree(c, cols, [140, 130, 120, 80, 100, 130, 100, 130, 120, 110, 110, 330, 100], height=10)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        rows, tags = [], []
        for b, e in sorted(A["branch_tbl"].items(), key=lambda x: (-x[1]["score"] / x[1]["n"], -x[1]["loss"])):
            rows.append([b, e["region"], e["area"], e["n"], fmt_l(e["loss"]), fmt_l(e["pledge"]),
                         ("%.1f%%" % (100.0 * e["gl_loss"] / e["gl_pledge"])) if e["gl_pledge"] else "-", fmt_l(e["net"]), e["pending"],
                         "%.0f" % (e["score"] / e["n"]), e["max"], ", ".join("%s (%d)" % kv for kv in e["perp"].most_common()),
                         "YES" if e["n"] > 1 else "No"])
            tags.append(e["max"])
        self.fill(tv, rows, tags)
        c = self.card(p, "Region view")
        c.pack(fill="both", expand=True, pady=4)
        frm, tv = self.tree(c, ["Region", "Incidents", "Branches", "Loss (Rs L)", "Pledge Value (Rs L)", "Avg Risk Score", "Staff / Collusion Cases"],
                            [200, 90, 90, 110, 140, 120, 170], height=6)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[g_, e["n"], len(e["branches"]), fmt_l(e["loss"]), fmt_l(e["pledge"]), "%.0f" % (e["score"] / e["n"]), e["staff"]]
                       for g_, e in sorted(A["region_tbl"].items(), key=lambda x: -x[1]["loss"])])
        if A["pareto"]:
            t, tot, pct = A["pareto"]
            tk.Label(p, text="Pareto: top %d of %d branch(es) (20%%) carry %.0f%% of quantified loss." % (t, tot, pct),
                     bg=BG, fg="#9A7B12", font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=6)

        # Pledge value x Gross loss % cross-tab
        p = page("Pledge vs Gross Loss %")
        self._pledge_matrix(p)

        # Gross loss % - branch x month, all branches
        p = page("Gross Loss % - Branch x Month")
        self._branch_month(p)

        # Detection & recovery
        p = page("Detection, Testing & Recovery")
        row = tk.Frame(p, bg=BG)
        row.pack(fill="both", expand=True)
        c = self.card(row, "Detection method")
        c.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["Detection Method", "Cases"], [330, 70], height=9)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[k, v] for k, v in A["det"].most_common()])
        c = self.card(row, "Purity tests recorded")
        c.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["Test", "Cases"], [280, 70], height=9)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[k, v] for k, v in A["tests"].most_common()] or [["No tests recorded", 0]])
        row2 = tk.Frame(p, bg=BG)
        row2.pack(fill="both", expand=True)
        c = self.card(row2, "Detection lag (abnormality start → observation)")
        c.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["Lag Bucket", "Cases"], [200, 70], height=7)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[k, A["lagb"].get(k, 0)] for k in LAG_ORDER])
        c = self.card(row2, "Recovery position")
        c.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["Recovery Status", "Cases", "Loss (Rs L)", "Recovered (Rs L)", "Net Exposure (Rs L)"],
                            [140, 70, 100, 120, 130], height=7)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        rr = []
        for k in ("Recovered", "Partial", "Pending", "Not stated"):
            g_ = [r for r in an.records if r["_m"]["Recovery Status"] == k]
            rr.append([k, len(g_), fmt_l(sum(r["_loss"] or 0 for r in g_)), fmt_l(sum(r["_recovered"] or 0 for r in g_)),
                       fmt_l(sum(r["_net"] or 0 for r in g_))])
        self.fill(tv, rr)

        # ML clusters
        p = page("Theme Clusters (ML)")
        c = self.card(p, "K-Means clustering of incident narratives on TF-IDF vectors - groups reports with similar storylines")
        c.pack(fill="both", expand=True, pady=4)
        if A["clusters"]:
            frm, tv = self.tree(c, ["Cluster (top terms)", "Reports", "Key Terms", "Member Files"], [330, 70, 330, 700], height=10)
            frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            self.fill(tv, [[cl["label"], len(cl["members"]), ", ".join(cl["terms"]),
                            ", ".join(an.records[i]["File Name"] for i in cl["members"])] for cl in A["clusters"]])
        else:
            tk.Label(c, text="At least 4 reports with descriptive text are needed for clustering.", bg=CARD,
                     fg=MUTED).pack(pady=20)

        # Similar MO
        p = page("Similar Modus Operandi (ML)")
        c = self.card(p, "Pairs of reports with similar text (cosine similarity ≥ 30%) - cross-branch pairs may indicate an organised group")
        c.pack(fill="both", expand=True, pady=4)
        frm, tv = self.tree(c, ["Similarity", "File A", "Branch A", "File B", "Branch B", "Pattern",
                                "Perpetrator A", "Perpetrator B"], [80, 200, 120, 200, 120, 160, 170, 170],
                            height=14, on_open=self.open_detail)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [["%.0f%%" % (s_ * 100), a["File Name"], branch_key(a), b["File Name"], branch_key(b),
                        "Same branch - repeat" if branch_key(a) == branch_key(b) else "CROSS-BRANCH",
                        a["_perp"], b["_perp"]] for s_, a, b in A["pairs"]] or [["", "No similar pairs found", "", "", "", "", "", ""]])

        # Entity links
        p = page("Entity Links")
        c = self.card(p, "Names / mobile numbers / account or ID codes appearing in more than one report")
        c.pack(fill="both", expand=True, pady=4)
        frm, tv = self.tree(c, ["Type", "Identifier", "No. of Reports", "Reports", "Branches"], [150, 200, 100, 500, 300], height=14)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[k, key, len(fs), ", ".join(fs), ", ".join(bs)] for k, key, fs, bs in A["links"]]
                  or [["", "No common identifiers found", "", "", ""]])

        # Keywords
        p = page("Keyword Insights")
        row = tk.Frame(p, bg=BG)
        row.pack(fill="both", expand=True)
        c = self.card(row, "Top words (reports containing)")
        c.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["Word", "Reports"], [200, 80], height=16)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[t, v] for t, v in A["top_terms"]])
        c = self.card(row, "Top phrases (two-word)")
        c.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["Phrase", "Reports"], [260, 80], height=16)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[t, v] for t, v in A["top_bigrams"]])
        c = self.card(row, "Typical words by perpetrator")
        c.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["Perpetrator", "Frequent Words"], [200, 420], height=16)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[p_, ", ".join("%s(%d)" % kv for kv in v)] for p_, v in A["perp_terms"].items()])

        # Score breakdown
        p = page("Risk Score Breakdown")
        c = self.card(p, "How each incident's 0-100 risk score is built")
        c.pack(fill="both", expand=True, pady=4)
        parts = list(next(iter(an.records))["_score_parts"].keys())
        cols = ["File Name", "Branch"] + parts + ["Context (+repeat/similar)", "Total", "Rating"]
        frm, tv = self.tree(c, cols, [180, 120] + [120] * len(parts) + [160, 70, 80], height=14, on_open=self.open_detail)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        rows, tags = [], []
        for r in sorted(an.records, key=lambda x: -x["_score"]):
            sp = r["_score_parts"]
            ctx = r["_score"] - sum(sp.values())
            rows.append([r["File Name"], branch_key(r)] + list(sp.values()) + [max(0, ctx), r["_score"], r["_rating"]])
            tags.append(r["_rating"])
        self.fill(tv, rows, tags)

        # Data quality
        p = page("Report Data Quality")
        row = tk.Frame(p, bg=BG)
        row.pack(fill="both", expand=True)
        c = self.card(row, "Heading-wise completeness across reports")
        c.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["Heading", "Reports Filled", "% Filled"], [260, 110, 90], height=9)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[f, v, "%.0f%%" % (100.0 * v / A["n"])] for f, v in A["field_quality"].items()])
        c = self.card(row, "Report-wise missing / placeholder headings")
        c.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["File Name", "Completeness %", "Missing / Placeholder Headings"], [200, 110, 600], height=9,
                            on_open=self.open_detail)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[r["File Name"], r["_complete"], ", ".join(r["_missing"]) or "None"]
                       for r in sorted(an.records, key=lambda x: x["_complete"])])
        # reports whose pledge value / financial impact is written with a "." in the Rs value
        dot_rows = [r for r in an.records if r.get("_dot_pledge") or r.get("_dot_fin")]
        c = self.card(p, "Rs values written with a '.'  -  %d report(s) (pledge value and / or financial impact, shown exactly "
                         "as in the Word file; double-click a row to open the report)" % len(dot_rows))
        c.pack(fill="both", expand=True, padx=4, pady=4)
        frm, tv = self.tree(c, ["File Name", "Pledge Value", "Financial Impact"], [230, 380, 380], height=8,
                            on_open=lambda t: self._open_selected(t))
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.fill(tv, [[r["File Name"], ", ".join(r.get("_dot_pledge") or []), ", ".join(r.get("_dot_fin") or [])]
                       for r in dot_rows])

    # .................................................................. 5. Recommendations
    def _recos(self, fr):
        an = self.result["an"]
        recos = generate_recommendations(an)
        top = tk.Frame(fr, bg=BG)
        top.pack(fill="x")
        cnt = Counter(r[0] for r in recos)
        tk.Label(top, text="%d recommendations  -  HIGH %d  •  MEDIUM %d  •  LOW %d   (derived from the patterns found in this "
                           "set of reports)" % (len(recos), cnt["HIGH"], cnt["MEDIUM"], cnt["LOW"]), bg=BG, fg=NAVY,
                 font=("Segoe UI Semibold", 11)).pack(anchor="w", pady=(0, 6))
        c = self.card(fr)
        c.pack(fill="both", expand=True)
        frm, tx = self.text_box(c, 30)
        frm.pack(fill="both", expand=True, padx=4, pady=4)
        area_prev = None
        for i, (pr, area, txt, why) in enumerate(recos, 1):
            if area != area_prev:
                tx.insert("end", "\n" + area + "\n", "h2")
                tx.insert("end", "Evidence: " + why + "\n", "muted")
                area_prev = area
            tx.insert("end", " %s " % pr, "P_" + pr)
            tx.insert("end", "  " + txt + "\n", "bullet")
        tx.insert("end", "\nNote: ", "b")
        tx.insert("end", "Indicators are analytical pointers generated from report text to prioritise audit follow-up; "
                         "they are not a finding of fraud against any person.\n", "muted")
        tx.configure(state="disabled")

    # .................................................................. Consolidated data
    def _data(self, fr):
        an = self.result["an"]
        bar = tk.Frame(fr, bg=BG)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="Export consolidated data to CSV (opens in Excel)", style="Gold.TButton",
                   command=self.export_csv).pack(side="left")
        ttk.Button(bar, text="Export CFO report (HTML)", style="Navy.TButton",
                   command=self.export_html).pack(side="left", padx=8)
        tk.Label(bar, text="Search:", bg=BG, fg=NAVY, font=("Segoe UI Semibold", 10)).pack(side="left", padx=(20, 4))
        self.search_var = tk.StringVar()
        e = ttk.Entry(bar, textvariable=self.search_var, width=30)
        e.pack(side="left")
        tk.Label(fr, text="One row per file.  Column 1 = file name, then the report headings (uniform names), any extra headings, "
                          "unmapped text, and then the ANALYTICS METRIC columns (from ‘Loss (Rs L)’ onwards) with the outcome "
                          "for every record.  Amounts in Rs lakhs.  Double-click a row for full text.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9), anchor="w", justify="left",
                 wraplength=int(1350 * self.sc)).pack(fill="x", pady=(0, 4))
        cols = consolidated_columns(an.extra_cols)
        widths = []
        for c in cols:
            if c == "File Name":
                widths.append(190)
            elif c in ("Narration", "What Happened", "Modus Operandi", "How Discovered", "Control Failures",
                       "Steps Taken to Tighten Control", "Red Flags", "Fraud Typology", "Control Failure Categories"):
                widths.append(300)
            else:
                widths.append(130)
        frm, tv = self.tree(fr, cols, widths, height=22, on_open=self.open_detail)
        frm.pack(fill="both", expand=True)
        all_recs = an.records + self.result["failed"]
        self._data_rows = [(r, record_row(r, an.extra_cols)) for r in all_recs]

        def refresh(*_):
            q = self.search_var.get().strip().lower()
            tv.delete(*tv.get_children())
            sel = [(r, v) for r, v in self._data_rows if not q or q in " ".join(map(str, v)).lower()]
            self.fill(tv, [v for _, v in sel], [r.get("_rating", "odd") if "_rating" in r else "Critical" for r, _ in sel])

        self.search_var.trace_add("write", refresh)
        refresh()

    def export_csv(self):
        if not self.result:
            return
        p = filedialog.asksaveasfilename(title="Save consolidated data", defaultextension=".csv",
                                         initialfile="Gold_Loan_Incidents_Consolidated_%s.csv" % dt.date.today().strftime("%Y%m%d"),
                                         filetypes=[("CSV (Excel)", "*.csv")])
        if not p:
            return
        try:
            an = self.result["an"]
            full = Analyzer.__new__(Analyzer)
            full.records = an.records + self.result["failed"]
            full.extra_cols = an.extra_cols
            export_csv(p, full)
            messagebox.showinfo(APP_TITLE, "Saved:\n%s" % p)
        except Exception as e:
            messagebox.showerror(APP_TITLE, "Could not save (is the file open in Excel?)\n\n%s" % e)

    def export_html(self):
        if not self.result:
            return
        p = filedialog.asksaveasfilename(title="Save CFO report", defaultextension=".html",
                                         initialfile="Gold_Loan_Fraud_Control_Report_%s.html" % dt.date.today().strftime("%Y%m%d"),
                                         filetypes=[("HTML report", "*.html")])
        if not p:
            return
        try:
            export_html(p, self.result["an"], self.result["folder"])
            if messagebox.askyesno(APP_TITLE, "Report saved:\n%s\n\nOpen it now in the browser?" % p):
                webbrowser.open("file:///" + os.path.abspath(p).replace("\\", "/"))
        except Exception as e:
            messagebox.showerror(APP_TITLE, "Could not save report:\n%s" % e)

    # .................................................................. File log
    def _log(self, fr):
        log = self.result["log"]
        c = self.card(fr, "File-wise read status")
        c.pack(fill="both", expand=True, pady=4)
        frm, tv = self.tree(c, ["File Name", "Format", "Status", "Characters Read", "Headings Captured",
                                "Headings Corrected / Made Uniform"], [220, 200, 330, 110, 120, 600], height=10,
                            on_open=self.open_detail)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        rows, tags = [], []
        for L in log:
            corr = ["%s → %s" % (a, b) for a, b, m in L["mapping"] if not m.startswith("exact") or "generic" in m]
            rows.append([L["file"], L["format"], L["status"], L["chars"], "%d of %d" % (L["found"], len(FIELD_NAMES)),
                         "; ".join(corr) or "None needed"])
            tags.append("Critical" if L["status"].startswith(("ERROR", "NO HEAD")) else
                        ("Medium" if not L["status"].startswith("OK") or "little text" in L["status"] else "odd"))
        self.fill(tv, rows, tags)
        c = self.card(fr, "Heading mapping detail - how each heading written in the file was converted to the uniform column name")
        c.pack(fill="both", expand=True, pady=4)
        frm, tv = self.tree(c, ["File Name", "Heading as written in file", "Uniform column name", "Method"],
                            [220, 300, 260, 380], height=12)
        frm.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        rows = []
        for L in log:
            for a, b, m in L["mapping"]:
                rows.append([L["file"], a, b, m])
        self.fill(tv, rows)

    # .................................................................. Methodology
    def _methodology(self, fr):
        frm, tx = self.text_box(fr, 30)
        frm.pack(fill="both", expand=True)
        T = [
            ("h1", "How this application reads and analyses the reports\n"),
            ("h2", "1. Reading the files\n"),
            ("", "• Only .docx / .docm / .doc / .pdf files in the selected folder are read (Word temporary files ‘~$…’ are skipped).\n"
                 "• .docx is read directly from its XML (tables, merged cells, tick-boxes ☒/☐, text boxes, headers).\n"
                 "• .doc (Word 97-2003) is read with a built-in binary reader that understands table cells and rows. "
                 "Files that are really RTF / HTML saved as .doc are also handled.\n"
                 "• .pdf text is read with a built-in PDF reader; table borders are used to rebuild label / value cells. "
                 "Scanned (image) PDFs contain no text and are flagged in the File Read Log.\n"
                 "• Optional: if Microsoft Word is installed, it is used automatically as a back-up converter for files "
                 "that the built-in readers cannot read.\n"),
            ("h2", "2. Uniform column names (heading correction)\n"),
            ("", "Each heading found in the first column of the report (or before a colon) is matched to a standard column: "
                 + ", ".join(FIELD_NAMES) + ". Matching uses a synonym list (e.g. ‘Control lapses’ → Control Failures), "
                 "spelling-error correction by edit distance (e.g. ‘Brnach’ → Branch, ‘Modus Operendi’ → Modus Operandi), "
                 "removal of numbering such as ‘(a)’, ‘1.’, and prefix matching (‘Financial impact in Rs’). The first "
                 "‘Date’ at the top of the report becomes Report Date; the ‘Date’ at the end becomes Date Observed. "
                 "Other headings are kept as extra columns. Every correction is listed in the File Read Log.\n"),
            ("h2", "3. Metrics added to every record (Consolidated Data)\n"),
            ("", "• Loss (Rs L): rupee figure in ‘Financial impact’ (Rs / INR / ₹, lakh / crore understood; the ‘total’ figure "
                 "if stated, otherwise ALL Rs figures are added up). Shown in Rs lakhs.\n"
                 "• Total Pledge Value (Rs L): every amount described as pledge value / gold value / loan amount / sanctioned "
                 "amount in ‘What happened’ (falls back to Narration), ignoring loss, recovery, interest and per-gram rates. A stated "
                 "‘total’ is used; otherwise the amounts are added up (pledge value is preferred over loan amount). "
                 "Gross Loss % = Financial impact (Loss) / pledge value involved. If Loss is not stated, the pledge value is used as the exposure for the risk score.\n"
                 "• Recovery Status: Recovered / Partial / Pending / Not stated; Recovered (Rs L) and Net Exposure (Rs L).\n"
                 "• Detection Lag (days): ‘Since when’ to Date Observed.\n"
                 "• Primary Perpetrator: weighted text evidence in People involved (×3), Modus operandi (×2), What happened "
                 "(×1.5), Narration (×1.2) for staff, customer, agent, collusion and process-error language, with negation "
                 "handling (‘no staff involved’). If not stated, the nature of the abnormality is used (custody/release/cash "
                 "type → insider; spurious/low purity/filled ornaments → customer).\n"
                 "• Staff Collusion Indicator: Strong (collusion language) / Possible (non-genuine gold accepted at appraisal, "
                 "or insider act on customer accounts) / Low (report denies staff role - validate) / Not indicated.\n"
                 "• Customer Intent to Defraud: Strong / Indicative / Not indicated.\n"
                 "• Fraud Typology: spurious gold, low purity, weight manipulation/filler, swapping, missing/tampered packets, "
                 "over-valuation/LTV, benami/KYC, unauthorised release, re-pledge, cash misappropriation, stolen gold. "
                 "If only purity tests are mentioned, ‘Spurious / Low-Purity Gold (inferred from tests)’.\n"
                 "• Control Failure Categories: 13 gold-loan control areas (appraisal & purity testing, weighing, KYC, dual "
                 "custody/vault, packet sealing, LTV, maker-checker, surprise verification, release/auction, MIS/CCTV, "
                 "training, rotation/segregation, linked accounts).\n"
                 "• Detection Method, Purity Tests Conducted (tick-boxes respected, negations ignored), Gold Weight, "
                 "Accounts/Packets, Ornament Types, Branch Repeat Count.\n"
                 "• Similar Incidents (ML): TF-IDF vectors (words + two-word phrases) and cosine similarity ≥ 30%.\n"
                 "• Theme Cluster (ML): K-Means clustering of narratives (k chosen from the number of reports).\n"
                 "• Data Completeness %: share of 14 key headings that carry real content (placeholders like ‘xxxx’ count as empty).\n"),
            ("h2", "4. Composite risk score (0-100)\n"),
            ("", "Financial severity up to 30 (unknown 12; <0.5 L 6; <1 L 10; <5 L 16; <10 L 22; <25 L 26; ≥25 L 30) + "
                 "Perpetrator/intent up to 25 (collusion 25, staff 22, agent 16, customer 13, undetermined 10, process 6; "
                 "+4 if collusion is ‘Possible’) + Control gaps up to 15 (5 per category) + Recovery up to 15 (pending 15, "
                 "not stated 10, partial 9, recovered 2) + Detection lag up to 10 + Typology severity up to 5 + context "
                 "(+3 repeat branch, +2 similar MO elsewhere).  Rating: Critical ≥ 70, High 55-69, Medium 40-54, Low < 40.\n"),
            ("h2", "5. Important\n"),
            ("", "All indicators come from the wording of the reports. They help the CFO and Audit Committee prioritise "
                 "follow-up; they are not a conclusion of fraud against any individual. Better-filled reports give better analytics.\n"),
        ]
        for tag, t in T:
            tx.insert("end", t, tag) if tag else tx.insert("end", t)
        tx.configure(state="disabled")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] in ("--read-only", "--readonly"):
        read_only_cli(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        return
    if tk is None:
        print("tkinter is not available in this Python installation. Please install Python from python.org "
              "(tick 'tcl/tk and IDLE' during setup).")
        return
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
