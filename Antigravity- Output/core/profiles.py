"""
Configuration and Profile Management for MarketMatch.
Reads config/column_aliases.json (READ-ONLY) to drive dynamic, multi-marketplace report ingestion.
Supports header matching ignoring case, extra spaces, and punctuation.
"""
import json
import os
import re
from typing import Dict, Any, List, Optional, Tuple

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "column_aliases.json")


def clean_header_name(header: Any) -> str:
    """
    Clean header name by lowercasing, stripping punctuation, and compressing whitespace.
    e.g. 'Invoice Number' -> 'invoicenumber'
    e.g. 'Date/Time' -> 'datetime'
    e.g. 'TDS (Section 194-O)' -> 'tdssection194o'
    """
    if header is None:
        return ""
    s = str(header).lower().strip()
    # Remove all non-alphanumeric characters
    cleaned = re.sub(r"[^a-z0-9]", "", s)
    return cleaned


class ProfileManager:
    """Manages marketplace report profiles from config/column_aliases.json."""

    def __init__(self, config_file: str = CONFIG_PATH):
        self.config_file = config_file
        self.config_data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file not found at: {self.config_file}")
        with open(self.config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def version(self) -> int:
        return self.config_data.get("version", 2)

    @property
    def profiles(self) -> Dict[str, Any]:
        return self.config_data.get("reports", {})

    def get_profile(self, profile_key: str) -> Dict[str, Any]:
        if profile_key not in self.profiles:
            raise KeyError(f"Profile '{profile_key}' not found in configuration.")
        return self.profiles[profile_key]

    def list_profiles(self) -> List[Tuple[str, str, str]]:
        """Return list of (profile_key, display_name, role)."""
        res = []
        for key, p in self.profiles.items():
            res.append((key, p.get("display_name", key), p.get("role", "unknown")))
        return res

    def get_state_normalisation(self) -> Dict[str, Any]:
        return self.config_data.get("state_normalisation", {})

    def match_header(self, actual_header: str, candidate_aliases: List[str], threshold: float = 85.0) -> bool:
        """
        Check if an actual column header matches any candidate alias.
        First attempts exact match after cleaning whitespace/punctuation/case.
        If RapidFuzz is available, attempts fuzzy match above threshold.
        """
        clean_act = clean_header_name(actual_header)
        if not clean_act:
            return False

        for alias in candidate_aliases:
            clean_al = clean_header_name(alias)
            if clean_act == clean_al:
                return True
            if HAS_RAPIDFUZZ:
                score = fuzz.ratio(clean_act, clean_al)
                if score >= threshold:
                    return True
        return False

    def detect_header_row(self, rows: List[List[Any]], keywords: List[str], max_scan: int = 50) -> Optional[int]:
        """
        Scan rows up to max_scan to find row that contains the required detection keywords.
        Keywords are checked ignoring case/punctuation.
        Returns 0-based row index or None.
        """
        clean_kw = [clean_header_name(kw) for kw in keywords]
        for row_idx, row in enumerate(rows[:max_scan]):
            cleaned_row_cells = [clean_header_name(cell) for cell in row if cell is not None]
            matched_kws = 0
            for kw in clean_kw:
                if any(kw in cell or cell in kw for cell in cleaned_row_cells if cell):
                    matched_kws += 1
            if matched_kws >= min(2, len(clean_kw)):
                return row_idx
        return None

    def map_columns(self, actual_headers: List[Any], column_definitions: Dict[str, List[str]]) -> Dict[str, int]:
        """
        Map defined target field names to column indices in actual_headers.
        Returns {target_field: column_index}.
        """
        mapping: Dict[str, int] = {}
        cleaned_headers = [clean_header_name(h) for h in actual_headers]

        for target_field, aliases in column_definitions.items():
            matched_idx = None
            clean_aliases = [clean_header_name(a) for a in aliases]

            # 1. Exact match
            for idx, h_clean in enumerate(cleaned_headers):
                if h_clean in clean_aliases:
                    matched_idx = idx
                    break

            # 2. Fuzzy match if needed
            if matched_idx is None and HAS_RAPIDFUZZ:
                best_score = 0
                for idx, h_clean in enumerate(cleaned_headers):
                    if not h_clean:
                        continue
                    for al_clean in clean_aliases:
                        score = fuzz.ratio(h_clean, al_clean)
                        if score > best_score and score >= 85:
                            best_score = score
                            matched_idx = idx

            if matched_idx is not None:
                mapping[target_field] = matched_idx

        return mapping
