"""
SECTION 6 - SIMPLIFIED RULE ENGINE (Generic, No Hardcoding)

This rule engine validates extraction sanity and lightweight cross-file consistency.
Workflow-specific semantic validation remains in Section 7.
"""

import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.rule_definition import (
    RuleEngineOutput,
    RuleEvaluationResult,
    RuleStatus,
    SeverityLevel,
    UnresolvedItem,
)


class SimplifiedRuleEngine:
    """
    Simplified rule engine with objective validations.

    Keeps checks deterministic and schema-driven, while avoiding workflow-specific heuristics.
    """

    RULE_VERSION = "2.0.0"
    MAX_SAMPLE_MISMATCHES = 5

    def __init__(self, task_id: str):
        """
        Initialize rule engine with task pack

        Args:
            task_id: Task identifier to load task-specific validation rules (required)
        """
        self.task_id = task_id

        # Load task pack for task-specific validations
        from services.task_loader import load_task
        self.task = load_task(task_id)

        # Get task-specific validation rules
        self.task_rules = self.task.get_validation_rules()

    def evaluate(
        self,
        normalized_data: Dict[str, Any],
        workflow_data: Dict[str, Any],
        client_context: Dict[str, Any],
    ) -> RuleEngineOutput:
        """Evaluate deterministic Section 6 rules."""
        start_time = time.time()

        print("\n" + "=" * 80)
        print("SECTION 6: SIMPLIFIED RULE ENGINE (Generic Validation)")
        print("=" * 80 + "\n")

        rule_results: List[RuleEvaluationResult] = []
        unresolved_items: List[UnresolvedItem] = []

        # Baseline extraction sanity rules (generic - keep in core)
        rule_results.append(self._validate_input_extraction(normalized_data))
        rule_results.append(self._validate_output_extraction(normalized_data))
        rule_results.append(self._validate_workflow_parsing(workflow_data))

        # Task-specific cross-file consistency rules (delegate to task pack)
        input_records_a = self.task_rules.extract_pdf_challans(normalized_data)
        output_records_a = self.task_rules.extract_output_challans(normalized_data)

        rule_results.append(self.task_rules.validate_challan_count_match(input_records_a, output_records_a))
        rule_results.append(self.task_rules.validate_challan_number_set_match(input_records_a, output_records_a))
        rule_results.append(self.task_rules.validate_bsr_code_match_for_each_challan(input_records_a, output_records_a))
        rule_results.append(self.task_rules.validate_amount_match_for_each_challan(input_records_a, output_records_a))

        input_identifiers_b, input_files_b = self.task_rules.extract_bsct_pans(normalized_data)
        output_identifiers_b, output_files_b = self.task_rules.extract_output_pans(normalized_data)
        rule_results.append(
            self.task_rules.validate_deductee_pan_set_match(input_identifiers_b, output_identifiers_b, input_files_b, output_files_b)
        )

        # Generic validation (keep in core)
        rule_results.append(self._validate_date_format_normalized(normalized_data))

        execution_time_ms = (time.time() - start_time) * 1000

        passed_count = len([r for r in rule_results if r.status == RuleStatus.PASS])
        failed_count = len([r for r in rule_results if r.status == RuleStatus.FAIL])
        indeterminate_count = len([r for r in rule_results if r.status == RuleStatus.INDETERMINATE])

        print("\nSection 6 Complete:")
        print(f"   {passed_count} passed, {failed_count} failed, {indeterminate_count} indeterminate")
        print(f"   Execution time: {execution_time_ms:.1f}ms")
        print("\n" + "=" * 80 + "\n")

        return RuleEngineOutput(
            rule_results=rule_results,
            unresolved_items=unresolved_items,
            total_rules_evaluated=len(rule_results),
            passed_count=passed_count,
            failed_count=failed_count,
            indeterminate_count=indeterminate_count,
            execution_time_ms=execution_time_ms,
            client_context_applied=False,
            knowledge_base_citations=[],
        )

    def _validate_input_extraction(self, normalized_data: Dict[str, Any]) -> RuleEvaluationResult:
        """Validate that input files were successfully extracted."""

        input_artifacts = normalized_data.get("normalized_inputs", [])
        input_files = self._artifact_files(input_artifacts)

        if not input_artifacts:
            return self._result(
                rule_id="INPUT_FILES_EXTRACTED",
                rule_name="Input Files Extraction",
                status=RuleStatus.FAIL,
                severity=SeverityLevel.CRITICAL,
                evaluated_on=["input_files"],
                expected_value="At least 1 input file",
                actual_value="0 input files found",
                deviation="No input files to validate against",
                evidence_files=input_files,
                evidence_fields=["document_type", "file"],
            )

        error_files = [
            artifact.get("file", "unknown")
            for artifact in input_artifacts
            if artifact.get("document_type") == "ERROR"
        ]

        if error_files:
            return self._result(
                rule_id="INPUT_FILES_EXTRACTED",
                rule_name="Input Files Extraction",
                status=RuleStatus.FAIL,
                severity=SeverityLevel.ERROR,
                evaluated_on=["input_files"],
                expected_value=f"{len(input_artifacts)} files extracted successfully",
                actual_value=f"{len(error_files)} files failed extraction",
                deviation=f"Failed files: {', '.join(error_files[: self.MAX_SAMPLE_MISMATCHES])}",
                justification={
                    "total_files": len(input_artifacts),
                    "error_count": len(error_files),
                    "success_count": len(input_artifacts) - len(error_files),
                },
                evidence_files=input_files,
                evidence_fields=["document_type", "file"],
                sample_mismatches=[{"file": file_name} for file_name in error_files[: self.MAX_SAMPLE_MISMATCHES]],
            )

        return self._result(
            rule_id="INPUT_FILES_EXTRACTED",
            rule_name="Input Files Extraction",
            status=RuleStatus.PASS,
            severity=SeverityLevel.INFO,
            evaluated_on=["input_files"],
            expected_value=f"{len(input_artifacts)} input files",
            actual_value=f"{len(input_artifacts)} files extracted successfully",
            justification={
                "total_files": len(input_artifacts),
                "error_count": 0,
                "success_count": len(input_artifacts),
            },
            evidence_files=input_files,
            evidence_fields=["document_type", "file"],
        )

    def _validate_output_extraction(self, normalized_data: Dict[str, Any]) -> RuleEvaluationResult:
        """Validate that output files were successfully extracted."""

        output_artifacts = normalized_data.get("normalized_outputs", [])
        output_files = self._artifact_files(output_artifacts)

        if not output_artifacts:
            return self._result(
                rule_id="OUTPUT_FILES_EXTRACTED",
                rule_name="Output Files Extraction",
                status=RuleStatus.FAIL,
                severity=SeverityLevel.CRITICAL,
                evaluated_on=["output_files"],
                expected_value="At least 1 output file",
                actual_value="0 output files found",
                deviation="No output files to validate",
                evidence_files=output_files,
                evidence_fields=["document_type", "file"],
            )

        error_files = [
            artifact.get("file", "unknown")
            for artifact in output_artifacts
            if artifact.get("document_type") == "ERROR"
        ]

        if error_files:
            return self._result(
                rule_id="OUTPUT_FILES_EXTRACTED",
                rule_name="Output Files Extraction",
                status=RuleStatus.FAIL,
                severity=SeverityLevel.ERROR,
                evaluated_on=["output_files"],
                expected_value=f"{len(output_artifacts)} files extracted successfully",
                actual_value=f"{len(error_files)} files failed extraction",
                deviation=f"Failed files: {', '.join(error_files[: self.MAX_SAMPLE_MISMATCHES])}",
                justification={
                    "total_files": len(output_artifacts),
                    "error_count": len(error_files),
                    "success_count": len(output_artifacts) - len(error_files),
                },
                evidence_files=output_files,
                evidence_fields=["document_type", "file"],
                sample_mismatches=[{"file": file_name} for file_name in error_files[: self.MAX_SAMPLE_MISMATCHES]],
            )

        return self._result(
            rule_id="OUTPUT_FILES_EXTRACTED",
            rule_name="Output Files Extraction",
            status=RuleStatus.PASS,
            severity=SeverityLevel.INFO,
            evaluated_on=["output_files"],
            expected_value=f"{len(output_artifacts)} output files",
            actual_value=f"{len(output_artifacts)} files extracted successfully",
            justification={
                "total_files": len(output_artifacts),
                "error_count": 0,
                "success_count": len(output_artifacts),
            },
            evidence_files=output_files,
            evidence_fields=["document_type", "file"],
        )

    def _validate_workflow_parsing(self, workflow_data: Dict[str, Any]) -> RuleEvaluationResult:
        """Validate that workflow was successfully parsed."""

        workflows = workflow_data.get("declared_workflows", [])
        workflow_files = sorted(
            {
                str(workflow.get("workflow_file")).strip()
                for workflow in workflows
                if workflow.get("workflow_file")
            }
        )

        if not workflows:
            return self._result(
                rule_id="WORKFLOW_PARSED",
                rule_name="Workflow Parsing",
                status=RuleStatus.FAIL,
                severity=SeverityLevel.ERROR,
                evaluated_on=["workflow"],
                expected_value="At least 1 workflow with steps",
                actual_value="No workflows found",
                deviation="Cannot validate without workflow requirements",
                evidence_files=workflow_files,
                evidence_fields=["declared_workflows", "steps"],
            )

        total_steps = 0
        for workflow in workflows:
            total_steps += len(workflow.get("steps", []))

        if total_steps == 0:
            return self._result(
                rule_id="WORKFLOW_PARSED",
                rule_name="Workflow Parsing",
                status=RuleStatus.FAIL,
                severity=SeverityLevel.ERROR,
                evaluated_on=["workflow"],
                expected_value="Workflow with defined steps",
                actual_value=f"{len(workflows)} workflow(s) but 0 steps",
                deviation="Workflow has no actionable steps to validate",
                justification={"workflow_count": len(workflows), "total_steps": total_steps},
                evidence_files=workflow_files,
                evidence_fields=["declared_workflows", "steps"],
            )

        return self._result(
            rule_id="WORKFLOW_PARSED",
            rule_name="Workflow Parsing",
            status=RuleStatus.PASS,
            severity=SeverityLevel.INFO,
            evaluated_on=["workflow"],
            expected_value="Workflow with steps",
            actual_value=f"{len(workflows)} workflow(s) with {total_steps} steps",
            justification={"workflow_count": len(workflows), "total_steps": total_steps},
            evidence_files=workflow_files,
            evidence_fields=["declared_workflows", "steps"],
        )

    def _validate_date_format_normalized(self, normalized_data: Dict[str, Any]) -> RuleEvaluationResult:
        """Ensure all output date values are normalized as YYYY-MM-DD."""

        observations = self._collect_output_date_observations(normalized_data)
        evidence_files = sorted({obs["file"] for obs in observations if obs.get("file")})

        if not observations:
            return self._result(
                rule_id="DATE_FORMAT_NORMALIZED",
                rule_name="Date Format Normalized",
                status=RuleStatus.INDETERMINATE,
                severity=SeverityLevel.WARNING,
                evaluated_on=["date"],
                expected_value="All output dates in YYYY-MM-DD",
                actual_value="No output date fields found",
                deviation="Rule not applicable without date values",
                evidence_files=evidence_files,
                evidence_fields=["date", "deposit_date"],
            )

        non_iso = [obs for obs in observations if not self._is_iso_date(obs.get("value"))]

        if not non_iso:
            return self._result(
                rule_id="DATE_FORMAT_NORMALIZED",
                rule_name="Date Format Normalized",
                status=RuleStatus.PASS,
                severity=SeverityLevel.INFO,
                evaluated_on=["date"],
                expected_value="All output dates in YYYY-MM-DD",
                actual_value=f"All {len(observations)} output date values are normalized",
                justification={"checked_date_values": len(observations), "non_iso_count": 0},
                evidence_files=evidence_files,
                evidence_fields=["date", "deposit_date"],
            )

        return self._result(
            rule_id="DATE_FORMAT_NORMALIZED",
            rule_name="Date Format Normalized",
            status=RuleStatus.FAIL,
            severity=SeverityLevel.WARNING,
            evaluated_on=["date"],
            expected_value="All output dates in YYYY-MM-DD",
            actual_value=f"{len(non_iso)}/{len(observations)} output date values are non-ISO",
            deviation="Output date normalization is inconsistent",
            justification={
                "checked_date_values": len(observations),
                "non_iso_count": len(non_iso),
            },
            evidence_files=evidence_files,
            evidence_fields=["date", "deposit_date"],
            sample_mismatches=self._first_n(non_iso, self.MAX_SAMPLE_MISMATCHES),
        )

    def _collect_output_date_observations(self, normalized_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect all date-like fields from output entities (generic)."""

        observations: List[Dict[str, Any]] = []
        for artifact in normalized_data.get("normalized_outputs", []):
            file_name = artifact.get("file")

            # Section 3 stores extracted data in 'entities' array (StandardEntity dicts)
            entities = artifact.get("entities") or []
            for index, entity in enumerate(entities):
                if not isinstance(entity, dict):
                    continue

                # StandardEntity wraps data under 'fields' key
                fields = entity.get("fields", entity)

                # Use first available identifier field as entity_id
                entity_id = entity.get("entity_id") or fields.get("serial_number") or fields.get("id") or f"entity[{index}]"

                for field_name, field_value in fields.items():
                    if "date" not in str(field_name).lower():
                        continue
                    if field_value in (None, ""):
                        continue

                    observations.append(
                        {
                            "file": file_name,
                            "entity": str(entity_id),
                            "field": str(field_name),
                            "value": str(field_value),
                        }
                    )

        return observations

    def _artifact_files(self, artifacts: List[Dict[str, Any]]) -> List[str]:
        """Extract unique file names from artifacts."""
        return sorted({str(a.get("file")).strip() for a in artifacts if a.get("file")})

    def _is_iso_date(self, value: Any) -> bool:
        """Check strict ISO date format YYYY-MM-DD."""

        if value in (None, ""):
            return False

        if isinstance(value, datetime):
            return True

        text = str(value).strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return False

        try:
            datetime.strptime(text, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _first_n(self, rows: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
        """Return first N rows for sample mismatch reporting."""
        return rows[:n]

    def _result(
        self,
        rule_id: str,
        rule_name: str,
        status: RuleStatus,
        severity: SeverityLevel,
        evaluated_on: List[str],
        expected_value: Optional[Any] = None,
        actual_value: Optional[Any] = None,
        deviation: Optional[str] = None,
        justification: Optional[Dict[str, Any]] = None,
        source_file: Optional[str] = None,
        source_location: Optional[str] = None,
        evidence_files: Optional[List[str]] = None,
        evidence_fields: Optional[List[str]] = None,
        sample_mismatches: Optional[List[Dict[str, Any]]] = None,
    ) -> RuleEvaluationResult:
        """Build a rule result with consistent metadata fields."""

        return RuleEvaluationResult(
            rule_id=rule_id,
            rule_name=rule_name,
            status=status,
            severity=severity,
            evaluated_on=evaluated_on,
            expected_value=expected_value,
            actual_value=actual_value,
            deviation=deviation,
            justification=justification or {},
            source_file=source_file,
            source_location=source_location,
            evidence_files=evidence_files,
            evidence_fields=evidence_fields,
            sample_mismatches=sample_mismatches,
            rule_version=self.RULE_VERSION,
            evaluated_at=datetime.utcnow().isoformat(),
        )


# Convenience function for backward compatibility
def evaluate_rules(
    normalized_data: Dict[str, Any],
    workflow_data: Dict[str, Any],
    client_context: Dict[str, Any],
) -> RuleEngineOutput:
    """Evaluate deterministic Section 6 rules."""
    engine = SimplifiedRuleEngine()
    return engine.evaluate(normalized_data, workflow_data, client_context)
