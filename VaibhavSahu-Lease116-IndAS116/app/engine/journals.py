"""Journal engine — GL role catalogue, resolution and validation.

The accounting engine emits postings against *roles* (e.g. ROU_ASSET); roles are
resolved to GL accounts by the service layer using configurable mappings (entity,
asset class, cost centre, lease type). Debits must equal credits for every journal.
"""
from __future__ import annotations

from collections import OrderedDict, defaultdict
from decimal import Decimal
from typing import Callable

from .decimal_utils import ZERO
from .models import Posting

# role: (default code, default account name, nature)
ROLE_CATALOG: "OrderedDict[str, tuple[str, str, str]]" = OrderedDict([
    ("ROU_ASSET", ("13010", "Right-of-use assets — gross carrying amount", "Asset")),
    ("ROU_ACC_DEP", ("13020", "Accumulated depreciation — right-of-use assets", "Asset (contra)")),
    ("ROU_ACC_IMP", ("13030", "Accumulated impairment — right-of-use assets", "Asset (contra)")),
    ("LEASE_LIABILITY", ("23010", "Lease liabilities", "Liability")),
    ("LESSOR_PAYABLE", ("21010", "Trade payables — lessors", "Liability")),
    ("BANK", ("11010", "Bank", "Asset")),
    ("PREPAID_LEASE_PAYMENTS", ("14010", "Advance / prepaid lease payments", "Asset")),
    ("IDC_CLEARING", ("21020", "Initial direct costs — payable / clearing", "Liability")),
    ("LEASE_INCENTIVE_RECEIVED", ("14020", "Lease incentives receivable / received", "Asset")),
    ("RESTORATION_PROVISION", ("24010", "Provision for restoration / dismantling", "Liability")),
    ("SECURITY_DEPOSIT", ("15010", "Security deposits (financial asset at amortised cost)", "Asset")),
    ("INTEREST_INCOME_DEPOSIT", ("42010", "Interest income — unwinding of security deposits", "Income")),
    ("FINANCE_COST_LEASE", ("52010", "Finance costs — interest on lease liabilities", "Expense")),
    ("FINANCE_COST_PROVISION", ("52020", "Finance costs — unwinding of discount on provisions", "Expense")),
    ("DEPRECIATION_ROU", ("53010", "Depreciation — right-of-use assets", "Expense")),
    ("VARIABLE_LEASE_EXPENSE", ("54010", "Rent — variable lease payments", "Expense")),
    ("NON_LEASE_EXPENSE", ("54020", "Maintenance / service charges (non-lease components)", "Expense")),
    ("SHORT_TERM_LEASE_EXPENSE", ("54030", "Rent — short-term leases", "Expense")),
    ("LOW_VALUE_LEASE_EXPENSE", ("54040", "Rent — leases of low-value assets", "Expense")),
    ("ACCRUED_RENT", ("21030", "Accrued rent — exempt leases", "Liability")),
    ("GAIN_LOSS_MODIFICATION", ("43010", "Gain / (loss) on lease modification", "Income / Expense")),
    ("GAIN_LOSS_TERMINATION", ("43020", "Gain / (loss) on termination of leases", "Income / Expense")),
    ("GAIN_REMEASUREMENT", ("43030", "Gain on remeasurement of lease liability (ROU at nil)", "Income")),
    ("IMPAIRMENT_LOSS_ROU", ("55010", "Impairment loss — right-of-use assets", "Expense")),
    ("IMPAIRMENT_REVERSAL_ROU", ("43040", "Reversal of impairment — right-of-use assets", "Income")),
    ("FX_LOSS_GAIN", ("56010", "Exchange differences (net) — lease balances", "Income / Expense")),
    ("RESTORATION_REVISION_PL", ("56020", "Restoration provision — change in estimate", "Income / Expense")),
    ("OTHER_ROU_ADJUSTMENT", ("21990", "ROU adjustment clearing", "Liability")),
    ("NET_INVESTMENT_LEASE", ("16010", "Net investment in finance leases", "Asset")),
    ("FINANCE_INCOME_LESSOR", ("41010", "Finance income on net investment in leases", "Income")),
    ("OPERATING_LEASE_INCOME", ("41020", "Operating lease income", "Income")),
    ("ACCRUED_LEASE_INCOME", ("16020", "Accrued operating lease income (straight-lining)", "Asset")),
    ("LESSEE_RECEIVABLE", ("16030", "Trade receivables — lessees", "Asset")),
    ("LEASED_ASSET_DERECOGNISED", ("12010", "Property, plant and equipment (leased out)", "Asset")),
    ("SELLING_PROFIT_LESSOR", ("41030", "Selling profit / (loss) on finance leases", "Income / Expense")),
    ("VARIABLE_LEASE_INCOME", ("41040", "Lease income — variable payments not depending on an index or rate", "Income")),
    ("NON_LEASE_REVENUE", ("41050", "Revenue — non-lease components (services / CAM) — Ind AS 115", "Income")),
    ("LESSOR_SALES_REVENUE", ("41060", "Revenue — manufacturer / dealer finance leases", "Income")),
    ("LESSOR_COST_OF_SALES", ("51010", "Cost of sales — manufacturer / dealer finance leases", "Expense")),
    ("UNDERLYING_ASSET_RECOGNISED", ("12030", "Property, plant and equipment — assets returned / reclassified from finance leases", "Asset")),
    ("SECURITY_DEPOSIT_RECEIVED", ("22010", "Security deposits received from lessees (financial liability at amortised cost)", "Liability")),
    ("FINANCE_COST_DEPOSIT_RECEIVED", ("52030", "Finance costs — unwinding of security deposits received", "Expense")),
    ("LESSOR_IDC_ASSET", ("12040", "Initial direct costs — operating leases (added to the underlying asset)", "Asset")),
    ("LESSOR_IDC_EXPENSE", ("54050", "Initial direct costs — lessor (amortisation / expense)", "Expense")),
    ("GAIN_LOSS_MODIFICATION_LESSOR", ("43070", "Gain / (loss) on modification of finance lease receivables", "Income / Expense")),
    ("GAIN_LOSS_TERMINATION_LESSOR", ("43080", "Gain / (loss) on early termination of leases — lessor", "Income / Expense")),
    ("GAIN_DERECOGNITION_LESSOR", ("43090", "Gain / (loss) on derecognition of assets let out under finance leases", "Income / Expense")),
    ("UGR_REDUCTION_LOSS", ("55020", "Loss on reduction of unguaranteed residual value", "Expense")),
    ("ECL_LEASE_RECEIVABLES", ("55030", "Impairment loss (expected credit losses) — lease receivables", "Expense")),
    ("LOSS_ALLOWANCE_LEASE_RECEIVABLES", ("16050", "Loss allowance — lease receivables", "Asset (contra)")),
    ("NET_INVESTMENT_SUBLEASE", ("16040", "Net investment in subleases", "Asset")),
    ("ROU_ASSET_SUBLEASED", ("13010", "Right-of-use assets — gross carrying amount (subleased portion)", "Asset")),
    ("GAIN_LOSS_SUBLEASE", ("43050", "Gain / (loss) on sublease", "Income / Expense")),
    ("ASSET_SOLD", ("12020", "Property, plant and equipment (sold under sale and leaseback)", "Asset")),
    ("SLB_FINANCIAL_LIABILITY", ("23020", "Lease liability / financial liability — sale and leaseback", "Liability")),
    ("GAIN_SLB_RIGHTS_TRANSFERRED", ("43060", "Gain on sale and leaseback — rights transferred", "Income")),
    ("DEFERRED_TAX_ASSET", ("17010", "Deferred tax assets", "Asset")),
    ("DEFERRED_TAX_LIABILITY", ("25010", "Deferred tax liabilities", "Liability")),
    ("DEFERRED_TAX_EXPENSE", ("57010", "Deferred tax expense / (credit)", "Expense")),
])

