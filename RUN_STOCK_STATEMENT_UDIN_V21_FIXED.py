"""
Stock Statement + ICAI UDIN assistant.

Runs a small local web server that:
  1. serves the Stock Statement HTML application,
  2. keeps all application data in a plain folder next to this script
     (StockStatementData/) so moving the folder moves the data with it,
  3. drives Microsoft Edge through the ICAI UDIN login, relaying the CAPTCHA
     picture back to the application so the CAPTCHA can be typed there
     instead of in the browser window.
"""

import base64
import json
import re
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, unquote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait


# ==========================================================================
# PATHS
# Everything resolves relative to this file, so the whole folder can be
# moved or copied anywhere and it still finds its own data.
# ==========================================================================

APP_DIR = Path(__file__).resolve().parent
APP = APP_DIR / "Stock_Statement_Drawing_Power_UDIN_Integrated_v20.html"
DATA_DIR = APP_DIR / "StockStatementData"
ATTACH_DIR = DATA_DIR / "attachments"
MISC_DIR = DATA_DIR / "misc"

HOST = "127.0.0.1"
PREFERRED_PORT = 25765
PORT_SPAN = 20
ENGINE_SIGNATURE = "stock-statement-udin-engine"
ICAI_LOGIN_URL = "https://udin.icai.org/ICAI/login"

CAPTCHA_WAIT_SECONDS = 900
MAX_LOGIN_ATTEMPTS = 6


# ==========================================================================
# FILE-BACKED KEY/VALUE STORE
#
# The HTML application talks to window.storage.get/set/delete. Those calls
# now land here instead of in the browser's IndexedDB, which was scoped to
# the origin and so lost everything whenever the server landed on a
# different port.
# ==========================================================================

KEY_FILES = {
    "stock-statement:current": "current.json",
    "stock-statement:clients": "clients.json",
    "stock-statement:profiles": "profiles.json",
    "stock-statement:cert-counter": "counter.json",
    "stock-statement:attachments:stock": "attachments/stock.json",
    "stock-statement:attachments:debtors": "attachments/debtors.json",
    "stock-statement:attachments:creditors": "attachments/creditors.json",
    "stock-statement:attachments:other": "attachments/other.json",
}

store_lock = threading.Lock()


def ensure_data_dirs():
    for d in (DATA_DIR, ATTACH_DIR, MISC_DIR):
        d.mkdir(parents=True, exist_ok=True)


def store_path(key):
    """Map a storage key to a file inside StockStatementData/."""
    key = str(key)
    known = KEY_FILES.get(key)
    if known:
        return DATA_DIR / known
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", key).strip("_") or "key"
    digest = base64.urlsafe_b64encode(key.encode("utf-8")).decode("ascii").rstrip("=")[:10]
    return MISC_DIR / (safe + "-" + digest + ".json")


def store_get(key):
    path = store_path(key)
    with store_lock:
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None


def store_set(key, value):
    path = store_path(key)
    with store_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(str(value), encoding="utf-8")
        tmp.replace(path)   # atomic, so a crash mid-write cannot truncate data
    return True


def store_delete(key):
    path = store_path(key)
    with store_lock:
        if path.exists():
            path.unlink()
    return True


def store_has_any():
    """True once anything has been saved - used to skip the IndexedDB import."""
    for key in KEY_FILES:
        if store_path(key).exists():
            return True
    return MISC_DIR.exists() and any(MISC_DIR.glob("*.json"))


# ==========================================================================
# SHARED STATE
# ==========================================================================

state = {
    "status": "idle",
    "udin": None,
    "message": "",
    "debug_log": [],
    "captcha_token": 0,
    "captcha_error": "",
    "needs_password": False,
    "login_username": "",
    "attempt": 0,
    "fields": {},
}

state_lock = threading.Lock()

captcha_image_bytes = None
captcha_image_type = "image/png"
captcha_submit = threading.Event()
captcha_refresh = threading.Event()
captcha_cancel = threading.Event()
captcha_input = {"text": "", "password": ""}

ACTIVE_STATUSES = ("starting", "waiting_login", "awaiting_captcha",
                   "logging_in", "filling", "awaiting_authorisation")


def set_state(**kwargs):
    with state_lock:
        state.update(kwargs)


def get_state():
    with state_lock:
        snapshot = dict(state)
        snapshot["debug_log"] = list(state["debug_log"])[-80:]
        return snapshot


def log_debug(msg):
    line = str(msg)
    with state_lock:
        state["debug_log"].append(line)
        if len(state["debug_log"]) > 400:
            del state["debug_log"][:200]
    try:
        print("[DEBUG] " + line)
    except Exception:
        print("[DEBUG] (line could not be printed)")


def set_captcha_image(data_uri):
    """Store the CAPTCHA picture and bump the token the page polls on."""
    global captcha_image_bytes, captcha_image_type
    if not data_uri:
        return False
    m = re.match(r"data:([^;,]+);base64,(.*)$", data_uri, re.S)
    if not m:
        return False
    try:
        raw = base64.b64decode(m.group(2))
    except Exception:
        return False
    with state_lock:
        captcha_image_bytes = raw
        captcha_image_type = m.group(1) or "image/png"
        state["captcha_token"] = state.get("captcha_token", 0) + 1
    return True


# ==========================================================================
# SELENIUM HELPERS
# ==========================================================================

def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def attr_text(element):
    vals = []
    for name in ("id", "name", "placeholder", "aria-label", "title",
                 "formcontrolname", "autocomplete", "data-test"):
        try:
            v = element.get_attribute(name)
            if v:
                vals.append(v)
        except Exception:
            pass
    return norm(" ".join(vals))


def element_text(driver, element):
    try:
        return norm(driver.execute_script("""
            const e = arguments[0];
            let p = e;
            for (let i = 0; i < 4 && p; i++, p = p.parentElement) {
                if ((p.innerText || '').length > 0) return p.innerText;
            }
            return '';
        """, element))
    except Exception:
        return ""


def wait_ready(driver, timeout=15):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete")
        time.sleep(1.0)
        return True
    except Exception:
        return False


def type_into(driver, element, value):
    """Type a value the way a person would, so Angular sees real key events."""
    if element is None:
        return False
    value = str(value)
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.15)
        try:
            element.click()
        except Exception:
            driver.execute_script("arguments[0].focus();", element)
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.DELETE)
        if value:
            element.send_keys(value)
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('blur',{bubbles:true}));", element)
        time.sleep(0.15)
        if str(element.get_attribute("value") or "") == value:
            return True
    except Exception as exc:
        log_debug("Typing failed, trying the JavaScript setter: " + str(exc))

    try:
        driver.execute_script("""
            const el = arguments[0], val = arguments[1];
            const proto = el.tagName === 'TEXTAREA'
                ? window.HTMLTextAreaElement.prototype
                : window.HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
            setter.call(el, val);
            ['input','change','blur'].forEach(n =>
                el.dispatchEvent(new Event(n, {bubbles:true})));
        """, element, value)
        time.sleep(0.15)
        return str(element.get_attribute("value") or "") == value
    except Exception as exc:
        log_debug("JavaScript setter also failed: " + str(exc))
        return False


# ==========================================================================
# ICAI LOGIN PAGE
# ==========================================================================

FIND_LOGIN_FIELDS_JS = """
const visible = [...document.querySelectorAll('input')].filter(e => {
    const t = (e.type || 'text').toLowerCase();
    if (['hidden','submit','button','checkbox','radio','file'].includes(t)) return false;
    return !!(e.offsetParent || e.getClientRects().length);
});
const sig = e => [e.getAttribute('formcontrolname'), e.id, e.name,
                  e.placeholder, e.getAttribute('aria-label')].join(' ').toLowerCase();

// The CAPTCHA box is whichever input sits closest to the CAPTCHA image.
let captcha = null;
const img = document.querySelector('#captcha, img.captcha-img, img[alt*="CAPTCHA" i]');
if (img) {
    let p = img;
    for (let i = 0; i < 6 && p && !captcha; i++, p = p.parentElement) {
        const found = [...p.querySelectorAll('input')].find(c => visible.includes(c));
        if (found) captcha = found;
    }
}
if (!captcha) captcha = visible.find(e => /captcha/.test(sig(e))) || null;

const password = visible.find(e => (e.type || '').toLowerCase() === 'password') || null;

let user = visible.find(e => e !== captcha && e !== password
                             && /user|email|login|member/.test(sig(e))) || null;
if (!user) {
    const cut = password ? visible.indexOf(password) : visible.length;
    user = visible.slice(0, cut).find(e => e !== captcha)
        || visible.find(e => e !== captcha && e !== password) || null;
}
return [user, password, captcha];
"""

