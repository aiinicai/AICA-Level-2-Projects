"""
engines/draft_risk_checker.py — R K Muley & Co | Tax Notice Litigation Assistant v8.0

DraftRiskChecker: 7-dimension pre-submission audit.

CRITICAL FIXES from v7:
  - run_passes_a_to_d() method now exists (v7 called it from UI but it didn't exist)
  - _detect_third_person / _detect_markdown no longer called as undefined names
    (v7 called _detect_third_person but only detect_third_person existed — NameError)
  - Pass A through D are now returned in a consistent list[dict] format
    that matches exactly what the Tab 6 UI renders
"""
from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger("RKMuley.DraftRiskChecker.v8")


def _normalise_section_ref(sec: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z\(\)]", "", sec)
    m = re.match(r"^(\d+[A-Za-z]*)(.*)$", cleaned)
    if not m:
        return cleaned.upper()
    return m.group(1).upper() + m.group(2).lower()


# ── Text Quality Utilities ────────────────────────────────────────────────────
# These are module-level functions — no naming ambiguity.

def detect_third_person(text: str) -> list[str]:
    """Return list of third-person violation phrases found in text."""
    patterns = [
        r"the assessee",
        r"the taxpayer",
        r"his/her",
        r"his or her",
        r"\bhe/she\b",
        r"it is submitted on behalf",
        r"the applicant",
        r"the petitioner",
        r"the deponent",
        r"the respondent assessee",
        r"on behalf of the assessee",
    ]
    found = []
    for p in patterns:
        matches = re.findall(p, text, re.IGNORECASE)
        if matches:
            found.append(f"'{matches[0]}' ×{len(matches)}")
    return found


def detect_markdown_residue(text: str) -> list[str]:
    """Return list of markdown artefacts found in text."""
    issues = []
    if re.search(r"\*{1,3}[^\s]", text):
        issues.append("Asterisks (*) found")
    if re.search(r"^#{1,6}\s", text, re.MULTILINE):
        issues.append("Hash headers (#) found")
    if re.search(r"^\s*[-•]\s", text, re.MULTILINE):
        issues.append("Bullet points found")
    if re.search(r"_{1,2}[^_]+_{1,2}", text):
        issues.append("Underscores (_) used for emphasis")
    return issues


def count_first_person_markers(text: str) -> int:
    """Count first-person markers. Used as a proxy for voice compliance."""
    markers = [
        " I ", " I,", " I.", " I;", " I:", "\nI ",
        "My ", "my ", "I've", "I'm", "I am", "I have", "I had",
        "I respectfully", "I submit", "I deny", "I accept",
        "I request", "I humbly", "I affirm",
    ]
    return sum(text.count(m) for m in markers)


# ── Citation Format Validator ─────────────────────────────────────────────────
_VALID_CITATION_PATTERN = re.compile(
    r"[A-Z][a-zA-Z\s&\.]+v\.\s*[A-Z][a-zA-Z\s&\.\(\)]+"
    r"(?:\s*\(\d{4}\))?"                   # year
    r"(?:\s+\d{1,3}\s+ITR\s+\d{1,4})?"    # reporter: N ITR N
    r"(?:\s+\([A-Z]{2,6}\.?\))?",          # court: (SC), (Del. HC), (Bom.)
    re.MULTILINE,
)

_CITATION_MUST_HAVE_YEAR = re.compile(r"\(\d{4}\)")
_CITATION_MUST_HAVE_REPORTER = re.compile(r"\d+\s+ITR\s+\d+|\d+\s+ITD\s+\d+|\d+\s+TAXMAN\s+\d+", re.IGNORECASE)


