from __future__ import annotations
import base64
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from .common import (TrackingResult, extract_eta, extract_labeled_value,
                     debug_save, detect_access_block, logger_for)
from .browser import launch_installed_browser


def _url(container: str) -> str:
    payload = f"trackingNumber={container}&trackingMode=0".encode()
    encoded = base64.b64encode(payload).decode()
    return f"https://www.msc.com/en/track-a-shipment?params={encoded}"


def _next_line(lines: list[str], label: str) -> str | None:
    for index, line in enumerate(lines):
        if line.casefold() == label.casefold() and index + 1 < len(lines):
            return lines[index + 1]
    return None


def _parse_msc_rendered_text(text: str) -> dict[str, str | None]:
    """Parse the visible MSC result card and newest event row."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines() if line.strip()]
    location = _next_line(lines, "Latest move")
    eta = _next_line(lines, "POD ETA")
    status = vessel = event = None
    date_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}$")
    try:
        header_index = next(i for i, line in enumerate(lines) if line.casefold() == "date")
        event_index = next(i for i in range(header_index + 1, len(lines)) if date_pattern.match(lines[i]))
        event_date = lines[event_index]
        event_location = lines[event_index + 1] if event_index + 1 < len(lines) else ""
        status = lines[event_index + 2] if event_index + 2 < len(lines) else None
        vessel_candidate = lines[event_index + 3] if event_index + 3 < len(lines) else ""
        if vessel_candidate.upper() not in {"EMPTY", "LADEN"}:
            vessel = re.sub(r"\s+[A-Z]{1,3}\d{2,4}[A-Z]$", "", vessel_candidate).strip() or None
        event = " | ".join(part for part in [event_date, event_location, status or "", vessel_candidate] if part)
        location = event_location or location
    except (StopIteration, IndexError):
        pass
    return {"eta": eta, "status": status, "location": location, "vessel": vessel, "event": event}


def track_msc(container: str, headless: bool = True) -> TrackingResult:
    url = _url(container)
    log = logger_for("MSC")
    try:
        log.info("Starting MSC test for %s", container)
        with sync_playwright() as p:
            log.info("Launching an already-installed browser (headless=%s)", headless)
            browser, browser_source = launch_installed_browser(p, headless, log)
            log.info("Browser source: %s", browser_source)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            response = page.goto(url, wait_until="domcontentloaded", timeout=90000)
            log.info("MSC page opened: HTTP %s, URL %s", response.status if response else "unknown", page.url)
            # Cookie banners are carrier/region dependent; click common consent wording if present.
            for label in ["Accept all", "Accept All", "Allow all", "I agree"]:
                try:
                    page.get_by_role("button", name=label).click(timeout=1500)
                    break
                except Exception:
                    pass
            page.wait_for_timeout(8000)
            text = page.locator("body").inner_text(timeout=15000)
            debug_save(container, "MSC", text)
            debug_dir = Path("tracking_debug")
            debug_dir.mkdir(exist_ok=True)
            (debug_dir / f"msc_{container}.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=f"tracking_debug/msc_{container}.png", full_page=True)
            browser.close()

        block = detect_access_block(text)
        if block:
            log.warning("MSC access block: %s", block)
            return TrackingResult(container, "MSC", False, True, False, block,
                                  source_url=url, raw_excerpt=text[:1200], error=block)
        rendered = _parse_msc_rendered_text(text)
        eta = rendered["eta"] or extract_eta(text)
        status = rendered["status"] or extract_labeled_value(text, ["Status", "Current status"])
        location = rendered["location"] or extract_labeled_value(text, ["Location", "Current location", "Last location"])
        vessel = rendered["vessel"] or extract_labeled_value(text, ["Vessel", "Vessel / Voyage", "Current vessel"])
        event = rendered["event"] or extract_labeled_value(text, ["Last tracking event", "Latest event", "Last event"])
        ok = bool(eta or status or location or vessel) and "container not found" not in text.lower()
        log.info("MSC extraction complete: success=%s", ok)
        accepted = container in text.upper() and "container not found" not in text.lower()
        return TrackingResult(container, "MSC", ok, True, accepted, None,
                              eta, status, location, vessel, event, url,
                              raw_excerpt=text[:1200],
                              error=None if ok else "Page opened, but structured tracking fields were not detected. Check tracking_debug output.")
    except Exception as e:
        log.exception("MSC test failed at browser/navigation stage")
        return TrackingResult(container, "MSC", False, source_url=url, error=str(e))
