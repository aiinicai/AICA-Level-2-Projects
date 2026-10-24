"""
HDFC NetBanking — Balance + Recent Transactions Checker
========================================================
For every configured account this script:
  1. Logs in with the shared password.
  2. Reads all account balances from the Accounts list page.
  3. Drills into each sub-account and scrapes Recent Transactions
     (Table View preferred; Smart View as fallback).
  4. Saves balances → balances_hdfc.xlsx
     Saves transactions → hdfc_recent.xlsx
     (one blank-row gap between each sub-account group)
  5. Logs out and moves to the next NetBanking login.

Configure ACCOUNTS below with your Customer IDs before running.

Requirements:
    pip install playwright openpyxl
    python3 -m playwright install chromium

Usage:
    python3 hdfc_balance_with_transactions.py
"""

import os
import re
import sys
import getpass
import openpyxl
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Support running both from base folder and from HDFC subfolder
for _p in [Path(__file__).parent.resolve(), Path(__file__).parent.parent.resolve()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ─── Configuration ────────────────────────────────────────────────────────────
from config import HDFC_BALANCES_FILE as BALANCE_FILE, HDFC_TRANSACTIONS_FILE as TRANSACTIONS_FILE, CHROME_PATH, load_bank_accounts
#
HEADLESS          = False


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


def select_accounts() -> list:
    """Ask Y/N for each account and return the ones the user wants to run."""
    print("\n" + "=" * 55)
    print("  HDFC NetBanking — Balance + Transactions")
    print("=" * 55)
    print("Select accounts to fetch (Y/N for each):\n")

    selected = []
    for acct in ACCOUNTS:
        while True:
            ans = input(f"    {acct['name']}? [Y/N]: ").strip().lower()
            if ans in ("y", "yes"):
                selected.append(acct)
                break
            elif ans in ("n", "no"):
                break
            else:
                print("    Please enter Y or N.")

    if not selected:
        print("\n    ⚠️  No accounts selected. Exiting.")
        sys.exit(0)

    print("\n    ✅ Will fetch: " + ", ".join(a["name"] for a in selected))
    return selected


def get_password() -> str:
    print("\n" + "="*55)
    print("  HDFC NetBanking Balance Checker")
    print("="*55)
    
    prompt = "Enter your HDFC NetBanking Password (hidden): "
    print(prompt, end='', flush=True)
    
    password = ""
    import sys
    while True:
        key = msvcrt.getch()
        if key in (b'\r', b'\n'):  # Enter key
            print('')
            break
        elif key == b'\x08':  # Backspace key
            if len(password) > 0:
                password = password[:-1]
                sys.stdout.write('\b \b')
                sys.stdout.flush()
        elif key == b'\x03':  # Ctrl+C
            raise KeyboardInterrupt
        else:
            try:
                char = key.decode('utf-8')
                password += char
                sys.stdout.write('*')
                sys.stdout.flush()
            except UnicodeDecodeError:
                pass
                
    return password


# ─── Excel helpers ────────────────────────────────────────────────────────────

def to_float(val):
    """Safely converts string currencies to float for Excel."""
    if not val:
        return ""
    try:
        return float(str(val).replace(",", "").replace("₹", "").strip())
    except ValueError:
        return val

def parse_date_value(date_str):
    """Parses various date strings into a datetime.date object for Excel custom formatting."""
    if not date_str:
        return ""
    if isinstance(date_str, datetime):
        return date_str.date()
    
    date_str = str(date_str).strip()
    
    # Try parsing common formats encountered
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%d %b %Y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
            
    return date_str


def save_balances(rows: list):
    file_exists = os.path.isfile(BALANCE_FILE)
    
    if file_exists:
        wb = openpyxl.load_workbook(BALANCE_FILE)
        ws = wb.active
        ws.append([]) # add a blank row separator if file already has data
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Balances"
        ws.append(["date", "time", "account_name", "account_type", "account_number", "balance"])
        
    for row in rows:
        parsed_date = parse_date_value(row["date"])
        added_row = ws.append([
            parsed_date, 
            row["time"], 
            row["account_name"], 
            row["account_type"], 
            row["account_number"], 
            to_float(row["balance"])
        ])
        
        # Apply custom format to the date cell (column 1)
        row_idx = ws.max_row
        cell = ws.cell(row=row_idx, column=1)
        if isinstance(parsed_date, datetime) or hasattr(parsed_date, 'year'):
            cell.number_format = 'dd-mmm-yy'
    
    ws.append([]) # Add blank line after each account's rows
    wb.save(BALANCE_FILE)
    print(f"    ✅ Balances saved → {BALANCE_FILE}")


def save_transactions(rows: list):
    """
    Append one account's transaction rows to the Excel sheet.
    Writes the header only on the very first run.
    Inserts one blank line before each subsequent account group so the sheet
    is easy to read at a glance.
    """
    if not rows:
        return
    
    file_exists = os.path.isfile(TRANSACTIONS_FILE)
    
    if file_exists:
        wb = openpyxl.load_workbook(TRANSACTIONS_FILE)
        ws = wb.active
        ws.append([]) # blank separator between account groups
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"
        ws.append(["fetched_date", "fetched_time", "account_name",
                   "account_number_masked", "txn_date", "description",
                   "debit", "credit", "balance"])
                   
    for row in rows:
        parsed_fetched_date = parse_date_value(row.get("fetched_date", ""))
        parsed_txn_date = parse_date_value(row.get("txn_date", ""))
        
        ws.append([
            parsed_fetched_date,
            row.get("fetched_time", ""),
            row.get("account_name", ""),
            row.get("account_number_masked", ""),
            parsed_txn_date,
            row.get("description", ""),
            to_float(row.get("debit")),
            to_float(row.get("credit")),
            to_float(row.get("balance"))
        ])
        
        row_idx = ws.max_row
        
        # Format fetched_date (Column 1)
        c1 = ws.cell(row=row_idx, column=1)
        if hasattr(parsed_fetched_date, 'year'):
            c1.number_format = 'dd-mmm-yy'
            
        # Format txn_date (Column 5)
        c5 = ws.cell(row=row_idx, column=5)
        if hasattr(parsed_txn_date, 'year'):
            c5.number_format = 'dd-mmm-yy'
        
    wb.save(TRANSACTIONS_FILE)
    print(f"    ✅ Transactions saved → {TRANSACTIONS_FILE}")


# ─── Playwright helpers ───────────────────────────────────────────────────────

def quick_fill(page, selectors, value, label, timeout=5000) -> bool:
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=timeout)
            el.fill(value)
            print(f"    ✅ Filled '{label}'")
            return True
        except Exception:
            continue
    print(f"    ⚠️  Could not fill '{label}'")
    return False


