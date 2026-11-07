"""Paragraph-pair comparison, classification and severity."""
import re
import time
from collections import Counter
from difflib import SequenceMatcher

from . import reflow
from .extract_pdf import Cancelled
from .models import CompareResult, Item, Row
from .textutil import NUM_WORDS, fmt_inr, is_blank, parse_amounts, token_key

SEV_ORDER = {"Critical": 0, "Major": 1, "Minor": 2, "Info": 3}
MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
          "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"}
PERIOD_UNITS = {"day", "days", "month", "months", "year", "years", "week", "weeks", "quarter", "quarters", "hour", "hours", "annum", "monthly",
                "yearly", "annual", "annually"}
STRICT_UNITS = {"day", "days", "month", "months", "year", "years", "week", "weeks", "quarter", "quarters", "hour", "hours"}
CURRENCY = {"rs", "inr", "₹", "rupees", "rupee", "usd", "$", "eur", "€", "/-", "lakh", "lakhs", "lac", "lacs", "crore", "crores", "million"}
LEGAL_CRIT = {"may", "shall", "must", "will", "would", "should", "can", "cannot", "not", "no", "never", "without", "unless", "except",
              "irrevocable", "irrevocably", "exclusive", "non-exclusive", "jointly", "severally", "absolute", "absolutely", "neither", "nor"}
LEGAL_MAJOR = {"and", "or", "any", "all", "each", "either", "only", "subject", "provided", "notwithstanding", "liable", "liability", "indemnify",
               "terminate", "termination", "waive", "waiver", "consent", "sole", "entire", "consecutive", "forthwith", "immediately"}
PARTY = {"licensor", "licensee", "lessor", "lessee", "landlord", "tenant", "buyer", "seller", "purchaser", "vendor", "borrower", "lender",
         "employer", "employee", "company", "owner", "contractor", "client", "principal", "agent", "guarantor", "first", "second", "party", "parties"}
FORMAL = ("witness", "signature", "signed", "signatory", "stamp", "notar", "seal", "initial", "attested", "thumb", "executed by", "in the presence")
_OCR_FOLD = str.maketrans({"I": "1", "l": "1", "|": "1", "!": "1", "O": "0", "o": "0", "S": "5", "B": "8", "Z": "2", "s": "5"})


def _strip(w):
    return re.sub(r"^[^\w₹$%]+|[^\w₹$%/-]+$", "", w.lower())


def _q(ws, n=80):
    t = " ".join(ws)
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def _nums(ws):
    v = parse_amounts(ws)
    if v:
        return v
    out = []
    for w in ws:
        k = _strip(w).strip("()")
        if k in NUM_WORDS:
            out.append(float(NUM_WORDS[k]))
    return out


def _fmt_plain(v):
    return ("%g" % v) if abs(v) < 1e6 else fmt_inr(v)


# ------------------------------------------------------------------ word-level diff of one pair
def diff_words(wa, wb, opts):
    """-> list of (tag, a0, a1, b0, b1) covering both word lists completely."""
    ka = [(token_key(w, opts.ignore_case, opts.compare_punct), i) for i, w in enumerate(wa)]
    kb = [(token_key(w, opts.ignore_case, opts.compare_punct), i) for i, w in enumerate(wb)]
    ka = [(k, i) for k, i in ka if k]; kb = [(k, i) for k, i in kb if k]
    A, B = [k for k, _ in ka], [k for k, _ in kb]
    ia, ib = [i for _, i in ka], [i for _, i in kb]
    if A == B:
        return [("equal", 0, len(wa), 0, len(wb))]
    sm = SequenceMatcher(None, A, B, autojunk=False)
    out, pa, pb = [], 0, 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        ea = ia[i2] if i2 < len(ia) else len(wa)
        eb = ib[j2] if j2 < len(ib) else len(wb)
        if tag == "equal" or (ea > pa or eb > pb):
            out.append((tag, pa, ea, pb, eb))
        pa, pb = ea, eb
    return out


