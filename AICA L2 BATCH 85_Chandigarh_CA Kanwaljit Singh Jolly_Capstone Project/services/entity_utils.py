# services/entity_utils.py

import hashlib
from typing import Any, Dict, List


def _clean(v: Any) -> str:
    """Clean a value for ID generation"""
    if v is None:
        return ""
    return str(v).strip()

def make_entity_id(entity_type: str, fields: Dict[str, Any], key_fields: List[str]) -> str:
    """
    Generic entity id builder.
    Task pack supplies key_fields (e.g., ["identifier","date"]).
    Core never hardcodes any domain keys.

    Args:
        entity_type: Type of entity (task-defined string)
        fields: Dict of field values
        key_fields: List of field names to use for ID (supplied by task pack)

    Returns:
        16-character hex hash as entity ID

    Example:
        make_entity_id("DOCUMENT", {"id": "123", "date": "2025-01-01"}, ["id", "date"])
        # Returns: "a1b2c3d4e5f6g7h8"
    """
    parts = [entity_type] + [_clean(fields.get(k)) for k in key_fields]
    raw = "|".join(parts).lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalize_identifier(value: Any) -> str:
    """
    Normalize an identifier (number, code, etc.) for matching.

    Args:
        value: Raw identifier value

    Returns:
        Normalized string (uppercase, no spaces/dashes)

    Examples:
        normalize_identifier("abc-123")  # "ABC123"
        normalize_identifier(12345)      # "12345"
    """
    if value is None:
        return ""

    s = str(value).strip().upper()
    # Remove common separators
    s = s.replace("-", "").replace("_", "").replace(" ", "")
    return s
