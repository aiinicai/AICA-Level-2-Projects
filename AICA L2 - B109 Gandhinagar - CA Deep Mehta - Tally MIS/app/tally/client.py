"""HTTP client for Tally's XML server (ported from http-client.ts).

Read-only: the app only ever asks Tally for data. Only loopback / allow-listed hosts and ports are contacted.
"""
from __future__ import annotations

import re
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field

import httpx
from lxml import etree

from . import requests as R
from .values import clean_text, parse_tally_date
from .xmlstream import TallyResponseError, stream_records, txt


class EndpointNotAllowedError(Exception):
    pass


class TallyConnectionError(Exception):
    def __init__(self, message: str, hint: str | None = None):
        super().__init__(message)
        self.hint = hint


class Cancelled(Exception):
    pass


@dataclass
class TallyConfig:
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1")
    allowed_ports: tuple[tuple[int, int], ...] = ((9000, 9010),)
    timeout_s: float = 120.0
    retries: int = 2


@dataclass
class Endpoint:
    host: str = "127.0.0.1"
    port: int = 9000
    request_encoding: str = "utf-8"  # some Tally.ERP 9 releases need 'utf-16'


def assert_allowed(cfg: TallyConfig, host: str, port: int) -> None:
    h = host.strip().lower()
    if not re.fullmatch(r"[a-z0-9.\-:\[\]]+", h):
        raise EndpointNotAllowedError(f'Invalid host "{host}"')
    if h not in cfg.allowed_hosts:
        raise EndpointNotAllowedError(f'Host "{host}" is not allowed. Only this computer can be contacted.')
    if not any(lo <= port <= hi for lo, hi in cfg.allowed_ports):
        raise EndpointNotAllowedError(f"Port {port} is not in the allowed Tally port range.")


def _describe(e: Exception, ep: Endpoint) -> TallyConnectionError:
    if isinstance(e, httpx.TimeoutException):
        return TallyConnectionError(f"Timed out waiting for Tally at {ep.host}:{ep.port}",
                                    "Tally may be busy (a report open, or a large request). Try fewer months at a time.")
    if isinstance(e, httpx.ConnectError):
        return TallyConnectionError(f"Connection refused at {ep.host}:{ep.port}",
                                    'Start TallyPrime and enable "TallyPrime acts as Server" (F1 > Settings > Connectivity).')
    if isinstance(e, (httpx.ReadError, httpx.RemoteProtocolError)):
        return TallyConnectionError("Tally closed the connection", "Retry; if it keeps happening, sync fewer months.")
    return TallyConnectionError(f"Network error contacting Tally: {e}")


def _encode(xml: str, enc: str) -> tuple[bytes, str]:
    if enc == "utf-16":
        return ("﻿" + xml).encode("utf-16-le"), "text/xml; charset=utf-16"
    return xml.encode("utf-8"), "text/xml; charset=utf-8"


_shared: httpx.Client | None = None


def _client() -> httpx.Client:
    """One shared connection pool (creating a client per request costs ~30 ms of TLS set-up we never use)."""
    global _shared
    if _shared is None:
        _shared = httpx.Client(follow_redirects=False, verify=False, trust_env=False)
    return _shared


def post_and_stream(cfg: TallyConfig, ep: Endpoint, xml: str, *, cancel: threading.Event | None = None,
                    ) -> Iterator[etree._Element]:
    """POST an XML request and yield record elements as they arrive.

    Retries only network failures that happen before any record was produced, so a retry can never
    duplicate records. Timeouts are never retried: Tally keeps working on the abandoned request.
    """
    assert_allowed(cfg, ep.host, ep.port)
    url = f"http://{ep.host}:{ep.port}/"
    body, ctype = _encode(xml, ep.request_encoding)
    attempt = 0
    while True:
        emitted = 0
        try:
            deadline = time.monotonic() + cfg.timeout_s
            timeout = httpx.Timeout(cfg.timeout_s, connect=10.0)
            with _client().stream("POST", url, content=body, headers={"Content-Type": ctype}, timeout=timeout) as res:
                if res.status_code != 200:
                    raise TallyConnectionError(f"Tally responded HTTP {res.status_code}")

                def stop() -> bool:
                    if cancel is not None and cancel.is_set():
                        raise Cancelled()
                    if time.monotonic() > deadline:
                        raise httpx.ReadTimeout("overall time limit")
                    return False

                for rec in stream_records(res.iter_bytes(65536), should_stop=stop):
                    emitted += 1
                    yield rec
            return
        except Cancelled:
            raise
        except (TallyConnectionError, TallyResponseError):
            raise
        except httpx.HTTPError as e:
            timed_out = isinstance(e, httpx.TimeoutException)
            if timed_out or emitted > 0 or attempt >= cfg.retries:
                raise _describe(e, ep) from e
            attempt += 1
            if cancel is not None and cancel.wait(0.5 * 2 ** attempt):
                raise Cancelled()
            if cancel is None:
                time.sleep(0.5 * 2 ** attempt)