_STOP1 = {"the", "a", "an", "of", "to", "in", "is", "be", "by", "as", "at", "on"}


def _is_ocr_variance(da, ib, confs, vocab, opts, b_ocr):
    """True when a difference is most probably a misreading of the scan rather than a change in the document."""
    if not (opts.ocr_tolerance and b_ocr):
        return False
    ja = "".join(da).lower(); jb = "".join(ib).lower()
    lowconf = bool(confs) and (sum(confs) / len(confs) < 72 or min(confs) < 55)
    invocab = bool(ib) and all(_strip(w) in vocab for w in ib)
    if da and ib:
        if len(da) <= 4 and len(ib) <= 4 and ja != jb and ja.translate(_OCR_FOLD) == jb.translate(_OCR_FOLD):
            return True
        if re.fullmatch(r"\d+(st|nd|rd|th)", ja) and re.fullmatch(r"[il|1]?(st|nd|rd|th)", jb):
            return True
        if re.search(r"\d", ja + jb):
            return False                           # digits: only the confusions above may be excused
        if len(da) > 6 or len(ib) > 6:
            return False
        if invocab:
            return ja == jb                        # a genuine word of the draft: a real substitution
        if ja.replace(" ", "") == jb.replace(" ", ""):
            return True
        if lowconf:
            return True
        r = SequenceMatcher(None, ja, jb).ratio()
        return r >= (0.78 if min(len(ja), len(jb)) >= 5 else 0.58) or (r >= 0.6 and min(confs or [100]) < 85)
    if ib and not da:
        if any(len(re.findall(r"\d", w)) >= 2 for w in ib):
            return False
        alpha = [re.sub(r"[^A-Za-z0-9]", "", w) for w in ib]
        if len(ib) <= 2 and all(len(x) <= 2 for x in alpha):
            return True
        return len(ib) <= 8 and lowconf and not invocab
    if da and not ib:
        k = _strip(da[0])
        return len(da) == 1 and (len(k) <= 1 or k in _STOP1)
    return False


