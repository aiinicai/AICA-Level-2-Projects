from __future__ import annotations

from dataclasses import dataclass
import logging
import re

from playwright.sync_api import sync_playwright

from tracker.browser import launch_installed_browser
from tracker.generic import FIELD_LABELS, frame_url_hint, security_restriction, track_generic


log = logging.getLogger("containerpulse.connector_setup")


INVENTORY_SCRIPT = r"""
els => {
  const esc = value => CSS.escape(value);
  const path = el => {
    if (el.id) return '#' + esc(el.id);
    for (const attr of ['data-test','data-testid','name','aria-label','placeholder']) {
      const value = el.getAttribute(attr);
      if (value) return el.tagName.toLowerCase() + '[' + attr + '="' + value.replace(/"/g, '\\"') + '"]';
    }
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 5) {
      let part = node.tagName.toLowerCase();
      const siblings = node.parentElement ? [...node.parentElement.children].filter(x => x.tagName === node.tagName) : [];
      if (siblings.length > 1) part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
      parts.unshift(part);
      node = node.parentElement;
    }
    return parts.join(' > ');
  };
  return els.filter(el => {
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0;
  }).slice(0, 1000).map(el => {
    const next = el.nextElementSibling;
    return {
      tag: el.tagName.toLowerCase(), type: el.getAttribute('type') || '', id: el.id || '',
      name: el.getAttribute('name') || '', placeholder: el.getAttribute('placeholder') || '',
      aria: el.getAttribute('aria-label') || '', dataTest: el.getAttribute('data-test') || el.getAttribute('data-testid') || '',
      text: (el.innerText || el.value || '').trim().replace(/\s+/g, ' ').slice(0, 300), selector: path(el),
      nextSelector: next ? path(next) : '', nextText: next ? (next.innerText || next.value || '').trim().replace(/\s+/g, ' ').slice(0, 300) : ''
    };
  });
}
"""


@dataclass
class SetupOutcome:
    success: bool
    config: dict | None = None
    reason: str = ""
    retest_result: object | None = None


def _haystack(record: dict) -> str:
    return " ".join(str(record.get(key, "")) for key in ["id", "name", "placeholder", "aria", "dataTest", "text"]).casefold()


def choose_input(records: list[dict]) -> dict | None:
    candidates = []
    for record in records:
        if record.get("tag") not in {"input", "textarea"}:
            continue
        if record.get("type", "").casefold() in {"hidden", "password", "email", "checkbox", "radio"}:
            continue
        words = _haystack(record)
        score = 0
        score += 8 if "container" in words else 0
        score += 5 if "tracking" in words or "track" in words else 0
        score += 3 if "shipment" in words or "booking" in words or "bill of lading" in words else 0
        score += 1 if "search" in words else 0
        candidates.append((score, record))
    return max(candidates, key=lambda item: item[0])[1] if candidates and max(x[0] for x in candidates) > 0 else None


def choose_button(records: list[dict]) -> dict | None:
    candidates = []
    for record in records:
        tag = record.get("tag")
        kind = record.get("type", "").casefold()
        if tag not in {"button", "a", "input"} or (tag == "input" and kind not in {"submit", "button"}):
            continue
        words = _haystack(record)
        score = 0
        score += 8 if re.search(r"\btrack\b", words) else 0
        score += 6 if re.search(r"\bsearch\b", words) else 0
        score += 3 if "submit" in words else 0
        score += 4 if tag == "button" or kind in {"submit", "button"} else 0
        score += 3 if record.get("text", "").strip().casefold() in {"track", "search", "track shipment", "track container"} else 0
        candidates.append((score, record))
    return max(candidates, key=lambda item: item[0])[1] if candidates and max(x[0] for x in candidates) > 0 else None


def choose_field_selectors(records: list[dict]) -> dict[str, str]:
    selectors = {}
    for field, labels in FIELD_LABELS.items():
        best = None
        for record in records:
            words = _haystack(record)
            score = max((len(label) for label in labels if label.casefold() in words), default=0)
            if score:
                value_selector = record.get("nextSelector") if record.get("nextText") else record.get("selector")
                candidate = (score + (3 if record.get("nextText") else 0), value_selector)
                if value_selector and (best is None or candidate[0] > best[0]):
                    best = candidate
        if best:
            selectors[field] = best[1]
    return selectors


def _inventory(frame) -> list[dict]:
    return frame.locator("input, textarea, button, a, label, dt, dd, th, td, [data-test], [data-testid], [aria-label]").evaluate_all(INVENTORY_SCRIPT)


def discover_and_retest(carrier: str, tracking_url: str, test_container: str, headless: bool = False) -> SetupOutcome:
    container = test_container.strip().upper()
    if not container:
        return SetupOutcome(False, reason="A test container number is required.")
    try:
        with sync_playwright() as playwright:
            browser, source = launch_installed_browser(playwright, headless, log)
            log.info("Connector setup launched using %s", source)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            response = page.goto(tracking_url, wait_until="domcontentloaded", timeout=90000)
            if response and response.status >= 400:
                browser.close()
                return SetupOutcome(False, reason=f"Tracking website returned HTTP {response.status} before setup.")
            page.wait_for_timeout(3000)
            initial_text = page.locator("body").inner_text(timeout=15000)
            initial_restriction = security_restriction(initial_text)
            if initial_restriction:
                browser.close()
                return SetupOutcome(False, reason=f"Setup stopped: {initial_restriction}. No security control was bypassed.")

            selected = None
            for frame in page.frames:
                try:
                    records = _inventory(frame)
                    input_record = choose_input(records)
                    button_record = choose_button(records)
                    if input_record and button_record:
                        selected = (frame, records, input_record, button_record)
                        break
                except Exception:
                    continue
            if not selected:
                browser.close()
                return SetupOutcome(False, reason="Could not identify both a container-number input and Track/Search button.")

            frame, records, input_record, button_record = selected
            frame.locator(input_record["selector"]).first.fill(container, timeout=10000)
            frame.locator(button_record["selector"]).first.click(timeout=10000)
            page.wait_for_timeout(8000)
            text = frame.locator("body").inner_text(timeout=15000)
            restriction = security_restriction(text)
            if restriction:
                browser.close()
                return SetupOutcome(False, reason=f"Setup stopped: {restriction}. No security control was bypassed.")
            result_records = _inventory(frame)
            field_selectors = choose_field_selectors(result_records)
            config = {
                "input_selector": input_record["selector"],
                "button_selector": button_record["selector"],
                "frame_name": frame.name or "",
                "frame_url_contains": frame_url_hint(frame.url) if frame != page.main_frame else "",
                "field_selectors": field_selectors,
                "result_wait_ms": 8000,
            }
            browser.close()

        provisional = {
            "shipping_line_name": carrier,
            "tracking_url": tracking_url,
            "connector_status": "Ready",
            "config": config,
        }
        retest = track_generic(container, carrier, provisional, headless=headless)
        if not retest.success:
            return SetupOutcome(False, reason=f"Automatic retest failed: {retest.error}", retest_result=retest)
        return SetupOutcome(True, config=config, retest_result=retest)
    except Exception as exc:
        log.exception("Automatic connector setup failed")
        return SetupOutcome(False, reason=str(exc))