@dataclass
class ProbeResult:
    kind: str  # data_server | license_server | not_tally | unreachable
    product: str | None = None
    banner: str = ""
    error: str | None = None
    hint: str | None = None


def probe(cfg: TallyConfig, ep: Endpoint, timeout_s: float = 4.0) -> ProbeResult:
    """GET the root URL. A Tally data server answers '<RESPONSE>TallyPrime Server is Running</RESPONSE>'."""
    assert_allowed(cfg, ep.host, ep.port)
    try:
        r = _client().get(f"http://{ep.host}:{ep.port}/", timeout=timeout_s)
    except httpx.HTTPError as e:
        d = _describe(e, ep)
        return ProbeResult("unreachable", error=str(d), hint=d.hint)
    text = r.text[:4000]
    banner = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()[:200]
    if re.search(r"License server is Running", text, re.I):
        return ProbeResult("license_server", banner=banner)
    if re.search(r"TallyPrime Server is Running", text, re.I):
        return ProbeResult("data_server", "TallyPrime", banner)
    if re.search(r"Tally\.?ERP\s*9 Server is Running", text, re.I):
        return ProbeResult("data_server", "Tally.ERP 9", banner)
    if re.search(r"Server is Running", text, re.I):
        return ProbeResult("data_server", "Tally (unknown edition)", banner)
    return ProbeResult("not_tally", banner=banner)


@dataclass
class OpenCompany:
    name: str
    books_from: str | None = None
    last_voucher_date: str | None = None


@dataclass
class OpenCompanies:
    ok: bool
    message: str
    port: int | None = None
    companies: list[OpenCompany] = field(default_factory=list)


def map_company(rec: etree._Element) -> OpenCompany:
    name = clean_text(rec.get("NAME") or txt(rec, "NAME"))
    return OpenCompany(name, parse_tally_date(txt(rec, "BOOKSFROM")), parse_tally_date(txt(rec, "LASTVOUCHERDATE")))


def find_open_companies(cfg: TallyConfig, host: str = "127.0.0.1", ports: Iterator[int] | None = None) -> OpenCompanies:
    """Find the Tally data server on the allowed ports and list the companies open in it."""
    candidates = list(ports) if ports else [p for lo, hi in cfg.allowed_ports for p in range(lo, hi + 1)]
    gateway, empty_server = False, None
    for port in candidates:
        res = probe(cfg, Endpoint(host, port), timeout_s=1.5)
        gateway = gateway or res.kind == "license_server"
        if res.kind != "data_server":
            continue
        ep = Endpoint(host, port)
        saved = cfg.timeout_s, cfg.retries
        cfg.timeout_s, cfg.retries = 15.0, 0
        try:
            comps = [map_company(r) for r in post_and_stream(cfg, ep, R.company_list_request()) if r.tag.upper() == "COMPANY"]
        finally:
            cfg.timeout_s, cfg.retries = saved
        comps = [c for c in comps if c.name]
        if comps:
            return OpenCompanies(True, "Tally found.", port, comps)
        empty_server = port  # a data server with nothing open: keep looking, another port may have a company
    if empty_server is not None:
        return OpenCompanies(False, "Tally is running but no company is open. Open one, then check again.", empty_server, [])
    if gateway:
        return OpenCompanies(False, "Found the Tally Gateway, not the data server. In Tally, set it to act as Server "
                                    "(F1 > Settings > Connectivity), then check again.")
    return OpenCompanies(False, "Tally was not found. Open Tally with a company loaded and its connectivity port on, then check again.")