GRAB_CAPTCHA_JS = """
const img = document.querySelector('#captcha, img.captcha-img, img[alt*="CAPTCHA" i]');
if (!img) return null;
const src = img.getAttribute('src') || '';
if (src.startsWith('data:')) return src;
try {
    const c = document.createElement('canvas');
    c.width = img.naturalWidth || img.width;
    c.height = img.naturalHeight || img.height;
    c.getContext('2d').drawImage(img, 0, 0);
    return c.toDataURL('image/png');
} catch (err) {
    return null;
}
"""

CAPTCHA_SRC_JS = """
const i = document.querySelector('#captcha, img.captcha-img, img[alt*="CAPTCHA" i]');
return i ? (i.getAttribute('src') || '').slice(0, 160) : null;
"""

CLICK_CAPTCHA_REFRESH_JS = """
const img = document.querySelector('#captcha, img.captcha-img, img[alt*="CAPTCHA" i]');
if (!img) return false;
const wanted = /refresh|reload|retry|rotate|renew/;
let p = img;
for (let i = 0; i < 5 && p; i++, p = p.parentElement) {
    for (const c of p.querySelectorAll('button, a, mat-icon, i, svg, span, img')) {
        if (c === img) continue;
        const label = [c.innerText, c.className && c.className.baseVal,
                       typeof c.className === 'string' ? c.className : '',
                       c.getAttribute('aria-label'), c.getAttribute('src'),
                       c.getAttribute('fonticon')].join(' ').toLowerCase();
        if (wanted.test(label)) { c.click(); return true; }
    }
}
const row = img.parentElement;
if (row) {
    const sibling = [...row.children].find(
        c => c !== img && /^(button|a|mat-icon|i|svg)$/i.test(c.tagName));
    if (sibling) { sibling.click(); return true; }
}
return false;
"""

FIND_LOGIN_BUTTON_JS = """
const buttons = [...document.querySelectorAll('button, input[type=submit]')]
    .filter(e => !!(e.offsetParent || e.getClientRects().length));
return buttons.find(b => /login-button/i.test(
           typeof b.className === 'string' ? b.className : ''))
    || buttons.find(b => /\\blog\\s*in\\b|\\bsign\\s*in\\b/i.test(b.innerText || b.value || ''))
    || null;
"""

PAGE_ALERTS_JS = """
const sel = 'mat-error, .mat-error, [role=alert], .alert, .toast, snack-bar-container,' +
            '.mat-snack-bar-container, .error, .text-danger, .invalid-feedback';
return [...document.querySelectorAll(sel)]
    .filter(e => !!(e.offsetParent || e.getClientRects().length))
    .map(e => e.innerText || '').join(' | ');
"""


def grab_captcha(driver, timeout=12):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            uri = driver.execute_script(GRAB_CAPTCHA_JS)
            if uri and uri.startswith("data:") and len(uri) > 200:
                return uri
        except Exception:
            pass
        time.sleep(0.4)
    return None


def page_alerts(driver):
    try:
        return norm(driver.execute_script(PAGE_ALERTS_JS))
    except Exception:
        return ""


def fill_login_credentials(driver, username, password, captcha_text):
    """Put username / password / CAPTCHA on the ICAI login page."""
    try:
        user_el, pwd_el, cap_el = driver.execute_script(FIND_LOGIN_FIELDS_JS)
    except Exception as exc:
        log_debug("Could not read the login form: " + str(exc))
        return False

    ok = True

    if username:
        if user_el is None:
            log_debug("Username field not found on the page.")
            ok = False
        elif type_into(driver, user_el, username):
            log_debug("Username filled: " + str(username))
        else:
            log_debug("Username field found but would not accept the value.")
            ok = False

    if password:
        if pwd_el is None:
            log_debug("Password field not found on the page.")
            ok = False
        elif type_into(driver, pwd_el, password):
            log_debug("Password filled.")
        else:
            log_debug("Password field found but would not accept the value.")
            ok = False

    if captcha_text is not None:
        if cap_el is None:
            log_debug("CAPTCHA field not found on the page.")
            ok = False
        elif type_into(driver, cap_el, captcha_text):
            log_debug("CAPTCHA filled.")
        else:
            log_debug("CAPTCHA field found but would not accept the value.")
            ok = False

    return ok


def click_login_button(driver, timeout=10):
    """
    The LOGIN button starts out disabled - Angular only enables it once it
    considers the form valid. Wait for that, then force it through if the
    framework has not caught up.
    """
    try:
        btn = driver.execute_script(FIND_LOGIN_BUTTON_JS)
    except Exception as exc:
        log_debug("Could not locate the LOGIN button: " + str(exc))
        return False
    if btn is None:
        log_debug("LOGIN button not found on the page.")
        return False

    enabled = False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            disabled = driver.execute_script(
                "const b = arguments[0];"
                "return b.disabled || b.classList.contains('mat-button-disabled');", btn)
            if not disabled:
                enabled = True
                break
        except Exception:
            break
        time.sleep(0.3)

    if not enabled:
        log_debug("LOGIN button stayed disabled - clicking it anyway.")

    try:
        driver.execute_script("""
            const b = arguments[0];
            b.disabled = false;
            b.removeAttribute('disabled');
            b.classList.remove('mat-button-disabled');
            b.scrollIntoView({block:'center'});
            b.click();
        """, btn)
        log_debug("LOGIN clicked.")
        return True
    except Exception as exc:
        log_debug("Clicking LOGIN failed: " + str(exc))
        return False


FAILURE_WORDS = ("invalid", "incorrect", "wrong", "does not match",
                 "not registered", "failed", "expired", "try again")
FAILURE_SUBJECTS = ("captcha", "password", "username", "user name",
                    "credential", "user id", "login")


def login_outcome(driver, timeout=25):
    """Returns ('ok', '') or ('failed', reason) or ('pending', '')."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            # Only the path decides - a query string can carry "login" too.
            path = urlparse(driver.current_url or "").path.lower()
            if "login" not in path:
                return "ok", ""
            alerts = page_alerts(driver)
            body = norm(driver.find_element(By.TAG_NAME, "body").text)
            haystack = alerts + " " + body
            if any(w in haystack for w in FAILURE_WORDS) and \
               any(s in haystack for s in FAILURE_SUBJECTS):
                return "failed", (alerts or body)[:160]
        except Exception:
            pass
        time.sleep(0.5)
    return "pending", ""


def refresh_captcha(driver, username, password):
    """Ask ICAI for a fresh CAPTCHA, reloading the page if there is no button."""
    before = None
    try:
        before = driver.execute_script(CAPTCHA_SRC_JS)
    except Exception:
        pass

    try:
        clicked = bool(driver.execute_script(CLICK_CAPTCHA_REFRESH_JS))
    except Exception:
        clicked = False

    if clicked:
        deadline = time.time() + 3
        while time.time() < deadline:
            try:
                now = driver.execute_script(CAPTCHA_SRC_JS)
                if now and now != before:
                    log_debug("New CAPTCHA loaded.")
                    return True
            except Exception:
                pass
            time.sleep(0.3)

    log_debug("Reloading the login page for a new CAPTCHA.")
    driver.get(ICAI_LOGIN_URL)
    wait_ready(driver, 20)
    fill_login_credentials(driver, username, password, None)
    return True


def wait_for_captcha_reply(timeout):
    """
    Block until the application posts a CAPTCHA, asks for a new picture, or
    the run is cancelled. Returns submit / refresh / cancel / timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        if captcha_cancel.is_set():
            return "cancel"
        if captcha_refresh.is_set():
            captcha_refresh.clear()
            return "refresh"
        if captcha_submit.wait(0.2):
            captcha_submit.clear()
            return "submit"
    return "timeout"


