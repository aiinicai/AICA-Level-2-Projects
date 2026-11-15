"""The local web server: the same URLs and JSON the screens already use, served on this PC only (127.0.0.1)."""
from __future__ import annotations

import io
import json
import os
import sys
import threading
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..assistant.lmstudio import AssistantError
from ..assistant.service import Assistant
from ..engine import dispatch, reports as R
from ..licensing import LicenceManager
from ..engine.context import detect_inventory_mode, make_ctx
from ..engine.periods import fy_of
from ..model.store import Store, now_iso
from ..sync import Runs, import_streams, live_sync
from ..tally.client import Endpoint, EndpointNotAllowedError, TallyConfig, assert_allowed, find_open_companies

DEMO_COMPANY = "Demo Trading Co (Sample Data)"
MAX_UPLOAD = 600 * 1024 * 1024


def resource_path(rel: str) -> Path:
    """Files shipped with the app: next to the source, or inside the PyInstaller bundle."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))
    return base / rel


@dataclass
class AppState:
    store: Store = field(default_factory=Store)
    runs: Runs = field(default_factory=Runs)
    assistant: Assistant = field(default_factory=Assistant)
    tally: TallyConfig = field(default_factory=TallyConfig)
    on_close: Callable[[], None] | None = None
    engine_lock: threading.RLock = field(default_factory=threading.RLock)
    allowed_hosts: set[str] = field(default_factory=set)
    licence: LicenceManager = field(default_factory=LicenceManager)


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def create_app(state: AppState, static_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Tally MIS", docs_url=None, redoc_url=None, openapi_url=None)
    store = state.store

    # ---------------------------------------------------------------- safety: this PC only
    @app.middleware("http")
    async def guard(request: Request, call_next):
        host = (request.headers.get("host") or "").lower()
        if state.allowed_hosts and host not in state.allowed_hosts:  # blocks DNS-rebinding from web pages
            return JSONResponse({"error": "Not allowed"}, status_code=403)
        if request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD") and request.headers.get("x-requested-with") != "mis":
            return JSONResponse({"error": "Missing request header"}, status_code=403)
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.exception_handler(HttpError)
    async def _http_error(_: Request, e: HttpError):
        return JSONResponse({"error": e.message}, status_code=e.status)

    @app.exception_handler(Exception)
    async def _any_error(_: Request, e: Exception):
        return JSONResponse({"error": f"Something went wrong: {type(e).__name__}. Details were not saved."}, status_code=500)

    # ---------------------------------------------------------------- shell
    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/auth/state")
    def auth_state():
        return {"needsSetup": False, "user": {"id": 1, "email": "local", "name": "You", "role": "admin"}, "demoMode": False}

    # ---------------------------------------------------------------- licence
    def real_companies_after(adding: str | None = None) -> int:
        names = {r["name"] for r in store.rows("SELECT name FROM companies WHERE is_demo = 0")}
        if adding:
            names.add(adding)
        return len(names)

    @app.get("/api/licence")
    def licence_status():
        return state.licence.current.public()

    @app.post("/api/licence")
    async def licence_activate(request: Request):
        key = str((await request.json()).get("key", "")).strip()
        if not key:
            raise HttpError(400, "Paste your licence key first")
        lic = state.licence.activate(key)
        if not lic.licensed:
            raise HttpError(400, lic.message)
        return state.licence.current.public()

    @app.delete("/api/licence")
    def licence_remove():
        return state.licence.remove().public()

    @app.post("/api/close")
    def close(bg: BackgroundTasks):
        if state.on_close:
            bg.add_task(state.on_close)
        return {"ok": True}

    @app.get("/api/industry-profiles")
    def profiles():
        from ..shared_industry import PROFILES
        return PROFILES

    # ---------------------------------------------------------------- companies
    def company_rows() -> list[dict]:
        rows = store.rows("SELECT * FROM companies ORDER BY is_demo, name")
        out = []
        for c in rows:
            span = store.one("SELECT MIN(date) AS a, MAX(date) AS b, COUNT(*) AS n FROM vouchers WHERE company_id = ?", [c["id"]])
            last = max((r.finished_at for r in state.runs.items.values() if r.company_id == c["id"] and r.status == "succeeded" and r.finished_at), default=None)
            c = {**c, "settings": json.loads(c["settings_json"] or "{}"), "is_demo": bool(c["is_demo"]), "data_from": span["a"], "data_to": span["b"],
                 "last_sync": last, "voucher_count": span["n"]}
            c.pop("settings_json", None)
            out.append(c)
        return out

    @app.get("/api/companies")
    def companies():
        return company_rows()

    @app.get("/api/companies/{cid}/meta")
    def company_meta(cid: int):
        c = store.one("SELECT * FROM companies WHERE id = ?", [cid])
        if not c:
            raise HttpError(404, "Company not found")
        span = store.one("SELECT MIN(date) AS a, MAX(date) AS b FROM vouchers WHERE company_id = ? AND is_accounting = 1", [cid])
        runs = sorted((r for r in state.runs.items.values() if r.company_id == cid), key=lambda r: r.id)
        last = runs[-1] if runs else None
        first = min([x for x in (span["a"], c["books_from"], None if span["a"] else (last.from_date if last else None)) if x], default=None)
        end = span["b"] or (last.to_date if last else None)
        fys = []
        if first and end:
            f = fy_of(first, c["fy_start_month"])
            while f.from_ <= end:
                fys.append({"label": f.label, "from": f.from_, "to": f.to})
                f = fy_of(f"{f.start_year + 1}-{c['fy_start_month']:02d}-15", c["fy_start_month"])
        ok = [r for r in runs if r.status == "succeeded"]
        cc = [r["name"] for r in store.rows("SELECT name FROM cost_centres WHERE company_id = ? ORDER BY name", [cid])]
        try:
            ctx = make_ctx(store, cid)
            mode = detect_inventory_mode(store, cid, ctx.chart)
        except Exception:
            mode = "none"
        company = {**c, "is_demo": bool(c["is_demo"]), "settings": json.loads(c["settings_json"] or "{}")}
        company.pop("settings_json", None)
        return {"company": company, "dataFrom": span["a"], "dataTo": span["b"], "financialYears": list(reversed(fys)), "costCentres": cc,
                "lastRun": ({"id": last.id, "status": last.status, "mode": last.mode, "finished_at": last.finished_at, "started_at": last.started_at,
                             "error": last.error, "from_date": last.from_date, "to_date": last.to_date} if last else None),
                "lastSuccessfulSync": ok[-1].finished_at if ok else None, "detectedInventoryMode": mode, "verifiedMappings": 0}

    # ---------------------------------------------------------------- reports (same URLs as the Node app)
    @app.get("/api/c/{cid}/{rest:path}")
    def reports(cid: int, rest: str, request: Request):
        with state.engine_lock:
            status, body = dispatch.handle(store, f"/api/c/{cid}/{rest}" + (f"?{request.url.query}" if request.url.query else ""))
        return JSONResponse(body, status_code=status)

    @app.post("/api/c/{cid}/collection-notes")
    async def collection_note(cid: int, request: Request):
        b = await request.json()
        if not store.one("SELECT id FROM ledgers WHERE id = ? AND company_id = ?", [b.get("ledgerId"), cid]):
            raise HttpError(404, "Ledger not found")
        if b.get("status") not in ("note", "disputed", "promised", "escalated", "resolved") or not str(b.get("note", "")).strip():
            raise HttpError(400, "A status and a note are required")
        nid = store.next_id("collection_notes")
        store.insert("collection_notes", [(nid, cid, b["ledgerId"], b.get("billName"), b["status"], str(b["note"])[:2000], now_iso())])
        return {"id": nid}

    # ---------------------------------------------------------------- Tally sync
    @app.get("/api/tally/companies")
    def tally_companies():
        r = find_open_companies(state.tally)
        return {"ok": r.ok, "message": r.message, "port": r.port,
                "companies": [{"name": c.name, "booksFrom": c.books_from, "lastVoucherDate": c.last_voucher_date} for c in r.companies]}

    @app.post("/api/tally/sync")
    async def tally_sync(request: Request):
        b = await request.json()
        name, port = str(b.get("company", "")).strip(), b.get("port")
        months = [str(m) for m in b.get("months", [])]
        if not name or not isinstance(port, int):
            raise HttpError(400, "company and port are required")
        if not months:
            raise HttpError(400, "Choose at least one month")
        if any(len(m) < 7 or not m[:4].isdigit() or m[4] != "-" or not m[5:7].isdigit() or not 1 <= int(m[5:7]) <= 12 for m in months):
            raise HttpError(400, "Months must look like 2025-04-01")
        try:
            assert_allowed(state.tally, "127.0.0.1", port)
        except EndpointNotAllowedError as e:
            raise HttpError(400, str(e))
        denied = state.licence.check_sync(len(months), real_companies_after(name))
        if denied:
            raise HttpError(402, denied)
        cid = store.ensure_company(name)
        if any(r.company_id == cid and r.status == "running" for r in state.runs.items.values()):
            raise HttpError(409, "A sync is already running for this company")
        run = state.runs.new(company_id=cid, mode="full", label=f"Tally on port {port}")
        threading.Thread(target=live_sync, args=(store, state.tally, Endpoint("127.0.0.1", port), run, cid, name, months), daemon=True).start()
        return {"runId": run.id, "companyId": cid}

    @app.get("/api/sync/runs")
    def sync_runs():
        return [r.public() for r in sorted(state.runs.items.values(), key=lambda r: -r.id)][:100]

    @app.get("/api/sync/runs/{rid}")
    def sync_run(rid: int):
        r = state.runs.items.get(rid)
        if not r:
            raise HttpError(404, "Run not found")
        return r.public(with_batches=True)

    @app.post("/api/sync/runs/{rid}/cancel")
    def cancel(rid: int):
        r = state.runs.items.get(rid)
        if not r or r.status != "running":
            return {"cancelled": False}
        r.cancel.set()
        return {"cancelled": True}

    # ---------------------------------------------------------------- files and demo
    @app.post("/api/import/xml")
    async def import_xml(request: Request, companyId: int | None = None, newCompany: str | None = None, asOf: str | None = None,
                         replaceRange: str | None = None, filename: str = "upload.xml"):
        if not companyId and not newCompany:
            raise HttpError(400, "Choose an existing company or name a new one")
        chunks: list[bytes] = []
        size = 0
        async for part in request.stream():
            size += len(part)
            if size > MAX_UPLOAD:
                raise HttpError(413, "That file is too large (limit 600 MB)")
            chunks.append(part)
        target = None
        if companyId:
            row = store.one("SELECT name, is_demo FROM companies WHERE id = ?", [companyId])
            target = row["name"] if row and not row["is_demo"] else None
        else:
            target = newCompany.strip()
        denied = state.licence.check_import(size, real_companies_after(target))
        if denied:
            raise HttpError(402, denied)
        cid = companyId or store.ensure_company(newCompany.strip())
        company = store.one("SELECT is_demo FROM companies WHERE id = ?", [cid])
        if not company:
            raise HttpError(404, "Company not found")
        if company["is_demo"]:
            raise HttpError(400, "Real data cannot be imported into the demo company")
        run = state.runs.new(company_id=cid, mode="file", label=filename[:200])
        await run_in_threadpool(import_streams, store, run, cid, [(filename, lambda: iter(chunks))], as_of=asOf, replace_range=replaceRange == "true")
        return {**run.public(), "runId": run.id, "companyId": cid, "voucherRange": None}

    @app.post("/api/demo/load")
    def load_demo():
        zpath = resource_path("app/demo_data/demo_company.zip")
        if not zpath.exists():
            raise HttpError(404, "The demo data file is missing from this install")
        cid = store.ensure_company(DEMO_COMPANY, is_demo=True)
        run = state.runs.new(company_id=cid, mode="demo", label="Fictional demo company")
        with zipfile.ZipFile(zpath) as z:
            names = sorted(n for n in z.namelist() if n.endswith(".xml"))
            blobs = [(n, z.read(n)) for n in names]
        sources = [(n, (lambda d=d: iter([d[i:i + 65536] for i in range(0, len(d), 65536)]))) for n, d in blobs]
        import_streams(store, run, cid, sources)
        return {"runId": run.id, "companyId": cid, "status": run.status}

    # ---------------------------------------------------------------- assistant
    @app.get("/api/settings/assistant")
    def get_assistant():
        return state.assistant.settings()

    @app.put("/api/settings/assistant")
    async def put_assistant(request: Request):
        try:
            state.assistant.update(await request.json())
        except AssistantError as e:
            raise HttpError(400, str(e))
        return state.assistant.settings()

    @app.post("/api/assistant/chat")
    async def assistant_chat(request: Request):
        b = await request.json()
        question = str(b.get("question", "")).strip()
        if not question:
            raise HttpError(400, "Type a question first")

        def run():
            f = None
            cid = b.get("companyId")
            if isinstance(cid, int):
                try:
                    f = R.make_filters(store, cid, b.get("from"), b.get("to"), b.get("compare"), b.get("costCentre"))
                except R.ApiError as e:
                    raise HttpError(e.status, e.message)
            if f is None:
                return {"kind": "refused", "label": None, "facts": None, "unmatched": [],
                        "answer": "Open a company first (Data sources → sync from Tally or load the demo company), then ask about its figures."}
            with state.engine_lock:
                return state.assistant.chat(question, f)
        return await run_in_threadpool(run)

    # ---------------------------------------------------------------- the screens
    if static_dir and (static_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="ui")
    return app
