import sys
import os
import re
import json
import webbrowser
import base64
from datetime import datetime
from pathlib import Path
import openpyxl

# Set console output encoding to utf-8 (if stdout exists)
if sys.stdout is not None and getattr(sys.stdout, 'encoding', None) != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config import (
    SCRIPT_DIR,
    DATA_DIR,
    HDFC_BALANCES_FILE as HDFC_FILE,
    HDFC_TRANSACTIONS_FILE,
    RBL_TRANSACTIONS_FILE,
    RBL_BALANCES_FILE as RBL_FILE,
    BANK_SUMMARY_HTML as OUTPUT_HTML,
    BANK_SUMMARY_SNIPPET as OUTPUT_SNIPPET,
    get_entity_names
)

ENTITY_NAMES = get_entity_names()


# Clean, authentic bank logos rendered purely in SVG (no external image dependencies)
HDFC_LOGO_SVG = '''<svg viewBox="0 0 40 40" width="22" height="22" xmlns="http://www.w3.org/2000/svg">
  <rect width="40" height="40" rx="4" fill="#004C8F"/>
  <rect x="8" y="8" width="24" height="24" fill="#ffffff"/>
  <rect x="12" y="12" width="16" height="16" fill="#ED232A"/>
  <rect x="16" y="16" width="8" height="8" fill="#004C8F"/>
</svg>'''

RBL_LOGO_SVG = '''<svg viewBox="0 0 40 40" width="22" height="22" xmlns="http://www.w3.org/2000/svg">
  <rect width="40" height="40" rx="4" fill="#C01D2E"/>
  <path d="M 10,24 L 20,10 L 30,24" fill="none" stroke="#FBB03B" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"/>
  <path d="M 10,30 L 20,16 L 30,30" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"/>
</svg>'''


def get_bank_logo(bank_name, width=22, height=22):
    """
    Looks for custom logo files:
      - hdfc_logo.png/svg/jpg/jpeg/webp or rbl_logo.png/svg/jpg/jpeg/webp
      in SCRIPT_DIR, DATA_DIR, or bank subfolders (HDFC/ or RBL/).
    Returns an inline SVG or <img> data URI tag.
    Falls back to built-in vector SVG if no custom image file is found.
    """
    bank_clean = str(bank_name).strip().upper()
    prefix = f"{bank_clean.lower()}_logo"
    folder_name = bank_clean

    extensions = [".png", ".svg", ".jpg", ".jpeg", ".webp"]
    search_dirs = [
        SCRIPT_DIR,
        DATA_DIR,
        SCRIPT_DIR / folder_name,
        DATA_DIR / folder_name,
    ]

    for d in search_dirs:
        for ext in extensions:
            candidate = d / f"{prefix}{ext}"
            if candidate.exists() and candidate.stat().st_size > 0:
                try:
                    if ext == ".svg":
                        svg_data = candidate.read_text(encoding="utf-8")
                        return f'<span class="bank-logo-icon" style="display:inline-flex; width:{width}px; height:{height}px; vertical-align:middle;">{svg_data}</span>'
                    else:
                        mime_type = "jpeg" if ext in [".jpg", ".jpeg"] else ext.lstrip(".")
                        b64_content = base64.b64encode(candidate.read_bytes()).decode("ascii")
                        return f'<img class="bank-logo-icon" src="data:image/{mime_type};base64,{b64_content}" width="{width}" height="{height}" style="object-fit:contain; vertical-align:middle; border-radius:3px;" alt="{bank_clean} Logo" />'
                except Exception as e:
                    print(f"[WARN] Error reading logo file {candidate}: {e}")

    # Fallback SVG shapes
    if "HDFC" in bank_clean:
        return f'''<svg viewBox="0 0 40 40" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle;">
  <rect width="40" height="40" rx="4" fill="#004C8F"/>
  <rect x="8" y="8" width="24" height="24" fill="#ffffff"/>
  <rect x="12" y="12" width="16" height="16" fill="#ED232A"/>
  <rect x="16" y="16" width="8" height="8" fill="#004C8F"/>
</svg>'''
    elif "RBL" in bank_clean:
        return f'''<svg viewBox="0 0 40 40" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle;">
  <rect width="40" height="40" rx="4" fill="#C01D2E"/>
  <path d="M 10,24 L 20,10 L 30,24" fill="none" stroke="#FBB03B" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"/>
  <path d="M 10,30 L 20,16 L 30,30" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linejoin="round" stroke-linecap="round"/>
</svg>'''
    else:
        # Generic monogram for any newly added bank
        letters = bank_clean[:3]
        return f'''<svg viewBox="0 0 40 40" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="vertical-align:middle;">
  <rect width="40" height="40" rx="6" fill="#2563eb"/>
  <text x="20" y="25" fill="#ffffff" font-size="13" font-weight="bold" font-family="sans-serif" text-anchor="middle">{letters}</text>
</svg>'''


# Modern circular refresh icon SVG
REFRESH_ICON_SVG = '''<svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19"/>
</svg>'''


def parse_row_dt(d_val, t_val):
    """Safely parse various date and time formats into datetime."""
    if d_val is None:
        return None
        
    t_str = str(t_val).strip() if t_val else "00:00"
    
    if isinstance(d_val, datetime):
        try:
            time_obj = datetime.strptime(t_str, "%H:%M").time()
            return datetime.combine(d_val.date(), time_obj)
        except ValueError:
            return d_val

    d_str = str(d_val).split(' ')[0].strip()

    formats = (
        "%d/%m/%y %H:%M",
        "%d/%m/%Y %H:%M",
        "%d-%m-%y %H:%M",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%y",
        "%d/%m/%Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(f"{d_str} {t_str}", fmt)
        except ValueError:
            pass
        try:
            return datetime.strptime(d_str, fmt)
        except ValueError:
            pass
    return None


def format_relative_time(dt, now=None):
    """
    Return (friendly_string, time_status).
    time_status: 'fresh' (< 1 hour), 'stale' (>= 12 hours), or 'normal' (1-12 hours).
    """
    if not dt:
        return "Unknown", "normal"
    if now is None:
        now = datetime.now()
    diff = now - dt
    total_seconds = int(diff.total_seconds())

    if total_seconds < 3600:
        time_status = "fresh"
    elif total_seconds >= 12 * 3600:
        time_status = "stale"
    else:
        time_status = "normal"

    if total_seconds < 0 or total_seconds < 60:
        return "Just now", time_status
    
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes} min{'s' if minutes != 1 else ''} ago", time_status
    
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago", time_status
    
    days = hours // 24
    if days == 1:
        return "1 day ago", time_status
    if days < 30:
        return f"{days} days ago", time_status
    
    months = days // 30
    return f"{months} month{'s' if months != 1 else ''} ago", time_status