def quick_click(page, selectors, label, timeout=3000, use_js=False) -> bool:
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=timeout)
            if use_js:
                page.eval_on_selector(sel, "el => el.click()")
            else:
                el.click()
            print(f"    ✅ Clicked '{label}'")
            return True
        except Exception:
            continue
    return False


# ─── Prompt 1 — Collect account buttons ──────────────────────────────────────

def collect_account_buttons(page) -> list:
    page.wait_for_timeout(1500)
    body_text = page.inner_text("body")
    lines     = [l.strip() for l in body_text.splitlines()]

    seen      = set()
    accounts  = []
    last4_re  = re.compile(r'\*+\s*(\d{2})\s+(\d{2})\s*$')
    balance_re = re.compile(r'^₹?([\d,]+\.\d{2})$')

    for i, line in enumerate(lines):
        if line != "Account Number Hidden":
            continue

        acct_line = lines[i - 1] if i > 0 else ""

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

        m4 = last4_re.search(acct_line)
        masked = (m4.group(1) + m4.group(2)) if m4 else ""
        key    = masked or acct_line

        if key in seen:
            continue
        seen.add(key)

        balance = None
        for offset in range(2, 6):
            if i + offset >= len(lines):
                break
            bm = balance_re.match(lines[i + offset])
            if bm:
                balance = bm.group(1)
                break

        if balance:
            entry = {
                "index":                 len(accounts),
                "account_name":          acc_type,
                "account_number_masked": f"...{masked}" if masked else "",
                "balance":               balance,
            }
            accounts.append(entry)
            print(f"       📋  [{entry['index']}] {acc_type:<12} "
                  f"{entry['account_number_masked']:<10}  {balance}")

    return accounts


