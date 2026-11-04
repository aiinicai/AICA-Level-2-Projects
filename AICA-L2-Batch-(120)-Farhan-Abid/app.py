"""Smart Ledger Anomaly & System-Override Detector  (ICAI AICA Level 2 Capstone - Proposal B)

ALL THE CODE IS IN THIS ONE FILE.   Run it with:   python app.py   (or press F5 in IDLE)
The first run installs the needed libraries automatically. Alternative: streamlit run app.py

File map (search for the "SECTION" lines):
    SECTION 1  LLM client       Grok (xAI) / Groq / OpenAI / Anthropic / Ollama - optional
    SECTION 2  Detectors        pandas tests, variance analysis, Benford, risk scoring
    SECTION 3  Sample data      built-in synthetic ledger with planted anomalies
    SECTION 4  Agents           Agent 1 Detector, Agent 2 Investigator (LLM tool-calling),
                                Agent 3 Letter Drafter, orchestrator
    SECTION 5  Export           Word letter + Excel findings
    SECTION 6  Streamlit UI     dashboard

The app works fully OFFLINE without any API key. If an LLM key is set (sidebar or .env),
the agents use LLM tool-calling and the LLM drafts the Management Letter.
"""
import importlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date

# ---- First-run auto-install: installs any missing libraries once, when run as a .py script.
# (Skipped automatically if the code is later packaged as an .exe, where everything is bundled.)
REQUIRED_LIBRARIES = {            # import name -> pip name
    "streamlit": "streamlit", "pandas": "pandas", "numpy": "numpy", "openpyxl": "openpyxl",
    "docx": "python-docx", "requests": "requests", "dotenv": "python-dotenv",
}


def _python_exe():
    exe = sys.executable
    return exe.replace("pythonw.exe", "python.exe") if exe.lower().endswith("pythonw.exe") else exe


def ensure_libraries():
    if getattr(sys, "frozen", False):
        return
    missing = [pip for mod, pip in REQUIRED_LIBRARIES.items() if importlib.util.find_spec(mod) is None]
    if missing:
        print("First run: installing libraries (%s). Please wait..." % ", ".join(missing))
        subprocess.check_call([_python_exe(), "-m", "pip", "install", *missing])
        importlib.invalidate_caches()


ensure_libraries()

import numpy as np
import pandas as pd
import requests
import streamlit as st
from docx import Document
from docx.shared import Pt

try:                                   # optional: read keys from a .env file
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass



# ==========================================================================
# SECTION 1: LLM client (optional)
# ==========================================================================
# OpenAI-compatible providers: name -> (base URL, env var for key, default model)
OPENAI_COMPATIBLE = {
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-4o-mini"),
    "xai":    ("https://api.x.ai/v1", "XAI_API_KEY", "grok-4.7"),      # Grok
    "groq":   ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
}


def provider() -> str:
    p = os.getenv("LLM_PROVIDER", "none").strip().lower()
    return "xai" if p == "grok" else p


def is_enabled() -> bool:
    p = provider()
    if p == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    if p in OPENAI_COMPATIBLE:
        return bool(os.getenv(OPENAI_COMPATIBLE[p][1]))
    if p == "ollama":
        return True
    return False


def _err_text(e):
    """Readable error text; includes the server's own explanation when there is one."""
    msg = f"{type(e).__name__}: {e}"
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            msg += " | Server says: " + resp.text.strip()[:300]
        except Exception:
            pass
    return msg


def last_error() -> str:
    """Most recent LLM error text (shown in the UI to help debugging)."""
    return _LAST_ERROR[0]


_LAST_ERROR = [""]


def supports_tools() -> bool:
    """True when the configured provider can do OpenAI-style tool calling (Grok/xAI, Groq, OpenAI)."""
    return is_enabled() and provider() in OPENAI_COMPATIBLE


def _retry_wait(e, attempt):
    """Seconds to wait before retrying. Uses the provider's own hint ("try again in 10.59s")."""
    m = re.search(r"try again in (?:(\d+)m)?\s*([\d.]+)s", str(getattr(getattr(e, "response", None), "text", "")))
    if m:
        return min(45.0, (int(m.group(1) or 0) * 60) + float(m.group(2)) + 1.0)
    return 2.0 * (attempt + 1)


def _post_with_retry(url, headers, payload, timeout=90, attempts=8):
    """POST that survives rate limits (429), server hiccups (5xx) and the occasional malformed
    tool call (400, retried twice only). Returns the response, or None (reason in last_error())."""
    for attempt in range(attempts):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            _LAST_ERROR[0] = _err_text(e)
            code = getattr(getattr(e, "response", None), "status_code", None)
            retry_ok = code in (429, 500, 502, 503) or (code == 400 and attempt < 3)
            if attempt < attempts - 1 and retry_ok:
                body = str(getattr(getattr(e, "response", None), "text", ""))
                if code == 400 and "tools" in payload and "output_parse_failed" in body:
                    payload = dict(payload, parallel_tool_calls=False)     # simpler output next time
                time.sleep(_retry_wait(e, attempt))
                continue
            return None
    return None


def chat(messages, tools=None):
    """One chat-completion round with optional tool (function) definitions.

    Returns the assistant message dict (may contain 'tool_calls'), or None on failure.
    """
    if not supports_tools():
        return None
    base, key_env, default_model = OPENAI_COMPATIBLE[provider()]
    payload = {"model": os.getenv("LLM_MODEL", "") or default_model, "messages": messages}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    r = _post_with_retry(f"{base}/chat/completions",
                         {"Authorization": f"Bearer {os.environ[key_env]}"}, payload)
    return r.json()["choices"][0]["message"] if r is not None else None


def ask(prompt: str, system: str = "You are a senior audit manager.", max_tokens: int = 2000):
    """Return LLM text, or None if no LLM is configured / the call fails."""
    if not is_enabled():
        return None
    p, model = provider(), os.getenv("LLM_MODEL", "")
    try:
        if p == "anthropic":
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                         "anthropic-version": "2023-06-01"},
                json={"model": model or "claude-sonnet-4-5", "max_tokens": max_tokens,
                      "system": system,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=60)
            r.raise_for_status()
            return r.json()["content"][0]["text"]
        if p in OPENAI_COMPATIBLE:
            base, key_env, default_model = OPENAI_COMPATIBLE[p]
            r = _post_with_retry(
                f"{base}/chat/completions", {"Authorization": f"Bearer {os.environ[key_env]}"},
                {"model": model or default_model, "max_tokens": max_tokens,
                 "messages": [{"role": "system", "content": system},
                              {"role": "user", "content": prompt}]}, timeout=60)
            if r is None:
                return None
            text = (r.json()["choices"][0]["message"].get("content") or "").strip()
            if not text:
                _LAST_ERROR[0] = ("Connected OK, but the model returned an empty reply "
                                  "(a thinking model may have used all its tokens). Try a larger limit or another model.")
                return None
            return text
        if p == "ollama":
            url = os.getenv("OLLAMA_URL", "http://localhost:11434")
            r = requests.post(f"{url}/api/chat",
                              json={"model": model or "llama3.2", "stream": False,
                                    "messages": [{"role": "system", "content": system},
                                                 {"role": "user", "content": prompt}]},
                              timeout=120)
            r.raise_for_status()
            return r.json()["message"]["content"]
    except Exception as e:
        _LAST_ERROR[0] = _err_text(e)
        return None
    return None


# ==========================================================================
# SECTION 2: Detectors
# ==========================================================================
REQUIRED_COLUMNS = ["JE_ID", "Posting_Date", "Account_Code", "Account_Name",
                    "Description", "Debit", "Credit", "User"]

SEVERITY_POINTS = {"High": 3, "Medium": 2, "Low": 1}


