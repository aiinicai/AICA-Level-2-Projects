"""Export schema loading. The schema JSON is the single source of truth for table names, column headings,
column order, value kinds and drop-down values (used for the Master Template AND the CSV files).

A user-editable copy in the data folder is preferred over the bundled one, so the schema can be adjusted
(or adopted from the official Offline Tool samples) without touching the program."""
import json
from pathlib import Path

from . import config


def schema_path() -> Path:
    return config.USER_SCHEMA_PATH if config.USER_SCHEMA_PATH.exists() else config.SCHEMA_PATH


def load_schema() -> dict:
    with open(schema_path(), encoding="utf-8") as f:
        return json.load(f)


def save_schema(schema: dict) -> Path:
    config.ensure_dirs()
    with open(config.USER_SCHEMA_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=1, ensure_ascii=False)
    return config.USER_SCHEMA_PATH


def reset_schema() -> None:
    """Go back to the bundled schema."""
    config.USER_SCHEMA_PATH.unlink(missing_ok=True)


def table_keys(schema: dict):
    return list(schema["tables"].keys())


def headers_status(schema: dict):
    """(verified_count, total, text)."""
    tabs = schema["tables"]
    n = sum(1 for t in tabs.values() if t.get("header_verified"))
    when = schema.get("headers_verified_on", "")
    if n == 0:
        return n, len(tabs), "PROVISIONAL - headings not verified against the official Offline Tool samples"
    return n, len(tabs), f"Headings verified against official samples for {n} of {len(tabs)} tables" + (
        f" (on {when})" if when else "")