def run_icai_login(driver, username, password, has_saved_password):
    """
    Drive the ICAI login. The CAPTCHA picture goes to the application and the
    typed answer comes back, so the browser window never needs attention.
    """
    driver.get(ICAI_LOGIN_URL)
    wait_ready(driver, 25)
    fill_login_credentials(driver, username, password, None)

    for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
        image = grab_captcha(driver)
        if not image:
            log_debug("CAPTCHA image not found - the login page may have changed.")
            set_state(status="error",
                      message="Could not read the CAPTCHA picture from the ICAI page. "
                              "Please finish the login in the Edge window.")
            return False

        set_captcha_image(image)
        set_state(status="awaiting_captcha",
                  attempt=attempt,
                  login_username=username or "",
                  needs_password=not has_saved_password,
                  message="Type the CAPTCHA shown here to sign in to ICAI.")

        action = wait_for_captcha_reply(CAPTCHA_WAIT_SECONDS)

        if action == "cancel":
            log_debug("Run cancelled from the application.")
            set_state(status="idle", message="UDIN run cancelled.")
            return False
        if action == "timeout":
            set_state(status="error",
                      message="Timed out waiting for the CAPTCHA. Please start again.")
            return False
        if action == "refresh":
            set_state(status="awaiting_captcha", captcha_error="",
                      message="Loading a new CAPTCHA...")
            refresh_captcha(driver, username, password)
            continue

        with state_lock:
            typed = captcha_input.get("text", "")
            typed_password = captcha_input.get("password", "")

        if typed_password:
            password = typed_password
            has_saved_password = True

        set_state(status="logging_in", captcha_error="",
                  message="Signing in to ICAI...")

        fill_login_credentials(driver, username, password, typed)
        click_login_button(driver)

        outcome, reason = login_outcome(driver)
        if outcome == "ok":
            log_debug("ICAI login succeeded.")
            set_state(captcha_error="")
            return True

        if outcome == "failed":
            log_debug("Login rejected: " + str(reason))
            set_state(captcha_error=reason or "ICAI rejected the login. Please try again.")
        else:
            set_state(captcha_error="ICAI did not accept the login. "
                                    "Please try the CAPTCHA again.")

        refresh_captcha(driver, username, password)

    set_state(status="error",
              message="Login failed after several attempts. Please check the "
                      "username and password saved on the CA profile.")
    return False


# ==========================================================================
# UDIN FORM
#
# Selectors below were read off a saved copy of the real
# https://udin.icai.org/ICAI/generateUDIN page, so they are exact rather
# than guessed:
#
#   FRN                  ng-select[formcontrolname=FRN] -> the profile's FRN,
#                        matched against entries like "999999W - FIRM NAME"
#   Document Type        mat-radio-group[docType]      -> "Certificates and Other Reports"
#   Type of Certificate  ng-select#certficateType      -> "Others"   (ICAI's own spelling)
#   Others box           input[othersCertificate]      -> "Stock statement"
#   Date of Signing      input[signingDate]            -> DD-MM-YYYY
#   Figures entered in   mat-radio-group[fieldType]    -> "Numeric"
#                        (matched exactly: "Numeric" must not win
#                         against "Numeric and Alphanumeric")
#   Three rows           input[udinPrtclName] + input[figureValue]
#                        + ng-select[denominationValue] -> "Actual"
#   Document Description textarea[desc]                 (5-250 characters)
#   Remarks              input[remarks]                 (max 250)
#   Buttons              Add More / Save Draft / Send OTP
#
# The order follows suggessions.docx, and Document Type has to be set before
# Type of Certificate because choosing Tax Audit swaps out the fields below.
# ==========================================================================

# ng-select carries no id of its own - only labelForId, which it copies onto
# its inner <input>. So "#FRN" is the search box, never the control, and
# formcontrolname is the only stable handle on the host.
SEL_FRN = "ng-select[formcontrolname='FRN']"
SEL_CERT_TYPE = "ng-select[formcontrolname='certficateType']"
SEL_OTHERS_BOX = "input[formcontrolname='othersCertificate']"
SEL_SIGNING_DATE = "input[formcontrolname='signingDate']"
SEL_DESCRIPTION = "[formcontrolname='desc']"
SEL_REMARKS = "[formcontrolname='remarks']"
SEL_PARTICULAR = "input[formcontrolname='udinPrtclName']"
SEL_FIGURE_VALUE = "input[formcontrolname='figureValue']"
SEL_DENOMINATION = "ng-select[formcontrolname='denominationValue']"

PLACEHOLDER_OPTIONS = ("select", "no items found", "none", "--", "choose")


def to_icai_date(value):
    """The certificate holds 26/08/2026; ICAI's box wants 26-08-2026."""
    digits = re.findall(r"\d+", str(value or ""))
    if len(digits) == 3:
        day, month, year = digits
        if len(year) == 2:
            year = "20" + year
        return day.zfill(2) + "-" + month.zfill(2) + "-" + year
    return str(value or "").replace("/", "-")


def format_amount(value):
    """Figures in INR - the box only accepts 14 characters, so keep it plain."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value or "")
    if number == int(number):
        return str(int(number))
    return ("%.2f" % number).rstrip("0").rstrip(".")


# -- Angular Material radio groups -----------------------------------------

FIND_RADIO_JS = r"""
const fc = arguments[0], wanted = arguments[1].toLowerCase().trim();
const group = document.querySelector('mat-radio-group[formcontrolname="' + fc + '"]');
if (!group) return null;
for (const btn of group.querySelectorAll('mat-radio-button')) {
    const content = btn.querySelector('.mat-radio-label-content');
    let text = (content ? content.innerText : btn.innerText) || '';
    // Each label carries a mat-icon whose ligature name renders as the word
    // "information"; strip it or the comparison never matches.
    for (const icon of btn.querySelectorAll('mat-icon')) {
        if (icon.innerText) text = text.split(icon.innerText).join(' ');
    }
    text = text.replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
    // Exact match only: "Numeric" must not win over "Numeric and Alphanumeric".
    if (text === wanted) return content || btn.querySelector('.mat-radio-label') || btn;
}
return null;
"""

RADIO_IS_CHECKED_JS = r"""
const group = document.querySelector('mat-radio-group[formcontrolname="' + arguments[0] + '"]');
if (!group) return '';
const on = group.querySelector('mat-radio-button.mat-radio-checked');
if (!on) return '';
const content = on.querySelector('.mat-radio-label-content');
let text = (content ? content.innerText : on.innerText) || '';
for (const icon of on.querySelectorAll('mat-icon')) {
    if (icon.innerText) text = text.split(icon.innerText).join(' ');
}
return text.replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
"""

LIST_RADIO_LABELS_JS = """
const group = document.querySelector('mat-radio-group[formcontrolname="' + arguments[0] + '"]');
if (!group) return [];
return [...group.querySelectorAll('mat-radio-button')].map(btn => {
    const content = btn.querySelector('.mat-radio-label-content');
    let text = (content ? content.innerText : btn.innerText) || '';
    for (const icon of btn.querySelectorAll('mat-icon')) {
        if (icon.innerText) text = text.split(icon.innerText).join(' ');
    }
    return text.replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
});
"""


def select_radio(driver, form_control, label_text):
    """Pick a Material radio by its visible label, with a real mouse click."""
    close_overlays(driver)      # a stray calendar backdrop would eat the click

    try:
        already = norm(driver.execute_script(RADIO_IS_CHECKED_JS, form_control))
    except Exception:
        already = ""
    if already and already == norm(label_text):
        log_debug(form_control + " already set to " + label_text)
        return True

    try:
        target = driver.execute_script(FIND_RADIO_JS, form_control, label_text)
    except Exception as exc:
        log_debug("Radio '" + form_control + "' failed: " + first_line(exc))
        return False

    if target is None:
        try:
            offered = driver.execute_script(LIST_RADIO_LABELS_JS, form_control)
        except Exception:
            offered = []
        log_debug("Radio '" + form_control + "' has no option '" + label_text +
                  "'. Offered: " + str(offered))
        return False

    if not real_click(driver, target, "radio " + form_control):
        return False
    time.sleep(0.5)

    try:
        now = norm(driver.execute_script(RADIO_IS_CHECKED_JS, form_control))
    except Exception:
        now = ""
    if now == norm(label_text):
        log_debug("Radio " + form_control + " = " + label_text)
        return True
    log_debug("Radio " + form_control + " did not take; it now reads " + repr(now))
    return False


# -- ng-select dropdowns ----------------------------------------------------

# ng-select links a control to its own panel by id: the .ng-input div carries
# aria-owns="<panelId>" and its input carries aria-controls="<panelId>", while
# each option is "<panelId>-<index>". With appendTo="body" every panel lands in
# the same place, so this id is the only dependable way to tell one row's
# Denomination list from the next row's.

NG_PANEL_ID_JS = """
const host = arguments[0];
const combo = host.querySelector('.ng-input');
let id = combo ? combo.getAttribute('aria-owns') : null;
if (!id) {
    const box = host.querySelector('.ng-input input');
    id = box ? box.getAttribute('aria-controls') : null;
}
if (id) return id;
const inline = host.querySelector('.ng-dropdown-panel');
return inline && inline.id ? inline.id : null;
"""

# Only ever the id, never the element. ng-select builds the panel, throws it
# away in the same tick and builds it again in the measured position - a
# recording of a manual run shows "panel-opened, panel-closed, panel-opened"
# every single time, 0ms apart. An element grabbed on the first open is
# detached by the time anything is clicked on it, which looks exactly like a
# click that does nothing.
NG_PANEL_OPTIONS_JS = """
const panel = document.getElementById(arguments[0]);
if (!panel) return null;
return [...panel.querySelectorAll('.ng-option')]
    .filter(e => !!(e.offsetParent || e.getClientRects().length))
    .map(e => {
        const label = e.querySelector('.ng-option-label');
        return ((label ? label.textContent : e.textContent) || '')
            .replace(/\\s+/g, ' ').trim();
    });
