"""
engines/reply_scorer.py — R K Muley & Co | Tax Notice Litigation Assistant v8.0

ReplySuccessScorer: 7-dimension weighted reply quality scorer.
NoticeProbabilityPredictor: Demand confirmation risk estimator.

CRITICAL FIXES from v7:
  - ReplySuccessScorer.score() now returns keys:
      "score" (not "total"), "color" (not "colour"), "grade" (not "band"),
      "breakdown", "recommendation"
    The v7 UI accessed rss["colour"], rss["total"], rss["band"] — all KeyErrors.

  - NoticeProbabilityPredictor.predict() now returns keys:
      "score", "color" (not "colour"), "verdict" (not "band"),
      "factors", "base"
    The v7 UI accessed npp["colour"], npp["band"] — all KeyErrors.

  - "breakdown" in ReplySuccessScorer now returns a dict keyed by dimension name
    so the Tab 6 UI can iterate: for dim, data in rss["breakdown"].items()
"""
from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger("RKMuley.Scorer.v8")


# ── Notice Probability Predictor ──────────────────────────────────────────────
_F1_FACTORS: dict[str, dict] = {
    "din_absent":         {"w": -30, "lbl": "DIN absent — notice void risk"},
    "time_barred":        {"w": -35, "lbl": "Notice prima facie time-barred u/s 149"},
    "148_no_148a":        {"w": -25, "lbl": "Sec 148 without confirmed 148A compliance"},
    "sec_68_evidence":    {"w": -20, "lbl": "Sec 68 — all 3 limbs documented"},
    "sec_68_no_evidence": {"w": +25, "lbl": "Sec 68 — evidence incomplete"},
    "sec_143_1":          {"w": -15, "lbl": "143(1) intimation — limited AO scope"},
    "scrutiny":           {"w": +15, "lbl": "Scrutiny/143(3)/144 assessment"},
    "high_quantum":       {"w": +20, "lbl": "Demand > Rs. 10 lakhs"},
    "penalty_invoked":    {"w": +15, "lbl": "Penalty sections invoked"},
    "prosecution":        {"w": +25, "lbl": "Prosecution risk indicated"},
    "tds_only":           {"w": -25, "lbl": "Pure TDS mismatch — CBDT Circular applies"},
    "vault_win":          {"w": -15, "lbl": "Firm has prior win on similar issue"},
    "vault_loss":         {"w": +10, "lbl": "Firm has prior loss on similar issue"},
    "admission_risk":     {"w": +10, "lbl": "Admission risks in draft"},
}


class NoticeProbabilityPredictor:
    """
    Deterministic multi-factor demand probability engine.
    Base: 50%. Each factor adjusts ±. Final: clipped to 5–95%.
    Lower score = better for taxpayer.

    Return dict keys (FIXED from v7):
        score     int       0–100 (demand confirmation probability)
        base      int       always 50
        color     str       hex color for UI (NOT "colour")
        verdict   str       human-readable risk level (NOT "band")
        factors   list[dict]
    """

    @classmethod
    def predict(
        cls,
        extraction: str,
        proc_flags: list,
        evidence_gaps: list,
        admission_findings: list,
        vault_similar: list,
    ) -> dict:
        score = 50
        factors: list[dict] = []
        tl = extraction.lower()

        def _add(key: str, direction: str) -> None:
            nonlocal score
            f = _F1_FACTORS[key]
            score += f["w"]
            factors.append({
                "factor":    f["lbl"],
                "change":    f["w"],
                "direction": direction,
            })

        if any("🔴 DIN" in f for f in proc_flags):   _add("din_absent",         "favours_taxpayer")
        if any("TIME-BARRED" in f for f in proc_flags): _add("time_barred",      "favours_taxpayer")
        if any("REASSESSMENT" in f for f in proc_flags): _add("148_no_148a",     "favours_taxpayer")
        if "143(3)" in tl or "scrutiny" in tl or "144" in tl: _add("scrutiny",   "favours_ao")
        if "143(1)" in tl or "intimation" in tl:       _add("sec_143_1",         "favours_taxpayer")
        if "68" in tl or "cash credit" in tl:
            if evidence_gaps:
                _add("sec_68_no_evidence", "favours_ao")
            else:
                _add("sec_68_evidence", "favours_taxpayer")
        if "tds" in tl and "26as" in tl:               _add("tds_only",          "favours_taxpayer")

        amt_m = re.search(r"(?:rs\.?|₹)\s*([\d,]+)", tl)
        if amt_m:
            try:
                if int(amt_m.group(1).replace(",", "")) >= 1_000_000:
                    _add("high_quantum", "favours_ao")
            except ValueError:
                pass

        if "270a" in tl or "271" in tl:  _add("penalty_invoked", "favours_ao")
        if "276" in tl or "prosecution" in tl: _add("prosecution", "favours_ao")
        if len(admission_findings) > 2:   _add("admission_risk",  "favours_ao")

        for entry in vault_similar[:3]:
            oc = entry.get("outcome", "")
            if oc == "Win":
                _add("vault_win",  "favours_taxpayer")
            elif oc == "Loss":
                _add("vault_loss", "favours_ao")

        final = max(5, min(95, score))
        return {
            "score":   final,
            "base":    50,
            "color":   cls._color(final),   # FIX: was "colour" in v7
            "verdict": cls._verdict(final), # FIX: was "band" in v7
            "factors": factors,
        }

    @staticmethod
    def _verdict(s: int) -> str:
        if s >= 70:  return "HIGH RISK"
        if s >= 45:  return "MODERATE RISK"
        return "LOW RISK"

    @staticmethod
    def _color(s: int) -> str:
        if s >= 70:  return "#c62828"   # red
        if s >= 45:  return "#e65100"   # orange
        return "#2e7d32"                # green


