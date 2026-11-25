"""Create an Excel export, check its formulas in LibreOffice, and release it only when they match.

1. Build a check copy with no stored results (so only a real recalculation can produce figures).
2. Recalculate it in headless LibreOffice and compare every formula cell with the app's figure.
3. Any difference, or no LibreOffice: the export is BLOCKED (logged with the differences).
4. All equal: build the download copy (same formulas, results stored so it opens with figures),
   stamp the check result in it, store its SHA-256 and release it.
"""
from __future__ import annotations

import hashlib
import re
import shutil
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.engine.forecast import Forecast
from app.export.recalc import TOLERANCE, RecalcError, RecalcUnavailable, compare, find_soffice, recalculate
from app.export.workbook import build_workbook
from app.models import ExportCheck, ExportLog, User
from app.models.base import utcnow
from app.services.audit import audit

MAX_STORED_DIFFS = 200


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:30] or "scenario"


def create_export(db: Session, fc: Forecast, user: User | None, *, tamper=None) -> ExportLog:
    """``tamper`` (tests only) may change the expected figures to prove a difference blocks the export."""
    s = get_settings()
    now = utcnow()
    local = datetime.now()
    name = f"cashflow_{fc.as_of:%Y%m%d}_{_slug(fc.scenario)}_{local:%Y%m%d-%H%M%S}.xlsx"
    work = s.exports_dir / "work" / name[:-5]
    work.mkdir(parents=True, exist_ok=True)
    by = (user.full_name or user.username) if user else "console"

    log = ExportLog(created_at=now, created_by_id=user.id if user else None, as_of_date=fc.as_of,
                    scenario_id=fc.scenario_id, filename=name, check_status=ExportCheck.NOT_RUN, released=False)
    check_copy = work / name
    expected = build_workbook(fc, check_copy, cached=False, generated_by=by, generated_at=local)
    if tamper:
        tamper(expected)
    try:
        recalced = recalculate(check_copy, work / "recalculated", soffice=find_soffice(s.soffice_path),
                               profile_dir=s.instance_dir / "lo_profile", timeout=s.recalc_timeout_seconds)
        diffs = compare(recalced, expected)
    except RecalcUnavailable as exc:
        log.note = str(exc)
        diffs = None
    except RecalcError as exc:
        log.check_status, log.note, diffs = ExportCheck.FAILED, f"Formula check could not run: {exc}", None

    if diffs is not None:
        if diffs:
            log.check_status = ExportCheck.FAILED
            log.differences = diffs[:MAX_STORED_DIFFS]
            log.note = (f"BLOCKED: {len(diffs)} cell(s) recalculated by LibreOffice differ from the app. "
                        "The file was not released.")
        else:
            log.check_status = ExportCheck.PASSED
            note = (f"Passed: LibreOffice recalculated all {len(expected)} formula cells on "
                    f"{local:%d-%b-%Y %H:%M} and every one equals the app's figure "
                    f"(tolerance {TOLERANCE}).")
            final = s.exports_dir / name
            build_workbook(fc, final, cached=True, generated_by=by, generated_at=local, check_note=note)
            log.sha256 = hashlib.sha256(final.read_bytes()).hexdigest()
            log.released, log.note = True, note
    db.add(log)
    db.flush()
    if log.released or log.check_status == ExportCheck.NOT_RUN:
        shutil.rmtree(work, ignore_errors=True)            # keep the work files of a failed check only
    audit(db, "export.create", "export_log", name,
          after={"status": log.check_status.value, "released": log.released, "cells": len(expected),
                 "differences": len(log.differences or []), "scenario": fc.scenario,
                 "as_of": fc.as_of.isoformat()},
          user_id=user.id if user else None)
    return log


def export_file(log: ExportLog):
    """Path of a released export, or None."""
    if not log.released:
        return None
    p = get_settings().exports_dir / log.filename
    if not p.exists():
        return None
    if log.sha256 and hashlib.sha256(p.read_bytes()).hexdigest() != log.sha256:
        return None                                         # file changed on disk since the check
    return p
