"""Talks to TallyPrime / Tally.ERP 9 over its XML-over-HTTP interface (port 9000).

Only the standard library is used. Every request and response can be logged
by the caller; this module never changes Tally data by itself – imports are
sent only through import_vouchers(), which the service calls after the user
has confirmed.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

DEFAULT_TIMEOUT = 30


class TallyError(Exception):
    pass


class TallyNotReachable(TallyError):
    pass


def esc(text) -> str:
    return escape("" if text is None else str(text), {'"': "&quot;"})


def _clean_xml(raw: bytes) -> str:
    """Decode Tally's reply (UTF-8 or UTF-16) and remove characters XML parsers reject."""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-16", errors="replace") if b"\x00" in raw[:20] else raw.decode("latin-1")
    text = re.sub(r"&#(?:[0-8]|1[124-9]|2\d|3[01]);", "", text)          # invalid char references like &#4;
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text


def parse(xml_text: str) -> ET.Element:
    try:
        return ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise TallyError(f"Tally sent a reply that could not be read: {e}") from e


@dataclass
class ImportResult:
    created: int = 0
    altered: int = 0
    deleted: int = 0
    errors: int = 0
    exceptions: int = 0
    last_vch_id: str = ""
    line_errors: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def ok(self) -> bool:
        return self.created + self.altered >= 1 and self.errors == 0 and self.exceptions == 0 \
            and not self.line_errors


def parse_import_response(text: str) -> ImportResult:
    root = parse(text)

    def num(tag: str) -> int:
        el = root.find(f".//{tag}")
        try:
            return int((el.text or "0").strip()) if el is not None else 0
        except ValueError:
            return 0
    r = ImportResult(created=num("CREATED"), altered=num("ALTERED"), deleted=num("DELETED"),
                     errors=num("ERRORS"), exceptions=num("EXCEPTIONS"), raw=text)
    vid = root.find(".//LASTVCHID")
    r.last_vch_id = (vid.text or "").strip() if vid is not None else ""
    r.line_errors = [(e.text or "").strip() for e in root.iter("LINEERROR") if (e.text or "").strip()]
    return r


class TallyClient:
    def __init__(self, host: str = "localhost", port: int = 9000, timeout: int = DEFAULT_TIMEOUT):
        # Tally listens on IPv4. On Windows 'localhost' tries IPv6 (::1) first and waits about 2 s for each
        # refused connection - one Day Book request per day of the year made that very slow.
        if (host or "").strip().lower() in ("localhost", ""):
            host = "127.0.0.1"
        self.url = f"http://{host}:{port}"
        self.timeout = timeout
        # never send Tally traffic through a system / office proxy
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    # ------------------------------------------------------------------ transport
    def post(self, xml: str) -> str:
        req = urllib.request.Request(self.url, data=xml.encode("utf-8"), method="POST",
                                     headers={"Content-Type": "text/xml; charset=utf-8"})
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                return _clean_xml(resp.read())
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            raise TallyNotReachable(
                f"Tally is not reachable at {self.url}. Open TallyPrime, open the company and check "
                f"F1 > Settings > Connectivity: 'TallyPrime acts as' = Both, port 9000. ({e})") from e

    def ping(self) -> str:
        """Tally answers a plain GET with e.g. '<RESPONSE>TallyPrime Server is Running</RESPONSE>'."""
        try:
            with self._opener.open(self.url, timeout=min(self.timeout, 8)) as resp:
                text = _clean_xml(resp.read())
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            raise TallyNotReachable(f"Tally is not reachable at {self.url} ({e})") from e
        m = re.search(r"<RESPONSE>(.*?)</RESPONSE>", text, re.S)
        return (m.group(1) if m else text).strip()

    # ------------------------------------------------------------------ export helpers
    def collection(self, name: str, obj_type: str, fetch: str, company: str | None = None,
                   filters: dict[str, str] | None = None, from_date: str | None = None,
                   to_date: str | None = None) -> ET.Element:
        statics = "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"
        if company:
            statics += f"<SVCURRENTCOMPANY>{esc(company)}</SVCURRENTCOMPANY>"
        if from_date:
            statics += f"<SVFROMDATE>{from_date}</SVFROMDATE>"
        if to_date:
            statics += f"<SVTODATE>{to_date}</SVTODATE>"
        filter_tags = "".join(f"<FILTER>{k}</FILTER>" for k in (filters or {}))
        systems = "".join(f'<SYSTEM TYPE="Formulae" NAME="{k}">{esc(v)}</SYSTEM>' for k, v in (filters or {}).items())
        xml = (f"<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE>"
               f"<ID>{name}</ID></HEADER><BODY><DESC><STATICVARIABLES>{statics}</STATICVARIABLES><TDL><TDLMESSAGE>"
               f'<COLLECTION NAME="{name}" ISMODIFY="No"><TYPE>{obj_type}</TYPE><FETCH>{fetch}</FETCH>{filter_tags}'
               f"</COLLECTION>{systems}</TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>")
        return parse(self.post(xml))

    def companies(self) -> list[dict]:
        root = self.collection("IPTCompanies", "Company", "NAME, GUID, STARTINGFROM, BOOKSFROM, STATENAME")
        out = []
        for el in root.iter("COMPANY"):
            name = el.get("NAME") or _child(el, "NAME")
            if name:
                out.append({"name": name, "books_from": _child(el, "BOOKSFROM"),
                            "starting_from": _child(el, "STARTINGFROM"), "state": _child(el, "STATENAME")})
        return out

    def import_xml(self, xml: str) -> ImportResult:
        return parse_import_response(self.post(xml))


def _child(el: ET.Element, tag: str) -> str:
    c = el.find(tag)
    if c is None:
        c = el.find(f"{tag}.LIST/{tag}")
    return (c.text or "").strip() if c is not None and c.text else ""


def first_text(el: ET.Element, *paths: str) -> str:
    for p in paths:
        c = el.find(p)
        if c is not None and c.text and c.text.strip():
            return c.text.strip()
    return ""