"""

NG_IS_OPEN_JS = """
const combo = arguments[0].querySelector('.ng-input');
return !!(combo && combo.getAttribute('aria-expanded') === 'true');
"""

NG_OPEN_JS = """
// Only click when it is actually shut - ng-select toggles, so clicking an
// already-open control closes it again.
const host = arguments[0];
const combo = host.querySelector('.ng-input');
if (combo && combo.getAttribute('aria-expanded') === 'true') return 'already-open';
(host.querySelector('.ng-select-container') || host).click();
return 'clicked';
"""

NG_OPTION_ELEMENTS_JS = """
const panel = document.getElementById(arguments[0]);
if (!panel) return null;
return [...panel.querySelectorAll('.ng-option')]
    .filter(e => !!(e.offsetParent || e.getClientRects().length));
"""

# Last resort only. A recorded manual run shows a real mouse emitting
# pointerdown before click, and ng-select commits an option on mousedown so
# the search box does not blur first. execute_script("el.click()") sends the
# click alone, which the component simply ignores.
NG_FORCE_CLICK_JS = """
const el = arguments[0];
for (const type of ['pointerover','pointerenter','pointerdown','mousedown',
                    'pointerup','mouseup','click']) {
    el.dispatchEvent(new MouseEvent(type, {bubbles:true, cancelable:true, view:window, button:0}));
}
return true;
"""

NG_CONTAINER_JS = """
const host = arguments[0];
return host.querySelector('.ng-select-container') || host;
"""

NG_CURRENT_VALUE_JS = """
const label = arguments[0].querySelector('.ng-value-label');
return label ? label.innerText.replace(/\\s+/g,' ').trim() : '';
"""

NG_SEARCH_INPUT_JS = """
return arguments[0].querySelector('.ng-input input, input');
"""

CLOSE_OVERLAYS_JS = """
let closed = 0;
for (const b of document.querySelectorAll('.cdk-overlay-backdrop')) { b.click(); closed++; }
// Blur an open ng-select and let the component close itself. Never strip
// .ng-select-opened by hand - the class is ng-select's own bookkeeping, and
// removing it leaves the component believing it is still open, so the next
// click toggles it shut instead of opening it.
for (const s of document.querySelectorAll('.ng-select.ng-select-opened')) {
    const box = s.querySelector('.ng-input input');
    if (box) box.blur();
    closed++;
}
return closed;
"""


def close_overlays(driver):
    """
    Material's date picker and every ng-select panel sit in an overlay. Left
    open, the calendar's backdrop swallows later clicks and a stray ng-select
    panel confuses the next row, so each step clears them before starting.
    """
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    except Exception:
        pass
    try:
        driver.execute_script(CLOSE_OVERLAYS_JS)
    except Exception:
        pass
    time.sleep(0.3)


def first_line(exc):
    """Selenium errors are pages long; only the first line is useful in a log."""
    return str(exc).splitlines()[0] if str(exc).splitlines() else str(exc)


def real_click(driver, element, what=""):
    """
    Click the way a mouse does. Selenium's own click drives the browser's
    input pipeline, so pointerdown/mousedown/mouseup/click all fire; a
    JavaScript .click() sends only the last of those, and ng-select commits an
    option on mousedown, so a scripted click on an option does nothing at all.
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        time.sleep(0.15)
        element.click()
        return True
    except Exception as exc:
        log_debug(what + ": direct click failed (" + first_line(exc) + "), moving the mouse")
    try:
        ActionChains(driver).move_to_element(element).pause(0.1).click().perform()
        return True
    except Exception as exc:
        log_debug(what + ": mouse move failed (" + first_line(exc) + "), dispatching events")
    try:
        return bool(driver.execute_script(NG_FORCE_CLICK_JS, element))
    except Exception as exc:
        log_debug(what + ": could not click at all: " + str(exc))
        return False


def ng_panel_id(driver, host):
    try:
        return driver.execute_script(NG_PANEL_ID_JS, host)
    except Exception:
        return None


def wait_for_ng_options(driver, host, timeout=8):
    """
    Poll this control's own panel until it settles.

    ng-select builds the panel, discards it in the same tick and builds it
    again in the measured position. A recording of a manual run shows
    "panel-opened, panel-closed, panel-opened" 0ms apart for every dropdown on
    this form. So the same option list has to come back twice in a row before
    it can be trusted, and only the panel id is carried forward - an element
    captured from the first build is detached by the time it would be clicked.
    """
    deadline = time.time() + timeout
    previous = None
    while time.time() < deadline:
        panel_id = ng_panel_id(driver, host)
        if panel_id:
            try:
                texts = driver.execute_script(NG_PANEL_OPTIONS_JS, panel_id)
            except Exception:
                texts = None
            if texts and any(t and norm(t) != "no items found" for t in texts):
                if texts == previous:
                    return panel_id, texts
                previous = texts
        time.sleep(0.25)
    return ng_panel_id(driver, host), (previous or [])


