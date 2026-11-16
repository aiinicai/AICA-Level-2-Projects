# Income Tax Return Download Tool

Single HTML page (`static/index.html`) + FastAPI backend (`main.py` +
`session_manager.py`) that:

1. Takes PAN + Password on the page.
2. Backend logs into the real Income Tax e-filing portal with Playwright,
   pulls the registered email & mobile from "My Profile", and shows them
   masked (e.g. `ab**@gmail.com`) on the page.
3. User types the **full** email — if wrong, shows an error and lets them
   retry. Same for mobile. This is the identity check (no OTP step anymore).
4. Once both are confirmed, the page asks for Assessment Year.
5. Backend (still attached to the same browser tab) opens "View Filed
   Returns" for that PAN+year and downloads the ITR-V PDF, which the page
   then auto-downloads to the user's computer.

## Easiest way to run it: double-click `Start Income Tax Return Download.bat`

On a computer that has **never run this tool before** (no Python
installed at all), double-click `Start Income Tax Return Download.bat`
instead of `launcher.pyw` directly. It:

- Checks for Python 3.12. If it's missing, downloads and silently
  installs it from python.org (one-time, needs internet).
- Then hands off to `launcher.pyw` (below) to do everything else.

If Python 3.12 is already installed, you can just double-click
`launcher.pyw` directly — the `.bat` file is only needed for a fresh
computer. Either way, from here on:

Once the one-time setup below is done, you don't need PowerShell or the
Chrome command at all. Just double-click `launcher.pyw` in the project
folder:

- It starts the background automation Chrome itself, fully hidden —
  running in headless mode, so **no Chrome window appears at all**
  (not even off-screen). Only the uvicorn server runs underneath it.
- It starts the server itself.
- It opens `http://localhost:8000` in your normal browser automatically.

A small status window stays open so you can see what's happening. If
anything goes wrong (e.g. Chrome not found at the expected path), the
window will say exactly what and why — the most common one is "Chrome
not found", which means you need to edit the `CHROME_CANDIDATES` list
near the top of `launcher.pyw` to point at your actual `chrome.exe`.

You can close the status window afterwards — the server and the
background Chrome both keep running. The sections below explain what
`launcher.pyw` is doing for you under the hood, and are the fallback if
you ever need to start things manually (e.g. to debug).

### If login suddenly shows "Permission Denied!!" again

`launcher.pyw` now starts the automation Chrome in **headless** mode
(`--headless=new`) so no window shows up anywhere, not even off-screen.
This should still bypass the portal's bot-detection the same way the
visible manual Chrome did, because that detection was tied to
Playwright's own automation flags, not to headless vs. visible — but
it hasn't been tested against the live portal yet. If you test it and
see "Permission Denied!!" or the "enter the key" prompt come back,
tell me and I'll switch `launcher.pyw` back to the off-screen (visible
but pushed off your screen) Chrome window instead, which is already
confirmed working.

## IMPORTANT — the portal blocks automated browsers

The Income Tax e-filing portal shows **"Permission Denied!!"** to any
browser Playwright *launches itself* — even real Chrome via
`--channel=chrome` — because a launched browser carries automation
fingerprints (`navigator.webdriver`, the `--enable-automation` flag, etc).

The fix (same trick your other tools like `itr_auto_flow.py` and
`pan-registration-tool` use): start a completely normal Chrome yourself,
with a debugging port open, and this script **attaches** to that
already-running, human-started window over CDP instead of launching its
own. Because you started it normally, it carries none of those
automation fingerprints.

### Every time before running this tool, start Chrome like this:

Close all other Chrome windows first (or use a separate profile folder as
below so it doesn't touch your normal Chrome at all), then in PowerShell:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-automation-profile" --window-position=-32000,-32000
```

The extra `--window-position=-32000,-32000` pushes this Chrome window
off-screen, so it runs in the background — nobody using the tool sees the
actual Income Tax portal, only your `index.html` page. It's still a
completely normal, non-headless Chrome (so the portal's bot-detection
still doesn't block it) — it's just positioned where you can't see it.

Don't use `--start-minimized` or `--headless` here — both make Chrome
stop actually rendering the page while it's minimized/hidden, which makes
every element look "not visible" to Playwright and every click times out
(this is exactly the "waiting for element to be visible... retrying" loop
you'd see if you tried it). Off-screen-but-not-minimized keeps Chrome
rendering normally, so Playwright can still interact with it — it's just
not on your visible desktop.

Open the tool's own page (`http://localhost:8000`) in a **separate**,
normal Chrome window (or any other browser) — not in this automation
window — so that's the only thing anyone using the tool actually sees.

- `--remote-debugging-port=9222` is the port `session_manager.py`'s
  `CDP_URL = "http://localhost:9222"` connects to — keep them matching.
- `--user-data-dir="C:\chrome-automation-profile"` gives this Chrome its
  own separate profile/cookies, so it doesn't log you out of your normal
  Chrome, and doesn't mix with it. First time you run it, it opens with
  no history/logins — that's expected, you don't need to log in here
  yourself, the tool does it per PAN.
- Leave this Chrome window open in the background the whole time you're
  using the tool. You can minimize it, but don't close it.

Then, in a separate terminal (with your venv activated), run the backend
as usual:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` and use the page. Each PAN submitted opens a
new tab inside that same Chrome window — you'll actually see it working
if you glance at that window.

## Setup (first time only)

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

(The bundled Chromium from this install isn't actually used for the live
automation anymore, since we connect to your real Chrome instead — but
`playwright install` also installs some shared libraries Playwright needs,
so keep this step.)

## IMPORTANT — selectors still need verification against the live portal

I built the Playwright steps in `session_manager.py` from the general,
known structure of eportal.incometax.gov.in, not from a screen recording
of the actual current flow. Every place marked `# VERIFY:` is a best-guess
locator that may need a small fix once you watch it run against the real
Chrome window (now that it can actually reach the login page without
being blocked). Specifically:

| Step | What to check |
|---|---|
| `login()` | PAN/"User ID" field label, Continue button text, whether a "Secure Access Message" confirmation screen appears before the password field, password field label |
| `login()` error detection | exact wording the portal shows for wrong PAN/password |
| `login()` profile scrape | URL of "My Profile", and the selectors for the displayed email and mobile — easiest: in the visible Chrome window, open My Profile, right-click the email value → Inspect, and copy the real selector in place of `page.get_by_test_id("profile-email")` |
| `list_assessment_years()` | URL of "View Filed Returns", and how each assessment year is marked up in the DOM (replace the `[data-ay]` placeholder selector) |
| `download_itrv()` | how you open a specific year's return, and the exact text/label of the "Download ITR-V" link |

Since the automated-browser block is gone now, you can also run
`playwright codegen --cdp-url=http://localhost:9222 https://eportal.incometax.gov.in/iec/foservices/#/login`
(with the Chrome from above already running) to click through the real
flow once and have Playwright print the exact selectors it sees.

## Notes

- Because all sessions share the one real Chrome window, this tool is
  meant for one person at a time to use locally (you), not a public
  multi-user web page — matching how your other PC-based tools work.
- Downloaded PDFs are saved under `downloads/` on the server as well as
  streamed to the browser.
- Session auto-closes its tab after 10 minutes idle, or right after a
  successful download — but it never closes the Chrome window itself.
