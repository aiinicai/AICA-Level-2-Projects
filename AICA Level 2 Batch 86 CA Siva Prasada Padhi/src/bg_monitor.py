#!/usr/bin/env python3
"""
BANK GUARANTEE MONITORING & EMAIL ALERT SYSTEM  (Python edition)

Progressive escalation: 30 days (polite), 20 days (firm), 10 days (assertive
invocation notice).  Reads the same Google Sheet, writes the same BG_Email_Log.

Usage:
    python bg_monitor.py --preview     # show what is due, send nothing
    python bg_monitor.py               # normal run (mode taken from Config sheet)
    python bg_monitor.py --test        # force TEST mode (all mail to DEFAULT_TO_EMAIL)
"""

import argparse
import os
import re
import smtplib
import sys
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

# ──────────────────────────────────────────────────────────────────────────
# SETTINGS  — edit these three lines only
# ──────────────────────────────────────────────────────────────────────────

SPREADSHEET_ID = "PASTE_YOUR_SHEET_ID_HERE"
SENDER_EMAIL = "bg-monitor@yourcompany.example"
APP_PASSWORD_ENV = "BG_GMAIL_APP_PASSWORD"   # env variable holding the 16-char app password

# ──────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(SCRIPT_DIR, "key.json")

CONFIG_SHEET_NAME = "Config"
BG_SHEET_NAME = "BG"
LOG_SHEET_NAME = "BG_Email_Log"
HOLIDAY_SHEET_NAME = "Holidays"

IST = ZoneInfo("Asia/Kolkata")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Most urgent first — order matters for escalation
ESCALATION_TIERS = [
    {"days": 10, "key": "10D", "name": "10-Day Final Notice (Assertive Invocation)"},
    {"days": 20, "key": "20D", "name": "20-Day Follow-Up (Firm)"},
    {"days": 30, "key": "30D", "name": "30-Day Reminder (Polite)"},
]

INACTIVE_STATUSES = {"cancelled", "released", "invoked", "discharged", "closed", "returned"}

LOG_HEADERS = [
    "Log ID", "Unique Record ID", "BG Number", "Expiry Date",
    "Processed Timestamp", "Mode", "Status", "Message/Error",
]

DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y",
    "%d/%m/%y", "%d-%m-%y",
]


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def parse_date(val):
    """Parse Indian-style date text (or an Excel serial number) into a date."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    text = str(val).strip()
    if text == "":
        return None

    # Excel / Sheets serial number
    if re.fullmatch(r"\d{5}(\.\d+)?", text):
        try:
            serial = float(text)
            return (datetime(1899, 12, 30) + timedelta(days=serial)).date()
        except ValueError:
            pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def fmt(d, pattern="%d-%m-%Y"):
    return d.strftime(pattern) if d else ""


def adjust_for_holidays_and_weekends(target, holidays):
    """Move the reminder date backwards past Saturdays, Sundays and holidays."""
    adjusted = target
    guard = 0
    while guard < 60:
        if adjusted.weekday() >= 5 or adjusted.strftime("%Y-%m-%d") in holidays:
            adjusted -= timedelta(days=1)
            guard += 1
        else:
            break
    return adjusted


def generate_unique_id(bg_number, expiry, tier_key):
    stamp = expiry.strftime("%Y%m%d") if expiry else "NA"
    clean = re.sub(r"\s+", "", str(bg_number))
    return f"BG-{clean}-{stamp}-{tier_key}"


def clean_email_list(raw):
    if not raw:
        return ""
    text = str(raw).replace(";", ",").replace(":", ",")
    text = re.sub(r"\s+com\b", ".com", text, flags=re.I).rstrip(".")
    seen, out = set(), []
    for part in text.split(","):
        addr = part.strip()
        if "@" in addr and addr not in seen:
            seen.add(addr)
            out.append(addr)
    return ", ".join(out)


def find_col(headers, pattern):
    for i, h in enumerate(headers):
        if re.search(pattern, h, re.I):
            return i
    return -1


def get_header_indexes(headers):
    return {
        "bgNumber": find_col(headers, r"BG\s*Number|Guarantee\s*Number|Ref\s*No|Sl\s*No"),
        "contractDate": find_col(headers, r"Contract\s*Date"),
        "bgDate": find_col(headers, r"BG\s*Date|Issue\s*Date"),
        "expiryDate": find_col(headers, r"Date\s*of\s*Expiry|Expiry\s*Date|Valid\s*Upto"),
        "status": find_col(headers, r"Status|BG\s*Status"),
        "email": find_col(headers, r"Recipient\s*Email|Vendor\s*Email|E-?mail"),
    }


# ──────────────────────────────────────────────────────────────────────────
# Sheet access
# ──────────────────────────────────────────────────────────────────────────

def open_spreadsheet():
    if not os.path.exists(KEY_FILE):
        sys.exit(f"Robot key file not found: {KEY_FILE}")
    if SPREADSHEET_ID.startswith("PASTE"):
        sys.exit("Please put your Sheet ID into SPREADSHEET_ID at the top of this file.")
    creds = Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(SPREADSHEET_ID)


def get_config(ss):
    config = {"SYSTEM_MODE": "TEST", "DEFAULT_TO_EMAIL": SENDER_EMAIL}
    try:
        rows = ss.worksheet(CONFIG_SHEET_NAME).get_all_values()
    except gspread.WorksheetNotFound:
        return config
    for row in rows:
        if row and str(row[0]).strip():
            key = str(row[0]).strip()
            value = str(row[1]).strip() if len(row) > 1 else ""
            config[key] = value
    return config


def get_holidays(ss):
    try:
        rows = ss.worksheet(HOLIDAY_SHEET_NAME).get_all_values()
    except gspread.WorksheetNotFound:
        return set()
    out = set()
    for row in rows[1:]:
        d = parse_date(row[0]) if row else None
        if d:
            out.add(d.strftime("%Y-%m-%d"))
    return out


def get_or_create_log(ss):
    try:
        return ss.worksheet(LOG_SHEET_NAME)
    except gspread.WorksheetNotFound:
        sheet = ss.add_worksheet(title=LOG_SHEET_NAME, rows=2000, cols=len(LOG_HEADERS))
        sheet.append_row(LOG_HEADERS, value_input_option="RAW")
        sheet.format("1:1", {"textFormat": {"bold": True}})
        return sheet


def read_log_state(log_sheet):
    """Return (ids already emailed successfully, every id ever logged)."""
    sent, everything = set(), set()
    rows = log_sheet.get_all_values()
    for row in rows[1:]:
        if len(row) < 7:
            continue
        uid, status = str(row[1]), str(row[6])
        everything.add(uid)
        if status == "Sent":
            sent.add(uid)
    return sent, everything


def make_log_row(uid, bg_number, expiry, status, message, mode):
    return [
        "LOG-" + uuid.uuid4().hex[:8],
        uid,
        str(bg_number),
        expiry.strftime("%Y-%m-%d") if hasattr(expiry, "strftime") else str(expiry),
        datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
        mode,
        status,
        message,
    ]


# ──────────────────────────────────────────────────────────────────────────
# Escalation logic
# ──────────────────────────────────────────────────────────────────────────

def evaluate_due_tier(expiry, today, holidays, sent_ids, bg_number):
    """
    Return the single reminder that is due now, or None.

    Checked most-urgent-first.  If the most urgent tier that has fallen due was
    already emailed, nothing further is sent — this stops a polite 30-day letter
    from going out AFTER a final notice (a flaw in the original Apps Script,
    which happened whenever a BG was entered late into the register).
    """
    for tier in ESCALATION_TIERS:
        target = adjust_for_holidays_and_weekends(expiry - timedelta(days=tier["days"]), holidays)
        if today >= target:
            uid = generate_unique_id(bg_number, expiry, tier["key"])
            if uid in sent_ids:
                return None
            return {"tier": tier, "target": target, "uid": uid}
    return None


# ──────────────────────────────────────────────────────────────────────────
# Email construction
# ──────────────────────────────────────────────────────────────────────────

def build_email(tier_key, count, recipient, is_test, display_keys, rows):
    prefix = "[TEST MODE] " if is_test else ""

    if tier_key == "30D":
        subject = (f"{prefix}Bank Guarantee Expiry Advisory (30-Day Notice) – "
                   f"{count} Item(s) Expiring Shortly")
        intro = """<p>Dear Sir/Madam,</p>
      <p>This is a polite reminder that the following Bank Guarantee(s) submitted towards your contract are scheduled to expire in approximately <strong>30 calendar days</strong>.</p>
      <p>You are kindly requested to review the contract validity and take necessary advance steps for extension or renewal through your issuing bank well before the expiry date to avoid any operational or contractual interruption.</p>"""
        notice = """<blockquote style="background-color: #f0f7ff; border-left: 4px solid #1a73e8; padding: 10px; margin: 10px 0; font-size: 12px; color: #333;">
        <strong>Notice:</strong> Please verify the details with your bank and arrange submission of the renewed Bank Guarantee in a timely manner.
      </blockquote>"""

    elif tier_key == "20D":
        subject = (f"{prefix}URGENT: Bank Guarantee Expiry Follow-Up (20-Day Notice) – "
                   f"{count} Item(s)")
        intro = """<p>Dear Sir/Madam,</p>
      <p>This is an <strong>urgent follow-up reminder</strong> that the following Bank Guarantee(s) are scheduled to expire in approximately <strong>20 calendar days</strong>.</p>
      <p>As the expiry date is fast approaching, you are requested to immediately expedite the extension/renewal process and submit the extended instrument / bank confirmation to our office without further delay.</p>"""
        notice = """<blockquote style="background-color: #fff3e0; border-left: 4px solid #e65100; padding: 10px; margin: 10px 0; font-size: 12px; color: #b75300;">
        <strong>Urgent Attention Required:</strong> Failure to provide the extended Bank Guarantee prior to expiry will lead to appropriate contractual and administrative actions as stipulated in the contract agreement.
      </blockquote>"""

    else:  # 10D
        subject = (f"{prefix}FINAL NOTICE: Imminent Bank Guarantee Expiry & "
                   f"Invocation Alert (10 Days) – Action Required")
        intro = """<p>Dear Sir/Madam,</p>
      <p>This is the <strong>FINAL NOTICE</strong> regarding the following Bank Guarantee(s) scheduled to expire in approximately <strong>10 calendar days</strong>.</p>"""
        notice = """<blockquote style="background-color: #f9f9f9; border-left: 4px solid #1a73e8; padding: 10px; margin: 10px 0; font-size: 12px; color: #555;">
        <strong>Caution:</strong> This is an automated reminder generated from the Bank Guarantee Monitoring Register. Please verify details immediately.
      </blockquote>
      <div style="color: #b71c1c; background-color: #ffebee; border-left: 5px solid #c62828; padding: 12px; margin: 15px 0; font-size: 13px; font-weight: bold; line-height: 1.5;">
        Please note that in the event the extended Bank Guarantee is not received within 10 (ten) days, we shall be constrained to invoke the Bank Guarantee before its expiry, without any further notice or reminder to you, and to recover such other amounts as may be due under the contract. Any consequences arising therefrom shall be entirely to your account.
      </div>"""

    html = '<div style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">'

    if is_test:
        html += (f'<div style="background-color: #fff3cd; color: #856404; padding: 10px; '
                 f'margin-bottom: 15px; border: 1px solid #ffeeba; border-radius: 4px;">'
                 f'<strong>[TEST MODE ACTIVE]</strong> In Production, this email will be '
                 f'delivered to: {recipient}</div>')

    html += intro
    html += ('<table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; '
             'width: 100%; border-color: #ccc; font-size: 13px; margin: 12px 0;">'
             '<thead><tr style="background-color: #f2f2f2; text-align: left;">')
    for key in display_keys:
        html += f'<th style="padding: 8px;">{key}</th>'
    html += "</tr></thead><tbody>"

    for record in rows:
        html += "<tr>"
        for key in display_keys:
            value = record.get(key, "")
            html += f'<td style="padding: 8px; font-size: 12px;">{value if value != "" else "N/A"}</td>'
        html += "</tr>"

    html += "</tbody></table>"
    html += notice
    html += (f'<p>Regards,<br/><strong>Bank Guarantee Monitoring System</strong><br/>'
             f'<small>Sent via: {SENDER_EMAIL}</small></p></div>')

    return subject, html


def send_via_gmail(to_addr, cc, bcc, subject, html, password):
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_addr
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg.set_content("This reminder requires an HTML-capable email client.")
    msg.add_alternative(html, subtype="html")

    recipients = [a.strip() for a in to_addr.split(",") if a.strip()]
    recipients += [a.strip() for a in cc.split(",") if a.strip()]
    recipients += [a.strip() for a in bcc.split(",") if a.strip()]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as server:
        server.login(SENDER_EMAIL, password)
        server.send_message(msg, from_addr=SENDER_EMAIL, to_addrs=recipients)


# ──────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Bank Guarantee expiry monitor")
    ap.add_argument("--preview", action="store_true",
                    help="list what is due; send no email and write no log")
    ap.add_argument("--test", action="store_true",
                    help="force TEST mode regardless of the Config sheet")
    args = ap.parse_args()

    ss = open_spreadsheet()
    config = get_config(ss)
    holidays = get_holidays(ss)
    log_sheet = get_or_create_log(ss)
    sent_ids, logged_ids = read_log_state(log_sheet)

    mode = "TEST" if args.test else config.get("SYSTEM_MODE", "TEST").upper()
    is_test = mode != "PRODUCTION"

    try:
        bg_sheet = ss.worksheet(BG_SHEET_NAME)
    except gspread.WorksheetNotFound:
        sys.exit("Error: Sheet named 'BG' was not found.")

    data = bg_sheet.get_all_values()
    if len(data) <= 1:
        print("BG sheet is empty.")
        return

    headers = [str(h).strip() for h in data[0]]
    idx = get_header_indexes(headers)
    contract_idx = idx["contractDate"] if idx["contractDate"] != -1 else 4    # column E
    bgdate_idx = idx["bgDate"] if idx["bgDate"] != -1 else 7                  # column H
    expiry_idx = idx["expiryDate"] if idx["expiryDate"] != -1 else 12         # column M

    today = datetime.now(IST).date()
    log_rows = []
    pending = []

    def cell(row, i):
        return row[i] if 0 <= i < len(row) else ""

    def note(uid, bg_no, expiry, status, message):
        """Log a skip only the first time it happens, so the log stays small."""
        if uid not in logged_ids:
            logged_ids.add(uid)
            log_rows.append(make_log_row(uid, bg_no, expiry, status, message, mode))

    for r, row in enumerate(data[1:], start=2):
        if all(str(c).strip() == "" for c in row):
            continue

        raw_expiry = cell(row, expiry_idx)
        if str(raw_expiry).strip() == "":
            continue

        record = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
        bg_number = (str(cell(row, idx["bgNumber"])).strip()
                     if idx["bgNumber"] != -1 and str(cell(row, idx["bgNumber"])).strip()
                     else f"ROW-{r}")
        status = (str(cell(row, idx["status"])).strip().lower()
                  if idx["status"] != -1 else "active")

        if status in INACTIVE_STATUSES:
            note(generate_unique_id(bg_number, None, "INACTIVE"), bg_number, raw_expiry,
                 "Skipped", "BG Status is Inactive/Closed")
            continue

        expiry = parse_date(raw_expiry)
        bg_date = parse_date(cell(row, bgdate_idx))
        contract_date = parse_date(cell(row, contract_idx))

        if not expiry:
            note(generate_unique_id(bg_number, None, "INVALID"), bg_number, raw_expiry,
                 "Invalid Expiry Date", "Expiry date text could not be parsed as a valid date")
            continue

        if bg_date and contract_date and bg_date < contract_date:
            note(generate_unique_id(bg_number, expiry, "INVALID_BG_DATE"), bg_number, expiry,
                 "Invalid BG Date",
                 "INVALID BG DATE: BG DATE CANNOT BE EARLIER THAN THE CONTRACT DATE.")
            continue

        if bg_date and expiry <= bg_date:
            note(generate_unique_id(bg_number, expiry, "INVALID_EXPIRY_DATE"), bg_number, expiry,
                 "Invalid Expiry Date",
                 "INVALID EXPIRY DATE: DATE OF EXPIRY MUST BE LATER THAN THE BG DATE.")
            continue

        if expiry < today:
            note(generate_unique_id(bg_number, expiry, "EXPIRED"), bg_number, expiry,
                 "Skipped", "BG is already expired in the past")
            continue

        due = evaluate_due_tier(expiry, today, holidays, sent_ids, bg_number)
        if due:
            record["_bgNumber"] = bg_number
            record["_uid"] = due["uid"]
            record["_expiry"] = expiry
            record["_tier"] = due["tier"]
            record["_email"] = (clean_email_list(cell(row, idx["email"]))
                                if idx["email"] != -1 else "")
            pending.append(record)

    # ── Preview only ──────────────────────────────────────────────────────
    if args.preview:
        if not pending:
            print("No active Bank Guarantees are due for reminder today "
                  "across all 3 tiers (30D, 20D, 10D).")
            return
        print(f"The following Bank Guarantee reminders are due ({today:%d-%m-%Y}):\n")
        for rec in pending:
            print(f"  • [{rec['_tier']['name']}] BG Ref: {rec['_bgNumber']} | "
                  f"Expiry: {fmt(rec['_expiry'])}")
        print("\n(Preview only — no email sent, no log written.)")
        return

    if not pending and not log_rows:
        print("No pending Bank Guarantee reminders due today.")
        return

    # ── Send ──────────────────────────────────────────────────────────────
    display_keys = [h for h in headers if h]
    default_to = clean_email_list(config.get("DEFAULT_TO_EMAIL") or config.get("TEST_EMAIL")
                                  or SENDER_EMAIL)
    cc = clean_email_list(config.get("CC_EMAILS", ""))
    bcc = clean_email_list(config.get("BCC_EMAILS", ""))

    password = os.environ.get(APP_PASSWORD_ENV, "")
    if pending and not password:
        sys.exit(f"Gmail app password not found. Set the {APP_PASSWORD_ENV} "
                 f"environment variable before running.")

    groups = {}
    for rec in pending:
        recipient = default_to if (is_test or not rec["_email"]) else rec["_email"]
        groups.setdefault((recipient, rec["_tier"]["key"]), []).append(rec)

    for (recipient, tier_key), items in groups.items():
        tier = items[0]["_tier"]
        subject, html = build_email(tier_key, len(items), recipient, is_test,
                                    display_keys, items)
        try:
            send_via_gmail(recipient, cc, bcc, subject, html, password)
            for rec in items:
                log_rows.append(make_log_row(
                    rec["_uid"], rec["_bgNumber"], rec["_expiry"], "Sent",
                    f"[{tier['name']}] Email sent successfully to {recipient}", mode))
            print(f"Sent {tier['key']} notice ({len(items)} item(s)) to {recipient}")
        except Exception as err:
            for rec in items:
                log_rows.append(make_log_row(
                    rec["_uid"], rec["_bgNumber"], rec["_expiry"], "Failed",
                    f"[{tier['name']}] Error: {err}", mode))
            print(f"FAILED {tier['key']} notice to {recipient}: {err}")

    if log_rows:
        log_sheet.append_rows(log_rows, value_input_option="RAW")

    print(f"Run complete ({mode} mode). {len(log_rows)} log entries written.")


if __name__ == "__main__":
    main()
