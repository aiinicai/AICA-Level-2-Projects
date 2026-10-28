"""
HDFC NetBanking Balance Checker — Multi-Account
=================================================
Logs into each account in sequence, fetches all account balances,
saves everything to an Excel file with an account name column.

Requirements:
    pip install playwright openpyxl
    python3 -m playwright install chromium

Usage:
    python3 hdfc_balance.py
"""

import os
import re
import sys
import getpass
from datetime import datetime
import openpyxl
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Support running both from base folder and from HDFC subfolder
for _p in [Path(__file__).parent.resolve(), Path(__file__).parent.parent.resolve()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ─── Configuration ────────────────────────────────────────────────────────────
from config import HDFC_BALANCES_FILE as OUTPUT_FILE, CHROME_PATH, load_bank_accounts

HEADLESS = False

# Persistent profile directory so Chrome remembers window size, position, and layout
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".hdfc_chrome_profile")

# Accounts to process — loaded dynamically from bank_accounts.json
def get_accounts():
    try:
        data = load_bank_accounts()
        accs = [
            {"name": a.get("code") or a.get("name"), "customer_id": a.get("id") or a.get("customer_id")}
            for a in data.get("HDFC", []) if a.get("active", True)
        ]
        if accs:
            return accs
    except Exception:
        pass
    return [

    ]

ACCOUNTS = get_accounts()
# ──────────────────────────────────────────────────────────────────────────────


def get_password():
    from config import get_password as _get_password
    print("\n" + "="*55)
    print("  HDFC NetBanking Balance Checker")
    print("  Accounts to fetch: " + ", ".join(a["name"] for a in ACCOUNTS))
    print("  Password is the same for all accounts.\n")
    return _get_password("  Enter your HDFC NetBanking Password (hidden): ")


def save_to_excel(rows: list):
    file_exists = os.path.isfile(OUTPUT_FILE)
    
    if file_exists:
        wb = openpyxl.load_workbook(OUTPUT_FILE)
        ws = wb.active
        ws.append([]) # Add blank row separator if file already has data
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Balances"
        # Write headers
        ws.append(["date", "time", "account_name", "account_type", "account_number", "balance"])

    for row in rows:
        # HDFC grabs the balance with commas (e.g. "1,234.56").
        # We need to remove the commas to save it as a true number in Excel.
        try:
            bal_val = float(row["balance"].replace(",", "")) if row["balance"] else ""
        except ValueError:
            bal_val = row["balance"]
            
        ws.append([
            row["date"], 
            row["time"], 
            row["account_name"], 
            row["account_type"], 
            row["account_number"], 
            bal_val
        ])

    ws.append([]) # Add blank line after each account's rows
    
    wb.save(OUTPUT_FILE)
    print(f"   ✅ Saved to {OUTPUT_FILE}")


def quick_fill(page, selectors, value, label, timeout=1000):
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=timeout)
            el.fill(value)
            print(f"   ✅ Filled '{label}' → {sel}")
            return True
        except Exception:
            continue
    print(f"   ⚠️  Could not fill '{label}'")
    return False


def quick_click(page, selectors, label, timeout=1000, use_js=False):
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=timeout)
            if use_js:
                page.eval_on_selector(sel, "el => el.click()")
            else:
                el.click()
            print(f"   ✅ Clicked '{label}' → {sel}")
            return True
        except Exception:
            continue
    return False


def parse_accounts(page) -> list:
    page.wait_for_timeout(1500)
    body_text = page.inner_text("body")
    lines     = [l.strip() for l in body_text.splitlines()]
    accounts   = []
    last4_re   = re.compile(r'\*+\s*(\d{2})\s+(\d{2})\s*$')
    balance_re = re.compile(r'^₹?([\d,]+\.\d{2})$')

    for i, line in enumerate(lines):
        if line != "Account Number Hidden":
            continue

        acct_line = lines[i - 1] if i > 0 else ""

        # Account type
        if re.search(r'\bsavings\b', acct_line, re.IGNORECASE) and \
           not re.search(r'scheme', acct_line, re.IGNORECASE):
            acc_type = "Savings"
        elif re.search(r'\bcurrent\b', acct_line, re.IGNORECASE):
            acc_type = "Current"
        elif re.search(r'provident|PPF|savings scheme', acct_line, re.IGNORECASE):
            acc_type = "PPF"
        elif re.search(r'\bsalary\b', acct_line, re.IGNORECASE):
            acc_type = "Salary"
        else:
            acc_type = re.sub(r'[*\s]+$', '', acct_line).strip()

        # Last 4 digits of account number
        m4 = last4_re.search(acct_line)
        acct_number = (m4.group(1) + m4.group(2)) if m4 else ""

        # Balance is within next 5 lines
        balance = None
        for offset in range(2, 6):
            if i + offset >= len(lines):
                break
            bm = balance_re.match(lines[i + offset])
            if bm:
                balance = bm.group(1)
                break

        if balance:
            accounts.append({
                "account_type":   acc_type,
                "account_number": f"...{acct_number}" if acct_number else "",
                "balance":        balance,
            })
            print(f"      💵  {acc_type:<12} ...{acct_number}   {balance}")

    return accounts


