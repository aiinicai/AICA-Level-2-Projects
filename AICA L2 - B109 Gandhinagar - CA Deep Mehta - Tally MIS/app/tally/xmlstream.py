"""Streaming reader for Tally XML (lxml).

Yields one record element (LEDGER, VOUCHER, ...) at a time and frees it afterwards, so memory is bounded by the
size of one record, not the whole response. Like the Node reader it is envelope-agnostic (records are found
wherever they sit), copes with UTF-8 / UTF-16, strips characters that are illegal in XML 1.0 (Tally emits some
in narrations), skips the CMPINFO count block, and turns Tally error replies into TallyResponseError.

IMPORTANT for callers: the yielded element is only valid until the next iteration. Read what you need first.
Tag names are matched in upper case, as Tally writes them.
"""
from __future__ import annotations

import codecs
import re
from collections.abc import Callable, Iterable, Iterator

from lxml import etree

RECORD_TAGS = frozenset({
    "COMPANY", "GROUP", "LEDGER", "VOUCHERTYPE", "VOUCHER", "COSTCENTRE", "COSTCATEGORY",
    "STOCKGROUP", "STOCKCATEGORY", "STOCKITEM", "UNIT", "GODOWN", "CURRENCY",
})
ERROR_TAGS = frozenset({"LINEERROR", "EXCEPTIONS", "RESPONSE", "ERRORS"})
_SKIP_PARENTS = RECORD_TAGS | {"CMPINFO"}


class TallyResponseError(Exception):
    """Tally answered with an error, or sent something that is not valid XML."""


# Character references to illegal XML 1.0 control characters, and the raw characters themselves.
_BAD_REF = re.compile(r"&#(x0*[0-8bcef]|x0*1[0-9a-f]|0*[0-8]|0*1[1-2]|0*1[4-9]|0*2[0-9]|0*3[01]);", re.I)
_XML_DECL = re.compile(r"^\s*<\?xml[^>]*\?>", re.I)


_CTRL = {c: None for c in [*range(0, 9), 11, 12, *range(14, 32), 0xFFFE, 0xFFFF]}


def clean(s: str) -> str:
    """Fast path: most chunks need no cleaning at all."""
    if "&#" in s:
        s = _BAD_REF.sub("", s)
    if "UDF:" in s:
        # Real TallyPrime writes custom-field tags such as <UDF:_UDF_123.LIST> without ever declaring the UDF prefix.
        # A strict XML reader rejects that, so the colon becomes an underscore (the Node reader ignored namespaces).
        s = s.replace("<UDF:", "<UDF_").replace("</UDF:", "</UDF_")
    return s.translate(_CTRL)


class _Sanitizer:
    """Cleans text in chunks, holding back a character reference that may be split across two chunks."""

    def __init__(self) -> None:
        self._carry = ""

    def push(self, chunk: str) -> str:
        s, self._carry = self._carry + chunk, ""
        tag_tail = ""
        lt = s.rfind("<")  # a tag name cut in half at the end of a chunk must be rejoined before it is rewritten
        if lt >= 0 and ">" not in s[lt:] and len(s) - lt < 8:
            s, tag_tail = s[:lt], s[lt:]
        amp = s.rfind("&")
        if amp >= 0 and s.find(";", amp) < 0 and len(s) - amp < 12:
            s, self._carry = s[:amp], s[amp:]
        self._carry += tag_tail
        return clean(s)

    def flush(self) -> str:
        s, self._carry = clean(self._carry), ""
        return s


def _make_decoder(first: bytes):
    if first[:2] == b"\xff\xfe":
        enc = "utf-16-le"
    elif first[:2] == b"\xfe\xff":
        enc = "utf-16-be"
    elif len(first) > 3 and first[1] == 0 and first[3] == 0 and first[0] != 0:
        enc = "utf-16-le"
    else:
        enc = "utf-8"
    return codecs.getincrementaldecoder(enc)(errors="replace")


def _flat_text(el: etree._Element) -> str:
    return " ".join(t.strip() for t in el.itertext() if t and t.strip())


