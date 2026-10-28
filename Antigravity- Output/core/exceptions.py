"""
Exceptions, Reason Codes, and Claim Drafting for MarketMatch.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any


class MarketMatchError(Exception):
    """Base exception for MarketMatch application errors."""
    pass


class ProfileError(MarketMatchError):
    """Raised when profile configuration is invalid or missing."""
    pass


class ParsingError(MarketMatchError):
    """Raised when file parsing fails or required columns are missing."""
    pass


class ValidationError(MarketMatchError):
    """Raised when business validation rules fail."""
    pass


class ReconciliationError(MarketMatchError):
    """Raised during reconciliation logic failures."""
    pass


# Canonical Reason Codes as specified in requirements:
REASON_CODES = [
    "Fees",
    "Returns/Refunds",
    "Timing/Cut-off",
    "TCS/TDS",
    "Duplicate",
    "Missing payout",
    "Missing in GST",
    "Rate/Value mismatch",
    "Place-of-supply",
    "Rounding",
    "Unexplained"
]

EXCEPTION_STATUSES = ["Open", "Claimed", "Recovered"]


@dataclass
class ExceptionRecord:
    id: str
    order_id: str
    invoice_no: str
    reason_code: str
    description: str
    recoverable_amount: Decimal
    status: str = "Open"
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    source_ref: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "invoice_no": self.invoice_no,
            "reason_code": self.reason_code,
            "description": self.description,
            "recoverable_amount": float(self.recoverable_amount),
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_ref": self.source_ref
        }


def generate_claim_email(
    seller_name: str,
    seller_gstin: str,
    order_id: str,
    invoice_no: str,
    reason_code: str,
    claim_amount: Decimal,
    details: str = "",
    as_of: Optional[str] = None
) -> str:
    """
    Generate a formatted seller support claim email template.
    Uses a standard fixed professional format for Amazon Seller Support.
    """
    date_str = as_of or datetime.now().strftime("%d-%m-%Y")
    formatted_amount = f"INR {claim_amount:,.2f}"

    subject = f"[Discrepancy Claim] Amazon Seller Dispute: Order #{order_id} - {reason_code} - Claim Amount: {formatted_amount}"
    
    body = f"""Subject: {subject}

Date: {date_str}
To: Amazon Seller Support / Payments & Discrepancies Team

Dear Amazon Seller Support Team,

I am writing regarding a financial discrepancy identified in our marketplace reconciliation for Order #{order_id}.

Merchant Details:
- Seller Name: {seller_name or 'Registered Merchant'}
- Seller GSTIN: {seller_gstin or 'N/A'}
- Order ID: {order_id}
- Invoice Number: {invoice_no or 'N/A'}
- Dispute Category: {reason_code}
- Claimed Recoverable Amount: {formatted_amount}

Issue Description:
{details or f"An audit of our Merchant Tax Report (MTR) against the Payments settlement report reveals an unresolved discrepancy classified under '{reason_code}'."}

Financial Summary:
- Impacted Order: {order_id}
- Discrepancy Type: {reason_code}
- Net Amount Due to Seller: {formatted_amount}

Supporting Documentation:
We have reconciled our internal MTR sales records and the Amazon Payments Unified Transaction Report. The records indicate that the payout received does not match the contractual settlement after standard fee and tax schedules.

Action Requested:
Kindly investigate this discrepancy under Order #{order_id} and credit the recoverable balance of {formatted_amount} to our disbursement account in the next settlement cycle.

Thank you for your prompt assistance.

Sincerely,
{seller_name or 'Finance Team'}
"""
    return body