def select_ng(driver, host, wanted_texts, fallback_first=False, what="", search_hint=None):
    """
    Pick an option from an ng-select. host may be a CSS selector or an element.

    fallback_first covers the note in suggessions.docx - take the firm's own
    entry, "OR FIRST OPTION FROM THERE" - so a renamed firm still proceeds.
    """
    if isinstance(host, str):
        try:
            host = driver.find_element(By.CSS_SELECTOR, host)
        except Exception:
            log_debug("Dropdown not found: " + (what or str(host)))
            return False
    if host is None:
        log_debug("Dropdown not found: " + what)
        return False

    wanted = [norm(w) for w in wanted_texts if w]

    def pick(texts):
        normed = [norm(t) for t in texts]
        index = next((i for i, t in enumerate(normed) if any(w == t for w in wanted)), -1)
        if index < 0:
            index = next((i for i, t in enumerate(normed)
                          if any(w and w in t for w in wanted)), -1)
        return index

    def search_box():
        try:
            box = driver.execute_script(NG_SEARCH_INPUT_JS, host)
        except Exception:
            return None
        if box is not None and box.get_attribute("readonly"):
            return None         # Denomination's box cannot be typed into
        return box

    try:
        current = norm(driver.execute_script(NG_CURRENT_VALUE_JS, host))
        if current and any(w == current or w in current for w in wanted):
            log_debug(what + " already set to: " + current)
            return True

        close_overlays(driver)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", host)
        time.sleep(0.2)
        if driver.execute_script(NG_IS_OPEN_JS, host):
            log_debug(what + ": already open")
        else:
            container = driver.execute_script(NG_CONTAINER_JS, host)
            real_click(driver, container, what)

        panel_id, texts = wait_for_ng_options(driver, host, 8)
        index = pick(texts) if texts else -1

        # Narrow a long list through the search box, the way a person would -
        # this is what makes "Others" reachable in the certificate list.
        if index < 0:
            hint = search_hint or (wanted_texts[0] if wanted_texts else "")
            box = search_box()
            if box is not None and hint:
                log_debug(what + ": filtering the list with '" + str(hint) + "'")
                try:
                    box.send_keys(Keys.CONTROL, "a")
                    box.send_keys(Keys.DELETE)
                except Exception:
                    pass
                box.send_keys(str(hint))
                panel_id, texts = wait_for_ng_options(driver, host, 6)
                index = pick(texts) if texts else -1

        if index < 0 and fallback_first:
            box = search_box()
            if box is not None:
                try:
                    box.send_keys(Keys.CONTROL, "a")
                    box.send_keys(Keys.DELETE)
                    panel_id, texts = wait_for_ng_options(driver, host, 5)
                except Exception:
                    pass
            index = next((i for i, t in enumerate(texts)
                          if t and not any(p in norm(t) for p in PLACEHOLDER_OPTIONS)), -1)
            if index >= 0:
                log_debug(what + ": no exact match, taking the first option - " + texts[index])

        if not texts:
            log_debug(what + ": the control opened but its panel listed nothing.")
            close_overlays(driver)
            return False

        log_debug(what + " offers: " + str(texts[:8]))

        if index < 0:
            log_debug(what + ": none of " + str(wanted) + " is in the list.")
            close_overlays(driver)
            return False

        # Re-read the options immediately before clicking: ng-select rebuilds
        # the panel, so anything fetched earlier is already detached.
        options = driver.execute_script(NG_OPTION_ELEMENTS_JS, panel_id)
        if not options or index >= len(options):
            log_debug(what + ": option " + str(index) + " vanished before it could be clicked.")
            close_overlays(driver)
            return False
        if not real_click(driver, options[index], what + " option"):
            close_overlays(driver)
            return False

        time.sleep(0.6)
        chosen = norm(driver.execute_script(NG_CURRENT_VALUE_JS, host))
        if not chosen:
            log_debug(what + ": the click did not stick.")
            return False
        log_debug(what + " = " + chosen)
        return True

    except Exception as exc:
        log_debug(what + " selection failed: " + str(exc))
        close_overlays(driver)
        return False


