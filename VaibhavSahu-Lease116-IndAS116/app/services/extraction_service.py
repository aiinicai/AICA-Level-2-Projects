"""Documents and the AI agreement reader: storage, background extraction, review and lease creation."""
from __future__ import annotations

import hashlib
import mimetypes
import shutil
import threading
import traceback
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config
from ..db.base import session_scope
from ..db.models import (AssetClass, Company, Counterparty, Deposit, Document, Entity, ExtractionRun, Lease, LeaseAssessment,
                         LeaseCost, LeaseOptionRow, RestorationObligation)
from ..engine.calendar_utils import add_months, next_day, parse_date, prev_day
from . import audit
from .lease_service import ServiceError, next_lease_code, regenerate_payments
from .settings_service import build_llm, get_settings

_jobs_lock = threading.Lock()


def save_document(db: Session, company: Company, data: bytes, filename: str, user, lease_id: int | None = None,
                  event_id: int | None = None, doc_type: str = "Lease agreement", notes: str | None = None) -> Document:
    config.ensure_dirs()
    sha = hashlib.sha256(data).hexdigest()
    safe = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in Path(filename).name)[:120]
    folder = config.DOCS_DIR / sha[:2]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sha[:16]}_{safe}"
    if not path.exists():
        path.write_bytes(data)
    doc = Document(company_id=company.id, lease_id=lease_id, event_id=event_id, doc_type=doc_type, filename=Path(filename).name,
                   stored_path=str(path), sha256=sha, size=len(data), mime=mimetypes.guess_type(filename)[0], uploaded_by=user.id,
                   notes=notes)
    db.add(doc)
    db.flush()
    audit.log(db, user, "UPLOAD", "Document", doc.id, doc.filename, "document", None, f"{doc_type}: {doc.filename} ({len(data):,} bytes)",
              document_id=doc.id)
    return doc


