"""
Panel validation ("the court") — optional, env-gated.

When AI_PANEL_ENABLED is on, instead of a single AI reviewer we convene a panel:
  - N neutral JURORS (diverse models and/or sampled temperatures), and
    Models are routed by name (services/llm_client), so AI_JURY_MODELS /
    AI_CRITIC_MODEL may mix providers (e.g. gpt-4o-mini + claude-*) for genuine
    cross-provider independence rather than one model at several temperatures.
  - one adversarial CRITIC whose job is to assume the output is wrong and hunt for
    concrete, evidence-cited defects.

Each reviewer is a full GenericValidator run, so every reviewer's verdicts are
already grounded (a FAIL must cite real data) and truncation-honest. Our own
deterministic code is the JUDGE: it aggregates votes per criterion with a
corroboration rule (a defect needs ≥2 independent supporters to become a FAIL,
so a lone over-eager critic produces UNCLEAR, not a false positive) and a
confidence threshold (verdicts below it are returned as UNCLEAR for human review).

Deterministic results from services/generic_checks.py remain authoritative and
are not voted on. The output shape matches GenericValidator.validate() plus a
per-criterion `confidence` and `votes`.
"""

import json
import logging
import math
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.check_spec import CheckSpec, CriterionSeverity
from services.generic_validator import (
    GenericValidator,
    _build_data_index,
    _cited_tokens,
    _is_grounded,
)

logger = logging.getLogger(__name__)

_BLOCKING = {CriterionSeverity.CRITICAL, CriterionSeverity.ERROR}

TIEBREAKER_PROMPT = (
    "You are the adjudicating judge for a review panel that DISAGREED on one criterion. "
    "Read the criterion and each reviewer's verdict with its cited evidence, then decide the "
    "correct verdict by REASONING about which evidence is actually right — do not just count "
    "votes. Cite the concrete value(s) from the data that decide it; never invent values. "
    'Respond ONLY with JSON: {"status":"PASS|FAIL|UNCLEAR","evidence":"...","explanation":"..."}'
)

ADVERSARIAL_PROMPT = (
    "You are an adversarial QA auditor. ASSUME the output is wrong and your job is to "
    "PROVE it. For each criterion, actively hunt for concrete defects, errors, omissions, "
    "wrong values, or inconsistencies, and cite the exact values/rows/fields from the data "
    "that demonstrate the defect. Mark PASS ONLY if, after genuinely trying, you cannot find "
    "any defect. Never invent values — cite only what actually appears in the data. If the "
    "data is a truncated SAMPLE, do not claim full-coverage PASS; return UNCLEAR. "
    "Respond ONLY with valid JSON in the required shape."
)


# ==================== configuration ====================

def panel_enabled() -> bool:
    return os.getenv("AI_PANEL_ENABLED", "false").strip().lower() == "true"


def _panel_mode() -> str:
    """on | off | auto. Default is AUTO (the system decides)."""
    raw = os.getenv("AI_PANEL_ENABLED", "auto").strip().lower()
    if raw in ("true", "on", "1", "yes"):
        return "on"
    if raw in ("false", "off", "0", "no"):
        return "off"
    return "auto"


def should_convene_panel(check_spec) -> bool:
    """Decide automatically whether this task warrants the panel.

    The panel earns its extra cost on HIGH-STAKES JUDGMENT criteria — blocking
    (critical/error) criteria that need reasoning rather than a tool/deterministic
    check (semantic or hybrid). When enough of those exist, a multi-model vote
    materially reduces error, so we convene it; otherwise the agentic tools-or-AI
    default is sufficient. `AI_PANEL_ENABLED=on|off` forces the decision.
    """
    mode = _panel_mode()
    if mode == "on":
        return True
    if mode == "off":
        return False
    min_n = int(os.getenv("AI_PANEL_AUTO_MIN_SEMANTIC", "3"))
    blocking_judgment = sum(
        1 for c in check_spec.criteria
        if c.severity.value in ("critical", "error") and c.type.value in ("semantic", "hybrid")
    )
    return blocking_judgment >= min_n


