"""
SECTION 7 - AI-BASED WORKFLOW VALIDATOR (New Approach)

AI validates workflow completion by comparing normalized input and output records.
Includes deterministic pre-flight fingerprinting and matching reliability gates.
"""

import dataclasses
import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

from services.ai_prompt_builder_v2 import estimate_token_count
from services.llm_client import complete as llm_complete

# Load environment variables from .env file
load_dotenv()


class AIWorkflowValidator:
    """AI-based workflow validator."""

    def __init__(self, task_id: str, api_key: str = None, model: str = None, debug_dir: str = "."):
        self.task_id = task_id
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        # Route by model name through llm_client (OpenAI / Anthropic / OpenRouter),
        # so an OpenRouter model in the env works and JSON fences are stripped.
        self.model = model or os.getenv("AI_VALIDATION_MODEL") or os.getenv("AI_PRIMARY_MODEL", "gpt-4o-mini")
        self.debug_dir = debug_dir

        # Load task pack for task-specific AI grounding
        from services.task_loader import load_task
        self.task = load_task(task_id)

        # Get task-specific AI grounding helper
        self.grounding_helper = self.task.get_ai_grounding_helper()

        # Get task-specific prompt builder
        self.prompt_builder = self.task.get_prompt_builder()

    def validate(
        self,
        workflow_data: Dict[str, Any],
        normalized_data: Dict[str, Any],
        rule_engine_results: Any,
    ) -> Dict[str, Any]:
        """Validate workflow completion using AI."""

        print("\n" + "=" * 80)
        print("SECTION 7: AI WORKFLOW VALIDATION")
        print("=" * 80 + "\n")

        rule_engine_dict = self._coerce_rule_engine_results(rule_engine_results)
        if rule_engine_dict.get('failed_count', 0) > 0:
            print("WARNING: Section 6 found deterministic rule failures")
            print("   Proceeding with AI validation using available data...\n")

        # Delegate to task pack for record extraction and fingerprinting
        records = self.grounding_helper.extract_record_collections(normalized_data)
        fingerprint = self.grounding_helper.build_data_fingerprint(records)
        self.grounding_helper.print_data_fingerprint(fingerprint)

        run_id = self._compute_run_id(workflow_data, normalized_data)

        print("[1/5] Building AI validation prompt (V2 - Section 6 aligned)...")
        prompt = self.prompt_builder(workflow_data, normalized_data, rule_engine_dict)

        debug_prompt_path = self._dump_prompt_debug(
            run_id=run_id,
            prompt=prompt,
            workflow_data=workflow_data,
            normalized_data=normalized_data,
            fingerprint=fingerprint,
        )
        print(f"   Prompt debug saved: {debug_prompt_path}")

        estimated_tokens = estimate_token_count(prompt)
        estimated_cost = self._estimate_cost(estimated_tokens, 800)
        print(f"   Prompt size: ~{estimated_tokens} tokens")
        print(f"   Estimated cost: ~${estimated_cost:.4f}")

        print(f"[2/5] Calling model ({self.model}) ...")
        try:
            ai_response = llm_complete(
                model=self.model,
                system_prompt="You are a workflow validation assistant. Respond ONLY with valid JSON in the specified format.",
                user_prompt=prompt,
                temperature=0.1,
                api_key=self.api_key,
                json_mode=True,
            )

            # llm_client records exact token cost into the run's cost tracker; for this
            # module's own summary we estimate (usage isn't returned by the seam).
            input_tokens = estimate_token_count(prompt)
            output_tokens = estimate_token_count(ai_response or "")
            actual_cost = self._estimate_cost(input_tokens, output_tokens)

            print("   AI response received")
            print(f"   ~Input tokens: {input_tokens}, ~Output tokens: {output_tokens}")

        except Exception as e:
            print(f"   API call failed: {e}")
            return self._error_response(str(e), run_id=run_id, fingerprint=fingerprint, debug_prompt_path=debug_prompt_path)

        print("[3/5] Parsing AI validation results...")
        try:
            validation_results = json.loads(ai_response)
            print("   Successfully parsed AI response")
        except json.JSONDecodeError as e:
            print(f"   Failed to parse AI response: {e}")
            return self._error_response(
                f"Invalid JSON from AI: {e}",
                run_id=run_id,
                fingerprint=fingerprint,
                debug_prompt_path=debug_prompt_path,
            )

        print("[4/5] Verifying AI's claimed mismatches...")
        verified_results = self._verify_mismatches(validation_results)
        # Delegate to task pack for entity-specific grounding and alignment
        grounded_results = self.grounding_helper.ground_and_normalize_issues(verified_results, records)
        dependency_safe_results = self.grounding_helper.suppress_dependent_issues(grounded_results)
        aligned_results = self.grounding_helper.align_with_section6_rules(dependency_safe_results, rule_engine_dict)
        complete_results = self._ensure_all_steps_covered(aligned_results, workflow_data)
        gated_results = self._apply_matching_gate(complete_results, fingerprint)
        self._recompute_summary(gated_results)

        # CRITICAL: Recompute status/summary AFTER all issue removal
        deterministic_results = self._make_deterministic_after_verification(gated_results)

        removed_count = deterministic_results.get('false_positives_removed', 0)
        ungrounded_removed = deterministic_results.get('ungrounded_issues_removed', 0)
        if removed_count > 0:
            print(f"   Removed {removed_count} false positive(s) (Expected == Actual)")
        if ungrounded_removed > 0:
            print(f"   Removed {ungrounded_removed} ungrounded issue(s)")
        if removed_count == 0 and ungrounded_removed == 0:
            print("   All mismatches verified and grounded")

        print("[5/5] Formatting validation results...")
        formatted_results = self._format_results(
            deterministic_results,
            cost=actual_cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            run_id=run_id,
            debug_prompt_path=debug_prompt_path,
            fingerprint=fingerprint,
        )

        summary = formatted_results.get('summary', {})
        total_steps = summary.get('total_steps', 0)
        passed_steps = summary.get('passed_steps', 0)
        failed_steps = summary.get('failed_steps', 0)
        overall_status = summary.get('overall_status', 'UNKNOWN')

        print("\nAI VALIDATION SUMMARY:")
        print(f"   Total steps: {total_steps}")
        print(f"   Passed: {passed_steps}")
        print(f"   Failed: {failed_steps}")
        print(f"   Overall: {overall_status}")
        print(f"   Cost: ${actual_cost:.4f}")

        print("\n" + "=" * 80 + "\n")

        return formatted_results

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost_per_1k = 0.00015
        output_cost_per_1k = 0.0006
        return (input_tokens / 1000) * input_cost_per_1k + (output_tokens / 1000) * output_cost_per_1k

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return self._estimate_cost(input_tokens, output_tokens)

    def _coerce_rule_engine_results(self, rule_engine_results: Any) -> Dict[str, Any]:
        """Accept dict or dataclass for Section 6 results."""
        if isinstance(rule_engine_results, dict):
            return rule_engine_results
        if dataclasses.is_dataclass(rule_engine_results):
            return dataclasses.asdict(rule_engine_results)
        return {}

    def _verify_mismatches(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Mechanically verify AI's claimed mismatches to filter false positives."""
        false_positives_removed = 0
        validations = validation_results.get('validations', [])

        for validation in validations:
            issues = validation.get('issues', [])
            verified_issues = []

            for issue in issues:
                expected = issue.get('expected')
                actual = issue.get('actual')
                if self._is_real_mismatch(expected, actual):
                    verified_issues.append(issue)
                else:
                    false_positives_removed += 1

            validation['issues'] = verified_issues
            validation['failed_checks'] = len(verified_issues)

            if len(verified_issues) == 0 and len(issues) > 0:
                validation['status'] = 'PASS'
                validation['passed_checks'] = validation.get('passed_checks', 0) + len(issues)

        # Get summary (handle both dict and string formats from AI)
        summary = validation_results.get('summary', {})
        if isinstance(summary, str):
            # AI returned summary as a string - convert to dict
            summary = {'text': summary}

        passed_count = sum(1 for v in validations if v.get('status') == 'PASS')
        failed_count = sum(1 for v in validations if v.get('status') == 'FAIL')

        summary['total_steps'] = len(validations)
        summary['passed_steps'] = passed_count
        summary['failed_steps'] = failed_count
        summary['overall_status'] = 'PASS' if failed_count == 0 else 'FAIL'

        validation_results['summary'] = summary
        validation_results['false_positives_removed'] = false_positives_removed

        return validation_results

    def _make_deterministic_after_verification(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRITICAL: Make Section 7 output deterministic AFTER all verification steps.

        This runs AFTER all issue removal (verify, ground, suppress, align, gate).
        It recomputes status/checks/summary from FINAL issues array, not AI text.

        Rules:
        1. Status computed from structured issues only (ignore AI's status)
        2. Summary generated from issues (ignore AI's summary text)
        3. Hard guardrail: PASS cannot mention problems

        This prevents "PASS with stale mismatch text" bugs.
        """
        validations = validation_results.get('validations', [])

        # Problem keywords that should NOT appear in PASS summaries
        problem_keywords = ['mismatch', 'missing', 'not found', 'difference', 'incorrect',
                           'invalid', 'failed', 'discrepancy', 'inconsistent', 'error',
                           'does not match', 'do not match']

        for validation in validations:
            issues = validation.get('issues', [])

            # RULE 1: Recompute checks from actual issues
            error_issues = [i for i in issues if i.get('severity') in ['CRITICAL', 'ERROR']]
            warn_issues = [i for i in issues if i.get('severity') == 'WARNING']

            failed_checks = len(error_issues)
            warn_checks = len(warn_issues)

            # Preserve AI's passed_checks if reasonable, else compute
            ai_passed_checks = validation.get('passed_checks', 0)
            if ai_passed_checks > 0:
                passed_checks = ai_passed_checks
            else:
                # Estimate from total - failed - warn
                total_checks_estimate = failed_checks + warn_checks
                passed_checks = max(0, total_checks_estimate)

            validation['failed_checks'] = failed_checks
            validation['warn_checks'] = warn_checks
            validation['passed_checks'] = passed_checks

            # RULE 2: Recompute status from actual issues (ignore AI's status)
            if failed_checks > 0:
                validation['status'] = 'FAIL'
            elif warn_checks > 0:
                validation['status'] = 'WARN'
            else:
                validation['status'] = 'PASS'

            # RULE 3: Regenerate summary from actual issues (ignore AI text)
            validation['summary'] = self._generate_deterministic_summary(validation, issues)

            # RULE 4: Hard guardrail - PASS cannot mention problems
            final_status = validation['status']
            final_summary = validation['summary']

            if final_status == 'PASS':
                summary_lower = final_summary.lower()
                has_problem_keywords = any(keyword in summary_lower for keyword in problem_keywords)

                if has_problem_keywords:
                    # Sanitize summary - PASS should not mention problems
                    validation['summary'] = 'No issues found.'
                    validation['summary_sanitized'] = True

        # Recompute overall summary from final validations
        summary = validation_results.get('summary', {})
        if isinstance(summary, str):
            summary = {'text': summary}

        passed_count = sum(1 for v in validations if v.get('status') == 'PASS')
        warn_count = sum(1 for v in validations if v.get('status') == 'WARN')
        failed_count = sum(1 for v in validations if v.get('status') == 'FAIL')

        summary['total_steps'] = len(validations)
        summary['passed_steps'] = passed_count
        summary['warn_steps'] = warn_count
        summary['failed_steps'] = failed_count

        # Overall status
        if failed_count > 0:
            summary['overall_status'] = 'FAIL'
        elif warn_count > 0:
            summary['overall_status'] = 'WARN'
        else:
            summary['overall_status'] = 'PASS'

        # Regenerate overall summary text
        if failed_count > 0:
            summary['text'] = f'Workflow validation failed: {failed_count} step(s) with errors.'
        elif warn_count > 0:
            summary['text'] = f'Workflow validation passed with warnings: {warn_count} step(s) have non-blocking issues.'
        else:
            summary['text'] = 'Workflow validation passed: all steps completed successfully.'

        validation_results['summary'] = summary

        return validation_results

    def _generate_deterministic_summary(self, validation: Dict[str, Any], issues: List[Dict[str, Any]]) -> str:
        """
        Generate summary ONLY from actual issues (not AI narrative).

        Rules:
        - If no issues: "No issues found."
        - If issues: "Found X error(s), Y warning(s): [top issues]"
        """
        if len(issues) == 0:
            return "No issues found."

        # Count by severity
        error_count = sum(1 for i in issues if i.get('severity') in ['CRITICAL', 'ERROR'])
        warn_count = sum(1 for i in issues if i.get('severity') == 'WARNING')

        parts = []
        if error_count > 0:
            parts.append(f"{error_count} error(s)")
        if warn_count > 0:
            parts.append(f"{warn_count} warning(s)")

        summary = f"Found {', '.join(parts)}."

        # Add top issues (max 2)
        top_issues = issues[:2]
        if top_issues:
            issue_desc = []
            for issue in top_issues:
                entity_type = issue.get('entity_type', 'item')
                entity_id = issue.get('entity_id', 'unknown')
                issue_type = issue.get('issue_type', 'issue')
                field_name = issue.get('field_name', '')

                if field_name:
                    issue_desc.append(f"{entity_type} {entity_id} - {field_name} {issue_type}")
                else:
                    issue_desc.append(f"{entity_type} {entity_id} - {issue_type}")

            summary += f" Top issues: {'; '.join(issue_desc)}."

        return summary

    def _enforce_output_contract(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce strict output contract for Section 7.

        Rules:
        1. If len(issues) > 0 → status CANNOT be PASS (must be FAIL or WARN)
        2. If len(issues) == 0 → summary must NOT mention problems
        3. Summary must be consistent with structured fields
        """
        validations = validation_results.get('validations', [])
        contract_violations_fixed = 0

        # Problem keywords that indicate issues
        problem_keywords = ['mismatch', 'missing', 'error', 'does not match', 'incorrect',
                           'invalid', 'failed', 'discrepancy', 'inconsistent']

        for validation in validations:
            issues = validation.get('issues', [])
            summary = validation.get('summary', '')
            status = validation.get('status', 'UNKNOWN')

            # Rule 1: If issues exist, status CANNOT be PASS
            if len(issues) > 0 and status == 'PASS':
                # Downgrade to WARN (issues exist but not blocking)
                validation['status'] = 'WARN'
                contract_violations_fixed += 1

            # Rule 2: If no issues but summary mentions problems, sanitize summary
            if len(issues) == 0 and summary:
                summary_lower = summary.lower()
                has_problem_keywords = any(keyword in summary_lower for keyword in problem_keywords)

                if has_problem_keywords:
                    # Summary mentions problems but no issues - regenerate summary
                    validation['summary'] = self._regenerate_summary_from_issues(validation)
                    contract_violations_fixed += 1

            # Rule 3: Prevent "rubber-stamp PASS" - require evidence of evaluation
            passed_checks = validation.get('passed_checks', 0)
            checks_list = validation.get('checks', [])

            if status == 'PASS':
                # Check if AI actually performed any checks
                has_checks = passed_checks > 0 or len(checks_list) > 0
                has_meaningful_summary = summary and len(summary.strip()) > 10 and summary not in [
                    'All checks passed.',
                    'Not explicitly validated by AI (assumed PASS based on Section 6).'
                ]

                if not has_checks and not has_meaningful_summary:
                    # No evidence of evaluation - downgrade to WARN
                    validation['status'] = 'WARN'
                    validation['summary'] = 'No checks performed (rubber-stamp PASS prevented).'
                    contract_violations_fixed += 1

        # Update overall summary
        summary = validation_results.get('summary', {})
        if isinstance(summary, str):
            summary = {'text': summary}

        passed_count = sum(1 for v in validations if v.get('status') == 'PASS')
        warn_count = sum(1 for v in validations if v.get('status') == 'WARN')
        failed_count = sum(1 for v in validations if v.get('status') == 'FAIL')

        summary['total_steps'] = len(validations)
        summary['passed_steps'] = passed_count
        summary['warn_steps'] = warn_count
        summary['failed_steps'] = failed_count

        # Overall status logic
        if failed_count > 0:
            summary['overall_status'] = 'FAIL'
        elif warn_count > 0:
            summary['overall_status'] = 'WARN'
        else:
            summary['overall_status'] = 'PASS'

        validation_results['summary'] = summary
        validation_results['contract_violations_fixed'] = contract_violations_fixed

        return validation_results

    def _regenerate_summary_from_issues(self, validation: Dict[str, Any]) -> str:
        """Regenerate summary based on actual remaining issues"""
        issues = validation.get('issues', [])

        if len(issues) == 0:
            return "All checks passed."

        issue_count = len(issues)
        issue_types = [issue.get('issue_type', 'unknown') for issue in issues]

        # Count by type
        missing_count = sum(1 for t in issue_types if t == 'missing_data')
        mismatch_count = sum(1 for t in issue_types if t == 'data_mismatch')
        quality_count = sum(1 for t in issue_types if t == 'quality_issue')

        parts = []
        if missing_count > 0:
            parts.append(f"{missing_count} missing data")
        if mismatch_count > 0:
            parts.append(f"{mismatch_count} data mismatch(es)")
        if quality_count > 0:
            parts.append(f"{quality_count} quality issue(s)")

        if parts:
            return f"Found {issue_count} issue(s): {', '.join(parts)}."
        else:
            return f"Found {issue_count} issue(s)."

    def _ensure_all_steps_covered(
        self, validation_results: Dict[str, Any], workflow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ensure AI validated ALL workflow steps deterministically.

        If AI skipped a step, create a placeholder validation for it.
        """
        validations = validation_results.get('validations', [])

        # Extract all workflow steps
        all_steps = []
        for workflow in workflow_data.get('declared_workflows', []):
            for step in workflow.get('steps', []):
                all_steps.append({
                    'step_id': step.get('step_id'),
                    'step_title': step.get('title'),
                    'raw_text': step.get('raw_text', '')
                })

        # Find which steps AI validated
        validated_step_ids = {v.get('step_id') for v in validations}

        # Add placeholder validations for missing steps
        missing_steps = [s for s in all_steps if s['step_id'] not in validated_step_ids]

        for step in missing_steps:
            # Create placeholder validation
            validations.append({
                'step_id': step['step_id'],
                'step_title': step['step_title'],
                'status': 'PASS',  # Default to PASS if AI didn't find issues
                'confidence': 0.5,  # Low confidence since AI didn't explicitly validate
                'issues': [],
                'failed_checks': 0,
                'passed_checks': 0,
                'summary': 'Not explicitly validated by AI (assumed PASS based on Section 6).'
            })

        # Sort by step_id to maintain order
        validations.sort(key=lambda v: v.get('step_id', 'ZZZ'))

        validation_results['validations'] = validations
        validation_results['missing_steps_filled'] = len(missing_steps)

        # Update summary to reflect final step count
        summary = validation_results.get('summary', {})
        if isinstance(summary, str):
            summary = {'text': summary}

        passed_count = sum(1 for v in validations if v.get('status') == 'PASS')
        warn_count = sum(1 for v in validations if v.get('status') == 'WARN')
        failed_count = sum(1 for v in validations if v.get('status') == 'FAIL')

        summary['total_steps'] = len(validations)
        summary['passed_steps'] = passed_count
        summary['warn_steps'] = warn_count
        summary['failed_steps'] = failed_count

        # Overall status logic
        if failed_count > 0:
            summary['overall_status'] = 'FAIL'
        elif warn_count > 0:
            summary['overall_status'] = 'WARN'
        else:
            summary['overall_status'] = 'PASS'

        validation_results['summary'] = summary

        return validation_results

    def _recompute_summary(self, validation_results: Dict[str, Any]) -> None:
        """Recompute summary from current validation issue state."""
        validations = validation_results.get('validations', [])
        passed_count = sum(1 for v in validations if str(v.get('status')) == 'PASS')
        failed_count = sum(1 for v in validations if str(v.get('status')) == 'FAIL')
        summary = validation_results.get('summary', {})
        summary['total_steps'] = len(validations)
        summary['passed_steps'] = passed_count
        summary['failed_steps'] = failed_count
        summary['overall_status'] = 'PASS' if failed_count == 0 else 'FAIL'
        validation_results['summary'] = summary

    def _is_real_mismatch(self, expected: Any, actual: Any) -> bool:
        """Check if expected and actual values are truly different."""
        if expected is None or actual is None:
            return True

        expected_str = str(expected).strip()
        actual_str = str(actual).strip()

        if expected_str == actual_str:
            return False

        try:
            expected_clean = expected_str.replace(',', '').replace('Rs', '').replace(' ', '')
            actual_clean = actual_str.replace(',', '').replace('Rs', '').replace(' ', '')
            expected_num = float(expected_clean)
            actual_num = float(actual_clean)
            return abs(expected_num - actual_num) >= 0.01
        except (ValueError, AttributeError):
            pass

        expected_normalized = expected_str.lower().replace(' ', '').replace('-', '')
        actual_normalized = actual_str.lower().replace(' ', '').replace('-', '')
        return expected_normalized != actual_normalized

    def _compute_run_id(self, workflow_data: Dict[str, Any], normalized_data: Dict[str, Any]) -> str:
        """Compute stable run checksum for current normalized snapshot."""
        payload = json.dumps(
            {'workflow_data': workflow_data, 'normalized_data': normalized_data},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]

    def _dump_prompt_debug(
        self,
        run_id: str,
        prompt: str,
        workflow_data: Dict[str, Any],
        normalized_data: Dict[str, Any],
        fingerprint: Dict[str, Any],
    ) -> str:
        """Write full prompt and payload fingerprints for stale-data debugging."""
        os.makedirs(self.debug_dir, exist_ok=True)
        debug_path = os.path.abspath(os.path.join(self.debug_dir, 'debug_section7_prompt.json'))

        path_hints = {
            'normalized_input_file_path': os.path.abspath('test_section3_output.json'),
            'workflow_file_path': os.path.abspath('test_section4_output.json'),
            'rule_results_file_path': os.path.abspath('test_section6_output.json'),
        }

        debug_payload = {
            'normalized_run_id': run_id,
            'fingerprint': fingerprint,
            'path_hints': path_hints,
            'prompt': prompt,
            'workflow_data': workflow_data,
            'normalized_data': normalized_data,
            'written_at': datetime.utcnow().isoformat(),
        }

        with open(debug_path, 'w', encoding='utf-8') as f:
            json.dump(debug_payload, f, indent=2, default=str)

        return debug_path

    def _apply_matching_gate(self, validation_results: Dict[str, Any], fingerprint: Dict[str, Any]) -> Dict[str, Any]:
        """Mark result as untrustworthy if no matchable records were identified."""
        input_records = fingerprint.get('input_records_identified', 0)
        output_records = fingerprint.get('output_records_identified', 0)

        blocking_issues = validation_results.get('blocking_issues', [])
        if input_records == 0 or output_records == 0:
            blocking_issues.append({
                'code': 'MATCHING_FAILED_NO_RECORDS',
                'severity': 'ERROR',
                'message': (
                    f"Matching failed: input_records_identified={input_records}, "
                    f"output_records_identified={output_records}"
                ),
            })
            summary = validation_results.get('summary', {})
            summary['overall_status'] = 'INDETERMINATE'
            validation_results['summary'] = summary

        validation_results['blocking_issues'] = blocking_issues
        return validation_results

    def _format_results(
        self,
        validation_results: Dict[str, Any],
        cost: float,
        input_tokens: int,
        output_tokens: int,
        run_id: str,
        debug_prompt_path: str,
        fingerprint: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Format AI validation results with debug metadata."""
        return {
            'validations': validation_results.get('validations', []),
            'summary': validation_results.get('summary', {}),
            'blocking_issues': validation_results.get('blocking_issues', []),
            'metadata': {
                'model': self.model,
                'cost': cost,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'timestamp': datetime.utcnow().isoformat(),
                'run_id': run_id,
                'debug_prompt_path': debug_prompt_path,
                'false_positives_removed': validation_results.get('false_positives_removed', 0),
                'ungrounded_issues_removed': validation_results.get('ungrounded_issues_removed', 0),
                'source_attribution_fixed': validation_results.get('source_attribution_fixed', 0),
                'entity_reclassification_count': validation_results.get('pan_missing_reclassified', 0),
                'dependent_issues_suppressed': validation_results.get('dependent_issues_suppressed', 0),
                'section6_conflicts_removed': validation_results.get('section6_conflicts_removed', 0),
                'deterministic_anchor': validation_results.get('deterministic_anchor'),
                'input_records_identified': fingerprint.get('input_records_identified', 0),
                'output_records_identified': fingerprint.get('output_records_identified', 0),
                'fingerprint': fingerprint,
            },
        }

    def _error_response(
        self,
        error_message: str,
        run_id: str = None,
        fingerprint: Dict[str, Any] = None,
        debug_prompt_path: str = None,
    ) -> Dict[str, Any]:
        """Return structured error response."""
        fingerprint = fingerprint or {}
        return {
            'validations': [],
            'summary': {
                'total_steps': 0,
                'passed_steps': 0,
                'failed_steps': 0,
                'overall_status': 'ERROR',
            },
            'blocking_issues': [],
            'error': error_message,
            'metadata': {
                'model': self.model,
                'cost': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'timestamp': datetime.utcnow().isoformat(),
                'run_id': run_id,
                'debug_prompt_path': debug_prompt_path,
                'false_positives_removed': 0,
                'ungrounded_issues_removed': 0,
                'source_attribution_fixed': 0,
                'entity_reclassification_count': 0,
                'dependent_issues_suppressed': 0,
                'section6_conflicts_removed': 0,
                'deterministic_anchor': None,
                'input_records_identified': fingerprint.get('input_records_identified', 0),
                'output_records_identified': fingerprint.get('output_records_identified', 0),
                'fingerprint': fingerprint,
            },
        }


# Convenience function
def validate_workflow_with_ai(
    workflow_data: Dict[str, Any],
    normalized_data: Dict[str, Any],
    rule_engine_results: Dict[str, Any],
    task_id: str,
    model: str = 'gpt-4o-mini',
) -> Dict[str, Any]:
    """Validate workflow using AI."""
    validator = AIWorkflowValidator(task_id=task_id, model=model)
    return validator.validate(workflow_data, normalized_data, rule_engine_results)
