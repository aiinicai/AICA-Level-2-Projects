from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from .browser import launch_installed_browser
from .common import TrackingResult, detect_access_block, extract_eta, extract_labeled_value


FIELD_LABELS = {
    "status": ["Current Status", "Shipment Status", "Status"],
    "current_location": ["Current Location", "Last Location", "Latest Location", "Location"],
    "vessel": ["Vessel / Voyage", "Vessel Name", "Current Vessel", "Vessel"],
    "latest_eta": ["Latest ETA", "Estimated Time of Arrival", "Estimated Arrival", "ETA"],
    "last_tracking_event": ["Last Tracking Event", "Latest Event", "Last Event", "Latest Milestone"],
}


def security_restriction(text: str) -> str | None:
    block = detect_access_block(text)
    if block:
        return block
    flat = re.sub(r"\s+", " ", text or "").casefold()
    if re.search(r"(?:login|log in|sign in).{0,60}(?:required|to view|to track|continue)", flat):
        return "login is required by the carrier website"
    return None


def _frame_for_config(page, config: dict):
    frame_name = config.get("frame_name") or ""
    url_hint = config.get("frame_url_contains") or ""
    for frame in page.frames:
        if frame_name and frame.name == frame_name:
            return frame
        if url_hint and url_hint in frame.url:
            return frame
    return page.main_frame


def _clean_extracted(value: str | None, labels: list[str]) -> str | None:
    cleaned = re.sub(r"\s+", " ", value or "").strip()
    for label in sorted(labels, key=len, reverse=True):
        cleaned = re.sub(rf"^{re.escape(label)}\s*[:\-]?\s*", "", cleaned, flags=re.I)
    return cleaned[:300] or None


def _extract_fields(frame, text: str, config: dict) -> dict:
    values = {}
    selectors = config.get("field_selectors") or {}
    for field, labels in FIELD_LABELS.items():
        value = None
        selector = selectors.get(field)
        if selector:
            try:
                locator = frame.locator(selector).first
                if locator.count():
                    value = _clean_extracted(locator.inner_text(timeout=5000), labels)
            except Exception:
                value = None
        if not value:
            value = extract_labeled_value(text, labels)
        values[field] = value
    values["latest_eta"] = values["latest_eta"] or extract_eta(text)
    return values


def track_generic(container: str, carrier: str, entry: dict, headless: bool = True) -> TrackingResult:
    config = entry.get("config") or {}
    url = entry.get("tracking_url") or ""
    log = logging.getLogger(f"containerpulse.generic.{carrier.lower().replace(' ', '_')}")
    if entry.get("connector_status") != "Ready" or not config:
        reason = entry.get("setup_error") or "Connector has not been configured"
        return TrackingResult(container, carrier, False, error=reason)
    try:
        with sync_playwright() as playwright:
            browser, browser_source = launch_installed_browser(playwright, headless, log)
            log.info("Generic connector launched using %s", browser_source)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            response = page.goto(url, wait_until="domcontentloaded", timeout=90000)
            log.info("Carrier page opened: HTTP %s URL %s", response.status if response else "unknown", page.url)
            frame = _frame_for_config(page, config)
            input_box = frame.locator(config["input_selector"]).first
            input_box.wait_for(state="visible", timeout=30000)
            input_box.fill(container, timeout=10000)
            frame.locator(config["button_selector"]).first.click(timeout=10000)
            page.wait_for_timeout(config.get("result_wait_ms", 8000))
            text = frame.locator("body").inner_text(timeout=15000)
            restriction = security_restriction(text)
            debug_dir = Path("tracking_debug")
            debug_dir.mkdir(exist_ok=True)
            safe_name = re.sub(r"[^A-Z0-9_-]+", "_", carrier.upper())
            (debug_dir / f"generic_{safe_name}_{container}.txt").write_text(text, encoding="utf-8")
            page.screenshot(path=str(debug_dir / f"generic_{safe_name}_{container}.png"), full_page=True)
            if restriction:
                browser.close()
                return TrackingResult(container, carrier, False, True, False, restriction, source_url=url, error=restriction)
            fields = _extract_fields(frame, text, config)
            browser.close()

        accepted = container in text.upper()
        success = accepted and any(fields.values())
        return TrackingResult(
            container,
            carrier,
            success,
            True,
            accepted,
            None,
            fields["latest_eta"],
            fields["status"],
            fields["current_location"],
            fields["vessel"],
            fields["last_tracking_event"],
            url,
            raw_excerpt=text[:1200],
            error=None if success else "Search completed, but the test container or tracking result fields were not detected.",
        )
    except Exception as exc:
        log.exception("Configured carrier tracking failed")
        return TrackingResult(container, carrier, False, source_url=url, error=str(exc))


def frame_url_hint(url: str) -> str:
    parsed = urlparse(url or "")
    if not parsed.netloc:
        return ""
    first_path = next((part for part in parsed.path.split("/") if part), "")
    return f"{parsed.netloc}/{first_path}" if first_path else parsed.netloc
