"""
session_manager.py
-------------------
Playwright automation against the official Income Tax e-filing portal
(https://eportal.incometax.gov.in), driven over CDP into a REAL, manually
launched Chrome — not a freshly-launched/automated browser.

Why: the portal's bot-protection shows "Permission Denied!!" to any browser
Playwright launches itself (even real Chrome via --channel=chrome), because
a launched browser carries automation flags (navigator.webdriver etc). The
fix, same as your other tools (itr_auto_flow.py, pan-registration-tool), is
to start a normal Chrome yourself with a remote-debugging port open, and
have this script attach to that already-running, human-started browser via
CDP. See README.md for the exact command to launch that Chrome.

IMPORTANT — selectors marked "VERIFY" below are best-effort guesses based on
the general structure of the e-filing 2.0 portal. The portal's DOM changes
over time, so before relying on this in production: watch it hit each
VERIFY line in the real (visible) Chrome window and fix the locator if it
doesn't find the element. See README.md.
"""

import asyncio
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
LOGIN_URL = "https://eportal.incometax.gov.in/iec/foservices/#/login"

# The remote-debugging endpoint of the real Chrome window you start manually
# before running this tool (see README.md for the launch command).
CDP_URL = "http://localhost:9222"

SESSION_IDLE_TIMEOUT_SEC = 10 * 60   # close a tab if nobody touches it for 10 min

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


def mask_email(email: str) -> str:
    """abcd@gmail.com -> ab**@gmail.com (keep first 2 chars of local part)."""
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        visible = local[:1]
    else:
        visible = local[:2]
    return f"{visible}{'*' * max(len(local) - len(visible), 2)}@{domain}"


def mask_mobile(mobile: str) -> str:
    """9876543210 -> 98******10"""
    digits = re.sub(r"\D", "", mobile)
    if len(digits) <= 4:
        return "*" * len(digits)
    return f"{digits[:2]}{'*' * (len(digits) - 4)}{digits[-2:]}"


