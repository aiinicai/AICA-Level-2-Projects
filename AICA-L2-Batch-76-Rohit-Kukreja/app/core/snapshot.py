"""Payload freeze and SHA-256. Build Prompt v2 §2 (`core/snapshot`), §5.4.

A `document_instance` stores every input used, frozen. Reprinting reads the
snapshot, never current data — which is what makes §18.6 true: changing
master data cannot alter a finalised document, and a reprint reproduces it
byte-identically.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.render.base import Document

SNAPSHOT_VERSION = 1


def _plain(value: Any) -> Any:
    """JSON-safe, and stable across runs.

    Decimals become strings rather than floats so that 4260000.00 cannot
    drift to 4260000.0000001 and change the hash of an unchanged document.
    """
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in sorted(value.items())}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if hasattr(value, "value"):  # enum
        return value.value
    return value


def freeze(
    *,
    document_id: str,
    template_version: str,
    responses: dict[str, Any],
    child_rows: dict[str, list[dict[str, Any]]],
    context: dict[str, Any],
) -> str:
    """The payload JSON stored on `document_instance`.

    Sorted keys throughout: two freezes of the same inputs must produce the
    same bytes, or the hash means nothing.
    """
    payload = {
        "snapshot_version": SNAPSHOT_VERSION,
        "document": document_id,
        "template_version": template_version,
        "responses": _plain(responses),
        "child_rows": _plain(child_rows),
        "context": _plain(context),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def thaw(payload_json: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(payload_json)
    if data.get("snapshot_version") != SNAPSHOT_VERSION:
        raise ValueError(
            f"snapshot version {data.get('snapshot_version')} cannot be read by "
            f"version {SNAPSHOT_VERSION}"
        )
    return data


def content_hash(document: Document) -> str:
    """SHA-256 over the rendered text, not the payload.

    Hashing the output rather than the inputs is deliberate: it is what lets
    a reprint be *checked*, not merely asserted.
    """
    joined = "\n".join(document.text_nodes())
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def payload_hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
