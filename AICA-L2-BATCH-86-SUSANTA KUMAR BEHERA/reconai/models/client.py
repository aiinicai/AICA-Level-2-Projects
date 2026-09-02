import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


class BankAccountProfile(BaseModel):
    """Bank account details associated with a client profile."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bank_name: str = Field(..., description="e.g. Bank of Maharashtra, HDFC, SBI")
    account_no: str = Field(..., description="Bank Account Number")
    ifsc: Optional[str] = Field(default=None, description="IFSC code")
    branch: Optional[str] = Field(default=None, description="Branch name or code")
    account_type: str = Field(default="CURRENT", description="CURRENT, SAVINGS, OVERDRAFT, CC")


class ClientBookProfile(BaseModel):
    """Client accounting book/ledger profile (Tally / Busy / SAP / Zoho)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    book_name: str = Field(..., description="e.g. BOM CA 60453403246 (SUN EYE CARE) Book")
    software: str = Field(default="Tally Prime", description="Tally Prime, Busy, SAP, Zoho, Excel")
    account_head: Optional[str] = Field(default="Bank Accounts", description="Ledger head in accounting software")
    opening_balance: float = Field(default=0.0, description="Opening balance in books")
    linked_bank_account: Optional[str] = Field(default=None, description="Linked Bank Account Number")


class ClientProfile(BaseModel):
    """Client Master Data for persistent CA firm records."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Client Name / Business Entity")
    entity_type: str = Field(default="PROPRIETORSHIP", description="PROPRIETORSHIP, PARTNERSHIP, PVT_LTD, LTD, LLP, TRUST")
    pan: Optional[str] = Field(default=None, description="Permanent Account Number (10 digits)")
    gstin: Optional[str] = Field(default=None, description="GST Identification Number (15 digits)")
    email: Optional[str] = Field(default=None, description="Client Email")
    phone: Optional[str] = Field(default=None, description="Contact Phone")
    address: Optional[str] = Field(default=None, description="Registered Address")
    bank_accounts: List[BankAccountProfile] = Field(default_factory=list)
    books: List[ClientBookProfile] = Field(default_factory=list, description="Associated accounting books / ledgers")
    approved_vendors: List[str] = Field(default_factory=list, description="Master list of approved vendors/suppliers")
    default_auditor_notes: Optional[str] = Field(default=None, description="Standard audit notes / standing instructions")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
