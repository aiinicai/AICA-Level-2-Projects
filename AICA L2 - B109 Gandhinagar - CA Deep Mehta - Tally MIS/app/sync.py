"""Sync: bring Tally data into the in-memory store, month by month (live) or from exported XML files.

Live sync order (as in the Node app): company list -> masters -> one request per selected month -> Tally's own
stock valuation at each month end. Each step is staged in plain memory and written in one short transaction,
so cancelling or failing never leaves half a month behind.
"""
from __future__ import annotations

import itertools
import re
import threading
import time
from dataclasses import dataclass, field

from .model.importer import Importer
from .model.store import Store, now_iso
from .tally import requests as R
from .tally.client import (Cancelled, Endpoint, TallyConfig, TallyConnectionError, map_company, post_and_stream, probe)
from .tally.values import parse_tally_date
from .tally.xmlstream import TallyResponseError, stream_records


@dataclass
class Batch:
    entity: str
    from_date: str | None = None
    to_date: str | None = None
    status: str = "running"
    records: int = 0
    seconds: float = 0.0
    error: str | None = None


@dataclass
class Run:
    id: int
    company_id: int | None
    mode: str  # 'full' | 'file'
    status: str = "running"  # running | succeeded | failed | cancelled
    started_at: str = field(default_factory=now_iso)
    finished_at: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    months: list[str] = field(default_factory=list)
    label: str | None = None
    counts: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    batches: list[Batch] = field(default_factory=list)
    error: str | None = None
    cancel: threading.Event = field(default_factory=threading.Event, repr=False)

    def public(self, with_batches: bool = False) -> dict:
        d = {"id": self.id, "company_id": self.company_id, "mode": self.mode, "status": self.status,
             "from_date": self.from_date, "to_date": self.to_date, "started_at": self.started_at,
             "finished_at": self.finished_at, "counts": self.counts, "warnings": self.warnings, "error": self.error,
             "source_label": self.label, "months": self.months,
             "progress": {"done": sum(1 for b in self.batches if b.status == "succeeded"), "steps": len(self.batches)}}
        if with_batches:
            d["batches"] = [b.__dict__ for b in self.batches]
        return d


class Runs:
    """Registry of sync runs in this session (memory only)."""

    def __init__(self) -> None:
        self._n = itertools.count(1)
        self.items: dict[int, Run] = {}

    def new(self, **kw) -> Run:
        r = Run(id=next(self._n), **kw)
        self.items[r.id] = r
        return r


def month_range_end(month_start: str) -> str:
    return R.month_end(month_start)


def reject_period_blind_snapshot(store: Store, cid: int, as_of: str, min_agreement: float = 0.8) -> str | None:
    """Discard a Tally stock valuation whose quantities disagree with recorded movements (Tally ignored the period)."""
    r = store.one(
        """SELECT COUNT(*) AS moved, SUM(CASE WHEN s.qty_e4 = i.opening_qty_e4 + m.net THEN 1 ELSE 0 END) AS agree
           FROM stock_items i
           JOIN stock_snapshots s ON s.stock_item_id = i.id AND s.as_of = ? AND s.source = 'tally'
           JOIN (SELECT il.stock_item_id AS id, SUM(CASE WHEN il.direction = 'in' THEN il.qty_e4 ELSE -il.qty_e4 END) AS net
                 FROM inventory_lines il JOIN vouchers v ON v.id = il.voucher_id
                 WHERE v.company_id = ? AND v.is_inventory = 1 AND v.date <= ? GROUP BY il.stock_item_id) m ON m.id = i.id
           WHERE i.company_id = ? AND m.net <> 0""", [as_of, cid, as_of, cid])
    if not r or not r["moved"] or r["agree"] / r["moved"] >= min_agreement:
        return None
    store.execute("DELETE FROM stock_snapshots WHERE company_id = ? AND as_of = ? AND source = 'tally'", [cid, as_of])
    return (f"Tally's stock valuation at {as_of} was discarded: closing quantities agree with recorded movements for only "
            f"{r['agree']} of {r['moved']} items that moved (Tally may not have applied the period). Closing stock for that date is estimated.")


def _finish(run: Run, status: str, imp: Importer | None, error: str | None = None) -> None:
    run.status, run.finished_at, run.error = status, now_iso(), error
    if imp:
        run.counts = dict(imp.counts)
        run.warnings = list(dict.fromkeys(run.warnings + imp.warnings))[:200]


# ---------------------------------------------------------------------------------------------- exported files
def _file_chunks(path: str, size: int = 1 << 16):
    with open(path, "rb") as f:
        while b := f.read(size):
            yield b


def import_files(store: Store, run: Run, company_id: int, paths: list[str], *, as_of: str | None = None,
                 replace_range: bool = False) -> Run:
    """Import Tally XML exports (masters, Day Book, stock valuation) from files."""
    return import_streams(store, run, company_id, [(p.replace("\\", "/").split("/")[-1], (lambda p=p: _file_chunks(p))) for p in paths],
                          as_of=as_of, replace_range=replace_range)