@dataclass
class Session:
    session_id: str
    pan: str
    browser: Browser
    context: BrowserContext
    page: Page
    email_full: str = ""
    mobile_full: str = ""
    email_confirmed: bool = False
    mobile_confirmed: bool = False
    last_touch: float = field(default_factory=time.time)

    def touch(self):
        self.last_touch = time.time()


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._pw = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        self._pw = await async_playwright().start()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
        for sid in list(self._sessions.keys()):
            await self._close_session(sid)
        if self._pw:
            await self._pw.stop()

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(60)
            now = time.time()
            for sid, sess in list(self._sessions.items()):
                if now - sess.last_touch > SESSION_IDLE_TIMEOUT_SEC:
                    await self._close_session(sid)

    async def _close_session(self, session_id: str):
        sess = self._sessions.pop(session_id, None)
        if sess:
            # Only close the tab we opened — never the context/browser,
            # since that's your real, manually-launched Chrome shared
            # across sessions. Closing it here would close your browser.
            try:
                await sess.page.close()
            except Exception:
                pass

    def get(self, session_id: str) -> Optional[Session]:
        sess = self._sessions.get(session_id)
        if sess:
            sess.touch()
        return sess

    # ------------------------------------------------------------------
    # Step 1: Login with PAN + Password, then scrape registered email/mobile
    # ------------------------------------------------------------------
    async def login(self, pan: str, password: str) -> dict:
        try:
            browser = await self._pw.chromium.connect_over_cdp(CDP_URL)
        except Exception as exc:
            return {
                "ok": False,
                "error": (
                    "Could not connect to your Chrome window on "
                    f"{CDP_URL}. Make sure you started Chrome with the "
                    "remote-debugging-port command from README.md before "
                    f"running this tool. ({exc})"
                ),
            }

        context = browser.contexts[0] if browser.contexts else await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        # Chrome throttles rendering/layout for background (non-active)
        # tabs, which is what was actually causing "Element is not
        # visible" even with force=True — the window's on-screen position
        # doesn't matter for this, only whether the TAB itself is active.
        # This keeps the tab active within its own (still off-screen,
        # still invisible-to-you) window.
        await page.bring_to_front()

        session_id = str(uuid.uuid4())
        sess = Session(session_id=session_id, pan=pan, browser=browser,
                        context=context, page=page)
        self._sessions[session_id] = sess  # register early so cleanup can close the tab on any failure below

        try:
            await page.goto(LOGIN_URL, wait_until="networkidle")

            # --- Enter PAN (User ID) ---------------------------------
            # Confirmed real selector (from live portal, 2026-11-14, via
            # the user's own browser inspect — note the portal's own typo,
            # "Adhaar" not "Aadhaar", in the id/name):
            # <input id="panAdhaarUserId" name="panAdhaarUserId"
            #        placeholder="PAN/ Aadhaar/ Other User ID">
            user_id_box = page.locator("#panAdhaarUserId")
            await user_id_box.fill(pan, force=True)

            # VERIFY: "Continue" button text.
            await page.get_by_role("button", name=re.compile("continue", re.I)).click(force=True)
            await page.wait_for_load_state("networkidle")

            # --- Secure Access Message + Password screen ----------------
            # Confirmed real selectors (from live portal, 2026-11-14):
            # the "Continue" button here stays disabled until BOTH the
            # secure-access checkbox is ticked AND the password is filled.
            # <input type="checkbox" id="passwordCheckBox-input">
            await page.locator("#passwordCheckBox-input").check(force=True)

            # VERIFY: password field id — using label/type fallback for now
            # since the exact id wasn't captured; replace with the real
            # id once you inspect it (right-click the Password field →
            # Inspect, same way the User ID / checkbox ones were found).
            pwd_box = page.get_by_label(re.compile("password", re.I))
            if await pwd_box.count() == 0:
                pwd_box = page.locator("input[type='password']")
            await pwd_box.first.fill(password, force=True)

            await page.get_by_role("button", name=re.compile("continue|login", re.I)).click(force=True)

            # --- Handle transient quirks before the dashboard shows up ----
            # Confirmed real behaviour (2026-11-14):
            #  (a) sometimes a red "Error: Request is not authenticated"
            #      box appears — just clicking Continue again clears it.
            #  (b) if a previous session is still open elsewhere, a "Dual
            #      Login Detected!" modal appears with a "Login Here"
            #      button — clicking it continues the login.
            # Loop a few times handling whichever shows up, until the URL
            # actually moves to the dashboard.
            for _ in range(6):
                if "/dashboard" in page.url:
                    break
                await page.wait_for_timeout(1500)
                if "/dashboard" in page.url:
                    break

                dual_login_btn = page.get_by_role("button", name=re.compile("login here", re.I))
                if await dual_login_btn.count() > 0:
                    await dual_login_btn.first.click(force=True)
                    continue

                auth_error = page.get_by_text(re.compile("not authenticated", re.I))
                if await auth_error.count() > 0:
                    retry_btn = page.get_by_role("button", name=re.compile("continue", re.I))
                    if await retry_btn.count() > 0:
                        try:
                            await retry_btn.first.click(timeout=3000, force=True)
                        except Exception:
                            pass
                    continue

            # --- Detect login success / failure --------------------------
            # Confirmed real behaviour (2026-11-14): on success the portal
            # redirects to a dashboard URL containing "/dashboard" (e.g.
            # .../#/dashboard/fileIncomeTaxReturn). This is an Angular SPA,
            # so the URL changes client-side slightly after networkidle —
            # wait for it explicitly instead of racing it.
            try:
                await page.wait_for_url(re.compile(r"/dashboard"), timeout=20000)
            except Exception:
                await self._close_session(session_id)
                return {"ok": False, "error": "Invalid PAN or Password"}
            await page.wait_for_load_state("networkidle")

            # --- Fetch registered email & mobile from My Profile --------
            # IMPORTANT: the portal disables browser Back/Forward/Refresh
            # and treats a direct page.goto() to an internal URL the same
            # way — it pops a "we have disabled Back/Forward/Refresh...
            # are you sure you want to Logout?" dialog. So we must navigate
            # the same way a real user would: click the account menu, then
            # click "My Profile" — never page.goto() into the dashboard.
            #
            # VERIFY: the exact selector for the top-right account menu
            # trigger (the "<Name> / Individual" button with a dropdown
            # chevron) — this is a best guess using its "Individual" text;
            # if it doesn't open the menu, right-click that button →
            # Inspect, and send the HTML the same way you did for the
            # User ID field / checkbox, and I'll correct this locator.
            # Confirmed real selector (2026-11-14):
            # <button class="mat-mdc-menu-trigger profileMenubtn ...">
            account_menu_trigger = page.locator("button.profileMenubtn")
            await account_menu_trigger.first.click(force=True)
            # Give the dropdown's open animation a moment before clicking
            # inside it — clicking mid-animation can land on the wrong
            # (still-collapsed) coordinates.
            await page.wait_for_timeout(800)
            # Confirmed real selector (2026-11-14): the dropdown's items
            # are mat-menu-item buttons with role="menuitem".
            await page.get_by_role("menuitem", name="My Profile").click(force=True)

            # This is a hash-based Angular SPA route change, not a real
            # page navigation, so wait_for_url's default "load" condition
            # never fires (it already caused one timeout here) — poll
            # page.url manually instead, same approach used for detecting
            # the dashboard redirect after login.
            for _ in range(15):
                if "myprofile" in page.url.lower():
                    break
                await page.wait_for_timeout(1000)
            else:
                await self._close_session(session_id)
                return {"ok": False, "error": "Could not open My Profile"}
            await page.wait_for_load_state("networkidle")

            # Confirmed real layout (2026-11-14): under a "Contact" card,
            # there's a "Mobile" block (Primary (Self) value) and an
            # "Email" block (Primary (Self) value). Rather than guess at
            # the exact DOM structure, pull the whole page's visible text
            # and regex out the first email/phone that appear after the
            # word "Contact" — matches "+91 9466655760" / "jagat0671@gmail.com"
            # style values seen on the real page.
            # Give the Contact card a moment in case it loads from a
            # slightly slower async call than the rest of the page.
            try:
                await page.get_by_text("Contact", exact=True).first.wait_for(
                    timeout=8000, state="attached"
                )
            except Exception:
                pass
            await page.wait_for_timeout(1000)

            full_text = await page.locator("body").inner_text()
            contact_idx = full_text.find("Contact")
            scope_text = full_text[contact_idx:] if contact_idx != -1 else full_text

            email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", scope_text)
            mobile_match = re.search(r"\+91\s*\d{10}", scope_text)

            if not email_match or not mobile_match:
                # Deliberately NOT printing the page text here — it would
                # contain the partner's name, PAN, email, mobile, address
                # etc. in plain text in whatever log captures stdout. If
                # this ever fires again, reproduce it locally and inspect
                # the live My Profile page directly instead of logging
                # its contents.
                await self._close_session(session_id)
                return {"ok": False, "error": "Could not read registered email/mobile from My Profile"}

            email_full = email_match.group(0).strip()
            mobile_full = mobile_match.group(0).strip()

            sess.email_full = email_full
            sess.mobile_full = mobile_full
            self._sessions[session_id] = sess

            return {
                "ok": True,
                "session_id": session_id,
                "masked_email": mask_email(email_full),
                "masked_mobile": mask_mobile(mobile_full),
            }

        except Exception as exc:
            await self._close_session(session_id)
            return {"ok": False, "error": f"Login automation failed: {exc}"}

    # ------------------------------------------------------------------
    # Step 2: User types full email / mobile to confirm identity
    # ------------------------------------------------------------------
    def confirm_email(self, session_id: str, typed_email: str) -> bool:
        sess = self.get(session_id)
        if not sess:
            return False
        ok = typed_email.strip().lower() == sess.email_full.strip().lower()
        sess.email_confirmed = ok
        return ok

    def confirm_mobile(self, session_id: str, typed_mobile: str) -> bool:
        sess = self.get(session_id)
        if not sess:
            return False
        ok = re.sub(r"\D", "", typed_mobile) == re.sub(r"\D", "", sess.mobile_full)
        sess.mobile_confirmed = ok
        return ok

    # ------------------------------------------------------------------
    # Step 3: Once both email and mobile are confirmed, list the
    # assessment years available for this PAN (no OTP step anymore).
    # ------------------------------------------------------------------
    async def list_assessment_years(self, session_id: str) -> dict:
        sess = self.get(session_id)
        if not sess:
            return {"ok": False, "error": "Session expired"}
        if not (sess.email_confirmed and sess.mobile_confirmed):
            return {"ok": False, "error": "Email and mobile must both be confirmed first"}

        page = sess.page

        # The tab usually sits idle for a while (user is typing email,
        # mobile, OTP on the page) between login() finishing and this
        # step running — Chrome can throttle an inactive tab's rendering
        # during that gap, which is what caused the occasional timeout
        # right after OTP verification. bring_to_front() re-activates
        # it, but the renderer needs a moment to actually catch up, so
        # we wait a bit before clicking, and retry once if a timeout
        # still slips through.
        last_exc: Optional[Exception] = None
        for attempt in range(2):
            try:
                await page.bring_to_front()
                await page.wait_for_timeout(800)

                # Navigate the same way a real user would (click-based),
                # not page.goto(), to avoid the portal's "Back/Forward/
                # Refresh disabled — Logout?" dialog — same lesson as the
                # My Profile step.
                #
                # Confirmed real behaviour (2026-11-16, from a live,
                # visible run): "Income Tax Returns" is a nested-menu
                # TRIGGER (it has a ">" chevron) — its flyout submenu
                # (which contains "View Filed Returns") opens on HOVER,
                # not on click. A .click() there doesn't open it, so the
                # next step's locator for "View Filed Returns" never
                # finds anything and times out. Hover it instead, then
                # give the flyout animation a moment before clicking
                # inside it.
                await page.get_by_text("e-File", exact=True).first.click(timeout=20000, force=True)
                await page.get_by_role("menuitem", name="Income Tax Returns").hover(timeout=20000)
                await page.wait_for_timeout(1000)
                await page.get_by_role("menuitem", name="View Filed Returns").click(timeout=20000, force=True)

                try:
                    await page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    # Some background polling on this page can keep the
                    # network "busy" forever — don't fail the whole step
                    # just because networkidle never strictly settles.
                    pass
                await page.wait_for_timeout(1500)

                # Confirmed real layout (2026-11-14): each filed return is
                # shown under a heading like "A.Y. 2026-27".
                year_headings = page.get_by_text(re.compile(r"A\.Y\.\s*\d{4}-\d{2}"))
                count = await year_headings.count()
                years = []
                for i in range(count):
                    text = (await year_headings.nth(i).inner_text()).strip()
                    m = re.search(r"\d{4}-\d{2}", text)
                    if m:
                        years.append(m.group(0))
                years = sorted(set(years), reverse=True)
                return {"ok": True, "years": years}
            except Exception as exc:
                last_exc = exc
                continue  # one retry before giving up

        return {"ok": False, "error": f"Could not fetch assessment years: {last_exc}"}

    # ------------------------------------------------------------------
    # Step 4: Download the ITR-V PDF for the chosen year
    # ------------------------------------------------------------------
    async def download_itrv(self, session_id: str, assessment_year: str) -> dict:
        sess = self.get(session_id)
        if not sess:
            return {"ok": False, "error": "Session expired"}
        if not (sess.email_confirmed and sess.mobile_confirmed):
            return {"ok": False, "error": "Email and mobile must both be confirmed first"}

        page = sess.page
        await page.bring_to_front()
        try:
            # Find the "A.Y. <year>" heading for the chosen year, then the
            # "Download Receipt" button within that same card (that button
            # is confirmed to be the ITR-V acknowledgement/receipt, from
            # the real "View Filed Returns" page layout, 2026-11-14).
            # Confirmed real selector (2026-11-14):
            # <button class="downloadButton wid100 drecback"> Download Receipt </button>
            # Scope to the nearest ancestor of the "A.Y. <year>" heading
            # that actually contains a "Download Receipt" button, so this
            # still works once a PAN has multiple years listed.
            year_heading = page.get_by_text(re.compile(rf"A\.Y\.\s*{re.escape(assessment_year)}")).first
            card = year_heading.locator(
                "xpath=ancestor::*[.//button[contains(., 'Download Receipt')]][1]"
            )
            download_btn = card.locator("button.downloadButton", has_text="Download Receipt")
            if await download_btn.count() == 0:
                # Fallback for a single-filing page where the ancestor
                # search above doesn't find a wrapping match.
                download_btn = page.locator("button.downloadButton", has_text="Download Receipt")

            async with page.expect_download() as download_info:
                await download_btn.first.click(force=True)
            download = await download_info.value

            dest = DOWNLOAD_DIR / f"ITRV_{sess.pan}_{assessment_year}.pdf"
            await download.save_as(dest)

            return {"ok": True, "file": str(dest)}
        except Exception as exc:
            return {"ok": False, "error": f"Could not download ITR-V: {exc}"}
        finally:
            await self._close_session(session_id)


manager = SessionManager()