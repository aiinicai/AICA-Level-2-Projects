"""App paths and settings (config.json next to the app / .exe)."""
import copy
import json
import os
import sys


def app_dir() -> str:
    """Folder where config.json, clients.xlsx etc. live (writable)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_dir() -> str:
    """Folder with bundled read-only files (ui/)."""
    return getattr(sys, "_MEIPASS", app_dir())


CONFIG_PATH = os.path.join(app_dir(), "config.json")


RETURNS_BODY = """Dear {name},

Greetings from {firm_name}.

Please find attached the filed copy of your {forms} for {period} (GSTIN: {gstin}).

Attached files:
{file_list}

Kindly review it and keep it for your records. If you notice any difference from your books, please let us know at the earliest.

Regards,
{firm_name}
{firm_phone}"""

GSTR2B_BODY = """Dear {name},

Your GSTR-2B for {period} (GSTIN: {gstin}) has been generated and is attached.

Attached files:
{file_list}

Please reconcile it with your purchase register and send us your GSTR-3B data along with the reconciliation sheet on or before {send_by_date}, so that we can file your return on time.

While reconciling, please keep these points in mind:

1. Business use only - ITC can be claimed only on purchases and expenses used for your business. Personal expenses are not eligible.

2. Blocked credits - Do not claim ITC on:
   - Motor cars / passenger vehicles (except where used for specified business purposes like resale, transport of passengers, training)
   - Food & beverages, outdoor catering
   - Beauty treatment, health services, cosmetic surgery
   - Club, gym or fitness memberships
   - Life / health insurance
   - Employee holiday / leave travel
   - Gifts, free samples and personal consumption
   - Goods lost, stolen, destroyed or written off
   - Construction of building / civil work (other than plant & machinery)

3. Invoice must be in GSTR-2B - ITC can be taken only for invoices reflected in your GSTR-2B. If an invoice is missing, please ask the supplier to file it in their GSTR-1. It can be claimed once it reflects.

4. Invoice & receipt - You must have the tax invoice and must have actually received the goods / services.

5. Payment within 180 days - If a supplier is not paid within 180 days of the invoice date, the ITC has to be reversed with interest.

6. Reverse charge (RCM) - Please share details of RCM expenses (e.g. GTA freight, advocate fees) separately.

7. Wrong invoices in IMS - If any invoice in GSTR-2B / IMS is not yours or is incorrect, please inform us so we can reject it or keep it pending before filing.

Please note that delay beyond {send_by_date} may result in late fee and interest.

Regards,
{firm_name}
{firm_phone}"""


DEFAULTS = {
    "clients_excel": "clients.xlsx",
    "download_folder": "GST_Downloads",
    "firm_name": "ABC & Associates",
    "firm_phone": "",
    "send_by_day": 18,
    "password_age_warn_days": 60,
    "browser": {
        "page_timeout": 30,
        "download_timeout": 180,
        "max_captcha_tries": 3,
        "delay_between_clients": 3,
    },
    "email": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "",
        "app_password": "",
        "sender_name": "ABC & Associates",
        "cc": "",
    },
    "templates": {
        "returns": {
            "subject": "Filed GST Return - {forms} - {period} | {name}",
            "body": RETURNS_BODY,
        },
        "gstr2b": {
            "subject": "Action Required: GSTR-2B for {period} - Send data by {send_by_date} | {name}",
            "body": GSTR2B_BODY,
        },
    },
    # Everything the app looks for on the GST portal. If the portal changes,
    # these can be edited here without touching the code.
    "portal": {
        "login_url": "https://services.gst.gov.in/services/login",
        "dashboard_url": "https://return.gst.gov.in/returns/auth/dashboard",
        "welcome_url": "https://services.gst.gov.in/services/auth/fowelcome",
        "dashboard_button_texts": ["RETURN DASHBOARD", "RETURNS DASHBOARD"],
        "dashboard_menu_texts": ["RETURNS DASHBOARD", "RETURN DASHBOARD"],
        "logout_url": "https://services.gst.gov.in/services/logout",
        "username_id": "username",
        "password_id": "user_pass",
        "captcha_input_id": "captcha",
        "captcha_image_id": "imgCaptcha",
        "login_success_url_parts": ["/services/auth/", "fowelcome", "/returns/auth/"],
        "captcha_error_texts": [
            "enter valid letters shown",
            "invalid captcha",
            "captcha is invalid",
        ],
        "bad_credential_texts": [
            "invalid username or password",
            "invalid user id or password",
            "username or password is invalid",
            "incorrect username or password",
            "invalid username/password",
        ],
        "locked_texts": ["has been locked", "is locked", "account locked", "temporarily blocked"],
        "password_expired_texts": ["password has expired", "your password is expired"],
        "popup_dismiss_texts": ["REMIND ME LATER", "SKIP", "CLOSE", "CONTINUE TO DASHBOARD", "NO, THANKS"],
        "fy_select_css": "select[name='fin']",
        "quarter_select_css": "select[name='quarter']",
        "month_select_css": "select[name='mon']",
        "search_button_texts": ["SEARCH"],
        "gstr2b_excel_button_texts": ["GENERATE EXCEL FILE TO DOWNLOAD", "DOWNLOAD EXCEL"],
        "gstr2b_json_button_texts": ["GENERATE JSON FILE TO DOWNLOAD", "DOWNLOAD JSON"],
        "gstr1_pdf_button_texts": ["DOWNLOAD (PDF)", "DOWNLOAD PDF"],
        "gstr1_summary_button_texts": ["VIEW SUMMARY"],
        "gstr3b_pdf_button_texts": ["DOWNLOAD FILED GSTR-3B", "DOWNLOAD FILED", "DOWNLOAD (PDF)", "DOWNLOAD PDF"],
        "not_filed_regex": "not\\s*filed|to\\s*be\\s*filed",
    },
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load() -> dict:
    if not os.path.exists(CONFIG_PATH):
        save(DEFAULTS)
        return copy.deepcopy(DEFAULTS)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        user = json.load(f)
    return _merge(DEFAULTS, user)


def save(cfg: dict) -> None:
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)


def resolve(path: str) -> str:
    """Relative paths in config are relative to the app folder."""
    if not path:
        return app_dir()
    path = os.path.expandvars(os.path.expanduser(path))
    return path if os.path.isabs(path) else os.path.join(app_dir(), path)
