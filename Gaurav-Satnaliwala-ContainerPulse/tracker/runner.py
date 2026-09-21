from __future__ import annotations
from .common import TrackingResult
from .msc import track_msc
from .maersk import track_maersk


CONNECTOR_REGISTRY = {
    "MSC": track_msc,
    "MAERSK": track_maersk,
}

SHIPPING_LINE_ALIASES = {
    "MEDITERRANEAN SHIPPING COMPANY": "MSC",
    "MAERSK LINE": "MAERSK",
}


def track_container(container_number: str, shipping_line: str, headless: bool = True):
    c = container_number.strip().upper()
    line = shipping_line.strip().upper()
    canonical_line = SHIPPING_LINE_ALIASES.get(line, line)
    connector = CONNECTOR_REGISTRY.get(canonical_line)
    if connector is None:
        return TrackingResult(
            c,
            canonical_line,
            False,
            error="Shipping line not currently supported",
        )
    return connector(c, headless=headless)
