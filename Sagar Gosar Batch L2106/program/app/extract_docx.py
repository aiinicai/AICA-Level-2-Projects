"""Read a Word (.docx) file into paragraph blocks, honouring tables, tracked insertions and auto-numbering."""
import hashlib
import os
import re
import time

from lxml import etree

from .models import Block, DocText
from .textutil import clean_text, split_label

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def q(tag):
    return "{%s}%s" % (W, tag)


def _roman(n):
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s; n -= v
    return out


def _alpha(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(97 + r) + s
    return s


def _fmt(n, f):
    if f == "decimal":
        return str(n)
    if f == "decimalZero":
        return "%02d" % n
    if f == "lowerLetter":
        return _alpha(n)
    if f == "upperLetter":
        return _alpha(n).upper()
    if f == "lowerRoman":
        return _roman(n)
    if f == "upperRoman":
        return _roman(n).upper()
    if f == "bullet" or f == "none":
        return ""
    return str(n)


class Numbering:
    def __init__(self, doc):
        self.abs, self.num, self.counters = {}, {}, {}
        self.style_num = {}
        try:
            root = doc.part.numbering_part.element
        except Exception:
            root = None
        if root is not None:
            for a in root.findall("w:abstractNum", NS):
                aid = a.get(q("abstractNumId")); lv = {}
                for l in a.findall("w:lvl", NS):
                    i = int(l.get(q("ilvl")))
                    st = l.find("w:start", NS); nf = l.find("w:numFmt", NS); lt = l.find("w:lvlText", NS)
                    lv[i] = (int(st.get(q("val"))) if st is not None else 1, nf.get(q("val")) if nf is not None else "decimal",
                             lt.get(q("val")) if lt is not None else "%1.")
                self.abs[aid] = lv
            for n in root.findall("w:num", NS):
                nid = n.get(q("numId")); a = n.find("w:abstractNumId", NS)
                ov = {}
                for o in n.findall("w:lvlOverride", NS):
                    s = o.find("w:startOverride", NS)
                    if s is not None:
                        ov[int(o.get(q("ilvl")))] = int(s.get(q("val")))
                self.num[nid] = (a.get(q("val")) if a is not None else None, ov)
        try:
            for st in doc.styles.element.findall("w:style", NS):
                np_ = st.find("w:pPr/w:numPr", NS)
                if np_ is not None:
                    nid = np_.find("w:numId", NS); il = np_.find("w:ilvl", NS)
                    self.style_num[st.get(q("styleId"))] = (nid.get(q("val")) if nid is not None else None, int(il.get(q("val"))) if il is not None else 0)
        except Exception:
            pass

    def label(self, p):
        ppr = p.find("w:pPr", NS)
        if ppr is None:
            return ""
        nid = lvl = None
        np_ = ppr.find("w:numPr", NS)
        if np_ is not None:
            n = np_.find("w:numId", NS); l = np_.find("w:ilvl", NS)
            nid = n.get(q("val")) if n is not None else None
            lvl = int(l.get(q("val"))) if l is not None else None
        ps = ppr.find("w:pStyle", NS)
        if ps is not None and ps.get(q("val")) in self.style_num:
            sn, sl = self.style_num[ps.get(q("val"))]
            nid = nid or sn; lvl = sl if lvl is None else lvl
        if lvl is None:
            lvl = 0
        if not nid or nid == "0" or nid not in self.num:
            return ""
        aid, ov = self.num[nid]
        lv = self.abs.get(aid)
        if not lv or lvl not in lv:
            return ""
        cnt = self.counters.setdefault(aid, {})
        start, fmt, text = lv[lvl]
        if fmt == "bullet":
            return ""
        cnt[lvl] = cnt.get(lvl, (ov.get(lvl, start) - 1)) + 1
        for deeper in [k for k in cnt if k > lvl]:
            del cnt[deeper]

        def sub(m):
            k = int(m.group(1)) - 1
            if k not in cnt:
                cnt[k] = lv.get(k, (1,))[0]
            f = lv.get(k, (1, "decimal"))[1]
            return _fmt(cnt[k], f)
        return re.sub(r"%(\d)", sub, text).strip()


def _para_text(p):
    out = []

    def walk(el):
        for ch in el:
            t = ch.tag
            if t == q("t"):
                out.append(ch.text or "")
            elif t == q("tab"):
                out.append(" ")
            elif t in (q("br"), q("cr")):
                out.append(" ")
            elif t == q("noBreakHyphen"):
                out.append("-")
            elif t in (q("del"), q("moveFrom"), q("delText"), q("pPr"), q("rPr")):
                continue
            elif t == q("sym"):
                continue
            else:
                walk(ch)
    walk(p)
    return "".join(out)


def extract_docx(path, options=None, progress=None, cancel=None):
    import docx
    d = docx.Document(path)
    num = Numbering(d)
    blocks = []

    def add(p, kind="para"):
        tx = clean_text(_para_text(p))
        lab = num.label(p)
        if not tx:
            return
        l2, body = split_label(tx)
        if lab and not l2:
            label, body = lab, tx
        else:
            label, body = (l2, body)
            if lab and l2 == "":
                label = lab
        text = (label + " " + body).strip()
        blocks.append(Block(idx=len(blocks), text=text, label=label, body=body, kind=kind, page=1))

    def walk_body(el):
        for ch in el:
            if ch.tag == q("p"):
                add(ch)
            elif ch.tag == q("tbl"):
                for tr in ch.findall("w:tr", NS):
                    for tc in tr.findall("w:tc", NS):
                        for p in tc.iter(q("p")):
                            add(p, "table")
            elif ch.tag in (q("sdt"),):
                c = ch.find("w:sdtContent", NS)
                if c is not None:
                    walk_body(c)
            elif ch.tag in (q("ins"),):
                walk_body(ch)
    walk_body(d.element.body)
    st = os.stat(path)
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    return DocText(path=path, name=os.path.basename(path), kind="docx", blocks=blocks, n_pages=1, pages_used=[1], sha256=h, size=st.st_size,
                   modified=time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime)))
