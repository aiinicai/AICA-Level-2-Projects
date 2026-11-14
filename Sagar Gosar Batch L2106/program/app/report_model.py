"""Presentation model shared by the screen and the Word / PDF exporters."""
from .pages import format_pages

PLAIN = "plain"
# style -> (text colour, fill, strike, underline, italic)
STYLE_DEF = {"plain": ("", "", False, False, False), "del": ("B91C1C", "FEE2E2", True, False, False),
             "ins": ("166534", "DCFCE7", False, True, False), "ocr": ("92400E", "FEF3C7", False, False, True)}
SEV_FILL = {"Critical": "F8D7DA", "Major": "FDE5CC", "Minor": "FFF3CD", "Info": "E2E8F0"}
SEV_TEXT = {"Critical": "9B1C1C", "Major": "9A4A06", "Minor": "7A5B00", "Info": "334155"}
LEGEND = [("Text only in the draft / changed", "del"), ("Text only in the executed copy / changed", "ins"), ("Probable OCR misreading", "ocr")]
DISCLAIMER = ("Automated comparison for review support. OCR can misread scans; verify every difference against the signed original "
              "before relying on this report. It is not legal advice.")


def clause_label(it):
    return (it.label_a or it.label_b or "—").strip() or "—"


def summary_lines(r):
    s = r.stats; b = s["by_severity"]
    lines = [f"Text similarity (word level): {r.similarity:.1f}%",
             f"Differences reported: {s['total']}  (Critical {b['Critical']}, Major {b['Major']}, Minor {b['Minor']}, Info {b['Info']})"]
    if r.stats.get("ocr_variances"):
        lines.append(f"Probable OCR misreadings (not counted): {r.stats['ocr_variances']}")
    if r.anchors_used:
        lines.append(f"Manual links applied: {r.anchors_used}")
    return lines


def _size(n):
    return f"{n / 1024:.0f} KB" if n < 1 << 20 else f"{n / (1 << 20):.1f} MB"


def meta_rows(r):
    for role, lab, d in (("Draft / base", r.label_a, r.doc_a), ("Executed copy", r.label_b, r.doc_b)):
        extra = f"{len(d.blocks)} paragraphs"
        if d.kind in ("pdf", "image"):
            extra += f", {d.n_pages} page(s)" + (f", OCR on {format_pages(d.ocr_pages)}" if d.ocr_pages else ", text layer")
        yield role, lab, (d.name, _size(d.size), d.modified, d.sha256, extra)


def _trim(text, n, head):
    w = text.split()
    if len(w) <= n:
        return text
    return (" ".join(w[-n:]) if head else " ".join(w[:n]))


def runs_for_item(it, context_words=None):
    """-> (left_runs, right_runs); each run is (text, style) and carries its own trailing space."""
    left, right = [], []
    n = len(it.ops)
    for k, (tag, ta, tb) in enumerate(it.ops):
        if tag == "equal":
            ca, cb = ta, tb
            if context_words:
                ca = ("… " if k == 0 and ta.split()[context_words:] else "") + _trim(ta, context_words, k == 0) + (" …" if k == n - 1 and len(ta.split()) > context_words else "")
                cb = ("… " if k == 0 and tb.split()[context_words:] else "") + _trim(tb, context_words, k == 0) + (" …" if k == n - 1 and len(tb.split()) > context_words else "")
            if ca:
                left.append((ca + " ", PLAIN))
            if cb:
                right.append((cb + " ", PLAIN))
        elif tag == "ocr":
            if ta:
                left.append((ta + " ", "ocr"))
            if tb:
                right.append((tb + " ", "ocr"))
        else:
            if ta and tag in ("delete", "replace"):
                left.append((ta + " ", "del"))
            if tb and tag in ("insert", "replace"):
                right.append((tb + " ", "ins"))
    if not left and it.text_a:
        left = [(it.text_a, PLAIN)]
    if not right and it.text_b:
        right = [(it.text_b, PLAIN)]
    return left, right


def redline_runs(row):
    """Combined redline of one paragraph: deleted words struck, inserted words underlined.  -> [(text, style)]"""
    out = []
    for tag, ta, tb in row.ops:
        if tag == "equal":
            out.append((tb or ta, PLAIN))
        elif tag == "ocr":
            out.append((tb or ta, "ocr"))
        else:
            if ta and tag in ("delete", "replace"):
                out.append((ta, "del"))
            if tb and tag in ("insert", "replace"):
                out.append((tb, "ins"))
    return out


def keyfigure_rows(result):
    """-> (header_lines, rows) ; rows = [(kind, draft, executed, clause, status)] for every figure that is not identical on both sides."""
    from . import keyfacts
    rec = keyfacts.reconcile(result)
    lines, rows = [], []
    for kind in keyfacts.KINDS:
        v = rec[kind]
        if v["draft_total"] or v["exec_total"]:
            lines.append(f"{kind}s: {v['matched']} of {v['draft_total']} figures in the draft appear unchanged in the executed copy ({v['exec_total']} found in the executed copy).")
        for r in v["rows"]:
            rows.append((kind, r["draft"], r["executed"], r["clause"] + (f" · p.{r['page']}" if r["page"] else ""), r["status"]))
    return lines, rows


def ocr_quality(result):
    """-> [(page, confidence, words, note)] for the scanned pages of the executed copy."""
    d = result.doc_b; out = []
    for p in sorted(d.page_conf):
        if p in d.ocr_pages:
            note = "Low – verify against the scan" if d.page_conf[p] < 80 else ("Fair" if d.page_conf[p] < 88 else "Good")
            out.append((p, d.page_conf[p], d.page_words.get(p, 0), note))
    return out
