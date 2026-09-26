"""
review_store.py
-----------------
Holds the controller review/sign-off workflow state — in-memory, keyed by
a per-run session id (a random token issued to the browser tab when a
flux run is created). This is deliberately NOT the AI: it is the record
of what a human controller decided about each flagged line.

This is intentionally simple (an in-memory dict, not a database) because
this is a capstone demo tool run by one person at a time. A real
deployment would persist this in a proper database with user auth — see
README §"Where this goes next" for that extension.

Statuses:
    pending    — default; the system draft has not yet been reviewed
    explained  — preparer has attached an explanation / edited the note
    approved   — CONTROLLER has approved this line; considered resolved
    rejected   — CONTROLLER has rejected the note; needs rework

Only "approved" (by a named controller) counts as resolved. A "final"
(non-draft) export is only produced once every material line for that
run is "approved" — see routes.py `/api/export/*`.

Two separate commentary fields are tracked per row, deliberately kept
apart end-to-end (store, API, UI, every export):

    ai_commentary          — the system/AI-drafted note. Set once when the
                              run is created and never changed afterwards.
                              Reference only — it is what the model
                              produced, for the controller to read against.
    controller_commentary  — starts as a copy of ai_commentary, but is the
                              ONE field a controller can edit. This is the
                              text that ships in a FINAL export; ai_commentary
                              ships alongside it, clearly labelled, so a
                              reviewer can always see what the AI said
                              versus what the controller decided.
"""

from __future__ import annotations

import secrets
import time
from threading import Lock

_lock = Lock()
_RUNS: dict[str, dict] = {}


def new_run(flux_records: list[dict], meta: dict) -> str:
    """Register a new flux run and return its run_id."""
    run_id = secrets.token_urlsafe(12)
    with _lock:
        _RUNS[run_id] = {
            "meta": meta,
            "created_at": time.time(),
            "rows": {
                r["row_id"]: {
                    "data": r,
                    "status": "pending",
                    "ai_commentary": r.get("ai_commentary", ""),
                    "controller_commentary": r.get("ai_commentary", ""),
                    "reviewer": None,
                    "reviewed_at": None,
                }
                for r in flux_records
            },
            "signoff": {
                "controller_name": None,
                "controller_title": None,
                "signed_off_at": None,
            },
        }
    return run_id


def get_run(run_id: str) -> dict | None:
    return _RUNS.get(run_id)


def update_row(run_id: str, row_id: str, status: str | None = None,
               controller_commentary: str | None = None, reviewer: str | None = None) -> dict | None:
    run = _RUNS.get(run_id)
    if not run or row_id not in run["rows"]:
        return None
    with _lock:
        entry = run["rows"][row_id]
        if status is not None:
            entry["status"] = status
        if controller_commentary is not None:
            entry["controller_commentary"] = controller_commentary
        if reviewer is not None:
            entry["reviewer"] = reviewer
            entry["reviewed_at"] = time.time()
    return entry


def sign_off(run_id: str, controller_name: str, controller_title: str) -> dict | None:
    run = _RUNS.get(run_id)
    if not run:
        return None
    with _lock:
        run["signoff"] = {
            "controller_name": controller_name,
            "controller_title": controller_title,
            "signed_off_at": time.time(),
        }
    return run["signoff"]


def is_ready_for_final_export(run_id: str) -> tuple[bool, int, int]:
    """Returns (ready, n_material, n_approved)."""
    run = _RUNS.get(run_id)
    if not run:
        return False, 0, 0
    material_rows = [r for r in run["rows"].values() if r["data"].get("is_material")]
    approved = [r for r in material_rows if r["status"] == "approved"]
    signed = run["signoff"]["controller_name"] is not None
    ready = signed and len(material_rows) > 0 and len(approved) == len(material_rows)
    return ready, len(material_rows), len(approved)
