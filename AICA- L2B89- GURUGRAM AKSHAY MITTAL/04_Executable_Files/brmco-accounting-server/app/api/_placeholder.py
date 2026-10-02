"""Shared helper for modules reserved for future phases."""
from __future__ import annotations

from fastapi import APIRouter


def placeholder_router(module: str, planned_phase: int, summary: str) -> APIRouter:
    router = APIRouter()

    @router.get("")
    def module_status() -> dict:
        return {
            "module": module,
            "enabled": False,
            "planned_phase": planned_phase,
            "summary": summary,
        }

    return router