def preview_dir(doc_id: int) -> Path:
    d = config.DOCS_DIR / "previews" / str(doc_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def delete_extraction(db: Session, run: ExtractionRun, user) -> list[Path]:
    """Delete an agreement read that was not used to create a lease, with its uploaded copy and page previews.

    A read that created a lease is kept: it is that lease's source evidence (reviewed fields, quotes, page highlights).
    The audit trail keeps a record of the deletion. Returns the files to remove once the transaction has been committed
    (the stored file is shared by identical uploads, so it is removed only when no other document uses it)."""
    if run.lease_id:
        raise ServiceError(f"This read created lease #{run.lease_id} and is kept as that lease's source evidence "
                           f"(reviewed fields, quotes and page highlights).", status=409)
    if run.status == "Running":
        raise ServiceError("This agreement is still being read. Delete it once the read has finished.", status=409)
    doc = db.get(Document, run.document_id)
    label = doc.filename if doc else f"document #{run.document_id}"
    audit.log(db, user, "DELETE", "ExtractionRun", run.id, label, reason="Agreement read deleted (not used for a lease)",
              document_id=run.document_id)
    db.delete(run)
    db.flush()
    files: list[Path] = []
    if doc is not None and doc.lease_id is None and doc.event_id is None:
        still_read = db.scalar(select(func.count()).select_from(ExtractionRun).where(ExtractionRun.document_id == doc.id))
        if not still_read:
            shared = db.scalar(select(func.count()).select_from(Document)
                               .where(Document.stored_path == doc.stored_path, Document.id != doc.id))
            audit.log(db, user, "DELETE", "Document", doc.id, doc.filename, reason="Uploaded copy deleted with its agreement read",
                      document_id=doc.id)
            if not shared:
                files.append(Path(doc.stored_path))
            files.append(config.DOCS_DIR / "previews" / str(doc.id))
            db.delete(doc)
            db.flush()
    return files


def delete_unused_extractions(db: Session, user) -> tuple[int, list[Path]]:
    """Delete every finished read that was not used to create a lease."""
    runs = db.scalars(select(ExtractionRun).where(ExtractionRun.lease_id.is_(None), ExtractionRun.status != "Running")).all()
    files: list[Path] = []
    for r in runs:
        files += delete_extraction(db, r, user)
    return len(runs), files


def remove_files(paths: list[Path]) -> None:
    """Remove files / preview folders after the database change has been committed (only inside the documents folder)."""
    root = config.DOCS_DIR.resolve()
    for p in paths:
        try:
            rp = Path(p).resolve()
            if root not in rp.parents:
                continue
            if rp.is_dir():
                shutil.rmtree(rp, ignore_errors=True)
            elif rp.exists():
                rp.unlink()
        except OSError:
            pass


def start_extraction(db: Session, company: Company, doc: Document, user, mode: str | None = None, allow_cloud: bool = False,
                     force_ocr: bool = False) -> ExtractionRun:
    llm, name = build_llm(company, allow_cloud_for_doc=allow_cloud, mode_override=mode)
    engine = "rules" + (f" + {name}" if name else "")
    run = ExtractionRun(document_id=doc.id, created_by=user.id, engine=engine, model=getattr(llm, "model", None), status="Running",
                        result={"progress": "Queued"})
    db.add(run)
    db.flush()
    if name == "claude":
        audit.log(db, user, "CLOUD_AI_CONSENT", "Document", doc.id, doc.filename, "ai", None,
                  f"Agreement text sent to Claude API ({getattr(llm, 'model', '') or 'auto model'}) with user confirmation",
                  document_id=doc.id)
    ai = get_settings(company)["ai"]
    ocr_llm = None
    if ai.get("local", {}).get("vision_model"):
        from ..docintel.llm import LocalLLM
        loc = ai["local"]
        ocr_llm = LocalLLM(base_url=loc.get("base_url"), kind=loc.get("kind"), model=loc.get("model") or "",
                           vision_model=loc.get("vision_model"))
    t = threading.Thread(target=_worker, args=(run.id, doc.stored_path, doc.filename, doc.id, llm, name, ai.get("ocr_engine", "auto"),
                                               force_ocr, ocr_llm), daemon=True)
    db.commit()
    t.start()
    return run


def run_extraction_sync(db: Session, company: Company, doc: Document, user, mode: str | None = "rules") -> ExtractionRun:
    llm, name = build_llm(company, mode_override=mode)
    run = ExtractionRun(document_id=doc.id, created_by=user.id, engine="rules" + (f" + {name}" if name else ""),
                        model=getattr(llm, "model", None), status="Running", result={})
    db.add(run)
    db.flush()
    _execute(run, Path(doc.stored_path).read_bytes(), doc.filename, doc.id, llm, name, "auto", False, None)
    return run


def _execute(run: ExtractionRun, data: bytes, filename: str, doc_id: int, llm, name: str, ocr_pref: str, force_ocr: bool, ocr_llm):
    from ..docintel.pipeline import run_pipeline
    res, loaded = run_pipeline(data, filename, llm=llm, provider_name=name, ocr_pref=ocr_pref, force_ocr=force_ocr, ocr_llm=ocr_llm)
    pdir = preview_dir(doc_id)
    for p in loaded.pages:
        if p.preview_png:
            (pdir / f"page_{p.number}.png").write_bytes(p.preview_png)
        (pdir / f"page_{p.number}.txt").write_text(p.text or "", encoding="utf-8")
    run.result = res.to_dict()
    run.status = "Completed"


def _worker(run_id: int, path: str, filename: str, doc_id: int, llm, name: str, ocr_pref: str, force_ocr: bool, ocr_llm):
    try:
        data = Path(path).read_bytes()
        with session_scope() as db:
            run = db.get(ExtractionRun, run_id)
            run.result = {"progress": "Reading document (OCR / computer vision where needed)…"}
        with session_scope() as db:
            run = db.get(ExtractionRun, run_id)
            _execute(run, data, filename, doc_id, llm, name, ocr_pref, force_ocr, ocr_llm)
            d = db.get(Document, doc_id)
            if d:
                d.pages = run.result.get("document", {}).get("pages")
    except Exception as exc:  # pragma: no cover - surfaced to the UI
        with session_scope() as db:
            run = db.get(ExtractionRun, run_id)
            run.status = "Failed"
            run.result = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-2000:]}


def _val(fields: dict, key: str):
    f = fields.get(key) or {}
    v = f.get("value")
    return None if v in ("", None) else v