# ─── Helper — navigate back to the Accounts list ─────────────────────────────

def navigate_to_accounts_list(page) -> bool:
    print("    🔙 Returning to Accounts list via nav menu...")

    # If sidebar is collapsed in responsive/small mode, expand it
    sidebar_toggle = page.locator(
        "button[aria-label='Toggle sidebar'], button.bb-layout__nav-expand-marker"
    ).first
    try:
        if sidebar_toggle.is_visible(timeout=1000):
            is_expanded = sidebar_toggle.get_attribute("aria-expanded")
            if is_expanded == "false":
                sidebar_toggle.click()
                page.wait_for_timeout(500)
    except Exception:
        pass

    for sel in [
        "a[routerlink='/my-accounts']",
        "a[href='/retail-app/my-accounts']",
        "[class*='nav'] a:has-text('Accounts')",
        "nav a:has-text('Accounts')",
        "a:has-text('Accounts')",
        "button:has-text('Accounts')",
        "li:has-text('Accounts') > a",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                el.click()
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                page.wait_for_timeout(1000)
                print("    ✅ Back on Accounts list (via nav menu).")
                return True
        except Exception:
            continue

    print("    ⚠️  Nav menu click failed — trying browser Back...")
    try:
        page.go_back(timeout=8000)
        page.wait_for_load_state("domcontentloaded", timeout=8000)
        page.wait_for_timeout(1000)
        print("    ✅ Back on Accounts list (via go_back).")
        return True
    except Exception:
        pass

    print("    ⚠️  go_back failed — falling back to direct URL navigation...")
    try:
        page.goto(
            "https://now.hdfc.bank.in/retail-app/my-accounts/list",
            timeout=15000
        )
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        page.wait_for_timeout(1000)
        print("    ✅ Back on Accounts list (via goto URL — session may have reset).")
        return True
    except Exception as e:
        print(f"    ❌ Could not return to Accounts list: {e}")
        return False


def open_recent_transactions(page, account_index: int, target_masked: str = "") -> bool:
    CARD_SEL = (
        ".multiple-account-product-tile-wrapper, "
        "bb-multiple-account-product-tile-ui div.multiple-account-product-tile-wrapper, "
        "div[role='button'].multiple-account-product-tile-wrapper"
    )

    # 1. Wait for either the account cards or a single-account Recent Transactions button to attach
    try:
        page.wait_for_selector(
            f"{CARD_SEL}, button.recent-transaction-btn, button:has-text('Recent Transaction')",
            state="attached",
            timeout=8000
        )
    except Exception as e:
        print(f"    ❌ Neither account cards nor Recent Transaction button found: {e}")
        return False

    all_cards = page.locator(CARD_SEL).all()

    # If no multiple-account cards exist, check for single-account layout
    if not all_cards:
        print(f"\n    📂 Single-account layout — clicking Recent Transactions button...")
        for sel in [
            "button.recent-transaction-btn",
            "button:has-text('Recent Transaction')",
        ]:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state="attached", timeout=4000)
                btn.click(force=True)
                page.wait_for_timeout(1200)
                if "transactions" in page.url:
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                    print(f"    ✅ On transactions page: {page.url}")
                    return True
            except Exception:
                continue
        print("    ❌ Could not click Recent Transaction button.")
        return False

    # Prefer visible cards, but if none are marked visible by Playwright, fall back to all cards
    visible_cards = [c for c in all_cards if c.is_visible()]
    candidates = visible_cards if visible_cards else all_cards

    # If target_masked is provided (e.g. "...0689" or "06 89"), try to find matching card
    target_card = None
    if target_masked:
        clean_target = target_masked.replace(".", "").replace(" ", "").strip()
        for c in candidates:
            txt = (c.text_content() or "").replace(" ", "")
            if clean_target and clean_target in txt:
                target_card = c
                break

    if target_card is None:
        if account_index < len(candidates):
            target_card = candidates[account_index]
        else:
            print(f"    ❌ Requested index {account_index} but only {len(candidates)} cards exist.")
            return False

    print(f"\n    📂 Clicking account card #{account_index}...")

    try:
        target_card.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass
    page.wait_for_timeout(300)

    # Try regular click, offset click, and JS click if needed
    clicked = False
    for click_action in [
        lambda: target_card.click(timeout=3000),
        lambda: target_card.click(position={"x": 80, "y": 40}, timeout=3000),
        lambda: target_card.click(force=True, timeout=3000),
        lambda: target_card.evaluate("el => el.click()"),
    ]:
        try:
            click_action()
            page.wait_for_timeout(1200)
            if "transactions" in page.url:
                clicked = True
                break
        except Exception:
            continue

    if not clicked and "transactions" not in page.url:
        print(f"    ❌ Navigation to transactions did not happen (URL: {page.url})")
        return False

    page.wait_for_load_state("domcontentloaded", timeout=10000)
    print(f"    ✅ On transactions page: {page.url}")
    return True