def classify(dw, iw, before, after, a_blocks_text="", b_ocr=False, low_conf=False):
    """-> (categories, severity, summary)"""
    U = dw + iw
    low = [_strip(w) for w in U]
    ctx = [_strip(w) for w in before[-3:]] + low + [_strip(w) for w in after[:2]]
    has_num = any(re.search(r"\d", w) for w in U) or any(w.strip("()") in NUM_WORDS for w in low)
    cats, sev = [], []
    nxt = _strip(after[0]) if after else ""
    nxt2 = _strip(after[1]) if len(after) > 1 else ""
    if dw and not iw or iw and not dw or dw and iw:
        pass
    blank_filled = bool(dw) and all(is_blank(w) for w in dw) and bool(iw)
    if blank_filled:
        return ["Blank filled"], "Info", f"Blank completed: {_q(iw)}"
    if has_num:
        if "%" in "".join(U) or nxt.startswith("%") or (nxt == "per" and nxt2 in ("cent", "centum")) or nxt in ("percent", "percentage"):
            cats.append("Percentage"); sev.append("Critical")
        elif (any(w in STRICT_UNITS for w in low) or nxt in STRICT_UNITS) and not (
                any(w in CURRENCY for w in [_strip(x) for x in before[-3:]] + low) or nxt in CURRENCY):
            cats.append("Period / timeline"); sev.append("Critical")
        elif (any(w in MONTHS for w in ctx) or any(re.search(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", w) for w in U)
              or any(re.fullmatch(r"(19|20)\d\d", w.strip("(),.")) for w in U) or any(re.fullmatch(r"\d{1,2}(st|nd|rd|th)", w) for w in low)):
            cats.append("Date"); sev.append("Critical")
        elif any(w in CURRENCY for w in ctx) or nxt in CURRENCY or max(_nums(U) or [0]) >= 10000:
            cats.append("Amount"); sev.append("Critical")
        else:
            cats.append("Number / reference"); sev.append("Major")
    lset = set(low)
    if "may" in lset and (has_num or any(w in MONTHS and w != "may" for w in low)):
        lset.discard("may")
    if lset and lset <= MONTHS:
        if "Date" not in cats:
            cats.append("Date"); sev.append("Critical")
        lset = set()
    if lset & LEGAL_CRIT:
        cats.append("Legal-effect wording"); sev.append("Critical")
    elif lset & PARTY:
        cats.append("Party reference"); sev.append("Critical")
    elif lset & LEGAL_MAJOR:
        cats.append("Legal-effect wording"); sev.append("Major")
    if not cats:
        caps = [w for w in U if re.match(r"^[A-Z][a-z]{2,}", w)]
        if caps and (not dw or not iw or len(caps) >= 1):
            cats.append("Name / defined term"); sev.append("Major")
    n = max(len(dw), len(iw))
    if not cats:
        if dw and iw:
            cats.append("Wording change")
        elif iw:
            cats.append("Text added")
        else:
            cats.append("Text deleted")
        sev.append("Minor" if n <= 6 and not (n >= 6 and (not dw or not iw)) else ("Major" if n <= 25 else "Critical"))
    else:
        if n > 25:
            cats.append("Wording change" if dw and iw else ("Text added" if iw else "Text deleted")); sev.append("Major")
    severity = min(sev, key=lambda s: SEV_ORDER[s])
    # summary -------------------------------------------------------------------
    delta = ""
    if dw and iw and cats[0] in ("Amount", "Percentage", "Period / timeline"):
        va, vb = _nums(dw), _nums(iw)
        if len(va) == 1 and len(vb) == 1 and not low_conf:
            d = vb[0] - va[0]
            if cats[0] == "Amount":
                delta = f"  [Δ {'+' if d >= 0 else '-'}{fmt_inr(abs(d))}]"
            elif cats[0] == "Percentage":
                delta = f"  [Δ {'+' if d >= 0 else '-'}{abs(d):g} pts]"
            else:
                delta = f"  [Δ {'+' if d >= 0 else '-'}{abs(d):g}]"
    if dw and iw:
        summary = f"“{_q(dw)}” → “{_q(iw)}”{delta}"
    elif iw:
        summary = f"Inserted “{_q(iw)}”"
    else:
        summary = f"Deleted “{_q(dw)}”"
    return cats, severity, summary


def _block_item_kind(text, n_words, added):
    t = text.lower()
    if any(k in t for k in FORMAL):
        return ["Execution formalities"], "Info" if added else "Major"
    if n_words >= 12:
        return (["Clause added"], "Critical") if added else (["Clause deleted"], "Critical")
    if n_words >= 5:
        return (["Clause added"], "Major") if added else (["Clause deleted"], "Major")
    return (["Clause added"], "Minor") if added else (["Clause deleted"], "Minor")


# ------------------------------------------------------------------ main entry
def compare_documents(doc_a, doc_b, opts, progress=None, cancel=None, anchors=None):
    def chk():
        if cancel is not None and ((hasattr(cancel, "is_set") and cancel.is_set()) or (callable(cancel) and not hasattr(cancel, "is_set") and cancel())):
            raise Cancelled()
    prog = progress or (lambda f, m: None)
    chk(); prog(0.02, "Aligning paragraphs…")
    if opts.reflow:
        units, ignored = reflow.align(doc_a, doc_b, opts, anchors, cancel=lambda: bool(cancel is not None and cancel.is_set()) if hasattr(cancel, "is_set") else False)
    else:
        units, ignored = _simple_align(doc_a, doc_b, opts, anchors)
    chk(); prog(0.35, "Comparing wording…")
    A, B = doc_a.blocks, doc_b.blocks
    vocab = {_strip(w) for b in A for w in b.body.split()}
    items, rows = [], []
    eq_words = tot_a = tot_b = 0
    n_pairs = n_ident = 0
    next_id = [1]

    def add_item(**kw):
        it = Item(id=next_id[0], **kw); next_id[0] += 1; items.append(it); return it

    for k, u in enumerate(units):
        if k % 25 == 0:
            chk(); prog(0.35 + 0.6 * k / max(1, len(units)), f"Comparing paragraph {k + 1} of {len(units)}…")
        a = None
        if u.a:
            a = A[u.a[0]] if len(u.a) == 1 else reflow.merge_blocks(A, u.a[0], u.a[-1] + 1)
        b = u.b
        la = a.label if a else ""; lb = b.label if b else ""
        ta = a.text if a else ""; tb = b.text if b else ""
        if a is not None:
            tot_a += len(a.body.split())
        if b is not None:
            tot_b += len(b.body.split())
        if a is None and b is not None:
            nw = len(b.body.split())
            cats, sev = _block_item_kind(b.text, nw, True)
            add_item(kind="added", severity=sev, categories=cats, summary=f"Added: “{_q(b.body.split(), 100)}”", text_a="", text_b=tb,
                     label_a="", label_b=lb, idx_b=b.idx, pages_b=sorted({r[0] for r in b.regions}) or [b.page], regions_b=list(b.regions),
                     ocr_only=False, ops=[("insert", "", b.body)])
            rows.append(Row(la, lb, "added", [("insert", "", b.body)], "", tb)); continue
        if b is None:
            nw = len(a.body.split())
            cats, sev = _block_item_kind(a.text, nw, False)
            add_item(kind="deleted", severity=sev, categories=cats, summary=f"Not found in executed copy: “{_q(a.body.split(), 100)}”",
                     text_a=ta, text_b="", label_a=la, label_b="", idx_a=a.idx, ops=[("delete", a.body, "")])
            rows.append(Row(la, "", "deleted", [("delete", a.body, "")], ta, "")); continue
        n_pairs += 1
        wa, wb = a.body.split(), b.body.split()
        ops = diff_words(wa, wb, opts)
        if len(ops) == 1 and ops[0][0] == "equal":
            n_ident += 1; eq_words += len(wa)
            rows.append(Row(la, lb, "equal", [("equal", a.body, b.body)], ta, tb)); continue
        wc = list(b.word_conf) if len(b.word_conf) == len(wb) else [b.conf] * len(wb)
        for t, a0, a1, b0, b1 in ops:
            if t == "equal":
                eq_words += a1 - a0
        # clause replaced?
        eqn = sum(a1 - a0 for t, a0, a1, b0, b1 in ops if t == "equal")
        ratio = 2.0 * eqn / max(1, len(wa) + len(wb))
        pages = sorted({r[0] for r in b.regions}) or [b.page]
        if ratio < 0.40 and len(wa) >= 8 and len(wb) >= 8:
            add_item(kind="replaced", severity="Critical", categories=["Clause replaced"], summary=f"Clause reworded substantially ({ratio * 100:.0f}% of wording common)",
                     text_a=ta, text_b=tb, label_a=la, label_b=lb, idx_a=a.idx, idx_b=b.idx, pages_b=pages, regions_b=list(b.regions),
                     ops=[("replace", a.body, b.body)])
            rows.append(Row(la, lb, "changed", [("replace", a.body, b.body)], ta, tb)); continue
        # flag each non-equal op as OCR variance or real
        flagged = []
        for t, a0, a1, b0, b1 in ops:
            if t == "equal":
                flagged.append((t, a0, a1, b0, b1, False)); continue
            da, ib = wa[a0:a1], wb[b0:b1]
            ocr = _is_ocr_variance(da, ib, wc[b0:b1], vocab, opts, b.ocr)
            flagged.append((t, a0, a1, b0, b1, ocr))
        # row ops for the redline
        rops = []
        for t, a0, a1, b0, b1, ocr in flagged:
            sa, sb_ = " ".join(wa[a0:a1]), " ".join(wb[b0:b1])
            rops.append(("equal" if t == "equal" else ("ocr" if ocr else {"delete": "delete", "insert": "insert", "replace": "replace"}[t]), sa, sb_))
        rows.append(Row(la, lb, "changed", rops, ta, tb))
        # cluster into items
        cl, cur = [], None
        for fi, (t, a0, a1, b0, b1, ocr) in enumerate(flagged):
            if t == "equal":
                if cur is not None and (a1 - a0) <= 2 and fi + 1 < len(flagged) and flagged[fi + 1][5] == cur["ocr"]:
                    cur["ops"].append((t, a0, a1, b0, b1)); continue
                cur = None; continue
            if cur is not None and cur["ocr"] == ocr:
                cur["ops"].append((t, a0, a1, b0, b1)); cur["a1"], cur["b1"] = a1, b1
            else:
                cur = dict(ocr=ocr, ops=[(t, a0, a1, b0, b1)], a0=a0, a1=a1, b0=b0, b1=b1); cl.append(cur)
        # trim cluster bounds to real changed words
        for c in cl:
            ch = [(a0, a1, b0, b1) for t, a0, a1, b0, b1 in c["ops"] if t != "equal"]
            c["a0"], c["a1"] = min(x[0] for x in ch), max(x[1] for x in ch)
            c["b0"], c["b1"] = min(x[2] for x in ch), max(x[3] for x in ch)
        for c in cl:
            dw, iw = wa[c["a0"]:c["a1"]], wb[c["b0"]:c["b1"]]
            before, after = wa[max(0, c["a0"] - 4):c["a0"]], wa[c["a1"]:c["a1"] + 4]
            if c["ocr"]:
                cats, sev = ["OCR variance"], "Info"
                summ = (f"“{_q(dw)}” → “{_q(iw)}”" if dw and iw else (f"Stray text “{_q(iw)}”" if iw else f"“{_q(dw)}” not read")) + "  (probable OCR misreading)"
            else:
                lowc = [w for w in wc[c["b0"]:c["b1"]] if w < 70]
                cats, sev, summ = classify(dw, iw, before, after, ta, b.ocr, bool(b.ocr and lowc))
                if b.ocr and lowc and any(re.search(r"\d", w) for w in dw + iw):
                    summ += "  – low OCR confidence, verify on scan"
            ctx0, ctx1 = max(0, c["a0"] - 12), min(len(wa), c["a1"] + 12)
            bc0, bc1 = max(0, c["b0"] - (c["a0"] - ctx0)), min(len(wb), c["b1"] + (ctx1 - c["a1"]))
            disp = [("equal", " ".join(wa[ctx0:c["a0"]]), " ".join(wb[bc0:c["b0"]]))]
            disp.append(("ocr" if c["ocr"] else ("replace" if dw and iw else ("insert" if iw else "delete")), " ".join(dw), " ".join(iw)))
            disp.append(("equal", " ".join(wa[c["a1"]:ctx1]), " ".join(wb[c["b1"]:bc1])))
            regs = list(b.regions)
            # long paragraphs: narrow the highlight to the neighbourhood of the changed words
            if len(regs) == 1:
                pg, x0, y0, x1, y1 = regs[0]
                if y1 - y0 > 0.07:
                    n = max(1, len(wb)); f0 = max(0, c["b0"] - 6) / n; f1 = min(n, c["b1"] + 6) / n
                    ya = max(y0, y0 + (y1 - y0) * f0 - 0.012); yb = min(y1, y0 + (y1 - y0) * f1 + 0.012)
                    regs = [(pg, x0, ya, x1, max(yb, ya + 0.03))]
            add_item(kind="replaced" if dw and iw else ("added" if iw else "deleted"), severity=sev, categories=cats, summary=summ,
                     text_a=ta, text_b=tb, label_a=la, label_b=lb, idx_a=a.idx, idx_b=b.idx, pages_b=pages, regions_b=regs,
                     ocr_only=c["ocr"], ops=disp,
                     low_conf=bool(b.ocr and any(w < 70 for w in wc[c["b0"]:c["b1"]])))
    # ---------------------------------------------------------------- statistics & observations
    real = [i for i in items if not i.ocr_only]
    by = {s: sum(1 for i in real if i.severity == s) for s in ("Critical", "Major", "Minor", "Info")}
    stats = {"total": len(real), "by_severity": by, "ocr_variances": len(items) - len(real), "paragraph_pairs": n_pairs, "identical_pairs": n_ident,
             "by_category": dict(Counter(c for i in real for c in i.categories))}
    sim = 100.0 * 2 * eq_words / max(1, tot_a + tot_b)
    obs = []
    if ignored:
        obs.append(("Info", f"{len(ignored)} stamp / registration / noise text segment(s) in the executed copy were left out of the comparison."))
    if doc_b.page_transform:
        rot = {p: t[0] for p, t in doc_b.page_transform.items() if t[0]}
        if rot:
            obs.append(("Info", "Pages turned upright before reading: " + ", ".join(f"{p} ({r}°)" for p, r in sorted(rot.items())) + "."))
    for p, c in sorted(doc_b.page_conf.items()):
        if p in doc_b.ocr_pages and c < 75:
            obs.append(("Minor", f"Page {p} average OCR confidence {c:.0f}% – verify differences on that page against the scan."))
    for p in doc_b.ocr_pages:
        if doc_b.page_words.get(p, 0) < 20 and p in doc_b.pages_used:
            obs.append(("Major", f"Page {p} of the executed copy yielded almost no text – it may be blank, handwritten or an image."))
    if tot_a and (eq_words / max(1, tot_a)) < 0.6:
        obs.append(("Major", f"Only {100 * eq_words / tot_a:.0f}% of the draft wording was found unchanged in the executed copy – check that the correct documents and pages were selected."))
    if stats["ocr_variances"]:
        obs.append(("Info", f"{stats['ocr_variances']} probable OCR misreading(s) are shown in the redline but not counted as differences."))
    if doc_b.excluded_pages:
        from .pages import format_pages
        obs.append(("Info", "Pages not included in the comparison: " + format_pages(doc_b.excluded_pages) + "."))
    res = CompareResult(doc_a=doc_a, doc_b=doc_b, items=items, rows=rows, stats=stats, observations=obs, similarity=round(sim, 1),
                        raw_a=doc_a, raw_b=doc_b, ignored_b=ignored, anchors_used=len(anchors or []),
                        created=time.strftime("%Y-%m-%d %H:%M"), n_pairs=n_pairs, n_identical=n_ident)
    prog(1.0, "Done")
    return res


def _simple_align(doc_a, doc_b, opts, anchors):
    """Paragraph-by-paragraph alignment without re-flowing the executed copy."""
    A, B = doc_a.blocks, doc_b.blocks
    ka = [[token_key(w, opts.ignore_case, opts.compare_punct) for w in b.body.split() if token_key(w, opts.ignore_case, opts.compare_punct)] for b in A]
    kb = [[token_key(w, opts.ignore_case, opts.compare_punct) for w in b.body.split() if token_key(w, opts.ignore_case, opts.compare_punct)] for b in B]
    pr = reflow._pair_dp(ka, kb, 0.30)
    units, ignored, j = [], [], 0
    pm = dict(pr)
    for i in range(len(A)):
        if i in pm:
            while j < pm[i]:
                reflow._emit_b_only(B[j], units, ignored, A, opts); j += 1
            units.append(reflow.Unit([i], B[pm[i]], "paired")); j = pm[i] + 1
        else:
            units.append(reflow.Unit([i], None, "deleted"))
    while j < len(B):
        reflow._emit_b_only(B[j], units, ignored, A, opts); j += 1
    return units, ignored
