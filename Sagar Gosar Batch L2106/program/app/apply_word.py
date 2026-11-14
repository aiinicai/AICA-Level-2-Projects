"""Save an updated Word file: the draft conformed to the executed copy for the changes the user has accepted.

Two modes
  tracked – every accepted change is written as a real Word tracked change (w:ins / w:del) so it can be reviewed, accepted or
            rejected in Word itself;
  clean   – the accepted changes are simply applied.
Only paragraphs with an accepted change are touched; everything else in the document (styles, tables, headers, numbering) stays as is.
Inside a changed paragraph the formatting of the main text run is used for all words (inline bold of defined terms is not carried over).
Words that the comparison classed as OCR variance are never applied – the draft wording is kept.
"""
import copy
import datetime as dt
import re

from lxml import etree

from .extract_docx import NS, W, _para_text, q
from .textutil import clean_text


def _norm(t):
    return re.sub(r"\s+", " ", (t or "")).strip()


def _paragraphs(doc):
    """Paragraph elements in exactly the order extract_docx numbers its blocks."""
    out = []

    def add(p):
        if clean_text(_para_text(p)):
            out.append(p)

    def walk(el):
        for ch in el:
            if ch.tag == q("p"):
                add(ch)
            elif ch.tag == q("tbl"):
                for tr in ch.findall("w:tr", NS):
                    for tc in tr.findall("w:tc", NS):
                        for p in tc.iter(q("p")):
                            add(p)
            elif ch.tag == q("sdt"):
                c = ch.find("w:sdtContent", NS)
                if c is not None:
                    walk(c)
            elif ch.tag == q("ins"):
                walk(ch)
    walk(doc.element.body)
    return out


class _Rev:
    def __init__(self, author):
        self.author = author; self.n = 9000; self.date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def attrs(self, el):
        self.n += 1
        el.set(q("id"), str(self.n)); el.set(q("author"), self.author); el.set(q("date"), self.date)
        return el