# ─── Prompt 3 — Scrape ALL pages of Recent Transactions ──────────────────────

def _clean_amount(text: str) -> str:
    return text.replace("₹", "").strip()

def _scrape_one_page_table_view(page) -> list:
    try:
        table = page.locator('div[role="table"][aria-label="Transactions"]')
        # Check instantly if the table exists on the page without waiting
        if table.count() == 0 or not table.first.is_visible():
            return []

        rowgroups = table.locator('div[role="rowgroup"]').all()
        if len(rowgroups) < 2:
            return []

        data_rows = rowgroups[1].locator('div[role="row"]').all()
        if not data_rows:
            return []

        print(f"      Found {len(data_rows)} rows in Table View.")
        result = []
        for row in data_rows:
            def cell(n):
                el = row.locator(f".table-view__column-{n}").first
                return el.inner_text().strip() if el.count() > 0 else ""

            date_raw = cell(1)
            date = date_raw.split("\n")[0].strip()

            result.append({
                "date":        date,
                "description": cell(2),
                "debit":       _clean_amount(cell(4)),
                "credit":      _clean_amount(cell(5)),
                "balance":     _clean_amount(cell(6)),
            })
        return result
    except Exception:
        return []


def _parse_row_text_content(tc: str) -> dict:
    d = {"date": "", "description": "", "debit": "", "credit": "", "balance": ""}
    if not tc:
        return d

    m = re.search(r'Date\s+(\d{1,2}\s+\w{3}\s+\d{4})', tc)
    if not m: return d
    d["date"] = m.group(1)

    m = re.search(r'Transaction\s*Summary(.*?)Ref\.\s*no\.', tc, re.DOTALL)
    if m: d["description"] = m.group(1).strip()

    m = re.search(r'Debit\s*₹([\d,]+\.?\d*)', tc)
    if m: d["debit"] = m.group(1)

    m = re.search(r'(?:Credit|Deposit)\s*₹([\d,]+\.?\d*)', tc)
    if m and not d["debit"]: d["credit"] = m.group(1)

    m = re.search(r'Closing balance\s*₹([\d,]+\.?\d*)', tc)
    if m: d["balance"] = m.group(1)

    return d


