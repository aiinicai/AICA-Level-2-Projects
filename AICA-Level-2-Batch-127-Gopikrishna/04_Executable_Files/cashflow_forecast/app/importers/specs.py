"""Input file specifications - the single source of truth for templates, import and validation.

Each SourceSpec lists its columns with a canonical key, the label used in the template, the
accepted ERP header aliases (matched after normalising case, spaces and punctuation; anything
still unmatched goes to rapidfuzz in Phase 4), the data type and whether it is required.

Natural keys (``key_columns``) identify a row across daily re-uploads, so user overrides survive.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

ColType = Literal["str", "date", "amount", "rate", "int", "bool", "direction", "treatment", "bd_type"]
CategoryMode = Literal["default", "column_or_default", "column_or_header", "none"]


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    type: ColType = "str"
    required: bool = True
    aliases: tuple[str, ...] = ()
    help: str = ""


@dataclass(frozen=True)
class SourceSpec:
    source_type: str                 # matches models.SourceType values
    title: str
    template_file: str
    columns: tuple[Column, ...]
    key_columns: tuple[str, ...]     # natural key; empty -> hash of the row's content
    direction: Literal["inflow", "outflow", "column", "bd_type", "none"]
    category_mode: CategoryMode = "default"
    date_column: str | None = None   # the planned date used to place the row in a lot
    amount_column: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def column(self, key: str) -> Column:
        return next(c for c in self.columns if c.key == key)

    @property
    def required_keys(self) -> list[str]:
        return [c.key for c in self.columns if c.required]


def normalise_header(text: object) -> str:
    """'Outstanding Amt. (OMR)' -> 'outstanding amt omr'."""
    s = re.sub(r"[^0-9a-z]+", " ", str(text or "").lower())
    return re.sub(r"\s+", " ", s).strip()


C = Column
CATEGORY_COL = C("category", "Category", required=False, aliases=("category name", "cash flow category", "cf category"),
                 help="Optional. Overrides the default category for this source.")

SPECS: dict[str, SourceSpec] = {}


def _add(spec: SourceSpec) -> None:
    SPECS[spec.source_type] = spec


_add(SourceSpec(
    "collections", "Customer collections (ERP receivables)", "customer_collections.xlsx",
    columns=(
        C("invoice_no", "Invoice No", aliases=("invoice number", "inv no", "invoice", "document no", "doc no")),
        C("customer", "Customer", aliases=("customer name", "party", "party name", "client")),
        C("project", "Project", required=False, aliases=("project code", "project name", "job", "job no")),
        C("due_date", "Due Date", "date", aliases=("due", "due on", "maturity date", "expected date")),
        C("amount", "Outstanding Amount", "amount",
          aliases=("outstanding", "outstanding amt", "outstanding omr", "balance", "balance due", "amount due",
                   "os amount")),
        CATEGORY_COL,
        C("risk_adjusted", "Risk Adjusted", "bool", required=False, aliases=("risk", "doubtful", "risk flag"),
          help="Y = excluded when the Risk-adjusted scenario is on."),
        C("bill_discounted", "Bill Discounted", "bool", required=False, aliases=("discounted", "bd"),
          help="Y = already financed by the bank; not counted again as a collection."),
    ),
    key_columns=("invoice_no",), direction="inflow", category_mode="column_or_default",
    date_column="due_date", amount_column="amount",
    notes=("One row per open invoice, as exported from the ERP receivables ageing.",
           "Unpaid invoices already past due are placed in the current lot."),
))

_add(SourceSpec(
    "additional", "Additional collections (manual template)", "additional_collections.xlsx",
    columns=(
        C("reference", "Reference", required=False, aliases=("ref", "ref no", "id"),
          help="Recommended: a unique reference keeps your changes when the file is re-uploaded."),
        C("project", "Project", aliases=("project code", "project name", "job")),
        C("customer", "Customer", required=False, aliases=("customer name", "party")),
        C("expected_date", "Expected Date", "date", aliases=("date", "expected on", "receipt date")),
        C("amount", "Amount", "amount", aliases=("expected amount", "amount omr", "value")),
        C("note", "Note", required=False, aliases=("notes", "remarks", "comment", "description")),
        CATEGORY_COL,
    ),
    key_columns=("reference",), direction="inflow", category_mode="column_or_default",
    date_column="expected_date", amount_column="amount",
    notes=("Collections not yet invoiced in the ERP, e.g. advances, retention releases, claims.",),
))

_add(SourceSpec(
    "vendor_pdc", "Vendor PDCs (ERP post-dated cheque register)", "vendor_pdcs.xlsx",
    columns=(
        C("voucher_no", "Voucher No", aliases=("voucher", "voucher number", "pv no", "payment voucher", "doc no")),
        C("vendor", "Vendor", aliases=("vendor name", "supplier", "supplier name", "party", "payee")),
        C("cheque_no", "Cheque No", aliases=("chq no", "cheque number", "check no", "chq number", "instrument no")),
        C("cheque_date", "Cheque Date", "date", aliases=("chq date", "check date", "pdc date", "instrument date")),
        C("amount", "Amount", "amount", aliases=("cheque amount", "chq amount", "amount omr", "value")),
        C("bank", "Bank", required=False, aliases=("bank name", "drawn on", "bank account")),
        CATEGORY_COL,
    ),
    key_columns=("voucher_no", "cheque_no"), direction="outflow", category_mode="column_or_default",
    date_column="cheque_date", amount_column="amount",
    notes=("Issued, uncleared cheques only. Key = Voucher No + Cheque No.",),
))

_add(SourceSpec(
    "allocation", "Vendor payment allocation (ERP payment plan)", "vendor_payment_allocation.xlsx",
    columns=(
        C("vendor", "Vendor", aliases=("vendor name", "supplier", "supplier name", "party")),
        C("invoice", "Invoice", aliases=("invoice no", "vendor invoice", "bill no", "purchase invoice")),
        C("planned_date", "Planned Date", "date", aliases=("payment date", "plan date", "pay on", "date")),
        C("amount", "Amount", "amount", aliases=("planned amount", "allocated amount", "amount omr")),
        CATEGORY_COL,
    ),
    key_columns=("vendor", "invoice"), direction="outflow", category_mode="column_or_default",
    date_column="planned_date", amount_column="amount",
    notes=("Payments planned by transfer (not by PDC). Key = Vendor + Invoice.",),
))

_add(SourceSpec(
    "bill_discount", "Bill discount and LC (bank file)", "bill_discount_lc.xlsx",
    columns=(
        C("reference", "Reference", aliases=("ref", "ref no", "deal no", "lc no", "transaction ref")),
        C("bank", "Bank", aliases=("bank name",)),
        C("bd_type", "Type", "bd_type", aliases=("transaction type", "deal type", "facility type"),
          help="Discount proceeds (inflow), Discount maturity or LC maturity (outflow)."),
        C("maturity_date", "Maturity Date", "date", aliases=("maturity", "value date", "due date", "date")),
        C("amount", "Amount", "amount", aliases=("amount omr", "deal amount", "value")),
        C("invoice_no", "Invoice No", required=False, aliases=("customer invoice", "invoice", "bill no"),
          help="For discount proceeds: the customer invoice financed, so it is not collected twice."),
        CATEGORY_COL,
    ),
    key_columns=("reference",), direction="bd_type", category_mode="column_or_default",
    date_column="maturity_date", amount_column="amount",
))

_add(SourceSpec(
    "other", "Other and recurring items (template)", "other_recurring.xlsx",
    columns=(
        C("reference", "Reference", required=False, aliases=("ref", "id")),
        C("category", "Category", required=False, aliases=("category name", "cash flow category")),
        C("description", "Description", aliases=("details", "narration", "item", "particulars")),
        C("date", "Date", "date", aliases=("due date", "payment date", "expected date")),
        C("amount", "Amount", "amount", required=False, aliases=("amount omr", "value")),
        C("direction", "Inflow/Outflow", "direction", required=False,
          aliases=("direction", "in out", "type", "flow"),
          help="Inflow or Outflow. If blank, the category's direction is used."),
    ),
    key_columns=("reference",), direction="column", category_mode="column_or_header",
    date_column="date", amount_column="amount",
    notes=("Two layouts are accepted:",
           "1) LONG: one row per item with a Category column and an Amount column.",
           "2) WIDE: Date, Description, then one column per category (the header IS the category).",
           "Unknown category names or headers go to the Exceptions screen to be mapped."),
))

_add(SourceSpec(
    "category_list", "Category list (master)", "category_list.xlsx",
    columns=(
        C("name", "Category", aliases=("name", "category name")),
        C("direction", "Inflow/Outflow", "direction", aliases=("direction", "type", "flow")),
        C("summary_group", "Summary Group", aliases=("group", "summary", "report group")),
        C("display_order", "Display Order", "int", aliases=("order", "sort", "sequence", "seq")),
        C("default_treatment", "Default Treatment", "treatment", aliases=("treatment", "fixed deferrable"),
          help="Fixed or Deferrable."),
        C("default_for_source", "Default For Source", required=False, aliases=("source", "default source"),
          help="Optional: one of " + ", ".join(
              ("collections", "additional", "vendor_pdc", "allocation", "bill_discount_in", "bill_discount_out",
               "other_in", "other_out")) + ". Used when a row has no category of its own."),
        C("aliases", "Aliases", required=False, aliases=("alias", "other names"),
          help="Optional: other spellings separated by ';' (e.g. 'Salaries; WPS')."),
    ),
    key_columns=("name",), direction="none", category_mode="none",
))

_add(SourceSpec(
    "payment_history", "Customer payment history (optional, for delay model)", "payment_history.xlsx",
    columns=(
        C("invoice_no", "Invoice No", aliases=("invoice number", "inv no", "invoice")),
        C("customer", "Customer", aliases=("customer name", "party")),
        C("project", "Project", required=False, aliases=("project code",)),
        C("invoice_date", "Invoice Date", "date", required=False, aliases=("inv date", "document date")),
        C("due_date", "Due Date", "date", aliases=("due",)),
        C("paid_date", "Paid Date", "date", aliases=("receipt date", "payment date", "cleared date")),
        C("amount", "Amount", "amount", aliases=("amount omr", "invoice amount", "paid amount")),
    ),
    key_columns=("invoice_no",), direction="none", category_mode="none",
))

_add(SourceSpec(
    "bank_balances", "Bank balances (optional bulk entry; normally typed on screen)", "bank_balances.xlsx",
    columns=(
        C("bank", "Bank", aliases=("bank name",)),
        C("account", "Account", aliases=("account name", "account no")),
        C("currency", "Currency", aliases=("ccy", "cur")),
        C("as_of_date", "As-of Date", "date", aliases=("date", "balance date")),
        C("balance", "Balance", "amount", aliases=("ledger balance", "erp balance", "closing balance")),
        C("fx_rate", "Rate to OMR", "rate", required=False, aliases=("fx rate", "rate", "exchange rate"),
          help="Required for non-OMR accounts; 1 for OMR."),
    ),
    key_columns=("bank", "account", "as_of_date"), direction="none", category_mode="none",
))

_add(SourceSpec(
    "bank_facility", "Bank facility (optional bulk entry; normally typed on screen)", "bank_facility.xlsx",
    columns=(
        C("bank", "Bank", aliases=("bank name",)),
        C("facility_type", "Facility Type", required=False, aliases=("type", "facility")),
        C("as_of_date", "As-of Date", "date", aliases=("date",)),
        C("limit", "Limit", "amount", required=False, aliases=("facility limit", "sanctioned limit")),
        C("utilised", "Utilised", "amount", required=False, aliases=("utilized", "used", "outstanding")),
        C("available", "Available", "amount", aliases=("available amount", "headroom", "undrawn")),
    ),
    key_columns=("bank", "facility_type", "as_of_date"), direction="none", category_mode="none",
))

# sources that create forecast line items (the rest are reference data)
FORECAST_SOURCES = ("collections", "additional", "vendor_pdc", "allocation", "bill_discount", "other")
BD_TYPES = {"discount proceeds": "inflow", "discount maturity": "outflow", "lc maturity": "outflow"}
