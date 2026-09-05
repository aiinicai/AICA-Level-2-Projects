"""
Rule Definition Models

Data structures for machine-readable rule definitions used by Section 6.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RuleType(Enum):
    """Types of rule evaluations"""
    DATE_COMPARISON = "date_comparison"
    NUMERIC_THRESHOLD = "numeric_threshold"
    EXISTENCE_CHECK = "existence_check"
    SEQUENCE_CHECK = "sequence_check"
    APPROVAL_PRESENCE = "approval_presence"
    DOCUMENT_MATCH = "document_match"
    CROSS_ARTIFACT_CONSISTENCY = "cross_artifact_consistency"
    CUSTOM_FORMULA = "custom_formula"


class RuleStatus(Enum):
    """Status of rule evaluation"""
    PASS = "PASS"
    FAIL = "FAIL"
    CONDITIONAL = "CONDITIONAL"
    INDETERMINATE = "INDETERMINATE"
    CONFLICT = "CONFLICT"


class SeverityLevel(Enum):
    """Severity levels for rule violations"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class RuleApplicability:
    """Defines when a rule applies"""
    jurisdiction: Optional[str] = None
    task_type: Optional[str] = None
    client_exclusions: List[str] = field(default_factory=list)
    workflow_patterns: List[str] = field(default_factory=list)


@dataclass
class EvaluationLogic:
    """Logic for evaluating a rule"""
    type: RuleType
    formula: Optional[str] = None  # For date/numeric calculations
    expected_value: Optional[Any] = None
    comparison_operator: Optional[str] = None  # ">=", "<=", "==", "!=", "contains"
    threshold: Optional[float] = None
    tolerance: Optional[float] = None
    custom_logic: Optional[Dict[str, Any]] = None
    field_to_check: Optional[str] = None  # For cross-document validation - specifies which field to compare


@dataclass
class SeverityMapping:
    """Maps conditions to severity levels"""
    default: SeverityLevel = SeverityLevel.ERROR
    conditions: Dict[str, SeverityLevel] = field(default_factory=dict)
    # Example: {"0_days": "PASS", "1-2_days": "WARNING", ">=3_days": "ERROR"}


@dataclass
class RuleDefinition:
    """
    Complete definition of a deterministic rule

    This is the core structure for machine-readable rules.
    NO natural language rules - everything must be structured.
    """
    rule_id: str
    name: str
    description: str

    # Applicability
    applies_when: RuleApplicability

    # Required data
    required_fields: List[str]

    # Evaluation logic
    evaluation_logic: EvaluationLogic

    # Severity mapping
    severity_levels: SeverityMapping

    # Metadata
    legal_source: Optional[str] = None
    section: Optional[str] = None
    version: str = "1.0"
    enabled: bool = True
    priority: int = 5  # 1=highest, 5=lowest

    # Client overrides
    allow_client_override: bool = False
    override_reason_required: bool = True


@dataclass
class RuleEvaluationResult:
    """
    Result of evaluating a single rule

    This is ONLY factual determinations, NOT opinions.
    """
    rule_id: str
    rule_name: str
    status: RuleStatus
    severity: SeverityLevel

    # What was evaluated
    evaluated_on: List[str]  # Field names
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    deviation: Optional[str] = None

    # Justification
    justification: Dict[str, Any] = field(default_factory=dict)
    # Example: {"source": "client_policy", "reference_id": "late_fee_tolerance"}

    # Confidence
    confidence: float = 1.0
    uncertainty_reason: Optional[str] = None

    # Evidence
    source_file: Optional[str] = None
    source_location: Optional[str] = None  # e.g., "Sheet1!A5"
    evidence_files: Optional[List[str]] = None
    evidence_fields: Optional[List[str]] = None
    sample_mismatches: Optional[List[Dict[str, Any]]] = None

    # Versioning
    rule_version: Optional[str] = None

    # Timestamps
    evaluated_at: Optional[str] = None


@dataclass
class UnresolvedItem:
    """
    Item that could not be evaluated deterministically
    """
    field: str
    reason: str
    required_by_rules: List[str]
    confidence: Optional[float] = None
    suggestion: Optional[str] = None


@dataclass
class RuleEngineOutput:
    """
    Complete output from Section 6

    This feeds into Section 7 (AI Audit Engine).
    """
    rule_results: List[RuleEvaluationResult]
    unresolved_items: List[UnresolvedItem]

    # Statistics
    total_rules_evaluated: int = 0
    passed_count: int = 0
    failed_count: int = 0
    indeterminate_count: int = 0

    # Performance
    execution_time_ms: float = 0

    # Metadata
    client_context_applied: bool = False
    knowledge_base_citations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ClientPolicyOverride:
    """
    Client-specific policy that can downgrade severity

    IMPORTANT: Overrides can only DOWNGRADE severity, never erase facts.
    """
    policy_id: str
    applies_to_rule: str
    condition: Optional[str] = None  # Expression like "delay <= 2"
    severity_downgrade: Optional[SeverityLevel] = None
    reason: str = ""
    reference: Optional[str] = None