def _scrape_one_page_smart_view(page) -> list:
    for sel in [
        '[role="list"][aria-label="Transactions"]',
        '[role="list"]:has([role="none"] > button)',
    ]:
        try:
            page.wait_for_selector(sel, timeout=5000)
            txn_list    = page.locator(sel).first
            row_buttons = txn_list.locator('[role="none"] > button').all()
            if not row_buttons:
                row_buttons = txn_list.locator('button').all()
            if not row_buttons:
                continue

            print(f"      Found {len(row_buttons)} row buttons (Smart View).")
            rows = []
            for btn in row_buttons:
                try:
                    parsed = _parse_row_text_content(btn.text_content() or "")
                    if parsed["date"]:
                        rows.append(parsed)
                except Exception:
                    continue

            if rows: return rows
            print("      ⚠️  Smart View buttons found but parsing failed.")
            return []
        except Exception:
            continue
    return []


def scrape_transactions(page, account_name: str, account_number_masked: str,
                        fetched_date: str, fetched_time: str) -> list:
    print("    🔍 Scraping transactions...")
    all_transactions = []

    in_table_view = False
    for tv_sel in [
        'button[aria-label="Switch to Table View"]',
        '[role="tab"][aria-label="Switch to Table View"]',
    ]:
        try:
            tv_btn = page.locator(tv_sel).first
            if tv_btn.is_visible(timeout=500):
                tv_btn.click()
                page.wait_for_timeout(1500)
                print("      ✅ Switched to Table View.")
                in_table_view = True
                break
        except Exception:
            continue
    if not in_table_view:
        print("      ℹ️  Table View toggle not found — using Smart View.")

    page_num = 1
    while True:
        print(f"      📄 Page {page_num}...")
        page.wait_for_timeout(800)
        page_rows = []

        if in_table_view:
            page_rows = _scrape_one_page_table_view(page)
            if page_rows:
                print(f"      ✅ Strategy 1 (Table View): {len(page_rows)} rows")

        if not page_rows:
            page_rows = _scrape_one_page_smart_view(page)
            if page_rows:
                print(f"      ✅ Strategy 2 (Smart View list): {len(page_rows)} rows")

        if not page_rows:
            print("      🔄 Strategy 3 (plain text fallback)...")
            try:
                page.evaluate("window.scrollBy(0, 600)")
                page.wait_for_timeout(600)
                lines = [l.strip() for l in
                         page.inner_text("body").splitlines() if l.strip()]
                
                date_re = re.compile(
                    r'^\d{1,2}\s+\w{3}\s+\d{4}$'
                    r'|^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$'
                )
                
                # Fast check: bail out instantly if no line matches a date pattern
                if any(date_re.match(l) for l in lines):
                    i = 0
                    while i < len(lines):
                        if date_re.match(lines[i]):
                            row = {"date": lines[i], "description": "",
                                   "debit": "", "credit": "", "balance": ""}
                            j = i + 1
                            while j < min(i + 10, len(lines)):
                                lbl = lines[j].lower()
                                nxt = lines[j + 1] if j + 1 < len(lines) else ""
                                if lbl == "transaction summary":
                                    row["description"] = nxt; j += 2; continue
                                if lbl == "debit":
                                    row["debit"] = nxt; j += 2; continue
                                if lbl == "credit":
                                    row["credit"] = nxt; j += 2; continue
                                if lbl == "closing balance":
                                    row["balance"] = nxt; j += 2; continue
                                if date_re.match(lines[j]): break
                                j += 1
                            page_rows.append(row)
                            i = j
                        else:
                            i += 1
                if page_rows:
                    print(f"      ✅ Strategy 3: {len(page_rows)} rows")
                else:
                    print("      ⚠️  No rows found on this page via any strategy.")
            except Exception as e:
                print(f"      ⚠️  Strategy 3 error: {e}")

        for r in page_rows:
            all_transactions.append({
                "fetched_date":          fetched_date,
                "fetched_time":          fetched_time,
                "account_name":          account_name,
                "account_number_masked": account_number_masked,
                "txn_date":    r.get("date", ""),
                "description": r.get("description", ""),
                "debit":       r.get("debit", ""),
                "credit":      r.get("credit", ""),
                "balance":     r.get("balance", ""),
            })

        next_clicked = False
        for next_sel in ['a[aria-label="Next"]', '[aria-label="Next"]']:
            try:
                nb = page.locator(next_sel).first
                if nb.is_visible(timeout=1500) and nb.is_enabled():
                    nb.click()
                    page.wait_for_load_state("domcontentloaded", timeout=1000)
                    page.wait_for_timeout(1000)
                    page_num += 1
                    next_clicked = True
                    print(f"      ➡️  Moving to page {page_num}...")
                    break
            except Exception:
                continue

        if not next_clicked:
            print(f"      ✅ All pages done ({page_num} page(s), "
                  f"{len(all_transactions)} total rows).")
            break

    return all_transactions


