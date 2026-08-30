import logging
from typing import List, Tuple, Optional
from app.models.profile import BankProfile

logger = logging.getLogger(__name__)

class ProfileMatcher:
    def __init__(self, profiles: List[BankProfile], config):
        # keep only active profiles
        self.profiles = [p for p in profiles if getattr(p, 'active', True)]
        # configuration thresholds
        self.auto_apply = (
            config.getboolean('profiles', 'auto_apply', fallback=True)
            if hasattr(config, 'getboolean') else True
        )
        self.match_threshold = (
            config.getint('profiles', 'match_threshold', fallback=80)
            if hasattr(config, 'getint') else 80
        )
        # New lower suggestion threshold (default 50)
        self.suggestion_threshold = (
            config.getint('profiles', 'suggestion_threshold', fallback=50)
            if hasattr(config, 'getint') else 50
        )

    def match(
        self,
        bank_detected: str,
        page_width: float,
        page_height: float,
        extracted_text: str,
    ) -> Tuple[str, Optional[BankProfile], int, dict]:
        if not self.profiles:
            return "NO_PROFILES_AVAILABLE", None, 0, {}

        candidates = []
        for prof in self.profiles:
            score, details = self._calculate_score(
                prof, bank_detected, page_width, page_height, extracted_text
            )
            candidates.append((score, prof, details))

        # sort highest first
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_score, top_prof, top_details = candidates[0]

        cand_list = [
            {
                "profile_id": p.profile_id,
                "profile_name": p.profile_name,
                "bank_name": p.bank_name,
                "revision": getattr(p, 'revision_number', 1),
                "score": s,
                "details": d,
            }
            for s, p, d in candidates
        ]

        if top_score >= self.match_threshold:
            if len(candidates) > 1:
                second_score, _, _ = candidates[1]
                if second_score >= self.match_threshold and (top_score - second_score) < 5:
                    return "SELECTION_REQUIRED", None, top_score, {"candidates": cand_list}
            return "AUTO_APPLIED", top_prof, top_score, {"candidates": cand_list, "top": top_details}

        return "SELECTION_REQUIRED", top_prof, top_score, {"candidates": cand_list}


    def _calculate_score(
        self,
        profile: BankProfile,
        bank_detected: str,
        page_width: float,
        page_height: float,
        extracted_text: str,
    ) -> Tuple[int, dict]:
        score = 0
        details = {}

        # 1. Bank Identity (15 pts)
        if bank_detected and bank_detected.strip().lower() not in ["unknown", "unknown bank", ""]:
            if profile.bank_name.lower() in bank_detected.lower() or bank_detected.lower() in profile.bank_name.lower():
                score += 15
                details["bank_match"] = True
            else:
                details["bank_match"] = False
        else:
            details["bank_match"] = False

        # 2. Page Dimensions (25 pts)
        w_diff = abs(profile.page_width - page_width)
        h_diff = abs(profile.page_height - page_height)
        if profile.page_width > 0 and profile.page_height > 0:
            if (
                w_diff <= getattr(profile, "page_size_tolerance", 5)
                and h_diff <= getattr(profile, "page_size_tolerance", 5)
            ):
                score += 25
                details["dimension_match"] = True
            else:
                details["dimension_match"] = False
        else:
            details["dimension_match"] = False

        # 3. Header signatures / column layout (up to 60 pts)
        import re
        def norm_hdr(t):
            return re.sub(r'\s+|[.,/\\(\\)\\[\\]]', '', str(t)).upper()
            
        ext_norm = norm_hdr(extracted_text)
        
        if profile.expected_header_signatures:
            sig_value = 60.0 / len(profile.expected_header_signatures)
            matched_sigs = sum(1 for sig in profile.expected_header_signatures if norm_hdr(sig) in ext_norm)
            score += int(round(matched_sigs * sig_value))
            details["signatures_matched"] = f"{matched_sigs}/{len(profile.expected_header_signatures)}"
        elif profile.column_definitions:
            col_matches = sum(
                1
                for col in profile.column_definitions
                if col.canonical_name and norm_hdr(col.canonical_name) in ext_norm
            )
            if col_matches > 0:
                score += min(60, int(round(col_matches * (60.0 / len(profile.column_definitions)))))
                details["columns_matched"] = f"{col_matches}/{len(profile.column_definitions)}"

        return min(score, 100), details
