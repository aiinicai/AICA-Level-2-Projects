"""
engines/hallucination_guard.py — R K Muley & Co | Tax Notice Litigation Assistant v8.0

HallucinationGuard: 3-layer fact-check engine.
  Layer 1: ITA section number validation against known-valid set (deterministic)
  Layer 2: Case law citation check against verified library (deterministic)
  Layer 3 / Pass E: LLM adversarial self-review (optional, requires API call)

CRITICAL FIXES from v7:
  - run_pass_e() method now exists (v7 called it from UI but only layer3_check() existed)
  - ALL_KNOWN_CITATION_FINGERPRINTS is now correctly populated at module load
    (v7 had _ALL_KNOWN_CITATIONS = set() that was never filled)
  - Consistent return dict keys throughout
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from config import KNOWN_IT_SECTIONS
from data.case_laws import ALL_KNOWN_CITATION_FINGERPRINTS

logger = logging.getLogger("RKMuley.HallucinationGuard.v8")


def _normalise_section_ref(sec: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z\(\)]", "", sec)
    m = re.match(r"^(\d+[A-Za-z]*)(.*)$", cleaned)
    if not m:
        return cleaned.upper()
    return m.group(1).upper() + m.group(2).lower()


def _fallback_pass_e_report(raw: str) -> dict:
    """Return a usable Pass E report even when the model returns damaged JSON."""
    text = re.sub(r"```json|```", "", raw or "").strip()
    risk_m = re.search(r'"?hallucination_risk"?\s*:\s*"?([A-Za-z]+)', text, re.IGNORECASE)
    verdict_m = re.search(r'"?overall_verdict"?\s*:\s*"([^"\n\r]{1,500})', text, re.IGNORECASE)
    rec_m = re.search(r'"?recommendation"?\s*:\s*"([^"\n\r]{1,500})', text, re.IGNORECASE)
    risk = risk_m.group(1).title() if risk_m else "Medium"
    if risk not in {"Low", "Medium", "High"}:
        risk = "Medium"
    return {
        "hallucination_risk": risk,
        "overall_verdict": verdict_m.group(1) if verdict_m else "Pass E returned malformed JSON; review the raw response manually.",
        "issues": [{
            "type": "manual_review",
            "detail": "The model response could not be parsed as valid JSON. Automated Pass E findings were not trusted.",
            "location": "Pass E raw response",
            "severity": "Medium",
        }],
        "positives": [],
        "recommendation": rec_m.group(1) if rec_m else "Run Pass E again or review draft manually before submission.",
    }


class HallucinationGuard:
    """
    Three-layer anti-hallucination engine for litigation draft quality control.

    Layer 1 (deterministic): Validates all ITA section references.
    Layer 2 (deterministic): Identifies citations not in the verified library.
    Layer 3 / Pass E (LLM): Internal consistency audit via adversarial second-pass prompt.
    """

    # Section reference regex (handles "Section 148A(b)", "u/s 68", "Sec 271(1)(c)")
    _SEC_RE = re.compile(
        r"[Ss]ection\s+(\d{1,3}[A-Z]{0,4}(?:\(\d+\))?(?:\([a-z]+\))?)"
        r"|[Uu]/[Ss]\s+(\d{1,3}[A-Z]{0,4}(?:\(\d+\))?(?:\([a-z]+\))?)"
        r"|\bu/s\s+(\d{1,3}[A-Z]{0,4}(?:\(\d+\))?(?:\([a-z]+\))?)",
        re.UNICODE,
    )

    # Citation regex — captures "Party v. Party (Year) N ITR N (Court)" patterns
    _CIT_RE = re.compile(
        r"[A-Z][a-zA-Z\s&\.]+v\.\s*[A-Z][a-zA-Z\s&\.\(\)]+"
        r"(?:\(\d{4}\))?(?:\s+\d+\s+ITR\s+\d+)?(?:\s+\([A-Z]{2,5}\.?\))?",
        re.MULTILINE,
    )

    @classmethod
    def check(cls, draft: str, user_citations: Optional[list[str]] = None) -> dict:
        """
        Run Layers 1 and 2 (deterministic — instant, no API call).

        Returns dict with consistent keys:
            invalid_sections      list[str]   — section refs not in KNOWN_IT_SECTIONS
            fabricated_citations  list[str]   — citations in neither library nor user-provided
            unverified_citations  list[str]   — user-provided but not in verified library
            verified_citations    list[str]   — confirmed in verified library
            layer1_pass           bool
            layer2_pass           bool
            overall_clean         bool
            summary               str
        """
        user_citations = user_citations or []

        report: dict = {
            "invalid_sections":     [],
            "fabricated_citations": [],
            "unverified_citations": [],
            "verified_citations":   [],
            "layer1_pass":          True,
            "layer2_pass":          True,
            "overall_clean":        True,
            "summary":              "",
        }

        # ── Layer 1: Section validation ───────────────────────────────────
        found_secs: set[str] = set()
        for m in cls._SEC_RE.finditer(draft):
            sec = next((g for g in m.groups() if g), None)
            if sec:
                found_secs.add(_normalise_section_ref(sec))

        invalid = [
            s for s in found_secs
            if s not in KNOWN_IT_SECTIONS
            and s not in {"ITA", "IT", "ACT", ""}
            and len(s) > 1
        ]
        if invalid:
            report["invalid_sections"] = invalid[:8]
            report["layer1_pass"] = False

        # ── Layer 2: Citation check ───────────────────────────────────────
        known_fps = ALL_KNOWN_CITATION_FINGERPRINTS  # populated at module load
        user_lower = {c.strip().lower() for c in user_citations if len(c.strip()) > 5}

        fabricated, unverified, verified_list = [], [], []

        for raw in cls._CIT_RE.findall(draft):
            cit = raw.strip()
            if len(cit) < 10:
                continue
            cl = cit.lower()
            in_lib  = any(cl in k or k in cl for k in known_fps)
            in_user = any(cl in u or u in cl for u in user_lower)
            if in_lib:
                verified_list.append(cit)
            elif in_user:
                unverified.append(cit)
            else:
                fabricated.append(cit)

        report["fabricated_citations"] = list(dict.fromkeys(fabricated))[:5]
        report["unverified_citations"] = list(dict.fromkeys(unverified))[:10]
        report["verified_citations"]   = list(dict.fromkeys(verified_list))[:20]

        if report["fabricated_citations"]:
            report["layer2_pass"] = False

        report["overall_clean"] = report["layer1_pass"] and report["layer2_pass"]

        if report["overall_clean"]:
            report["summary"] = (
                f"✅ CLEAN — {len(report['verified_citations'])} verified, "
                f"{len(report['unverified_citations'])} user-supplied, "
                f"0 fabricated, 0 invalid sections."
            )
        else:
            issues = []
            if not report["layer1_pass"]:
                issues.append(f"{len(invalid)} invalid ITA sections: {invalid[:3]}")
            if not report["layer2_pass"]:
                issues.append(
                    f"{len(report['fabricated_citations'])} potentially fabricated citations"
                )
            report["summary"] = "⚠️ ISSUES: " + "; ".join(issues)

        return report

    @classmethod
    def run_pass_e(
        cls,
        api_key: str,
        model_name: str,
        draft: str,
        extraction: str,
    ) -> dict:
        """
        Pass E: LLM adversarial self-review (Layer 3).

        The LLM is asked to audit its own draft as a strict legal quality reviewer.
        Returns structured JSON report.

        This is the method called from Tab 6 UI (was missing in v7).

        Return dict keys:
            hallucination_risk   str   "Low" | "Medium" | "High"
            overall_verdict      str
            issues               list[dict]
            positives            list[str]
            recommendation       str
            layer3_available     bool
            raw_response         str   (for debugging)
            error                str   (if failed)
        """
        from data.prompts import PASS_E_ADVERSARIAL_PROMPT
        from services.gemini_service import call_gemini, APICallError

        empty_result: dict = {
            "hallucination_risk": "Unknown",
            "overall_verdict":    "Pass E could not be completed.",
            "issues":             [],
            "positives":          [],
            "recommendation":     "Re-run Pass E or review manually.",
            "layer3_available":   False,
            "raw_response":       "",
            "error":              "",
        }

        prompt = PASS_E_ADVERSARIAL_PROMPT.format(
            extraction=extraction[:2500],
            draft=draft[:5000],
        )

        try:
            # Use very low temperature for deterministic audit output
            raw = call_gemini(
                model_name=model_name,
                prompt=prompt,
                temperature=0.05,
                max_tokens=1500,
                step="pass_e",
                inject_guard=False,  # Pass E IS the guard — no prefix needed
            )

            # Strip markdown fences if model wraps JSON despite instructions
            clean = re.sub(r"```json|```", "", raw).strip()
            # Handle case where model returns explanation before/after JSON
            json_match = re.search(r"\{.*\}", clean, re.DOTALL)
            if json_match:
                clean = json_match.group(0)

            parsed = json.loads(clean)

            return {
                "hallucination_risk": parsed.get("hallucination_risk", "Unknown"),
                "overall_verdict":    parsed.get("overall_verdict", ""),
                "issues":             parsed.get("issues", []),
                "positives":          parsed.get("positives", []),
                "recommendation":     parsed.get("recommendation", ""),
                "layer3_available":   True,
                "raw_response":       raw,
                "error":              "",
            }

        except json.JSONDecodeError as exc:
            logger.warning("Pass E JSON parse failed: %s | Raw: %s", exc, raw[:200] if 'raw' in dir() else "N/A")
            fallback = _fallback_pass_e_report(raw if 'raw' in dir() else "")
            return {**fallback,
                    "error": "",
                    "raw_response": raw if 'raw' in dir() else "",
                    "layer3_available": True,
                    "parse_warning": f"JSON parse failed: {exc}"}
        except APICallError as exc:
            logger.warning("Pass E API call failed: %s", exc)
            return {**empty_result, "error": str(exc)}
        except Exception as exc:
            logger.error("Pass E unexpected error: %s", exc)
            return {**empty_result, "error": str(exc)}