# ─── Prompt 4 / 5 — Full account transaction loop ────────────────────────────

def fetch_transactions_for_account(page, acct: dict, account_index: int,
                                   owner_name: str, fetched_date: str,
                                   fetched_time: str, already_on_list: bool = False) -> list:
    print(f"\n    🏦 Fetching transactions for "
          f"{acct['account_name']} {acct['account_number_masked']} ...")

    if not already_on_list:
        navigate_to_accounts_list(page)

    success = open_recent_transactions(page, account_index, target_masked=acct.get("account_number_masked", ""))
    if not success:
        print(f"    ⚠️  Skipping transactions for {acct['account_number_masked']}.")
        return []

    txns = scrape_transactions(
        page,
        account_name         = f"{owner_name} — {acct['account_name']}",
        account_number_masked = acct["account_number_masked"],
        fetched_date         = fetched_date,
        fetched_time         = fetched_time,
    )
    print(f"      📊 {len(txns)} transaction(s) collected.")
    return txns


# ─── parse_accounts (unchanged from original) ────────────────────────────────

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

        m4 = last4_re.search(acct_line)
        acct_number = (m4.group(1) + m4.group(2)) if m4 else ""

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
            print(f"       💵  {acc_type:<12} ...{acct_number}   {balance}")

    return accounts


# ─── Login + fetch balances + transactions for one NetBanking user ────────────

