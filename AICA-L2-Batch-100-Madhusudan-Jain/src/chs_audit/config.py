"""Society master data and statutory parameters used across all modules.

Everything that an auditor might want to change for a different society lives
here (rates, thresholds, due dates). All amounts are in INR.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

FY_START = date(2025, 4, 1)
FY_END = date(2026, 3, 31)
FY_LABEL = "FY 2025-26"
AY_LABEL = "AY 2026-27"


@dataclass
class Society:
    name: str = "Sunrise Heights Co-operative Housing Society Ltd."
    reg_no: str = "TNA/(TNA)/HSG/(TC)/12345/2009"
    address: str = "Plot 17, Ghodbunder Road, Thane (West) 400607, Maharashtra"
    registration_date: date = date(2009, 3, 12)
    occupation_certificate_date: date = date(2008, 9, 30)
    gstin: str = "27AAAAS1234A1Z5"
    pan: str = "AAAAS1234A"
    tan: str = "MUMS12345A"
    wings: tuple[str, ...] = ("A", "B")
    floors: int = 8
    flats_per_floor: int = 4
    committee_size: int = 11
    # Flats held by managing committee office bearers (used for related-party tests)
    chairman_flat: str = "A-801"
    secretary_flat: str = "A-402"
    treasurer_flat: str = "B-203"
    committee_flats: tuple[str, ...] = (
        "A-801", "A-402", "B-203", "A-104", "A-603", "B-401", "B-702",
        "A-302", "B-104", "A-704", "B-503",
    )
    last_structural_audit: date = date(2021, 3, 20)
    last_mc_election: date = date(2023, 1, 15)
    lift_licence_expiry: date = date(2026, 9, 15)
    insurance_policy_expiry: date = date(2026, 11, 14)
    last_fire_audit_form_b: date = date(2026, 1, 20)
    deemed_conveyance_status: str = "Pending - application not yet filed"


SOCIETY = Society()


# --------------------------------------------------------------------------- audit firm
FIRM_FILE = Path(__file__).resolve().parents[2] / "data" / "firm.json"


@dataclass
class Firm:
    """The chartered accountancy firm using the tool. Edited in the app (Data & settings) and stored in data/firm.json."""
    name: str = "Jain Jakhotiya & Associates"
    short_name: str = "JJAA"
    descriptor: str = "Chartered Accountants"
    website: str = "jjaa.in"
    signatory: str = "CA Madhusudan Jain"   # partner who signs every draft
    membership_no: str = ""      # ICAI membership number of the signatory
    panel_no: str = ""           # co-operative audit panel number, if empanelled
    address: str = "F-12/13, 4th Floor, Butte Patil Towers, Ganjawe Chowk, LBS Road, Navi Peth, Sadashiv Peth, Pune 411030"
    email: str = "support@jjaa.in"
    phone: str = "020-29524030"

    @property
    def display(self) -> str:
        return f"{self.name}, {self.descriptor}" if self.descriptor else self.name

    def signature_block(self) -> list[str]:
        """Sign-off used in every draft: the signing partner by name, not a firm-name template."""
        who = self.signatory or "Partner"
        if self.membership_no:
            who += f", M. No. {self.membership_no}"
        role = "Chartered Accountant" + (" (Panel Auditor)" if self.panel_no == "" else f" (Panel Auditor No. {self.panel_no})")
        lines = [who, role]
        if self.address:
            lines.append(self.address)
        if self.email or self.phone:
            lines.append(" · ".join(x for x in (self.email, self.phone) if x))
        return lines

    @property
    def auditor(self) -> str:
        """Who the drafts speak for: the signing partner if named, else the firm."""
        return self.signatory or self.display


def load_firm() -> Firm:
    if FIRM_FILE.exists():
        try:
            data = json.loads(FIRM_FILE.read_text(encoding="utf-8"))
            return Firm(**{k: v for k, v in data.items() if k in Firm.__dataclass_fields__})
        except Exception:
            pass
    return Firm()


def save_firm(firm: Firm) -> None:
    FIRM_FILE.parent.mkdir(parents=True, exist_ok=True)
    FIRM_FILE.write_text(json.dumps(asdict(firm), indent=2), encoding="utf-8")


FIRM = load_firm()


@dataclass(frozen=True)
class Rates:
    """Billing and statutory rates for the financial year."""
    # Bye-law 13(a)/(b): sinking fund 0.25% p.a. and repair fund 0.75% p.a. of construction cost
    construction_cost_per_sqft: float = 3500.0
    sinking_fund_rate: float = 0.0025
    repair_fund_rate: float = 0.0075
    # Bye-law 69: service charges shared equally by all flats
    service_charges_per_flat: float = 3200.0
    water_charges_per_flat: float = 300.0
    property_tax_per_sqft_month: float = 1.50
    car_parking_per_month: float = 500.0
    # Bye-law 43: non-occupancy charges capped at 10% of service charges
    non_occupancy_pct: float = 0.10
    # Bye-law 72: interest on arrears, simple interest, maximum 21% p.a.
    arrears_interest_rate: float = 0.21
    bill_due_day: int = 15
    # GST: Notification 12/2017 entry 77(c) + Circular 109/28/2019-GST
    gst_exemption_per_member_month: float = 7500.0
    gst_registration_threshold: float = 2_000_000.0
    gst_rate: float = 0.18
    # Expenditure approval limit fixed by the General Body (resolution of AGM 2024)
    committee_approval_limit: float = 50_000.0
    # Cash payment limit (bye-law and s.40A(3) discipline)
    cash_payment_limit: float = 10_000.0
    # Defaulter definition used by the society (months of arrears)
    defaulter_months: int = 3
    # TDS thresholds FY 2025-26
    tds_194c_single: float = 30_000.0
    tds_194c_aggregate: float = 100_000.0
    tds_194j_threshold: float = 50_000.0
    tds_194c_rate_individual: float = 0.01
    tds_194c_rate_others: float = 0.02
    tds_194j_rate: float = 0.10
    tds_194i_rate: float = 0.10


RATES = Rates()

# Flat typology by unit number on each floor
FLAT_TYPES = {
    1: ("2BHK", 950, True),
    2: ("2BHK", 950, True),
    3: ("1BHK", 650, False),
    4: ("3BHK", 1250, True),
}

MONTHS = [
    (2025, 4), (2025, 5), (2025, 6), (2025, 7), (2025, 8), (2025, 9),
    (2025, 10), (2025, 11), (2025, 12), (2026, 1), (2026, 2), (2026, 3),
]


def month_label(y: int, m: int) -> str:
    return date(y, m, 1).strftime("%b-%Y")
