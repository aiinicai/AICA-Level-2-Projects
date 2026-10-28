"""
RBL Corporate NetBanking Balance Checker
=================================================
Logs into corporate account, fetches all account balances,
saves everything to an Excel file with an account name column.

Requirements:
    pip install playwright openpyxl
    python -m playwright install chromium

Usage:
    python rbl_balance.py
"""

import os
import sys
import getpass
import time
from datetime import datetime
import openpyxl
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Support running both from base folder and from RBL subfolder
for _p in [Path(__file__).parent.resolve(), Path(__file__).parent.parent.resolve()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ─── Configuration ────────────────────────────────────────────────────────────
from config import RBL_BALANCES_FILE as OUTPUT_FILE, CHROME_PATH, load_bank_accounts
#
HEADLESS    = False


# Accounts to process — loaded dynamically from bank_accounts.json
def get_accounts():
    try:
        data = load_bank_accounts()
        accs = [
            {"name": a.get("code") or a.get("name"), "user_id": a.get("id") or a.get("user_id")}
            for a in data.get("RBL", []) if a.get("active", True)
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
    print("  Bank Data Fetcher")
    print("  Accounts to fetch: " + ", ".join(a.get("name", "") for a in ACCOUNTS))
    print("  Password is the same for all accounts.\n")
    return _get_password("  Enter your NetBanking Password (hidden): ")


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
        ws.append([
            row["date"], 
            row["time"], 
            row["account_name"], 
            row["account_type"], 
            row["account_number"], 
            float(row["balance"]) if row["balance"] else "" # Save balance as a number in Excel
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


def handle_interstitial_popups(page, max_wait_sec=15):
    """
    Monitors for any intermediate advert/banner/modal pages or popups
    and clicks close/skip until the account summary becomes visible.
    """
    ad_close_selectors = [
        # Close buttons / cross icons
        "input[id='CLOSE']", "input[name='Action.CLOSE']", "button[aria-label*='close' i]",
        "a[aria-label*='close' i]",
        "[id*='close' i]",
        "[class*='close' i]",
        "button:has-text('✕')",
        "button:has-text('×')",
        "span:has-text('✕')",
        "span:has-text('×')",
        "img[src*='close' i]",
        # Action prompts
        "a:has-text('Skip')", "button:has-text('Skip')",
        "a:has-text('Close')", "button:has-text('Close')",
        "a:has-text('Remind me later')", "button:has-text('Later')",
        "button:has-text('Proceed to Dashboard')",
        "a:has-text('Continue to Dashboard')",
        "a:has-text('Proceed to Accounts')",
        "button:has-text('Dismiss')",
    ]

    target_table_selectors = [
        "a.searchsimpletext_wrapnew.bluelink",
        "a[id*='OPR_ACCOUNT_NUMBER_ARRAY']",
        "span.customNewUIAmount"
    ]

    start_time = time.time()
    while time.time() - start_time < max_wait_sec:
        # Check if the target dashboard/account table is already visible
        for target_sel in target_table_selectors:
            try:
                if page.locator(target_sel).first.is_visible():
                    return True
            except Exception:
                pass

        # Check for advert or banner close buttons
        clicked = False
        for sel in ad_close_selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=500):
                    loc.click(timeout=1000)
                    print(f"   ✅ Dismissed advert / popup via selector: {sel}")
                    page.wait_for_timeout(1000)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            page.wait_for_timeout(500)

    return False


def parse_accounts(page) -> list:
    print("      ⏳ Waiting for account table to load...")
    
    try:
        page.wait_for_selector("a.searchsimpletext_wrapnew.bluelink, a[id*='OPR_ACCOUNT_NUMBER_ARRAY']", timeout=15000)
    except Exception:
        pass 
    
    page.wait_for_timeout(2000)
    
    # 1. Grab Account Numbers
    acc_elements = page.locator("a.searchsimpletext_wrapnew.bluelink").all()
    if not acc_elements:
        acc_elements = page.locator("a[id*='OPR_ACCOUNT_NUMBER_ARRAY']").all()
        
    # 2. Grab Account Types ("Current", "Term Deposits", etc.)
    type_elements = page.locator("span[id*='PRODUCT_CATEGORY_ARRAY']").all()
        
    # 3. Grab Balances
    bal_elements = page.locator("span.customNewUIAmount").all()

    numeric_balances = []
    for b in bal_elements:
        text = b.inner_text().strip().replace('INR', '').replace('₹', '').replace(',', '').strip()
        if text and any(char.isdigit() for char in text):
            numeric_balances.append(text)

    print(f"      🔍 Found {len(acc_elements)} account numbers, {len(type_elements)} account types, and {len(numeric_balances)} numeric balances.")

    raw_accounts = []
    total_fd_amount = 0.0

    for i in range(len(acc_elements)):
        try:
            acct_number = acc_elements[i].inner_text().strip()
            balance_str = numeric_balances[i] if i < len(numeric_balances) else ""
            acct_type = type_elements[i].inner_text().strip() if i < len(type_elements) else "Corporate"

            if balance_str:
                bal_float = float(balance_str)
                # Check if this row is a Fixed Deposit / Term Deposit
                is_fd = any(keyword in acct_type.lower() for keyword in ["term deposit", "fixed deposit", "fd"])
                if is_fd:
                    total_fd_amount += bal_float

                raw_accounts.append({
                    "account_type":   acct_type,
                    "account_number": acct_number,
                    "raw_balance":    bal_float,
                    "is_fd":          is_fd
                })
            else:
                print(f"      ⚠️  Skipped account {acct_number} because no valid balance was found.")
        except Exception as e:
            print(f"      ⚠️  Error parsing account {i}: {e}")

    final_accounts = []
    for acc in raw_accounts:
        if not acc["is_fd"]:
            # Subtract FD amount from the main/current account balance
            net_balance = round(acc["raw_balance"] - total_fd_amount, 2)
            print(f"      💵  {acc['account_type']:<14} {acc['account_number']}   Net: {net_balance:.2f} (Gross: {acc['raw_balance']:.2f} - FD: {total_fd_amount:.2f})")
            final_accounts.append({
                "account_type":   acc["account_type"],
                "account_number": acc["account_number"],
                "balance":        str(net_balance),
            })
        else:
            # Keep FD row recorded as-is for reference
            print(f"      💵  {acc['account_type']:<14} {acc['account_number']}   FD Amount: {acc['raw_balance']:.2f}")
            final_accounts.append({
                "account_type":   acc["account_type"],
                "account_number": acc["account_number"],
                "balance":        str(acc["raw_balance"]),
            })

    return final_accounts


def login_and_fetch(page, user_id: str, account_name: str, password: str, is_last: bool = False) -> list:
    results  = []
    now      = datetime.now()
    date_str = now.strftime("%d/%m/%y")
    time_str = now.strftime("%H:%M")

    print(f"\n{'='*55}")
    print(f"  Account: {account_name}  (User ID: {user_id})")
    print(f"{'='*55}")

    try:
        # ── Load Corporate login page ──────────────────────────────────────────
        print("🔗 Loading login page...")
        page.goto("https://online.rbl.bank.in/CorpBank/", timeout=30000, wait_until="domcontentloaded")

        # ── Enter User ID ──────────────────────────────────────────────────────
        print("🔑 Entering Corporate User ID...")
        quick_fill(page, [
            "input[type='text']"
        ], user_id, "User ID", timeout=10000)

        # ── Click Next ─────────────────────────────────────────────────────────
        quick_click(page, [
            "input[value='Next']",
        ], "Next/Continue", timeout=3000)

        page.wait_for_timeout(2000)

        # ── Check 'I confirm the image' ────────────────────────────────────────
        print("🖼️  Checking 'I confirm the image' checkbox...")
        try:
            page.locator("input[id='AuthenticationFG.TARGET_CHECKBOX']").check(force=True, timeout=3000)
            print("   ✅ Checked using Playwright check(force=True)")
        except Exception:
            try:
                page.evaluate('''() => { 
                    const cb = document.getElementById('AuthenticationFG.TARGET_CHECKBOX'); 
                    if(cb) { cb.click(); cb.checked = true; cb.dispatchEvent(new Event('change', {bubbles: true})); } 
                }''')
                print("   ✅ Checked using JavaScript event dispatch")
            except Exception:
                print("   ⚠️ Could not check the box.")

        # ── Enter Password ─────────────────────────────────────────────────────
        print("🔒 Entering password...")
        quick_fill(page, [
            "input[id='AuthenticationFG.ACCESS_CODE']",
            "input[type='password']",
            "input[id*='password']", "input[id*='Password']",
            "input[placeholder*='Password']",
        ], password, "Password")

        # ── Click Login ────────────────────────────────────────────────────────
        quick_click(page, [
            "input[id='VALIDATE_STU_CREDENTIALS_UX']",
            "input[type='submit']",
            "button:has-text('Login')", "button:has-text('LOGIN')",
            "button:has-text('Sign In')",
        ], "Login", use_js=True)

        # ── Wait for post-login screen & handle adverts / popups ───────────────
        print("⏳ Waiting for post-login home page (handling potential popups)...")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Dismiss any interstitial ads / close buttons
        handle_interstitial_popups(page, max_wait_sec=12)

        # ── Scrape balances from Home Page ─────────────────────────────────────
        print("💰 Reading balances from Home Page...")
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
            print("   ⚠️  No balances found on the home page. Check parsing logic.")

    except PlaywrightTimeoutError as e:
        print(f"   ❌ Timeout: {e}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # ── Logout ─────────────────────────────────────────────────────────────────
    print("🔒 Logging out...")
    
    for sel in [
        "a:has-text('Logout')",   "a:has-text('logout')",
        "a:has-text('Log Out')",  "a:has-text('Log out')",
        "button:has-text('Logout')", "button:has-text('Log Out')",
        "[aria-label*='logout']", "[aria-label*='Logout']",
        "[class*='logout']", "a[href*='logout']"
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                el.click()
                page.wait_for_load_state("domcontentloaded", timeout=8000)
                print("   ✅ Logged out.")
                break
        except Exception:
            continue

    if not is_last:
        try:
            page.goto("https://online.rbl.bank.in/CorpBank/", timeout=10000, wait_until="domcontentloaded")
        except:
            pass

    return results


def main():
    password   = get_password()
    all_results = []

    with sync_playwright() as p:
        print("\n🌐 Opening Google Chrome...")
        try:
            browser = p.chromium.launch(executable_path=CHROME_PATH, headless=HEADLESS)
        except Exception:
            print("   ⚠️  Chrome not found, falling back to Chromium.")
            browser = p.chromium.launch(headless=HEADLESS)

        page = browser.new_page()

        for i, account in enumerate(ACCOUNTS):
            is_last = (i == len(ACCOUNTS) - 1)
            rows = login_and_fetch(page, account["user_id"], account["name"], password, is_last=is_last)
            if rows:
                save_to_excel(rows)   # Save to Excel immediately after each account
            all_results.extend(rows)

        browser.close()

    if all_results:
        print(f"\n{'='*55}")
        print("  Final Summary")
        print(f"{'='*55}")
        print(f"   {'Name':<6} {'Type':<14} {'Account':<15} {'Balance':>15}")
        print("   " + "-"*53)
        for r in all_results:
            print(f"   {r['account_name']:<6} {r['account_type']:<14} {r['account_number']:<15} {r['balance']:>15}")
        print(f"\n📂 Done! Open '{OUTPUT_FILE}' to see your balance history.")
    else:
        print("\n⚠️  No balance data was captured.")


if __name__ == "__main__":
    main()