def login_and_fetch(page, customer_id: str, account_name: str,
                    password: str, is_last: bool = False):
    balance_rows     = []
    transaction_rows = []
    now              = datetime.now()
    date_str         = now.strftime("%d/%m/%y")
    time_str         = now.strftime("%H:%M")

    print(f"\n{'='*55}")
    print(f"  Account: {account_name}  (ID: {customer_id})")
    print(f"{'='*55}")

    try:
        print("🔗 Loading login page...")
        page.goto("https://now.hdfc.bank.in/", timeout=30000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)

        print("🔑 Entering Customer ID...")
        quick_fill(page, [
            "input#username", "input[name='username']", ".login-username-field",
            "input[id*='username']",
        ], customer_id, "Customer ID")
        page.wait_for_timeout(300)

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
                    print("    📱 Sidebar collapsed, expanding sidebar...")
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

        print("\n💰 Reading balances...")
        raw_accounts = parse_accounts(page)
        for acc in raw_accounts:
            balance_rows.append({
                "date":            date_str,
                "time":            time_str,
                "account_name":    account_name,
                "account_type":    acc["account_type"],
                "account_number":  acc["account_number"],
                "balance":         acc["balance"],
            })

        if not raw_accounts:
            print("    ⚠️  No balances found.")

        print("\n📋 Collecting account buttons (Prompt 1)...")
        account_buttons = collect_account_buttons(page)
        print(f"    Found {len(account_buttons)} unique accounts.")

        print("\n🔄 Fetching recent transactions...")
        for loop_idx, acct in enumerate(account_buttons):
            txns = fetch_transactions_for_account(
                page,
                acct             = acct,
                account_index    = acct["index"],
                owner_name       = account_name,
                fetched_date     = date_str,
                fetched_time     = time_str,
                already_on_list  = (loop_idx == 0),
            )
            if txns:
                save_transactions(txns)
            transaction_rows.extend(txns)

    except PlaywrightTimeoutError as e:
        print(f"    ❌ Timeout: {e}")
    except Exception as e:
        print(f"    ❌ Error: {e}")

    print("\n🔒 Logging out...")
    logged_out = False

    for trigger in [
        "[class*='profile']", "[class*='user-menu']", "[class*='userMenu']",
        "[class*='avatar']",  "[aria-label*='profile']", "[aria-label*='user']",
        f"button:has-text('{account_name}')",
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

    for sel in [
        "a:has-text('Logout')",    "a:has-text('logout')",
        "a:has-text('Log Out')",   "a:has-text('Log out')",
        "a:has-text('Sign Out')",  "a:has-text('Sign out')",
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
                print("    ✅ Logged out.")
                logged_out = True
                break
        except Exception:
            continue

    if not logged_out:
        try:
            page.goto("https://now.hdfc.bank.in/logout", timeout=10000)
            page.wait_for_load_state("domcontentloaded", timeout=8000)
            print("    ✅ Logged out via /logout URL.")
        except Exception:
            pass

    if not is_last:
        try:
            page.goto("https://now.hdfc.bank.in/", timeout=10000)
            page.wait_for_load_state("domcontentloaded", timeout=8000)
            print("    ✅ Returned to login page.")
        except Exception:
            pass

    return balance_rows, transaction_rows


# ─── Main ────────────────────────────────────────────────────────────────     

def main():
    run_accounts       = select_accounts()
    password           = get_password()
    all_balances       = []
    all_transactions = []

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
            print("    ⚠️  Chrome not found, falling back to Chromium.")
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=HEADLESS,
                no_viewport=True
            )

        page = context.pages[0] if context.pages else context.new_page()

        for i, account in enumerate(run_accounts):
            is_last = (i == len(run_accounts) - 1)
            bal_rows, txn_rows = login_and_fetch(
                page,
                customer_id  = account["customer_id"],
                account_name = account["name"],
                password     = password,
                is_last      = is_last,
            )

            if bal_rows:
                save_balances(bal_rows)

            all_balances.extend(bal_rows)
            all_transactions.extend(txn_rows)

        context.close()

    print(f"\n{'='*55}")
    print("  Final Summary")
    print(f"{'='*55}")

    if all_balances:
        print(f"\n  Balances ({len(all_balances)} accounts):")
        print(f"    {'Name':<6} {'Type':<14} {'Account':<10} {'Balance':>15}")
        print("    " + "-"*48)
        for r in all_balances:
            print(f"    {r['account_name']:<6} {r['account_type']:<14} "
                  f"{r['account_number']:<10} {r['balance']:>15}")
        print(f"\n    📂 {BALANCE_FILE}")
    else:
        print("\n  ⚠️  No balance data was captured.")

    if all_transactions:
        print(f"\n  Transactions ({len(all_transactions)} total):")
        for acct_key in dict.fromkeys(
            f"{r['account_name']} {r['account_number_masked']}"
            for r in all_transactions
        ):
            count = sum(
                1 for r in all_transactions
                if f"{r['account_name']} {r['account_number_masked']}" == acct_key
            )
            print(f"    • {acct_key}: {count} transaction(s)")
        print(f"\n    📂 {TRANSACTIONS_FILE}")
    else:
        print("\n  ⚠️  No transaction data was captured.")

    print(f"\n✅ Done!")


if __name__ == "__main__":
    main()