def wait_for_element(driver, selector, timeout=6):
    """Wait for a control that only appears once an earlier choice is made."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            found = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in found:
                if el.is_displayed():
                    return el
        except Exception:
            pass
        time.sleep(0.25)
    return None


# -- plain boxes ------------------------------------------------------------

def fill_box(driver, selector, value, what="", required=True):
    if value in (None, ""):
        return not required
    close_overlays(driver)      # nothing can be typed under an open backdrop
    try:
        field = driver.find_element(By.CSS_SELECTOR, selector)
    except Exception:
        log_debug(what + ": box not found (" + selector + ")")
        return False
    ok = type_into(driver, field, value)
    log_debug((what + " = " + str(value)) if ok else (what + ": would not accept the value"))
    return ok


def click_button_fuzzy(driver, button_texts, timeout=8):
    deadline = time.time() + timeout
    wanted = [norm(x) for x in button_texts]
    while time.time() < deadline:
        for el in driver.find_elements(
                By.XPATH, "//button | //a | //input[@type='button'] | //input[@type='submit']"):
            try:
                if not el.is_displayed() or not el.is_enabled():
                    continue
                txt = norm(el.text or el.get_attribute("value")
                           or el.get_attribute("aria-label") or "")
                if txt and any(c == txt for c in wanted):
                    if real_click(driver, el, str(button_texts)):
                        log_debug("Clicked: " + str(button_texts))
                        return True
            except Exception:
                pass
        time.sleep(0.3)
    log_debug("Could not click: " + str(button_texts))
    return False


# -- the Figures/Values rows ------------------------------------------------

FIND_FIGURE_ROWS_JS = """
// One entry per row: [particulars box, figures box, denomination ng-select].
// The row is the nearest ancestor of a Particulars box that also holds a
// Figures box, which keeps the three controls of a row together.
const rows = [];
for (const p of document.querySelectorAll("input[formcontrolname='udinPrtclName']")) {
    let holder = p.parentElement, figure = null;
    for (let i = 0; i < 8 && holder; i++, holder = holder.parentElement) {
        figure = holder.querySelector("input[formcontrolname='figureValue']");
        if (figure) break;
    }
    if (!figure) continue;
    rows.push([p, figure,
               holder.querySelector("ng-select[formcontrolname='denominationValue']")]);
}
return rows;
"""


def read_figure_rows(driver):
    try:
        return driver.execute_script(FIND_FIGURE_ROWS_JS) or []
    except Exception as exc:
        log_debug("Could not read the figures table: " + str(exc))
        return []


def fill_financial_figures(driver, figures):
    """
    Stock (Schedule A), Sundry Debtors (Schedule B) and Sundry Creditors
    (Schedule C). ICAI starts with three rows, so Add More is only needed if
    that ever changes. No client name goes in here - suggessions.docx is
    explicit that client details must not be disclosed on this table.
    """
    if not figures:
        return True

    close_overlays(driver)      # the date picker's backdrop blocks this whole table
    filled = 0
    for index, item in enumerate(figures):
        particular = str(item.get("particular", "")).strip()
        if not particular:
            continue
        amount = format_amount(item.get("value", ""))
        denomination = item.get("denomination", "Actual")

        rows = read_figure_rows(driver)
        if index >= len(rows):
            if click_button_fuzzy(driver, ["Add More"], timeout=3):
                time.sleep(1.0)
                rows = read_figure_rows(driver)
        if index >= len(rows):
            log_debug("No row " + str(index + 1) + " for: " + particular)
            continue

        particular_box, figure_box, denomination_select = rows[index]

        ok_name = type_into(driver, particular_box, particular)
        ok_value = type_into(driver, figure_box, amount)
        if denomination_select is not None:
            select_ng(driver, denomination_select, [denomination, "Actual"],
                      what="Row " + str(index + 1) + " denomination")

        if ok_name and ok_value:
            filled += 1
            log_debug("Row " + str(index + 1) + ": " + particular + " = " + amount)
        else:
            log_debug("Row " + str(index + 1) + " incomplete: " + particular)
        time.sleep(0.4)

    log_debug("Figure rows filled: " + str(filled) + "/" + str(len(figures)))
    return filled == len(figures)


# -- the form, step by step -------------------------------------------------

def fill_udin_form(driver, payload, only_missing=None):
    """
    Fill the Generate UDIN form. only_missing limits a retry to the steps that
    failed, so nothing already correct gets clicked a second time.
    """
    u = payload.get("udin", {})
    results = {}

    def step(name):
        return only_missing is None or name in only_missing

    log_debug("=== Filling the UDIN form ===")
    wait_ready(driver, 15)

    # 1. FRN - the firm, or the first entry offered.
    if step("FRN"):
        frn = str(u.get("frn", "")).strip()
        results["FRN"] = select_ng(
            driver, SEL_FRN, [frn], fallback_first=True, what="FRN")

    # 2. Document Type - radio buttons.
    if step("Document Type"):
        results["Document Type"] = select_radio(
            driver, "docType", u.get("documentType", "Certificates and Other Reports"))

    # 3. Type of Certificate - Others.
    if step("Type of Certificate"):
        results["Type of Certificate"] = select_ng(
            driver, SEL_CERT_TYPE, [u.get("certificateType", "Others")],
            what="Type of Certificate")

    # 4. The box that "Others" reveals - it is added to the form only after
    #    that choice lands, so wait for it rather than assuming a delay.
    if step("Certificate Name"):
        box = wait_for_element(driver, SEL_OTHERS_BOX, timeout=6)
        if box is None:
            log_debug("Certificate name box never appeared - is 'Others' selected?")
            results["Certificate Name"] = False
        else:
            results["Certificate Name"] = fill_box(
                driver, SEL_OTHERS_BOX,
                u.get("otherCertificateRemark", "Stock statement"), "Certificate name")

    # 5. Date of signing, in ICAI's DD-MM-YYYY. Clicking the box pops the
    #    Material calendar, whose backdrop would then eat every later click,
    #    so it gets closed before moving on.
    if step("Date of Signing"):
        results["Date of Signing"] = fill_box(
            driver, SEL_SIGNING_DATE, to_icai_date(u.get("dateOfSigning", "")),
            "Date of signing")
        close_overlays(driver)

    # 6. How the figures are expressed.
    if step("Figures Format"):
        results["Figures Format"] = select_radio(
            driver, "fieldType", u.get("figureFormat", "Numeric"))

    # 7. Stock / Sundry Debtors / Sundry Creditors.
    if step("Financial Figures"):
        results["Financial Figures"] = fill_financial_figures(
            driver, u.get("financialFigures", []))

    # 8. Document Description - ICAI wants at least 5 characters.
    if step("Document Description"):
        results["Document Description"] = fill_box(
            driver, SEL_DESCRIPTION, u.get("documentDescription", ""), "Document description")

    # 9. Remarks.
    if step("Remarks"):
        results["Remarks"] = fill_box(
            driver, SEL_REMARKS, u.get("remarks", ""), "Remarks")

    done = [k for k, v in results.items() if v]
    log_debug("Filled " + str(len(done)) + "/" + str(len(results)) + ": " + ", ".join(done))
    return results


def save_draft(driver):
    """
    Save the draft and stop there. Send OTP, the OTP itself and Generate UDIN
    stay manual, so nothing is submitted before it has been checked.
    """
    if click_button_fuzzy(driver, ["Save Draft"], timeout=5):
        time.sleep(1.5)
        return True
    log_debug("Save Draft button not found - please save it on the ICAI page.")
    return False


def find_generated_udin(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return None
    for pattern in (r"UDIN\s*(?:is|:|-)?\s*([0-9]{8}[A-Z0-9]{10})\b",
                    r"\b([0-9]{8}[A-Z0-9]{10})\b"):
        m = re.search(pattern, body, re.I)
        if m:
            candidate = m.group(1).upper()
            if len(candidate) == 18:
                return candidate
    return None


def is_udin_form_ready(driver):
    """The form is up once its own controls exist - far tighter than text matching."""
    try:
        return bool(driver.execute_script(
            "return !!(document.querySelector(\"ng-select#FRN, "
            "ng-select[formcontrolname='FRN']\") && "
            "document.querySelector(\"mat-radio-group[formcontrolname='docType']\"));"))
    except Exception:
        return False


def open_generate_udin(driver):
    try:
        if is_udin_form_ready(driver):
            return True
        driver.get("https://udin.icai.org/ICAI/generateUDIN")
        wait_ready(driver, 20)
        for _ in range(10):
            if is_udin_form_ready(driver):
                return True
            time.sleep(1)
        if click_button_fuzzy(driver, ["Generate UDIN"], timeout=6):
            time.sleep(2)
        return is_udin_form_ready(driver)
    except Exception as exc:
        log_debug("Could not open the Generate UDIN form: " + str(exc))
        return False

# ==========================================================================
# BROWSER WORKER
# ==========================================================================

def browser_worker(payload):
    driver = None
    try:
        login = payload.get("login", {}) or {}
        username = str(login.get("username", "")).strip()
        password = str(login.get("password", ""))

        captcha_submit.clear()
        captcha_refresh.clear()
        captcha_cancel.clear()

        set_state(status="starting", udin=None, captcha_error="", debug_log=[],
                  message="Opening Microsoft Edge...")

        options = webdriver.EdgeOptions()
        options.add_argument("--start-maximized")
        driver = webdriver.Edge(options=options)

        if not run_icai_login(driver, username, password, bool(password)):
            return

        set_state(status="filling", captcha_error="",
                  message="Signed in. Opening the Generate UDIN form...")
        time.sleep(1.5)
        open_generate_udin(driver)

        try:
            WebDriverWait(driver, 60).until(lambda d: is_udin_form_ready(d))
        except Exception:
            log_debug("The UDIN form did not appear within 60 seconds.")

        set_state(status="filling", message="Filling the UDIN form...")

        results = fill_udin_form(driver, payload)
        missing = [k for k, v in results.items() if not v]
        if missing:
            log_debug("Retrying: " + ", ".join(missing))
            time.sleep(1.0)
            retry = fill_udin_form(driver, payload, only_missing=set(missing))
            results.update({k: v for k, v in retry.items() if v})

        try:
            driver.save_screenshot(str(APP_DIR / "udin_autofill_debug.png"))
        except Exception:
            pass

        drafted = save_draft(driver)

        ok_count = sum(1 for v in results.values() if v)
        not_filled = [k for k, v in results.items() if not v]
        note = ("All fields filled." if not not_filled
                else "Please fill these by hand: " + ", ".join(not_filled) + ".")

        set_state(status="awaiting_authorisation",
                  fields=results,
                  message=("Filled " + str(ok_count) + "/" + str(len(results)) +
                           " fields. " + note +
                           (" Draft saved." if drafted else " Please click Save Draft yourself.") +
                           " Now check the form in the Edge window, click Send OTP, "
                           "type the OTP there and generate the UDIN - it will be "
                           "copied back into this certificate automatically."))

        WebDriverWait(driver, 1800).until(lambda d: find_generated_udin(d) is not None)
        udin = find_generated_udin(driver)

        set_state(status="generated", udin=udin,
                  message="UDIN " + str(udin) + " generated and copied into the certificate.")
        time.sleep(5)

    except Exception as exc:
        message = str(exc)
        lowered = message.lower()
        if "no such window" in lowered or "target window already closed" in lowered:
            set_state(status="idle", message="The Edge window was closed.")
        else:
            set_state(status="error", message="UDIN error: " + message)
        log_debug("Exception: " + traceback.format_exc())

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# ==========================================================================
# STEP RECORDER
#
# Opens the ICAI site and watches what you do. Every click, every value you
# type and every dropdown that opens or closes is captured with the exact
# element behind it - formControlName, aria-owns, which figures row, which
# option index - and written to StockStatementData/recordings/.
#
# The point is to stop guessing: whatever the automation cannot do, you do it
# by hand once, and the recording says precisely which element answered.
#
# Passwords, CAPTCHA and OTP values are never written down.
# ==========================================================================

RECORDINGS_DIR = DATA_DIR / "recordings"

RECORDER_JS = r"""
if (window.__udinRec) return 'already-installed';

const buffer = [];
const LIMIT = 8000;
const short = s => String(s || '').replace(/\s+/g, ' ').trim().slice(0, 140);

// Angular repaints these constantly; they say nothing about which element it is.
const NOISE = /^(ng-(star|tns|untouched|touched|pristine|dirty|valid|invalid|reflect)|cdk-|mat-focus|mat-ripple)/;

