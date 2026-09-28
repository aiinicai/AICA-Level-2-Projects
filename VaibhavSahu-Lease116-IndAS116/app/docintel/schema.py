"""Extraction schema — the Ind AS 116 inputs the agreement reader looks for.

Each field carries a description used in LLM prompts, the retrieval keywords used to
pick relevant clauses for small local models, and whether the field is essential for
measurement (missing essentials must be supplied by the user before calculation).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldDef:
    key: str
    label: str
    type: str                 # date | amount | percent | int | text | bool | choice
    group: str
    description: str
    keywords: tuple = ()
    choices: tuple = ()
    essential: bool = False
    ind_as_ref: str = ""


FIELDS: list[FieldDef] = [
    # parties & document
    FieldDef("agreement_type", "Agreement type", "choice", "Parties", "Type of document",
             ("leave and licen", "lease deed", "rent agreement", "lease agreement"),
             ("LEAVE_AND_LICENSE", "LEASE_DEED", "LEASE_AGREEMENT", "RENT_AGREEMENT", "EQUIPMENT_LEASE", "VEHICLE_LEASE", "OTHER")),
    FieldDef("lessor_name", "Lessor / licensor", "text", "Parties", "Legal name of the lessor / licensor / landlord / owner",
             ("lessor", "licensor", "landlord", "owner", "between")),
    FieldDef("lessee_name", "Lessee / licensee", "text", "Parties", "Legal name of the lessee / licensee / tenant",
             ("lessee", "licensee", "tenant")),
    FieldDef("agreement_date", "Agreement date", "date", "Parties", "Date on which the agreement was executed / made",
             ("made", "entered", "executed", "dated", "day of")),
    # asset
    FieldDef("asset_description", "Underlying asset / premises", "text", "Asset",
             "Description of the premises or asset leased (unit, floor, building, equipment)",
             ("premises", "property", "schedule", "unit", "floor", "equipment", "vehicle")),
    FieldDef("asset_category", "Asset class", "choice", "Asset", "Class of underlying asset", (),
             ("Buildings", "Land", "Vehicles", "Plant and machinery", "IT equipment", "Furniture and fixtures", "Other")),
    FieldDef("asset_address", "Location / address", "text", "Asset", "Address or location of the premises/asset",
             ("situated", "located", "address")),
    FieldDef("area_sqft", "Area (sq ft)", "number", "Asset", "Leased area in square feet (carpet/chargeable)",
             ("sq. ft", "square feet", "sq ft", "sft", "area")),
    # term
    FieldDef("commencement_date", "Commencement date", "date", "Term",
             "Date from which the lessee has the right to use the asset (lease/licence commencement, handover)",
             ("commence", "commencement", "with effect from", "w.e.f", "handover", "possession"), essential=True,
             ind_as_ref="App. A — commencement date"),
    FieldDef("rent_commencement_date", "Rent commencement date", "date", "Term",
             "Date from which rent/licence fee becomes payable (after any rent-free / fit-out period)",
             ("rent commencement", "rent shall commence", "fee shall be payable from")),
    FieldDef("expiry_date", "Expiry date", "date", "Term", "Last day of the contractual term", ("expire", "expiry", "ending on", "till", "until")),
    FieldDef("tenure_months", "Contractual term (months)", "int", "Term", "Total contractual period of the lease/licence in months",
             ("period of", "term of", "tenure", "duration"), essential=True, ind_as_ref="18"),
    FieldDef("lock_in_months", "Lock-in period (months)", "int", "Term", "Lock-in period during which termination is not permitted",
             ("lock-in", "lock in", "locked in"), ind_as_ref="B34"),
    FieldDef("lock_in_applies_to", "Lock-in applies to", "choice", "Term", "Which party is bound by the lock-in", ("lock-in",),
             ("BOTH", "LESSEE", "LESSOR")),
    # rent
    FieldDef("currency", "Currency", "text", "Rent", "Currency of the lease payments", ("rs", "inr", "usd", "rupees")),
    FieldDef("rent_amount", "Rent / licence fee per period", "amount", "Rent",
             "Fixed rent or licence fee amount per payment period (excluding taxes and maintenance)",
             ("rent", "license fee", "licence fee", "compensation", "rental"), essential=True, ind_as_ref="27(a)"),
    FieldDef("rent_frequency", "Payment frequency", "choice", "Rent", "How often rent is paid",
             ("per month", "monthly", "quarterly", "per annum"), ("MONTHLY", "QUARTERLY", "HALF_YEARLY", "ANNUAL"), essential=True),
    FieldDef("payment_timing", "Payment timing", "choice", "Rent", "Rent payable in advance or in arrears",
             ("in advance", "in arrears", "on or before"), ("ADVANCE", "ARREARS"), essential=True),
    FieldDef("payment_due_day", "Due day of month", "int", "Rent", "Day of the month by which rent is payable", ("on or before", "day of each")),
    FieldDef("rate_per_sqft", "Rate per sq ft", "amount", "Rent", "Rent rate per square foot per month", ("per sq",)),
    FieldDef("escalation_pct", "Escalation %", "percent", "Rent", "Percentage increase in rent", ("escalation", "increase", "enhance"),
             ind_as_ref="27(a)"),
    FieldDef("escalation_every_months", "Escalation frequency (months)", "int", "Rent", "Interval between escalations in months",
             ("every", "annually", "per annum")),
    FieldDef("escalation_basis", "Escalation basis", "choice", "Rent", "Escalation on last paid rent (compound) or base rent (simple)",
             ("last paid", "base rent"), ("COMPOUND", "SIMPLE")),
    FieldDef("rent_free_days", "Rent-free / fit-out period (days)", "int", "Rent",
             "Rent-free or fit-out period during which no rent is payable (in days)", ("rent free", "rent-free", "fit-out", "fitout")),
    FieldDef("gst_treatment", "GST", "text", "Rent", "Whether amounts are exclusive or inclusive of GST", ("gst", "goods and services tax")),
    # deposit & charges
    FieldDef("deposit_amount", "Security deposit", "amount", "Deposit", "Refundable security deposit amount",
             ("security deposit", "deposit"), ind_as_ref="Ind AS 109"),
    FieldDef("deposit_interest_free", "Deposit is interest-free", "bool", "Deposit", "True if the deposit carries no interest",
             ("interest free", "interest-free", "without interest")),
    FieldDef("cam_amount", "Maintenance / CAM charges per month", "amount", "Charges",
             "Maintenance / common area maintenance / service charges per month (non-lease component)",
             ("maintenance", "cam", "common area"), ind_as_ref="12"),
    FieldDef("variable_rent", "Variable rent terms", "text", "Charges", "Revenue share / turnover rent / usage-based payments",
             ("revenue share", "turnover", "% of sales", "minimum guarantee"), ind_as_ref="38(b)"),
    FieldDef("stamp_duty_amount", "Stamp duty paid", "amount", "Charges", "Stamp duty amount (e-stamp certificate)",
             ("stamp duty",), ind_as_ref="24(c)"),
    FieldDef("stamp_duty_borne_by", "Stamp duty & registration borne by", "choice", "Charges",
             "Party bearing stamp duty and registration charges", ("stamp duty", "registration"), ("LESSEE", "LESSOR", "EQUALLY")),
    FieldDef("brokerage_amount", "Brokerage", "amount", "Charges", "Brokerage paid by the lessee", ("brokerage",), ind_as_ref="24(c)"),
    # options
    FieldDef("renewal_option", "Renewal / extension clause", "bool", "Options", "Whether the agreement can be renewed / extended",
             ("renew", "extension", "extend"), ind_as_ref="18(a)"),
    FieldDef("renewal_months", "Renewal period (months)", "int", "Options", "Length of each renewal period in months", ("renew",)),
    FieldDef("renewal_at_option_of", "Renewal at option of", "choice", "Options", "Whether renewal is the lessee's option or by mutual consent",
             ("renew", "option", "mutual"), ("LESSEE", "MUTUAL", "LESSOR")),
    FieldDef("renewal_escalation_pct", "Escalation on renewal %", "percent", "Options", "Rent increase applicable on renewal", ("renew",)),
    FieldDef("lessee_termination_notice_months", "Lessee termination notice (months)", "int", "Options",
             "Notice period for the lessee/licensee to terminate (after lock-in)", ("terminate", "notice"), ind_as_ref="18(b)"),
    FieldDef("lessor_can_terminate_without_cause", "Lessor may terminate without cause", "bool", "Options",
             "Whether the lessor/licensor may terminate by notice other than for breach", ("terminate", "notice"), ind_as_ref="B34–B35"),
    FieldDef("purchase_option_price", "Purchase option price", "amount", "Options", "Price at which the lessee may purchase the asset",
             ("purchase", "buy", "option to acquire"), ind_as_ref="27(d)"),
    FieldDef("termination_penalty", "Termination penalty", "amount", "Options", "Penalty payable by the lessee on early termination",
             ("penalty", "compensation", "liquidated damages"), ind_as_ref="27(e)"),
    FieldDef("residual_value_guarantee", "Residual value guarantee", "amount", "Options", "Residual value guaranteed by the lessee",
             ("residual value",), ind_as_ref="27(c)"),
    # other clauses
    FieldDef("restoration_obligation", "Restoration / reinstatement obligation", "bool", "Other",
             "Lessee must restore/reinstate the premises to original condition", ("restore", "reinstate", "original condition"),
             ind_as_ref="24(d)"),
    FieldDef("sublease_permitted", "Subletting permitted", "bool", "Other", "Whether subletting/sub-licensing is permitted",
             ("sub-let", "sublet", "sub-lease", "sublease", "assign")),
    FieldDef("substitution_right", "Lessor substitution / relocation right", "bool", "Other",
             "Whether the lessor can substitute or relocate the asset/premises", ("substitute", "relocate", "shift"), ind_as_ref="B14–B19"),
]

FIELD_MAP = {f.key: f for f in FIELDS}
GROUPS = ["Parties", "Asset", "Term", "Rent", "Deposit", "Charges", "Options", "Other"]
ESSENTIAL = [f.key for f in FIELDS if f.essential]


def llm_field_list(keys: list[str] | None = None) -> str:
    lines = []
    for f in FIELDS:
        if keys and f.key not in keys:
            continue
        extra = f" One of: {', '.join(f.choices)}." if f.choices else ""
        fmt = {"date": " (YYYY-MM-DD)", "amount": " (number, no commas)", "percent": " (number, e.g. 5 for 5%)",
               "int": " (integer)", "bool": " (true/false)", "number": " (number)"}.get(f.type, "")
        lines.append(f'- "{f.key}": {f.description}{fmt}.{extra}')
    return "\n".join(lines)
