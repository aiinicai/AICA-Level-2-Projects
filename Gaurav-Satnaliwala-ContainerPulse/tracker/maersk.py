from __future__ import annotations
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from .common import TrackingResult, debug_save, detect_access_block, logger_for
from .browser import launch_installed_browser


def _url(container: str) -> str:
    return f"https://www.maersk.com/tracking/{container}"


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _result_state(page, timeout: int = 60000) -> str:
    """Wait for either a rendered tracking result or Maersk's public no-result state."""
    page.wait_for_function(
        """() => document.querySelector('[data-test="container"]') ||
                  document.querySelector('[data-test="track-error"]')""",
        timeout=timeout,
    )
    if page.locator('[data-test="container"]').count():
        return "result"
    if page.locator('[data-test="track-error"]').count():
        return "no_results"
    return "unknown"


def _accept_cookies(page, log) -> None:
    for label in ["Allow all", "Accept all", "Accept All", "I agree", "Essential only"]:
        try:
            page.get_by_role("button", name=label, exact=True).click(timeout=2500)
            log.info("Maersk cookie dialog handled with button=%s", label)
            return
        except Exception:
            pass


def _submit_tracking_form(page, container: str, log) -> str:
    """Submit Maersk's visible public tracking form; no carrier API is used."""
    host = page.locator('[data-test="track-input"]').first
    host.wait_for(state="visible", timeout=30000)
    input_box = host.locator("input:visible").first
    input_box.fill(container, timeout=10000)
    page.locator('[data-test="track-button"]').first.click(timeout=10000)
    log.info("Maersk public tracking form submitted for %s", container)
    page.wait_for_timeout(3500)
    return _result_state(page)


def _parse_maersk_visible_text(text: str, container: str) -> dict[str, str | bool | None]:
    """Fallback for rendered-data selector changes; parses only visible browser text."""
    lines = [_clean(line) for line in (text or "").splitlines() if _clean(line)]
    date_pattern = re.compile(r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}$")
    events = []
    for index, line in enumerate(lines):
        if date_pattern.match(line) and index >= 3:
            milestone = lines[index - 1]
            location = lines[index - 3]
            events.append({"date": line, "milestone": milestone, "location": location})
    first = events[0] if events else {}
    final_arrival = next((event for event in reversed(events) if "arrival" in event["milestone"].lower()), events[-1] if events else {})
    vessel_match = re.search(r"\(([^/()]+?)\s*/\s*[^)]+\)", first.get("milestone", ""))
    return {
        "accepted": container in (text or "").upper(),
        "eta": final_arrival.get("date"),
        "status": "Planned / awaiting first milestone" if events else None,
        "location": f'{first.get("location")} (planned origin)' if first.get("location") else None,
        "vessel": vessel_match.group(1).strip() if vessel_match else None,
        "event": "No completed tracking event displayed" if events else None,
        "last_updated": None,
        "timeline": events,
    }


def _rendered_fields(page, container: str, log) -> dict[str, str | bool | None]:
    """Extract Maersk's rendered web components and timeline (no API use)."""
    panel = page.locator('[data-test="container"]').first
    panel.wait_for(state="visible", timeout=30000)
    panel_text = panel.inner_text(timeout=10000)

    # ETA is rendered inside the open shadow root of mc-text-and-icon.
    eta_host = page.locator('[data-test="container-eta"]').first
    eta_text = eta_host.evaluate(
        "el => el.shadowRoot ? el.shadowRoot.textContent : el.textContent"
    ) if eta_host.count() else ""
    eta = re.sub(r"^.*?Estimated arrival date\s*", "", _clean(eta_text), flags=re.I) or None

    items = []
    timeline = page.locator('[data-test="transport-plan"] li')
    for index in range(timeline.count()):
        item = timeline.nth(index)
        state = item.get_attribute("data-test") or ""
        milestone_locator = item.locator('[data-test="milestone"]')
        date_locator = item.locator('[data-test="milestone-date"]')
        location_locator = item.locator('[data-test="location-name"] strong')
        milestone = _clean(milestone_locator.inner_text()) if milestone_locator.count() else ""
        date = _clean(date_locator.inner_text()) if date_locator.count() else ""
        location = _clean(location_locator.inner_text()) if location_locator.count() else ""
        items.append({
            "state": state,
            "milestone": milestone,
            "date": date,
            "location": location,
        })

    completed = [item for item in items if "future" not in item["state"].lower()]
    latest = completed[-1] if completed else None
    next_item = next((item for item in items if "future" in item["state"].lower()), None)

    if latest:
        status = latest["milestone"].split("(", 1)[0].strip() or "In progress"
        location = latest["location"] or None
        event = " | ".join(x for x in [latest["date"], latest["location"], latest["milestone"]] if x)
        vessel_source = latest["milestone"]
    else:
        status = "Planned / awaiting first milestone"
        location = f'{next_item["location"]} (planned origin)' if next_item and next_item["location"] else None
        event = "No completed tracking event displayed"
        vessel_source = next_item["milestone"] if next_item else ""

    vessel_match = re.search(r"\(([^/()]+?)\s*/\s*[^)]+\)", vessel_source)
    vessel = vessel_match.group(1).strip() if vessel_match else None

    last_updated = None
    last_updated_locator = page.locator('[data-test="last-updated"]').first
    if last_updated_locator.count():
        last_updated = _clean(last_updated_locator.inner_text())

    log.info("Maersk selectors: panel=[data-test=container], ETA shadow host=[data-test=container-eta], timeline=[data-test=transport-plan] li")
    log.info("Maersk rendered extraction: eta=%r status=%r location=%r vessel=%r last_event=%r", eta, status, location, vessel, event)
    return {
        "accepted": container in panel_text.upper(),
        "eta": eta,
        "status": status,
        "location": location,
        "vessel": vessel,
        "event": event,
        "last_updated": last_updated,
        "timeline": items,
    }