def stream_records(chunks: Iterable[bytes], *, on_prologue: Callable[[str], None] | None = None,
                   should_stop: Callable[[], bool] | None = None) -> Iterator[etree._Element]:
    """Yield record elements from a stream of response bytes."""
    parser = etree.XMLPullParser(events=("end",), tag=sorted(RECORD_TAGS | ERROR_TAGS), huge_tree=True)
    decoder = None
    san = _Sanitizer()
    saw_root = False
    first_text = True
    prologue, prologue_done = "", on_prologue is None

    def feed(text: str):
        nonlocal saw_root, first_text
        if not text:
            return
        if first_text:
            first_text = False
            text = text.lstrip("﻿")
            text = _XML_DECL.sub("", text, count=1)  # we always hand lxml UTF-8 bytes; drop a stale encoding claim
        try:
            parser.feed(text.encode("utf-8"))
        except etree.XMLSyntaxError as e:
            raise TallyResponseError(f"Malformed XML from source: {e}") from None
        saw_root = True

    def drain() -> Iterator[etree._Element]:
        try:
            events = list(parser.read_events())
        except etree.XMLSyntaxError as e:
            raise TallyResponseError(f"Malformed XML from source: {e}") from None
        for _, el in events:
            tag = el.tag.upper() if isinstance(el.tag, str) else ""
            anc = el.getparent()
            inside = False
            while anc is not None:
                if isinstance(anc.tag, str) and anc.tag.upper() in _SKIP_PARENTS:
                    inside = True
                    break
                anc = anc.getparent()
            if inside:
                continue  # nested element or a CMPINFO count, not a top-level record
            if tag in RECORD_TAGS:
                yield el
                _free(el)
            elif tag in ERROR_TAGS:
                msg = _flat_text(el).strip()
                benign = tag == "EXCEPTIONS" and re.fullmatch(r"0?", msg) is not None
                if msg and not benign:
                    raise TallyResponseError(f"Tally returned {tag}: {msg}")
                _free(el)

    for chunk in chunks:
        if should_stop and should_stop():
            raise TallyResponseError("Cancelled")
        if not chunk:
            continue
        if decoder is None:
            decoder = _make_decoder(chunk)
        text = decoder.decode(chunk)
        if not prologue_done:
            prologue += text
            if len(prologue) >= 32768 or re.search(r"<(REQUESTDATA|DATA|COLLECTION|TALLYMESSAGE)\b", prologue, re.I):
                prologue_done = True
                on_prologue(prologue[:32768])
        feed(san.push(text))
        yield from drain()
    if not prologue_done and on_prologue:
        on_prologue(prologue)
    if decoder is not None:
        feed(san.push(decoder.decode(b"", final=True)))
    feed(san.flush())
    if not saw_root:
        raise TallyResponseError("Empty response from source")
    try:
        parser.close()
    except etree.XMLSyntaxError as e:
        raise TallyResponseError(f"Malformed XML from source: {e}") from None
    yield from drain()


def _free(el: etree._Element) -> None:
    """Release a finished element and its earlier siblings so memory stays flat."""
    el.clear()
    parent = el.getparent()
    if parent is not None:
        while el.getprevious() is not None:
            del parent[0]


# ----------------------------------------------------------------- navigation helpers (like txt()/children())

def child(n: etree._Element | None, tag: str) -> etree._Element | None:
    """First direct child with this exact (upper-case) tag."""
    return None if n is None else next(n.iterchildren(tag), None)


def children(n: etree._Element | None, *tags: str) -> list[etree._Element]:
    return [] if n is None else list(n.iterchildren(*tags))


def txt(n: etree._Element | None, *tags: str) -> str | None:
    """Text of the first child with one of the tags (falls back to an attribute of the same name)."""
    if n is None:
        return None
    for t in tags:
        c = next(n.iterchildren(t), None)
        if c is not None:
            text = (c.text or "").strip()
            if text != "" or len(c) == 0:
                return text
        v = n.get(t)
        if v is not None:
            return v
    return None


class View:
    """One pass over an element's children, so many lookups cost one scan (the mappers read ~10 fields per record)."""

    __slots__ = ("el", "d")

    def __init__(self, el: etree._Element) -> None:
        self.el = el
        d: dict[str, list] = {}
        for c in el:
            t = c.tag
            if t.__class__ is str:
                lst = d.get(t)
                if lst is None:
                    d[t] = [c]
                else:
                    lst.append(c)
        self.d = d

    def txt(self, *tags: str) -> str | None:
        d = self.d
        for t in tags:
            lst = d.get(t)
            if lst:
                c = lst[0]
                text = (c.text or "").strip()
                if text != "" or len(c) == 0:
                    return text
            v = self.el.get(t)
            if v is not None:
                return v
        return None

    def kids(self, tag: str) -> list[etree._Element]:
        return self.d.get(tag, [])

    def has(self, tag: str) -> bool:
        return tag in self.d


def stream_file(path: str, chunk_size: int = 1 << 16, **kw) -> Iterator[etree._Element]:
    """Read an exported Tally XML file the same way as a live response."""
    def chunks():
        with open(path, "rb") as f:
            while b := f.read(chunk_size):
                yield b
    return stream_records(chunks(), **kw)