def format_inr(val, symbol=True):
    """Format number into Indian currency system (e.g. 1,34,48,490.32)."""
    if val is None:
        return "₹ 0.00" if symbol else "0.00"
    neg = val < 0
    val = abs(val)
    s = f"{val:.2f}"
    integer_part, dec_part = s.split(".")
    if len(integer_part) > 3:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        groups.append(last3)
        formatted_int = ",".join(groups)
    else:
        formatted_int = integer_part

    prefix = ("-" if neg else "") + ("₹ " if symbol else "")
    return f"{prefix}{formatted_int}.{dec_part}"


def format_inr_short(val):
    """Convert large amounts to readable Cr / Lakh format."""
    if val is None:
        return "₹ 0"
    abs_v = abs(val)
    sign = "-" if val < 0 else ""
    if abs_v >= 1_00_00_000:
        return f"{sign}₹ {abs_v / 1_00_00_000:.2f} Cr"
    elif abs_v >= 1_00_000:
        return f"{sign}₹ {abs_v / 1_00_000:.2f} L"
    else:
        return format_inr(val)


def load_bank_file(path, bank_name):
    """Load rows from Excel file."""
    if not path.exists():
        print(f"[WARN] File not found: {path}")
        return []

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Balances"] if "Balances" in wb.sheetnames else wb.active
    rows = []

    for r in ws.iter_rows(values_only=True):
        if not any(r):
            continue
        if str(r[0]).strip().lower() == "date":
            continue
        if len(r) >= 6:
            d, t, name, acct_type, acct_num, bal = r[:6]
            if not d or not name or bal is None:
                continue
            dt = parse_row_dt(d, t)
            try:
                bal_num = float(str(bal).replace(",", ""))
            except ValueError:
                bal_num = 0.0

            rows.append({
                "bank": bank_name,
                "date": str(d).strip(),
                "time": str(t).strip() if t else "",
                "dt": dt,
                "account_name": str(name).strip(),
                "account_type": str(acct_type).strip() if acct_type else "Other",
                "account_number": str(acct_num).strip() if acct_num else "-",
                "balance": bal_num
            })
    return rows


def load_transactions(path=HDFC_TRANSACTIONS_FILE):
    """
    Load transactions from HDFC transactions.xlsx and index by (entity, last4_digits).
    Returns dict: { 'ENTITY_LAST4': [ { date, desc, debit, credit, balance }, ... ] }
    """
    if not path.exists():
        return {}

    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb["Transactions"] if "Transactions" in wb.sheetnames else wb.active
        rows = list(ws.iter_rows(values_only=True))
    except Exception as e:
        print(f"[WARN] Error loading transactions from {path}: {e}")
        return {}

    txns_by_account = {}
    for r in rows[1:]:
        if not any(r) or len(r) < 9:
            continue
        f_date, f_time, raw_acc, raw_mask, t_date, desc, debit, credit, bal = r[:9]
        if not raw_acc and not raw_mask:
            continue

        raw_acc_str = str(raw_acc or "")
        ent = re.split(r'[\s\uFFFD\u2013\u2014\-*]+', raw_acc_str)[0].strip() if raw_acc_str else ""
        digits = "".join(re.findall(r'\d+', str(raw_mask or raw_acc_str)))
        last4 = digits[-4:] if len(digits) >= 4 else digits
        if not ent or not last4:
            continue

        key = f"{ent.upper()}_{last4}"
        if key not in txns_by_account:
            txns_by_account[key] = []

        if isinstance(t_date, datetime):
            t_date_str = t_date.strftime("%d-%b-%Y")
        else:
            t_date_str = str(t_date or "").strip()

        try:
            deb_val = float(str(debit).replace(",", "")) if debit is not None else None
        except ValueError:
            deb_val = None

        try:
            cred_val = float(str(credit).replace(",", "")) if credit is not None else None
        except ValueError:
            cred_val = None

        try:
            bal_val = float(str(bal).replace(",", "")) if bal is not None else None
        except ValueError:
            bal_val = None

        txns_by_account[key].append({
            "f_date": str(f_date or ""),
            "f_time": str(f_time or ""),
            "date": t_date_str,
            "desc": str(desc or "").strip(),
            "debit": deb_val,
            "credit": cred_val,
            "balance": bal_val
        })

    # Deduplicate transactions: keep only the latest pull (max f_date + f_time) per account
    for key, txns in txns_by_account.items():
        if not txns: continue
        # Find the latest (f_date, f_time)
        latest_pull = max(txns, key=lambda x: (x["f_date"], x["f_time"]))
        max_f_date, max_f_time = latest_pull["f_date"], latest_pull["f_time"]
        # Keep only txns from this exact pull
        txns_by_account[key] = [t for t in txns if t["f_date"] == max_f_date and t["f_time"] == max_f_time]
    
    return txns_by_account


def get_latest_data(hdfc_path=HDFC_FILE, rbl_path=RBL_FILE, hdfc_txns_path=HDFC_TRANSACTIONS_FILE, rbl_txns_path=RBL_TRANSACTIONS_FILE):
    """
    Extracts only the latest pulled report for each account,
    deduplicates identical records, and computes summaries.
    Also associates recent transactions if available.
    """
    hdfc_rows = load_bank_file(hdfc_path, "HDFC")
    rbl_rows = load_bank_file(rbl_path, "RBL")
    all_rows = hdfc_rows + rbl_rows

    if not all_rows:
        return None

    now = datetime.now()
    txns_data = load_transactions(hdfc_txns_path)
    rbl_txns = load_transactions(rbl_txns_path)
    for k, v in rbl_txns.items():
        if k in txns_data:
            txns_data[k].extend(v)
        else:
            txns_data[k] = v

    # Step 1: Find latest datetime for each (bank, account_name)
    latest_dt_map = {}
    for r in all_rows:
        key = (r["bank"], r["account_name"])
        if r["dt"]:
            if key not in latest_dt_map or r["dt"] > latest_dt_map[key]:
                latest_dt_map[key] = r["dt"]

    # Step 2: Filter rows that match the latest timestamp for their account_name
    latest_rows = [
        r for r in all_rows
        if r["dt"] == latest_dt_map.get((r["bank"], r["account_name"]))
    ]

    # Step 3: Deduplicate (bank, account_name, account_number), retaining last occurrence
    seen = set()
    deduped_rows = []
    for r in reversed(latest_rows):
        key = (r["bank"], r["account_name"], r["account_number"])
        if key not in seen:
            seen.add(key)
            deduped_rows.append(r)
    deduped_rows.reverse()

    # Step 4: Add relative time strings, last4 digits, and associate transactions
    for r in deduped_rows:
        rel_str, time_status = format_relative_time(r["dt"], now)
        r["relative_time"] = rel_str
        r["time_status"] = time_status
        r["iso_time"] = r["dt"].strftime("%Y-%m-%d %H:%M:%S") if r["dt"] else ""
        
        # Extract last 4 digits
        digits = "".join(re.findall(r'\d+', r["account_number"]))
        r["last4"] = digits[-4:] if len(digits) >= 4 else digits
        txn_key = f"{r['account_name'].upper()}_{r['last4']}"
        r["has_txns"] = txn_key in txns_data
        r["txn_count"] = len(txns_data.get(txn_key, []))

    # Sort: Bank (HDFC first, RBL second), then Account Name, then Account Type
    deduped_rows.sort(key=lambda r: (r["bank"], r["account_name"], r["account_type"]))

    hdfc_total = sum(r["balance"] for r in deduped_rows if r["bank"] == "HDFC")
    rbl_total = sum(r["balance"] for r in deduped_rows if r["bank"] == "RBL")

    # Entity-level summary
    entity_summary = {}
    for r in deduped_rows:
        key = (r["bank"], r["account_name"])
        if key not in entity_summary:
            entity_summary[key] = {
                "bank": r["bank"],
                "account_name": r["account_name"],
                "company_name": ENTITY_NAMES.get(r["account_name"], r["account_name"]),
                "last_date": r["date"],
                "last_time": r["time"],
                "dt": r["dt"],
                "relative_time": r["relative_time"],
                "time_status": r["time_status"],
                "iso_time": r["iso_time"],
                "account_count": 0,
                "total_balance": 0.0,
            }
        entity_summary[key]["account_count"] += 1
        entity_summary[key]["total_balance"] += r["balance"]

    sorted_entities = sorted(
        entity_summary.values(),
        key=lambda x: (x["bank"], x["account_name"])
    )

    return {
        "rows": deduped_rows,
        "hdfc_total": hdfc_total,
        "rbl_total": rbl_total,
        "hdfc_count": len([r for r in deduped_rows if r["bank"] == "HDFC"]),
        "rbl_count": len([r for r in deduped_rows if r["bank"] == "RBL"]),
        "hdfc_entities": len([e for e in sorted_entities if e["bank"] == "HDFC"]),
        "rbl_entities": len([e for e in sorted_entities if e["bank"] == "RBL"]),
        "entity_summary": sorted_entities,
        "transactions_map": txns_data,
        "generated_at": now.strftime("%d/%m/%Y %H:%M:%S")
    }