EVENT_LABELS = {
    "COMMENCEMENT": "Commencement", "PREPAYMENT": "Prepaid lease payments", "INCENTIVE": "Lease incentives",
    "IDC": "Initial direct costs", "RESTORATION": "Restoration obligation", "DEPOSIT_FV": "Deposit fair value",
    "DEPOSIT_PAID": "Deposit paid", "DEPOSIT_REFUND": "Deposit refund", "DEPOSIT_CATCHUP": "Deposit catch-up",
    "INTEREST": "Interest", "PAYMENT": "Lease payments", "DEPRECIATION": "Depreciation", "VARIABLE": "Variable payments",
    "NON_LEASE": "Non-lease components", "UNWINDING": "Provision unwinding", "DEPOSIT_INTEREST": "Deposit interest",
    "FX": "Exchange difference", "MODIFICATION": "Modification", "PARTIAL_TERMINATION": "Partial termination",
    "REASSESSMENT": "Reassessment", "TERMINATION": "Termination", "IMPAIRMENT": "Impairment",
    "IMPAIRMENT_REVERSAL": "Impairment reversal", "RESTORATION_REVISION": "Restoration revision",
    "RESTORATION_SETTLED": "Restoration settled", "ROU_ADJUSTMENT": "ROU adjustment",
    "EXEMPT_EXPENSE": "Exempt lease expense", "LESSOR_COMMENCEMENT": "Lessor commencement",
    "FINANCE_INCOME": "Finance income", "LESSOR_RECEIPT": "Lessor receipts", "OPERATING_LEASE_INCOME": "Operating lease income",
    "SUBLEASE_COMMENCEMENT": "Sublease commencement", "SLB_COMMENCEMENT": "Sale and leaseback", "SLB_FAILED_SALE": "Failed sale",
    "DEFERRED_TAX": "Deferred tax", "LESSOR_IDC": "Initial direct costs (lessor)", "LESSOR_IDC_AMORTISATION": "IDC amortisation",
    "DEPOSIT_RECEIVED": "Deposit received", "DEPOSIT_UNWINDING": "Deposit unwinding", "RESIDUAL_RETURNED": "Residual asset returned",
    "VARIABLE_LEASE_INCOME": "Variable lease income", "NON_LEASE_REVENUE": "Non-lease revenue", "LESSOR_MODIFICATION": "Lessor modification",
    "FL_TO_OL_RECLASS": "Reclassified to operating", "LESSOR_TERMINATION": "Lessor termination", "UGR_REVISION": "Residual value revision",
    "ECL": "Expected credit loss",
}