def load_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Validate columns, parse dates, build a single Amount column."""
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if "Source" not in df.columns:
        df["Source"] = "Unknown"
    df["Posting_Date"] = pd.to_datetime(df["Posting_Date"], errors="coerce")
    df = df.dropna(subset=["Posting_Date"])
    df["Debit"] = pd.to_numeric(df["Debit"], errors="coerce").fillna(0.0)
    df["Credit"] = pd.to_numeric(df["Credit"], errors="coerce").fillna(0.0)
    df["Amount"] = df[["Debit", "Credit"]].max(axis=1)
    df["Account_Code"] = df["Account_Code"].astype(str)
    # Optional columns used by the extra control tests. If a column is absent the related test is skipped.
    df["Approved_By"] = df["Approved_By"].fillna("").astype(str).str.strip() if "Approved_By" in df.columns else "N/A"
    df["Posting_Time"] = df["Posting_Time"].fillna("").astype(str).str.strip() if "Posting_Time" in df.columns else ""
    df["Override"] = df["Override"].fillna("").astype(str).str.strip().str.upper() if "Override" in df.columns else ""
    df["Entry_Date"] = (pd.to_datetime(df["Entry_Date"], errors="coerce") if "Entry_Date" in df.columns
                        else pd.NaT)
    return df.reset_index(drop=True)


def _flag(df, mask, test, severity, reason):
    out = df[mask].copy()
    out["Test"] = test
    out["Severity"] = severity
    out["Reason"] = reason if isinstance(reason, str) else reason[mask].values
    return out


# ---------------------------------------------------------------- detectors
def weekend_postings(df, privileged_users=("admin", "cfo.override")):
    """Weekend postings (Sat/Sun). High if by a privileged user."""
    wk = df["Posting_Date"].dt.weekday >= 5
    m = wk & (df["Amount"] > 0)
    out = df[m].copy()
    out["Test"] = "Weekend posting"
    out["Severity"] = np.where(out["User"].isin(privileged_users), "High", "Medium")
    out["Reason"] = (out["Posting_Date"].dt.day_name() + " posting by '" + out["User"]
                     + "' of " + out["Amount"].map("{:,.2f}".format))
    return out


def round_amounts(df, min_amount=10000):
    """Large round-number entries (multiples of 10,000) — a classic fraud indicator."""
    m = (df["Amount"] >= min_amount) & (df["Amount"] % 10000 == 0)
    return _flag(df, m, "Round-number amount", "Medium",
                 "Large round amount - possible estimate/override rather than a real invoice")


def duplicate_entries(df):
    """Same account, amount, date and user posted more than once."""
    d = df[df["Amount"] > 0]
    key = ["Account_Code", "Posting_Date", "Amount", "User", "Description"]
    dup = d[d.duplicated(subset=key, keep=False)]
    # offsetting lines inside one journal are not duplicates: require >1 distinct JE
    n_je = dup.groupby(key)["JE_ID"].transform("nunique")
    dup = dup[n_je > 1].copy()
    dup["Test"] = "Duplicate entry"
    dup["Severity"] = "High"
    dup["Reason"] = "Identical account/amount/date/user posted in multiple journals"
    return dup


def period_end_manual(df, days=2):
    """Manual journals posted in the last days of a month (cut-off risk)."""
    month_end = df["Posting_Date"] + pd.offsets.MonthEnd(0)
    near = (month_end - df["Posting_Date"]).dt.days < days
    manual = df["Source"].astype(str).str.lower().eq("manual")
    m = near & manual & (df["Amount"] >= 100000)
    return _flag(df, m, "Period-end manual journal", "Medium",
                 "Large manual journal at period end - check cut-off and support")


def outlier_amounts(df, z=3.0):
    """Amount outliers within each account using a robust z-score (median/MAD)."""
    d = df[df["Amount"] > 0].copy()
    # log-scale z-score per account, since ledger amounts are heavily right-skewed
    d["lr"] = np.log1p(d["Amount"])
    lg = d.groupby("Account_Code")["lr"]
    d["lz"] = (d["lr"] - lg.transform("mean")) / lg.transform("std").replace(0, np.nan)
    m = (d["lz"] > z)
    out = d[m].copy()
    out["Test"] = "Statistical outlier"
    out["Severity"] = np.where(out["lz"] > z + 1, "High", "Medium")
    out["Reason"] = ("Amount is " + out["lz"].round(1).astype(str)
                     + " std-devs above normal for account " + out["Account_Code"])
    return out.drop(columns=["lr", "lz"])


def monthly_variance(df, z=2.0, min_abs=50000):
    """Variance analysis: net movement per account per month vs that account's
    own monthly average. Flags months that deviate strongly (z-score) AND are
    material (absolute difference >= min_abs).

    Returns a table sorted by |z|: Account, Month, Net_Movement, Avg_Monthly,
    Variance_Amt, Variance_Pct, Z_Score, Flag, Side, Activity_vs_Avg_Pct.
    """
    d = df.copy()
    d["Month"] = d["Posting_Date"].dt.to_period("M").astype(str)
    d["Net"] = d["Debit"] - d["Credit"]
    g = d.groupby(["Account_Code", "Account_Name", "Month"], as_index=False)["Net"].sum()
    g = g.rename(columns={"Net": "Net_Movement"})
    grp = g.groupby("Account_Code")["Net_Movement"]
    g["Avg_Monthly"] = grp.transform("mean")
    std = grp.transform("std").replace(0, np.nan)
    g["Variance_Amt"] = g["Net_Movement"] - g["Avg_Monthly"]
    g["Variance_Pct"] = (g["Variance_Amt"] / g["Avg_Monthly"].abs().replace(0, np.nan) * 100).round(1)
    g["Z_Score"] = (g["Variance_Amt"] / std).round(2)
    g["Flag"] = (g["Z_Score"].abs() >= z) & (g["Variance_Amt"].abs() >= min_abs)
    # Plain-English size of the month's activity vs the account's usual activity. A revenue account has a
    # NET CREDIT, shown as a negative number, so the signed percentage above can mislead: use this one.
    g["Side"] = np.where(g["Net_Movement"] < 0, "Net credit", "Net debit")
    g["Activity_vs_Avg_Pct"] = ((g["Net_Movement"].abs() - g["Avg_Monthly"].abs())
                                / g["Avg_Monthly"].abs().replace(0, np.nan) * 100).round(1)
    for c in ["Net_Movement", "Avg_Monthly", "Variance_Amt"]:
        g[c] = g[c].round(2)
    return g.reindex(g["Z_Score"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def just_below_limit(df, limit=50000, band=0.01):
    """Amounts just under an approval limit (possible split / threshold avoidance)."""
    lo = limit * (1 - band)
    m = (df["Amount"] >= lo) & (df["Amount"] < limit)
    return _flag(df, m, "Just below approval limit", "High",
                 f"Amount within {band:.0%} below the {limit:,.0f} approval limit")


def privileged_user_manual(df, privileged_users=("admin", "cfo.override"), min_amount=100000):
    """Large manual entries by privileged / override users."""
    manual = df["Source"].astype(str).str.lower().eq("manual")
    m = df["User"].isin(privileged_users) & manual & (df["Amount"] >= min_amount)
    return _flag(df, m, "Privileged-user large manual entry", "High",
                 "Large manual entry posted by a privileged/override user")


def benford_analysis(df):
    """First-digit (Benford) test. Returns (table, chi_square, flagged_bool)."""
    a = df.loc[df["Amount"] >= 10, "Amount"]
    first = a.astype(str).str.replace(r"[^0-9]", "", regex=True).str.lstrip("0").str[0]
    first = pd.to_numeric(first, errors="coerce").dropna().astype(int)
    first = first[first.between(1, 9)]
    n = len(first)
    obs = first.value_counts().reindex(range(1, 10), fill_value=0)
    exp_p = np.log10(1 + 1 / np.arange(1, 10))
    table = pd.DataFrame({
        "Digit": range(1, 10),
        "Actual %": (obs.values / n * 100).round(2),
        "Benford %": (exp_p * 100).round(2),
    })
    table["Deviation (pp)"] = (table["Actual %"] - table["Benford %"]).round(2)
    chi = float((((obs.values - exp_p * n) ** 2) / (exp_p * n)).sum())
    return table, chi, chi > 15.51        # 8 d.o.f., 5% critical value


def _no_flags(df, test):
    out = df.iloc[0:0].copy()
    out["Test"], out["Severity"], out["Reason"] = [], [], []
    return out


def _is_manual_or_override(df):
    return df["Source"].astype(str).str.lower().eq("manual") | df["Override"].eq("Y")


def override_without_approval(df):
    """Manual / override journals with no approver recorded, or approved by the person who posted them."""
    if (df["Approved_By"] == "N/A").all():
        return _no_flags(df, "Override without approval / self-approval")
    appr = df["Approved_By"].str.lower()
    none = appr.eq("")
    selfa = appr.eq(df["User"].astype(str).str.lower()) & ~none
    m = _is_manual_or_override(df) & (none | selfa) & (df["Amount"] > 0)
    reason = np.where(none, "No approver recorded on a manual/override journal",
                      "Approved by the same user who posted it (no segregation of duties)")
    return _flag(df, m, "Override without approval / self-approval", "High", pd.Series(reason, index=df.index))


def after_hours_posting(df, start_hour=22, end_hour=5):
    """Manual/override journals posted between 22:00 and 05:00."""
    if (df["Posting_Time"] == "").all():
        return _no_flags(df, "After-hours posting")
    hour = pd.to_numeric(df["Posting_Time"].str.slice(0, 2), errors="coerce")
    m = _is_manual_or_override(df) & ((hour >= start_hour) | (hour < end_hour)) & (df["Amount"] > 0)
    return _flag(df, m, "After-hours posting", "Medium",
                 pd.Series("Posted at " + df["Posting_Time"] + " (outside normal business hours)", index=df.index))


def backdated_entries(df, max_days=30):
    """Posting date far before the date the entry was keyed in, or after it (future-dated)."""
    if df["Entry_Date"].isna().all():
        return _no_flags(df, "Back-dated / future-dated entry")
    lag = (df["Entry_Date"] - df["Posting_Date"]).dt.days
    m = ((lag > max_days) | (lag < 0)) & (df["Amount"] > 0)
    reason = np.where(lag > max_days, "Entered " + lag.astype("Int64").astype(str) + " days after its posting date (back-dated)",
                      "Posting date is after the date it was entered (future-dated)")
    return _flag(df, m, "Back-dated / future-dated entry", "Medium", pd.Series(reason, index=df.index))


def debit_credit_imbalance(df, tolerance=0.01):
    """Journals whose debits and credits do not agree."""
    diff = (df.groupby("JE_ID")["Debit"].sum() - df.groupby("JE_ID")["Credit"].sum()).abs()
    bad = diff[diff > tolerance]
    m = df["JE_ID"].isin(bad.index)
    reason = df["JE_ID"].map(bad).map(lambda v: f"Debits and credits differ by {v:,.2f}" if pd.notna(v) else "")
    return _flag(df, m, "Debit-credit imbalance", "High", reason)


def rare_user_large_entry(df, max_journals=2, min_amount=100000):
    """Large manual entries posted by a user who hardly ever posts."""
    n = df.groupby("User")["JE_ID"].nunique()
    rare = n[n <= max_journals].index
    m = df["User"].isin(rare) & _is_manual_or_override(df) & (df["Amount"] >= min_amount)
    return _flag(df, m, "Rare user large entry", "Medium",
                 "Large manual entry by a user who posted very few journals in the period")


ALL_TESTS = [weekend_postings, round_amounts, duplicate_entries, period_end_manual,
             outlier_amounts, just_below_limit, privileged_user_manual,
             override_without_approval, after_hours_posting, backdated_entries,
             debit_credit_imbalance, rare_user_large_entry]


def run_all_detectors(df, enabled=None, params=None):
    """Run every enabled detector and return one combined flag table."""
    params = params or {}
    frames = []
    for fn in ALL_TESTS:
        if enabled is not None and fn.__name__ not in enabled:
            continue
        frames.append(fn(df, **params.get(fn.__name__, {})))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    return out


def risk_score_by_journal(flags: pd.DataFrame) -> pd.DataFrame:
    """Aggregate flags into one risk score per journal entry."""
    if flags.empty:
        return pd.DataFrame(columns=["JE_ID", "Risk_Score", "Tests_Triggered", "Max_Severity"])
    f = flags.copy()
    f["pts"] = f["Severity"].map(SEVERITY_POINTS)
    # count each test once per journal
    per = f.drop_duplicates(["JE_ID", "Test"])
    g = per.groupby("JE_ID").agg(
        Risk_Score=("pts", "sum"),
        Tests_Triggered=("Test", lambda s: ", ".join(sorted(s))),
        Max_Severity=("Severity", lambda s: max(s, key=SEVERITY_POINTS.get)),
    ).reset_index()
    return g.sort_values("Risk_Score", ascending=False).reset_index(drop=True)


# ==========================================================================
# SECTION 3: Sample data
# ==========================================================================

def generate_sample_ledger() -> pd.DataFrame:
    """Synthetic general ledger (about 3,400 lines) with planted anomalies. All data is fictional."""
    rng = np.random.default_rng(42)
    ACCOUNTS = {
        "4000": "Sales Revenue", "5000": "Cost of Sales", "5100": "Salaries & Wages",
        "5200": "Rent Expense", "5300": "Utilities", "5400": "Travel & Entertainment",
        "5500": "Professional Fees", "5600": "Repairs & Maintenance", "1000": "Cash at Bank",
        "1200": "Trade Receivables", "2000": "Trade Payables", "3000": "Owner Current Account",
    }
    users = ["a.khan", "s.mathew", "r.nair", "m.hassan"]
    rows, st_ = [], {"je": 1000}

    rng2 = np.random.default_rng(7)                        # separate generator: keeps the main data identical
    approvers = ["fin.controller", "chief.accountant"]
    last = {}

    def ex(d=None):
        """Extra columns for a normal system entry: office-hours time, an approver, no override."""
        t = f"{int(rng2.integers(8, 18)):02d}:{int(rng2.integers(0, 60)):02d}:{int(rng2.integers(0, 60)):02d}"
        last["v"] = [t, approvers[int(rng2.integers(0, 2))], "N", None]
        return list(last["v"])

    def ex_last():
        v = list(last["v"])
        return v

    def business_day():
        start = pd.Timestamp("2025-01-01")
        while True:
            d = start + pd.Timedelta(days=int(rng.integers(0, 365)))
            if d.weekday() < 5:
                return d

    for _ in range(1200):                                  # normal expenses
        st_["je"] += 1
        exp = rng.choice(["5000", "5100", "5200", "5300", "5400", "5500", "5600"])
        amt = round(float(rng.lognormal(mean=7.6, sigma=1.3)), 2)
        d, user = business_day(), rng.choice(users)
        cr = rng.choice(["1000", "2000"])
        desc = f"{ACCOUNTS[exp]} - routine posting"
        rows.append([f"JE{st_['je']}", d, exp, ACCOUNTS[exp], desc, amt, 0.0, user, "System"] + ex())
        rows.append([f"JE{st_['je']}", d, cr, ACCOUNTS[cr], desc, 0.0, amt, user, "System"] + ex_last())
    for _ in range(500):                                   # normal sales
        st_["je"] += 1
        amt = round(float(rng.lognormal(mean=8.4, sigma=1.2)), 2)
        d, user = business_day(), rng.choice(users)
        dr = rng.choice(["1000", "1200"])
        rows.append([f"JE{st_['je']}", d, dr, ACCOUNTS[dr], "Sales invoice posting", amt, 0.0, user, "System"] + ex(d))
        rows.append([f"JE{st_['je']}", d, "4000", ACCOUNTS["4000"], "Sales invoice posting", 0.0, amt, user, "System"] + ex_last())

    def add(acc, desc, amt, dt, user, source="Manual", side="Dr", offset="1000",
            time="11:00:00", approved="fin.controller", override="N", entered=None):
        st_["je"] += 1
        d1, c1 = (amt, 0.0) if side == "Dr" else (0.0, amt)
        ent = pd.Timestamp(entered) if entered else pd.Timestamp(dt)
        extra = [time, approved, override, ent]
        rows.append([f"JE{st_['je']}", pd.Timestamp(dt), acc, ACCOUNTS[acc], desc, d1, c1, user, source] + extra)
        rows.append([f"JE{st_['je']}", pd.Timestamp(dt), offset, ACCOUNTS[offset], desc, c1, d1, user, source] + extra)

    add("5500", "Consulting fee - urgent settlement", 185000, "2025-03-08", "cfo.override", time="23:15:08", approved="", override="Y")   # Saturday
    add("5400", "Management retreat advance", 96500, "2025-06-14", "admin", time="02:40:31", approved="admin", override="Y")                   # Saturday
    add("3000", "Owner drawings adjustment", 250000, "2025-09-21", "cfo.override", time="14:05:12", approved="", override="Y")            # Sunday
    add("5600", "Emergency repair - no PO", 74000, "2025-11-02", "admin", time="22:30:45", approved="admin", override="Y")                     # Sunday
    add("5500", "Advisory services", 100000, "2025-04-10", "m.hassan")                        # round amounts
    add("5400", "Client entertainment", 50000, "2025-07-17", "r.nair")
    add("5600", "Maintenance accrual", 200000, "2025-10-09", "admin", time="03:12:40", approved="", override="Y")
    for _ in range(2):                                                                       # duplicates
        add("5500", "Legal retainer - Q2", 38750.00, "2025-05-12", "a.khan")
    for _ in range(3):
        add("5300", "Utility bill adjustment", 12640.50, "2025-08-20", "s.mathew")
    add("4000", "Revenue accrual - period end", 480000, "2025-12-31", "cfo.override", side="Cr", offset="1200", time="23:48:02", approved="", override="Y")
    add("4000", "Revenue cut-off adjustment", 365000, "2025-12-30", "admin", side="Cr", offset="1200", time="16:20:00", approved="admin", override="Y")
    add("5100", "Special bonus - unapproved", 640000, "2025-02-26", "admin", time="01:55:19", approved="", override="Y")                 # outliers
    add("5200", "Rent - prepayment", 910000, "2025-01-15", "cfo.override", time="10:10:10", approved="cfo.override", override="Y")
    for i, dt in enumerate(["2025-03-03", "2025-03-04", "2025-03-05", "2025-03-06"]):         # just below limit
        add("5600", f"Repairs - vendor split invoice {i+1}", 49900 + i * 10, dt, "m.hassan")

    # extra planted control failures
    add("5100", "Year-end bonus accrual - back-dated", 150000, "2025-09-30", "admin",
        time="15:30:00", approved="", override="Y", entered="2025-12-15")                       # back-dated 76 days
    add("5300", "Utilities accrual - future dated", 42000, "2026-01-20", "s.mathew",
        approved="chief.accountant", entered="2025-12-22")                                      # future-dated
    add("5400", "Contractor payment - temp account", 175000, "2025-07-23", "temp.user",
        time="09:45:00", approved="", override="Y")                                             # rare user, no approval
    st_["je"] += 1                                                                              # unbalanced journal
    rows.append([f"JE{st_['je']}", pd.Timestamp("2025-06-18"), "5400", ACCOUNTS["5400"], "Staff incentive accrual",
                 120000.0, 0.0, "r.nair", "Manual", "11:20:00", "fin.controller", "N", pd.Timestamp("2025-06-18")])
    rows.append([f"JE{st_['je']}", pd.Timestamp("2025-06-18"), "2000", ACCOUNTS["2000"], "Staff incentive accrual",
                 0.0, 119150.0, "r.nair", "Manual", "11:20:00", "fin.controller", "N", pd.Timestamp("2025-06-18")])

    df = pd.DataFrame(rows, columns=["JE_ID", "Posting_Date", "Account_Code", "Account_Name",
                                     "Description", "Debit", "Credit", "User", "Source",
                                     "Posting_Time", "Approved_By", "Override", "Entry_Date"])
    df["Entry_Date"] = df["Entry_Date"].fillna(df["Posting_Date"])
    return df.sort_values(["Posting_Date", "JE_ID"]).reset_index(drop=True)



# ==========================================================================
# SECTION 4: Agents
# ==========================================================================
MAX_LLM_JOURNALS = 4       # journals the LLM investigates via tools (highest risk first); free API plans have token limits
MAX_TOOL_ROUNDS = 40       # safety cap on the tool-calling loop

RECOMMENDATIONS = {
    "Weekend posting": "Obtain approval evidence and business reason for the weekend posting; review user access logs.",
    "Round-number amount": "Vouch to third-party support (invoice/contract); round amounts often indicate estimates or overrides.",
    "Duplicate entry": "Check for duplicate invoices/payments; reverse and recover any amount posted twice.",
    "Period-end manual journal": "Test cut-off: confirm the item belongs to the period and review subsequent-period reversals.",
    "Statistical outlier": "Investigate why the amount is far outside the account's normal range; obtain board/CFO approval.",
    "Just below approval limit": "Review for split transactions to avoid approval limits; check the vendor and approver.",
    "Privileged-user large manual entry": "Review segregation of duties; confirm a second approver exists for override-user entries.",
    "Override without approval / self-approval": "Obtain the missing approval or reverse the entry; enforce independent approval for every override or manual journal.",
    "After-hours posting": "Ask the user why the entry was posted at night; review system access logs for that time.",
    "Back-dated / future-dated entry": "Check whether the period was already closed; confirm who authorised posting into another period.",
    "Debit-credit imbalance": "Investigate how an unbalanced journal was accepted; correct it and fix the system validation.",
    "Rare user large entry": "Confirm the user's identity and role, and why such a large entry came from an infrequent user.",
}


@dataclass
class AgentLog:
    steps: list = field(default_factory=list)

    def add(self, agent, message):
        self.steps.append({"Agent": agent, "Action": message})

    def to_df(self):
        return pd.DataFrame(self.steps)


# ============================================================ Agent 1
class DetectorAgent:
    name = "Agent 1 - Detector"

    def run(self, df, enabled, params, log):
        log.add(self.name, f"Loaded {len(df):,} ledger lines / {df['JE_ID'].nunique():,} journals")
        flags = run_all_detectors(df, enabled, params)
        scores = risk_score_by_journal(flags)
        log.add(self.name, f"Ran {len(enabled)} tests -> {len(flags):,} flags on {len(scores)} journals")
        variance = monthly_variance(df)
        log.add(self.name, f"Variance analysis: {int(variance['Flag'].sum())} account-months deviate materially")
        benford, chi, benford_flag = benford_analysis(df)
        log.add(self.name, f"Benford first-digit test: chi-square={chi:.1f} "
                           f"({'DEVIATES' if benford_flag else 'conforms'})")
        return {"flags": flags, "scores": scores, "variance": variance, "benford": benford,
                "chi": chi, "benford_flag": benford_flag}


# ============================================================ tools for the LLM
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "list_flagged_journals",
        "description": "List the highest-risk flagged journals (id, risk score, tests triggered).",
        "parameters": {"type": "object", "properties": {
            "limit": {"type": "integer", "description": "How many journals to return (default 10)"}}}}},
    {"type": "function", "function": {
        "name": "get_journal_lines",
        "description": "Get all ledger lines of one journal entry (date, account, description, debit, credit, user, source).",
        "parameters": {"type": "object", "properties": {
            "je_id": {"type": "string"}}, "required": ["je_id"]}}},
    {"type": "function", "function": {
        "name": "get_user_activity",
        "description": "Summarise a user's activity: journals posted, weekend postings, manual entries, flagged journals, total amount.",
        "parameters": {"type": "object", "properties": {
            "user": {"type": "string"}}, "required": ["user"]}}},
    {"type": "function", "function": {
        "name": "get_account_variance",
        "description": "Monthly variance analysis for one account code (net movement vs the account's monthly average).",
        "parameters": {"type": "object", "properties": {
            "account_code": {"type": "string"}}, "required": ["account_code"]}}},
    {"type": "function", "function": {
        "name": "record_finding",
        "description": "Record your final audit assessment for one journal. Call once per investigated journal.",
        "parameters": {"type": "object", "properties": {
            "je_id": {"type": "string"},
            "risk_level": {"type": "string", "enum": ["CRITICAL", "HIGH", "MODERATE"]},
            "assessment": {"type": "string", "description": "2-3 sentence professional assessment of why this entry is risky"},
            "procedures": {"type": "array", "items": {"type": "string"},
                           "description": "Recommended audit procedures"}},
            "required": ["je_id", "risk_level", "assessment", "procedures"]}}},
]


class ToolBox:
    """Python functions the LLM can call. Every tool returns a JSON string."""

    def __init__(self, df, detector_out):
        self.df = df
        self.flags = detector_out["flags"]
        self.scores = detector_out["scores"]
        self.variance = detector_out["variance"]
        self.recorded = {}          # je_id -> finding dict recorded by the LLM

    def call(self, name, args):
        try:
            fn = getattr(self, f"_t_{name}", None)
            if fn is None:
                return json.dumps({"error": f"unknown tool {name}"})
            return json.dumps(fn(**args), default=str)
        except Exception as e:      # never let a bad tool call crash the loop
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    def _t_list_flagged_journals(self, limit=10):
        return self.scores.head(int(limit)).to_dict("records")

    def _t_get_journal_lines(self, je_id):
        cols = ["Posting_Date", "Posting_Time", "Account_Code", "Description", "Debit", "Credit", "User", "Source", "Override", "Approved_By"]
        lines = self.df[self.df["JE_ID"] == je_id][cols].copy()
        lines["Posting_Date"] = lines["Posting_Date"].dt.strftime("%Y-%m-%d %a")
        return lines.to_dict("records") or {"error": "journal not found"}

    def _t_get_user_activity(self, user):
        u = self.df[self.df["User"] == user]
        if u.empty:
            return {"error": "user not found"}
        je = u.drop_duplicates("JE_ID")
        flagged = self.scores[self.scores["JE_ID"].isin(je["JE_ID"])]
        return {"user": user, "journals_posted": int(je["JE_ID"].nunique()),
                "weekend_journals": int((je["Posting_Date"].dt.weekday >= 5).sum()),
                "manual_journals": int(je["Source"].astype(str).str.lower().eq("manual").sum()),
                "flagged_journals": int(len(flagged)),
                "largest_amount": float(u["Amount"].max())}

    def _t_get_account_variance(self, account_code):
        v = self.variance[self.variance["Account_Code"] == str(account_code)]
        return v.sort_values("Month")[["Month", "Net_Movement", "Avg_Monthly",
                                       "Variance_Pct", "Z_Score", "Flag"]].to_dict("records") \
            or {"error": "account not found"}

    def _t_record_finding(self, je_id, risk_level, assessment, procedures):
        self.recorded[je_id] = {"risk_level": risk_level, "assessment": assessment,
                                "procedures": list(procedures)}
        return {"status": "recorded", "je_id": je_id}


# ============================================================ Agent 2
class InvestigatorAgent:
    name = "Agent 2 - Investigator"

    def run(self, df, detector_out, log, escalation_threshold=7, max_llm=MAX_LLM_JOURNALS):
        scores = detector_out["scores"]
        llm_findings = {}
        if len(scores) and supports_tools():
            llm_findings = self._run_llm(df, detector_out, log, max_llm)
        elif len(scores):
            log.add(self.name, "No LLM configured - using offline rule-based investigation")

        findings = []
        for _, s in scores.iterrows():
            base = self._offline_finding(df, detector_out["flags"], s, escalation_threshold)
            rec = llm_findings.get(s["JE_ID"])
            if rec:                                  # LLM investigated this journal via tools
                base["Narrative"] = rec["assessment"]
                base["Procedures"] = rec["procedures"] or base["Procedures"]
                base["Analysed_By"] = "LLM tool-calling"
            findings.append(base)
        crit = sum(1 for f in findings if f["Risk_Level"] == "CRITICAL")
        log.add(self.name, f"Investigated {len(findings)} journals; {crit} CRITICAL "
                           f"({len(llm_findings)} analysed by LLM, rest by rules)")
        return pd.DataFrame(findings)

    # ---- LLM tool-calling loop (the "agentic" part)
    def _run_llm(self, df, detector_out, log, max_llm=MAX_LLM_JOURNALS):
        box = ToolBox(df, detector_out)
        target = min(int(max_llm), len(detector_out["scores"]))
        top = detector_out["scores"].head(target)
        listing = "; ".join(f"{r.JE_ID} (score {r.Risk_Score}: {r.Tests_Triggered})" for r in top.itertuples())
        messages = [
            {"role": "system", "content":
                "You are a senior audit manager investigating suspicious general-ledger journals. "
                "Use the tools to inspect evidence before judging. Do not invent facts."},
            {"role": "user", "content":
                f"Investigate these {target} highest-risk journals: {listing}. For each: call "
                "get_journal_lines (use get_user_activity / get_account_variance only if useful), "
                "then call record_finding once with a short assessment and procedures. "
                "When all are recorded, reply DONE."},
        ]
        n_calls = 0
        for _ in range(MAX_TOOL_ROUNDS):
            msg = chat(messages, TOOL_SCHEMAS)
            if msg is None:
                log.add(self.name, f"LLM call failed - falling back to rules ({last_error()[:600]})")
                break
            calls = msg.get("tool_calls") or []
            # send back only the standard fields (providers may add extras that they reject)
            assistant = {"role": "assistant", "content": msg.get("content")}
            if calls:
                assistant["tool_calls"] = [
                    {"id": c["id"], "type": "function",
                     "function": {"name": c["function"]["name"],
                                  "arguments": c["function"].get("arguments") or "{}"}} for c in calls]
            messages.append(assistant)
            if not calls:                       # conditional exit: model has finished
                break
            for c in calls:
                n_calls += 1
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = box.call(c["function"]["name"], args)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": result})
            if len(box.recorded) >= target:
                break
        log.add(self.name, f"LLM tool-calling: {n_calls} tool calls, {len(box.recorded)} findings recorded")
        return box.recorded

    # ---- offline rule-based investigation (also used for journals the LLM did not cover)
    @staticmethod
    def _offline_finding(df, flags, s, escalation_threshold):
        lines = df[df["JE_ID"] == s["JE_ID"]]
        top = lines.loc[lines["Amount"].idxmax()]
        je_flags = flags[flags["JE_ID"] == s["JE_ID"]].drop_duplicates("Test")
        tests = list(je_flags["Test"])
        if s["Risk_Score"] >= escalation_threshold:      # conditional escalation
            level = "CRITICAL"
        elif s["Risk_Score"] >= 3:
            level = "HIGH"
        else:
            level = "MODERATE"
        narrative = (
            f"Journal {s['JE_ID']} dated {top['Posting_Date']:%d-%b-%Y} was posted by "
            f"'{top['User']}' to {top['Account_Name']} ({top['Account_Code']}) for "
            f"{top['Amount']:,.2f} with description \"{top['Description']}\". "
            f"It triggered {len(tests)} test(s): {', '.join(tests)}.")
        return {
            "JE_ID": s["JE_ID"], "Date": top["Posting_Date"], "User": top["User"],
            "Account": f"{top['Account_Code']} {top['Account_Name']}",
            "Amount": float(top["Amount"]), "Risk_Score": int(s["Risk_Score"]),
            "Risk_Level": level, "Tests": ", ".join(tests), "Narrative": narrative,
            "Procedures": [RECOMMENDATIONS[t] for t in tests if t in RECOMMENDATIONS],
            "Analysed_By": "Rules",
        }


# ============================================================ Agent 3
class LetterAgent:
    name = "Agent 3 - Letter Drafter"

    def run(self, findings, detector_out, company, period, auditor, log):
        today = date.today().strftime("%d %B %Y")
        if len(findings) == 0:
            log.add(self.name, "No findings - drafted clean letter")
            return self._wrap(company, period, auditor, today,
                              "Our journal-entry testing did not identify any entries that "
                              "require management's attention.", [], source="Template")

        template = self._template_letter(findings, detector_out, company, period, auditor, today)

        if is_enabled():
            text = self._llm_letter(findings, detector_out, company, period, auditor, today)
            if text:
                log.add(self.name, "Management Letter generated by the LLM from the extreme anomalies")
                return {"text": text, "points": template["points"], "intro": "", "source": "LLM"}
            log.add(self.name, f"LLM letter failed - used template ({last_error()[:600]})")
        log.add(self.name, f"Drafted Management Letter from template with {len(template['points'])} finding(s)")
        return template

    def _llm_letter(self, findings, d_out, company, period, auditor, today):
        top = findings.sort_values("Risk_Score", ascending=False).head(8)
        flags = d_out["flags"].drop_duplicates(["JE_ID", "Test"])
        by_test = {}
        for test, grp in flags.groupby("Test"):
            ids = grp["JE_ID"].tolist()
            by_test[test] = {"journals": len(ids), "examples": ids[:6]}
        var = d_out["variance"]
        var = var[var["Flag"]].head(6)
        payload = {
            "company": company, "period": period, "signatory": auditor, "date": today,
            "total_journals_flagged": int(len(findings)),
            "critical_journals": int((findings["Risk_Level"] == "CRITICAL").sum()),
            "journals_flagged_by_test": by_test,
            "top_anomalies": [
                {"je_id": r.JE_ID, "date": f"{r.Date:%Y-%m-%d}", "user": r.User, "account": r.Account,
                 "amount_aed": r.Amount, "risk": r.Risk_Level, "tests": r.Tests} for r in top.itertuples()],
            "benford": {"chi_square": round(d_out["chi"], 1), "deviates": bool(d_out["benford_flag"])},
            "material_monthly_variances": [
                {"account": r.Account_Name, "month": r.Month, "net_movement_aed": abs(r.Net_Movement),
                 "side": r.Side, "usual_monthly_aed": abs(r.Avg_Monthly),
                 "activity_vs_usual_pct": r.Activity_vs_Avg_Pct} for r in var.itertuples()],
        }
        prompt = ("Draft a formal audit Management Letter (plain text, no markdown) addressed to the Board, "
                  "based ONLY on this JSON of results from automated journal-entry testing.\n"
                  "Structure: short intro; numbered findings, each with Observation and Recommendation; "
                  "closing paragraph saying the findings are a draft that needs auditor validation.\n"
                  "Rules:\n"
                  "- Cover EVERY test listed in journals_flagged_by_test (for example duplicate entries and weekend "
                  "postings), not only the top anomalies. Group similar journals in one finding and cite example journal ids.\n"
                  "- Include one finding on material_monthly_variances (the account-months that moved most versus "
                  "usual, with amounts) and one short note on the Benford result.\n"
                  "- Use neutral, factual wording such as 'may indicate a control weakness'. Do NOT allege fraud, "
                  "kick-backs or misappropriation, and do NOT say approvals are missing: the data has no approval information.\n"
                  "- Do not invent journals, amounts or facts.\n"
                  "- activity_vs_usual_pct is how much bigger (+) or smaller (-) the month's activity was than the "
                  "account's usual month. A positive value means MORE activity than usual, including for revenue.\n\n"
                  + json.dumps(payload, default=str))
        text = ask(prompt, system="You are an experienced audit partner drafting a management letter.",
                   max_tokens=3500)
        return text.strip() if text and len(text.strip()) > 200 else None

    def _template_letter(self, findings, d_out, company, period, auditor, today):
        n = len(findings)
        crit = findings[findings["Risk_Level"] == "CRITICAL"]
        by_test = (d_out["flags"].drop_duplicates(["JE_ID", "Test"])
                   .groupby("Test")["JE_ID"].nunique().sort_values(ascending=False))
        total_amt = findings["Amount"].sum()
        intro = (f"During our review of the general ledger for {period}, we applied "
                 f"data-analytic tests to all journal entries. {n} journal(s) with a "
                 f"combined value of AED {total_amt:,.0f} were flagged, of which "
                 f"{len(crit)} are rated critical. The matters below require management's attention.")
        points = []
        for i, (test, count) in enumerate(by_test.items(), 1):
            ex = findings[findings["Tests"].str.contains(test, regex=False)].head(3)
            examples = "; ".join(f"{r.JE_ID} (AED {r.Amount:,.0f})" for r in ex.itertuples())
            points.append({
                "title": f"{i}. {test} ({count} journal(s))",
                "observation": f"Examples: {examples}.",
                "recommendation": RECOMMENDATIONS.get(test, "Management should review and document the business rationale."),
            })
        var = d_out["variance"]
        var = var[var["Flag"]].head(3)
        if len(var):
            ex = "; ".join(f"{r.Account_Name} in {r.Month} (activity {r.Activity_vs_Avg_Pct:+.0f}% vs its monthly average, {r.Side.lower()})"
                           for r in var.itertuples())
            points.append({
                "title": f"{len(points)+1}. Unusual monthly movements (variance analysis)",
                "observation": f"Material deviations from the account's normal monthly level: {ex}.",
                "recommendation": "Obtain explanations and supporting documents for the movements; confirm they are not misstatements.",
            })
        if d_out["benford_flag"]:
            points.append({
                "title": f"{len(points)+1}. First-digit distribution deviates from Benford's Law",
                "observation": f"Chi-square statistic {d_out['chi']:.1f} exceeds the 5% critical value (15.51).",
                "recommendation": "Perform a deeper review of the digits with the largest deviations for manipulation or systematic estimates.",
            })
        return self._wrap(company, period, auditor, today, intro, points, source="Template")

    @staticmethod
    def _wrap(company, period, auditor, today, intro, points, source):
        lines = [f"{auditor}", f"{today}", "", "The Board of Directors", f"{company}", "",
                 f"Subject: Management Letter - Journal Entry Testing for {period}", "",
                 "Dear Sirs,", "", intro, ""]
        for p in points:
            lines += [p["title"], f"   Observation: {p['observation']}",
                      f"   Recommendation: {p['recommendation']}", ""]
        lines += ["This letter is draft output of automated analytics and does not replace "
                  "auditor judgment. Findings should be validated before issue.", "",
                  "Yours faithfully,", auditor]
        return {"text": "\n".join(lines), "points": points, "intro": intro, "source": source}


# ============================================================ Orchestrator
def run_pipeline(df, enabled, params, company, period, auditor, llm_journals=MAX_LLM_JOURNALS):
    """Orchestrator: Agent 1 -> Agent 2 -> Agent 3."""
    log = AgentLog()
    d_out = DetectorAgent().run(df, enabled, params, log)
    findings = InvestigatorAgent().run(df, d_out, log, max_llm=llm_journals)
    letter = LetterAgent().run(findings, d_out, company, period, auditor, log)
    return {"detector": d_out, "findings": findings, "letter": letter, "log": log.to_df()}


# ==========================================================================
# SECTION 5: Export  (Word letter + formatted Excel report)
# ==========================================================================
NAVY, LIGHT, WHITE = "1F3864", "D9E2F3", "FFFFFF"
LEVEL_FILL = {"CRITICAL": "F4B6B6", "HIGH": "FAD7A0", "MODERATE": "FFF2CC"}

TEST_EXPLAINED = {
    "Weekend posting": "Journal posted on a Saturday or Sunday (higher severity for privileged users).",
    "Round-number amount": "Large amount that is an exact round figure, which can indicate an estimate or a plug.",
    "Duplicate entry": "Same date, account, amount and description posted under different journal numbers.",
    "Period-end manual journal": "Large manual journal posted in the last days of the period (cut-off risk).",
    "Statistical outlier": "Amount far outside the usual range for that account (log-scale z-score).",
    "Just below approval limit": "Amount just under the approval limit, which can indicate split or avoided approval.",
    "Privileged-user large manual entry": "Large manual entry posted by an admin or override user.",
    "Override without approval / self-approval": "Manual or override journal with no approver, or approved by the person who posted it.",
    "After-hours posting": "Manual or override journal posted between 22:00 and 05:00.",
    "Back-dated / future-dated entry": "Posting date is more than 30 days before the entry date, or after it.",
    "Debit-credit imbalance": "Total debits and credits of the journal do not agree.",
    "Rare user large entry": "Large manual entry by a user who posted two journals or fewer in the whole period.",
}


def report_meta(df, res, company, period, auditor, params=None):
    """Numbers and names used on the report cover / summary sheet."""
    f = res["findings"]
    lv = f["Risk_Level"].value_counts() if len(f) else {}
    return {
        "company": company, "period": period, "auditor": auditor, "params": params or {},
        "date": f"{date.today():%d %B %Y}",
        "lines": int(len(df)), "journals": int(df["JE_ID"].nunique()),
        "flagged": int(len(f)),
        "critical": int(lv.get("CRITICAL", 0)), "high": int(lv.get("HIGH", 0)),
        "moderate": int(lv.get("MODERATE", 0)),
        "flagged_value": float(f["Amount"].sum()) if len(f) else 0.0,
        "benford_chi": float(res["detector"]["chi"]),
        "benford_flag": bool(res["detector"]["benford_flag"]),
        "variances": int(res["detector"]["variance"]["Flag"].sum()),
        "letter_source": res["letter"].get("source", "Template"),
    }


def _shade(cell, hex_fill):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _docx_table(doc, header, rows, widths=None, font=9, level_col=None):
    from docx.shared import RGBColor
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(str(h))
        r.bold, r.font.size, r.font.color.rgb = True, Pt(font), RGBColor(255, 255, 255)
        _shade(c, NAVY)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(v))
            run.font.size = Pt(font)
            if level_col is not None and i == level_col and str(v) in LEVEL_FILL:
                _shade(cells[i], LEVEL_FILL[str(v)])
                run.bold = True
    if widths:
        from docx.shared import Cm
        t.autofit = False
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(w)
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    return t


def _priority(levels):
    return "High" if "CRITICAL" in levels else ("Medium" if "HIGH" in levels else "Low")


def _add_footer(doc, text):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import RGBColor

    def field(par, instr):
        r = par.add_run()
        for kind, val in (("begin", None), (None, instr), ("end", None)):
            if kind:
                el = OxmlElement("w:fldChar")
                el.set(qn("w:fldCharType"), kind)
            else:
                el = OxmlElement("w:instrText")
                el.set(qn("xml:space"), "preserve")
                el.text = val
            r._r.append(el)
        r.font.size = Pt(8)
    for sec in doc.sections:
        p = sec.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text + "   |   Page ")
        r.font.size, r.font.color.rgb = Pt(8), RGBColor(0x7F, 0x7F, 0x7F)
        field(p, "PAGE")
        r2 = p.add_run(" of ")
        r2.font.size, r2.font.color.rgb = Pt(8), RGBColor(0x7F, 0x7F, 0x7F)
        field(p, "NUMPAGES")


def letter_to_docx(letter_text: str, meta: dict = None, findings: pd.DataFrame = None,
                   variance: pd.DataFrame = None) -> bytes:
    from docx.shared import Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)
        s.top_margin = s.bottom_margin = Cm(2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(11)
    for name, size in (("Heading 1", 15), ("Heading 2", 12)):
        st_ = doc.styles[name]
        st_.font.name, st_.font.size = "Calibri", Pt(size)
        st_.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    if meta:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run("MANAGEMENT LETTER")
        r.bold, r.font.size, r.font.color.rgb = True, Pt(22), RGBColor(0x1F, 0x38, 0x64)
        p = doc.add_paragraph()
        r = p.add_run("Review of journal entries, anomalies and system overrides")
        r.font.size, r.italic = Pt(12), True
        _docx_table(doc, ["Item", "Detail"], [
            ["Entity", meta["company"]], ["Period reviewed", meta["period"]],
            ["Date", meta["date"]], ["Prepared by", meta["auditor"]],
            ["Status", "DRAFT - for discussion with management; findings need auditor validation"],
        ], widths=[4, 12.5], font=10)
        doc.add_paragraph()
        doc.add_heading("Executive summary", level=1)
        doc.add_paragraph(
            f"We tested all {meta['journals']:,} journals ({meta['lines']:,} ledger lines) of "
            f"{meta['company']} for {meta['period']} with automated tests. {meta['flagged']} journals "
            f"were flagged, of which {meta['critical']} are rated CRITICAL and {meta['high']} HIGH. "
            f"{meta['variances']} account-months moved materially against their own monthly average. "
            f"The Benford's Law first-digit test "
            + ("deviates from the expected pattern" if meta["benford_flag"] else "conforms to the expected pattern")
            + f" (chi-square {meta['benford_chi']:.1f} against a 15.51 threshold).")
        _docx_table(doc, ["Key figure", "Value", "Key figure", "Value"], [
            ["Journals tested", f"{meta['journals']:,}", "CRITICAL journals", meta["critical"]],
            ["Ledger lines tested", f"{meta['lines']:,}", "HIGH journals", meta["high"]],
            ["Journals flagged", f"{meta['flagged']} ({meta['flagged'] / max(meta['journals'], 1):.1%})",
             "MODERATE journals", meta["moderate"]],
            ["Value of flagged journals", f"{meta['flagged_value']:,.0f}", "Material variances", meta["variances"]],
        ], widths=[4.6, 3.6, 4.6, 3.6], font=10)
        if findings is not None and len(findings):
            doc.add_paragraph()
            doc.add_heading("Summary of observations", level=1)
            rows = []
            tests = {}
            for r in findings.itertuples():
                for t_ in str(r.Tests).split(", "):
                    tests.setdefault(t_, []).append(r.Risk_Level)
            for i, (t_, lv) in enumerate(sorted(tests.items(), key=lambda kv: (-len(kv[1]))), start=1):
                rows.append([i, t_, len(lv), _priority(lv)])
            _docx_table(doc, ["#", "Observation (test)", "Journals", "Priority"], rows,
                        widths=[1.0, 9.6, 2.4, 3.0], font=10, level_col=None)
            doc.add_paragraph("Priority: High = at least one CRITICAL journal; Medium = at least one HIGH journal; "
                              "Low = MODERATE only.").runs[0].italic = True
        doc.add_paragraph()
        doc.add_heading("Letter", level=1)

    for line in letter_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^\d{1,2}\.\s", stripped) and not line.startswith(" "):
            doc.add_heading(stripped, level=2)
            continue
        low = stripped.lower()
        label = next((k for k in ("observation", "recommendation") if low.startswith(k)), None)
        p = doc.add_paragraph()
        if label and len(stripped) > len(label) + 1 and stripped[len(label)] in " -–:":
            r = p.add_run(stripped[:len(label)])
            r.bold = True
            p.add_run(stripped[len(label):])
        else:
            p.add_run(stripped)

    if findings is not None and len(findings):
        doc.add_page_break()
        doc.add_heading("Appendix A - Journals rated CRITICAL or HIGH", level=1)
        top = findings[findings["Risk_Level"].isin(["CRITICAL", "HIGH"])].sort_values(
            "Risk_Score", ascending=False)
        _docx_table(doc, ["Journal", "Date", "User", "Account", "Amount", "Score", "Risk", "Tests"], [
            [r.JE_ID, f"{r.Date:%d-%b-%Y}", r.User, r.Account, f"{r.Amount:,.0f}", r.Risk_Score,
             r.Risk_Level, r.Tests] for r in top.itertuples()],
            widths=[1.7, 1.9, 2.0, 2.7, 1.7, 1.0, 1.7, 3.9], font=8, level_col=6)
    if variance is not None and len(variance[variance["Flag"]]):
        v = variance[variance["Flag"]]
        doc.add_paragraph()
        doc.add_heading("Appendix B - Material monthly variances", level=1)
        _docx_table(doc, ["Account", "Month", "Net movement", "Usual month", "Activity vs usual", "Side"], [
            [r.Account_Name, r.Month, f"{r.Net_Movement:,.0f}", f"{r.Avg_Monthly:,.0f}",
             f"{r.Activity_vs_Avg_Pct:+.0f}%", r.Side] for r in v.itertuples()],
            widths=[4.0, 2.0, 3.0, 3.0, 2.8, 2.2], font=9)
    _add_footer(doc, f"{(meta or {}).get('company', 'Management Letter')} - DRAFT - Confidential")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def findings_to_xlsx(findings: pd.DataFrame, flags: pd.DataFrame, log: pd.DataFrame,
                     variance: pd.DataFrame = None, meta: dict = None, letter_text: str = "",
                     benford: pd.DataFrame = None) -> bytes:
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    from openpyxl.chart import BarChart, PieChart, Reference
    from openpyxl.formatting.rule import CellIsRule, FormulaRule
    from openpyxl.utils import get_column_letter

    f = findings.copy()
    if "Procedures" in f:
        f["Procedures"] = f["Procedures"].apply(lambda x: " | ".join(x))
    if "Date" in f:
        f["Date"] = pd.to_datetime(f["Date"]).dt.date
    fl = flags.copy()
    if "Posting_Date" in fl:
        fl["Posting_Date"] = fl["Posting_Date"].dt.date
    by_test = (flags.drop_duplicates(["JE_ID", "Test"]).groupby("Test")["JE_ID"].nunique()
               .sort_values(ascending=False).reset_index()
               if len(flags) else pd.DataFrame(columns=["Test", "JE_ID"]))
    by_test.columns = ["Test", "Journals flagged"]
    by_test["What it checks"] = by_test["Test"].map(TEST_EXPLAINED).fillna("")

    hdr_fill = PatternFill("solid", fgColor=NAVY)
    hdr_font = Font(bold=True, color=WHITE)
    thin = Side(style="thin", color="BFBFBF")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame().to_excel(xw, sheet_name="Summary", index=False)
        f.to_excel(xw, sheet_name="Journal findings", index=False)
        fl.to_excel(xw, sheet_name="Flagged lines", index=False)
        if variance is not None:
            variance.to_excel(xw, sheet_name="Variance analysis", index=False)
        if benford is not None:
            benford.to_excel(xw, sheet_name="Benford", index=False)
        pd.DataFrame({"Management Letter (draft)": letter_text.split("\n")}).to_excel(
            xw, sheet_name="Management Letter", index=False)
        pd.DataFrame(
            [("Approval limit", f"{(meta or {}).get('params', {}).get('just_below_limit', {}).get('limit', 50000):,}"),
             ("Outlier z-score threshold", (meta or {}).get("params", {}).get("outlier_amounts", {}).get("z", 3.0)),
             ("Variance flag", "|z-score| >= 2 and difference >= 50,000 against the account's own monthly average"),
             ("Benford test", "First-digit chi-square, 5% critical value 15.51"),
             ("Risk score", "High = 3, Medium = 2, Low = 1 points per test, each test counted once per journal"),
             ("Risk level", "CRITICAL at the escalation score or above, HIGH at 3 or above, otherwise MODERATE"),
             ("Reading variances", "Revenue and liability accounts show negative net movement for normal activity "
                                   "(debit minus credit); use Activity vs usual % for direction")],
            columns=["Parameter", "Value"]).to_excel(xw, sheet_name="Methodology", index=False, startrow=0)
        by_test.to_excel(xw, sheet_name="Methodology", index=False, startrow=10)
        log.to_excel(xw, sheet_name="Agent log", index=False)

        wb = xw.book
        # ---- style every data sheet
        for ws in wb.worksheets:
            if ws.title == "Summary":
                continue
            for c in ws[1]:
                c.fill, c.font = hdr_fill, hdr_font
                c.alignment = Alignment(vertical="center", wrap_text=True)
            ws.freeze_panes = "A2"
            if ws.max_row > 1 and ws.title not in ("Methodology", "Management Letter"):
                ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                letter = get_column_letter(col[0].column)
                head = str(col[0].value or "")
                width = min(60, max(len(str(c.value)) if c.value is not None else 0 for c in col[:200]) + 2)
                ws.column_dimensions[letter].width = max(width, len(head) + 2)
                for c in col[1:]:
                    if isinstance(c.value, float):
                        c.number_format = "#,##0.00" if abs(c.value) >= 100 else "0.0"
                    if head in ("Narrative", "Procedures", "Reasons", "What it checks", "Value", "Action"):
                        c.alignment = Alignment(wrap_text=True, vertical="top")
                        ws.column_dimensions[letter].width = 70 if head != "Action" else 90
        ws = wb["Journal findings"]
        ws.freeze_panes = "B2"
        level_col = [c.value for c in ws[1]].index("Risk_Level") + 1
        rng = f"{get_column_letter(level_col)}2:{get_column_letter(level_col)}{max(ws.max_row, 2)}"
        for lvl, fill in LEVEL_FILL.items():
            ws.conditional_formatting.add(rng, CellIsRule(
                operator="equal", formula=[f'"{lvl}"'], fill=PatternFill("solid", bgColor=fill, fgColor=fill)))
        if "Variance analysis" in wb.sheetnames:
            wv = wb["Variance analysis"]
            heads = [c.value for c in wv[1]]
            if "Flag" in heads:
                col = get_column_letter(heads.index("Flag") + 1)
                wv.conditional_formatting.add(
                    f"A2:{get_column_letter(wv.max_column)}{wv.max_row}",
                    FormulaRule(formula=[f"${col}2=TRUE"], fill=PatternFill("solid", bgColor="FFF2CC", fgColor="FFF2CC")))
        wl = wb["Management Letter"]
        wl.column_dimensions["A"].width = 120
        for row in wl.iter_rows(min_row=2):
            row[0].alignment = Alignment(wrap_text=True, vertical="top")

        # ---- Summary sheet
        ws = wb["Summary"]
        ws.sheet_view.showGridLines = False
        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["B"].width = 22
        ws.column_dimensions["C"].width = 34
        ws.column_dimensions["D"].width = 22
        ws["A1"] = "Smart Ledger Anomaly & System-Override Detector"
        ws["A1"].font = Font(bold=True, size=16, color=NAVY)
        ws["A2"] = "Audit report - journal-entry testing"
        ws["A2"].font = Font(italic=True, size=11)
        m = meta or {}
        info = [("Entity", m.get("company", "")), ("Period reviewed", m.get("period", "")),
                ("Date", m.get("date", "")), ("Prepared by", m.get("auditor", "")),
                ("Status", "DRAFT - flags are indicators, auditor judgment required"),
                ("Letter written by", m.get("letter_source", ""))]
        for i, (k, v) in enumerate(info, start=4):
            ws.cell(i, 1, k).font = Font(bold=True)
            ws.cell(i, 2, v)
        r0 = 11
        ws.cell(r0, 1, "Key figures").font = Font(bold=True, size=13, color=NAVY)
        kf = [("Ledger lines tested", m.get("lines", 0)), ("Journals tested", m.get("journals", 0)),
              ("Journals flagged", m.get("flagged", 0)), ("CRITICAL", m.get("critical", 0)),
              ("HIGH", m.get("high", 0)), ("MODERATE", m.get("moderate", 0)),
              ("Value of flagged journals", m.get("flagged_value", 0)),
              ("Material monthly variances", m.get("variances", 0)),
              ("Benford chi-square (limit 15.51)", round(m.get("benford_chi", 0), 1)),
              ("Benford result", "Deviates" if m.get("benford_flag") else "Conforms")]
        for i, (k, v) in enumerate(kf, start=r0 + 1):
            a, b = ws.cell(i, 1, k), ws.cell(i, 2, v)
            a.fill = PatternFill("solid", fgColor=LIGHT)
            a.border = b.border = box
            b.alignment = Alignment(horizontal="right")
            if isinstance(v, (int, float)):
                b.number_format = "#,##0"
        # risk level table + pie
        t0 = r0 + 1
        ws.cell(r0, 3, "Risk level").font = Font(bold=True, size=13, color=NAVY)
        for j, (lvl, key) in enumerate([("CRITICAL", "critical"), ("HIGH", "high"), ("MODERATE", "moderate")]):
            c1, c2 = ws.cell(t0 + j, 3, lvl), ws.cell(t0 + j, 4, m.get(key, 0))
            c1.fill = PatternFill("solid", fgColor=LEVEL_FILL[lvl])
            c1.border = c2.border = box
        pie = PieChart()
        pie.title = "Flagged journals by risk level"
        pie.add_data(Reference(ws, min_col=4, min_row=t0, max_row=t0 + 2))
        pie.set_categories(Reference(ws, min_col=3, min_row=t0, max_row=t0 + 2))
        from openpyxl.chart.series import DataPoint
        for idx, colr in enumerate(["C0392B", "E67E22", "F1C40F"]):
            pt = DataPoint(idx=idx)
            pt.graphicalProperties.solidFill = colr
            pie.series[0].dPt.append(pt)
        pie.height, pie.width = 6.5, 9
        ws.add_chart(pie, "F3")
        # tests table + bar chart
        s0 = r0 + 13
        ws.cell(s0 - 1, 1, "Journals flagged by test").font = Font(bold=True, size=13, color=NAVY)
        for c, h in enumerate(["Test", "Journals flagged"], start=1):
            cell = ws.cell(s0, c, h)
            cell.fill, cell.font, cell.border = hdr_fill, hdr_font, box
        for i, row in enumerate(by_test.itertuples(index=False), start=s0 + 1):
            ws.cell(i, 1, row[0]).border = box
            ws.cell(i, 2, row[1]).border = box
        if len(by_test):
            bar = BarChart()
            bar.type = "bar"
            bar.title = "Journals flagged by test"
            bar.add_data(Reference(ws, min_col=2, min_row=s0, max_row=s0 + len(by_test)), titles_from_data=True)
            bar.set_categories(Reference(ws, min_col=1, min_row=s0 + 1, max_row=s0 + len(by_test)))
            bar.legend = None
            bar.height, bar.width = 8, 16
            ws.add_chart(bar, "F17")
        # top 10 journals by risk
        top0 = s0 + len(by_test) + 3
        ws.cell(top0 - 1, 1, "Top 10 journals by risk score").font = Font(bold=True, size=13, color=NAVY)
        for c, h in enumerate(["Journal", "User", "Account", "Amount", "Score", "Risk"], start=1):
            cell = ws.cell(top0, c, h)
            cell.fill, cell.font, cell.border = hdr_fill, hdr_font, box
        for i, r in enumerate(findings.sort_values("Risk_Score", ascending=False).head(10).itertuples(), start=top0 + 1):
            vals = [r.JE_ID, r.User, r.Account, r.Amount, r.Risk_Score, r.Risk_Level]
            for c, v in enumerate(vals, start=1):
                cell = ws.cell(i, c, v)
                cell.border = box
                if c == 4:
                    cell.number_format = "#,##0"
                if c == 6:
                    cell.fill = PatternFill("solid", fgColor=LEVEL_FILL.get(r.Risk_Level, "FFFFFF"))
        ws.column_dimensions["E"].width = 10
        ws.column_dimensions["F"].width = 14
        ws.sheet_properties.tabColor = NAVY
        for w_ in wb.worksheets:
            w_.page_setup.orientation = "landscape"
            w_.page_setup.fitToWidth = 1
            w_.page_setup.fitToHeight = 0
            w_.sheet_properties.pageSetUpPr = __import__("openpyxl").worksheet.properties.PageSetupProperties(fitToPage=True)
            w_.oddFooter.center.text = "Draft - Confidential - Page &P of &N"
        from openpyxl.formatting.rule import DataBarRule
        wj = wb["Journal findings"]
        heads = [c.value for c in wj[1]]
        if "Risk_Score" in heads and wj.max_row > 1:
            col = get_column_letter(heads.index("Risk_Score") + 1)
            wj.conditional_formatting.add(f"{col}2:{col}{wj.max_row}",
                                          DataBarRule(start_type="num", start_value=0, end_type="max", color="2F5597"))
        wb.active = 0
    return buf.getvalue()


# ==========================================================================
# SECTION 6: Streamlit UI
# ==========================================================================

TEST_LABELS = {
    "weekend_postings": "Weekend postings",
    "round_amounts": "Round-number amounts",
    "duplicate_entries": "Duplicate entries",
    "period_end_manual": "Period-end manual journals",
    "outlier_amounts": "Statistical outliers",
    "just_below_limit": "Just below approval limit",
    "privileged_user_manual": "Privileged-user manual entries",
    "override_without_approval": "Override without approval",
    "after_hours_posting": "After-hours postings",
    "backdated_entries": "Back-dated / future-dated entries",
    "debit_credit_imbalance": "Debit-credit imbalance",
    "rare_user_large_entry": "Rare-user large entries",
}


@st.cache_data
def get_sample_ledger():
    return generate_sample_ledger()


def main():
    st.set_page_config(page_title="Smart Ledger Anomaly Detector", page_icon="🔍", layout="wide")



    # ------------------------------------------------------------------ sidebar
    st.sidebar.title("⚙️ Settings")
    company = st.sidebar.text_input("Company name", "Demo Trading LLC")
    period = st.sidebar.text_input("Audit period", "FY2025")
    auditor = st.sidebar.text_input("Auditor / signatory", "Audit Team")

    st.sidebar.subheader("Tests")
    enabled = [k for k, v in TEST_LABELS.items() if st.sidebar.checkbox(v, True)]

    st.sidebar.subheader("Parameters")
    approval_limit = st.sidebar.number_input("Approval limit", 1000, 10_000_000, 50_000, 1000)
    priv_users = [u.strip() for u in st.sidebar.text_input(
        "Privileged users (comma separated)", "admin, cfo.override").split(",") if u.strip()]
    z_thr = st.sidebar.slider("Outlier z-score threshold", 2.0, 5.0, 3.0, 0.5)
    min_manual = st.sidebar.number_input("Large manual entry (min amount)", 10_000, 5_000_000, 100_000, 10_000)

    with st.sidebar.expander("🔑 LLM API key - optional"):
        prov_in = st.selectbox("Provider", ["Grok (xAI)", "Groq"], index=1,
                               help="Grok (xAI) keys start with xai-. Groq keys start with gsk_.")
        key_in = st.text_input("API key", type="password", help="Used only while the app is open. Not saved to disk.")
        model_in = st.text_input("Model name (optional)", "", placeholder="leave empty = default",
                                 help="Default: openai/gpt-oss-120b for Groq, grok-4.7 for Grok (xAI)")
        env_name, prov_id = ("XAI_API_KEY", "xai") if prov_in.startswith("Grok") else ("GROQ_API_KEY", "groq")
        for other in ("XAI_API_KEY", "GROQ_API_KEY"):          # forget keys typed for the other provider
            if other != env_name and os.environ.get("_UI_KEY") == other:
                os.environ.pop(other, None)
        if key_in:
            os.environ[env_name] = key_in.strip().strip('"').strip("'")
            os.environ["LLM_PROVIDER"] = prov_id
            os.environ["_UI_KEY"] = env_name
        elif os.environ.get("_UI_KEY") == env_name:
            os.environ.pop("_UI_KEY", None)
            os.environ.pop(env_name, None)
        if model_in:
            os.environ["LLM_MODEL"] = model_in.strip()
        else:
            os.environ.pop("LLM_MODEL", None)
        llm_n = st.number_input("Journals the LLM investigates", 1, 10, MAX_LLM_JOURNALS,
                                help="Free API plans have token-per-minute limits. More journals = slower.")

    st.sidebar.divider()
    mode = (f"LLM: {provider()} (tool-calling {'on' if supports_tools() else 'off'})"
            if is_enabled() else "Offline mode (no API key set)")
    st.sidebar.caption(f"🤖 {mode}")
    if is_enabled() and st.sidebar.button("Test LLM connection"):
        reply = ask("Reply with exactly: connection OK", max_tokens=600)
        if reply:
            st.sidebar.success(f"{provider()} replied: {reply.strip()[:60]}")
        else:
            st.sidebar.error(f"LLM call failed. {last_error() or 'No error text was returned.'}")

    params = {
        "just_below_limit": {"limit": approval_limit},
        "outlier_amounts": {"z": z_thr},
        "weekend_postings": {"privileged_users": tuple(priv_users)},
        "privileged_user_manual": {"privileged_users": tuple(priv_users), "min_amount": min_manual},
    }

    # -------------------------------------------------------------------- main
    st.markdown(DASH_CSS, unsafe_allow_html=True)
    st.markdown("<h1 class='hero'>Smart Ledger Anomaly &amp; System-Override Detector</h1>", unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload a general ledger CSV (or use the built-in sample below)", type=["csv"])
    c_a, c_b = st.columns([3, 2])
    use_sample = c_a.checkbox("Use the built-in sample ledger", value=uploaded is None)
    c_b.download_button("Download the sample ledger as CSV", get_sample_ledger().to_csv(index=False),
                        "sample_general_ledger.csv", "text/csv")

    raw = None
    if uploaded is not None and not use_sample:
        raw = pd.read_csv(uploaded)
    elif use_sample:
        raw = get_sample_ledger()

    if raw is None:
        st.info("Upload a CSV with columns: JE_ID, Posting_Date, Account_Code, Account_Name, "
                "Description, Debit, Credit, User (optional: Source).")
        st.stop()

    try:
        df = load_and_clean(raw)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    st.markdown(f"<p class='sub'>{company} &bull; {period} &bull; {df['JE_ID'].nunique():,} journal entries "
                f"({len(df):,} ledger lines) ready to test</p>", unsafe_allow_html=True)
    run_clicked = st.button("Run analysis", type="primary", icon=":material/play_arrow:")
    if not (run_clicked or "result" in st.session_state):
        st.info("Click **Run analysis**. The three agents will test every journal, investigate the riskiest "
                "ones and draft the Management Letter.")
        st.stop()

    run_key = (len(df), tuple(enabled), str(params), provider() if is_enabled() else "offline",
               os.getenv("LLM_MODEL", ""))
    if run_clicked or st.session_state.get("_rerun_key") != run_key:
        with st.spinner("Agents working... with an LLM on a free plan this can take a few minutes (waiting for rate limits)."):
            st.session_state["result"] = run_pipeline(df, enabled, params, company, period, auditor, llm_n)
            st.session_state["_rerun_key"] = run_key
    res = st.session_state["result"]
    findings, flags = res["findings"], res["detector"]["flags"]
    meta = report_meta(df, res, company, period, auditor, params)

    m = st.columns(6)
    cards = [("Journals tested", f"{meta['journals']:,}"), ("Journals flagged", f"{meta['flagged']:,}"),
             ("% flagged", f"{meta['flagged'] / max(meta['journals'], 1):.1%}"),
             ("Critical", f"{meta['critical']}"), ("High", f"{meta['high']}"),
             ("Flagged value", f"{meta['flagged_value'] / 1e6:,.2f} M")]
    for col, (label, val) in zip(m, cards):
        col.metric(label, val)

    t_over, t_exp, t_var, t_ben, t_log, t_let, t_about = st.tabs(
        [":material/dashboard: Overview", ":material/search: Anomaly Explorer",
         ":material/trending_up: Variance", ":material/pin: Benford",
         ":material/smart_toy: Agent Trace", ":material/mail: Management Letter", ":material/info: About"])

    with t_over:
        import altair as alt
        if flags.empty:
            st.success("No anomalies found.")
        else:
            top_user = findings.groupby("User")["Amount"].sum().sort_values(ascending=False)
            top_test = (flags.drop_duplicates(["JE_ID", "Test"]).groupby("Test")["JE_ID"].nunique()
                        .sort_values(ascending=False))
            st.markdown(
                "<div class='insight'><b>Key insights</b><ul>"
                f"<li><b>{meta['critical']}</b> journals are rated CRITICAL and <b>{meta['high']}</b> HIGH "
                f"out of {meta['flagged']} flagged ({meta['flagged'] / max(meta['journals'], 1):.1%} of all journals).</li>"
                f"<li>User <b>{top_user.index[0]}</b> posted the largest flagged value "
                f"({top_user.iloc[0]:,.0f}, {top_user.iloc[0] / max(top_user.sum(), 1):.0%} of the total).</li>"
                f"<li>Most frequent test: <b>{top_test.index[0]}</b> ({int(top_test.iloc[0])} journals).</li>"
                f"<li>{meta['variances']} account-months moved materially against their usual month; Benford's Law "
                f"{'deviates' if meta['benford_flag'] else 'conforms'} (chi-square {meta['benford_chi']:.1f}).</li>"
                "</ul></div>", unsafe_allow_html=True)
            left, right = st.columns(2)
            bt = (flags.drop_duplicates(["JE_ID", "Test"]).groupby("Test")["JE_ID"].nunique()
                  .sort_values(ascending=False).reset_index())
            bt.columns = ["Test", "Journals"]
            left.markdown("##### Flagged journals by test")
            left.caption("How many journals failed each test. One journal can fail several tests.")
            left.altair_chart(alt.Chart(bt).mark_bar(color=NAVY_HEX).encode(
                y=alt.Y("Test:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)), x=alt.X("Journals:Q", title=None),
                tooltip=["Test", "Journals"]).properties(height=280), width='stretch')
            lv = findings["Risk_Level"].value_counts().reindex(["CRITICAL", "HIGH", "MODERATE"]).fillna(0).reset_index()
            lv.columns = ["Risk", "Journals"]
            right.markdown("##### Risk level of flagged journals")
            right.caption("Red = look at first, orange = next, yellow = low priority.")
            right.altair_chart(alt.Chart(lv).mark_bar().encode(
                x=alt.X("Risk:N", sort=["CRITICAL", "HIGH", "MODERATE"], title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Journals:Q", title=None),
                color=alt.Color("Risk:N", legend=None, scale=alt.Scale(
                    domain=["CRITICAL", "HIGH", "MODERATE"], range=["#C0392B", "#E67E22", "#F1C40F"])),
                tooltip=["Risk", "Journals"]).properties(height=280), width='stretch')
            l2, r2 = st.columns(2)
            by_user = findings.groupby("User")["Amount"].sum().sort_values(ascending=False).reset_index()
            l2.markdown("##### Flagged amount by user")
            l2.caption("Total value of flagged journals per person who posted them.")
            l2.altair_chart(alt.Chart(by_user).mark_bar(color=NAVY_HEX).encode(
                x=alt.X("User:N", sort="-y", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Amount:Q", title=None), tooltip=["User", alt.Tooltip("Amount:Q", format=",.0f")]
            ).properties(height=260), width='stretch')
            wd = df.drop_duplicates("JE_ID")["Posting_Date"].dt.day_name().value_counts().reset_index()
            wd.columns = ["Day", "Journals"]
            r2.markdown("##### Postings by weekday (all journals)")
            r2.caption("Normal activity is Monday to Friday. Saturday and Sunday bars deserve a question.")
            r2.altair_chart(alt.Chart(wd).mark_bar(color="#8497B0").encode(
                x=alt.X("Day:N", sort=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                        title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Journals:Q", title=None), tooltip=["Day", "Journals"]).properties(height=260),
                width='stretch')

    with t_over:
        if not findings.empty:
            st.markdown("##### Top 10 journals by risk")
            st.caption("The ten entries with the most red flags. Open the Anomaly Explorer tab for the full list and explanations.")
            top10 = findings.sort_values("Risk_Score", ascending=False).head(10)[
                ["JE_ID", "Date", "User", "Account", "Amount", "Risk_Score", "Risk_Level", "Tests"]].copy()
            top10["Date"] = pd.to_datetime(top10["Date"]).dt.strftime("%d-%b-%Y")
            cmap = {"CRITICAL": "background-color:#F4B6B6;font-weight:600",
                    "HIGH": "background-color:#FAD7A0", "MODERATE": "background-color:#FFF2CC"}
            st.dataframe(top10.style.map(lambda v: cmap.get(v, ""), subset=["Risk_Level"]),
                         hide_index=True, width='stretch',
                         column_config={"Amount": st.column_config.NumberColumn(format="%,.0f")})

    with t_exp:
        if findings.empty:
            st.success("No anomalies found.")
        else:
            st.markdown(
                "<div class='insight'><b>How to read this page</b><ul>"
                "<li>Each row is one <b>journal entry</b> that failed at least one test. Nothing here is proven wrong: "
                "these are the entries an auditor should look at first.</li>"
                "<li><b>Risk score</b> adds points for every test failed (High test = 3, Medium = 2, Low = 1). "
                "A higher score means more red flags on the same journal.</li>"
                "<li><b>CRITICAL</b> = score 7 or more (look at first), <b>HIGH</b> = 3 to 6 (look at next), "
                "<b>MODERATE</b> = below 3 (low priority).</li>"
                "<li>Open a journal below to see in plain English why it was flagged, what it could mean and "
                "what to do next.</li></ul></div>", unsafe_allow_html=True)
            f1, f2 = st.columns([2, 3])
            levels = f1.multiselect("Show risk levels", ["CRITICAL", "HIGH", "MODERATE"],
                                    default=["CRITICAL", "HIGH", "MODERATE"])
            users = f2.multiselect("Only journals posted by", sorted(findings["User"].unique()), default=[],
                                   placeholder="All users")
            view = findings[findings["Risk_Level"].isin(levels)]
            if users:
                view = view[view["User"].isin(users)]
            show = view[["JE_ID", "Date", "User", "Account", "Amount", "Risk_Score", "Risk_Level", "Tests"]].copy()
            show["Date"] = pd.to_datetime(show["Date"]).dt.strftime("%d-%b-%Y")
            show.columns = ["Journal", "Date", "Posted by", "Account", "Amount", "Risk score", "Risk level",
                            "Why it was flagged"]
            colour = {"CRITICAL": "background-color:#F4B6B6;font-weight:600",
                      "HIGH": "background-color:#FAD7A0", "MODERATE": "background-color:#FFF2CC"}
            st.caption(f"{len(show)} journals shown, highest risk first.")
            st.dataframe(show.style.map(lambda v: colour.get(v, ""), subset=["Risk level"]),
                         hide_index=True, width='stretch',
                         column_config={"Amount": st.column_config.NumberColumn(format="%,.0f"),
                                        "Risk score": st.column_config.ProgressColumn(
                                            "Risk score", min_value=0, max_value=int(findings["Risk_Score"].max()),
                                            format="%d")})
            st.markdown("##### Journal by journal: what it means and what to do")
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MODERATE": "🟡"}
            for _, r in view.head(15).iterrows():
                title = (f"{icon.get(r.Risk_Level, '')} {r.JE_ID} | {r.Risk_Level} | {r.Amount:,.0f} | "
                         f"{r.Account} | posted by {r.User}")
                with st.expander(title):
                    st.markdown(f"**What happened.** {r.Narrative}")
                    st.markdown("**Why it was flagged**")
                    for t_ in str(r.Tests).split(", "):
                        st.markdown(f"- **{t_}**: {TEST_EXPLAINED.get(t_, '')}")
                    st.markdown("**What to do next (recommended audit procedures)**")
                    for p in r.Procedures:
                        st.markdown(f"- {p}")
                    st.caption(f"Assessed by: {'the LLM using tools' if 'LLM' in str(r.Analysed_By) else 'built-in audit rules'}.")

    with t_var:
        var = res["detector"]["variance"]
        st.caption("Net movement per account per month compared with that account's own monthly average. "
                   "Flagged = |z-score| >= 2 and difference >= 50,000. Revenue and liabilities show negative "
                   "movement for normal activity (debit minus credit), so read the **Activity vs usual %** column.")
        only_flag = st.checkbox("Show only flagged months", True)
        vshow = var[var["Flag"]] if only_flag else var
        st.dataframe(vshow, hide_index=True, width='stretch', column_config={
            "Net_Movement": st.column_config.NumberColumn(format="%,.0f"),
            "Avg_Monthly": st.column_config.NumberColumn(format="%,.0f"),
            "Variance_Amt": st.column_config.NumberColumn(format="%,.0f"),
            "Activity_vs_Avg_Pct": st.column_config.NumberColumn("Activity vs usual %", format="%+.0f%%")})

    with t_ben:
        import altair as alt
        table, chi, bflag = res["detector"]["benford"], res["detector"]["chi"], res["detector"]["benford_flag"]
        (st.warning if bflag else st.success)(
            f"Chi-square = {chi:.1f} (5% critical value 15.51): "
            + ("the first digits deviate from Benford's Law." if bflag else "the first digits conform to Benford's Law."))
        long = table.melt("Digit", ["Actual %", "Benford %"], var_name="Series", value_name="Percent")
        st.altair_chart(alt.Chart(long).mark_bar().encode(
            x=alt.X("Digit:O", title="First digit", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Percent:Q", title="% of amounts"), xOffset="Series:N",
            color=alt.Color("Series:N", scale=alt.Scale(range=[NAVY_HEX, "#E67E22"]), legend=alt.Legend(orient="top")),
            tooltip=["Digit", "Series", alt.Tooltip("Percent:Q", format=".1f")]).properties(height=300),
            width='stretch')
        st.dataframe(table, hide_index=True, width='stretch')

    with t_log:
        st.caption("How the three agents handed work to each other.")
        st.table(res["log"].set_index("Agent"))

    with t_let:
        st.caption(f"Letter generated by: **{res['letter'].get('source', 'Template')}**. "
                   "Edit the text below before downloading.")
        edited = st.text_area("Draft Management Letter", res["letter"]["text"], height=450,
                              label_visibility="collapsed")
        d1, d2 = st.columns(2)
        d1.download_button("Download Word letter", letter_to_docx(edited, meta, findings, res["detector"]["variance"]),
                           "Management_Letter_Draft.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           icon=":material/description:", width='stretch')
        if not findings.empty:
            d2.download_button("Download Excel report",
                               findings_to_xlsx(findings, flags, res["log"], res["detector"]["variance"],
                                                meta, edited, res["detector"]["benford"]),
                               "Anomaly_Findings.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               icon=":material/table_chart:", width='stretch')

    with t_about:
        st.markdown("""
