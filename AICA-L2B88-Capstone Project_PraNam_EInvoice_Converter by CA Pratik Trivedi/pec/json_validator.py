"""Offline validation of the generated e-Invoice JSON against Schema 1.1."""
from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache

from jsonschema import Draft7Validator

SCHEMA_PATH = Path(__file__).with_name("data") / "einvoice_schema_v1_1.json"


@lru_cache(maxsize=1)
def validator() -> Draft7Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft7Validator(schema)


def validate_documents(data) -> list[str]:
    """Return human-readable schema errors. Data may be one object or a bulk list."""
    docs = data if isinstance(data, list) else [data]
    errors: list[str] = []
    v = validator()
    for idx, doc in enumerate(docs, 1):
        for err in sorted(v.iter_errors(doc), key=lambda e: list(e.path)):
            path = ".".join(str(x) for x in err.absolute_path) or "JSON"
            errors.append(f"Invoice {idx}: {path}: {err.message}")
    return errors
