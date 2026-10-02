"""Top-level API router: dashboard, settings, batches (preview/XML/post), server link."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import Response
from pydantic import ValidationError

from app.accounting.gst import STATE_NAMES
from app.api import bank, history, journal, purchase, sales, tally
from app.config.settings import APP_NAME, APP_VERSION
from app.container import Container, get_container
from app.services.audit_service import AuditAction
from app.services.errors import UserError

api_router = APIRouter(prefix="/api")
for module in (sales, purchase, journal, bank, tally, history):
    api_router.include_router(module.router)


@api_router.get("/app", tags=["app"])
def app_info(c: Container = Depends(get_container)) -> dict:
    config = c.settings.get()
    return {"name": APP_NAME, "version": APP_VERSION, "demo_mode": config.demo_mode,
            "company_name": config.company_name, "financial_year": config.financial_year}


@api_router.get("/dashboard", tags=["app"])
def dashboard(c: Container = Depends(get_container)) -> dict:
    config = c.settings.get()
    return {
        "company_name": config.company_name, "financial_year": config.financial_year,
        "tally_company_name": config.tally_company_name, "tally_url": config.tally_url,
        "demo_mode": config.demo_mode, "master_counts": c.tally.counts(config),
        "history_stats": c.history.stats(), "recent": c.history.search(limit=8),
    }


# ---------------------------------------------------------------- settings
@api_router.get("/settings", tags=["settings"])
def get_settings(c: Container = Depends(get_container)) -> dict:
    return {"settings": c.settings.get().model_dump(mode="json"), "states": STATE_NAMES}


@api_router.put("/settings", tags=["settings"])
def update_settings(changes: dict[str, Any] = Body(...), c: Container = Depends(get_container)) -> dict:
    try:
        updated = c.settings.update(changes)
    except ValidationError as exc:
        msgs = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg'].removeprefix('Value error, ')}" for e in exc.errors()]
        raise UserError("; ".join(msgs)) from None
    except ValueError as exc:
        raise UserError(str(exc)) from None
    c.audit.record(AuditAction.SETTINGS_UPDATED, company=updated.company_name, details={"fields": sorted(changes)})
    return {"settings": updated.model_dump(mode="json")}


# ---------------------------------------------------------------- batches
@api_router.get("/batches/{batch_id}", tags=["import"])
def batch(batch_id: str, c: Container = Depends(get_container)) -> dict:
    return c.imports.batch_view(batch_id)


@api_router.get("/batches/{batch_id}/xml", tags=["import"], summary="Download Tally XML")
def batch_xml(batch_id: str, c: Container = Depends(get_container)) -> Response:
    name, content = c.imports.xml(batch_id)
    return Response(content, media_type="application/xml",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@api_router.get("/batches/{batch_id}/missing-ledgers", tags=["import"],
                summary="Ledgers used by the file that don't exist in Tally, with suggested groups")
def batch_missing_ledgers(batch_id: str, c: Container = Depends(get_container)) -> dict:
    return c.imports.missing_ledgers(batch_id)


@api_router.post("/batches/{batch_id}/revalidate", tags=["import"], summary="Validate the same file again")
def batch_revalidate(batch_id: str, c: Container = Depends(get_container)) -> dict:
    return c.imports.revalidate(batch_id)


@api_router.post("/batches/{batch_id}/post", tags=["import"], summary="Confirm & post to Tally")
def batch_post(batch_id: str, c: Container = Depends(get_container)) -> dict:
    return c.imports.post(batch_id)


# ---------------------------------------------------------------- server host link
@api_router.get("/server/status", tags=["server"])
def server_status(c: Container = Depends(get_container)) -> dict:
    return c.server_client().status().to_dict()
