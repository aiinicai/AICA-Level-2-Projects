"""Companies and financial years. Keeps every company's data separate."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import select

from ipt.core import permissions as perms
from ipt.core.context import CurrentUser
from ipt.core.gstin import normalize, validate_gstin
from ipt.core.states import STATES
from ipt.db.base import Database
from ipt.db.models import Company, FinancialYear
from ipt.services import audit_service, storage_service


class ValidationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


@dataclass
class CompanyInput:
    name: str
    state_code: str
    gstin: str = ""
    address: str = ""
    currency: str = "INR"
    tally_company_name: str = ""
    tally_version: str = ""
    tally_host: str = "localhost"
    tally_port: int = 9000
    extra: dict = field(default_factory=dict)


def fy_label(start_year: int) -> str:
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def _company_dict(c: Company) -> dict:
    return {k: getattr(c, k) for k in ("name", "gstin", "state_code", "address", "currency",
                                       "tally_company_name", "tally_version", "tally_host",
                                       "tally_port", "is_active")}


class CompanyService:
    def __init__(self, db: Database, data_root: Path):
        self.db = db
        self.data_root = data_root

    # ---------- validation ----------
    def _validate(self, data: CompanyInput, s, company_id: int | None) -> CompanyInput:
        errors: dict[str, str] = {}
        data.name = data.name.strip()
        data.gstin = normalize(data.gstin)
        if not data.name:
            errors["name"] = "Company name is required"
        if data.state_code not in STATES:
            errors["state_code"] = "Select a valid state"
        if data.gstin:
            res = validate_gstin(data.gstin)
            if not res.valid:
                errors["gstin"] = res.message
            elif res.state_code != data.state_code:
                errors["gstin"] = f"GSTIN state code {res.state_code} does not match selected state {data.state_code}"
            else:
                dup = s.scalar(select(Company).where(Company.gstin == data.gstin))
                if dup and dup.id != company_id:
                    errors["gstin"] = f"GSTIN already used by company '{dup.name}'"
        if not (1 <= int(data.tally_port) <= 65535):
            errors["tally_port"] = "Port must be between 1 and 65535"
        if len(data.currency.strip()) != 3:
            errors["currency"] = "Use a 3-letter currency code, e.g. INR"
        if errors:
            raise ValidationError(errors)
        return data

    # ---------- companies ----------
    def list_companies(self, include_inactive: bool = True) -> list[Company]:
        with self.db.session() as s:
            q = select(Company).order_by(Company.name)
            if not include_inactive:
                q = q.where(Company.is_active.is_(True))
            return list(s.scalars(q))

    def get_company(self, company_id: int) -> Company | None:
        with self.db.session() as s:
            return s.get(Company, company_id)

    def create_company(self, data: CompanyInput, actor: CurrentUser) -> Company:
        perms.require(actor.role, "company.manage")
        with self.db.session() as s:
            data = self._validate(data, s, None)
            c = Company(name=data.name, gstin=data.gstin or None, state_code=data.state_code,
                        address=data.address.strip(), currency=data.currency.strip().upper(),
                        tally_company_name=data.tally_company_name.strip(),
                        tally_version=data.tally_version.strip(), tally_host=data.tally_host.strip() or "localhost",
                        tally_port=int(data.tally_port), is_active=True, folder_name="pending")
            s.add(c)
            s.flush()
            c.folder_name = storage_service.safe_folder_name(c.name, c.id)
            storage_service.company_dir(self.data_root, c.folder_name).mkdir(parents=True, exist_ok=True)
            audit_service.record(s, actor, "company.create", "company", c.id, after=_company_dict(c), company_id=c.id)
            return c

    def update_company(self, company_id: int, data: CompanyInput, actor: CurrentUser) -> Company:
        perms.require(actor.role, "company.manage")
        with self.db.session() as s:
            c = s.get(Company, company_id)
            if c is None:
                raise ValidationError({"company": "Company not found"})
            data = self._validate(data, s, company_id)
            before = _company_dict(c)
            c.name, c.gstin, c.state_code = data.name, data.gstin or None, data.state_code
            c.address, c.currency = data.address.strip(), data.currency.strip().upper()
            c.tally_company_name, c.tally_version = data.tally_company_name.strip(), data.tally_version.strip()
            c.tally_host, c.tally_port = data.tally_host.strip() or "localhost", int(data.tally_port)
            # folder_name intentionally never changes, so stored file paths stay valid.
            audit_service.record(s, actor, "company.update", "company", c.id, before, _company_dict(c), company_id=c.id)
            return c

    def set_company_active(self, company_id: int, active: bool, actor: CurrentUser) -> None:
        perms.require(actor.role, "company.manage")
        with self.db.session() as s:
            c = s.get(Company, company_id)
            if c is None:
                raise ValidationError({"company": "Company not found"})
            c.is_active = active
            audit_service.record(s, actor, "company.enable" if active else "company.disable", "company", c.id,
                                 company_id=c.id)

    # ---------- financial years ----------
    def list_fys(self, company_id: int) -> list[FinancialYear]:
        with self.db.session() as s:
            return list(s.scalars(select(FinancialYear).where(FinancialYear.company_id == company_id)
                                  .order_by(FinancialYear.start_date.desc())))

    def create_fy(self, company_id: int, start_year: int, actor: CurrentUser,
                  books_begin: date | None = None) -> FinancialYear:
        perms.require(actor.role, "company.manage")
        if not 2017 <= start_year <= 2100:
            raise ValidationError({"start_year": "GST financial years start from 2017-18"})
        start, end = date(start_year, 4, 1), date(start_year + 1, 3, 31)
        books_begin = books_begin or start
        if not start <= books_begin <= end:
            raise ValidationError({"books_begin_date": "Books beginning date must fall inside the financial year"})
        label = fy_label(start_year)
        with self.db.session() as s:
            c = s.get(Company, company_id)
            if c is None:
                raise ValidationError({"company": "Company not found"})
            if s.scalar(select(FinancialYear).where(FinancialYear.company_id == company_id,
                                                    FinancialYear.label == label)):
                raise ValidationError({"label": f"FY {label} already exists for {c.name}"})
            fy = FinancialYear(company_id=company_id, label=label, start_date=start, end_date=end,
                               books_begin_date=books_begin, is_locked=False)
            s.add(fy)
            s.flush()
            storage_service.ensure_fy_folders(self.data_root, c.folder_name, label)
            audit_service.record(s, actor, "fy.create", "financial_year", fy.id,
                                 after={"label": label, "books_begin_date": books_begin}, company_id=company_id)
            return fy

    def set_fy_locked(self, fy_id: int, locked: bool, actor: CurrentUser) -> None:
        perms.require(actor.role, "company.manage")
        with self.db.session() as s:
            fy = s.get(FinancialYear, fy_id)
            if fy is None:
                raise ValidationError({"fy": "Financial year not found"})
            fy.is_locked = locked
            audit_service.record(s, actor, "fy.lock" if locked else "fy.unlock", "financial_year", fy.id,
                                 company_id=fy.company_id)
