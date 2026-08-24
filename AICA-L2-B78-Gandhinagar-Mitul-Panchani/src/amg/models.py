"""Pydantic schemas shared by the memory governance components."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ServedBy = Literal[
    "live",
    "cache",
    "cache_after_error",
    "stub",
    "fallback_after_error",
    "blocked_by_cap",
    "blocked_offline",
]


class SourceType(StrEnum):
    USER_STATED = "user_stated"
    AI_INFERRED = "ai_inferred"


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    FLAGGED_CONFLICT = "flagged_conflict"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class AssertionType(StrEnum):
    DIRECT_SELF_STATEMENT = "direct_self_statement"
    HYPOTHETICAL = "hypothetical"
    THIRD_PARTY = "third_party"
    QUOTED = "quoted"


class EventType(StrEnum):
    WRITE = "write"
    WRITE_REJECTED = "write_rejected"
    CONTEXTUAL_READ = "contextual_read"
    FULL_EXPORT = "full_export"
    UPDATE = "update"
    DELETE = "delete"
    ACCESS_DENIED = "access_denied"


class TrustTier(StrEnum):
    STATED = "stated"
    CONFIRMED_INFERENCE = "confirmed_inference"
    UNCONFIRMED_INFERENCE = "unconfirmed_inference"


class RequestShape(StrEnum):
    """Policy classification for a read-side request."""

    ORDINARY_QUERY = "ordinary_query"
    UNSCOPED_DUMP_ATTEMPT = "unscoped_dump_attempt"
    LEGITIMATE_EXPORT_REQUEST = "legitimate_export_request"


class CheckerReasonCode(StrEnum):
    """Small, stable vocabulary for checker decisions and safe audit metadata."""

    OK = "ok"
    INSTRUCTION_SHAPED = "instruction_shaped"
    NOT_FIRST_PERSON = "not_first_person"
    HYPOTHETICAL_FRAMING = "hypothetical_framing"
    THIRD_PARTY_SUBJECT = "third_party_subject"
    QUOTED_SPEECH = "quoted_speech"
    EMPTY_OR_TRIVIAL = "empty_or_trivial"
    NOT_INFERENCE_SHAPED = "not_inference_shaped"
    OVERCLAIMS_CERTAINTY = "overclaims_certainty"


class Memory(BaseModel):
    """A complete row from the ``memories`` table."""

    model_config = ConfigDict(frozen=True)

    id: int
    content: str
    subject_key: str
    category: str
    source_type: SourceType
    confirmed_at: str | None
    source_session_id: str
    created_at: str
    last_verified_at: str
    status: MemoryStatus
    supersedes_id: int | None
    embedding_id: int


class AuditEvent(BaseModel):
    """A complete row from the ``audit_log`` table."""

    model_config = ConfigDict(frozen=True)

    id: int
    event_type: EventType
    memory_id: int | None
    actor: str
    timestamp: str
    detail: dict[str, object]
    prev_row_hash: str
    row_hash: str


class CandidateFact(BaseModel):
    """A candidate proposed by the maker from one direct user turn.

    ``assertion_type`` classifies the originating user statement, while
    ``source_type`` records how this candidate itself came to exist. An
    inference therefore keeps its parent's assertion type but is explicitly
    marked ``ai_inferred`` so it can never masquerade as user testimony.
    """

    model_config = ConfigDict(frozen=True)

    content: str
    subject_key: str
    category: str
    assertion_type: AssertionType
    source_type: SourceType
    # Inference parentage is limited to a sibling fact from the same maker call.
    inferred_from_content: str | None = None


class CheckerVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    approved: bool
    reason_code: CheckerReasonCode
    notes: str


class EntailmentVerdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    contradicts: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class TaggedFact(BaseModel):
    """A checker-approved fact with normalized provenance and trust metadata."""

    model_config = ConfigDict(frozen=True)

    content: str
    subject_key: str
    category: str
    assertion_type: AssertionType
    source_type: SourceType
    inferred_from_content: str | None = None
    confirmed_at: str | None = None
    trust_tier: TrustTier


class ContradictionResult(BaseModel):
    """All explicit entailment judgments made for one proposed fact."""

    model_config = ConfigDict(frozen=True)

    conflicts: list[tuple[Memory, EntailmentVerdict]]
    checked_count: int = Field(ge=0)


class ProviderUse(BaseModel):
    """Honest, UI-safe summary of the backend that served an operation."""

    model_config = ConfigDict(frozen=True)

    provider_name: str
    model: str
    served_by: ServedBy
    was_fallback: bool


class CandidateIngestResult(BaseModel):
    """Governance outcome for one maker-proposed candidate."""

    model_config = ConfigDict(frozen=True)

    candidate_index: int
    assertion_type: AssertionType
    source_type: SourceType
    subject_key: str
    category: str
    content_sha256: str
    outcome: Literal["written", "rejected"]
    reason_code: str
    reason: str
    memory_id: int | None = None
    status: MemoryStatus | None = None
    trust_tier: TrustTier | None = None
    checked_count: int = 0
    conflict_memory_ids: list[int] = Field(default_factory=list)
    audit_row_ids: list[int] = Field(default_factory=list)
    provider_calls: dict[str, ProviderUse] = Field(default_factory=dict)
    fallback_used: bool = False


class IngestReport(BaseModel):
    """Complete governed-write report suitable for direct UI rendering."""

    model_config = ConfigDict(frozen=True)

    session_id: str
    candidate_count: int
    written_count: int
    rejected_count: int
    candidates: list[CandidateIngestResult]
    audit_row_ids: list[int]
    maker_provider: ProviderUse | None = None
    fallback_used: bool = False


class CascadePlan(BaseModel):
    """Immutable preview of every row affected by one cascading erasure."""

    model_config = ConfigDict(frozen=True)

    target_memory_id: int
    memory_ids: list[int]
    embedding_ids: list[int]

    @property
    def cascade_count(self) -> int:
        return len(self.memory_ids)


class ChainVerification(BaseModel):
    """Result of verifying every currently stored audit row."""

    model_config = ConfigDict(frozen=True)

    valid: bool
    rows_checked: int
    broken_at_row_id: int | None
    reason: str


class EraseReport(BaseModel):
    """Confirmed or refused outcome of an erasure request."""

    model_config = ConfigDict(frozen=True)

    confirmed: bool
    erased: bool
    plan: CascadePlan
    audit_row_ids: list[int] = Field(default_factory=list)
    chain_verification: ChainVerification
    reason: str

    @property
    def chain_valid(self) -> bool:
        return self.chain_verification.valid

    @property
    def preview(self) -> CascadePlan:
        return self.plan

    @property
    def erased_memory_ids(self) -> list[int]:
        return self.plan.memory_ids if self.erased else []


class GuardDecision(BaseModel):
    """Pure policy decision; persistence is performed by the owning operation."""

    model_config = ConfigDict(frozen=True)

    allowed: bool
    shape: RequestShape
    reason: str
    audit_event: Literal["access_denied"] | None = None


class RetrievalHit(Memory):
    """A contextual match with its provenance, trust, and similarity visible."""

    trust_tier: TrustTier
    similarity: float = Field(ge=-1.0, le=1.0)


class ContextualResult(BaseModel):
    """Bounded contextual-read outcome; a refusal always has zero hits."""

    model_config = ConfigDict(frozen=True)

    allowed: bool
    hits: list[RetrievalHit] = Field(default_factory=list)
    reason: str
    provider: ProviderUse | None = None
    audit_row_id: int

    @property
    def results(self) -> list[RetrievalHit]:
        return self.hits

    @property
    def memories(self) -> list[RetrievalHit]:
        return self.hits


class ExportResult(BaseModel):
    """Passphrase-gated full-export outcome."""

    model_config = ConfigDict(frozen=True)

    succeeded: bool
    memories: list[Memory] = Field(default_factory=list)
    reason: str
    audit_row_id: int

    @property
    def allowed(self) -> bool:
        return self.succeeded

    @property
    def rows(self) -> list[Memory]:
        return self.memories

    @property
    def refused(self) -> bool:
        return not self.succeeded


class ScenarioResult(BaseModel):
    """Machine-readable outcome from one scripted capstone demonstration."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    what_it_proves: str
    steps: list[str]
    passed: bool
    evidence: list[dict[str, Any]]
    audit_rows_written: int = Field(ge=0)
