"""The Phase 1 workflow, end to end:

    template -> upload -> read -> parse -> assemble vouchers -> validate
             -> preview -> XML -> post to Tally -> parse response -> history + audit

Posting always works from the vouchers stored with a *validated* batch, so a
file with errors can never reach Tally.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any

from app.accounting.models import ValidationIssue, Voucher, VoucherKind
from app.accounting.services import VoucherAssembler
from app.accounting.validation import BANK_GROUPS, VoucherValidator, exact_history_key, history_company_key, summarise
from app.config.settings import AppConfig, EnvSettings
from app.database.database import utc_now
from app.database.repositories import BatchRepository, HistoryRepository
from app.excel.generator import TemplateLists, build_template, template_filename
from app.excel.reader import read_workbook
from app.excel.samples import SAMPLE_ROWS
from app.excel.template_spec import spec_for
from app.excel.validator import parse_rows
from app.services.audit_service import AuditAction, AuditService
from app.services.errors import NotFound, UserError
from app.services.settings_service import SettingsService
from app.services.tally_service import TallyService
from app.tally.client import TallyConnectionError
from app.tally.response_parser import parse_import_response
from app.tally.xml_generator import TallyXmlGenerator

logger = logging.getLogger("brmco.import")

_SEVERITY_ORDER = {"error": 0, "warning": 1}


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[-80:] or "upload.xlsx"


class ImportService:
    def __init__(self, env: EnvSettings, settings: SettingsService, batches: BatchRepository,
                 history: HistoryRepository, tally: TallyService, audit: AuditService) -> None:
        self.env = env
        self.settings = settings
        self.batches = batches
        self.history = history
        self.tally = tally
        self.audit = audit

    # ------------------------------------------------------------------ templates
    def template(self, kind: VoucherKind, sample: bool = False) -> tuple[str, bytes]:
        config = self.settings.get()
        spec = spec_for(kind)
        if sample:
            content = build_template(spec, TemplateLists(), company_name="BRMCo Demo Company",
                                     financial_year="2026-27", sample_rows=SAMPLE_ROWS[kind])
            return f"sample-{template_filename(spec)}", content
        masters = self.tally.lookup(config)
        lists = TemplateLists(
            ledgers=masters.names("ledger"),
            bank_ledgers=masters.ledgers_under(BANK_GROUPS),
            stock_items=masters.names("stock_item"),
            units=masters.names("unit"),
        )
        content = build_template(spec, lists, company_name=config.company_name,
                                 financial_year=config.financial_year)
        self.audit.record(AuditAction.TEMPLATE_DOWNLOADED, company=config.company_name, kind=kind.value,
                          details={"ledgers_in_dropdown": len(lists.ledgers)})
        return template_filename(spec), content

    # ------------------------------------------------------------------ upload + validate
    def upload(self, kind: VoucherKind, file_name: str, content: bytes) -> dict[str, Any]:
        config = self.settings.get()
        spec = spec_for(kind)
        batch_id = uuid.uuid4().hex[:12]
        file_name = file_name or "upload.xlsx"
        self.audit.record(AuditAction.EXCEL_UPLOADED, company=config.company_name, kind=kind.value,
                          batch_id=batch_id, details={"file": file_name, "bytes": len(content)})

        issues: list[ValidationIssue] = []
        vouchers: list[Voucher] = []
        row_count = 0
        if len(content) > self.env.max_upload_mb * 1024 * 1024:
            issues.append(ValidationIssue(severity="error", code="file.size",
                                          message=f"File is larger than {self.env.max_upload_mb} MB."))
        else:
            read = read_workbook(content, spec, file_name)
            issues.extend(read.issues)
            row_count = len(read.rows)
            if read.ok:
                parsed, cell_issues = parse_rows(spec, read.rows)
                issues.extend(cell_issues)
                masters = self.tally.lookup(config)
                vouchers, asm_issues = VoucherAssembler(spec, config, masters).assemble(parsed)
                issues.extend(asm_issues)
                issues.extend(VoucherValidator(config, masters, self.history).validate(vouchers))

        issues.sort(key=lambda i: (i.row or 0, _SEVERITY_ORDER[i.severity]))
        counts = summarise(issues)
        status = "invalid" if counts["errors"] else "validated"

        stored = self.env.upload_dir / f"{batch_id}_{_safe_name(file_name)}"
        try:
            stored.write_bytes(content)
        except OSError:
            logger.exception("Could not store uploaded file")
            stored = None  # type: ignore[assignment]

        self.batches.create({
            "id": batch_id, "created_at": utc_now(), "voucher_kind": kind.value, "file_name": file_name,
            "stored_file": str(stored) if stored else None, "company_name": config.company_name,
            "tally_company": config.tally_company_name, "financial_year": config.financial_year,
            "demo_mode": int(config.demo_mode), "status": status, "voucher_count": len(vouchers),
            "row_count": row_count, "error_count": counts["errors"], "warning_count": counts["warnings"],
            "vouchers_json": json.dumps([v.model_dump(mode="json") for v in vouchers]),
            "issues_json": json.dumps([i.model_dump() for i in issues]),
        })
        action = AuditAction.VALIDATION_FAILED if counts["errors"] else AuditAction.VALIDATION_PERFORMED
        self.audit.record(action, company=config.company_name, kind=kind.value, batch_id=batch_id,
                          details={"file": file_name, "rows": row_count, "vouchers": len(vouchers), **counts})
        logger.info("Batch %s (%s, %s): %d vouchers, %d errors, %d warnings", batch_id, kind.value, file_name,
                    len(vouchers), counts["errors"], counts["warnings"])
        return self.batch_view(batch_id)

    # ------------------------------------------------------------------ batch access
    def _batch(self, batch_id: str) -> dict[str, Any]:
        batch = self.batches.get(batch_id)
        if not batch:
            raise NotFound("This upload was not found. Please upload the file again.")
        return batch

    @staticmethod
    def _vouchers(batch: dict[str, Any]) -> list[Voucher]:
        return [Voucher.model_validate(v) for v in json.loads(batch["vouchers_json"] or "[]")]

    def batch_view(self, batch_id: str) -> dict[str, Any]:
        batch = self._batch(batch_id)
        vouchers = self._vouchers(batch)
        config = self.settings.get()
        return {
            "id": batch["id"], "kind": batch["voucher_kind"], "kind_label": VoucherKind(batch["voucher_kind"]).label,
            "file_name": batch["file_name"], "created_at": batch["created_at"], "status": batch["status"],
            "row_count": batch["row_count"], "voucher_count": batch["voucher_count"],
            "errors": batch["error_count"], "warnings": batch["warning_count"],
            "issues": json.loads(batch["issues_json"] or "[]"),
            "vouchers": [v.preview() for v in vouchers],
            "totals": {
                "debit": str(sum((v.total_debit for v in vouchers), 0)),
                "credit": str(sum((v.total_credit for v in vouchers), 0)),
            },
            "can_post": batch["status"] in ("validated", "failed", "partial", "demo") and not batch["error_count"],
            "demo_mode": bool(batch["demo_mode"]),
            "stale": self._stale_reason(batch, config),
            "missing_ledgers": sum(1 for i in json.loads(batch["issues_json"] or "[]") if i.get("code") == "master.ledger"),
        }

    # ------------------------------------------------------------------ missing ledgers
    _GROUP_BY_COLUMN = {
        "customer ledger": ("Sundry Debtors", True), "supplier ledger": ("Sundry Creditors", True),
        "party ledger": ("Sundry Debtors", True), "sales ledger": ("Sales Accounts", False),
        "purchase/expense ledger": ("Purchase Accounts", False), "bank ledger": ("Bank Accounts", False),
        "settings: round off ledger": ("Indirect Expenses", False),
    }
    _DUTY_HEADS = {"cgst": "Central Tax", "sgst": "State Tax", "igst": "Integrated Tax", "cess": "Cess"}

    def missing_ledgers(self, batch_id: str) -> dict[str, Any]:
        """Ledgers used by an uploaded file that are not in the Tally master cache, with suggested groups.

        Suggestions only — nothing is created until the user reviews and confirms them.
        """
        batch = self._batch(batch_id)
        config = self.settings.get()
        masters = self.tally.lookup(config)
        found: dict[str, dict[str, Any]] = {}
        for v in self._vouchers(batch):
            entries = [(p.ledger, p.source_column or "", p.is_party) for p in v.postings]
            entries += [(i.ledger, "Sales Ledger" if v.kind == VoucherKind.SALES else "Purchase/Expense Ledger", False)
                        for i in v.inventory]
            for ledger, column, is_party in entries:
                if not ledger or masters.resolve("ledger", ledger) or ledger.lower() in found:
                    continue
                col = column.lower()
                parent, bill_wise = self._GROUP_BY_COLUMN.get(col, ("", False))
                duty = None
                if col.startswith("settings: output") or col.startswith("settings: input"):
                    parent = "Duties & Taxes"
                    duty = next((h for k, h in self._DUTY_HEADS.items() if k in col), None)
                if parent and masters.has("group") and not masters.resolve("group", parent):
                    parent = ""
                gstin = v.party_gstin if is_party else None
                found[ledger.lower()] = {
                    "name": ledger, "parent": parent, "used_in": column or "Ledger", "bill_wise": bill_wise,
                    "gst_duty_head": duty, "gstin": gstin, "state": v.party_state if is_party else None,
                    "gst_registration_type": ("Regular" if gstin else "Unregistered") if is_party and v.lines else None,
                    "row": v.first_row,
                }
        return {"batch_id": batch_id, "file_name": batch["file_name"], "ledgers": list(found.values())}

    def revalidate(self, batch_id: str) -> dict[str, Any]:
        """Validate the same uploaded file again (e.g. after creating missing ledgers)."""
        batch = self._batch(batch_id)
        path = batch.get("stored_file")
        try:
            content = open(path, "rb").read() if path else None
        except OSError:
            content = None
        if not content:
            raise UserError("The original file is no longer available. Please upload it again.")
        return self.upload(VoucherKind(batch["voucher_kind"]), batch["file_name"], content)

    @staticmethod
    def _stale_reason(batch: dict[str, Any], config: AppConfig) -> str | None:
        if bool(batch["demo_mode"]) != config.demo_mode:
            return "Demo mode was switched since this file was validated. Upload it again."
        if (batch["tally_company"] or "") != config.tally_company_name or \
                (batch["financial_year"] or "") != config.financial_year:
            return "Company or financial year changed since this file was validated. Upload it again."
        return None

    def _require_postable(self, batch: dict[str, Any], config: AppConfig) -> list[Voucher]:
        if batch["error_count"]:
            raise UserError("This file has validation errors. Fix them in Excel and upload again.")
        if batch["status"] == "posted":
            raise UserError("This file has already been posted to Tally.")
        stale = self._stale_reason(batch, config)
        if stale:
            raise UserError(stale)
        vouchers = self._vouchers(batch)
        if not vouchers:
            raise UserError("There are no vouchers to post.")
        return vouchers

    # ------------------------------------------------------------------ XML
    def xml(self, batch_id: str, download: bool = True) -> tuple[str, bytes]:
        config = self.settings.get()
        batch = self._batch(batch_id)
        if batch["error_count"]:
            raise UserError("XML is only available for files that passed validation.")
        vouchers = self._vouchers(batch)
        content = TallyXmlGenerator(config).import_envelope(vouchers)
        name = f"{batch['voucher_kind']}_{batch_id}_{datetime.now():%Y%m%d_%H%M%S}.xml"
        (self.env.xml_dir / name).write_bytes(content)
        self.batches.update(batch_id, xml_file=name)
        self.audit.record(AuditAction.XML_GENERATED, company=config.company_name, kind=batch["voucher_kind"],
                          batch_id=batch_id, details={"file": name, "vouchers": len(vouchers)})
        if download:
            self.audit.record(AuditAction.XML_DOWNLOADED, company=config.company_name,
                              kind=batch["voucher_kind"], batch_id=batch_id, details={"file": name})
        return name, content

    # ------------------------------------------------------------------ posting
    def post(self, batch_id: str) -> dict[str, Any]:
        config = self.settings.get()
        batch = self._batch(batch_id)
        vouchers = self._require_postable(batch, config)
        kind = batch["voucher_kind"]
        generator = TallyXmlGenerator(config)
        xml_name, _ = self.xml(batch_id, download=False)
        client = self.tally.client(config)
        demo = config.demo_mode
        company_key = history_company_key(config)

        # Catch what Tally would reject with a cryptic message (Educational-mode dates, pre-books dates).
        problem = self.tally.posting_problem(config, client, vouchers)
        if problem:
            self.audit.record(AuditAction.TALLY_POST_FAILED, company=config.company_name, kind=kind,
                              batch_id=batch_id, details={"blocked_before_posting": problem})
            raise UserError(problem)

        self.audit.record(AuditAction.TALLY_POST_ATTEMPTED, company=config.company_name, kind=kind,
                          batch_id=batch_id, details={"vouchers": len(vouchers), "demo": demo, "url": client.url})

        # Re-check: something may have been posted since validation (e.g. in another tab).
        already = {} if demo else self.history.find_exact(
            company_key, [k for k in (exact_history_key(config, v) for v in vouchers) if k])

        results: list[dict[str, Any]] = []
        totals = {"created": 0, "altered": 0, "ignored": 0, "errors": 0}
        posted_records: list[dict[str, Any]] = []
        connection_error: str | None = None
        for v in vouchers:
            base = {"voucher": v.label, "date": v.date.isoformat(), "amount": str(v.amount), "rows": v.rows}
            key = exact_history_key(config, v)
            if key and key in already:
                results.append({**base, "status": "SKIPPED", "message": "Already posted to Tally earlier."})
                continue
            if connection_error:
                results.append({**base, "status": "NOT_ATTEMPTED", "message": "Not sent: Tally connection failed."})
                continue
            try:
                raw = client.post(generator.import_envelope([v]))
            except TallyConnectionError as exc:
                connection_error = str(exc)
                logger.warning("Tally connection failed during batch %s: %s", batch_id, exc)
                results.append({**base, "status": "FAILED", "message": connection_error})
                totals["errors"] += 1
                continue
            r = parse_import_response(raw, expected=1)
            totals["created"] += r.created
            totals["altered"] += r.altered
            totals["ignored"] += r.ignored
            totals["errors"] += 0 if r.success else max(1, r.errors + r.exceptions)
            results.append({**base, "status": r.status, "message": r.message, "created": r.created,
                            "altered": r.altered, "errors": r.errors, "line_errors": r.line_errors,
                            "last_voucher_id": r.last_voucher_id, "response": r.raw[:2000]})
            if r.success and not demo:
                posted_records.append({
                    "company": company_key, "financial_year": config.financial_year, "voucher_kind": kind,
                    "exact_key": key, "fuzzy_key": v.fuzzy_key(), "voucher_label": v.label,
                    "voucher_date": v.date.isoformat(), "party_ledger": v.party_ledger, "amount": str(v.amount),
                })

        attempted = [r for r in results if r["status"] != "SKIPPED"]
        ok = [r for r in attempted if r["status"] == "SUCCESS"]
        if attempted and len(ok) == len(attempted):
            overall = "SUCCESS"
        elif ok:
            overall = "PARTIAL"
        else:
            overall = "FAILED"
        if not attempted:
            overall, summary = "FAILED", "Nothing was posted: every voucher had already been posted."
        elif connection_error and not ok:
            summary = connection_error
        else:
            summary = f"{len(ok)} of {len(attempted)} voucher(s) accepted by Tally."
            failures = [f"{r['voucher']}: {r['message']}" for r in attempted if r["status"] != "SUCCESS"]
            if failures:
                summary += " Failed — " + "; ".join(failures[:5]) + (" …" if len(failures) > 5 else "")
        if demo:
            summary = "DEMO MODE — No entry posted to Tally. " + summary

        history_id = self.history.add({
            "batch_id": batch_id, "company_name": config.company_name, "tally_company": config.tally_company_name,
            "financial_year": config.financial_year, "voucher_kind": kind,
            "voucher_numbers": ", ".join(v.label for v in vouchers)[:2000],
            "excel_file_name": batch["file_name"], "xml_file_name": xml_name, "record_count": len(vouchers),
            "tally_status": overall, "created_count": totals["created"], "altered_count": totals["altered"],
            "ignored_count": totals["ignored"], "error_count": totals["errors"], "tally_response": summary,
            "error_details": json.dumps([{k: v for k, v in r.items() if k != "response"} for r in results]),
            "demo_mode": int(demo),
        }, posted_records)

        new_status = "demo" if demo else {"SUCCESS": "posted", "PARTIAL": "partial", "FAILED": "failed"}[overall]
        self.batches.update(batch_id, status=new_status)
        action = AuditAction.TALLY_POST_SUCCESS if overall == "SUCCESS" else AuditAction.TALLY_POST_FAILED
        self.audit.record(action, company=config.company_name, kind=kind, batch_id=batch_id,
                          details={"status": overall, "demo": demo, "history_id": history_id, **totals})
        logger.info("Batch %s posted: %s (%s)", batch_id, overall, summary)
        return {"status": overall, "demo_mode": demo, "message": summary, "history_id": history_id,
                "xml_file": xml_name, **totals, "results": results}
