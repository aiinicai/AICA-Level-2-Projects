"""FastAPI demo shell over the existing Phase 1–6 governance services.

The memory table is an operator display that reads SQLite directly. It is not
an assistant retrieval path and cannot be reached through contextual queries;
P0 rule 4 remains enforced by ``contextual_retrieve`` with no size override.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

import amg.config as config_module
from amg import audit
from amg.config import (
    bundled_src_dir,
    get_settings,
    user_data_dir,
)
from amg.db import connect, init_schema, reset_db
from amg.deletion import erase, preview_cascade
from amg.demo.persona import SCENARIOS
from amg.demo.scenarios import SCENARIO_FUNCTIONS, run_all
from amg.memory_service import confirm_inference, ingest_turn, resolve_conflict
from amg.models import SourceType, TrustTier
from amg.providers import (
    last_provider_report,
    reset_provider_state,
    test_provider_connections,
)
from amg.providers.budget import budget_report
from amg.providers.cache import cache_entry_count
from amg.retrieval import contextual_retrieve, full_export
from amg.session import new_session
from amg.settings_store import (
    DEFAULT_GEMINI_MODEL,
    clear_provider_settings,
    save_provider_settings,
)


WEB_ROOT = bundled_src_dir() / "amg" / "web"
templates = Jinja2Templates(directory=str(WEB_ROOT / "templates"))


class TextBody(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class ExportBody(BaseModel):
    passphrase: str = Field(max_length=1_000)


class DeleteBody(BaseModel):
    confirmed: bool = False


class ResolveBody(BaseModel):
    keep_id: int = Field(gt=0)
    supersede_id: int = Field(gt=0)


class ProviderSettingsBody(BaseModel):
    gemini_api_key: str = Field(default="", max_length=2_000)
    voyage_api_key: str = Field(default="", max_length=2_000)
    gemini_model: str = Field(default=DEFAULT_GEMINI_MODEL, max_length=200)


def _configured_db_path() -> Path:
    configured = Path(get_settings().db_path)
    return configured if configured.is_absolute() else user_data_dir() / configured


def _connection(app: FastAPI) -> sqlite3.Connection:
    path = Path(app.state.db_path)
    conn = connect(path)
    init_schema(conn)
    return conn


def _trust_tier(source_type: str, confirmed_at: str | None) -> str:
    if source_type == SourceType.USER_STATED.value:
        return TrustTier.STATED.value
    if confirmed_at:
        return TrustTier.CONFIRMED_INFERENCE.value
    return TrustTier.UNCONFIRMED_INFERENCE.value


def _provider_status(kind: str) -> dict[str, object]:
    settings = get_settings()
    reports = last_provider_report()
    report = reports.get(kind)
    if report is None:
        if kind == "llm":
            if settings.offline or settings.resolved_llm_provider() == "stub":
                return {
                    "label": "Stub (offline)",
                    "state": "offline",
                    "provider": "stub",
                    "model": "stub-rule-v1",
                    "fallback": False,
                    "has_served_call": False,
                }
            return {
                "label": "Gemini (live configured; no call yet)",
                "state": "ready",
                "provider": "gemini",
                "model": settings.gemini_model,
                "fallback": False,
                "has_served_call": False,
            }
        if settings.offline or settings.resolved_embed_provider() == "local":
            return {
                "label": "Local embeddings (offline)",
                "state": "offline",
                "provider": "local",
                "model": "local-hash-v1",
                "fallback": False,
                "has_served_call": False,
            }
        return {
            "label": "Voyage (live configured; no call yet)",
            "state": "ready",
            "provider": "voyage",
            "model": settings.voyage_model,
            "fallback": False,
            "has_served_call": False,
        }

    provider = str(report.get("provider_name", "unknown"))
    served_by = str(report.get("served_by", "unknown"))
    model = str(report.get("model", "unknown"))
    labels = {
        "llm": {
            "live": "Gemini (live API response)",
            "cache": "Gemini (cached real response)",
            "cache_after_error": (
                "Gemini (cached real response after live error)"
            ),
            "stub": "Stub (configured synthetic provider)",
            "fallback_after_error": "Stub (synthetic fallback after live error)",
            "blocked_by_cap": "Stub (synthetic; live call blocked by cap)",
            "blocked_offline": "Stub (synthetic; live call blocked offline)",
        },
        "embedding": {
            "live": "Voyage (live API response)",
            "cache": "Voyage (cached real response)",
            "cache_after_error": "Voyage (cached real response after live error)",
            "stub": "Local embeddings (configured synthetic provider)",
            "fallback_after_error": (
                "Local embeddings (synthetic fallback after live error)"
            ),
            "blocked_by_cap": "Local embeddings (synthetic; live call blocked by cap)",
            "blocked_offline": "Local embeddings (synthetic; live call blocked offline)",
        },
    }
    label = labels[kind].get(served_by, f"Unknown provider state ({served_by})")
    response_kind = (
        "real"
        if served_by in {"live", "cache", "cache_after_error"}
        else "synthetic"
    )
    return {
        "label": label,
        "state": served_by,
        "provider": provider,
        "model": model,
        "fallback": bool(report.get("was_fallback"))
        or served_by == "cache_after_error",
        "response_kind": response_kind,
        "has_served_call": True,
        "served_by": served_by,
    }


def _settings_payload() -> dict[str, object]:
    settings = get_settings()
    gemini_configured = bool(settings.gemini_api_key)
    voyage_configured = bool(settings.voyage_api_key)
    if settings.offline:
        mode = "Offline (deterministic) — no API key configured"
    else:
        live_names = []
        if settings.resolved_llm_provider() == "gemini":
            live_names.append("Gemini")
        if settings.resolved_embed_provider() == "voyage":
            live_names.append("Voyage")
        mode = "Live-enabled: " + ", ".join(live_names)
    return {
        "mode": mode,
        "offline": settings.offline,
        "gemini": {
            "configured": gemini_configured,
            "model": settings.gemini_model,
            "resolved_provider": settings.resolved_llm_provider(),
        },
        "voyage": {
            "configured": voyage_configured,
            "model": settings.voyage_model,
            "resolved_provider": settings.resolved_embed_provider(),
        },
        "storage": str(config_module.settings_file_path()),
        "warning": (
            "Keys are stored in plain text on this computer. This demo is not "
            "a credential manager."
        ),
    }


def _reload_runtime_settings() -> None:
    get_settings.cache_clear()
    reset_provider_state(clear_working_model=True)


def create_app(db_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="AI Memory Governance Demo", version="2.1")
    app.state.db_path = Path(db_path) if db_path is not None else _configured_db_path()
    app.state.session = new_session()
    app.mount("/static", StaticFiles(directory=str(WEB_ROOT / "static")), name="static")

    @app.on_event("startup")
    def initialise() -> None:
        conn = _connection(app)
        conn.close()

    @app.exception_handler(Exception)
    async def readable_error(_: Request, exc: Exception) -> JSONResponse:
        _ = exc
        return JSONResponse(
            status_code=500,
            content={"detail": "The demo could not complete that action safely."},
        )

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Any:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"scenarios": SCENARIOS},
        )

    @app.post("/api/session/new")
    def new_session_endpoint() -> dict[str, object]:
        app.state.session = new_session()
        return {
            "session_id": app.state.session.session_id,
            "started_at": app.state.session.started_at,
            "conversation_history_count": 0,
            "note": "Fresh context: this session carries zero conversation history.",
        }

    @app.get("/api/settings")
    def get_provider_settings() -> dict[str, object]:
        return _settings_payload()

    @app.post("/api/settings")
    def set_provider_settings(body: ProviderSettingsBody) -> dict[str, object]:
        save_provider_settings(
            config_module.settings_file_path(),
            gemini_api_key=body.gemini_api_key,
            voyage_api_key=body.voyage_api_key,
            gemini_model=body.gemini_model,
        )
        _reload_runtime_settings()
        return _settings_payload()

    @app.post("/api/settings/test")
    def test_settings_connections() -> dict[str, object]:
        return {
            "mode": _settings_payload()["mode"],
            "results": test_provider_connections(),
            "budget": budget_report(),
        }

    @app.post("/api/settings/clear")
    def clear_settings() -> dict[str, object]:
        clear_provider_settings(config_module.settings_file_path())
        _reload_runtime_settings()
        return _settings_payload()

    @app.post("/api/turn")
    def turn(body: TextBody) -> dict[str, object]:
        conn = _connection(app)
        try:
            return ingest_turn(conn, app.state.session, body.text).model_dump(mode="json")
        finally:
            conn.close()

    @app.post("/api/query")
    def query(body: TextBody) -> dict[str, object]:
        conn = _connection(app)
        try:
            result = contextual_retrieve(conn, app.state.session, body.text)
            payload = result.model_dump(mode="json")
            payload["top_k_max"] = get_settings().contextual_top_k
            payload["returned_count"] = len(result.hits)
            return payload
        finally:
            conn.close()

    @app.post("/api/export")
    def export(body: ExportBody) -> dict[str, object]:
        conn = _connection(app)
        try:
            return full_export(
                conn, app.state.session, body.passphrase
            ).model_dump(mode="json")
        finally:
            conn.close()

    @app.get("/api/memories")
    def memories() -> dict[str, object]:
        conn = _connection(app)
        try:
            # Operator display only: this direct SQL route is never callable by
            # the assistant's governed contextual-retrieval path.
            rows = conn.execute(
                "SELECT * FROM memories WHERE status != 'deleted' ORDER BY id"
            ).fetchall()
            values = []
            for row in rows:
                item = dict(row)
                item["trust_tier"] = _trust_tier(
                    str(row["source_type"]), row["confirmed_at"]
                )
                values.append(item)
            return {
                "memories": values,
                "count": len(values),
                "display_source": "direct_sql_operator_panel",
            }
        finally:
            conn.close()

    @app.get("/api/audit")
    def audit_rows() -> dict[str, object]:
        conn = _connection(app)
        try:
            rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC").fetchall()
            values = []
            for row in rows:
                item = dict(row)
                item["detail"] = json.loads(str(row["detail"]))
                values.append(item)
            return {
                "rows": values,
                "count": len(values),
                "chain": audit.verify_chain(conn).model_dump(mode="json"),
            }
        finally:
            conn.close()

    @app.post("/api/memory/{memory_id}/confirm")
    def confirm(memory_id: int) -> dict[str, object]:
        conn = _connection(app)
        try:
            try:
                memory = confirm_inference(conn, app.state.session, memory_id)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            return {"memory": memory.model_dump(mode="json")}
        finally:
            conn.close()

    @app.get("/api/memory/{memory_id}/cascade")
    def cascade(memory_id: int) -> dict[str, object]:
        conn = _connection(app)
        try:
            plan = preview_cascade(conn, memory_id)
            if not plan.memory_ids:
                raise HTTPException(status_code=404, detail="Memory not found.")
            return plan.model_dump(mode="json")
        finally:
            conn.close()

    @app.delete("/api/memory/{memory_id}")
    def delete(memory_id: int, body: DeleteBody) -> dict[str, object]:
        conn = _connection(app)
        try:
            report = erase(conn, app.state.session, memory_id, body.confirmed)
            if body.confirmed and not report.plan.memory_ids:
                raise HTTPException(status_code=404, detail="Memory not found.")
            return report.model_dump(mode="json")
        finally:
            conn.close()

    @app.post("/api/conflict/resolve")
    def resolve(body: ResolveBody) -> dict[str, object]:
        conn = _connection(app)
        try:
            try:
                keep, superseded = resolve_conflict(
                    conn, app.state.session, body.keep_id, body.supersede_id
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            return {
                "keep": keep.model_dump(mode="json"),
                "superseded": superseded.model_dump(mode="json"),
            }
        finally:
            conn.close()

    @app.post("/api/scenario/{scenario_id}")
    def scenario(scenario_id: str) -> dict[str, object]:
        conn = _connection(app)
        try:
            if scenario_id == "all":
                results = run_all(conn)
                return {
                    "results": [item.model_dump(mode="json") for item in results],
                    "passed": all(item.passed for item in results),
                }
            function = SCENARIO_FUNCTIONS.get(scenario_id.casefold())
            if function is None:
                raise HTTPException(status_code=404, detail="Unknown scenario id.")
            result = function(conn)
            return result.model_dump(mode="json")
        finally:
            conn.close()

    @app.post("/api/reset")
    def reset() -> dict[str, object]:
        conn = reset_db(app.state.db_path)
        conn.close()
        app.state.session = new_session()
        return {"reset": True, "session_id": app.state.session.session_id}

    @app.get("/api/status")
    def status() -> dict[str, object]:
        reports = last_provider_report()
        served_states = {
            str(report.get("served_by")) for report in reports.values()
        }
        notices: list[str] = []
        if "cache_after_error" in served_states:
            notices.append(
                "A live provider attempt failed; a pre-warmed real cached "
                "response served the request."
            )
        if "fallback_after_error" in served_states:
            notices.append(
                "A live provider attempt failed; a deterministic synthetic "
                "fallback served the request."
            )
        if "blocked_by_cap" in served_states:
            notices.append(
                "The daily cap deliberately blocked a live call; a deterministic "
                "synthetic fallback served the request."
            )
        return {
            "offline": get_settings().offline,
            "llm": _provider_status("llm"),
            "embeddings": _provider_status("embedding"),
            "budget": budget_report(),
            "cache_entries": cache_entry_count(),
            "fallback_notice": " ".join(notices) or None,
        }

    @app.post("/api/audit/tamper")
    def tamper() -> dict[str, object]:
        """Deliberately break one local demo row so tamper evidence is observable."""

        conn = _connection(app)
        try:
            row = conn.execute("SELECT id FROM audit_log ORDER BY id LIMIT 1").fetchone()
            if row is None:
                raise HTTPException(status_code=409, detail="Create an audit row before the tamper test.")
            row_id = int(row["id"])
            conn.execute(
                "UPDATE audit_log SET actor = actor || '-tampered' WHERE id = ?",
                (row_id,),
            )
            conn.commit()
            chain = audit.verify_chain(conn)
            return {
                "tampered_row_id": row_id,
                "chain": chain.model_dump(mode="json"),
                "note": "Raw SQL changed an audited field without recomputing the hash.",
            }
        finally:
            conn.close()

    return app


app = create_app()