def generate_html_content(data, standalone=True):
    from datetime import datetime
    now = datetime.now()
    """
    Generates compact HTML with:
      - Always-visible Reset button in filter bar.
      - Relative time badges: < 1 hour in GREEN, > 12 hours in RED.
      - Entity drill down: Individual Accounts Statement is hidden until an entity is clicked.
      - Refresh button icon next to latest pulled time.
      - Light/Dark theme toggle (defaulting to dark blueish palette matching run_dashboard.py).
    """
    if not data:
        return "<div class='bbs-container'><p>No balance data found.</p></div>"

    rows = data["rows"]
    hdfc_total = data["hdfc_total"]
    rbl_total = data["rbl_total"]
    # Prepare accounts grouped by entity (bank, entity_name)
    accounts_by_entity = {}
    for r in rows:
        key = (r["bank"], r["account_name"])
        if key not in accounts_by_entity:
            accounts_by_entity[key] = []
        accounts_by_entity[key].append(r)

    # Build Unified Nested Accordion Table Rows
    unified_rows_html = ""
    for ent_idx, ent in enumerate(data["entity_summary"]):
        bank_key = ent["bank"]
        ent_key = ent["account_name"]
        ent_accounts = accounts_by_entity.get((bank_key, ent_key), [])
        ent_id = f"ent_{bank_key}_{ent_key}_{ent_idx}"

        bank_badge = (
            '<span class="bbs-badge bbs-badge-hdfc">HDFC</span>'
            if bank_key == "HDFC"
            else '<span class="bbs-badge bbs-badge-rbl">RBL</span>'
        )
        status_cls = ""
        if ent["time_status"] == "fresh":
            status_cls = " bbs-fresh"
        elif ent["time_status"] == "stale":
            status_cls = " bbs-stale"

        # Entity Top-Level Row
        unified_rows_html += f"""
        <tr class="bbs-entity-row" id="row_{ent_id}" data-bank="{bank_key}" data-entity="{ent_key}" onclick="toggleEntityTree('{ent_id}')" title="Click to expand/collapse accounts for {ent_key}">
          <td style="width: 55px;">{bank_badge}</td>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="bbs-tree-toggle" id="toggle_{ent_id}">▶</span>
              <strong style="font-size: 13.5px;">{ent_key}</strong>
              <span class="bbs-subtext">· {ent['company_name']}</span>
            </div>
          </td>
          <td class="bbs-text-center" style="width: 70px;">
            <span class="bbs-count-pill">{ent['account_count']} a/c</span>
          </td>
          <td style="width: 160px;">
            <div style="display: inline-flex; align-items: center; gap: 5px;">
              <span class="bbs-rel-time{status_cls}" data-iso="{ent['iso_time']}" title="Pulled: {ent['last_date']} {ent['last_time']}">⏱ {ent['relative_time']}</span>
              <button type="button" class="bbs-icon-btn" onclick="onEntityRefreshClicked(event, '{ent_key}', '{bank_key}')" title="Refresh balances for {ent_key}">{REFRESH_ICON_SVG}</button>
            </div>
          </td>
          <td class="bbs-amount-col" style="width: 140px;">{format_inr(ent['total_balance'])}</td>
        </tr>
        """

        # Accounts Drawer Row (Nested immediately underneath entity)
        accounts_sub_rows = ""
        for acc_idx, r in enumerate(ent_accounts):
            acc_id = f"acc_{ent_id}_{acc_idx}"
            company_full = ENTITY_NAMES.get(r["account_name"], "")

            type_badge_cls = "bbs-pill-current"
            t_lower = r["account_type"].lower()
            if "saving" in t_lower:
                type_badge_cls = "bbs-pill-savings"
            elif "term" in t_lower or "deposit" in t_lower:
                type_badge_cls = "bbs-pill-td"
            elif "ppf" in t_lower:
                type_badge_cls = "bbs-pill-ppf"

            acc_status_cls = ""
            if r["time_status"] == "fresh":
                acc_status_cls = " bbs-fresh"
            elif r["time_status"] == "stale":
                acc_status_cls = " bbs-stale"

            last4 = r.get("last4", "")
            txn_key = f"{ent_key.upper()}_{last4}"
            acc_txns = data.get("transactions_map", {}).get(txn_key, [])
            has_txns = len(acc_txns) > 0

            # Format display account number (normalize any star/digit spacing)
            raw_acc_type = r['account_type']
            if "*" in raw_acc_type:
                # Masked account number, e.g. '**** **** **18 94' -> '•••• •••• ••' + last4
                display_acc = f"•••• •••• ••{last4[:2]} {last4[2:]}" if len(last4) == 4 else raw_acc_type
            elif r['account_number'] and r['account_number'] != '-':
                display_acc = r['account_number']
            else:
                display_acc = f"•••• {last4}"

            # Sub-account Row
            accounts_sub_rows += f"""
            <tr class="bbs-account-row" id="row_{acc_id}" data-bank="{bank_key}" data-entity="{ent_key}" data-last4="{last4}" onclick="toggleAccountTxnsTree('{acc_id}', '{ent_key}', '{last4}', '{bank_key}')" title="Click to expand recent transactions">
              <td style="width: 45px; text-align: right; padding-right: 4px;">
                <span class="bbs-tree-toggle-sm" id="toggle_{acc_id}">▶</span>
              </td>
              <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span class="bbs-tree-connector">|_____</span>
                  <span class="bbs-mono" style="font-weight: 600; letter-spacing: 0.5px; font-size: 11px;">{display_acc}</span>
                  <span class="bbs-pill-txns" title="{len(acc_txns)} transactions available">📜 {len(acc_txns)} Txns</span>
                </div>
              </td>
              <td class="bbs-text-center" style="width: 100px;">
                <button type="button" class="bbs-icon-btn bbs-txn-refresh-btn" onclick="event.stopPropagation(); onTransactionRefreshClicked(event, '{ent_key}', '{bank_key}')" title="Refresh transactions for {ent_key} ({display_acc})">
                  {REFRESH_ICON_SVG} <span style="margin-left: 3px; font-weight: 600; font-size: 10px;">Refresh</span>
                </button>
              </td>
              <td style="width: 160px;">
                <span class="bbs-rel-time{acc_status_cls}" data-iso="{r['iso_time']}" title="Pulled: {r['date']} {r['time']}">⏱ {r['relative_time']}</span>
              </td>
              <td class="bbs-amount-col" style="width: 140px; font-weight: 700;">{format_inr(r['balance'])}</td>
            </tr>
            """

            # Transactions Drawer Row (Nested directly underneath sub-account starting with Date, Description, Debit, Credit, Balance table)
            txns_table_content = ""
            if has_txns:
                txns_table_rows = ""
                for t in acc_txns:
                    debit_str = format_inr(t['debit']) if (t.get('debit') is not None) else "-"
                    credit_str = format_inr(t['credit']) if (t.get('credit') is not None) else "-"
                    bal_str = format_inr(t['balance']) if (t.get('balance') is not None) else "-"

                    txns_table_rows += f"""
                    <tr>
                      <td class="bbs-mono" style="white-space: nowrap; width: 95px;">{t.get('date', '-')}</td>
                      <td style="font-size: 11px; word-break: break-word;">{t.get('desc', '-')}</td>
                      <td class="bbs-amount-col bbs-debit-val" style="width: 110px;">{debit_str}</td>
                      <td class="bbs-amount-col bbs-credit-val" style="width: 110px;">{credit_str}</td>
                      <td class="bbs-amount-col bbs-mono" style="font-weight: 600; width: 120px;">{bal_str}</td>
                    </tr>
                    """
                txns_table_content = f"""
                <div class="bbs-txns-table-wrap">
                  <table class="bbs-nested-table">
                    <thead>
                      <tr>
                        <th style="width: 95px;">Date</th>
                        <th>Description</th>
                        <th class="bbs-amount-col" style="width: 110px;">Debit (Dr)</th>
                        <th class="bbs-amount-col" style="width: 110px;">Credit (Cr)</th>
                        <th class="bbs-amount-col" style="width: 120px;">Balance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {txns_table_rows}
                    </tbody>
                  </table>
                </div>
                """
            else:
                txns_table_content = f"""
                <div class="bbs-empty-txns">
                  <span>Transactions unavailable for <strong>{ent_key} ({display_acc})</strong>.</span>
                  <div style="margin-top: 4px; font-size: 11px; color: var(--bbs-text-muted);">
                    Click <strong>Refresh</strong> on the account line to pull the latest transaction statement.
                  </div>
                </div>
                """

            accounts_sub_rows += f"""
            <tr class="bbs-txns-drawer-row" id="drawer_{acc_id}" style="display: none;">
              <td colspan="5" style="padding: 0 0 6px 42px; background: rgba(0, 0, 0, 0.08);">
                <div class="bbs-txns-container" style="margin: 4px 10px 8px 10px;">
                  {txns_table_content}
                </div>
              </td>
            </tr>
            """

        unified_rows_html += f"""
        <tr class="bbs-entity-drawer-row" id="drawer_{ent_id}" style="display: none;">
          <td colspan="5" style="padding: 0; background: rgba(0, 0, 0, 0.04);">
            <table class="bbs-nested-table" style="width: 100%; border-collapse: collapse;">
              <tbody>
                {accounts_sub_rows}
              </tbody>
            </table>
          </td>
        </tr>
        """

    # Scoped CSS styles matching bank_dashboard.py
    css_styles = """
    /* Bank Balance Summary Scoped Styles - Unified Accordion Hierarchy */
    :root, .bbs-root[data-theme="dark"], body[data-theme="dark"] {
      --bbs-bg-primary: #0f172a;
      --bbs-bg-secondary: #1e293b;
      --bbs-card-bg: #1e293b;
      --bbs-card-hover: #27354a;
      --bbs-accent-blue: #3b82f6;
      --bbs-accent-hover: #2563eb;
      --bbs-accent-green: #10b981;
      --bbs-accent-red: #ef4444;
      --bbs-text-main: #f8fafc;
      --bbs-text-muted: #94a3b8;
      --bbs-border: #334155;
      --bbs-border-light: #243247;
      --bbs-table-hover: #26354d;
      --bbs-pill-bg: #28374d;
      --bbs-pill-text: #cbd5e1;
      --bbs-hdfc-bg: rgba(59, 130, 246, 0.18);
      --bbs-hdfc-text: #60a5fa;
      --bbs-hdfc-border: #2563eb;
      --bbs-rbl-bg: rgba(239, 68, 68, 0.18);
      --bbs-rbl-text: #f87171;
      --bbs-rbl-border: #dc2626;
      --bbs-time-bg: rgba(255, 255, 255, 0.08);
      --bbs-active-ring: #38bdf8;
      --bbs-stale-bg: rgba(239, 68, 68, 0.22);
      --bbs-stale-text: #f87171;
      --bbs-stale-border: #ef4444;
      --bbs-fresh-bg: rgba(16, 185, 129, 0.22);
      --bbs-fresh-text: #34d399;
      --bbs-fresh-border: #10b981;
      --bbs-nested-bg: rgba(15, 23, 42, 0.55);
      --bbs-txns-bg: rgba(30, 41, 59, 0.7);
    }

    .bbs-root[data-theme="light"], body[data-theme="light"] {
      --bbs-bg-primary: #f8fafc;
      --bbs-bg-secondary: #ffffff;
      --bbs-card-bg: #ffffff;
      --bbs-card-hover: #f1f5f9;
      --bbs-accent-blue: #2563eb;
      --bbs-accent-hover: #1d4ed8;
      --bbs-accent-green: #059669;
      --bbs-accent-red: #dc2626;
      --bbs-text-main: #0f172a;
      --bbs-text-muted: #64748b;
      --bbs-border: #cbd5e1;
      --bbs-border-light: #e2e8f0;
      --bbs-table-hover: #f1f5f9;
      --bbs-pill-bg: #e2e8f0;
      --bbs-pill-text: #334155;
      --bbs-hdfc-bg: #e0f2fe;
      --bbs-hdfc-text: #0284c7;
      --bbs-hdfc-border: #38bdf8;
      --bbs-rbl-bg: #fee2e2;
      --bbs-rbl-text: #dc2626;
      --bbs-rbl-border: #f87171;
      --bbs-time-bg: #f1f5f9;
      --bbs-active-ring: #2563eb;
      --bbs-stale-bg: #fee2e2;
      --bbs-stale-text: #b91c1c;
      --bbs-stale-border: #f87171;
      --bbs-fresh-bg: #d1fae5;
      --bbs-fresh-text: #065f46;
      --bbs-fresh-border: #34d399;
      --bbs-nested-bg: #f8fafc;
      --bbs-txns-bg: #ffffff;
    }

    body {
      background-color: var(--bbs-bg-primary);
      color: var(--bbs-text-main);
      transition: background-color 0.2s ease, color 0.2s ease;
    }

    .bbs-root {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: var(--bbs-text-main);
      background-color: var(--bbs-bg-primary);
      line-height: 1.35;
      font-size: 13px;
      margin: 0 auto;
      max-width: 1440px;
      padding: 4px;
      transition: background-color 0.2s ease, color 0.2s ease;
    }
    .bbs-root * {
      box-sizing: border-box;
    }

    /* Drill-down Bank Cards */
    .bbs-bank-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 8px;
    }
    .bbs-bank-card {
      background: var(--bbs-bg-secondary);
      border: 1px solid var(--bbs-border);
      border-radius: 8px;
      padding: 9px 13px;
      cursor: pointer;
      position: relative;
      transition: all 0.15s ease;
      user-select: none;
    }
    .bbs-bank-card:hover {
      border-color: var(--bbs-accent-blue);
      background: var(--bbs-card-hover);
    }
    .bbs-bank-card.active {
      border-color: var(--bbs-active-ring);
      box-shadow: 0 0 0 2px var(--bbs-active-ring);
    }
    .bbs-bank-card-hdfc {
      border-left: 4px solid var(--bbs-hdfc-border);
    }
    .bbs-bank-card-rbl {
      border-left: 4px solid var(--bbs-rbl-border);
    }
    .bbs-card-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }
    .bbs-bank-title {
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.2px;
      color: var(--bbs-text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .bbs-bank-logo {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 4px;
      flex-shrink: 0;
    }
    .bbs-bank-logo svg {
      width: 100%;
      height: 100%;
      display: block;
    }
    .bbs-bank-val {
      font-size: 19px;
      font-weight: 700;
      font-feature-settings: "tnum";
      color: var(--bbs-text-main);
    }
    .bbs-bank-meta {
      font-size: 11px;
      color: var(--bbs-text-muted);
      display: flex;
      justify-content: space-between;
      margin-top: 3px;
    }

    /* Drilldown Filter Bar with Persistent Reset */
    .bbs-filter-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--bbs-bg-secondary);
      border: 1px solid var(--bbs-border);
      border-radius: 8px;
      padding: 6px 12px;
      margin-bottom: 8px;
      font-size: 12px;
      flex-wrap: wrap;
    }
    .bbs-filter-label {
      font-weight: 700;
      color: var(--bbs-text-muted);
      text-transform: uppercase;
      font-size: 10.5px;
      letter-spacing: 0.4px;
    }
    .bbs-chip {
      background: var(--bbs-pill-bg);
      color: var(--bbs-text-main);
      border: 1px solid var(--bbs-border);
      border-radius: 5px;
      padding: 3px 9px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .bbs-chip:hover {
      border-color: var(--bbs-accent-blue);
      color: var(--bbs-accent-blue);
    }
    .bbs-chip.active {
      background: var(--bbs-accent-blue);
      border-color: var(--bbs-accent-blue);
      color: #ffffff;
    }

    /* Persistent Reset Button */
    .bbs-reset-btn {
      background: rgba(239, 68, 68, 0.12);
      border: 1px solid var(--bbs-border);
      color: var(--bbs-text-main);
      padding: 3px 10px;
      border-radius: 5px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s;
    }
    .bbs-reset-btn:hover {
      background: var(--bbs-accent-red);
      color: #ffffff;
      border-color: var(--bbs-accent-red);
    }

    .bbs-stale-legend {
      font-size: 11px;
      color: var(--bbs-text-muted);
      margin-left: auto;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* Unified Accordion Table Box */
    .bbs-section-box {
      background: var(--bbs-bg-secondary);
      border: 1px solid var(--bbs-border);
      border-radius: 8px;
      overflow: hidden;
      width: 100%;
    }
    .bbs-section-head {
      padding: 7px 12px;
      border-bottom: 1px solid var(--bbs-border);
      font-size: 11.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: var(--bbs-text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(0, 0, 0, 0.06);
    }
    .bbs-table-wrap {
      overflow-x: auto;
      max-height: 560px;
      overflow-y: auto;
    }
    table.bbs-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 12px;
    }
    table.bbs-table th {
      background: var(--bbs-bg-secondary);
      color: var(--bbs-text-muted);
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      padding: 7px 10px;
      border-bottom: 1px solid var(--bbs-border);
      position: sticky;
      top: 0;
      z-index: 2;
    }
    table.bbs-table td {
      padding: 6px 10px;
      border-bottom: 1px solid var(--bbs-border-light);
      vertical-align: middle;
    }
    table.bbs-table tr.bbs-entity-row {
      cursor: pointer;
      user-select: none;
      transition: background-color 0.15s ease;
    }
    table.bbs-table tr.bbs-entity-row:hover {
      background-color: var(--bbs-table-hover);
    }
    table.bbs-table tr.bbs-entity-row.bbs-expanded {
      background-color: rgba(56, 189, 248, 0.1) !important;
      border-bottom: 1px solid var(--bbs-accent-blue);
    }

    /* Tree Chevrons & Markers */
    .bbs-tree-toggle {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 16px;
      height: 16px;
      font-size: 10.5px;
      color: var(--bbs-accent-blue);
      transition: transform 0.18s ease;
      cursor: pointer;
    }
    .bbs-tree-toggle.open {
      transform: rotate(90deg);
    }
    .bbs-tree-toggle-sm {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 14px;
      height: 14px;
      font-size: 9.5px;
      color: var(--bbs-text-muted);
      transition: transform 0.18s ease;
      cursor: pointer;
    }
    .bbs-tree-toggle-sm.open {
      transform: rotate(90deg);
      color: var(--bbs-accent-blue);
    }
    .bbs-tree-connector {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      color: var(--bbs-text-muted);
      font-size: 11px;
      user-select: none;
      opacity: 0.75;
    }

    /* Nested Sub-Table */
    table.bbs-nested-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11.5px;
    }
    table.bbs-nested-table td {
      padding: 5px 10px;
      border-bottom: 1px solid var(--bbs-border-light);
      vertical-align: middle;
    }
    table.bbs-nested-table th {
      padding: 5px 8px;
      font-size: 10px;
      font-weight: 700;
      color: var(--bbs-text-muted);
      border-bottom: 1px solid var(--bbs-border);
      background: rgba(0, 0, 0, 0.08);
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }
    table.bbs-nested-table tr.bbs-account-row {
      cursor: pointer;
      user-select: none;
      background: var(--bbs-nested-bg);
      transition: background-color 0.15s ease;
    }
    table.bbs-nested-table tr.bbs-account-row:hover {
      background-color: var(--bbs-table-hover);
    }
    table.bbs-nested-table tr.bbs-account-row.bbs-expanded {
      background-color: rgba(56, 189, 248, 0.14) !important;
    }

    /* Transactions Container Inside Drawer */
    .bbs-txns-container {
      margin: 4px 10px 8px 10px;
      background: var(--bbs-txns-bg);
      border: 1px solid var(--bbs-border);
      border-radius: 6px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      animation: bbsSlideDown 0.15s ease-out;
    }
    @keyframes bbsSlideDown {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .bbs-txns-header-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 10px;
      background: rgba(0, 0, 0, 0.1);
      border-bottom: 1px solid var(--bbs-border);
    }
    .bbs-txns-table-wrap {
      max-height: 240px;
      overflow-y: auto;
      overflow-x: auto;
    }
    .bbs-txn-refresh-btn {
      padding: 2px 7px;
      font-size: 10.5px;
      font-weight: 600;
      border-radius: 4px;
      background: rgba(59, 130, 246, 0.15);
    }
    .bbs-txn-refresh-btn:hover {
      background: var(--bbs-accent-blue);
      color: #ffffff;
    }
    .bbs-debit-val {
      color: #ef4444;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }
    .bbs-credit-val {
      color: #10b981;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }
    .bbs-empty-txns {
      padding: 14px 12px;
      text-align: center;
      color: var(--bbs-text-muted);
      font-size: 11.5px;
    }

    .bbs-amount-col {
      text-align: right;
      font-variant-numeric: tabular-nums;
      font-weight: 600;
      color: var(--bbs-text-main);
    }
    th.bbs-amount-col {
      text-align: right;
    }
    .bbs-text-center {
      text-align: center;
    }
    th.bbs-text-center {
      text-align: center;
    }
    .bbs-mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 11px;
      color: var(--bbs-text-muted);
    }

    /* Badges & Pills */
    .bbs-badge {
      display: inline-block;
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 9.5px;
      font-weight: 700;
      letter-spacing: 0.3px;
    }
    .bbs-badge-hdfc {
      background: var(--bbs-hdfc-bg);
      color: var(--bbs-hdfc-text);
      border: 1px solid var(--bbs-hdfc-border);
    }
    .bbs-badge-rbl {
      background: var(--bbs-rbl-bg);
      color: var(--bbs-rbl-text);
      border: 1px solid var(--bbs-rbl-border);
    }

    .bbs-pill {
      display: inline-block;
      padding: 1px 6px;
      border-radius: 10px;
      font-size: 10.5px;
      font-weight: 500;
      white-space: nowrap;
    }
    .bbs-pill-current {
      background: var(--bbs-pill-bg);
      color: var(--bbs-pill-text);
    }
    .bbs-pill-savings {
      background: rgba(16, 185, 129, 0.18);
      color: var(--bbs-accent-green);
    }
    .bbs-pill-td {
      background: rgba(245, 158, 11, 0.18);
      color: #f59e0b;
    }
    .bbs-pill-ppf {
      background: rgba(168, 85, 247, 0.18);
      color: #c084fc;
    }

    .bbs-count-pill {
      background: var(--bbs-pill-bg);
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 10px;
      color: var(--bbs-text-muted);
    }
    .bbs-pill-txns {
      background: rgba(59, 130, 246, 0.16);
      color: var(--bbs-accent-blue);
      border: 1px solid rgba(59, 130, 246, 0.3);
      font-size: 9.5px;
      font-weight: 600;
      padding: 1px 5px;
      border-radius: 4px;
    }

    /* Relative Time Tag with <1hr Green and >12hr Red Alert */
    .bbs-rel-time {
      display: inline-block;
      background: var(--bbs-time-bg);
      border: 1px solid transparent;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10.5px;
      font-weight: 500;
      color: var(--bbs-text-muted);
      white-space: nowrap;
    }
    .bbs-rel-time.bbs-stale {
      background: var(--bbs-stale-bg) !important;
      color: var(--bbs-stale-text) !important;
      border: 1px solid var(--bbs-stale-border) !important;
      font-weight: 700 !important;
    }
    .bbs-rel-time.bbs-fresh {
      background: var(--bbs-fresh-bg) !important;
      color: var(--bbs-fresh-text) !important;
      border: 1px solid var(--bbs-fresh-border) !important;
      font-weight: 700 !important;
    }

    /* Refresh Icon Button next to time */
    .bbs-icon-btn {
      background: rgba(59, 130, 246, 0.12);
      border: 1px solid var(--bbs-border);
      color: var(--bbs-accent-blue);
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 11px;
      cursor: pointer;
      line-height: 1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s ease;
    }
    .bbs-icon-btn:hover {
      background: var(--bbs-accent-blue);
      color: #ffffff;
      border-color: var(--bbs-accent-blue);
      transform: scale(1.06);
    }

    .bbs-subtext {
      font-size: 11px;
      color: var(--bbs-text-muted);
      font-weight: normal;
    }
    """

    transactions_json = json.dumps(data.get("transactions_map", {}))

    # Interactive JS script for unified accordion tree hierarchy
    js_script = f"""
    const allTransactionsData = {transactions_json};
    let currentBankFilter = 'ALL';

    function initTheme() {{
      const savedTheme = localStorage.getItem('bank_summary_theme') || 'dark';
      setTheme(savedTheme);
      updateRelativeTimes();
    }}

    function toggleTheme() {{
      const root = document.querySelector('.bbs-root');
      const current = (root && root.getAttribute('data-theme')) || 'dark';
      const next = current === 'dark' ? 'light' : 'dark';
      setTheme(next);
    }}

    function setTheme(theme) {{
      document.body.setAttribute('data-theme', theme);
      const roots = document.querySelectorAll('.bbs-root');
      roots.forEach(r => r.setAttribute('data-theme', theme));
      try {{
        localStorage.setItem('bank_summary_theme', theme);
      }} catch(e) {{}}
    }}

    // Toggle Entity Row -> expands/collapses account drawer underneath
    function toggleEntityTree(entId) {{
      const drawer = document.getElementById('drawer_' + entId);
      const toggle = document.getElementById('toggle_' + entId);
      const row = document.getElementById('row_' + entId);
      if (!drawer) return;

      const isHidden = (drawer.style.display === 'none' || drawer.style.display === '');
      drawer.style.display = isHidden ? 'table-row' : 'none';
      if (toggle) toggle.classList.toggle('open', isHidden);
      if (row) row.classList.toggle('bbs-expanded', isHidden);
      
      if (!isHidden) {{
          drawer.querySelectorAll('.bbs-txns-drawer-row').forEach(row => {{ row.style.display = 'none'; }});
          drawer.querySelectorAll('.bbs-account-row').forEach(row => {{ row.classList.remove('bbs-expanded'); }});
      }}
    }}
    }}

    // Toggle Sub-Account Row -> expands/collapses transaction drawer underneath
    function toggleAccountTxnsTree(accId, entity, last4, bank) {{
      const drawer = document.getElementById('drawer_' + accId);
      const toggle = document.getElementById('toggle_' + accId);
      const row = document.getElementById('row_' + accId);
      if (!drawer) return;

      const isHidden = (drawer.style.display === 'none' || drawer.style.display === '');
      drawer.style.display = isHidden ? 'table-row' : 'none';
      if (toggle) toggle.classList.toggle('open', isHidden);
      if (row) row.classList.toggle('bbs-expanded', isHidden);
    }}

    // Filter by Bank
    function filterByBank(bank) {{
      currentBankFilter = (currentBankFilter === bank) ? 'ALL' : bank;
      applyFilters();
    }}

    // Reset Filters -> collapses all open drawers and restores view
    function resetFilters() {{
      currentBankFilter = 'ALL';
      collapseAllDrawers();
      applyFilters();
    }}

    function collapseAllDrawers() {{
      document.querySelectorAll('.bbs-entity-drawer-row').forEach(dr => {{
        dr.style.display = 'none';
      }});
      document.querySelectorAll('.bbs-txns-drawer-row').forEach(dr => {{
        dr.style.display = 'none';
      }});
      document.querySelectorAll('.bbs-tree-toggle').forEach(tg => {{
        tg.classList.remove('open');
      }});
      document.querySelectorAll('.bbs-tree-toggle-sm').forEach(tg => {{
        tg.classList.remove('open');
      }});
      document.querySelectorAll('.bbs-entity-row').forEach(r => {{
        r.classList.remove('bbs-expanded');
      }});
      document.querySelectorAll('.bbs-account-row').forEach(r => {{
        r.classList.remove('bbs-expanded');
      }});
    }}

    function onEntityRefreshClicked(e, entity, bank) {{
      e.stopPropagation();
      if (typeof window.quickRefreshEntity === 'function') {{
        window.quickRefreshEntity(entity, bank);
      }} else {{
        alert(`Refresh triggered for ${{bank}} - ${{entity}}`);
      }}
    }}

    function onBankRefreshClicked(e, bank) {{
      e.stopPropagation();
      if (typeof window.quickRefreshBank === 'function') {{
        window.quickRefreshBank(bank);
      }} else {{
        alert(`Refresh triggered for all ${{bank}} accounts`);
      }}
    }}

    function onTransactionRefreshClicked(e, entity, bank) {{
      e.stopPropagation();
      if (typeof window.quickRefreshEntityTransactions === 'function') {{
        window.quickRefreshEntityTransactions(entity, bank);
      }} else if (typeof window.quickRefreshEntity === 'function') {{
        window.quickRefreshEntity(entity, bank);
      }} else {{
        alert(`Refresh transactions triggered for ${{entity}} (${{bank}})`);
      }}
    }}

    function applyFilters() {{
      // 1. Bank card active states
      const hdfcCard = document.getElementById('bbsCardHDFC');
      const rblCard = document.getElementById('bbsCardRBL');
      if (hdfcCard) hdfcCard.classList.toggle('active', currentBankFilter === 'HDFC');
      if (rblCard) rblCard.classList.toggle('active', currentBankFilter === 'RBL');

      // 2. Bank chips
      document.querySelectorAll('.bbs-bank-chip').forEach(c => {{
        c.classList.toggle('active', c.getAttribute('data-filter-bank') === currentBankFilter);
      }});

      // 3. Filter Entity Rows
      let visibleEntities = 0;
      document.querySelectorAll('.bbs-entity-row').forEach(row => {{
        const rowBank = row.getAttribute('data-bank');
        const bankMatch = (currentBankFilter === 'ALL' || rowBank === currentBankFilter);
        row.style.display = bankMatch ? '' : 'none';
        
        // Hide corresponding drawer if parent entity is filtered out
        const entId = row.id.replace('row_', '');
        const drawer = document.getElementById('drawer_' + entId);
        if (drawer && !bankMatch) {{
          drawer.style.display = 'none';
          const toggle = document.getElementById('toggle_' + entId);
          if (toggle) toggle.classList.remove('open');
          row.classList.remove('bbs-expanded');
        }}

        if (bankMatch) visibleEntities++;
      }});

      // 4. Update Status Bar
      const countEl = document.getElementById('bbsFilteredCount');
      if (countEl) {{
        if (currentBankFilter !== 'ALL') {{
          countEl.innerHTML = `Showing <strong>${{currentBankFilter}}</strong> entities (${{visibleEntities}} entities) · <em>Click any entity to view accounts & transactions</em>`;
        }} else {{
          countEl.innerHTML = `All entities (${{visibleEntities}}) · <em>Click any entity to view accounts & transactions inline</em>`;
        }}
      }}
    }}

    function updateRelativeTimes() {{
      const now = new Date();
      document.querySelectorAll('.bbs-rel-time[data-iso]').forEach(el => {{
        const iso = el.getAttribute('data-iso');
        if (!iso) return;
        const dt = new Date(iso.replace(' ', 'T'));
        if (isNaN(dt.getTime())) return;
        const diffSec = Math.floor((now - dt) / 1000);
        let str = 'Just now';

        const isFresh = (diffSec < 3600);
        const isStale = (diffSec >= 12 * 3600);

        if (diffSec >= 60) {{
          const mins = Math.floor(diffSec / 60);
          if (mins < 60) {{
            str = `${{mins}} min${{mins !== 1 ? 's' : ''}} ago`;
          }} else {{
            const hours = Math.floor(mins / 60);
            if (hours < 24) {{
              
              str = `${{hours}} hour${{hours !== 1 ? 's' : ''}} ago`;
            }} else {{
              const days = Math.floor(hours / 24);
              str = days === 1 ? '1 day ago' : `${{days}} days ago`;
            }}
          }}
        }}
        el.innerText = '⏱ ' + str;

        el.classList.toggle('bbs-fresh', isFresh);
        el.classList.toggle('bbs-stale', isStale);
      }});
    }}

    if (document.readyState === 'loading') {{
      document.addEventListener('DOMContentLoaded', initTheme);
    }} else {{
      initTheme();
    }}
    """

    # Dynamic Bank Logos (auto-loads custom image if present, else fallback vector SVG)
    hdfc_logo_rendered = get_bank_logo('HDFC', 22, 22)
    rbl_logo_rendered = get_bank_logo('RBL', 22, 22)

    # Combined widget HTML snippet with unified single-table accordion tree
    snippet_html = f"""<!-- START OF BANK BALANCE SUMMARY COMPONENT -->
<div class="bbs-root" data-theme="dark">
  <style>
{css_styles}
  </style>

  <!-- Bank-Wise Totals (Clickable Drill Down with Icon Refresh & Logos) -->
  <div class="bbs-bank-grid">
    <div class="bbs-bank-card bbs-bank-card-hdfc" id="bbsCardHDFC" onclick="filterByBank('HDFC')" title="Click to filter HDFC accounts">
      <div class="bbs-card-top">
        <span class="bbs-bank-title">
          <span class="bbs-bank-logo">{hdfc_logo_rendered}</span>
          <span>HDFC Bank Total</span>
          <button type="button" class="bbs-icon-btn" onclick="onBankRefreshClicked(event, 'HDFC')" title="Refresh all HDFC accounts">{REFRESH_ICON_SVG}</button>
        </span>
        <span class="bbs-badge bbs-badge-hdfc">HDFC BANK</span>
      </div>
      <div class="bbs-bank-val">{format_inr(hdfc_total)}</div>
      <div class="bbs-bank-meta">
        <span>{data['hdfc_count']} accounts across {data['hdfc_entities']} entities</span>
        <span><strong>{format_inr_short(hdfc_total)}</strong></span>
      </div>
    </div>

    <div class="bbs-bank-card bbs-bank-card-rbl" id="bbsCardRBL" onclick="filterByBank('RBL')" title="Click to filter RBL accounts">
      <div class="bbs-card-top">
        <span class="bbs-bank-title">
          <span class="bbs-bank-logo">{rbl_logo_rendered}</span>
          <span>RBL Bank Total</span>
          <button type="button" class="bbs-icon-btn" onclick="onBankRefreshClicked(event, 'RBL')" title="Refresh all RBL accounts">{REFRESH_ICON_SVG}</button>
        </span>
        <span class="bbs-badge bbs-badge-rbl">RBL BANK</span>
      </div>
      <div class="bbs-bank-val">{format_inr(rbl_total)}</div>
      <div class="bbs-bank-meta">
        <span>{data['rbl_count']} accounts across {data['rbl_entities']} entities</span>
        <span><strong>{format_inr_short(rbl_total)}</strong></span>
      </div>
    </div>
  </div>

  <!-- Drill-Down Filter Bar with Always-Visible Reset -->
  <div class="bbs-filter-bar">
    <span class="bbs-filter-label">Filter:</span>
    <span class="bbs-chip bbs-bank-chip active" data-filter-bank="ALL" onclick="filterByBank('ALL')">All Banks ({len(rows)})</span>
    <span class="bbs-chip bbs-bank-chip" data-filter-bank="HDFC" onclick="filterByBank('HDFC')">HDFC ({data['hdfc_count']})</span>
    <span class="bbs-chip bbs-bank-chip" data-filter-bank="RBL" onclick="filterByBank('RBL')">RBL ({data['rbl_count']})</span>

    <!-- Always Visible Reset Button -->
    <button id="bbsResetBtn" class="bbs-reset-btn" onclick="resetFilters()" title="Collapse all open drawers and reset filters">
      🔄 Reset Filters
    </button>

    <span style="border-left: 1px solid var(--bbs-border); height: 14px; margin: 0 4px;"></span>
    <span id="bbsFilteredCount" class="bbs-subtext">Click any entity below to drill down into its accounts & transactions</span>

    <div class="bbs-stale-legend">
      <span class="bbs-rel-time bbs-fresh" style="padding: 1px 5px; font-size: 9.5px;">&lt; 1 hr</span>
      <span style="margin-right: 6px;">Fresh</span>
      <span class="bbs-rel-time bbs-stale" style="padding: 1px 5px; font-size: 9.5px;">&gt; 12 hrs</span>
      <span>Stale</span>
    </div>
  </div>

  <!-- Unified Tree Hierarchy Section (Single Accordion Table) -->
  <div class="bbs-section-box" id="bbsUnifiedSectionBox">
    <div class="bbs-section-head">
      <span>Entity &amp; Account Breakdown (Click entity / account to expand)</span>
      <span class="bbs-subtext">{len(data['entity_summary'])} Entities · {len(rows)} Accounts</span>
    </div>
    <div class="bbs-table-wrap">
      <table class="bbs-table">
        <thead>
          <tr>
            <th style="width: 55px;">Bank</th>
            <th>Entity / Account</th>
            <th class="bbs-text-center" style="width: 70px;">A/C</th>
            <th style="width: 160px;">Latest Pulled</th>
            <th class="bbs-amount-col" style="width: 140px;">Balance</th>
          </tr>
        </thead>
        <tbody>
          {unified_rows_html}
        </tbody>
      </table>
    </div>
  </div>

  <script>
{js_script}
  </script>
</div>
<!-- END OF BANK BALANCE SUMMARY COMPONENT -->
"""

    if not standalone:
        return snippet_html

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bank Balances Summary (HDFC & RBL)</title>
  <style>
    body {{
      margin: 0;
      padding: 10px;
    }}
  </style>
