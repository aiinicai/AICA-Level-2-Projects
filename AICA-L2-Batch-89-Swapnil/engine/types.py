"""Plain input/output records for the engine. The Flask/SQLAlchemy layer maps
its ORM rows onto these; the engine never sees the database."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

COMPANY_TYPES = {"PRIVATE", "OPC", "PUBLIC_UNLISTED", "PUBLIC_LISTED", "SECTION8",
                 "NIDHI", "PRODUCER", "FOREIGN_CO"}
ENTITY_TYPES = COMPANY_TYPES | {"LLP"}


@dataclass
class EntityIn:
    id: int | str
    name: str
    entity_type: str
    incorporation_date: date
    has_share_capital: bool = True
    nominal_capital: float = 0.0
    paid_up_capital: float = 0.0
    llp_contribution: float = 0.0
    is_holding: bool = False
    is_subsidiary: bool = False
    subsidiary_of_public: bool = False
    nbfc: bool = False
    hfc: bool = False
    banking: bool = False
    excluded_sector: bool = False        # banking / insurance / power (XBRL r.3)
    government: bool = False
    special_act: bool = False
    listed_subsidiary: bool = False      # subsidiary of a listed company (XBRL)
    startup: bool = False
    status: str = "ACTIVE"               # ACTIVE / DORMANT / UNDER_STRIKE_OFF / STRUCK_OFF / AMALGAMATED
    single_director: bool = False        # OPC with one director -> no s.173 meetings
    ro_furnished_at_incorporation: bool = True
    engagement_start: date | None = None
    llp_elect_longer_first_fy: bool = False
    ccfs_excluded: bool = False          # strike-off/dormancy applied, vanishing, etc.

    @property
    def is_llp(self) -> bool:
        return self.entity_type == "LLP"

    @property
    def is_company(self) -> bool:
        return not self.is_llp

    @property
    def is_private(self) -> bool:
        return self.entity_type in {"PRIVATE", "OPC"}

    @property
    def is_public(self) -> bool:
        return self.entity_type in {"PUBLIC_UNLISTED", "PUBLIC_LISTED"}


@dataclass
class FactsIn:
    """Per-FY facts (brief §5.3). ``None`` means 'not entered'."""
    fy_key: str
    paid_up_capital: float | None = None
    turnover: float | None = None
    net_worth: float | None = None
    net_profit: float | None = None
    bank_borrowings_at_fy_end: float | None = None
    bank_borrowings_max: float | None = None
    deposits_max: float | None = None
    deposits_outstanding_31mar: bool | None = None
    has_subs_assoc_jv: bool | None = None
    ind_as: bool | None = None
    cost_audit_applicable: bool | None = None
    csr_override: bool | None = None
    agm_date: date | None = None
    board_approval_date: date | None = None
    auditor_appointed_at_agm: bool | None = None
    isin_obtained_date: date | None = None
    llp_contribution: float | None = None


@dataclass
class EventIn:
    id: int | str
    type: str
    date: date
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonIn:
    id: int | str
    name: str
    din: str
    din_allotment_date: date
    din_status: str = "APPROVED"
    last_annual_kyc_fy: str | None = None   # e.g. 'FY2024-25' -> annual KYC done up to that FY
    kyc_override_first_due: date | None = None
    detail_changes: list[date] = field(default_factory=list)


@dataclass
class Spec:
    """One generated obligation instance (brief §5.8)."""
    key: str
    rule_code: str
    form: str
    title: str
    period_key: str
    anchor_type: str
    anchor_date: date
    due_date: date
    entity_id: int | str | None = None
    person_din: str | None = None
    event_id: int | str | None = None
    variant: str | None = None
    provisional: bool = False
    facts_stale: bool = False
    needs_decision: str | None = None
    pre_engagement: bool = False
    agm_not_held: bool = False
    interpretation: bool = False
    verified: bool = False
    rule_version: str = ""
    rule_hash: str = ""
    law: str = ""
    fee_regime: str = "NONE"
    notes: list[str] = field(default_factory=list)