def login_and_fetch(page, customer_id: str, account_name: str, password: str, is_last: bool = False) -> list:
    """Log into one account, fetch balances, log out. Returns list of balance rows."""
    results  = []
    now      = datetime.now()
    date_str = now.strftime("%d/%m/%y")
    time_str = now.strftime("%H:%M")

    print(f"\n{'='*55}")
    print(f"  Account: {account_name}  (ID: {customer_id})")
    print(f"{'='*55}")

    try:
        # ── Load login page ────────────────────────────────────────────────────
        print("🔗 Loading login page...")
        page.goto("https://now.hdfc.bank.in/", timeout=30000, wait_until="domcontentloaded")

        # ── Enter Customer ID ──────────────────────────────────────────────────
        print("🔑 Entering Customer ID...")
        quick_fill(page, [
            "input[type='text']", "input[id*='username']",
            "input[id*='Username']", "input[id*='userId']",
            "input[id*='UserId']", "input[name='fldLoginUserId']",
            "input[placeholder*='Customer']", "input[placeholder*='User']",
        ], customer_id, "Customer ID")

        page.wait_for_timeout(300)

        # ── Enter Password ─────────────────────────────────────────────────────
        print("🔒 Entering password...")
        quick_fill(page, [
            "input[type='password']",
            "input[name='fldPassword']",
            "input[id*='password']", "input[id*='Password']",
            "input[placeholder*='Password']", "input[placeholder*='IPIN']",
        ], password, "Password")

        quick_click(page, [
            "input[type='submit']",
            "button:has-text('Login')", "button:has-text('LOGIN')",
            "button:has-text('Sign In')",
            "input[name='btnLogin']",
        ], "Login", use_js=True)

        # ── Smart Post-Login Watcher (Handles OTP, Proceed here, and Dashboard load) ──
        print("⏳ Waiting for dashboard (monitoring for OTP or 'Proceed here')...")
        import time
        start_time = time.time()
        timeout_sec = 120
        dashboard_reached = False
        otp_notified = False

        proceed_selector = "a:has-text('Proceed here'), button:has-text('Proceed here'), a:has-text('proceed here')"
        dashboard_selector = (
            "button[aria-label='Toggle sidebar'], "
            "button.bb-layout__nav-expand-marker, "
            "[class*='nav'] a:has-text('Accounts'), "
            "nav a:has-text('Accounts'), "
            "a:has-text('Accounts'), "
            "a:has-text('Home')"
        )
        # Match typical OTP flow text or inputs
        otp_selector = "input[type='password'][name*='otp' i], input[type='text'][name*='otp' i], text='One Time Password', text='OTP'"

        while time.time() - start_time < timeout_sec:
            # 1. Check for dashboard
            try:
                if page.locator(dashboard_selector).first.is_visible(timeout=500):
                    dashboard_reached = True
                    break
            except Exception:
                pass

            # 2. Check for 'Proceed here'
            try:
                if page.locator(proceed_selector).first.is_visible(timeout=500):
                    page.locator(proceed_selector).first.click()
                    print("    ✅ Clicked 'Proceed here' (active session cleared).")
                    page.wait_for_timeout(2000)
                    continue
            except Exception:
                pass

            # 3. Check for OTP Multi-Step Flow
            try:
                if not otp_notified and page.locator(otp_selector).first.is_visible(timeout=500):
                    print("    📱 Multi-step OTP detected. Please select delivery method and enter OTP in Chrome (waiting up to 120s)...")
                    otp_notified = True
            except Exception:
                pass

            page.wait_for_timeout(1000)

        if not dashboard_reached:
            print("    ⚠️ Dashboard did not appear within 120 seconds. Attempting to continue anyway...")
        else:
            print("    ✅ Dashboard loaded successfully.")

        # ── Expand sidebar if collapsed (for responsive / smaller windows) ─────
        sidebar_toggle = page.locator(
            "button[aria-label='Toggle sidebar'], button.bb-layout__nav-expand-marker"
        ).first
        try:
            if sidebar_toggle.is_visible(timeout=1000):
                is_expanded = sidebar_toggle.get_attribute("aria-expanded")
                if is_expanded == "false":
                    print("   📱 Sidebar collapsed, expanding sidebar...")
                    sidebar_toggle.click()
                    page.wait_for_timeout(600)
        except Exception:
            pass

        # ── Step 4: Click Accounts menu ────────────────────────────────────────
        print("📂 Clicking Accounts menu...")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        quick_click(page, [
            "[class*='nav'] a:has-text('Accounts')",
            "nav a:has-text('Accounts')",
            "a:has-text('Accounts')",
            "button:has-text('Accounts')",
            "li:has-text('Accounts') > a",
        ], "Accounts menu")

        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # ── Scrape balances ────────────────────────────────────────────────────
        print("💰 Reading balances...")
        accounts = parse_accounts(page)

        for acc in accounts:
            results.append({
                "date":           date_str,
                "time":           time_str,
                "account_name":   account_name,
                "account_type":   acc["account_type"],
                "account_number": acc["account_number"],
                "balance":        acc["balance"],
            })

        if not accounts:
            print("   ⚠️  No balances found for this account.")

    except PlaywrightTimeoutError as e:
        print(f"   ❌ Timeout: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # ── Logout ─────────────────────────────────────────────────────────────────
    print("🔒 Logging out...")
    logged_out = False

    # Some portals hide logout inside a profile/user dropdown — open it first
    for trigger in [
        "[class*='profile']", "[class*='user-menu']", "[class*='userMenu']",
        "[class*='avatar']",  "[aria-label*='profile']", "[aria-label*='user']",
        "button:has-text('VM')", "button:has-text('SM')",
        "[class*='header'] button", "[class*='topbar'] button",
    ]:
        try:
            el = page.locator(trigger).first
            if el.is_visible(timeout=800):
                el.click()
                page.wait_for_timeout(600)
                break
        except Exception:
            continue

    # Now try to find and click the logout link
    for sel in [
        "a:has-text('Logout')",   "a:has-text('logout')",
        "a:has-text('Log Out')",  "a:has-text('Log out')",
        "a:has-text('Sign Out')", "a:has-text('Sign out')",
        "button:has-text('Logout')", "button:has-text('Log Out')",
        "button:has-text('Sign Out')",
        "[aria-label*='logout']", "[aria-label*='Logout']",
        "[class*='logout']",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=800):
                el.click()
                page.wait_for_load_state("domcontentloaded", timeout=8000)
                print("   ✅ Logged out.")
                logged_out = True
                break
        except Exception:
            continue

    # Final fallback — navigate directly to the logout URL
    if not logged_out:
        try:
            page.goto("https://now.hdfc.bank.in/logout", timeout=10000)
            page.wait_for_load_state("domcontentloaded", timeout=8000)
            print("   ✅ Logged out via /logout URL.")
            logged_out = True
        except Exception:
            pass

    # Only navigate back to login page if there is a next account to process
    if not is_last:
        try:
            page.goto("https://now.hdfc.bank.in/", timeout=10000, wait_until="domcontentloaded")
            print("   ✅ Returned to login page.")
        except Exception:
            pass

    return results


def main():
    password   = get_password()
    all_results = []

    with sync_playwright() as p:
        print("\n🌐 Opening Google Chrome...")
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                executable_path=CHROME_PATH,
                headless=HEADLESS,
                no_viewport=True
            )
        except Exception:
            print("   ⚠️  Chrome not found, falling back to Chromium.")
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=HEADLESS,
                no_viewport=True
            )

        page = context.pages[0] if context.pages else context.new_page()

        for i, account in enumerate(ACCOUNTS):
            is_last = (i == len(ACCOUNTS) - 1)
            rows = login_and_fetch(page, account["customer_id"], account["name"], password, is_last=is_last)
            if rows:
                save_to_excel(rows)   # Save to Excel immediately after each account
            all_results.extend(rows)

        context.close()

    # ── Print final summary ────────────────────────────────────────────────────
    if all_results:
        print(f"\n{'='*55}")
        print("  Final Summary")
        print(f"{'='*55}")
        print(f"   {'Name':<6} {'Type':<14} {'Account':<10} {'Balance':>15}")
        print("   " + "-"*48)
        for r in all_results:
            print(f"   {r['account_name']:<6} {r['account_type']:<14} {r['account_number']:<10} {r['balance']:>15}")
        print(f"\n📂 Done! Open '{OUTPUT_FILE}' to see your balance history.")
    else:
        print("\n⚠️  No balance data was captured.")


if __name__ == "__main__":
    main()