def confirm_extraction(db: Session, company: Company, run: ExtractionRun, user, payload: dict) -> Lease:
    """Create a draft lease from reviewed fields. payload = {fields: {key: value}, answers: {...}, entity_id, ...}"""
    if run.lease_id:
        raise ServiceError(f"This extraction has already created lease #{run.lease_id}.")
    fields = {k: {"value": v} for k, v in (payload.get("fields") or {}).items()}
    base = (run.result or {}).get("fields", {})
    for k, v in base.items():
        fields.setdefault(k, {"value": v.get("value")})
    ans = payload.get("answers") or {}
    comm = parse_date(_val(fields, "commencement_date"))
    tenure = _val(fields, "tenure_months")
    end = parse_date(_val(fields, "expiry_date"))
    if comm is None:
        raise ServiceError("Commencement date is required to create the lease.")
    if end is None and tenure:
        end = prev_day(add_months(comm, int(tenure)))
    if end is None:
        raise ServiceError("Expiry date or contractual term is required.")
    if _val(fields, "rent_amount") is None:
        raise ServiceError("Rent amount is required.")
    ent_id = payload.get("entity_id") or db.scalar(select(Entity.id).order_by(Entity.id))
    ac_name = _val(fields, "asset_category") or "Buildings"
    ac = db.scalar(select(AssetClass).where(AssetClass.name == ac_name))
    if ac is None:
        ac = AssetClass(company_id=company.id, code=ac_name[:20].upper().replace(" ", "_"), name=ac_name)
        db.add(ac)
        db.flush()
    role = (payload.get("role") or "LESSEE").upper()
    if role not in ("LESSEE", "LESSOR"):
        raise ServiceError("Role must be LESSEE or LESSOR.")
    # the counterparty is the other party to the agreement: the lessor when we are the lessee, the lessee (tenant) when we let out
    cp_name = _val(fields, "lessee_name" if role == "LESSOR" else "lessor_name")
    cp = None
    if cp_name:
        cp = db.scalar(select(Counterparty).where(Counterparty.name == cp_name))
        if cp is None:
            cp = Counterparty(company_id=company.id, name=cp_name, related_party=bool(ans.get("related_party")))
            db.add(cp)
            db.flush()
    freq_code = _val(fields, "rent_frequency") or "MONTHLY"
    freq = {"MONTHLY": 1, "QUARTERLY": 3, "HALF_YEARLY": 6, "ANNUAL": 12}.get(freq_code, 1)
    due = _val(fields, "payment_due_day")
    cfg = {"amount": str(_val(fields, "rent_amount")), "start_date": comm.isoformat(), "end_date": end.isoformat(),
           "frequency_months": freq, "timing": _val(fields, "payment_timing") or "ADVANCE",
           "alignment": "CALENDAR" if (due and freq == 1) else "ANNIVERSARY", "due_day": due, "escalations": [], "rent_free": [],
           "non_lease_amount": str(_val(fields, "cam_amount") or "0")}
    if _val(fields, "escalation_pct"):
        cfg["escalations"].append({"value": str(_val(fields, "escalation_pct")), "every_months": int(_val(fields, "escalation_every_months") or 12),
                                   "compounding": (_val(fields, "escalation_basis") or "COMPOUND") == "COMPOUND"})
    if _val(fields, "rent_free_days"):
        cfg["rent_free"].append({"start": comm.isoformat(), "end": (comm + timedelta(days=int(_val(fields, "rent_free_days")) - 1)).isoformat()})
    lease_type = "STANDARD" if role == "LESSOR" else (payload.get("lease_type") or "STANDARD")
    desc = payload.get("description") or (f"{ac_name} — " + (_val(fields, "asset_address") or _val(fields, "asset_description") or "")[:120])
    lease = Lease(lease_code=next_lease_code(db), company_id=company.id, entity_id=ent_id, description=desc[:290],
                  asset_class_id=ac.id, asset_description=_val(fields, "asset_description"), location=_val(fields, "asset_address"),
                  counterparty_id=cp.id if cp else None, contract_date=parse_date(_val(fields, "agreement_date")), commencement_date=comm,
                  availability_date=comm, contract_end=end, currency=_val(fields, "currency") or company.functional_currency,
                  payment_frequency=freq_code, payment_timing=cfg["timing"], generator_config=cfg, lease_type=lease_type, role=role,
                  discount_rate_pct=(ans.get("discount_rate") or None) if role == "LESSEE" else None,
                  rate_source=ans.get("discount_rate_source") if role == "LESSEE" else None,
                  lessor_details=({} if role == "LESSOR" else None),
                  cost_centre=payload.get("cost_centre"), business_unit=payload.get("business_unit"),
                  source_extraction_id=run.id, created_by=user.id, status="Draft",
                  notes=f"Created from agreement '{run.result.get('document', {}).get('filename')}' (extraction #{run.id})."
                  + (" Lessor: complete the classification inputs (fair value, carrying amount and economic life of the asset, or a "
                     "documented classification) before calculating." if role == "LESSOR" else ""))
    db.add(lease)
    db.flush()
    lock = _val(fields, "lock_in_months")
    if lock and tenure and int(lock) < int(tenure):
        rc = ans.get("rc_continue_after_lock_in")
        notice = _val(fields, "lessee_termination_notice_months")
        lease.options.append(LeaseOptionRow(kind="TERMINATION", holder="LESSEE", exercise_date=prev_day(add_months(comm, int(lock))),
                                            reasonably_certain=None if rc is None else bool(rc), rationale=ans.get("rc_continue_rationale"),
                                            price=_val(fields, "termination_penalty"),
                                            description=f"Lessee may terminate after {lock}-month lock-in"
                                            + (f" ({notice} months' notice)" if notice else "")))
    if _val(fields, "renewal_option") in (True, "true", "True"):
        months = _val(fields, "renewal_months") or tenure
        if months:
            lessee_opt = _val(fields, "renewal_at_option_of") == "LESSEE"
            rc = ans.get("rc_renewal") if lessee_opt else False
            lease.options.append(LeaseOptionRow(kind="EXTENSION", holder="LESSEE" if lessee_opt else "LESSOR",
                                                exercise_date=next_day(end), extension_end_date=prev_day(add_months(next_day(end), int(months))),
                                                reasonably_certain=None if rc is None else bool(rc),
                                                rationale=ans.get("rc_renewal_rationale") or ("Renewal requires mutual consent — not a lessee "
                                                                                              "option (B34)" if not lessee_opt else None),
                                                renewal_escalation_pct=_val(fields, "renewal_escalation_pct"),
                                                description="Renewal " + ("at lessee's option" if lessee_opt else "by mutual consent")))
    if _val(fields, "purchase_option_price"):
        rc = ans.get("rc_purchase")
        lease.options.append(LeaseOptionRow(kind="PURCHASE", holder="LESSEE", exercise_date=end, price=_val(fields, "purchase_option_price"),
                                            reasonably_certain=None if rc is None else bool(rc), description="Purchase option"))
    if _val(fields, "deposit_amount"):
        lease.deposits.append(Deposit(amount=_val(fields, "deposit_amount"), payment_date=comm, refund_date=next_day(end),
                                      interest_bearing=_val(fields, "deposit_interest_free") in (False, "false"),
                                      market_rate_pct=ans.get("deposit_market_rate") or (ans.get("discount_rate") if role == "LESSEE" else None),
                                      treat_difference_as_prepaid_rent=True,
                                      notes=("Deposit received from the lessee; " if role == "LESSOR" else "")
                                      + "From agreement; market rate per review answers"))
    if role == "LESSOR":
        # lessor: stamp duty is normally borne by the lessee; only costs borne by the lessor are its initial direct costs
        if _val(fields, "stamp_duty_amount") and _val(fields, "stamp_duty_borne_by") == "LESSOR":
            lease.lessor_details = {**(lease.lessor_details or {}), "lessor_idc": str(_val(fields, "stamp_duty_amount"))}
    else:
        if _val(fields, "stamp_duty_amount") and (_val(fields, "stamp_duty_borne_by") in ("LESSEE", None)):
            lease.costs.append(LeaseCost(kind="IDC", cost_date=comm, amount=_val(fields, "stamp_duty_amount"), description="Stamp duty & registration"))
        if _val(fields, "brokerage_amount"):
            lease.costs.append(LeaseCost(kind="IDC", cost_date=comm, amount=_val(fields, "brokerage_amount"), description="Brokerage"))
    if ans.get("restoration_estimate") and role == "LESSEE":
        lease.restorations.append(RestorationObligation(estimated_cost=ans["restoration_estimate"], settlement_date=next_day(end),
                                                        discount_rate_pct=ans.get("restoration_rate") or ans.get("discount_rate") or "8",
                                                        recognition_date=comm, notes="Estimate from review"))
    db.add(LeaseAssessment(lease_id=lease.id, identified_asset=True,
                           substitution_rights="SUBSTANTIVE?" if _val(fields, "substitution_right") else "NONE",
                           contains_lease=None if _val(fields, "substitution_right") else True,
                           exemption=lease_type if lease_type in ("SHORT_TERM", "LOW_VALUE") else "NONE",
                           conclusion=None, notes="Initial assessment from agreement reader — reviewer to confirm."))
    regenerate_payments(db, lease, user)
    doc_id = db.scalar(select(ExtractionRun.document_id).where(ExtractionRun.id == run.id))
    doc = db.get(Document, doc_id)
    if doc and doc.lease_id is None:
        doc.lease_id = lease.id
    run.lease_id = lease.id
    run.confirmed_by = user.id
    run.confirmed_at = datetime.now()
    edited = [k for k, v in (payload.get("fields") or {}).items() if str(v) != str((base.get(k) or {}).get("value"))]
    audit.log(db, user, "CREATE", "Lease", lease.id, lease.lease_code, None, None,
              f"Created from extraction #{run.id} as {role.title()}; fields edited by reviewer: {', '.join(edited) or 'none'}",
              document_id=doc_id)
    return lease