</head>
<body data-theme="dark">
{snippet_html}
</body>
</html>
"""


def main():
    print("=" * 60)
    print("  Consolidated Bank Balances Summary Generator")
    print("  Extracting latest pull only (Compact & Drill-Down view)...")
    print("=" * 60)

    data = get_latest_data()
    if not data:
        print("[ERROR] No data found or could not read Excel files.")
        return

    print(f"\n🏦 BANK-WISE TOTALS:")
    print(f"   ├─ HDFC Bank Subtotal : {format_inr(data['hdfc_total']):>18} ({data['hdfc_count']} accounts)")
    print(f"   └─ RBL Bank Subtotal  : {format_inr(data['rbl_total']):>18} ({data['rbl_count']} accounts)")

    print("\n🏢 Entities (Latest Report Pulled):")
    for ent in data["entity_summary"]:
        status_flag = ""
        if ent["time_status"] == "fresh":
            status_flag = " [FRESH <1h]"
        elif ent["time_status"] == "stale":
            status_flag = " [STALE >12h]"
        print(f"   [{ent['bank']:<4}] {ent['account_name']:<5} {ent['company_name'][:20]:<21} {ent['relative_time']:<14}{status_flag:<15} {format_inr(ent['total_balance']):>18}")

    full_html = generate_html_content(data, standalone=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"\n✅ Standalone HTML report saved to:")
    print(f"   file:///{str(OUTPUT_HTML).replace(chr(92), '/')}")

    snippet_html = generate_html_content(data, standalone=False)
    with open(OUTPUT_SNIPPET, "w", encoding="utf-8") as f:
        f.write(snippet_html)
    print(f"✅ Embeddable HTML snippet saved to:")
    print(f"   file:///{str(OUTPUT_SNIPPET).replace(chr(92), '/')}")

    # Automatically open in browser when executed
    print("\n🌐 Opening report in default web browser...")
    try:
        webbrowser.open(OUTPUT_HTML.as_uri())
    except Exception as e:
        print(f"[WARN] Could not automatically open browser: {e}")

    # If executed by double-clicking in Explorer, keep window open
    if sys.stdin and sys.stdin.isatty():
        try:
            input("\nPress Enter to exit...")
        except Exception:
            pass


if __name__ == "__main__":
    main()