def import_streams(store: Store, run: Run, company_id: int, sources: list, *, as_of: str | None = None,
                   replace_range: bool = False) -> Run:
    """Import Tally XML exports from (name, chunk-producer) pairs. `as_of` for closing balances is read from SVTODATE."""
    imp = Importer(store, company_id, run.id, as_of)
    try:
        for name, producer in sources:
            b = Batch(f"file:{name}")
            run.batches.append(b)
            t0, found = time.perf_counter(), {"as_of": as_of}

            def prologue(text: str, found=found):
                m = re.search(r"<SVTODATE[^>]*>([^<]+)</SVTODATE>", text, re.I)
                if m and not as_of:
                    found["as_of"] = parse_tally_date(m.group(1))

            n = 0
            for rec in stream_records(producer(), on_prologue=prologue, should_stop=lambda: run.cancel.is_set()):
                if n == 0:
                    imp.balances_as_of = found["as_of"]
                if rec.tag.upper() == "COMPANY":
                    bf = parse_tally_date(next((c.text for c in rec if c.tag.upper() == "BOOKSFROM"), None))
                    if bf:
                        store.execute("UPDATE companies SET books_from = COALESCE(books_from, ?) WHERE id = ?", [bf, company_id])
                imp.add(rec)
                n += 1
            if replace_range and imp.voucher_range.get("min"):
                imp.replace_vouchers_in(imp.voucher_range["min"], imp.voucher_range["max"])
            imp.commit()
            b.records, b.status, b.seconds = n, "succeeded", round(time.perf_counter() - t0, 3)
        imp.finalize()
        _finish(run, "succeeded", imp)
    except (TallyResponseError, Cancelled) as e:
        imp.discard()
        if run.batches:
            run.batches[-1].status, run.batches[-1].error = "failed", str(e)
        _finish(run, "cancelled" if run.cancel.is_set() else "failed", imp, str(e))
    return run


# ---------------------------------------------------------------------------------------------- live Tally
def list_months(frm: str, to: str) -> list[str]:
    return R.months_between(frm, to)


def live_sync(store: Store, cfg: TallyConfig, ep: Endpoint, run: Run, company_id: int, tally_company: str,
              months: list[str]) -> Run:
    """Sync the chosen months (each a first-of-month date) for one company open in Tally."""
    months = sorted(set(m[:7] + "-01" for m in months))
    run.months, run.from_date, run.to_date = months, months[0], R.month_end(months[-1])
    to = run.to_date
    imp = Importer(store, company_id, run.id, to)

    def step(entity: str, xml: str, frm: str | None = None, until: str | None = None, replace: tuple[str, str] | None = None) -> None:
        if run.cancel.is_set():
            raise Cancelled()
        b = Batch(entity, frm, until)
        run.batches.append(b)
        t0 = time.perf_counter()
        try:
            for rec in post_and_stream(cfg, ep, xml, cancel=run.cancel):
                imp.add(rec)
                b.records += 1
            if replace:
                imp.replace_vouchers_in(*replace)
            imp.commit()
        except BaseException as e:
            imp.discard()
            b.status = "cancelled" if isinstance(e, Cancelled) else "failed"
            b.error = str(e)
            raise
        finally:
            b.seconds = round(time.perf_counter() - t0, 3)
        b.status = "succeeded"
        run.counts = dict(imp.counts)

    try:
        pr = probe(cfg, ep)
        if pr.kind != "data_server":
            raise TallyConnectionError(pr.error or f"Endpoint is not a Tally data server ({pr.kind})", pr.hint)
        comps = [map_company(r) for r in post_and_stream(cfg, ep, R.company_list_request(), cancel=run.cancel)
                 if r.tag.upper() == "COMPANY"]
        books_from = next((c.books_from for c in comps if c.name == tally_company), None)
        if books_from:
            store.execute("UPDATE companies SET books_from = ? WHERE id = ?", [books_from, company_id])
        else:
            run.warnings.append("Tally did not report when the books begin, so opening balances may follow its current period. "
                                "Compare the figures with Tally.")
        for entity, xml in R.master_requests(tally_company, to, books_from).items():
            step(f"masters:{entity}", xml)
        for m in months:
            end = R.month_end(m)
            step("vouchers", R.voucher_range_request(tally_company, m, end), m, end, replace=(m, end))
        has_items = store.scalar("SELECT COUNT(*) FROM stock_items WHERE company_id = ?", [company_id]) > 0
        if has_items:
            for m in months:
                as_of = R.month_end(m)
                imp.balances_as_of = as_of
                step("stock_valuation", R.stock_valuation_request(tally_company, months[0], as_of), as_of, as_of)
                w = reject_period_blind_snapshot(store, company_id, as_of)
                if w:
                    run.warnings.append(w)
        imp.finalize()
        _finish(run, "succeeded", imp)
    except Cancelled:
        _finish(run, "cancelled", imp, "Cancelled by user")
    except (TallyConnectionError, TallyResponseError) as e:
        hint = getattr(e, "hint", None)
        _finish(run, "failed", imp, f"{e}{' — ' + hint if hint else ''}")
    return run
