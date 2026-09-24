"""
Form and Act Classification Engine for TDS & TCS Certificates.
Accurately identifies:
- Income-tax Act, 1961 vs Income-tax Act, 2025
- Form 16, 16A, 16B, 16C, 16D, 16E, 27D
- Form 130, 131, 132, 133
"""

import re
from typing import Tuple, Optional, Dict, Any
from config import FORM_REGISTRY, ACT_1961, ACT_2025, CATEGORY_TDS, CATEGORY_TCS


class CertificateClassifier:
    """Classifies PDF text into governing Act and specific Form type."""

    def __init__(self, custom_registry: Optional[Dict[str, Dict[str, Any]]] = None):
        self.registry = custom_registry or FORM_REGISTRY

    def classify(self, text: str) -> Tuple[str, str, str, str, float]:
        """
        Classify document text.
        
        Returns:
            Tuple of (form_code, form_name, act, category, confidence_score)
        """
        if not text or not text.strip():
            return "UNKNOWN", "Unknown Form", "Unknown Act", "Unknown", 0.0

        normalized_text = " ".join(text.split())

        # Step 1: Detect explicit governing Act mention
        explicit_act = self._detect_act(normalized_text)

        # Step 2: Score each registered form against the text
        best_code = None
        best_score = 0.0
        best_meta = None

        # Sort candidate forms: longer form codes first (e.g. '16A', '16B' before '16')
        sorted_forms = sorted(self.registry.items(), key=lambda item: len(item[0]), reverse=True)

        for code, meta in sorted_forms:
            score = self._score_form(normalized_text, code, meta, explicit_act)
            if score > best_score:
                best_score = score
                best_code = code
                best_meta = meta

        if best_code and best_score >= 0.35:
            # Reconcile Act: Forms 130-133 are strictly Income-tax Act, 2025 forms
            if best_code in ["130", "131", "132", "133"]:
                resolved_act = ACT_2025
            elif best_code in ["16", "16A", "16B", "16C", "16D", "16E", "27D"]:
                resolved_act = ACT_1961
            else:
                form_act = best_meta["act"]
                resolved_act = explicit_act if explicit_act else form_act
            
            # Confidence normalizer (0.0 to 1.0)
            confidence = min(1.0, round(best_score, 2))
            return best_code, best_meta["form_name"], resolved_act, best_meta["category"], confidence

        # Fallback detection for generic TDS / TCS certificates
        return self._fallback_classification(normalized_text, explicit_act)

    def _detect_act(self, text: str) -> Optional[str]:
        """Detect explicit mention of Income-tax Act, 1961 or 2025."""
        if re.search(r"Income[\s\-]?tax\s+Act,?\s*2025", text, re.IGNORECASE):
            return ACT_2025
        # Statutory indicators under Income-tax Act, 2025
        if re.search(r"\bFORM\s+NO\.?\s*13[0-3]\b", text, re.IGNORECASE):
            return ACT_2025
        if re.search(r"section\s+395\b|rule\s+215\b|section\s+397\b|section\s+398\b|rule\s+217\b", text, re.IGNORECASE):
            return ACT_2025
        if re.search(r"Income[\s\-]?tax\s+Act,?\s*1961", text, re.IGNORECASE):
            return ACT_1961
        return None

    def _score_form(self, text: str, code: str, meta: Dict[str, Any], explicit_act: Optional[str]) -> float:
        """Calculate a match score for a given form configuration."""
        score = 0.0

        # Pattern match weight (Highest priority)
        patterns = meta.get("detection_regex", [])
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.50
                break

        # Specific section reference weight
        section_ref = meta.get("section_ref")
        if section_ref and re.search(rf"\bsection\s+{re.escape(section_ref)}\b", text, re.IGNORECASE):
            score += 0.30

        # Rule reference weight
        rule_ref = meta.get("rule_ref")
        if rule_ref:
            clean_rule = rule_ref.replace("(", r"\s*\(\s*").replace(")", r"\s*\)\s*")
            if re.search(clean_rule, text, re.IGNORECASE):
                score += 0.25

        # Act alignment bonus
        if explicit_act and explicit_act == meta.get("act"):
            score += 0.15

        # Form code exact word match bonus
        if re.search(rf"\bFORM\s*(?:NO\.?\s*)?{re.escape(code)}\b", text, re.IGNORECASE):
            score += 0.20

        return score

    def _fallback_classification(self, text: str, explicit_act: Optional[str]) -> Tuple[str, str, str, str, float]:
        """Fallback when exact form code is ambiguous but TDS/TCS markers exist."""
        act = explicit_act or ACT_1961

        if re.search(r"Tax\s+Collected\s+at\s+Source|section\s+206C", text, re.IGNORECASE):
            if act == ACT_2025:
                return "133", "Form 133", ACT_2025, CATEGORY_TCS, 0.40
            return "27D", "Form 27D", ACT_1961, CATEGORY_TCS, 0.40

        if re.search(r"Tax\s+Deducted\s+at\s+Source|section\s+203", text, re.IGNORECASE):
            if "salary" in text.lower():
                if act == ACT_2025:
                    return "130", "Form 130", ACT_2025, CATEGORY_TDS, 0.40
                return "16", "Form 16", ACT_1961, CATEGORY_TDS, 0.40
            else:
                if act == ACT_2025:
                    return "131", "Form 131", ACT_2025, CATEGORY_TDS, 0.40
                return "16A", "Form 16A", ACT_1961, CATEGORY_TDS, 0.40

        return "UNKNOWN", "Unrecognized Certificate", act, "Unknown", 0.0
