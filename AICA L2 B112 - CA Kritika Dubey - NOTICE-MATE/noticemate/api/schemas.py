"""Request models (pydantic v2). Length limits are enforced here and again in services."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class UserIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=120)
    role: str
    password: str = Field(min_length=10, max_length=200)
    membership_no: Optional[str] = Field(default=None, max_length=20)


class PasswordChangeIn(BaseModel):
    old_password: str = Field(max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class CaseIn(BaseModel):
    case_ref: str = Field(min_length=1, max_length=60)
    assessee_name: str = Field(min_length=1, max_length=200)
    assessee_category: str
    pan: Optional[str] = Field(default=None, max_length=10)
    assessment_year: Optional[str] = Field(default=None, max_length=7)
    party_names: list[str] = Field(default_factory=list, max_length=200)


class TermsIn(BaseModel):
    names: list[str] = Field(max_length=200)


class MemberIn(BaseModel):
    user_id: int


class StatusIn(BaseModel):
    status: str


class DocTypeIn(BaseModel):
    doc_type: str


class AnnexureIn(BaseModel):
    is_annexure: bool
    label: Optional[str] = Field(default=None, max_length=6)


class NoticeFieldIn(BaseModel):
    field: str
    value: str = Field(max_length=500)


class DeadlineIn(BaseModel):
    deadline: str = Field(max_length=10)
    source: str = Field(min_length=5, max_length=300)


class IssueIn(BaseModel):
    query_text: str = Field(min_length=5, max_length=5000)
    category: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)


class IssueMergeIn(BaseModel):
    target_issue_id: int
    source_issue_ids: list[int] = Field(min_length=1, max_length=30)
    query_text: str = Field(min_length=10, max_length=8000)


class IssueQueryUpdateIn(BaseModel):
    query_text: str = Field(min_length=10, max_length=8000)


class AnalysisUpdateIn(BaseModel):
    updates: dict[str, Any]


class StrategyIn(BaseModel):
    strategy: str
    reason: str = Field(min_length=10, max_length=2000)


class EvidenceAssessIn(BaseModel):
    status: str
    establishes: str = Field(default="", max_length=2000)
    does_not_establish: str = Field(default="", max_length=2000)
    supports_explanation: str = Field(default="", max_length=1000)
    inconsistency: str = Field(default="", max_length=2000)
    document_id: Optional[int] = None


class BankBookIn(BaseModel):
    statement_doc: int
    book_doc: int


class SourceRow(BaseModel):
    deposit_date: str
    receipt_date: str
    amount: float = Field(gt=0)
    description: str = Field(default="", max_length=200)


class CashChronIn(BaseModel):
    cash_book_doc: int
    statement_doc: int
    opening_balance: float = 0.0
    source_mapping: Optional[list[SourceRow]] = None


class LedgerCompareIn(BaseModel):
    doc_a: int
    doc_b: int
    label_a: str = Field(max_length=40)
    label_b: str = Field(max_length=40)
    filter_a: Optional[str] = Field(default=None, max_length=100)
    filter_b: Optional[str] = Field(default=None, max_length=100)
    table_a: int = 0
    table_b: int = 0


class FSFigure(BaseModel):
    label: str = Field(max_length=100)
    per_financial_statements: Any = None
    per_books: Any = None
    per_return: Any = None


class FSIn(BaseModel):
    figures: list[FSFigure] = Field(min_length=1, max_length=100)


class AdditionIn(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0)
    issue_id: Optional[int] = None
    possible_provision: Optional[str] = Field(default=None, max_length=100)


class TaxSimIn(BaseModel):
    assessment_year: str
    assessee_category: str
    returned_income: Optional[float] = Field(default=None, ge=0)
    additions: list[AdditionIn] = Field(min_length=1, max_length=50)


class LawIn(BaseModel):
    year_label: str
    label_type: str = "AY"
    notice_date: Optional[str] = None
    proceeding_type: Optional[str] = None


class LegalRefIn(BaseModel):
    ref_key: str
    act: str = Field(max_length=200)
    provision: str = Field(max_length=200)
    title: str = Field(max_length=300)
    summary: str = Field(max_length=2000)
    source_url: Optional[str] = Field(default=None, max_length=500)


class VerifyRefIn(BaseModel):
    source_url: str = Field(max_length=500)


class SelectRefsIn(BaseModel):
    ref_keys: list[str] = Field(max_length=20)


class DraftBuildIn(BaseModel):
    notice_id: Optional[int] = None
    reflect_reconciliation: bool = False
    reconciliation_run_ids: list[int] = Field(default_factory=list, max_length=30)
    include_record_references: bool = True
    include_legal_suggestions: bool = False
    ai_draft_ids: list[int] = Field(default_factory=list, max_length=200)


class CloudDraftIn(BaseModel):
    provider: str = Field(pattern="^(anthropic|gemini)$")


class AppSettingIn(BaseModel):
    key: str = Field(max_length=60)
    value: str = Field(max_length=300)


class CaseDeleteIn(BaseModel):
    confirm_case_ref: str = Field(min_length=1, max_length=200)


class DocLinkStatusIn(BaseModel):
    status: str = Field(pattern="^(AUTO|ACCEPTED|REJECTED)$")


class DraftEditIn(BaseModel):
    updates: dict[str, Any]


class TickIn(BaseModel):
    item_key: str
    checked: bool
    note: str = Field(default="", max_length=1000)


class ApproveIn(BaseModel):
    declaration_accepted: bool


class RevokeIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class AIPrepareIn(BaseModel):
    task: str
    content: str = Field(min_length=1, max_length=100000)
    extra_instructions: str = Field(default="", max_length=4000)
    provider: Optional[str] = None
    related_id: Optional[int] = None


# ---------------- v2 ----------------
class ProviderIn(BaseModel):
    provider: Optional[str] = None


class AnalysisLocalIn(BaseModel):
    notice_id: Optional[int] = None


class AnalysisAIIn(BaseModel):
    notice_id: Optional[int] = None
    provider: Optional[str] = None


class AnalysisEditIn(BaseModel):
    content: dict[str, Any]


class DecisionIn(BaseModel):
    decision: str
    comment: str = Field(default="", max_length=3000)


class MatchIn(BaseModel):
    doc_a: int
    doc_b: int
    perspective_a: str = "books"
    perspective_b: str = "books"
    side_a: str = "inflow"
    side_b: str = "inflow"
    label_a: str = Field(default="A", max_length=30)
    label_b: str = Field(default="B", max_length=30)
    filter_a: Optional[str] = Field(default=None, max_length=100)
    filter_b: Optional[str] = Field(default=None, max_length=100)
    date_window_days: int = Field(default=0, ge=0, le=90)
    require_party: bool = False
    table_a: int = 0
    table_b: int = 0


class BankBookLedgerIn(BaseModel):
    bank_book_doc: int
    ledger_doc: int
    ledger_side: str = "outflow"
    date_window_days: int = Field(default=0, ge=0, le=90)
    filter_ledger: Optional[str] = Field(default=None, max_length=100)


class SalesBankIn(BaseModel):
    sales_doc: int
    statement_doc: int
    date_window_days: int = Field(default=7, ge=0, le=90)
    filter_sales: Optional[str] = Field(default=None, max_length=100)
    require_party: bool = False


class AISIn(BaseModel):
    ais_doc: int
    books_doc: int
    books_perspective: str = "books"
    books_side: str = "outflow"
    ais_table: int = 0
    books_table: int = 0


class DebtorsIn(BaseModel):
    debtor_doc: int
    receipts_doc: Optional[int] = None
    receipts_perspective: str = "books"
    debtor_table: int = 0


class PartyIn(BaseModel):
    record_type: str
    party_name: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0)
    txn_date: Optional[str] = None
    mode: Optional[str] = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    observations: str = Field(default="", max_length=2000)
    issue_id: Optional[int] = None


class ResearchIn(BaseModel):
    question: str = Field(min_length=5, max_length=3000)
    issue_id: Optional[int] = None


class ResearchAIIn(BaseModel):
    provider: Optional[str] = None
    live: bool = False


class PropositionIn(BaseModel):
    status: str
    source_url: Optional[str] = Field(default=None, max_length=500)
    note: str = Field(default="", max_length=500)


class PromoteIn(BaseModel):
    ref_key: str = Field(min_length=3, max_length=60)


class LegalRefV2In(BaseModel):
    ref_key: str
    act: str = Field(max_length=200)
    provision: str = Field(max_length=200)
    title: str = Field(max_length=300)
    summary: str = Field(max_length=2000)
    source_url: Optional[str] = Field(default=None, max_length=500)
    ref_type: str = "STATUTE"
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    applies_to: Optional[str] = Field(default=None, max_length=200)


class VerifyRefV2In(BaseModel):
    source_url: str = Field(max_length=500)
    effective_from: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=1000)


class CommentIn(BaseModel):
    section: str = Field(min_length=1, max_length=100)
    comment: str = Field(min_length=3, max_length=3000)


class ResolveIn(BaseModel):
    resolution: str = Field(min_length=3, max_length=2000)


class RejectIn(BaseModel):
    comment: str = Field(min_length=5, max_length=3000)
    decision: str = "REJECTED"


class AISendIn(BaseModel):
    payload_hash: str = Field(min_length=64, max_length=64)
    confirm: bool


# ---------------- V3: legal authorities, propositions, trace ----------------
class SourceIn(BaseModel):
    source_class: str = Field(max_length=20)
    source_type: str = Field(max_length=20)
    title: str = Field(min_length=1, max_length=400)
    citation: Optional[str] = Field(default=None, max_length=500)
    issuing_body: Optional[str] = Field(default=None, max_length=200)
    court_level: Optional[str] = Field(default=None, max_length=20)
    document_number: Optional[str] = Field(default=None, max_length=120)
    date_issued: Optional[str] = Field(default=None, max_length=10)
    effective_from: Optional[str] = Field(default=None, max_length=10)
    effective_to: Optional[str] = Field(default=None, max_length=10)
    act: Optional[str] = Field(default=None, max_length=20)
    provision: Optional[str] = Field(default=None, max_length=200)
    pinpoint: Optional[str] = Field(default=None, max_length=200)
    excerpt: Optional[str] = Field(default=None, max_length=2000)
    summary: Optional[str] = Field(default=None, max_length=2000)
    applicability_note: Optional[str] = Field(default=None, max_length=2000)
    ay_from: Optional[str] = Field(default=None, max_length=10)
    ay_to: Optional[str] = Field(default=None, max_length=10)
    official_url: Optional[str] = Field(default=None, max_length=1000)
    superseded_by: Optional[int] = None


class SourceUpdateIn(BaseModel):
    updates: dict[str, Any]


class SourceDecisionIn(BaseModel):
    decision: str = Field(max_length=20)
    checked_url: Optional[str] = Field(default=None, max_length=1000)
    checked_pinpoint: Optional[str] = Field(default=None, max_length=200)
    applicability_confirmed: bool = False
    note: str = Field(default="", max_length=2000)


class PropositionIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    issue_id: Optional[int] = None
    kind: str = Field(default="LEGAL", max_length=10)


class PropositionEditIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class LinkSourceIn(BaseModel):
    source_id: int
    stance: str = Field(max_length=20)
    relevance_note: str = Field(default="", max_length=1000)
    pinpoint: Optional[str] = Field(default=None, max_length=200)


class FactIn(BaseModel):
    fact_type: str = Field(max_length=20)
    basis: str = Field(max_length=20)
    document_id: Optional[int] = None
    page: Optional[int] = None
    quote: Optional[str] = Field(default=None, max_length=600)
    evidence_item_id: Optional[int] = None
    recon_run_id: Optional[int] = None
    note: str = Field(default="", max_length=1000)


class PropDecisionIn(BaseModel):
    decision: str = Field(max_length=20)
    note: str = Field(default="", max_length=4000)


class ConfirmCaseIn(BaseModel):
    assessee_name: str = Field(min_length=1, max_length=200)
    assessee_category: str = Field(max_length=30)
    pan: Optional[str] = Field(default=None, max_length=10)
    assessment_year: Optional[str] = Field(default=None, max_length=7)
    case_ref: Optional[str] = Field(default=None, max_length=60)