# ── Reply Success Scorer ──────────────────────────────────────────────────────
class ReplySuccessScorer:
    """
    Scores draft reply quality on 0–100.

    Return dict keys (FIXED from v7):
        score           int       0–100 (NOT "total")
        color           str       hex color (NOT "colour")
        grade           str       A/B/C/D/F label (NOT "band")
        breakdown       dict      keyed by dimension name → {weight, raw, note, status}
        recommendation  str
    """

    @classmethod
    def score(
        cls,
        draft: str,
        proc_flags: list,
        admission_findings: list,
        hall_report: dict,
        evidence_gaps: list,
        vault_similar: list,
        matched_laws: str,
    ) -> dict:
        sc = 50
        breakdown: dict[str, dict] = {}

        def _dim(
            name: str,
            weight: int,
            condition: bool,
            pos_score: int,
            neg_score: int,
            pass_note: str,
            fail_note: str,
        ) -> None:
            nonlocal sc
            if condition:
                sc += pos_score
                breakdown[name] = {
                    "weight": weight,
                    "raw":    min(100, 50 + pos_score),
                    "note":   pass_note,
                    "status": "pass",
                }
            else:
                sc += neg_score
                breakdown[name] = {
                    "weight": weight,
                    "raw":    max(0, 50 + neg_score),
                    "note":   fail_note,
                    "status": "fail" if neg_score < -10 else "warn",
                }

        # 1. Procedural defects raised
        if proc_flags:
            din_raised = "19/2019" in draft or "Document Identification" in draft
            tb_raised  = "149" in draft or "time-barred" in draft.lower()
            din_flag   = any("DIN" in f for f in proc_flags)
            tb_flag    = any("TIME-BARRED" in f for f in proc_flags)
            if din_flag:
                _dim("DIN Defect Raised", 20, din_raised, 35, -25,
                     "DIN defect raised with Circular 19/2019 citation",
                     "DIN defect NOT raised — critical miss")
            if tb_flag:
                _dim("Time-Bar Objection", 15, tb_raised, 20, -20,
                     "Sec 149 limitation raised as threshold objection",
                     "Notice time-barred but limitation objection absent")

        # 2. Case law integrity
        fab = hall_report.get("fabricated_citations", [])
        _dim("Case Law Integrity", 20, not fab, 20, -40,
             f"{len(hall_report.get('verified_citations', []))} verified citations used",
             f"FABRICATED citations found: {fab[:2]}")

        # 3. First-person voice
        from engines.draft_risk_checker import detect_third_person
        viol = detect_third_person(draft)
        _dim("First-Person Voice", 10, not viol, 5, -20,
             "Consistent first-person voice throughout",
             f"Third-person violations: {viol[:2]}")

        # 4. Admission risk
        _dim("Admission Risk", 15, not admission_findings, 10, -30,
             "No confessionary language detected",
             f"{len(admission_findings)} risky phrases — review before submission")

        # 5. Without Prejudice (for partial admissions)
        _dim("Without Prejudice Compliance", 5, "without prejudice" in draft.lower(), 8, 0,
             "'Without Prejudice' qualifier present",
             "Not applicable / missing (only required for partial admissions)")

        # 6. Annexure Schedule
        _dim("Annexure Schedule", 5, "ANNEXURE" in draft.upper(), 5, 0,
             "Documents indexed in Annexure Schedule",
             "Annexure schedule missing — add before submission")

        # 7. Evidence completeness
        _dim("Evidence Completeness", 18, not evidence_gaps, 0, -25,
             "Evidence matrix appears complete",
             f"Evidence gaps: {evidence_gaps[:2]}")

        # 8. Section validity
        inv = hall_report.get("invalid_sections", [])
        _dim("Section Reference Validity", 5, not inv, 5, -15,
             "All ITA sections valid",
             f"Invalid/non-existent sections: {inv}")

        # 9. Vault win matches
        for entry in vault_similar[:2]:
            if entry.get("outcome") == "Win":
                sc += 15
                breakdown["Vault Win Match"] = {
                    "weight": 7,
                    "raw":    80,
                    "note":   f"Firm won similar: {entry.get('issue_type', '')}",
                    "status": "pass",
                }
                break

        final = max(0, min(100, sc))
        return {
            "score":          final,               # FIX: was "total" in v7
            "color":          cls._color(final),   # FIX: was "colour" in v7
            "grade":          cls._grade(final),   # FIX: was "band" in v7
            "breakdown":      breakdown,
            "recommendation": cls._rec(final, breakdown),
        }

    @staticmethod
    def _grade(s: int) -> str:
        if s >= 80: return "A — Strong"
        if s >= 65: return "B — Good"
        if s >= 50: return "C — Adequate"
        if s >= 35: return "D — Needs Work"
        return "F — Do Not Submit"

    @staticmethod
    def _color(s: int) -> str:
        if s >= 65: return "#2e7d32"   # green
        if s >= 45: return "#e65100"   # orange
        return "#c62828"               # red

    @staticmethod
    def _rec(score: int, breakdown: dict) -> str:
        fails = [data["note"] for data in breakdown.values() if data["status"] == "fail"]
        if score >= 80: return "Reply is ready for submission."
        if score >= 65: return f"Reply is good. Address: {fails[0] if fails else 'Minor refinements possible'}."
        if score >= 50: return f"Improve before submission: {'; '.join(fails[:2])}."
        return f"Do not submit without significant revision: {'; '.join(fails[:3])}."
