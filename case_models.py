"""Structured evidence, research and strategy records for a reviewed tax reply."""
from typing import Literal
from pydantic import Field
from services.models import StrictModel


class DocumentNeed(StrictModel):
    name: str
    issue: str
    purpose: str
    origin: Literal["Notice requested", "AI suggested"]


class DocumentPlan(StrictModel):
    documents: list[DocumentNeed]
    public_research_topics: list[str]


class DocumentFinding(StrictModel):
    observation: str
    source_quote: str
    relevance: str
    effect: Literal["Supports", "Contradicts", "Neutral", "Unclear"]


class EvidenceReview(StrictModel):
    findings: list[DocumentFinding]
    missing_information: list[str]


class Authority(StrictModel):
    title: str
    kind: Literal["Act", "Rule", "Regulation", "Circular", "Notification", "Case law"]
    reference: str
    court_or_issuer: str
    date_or_effective_period: str
    issue: str
    position: Literal["For client", "Against client", "Mixed / neutral"]
    proposition: str
    relevance_and_distinctions: str
    pinpoint: str
    source_url: str
    status_checks: str = Field(description="Amendment/applicability or appeal/overruling checks, with unresolved gaps stated explicitly.")


class Research(StrictModel):
    authorities: list[Authority]
    gaps: list[str]
    search_summary: str


class IssueStrategy(StrictModel):
    issue: str
    established_facts: list[str]
    evidence_references: list[str]
    missing_facts: list[str]
    primary_position: str
    alternative_position: str
    adverse_arguments_and_response: str
    authorities_to_use: list[str]


class Strategy(StrictModel):
    issues: list[IssueStrategy]
    procedural_checks: list[str]
    contradictions: list[str]
    pre_filing_actions: list[str]
    overall_approach: str


class ReviewResult(StrictModel):
    revised_reply: str
    review_notes: list[str]
