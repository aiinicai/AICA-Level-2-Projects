"""
Canonical FinSight field catalog + mapping-suggestion confidence scoring
(Stage 7 requirements #5/#6/#8).

Every target field name below is copied verbatim from an already
*approved* model column — `app/models/transactions.py` for the
ledger-style file types, `app/models/structured_datasets.py` for
Fixed Assets / GST / TDS — nothing here invents a new canonical field
or a new table. This module only decides which source column is likely
to correspond to which of those existing fields, and with how much
confidence; it never writes anything (see
`app/services/mapping_service.py` for persistence).

Deliberately NOT an Accounting/Audit/Tax/SEBI rule engine: everything
below is lexical (comparing column-header text to a list of known
synonyms) — it has no opinion on debits vs. credits balancing, tax
treatment, or any other analytical judgment. That is out of Stage 7's
approved scope.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize_label(text: str) -> str:
    return _NORMALIZE_RE.sub(" ", (text or "").strip().lower()).strip()


# target_field -> (display_label, [synonym phrases])
CANONICAL_FIELDS: dict[str, tuple[str, list[str]]] = {
    # Transaction (app/models/transactions.py) — used by TB/GL/JE/SALES/
    # PURCHASE/BANK/AR/AP/PRIOR_YEAR/OTHER.
    "transaction_date": ("Transaction Date", [
        "date", "txn date", "transaction date", "entry date", "voucher date",
        "value date", "posting date", "trans date",
    ]),
    "account_name": ("Account Name", [
        "account", "account name", "ledger", "ledger name", "gl account",
        "particulars", "head of account", "account head", "nominal account",
    ]),
    "party_name": ("Party Name", [
        "party", "party name", "customer", "customer name", "vendor",
        "vendor name", "supplier", "supplier name", "debtor", "creditor",
    ]),
    "description": ("Description / Narration", [
        "narration", "description", "particulars", "remarks", "details", "memo",
    ]),
    "debit_amount": ("Debit Amount", [
        "debit", "dr", "debit amount", "debit rs", "dr amount", "withdrawal",
    ]),
    "credit_amount": ("Credit Amount", [
        "credit", "cr", "credit amount", "credit rs", "cr amount", "deposit",
    ]),
    "reference_number": ("Reference Number", [
        "reference", "reference no", "ref no", "voucher no", "voucher number",
        "invoice no", "cheque no", "doc no", "document number", "bill no",
    ]),
    "payment_mode": ("Payment Mode", [
        "mode", "payment mode", "mode of payment", "payment type",
    ]),
    "is_manual_entry": ("Manual Entry Flag", ["manual entry", "is manual", "manual je"]),

    # FixedAsset (app/models/structured_datasets.py)
    "asset_description": ("Asset Description", ["asset", "asset description", "asset name", "description"]),
    "asset_class": ("Asset Class", ["asset class", "category", "block", "asset category"]),
    "date_put_to_use": ("Date Put to Use", [
        "date put to use", "put to use date", "capitalisation date", "capitalization date",
    ]),
    "original_cost_paise": ("Original Cost", ["original cost", "gross block", "cost", "purchase cost"]),
    "opening_wdv_paise": ("Opening WDV", ["opening wdv", "opening w d v", "wdv opening", "opening w.d.v."]),
    "additions_paise": ("Additions", ["additions", "addition"]),
    "deletions_paise": ("Deletions", ["deletions", "deletion", "disposal", "disposals"]),
    "book_depreciation_rate": ("Book Depreciation Rate", ["depreciation rate", "book dep rate", "rate of depreciation"]),
    "book_depreciation_amount_paise": ("Book Depreciation Amount", ["depreciation amount", "book depreciation", "dep amount"]),
    "tax_block_of_asset": ("Tax Block of Asset", ["block of assets", "tax block", "income tax block"]),
    "tax_depreciation_rate": ("Tax Depreciation Rate", ["tax depreciation rate", "it act rate", "income tax rate"]),
    "closing_wdv_paise": ("Closing WDV", ["closing wdv", "wdv closing", "closing w.d.v."]),

    # GstLineItem
    "gstin": ("GSTIN", ["gstin", "gst no", "gst number"]),
    "invoice_number": ("Invoice Number", ["invoice no", "invoice number", "bill no", "bill number"]),
    "invoice_date": ("Invoice Date", ["invoice date", "bill date"]),
    "taxable_value_paise": ("Taxable Value", ["taxable value", "taxable amount", "assessable value"]),
    "cgst_paise": ("CGST", ["cgst", "cgst amount"]),
    "sgst_paise": ("SGST", ["sgst", "sgst amount"]),
    "igst_paise": ("IGST", ["igst", "igst amount"]),
    "tax_rate": ("Tax Rate", ["tax rate", "gst rate", "rate", "rate of tax"]),

    # TdsLineItem
    "section_code": ("TDS Section", ["section", "section code", "tds section"]),
    "deductee_pan": ("Deductee PAN", ["pan", "deductee pan", "pan no", "pan number"]),
    "rate_applied": ("TDS Rate Applied", ["rate applied", "tds rate", "rate of tds"]),
    "amount_deducted_paise": ("Amount Deducted", ["tds amount", "amount deducted", "tax deducted", "tds"]),
    "challan_number": ("Challan Number", ["challan no", "challan number"]),
    "deposit_date": ("Deposit Date", ["deposit date", "date of deposit", "challan date"]),
}

# file_type -> ordered list of target_field names it's reasonable to
# suggest for that file type. A field can legitimately appear under
# more than one file type (e.g. SALES/PURCHASE registers commonly carry
# GST columns alongside ledger-style ones).
FILE_TYPE_FIELD_SETS: dict[str, list[str]] = {
    "TB": ["account_name", "debit_amount", "credit_amount", "reference_number", "description"],
    "GL": ["transaction_date", "account_name", "description", "debit_amount", "credit_amount",
           "reference_number", "payment_mode", "party_name"],
    "JE": ["transaction_date", "account_name", "description", "debit_amount", "credit_amount",
           "reference_number", "is_manual_entry"],
    "SALES": ["transaction_date", "party_name", "description", "debit_amount", "credit_amount",
              "reference_number", "gstin", "invoice_number", "invoice_date",
              "taxable_value_paise", "cgst_paise", "sgst_paise", "igst_paise", "tax_rate"],
    "PURCHASE": ["transaction_date", "party_name", "description", "debit_amount", "credit_amount",
                 "reference_number", "gstin", "invoice_number", "invoice_date",
                 "taxable_value_paise", "cgst_paise", "sgst_paise", "igst_paise", "tax_rate"],
    "BANK": ["transaction_date", "description", "debit_amount", "credit_amount",
             "reference_number", "payment_mode"],
    "AR": ["party_name", "transaction_date", "debit_amount", "credit_amount", "reference_number", "description"],
    "AP": ["party_name", "transaction_date", "debit_amount", "credit_amount", "reference_number", "description"],
    "FIXED_ASSETS": ["asset_description", "asset_class", "date_put_to_use", "original_cost_paise",
                      "opening_wdv_paise", "additions_paise", "deletions_paise",
                      "book_depreciation_rate", "book_depreciation_amount_paise",
                      "tax_block_of_asset", "tax_depreciation_rate", "closing_wdv_paise"],
    "GST": ["gstin", "invoice_number", "invoice_date", "taxable_value_paise",
            "cgst_paise", "sgst_paise", "igst_paise", "tax_rate"],
    "TDS": ["section_code", "deductee_pan", "rate_applied", "amount_deducted_paise",
            "challan_number", "deposit_date"],
    "PRIOR_YEAR": ["transaction_date", "account_name", "description", "debit_amount",
                   "credit_amount", "reference_number"],
    "OTHER": ["transaction_date", "account_name", "party_name", "description",
              "debit_amount", "credit_amount", "reference_number"],
}

SUGGESTION_THRESHOLD = 0.35


@dataclass
class MappingSuggestion:
    column_key: str
    target_field: str | None
    target_label: str | None
    confidence: float | None  # 0-1, None when target_field is None


def field_score(source_label: str, target_field: str) -> float:
    """Best similarity between `source_label` and the target field's own
    name or any of its known synonyms. 1.0 = exact match after
    normalization, 0.75 = one contains the other, otherwise a
    difflib-ratio fuzzy score scaled down so it never outranks a real
    substring/exact match."""
    display_label, synonyms = CANONICAL_FIELDS[target_field]
    norm_source = normalize_label(source_label)
    if not norm_source:
        return 0.0

    candidates = [normalize_label(target_field.replace("_", " ")), normalize_label(display_label)]
    candidates.extend(normalize_label(s) for s in synonyms)

    best = 0.0
    for candidate in candidates:
        if not candidate:
            continue
        if norm_source == candidate:
            best = max(best, 1.0)
        elif norm_source in candidate or candidate in norm_source:
            best = max(best, 0.75)
        else:
            ratio = difflib.SequenceMatcher(None, norm_source, candidate).ratio()
            best = max(best, ratio * 0.7)
    return round(best, 3)


def suggest_mappings(column_labels: list[str], file_type: str) -> list[MappingSuggestion]:
    """One suggestion per source column, in the same order as
    `column_labels`. Assignment is greedy and exclusive: the single
    best-scoring (column, field) pair across the whole file is locked
    in first, then the next best among what's left, and so on — so two
    columns are not both suggested for the same target field. A column
    with no candidate scoring at or above `SUGGESTION_THRESHOLD` is left
    unmapped (target_field=None) rather than guessed."""
    candidate_fields = FILE_TYPE_FIELD_SETS.get(file_type, [])

    scored: list[tuple[float, int, str]] = []
    for idx, label in enumerate(column_labels):
        for target_field in candidate_fields:
            score = field_score(label, target_field)
            if score >= SUGGESTION_THRESHOLD:
                scored.append((score, idx, target_field))
    scored.sort(key=lambda t: t[0], reverse=True)

    assigned_field_to_column: dict[str, int] = {}
    assigned_column_to_field: dict[int, tuple[str, float]] = {}
    for score, idx, target_field in scored:
        if idx in assigned_column_to_field or target_field in assigned_field_to_column:
            continue
        assigned_column_to_field[idx] = (target_field, score)
        assigned_field_to_column[target_field] = idx

    results = []
    for idx, label in enumerate(column_labels):
        if idx in assigned_column_to_field:
            target_field, score = assigned_column_to_field[idx]
            results.append(MappingSuggestion(
                column_key=label, target_field=target_field,
                target_label=CANONICAL_FIELDS[target_field][0], confidence=score,
            ))
        else:
            results.append(MappingSuggestion(column_key=label, target_field=None, target_label=None, confidence=None))
    return results


def file_type_signature_scores(column_labels: list[str]) -> dict[str, float]:
    """For every known file type, the average of each column's best
    score against that file type's field vocabulary (non-exclusive —
    unlike suggest_mappings, this is only measuring "how well does this
    vocabulary fit," not proposing an actual mapping). Used to flag a
    likely wrong file-type selection (Stage 7 requirement #8)."""
    scores: dict[str, float] = {}
    for file_type, fields in FILE_TYPE_FIELD_SETS.items():
        if not column_labels or not fields:
            scores[file_type] = 0.0
            continue
        per_column_best = [max((field_score(label, f) for f in fields), default=0.0) for label in column_labels]
        scores[file_type] = round(sum(per_column_best) / len(per_column_best), 3)
    return scores


def detect_file_type_mismatch(column_labels: list[str], selected_file_type: str) -> str | None:
    """None when the selected file type is a reasonable-enough fit, or
    is at least as good a fit as any other file type. A warning string
    otherwise — this never blocks anything by itself; the mapping
    screen is what turns it into a required-review gate."""
    scores = file_type_signature_scores(column_labels)
    selected_score = scores.get(selected_file_type, 0.0)

    best_other_type, best_other_score = None, 0.0
    for file_type, score in scores.items():
        if file_type == selected_file_type:
            continue
        if score > best_other_score:
            best_other_type, best_other_score = file_type, score

    if best_other_type and best_other_score >= 0.45 and (best_other_score - selected_score) >= 0.15:
        from app.upload.validation import FILE_TYPE_LABELS
        selected_label = FILE_TYPE_LABELS.get(selected_file_type, selected_file_type)
        other_label = FILE_TYPE_LABELS.get(best_other_type, best_other_type)
        return (
            f"These columns look more like {other_label} data than {selected_label}. "
            f"Please review the selected file type before confirming any mappings."
        )
    return None


# Stage 7 correction #1: the automatic suggestion engine (suggest_mappings,
# above) already assigns each target field to at most one source column —
# but a user can still manually pick the same target field for two
# different columns in the mapping form. That must be rejected
# server-side, not merely discouraged client-side.
def find_duplicate_target_assignments(selection: dict[str, str]) -> dict[str, list[str]]:
    """`selection` maps column_key -> chosen target_field (blank/absent
    entries mean "skip", already excluded by the caller). Returns
    target_field -> the list of column_keys that were both assigned to
    it, for every target_field claimed by more than one column. Empty
    dict means no duplicates. No target field is currently designated
    "repeatable" — see the module-level CANONICAL_FIELDS catalog if that
    ever needs to change; until then, every field is one-source-column-
    only, for every file type."""
    by_target: dict[str, list[str]] = {}
    for column_key, target_field in selection.items():
        if not target_field:
            continue
        by_target.setdefault(target_field, []).append(column_key)
    return {field: columns for field, columns in by_target.items() if len(columns) > 1}