**What this tool does.** It tests 100% of journal entries instead of a sample, flags the unusual ones,
investigates the riskiest with an LLM that calls Python tools, and drafts a Management Letter.

| Agent | Role |
|---|---|
| Agent 1 - Detector | 12 anomaly tests, monthly variance analysis, Benford's Law, risk score per journal |
| Agent 2 - Investigator | LLM tool-calling loop (rules fallback without a key) |
| Agent 3 - Letter Drafter | LLM-written Management Letter (template fallback) |

Flags are indicators, not conclusions. Auditor judgment is required, and the letter is a draft.
""")
        st.table(pd.DataFrame({"Test": list(TEST_EXPLAINED), "What it checks": list(TEST_EXPLAINED.values())}).set_index("Test"))


NAVY_HEX = "#1F3864"
DASH_CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1250px;}
h1.hero {font-size: 2.3rem; font-weight: 800; color: #1F3864; margin-bottom: .1rem; letter-spacing: -.5px;}
p.sub {color: #5b6b82; margin: .2rem 0 .8rem 0;}
div[data-testid="stMetric"] {background: #F3F5F9; border-left: 5px solid #1F3864; border-radius: 6px;
    padding: .7rem .9rem; box-shadow: 0 1px 2px rgba(0,0,0,.06);}
div[data-testid="stMetricLabel"] p {font-size: .8rem; color: #5b6b82;}
div[data-testid="stMetricValue"] {font-size: 1.6rem; font-weight: 700; color: #1F3864;}
button[data-baseweb="tab"] {font-weight: 600;}
.insight {background:#EEF3FB; border-left:5px solid #1F3864; border-radius:6px; padding:.6rem 1rem; margin:.6rem 0 1rem 0;}
.insight ul {margin:.3rem 0 0 0; padding-left:1.2rem;}
</style>
"""


if __name__ == "__main__":
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx(suppress_warning=True) is None:
        # Started with plain "python app.py" (or F5 in IDLE): launch the Streamlit server.
        print("Starting the app... your browser will open. Close this window to stop it.")
        subprocess.call([_python_exe(), "-m", "streamlit", "run", os.path.abspath(__file__),
                         "--browser.gatherUsageStats", "false"], stdin=subprocess.DEVNULL)
    else:
        main()