function cssPath(el) {
    const parts = [];
    for (let e = el; e && e.nodeType === 1 && parts.length < 8; e = e.parentElement) {
        let piece = e.tagName.toLowerCase();
        const fc = e.getAttribute && e.getAttribute('formcontrolname');
        if (fc) piece += '[formcontrolname="' + fc + '"]';
        else if (e.id) { parts.unshift(piece + '#' + e.id); break; }
        else {
            const cls = String(e.className && e.className.baseVal !== undefined
                ? e.className.baseVal : e.className || '')
                .split(/\s+/).filter(c => c && !NOISE.test(c)).slice(0, 2);
            if (cls.length) piece += '.' + cls.join('.');
        }
        const parent = e.parentElement;
        if (parent) {
            const same = [...parent.children].filter(x => x.tagName === e.tagName);
            if (same.length > 1) piece += ':nth-of-type(' + (same.indexOf(e) + 1) + ')';
        }
        parts.unshift(piece);
    }
    return parts.join(' > ');
}

function labelFor(el) {
    if (el.id) {
        try {
            const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
            if (l && l.innerText) return short(l.innerText);
        } catch (err) { }
    }
    // A dropdown panel is appended to <body> and has no caption of its own,
    // so walking outwards from one just borrows the first caption on the page.
    if (el.closest && el.closest('.ng-dropdown-panel')) return '';
    // ICAI puts the caption in a sibling column, so walk outwards - but stop
    // as soon as the ancestor holds more than one control, otherwise every
    // field ends up borrowing the caption of whichever one comes first.
    for (let p = el.parentElement, i = 0; p && i < 6; p = p.parentElement, i++) {
        if (p.tagName === 'BODY' || p.tagName === 'FORM') break;
        const controls = p.querySelectorAll
            ? p.querySelectorAll('input, textarea, select, ng-select, mat-radio-group')
            : [];
        if (controls.length > 1) break;
        const lab = p.querySelector && p.querySelector('mat-label, label');
        if (lab && lab.innerText) return short(lab.innerText);
    }
    return '';
}

const SECRET = /password|captcha|otp/i;
function valueOf(el) {
    if (!el || !('value' in el)) return undefined;
    const signature = [el.getAttribute('formcontrolname'), el.id, el.name, el.type].join(' ');
    if (el.type === 'password' || SECRET.test(signature)) return el.value ? '***' : '';
    return short(el.value);
}

function describe(el) {
    if (!el || el.nodeType !== 1) return null;
    const out = {
        tag: el.tagName.toLowerCase(),
        fc: el.getAttribute('formcontrolname') || undefined,
        id: el.id || undefined,
        name: el.getAttribute('name') || undefined,
        type: el.getAttribute('type') || undefined,
        role: el.getAttribute('role') || undefined,
        placeholder: el.getAttribute('placeholder') || undefined,
        readonly: el.hasAttribute('readonly') || undefined,
        ariaOwns: el.getAttribute('aria-owns') || undefined,
        ariaControls: el.getAttribute('aria-controls') || undefined,
        ariaExpanded: el.getAttribute('aria-expanded') || undefined,
        text: short(el.innerText),
        label: labelFor(el),
        value: valueOf(el),
        path: cssPath(el)
    };

    const host = el.closest && el.closest('ng-select');
    if (host) {
        out.ngSelect = host.getAttribute('formcontrolname') || short(host.className);
        const chosen = host.querySelector('.ng-value-label');
        if (chosen) out.ngSelectValue = short(chosen.innerText);
    }

    const panel = el.closest && el.closest('.ng-dropdown-panel');
    if (panel) {
        out.panelId = panel.id || undefined;
        const options = [...panel.querySelectorAll('.ng-option')];
        const option = el.closest('.ng-option');
        if (option) out.optionIndex = options.indexOf(option);
        out.panelOptions = options.slice(0, 12).map(o => short(o.innerText));
    }

    const radio = el.closest && el.closest('mat-radio-button');
    if (radio) {
        const group = radio.closest('mat-radio-group');
        out.radioGroup = group ? (group.getAttribute('formcontrolname') || '') : '';
        out.radioValue = radio.getAttribute('value') || undefined;
    }

    const row = el.closest && el.closest('.particularsForm');
    if (row) {
        // Count only rows that hold a Particulars box - the column header
        // carries .particularsForm too and would shift every number by one.
        const rows = [...document.querySelectorAll('.particularsForm')]
            .filter(r => r.querySelector("input[formcontrolname='udinPrtclName']"));
        const at = rows.indexOf(row);
        if (at >= 0) out.figureRow = at + 1;
    }

    for (const k of Object.keys(out)) if (out[k] === undefined || out[k] === '') delete out[k];
    return out;
}

function push(type, extra) {
    if (buffer.length >= LIMIT) buffer.shift();
    buffer.push(Object.assign({ at: Date.now(), type: type, url: location.pathname }, extra));
}

for (const type of ['pointerdown', 'click', 'change', 'focusin']) {
    // Capture phase, so a handler that stops propagation cannot hide the step.
    document.addEventListener(type, e => push(type, { el: describe(e.target) }), true);
}

let typingTimer = null, typingTarget = null;
document.addEventListener('input', e => {
    typingTarget = e.target;
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => push('typed', { el: describe(typingTarget) }), 600);
}, true);

new MutationObserver(records => {
    for (const rec of records) {
        if (rec.type === 'attributes' && rec.attributeName === 'aria-expanded') {
            push('expanded', { el: describe(rec.target),
                               to: rec.target.getAttribute('aria-expanded') });
        }
        for (const n of rec.addedNodes || []) {
            if (n.nodeType === 1 && n.classList && n.classList.contains('ng-dropdown-panel')) {
                push('panel-opened', { el: describe(n) });
            }
        }
        for (const n of rec.removedNodes || []) {
            if (n.nodeType === 1 && n.classList && n.classList.contains('ng-dropdown-panel')) {
                push('panel-closed', { el: { tag: 'ng-dropdown-panel', panelId: n.id || undefined } });
            }
        }
    }
}).observe(document.documentElement, {
    subtree: true, childList: true, attributes: true, attributeFilter: ['aria-expanded']
});

