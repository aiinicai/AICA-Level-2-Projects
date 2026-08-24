"""Audit trail accumulator.

A single AuditTrail instance is threaded through an analysis run (created
in app/main.py, passed into each layer). Every layer that produces a
material conclusion appends an AuditTrailEntry. This is what backs
Module 11 (source traceability) and lets the report generator and UI
show "why do you believe this" for any claim in the final report.
"""

from __future__ import annotations

import logging

from app.core.enums import ConfidenceLevel
from app.core.models import AuditTrailEntry

logger = logging.getLogger(__name__)


class AuditTrail:
    """In-memory ordered collection of AuditTrailEntry records.

    Not persisted to disk by this class directly — app/main.py or the
    report generator is responsible for serializing it alongside a
    generated report, so the trail can be reviewed independently of the
    prose report.
    """

    def __init__(self) -> None:
        self._entries: list[AuditTrailEntry] = []

    def record(
        self,
        claim: str,
        *,
        source: str | None = None,
        page: int | None = None,
        evidence: str | None = None,
        calculation: str | None = None,
        interpretation: str | None = None,
        confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    ) -> AuditTrailEntry:
        """Append a new entry and return it (callers may want its entry_id
        to cross-link from a MetricResult or AIInterpretation)."""
        # AuditTrailEntry (a pydantic model) will coerce a plain string like
        # "high" into ConfidenceLevel.HIGH, so this also validates the value.
        entry = AuditTrailEntry(
            claim=claim,
            source=source,
            page=page,
            evidence=evidence,
            calculation=calculation,
            interpretation=interpretation,
            confidence=confidence,
        )
        self._entries.append(entry)
        logger.debug(
            "Audit entry recorded: %s (confidence=%s)", claim, entry.confidence.value
        )
        return entry

    @property
    def entries(self) -> list[AuditTrailEntry]:
        return list(self._entries)

    @classmethod
    def from_entries(cls, entries: list[AuditTrailEntry]) -> "AuditTrail":
        """Reconstruct an AuditTrail from a previously-serialized entry
        list (e.g. when restoring a saved session — see
        app/ui/session_io.py). The resulting trail's history starts
        exactly as supplied; new .record() calls append after it."""
        trail = cls()
        trail._entries = list(entries)
        return trail

    def find_by_id(self, entry_id: str) -> AuditTrailEntry | None:
        return next((e for e in self._entries if e.entry_id == entry_id), None)

    def to_dicts(self) -> list[dict]:
        """Serializable form for export alongside a generated report."""
        return [e.model_dump(mode="json") for e in self._entries]

    def __len__(self) -> int:
        return len(self._entries)
