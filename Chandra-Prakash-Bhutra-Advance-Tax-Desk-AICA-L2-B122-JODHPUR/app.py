"""Advance Tax Desk - Streamlit app.

Run:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
import html
import io
import os
import re
import subprocess
import sys
import time
import zipfile
from dataclasses import replace
from datetime import date
from urllib.parse import quote

import altair as alt
import pandas as pd
import streamlit as st

from advtax import ai, cg_import, form26as_read, notes, portal_26as, storage, tb_import
from advtax.engine import AGE_BANDS, CONSTITUTIONS, ClientInputs, compute, fmt_inr, load_rules
from advtax.projection import project_business, project_presumptive

st.set_page_config(page_title="Advance Tax Desk", page_icon="🧾", layout="wide",
                   initial_sidebar_state="expanded")

RULES = load_rules()
START, END = date.fromisoformat(RULES["start"]), date.fromisoformat(RULES["end"])
TODAY = min(max(date.today(), START), END)

PAGES = ["Dashboard", "Client"]
NEW_CLIENT = "(new client)"

CSS = """
<style>
html, body, [data-testid="stAppViewContainer"] {font-feature-settings: "tnum" 1, "lnum" 1;}
.block-container {padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1360px;}
h4 {font-size: 1.02rem !important; font-weight: 650 !important; color: #1B365D;}

/* sidebar */
[data-testid="stSidebar"] {background: #F4F6F9; border-right: 1px solid #D9DFE7;}
.atd-brand {font-size: 1.05rem; font-weight: 700; color: #1B365D; letter-spacing: .01em;}
.atd-brand small {display: block; font-size: .72rem; font-weight: 500; color: #5F6B7A; letter-spacing: .02em;}
.atd-label {font-size: .68rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
    color: #6B7686; margin: 14px 0 4px 0;}
[data-testid="stSidebar"] [role="radiogroup"] {gap: 2px;}
[data-testid="stSidebar"] [role="radiogroup"] label {width: 100%; padding: 7px 10px; border-radius: 4px;
    border-left: 3px solid transparent; margin: 0;}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child:not([data-testid]),
[data-testid="stSidebar"] [role="radiogroup"] label > div > div:first-child:not([data-testid]) {display: none;}
[data-testid="stSidebar"] [role="radiogroup"], [data-testid="stSidebar"] .stRadio > div {width: 100%;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background: #E9EDF3;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),
[data-testid="stSidebar"] [role="radiogroup"] label[data-selected="true"] {background: #E3E9F2;
    border-left-color: #1B365D;}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p,
[data-testid="stSidebar"] [role="radiogroup"] label[data-selected="true"] p {font-weight: 650; color: #1B365D;}

/* title bar */
.atd-bar {display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap;
    border-bottom: 2px solid #1B365D; padding: 0 0 10px 0; margin-bottom: 18px;}
.atd-bar .page {font-size: 1.45rem; font-weight: 700; color: #1B365D; line-height: 1.2;}
.atd-bar .crumb {font-size: .74rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
    color: #6B7686;}
.atd-bar .meta {display: flex; gap: 22px; font-size: .78rem; color: #5F6B7A; text-align: right;}
.atd-bar .meta b {display: block; font-size: .95rem; color: #1D2733; font-weight: 650;}

/* figures */
[data-testid="stMetric"] {background: #FFFFFF; border: 1px solid #D9DFE7; border-top: 3px solid #1B365D;
    border-radius: 4px; padding: 10px 14px;}
[data-testid="stMetricLabel"] p {font-size: .7rem; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; color: #6B7686;}
[data-testid="stMetricValue"] {font-size: 1.3rem; font-weight: 650; color: #1D2733;}

/* position summary */
.atd-pos {display: grid; grid-template-columns: 1.5fr 1.2fr 1fr; gap: 0; background: #FFFFFF;
    border: 1px solid #D9DFE7; border-left: 5px solid #1B365D; border-radius: 4px; margin: 4px 0 14px 0;}
.atd-pos > div {padding: 14px 18px; border-right: 1px solid #E6EAF0;}
.atd-pos > div:last-child {border-right: 0;}
.atd-pos .lbl {font-size: .68rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; color: #6B7686;}
.atd-pos .name {font-size: 1.05rem; font-weight: 650; color: #1D2733; margin-top: 2px;}
.atd-pos .amt {font-size: 1.7rem; font-weight: 700; color: #1D2733; line-height: 1.25;}
.atd-pos .sub {font-size: .82rem; color: #5F6B7A; margin-top: 2px;}
.atd-pos.due {border-left-color: #B7791F;}
.atd-pos.urgent {border-left-color: #B42318;}
.atd-pos.clear {border-left-color: #1E7B4F;}

/* badges */
.atd-badge {display: inline-block; font-size: .7rem; font-weight: 700; letter-spacing: .04em;
    text-transform: uppercase; padding: 2px 8px; border-radius: 3px; border: 1px solid; white-space: nowrap;}
.b-due {color: #8A5A0B; background: #FDF4E3; border-color: #EBCB8B;}
.b-urgent {color: #9B1C12; background: #FCEBE9; border-color: #F0B4AD;}
.b-ok {color: #17633F; background: #E8F4EE; border-color: #A9D5BF;}
.b-muted {color: #5F6B7A; background: #F1F3F6; border-color: #D3D9E2;}

/* statement tables */
.atd-wrap {border: 1px solid #D9DFE7; border-radius: 4px; overflow: auto; background: #FFFFFF;}
table.atd {width: 100%; border-collapse: collapse; font-size: .86rem; margin: 0;}
table.atd th, table.atd td {border-left: 0; border-right: 0; border-bottom: 0;}
table.atd th {position: sticky; top: 0; background: #1B365D; color: #FFFFFF; font-weight: 600; font-size: .72rem;
    letter-spacing: .05em; text-transform: uppercase; text-align: left; padding: 8px 12px; white-space: nowrap;}
table.atd td {padding: 7px 12px; border-top: 1px solid #E9EDF2; color: #1D2733; white-space: nowrap;}
table.atd tbody tr:nth-child(even) td {background: #FAFBFC;}
table.atd tbody tr:hover td {background: #F0F4F9;}
table.atd .num {text-align: right;}
table.atd tr.total td {font-weight: 700; border-top: 1px solid #1B365D; border-bottom: 1px solid #1B365D;
    background: #F4F6F9 !important;}
table.atd td.wrapok {white-space: normal;}

.atd-step {font-size: .68rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
    color: #6B7686; margin: 4px 0 4px 0;}
.stButton button, .stDownloadButton button, .stLinkButton a {border-radius: 4px;}
[data-testid="stExpander"] details {border-radius: 4px;}
#MainMenu, footer {visibility: hidden;}
</style>
"""

BADGES = {"Due": "b-due", "Missed / short": "b-urgent", "Covered": "b-ok", "Paid in full": "b-ok",
          "Not liable": "b-muted", "Covered, interest arisen": "b-due"}


class Raw(str):
    """HTML that is already safe; everything else going into a table is escaped."""


def badge(text: str, cls: str | None = None) -> Raw:
    return Raw(f'<span class="atd-badge {cls or BADGES.get(text, "b-muted")}">{html.escape(text)}</span>')


def html_table(headers: list, rows: list, num_cols: tuple = (), total_rows: tuple = (),
               max_height: int | None = None) -> None:
    """Statement-style table: amounts right-aligned, totals ruled off."""
    def cell(v, i, tag="td"):
        text = v if isinstance(v, Raw) else html.escape(str(v))
        return f'<{tag}{" class=num" if i in num_cols else ""}>{text}</{tag}>'
    head = "".join(cell(h, i, "th") for i, h in enumerate(headers))
    body = "".join(f'<tr{" class=total" if n in total_rows else ""}>'
                   + "".join(cell(v, i) for i, v in enumerate(r)) + "</tr>" for n, r in enumerate(rows))
    style = f' style="max-height:{max_height}px"' if max_height else ""
    st.markdown(f'<div class="atd-wrap"{style}><table class="atd"><thead><tr>{head}</tr></thead>'
                f'<tbody>{body}</tbody></table></div>', unsafe_allow_html=True)


def wa_number(mobile: str) -> str:
    """Mobile number in the form WhatsApp links need (country code, digits only). Empty if it is not usable."""
    digits = re.sub(r"\D", "", mobile or "")
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        return "91" + digits
    return digits if 11 <= len(digits) <= 15 else ""


def wa_link(mobile: str, message: str) -> str:
    return f"https://wa.me/{wa_number(mobile)}?text={quote(message)}"


def goto(page: str) -> None:
    st.session_state["nav"] = page


def next_instalment(as_on: date):
    """Next advance tax due date on or after the given date, from the rules file."""
    for due_s, _ in RULES["advance_tax"]["instalments"]:
        due = date.fromisoformat(due_s)
        if due >= as_on:
            return due
    return None


def step(text: str) -> None:
    st.markdown(f'<div class="atd-step">{html.escape(text)}</div>', unsafe_allow_html=True)


MODE_LABELS = {"Upload trial balance": "Trial balance", "Enter year-to-date figures": "Figures to date",
               "Enter full-year figure directly": "Full-year figure", "Presumptive (% of turnover)": "Presumptive"}
MODES = ["Upload trial balance", "Enter year-to-date figures", "Enter full-year figure directly",
         "Presumptive (% of turnover)"]

DEFAULTS = {
    "f_name": "", "f_constitution": "Individual", "f_age_band": "below60", "f_resident": True,
    "f_regime": "auto", "f_mode": MODES[0], "f_books_date": TODAY, "f_as_on": TODAY,
    "f_rec_income": 0.0, "f_rec_expense": 0.0, "f_oneoff_income": 0.0, "f_oneoff_expense": 0.0,
    "f_opening_stock": 0.0, "f_closing_stock": 0.0, "f_add_backs": 0.0, "f_less_deductions": 0.0,
    "f_growth": 0.0, "f_direct_business": 0.0, "f_turnover": 0.0, "f_presumptive_rate": 6.0,
    "f_salary": 0.0, "f_hp_rent": 0.0, "f_hp_muni": 0.0, "f_hp_lo_int": 0.0, "f_hp_so_int": 0.0,
    "f_stcg_eq": 0.0, "f_ltcg_eq": 0.0, "f_ltcg_ot": 0.0, "f_stcg_ot": 0.0,
    "f_int": 0.0, "f_div": 0.0, "f_misc": 0.0, "f_ded_old": 0.0, "f_tds": 0.0, "f26_pan": "", "f_mobile": "",
}


def payments_frame(pays: list) -> pd.DataFrame:
    """Challan table with fixed column types, so an empty list still edits as date + number."""
    return pd.DataFrame({
        "Date": pd.Series(pd.to_datetime([p["date"] for p in pays]), dtype="datetime64[ns]"),
        "Amount": pd.Series([float(p["amount"]) for p in pays], dtype="float64"),
    })


def init_state() -> None:
    for k, v in DEFAULTS.items():
        st.session_state.setdefault(k, v)
    st.session_state.setdefault("payments_base", payments_frame([]))
    st.session_state.setdefault("pay_ver", 0)
    st.session_state.setdefault("tb_ver", 0)
    st.session_state.setdefault("up_ver", 0)
    st.session_state.setdefault("ai_text", "")


def reset_form() -> None:
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    st.session_state["payments_base"] = payments_frame([])
    st.session_state["pay_ver"] += 1
    st.session_state["ai_text"] = ""
    st.session_state["up_ver"] += 1  # clears the file uploader
    for key in ("tb_table", "tb_sig", "tb_saved", "tb_current", "tb_pl_ledgers"):
        st.session_state.pop(key, None)


def ledger_frame(ledgers: list) -> pd.DataFrame:
    df = pd.DataFrame(ledgers, columns=["ledger", "group", "net", "type", "review", "one_off"])
    return df.astype({"ledger": str, "group": str, "net": float, "type": str, "review": bool, "one_off": bool})


def attach_saved_trial_balance(con, name: str, working: dict) -> None:
    """If the client was worked from a trial balance, bring back the file and the ledger classification."""
    s = st.session_state
    if working.get("mode") != MODES[0]:
        return
    tb = storage.get_trial_balance(con, name)
    if not tb:
        return
    s["f_mode"], s["tb_saved"] = MODES[0], tb
    s["tb_table"], s["tb_sig"] = ledger_frame(tb["ledgers"]), f"saved|{name}|{tb['saved_at']}"
    s["tb_ver"] += 1


def load_client(name: str) -> None:
    con = storage.connect()
    rec = storage.get_client(con, name)
    if not rec:
        return
    reset_form()
    apply_record(rec["inputs"], rec["working"])
    attach_saved_trial_balance(con, name, rec["working"])


def load_estimate(estimate_id: int) -> None:
    con = storage.connect()
    rec = storage.get_estimate(con, estimate_id)
    if not rec:
        return
    reset_form()
    apply_record(rec["inputs"], rec["working"])
    st.session_state["f_as_on"] = min(max(date.fromisoformat(rec["as_on"]), START), END)
    attach_saved_trial_balance(con, rec["client_name"], rec["working"])


def apply_record(i: dict, w: dict) -> None:
    s = st.session_state
    s["f_name"], s["f_constitution"] = i["name"], i["constitution"]
    s["f_age_band"], s["f_resident"], s["f_regime"] = i["age_band"], i["resident"], i["regime"]
    s["f_salary"], s["f_hp_rent"], s["f_hp_muni"] = i["salary_gross"], i["hp_let_out_rent"], i["hp_municipal_tax"]
    s["f_hp_lo_int"], s["f_hp_so_int"] = i["hp_let_out_interest"], i["hp_self_occupied_interest"]
    s["f_stcg_eq"], s["f_ltcg_eq"] = i["stcg_equity"], i["ltcg_equity"]
    s["f_ltcg_ot"], s["f_stcg_ot"] = i["ltcg_other"], i["stcg_other"]
    s["f_int"], s["f_div"], s["f_misc"] = i["other_interest"], i["other_dividend"], i["other_misc"]
    s["f_ded_old"], s["f_tds"] = i["deductions_old"], i["tds_tcs"]
    mode = w.get("mode", MODES[2])
    s["f_mode"] = MODES[1] if mode == MODES[0] else mode
    for key in ("f_rec_income", "f_rec_expense", "f_oneoff_income", "f_oneoff_expense", "f_opening_stock",
                "f_closing_stock", "f_add_backs", "f_less_deductions", "f_growth", "f_turnover",
                "f_presumptive_rate"):
        if key in w:
            s[key] = float(w[key])
    s["f_mobile"] = str(w.get("mobile", ""))
    s["f_direct_business"] = float(w.get("f_direct_business", i["business_income"]))
    if w.get("f_books_date"):
        s["f_books_date"] = date.fromisoformat(w["f_books_date"])
    pays = i.get("payments", [])
    s["payments_base"] = payments_frame(pays)
    s["pay_ver"] += 1


def money(label: str, key: str, help_text: str | None = None) -> None:
    st.number_input(label, key=key, step=1000.0, format="%.0f", help=help_text)


# ---------------------------------------------------------------- business
def business_section() -> tuple[float, dict]:
    s = st.session_state
    st.radio("Business figures from", MODES, key="f_mode", horizontal=True, format_func=MODE_LABELS.get)
    mode, working = s["f_mode"], {"mode": s["f_mode"]}
    if mode != MODES[0]:
        s.pop("tb_current", None)

    if mode == MODES[2]:
        money("Projected taxable business income for the full year", "f_direct_business")
        working["f_direct_business"] = s["f_direct_business"]
        return s["f_direct_business"], working

    c1, _ = st.columns(2)
    c1.date_input("Books are updated up to", key="f_books_date", min_value=START, max_value=END, format="DD/MM/YYYY")
    adjust = st.expander("Adjustments (optional)")
    adjust.number_input("Expected change in remaining months (%)", key="f_growth", step=5.0,
                        help="0 means the rest of the year runs at the same rate as the year to date. "
                             "Use +20 for a stronger season ahead, -20 for a weaker one.")
    working.update({"f_books_date": s["f_books_date"].isoformat(), "f_growth": s["f_growth"]})

    if mode == MODES[3]:
        c1, c2 = st.columns(2)
        with c1:
            money("Turnover / gross receipts up to that date", "f_turnover")
        c2.number_input("Presumptive rate (%)", key="f_presumptive_rate", step=1.0,
                        help="6% for digital receipts and 8% for others in business; 50% for profession.")
        res = project_presumptive(s["f_turnover"], s["f_presumptive_rate"], START, s["f_books_date"], END, s["f_growth"])
        st.info(f"Projected turnover Rs {fmt_inr(res['projected_turnover'])} at {res['rate_pct']:g}% "
                f"= business income Rs {fmt_inr(res['projected_business_income'])}")
        working.update({"f_turnover": s["f_turnover"], "f_presumptive_rate": s["f_presumptive_rate"]})
        return res["projected_business_income"], working

    totals = None
    if mode == MODES[0]:
        st.caption("Any software works: Tally, Busy, Zoho Books, QuickBooks, Marg, or the template in "
                   "demo_clients/templates/trial_balance_template.xlsx. Export the trial balance ledger-wise "
                   "(with group names if possible) as Excel or CSV.")
        up = st.file_uploader("Trial balance file", type=["xlsx", "xls", "csv"], key=f"tb_upload_{s['up_ver']}")
        saved = s.get("tb_saved")
        if up is None and saved is None:
            st.warning("Upload a trial balance, or switch to another option above.")
            return 0.0, working
        if up is not None:
            data = up.getvalue()
            fid = hashlib.md5(data).hexdigest()
            with st.expander("Columns matched automatically - open to change"):
                sheets = tb_import.sheet_names(data, up.name)
                sheet = st.selectbox("Sheet", sheets) if len(sheets) > 1 else 0
                raw = tb_import.read_raw(data, up.name, sheet)
                hdr = st.number_input("Header row (row that has the column titles)", min_value=1,
                                      max_value=max(1, len(raw)), value=tb_import.detect_header_row(raw) + 1,
                                      key=f"hdr_{fid}_{sheet}")
                table = tb_import.build_table(raw, int(hdr) - 1)
                guess = tb_import.guess_columns(table)
                cols, none = list(table.columns), "(none)"

                def pick(label, key, col):
                    options = cols if key == "ledger" else [none] + cols
                    default = guess.get(key)
                    idx = options.index(default) if default in options else 0
                    val = col.selectbox(label, options, index=idx, key=f"map_{key}_{fid}_{hdr}")
                    return None if val == none else val

                m = st.columns(6)
                mapping = {"ledger": pick("Ledger name", "ledger", m[0]), "group": pick("Group / type", "group", m[1]),
                           "debit": pick("Debit", "debit", m[2]), "credit": pick("Credit", "credit", m[3]),
                           "balance": pick("Single balance", "balance", m[4]), "drcr": pick("Dr/Cr column", "drcr", m[5])}
            try:
                norm = tb_import.normalise(table, mapping)
            except (ValueError, KeyError) as exc:
                st.error(str(exc))
                return 0.0, working
            sig = f"{fid}|{sheet}|{hdr}|{sorted(mapping.items())}"
            if s.get("tb_sig") != sig or "tb_table" not in s:
                s["tb_sig"], s["tb_table"] = sig, tb_import.classify(norm)
                s["tb_ver"] += 1
            source = {"filename": up.name, "data": data,
                      "meta": {"sheet": sheet, "header_row": int(hdr), "mapping": mapping}}
        else:
            sig = f"saved|{s['f_name']}|{saved['saved_at']}"
            if s.get("tb_sig") != sig or "tb_table" not in s:
                s["tb_sig"], s["tb_table"] = sig, ledger_frame(saved["ledgers"])
                s["tb_ver"] += 1
            st.info(f"Using the saved trial balance: {saved['filename']} (saved on {saved['saved_at'][:10]}). "
                    "Upload a new file above to replace it.")
            st.download_button("Download the saved trial balance file", saved["data"], file_name=saved["filename"])
            source = {"filename": saved["filename"], "data": saved["data"], "meta": saved["meta"]}
        st.markdown("**Check the ledger classification** (only Income, Expense and Opening Stock are used)")
        edited = st.data_editor(
            s["tb_table"], key=f"tb_editor_{s['tb_ver']}", hide_index=True, width="stretch", height=320,
            disabled=["ledger", "group", "net", "review"],
            column_config={
                "ledger": "Ledger", "group": "Group",
                "net": st.column_config.NumberColumn("Net (Dr + / Cr -)", format="%.2f"),
                "type": st.column_config.SelectboxColumn("Type", options=tb_import.TYPES, required=True),
                "review": st.column_config.CheckboxColumn("Guessed", help="No group found; classified from the name. Please check."),
                "one_off": st.column_config.CheckboxColumn("One-off", help="Tick items that should not be annualised."),
            })
        totals = tb_import.summarise(edited)
        s["tb_current"] = {**source, "ledgers": edited.to_dict("records")}
        a, b, c = st.columns(3)
        a.metric("Ledgers read", totals["ledgers"])
        b.metric("Guessed, please check", totals["needs_review"])
        c.metric("Trial balance difference", fmt_inr(totals["difference"]))
        key_ = s.get("api_key", "")
        if key_ and totals["needs_review"]:
            if st.button("Ask AI to classify the guessed ledgers"):
                todo = edited[edited["review"]][["ledger", "group"]].to_dict("records")
                try:
                    result = ai.classify_ledgers(todo, key_, s.get("ai_model", ai.DEFAULT_MODEL), provider=s.get("ai_provider"))
                    tbl = edited.copy()
                    hit = tbl["ledger"].isin(result.keys()) & tbl["review"]
                    tbl.loc[hit, "type"] = tbl.loc[hit, "ledger"].map(result)
                    s["tb_table"], s["tb_ver"] = tbl, s["tb_ver"] + 1
                    st.rerun()
                except Exception as exc:  # noqa: BLE001 - show any API problem to the user
                    st.error(f"AI call failed: {exc}")
        st.session_state["tb_pl_ledgers"] = [
            {"ledger": r.ledger, "type": r.type, "amount": round(abs(r.net))}
            for r in edited[edited["type"].isin(["Income", "Expense"])].itertuples()]
        money("Closing stock on the books date", "f_closing_stock")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            money("Regular income to date (sales etc.)", "f_rec_income")
            money("One-off income to date", "f_oneoff_income")
        with c2:
            money("Regular expenses to date (incl. purchases)", "f_rec_expense")
            money("One-off expenses to date", "f_oneoff_expense")
        with c3:
            money("Opening stock", "f_opening_stock")
            money("Closing stock on the books date", "f_closing_stock")
        totals = {"recurring_income": s["f_rec_income"], "recurring_expense": s["f_rec_expense"],
                  "one_off_income": s["f_oneoff_income"], "one_off_expense": s["f_oneoff_expense"],
                  "opening_stock": s["f_opening_stock"]}

    c1, c2 = adjust.columns(2)
    with c1:
        money("Add: disallowances / items not deductible (full year)", "f_add_backs",
              "Book depreciation, personal expenses, donations, penalties and similar.")
    with c2:
        money("Less: further deductions (full year)", "f_less_deductions",
              "Tax depreciation, allowable partner remuneration and interest not yet booked, and similar.")
    proj = project_business(totals["recurring_income"], totals["recurring_expense"], totals["one_off_income"],
                            totals["one_off_expense"], totals["opening_stock"], s["f_closing_stock"], START,
                            s["f_books_date"], END, s["f_add_backs"], s["f_less_deductions"], s["f_growth"])
    p = st.columns(4)
    p[0].metric("Profit to date", fmt_inr(proj["ytd_profit"]))
    p[1].metric("Projected for remaining days", fmt_inr(proj["projected_remaining_profit"]))
    p[2].metric("Projected book profit", fmt_inr(proj["projected_book_profit"]))
    p[3].metric("Projected business income", fmt_inr(proj["projected_business_income"]))
    st.caption(f"{proj['days_done']} of {proj['days_total']} days covered by the books.")
    working.update({"f_rec_income": totals["recurring_income"], "f_rec_expense": totals["recurring_expense"],
                    "f_oneoff_income": totals["one_off_income"], "f_oneoff_expense": totals["one_off_expense"],
                    "f_opening_stock": totals["opening_stock"], "f_closing_stock": s["f_closing_stock"],
                    "f_add_backs": s["f_add_backs"], "f_less_deductions": s["f_less_deductions"]})
    return proj["projected_business_income"], working


# ---------------------------------------------------------------- Form 26AS
def start_26as(pan: str, folder, status_path) -> None:
    """Start the browser robot as a separate program, so the app stays usable while the user signs in."""
    portal_26as.Status(status_path).say("Starting the browser...")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [sys.executable, "-m", "advtax.portal_26as", "--out", str(folder), "--status", str(status_path),
         "--tax-year", RULES["tax_year"]],
        cwd=str(storage.ROOT), env=dict(os.environ, ADVTAX_PAN=pan), creationflags=flags)


def robot_running(status_path) -> bool:
    data = portal_26as.read_status(status_path)
    try:
        fresh = time.time() - status_path.stat().st_mtime < 20 * 60
    except OSError:
        return False
    return bool(data) and data.get("state") == "running" and fresh


def show_26as_progress(folder, status_path) -> None:
    data = portal_26as.read_status(status_path)
    if data and data.get("steps"):
        state = data.get("state")
        last = data["steps"][-1]["message"]
        if state == "done":
            st.success(last)
        elif state in ("failed", "closed"):
            st.warning(last)
        elif robot_running(status_path):
            st.info(last)
        with st.expander("Steps so far"):
            for row in data["steps"]:
                st.text(f'{row["time"]}  {row["message"]}')
    files = portal_26as.downloaded_files(folder)
    if files:
        st.markdown("**Saved for this client**")
        for n, f in enumerate(files[:5]):
            c = st.columns([3, 1.4, 1], vertical_alignment="center")
            c[0].write(f.name)
            c[1].caption(f"{date.fromtimestamp(f.stat().st_mtime).strftime('%d %b %Y')} | {max(1, f.stat().st_size // 1024)} KB")
            c[2].download_button("Download", f.read_bytes(), file_name=f.name, key=f"f26_dl_{n}_{f.name}", width="stretch")
        st.caption(f"Folder: {folder}")


def apply_tds(amount: float) -> None:
    st.session_state["f_tds"] = float(amount)
    st.session_state["tds_applied"] = True


def read_26as_box(folder) -> None:
    """Read a 26AS file (downloaded above or uploaded) and offer its TDS / TCS total for tab 4."""
    s = st.session_state
    step("Read the TDS / TCS from a 26AS file")
    with st.container(border=True):
        st.caption("Form 26AS now shows only TDS and TCS. Advance tax challans are in the AIS, so enter those in tab 4 "
                   "from the challans. PDF or text file; a password-protected file must be unlocked first.")
        saved = [f for f in portal_26as.downloaded_files(folder) if f.suffix.lower() in (".pdf", ".txt")]
        c = st.columns(2)
        pick = c[0].selectbox("Saved file for this client", ["(none)"] + [f.name for f in saved], key=f"f26_pick_{folder.name}")
        up = c[1].file_uploader("Or upload a 26AS file", type=["pdf", "txt"], key=f"f26_upload_{s['up_ver']}")
        if s.pop("tds_applied", False):
            st.success("TDS / TCS in tab 4 is filled from the 26AS. Add any TDS expected in the rest of the year.")
        if up is not None:
            name, data = up.name, up.getvalue()
        elif pick != "(none)":
            chosen = next((f for f in saved if f.name == pick), None)
            if chosen is None:
                return
            name, data = chosen.name, chosen.read_bytes()
        else:
            return
        try:
            found = form26as_read.read(data, name)
        except ValueError as exc:
            st.error(str(exc))
            return
        if not found["rows"]:
            st.warning("No deductor lines could be read from this file. Enter the TDS / TCS in tab 4 by hand.")
            return
        html_table(["Deductor / collector", "TAN", "Type", "Amount paid / credited", "Tax deducted", "Tax deposited"],
                   [[r["name"], r["tan"], r["kind"], fmt_inr(r["amount_paid"]), fmt_inr(r["tax_deducted"]),
                     fmt_inr(r["tax_deposited"])] for r in found["rows"]]
                   + [["Total", "", "", "", fmt_inr(found["total_deducted"]), fmt_inr(found["total_deposited"])]],
                   num_cols=(3, 4, 5), total_rows=(len(found["rows"]),), max_height=320)
        remarks = []
        if found["pan"]:
            typed = s.get("f26_pan", "").strip().upper()
            remarks.append(f"PAN in the file: {found['pan']}" + (" (differs from the PAN typed above)" if typed and typed != found["pan"] else "") + ".")
        expected = portal_26as.assessment_year(RULES["tax_year"])
        if found["year"]:
            remarks.append(f"Year in the file: {found['year']}" + ("" if found["year"][:7] == expected else f" (expected {expected})") + ".")
        if found["lines_not_read"]:
            remarks.append(f"{found['lines_not_read']} lines with a TAN could not be read; compare the total with the file.")
        remarks.append("Entries shown against a PAN instead of a TAN (TDS on property or rent) are not read; add them by hand.")
        st.caption(" ".join(remarks))
        st.button(f"Use Rs {fmt_inr(found['total_deposited'])} as TDS / TCS", type="primary", on_click=apply_tds,
                  args=(found["total_deposited"],), key="f26_apply")


def form_26as_section() -> None:
    s = st.session_state
    step("Form 26AS from the income-tax portal")
    with st.container(border=True):
        st.caption("Opens the e-filing portal in a browser window, fills the PAN and, once you have signed in, goes to "
                   "Form 26AS on TRACES and saves it in this client's folder. You type the password and any OTP "
                   "yourself in the portal's own page; this app never sees or stores them.")
        name = s["f_name"].strip()
        c = st.columns([1.2, 1.2, 2.2], vertical_alignment="bottom")
        pan = c[0].text_input("Client PAN", key="f26_pan", max_chars=10, placeholder="Type the 10-character PAN").strip().upper()
        folder = storage.data_dir() / "26AS" / portal_26as.safe_folder_name(name)
        status_path = folder / "_status.json"
        running = robot_running(status_path)
        ready = bool(name) and portal_26as.valid_pan(pan) and not running
        if c[1].button("Download Form 26AS", type="primary", disabled=not ready, width="stretch"):
            start_26as(pan, folder, status_path)
            st.rerun()
        if not name:
            c[2].caption("Enter the client name in tab 1 first.")
        elif not pan:
            c[2].caption("Type the PAN and press Enter; the button then becomes active.")
        elif not portal_26as.valid_pan(pan):
            c[2].caption("A PAN looks like ABCDE1234F.")
        elif running:
            c[2].caption("The browser is open. Sign in there; progress shows below.")
        else:
            c[2].caption("The PAN is used only to fill the login box. It is not saved.")
        st.fragment(run_every=3 if running else None)(show_26as_progress)(folder, status_path)
    read_26as_box(folder)


# ------------------------------------------------------------- client page
def apply_capital_gains(buckets: dict) -> None:
    s = st.session_state
    s["f_stcg_eq"], s["f_ltcg_eq"] = float(buckets["stcg_equity"]), float(buckets["ltcg_equity"])
    s["f_ltcg_ot"], s["f_stcg_ot"] = float(buckets["ltcg_other"]), float(buckets["stcg_other"])
    s["cg_applied"] = True


def cg_import_box() -> None:
    """Capital gains statement from any broker or app -> the four capital gains boxes above."""
    s = st.session_state
    st.markdown("**Import from a broker, mutual fund or app statement**")
    st.caption("Any transaction-wise capital gains or tax P&L sheet works (Excel or CSV): one row per sale, with the "
               "name and either the gain, or the buy and sell values. Buy and sell dates decide short or long term. "
               "A blank sheet to fill is in demo_clients/templates/capital_gains_template.xlsx.")
    up = st.file_uploader("Capital gains statement", type=["xlsx", "xls", "csv"], key=f"cg_upload_{s['up_ver']}")
    if s.pop("cg_applied", False):
        st.success("The four capital gains boxes above are filled from the statement. Add gains expected later in the year by hand.")
    if up is None:
        return
    data = up.getvalue()
    fid = hashlib.md5(data).hexdigest()
    try:
        sheets = cg_import.sheet_names(data, up.name)
        sheet = st.selectbox("Sheet", sheets, key=f"cg_sheet_{fid}") if len(sheets) > 1 else 0
        raw = cg_import.read_raw(data, up.name, sheet)
    except Exception as exc:  # noqa: BLE001 - unreadable or damaged file
        st.error(f"Could not read this file: {exc}")
        return
    if raw.empty:
        st.warning("This sheet is empty.")
        return
    with st.expander("Columns matched automatically - open to change"):
        c = st.columns([1, 2, 3])
        hdr = c[0].number_input("Header row", min_value=1, max_value=max(1, len(raw)),
                                value=cg_import.detect_header_row(raw) + 1, key=f"cg_hdr_{fid}_{sheet}",
                                help="The row that has the column titles.")
        default_class = c[1].selectbox("Rows with no asset type are", cg_import.CLASSES[:3], key=f"cg_def_{fid}")
        table = cg_import.build_table(raw, int(hdr) - 1)
        guess, cols, none = cg_import.guess_columns(table), list(table.columns), "(none)"
        mapping, grid = {}, st.columns(5) + st.columns(5)
        for n, (key, (label, required)) in enumerate(cg_import.FIELDS.items()):
            options = cols if required else [none] + cols
            default = guess.get(key)
            val = grid[n].selectbox(label, options, index=options.index(default) if default in options else 0,
                                    key=f"cg_map_{key}_{fid}_{hdr}")
            mapping[key] = None if val == none else val
    try:
        rows = cg_import.normalise(table, mapping, default_class)
    except (ValueError, KeyError, TypeError) as exc:
        st.error(str(exc))
        return
    if rows.empty:
        st.warning("No sale rows were found with these columns. Check the header row and the column matching.")
        return
    sig = f"{fid}|{sheet}|{hdr}|{default_class}|{sorted(mapping.items(), key=str)}"
    if s.get("cg_sig") != sig:
        s["cg_sig"], s["cg_ver"] = sig, s.get("cg_ver", 0) + 1
    st.markdown("**Check the rows** (change the class or the term where needed)")
    edited = st.data_editor(
        rows, key=f"cg_editor_{s.get('cg_ver', 0)}", hide_index=True, width="stretch", height=300,
        disabled=["asset", "buy_date", "sell_date", "days", "cost", "sale", "gain", "check"],
        column_config={
            "asset": "Asset", "buy_date": st.column_config.DateColumn("Bought", format="DD-MM-YYYY"),
            "sell_date": st.column_config.DateColumn("Sold", format="DD-MM-YYYY"),
            "days": st.column_config.NumberColumn("Days held", format="%d"),
            "cost": st.column_config.NumberColumn("Cost", format="%.0f"),
            "sale": st.column_config.NumberColumn("Sale", format="%.0f"),
            "gain": st.column_config.NumberColumn("Gain / loss", format="%.0f"),
            "class": st.column_config.SelectboxColumn("Class", options=cg_import.CLASSES, required=True),
            "term": st.column_config.SelectboxColumn("Term", options=cg_import.TERMS, required=True),
            "check": st.column_config.CheckboxColumn("Check", help="No dates and no short / long column; taken as short-term."),
        })
    total = cg_import.summarise(edited)
    after = cg_import.set_off(total["buckets"])
    html_table(["Head", "As per statement", "After set-off of losses"],
               [[label, fmt_inr(total["buckets"][k]), fmt_inr(after["buckets"][k])] for k, label in cg_import.BUCKETS.items()]
               + [["Total", fmt_inr(sum(total["buckets"].values())), fmt_inr(sum(after["buckets"].values()))]],
               num_cols=(1, 2), total_rows=(4,))
    notes_ = [f"{total['rows']} sale rows read."]
    if total["to_check"]:
        notes_.append(f"{total['to_check']} rows have no dates and no short / long column; they are taken as short-term.")
    if total["ignored"]:
        notes_.append(f"Rs {fmt_inr(total['ignored'])} from intraday, F&O and similar rows is left out; it is business income.")
    if after["short_term_loss_carried"] or after["long_term_loss_carried"]:
        notes_.append(f"Loss carried forward, not set off against other income: short-term Rs "
                      f"{fmt_inr(after['short_term_loss_carried'])}, long-term Rs {fmt_inr(after['long_term_loss_carried'])}.")
    notes_.append("Long-term means held for more than 12 months for listed shares and equity funds, and more than 24 "
                  "months for other assets; change the term for listed bonds, gold ETFs and similar where 12 months "
                  "applies. Not adjusted: cost as on 31 Jan 2018 for old equity holdings, indexation on land or "
                  "building bought before 23 Jul 2024, exemptions and brought-forward losses.")
    st.caption(" ".join(notes_))
    st.button("Use these figures", type="primary", on_click=apply_capital_gains, args=(after["buckets"],),
              key=f"cg_apply_{fid}")


def other_income_section(firm: bool) -> None:
    s = st.session_state
    if not firm:
        with st.expander("Salary", expanded=s["f_salary"] > 0):
            money("Gross salary for the full year (after exempt allowances)", "f_salary",
                  "Standard deduction is applied automatically as per the regime.")
    with st.expander("House property", expanded=(s["f_hp_rent"] + s["f_hp_so_int"]) > 0):
        h = st.columns(4)
        with h[0]:
            money("Annual rent from let-out property", "f_hp_rent")
        with h[1]:
            money("Municipal taxes paid", "f_hp_muni")
        with h[2]:
            money("Interest on loan: let-out property", "f_hp_lo_int")
        with h[3]:
            money("Interest on loan: self-occupied house", "f_hp_so_int")
        st.caption("30% standard deduction on let-out property is applied automatically.")
    with st.expander("Capital gains (type the figures, or import a broker / app statement)", expanded=(s["f_stcg_eq"] + s["f_ltcg_eq"] + s["f_ltcg_ot"] + s["f_stcg_ot"]) > 0):
        g = st.columns(4)
        with g[0]:
            money("Short-term: listed shares / equity funds (20%)", "f_stcg_eq")
        with g[1]:
            money("Long-term: listed shares / equity funds (12.5% above Rs 1.25 lakh)", "f_ltcg_eq")
        with g[2]:
            money("Long-term: property and other assets (12.5%)", "f_ltcg_ot")
        with g[3]:
            money("Short-term: other assets (slab rate)", "f_stcg_ot")
        st.caption("Enter gains already made plus gains expected in the rest of the year, net of exemptions claimed.")
        cg_import_box()
    with st.expander("Other sources", expanded=(s["f_int"] + s["f_div"] + s["f_misc"]) > 0):
        o = st.columns(3)
        with o[0]:
            money("Interest (bank, FD, loans)", "f_int")
        with o[1]:
            money("Dividend", "f_div")
        with o[2]:
            money("Any other income", "f_misc")
    if not firm:
        with st.expander("Deductions (old regime only)", expanded=s["f_ded_old"] > 0):
            money("Total deductions: life insurance, PPF, health insurance, NPS and similar", "f_ded_old")


def pick_client() -> None:
    choice = st.session_state.get("open_choice")
    if choice and choice != NEW_CLIENT:
        load_client(choice)
    else:
        reset_form()


def new_client() -> None:
    reset_form()
    st.session_state["open_choice"] = NEW_CLIENT


def client_page() -> None:
    s = st.session_state
    con = storage.connect()
    names = [c["name"] for c in storage.list_clients(con)]
    if s.get("open_choice") not in [NEW_CLIENT] + names:
        s["open_choice"] = NEW_CLIENT
    top = st.columns([4, 1], vertical_alignment="bottom")
    top[0].selectbox("Client", [NEW_CLIENT] + names, key="open_choice", on_change=pick_client,
                     help="Pick a saved client to open it. The saved figures and trial balance come back.")
    top[1].button("New client", on_click=new_client, width="stretch")

    firm = s["f_constitution"] in ("Firm", "LLP")
    tab_client, tab_business, tab_other, tab_paid, tab_26as = st.tabs(
        ["1  Client", "2  Business", "3  Other income", "4  Taxes paid", "5  Form 26AS"])
    with tab_client:
        step("Who is the client")
        c = st.columns(4)
        c[0].text_input("Client name", key="f_name", placeholder="Name as it should appear on the note")
        c[1].selectbox("Constitution", CONSTITUTIONS, key="f_constitution")
        firm = s["f_constitution"] in ("Firm", "LLP")
        if s["f_constitution"] == "Individual":
            c[2].selectbox("Age", list(AGE_BANDS), format_func=AGE_BANDS.get, key="f_age_band")
        if not firm:
            c[3].selectbox("Tax regime", ["auto", "new", "old"], key="f_regime",
                           format_func={"auto": "Whichever is lower", "new": "New regime", "old": "Old regime"}.get)
            st.checkbox("Resident in India", key="f_resident")
        m = st.columns(4)
        m[0].text_input("Mobile number (WhatsApp)", key="f_mobile", placeholder="10-digit mobile", max_chars=16,
                        help="Optional. With a number, 'Open in WhatsApp' opens this client's chat directly.")
        if s["f_mobile"].strip() and not wa_number(s["f_mobile"]):
            m[1].caption("This does not look like a mobile number; WhatsApp will ask you to pick the contact.")
        st.caption("Fill tabs 1 to 4 from left to right. The result below updates as you type. Tab 5 downloads Form 26AS.")

    with tab_business:
        step("Profit from the books, projected to the full year")
        business_income, working = business_section()
    working["mobile"] = s["f_mobile"].strip()

    with tab_other:
        step("Income under the other heads, for the full year")
        other_income_section(firm)

    with tab_paid:
        step("TDS, TCS and advance tax challans")
        t = st.columns([1, 2])
        with t[0]:
            money("TDS / TCS for the full year (deducted + expected)", "f_tds")
            st.date_input("Position as on", key="f_as_on", min_value=START, max_value=END, format="DD/MM/YYYY",
                          help="The instalment position and interest are worked out as on this date.")
        with t[1]:
            st.markdown("Advance tax challans paid")
            pays = st.data_editor(
                s["payments_base"], key=f"pay_editor_{s['pay_ver']}", num_rows="dynamic", hide_index=True,
                width="stretch",
                column_config={"Date": st.column_config.DateColumn("Date", min_value=START, max_value=END, format="DD-MM-YYYY"),
                               "Amount": st.column_config.NumberColumn("Amount", min_value=0, step=1000, format="%.0f")})
            st.caption("Click the last empty row to add a challan.")
    with tab_26as:
        form_26as_section()
    payments = [{"date": pd.Timestamp(r.Date).date().isoformat(), "amount": float(r.Amount)}
                for r in pays.itertuples() if pd.notna(r.Date) and pd.notna(r.Amount) and float(r.Amount) > 0]

    inp = ClientInputs(
        name=s["f_name"].strip(), constitution=s["f_constitution"], age_band=s["f_age_band"],
        resident=True if firm else s["f_resident"], regime=s["f_regime"], presumptive=s["f_mode"] == MODES[3],
        business_income=float(business_income), salary_gross=0.0 if firm else s["f_salary"],
        hp_let_out_rent=s["f_hp_rent"], hp_municipal_tax=s["f_hp_muni"], hp_let_out_interest=s["f_hp_lo_int"],
        hp_self_occupied_interest=0.0 if firm else s["f_hp_so_int"], stcg_equity=s["f_stcg_eq"],
        ltcg_equity=s["f_ltcg_eq"], ltcg_other=s["f_ltcg_ot"], stcg_other=s["f_stcg_ot"],
        other_interest=s["f_int"], other_dividend=s["f_div"], other_misc=s["f_misc"],
        deductions_old=0.0 if firm else s["f_ded_old"], tds_tcs=s["f_tds"], payments=payments)
    result = compute(inp, RULES, s["f_as_on"])
    show_result(inp, result, working, con)


def position_strip(inp: ClientInputs, result: dict) -> None:
    """Client, amount payable now and status in one strip. Used on the client screen and the dashboard."""
    sched, chosen = result["schedule"], result["chosen"]
    nd = sched["next_due"]
    due_now = bool(result["liable"] and nd and nd["pay_now"] > 0)
    tone = ("urgent" if nd["days_left"] <= 7 else "due") if due_now else "clear"
    regime = f' &middot; {html.escape(chosen["regime"])}' if len(result["options"]) > 1 else ""
    if due_now:
        amount, by = f'Rs {fmt_inr(nd["pay_now"])}', f'by {nd["date"].strftime("%d %b %Y")}'
        tag = badge(f'{nd["days_left"]} days left', "b-urgent" if tone == "urgent" else "b-due")
    else:
        amount, by = "Nil", notes.headline(result)
        tag = badge("Not liable", "b-muted") if not result["liable"] else badge("Nothing due", "b-ok")
    interest = (f'Interest already arisen: Rs {fmt_inr(sched["interest_incurred"])}'
                if sched["interest_incurred"] > 0 else "No interest has arisen so far")
    st.markdown(
        f'<div class="atd-pos {tone}">'
        f'<div><div class="lbl">Client</div><div class="name">{html.escape(inp.name or "New client")}</div>'
        f'<div class="sub">{html.escape(inp.constitution)}{regime} &middot; position as on '
        f'{result["as_on"].strftime("%d %b %Y")}</div></div>'
        f'<div><div class="lbl">Amount payable now</div><div class="amt">{amount}</div>'
        f'<div class="sub">{html.escape(by)}</div></div>'
        f'<div><div class="lbl">Status</div><div style="margin-top:6px">{tag}</div>'
        f'<div class="sub" style="margin-top:8px">{html.escape(interest)}</div></div></div>',
        unsafe_allow_html=True)


def basis_of_calculation() -> None:
    """The rates and sections applied, in words. Replaces the old rules screen."""
    new, old, cg, at, firm = (RULES["new_regime"], RULES["old_regime"], RULES["capital_gains"], RULES["advance_tax"],
                              RULES["firm"])

    def slabs(rows: list) -> str:
        parts, lower = [], 0
        for upper, rate in rows:
            span = f"above {fmt_inr(lower)}" if upper is None else f"{fmt_inr(lower)} to {fmt_inr(upper)}"
            parts.append(f"{span}: {'nil' if rate == 0 else f'{rate * 100:g}%'}")
            lower = upper or lower
        return "; ".join(parts)

    pct = lambda x: f"{x * 100:g}%"  # noqa: E731
    dues = ", ".join(f"{pct(share)} by {date.fromisoformat(d).strftime('%d %b')}" for d, share in at["instalments"])
    rows = [
        ["New regime slabs", "Section 202", slabs(new["slabs"])],
        ["Old regime slabs (below 60)", "Finance Act, 2026", slabs(old["slabs_by_age"]["below60"])],
        ["Rebate, resident individuals", "Section 156",
         f"New regime: up to Rs {fmt_inr(new['rebate_max'])} where income is up to Rs {fmt_inr(new['rebate_income_limit'])}, "
         f"with marginal relief. Old regime: up to Rs {fmt_inr(old['rebate_max'])} up to Rs {fmt_inr(old['rebate_income_limit'])}."],
        ["Standard deduction on salary", "Section 19", f"Rs {fmt_inr(new['standard_deduction'])} new regime, Rs {fmt_inr(old['standard_deduction'])} old regime"],
        ["Firms and LLPs", "Finance Act, 2026", f"{pct(firm['rate'])}; surcharge {pct(firm['surcharge'])} above Rs {fmt_inr(firm['surcharge_threshold'])}"],
        ["Short-term gains, listed equity", "Section 196", pct(cg["stcg_equity_rate"])],
        ["Long-term gains, other assets", "Section 197", pct(cg["ltcg_other_rate"])],
        ["Long-term gains, listed equity", "Section 198", f"{pct(cg['ltcg_equity_rate'])} above Rs {fmt_inr(cg['ltcg_equity_exemption'])}"],
        ["Surcharge, individuals and HUFs", "Finance Act, 2026",
         "10% / 15% / 25% / 37% above Rs 50 lakh / 1 crore / 2 crore / 5 crore; 25% maximum in the new regime; "
         "15% maximum on these capital gains"],
        ["Health and education cess", "Finance Act, 2026", pct(RULES["cess"])],
        ["Presumptive income", "Section 58", "Taken at the percentage of turnover or receipts entered"],
        ["Advance tax payable", "Sections 403, 404", f"When tax after TDS / TCS is Rs {fmt_inr(at['threshold'])} or more. "
         "Resident individuals aged 60 or more with no business or professional income are not liable."],
        ["Instalments", "Section 408", f"{dues}. Presumptive business or profession: the whole amount by 15 March."],
        ["Interest for deferment", "Section 425", "1% a month for 3 months on the shortfall in each of the first three instalments, "
         "1% on the last; none where 12% and 36% are paid by June and September"],
        ["Interest for default", "Section 424", "1% a month from 1 April where advance tax paid is below 90% of the tax"],
    ]
    with st.expander(f"Basis of calculation: tax year {RULES['tax_year']}, {RULES['law']}"):
        html_table(["Item", "Provision", "Applied as"], [[r[0], r[1], Raw('<span style="white-space:normal">' + html.escape(r[2]) + "</span>")] for r in rows])
        st.caption("Not covered, check by hand: companies, alternate minimum tax, agricultural and casual income, brought-forward "
                   "losses, marginal relief where surcharge applies with capital gains, the 15% surcharge limit on dividend, and the "
                   "relief from deferment interest where a shortfall arises only from capital gains, dividend or a new business.")


def instalment_chart(sched: dict) -> None:
    data = pd.DataFrame(
        [{"Due date": r["due_date"].strftime("%d %b"), "order": n, "What": "Required by this date", "Amount": r["required_cumulative"]}
         for n, r in enumerate(sched["rows"])]
        + [{"Due date": r["due_date"].strftime("%d %b"), "order": n, "What": "Paid by this date", "Amount": r["paid_by_due_date"]}
           for n, r in enumerate(sched["rows"])])
    chart = alt.Chart(data).mark_bar().encode(
        x=alt.X("Due date:N", sort=alt.SortField("order"), title=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("What:N", sort=["Required by this date", "Paid by this date"]),
        y=alt.Y("Amount:Q", title="Rs"),
        color=alt.Color("What:N", title=None, sort=["Required by this date", "Paid by this date"],
                        scale=alt.Scale(domain=["Required by this date", "Paid by this date"], range=["#B9C4D4", "#1B365D"]),
                        legend=alt.Legend(orient="top")),
        tooltip=["Due date", "What", alt.Tooltip("Amount:Q", format=",.0f")],
    ).properties(height=240)
    st.altair_chart(chart)


def what_if(inp: ClientInputs, result: dict) -> None:
    """Try a payment made today and see what it does to the interest."""
    sched, nd = result["schedule"], result["schedule"]["next_due"]
    if not result["liable"] or result["net_liability"] <= sched["paid_to_date"]:
        return
    step("What if the client pays today")
    c = st.columns([1.2, 3], vertical_alignment="center")
    start = float(nd["pay_now"]) if nd and nd["pay_now"] > 0 else float(result["net_liability"] - sched["paid_to_date"])
    amount = c[0].number_input("Payment today (Rs)", min_value=0.0, value=start, step=5000.0, format="%.0f",
                               key=f"whatif_{inp.name}_{result['as_on']}_{int(start)}")
    trial = compute(replace(inp, payments=list(inp.payments) + [{"date": result["as_on"].isoformat(), "amount": amount}]),
                    RULES, result["as_on"])
    before, after = sched["interest_if_nothing_more_paid"], trial["schedule"]["interest_if_nothing_more_paid"]
    left = max(0, result["net_liability"] - sched["paid_to_date"] - round(amount))
    c[1].markdown(f"Interest for deferment comes to **Rs {fmt_inr(after)}** instead of Rs {fmt_inr(before)} "
                  f"(saves Rs {fmt_inr(before - after)}). Balance for the rest of the year: Rs {fmt_inr(left)}.")


def show_result(inp: ClientInputs, result: dict, working: dict, con) -> None:
    s = st.session_state
    sched, chosen = result["schedule"], result["chosen"]
    nd = sched["next_due"]
    firm_name = s.get("firm_name", "")
    explanation = s["ai_text"] or notes.plain_explanation(inp, result)
    message = notes.whatsapp_text(inp, result, firm_name, explanation)

    position_strip(inp, result)
    due_now = bool(result["liable"] and nd and nd["pay_now"] > 0)

    k = st.columns(4)
    k[0].metric("Total income", fmt_inr(chosen["total_income"]))
    k[1].metric(f"Tax ({chosen['regime']})", fmt_inr(chosen["total_tax"]))
    k[2].metric("Advance tax for the year", fmt_inr(result["net_liability"]))
    k[3].metric("Paid so far", fmt_inr(sched["paid_to_date"]))
    if not result["liable"]:
        st.success(result["not_liable_reason"])
    for flag in result["flags"]:
        st.warning(flag)

    # ---- save
    sv = st.columns([1, 4], vertical_alignment="center")
    if sv[0].button("Save client", type="primary", disabled=not inp.name, width="stretch"):
        storage.save_client(con, inp.name, inp.to_dict(), working)
        tb = s.get("tb_current")
        if working.get("mode") == MODES[0] and tb:
            storage.save_trial_balance(con, inp.name, tb["filename"], tb["data"], tb["meta"], tb["ledgers"])
            s["tb_saved"] = storage.get_trial_balance(con, inp.name)
        summary = {"regime": chosen["regime"], "total_income": chosen["total_income"], "total_tax": chosen["total_tax"],
                   "advance_tax_for_year": result["net_liability"], "paid_so_far": sched["paid_to_date"],
                   "next_due_date": nd["date"].isoformat() if nd else "",
                   "pay_now": nd["pay_now"] if (nd and result["liable"]) else 0,
                   "interest_arisen": sched["interest_incurred"]}
        storage.save_estimate(con, inp.name, result["as_on"].isoformat(), inp.to_dict(), working, summary,
                              message, explanation)
        st.toast(f"Saved {inp.name}")
        sv[1].success(f"Saved {inp.name}. A dated copy of this estimate is kept in the History tab.")
    elif not inp.name:
        sv[1].caption("Enter the client name in tab 1 to save.")
    else:
        sv[1].caption("Saves the figures, the trial balance and a dated copy of this estimate on this computer.")

    tab_msg, tab_comp, tab_inst, tab_hist = st.tabs(
        ["Message for the client", "Computation", "Instalments and interest", "History"])

    with tab_msg:
        api_key = s.get("api_key", "")
        if api_key:
            b = st.columns([1, 1, 1])
            lang = b[0].selectbox("Language", ["English", "Hindi", "Gujarati", "Marathi"], label_visibility="collapsed")
            if b[1].button("Write explanation with AI", width="stretch"):
                summary = {"headline": notes.headline(result), "total_income": chosen["total_income"],
                           "total_tax": chosen["total_tax"], "regime": chosen["regime"], "tds_tcs": result["tds_tcs"],
                           "advance_tax_for_year": result["net_liability"], "paid_so_far": sched["paid_to_date"],
                           "next_due_date": nd["date"] if nd else None, "pay_now": nd["pay_now"] if nd else 0,
                           "interest_already_arisen": sched["interest_incurred"]}
                try:
                    with st.spinner("Writing the explanation..."):
                        s["ai_text"] = ai.explain_for_client(summary, api_key, s.get("ai_model", ai.DEFAULT_MODEL), lang,
                                                            provider=s.get("ai_provider"))
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"AI call failed: {exc}")
            if s["ai_text"] and b[2].button("Back to standard text", width="stretch"):
                s["ai_text"] = ""
                st.rerun()
            if s.get("tb_pl_ledgers") and st.button("Ask AI for unusual items in the books"):
                try:
                    with st.spinner("Reading the ledgers..."):
                        st.info(ai.flag_unusual_items(s["tb_pl_ledgers"], api_key, s.get("ai_model", ai.DEFAULT_MODEL),
                                                      provider=s.get("ai_provider")))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"AI call failed: {exc}")
        else:
            st.caption("Add a Claude, ChatGPT or Gemini API key under Settings in the sidebar for an AI-written explanation in English, Hindi, "
                       "Gujarati or Marathi. A standard explanation is used otherwise.")
        st.text_area("WhatsApp / email text", message, height=300,
                     help="Copy this text, or use the buttons below.")
        d = st.columns([1, 1, 2])
        d[0].link_button("Open in WhatsApp", wa_link(s.get("f_mobile", ""), message), width="stretch",
                         help="Opens WhatsApp with this message ready, in the client's chat if a mobile number is "
                              "entered in tab 1; otherwise you choose the contact there.")
        d[1].download_button("Download Word note", notes.docx_note(inp, result, firm_name, explanation),
                             file_name=f"Advance tax - {inp.name or 'client'}.docx", width="stretch",
                             mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    with tab_comp:
        labels = [("Salary", "salary_income"), ("House property", "house_property_income"),
                  ("Business or profession", "business_income"), ("Other sources", "other_sources_income"),
                  ("STCG at slab rate", "stcg_other"), ("Less: deductions", "deductions"),
                  ("STCG on equity", "stcg_equity"), ("LTCG on equity", "ltcg_equity"),
                  ("LTCG on other assets", "ltcg_other"), ("Total income", "total_income"),
                  ("Tax on normal income", "tax_on_normal_income"), ("Tax on capital gains", "tax_on_capital_gains"),
                  ("Less: rebate / marginal relief", "rebate"), ("Surcharge", "surcharge"), ("Cess", "cess"),
                  ("Total tax", "total_tax")]
        heads, opts = ["Particulars"], list(result["options"].items())
        for key, opt in opts:
            heads.append(opt["regime"] + (" (used)" if key == result["chosen_key"] and len(opts) > 1 else ""))
        labels = [(label, f) for label, f in labels
                  if f in ("total_income", "total_tax") or any(opt[f] for _, opt in opts)]
        body = [[label] + [fmt_inr(opt[f]) for _, opt in opts] for label, f in labels]
        totals = tuple(n for n, (_, f) in enumerate(labels) if f in ("total_income", "total_tax"))
        html_table(heads, body, num_cols=tuple(range(1, len(heads))), total_rows=totals)
        saving = result["regime_saving"] or 0
        if saving > 0:
            st.caption(f"The regime used saves Rs {fmt_inr(saving)} over the other one.")
        elif saving < 0:
            st.warning(f"The other regime would be lower by Rs {fmt_inr(-saving)}. Change 'Tax regime' in tab 1 if the client can switch.")
        st.write("")
        basis_of_calculation()

    with tab_inst:
        if result["liable"]:
            if result["net_liability"] > 0:
                done = min(1.0, max(0.0, sched["paid_to_date"] / result["net_liability"]))
                st.progress(done, text=f"Paid Rs {fmt_inr(sched['paid_to_date'])} of Rs {fmt_inr(result['net_liability'])} "
                                       f"for the year ({done:.0%})")
            html_table(
                ["Due date", "Cumulative", "Required", "Paid by date", "Shortfall", "Interest", "Status"],
                [[r["due_date"].strftime("%d %b %Y"), f"{int(r['cumulative_pct'] * 100)}%",
                  fmt_inr(r["required_cumulative"]), fmt_inr(r["paid_by_due_date"]), fmt_inr(r["shortfall"]),
                  fmt_inr(r["interest"]), badge(r["status"])] for r in sched["rows"]],
                num_cols=(1, 2, 3, 4, 5))
            st.write("")
            instalment_chart(sched)
            what_if(inp, result)
            i = st.columns(3)
            i[0].metric("Interest already arisen", fmt_inr(sched["interest_incurred"]))
            i[1].metric("Interest if nothing more is paid", fmt_inr(sched["interest_if_nothing_more_paid"]))
            i[2].metric("Per month after 31 March", fmt_inr(result["monthly_default_interest"]),
                        help="Interest for default if less than 90% of the tax is paid as advance tax.")
        else:
            st.info("No instalments apply on the present estimate.")

    with tab_hist:
        if inp.name:
            history_section(con, inp.name, firm_name)
        else:
            st.caption("Enter the client name to see the saved estimates.")


def history_section(con, name: str, firm_name: str) -> None:
    hist = storage.list_estimates(con, name)
    if not hist:
        st.info("Nothing saved yet. Every time you press Save client, a dated copy is added here.")
        return
    html_table(
        ["Saved on", "Position as on", "Regime", "Total income", "Tax for year", "Advance tax", "Paid", "Due then"],
        [[h["saved_at"].replace("T", " "), h["as_on"], h["summary"].get("regime", ""),
          fmt_inr(h["summary"].get("total_income", 0)), fmt_inr(h["summary"].get("total_tax", 0)),
          fmt_inr(h["summary"].get("advance_tax_for_year", 0)), fmt_inr(h["summary"].get("paid_so_far", 0)),
          fmt_inr(h["summary"].get("pay_now", 0))] for h in hist],
        num_cols=(3, 4, 5, 6, 7), max_height=260)
    st.write("")
    ids = [h["id"] for h in hist]
    labels = {h["id"]: f"{h['saved_at'].replace('T', ' ')}  |  as on {h['as_on']}  |  tax {fmt_inr(h['summary'].get('total_tax', 0))}"
              for h in hist}
    pick = st.selectbox("Open an earlier estimate", ids, format_func=labels.get, key=f"hist_pick_{name}")
    old = next(h for h in hist if h["id"] == pick)
    st.text_area("Message sent with that estimate", old["message"], height=220, key=f"hist_msg_{pick}")
    old_inp = ClientInputs.from_dict(old["inputs"])
    old_res = compute(old_inp, RULES, date.fromisoformat(old["as_on"]))
    b = st.columns(2)
    b[0].download_button("Download Word note of that estimate",
                         notes.docx_note(old_inp, old_res, firm_name, old["explanation"] or None),
                         file_name=f"Advance tax - {name} - {old['as_on']}.docx", key=f"hist_doc_{pick}",
                         mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    b[1].button("Load that estimate into the form", on_click=load_estimate, args=(pick,), key=f"hist_load_{pick}")


# --------------------------------------------------------------- dashboard
def open_from_dashboard(name: str) -> None:
    load_client(name)
    st.session_state["open_choice"] = name
    goto("Client")


def new_from_dashboard() -> None:
    reset_form()
    st.session_state["open_choice"] = NEW_CLIENT
    goto("Client")


def load_demo_clients() -> None:
    """The six clients in demo_clients/, each with its own test files (reloading replaces the same six)."""
    from advtax import demo
    done = demo.load_demo_folder(storage.connect())
    st.session_state["demo_loaded"] = len(done)


def client_status(r: dict) -> str:
    nd = r["schedule"]["next_due"]
    if not r["liable"]:
        return "Not liable"
    if nd and nd["pay_now"] > 0:
        return "Due"
    if r["schedule"]["interest_incurred"] > 0:
        return "Covered, interest arisen"
    return "Covered"


def reminders_tab(due: pd.DataFrame, computed: dict, as_on: date) -> None:
    """One place to send the reminder to every client who has an amount due."""
    s = st.session_state
    if due.empty:
        st.info("No client shown has an amount due.")
        return
    firm_name = s.get("firm_name", "")
    st.caption(f"{len(due)} clients have an amount due. The message is the standard one from the client screen. "
               "'Open chat' needs the mobile number saved in tab 1 of the client.")
    packs, body = {}, []
    for r in due.to_dict("records"):
        inp, res = computed[r["Client"]]
        message = notes.whatsapp_text(inp, res, firm_name, notes.plain_explanation(inp, res))
        packs[r["Client"]] = (inp, res, message)
        if wa_number(r["Mobile"]):
            link = Raw(f'<a href="{html.escape(wa_link(r["Mobile"], message))}" target="_blank" rel="noopener">Open chat</a>')
        else:
            link = Raw('<span style="color:#6B7686">No mobile saved</span>')
        body.append([r["Client"], fmt_inr(r["Pay now"]), r["Next due date"],
                     "-" if pd.isna(r["Days left"]) else int(r["Days left"]), r["Mobile"] or "-", link])
    html_table(["Client", "Pay now", "Due date", "Days left", "Mobile", "WhatsApp"], body, num_cols=(1, 3), max_height=420)
    st.write("")
    sig = f"{as_on}|{firm_name}|{sorted(packs)}|{[round(v) for v in due['Pay now']]}"
    b = st.columns([1.4, 1.4, 3], vertical_alignment="center")
    if b[0].button("Prepare all notes", type="primary", width="stretch",
                   help="Builds the Word note for every client listed and one text file with all the messages."):
        buf, used = io.BytesIO(), set()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            every = []
            for name, (inp, res, message) in packs.items():
                base = portal_26as.safe_folder_name(name)
                while base.lower() in used:
                    base += " (2)"
                used.add(base.lower())
                z.writestr(f"Advance tax - {base}.docx", notes.docx_note(inp, res, firm_name, notes.plain_explanation(inp, res)))
                every.append(f"===== {name} =====\n{message}\n")
            z.writestr("All messages.txt", "\n".join(every))
        s["remind_zip"], s["remind_sig"] = buf.getvalue(), sig
    if s.get("remind_zip") and s.get("remind_sig") == sig:
        b[1].download_button("Download ZIP", s["remind_zip"], file_name=f"Advance tax reminders {as_on.isoformat()}.zip",
                             mime="application/zip", width="stretch")
        b[2].caption(f"Ready: {len(packs)} Word notes and one file with all the messages.")
    else:
        b[2].caption("Press once to build the notes for the clients listed above, then download.")


STATUS_STYLE = {"Due": "color:#8A5A0B;background-color:#FDF4E3;font-weight:600",
                "Covered": "color:#17633F;background-color:#E8F4EE;font-weight:600",
                "Covered, interest arisen": "color:#8A5A0B;background-color:#FDF4E3;font-weight:600",
                "Not liable": "color:#5F6B7A;background-color:#F1F3F6;font-weight:600"}
FILTERS = ["All", "Due", "Covered", "Not liable"]


def delete_from_dashboard(name: str) -> None:
    storage.delete_client(storage.connect(), name)
    st.session_state["dash_deleted"] = name


def client_panel(row: dict, inp: ClientInputs, result: dict) -> None:
    """What shows under the list when a client row is clicked."""
    position_strip(inp, result)
    firm_name = st.session_state.get("firm_name", "")
    explanation = notes.plain_explanation(inp, result)
    message = notes.whatsapp_text(inp, result, firm_name, explanation)
    b = st.columns([1.2, 1.4, 1.4, 1.2, 2], vertical_alignment="center")
    b[0].button("Open client", type="primary", on_click=open_from_dashboard, args=(inp.name,), width="stretch",
                key=f"panel_open_{inp.name}")
    b[1].link_button("WhatsApp reminder", wa_link(row["Mobile"], message), width="stretch",
                     help="Opens WhatsApp with the reminder ready, in the client's chat if a mobile number is saved.")
    b[2].download_button("Word note", notes.docx_note(inp, result, firm_name, explanation),
                         file_name=f"Advance tax - {inp.name}.docx", width="stretch", key=f"panel_doc_{inp.name}",
                         mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with b[3].popover("Remove"):
        st.write(f"Remove **{inp.name}** with its trial balance and history? This cannot be undone.")
        st.button("Remove permanently", on_click=delete_from_dashboard, args=(inp.name,), key=f"panel_del_{inp.name}")


def dashboard_page() -> None:
    s = st.session_state
    con = storage.connect()
    clients = storage.list_clients(con)
    if s.pop("dash_deleted", None):
        st.toast("Client removed")
    if not clients:
        with st.container(border=True):
            st.markdown("#### No clients yet")
            st.write("Start with a new client, or load the invented demo clients to see how the desk works.")
            e = st.columns([1, 1, 3])
            e[0].button("New client", type="primary", on_click=new_from_dashboard, width="stretch")
            e[1].button("Load demo clients", on_click=load_demo_clients, width="stretch")
        return

    as_on = s.get("dash_as_on", TODAY)
    rows, computed = [], {}
    for c in clients:
        inp = ClientInputs.from_dict(c["inputs"])
        r = compute(inp, RULES, as_on)
        nd = r["schedule"]["next_due"]
        rows.append({"Client": inp.name, "Type": inp.constitution, "Status": client_status(r),
                     "Pay now": nd["pay_now"] if nd and r["liable"] else 0,
                     "Next due date": nd["date"].strftime("%d %b %Y") if nd else "-",
                     "Days left": nd["days_left"] if nd else None,
                     "Advance tax for year": r["net_liability"], "Paid so far": r["schedule"]["paid_to_date"],
                     "Interest arisen": r["schedule"]["interest_incurred"],
                     "Regime": r["chosen"]["regime"], "Total income": r["chosen"]["total_income"],
                     "Tax for year": r["chosen"]["total_tax"], "Updated": c["updated_at"][:10],
                     "Mobile": str((c.get("working") or {}).get("mobile", ""))})
        computed[inp.name] = (inp, r)
    full = pd.DataFrame(rows).sort_values("Pay now", ascending=False).reset_index(drop=True)

    k = st.columns(4)
    k[0].metric("Clients", len(full))
    k[1].metric("Clients with amount due", int((full["Pay now"] > 0).sum()))
    k[2].metric("Total due now", fmt_inr(full["Pay now"].sum()))
    k[3].metric("Interest already arisen", fmt_inr(full["Interest arisen"].sum()))

    f = st.columns([2.4, 2.6, 1, 1], vertical_alignment="bottom")
    search = f[0].text_input("Search", placeholder="Search client", label_visibility="collapsed")
    show = f[1].segmented_control("Show", FILTERS, default="All", label_visibility="collapsed", key="dash_filter") or "All"
    with f[2].popover("More"):
        st.date_input("Position as on", value=TODAY, min_value=START, max_value=END, format="DD/MM/YYYY", key="dash_as_on",
                      help="The whole dashboard is worked out as on this date.")
        st.download_button("Download list (CSV)", full.to_csv(index=False).encode("utf-8"),
                           "advance_tax_dashboard.csv", "text/csv")
    f[3].button("New client", type="primary", on_click=new_from_dashboard, width="stretch")

    df = full
    if search.strip():
        df = df[df["Client"].str.contains(search.strip(), case=False, regex=False)]
    if show == "Due":
        df = df[df["Pay now"] > 0]
    elif show == "Covered":
        df = df[df["Status"].str.startswith("Covered")]
    elif show == "Not liable":
        df = df[df["Status"] == "Not liable"]
    df = df.reset_index(drop=True)

    tab_list, tab_remind, tab_chart = st.tabs(["Clients", "Reminders", "Chart"])
    with tab_list:
        if df.empty:
            st.info("No client matches.")
        else:
            cols = ["Client", "Type", "Status", "Pay now", "Next due date", "Days left", "Advance tax for year",
                    "Paid so far", "Interest arisen"]
            money_cols = ["Pay now", "Advance tax for year", "Paid so far", "Interest arisen"]
            styled = (df[cols].style
                      .format({**{c: fmt_inr for c in money_cols},
                               "Days left": lambda v: "-" if pd.isna(v) else f"{int(v)}"})
                      .map(lambda v: STATUS_STYLE.get(v, ""), subset=["Status"]))
            event = st.dataframe(
                styled, hide_index=True, width="stretch", height=min(38 + 35 * len(df), 458),
                on_select="rerun", selection_mode="single-row", key=f"dash_table_{show}_{search.strip().lower()}_{as_on}",
                column_config={"Client": st.column_config.TextColumn("Client", width="large", pinned=True)})
            picked = event.selection.rows if event and event.selection else []
            if picked and picked[0] < len(df):
                row = df.iloc[picked[0]].to_dict()
                client_panel(row, *computed[row["Client"]])
            else:
                st.caption(f"{len(df)} of {len(full)} clients. Click a row to see the client and its actions. "
                           "Click a column heading to sort.")
    with tab_remind:
        reminders_tab(df[df["Pay now"] > 0], computed, as_on)
    with tab_chart:
        due = df[df["Pay now"] > 0].sort_values("Pay now", ascending=False).head(15)
        if due.empty:
            st.info("No amount is due from the clients shown.")
        else:
            chart = alt.Chart(due[["Client", "Pay now"]]).mark_bar(color="#1B365D", cornerRadiusEnd=2).encode(
                x=alt.X("Pay now:Q", title="Amount to pay now (Rs)"),
                y=alt.Y("Client:N", sort="-x", title=None, axis=alt.Axis(labelLimit=360)),
                tooltip=["Client", alt.Tooltip("Pay now:Q", format=",.0f")],
            ).properties(height=max(200, 32 * len(due) + 60))
            st.altair_chart(chart)
            if len(df[df["Pay now"] > 0]) > len(due):
                st.caption("The 15 largest amounts are shown.")


def data_folder_box() -> None:
    with st.expander("Data folder and backup"):
        folder, db = storage.data_dir(), storage.db_path()
        st.caption("Clients, trial balances and history are saved in this folder on your computer:")
        st.code(str(folder), language=None)
        if os.environ.get("ADVTAX_DATA_DIR"):
            st.caption("Set by the ADVTAX_DATA_DIR environment variable.")
        else:
            new = st.text_input("Move to another folder (full path)", key="new_data_dir",
                                placeholder="D:\\OfficeData\\AdvanceTax")
            c = st.columns(2)
            if c[0].button("Use this folder", disabled=not new):
                try:
                    target = storage.set_data_dir(new)
                    st.success(f"Now using {target}")
                    st.rerun()
                except (OSError, ValueError) as exc:
                    st.error(f"Cannot use that folder: {exc}")
            if c[1].button("Back to default"):
                storage.reset_data_dir()
                st.rerun()
            st.caption("An existing database in the new folder is used as it is; otherwise a new empty one is "
                       "created. To carry your clients over, copy advance_tax.db into the new folder first. "
                       "On a shared drive, let one person save at a time.")
        st.button("Load demo clients", on_click=load_demo_clients, key="demo_load_side",
                  help="Adds the six clients in the demo_clients folder, with their test files. "
                       "Your own clients are not touched; reloading replaces the same six.")
        if st.session_state.pop("demo_loaded", None):
            st.success("Demo clients loaded.")
        if db.exists():
            n = storage.counts(storage.connect())
            st.caption(f"{n['clients']} clients, {n['trial_balances']} trial balances, {n['estimates']} saved estimates.")
            st.download_button("Download backup (.db)", db.read_bytes(),
                               file_name=f"advance_tax_backup_{date.today().isoformat()}.db")


def header(page: str) -> None:
    due = next_instalment(TODAY)
    if due:
        days = (due - TODAY).days
        nxt = f'{due.strftime("%d %b %Y")} ({"today" if days == 0 else f"{days} days"})'
    else:
        nxt = "All dates passed"
    firm = html.escape(st.session_state.get("firm_name", "").strip())
    firm_box = f'<div>Firm<b>{firm}</b></div>' if firm else ""
    st.markdown(
        f'<div class="atd-bar"><div><div class="crumb">Advance Tax Desk</div><div class="page">{html.escape(page)}</div></div>'
        f'<div class="meta">{firm_box}<div>Tax year<b>{html.escape(RULES["tax_year"])}</b></div>'
        f'<div>Next due date<b>{nxt}</b></div></div></div>', unsafe_allow_html=True)


def ai_settings() -> None:
    """API key box, then the provider it belongs to and a list of that provider's models to pick from."""
    s = st.session_state
    st.text_input("AI API key (optional)", type="password", key="api_key_box",
                  placeholder="Paste your key",
                  help="Paste a key from Anthropic, OpenAI or Google. Used only for this session. Never saved to disk.")
    key, from_env = (s.get("api_key_box") or "").strip(), None
    if not key:
        key, from_env = ai.key_from_environment()
    s["api_key"] = key
    if not key:
        s["ai_provider"] = None
        return
    provider = from_env or ai.detect_provider(key)
    if provider:
        st.caption(f"Key recognised: {ai.PROVIDERS[provider]}")
    else:
        provider = st.selectbox("Which provider is this key from?", list(ai.PROVIDERS), format_func=ai.PROVIDERS.get,
                                key="ai_provider_pick")
    s["ai_provider"] = provider
    sig = hashlib.sha256(f"{provider}|{key}".encode()).hexdigest()
    if s.get("ai_models_sig") != sig:
        try:
            with st.spinner("Reading the model list..."):
                models, err = ai.list_models(key, provider), ""
        except ai.AIError as exc:
            models, err = [], str(exc)
        s["ai_models"], s["ai_models_err"], s["ai_models_sig"] = models, err, sig
        s["ai_model"] = ai.suggested_model(models, provider)
    models = s.get("ai_models") or []
    if models:
        ids = [m["id"] for m in models]
        labels = {m["id"]: m["id"] if m["label"] == m["id"] else f'{m["label"]}  ({m["id"]})' for m in models}
        if s.get("ai_model") not in ids:
            s["ai_model"] = ai.suggested_model(models, provider)
        st.selectbox("Model", ids, format_func=labels.get, key="ai_model",
                     help="The list comes from the provider for this key. Smaller models are cheaper and enough here.")
    else:
        st.warning(s.get("ai_models_err") or "The provider returned no models for this key.")
        if not s.get("ai_model"):
            s["ai_model"] = ai.FALLBACK_MODELS[provider]
        st.text_input("Model name", key="ai_model")
        if st.button("Read the model list again"):
            s.pop("ai_models_sig", None)
            st.rerun()


def sidebar() -> str:
    s = st.session_state
    s.setdefault("nav", PAGES[0])
    with st.sidebar:
        st.markdown('<div class="atd-brand">Advance Tax Desk<small>Estimates, instalments and client notes</small></div>'
                    '<div class="atd-label">Menu</div>', unsafe_allow_html=True)
        page = st.radio("Go to", PAGES, key="nav", label_visibility="collapsed",
                        format_func={"Dashboard": ":material/space_dashboard:  Dashboard",
                                     "Client": ":material/person:  Client"}.get)
        st.markdown('<div class="atd-label">Setup</div>', unsafe_allow_html=True)
        with st.expander("Settings", expanded=True):
            st.text_input("Your firm name (for notes)", key="firm_name")
            ai_settings()
        data_folder_box()
        st.caption(("AI is on. " if s["api_key"] else "AI is off; the app works fully without it. ")
                   + "AI never receives the client's name. The tax calculation is rule-based and does not use AI.")
    return page


def main() -> None:
    init_state()
    st.markdown(CSS, unsafe_allow_html=True)
    page = sidebar()
    header(page)
    if page == "Dashboard":
        dashboard_page()
    else:
        client_page()


main()