def _run(text, rpr, deleted=False):
    r = etree.Element(q("r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, q("delText" if deleted else "t")); t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return r


def _main_rpr(p):
    best, bl = None, -1
    for r in p.iter(q("r")):
        tx = "".join(t.text or "" for t in r.iter(q("t")))
        if len(tx) > bl:
            bl = len(tx); best = r.find("w:rPr", NS)
    return best


def _clear(p):
    """Remove the content of a paragraph but keep pPr and bookmarks."""
    keep = []
    for ch in list(p):
        if ch.tag == q("pPr") or ch.tag in (q("bookmarkStart"), q("bookmarkEnd")):
            keep.append(ch)
        else:
            p.remove(ch)
    return keep


def _segments(ops):
    """ops -> [(kind, text)] with kind in keep | del | ins; OCR variances keep the draft wording."""
    seg = []
    for tag, ta, tb in ops:
        if tag in ("equal", "ocr"):
            seg.append(("keep", ta))
        elif tag == "delete":
            seg.append(("del", ta))
        elif tag == "insert":
            seg.append(("ins", tb))
        else:                                   # replace
            seg.append(("del", ta)); seg.append(("ins", tb))
    return [(k, t) for k, t in seg if t]


def _rewrite(p, row, rev, tracked):
    full = _norm(_para_text(p))
    body_a = _norm(" ".join(ta for tag, ta, _tb in row.ops if tag != "insert" and ta))
    idx = full.find(body_a[:40]) if body_a else -1
    prefix = full[:idx] if idx > 0 else ""
    rpr = _main_rpr(p)
    _clear(p)
    seg = _segments(row.ops)
    first = True
    if prefix:
        p.append(_run(prefix, rpr)); first = False
    for kind, text in seg:
        text = ("" if first else " ") + text
        if kind == "keep":
            p.append(_run(text, rpr))
        elif kind == "del":
            if tracked:
                d = rev.attrs(etree.Element(q("del"))); d.append(_run(text, rpr, True)); p.append(d)
        else:
            if tracked:
                i = rev.attrs(etree.Element(q("ins"))); i.append(_run(text, rpr)); p.append(i)
            else:
                p.append(_run(text, rpr))
        first = False


def _mark_paragraph(p, rev, what):
    """Tracked insertion / deletion of the paragraph mark itself."""
    ppr = p.find("w:pPr", NS)
    if ppr is None:
        ppr = etree.Element(q("pPr")); p.insert(0, ppr)
    rpr = ppr.find("w:rPr", NS)
    if rpr is None:
        rpr = etree.SubElement(ppr, q("rPr"))
    rpr.insert(0, rev.attrs(etree.Element(q(what))))


def build_updated_word(result, src_docx, out_path, accepted_ids=None, mode="tracked", author="Agreement Compare", progress=None):
    """Write `out_path`.  accepted_ids = set of item ids to apply (None = every non-OCR difference).
    -> dict(applied, inserted, deleted, skipped=[...], paragraphs)"""
    import docx
    from .extract_docx import extract_docx
    prog = progress or (lambda f, m: None)
    tracked = mode == "tracked"
    d = docx.Document(src_docx)
    paras = _paragraphs(d)
    blocks = extract_docx(src_docx).blocks
    if len(paras) != len(blocks):
        raise RuntimeError("The Word file could not be matched paragraph-by-paragraph with the comparison (was it changed after comparing?).")
    key = lambda a, b: (a, b)
    want = set()
    for it in result.items:
        if it.ocr_only:
            continue
        if accepted_ids is None or it.id in accepted_ids:
            want.add(key(it.text_a, it.text_b))
    rev = _Rev(author)
    stats = dict(applied=0, inserted=0, deleted=0, skipped=[], paragraphs=len(paras))
    ptr = 0; last = None
    todo = []
    for n, row in enumerate(result.rows):
        el = None
        if row.text_a:
            for j in range(ptr, len(blocks)):
                if _norm(blocks[j].text) == _norm(row.text_a):
                    el = paras[j]; ptr = j + 1; break
            if el is None and key(row.text_a, row.text_b) in want:
                stats["skipped"].append(f"{row.label_a or row.text_a[:40]} – paragraph not located in the Word file")
        if key(row.text_a, row.text_b) in want and row.kind != "equal":
            todo.append((row, el, last))
        if el is not None:
            last = el
    for k, (row, el, anchor) in enumerate(todo):
        prog(k / max(1, len(todo)), "Applying accepted changes…")
        if not row.text_a:                                         # clause present only in the executed copy -> insert
            if anchor is None:
                anchor = paras[0]
            newp = etree.Element(q("p"))
            ppr = anchor.find("w:pPr", NS)
            if ppr is not None:
                ppr = copy.deepcopy(ppr)
                for bad in ppr.findall("w:numPr", NS) + ppr.findall("w:rPr", NS):
                    ppr.remove(bad)
                newp.append(ppr)
            rpr = _main_rpr(anchor)
            body = row.text_b
            if tracked:
                i = rev.attrs(etree.Element(q("ins"))); i.append(_run(body, rpr)); newp.append(i); _mark_paragraph(newp, rev, "ins")
            else:
                newp.append(_run(body, rpr))
            anchor.addnext(newp); stats["inserted"] += 1
        elif not row.text_b:                                       # clause missing from the executed copy -> delete
            if el is None:
                continue
            if tracked:
                rpr = _main_rpr(el); txt = _norm(_para_text(el)); _clear(el)
                dl = rev.attrs(etree.Element(q("del"))); dl.append(_run(txt, rpr, True)); el.append(dl); _mark_paragraph(el, rev, "del")
            else:
                el.getparent().remove(el)
            stats["deleted"] += 1
        else:
            if el is None:
                continue
            if all(t in ("equal", "ocr") for t, _a, _b in row.ops):
                continue
            _rewrite(el, row, rev, tracked); stats["applied"] += 1
    d.save(out_path)
    return stats
