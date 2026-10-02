"""/api/tally — connection test and master synchronisation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.container import Container, get_container
from app.tally.master_xml import NewLedger
from app.tally.masters import MASTER_TYPES

router = APIRouter(prefix="/tally", tags=["tally"])


class SyncRequest(BaseModel):
    types: list[str] | None = None


@router.get("/status", summary="Test the Tally connection")
def status(c: Container = Depends(get_container)) -> dict:
    return c.tally.status(c.settings.get())


@router.post("/masters/sync", summary="Fetch masters from Tally into the local cache")
def sync(body: SyncRequest | None = None, c: Container = Depends(get_container)) -> dict:
    return c.tally.sync_masters(c.settings.get(), body.types if body else None)


class CreateLedgersRequest(BaseModel):
    ledgers: list[NewLedger]


@router.get("/ledgers/options", summary="Groups, GST duty heads, registration types and states for the ledger form")
def ledger_options(c: Container = Depends(get_container)) -> dict:
    return c.tally.ledger_options(c.settings.get())


@router.post("/ledgers", summary="Create reviewed ledgers in Tally")
def create_ledgers(body: CreateLedgersRequest, c: Container = Depends(get_container)) -> dict:
    return c.tally.create_ledgers(c.settings.get(), body.ledgers)


@router.get("/masters", summary="Cached master counts")
def counts(c: Container = Depends(get_container)) -> dict:
    config = c.settings.get()
    return {"company_key": config.master_cache_key, "types": list(MASTER_TYPES), "counts": c.tally.counts(config)}


@router.get("/masters/{master_type}", summary="Search cached masters")
def list_masters(master_type: str, q: str = "", c: Container = Depends(get_container)) -> dict:
    return {"items": c.tally.list_masters(c.settings.get(), master_type, q)}