window.__udinRec = {
    drain: () => buffer.splice(0, buffer.length),
    pending: () => buffer.length,
    snapshot: () => {
        const state = {};
        for (const el of document.querySelectorAll('[formcontrolname]')) {
            const fc = el.getAttribute('formcontrolname');
            let v;
            if (el.tagName.toLowerCase() === 'ng-select') {
                const label = el.querySelector('.ng-value-label');
                v = label ? short(label.innerText) : '';
            } else if (el.tagName.toLowerCase() === 'mat-radio-group') {
                const on = el.querySelector('mat-radio-button.mat-radio-checked');
                if (on) {
                    const content = on.querySelector('.mat-radio-label-content');
                    let t = content ? content.innerText : on.innerText;
                    for (const ic of on.querySelectorAll('mat-icon'))
                        if (ic.innerText) t = t.split(ic.innerText).join(' ');
                    v = short(t);
                } else v = '';
            } else v = valueOf(el);
            if (v !== undefined) (state[fc] = state[fc] || []).push(v);
        }
        return state;
    }
};
return 'installed';
"""


def summarise_step(event):
    """One readable line per captured step."""
    el = event.get("el") or {}
    bits = []
    what = el.get("fc") or el.get("id") or el.get("tag", "?")
    if el.get("ngSelect"):
        what = "ng-select[" + el["ngSelect"] + "]"
    if el.get("radioGroup"):
        what = "radio[" + el["radioGroup"] + "]"
    if el.get("figureRow"):
        what += " row" + str(el["figureRow"])
    bits.append(what)
    if el.get("label"):
        bits.append("label=" + repr(el["label"]))
    if el.get("text") and el.get("optionIndex") is not None:
        bits.append("option#" + str(el["optionIndex"]) + "=" + repr(el["text"]))
    elif el.get("text") and el.get("tag") == "button":
        bits.append("button=" + repr(el["text"]))
    if el.get("value") is not None:
        bits.append("value=" + repr(el["value"]))
    if el.get("ngSelectValue"):
        bits.append("selected=" + repr(el["ngSelectValue"]))
    if event.get("to"):
        bits.append("aria-expanded=" + event["to"])
    if el.get("panelId"):
        bits.append("panel=" + el["panelId"])
    return event["type"].ljust(13) + " " + "  ".join(bits)


def record_worker(stop_event, start_url):
    """Drive Edge and write down every step the user takes."""
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = RECORDINGS_DIR / ("steps-" + stamp + ".jsonl")
    text_path = RECORDINGS_DIR / ("steps-" + stamp + ".txt")

    driver = None
    total = 0
    try:
        options = webdriver.EdgeOptions()
        options.add_argument("--start-maximized")
        driver = webdriver.Edge(options=options)
        driver.get(start_url)

        print("=" * 72)
        print(" RECORDING - do the UDIN steps by hand in the Edge window.")
        print(" Every click and value is written to:")
        print("   " + str(text_path))
        print(" Close the Edge window (or press Ctrl+C here) when you are done.")
        print(" Passwords, CAPTCHA and OTP are not recorded.")
        print("=" * 72)

        with raw_path.open("w", encoding="utf-8") as raw, \
             text_path.open("w", encoding="utf-8") as text:

            text.write("ICAI UDIN - recorded steps\n")
            text.write("started " + stamp + "\n\n")
            text.flush()

            last_snapshot = None
            while not stop_event.is_set():
                try:
                    installed = driver.execute_script(RECORDER_JS)
                    if installed == "installed":
                        log_debug("Recorder attached to " + driver.current_url)
                    events = driver.execute_script(
                        "return (window.__udinRec && window.__udinRec.drain()) || [];") or []
                except Exception as exc:
                    message = str(exc).lower()
                    if "no such window" in message or "target window already closed" in message \
                            or "invalid session id" in message:
                        break
                    events = []

                for event in events:
                    total += 1
                    raw.write(json.dumps(event, ensure_ascii=False) + "\n")
                    line = str(total).rjust(4) + ". " + summarise_step(event)
                    text.write(line + "\n")
                    print("  " + line)
                if events:
                    raw.flush()
                    text.flush()

                # A snapshot of every form value, whenever one changes.
                try:
                    snapshot = driver.execute_script(
                        "return (window.__udinRec && window.__udinRec.snapshot()) || null;")
                except Exception:
                    snapshot = None
                if snapshot and snapshot != last_snapshot:
                    last_snapshot = snapshot
                    raw.write(json.dumps({"type": "snapshot", "state": snapshot},
                                         ensure_ascii=False) + "\n")
                    raw.flush()

                time.sleep(0.5)

            if last_snapshot:
                text.write("\nForm values at the end:\n")
                for key, values in sorted(last_snapshot.items()):
                    text.write("   " + key + " = " + repr(values) + "\n")
            text.write("\n" + str(total) + " steps recorded.\n")

    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        print("\n" + "=" * 72)
        print(" Recording finished - " + str(total) + " steps.")
        print("   readable : " + str(text_path))
        print("   full data: " + str(raw_path))
        print("=" * 72)


def run_recorder():
    ensure_data_dirs()
    stop_event = threading.Event()
    try:
        record_worker(stop_event, ICAI_LOGIN_URL)
    except KeyboardInterrupt:
        stop_event.set()


# ==========================================================================
# HTTP SERVER
# ==========================================================================

class Handler(BaseHTTPRequestHandler):

    server_version = "StockStatementUDIN/22"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")

    def send_json(self, obj, code=200):
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(raw)

    def read_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return ""
        return self.rfile.read(length).decode("utf-8")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    # -- GET ---------------------------------------------------------------

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self.send_json({"ok": True, "engine": ENGINE_SIGNATURE,
                            "dataDir": str(DATA_DIR)})
            return

        if path == "/udin/status":
            self.send_json(get_state())
            return

        if path == "/udin/captcha.img":
            with state_lock:
                raw = captcha_image_bytes
                kind = captcha_image_type
            if not raw:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/store/keys":
            self.send_json({"ok": True, "hasData": store_has_any()})
            return

        if path.startswith("/store/"):
            key = unquote(path[len("/store/"):])
            value = store_get(key)
            if value is None:
                self.send_json({"ok": False, "found": False}, 404)
            else:
                self.send_json({"ok": True, "found": True, "key": key, "value": value})
            return

        if path == "/":
            if not APP.exists():
                self.send_error(500, "Stock Statement HTML file is missing")
                return
            raw = APP.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
            return

        self.send_error(404)

    # -- PUT / DELETE (storage) -------------------------------------------

    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/store/"):
            self.send_error(404)
            return
        key = unquote(path[len("/store/"):])
        try:
            store_set(key, self.read_body())
            self.send_json({"ok": True, "key": key})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/store/"):
            self.send_error(404)
            return
        key = unquote(path[len("/store/"):])
        try:
            store_delete(key)
            self.send_json({"ok": True, "key": key})
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)

    # -- POST --------------------------------------------------------------

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/udin/start":
            try:
                payload = json.loads(self.read_body() or "{}")
            except Exception as exc:
                self.send_json({"ok": False, "error": "Bad payload: " + str(exc)}, 400)
                return
            if get_state()["status"] in ACTIVE_STATUSES:
                self.send_json({"ok": False,
                                "error": "A UDIN run is already in progress."}, 409)
                return
            threading.Thread(target=browser_worker, args=(payload,), daemon=True).start()
            self.send_json({"ok": True})
            return

        if path == "/udin/captcha":
            try:
                body = json.loads(self.read_body() or "{}")
            except Exception:
                body = {}
            with state_lock:
                captcha_input["text"] = str(body.get("text", "")).strip()
                captcha_input["password"] = str(body.get("password", ""))
            captcha_submit.set()
            self.send_json({"ok": True})
            return

        if path == "/udin/captcha/refresh":
            captcha_refresh.set()
            self.send_json({"ok": True})
            return

        if path == "/udin/cancel":
            captcha_cancel.set()
            captcha_submit.set()
            self.send_json({"ok": True})
            return

        self.send_error(404)

    def log_message(self, fmt, *args):
        pass    # the debug log is the useful one; keep the console readable


def existing_engine(port):
    """True when our own engine is already answering on this port."""
    try:
        with urllib.request.urlopen(
                "http://" + HOST + ":" + str(port) + "/health", timeout=2) as r:
            return json.loads(r.read().decode("utf-8")).get("engine") == ENGINE_SIGNATURE
    except Exception:
        return False


class AppServer(ThreadingHTTPServer):
    # Windows lets a second process bind a port that is already listening
    # when SO_REUSEADDR is on, which would silently split requests between
    # two engines writing to the same data folder. Refuse instead.
    allow_reuse_address = False
    daemon_threads = True


def port_is_free(port):
    """Plain bind test - deliberately without SO_REUSEADDR (see AppServer)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, port))
            return True
        except OSError:
            return False


def create_server():
    """
    Always prefer port 25765. The saved data used to live in browser storage
    keyed by origin, so a shifting port meant a fresh empty app every time.
    Data now lives in files, but keeping the address stable also means
    bookmarks and open tabs keep working.

    Returns (None, port) when our own engine already holds the port, so the
    caller just opens that one instead of starting a second copy.
    """
    for port in range(PREFERRED_PORT, PREFERRED_PORT + PORT_SPAN):
        if port_is_free(port):
            try:
                return AppServer((HOST, port), Handler), port
            except OSError:
                continue
        elif existing_engine(port):
            return None, port
    raise RuntimeError("Ports " + str(PREFERRED_PORT) + "-" +
                       str(PREFERRED_PORT + PORT_SPAN - 1) + " are all busy.")


def main():
    if "--record" in sys.argv:
        run_recorder()
        return

    if not APP.exists():
        raise FileNotFoundError("Missing application file:\n" + str(APP))

    ensure_data_dirs()
    server, port = create_server()
    url = "http://" + HOST + ":" + str(port) + "/"

    print("=" * 72)
    print(" STOCK STATEMENT + ICAI UDIN ASSISTANT")
    print("=" * 72)
    print(" Application : " + url)
    print(" Data folder : " + str(DATA_DIR))
    print(" Browser     : Microsoft Edge (Selenium)")
    if server is None:
        print(" An assistant is already running on this port - opening it.")
    else:
        print(" Keep this window open while you work.")
    print("=" * 72)

    if server is None:
        webbrowser.open(url)
        return

    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.5)
    webbrowser.open(url)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        input("\nPress ENTER to close...")
