"""Form 26AS download helper (browser robot).

Opens a normal browser window on the income-tax e-filing portal, fills the PAN,
waits while the user signs in, then walks to Form 26AS on TRACES and saves the
file into the client's folder.

What it deliberately does NOT do:
  * It never asks for, sees or stores the portal password or any OTP. The user
    types these in the portal's own page.
  * It does not try to get past a captcha or any other check. If the portal
    asks for one, the user answers it and the robot carries on.

Every automatic step is best effort. If the portal's screens have changed and a
step cannot be done, the robot says which step to do by hand and keeps watching
the folder, so the download still lands in the right place.

Run by the app as:  python -m advtax.portal_26as --out <folder> --status <file>
with the PAN in the ADVTAX_PAN environment variable.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

LOGIN_URL = "https://eportal.incometax.gov.in/iec/foservices/#/login"
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
LOGIN_WAIT = 600      # seconds allowed for the user to sign in
DOWNLOAD_WAIT = 900   # seconds the robot keeps watching for the file
PARTIAL = (".crdownload", ".tmp", ".part")

MANUAL_STEPS = ("In the browser: e-File > Income Tax Returns > View Form 26AS > Confirm. On TRACES tick the box, "
                "Proceed, open 'View Tax Credit (Form 26AS/Annual Tax Statement)', choose the year, View As HTML, "
                "View / Download, then Export as PDF.")


# ------------------------------------------------------------------ helpers
def valid_pan(pan: str) -> bool:
    return bool(PAN_RE.match((pan or "").strip().upper()))


def assessment_year(tax_year: str) -> str:
    """'2026-27' -> '2027-28': the year label TRACES lists for that tax year."""
    start = int(tax_year[:4]) + 1
    return f"{start}-{str(start + 1)[-2:]}"


def safe_folder_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name or "").strip(" .")
    return re.sub(r"\s+", " ", cleaned)[:80] or "client"


def downloaded_files(folder: Path) -> list[Path]:
    """Finished downloads in the folder, newest first (status files and part-files left out)."""
    if not folder.exists():
        return []
    files = [f for f in folder.iterdir()
             if f.is_file() and not f.name.startswith("_") and not f.name.lower().endswith(PARTIAL)]
    return sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)


class Status:
    """Progress written to a small JSON file that the app shows on screen."""

    def __init__(self, path: Path):
        self.path, self.data = Path(path), {"state": "running", "steps": [], "files": []}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write()

    def say(self, message: str, state: str | None = None) -> None:
        self.data["steps"].append({"time": datetime.now().strftime("%H:%M:%S"), "message": message})
        if state:
            self.data["state"] = state
        self._write()

    def files(self, names: list[str]) -> None:
        self.data["files"] = names
        self._write()

    def _write(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)


def read_status(path: Path) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ browser
def open_browser(download_dir: Path):
    """A visible Chrome window, or Edge if Chrome is not installed, saving downloads into the folder."""
    from selenium import webdriver

    prefs = {"download.default_directory": str(download_dir), "download.prompt_for_download": False,
             "plugins.always_open_pdf_externally": True}
    errors = []
    for options_cls, driver_cls in ((webdriver.ChromeOptions, webdriver.Chrome), (webdriver.EdgeOptions, webdriver.Edge)):
        try:
            options = options_cls()
            options.add_experimental_option("prefs", prefs)
            options.add_argument("--start-maximized")
            return driver_cls(options=options)
        except Exception as exc:  # noqa: BLE001 - try the next browser
            errors.append(f"{driver_cls.__module__.split('.')[-2]}: {str(exc).splitlines()[0][:120]}")
    raise RuntimeError("Could not open Chrome or Edge. " + " | ".join(errors))


def _visible(driver, xpath: str):
    from selenium.webdriver.common.by import By

    for el in driver.find_elements(By.XPATH, xpath):
        try:
            if el.is_displayed():
                return el
        except Exception:  # noqa: BLE001 - element went stale, look at the next one
            continue
    return None


def _wait_for(driver, xpath: str, seconds: float = 20):
    end = time.time() + seconds
    while time.time() < end:
        el = _visible(driver, xpath)
        if el is not None:
            return el
        time.sleep(0.5)
    return None


def _click(driver, el) -> None:
    try:
        el.click()
    except Exception:  # noqa: BLE001 - covered by another element; click through script instead
        driver.execute_script("arguments[0].click();", el)


def click_text(driver, *texts: str, seconds: float = 20) -> bool:
    """Click the first visible link, button or menu item showing one of the texts."""
    parts = []
    for t in texts:
        low = t.lower()
        cond = f"contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),\"{low}\")"
        val = f"contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),\"{low}\")"
        parts.append(f"//a[{cond}] | //button[{cond}] | //input[@type='button' or @type='submit'][{val}] "
                     f"| //*[@role='menuitem'][{cond}] | //span[{cond} and not(*)]")
    el = _wait_for(driver, " | ".join(parts), seconds)
    if el is None:
        return False
    _click(driver, el)
    return True


def choose_option(driver, wanted: str, seconds: float = 15) -> bool:
    """Pick the first drop-down option whose text contains the wanted text."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select

    end = time.time() + seconds
    while time.time() < end:
        for sel in driver.find_elements(By.TAG_NAME, "select"):
            try:
                for opt in sel.find_elements(By.TAG_NAME, "option"):
                    if wanted.lower() in (opt.text or "").lower():
                        Select(sel).select_by_visible_text(opt.text)
                        return True
            except Exception:  # noqa: BLE001
                continue
        time.sleep(0.5)
    return False