def default_resolver(role: str) -> tuple[str, str]:
    code, name, _ = ROLE_CATALOG.get(role, ("99999", role.replace("_", " ").title(), ""))
    return code, name


def validate_postings(postings: list[Posting]) -> list[str]:
    errors = []
    for p in postings:
        dr = sum((l[1] for l in p.lines), ZERO)
        cr = sum((l[2] for l in p.lines), ZERO)
        if dr != cr:
            errors.append(f"{p.date} {p.event}: debits {dr} ≠ credits {cr}")
    return errors


def to_journal_lines(postings: list[Posting], resolver: Callable[[str], tuple[str, str]] = default_resolver) -> list[dict]:
    out = []
    for n, p in enumerate(postings, start=1):
        for i, (role, dr, cr) in enumerate(p.lines, start=1):
            code, name = resolver(role)
            out.append({"je_no": n, "line": i, "date": p.date, "period_end": p.period_end or p.date, "event": p.event,
                        "narration": p.narration, "role": role, "account_code": code, "account_name": name,
                        "debit": dr, "credit": cr, "ref": p.ref})
    return out


def trial_balance_effect(postings: list[Posting]) -> dict[str, Decimal]:
    tb: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for p in postings:
        for role, dr, cr in p.lines:
            tb[role] += dr - cr
    return dict(tb)
