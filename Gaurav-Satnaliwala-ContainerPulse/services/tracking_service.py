from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import logging
from pathlib import Path
import re

import pandas as pd

from services.registry_service import ShippingLineRegistry
from tracker import track_container
from tracker.common import TrackingResult
from tracker.generic import track_generic

log = logging.getLogger("containerpulse.batch")
DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "shipping_line_registry.json"


def parse_datetime(value):
    """Convert carrier date strings to a display/export-friendly timestamp."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return pd.NaT
    if isinstance(value, (pd.Timestamp, datetime)):
        return pd.Timestamp(value)
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}", value.strip()):
        return pd.to_datetime(value, errors="coerce", yearfirst=True)
    return pd.to_datetime(value, errors="coerce", dayfirst=True)


def _result_row(container: str, carrier: str, raw: dict) -> dict:
    success = bool(raw.get("success"))
    checked_at = parse_datetime(raw.get("checked_at"))
    if pd.isna(checked_at):
        checked_at = pd.Timestamp(datetime.now().astimezone())
    return {
        "Container Number": container,
        "Shipping Line": carrier,
        "Current Status": raw.get("status") or "",
        "Current Location": raw.get("current_location") or "",
        "Vessel": raw.get("vessel") or "",
        "Latest ETA": parse_datetime(raw.get("latest_eta")),
        "Last Tracking Event": raw.get("last_tracking_event") or "",
        "Checked At": checked_at,
        "Tracking Result": "Success" if success else "Failed",
        "Error": "" if success else (raw.get("error") or "Tracking failed"),
    }


def run_tracking_batch(
    containers: pd.DataFrame,
    headless: bool = False,
    progress_callback: Callable | None = None,
    tracker: Callable | None = None,
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
) -> pd.DataFrame:
    """Track each row independently without reading or writing shipment history."""
    rows = []
    total = len(containers)
    for position, (_, source) in enumerate(containers.iterrows(), start=1):
        container = str(source["Container Number"]).strip().upper()
        carrier = str(source["Shipping Line"]).strip().upper()
        log.info("Tracking started: container=%s carrier=%s headless=%s", container, carrier, headless)
        try:
            connector = tracker or _registry_tracker(registry_path)
            raw = connector(container, carrier, headless=headless).to_dict()
            rows.append(_result_row(container, carrier, raw))
            if raw.get("success"):
                log.info(
                    "Tracking successful: container=%s eta=%r status=%r vessel=%r location=%r",
                    container,
                    raw.get("latest_eta"),
                    raw.get("status"),
                    raw.get("vessel"),
                    raw.get("current_location"),
                )
            else:
                log.warning("Tracking failed: container=%s error=%s", container, raw.get("error") or "Tracking failed")
        except Exception as exc:
            rows.append(_result_row(container, carrier, {"success": False, "error": str(exc)}))
            log.exception("Tracking exception: container=%s", container)
        if progress_callback:
            progress_callback(position, total, container, carrier)
    return pd.DataFrame(rows)


def _registry_tracker(registry_path: str | Path) -> Callable:
    registry = ShippingLineRegistry(registry_path)

    def configured_tracker(container: str, carrier: str, headless: bool = False):
        if carrier in {"MSC", "MAERSK"}:
            return track_container(container, carrier, headless=headless)
        entry = registry.get(carrier)
        if entry is None:
            return TrackingResult(container, carrier, False, error="Shipping line not currently supported")
        if entry["connector_status"] != "Ready":
            reason = entry.get("setup_error") or "Connector is not configured. Use Admin / Shipping Line Registry."
            return TrackingResult(container, carrier, False, error=reason)
        return track_generic(container, carrier, entry, headless=headless)

    return configured_tracker
