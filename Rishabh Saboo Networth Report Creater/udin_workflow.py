"""Drive the official ICAI portal in a dedicated, visible browser window."""
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

PORTAL = "https://udin.icai.org"


def run_udin(data, password, update):
    from playwright.sync_api import sync_playwright, Error

    with sync_playwright() as playwright:
        for channel in ("msedge", "chrome"):
            try:
                browser = playwright.chromium.launch(channel=channel, headless=False)
                break
            except Error:
                continue
        else:
            raise RuntimeError("Install Microsoft Edge or Google Chrome on the app computer.")
        try:
            page = browser.new_page()
            page.set_default_timeout(5000)
            return portal_workflow(page, data, password, update)
        finally:
            browser.close()


def portal_workflow(page, data, password, update):
    def official():
        url = urlsplit(page.url)
        return url.scheme == "https" and url.netloc == "udin.icai.org"

    def control(selector):
        return page.locator(selector).first

    def wait_for(check, seconds, error):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if page.is_closed():
                raise RuntimeError("The ICAI window was closed. Check the portal before starting another request.")
            if official():
                value = check()
                if value:
                    return value
            page.wait_for_timeout(500)
        raise RuntimeError(error)

    def button(label):
        return control(f'button:visible:text-is("{label}"),input[type=submit][value="{label}"]:visible')

    def click_available(label):
        target = button(label)
        if target.is_visible() and target.is_enabled():
            target.click()
            return True
        return False

    login_network = {}

    def observe_response(response):
        parsed = urlsplit(response.url)
        if (parsed.scheme == "https" and parsed.hostname and
                (parsed.hostname == "icai.org" or parsed.hostname.endswith(".icai.org")) and
                response.request.method == "POST" and response.request.resource_type in ("xhr", "fetch")):
            login_network["status"] = response.status

    page.on("response", observe_response)
    update("Opening the official ICAI portal.")
    response = page.goto(PORTAL + "/ICAI/login", wait_until="domcontentloaded", timeout=45000)
    if response and response.status >= 400:
        raise RuntimeError(f"ICAI returned HTTP {response.status} when opening its login page.")
    if not official():
        raise RuntimeError("ICAI redirected to a different site. Credentials were withheld.")
    username = control('#username:visible,input[formcontrolname=username]:visible,'
                       'input[autocomplete=username]:visible,input[name*=user i]:visible')
    password_field = control("#password:visible,input[type=password]:visible")
    captcha = control("input#captcha:visible,input[formcontrolname=captcha]:visible")
    if "/login" in page.url.lower():
        update("Waiting for ICAI to render the SSP login form.")
        wait_for(lambda: username.is_visible() and password_field.is_visible(), 35,
                 "The ICAI URL opened, but its SSP login fields did not load. Check the ICAI window and try again.")
        username.fill(data["username"] or data["membership"] + "@icai.org")
        if password:
            password_field.fill(password)
        if captcha.is_visible():
            captcha.focus()
            captcha.scroll_into_view_if_needed()
        update("Enter CAPTCHA in Edge. Net Worth Office will click the LOGIN button below it." if password else
               "Enter your SSP password and CAPTCHA in Edge. Net Worth Office will click the LOGIN button below it.")
        login_submit = control("button.login-button:visible")
        last_notice = None
        attempted_captcha = ""

        def login_finished():
            nonlocal last_notice, attempted_captcha
            route = urlsplit(page.url).path.rstrip("/").lower()
            generate = page.get_by_text("Generate UDIN", exact=True).first
            if route.endswith("/generateudin") or (
                not route.endswith("/login") and not password_field.is_visible() and generate.is_visible()
            ):
                return True
            visible_error = page.get_by_text(re.compile(
                r"(?:invalid|incorrect|expired|failed|mismatch|required).{0,45}"
                r"(?:captcha|credentials|password|username|login)|"
                r"(?:captcha|credentials|password|username|login).{0,45}"
                r"(?:invalid|incorrect|expired|failed|mismatch|required)|"
                r"unable to (?:log in|login)|something went wrong",
                re.I,
            )).first
            status = login_network.get("status")
            if captcha.is_visible():
                entered = captcha.input_value().strip()
                maxlength = captcha.get_attribute("maxlength")
                captcha_length = int(maxlength) if maxlength and maxlength.isdigit() else 6
                if not entered:
                    attempted_captcha = ""
                if (len(entered) == captcha_length and entered != attempted_captcha
                        and status is None and not visible_error.is_visible()
                        and login_submit.is_visible() and login_submit.is_enabled()):
                    attempted_captcha = entered
                    update("Submitting the ICAI login. Waiting for the portal to respond.")
                    login_submit.click(timeout=2500)
                    return False
                if (len(entered) == captcha_length and attempted_captcha != entered
                        and status is None and not login_submit.is_enabled()):
                    notice = "ICAI has disabled the LOGIN button below CAPTCHA. Check the username, password, and CAPTCHA fields in Edge."
                    if notice != last_notice:
                        update(notice)
                        last_notice = notice
            if visible_error.is_visible():
                notice = "ICAI rejected the login or highlighted a field. Read the error in Edge, correct it, and try again there."
            elif status and status >= 400:
                notice = f"ICAI returned HTTP {status} after login. Check the message in Edge and retry there."
            elif status:
                notice = "ICAI responded to Login. Waiting for the signed-in page. If Edge shows an error, correct it and retry there."
            else:
                return False
            if notice != last_notice:
                update(notice)
                last_notice = notice
            return False

        wait_for(login_finished, 300,
                 "ICAI never reached its signed-in page. Check the login message in Edge before retrying.")
    page.remove_listener("response", observe_response)

    update("ICAI sign-in completed. Opening the Generate UDIN form.")
    if "/generateudin" not in page.url.lower():
        page.goto(data["portal"], wait_until="domcontentloaded", timeout=45000)
    dismiss = button("Dismiss")
    for _ in range(2):
        page.keyboard.press("Escape")

    def form_ready():
        if dismiss.is_visible():
            update("Dismissing the ICAI notice.")
            dismiss.click(timeout=2000)
            return False
        return ("/generateudin" in page.url.lower() and
                (page.locator('input[formcontrolname="signingDate"]').first.is_visible() or
                 page.get_by_text(re.compile("Type of Certificate", re.I)).first.is_visible()))

    wait_for(form_ready, 45, "ICAI signed in, but the Generate UDIN form did not become available.")
    update("Filling the ICAI certificate and net worth figures.")
    source = Path(__file__).with_name("udin-autofill.js").read_text(encoding="utf-8")
    outcome = page.evaluate(source, data)
    for _ in range(3):
        if outcome.get("needsDate"):
            expected = "-".join(reversed(data["signed_iso"].split("-")))
            update(f"Select signing date {expected} in ICAI's calendar. Autofill will continue when that date is selected.")
            signing_date = page.locator('input[formcontrolname="signingDate"]').first
            wait_for(lambda: signing_date.is_visible() and signing_date.input_value() == expected,
                     180, "The report's signing date was not selected in ICAI.")
        elif outcome.get("needsCertificate"):
            update("Choose the correct Type of Certificate from ICAI's dropdown in Edge. "
                   "Autofill will continue after you select it.")
            certificate = page.locator('ng-select[formcontrolname="certficateType"]').first
            selected = certificate.locator(".ng-value-label").first
            wait_for(lambda: not certificate.evaluate("(el) => el.classList.contains('ng-select-opened')")
                     and selected.is_visible() and selected.inner_text().strip(),
                     180, "No certificate type was selected in ICAI.")
            data = {**data, "accept_portal_certificate": True}
        else:
            break
        outcome = page.evaluate(source, data)
    if outcome["pending"]:
        completed = ", ".join(outcome["done"])
        update((f"Filled: {completed}. " if completed else "") +
               f"Autofill stopped at {outcome['pending'][0]}. Complete it and the remaining fields "
               "in the ICAI window, verify the figures, then click Send OTP.")
    elif not click_available("Send OTP"):
        update("Review the filled fields and click Send OTP in the ICAI window.")
    else:
        update("OTP requested. Enter it in the ICAI window, then verify and submit the certificate.")

    otp = control('input[autocomplete=one-time-code]:visible,input[placeholder*=otp i]:visible,'
                  'input[id*=otp i]:visible,input[name*=otp i]:visible')
    verify_clicked = False
    preview_clicked = False
    submitted = False
    code_pattern = re.compile(r"\b\d{2}" + re.escape(data["membership"]) + r"[A-Z0-9]{10}\b")

    def check():
        nonlocal verify_clicked, preview_clicked, submitted
        result = page.evaluate(r"""() => [...document.querySelectorAll(
          '[role=dialog],.modal.show,.swal2-popup,mat-dialog-container,[role=alert],h1,h2,h3,h4,p,label,td'
        )].filter(e => e.getClientRects().length).map(e => e.innerText)
          .filter(t => t && t.length < 1800 &&
            /UDIN\s*(?:number|no\.?|generated|:)|generated\s+successfully/i.test(t))""")
        confirmed = {code for line in result for code in code_pattern.findall(line)}
        if submitted and not confirmed:
            # Some confirmation pages render the label and identifier in separate cells.
            body = page.locator("body").inner_text()
            if re.search(r"UDIN\s*(?:has been )?generated|successfully generated|generated successfully", body, re.I):
                confirmed = set(code_pattern.findall(body))
        if len(confirmed) == 1:
            return confirmed.pop()
        if not verify_clicked and otp.is_visible() and otp.input_value().strip().isdigit():
            length = otp.get_attribute("maxlength")
            digits = int(length) if length and length.isdigit() and 4 <= int(length) <= 8 else 6
            if len(otp.input_value().strip()) == digits:
                verify_clicked = click_available("Verify OTP")
        if verify_clicked and not submitted:
            if not preview_clicked:
                preview_clicked = click_available("Preview")
            # Submit only after verification exposes a preview. A failed OTP
            # remains on ICAI where the user can retry it.
            if not otp.is_visible() and (preview_clicked or
                    page.get_by_text(re.compile(r"OTP (?:has been )?verified", re.I)).first.is_visible()):
                submitted = click_available("Submit")
        return None

    return wait_for(check, 420, "No issued UDIN was detected. Check ICAI's result before retrying.")