def _jury_models() -> List[str]:
    raw = os.getenv("AI_JURY_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    base = os.getenv("AI_VALIDATION_MODEL") or os.getenv("AI_PRIMARY_MODEL", "gpt-4o-mini")
    return [base]


def _jury_size() -> int:
    try:
        return max(1, int(os.getenv("AI_JURY_SIZE", "3")))
    except ValueError:
        return 3


def _critic_enabled() -> bool:
    return os.getenv("AI_CRITIC_ENABLED", "true").strip().lower() == "true"


def _confidence_threshold() -> float:
    try:
        return float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.67"))
    except ValueError:
        return 0.67


def _tiebreaker_enabled() -> bool:
    return os.getenv("AI_PANEL_TIEBREAKER_ENABLED", "false").strip().lower() == "true"


def _temperatures(n: int) -> List[float]:
    if n <= 1:
        return [0.1]
    return [round(0.8 * i / (n - 1), 2) for i in range(n)]


# ==================== panel ====================

class PanelValidator:
    """Convene jurors + an adversarial critic; aggregate deterministically."""

    def __init__(self, api_key: Optional[str] = None, jury_models: Optional[List[str]] = None,
                 jury_size: Optional[int] = None, critic_enabled: Optional[bool] = None,
                 critic_model: Optional[str] = None, confidence_threshold: Optional[float] = None):
        self.api_key = api_key
        self.jury_models = jury_models or _jury_models()
        self.jury_size = jury_size if jury_size is not None else _jury_size()
        self.critic_enabled = _critic_enabled() if critic_enabled is None else critic_enabled
        self.critic_model = critic_model or os.getenv("AI_CRITIC_MODEL") or self.jury_models[0]
        self.threshold = confidence_threshold if confidence_threshold is not None else _confidence_threshold()
        # Optional LLM tie-breaker: adjudicates ONLY criteria where reviewers genuinely
        # disagree (a PASS/FAIL split that mechanical counting leaves UNCLEAR). The code
        # still clamps its result — it can't override deterministic, ground-less FAIL, or
        # PASS a blocking criterion below confidence.
        self.tiebreaker_enabled = _tiebreaker_enabled()
        self.tiebreaker_model = os.getenv("AI_PANEL_TIEBREAKER_MODEL") or self.jury_models[0]

    def _build_reviewers(self):
        reviewers = []
        temps = _temperatures(self.jury_size)
        for i in range(self.jury_size):
            model = self.jury_models[i % len(self.jury_models)]
            reviewers.append(("juror", GenericValidator(model=model, api_key=self.api_key, temperature=temps[i])))
        if self.critic_enabled:
            reviewers.append(("critic", GenericValidator(
                model=self.critic_model, api_key=self.api_key, temperature=0.2,
                system_prompt=ADVERSARIAL_PROMPT)))
        return reviewers

    def validate(self, check_spec: CheckSpec, normalized_data: Dict[str, Any],
                 workflow_data: Optional[Dict[str, Any]] = None,
                 deterministic_results: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        det = deterministic_results or {}
        if not check_spec.criteria:
            return GenericValidator(api_key=self.api_key).validate(
                check_spec, normalized_data, workflow_data, det)

        reviewer_results = []  # list of (role, {id: verdict})
        num_jurors = 0
        for role, validator in self._build_reviewers():
            try:
                res = validator.validate(check_spec, normalized_data, workflow_data, det)
            except Exception as e:  # noqa: BLE001 - one reviewer failing must not kill the panel
                logger.warning("Panel reviewer (%s) failed: %s", role, e)
                continue
            by_id = {r["id"]: r for r in res.get("criteria_results", [])}
            reviewer_results.append((role, by_id))
            if role == "juror":
                num_jurors += 1

        if not reviewer_results:
            # whole panel unavailable -> fall back to a single validator
            return GenericValidator(api_key=self.api_key).validate(
                check_spec, normalized_data, workflow_data, det)

        return self._aggregate(check_spec, det, reviewer_results, num_jurors, normalized_data)

    # -- deterministic judge ----------------------------------------------

    def _aggregate(self, check_spec, det, reviewer_results, num_jurors, normalized_data=None) -> Dict[str, Any]:
        n_reviewers = len(reviewer_results)
        results: List[Dict[str, Any]] = []
        data_index = None  # built lazily only if the tie-breaker actually runs
        tiebreaks = 0

        for c in check_spec.criteria:
            if c.id in det:
                d = det[c.id]
                results.append(self._row(c, str(d.get("status", "UNCLEAR")).upper(),
                                         1.0, d.get("detail", ""), "deterministic",
                                         {"deterministic": 1}, "", "full"))
                continue

            votes = [(role, by_id.get(c.id, {})) for role, by_id in reviewer_results]
            # most conservative coverage across reviewers (sampled wins over full)
            coverage = "sampled" if any(v.get("coverage") == "sampled" for _r, v in votes) else "full"
            statuses = [str(v.get("status", "UNCLEAR")).upper() for _role, v in votes]
            n = len(statuses)
            pass_n = statuses.count("PASS")
            fail_n = statuses.count("FAIL")
            unclear_n = statuses.count("UNCLEAR")
            fail_votes = [(role, v) for role, v in votes if str(v.get("status")).upper() == "FAIL"]

            # corroboration: a defect needs >=2 supporters (or critic-only mode)
            if fail_n >= 2 or (fail_n >= 1 and num_jurors == 0):
                status, winners = "FAIL", fail_n
                evidence = self._pick_evidence(fail_votes, prefer="critic")
            elif fail_n == 1:
                status, winners = "UNCLEAR", max(unclear_n, 1)
                lone = self._pick_evidence(fail_votes)
                evidence = f"Reviewers disagree (1 flagged a defect): {lone}".strip()
            elif pass_n >= math.ceil(n / 2) and fail_n == 0:
                status, winners = "PASS", pass_n
                evidence = self._pick_evidence([(r, v) for r, v in votes if str(v.get("status")).upper() == "PASS"])
            else:
                status, winners = "UNCLEAR", max(pass_n, unclear_n)
                evidence = "No confident agreement among reviewers."

            confidence = round(winners / n, 2) if n else 0.0
            note = ""

            # Confidence gate applies to PASS only: never declare a blocking criterion
            # "passed" without enough agreement. FAIL precision is handled by the >=2
            # corroboration rule above (a grounded defect 2 reviewers found is worth
            # surfacing even when contested; the confidence is shown to the human).
            if status == "PASS" and c.severity in _BLOCKING and confidence < self.threshold:
                note = f"low panel confidence {confidence} (< {self.threshold})"
                status = "UNCLEAR"

            # Scoped LLM tie-breaker: only on genuine disagreement (PASS vs FAIL split)
            # that mechanical counting left UNCLEAR. The code still clamps the result.
            decided_by = "panel"
            if self.tiebreaker_enabled and status == "UNCLEAR" and pass_n >= 1 and fail_n >= 1:
                if data_index is None:
                    data_index = _build_data_index(normalized_data or {})
                status, evidence, note, broke = self._apply_tiebreak(
                    c, votes, status, evidence, confidence, data_index)
                if broke:
                    decided_by, tiebreaks = "panel+tiebreak", tiebreaks + 1

            results.append(self._row(c, status, confidence, evidence, decided_by,
                                     {"PASS": pass_n, "FAIL": fail_n, "UNCLEAR": unclear_n}, note, coverage))

        result = self._summarize(check_spec, results, n_reviewers, num_jurors)
        if self.tiebreaker_enabled:
            result["metadata"]["tiebreaker_model"] = self.tiebreaker_model
            result["metadata"]["tiebreaks"] = tiebreaks
        return result

    # -- scoped LLM tie-breaker (clamped by code) -------------------------

    def _tiebreak_complete(self, prompt: str) -> str:
        from services.llm_client import complete
        return complete(model=self.tiebreaker_model, system_prompt=TIEBREAKER_PROMPT,
                        user_prompt=prompt, temperature=0.0, api_key=self.api_key, json_mode=True)

    def _apply_tiebreak(self, c, votes, status, evidence, confidence, data_index):
        """Ask the judge LLM to resolve a contested criterion, then clamp the result.

        Returns (status, evidence, note, broke). The code keeps the guarantees:
        a tie-break FAIL must be grounded; a tie-break PASS on a blocking criterion
        below the confidence threshold stays UNCLEAR.
        """
        values, blob = data_index
        lines = []
        for role, v in votes:
            st = str(v.get("status", "UNCLEAR")).upper()
            ev = v.get("evidence") or v.get("explanation") or ""
            lines.append(f"- {role}: {st} — {ev}")
        prompt = (f"CRITERION ({c.severity.value}): {c.statement}\n"
                  + (f"how_to_verify: {c.how_to_verify}\n" if c.how_to_verify else "")
                  + "\nREVIEWERS DISAGREE:\n" + "\n".join(lines)
                  + "\n\nAdjudicate by reasoning about the evidence. Respond ONLY with the JSON.")
        try:
            tb = json.loads(self._tiebreak_complete(prompt))
        except Exception as e:  # noqa: BLE001 - a tie-breaker failure must not break the panel
            logger.warning("Tie-breaker failed for %s: %s", c.id, e)
            return status, evidence, "tie-breaker unavailable", False
        if not isinstance(tb, dict):
            return status, evidence, "tie-breaker returned no verdict", False

        tb_status = str(tb.get("status", "UNCLEAR")).upper()
        tb_ev = str(tb.get("evidence") or tb.get("explanation") or "").strip()

        if tb_status == "FAIL":
            cited = _cited_tokens(tb_ev)
            if cited and any(_is_grounded(t, values, blob) for t in cited):
                return "FAIL", tb_ev, "resolved by tie-breaker", True
            return status, evidence, "tie-breaker flagged a defect but it was ungrounded; left for review", False
        if tb_status == "PASS":
            if c.severity in _BLOCKING and confidence < self.threshold:
                return status, evidence, "tie-breaker passed but confidence gate keeps it UNCLEAR", False
            return "PASS", (tb_ev or evidence), "resolved by tie-breaker", True
        return status, evidence, "tie-breaker could not decide", False

    def _pick_evidence(self, role_votes, prefer: str = None) -> str:
        if prefer:
            for role, v in role_votes:
                if role == prefer and (v.get("evidence") or v.get("explanation")):
                    return str(v.get("evidence") or v.get("explanation"))
        for _role, v in role_votes:
            if v.get("evidence") or v.get("explanation"):
                return str(v.get("evidence") or v.get("explanation"))
        return ""

    def _row(self, c, status, confidence, evidence, decided_by, votes, note, coverage="full") -> Dict[str, Any]:
        return {
            "id": c.id, "statement": c.statement, "type": c.type.value,
            "severity": c.severity.value, "source": c.source.value,
            "status": status, "confidence": confidence, "evidence": evidence,
            "explanation": evidence, "decided_by": decided_by, "votes": votes,
            "note": note, "coverage": coverage,
        }

    def _summarize(self, check_spec, results, n_reviewers, num_jurors) -> Dict[str, Any]:
        sev_by_id = {c.id: c.severity for c in check_spec.criteria}
        passed = sum(1 for r in results if r["status"] == "PASS")
        failed = sum(1 for r in results if r["status"] == "FAIL")
        unclear = sum(1 for r in results if r["status"] == "UNCLEAR")
        blocking_fail = any(r["status"] == "FAIL" and sev_by_id.get(r["id"]) in _BLOCKING for r in results)
        blocking_unclear = any(r["status"] == "UNCLEAR" and sev_by_id.get(r["id"]) in _BLOCKING for r in results)

        if blocking_fail:
            overall = "FAIL"
        elif failed:
            overall = "WARN"
        elif blocking_unclear:
            overall = "INDETERMINATE"
        else:
            overall = "PASS"

        blocking_conf = [r["confidence"] for r in results if sev_by_id.get(r["id"]) in _BLOCKING]
        overall_confidence = round(min(blocking_conf), 2) if blocking_conf else 1.0

        return {
            "task_summary": check_spec.task_summary,
            "criteria_results": results,
            "summary": {
                "total": len(results), "passed": passed, "failed": failed, "unclear": unclear,
                "overall_status": overall, "overall_confidence": overall_confidence,
            },
            "metadata": {
                "validator": "panel",
                "jurors": num_jurors,
                "critic": self.critic_enabled,
                "reviewers": n_reviewers,
                "confidence_threshold": self.threshold,
                "jury_models": self.jury_models,
                "timestamp": datetime.utcnow().isoformat(),
            },
        }