# ── DraftRiskChecker Class ────────────────────────────────────────────────────
class DraftRiskChecker:
    """
    7-dimension pre-submission audit.
    Every pass returns a consistent finding dict:
    {
        pass:     str   — "A" | "B" | "C" | "D"
        severity: str   — "High" | "Medium" | "Low"
        issue:    str   — human-readable description
        context:  str   — excerpt showing the problem
        action:   str   — recommended fix
    }
    """

    @classmethod
    def run_passes_a_to_d(cls, draft: str, extraction: str) -> list[dict]:
        """
        Run all four deterministic passes and return combined findings list.
        This is the method called by the Tab 6 UI (was missing in v7).

        Pass A: Section number validation
        Pass B: Citation format check
        Pass C: Quantum consistency check
        Pass D: Admission language scan
        """
        findings: list[dict] = []
        findings.extend(cls._pass_a_sections(draft))
        findings.extend(cls._pass_b_citations(draft))
        findings.extend(cls._pass_c_quantum(draft, extraction))
        findings.extend(cls._pass_d_admissions(draft))
        return findings

    @classmethod
    def _pass_a_sections(cls, draft: str) -> list[dict]:
        """Pass A: Validate all ITA section references."""
        from config import KNOWN_IT_SECTIONS

        sec_re = re.compile(
            r"[Ss]ection\s+(\d{1,3}[A-Z]{0,4}(?:\(\d+\))?(?:\([a-z]+\))?)"
            r"|[Uu]/[Ss]\s+(\d{1,3}[A-Z]{0,4}(?:\(\d+\))?(?:\([a-z]+\))?)"
            r"|\bu/s\s+(\d{1,3}[A-Z]{0,4}(?:\(\d+\))?(?:\([a-z]+\))?)",
        )
        findings = []
        for m in sec_re.finditer(draft):
            sec = next((g for g in m.groups() if g), None)
            if not sec:
                continue
            sc = _normalise_section_ref(sec)
            if sc not in KNOWN_IT_SECTIONS and len(sc) > 1 and sc not in {"IT", "ITA", "ACT"}:
                start = max(0, m.start() - 60)
                end   = min(len(draft), m.end() + 60)
                findings.append({
                    "pass":     "A",
                    "severity": "High",
                    "issue":    f"Section '{sec}' does not exist in the Income Tax Act, 1961.",
                    "context":  f"...{draft[start:end]}...",
                    "action":   "Remove this section reference. Do not submit with non-existent sections.",
                })
        return findings

    @classmethod
    def _pass_b_citations(cls, draft: str) -> list[dict]:
        """Pass B: Citation format check."""
        from data.case_laws import ALL_KNOWN_CITATION_FINGERPRINTS

        cit_re = re.compile(
            r"[A-Z][a-zA-Z\s&\.]{5,}v\.\s*[A-Z][a-zA-Z\s&\.\(\)]{3,}",
            re.MULTILINE,
        )
        findings = []
        for raw in cit_re.findall(draft):
            cit = raw.strip()
            if len(cit) < 10:
                continue
            cl = cit.lower()
            in_lib = any(cl in k or k in cl for k in ALL_KNOWN_CITATION_FINGERPRINTS)
            if in_lib:
                continue  # Verified — no issue

            issues = []
            if not _CITATION_MUST_HAVE_YEAR.search(cit):
                issues.append("year missing")
            if not _CITATION_MUST_HAVE_REPORTER.search(cit):
                issues.append("reporter (ITR/ITD/Taxman) missing")

            if issues:
                findings.append({
                    "pass":     "B",
                    "severity": "Medium",
                    "issue":    f"Citation format incomplete: '{cit[:80]}' — {', '.join(issues)}.",
                    "context":  cit[:150],
                    "action":   "Verify on SCC Online / Taxmann / IndianKanoon. Complete the citation with year and reporter before submission.",
                })

        return findings

    @classmethod
    def _pass_c_quantum(cls, draft: str, extraction: str) -> list[dict]:
        """Pass C: Quantum consistency — amounts in draft vs amounts in extraction."""
        findings = []

        # Extract all Rs. amounts from extraction
        ext_amounts: set[str] = set()
        for m in re.finditer(r"(?:Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)", extraction):
            amt_clean = m.group(1).replace(",", "")
            if len(amt_clean) >= 4:  # Ignore amounts < 1000
                ext_amounts.add(amt_clean)

        # Find amounts in draft that are NOT in extraction
        suspicious: list[str] = []
        for m in re.finditer(r"(?:Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)", draft):
            amt_clean = m.group(1).replace(",", "")
            if len(amt_clean) >= 6:  # Only flag amounts >= 1,00,000
                if amt_clean not in ext_amounts:
                    # Check if it's a derived amount (±5% tolerance) — skip if so
                    is_derived = any(
                        abs(float(amt_clean) - float(ea)) / (float(ea) + 0.001) < 0.05
                        for ea in ext_amounts if ea.isdigit()
                    )
                    if not is_derived:
                        suspicious.append(m.group(0))

        for amt in suspicious[:3]:
            findings.append({
                "pass":     "C",
                "severity": "Medium",
                "issue":    f"Amount {amt} appears in draft but was not found in the extracted notice data.",
                "context":  amt,
                "action":   "Verify this amount against the original notice. Invented amounts in submissions are a professional risk.",
            })

        return findings

    @classmethod
    def _pass_d_admissions(cls, draft: str) -> list[dict]:
        """Pass D: Admission language scan."""
        triggers = [
            (r"\bI accept that\b",                   "Outright admission",       "High"),
            (r"\bI acknowledge that the amount\b",   "Quantum admission",         "High"),
            (r"\bthe income was not disclosed\b",    "Concealment admission",     "High"),
            (r"\bI failed to\b",                     "Duty-failure admission",    "High"),
            (r"\bI did not maintain\b",              "Record-keeping concession", "Medium"),
            (r"\bI concede\b",                       "Explicit concession",       "High"),
            (r"\bI agree that the addition\b",       "Addition acceptance",       "High"),
            (r"\bI admit that the return\b",         "Return deficiency admission","High"),
            (r"\bI was not aware\b",                 "Ignorance plea",            "Medium"),
            (r"\bnever been subject to any penalty\b","Unverified blanket statement","Medium"),
            (r"\ball income has been disclosed\b",   "Blanket disclosure claim",  "Medium"),
        ]
        findings = []
        for pattern, label, severity in triggers:
            for m in re.finditer(pattern, draft, re.IGNORECASE):
                start = max(0, m.start() - 100)
                end   = min(len(draft), m.end() + 100)
                findings.append({
                    "pass":     "D",
                    "severity": severity,
                    "issue":    f"{label}: '{m.group(0)}'",
                    "context":  f"...{draft[start:end]}...",
                    "action":   (
                        "Remove or wrap with 'Without Prejudice' qualifier before submission. "
                        "High-risk admission language can be used against the assessee."
                        if severity == "High"
                        else "Review carefully. Consider adding 'to the best of my knowledge' qualifier."
                    ),
                })
        return findings

    @classmethod
    def audit(
        cls,
        draft: str,
        proc_flags: list,
        hall_report: dict,
        admission_findings: list,
        evidence_gaps: list,
        cover_note: str = "",
    ) -> list[dict]:
        """
        7-dimension overall audit (used for the full risk tab display).
        Returns list of dimension result dicts with {dim, status, icon, note, fix}.
        """
        results = []

        # 1. Procedural Defects Raised
        if proc_flags:
            din_f  = any("DIN" in f for f in proc_flags)
            tb_f   = any("TIME-BARRED" in f for f in proc_flags)
            r148_f = any("REASSESSMENT" in f for f in proc_flags)
            missing = []
            if din_f  and "19/2019" not in draft:       missing.append("DIN defect (Circular 19/2019)")
            if tb_f   and "149" not in draft:           missing.append("Sec 149 time-bar objection")
            if r148_f and "148A" not in draft:          missing.append("Sec 148A procedure objection")
            results.append({
                "dim": "Procedural Defects Raised",
                "status": "fail" if missing else "pass",
                "icon":   "🔴" if missing else "✅",
                "note":   f"Missing: {'; '.join(missing)}" if missing else "All defects raised as preliminary submissions",
                "fix":    "Regenerate — procedural_defect_block must inject these submissions." if missing else "",
            })
        else:
            results.append({"dim": "Procedural Defects Raised", "status": "pass",
                             "icon": "✅", "note": "No defects — merits reply appropriate", "fix": ""})

        # 2. Case Law Integrity
        fab = hall_report.get("fabricated_citations", [])
        unv = hall_report.get("unverified_citations", [])
        if fab:
            results.append({"dim": "Case Law Integrity", "status": "fail", "icon": "🔴",
                             "note": f"FABRICATED CITATIONS: {fab[:2]}",
                             "fix": "Remove all fabricated citations immediately. Never submit with invented case laws."})
        elif unv:
            results.append({"dim": "Case Law Integrity", "status": "warn", "icon": "🟡",
                             "note": f"User-supplied (unverified): {unv[:2]}",
                             "fix": "Verify on SCC Online / Taxmann / IndianKanoon before submission."})
        else:
            results.append({"dim": "Case Law Integrity", "status": "pass", "icon": "✅",
                             "note": "All citations verified or user-supplied", "fix": ""})

        # 3. Voice Compliance
        viol = detect_third_person(draft)
        md   = detect_markdown_residue(draft)
        if viol:
            results.append({"dim": "Voice Compliance", "status": "fail", "icon": "🔴",
                             "note": f"Third-person violations: {viol[:3]}",
                             "fix": "Replace 'the assessee/taxpayer' with 'I/my'. Regenerate or edit manually."})
        elif md:
            results.append({"dim": "Voice Compliance", "status": "warn", "icon": "🟡",
                             "note": f"Markdown residue: {md}",
                             "fix": "Enable markdown auto-clean and regenerate."})
        else:
            results.append({"dim": "Voice Compliance", "status": "pass", "icon": "✅",
                             "note": "First-person voice OK, no markdown", "fix": ""})

        # 4. Admission Risk
        critical = [f for f in admission_findings
                    if f.get("risk_label") in ("Outright admission", "Concealment admission", "Duty-failure admission")]
        if critical:
            results.append({"dim": "Admission Risk", "status": "fail", "icon": "🔴",
                             "note": f"{len(critical)} high-risk confessionary phrases detected",
                             "fix": "Add 'Without Prejudice' wrapper or remove entirely before submission."})
        elif admission_findings:
            results.append({"dim": "Admission Risk", "status": "warn", "icon": "🟡",
                             "note": f"{len(admission_findings)} low-risk phrases",
                             "fix": "Review each. Consider Without Prejudice qualifier."})
        else:
            results.append({"dim": "Admission Risk", "status": "pass", "icon": "✅",
                             "note": "No confessionary language detected", "fix": ""})

        # 5. Evidence Completeness
        if evidence_gaps:
            results.append({"dim": "Evidence Completeness", "status": "warn", "icon": "🟡",
                             "note": f"Missing evidence: {'; '.join(evidence_gaps[:3])}",
                             "fix": "Gather before submission. Do not submit with key evidence absent."})
        else:
            results.append({"dim": "Evidence Completeness", "status": "pass", "icon": "✅",
                             "note": "Evidence matrix appears complete", "fix": ""})

        # 6. Section Reference Validity
        inv = hall_report.get("invalid_sections", [])
        if inv:
            results.append({"dim": "Section Reference Validity", "status": "fail", "icon": "🔴",
                             "note": f"Non-existent ITA sections: {inv}",
                             "fix": "Remove these sections. They do not exist in ITA 1961."})
        else:
            results.append({"dim": "Section Reference Validity", "status": "pass", "icon": "✅",
                             "note": "All ITA section references valid", "fix": ""})

        # 7. Portal Readiness
        portal_issues = []
        if not cover_note or len(cover_note) > 4000:
            portal_issues.append("Cover note not ready or over 4,000 chars")
        if "ANNEXURE" not in draft.upper():
            portal_issues.append("Annexure Schedule missing")
        if "PRAYER" not in draft.upper():
            portal_issues.append("Prayer section absent")
        if "DECLARATION" not in draft.upper():
            portal_issues.append("Declaration absent")
        if portal_issues:
            results.append({"dim": "Portal Readiness", "status": "warn", "icon": "🟡",
                             "note": "; ".join(portal_issues),
                             "fix": "Regenerate draft to include all required sections."})
        else:
            results.append({"dim": "Portal Readiness", "status": "pass", "icon": "✅",
                             "note": "Cover note ready | Annexure indexed | Prayer & Declaration present",
                             "fix": ""})

        return results
