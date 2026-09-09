import datetime
from decimal import Decimal
import re
from typing import List, Optional

from reconai.models.transaction import (
    LedgerEntry,
    AuditFlag,
    AuditSeverity,
    AuditCategory,
    TransactionType,
)
from reconai.config import AuditConfig

# Regex for standard 15-character Indian GSTIN
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


class AuditRulesEngine:
    """Deterministic Compliance and Anomaly Audit Rules Engine."""

    def __init__(self, config: Optional[AuditConfig] = None):
        self.config = config or AuditConfig()

    def audit(self, entries: List[LedgerEntry]) -> List[AuditFlag]:
        flags: List[AuditFlag] = []

        # 1. Duplicate Detection Pass
        flags.extend(self._check_duplicates(entries))

        # 2. Per-entry Deterministic Rule Checks
        for entry in entries:
            # Check Round Number Expense
            flag = self._check_round_amount(entry)
            if flag:
                flags.append(flag)

            # Check Weekend Entry
            if self.config.flag_weekend_transactions:
                flag = self._check_weekend(entry)
                if flag:
                    flags.append(flag)

            # Check High Value Missing Approval
            flag = self._check_approval_missing(entry)
            if flag:
                flags.append(flag)

            # Check Approved Vendor List
            if self.config.approved_vendors:
                flag = self._check_approved_vendor(entry)
                if flag:
                    flags.append(flag)

            # Check India GSTIN / TDS Compliance
            if self.config.enable_gst_tds_compliance:
                gst_flags = self._check_gst_tds(entry)
                flags.extend(gst_flags)

        return flags

    def _check_duplicates(self, entries: List[LedgerEntry]) -> List[AuditFlag]:
        """Detect true duplicate payments for the same vendor/party within the configured window."""
        from collections import defaultdict

        def normalize_party(desc: str) -> str:
            d = re.sub(r"^(to|by)\s+", "", str(desc).strip(), flags=re.IGNORECASE)
            d = re.sub(r"[^a-zA-Z0-9\s]", " ", d)
            tokens = [t for t in d.lower().split() if len(t) > 2 and t not in ["chq", "neft", "rtgs", "imps", "upi", "pvt", "ltd"]]
            return " ".join(tokens[:3])

        # Group by transaction type, exact amount, and normalized party
        grouped = defaultdict(list)
        for e in entries:
            party = normalize_party(e.description or e.account_name or "")
            if party and len(party) >= 3:
                grouped[(e.type, e.amount, party)].append(e)

        flags: List[AuditFlag] = []
        for (tx_type, amt, party), sub_entries in grouped.items():
            if len(sub_entries) > 1:
                sub_entries.sort(key=lambda x: x.date)
                for i in range(1, len(sub_entries)):
                    e_prev = sub_entries[i - 1]
                    e_curr = sub_entries[i]
                    days_diff = abs((e_curr.date - e_prev.date).days)
                    if days_diff <= self.config.duplicate_date_window_days:
                        sev = AuditSeverity.HIGH if tx_type == TransactionType.DEBIT else AuditSeverity.LOW
                        flags.append(
                            AuditFlag(
                                target_type="LEDGER",
                                source_row_ref=e_curr.source_row_ref,
                                entry_id=e_curr.id,
                                rule_name="POTENTIAL_DUPLICATE_ENTRY",
                                severity=sev,
                                category=AuditCategory.DUPLICATE,
                                plain_english_reason=(
                                    f"Potential duplicate {'payment' if tx_type == TransactionType.DEBIT else 'receipt'} of ₹{e_curr.amount:,.2f} for '{party.upper()}'. "
                                    f"Matches voucher {e_prev.source_row_ref} dated {e_prev.date.strftime('%d-%b-%Y')} "
                                    f"('{e_prev.description[:35]}') with timing difference of {days_diff} day(s)."
                                ),
                                suggested_action="Verify physical invoices and payment advice to confirm transaction was not booked or paid twice.",
                                entry_summary={
                                    "voucher": str(e_curr.source_row_ref),
                                    "date": str(e_curr.date),
                                    "amount": str(e_curr.amount),
                                    "party": party,
                                    "conflicting_voucher": str(e_prev.source_row_ref),
                                },
                            )
                        )
        return flags

    def _check_round_amount(self, entry: LedgerEntry) -> Optional[AuditFlag]:
        if entry.type == TransactionType.DEBIT and entry.amount >= self.config.round_amount_threshold:
            # Check if perfectly divisible by 10,000 or 5,000 or 1,000
            if entry.amount % Decimal("1000.00") == Decimal("0.00"):
                return AuditFlag(
                    target_type="LEDGER",
                    source_row_ref=entry.source_row_ref,
                    entry_id=entry.id,
                    rule_name="HIGH_ROUND_NUMBER_EXPENSE",
                    severity=AuditSeverity.MEDIUM,
                    category=AuditCategory.ROUND_AMOUNT,
                    plain_english_reason=(
                        f"Round-figure expense of ₹{entry.amount:,.2f} on '{entry.description}'. "
                        f"Round numbers above ₹{self.config.round_amount_threshold:,.2f} often indicate ad-hoc cash withdrawals, unbilled advances, or non-contractual settlements."
                    ),
                    suggested_action="Review underlying itemized invoice or cash settlement vouchers.",
                    entry_summary={"voucher": str(entry.source_row_ref), "amount": str(entry.amount)},
                )
        return None

    def _check_weekend(self, entry: LedgerEntry) -> Optional[AuditFlag]:
        # Monday is 0 and Sunday is 6
        if entry.date.weekday() in (5, 6):
            day_name = "Saturday" if entry.date.weekday() == 5 else "Sunday"
            return AuditFlag(
                target_type="LEDGER",
                source_row_ref=entry.source_row_ref,
                entry_id=entry.id,
                rule_name="WEEKEND_DATED_TRANSACTION",
                severity=AuditSeverity.LOW,
                category=AuditCategory.WEEKEND_HOLIDAY,
                plain_english_reason=(
                    f"Entry dated on {day_name} ({entry.date.strftime('%d-%b-%Y')}) for ₹{entry.amount:,.2f}. "
                    f"Unless authorized under shift operations, weekend postings warrant verification of posting cutoffs."
                ),
                suggested_action="Confirm if weekend posting aligns with actual banking / expense authorization date.",
                entry_summary={"voucher": str(entry.source_row_ref), "weekday": day_name},
            )
        return None

    def _check_approval_missing(self, entry: LedgerEntry) -> Optional[AuditFlag]:
        if entry.type == TransactionType.DEBIT and entry.amount >= self.config.high_value_approval_threshold:
            if not entry.approver_ref or str(entry.approver_ref).strip() == "" or str(entry.approver_ref).lower() == "nan":
                return AuditFlag(
                    target_type="LEDGER",
                    source_row_ref=entry.source_row_ref,
                    entry_id=entry.id,
                    rule_name="MISSING_MANAGEMENT_APPROVAL",
                    severity=AuditSeverity.HIGH,
                    category=AuditCategory.APPROVAL_MISSING,
                    plain_english_reason=(
                        f"High-value payment of ₹{entry.amount:,.2f} exceeds approval threshold "
                        f"(₹{self.config.high_value_approval_threshold:,.2f}) without documented authorizer/approver reference."
                    ),
                    suggested_action="Verify signing authority and obtain formal management approval document.",
                    entry_summary={"voucher": str(entry.source_row_ref), "amount": str(entry.amount)},
                )
        return None

    def _check_approved_vendor(self, entry: LedgerEntry) -> Optional[AuditFlag]:
        vendor_name = (entry.account_name or entry.description).strip().lower()
        approved_lower = [v.lower() for v in self.config.approved_vendors]
        if not any(v in vendor_name for v in approved_lower):
            return AuditFlag(
                target_type="LEDGER",
                source_row_ref=entry.source_row_ref,
                entry_id=entry.id,
                rule_name="UNAPPROVED_VENDOR",
                severity=AuditSeverity.MEDIUM,
                category=AuditCategory.GENERAL,
                plain_english_reason=(
                    f"Vendor/Party '{entry.account_name or entry.description}' is not in the approved vendor master list."
                ),
                suggested_action="Check vendor onboarding documentation and KYC records.",
                entry_summary={"voucher": str(entry.source_row_ref), "party": entry.account_name},
            )
        return None

    def _check_gst_tds(self, entry: LedgerEntry) -> List[AuditFlag]:
        flags: List[AuditFlag] = []

        # Validate GSTIN format if provided
        if entry.gstin and str(entry.gstin).strip() and str(entry.gstin).lower() != "nan":
            gstin_clean = str(entry.gstin).strip().upper()
            if not GSTIN_REGEX.match(gstin_clean):
                flags.append(
                    AuditFlag(
                        target_type="LEDGER",
                        source_row_ref=entry.source_row_ref,
                        entry_id=entry.id,
                        rule_name="INVALID_GSTIN_FORMAT",
                        severity=AuditSeverity.HIGH,
                        category=AuditCategory.GST_TDS_COMPLIANCE,
                        plain_english_reason=(
                            f"GSTIN '{entry.gstin}' on voucher {entry.source_row_ref} does not match statutory 15-digit GST format (2 digits state + PAN + entity + Z + check digit)."
                        ),
                        suggested_action="Correct GSTIN in vendor master to avoid loss of Input Tax Credit (ITC).",
                        entry_summary={"voucher": str(entry.source_row_ref), "gstin": entry.gstin},
                    )
                )

        # Check TDS Section for contractual/professional services above statutory threshold (e.g. ₹30,000)
        desc_lower = entry.description.lower()
        is_service_or_contract = any(
            k in desc_lower
            for k in ["consult", "fee", "retainer", "contract", "license", "legal", "audit", "developer", "service"]
        )
        if is_service_or_contract and entry.amount >= Decimal("30000.00") and entry.type == TransactionType.DEBIT:
            if not entry.tds_section or str(entry.tds_section).strip() == "" or str(entry.tds_section).lower() == "nan":
                flags.append(
                    AuditFlag(
                        target_type="LEDGER",
                        source_row_ref=entry.source_row_ref,
                        entry_id=entry.id,
                        rule_name="POTENTIAL_TDS_NON_DEDUCTION",
                        severity=AuditSeverity.HIGH,
                        category=AuditCategory.GST_TDS_COMPLIANCE,
                        plain_english_reason=(
                            f"Professional/contractual expense of ₹{entry.amount:,.2f} on '{entry.description}' "
                            f"has no TDS Section (e.g., 194C / 194J) specified. Failure to deduct TDS may attract Section 40(a)(ia) disallowance."
                        ),
                        suggested_action="Check if TDS was deducted at source or lower deduction certificate is on file.",
                        entry_summary={"voucher": str(entry.source_row_ref), "amount": str(entry.amount)},
                    )
                )

        return flags
