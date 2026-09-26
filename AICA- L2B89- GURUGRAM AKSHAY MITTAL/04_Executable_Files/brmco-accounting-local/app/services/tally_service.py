"""Chooses the real or demo Tally client and wraps connection / master-sync use cases."""
from __future__ import annotations

import logging
from typing import Any

from app.accounting.models import Voucher
from app.config.settings import AppConfig, EnvSettings
from app.database.repositories import MasterRepository
from app.services.audit_service import AuditAction, AuditService
from app.accounting.gst import STATE_NAMES
from app.services.errors import UserError
from app.tally.client import CompanyInfo, DemoTallyClient, TallyClient, TallyConnectionError
from app.tally.master_xml import GST_DUTY_HEADS, GST_REGISTRATION_TYPES, NewLedger, ledger_import_envelope
from app.tally.masters import MASTER_TYPES, CachedMasters, MasterSyncService
from app.tally.response_parser import parse_import_response


logger = logging.getLogger("brmco.tally")

# TallyPrime Educational mode only accepts vouchers dated on these days of the month.
EDU_ALLOWED_DAYS = {1, 2, 31}


class TallyService:
    def __init__(self, env: EnvSettings, masters: MasterRepository, audit: AuditService) -> None:
        self.env = env
        self.masters_repo = masters
        self.audit = audit
        self.sync_service = MasterSyncService(masters)

    def client(self, config: AppConfig) -> TallyClient | DemoTallyClient:
        if config.demo_mode:
            return DemoTallyClient()
        return TallyClient(config.tally_url, timeout=self.env.tally_timeout_seconds)

    def _company(self, config: AppConfig, client) -> CompanyInfo | None:
        """Info for the configured company (or the first open one). None if it can't be read."""
        try:
            companies = client.company_info()
        except TallyConnectionError:
            return None
        except Exception:
            logger.exception("Could not read company info from Tally")
            return None
        wanted = config.tally_company_name.strip().lower()
        return next((c for c in companies if c.name.lower() == wanted), None) if wanted else \
            (companies[0] if companies else None)

    def posting_problem(self, config: AppConfig, client, vouchers: list[Voucher]) -> str | None:
        """Checks Tally will accept these dates before sending anything. Returns a message, or None."""
        info = self._company(config, client)
        if info is None:
            return None  # the posting loop reports connection problems per voucher
        if info.educational_mode:
            bad = [f"{v.label} ({v.date:%d-%m-%Y})" for v in vouchers if v.date.day not in EDU_ALLOWED_DAYS]
            if bad:
                return (f"TallyPrime is running in Educational mode, which only accepts vouchers dated the 1st, 2nd "
                        f"or 31st of a month. Tally would reject: {', '.join(bad[:10])}"
                        f"{' …' if len(bad) > 10 else ''}. Activate your TallyPrime licence (or, for testing only, "
                        "use those dates).")
        if info.books_from:
            early = [f"{v.label} ({v.date:%d-%m-%Y})" for v in vouchers if v.date < info.books_from]
            if early:
                return (f'Company "{info.name}" books begin on {info.books_from:%d-%m-%Y}; Tally will not accept '
                        f"earlier vouchers: {', '.join(early[:10])}.")
        return None

    def status(self, config: AppConfig) -> dict[str, Any]:
        client = self.client(config)
        st = client.status()
        warnings = []
        if st.connected and not st.demo and config.tally_company_name and st.companies and \
                config.tally_company_name.lower() not in (c.lower() for c in st.companies):
            warnings.append(f'Company "{config.tally_company_name}" is not open in Tally. '
                            f"Open companies: {', '.join(st.companies)}")
        info = self._company(config, client) if st.connected and not st.demo else None
        if info and info.educational_mode:
            warnings.append("TallyPrime is running in EDUCATIONAL MODE: it only accepts vouchers dated the 1st, 2nd "
                            "or 31st of a month. Other dates are rejected with 'Voucher date is missing'. "
                            "Activate your TallyPrime licence to post real data.")
        warning = " ".join(warnings) or None
        self.audit.record(AuditAction.TALLY_CONNECTION_TESTED, company=config.company_name,
                          details={"url": st.url, "connected": st.connected, "message": st.message})
        return {"connected": st.connected, "message": st.message, "url": st.url, "companies": st.companies,
                "demo_mode": st.demo, "warning": warning,
                "educational_mode": bool(info and info.educational_mode),
                "books_from": info.books_from.isoformat() if info and info.books_from else None}

    def sync_masters(self, config: AppConfig, types: list[str] | None = None) -> dict[str, Any]:
        results = self.sync_service.sync(self.client(config), config.master_cache_key,
                                         "" if config.demo_mode else config.tally_company_name, types)
        self.audit.record(AuditAction.MASTER_SYNC, company=config.company_name,
                          details={"company_key": config.master_cache_key, "results": results})
        return {"company_key": config.master_cache_key, "results": results,
                "counts": self.masters_repo.counts(config.master_cache_key)}

    def ledger_options(self, config: AppConfig) -> dict[str, Any]:
        masters = self.lookup(config)
        return {"groups": sorted(masters.names("group"), key=str.lower), "duty_heads": list(GST_DUTY_HEADS),
                "registration_types": list(GST_REGISTRATION_TYPES), "states": STATE_NAMES,
                "ledgers_synced": masters.has("ledger"), "demo_mode": config.demo_mode}

    def create_ledgers(self, config: AppConfig, ledgers: list[NewLedger]) -> dict[str, Any]:
        """Creates ledgers the user has reviewed. Each ledger is sent separately for an exact result."""
        if not ledgers:
            raise UserError("Add at least one ledger.")
        masters = self.lookup(config)
        problems: list[str] = []
        seen: set[str] = set()
        for i, led in enumerate(ledgers, start=1):
            key = led.name.lower()
            if key in seen:
                problems.append(f'Line {i}: "{led.name}" is listed twice.')
            seen.add(key)
            if masters.resolve("ledger", led.name):
                problems.append(f'Line {i}: ledger "{led.name}" already exists in Tally.')
            if masters.has("group"):
                parent = masters.resolve("group", led.parent)
                if parent is None:
                    problems.append(f'Line {i}: group "{led.parent}" does not exist in Tally.')
                else:
                    led.parent = parent
        if problems:
            raise UserError(" ".join(problems))

        client = self.client(config)
        company = "" if config.demo_mode else config.tally_company_name
        self.audit.record(AuditAction.LEDGER_CREATE_ATTEMPTED, company=config.company_name,
                          details={"ledgers": [l.model_dump() for l in ledgers], "demo": config.demo_mode})
        results: list[dict[str, Any]] = []
        connection_error: str | None = None
        for led in ledgers:
            if connection_error:
                results.append({"name": led.name, "status": "NOT_ATTEMPTED", "message": "Not sent: Tally connection failed."})
                continue
            try:
                raw = client.post(ledger_import_envelope([led], company))
            except TallyConnectionError as exc:
                connection_error = str(exc)
                results.append({"name": led.name, "status": "FAILED", "message": connection_error})
                continue
            r = parse_import_response(raw, expected=1)
            message = f'Ledger created under "{led.parent}".' if r.success else r.message
            results.append({"name": led.name, "status": r.status, "message": message})

        created = [r for r in results if r["status"] == "SUCCESS"]
        sync = self.sync_masters(config, ["ledger"]) if created else None
        overall = "SUCCESS" if len(created) == len(results) else ("PARTIAL" if created else "FAILED")
        self.audit.record(AuditAction.LEDGER_CREATED if created else AuditAction.LEDGER_CREATE_FAILED,
                          company=config.company_name, details={"status": overall, "results": results})
        return {"status": overall, "demo_mode": config.demo_mode, "created": len(created), "results": results,
                "resynced": bool(sync and sync["results"].get("ledger", {}).get("status") == "ok")}

    def lookup(self, config: AppConfig) -> CachedMasters:
        return CachedMasters(self.masters_repo, config.master_cache_key)

    def list_masters(self, config: AppConfig, master_type: str, q: str = "") -> list[dict[str, Any]]:
        if master_type not in MASTER_TYPES:
            return []
        return self.masters_repo.search(config.master_cache_key, master_type, q)

    def counts(self, config: AppConfig) -> dict[str, Any]:
        return self.masters_repo.counts(config.master_cache_key)
