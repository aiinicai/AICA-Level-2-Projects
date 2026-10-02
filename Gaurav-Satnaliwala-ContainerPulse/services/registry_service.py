from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


VALID_STATUSES = {"Ready", "Not Configured", "Setup Failed"}
BUILT_IN_CARRIERS = {
    "MSC": "https://www.msc.com/en/track-a-shipment",
    "MAERSK": "https://www.maersk.com/tracking/",
}


def normalize_carrier(name: str) -> str:
    return " ".join(str(name or "").strip().upper().split())


def _default_entry(name: str, url: str) -> dict:
    return {
        "shipping_line_name": name,
        "tracking_url": url,
        "connector_status": "Ready",
        "built_in": True,
        "config": None,
        "setup_error": "",
    }


class ShippingLineRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([_default_entry(name, url) for name, url in BUILT_IN_CARRIERS.items()])
        else:
            self._ensure_built_ins()

    def list_entries(self) -> list[dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Shipping line registry could not be read: {exc}") from exc
        if not isinstance(data, list):
            raise ValueError("Shipping line registry must contain a JSON list.")
        return sorted(data, key=lambda item: item["shipping_line_name"])

    def get(self, name: str) -> dict | None:
        carrier = normalize_carrier(name)
        return next((entry for entry in self.list_entries() if entry["shipping_line_name"] == carrier), None)

    def add(self, name: str, tracking_url: str) -> dict:
        carrier = normalize_carrier(name)
        self._validate(carrier, tracking_url)
        entries = self.list_entries()
        if any(entry["shipping_line_name"] == carrier for entry in entries):
            raise ValueError(f"{carrier} already exists in the registry.")
        entry = {
            "shipping_line_name": carrier,
            "tracking_url": tracking_url.strip(),
            "connector_status": "Not Configured",
            "built_in": False,
            "config": None,
            "setup_error": "",
        }
        entries.append(entry)
        self._write(entries)
        return entry

    def update(self, original_name: str, name: str, tracking_url: str) -> dict:
        original = normalize_carrier(original_name)
        carrier = normalize_carrier(name)
        self._validate(carrier, tracking_url)
        entries = self.list_entries()
        entry = next((item for item in entries if item["shipping_line_name"] == original), None)
        if entry is None:
            raise ValueError(f"{original} was not found in the registry.")
        if entry.get("built_in") and carrier != original:
            raise ValueError("Built-in carrier names cannot be changed.")
        if carrier != original and any(item["shipping_line_name"] == carrier for item in entries):
            raise ValueError(f"{carrier} already exists in the registry.")
        url_changed = entry["tracking_url"] != tracking_url.strip()
        entry["shipping_line_name"] = carrier
        entry["tracking_url"] = tracking_url.strip()
        if url_changed and not entry.get("built_in"):
            entry.update(connector_status="Not Configured", config=None, setup_error="")
        self._write(entries)
        return entry

    def delete(self, name: str) -> None:
        carrier = normalize_carrier(name)
        entries = self.list_entries()
        entry = next((item for item in entries if item["shipping_line_name"] == carrier), None)
        if entry is None:
            raise ValueError(f"{carrier} was not found in the registry.")
        if entry.get("built_in"):
            raise ValueError("Built-in MSC and MAERSK entries cannot be deleted.")
        self._write([item for item in entries if item["shipping_line_name"] != carrier])

    def save_setup_result(self, name: str, success: bool, config: dict | None, reason: str = "") -> dict:
        carrier = normalize_carrier(name)
        entries = self.list_entries()
        entry = next((item for item in entries if item["shipping_line_name"] == carrier), None)
        if entry is None:
            raise ValueError(f"{carrier} was not found in the registry.")
        if entry.get("built_in"):
            return entry
        entry["connector_status"] = "Ready" if success else "Setup Failed"
        entry["config"] = config if success else None
        entry["setup_error"] = "" if success else reason
        self._write(entries)
        return entry

    def ready_names(self) -> list[str]:
        return [entry["shipping_line_name"] for entry in self.list_entries() if entry["connector_status"] == "Ready"]

    def _ensure_built_ins(self) -> None:
        entries = self.list_entries()
        changed = False
        for name, url in BUILT_IN_CARRIERS.items():
            entry = next((item for item in entries if item.get("shipping_line_name") == name), None)
            if entry is None:
                entries.append(_default_entry(name, url))
                changed = True
            else:
                required = {"connector_status": "Ready", "built_in": True, "config": None, "setup_error": ""}
                for key, value in required.items():
                    if entry.get(key) != value:
                        entry[key] = value
                        changed = True
        if changed:
            self._write(entries)

    @staticmethod
    def _validate(name: str, tracking_url: str) -> None:
        if not name:
            raise ValueError("Shipping Line Name is required.")
        parsed = urlparse(str(tracking_url or "").strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Tracking URL must be a complete http:// or https:// address.")

    def _write(self, entries: list[dict]) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)