def track_maersk(container: str, headless: bool = True) -> TrackingResult:
    url = _url(container)
    log = logger_for("MAERSK")
    try:
        log.info("Starting Maersk test for %s", container)
        with sync_playwright() as p:
            log.info("Launching an already-installed browser (headless=%s)", headless)
            browser, browser_source = launch_installed_browser(p, headless, log)
            log.info("Browser source: %s", browser_source)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            response = page.goto(url, wait_until="domcontentloaded", timeout=90000)
            log.info("Maersk page opened: HTTP %s, URL %s", response.status if response else "unknown", page.url)
            # The successful POC showed that tracking data renders underneath
            # Maersk's cookie dialog. Dismissing it too early can reload/reset
            # the search, so leave the initial direct-link page undisturbed.
            log.info("Waiting for Maersk direct-link result state")
            try:
                state = _result_state(page)
            except Exception as readiness_error:
                state = "unknown"
                log.warning("Maersk direct-link result did not render: %s", str(readiness_error).splitlines()[0])

            if state == "no_results":
                log.warning("Maersk direct URL returned No results found; retrying through the visible public form")
                _accept_cookies(page, log)
                state = _submit_tracking_form(page, container, log)

            if state == "no_results":
                log.warning("Maersk form retry returned No results found; retrying once from the tracking landing page")
                page.goto("https://www.maersk.com/tracking/", wait_until="domcontentloaded", timeout=90000)
                _accept_cookies(page, log)
                state = _submit_tracking_form(page, container, log)

            if state == "result":
                try:
                    page.wait_for_function(
                        """() => {
                            const eta = document.querySelector('[data-test="container-eta"]');
                            const plan = document.querySelectorAll('[data-test="transport-plan"] li');
                            return eta && (eta.shadowRoot?.textContent || eta.textContent || '').trim() && plan.length > 0;
                        }""",
                        timeout=30000,
                    )
                    log.info("Maersk tracking components are fully rendered")
                except Exception as component_error:
                    log.warning("Maersk result appeared but components were incomplete: %s", str(component_error).splitlines()[0])
            text = page.locator("body").inner_text(timeout=15000)
            debug_save(container, "MAERSK", text)
            debug_dir = Path("tracking_debug")
            debug_dir.mkdir(exist_ok=True)
            (debug_dir / f"maersk_{container}.html").write_text(page.content(), encoding="utf-8")
            page.screenshot(path=f"tracking_debug/maersk_{container}_fullpage.png", full_page=True)
            block = detect_access_block(text)
            if block:
                log.warning("Maersk access block: %s", block)
                browser.close()
                return TrackingResult(container, "MAERSK", False, True, False, block,
                                      source_url=url, raw_excerpt=text[:1200], error=block)

            if state == "no_results":
                log.warning("Maersk public website returned No results found after direct and form-based attempts")
                browser.close()
                return TrackingResult(
                    container, "MAERSK", False, True, True, None,
                    source_url=url, raw_excerpt=text[:1200],
                    error="Maersk public tracking returned 'No results found' after retrying through the visible tracking form.",
                )

            frame_info = page.locator("iframe").evaluate_all(
                "els => els.map(x => ({src:x.src, name:x.name, title:x.title}))"
            )
            shadow_hosts = page.locator("*").evaluate_all(
                "els => els.filter(x => x.shadowRoot).map(x => ({tag:x.tagName.toLowerCase(), id:x.id, dataTest:x.getAttribute('data-test')}))"
            )
            eta_locator = page.locator('[data-test="container-eta"]').first
            eta_shadow = eta_locator.evaluate(
                "el => ({text:el.shadowRoot?.textContent || '', html:el.shadowRoot?.innerHTML || ''})"
            ) if eta_locator.count() else {"text": "", "html": ""}
            (debug_dir / f"maersk_{container}_dom_inspection.json").write_text(
                json.dumps({"iframes": frame_info, "shadow_hosts": shadow_hosts, "eta_shadow_root": eta_shadow}, indent=2),
                encoding="utf-8",
            )
            try:
                fields = _rendered_fields(page, container, log)
            except Exception as selector_error:
                log.warning("Maersk primary selectors failed; using rendered visible-text fallback: %s", str(selector_error).splitlines()[0])
                fields = _parse_maersk_visible_text(text, container)
                log.info("Maersk fallback extraction: eta=%r status=%r location=%r vessel=%r", fields["eta"], fields["status"], fields["location"], fields["vessel"])
            browser.close()

        eta = fields["eta"]
        status = fields["status"]
        location = fields["location"]
        vessel = fields["vessel"]
        event = fields["event"]
        accepted = bool(fields["accepted"])
        ok = accepted and bool(eta or status or location or vessel or event)
        log.info("Maersk extraction complete: success=%s", ok)
        return TrackingResult(container, "MAERSK", ok, True, accepted, None,
                              eta, status, location, vessel, event, url,
                              raw_excerpt=text[:1200],
                              error=None if ok else "Page opened, but structured tracking fields were not detected. Check tracking_debug output.")
    except Exception as e:
        log.exception("Maersk test failed at browser/navigation stage")
        return TrackingResult(container, "MAERSK", False, source_url=url, error=str(e))