# --------------------------------------------------------------------- flow
def fill_pan(driver, pan: str) -> bool:
    box = _wait_for(driver, "//input[@id='panAdhaarUserId'] | //input[@type='text' and not(@readonly)]", 40)
    if box is None:
        return False
    box.clear()
    box.send_keys(pan)
    return click_text(driver, "continue", seconds=10)


def wait_for_login(driver, seconds: int = LOGIN_WAIT) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if "dashboard" in (driver.current_url or "").lower():
            return True
        time.sleep(1)
    return False


def walk_to_26as(driver, ay: str, status: Status) -> bool:
    """From the portal dashboard to the 26AS export. Returns False at the first step that cannot be done."""
    steps = [
        ("open the e-File menu", lambda: click_text(driver, "e-file")),
        ("open Income Tax Returns", lambda: click_text(driver, "income tax returns")),
        ("choose View Form 26AS", lambda: click_text(driver, "view form 26as")),
        ("confirm the move to TRACES", lambda: click_text(driver, "confirm")),
    ]
    for label, action in steps:
        if not action():
            status.say(f"Could not {label} automatically. {MANUAL_STEPS}")
            return False
        time.sleep(1.5)

    end = time.time() + 30  # TRACES opens in a new tab
    while time.time() < end and len(driver.window_handles) < 2:
        time.sleep(0.5)
    driver.switch_to.window(driver.window_handles[-1])
    status.say("TRACES opened.")

    box = _wait_for(driver, "//input[@type='checkbox']", 30)
    if box is not None and not box.is_selected():
        _click(driver, box)
    traces = [
        ("press Proceed on TRACES", lambda: click_text(driver, "proceed")),
        ("open View Tax Credit (Form 26AS)", lambda: click_text(driver, "view tax credit")),
        (f"choose the year {ay}", lambda: choose_option(driver, ay)),
        ("choose View As HTML", lambda: choose_option(driver, "html")),
        ("press View / Download", lambda: click_text(driver, "view / download", "view/download")),
        ("press Export as PDF", lambda: click_text(driver, "export as pdf", seconds=40)),
    ]
    for label, action in traces:
        if not action():
            status.say(f"Could not {label} automatically. Please do this step in the browser; "
                       "the file will still be saved in the client's folder.")
            return False
        time.sleep(1.5)
    return True


def run(pan: str, out: Path, status_path: Path, tax_year: str = "2026-27") -> int:
    status = Status(status_path)
    out.mkdir(parents=True, exist_ok=True)
    before = {f.name for f in downloaded_files(out)}
    try:
        import selenium  # noqa: F401
    except ImportError:
        status.say("The browser robot is not installed. Close the app and start it again with "
                   "'Start Advance Tax Desk.bat' so it can install it.", "failed")
        return 2
    try:
        driver = open_browser(out)
    except Exception as exc:  # noqa: BLE001
        status.say(str(exc).splitlines()[0][:300], "failed")
        return 2
    try:
        driver.get(LOGIN_URL)
        status.say("Portal opened." + (" PAN filled." if fill_pan(driver, pan) else " Enter the PAN in the browser."))
        status.say("Waiting for you: type the password (and OTP, if asked) in the browser window.")
        if not wait_for_login(driver):
            status.say("Sign-in was not completed in 10 minutes. Press the button again to retry.", "failed")
            return 1
        status.say("Signed in. Going to Form 26AS.")
        ay = assessment_year(tax_year)
        if walk_to_26as(driver, ay, status):
            status.say("Export requested. Waiting for the file.")
        end = time.time() + DOWNLOAD_WAIT
        while time.time() < end:
            new = [f.name for f in downloaded_files(out) if f.name not in before]
            if new:
                status.files(new)
                status.say(f"Saved: {', '.join(new)}. You can close the browser.", "done")
                time.sleep(20)
                return 0
            _ = driver.window_handles  # raises once the user closes the browser
            time.sleep(2)
        status.say("No file arrived in 15 minutes. Press the button again to retry.", "failed")
        return 1
    except Exception as exc:  # noqa: BLE001 - most often the user closed the browser
        closed = "no such window" in str(exc).lower() or "disconnected" in str(exc).lower() or "closed" in str(exc).lower()
        status.say("The browser was closed before a file was saved." if closed
                   else f"Stopped: {str(exc).splitlines()[0][:160]}", "closed" if closed else "failed")
        return 1
    finally:
        try:
            driver.quit()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Download Form 26AS with the user signing in by hand.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--status", required=True)
    ap.add_argument("--tax-year", default="2026-27")
    args = ap.parse_args()
    pan_value = os.environ.get("ADVTAX_PAN", "").strip().upper()
    if not valid_pan(pan_value):
        Status(Path(args.status)).say("The PAN is not valid.", "failed")
        raise SystemExit(2)
    raise SystemExit(run(pan_value, Path(args.out), Path(args.status), args.tax_year))
