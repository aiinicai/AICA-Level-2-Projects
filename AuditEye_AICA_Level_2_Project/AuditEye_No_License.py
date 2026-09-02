
import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px
from rapidfuzz import fuzz, process
from sklearn.ensemble import IsolationForest

APP_NAME = "AuditEye"
APP_SUBTITLE = "AI Assisted Audit Red Flag Analyzer"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🔍",
    layout="wide",
)

# ------------------------------------------------------------
# STYLE
# ------------------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background: #F4F7FB;
    }
    .main-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #123B5D;
        margin-bottom: 0;
    }
    .sub-title {
        font-size: 1rem;
        color: #60758A;
        margin-top: 0.2rem;
        margin-bottom: 1.2rem;
    }
    .section-card {
        background: white;
        border: 1px solid #DFE7EF;
        border-radius: 14px;
        padding: 1.1rem 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(20, 45, 70, 0.04);
    }
    .small-note {
        color: #6B7D8F;
        font-size: 0.92rem;
    }
    .success-box {
        background: #ECF8F1;
        border-left: 5px solid #2D9D62;
        border-radius: 8px;
        padding: 0.9rem 1rem;
        color: #1B5E3B;
    }
    .warning-box {
        background: #FFF7E6;
        border-left: 5px solid #F0A23A;
        border-radius: 8px;
        padding: 0.9rem 1rem;
        color: #7C531B;
    }
    .metric-label {
        color: #60758A;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .metric-value {
        color: #123B5D;
        font-size: 1.55rem;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------

defaults = {
    "step": 1,
    "raw_df": None,
    "source_name": "",
    "source_type": "",
    "mapping": {},
    "standard_df": None,
    "profile_saved": False,
    "analysis_df": None,
    "patterns_df": None,
    "analysis_run": False,
    "ai_analysis_df": None,
    "ai_monthly_spikes_df": None,
    "ai_run": False,
    "selected_voucher": "",
    "final_export_bytes": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

FIELD_SYNONYMS = {
    "Date": [
        "date", "transaction date", "txn date", "voucher date",
        "posting date", "transaction_date"
    ],
    "Ledger Account": [
        "ledger", "ledger account", "account", "account name",
        "gl account", "ledger_name"
    ],
    "Party Name": [
        "party", "party name", "contact name", "contact",
        "vendor", "vendor name", "customer", "customer name",
        "particulars"
    ],
    "Voucher Type": [
        "voucher type", "vch type", "transaction type",
        "document type", "voucher_type"
    ],
    "Voucher Number": [
        "voucher no", "voucher number", "vch no", "transaction #",
        "transaction number", "transaction no", "reference",
        "reference no", "document no", "voucher_no"
    ],
    "Narration": [
        "narration", "description", "remarks", "memo",
        "details", "particular description"
    ],
    "Debit": [
        "debit", "debit amount", "dr", "dr amount"
    ],
    "Credit": [
        "credit", "credit amount", "cr", "cr amount"
    ],
    "Amount": [
        "amount", "transaction amount", "value", "net amount"
    ],
    "Dr/Cr": [
        "dr/cr", "debit/credit", "type", "dr cr", "d/c"
    ],
    "Created By": [
        "created by", "user", "entered by", "posted by",
        "created_by"
    ],
    "Entry Time": [
        "entry time", "created time", "time", "posting time",
        "entry_time"
    ],
    "Invoice No": [
        "invoice no", "invoice number", "invoice #",
        "bill no", "bill number"
    ],
    "GSTIN": [
        "gstin", "gst no", "gst number"
    ],
    "PAN": [
        "pan", "pan no", "pan number"
    ],
    "Bank Reference": [
        "bank ref", "bank reference", "utr", "utr no",
        "bank transaction id"
    ],
}


def normalize_heading(value):
    value = str(value).strip().lower()
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w/# ]", "", value)
    return value.strip()


def detect_source(columns):
    normalized = {normalize_heading(c) for c in columns}

    tally_markers = {"vch type", "vch no", "particulars"}
    zoho_markers = {"transaction date", "transaction type", "transaction #", "contact name"}

    tally_score = len(normalized.intersection(tally_markers))
    zoho_score = len(normalized.intersection(zoho_markers))

    if tally_score >= 2 and tally_score > zoho_score:
        return "Tally-style Day Book"
    if zoho_score >= 2 and zoho_score > tally_score:
        return "Zoho Books-style General Ledger"
    return "Generic Excel / CSV / Google Sheets"


def best_match_column(target_field, columns):
    synonyms = [normalize_heading(x) for x in FIELD_SYNONYMS.get(target_field, [])]
    normalized_cols = {normalize_heading(c): c for c in columns}

    # Exact normalized match first
    for syn in synonyms:
        if syn in normalized_cols:
            return normalized_cols[syn]

    # Conservative token/substring match second
    for syn in synonyms:
        for norm_col, original in normalized_cols.items():
            if syn and (syn == norm_col or syn in norm_col or norm_col in syn):
                return original

    return None


def auto_mapping(columns):
    return {field: best_match_column(field, columns) for field in FIELD_SYNONYMS.keys()}


def clean_numeric(series):
    if series is None:
        return pd.Series(dtype=float)

    text = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("Rs.", "", regex=False)
        .str.replace("Rs", "", regex=False)
        .str.replace(r"\((.*?)\)", r"-\1", regex=True)
        .str.strip()
    )

    text = text.replace({
        "": None, "nan": None, "None": None, "-": None
    })

    return pd.to_numeric(text, errors="coerce").fillna(0.0)


def parse_dates(series):
    # Try general parser first. dayfirst=True is practical for Indian ledgers.
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def read_excel_flexible(uploaded_file):
    # First pass: default header
    raw = pd.read_excel(uploaded_file)

    # If default read produced mostly unnamed columns or too few useful headers,
    # scan first 10 rows to locate a likely header.
    unnamed_ratio = sum(str(c).startswith("Unnamed") for c in raw.columns) / max(1, len(raw.columns))

    if len(raw.columns) >= 3 and unnamed_ratio < 0.6:
        return raw

    uploaded_file.seek(0)
    preview = pd.read_excel(uploaded_file, header=None, nrows=12)

    best_row = 0
    best_score = -1

    all_synonyms = set()
    for values in FIELD_SYNONYMS.values():
        all_synonyms.update(normalize_heading(v) for v in values)

    for idx in range(len(preview)):
        values = [normalize_heading(v) for v in preview.iloc[idx].tolist()]
        score = sum(1 for v in values if v in all_synonyms)
        if score > best_score:
            best_score = score
            best_row = idx

    uploaded_file.seek(0)
    return pd.read_excel(uploaded_file, header=best_row)


def read_csv_flexible(uploaded_file):
    data = uploaded_file.getvalue()

    attempts = [
        {"encoding": "utf-8-sig", "sep": None, "engine": "python"},
        {"encoding": "utf-8", "sep": None, "engine": "python"},
        {"encoding": "latin-1", "sep": None, "engine": "python"},
    ]

    last_error = None

    for kwargs in attempts:
        try:
            return pd.read_csv(io.BytesIO(data), **kwargs)
        except Exception as error:
            last_error = error

    raise last_error


def read_pasted_table(text):
    if not text.strip():
        return None

    # Clipboard-style pasted Excel/Sheets data is normally tab-separated.
    try:
        df = pd.read_csv(io.StringIO(text), sep="\t")
        if len(df.columns) > 1:
            return df
    except Exception:
        pass

    # Fallback CSV
    return pd.read_csv(io.StringIO(text))


def drop_obvious_empty_rows(df):
    df = df.copy()
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def standardize_ledger(df, mapping):
    result = pd.DataFrame(index=df.index)

    def mapped(field):
        col = mapping.get(field)
        if col and col in df.columns:
            return df[col]
        return None

    date_series = mapped("Date")
    ledger_series = mapped("Ledger Account")
    party_series = mapped("Party Name")
    voucher_type_series = mapped("Voucher Type")
    voucher_no_series = mapped("Voucher Number")
    narration_series = mapped("Narration")
    debit_series = mapped("Debit")
    credit_series = mapped("Credit")
    amount_series = mapped("Amount")
    drcr_series = mapped("Dr/Cr")

    result["Date"] = parse_dates(date_series) if date_series is not None else pd.NaT
    result["Ledger Account"] = ledger_series.astype(str).str.strip() if ledger_series is not None else ""
    result["Party Name"] = party_series.astype(str).str.strip() if party_series is not None else ""
    result["Voucher Type"] = voucher_type_series.astype(str).str.strip() if voucher_type_series is not None else ""
    result["Voucher Number"] = voucher_no_series.astype(str).str.strip() if voucher_no_series is not None else ""
    result["Narration"] = narration_series.astype(str).str.strip() if narration_series is not None else ""

    if debit_series is not None or credit_series is not None:
        result["Debit"] = clean_numeric(debit_series) if debit_series is not None else 0.0
        result["Credit"] = clean_numeric(credit_series) if credit_series is not None else 0.0

    elif amount_series is not None and drcr_series is not None:
        amount = clean_numeric(amount_series)
        marker = drcr_series.astype(str).str.strip().str.lower()
        result["Debit"] = amount.where(marker.str.contains(r"\bdr\b|debit", regex=True), 0.0)
        result["Credit"] = amount.where(marker.str.contains(r"\bcr\b|credit", regex=True), 0.0)

    elif amount_series is not None:
        amount = clean_numeric(amount_series)
        result["Debit"] = amount.where(amount > 0, 0.0)
        result["Credit"] = (-amount).where(amount < 0, 0.0)

    else:
        result["Debit"] = 0.0
        result["Credit"] = 0.0

    result["Amount"] = result[["Debit", "Credit"]].max(axis=1)

    for optional in ["Created By", "Entry Time", "Invoice No", "GSTIN", "PAN", "Bank Reference"]:
        series = mapped(optional)
        result[optional] = series.astype(str).str.strip() if series is not None else ""

    # Remove obvious non-transaction rows after standardization
    obvious_text = (
        result["Ledger Account"].fillna("").astype(str)
        + " "
        + result["Party Name"].fillna("").astype(str)
        + " "
        + result["Narration"].fillna("").astype(str)
    ).str.lower()

    total_like = obvious_text.str.contains(
        r"grand total|closing balance|opening balance|carried forward|brought forward",
        regex=True,
        na=False,
    )

    fully_blank = (
        result["Date"].isna()
        & (result["Ledger Account"].astype(str).str.strip() == "")
        & (result["Party Name"].astype(str).str.strip() == "")
        & (result["Debit"] == 0)
        & (result["Credit"] == 0)
    )

    result = result[~(total_like | fully_blank)].copy()
    result.reset_index(drop=True, inplace=True)
    return result


def inr(value):
    value = float(value or 0)
    abs_value = abs(value)

    if abs_value >= 10_000_000:
        return f"₹{value / 10_000_000:,.2f} Cr"
    if abs_value >= 100_000:
        return f"₹{value / 100_000:,.2f} L"
    return f"₹{value:,.0f}"


def format_date(value):
    if pd.isna(value):
        return "Not available"
    return pd.Timestamp(value).strftime("%d-%b-%Y")


def mapping_ready(mapping):
    has_date = bool(mapping.get("Date"))
    has_ledger = bool(mapping.get("Ledger Account"))
    has_drcr_pair = bool(mapping.get("Debit")) and bool(mapping.get("Credit"))
    has_amount_logic = bool(mapping.get("Amount"))
    return has_date and has_ledger and (has_drcr_pair or has_amount_logic)


def available_test_notes(mapping):
    notes = []

    if not mapping.get("Created By"):
        notes.append("Created By unavailable — user-based posting analysis will be skipped.")
    if not mapping.get("Entry Time"):
        notes.append("Entry Time unavailable — late-night posting analysis will be skipped.")
    if not mapping.get("Party Name"):
        notes.append("Party Name unavailable — party-level anomaly and related-party analysis will be limited.")
    if not mapping.get("Narration"):
        notes.append("Narration unavailable — keyword/context analysis will be limited.")
    if not mapping.get("Voucher Type"):
        notes.append("Voucher Type unavailable — manual-journal tests may be limited.")

    return notes


# ------------------------------------------------------------
# STAGE 2 — AUDIT RED-FLAG ENGINE
# ------------------------------------------------------------

RISK_WEIGHTS = {
    "Possible Fund-Use / Borrowing Risk": 35,
    "Related Party": 20,
    "Duplicate / Near-Duplicate": 25,
    "Possible Split Transaction": 25,
    "Explicit Reversal": 30,
    "High / Material Value": 20,
    "Manual Journal": 15,
    "Unusual Party Amount": 15,
    "New / Dormant Party": 10,
    "Large Cash Transaction": 15,
    "Year-End Entry": 10,
    "Round Figure": 5,
    "Weekend / Unusual Timing": 5,
    "Director / Group Fund Movement": 20,
}


def clean_party_name(value):
    value = str(value or "").strip().lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\bm/s\b", " ", value)
    value = re.sub(r"\bprivate limited\b", " ", value)
    value = re.sub(r"\bpvt\.?\s*ltd\.?\b", " ", value)
    value = re.sub(r"\blimited\b", " ", value)
    value = re.sub(r"\bltd\.?\b", " ", value)
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def split_names(text):
    if not text:
        return []
    parts = re.split(r"[,;\n]+", str(text))
    return [x.strip() for x in parts if x.strip()]


def fy_bounds(fy_text):
    try:
        start_year = int(str(fy_text).split("-")[0])
    except Exception:
        start_year = 2025
    return pd.Timestamp(start_year, 4, 1), pd.Timestamp(start_year + 1, 3, 31)


def first_nonblank(series):
    for value in series:
        if pd.notna(value):
            text = str(value).strip()
            if text and text.lower() not in {"nan", "none"}:
                return text
    return ""


def unique_join(series, sep=" | "):
    values = []
    seen = set()
    for value in series:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none"}:
            continue
        if text not in seen:
            seen.add(text)
            values.append(text)
    return sep.join(values)


def build_voucher_view(std):
    """
    Convert debit/credit ledger lines into one voucher-level row.
    This prevents a normal double-entry pair from being treated as a duplicate transaction.
    """
    work = std.copy()
    work["Voucher Number"] = work["Voucher Number"].fillna("").astype(str).str.strip()

    # Create a synthetic voucher ID when voucher number is missing.
    missing = work["Voucher Number"].eq("") | work["Voucher Number"].str.lower().eq("nan")
    work.loc[missing, "Voucher Number"] = [
        f"AUTO-{i+1:06d}" for i in range(missing.sum())
    ]

    voucher_rows = []

    for voucher_no, grp in work.groupby("Voucher Number", sort=False):
        grp = grp.copy()

        date_values = grp["Date"].dropna()
        date = date_values.iloc[0] if len(date_values) else pd.NaT

        debit_accounts = grp.loc[grp["Debit"] > 0, "Ledger Account"]
        credit_accounts = grp.loc[grp["Credit"] > 0, "Ledger Account"]

        total_debit = float(grp["Debit"].sum())
        total_credit = float(grp["Credit"].sum())

        party_candidate = first_nonblank(grp["Party Name"])
        account_names_clean = {
            clean_party_name(x)
            for x in grp["Ledger Account"].fillna("").astype(str)
            if str(x).strip()
        }

        # In some Tally-style exports "Particulars" may contain an account name
        # rather than a real external party. Avoid treating a ledger account itself
        # as a vendor/customer for party-history tests.
        if clean_party_name(party_candidate) in account_names_clean:
            party_candidate = ""

        voucher_rows.append({
            "Date": date,
            "Voucher Number": voucher_no,
            "Voucher Type": first_nonblank(grp["Voucher Type"]),
            "Party Name": party_candidate,
            "Narration": first_nonblank(grp["Narration"]),
            "Debit Accounts": unique_join(debit_accounts),
            "Credit Accounts": unique_join(credit_accounts),
            "All Accounts": unique_join(grp["Ledger Account"]),
            "Debit Total": total_debit,
            "Credit Total": total_credit,
            "Amount": max(total_debit, total_credit),
            "Created By": first_nonblank(grp["Created By"]),
            "Entry Time": first_nonblank(grp["Entry Time"]),
            "Invoice No": first_nonblank(grp["Invoice No"]),
            "GSTIN": first_nonblank(grp["GSTIN"]),
            "PAN": first_nonblank(grp["PAN"]),
            "Bank Reference": first_nonblank(grp["Bank Reference"]),
        })

    result = pd.DataFrame(voucher_rows)
    if not result.empty:
        result["Date"] = pd.to_datetime(result["Date"], errors="coerce")
        result.sort_values(["Date", "Voucher Number"], inplace=True, na_position="last")
        result.reset_index(drop=True, inplace=True)
    return result


def add_flag(flag_sets, scores, idx, flag_name, points=None):
    if flag_name in flag_sets[idx]:
        return
    flag_sets[idx].add(flag_name)
    scores[idx] += RISK_WEIGHTS.get(flag_name, points or 0)


def is_related_party(party, related_names):
    cleaned = clean_party_name(party)
    if not cleaned:
        return False, ""
    for original in related_names:
        rp = clean_party_name(original)
        if not rp:
            continue
        if cleaned == rp:
            return True, original
    return False, ""


def time_is_late(value):
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none"}:
        return False
    match = re.match(r"^\s*(\d{1,2}):(\d{2})", text)
    if not match:
        return False
    hour = int(match.group(1))
    return hour >= 21 or hour < 6


def classify_priority(score):
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    if score >= 20:
        return "LOW"
    return "NO SIGNIFICANT FLAG"


def run_red_flag_analysis(vouchers, materiality, approval_threshold, fy_text, related_names):
    """
    Stage 2 transparent / explainable audit analytics.
    These are risk indicators for auditor review, not conclusions of fraud.
    """
    if vouchers is None or vouchers.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = vouchers.copy()
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
    fy_start, fy_end = fy_bounds(fy_text)

    flag_sets = {idx: set() for idx in df.index}
    scores = {idx: 0 for idx in df.index}
    matched_related = {idx: "" for idx in df.index}
    pattern_rows = []

    # Normalize frequently used text once.
    df["_party_clean"] = df["Party Name"].map(clean_party_name)
    df["_text"] = (
        df["All Accounts"].fillna("").astype(str)
        + " "
        + df["Narration"].fillna("").astype(str)
        + " "
        + df["Voucher Type"].fillna("").astype(str)
    ).str.lower()

    # --------------------------------------------------------
    # 1. High / material value
    # --------------------------------------------------------
    for idx, row in df.iterrows():
        if materiality > 0 and row["Amount"] >= materiality:
            add_flag(flag_sets, scores, idx, "High / Material Value")

    # --------------------------------------------------------
    # 2. Year-end (last 7 days of FY)
    # --------------------------------------------------------
    year_end_start = fy_end - pd.Timedelta(days=6)
    for idx, row in df.iterrows():
        date = row["Date"]
        if pd.notna(date) and year_end_start <= date <= fy_end:
            add_flag(flag_sets, scores, idx, "Year-End Entry")

    # --------------------------------------------------------
    # 3. Round figures — only meaningful-sized values
    # --------------------------------------------------------
    for idx, row in df.iterrows():
        amount = row["Amount"]
        if amount >= max(5_00_000, materiality * 0.10) and amount % 1_00_000 == 0:
            add_flag(flag_sets, scores, idx, "Round Figure")

    # --------------------------------------------------------
    # 4. Exact / near duplicate payment pattern
    # Same date + same party + same amount; invoice strengthens the case.
    # --------------------------------------------------------
    duplicate_basis = df[
        (df["_party_clean"] != "") & (df["Amount"] > 0) & df["Date"].notna()
    ].copy()

    for _, grp in duplicate_basis.groupby(["Date", "_party_clean", "Amount"], dropna=False):
        if len(grp) < 2:
            continue

        # Avoid calling repetitive monthly patterns duplicates when dates differ;
        # this grouping is same-date only.
        idxs = list(grp.index)
        for idx in idxs:
            add_flag(flag_sets, scores, idx, "Duplicate / Near-Duplicate")

        party = first_nonblank(grp["Party Name"])
        invoices = unique_join(grp["Invoice No"], ", ")
        pattern_rows.append({
            "Pattern": "Possible Duplicate / Near-Duplicate",
            "Date / Window": format_date(grp["Date"].iloc[0]),
            "Party": party,
            "Amount / Value": inr(float(grp["Amount"].iloc[0])),
            "Details": f"{len(grp)} vouchers with same party, date and amount"
                       + (f"; invoice(s): {invoices}" if invoices else ""),
            "Voucher(s)": ", ".join(grp["Voucher Number"].astype(str)),
        })

    # --------------------------------------------------------
    # 5. Split payments below approval threshold
    # --------------------------------------------------------
    if approval_threshold > 0:
        candidates = df[
            (df["_party_clean"] != "")
            & df["Date"].notna()
            & (df["Amount"] >= approval_threshold * 0.80)
            & (df["Amount"] < approval_threshold)
        ]

        for (date, party_clean), grp in candidates.groupby(["Date", "_party_clean"]):
            total = float(grp["Amount"].sum())
            if len(grp) >= 3 and total > approval_threshold * 2:
                for idx in grp.index:
                    add_flag(flag_sets, scores, idx, "Possible Split Transaction")

                pattern_rows.append({
                    "Pattern": "Possible Transaction Splitting",
                    "Date / Window": format_date(date),
                    "Party": first_nonblank(grp["Party Name"]),
                    "Amount / Value": inr(total),
                    "Details": (
                        f"{len(grp)} same-day vouchers; each between 80% and 100% "
                        f"of approval threshold {inr(approval_threshold)}"
                    ),
                    "Voucher(s)": ", ".join(grp["Voucher Number"].astype(str)),
                })

    # --------------------------------------------------------
    # 6. Related parties
    # --------------------------------------------------------
    for idx, row in df.iterrows():
        matched, matched_name = is_related_party(row["Party Name"], related_names)
        if matched:
            matched_related[idx] = matched_name
            add_flag(flag_sets, scores, idx, "Related Party")

    # --------------------------------------------------------
    # 7. New / dormant party with material amount
    # New: first appearance after 8 months and <=2 total vouchers.
    # Dormant: gap of 180+ days.
    # --------------------------------------------------------
    if materiality > 0:
        party_groups = df[df["_party_clean"] != ""].sort_values("Date").groupby("_party_clean")

        for _, grp in party_groups:
            grp = grp.sort_values("Date")
            total_count = len(grp)
            prev_date = None

            for position, (idx, row) in enumerate(grp.iterrows()):
                date = row["Date"]
                if pd.isna(date):
                    continue

                is_new_late = (
                    position == 0
                    and total_count <= 2
                    and date >= fy_start + pd.Timedelta(days=240)
                    and row["Amount"] >= materiality
                )

                is_dormant = (
                    prev_date is not None
                    and (date - prev_date).days >= 180
                    and row["Amount"] >= materiality
                )

                if is_new_late or is_dormant:
                    add_flag(flag_sets, scores, idx, "New / Dormant Party")

                prev_date = date

    # --------------------------------------------------------
    # 8. Unusual amount against party's own history
    # Transparent statistical rule: 4x historical median.
    # --------------------------------------------------------
    for _, grp in df[df["_party_clean"] != ""].sort_values("Date").groupby("_party_clean"):
        history = []

        for idx, row in grp.sort_values("Date").iterrows():
            amount = float(row["Amount"])

            if len(history) >= 3:
                median = float(pd.Series(history).median())
                if (
                    median > 0
                    and amount >= materiality
                    and amount >= median * 4
                ):
                    add_flag(flag_sets, scores, idx, "Unusual Party Amount")

            if amount > 0:
                history.append(amount)

    # --------------------------------------------------------
    # 9. Manual journal
    # --------------------------------------------------------
    for idx, row in df.iterrows():
        vtype = str(row["Voucher Type"]).lower()
        if (
            ("journal" in vtype or re.search(r"\bjv\b", vtype))
            and (
                row["Amount"] >= materiality
                or (
                    pd.notna(row["Date"])
                    and row["Date"] >= year_end_start
                    and row["Amount"] >= materiality * 0.50
                )
            )
        ):
            add_flag(flag_sets, scores, idx, "Manual Journal")

    # --------------------------------------------------------
    # 10A. Large cash transactions
    # --------------------------------------------------------
    cash_threshold = max(10_00_000, materiality * 0.20)

    for idx, row in df.iterrows():
        text = row["_text"]

        # "Cash Credit" is a bank borrowing facility, not a cash-in-hand transaction.
        cash_indicator = bool(re.search(
            r"cash[- ]?in[- ]?hand|cash withdrawal|cash withdrawn|cash payment|cash receipt|petty cash",
            text,
        ))

        if cash_indicator and "cash credit" not in text and row["Amount"] >= cash_threshold:
            add_flag(flag_sets, scores, idx, "Large Cash Transaction")

    # --------------------------------------------------------
    # 10B. Director / group fund movement
    # --------------------------------------------------------
    fund_terms = r"advance|loan|inter.?corporate|director|holding|group company|security deposit"

    for idx, row in df.iterrows():
        if matched_related[idx] and re.search(fund_terms, row["_text"]):
            add_flag(flag_sets, scores, idx, "Director / Group Fund Movement")

    # --------------------------------------------------------
    # 10C. Borrowing / end-use pattern
    # Borrowing receipt followed within 7 days by a related-party /
    # advance / investment / non-operating use.
    # --------------------------------------------------------
    borrowing_mask = df["_text"].str.contains(
        r"borrow|cash credit|working capital|term loan|unsecured loan",
        regex=True,
        na=False,
    )

    borrowings = df[borrowing_mask & (df["Amount"] >= materiality)].copy()

    for source_idx, source in borrowings.iterrows():
        if pd.isna(source["Date"]):
            continue

        window_end = source["Date"] + pd.Timedelta(days=7)

        possible_targets = df[
            (df["Date"] > source["Date"])
            & (df["Date"] <= window_end)
            & (df["Amount"] >= materiality)
            & (df.index != source_idx)
        ]

        for target_idx, target in possible_targets.iterrows():
            target_related = bool(matched_related[target_idx])
            target_non_operating = bool(re.search(
                r"advance|investment|mutual fund|director|holding|group company|security deposit|inter.?corporate",
                target["_text"],
            ))

            if not (target_related or target_non_operating):
                continue

            if target["Amount"] > source["Amount"] * 1.10:
                continue

            add_flag(flag_sets, scores, target_idx, "Possible Fund-Use / Borrowing Risk")

            days = int((target["Date"] - source["Date"]).days)
            pattern_rows.append({
                "Pattern": "Possible Borrowing End-Use Risk",
                "Date / Window": f"{format_date(source['Date'])} → {format_date(target['Date'])}",
                "Party": target["Party Name"],
                "Amount / Value": (
                    f"Borrowing {inr(source['Amount'])} → Transfer {inr(target['Amount'])}"
                ),
                "Details": (
                    f"Material transfer {days} day(s) after borrowing; "
                    "verify sanction terms and actual end use before drawing a conclusion."
                ),
                "Voucher(s)": f"{source['Voucher Number']} → {target['Voucher Number']}",
            })

    # --------------------------------------------------------
    # 11. Explicit reversal / reversing entry
    # --------------------------------------------------------
    reversal_mask = df["Narration"].fillna("").astype(str).str.lower().str.contains(
        r"\breversal\b|\breversed\b|\breverse\b",
        regex=True,
        na=False,
    )

    for idx in df.index[reversal_mask]:
        if df.at[idx, "Amount"] >= max(5_00_000, materiality * 0.20):
            add_flag(flag_sets, scores, idx, "Explicit Reversal")

    # --------------------------------------------------------
    # Supporting timing indicator — weekend or late-night.
    # --------------------------------------------------------
    for idx, row in df.iterrows():
        weekend = pd.notna(row["Date"]) and row["Date"].weekday() >= 5
        late = time_is_late(row["Entry Time"])

        if weekend or late:
            if row["Amount"] >= max(5_00_000, materiality * 0.20):
                add_flag(flag_sets, scores, idx, "Weekend / Unusual Timing")

    # --------------------------------------------------------
    # 12. Multiple independent indicators
    # --------------------------------------------------------
    final_rows = []

    for idx, row in df.iterrows():
        flags = sorted(flag_sets[idx])
        base_score = scores[idx]

        if len(flags) >= 5:
            bonus = 10
            bonus_label = "Multiple Risk Indicators (5+)"
        elif len(flags) >= 3:
            bonus = 5
            bonus_label = "Multiple Risk Indicators (3+)"
        else:
            bonus = 0
            bonus_label = ""

        score = min(100, base_score + bonus)
        reasons = flags.copy()
        if bonus_label:
            reasons.append(bonus_label)

        final_rows.append({
            "Risk Score": int(score),
            "Priority": classify_priority(score),
            "Date": row["Date"],
            "Voucher Number": row["Voucher Number"],
            "Voucher Type": row["Voucher Type"],
            "Party Name": row["Party Name"],
            "Amount": row["Amount"],
            "Debit Accounts": row["Debit Accounts"],
            "Credit Accounts": row["Credit Accounts"],
            "Narration": row["Narration"],
            "Created By": row["Created By"],
            "Entry Time": row["Entry Time"],
            "Related Party Match": matched_related[idx],
            "Flags": " | ".join(reasons),
            "Flag Count": len(flags),
        })

    analysis = pd.DataFrame(final_rows)

    priority_rank = {
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3,
        "NO SIGNIFICANT FLAG": 4,
    }

    analysis["_rank"] = analysis["Priority"].map(priority_rank)
    analysis.sort_values(
        ["_rank", "Risk Score", "Amount"],
        ascending=[True, False, False],
        inplace=True,
    )
    analysis.drop(columns=["_rank"], inplace=True)
    analysis.reset_index(drop=True, inplace=True)

    patterns = pd.DataFrame(pattern_rows)
    if not patterns.empty:
        patterns.drop_duplicates(inplace=True)
        patterns.reset_index(drop=True, inplace=True)

    return analysis, patterns


def count_flag(analysis, label):
    if analysis is None or analysis.empty:
        return 0
    return int(analysis["Flags"].fillna("").str.contains(re.escape(label), regex=True).sum())


def analysis_display_frame(df):
    display = df.copy()
    if "Date" in display.columns:
        display["Date"] = pd.to_datetime(display["Date"], errors="coerce").dt.strftime("%d-%b-%Y")
    if "Amount" in display.columns:
        display["Amount"] = display["Amount"].map(inr)
    return display



# ------------------------------------------------------------
# STAGE 3 — AI / ANOMALY LAYER
# ------------------------------------------------------------

AI_FLAG_WEIGHT = 15
FUZZY_RP_THRESHOLD = 90


def fuzzy_related_party_match(party, related_names, threshold=FUZZY_RP_THRESHOLD):
    """
    Returns:
        matched_name, score, match_type
    Exact cleaned-name matches are CONFIRMED.
    High-confidence fuzzy matches are POSSIBLE and require auditor confirmation.
    """
    cleaned_party = clean_party_name(party)

    if not cleaned_party or not related_names:
        return "", 0, ""

    cleaned_map = {}
    for original in related_names:
        cleaned = clean_party_name(original)
        if cleaned:
            cleaned_map[cleaned] = original

    if cleaned_party in cleaned_map:
        return cleaned_map[cleaned_party], 100, "Confirmed exact/cleaned-name match"

    choices = list(cleaned_map.keys())
    if not choices:
        return "", 0, ""

    match = process.extractOne(
        cleaned_party,
        choices,
        scorer=fuzz.token_set_ratio,
    )

    if not match:
        return "", 0, ""

    matched_clean, score, _ = match

    if score >= threshold:
        return cleaned_map[matched_clean], int(round(score)), "Possible fuzzy-name match"

    return "", int(round(score)), ""


def safe_ratio(numerator, denominator):
    if denominator is None or denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def build_ai_features(vouchers):
    """
    Build transparent numeric features for statistical anomaly detection.
    No text is sent anywhere and no external API is used.
    """
    df = vouchers.copy()

    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["_party_clean"] = df["Party Name"].map(clean_party_name)

    # Party history statistics
    party_stats = (
        df[df["_party_clean"] != ""]
        .groupby("_party_clean")["Amount"]
        .agg(["count", "median", "mean", "max"])
        .rename(columns={
            "count": "Party_Count",
            "median": "Party_Median",
            "mean": "Party_Mean",
            "max": "Party_Max",
        })
    )

    df = df.merge(
        party_stats,
        left_on="_party_clean",
        right_index=True,
        how="left",
    )

    df["Party_Count"] = df["Party_Count"].fillna(1)
    df["Party_Median"] = df["Party_Median"].fillna(df["Amount"].replace(0, 1))
    df["Party_Mean"] = df["Party_Mean"].fillna(df["Amount"].replace(0, 1))

    df["Amount_to_Party_Median"] = [
        safe_ratio(a, m)
        for a, m in zip(df["Amount"], df["Party_Median"])
    ]

    df["Log_Amount"] = (df["Amount"].clip(lower=0) + 1).map(lambda x: __import__("math").log1p(x))

    df["Day_of_Year"] = df["Date"].dt.dayofyear.fillna(0)
    df["Weekend"] = df["Date"].dt.weekday.fillna(-1).ge(5).astype(int)
    df["Month"] = df["Date"].dt.month.fillna(0).astype(int)

    df["Manual_Journal"] = (
        df["Voucher Type"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(r"journal|\bjv\b", regex=True)
        .astype(int)
    )

    df["Late_Time"] = df["Entry Time"].map(lambda x: 1 if time_is_late(x) else 0)

    return df


def run_isolation_forest(vouchers, contamination=0.08):
    """
    Unsupervised anomaly detection.

    It learns the distribution of the uploaded ledger itself rather than using a
    fixed rupee threshold.  We keep the model small and transparent:
    amount size, party-relative size, date, weekend, manual-JV and late-time features.
    """
    if vouchers is None or len(vouchers) < 20:
        result = vouchers.copy()
        result["AI Anomaly"] = False
        result["AI Anomaly Score"] = 0
        result["AI Reason"] = "Insufficient transactions for statistical anomaly model."
        return result

    df = build_ai_features(vouchers)

    feature_cols = [
        "Log_Amount",
        "Amount_to_Party_Median",
        "Party_Count",
        "Day_of_Year",
        "Weekend",
        "Manual_Journal",
        "Late_Time",
    ]

    X = df[feature_cols].replace([float("inf"), float("-inf")], 0).fillna(0)

    # Keep contamination bounded so small files are not flooded with flags.
    contamination = max(0.02, min(0.10, contamination))

    model = IsolationForest(
        n_estimators=250,
        contamination=contamination,
        random_state=104,
    )

    predictions = model.fit_predict(X)
    decision = model.decision_function(X)

    # Lower decision score = more anomalous.
    # Convert to a simple 0–100 relative anomaly score.
    decision_series = pd.Series(decision, index=df.index)

    d_min = float(decision_series.min())
    d_max = float(decision_series.max())

    if d_max == d_min:
        ai_score = pd.Series(0, index=df.index)
    else:
        ai_score = (
            100
            * (d_max - decision_series)
            / (d_max - d_min)
        ).round().clip(0, 100)

    df["AI Anomaly"] = predictions == -1
    df["AI Anomaly Score"] = ai_score.astype(int)

    reasons = []

    for _, row in df.iterrows():
        row_reasons = []

        if row["Amount_to_Party_Median"] >= 4 and row["Party_Count"] >= 3:
            row_reasons.append(
                f"Amount is {row['Amount_to_Party_Median']:.1f}× the party's median transaction"
            )

        if row["Manual_Journal"]:
            row_reasons.append("Manual journal")

        if row["Weekend"]:
            row_reasons.append("Weekend posting")

        if row["Late_Time"]:
            row_reasons.append("Late-night posting")

        if row["Party_Count"] <= 2 and row["Amount"] > 0:
            row_reasons.append("Very limited party history")

        if not row_reasons:
            row_reasons.append("Unusual combination of amount, timing and transaction pattern")

        reasons.append("; ".join(row_reasons))

    df["AI Reason"] = reasons

    return df


def detect_monthly_account_spikes(std, materiality):
    """
    Detects debit-side monthly ledger spikes using the ledger's own history.

    A month is flagged when:
    - at least 4 months of prior history exist,
    - current month value is material,
    - and current month is >= 3x the median of prior months.
    """
    if std is None or std.empty:
        return pd.DataFrame()

    df = std.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Debit"] = pd.to_numeric(df["Debit"], errors="coerce").fillna(0.0)

    df = df[
        df["Date"].notna()
        & (df["Debit"] > 0)
        & (df["Ledger Account"].fillna("").astype(str).str.strip() != "")
    ].copy()

    if df.empty:
        return pd.DataFrame()

    df["Month"] = df["Date"].dt.to_period("M").astype(str)

    monthly = (
        df.groupby(["Ledger Account", "Month"], as_index=False)["Debit"]
        .sum()
        .rename(columns={"Debit": "Monthly Debit"})
    )

    output = []

    for ledger, grp in monthly.groupby("Ledger Account"):
        grp = grp.sort_values("Month").reset_index(drop=True)
        history = []

        for _, row in grp.iterrows():
            current = float(row["Monthly Debit"])

            if len(history) >= 4:
                median_prior = float(pd.Series(history).median())

                if (
                    median_prior > 0
                    and current >= max(materiality, median_prior * 3)
                ):
                    output.append({
                        "Ledger Account": ledger,
                        "Month": row["Month"],
                        "Current Month": current,
                        "Prior Median": median_prior,
                        "Multiple of Normal": round(current / median_prior, 1),
                        "AI Observation": (
                            f"Monthly debit is {current / median_prior:.1f}× the median of prior months."
                        ),
                    })

            history.append(current)

    result = pd.DataFrame(output)

    if not result.empty:
        result.sort_values(
            ["Multiple of Normal", "Current Month"],
            ascending=[False, False],
            inplace=True,
        )
        result.reset_index(drop=True, inplace=True)

    return result


def merge_stage2_and_ai(stage2_analysis, ai_vouchers, related_names):
    """
    Add the AI layer to Stage 2 results without hiding the original explainable rules.
    """
    if stage2_analysis is None or stage2_analysis.empty:
        return stage2_analysis

    result = stage2_analysis.copy()

    ai_lookup = ai_vouchers.set_index("Voucher Number")

    ai_scores = []
    ai_flags = []
    ai_reasons = []
    fuzzy_names = []
    fuzzy_conf = []
    fuzzy_types = []
    combined_scores = []
    combined_priorities = []
    combined_flags = []

    for _, row in result.iterrows():
        voucher_no = row["Voucher Number"]

        if voucher_no in ai_lookup.index:
            ai_row = ai_lookup.loc[voucher_no]

            # In the unlikely case of duplicate index values, keep the first.
            if isinstance(ai_row, pd.DataFrame):
                ai_row = ai_row.iloc[0]

            anomaly = bool(ai_row.get("AI Anomaly", False))
            ai_score = int(ai_row.get("AI Anomaly Score", 0))
            ai_reason = str(ai_row.get("AI Reason", ""))

        else:
            anomaly = False
            ai_score = 0
            ai_reason = ""

        matched_name, confidence, match_type = fuzzy_related_party_match(
            row["Party Name"],
            related_names,
        )

        original_score = int(row["Risk Score"])
        new_score = original_score
        flags_text = str(row["Flags"] or "")

        if anomaly:
            new_score += AI_FLAG_WEIGHT
            if "AI Statistical Anomaly" not in flags_text:
                flags_text = (
                    flags_text + " | AI Statistical Anomaly"
                    if flags_text
                    else "AI Statistical Anomaly"
                )

        # A fuzzy match is not treated as a confirmed related party.
        # It adds a small audit-priority uplift only when the Stage 2 related-party
        # rule was not already triggered.
        if (
            match_type == "Possible fuzzy-name match"
            and "Related Party" not in flags_text
        ):
            new_score += 10
            flags_text = (
                flags_text + " | Possible Related Party Match"
                if flags_text
                else "Possible Related Party Match"
            )

        new_score = min(100, new_score)

        ai_scores.append(ai_score)
        ai_flags.append("YES" if anomaly else "NO")
        ai_reasons.append(ai_reason)
        fuzzy_names.append(matched_name)
        fuzzy_conf.append(confidence if matched_name else 0)
        fuzzy_types.append(match_type)
        combined_scores.append(new_score)
        combined_priorities.append(classify_priority(new_score))
        combined_flags.append(flags_text)

    result["AI Anomaly"] = ai_flags
    result["AI Anomaly Score"] = ai_scores
    result["AI Reason"] = ai_reasons
    result["AI Related Party Match"] = fuzzy_names
    result["RP Match Confidence"] = fuzzy_conf
    result["RP Match Type"] = fuzzy_types
    result["Risk Score"] = combined_scores
    result["Priority"] = combined_priorities
    result["Flags"] = combined_flags

    priority_rank = {
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3,
        "NO SIGNIFICANT FLAG": 4,
    }

    result["_rank"] = result["Priority"].map(priority_rank)

    result.sort_values(
        ["_rank", "Risk Score", "AI Anomaly Score", "Amount"],
        ascending=[True, False, False, False],
        inplace=True,
    )

    result.drop(columns=["_rank"], inplace=True)
    result.reset_index(drop=True, inplace=True)

    return result


# ------------------------------------------------------------
# FINAL DASHBOARD / INVESTIGATION / EXPORT HELPERS
# ------------------------------------------------------------

def risk_badge(priority):
    mapping = {
        "HIGH": "🔴 HIGH",
        "MEDIUM": "🟠 MEDIUM",
        "LOW": "🟡 LOW",
        "NO SIGNIFICANT FLAG": "🟢 NO SIGNIFICANT FLAG",
    }
    return mapping.get(priority, priority)


def suggested_auditor_actions(row):
    """
    Explainable auditor procedures based on the actual flags triggered.
    These are suggested procedures, not conclusions.
    """
    flags = str(row.get("Flags", "") or "")
    narration = str(row.get("Narration", "") or "").lower()
    account_text = (
        str(row.get("Debit Accounts", "") or "")
        + " "
        + str(row.get("Credit Accounts", "") or "")
    ).lower()

    actions = []

    def add(action):
        if action not in actions:
            actions.append(action)

    add("Inspect the underlying voucher and supporting documents.")
    add("Verify authorization / approval and the business purpose of the transaction.")

    if "Related Party" in flags or "Possible Related Party Match" in flags:
        add("Confirm the related-party relationship and verify disclosure / approval requirements.")
        add("Check whether pricing and commercial terms are consistent with the business rationale.")

    if "High / Material Value" in flags:
        add("Perform detailed substantive verification because the transaction is material.")

    if "Year-End Entry" in flags:
        add("Perform cut-off testing and verify whether the transaction belongs to the correct financial year.")

    if "Manual Journal" in flags:
        add("Inspect journal support, maker-checker approval and the system audit trail.")

    if "Duplicate / Near-Duplicate" in flags:
        add("Trace both entries to invoices and bank payments and verify whether a duplicate payment / posting occurred.")

    if "Possible Split Transaction" in flags:
        add("Compare the grouped transactions with the internal approval threshold and procurement / approval policy.")

    if "Possible Fund-Use / Borrowing Risk" in flags or "Director / Group Fund Movement" in flags:
        add("Trace the source and end use of funds through the bank statement.")
        add("Verify borrowing sanction terms, Board approval and recovery / settlement of the advance.")

    if "Large Cash Transaction" in flags:
        add("Verify cash book, supporting vouchers, recipients and subsequent utilization of cash.")

    if "Explicit Reversal" in flags:
        add("Inspect the original entry and subsequent reversal and assess whether it affects cut-off or reported results.")

    if "Unusual Party Amount" in flags or "AI Statistical Anomaly" in flags:
        add("Compare with the party's historical transactions and obtain an explanation for the unusual amount / pattern.")

    if "New / Dormant Party" in flags:
        add("Verify vendor / customer onboarding, existence, PAN/GSTIN, agreement, invoice and commercial rationale.")

    if "Round Figure" in flags:
        add("Inspect the basis / computation supporting the round-figure amount.")

    if "Weekend / Unusual Timing" in flags:
        add("Review the posting timestamp and authorization for the unusual timing.")

    if "sales" in account_text or "sales" in narration or "revenue" in narration:
        add("Verify invoice, dispatch / service evidence, customer acceptance and subsequent realization.")

    if "consult" in narration or "professional" in account_text:
        add("Verify agreement, invoice, deliverables / evidence of services, TDS and GST treatment.")

    if "suspense" in account_text:
        add("Obtain the suspense-account reconciliation and identify the final counter-account / beneficiary.")

    if "plant" in account_text or "machinery" in account_text or "capital" in narration:
        add("Assess whether the expenditure is capital or revenue in nature and verify depreciation treatment.")

    if "director" in account_text or "director" in narration:
        add("Verify statutory / disclosure implications and subsequent recovery or settlement.")

    return actions[:10]


def flag_summary_from_analysis(analysis):
    labels = [
        "High / Material Value",
        "Year-End Entry",
        "Round Figure",
        "Duplicate / Near-Duplicate",
        "Possible Split Transaction",
        "Related Party",
        "Possible Related Party Match",
        "New / Dormant Party",
        "Unusual Party Amount",
        "Manual Journal",
        "Large Cash Transaction",
        "Director / Group Fund Movement",
        "Possible Fund-Use / Borrowing Risk",
        "Explicit Reversal",
        "Weekend / Unusual Timing",
        "AI Statistical Anomaly",
    ]

    rows = []
    for label in labels:
        count = count_flag(analysis, label)
        if count:
            rows.append({"Red Flag": label, "Transactions Flagged": count})

    return pd.DataFrame(rows)


def build_export_workbook_bytes(company_name, fy, analysis, patterns, monthly_spikes, std):
    output = io.BytesIO()

    high = analysis[analysis["Priority"] == "HIGH"].copy()
    flagged = analysis[analysis["Priority"] != "NO SIGNIFICANT FLAG"].copy()
    related = analysis[
        analysis["Flags"].fillna("").str.contains(
            "Related Party|Possible Related Party Match",
            regex=True,
        )
    ].copy()

    dup_split = analysis[
        analysis["Flags"].fillna("").str.contains(
            "Duplicate / Near-Duplicate|Possible Split Transaction",
            regex=True,
        )
    ].copy()

    fund_flow = analysis[
        analysis["Flags"].fillna("").str.contains(
            "Possible Fund-Use / Borrowing Risk|Director / Group Fund Movement|Large Cash Transaction",
            regex=True,
        )
    ].copy()

    year_end = analysis[
        analysis["Flags"].fillna("").str.contains(
            "Year-End Entry|Manual Journal|Explicit Reversal",
            regex=True,
        )
    ].copy()

    procedure_rows = []
    for _, row in flagged.iterrows():
        for action in suggested_auditor_actions(row):
            procedure_rows.append({
                "Voucher Number": row["Voucher Number"],
                "Date": row["Date"],
                "Party Name": row["Party Name"],
                "Risk Score": row["Risk Score"],
                "Priority": row["Priority"],
                "Suggested Auditor Procedure": action,
            })
    procedures = pd.DataFrame(procedure_rows)

    summary = pd.DataFrame([
        ["Company", company_name],
        ["Financial Year", fy],
        ["Ledger Rows Analysed", len(std)],
        ["Accounting Vouchers Analysed", len(analysis)],
        ["High Priority", int((analysis["Priority"] == "HIGH").sum())],
        ["Medium Priority", int((analysis["Priority"] == "MEDIUM").sum())],
        ["Low Priority", int((analysis["Priority"] == "LOW").sum())],
        ["No Significant Flag", int((analysis["Priority"] == "NO SIGNIFICANT FLAG").sum())],
        ["AI Statistical Anomalies", int((analysis["AI Anomaly"] == "YES").sum()) if "AI Anomaly" in analysis else 0],
        ["Important Note", "AuditEye identifies risk indicators for auditor review. A flag is not evidence or a conclusion of fraud."],
    ], columns=["Particular", "Result"])

    sheets = {
        "Executive Summary": summary,
        "High Priority": high,
        "All Red Flags": flagged,
        "Related Parties": related,
        "Duplicate & Split": dup_split,
        "Fund Flow Patterns": fund_flow,
        "Year End & Journals": year_end,
        "Patterns Detected": patterns if patterns is not None else pd.DataFrame(),
        "Monthly Spikes": monthly_spikes if monthly_spikes is not None else pd.DataFrame(),
        "Audit Procedures": procedures,
    }

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df_sheet in sheets.items():
            safe_df = df_sheet.copy()

            for col in safe_df.columns:
                if pd.api.types.is_datetime64_any_dtype(safe_df[col]):
                    safe_df[col] = safe_df[col].dt.strftime("%d-%b-%Y")

            safe_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

        workbook = writer.book

        for ws in workbook.worksheets:
            ws.freeze_panes = "A2"

            # Header formatting
            for cell in ws[1]:
                cell.font = __import__("openpyxl").styles.Font(
                    bold=True,
                    color="FFFFFF",
                )
                cell.fill = __import__("openpyxl").styles.PatternFill(
                    "solid",
                    fgColor="1F6E8C",
                )
                cell.alignment = __import__("openpyxl").styles.Alignment(
                    horizontal="center",
                    vertical="center",
                    wrap_text=True,
                )

            # Auto width with sensible cap
            for column_cells in ws.columns:
                max_length = 0
                letter = column_cells[0].column_letter

                for cell in column_cells:
                    try:
                        value = "" if cell.value is None else str(cell.value)
                        max_length = max(max_length, len(value))
                    except Exception:
                        pass

                ws.column_dimensions[letter].width = min(max(max_length + 2, 12), 55)

    output.seek(0)
    return output.getvalue()


def dashboard_display_frame(df):
    display = df.copy()
    if "Date" in display.columns:
        display["Date"] = pd.to_datetime(display["Date"], errors="coerce").dt.strftime("%d-%b-%Y")
    if "Amount" in display.columns:
        display["Amount"] = display["Amount"].map(inr)
    return display


def transaction_label(row):
    date_text = format_date(row["Date"])
    party = row["Party Name"] if str(row["Party Name"]).strip() else "(No Party)"
    return (
        f"{row['Risk Score']:>3}/100 | {date_text} | "
        f"{party} | {inr(row['Amount'])} | {row['Voucher Number']}"
    )

# ------------------------------------------------------------
# HEADER / SIDEBAR
# ------------------------------------------------------------

st.markdown('<div class="main-title">🔍 AUDITEYE</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">AI Assisted Audit Red Flag Analyzer — Complete Demo</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### AuditEye Workflow")
    steps = [
        "1. Company Profile",
        "2. Upload Ledger",
        "3. Map & Validate",
        "4. Audit Analysis",
        "5. Investigation",
    ]

    for idx, label in enumerate(steps, start=1):
        if idx == st.session_state.step:
            st.markdown(f"**▶ {label}**")
        elif idx <= 5:
            st.markdown(label)
        else:
            st.markdown(f"🔒 {label}")

    st.divider()
    st.caption("Complete classroom demo")
    st.caption("Upload → Validate → Audit Rules → AI Anomalies → Dashboard → Investigation → Export")

# ------------------------------------------------------------
# STEP 1 — COMPANY PROFILE
# ------------------------------------------------------------

if st.session_state.step == 1:
    st.markdown("## 1. Company & Audit Profile")
    st.caption("This gives AuditEye the business context that will later be used by the red-flag engine.")

    col1, col2 = st.columns(2)

    with col1:
        company_name = st.text_input(
            "Company Name",
            value=st.session_state.get("company_name", "Aarav Precision Components Pvt Ltd"),
        )

        nature = st.selectbox(
            "Nature of Business",
            [
                "Manufacturing - Auto Components",
                "Manufacturing - General",
                "Trading",
                "Services",
                "Construction / Real Estate",
                "Other",
            ],
            index=0,
        )

        turnover = st.number_input(
            "Annual Turnover (₹)",
            min_value=0.0,
            value=float(st.session_state.get("turnover", 100_00_00_000)),
            step=10_00_000.0,
            format="%.0f",
        )

        wc_borrowing = st.number_input(
            "Working Capital Borrowing (₹)",
            min_value=0.0,
            value=float(st.session_state.get("wc_borrowing", 25_00_00_000)),
            step=10_00_000.0,
            format="%.0f",
        )

    with col2:
        fy = st.selectbox(
            "Financial Year",
            ["2025-26", "2024-25", "2023-24"],
            index=0,
        )

        materiality = st.number_input(
            "Audit Materiality (₹)",
            min_value=0.0,
            value=float(st.session_state.get("materiality", 50_00_000)),
            step=1_00_000.0,
            format="%.0f",
        )

        approval_threshold = st.number_input(
            "Internal Approval Threshold (₹)",
            min_value=0.0,
            value=float(st.session_state.get("approval_threshold", 5_00_000)),
            step=50_000.0,
            format="%.0f",
        )

        term_loan = st.number_input(
            "Term Loan (₹)",
            min_value=0.0,
            value=float(st.session_state.get("term_loan", 10_00_00_000)),
            step=10_00_000.0,
            format="%.0f",
        )

    directors = st.text_input(
        "Directors / Promoters",
        value=st.session_state.get("directors", "Rohan Mehta, Neha Mehta"),
        help="Separate multiple names with commas.",
    )

    related_parties = st.text_area(
        "Known Related Parties / Group Entities",
        value=st.session_state.get(
            "related_parties",
            "RM Holdings Pvt Ltd, Mehta Industrial Supplies, Mehta Family Trust"
        ),
        height=90,
        help="Separate names with commas or new lines. Stage 2 uses confirmed-name matching."
    )

    st.info(
        "Why this matters: a ₹1 crore transaction may be normal for one business and unusual for another. "
        "AuditEye will later use this profile only as context — not as proof of wrongdoing."
    )

    if st.button("SAVE & CONTINUE →", type="primary", use_container_width=True):
        st.session_state.company_name = company_name
        st.session_state.nature = nature
        st.session_state.turnover = turnover
        st.session_state.wc_borrowing = wc_borrowing
        st.session_state.term_loan = term_loan
        st.session_state.fy = fy
        st.session_state.materiality = materiality
        st.session_state.approval_threshold = approval_threshold
        st.session_state.directors = directors
        st.session_state.related_parties = related_parties
        st.session_state.profile_saved = True
        st.session_state.step = 2
        st.rerun()

# ------------------------------------------------------------
# STEP 2 — UPLOAD / PASTE
# ------------------------------------------------------------

elif st.session_state.step == 2:
    st.markdown("## 2. Upload Transaction Ledger / Day Book")
    st.caption("Export from Tally, Zoho Books, Excel, Google Sheets, CSV or another accounting system.")

    tab_upload, tab_paste = st.tabs(["📂 Upload Excel / CSV", "📋 Paste Excel / Google Sheets Data"])

    with tab_upload:
        uploaded_file = st.file_uploader(
            "Choose ledger file",
            type=["xlsx", "xls", "csv"],
            help="Upload a transaction-level General Ledger, Day Book or Voucher Register.",
        )

        if uploaded_file is not None:
            try:
                if uploaded_file.name.lower().endswith(".csv"):
                    df = read_csv_flexible(uploaded_file)
                else:
                    df = read_excel_flexible(uploaded_file)

                df = drop_obvious_empty_rows(df)

                if len(df.columns) < 2:
                    st.error("The uploaded file does not appear to contain a usable tabular ledger.")
                else:
                    source_type = detect_source(df.columns)

                    st.session_state.raw_df = df
                    st.session_state.source_name = uploaded_file.name
                    st.session_state.source_type = source_type
                    st.session_state.mapping = auto_mapping(df.columns)

                    st.success("Ledger uploaded successfully.")

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Rows detected", f"{len(df):,}")
                    m2.metric("Columns detected", len(df.columns))
                    m3.metric("Source layout", source_type)

                    st.dataframe(df.head(12), use_container_width=True, hide_index=True)

            except Exception as error:
                st.error(f"Could not read the uploaded file: {error}")

    with tab_paste:
        pasted = st.text_area(
            "Paste copied ledger rows here",
            height=240,
            placeholder="Date\tParticulars\tVch Type\tVch No.\tDebit\tCredit\tNarration\n...",
        )

        if st.button("IMPORT PASTED DATA", use_container_width=True):
            try:
                pasted_df = read_pasted_table(pasted)

                if pasted_df is None or pasted_df.empty:
                    st.warning("Paste ledger data first.")
                else:
                    pasted_df = drop_obvious_empty_rows(pasted_df)
                    st.session_state.raw_df = pasted_df
                    st.session_state.source_name = "Pasted Excel / Google Sheets data"
                    st.session_state.source_type = detect_source(pasted_df.columns)
                    st.session_state.mapping = auto_mapping(pasted_df.columns)
                    st.success(f"Imported {len(pasted_df):,} rows.")
                    st.dataframe(pasted_df.head(12), use_container_width=True, hide_index=True)

            except Exception as error:
                st.error(f"Could not read pasted data: {error}")

    if st.session_state.raw_df is not None:
        st.markdown("---")
        st.markdown(
            f"""
            <div class="success-box">
            <b>Ready for column mapping</b><br>
            Source: {st.session_state.source_name}<br>
            Layout detected: {st.session_state.source_type}
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("← BACK TO PROFILE", use_container_width=True):
                st.session_state.step = 1
                st.rerun()

        with c2:
            if st.button("CONTINUE TO MAPPING →", type="primary", use_container_width=True):
                st.session_state.step = 3
                st.rerun()

# ------------------------------------------------------------
# STEP 3 — MAPPING & VALIDATION
# ------------------------------------------------------------

elif st.session_state.step == 3:
    if st.session_state.raw_df is None:
        st.warning("Please upload or paste a ledger first.")
        if st.button("GO TO UPLOAD"):
            st.session_state.step = 2
            st.rerun()
        st.stop()

    df = st.session_state.raw_df
    columns = list(df.columns)
    detected = st.session_state.mapping or auto_mapping(columns)

    st.markdown("## 3. Column Mapping & Validation")
    st.caption("AuditEye has suggested mappings. Review them and correct any field using the dropdowns.")

    st.markdown(
        f"**Source:** {st.session_state.source_name}  \n"
        f"**Detected layout:** {st.session_state.source_type}"
    )

    mapping = {}

    required_fields = [
        "Date",
        "Ledger Account",
        "Party Name",
        "Voucher Type",
        "Voucher Number",
        "Narration",
        "Debit",
        "Credit",
        "Amount",
        "Dr/Cr",
        "Created By",
        "Entry Time",
        "Invoice No",
        "GSTIN",
        "PAN",
        "Bank Reference",
    ]

    none_label = "— Not Available —"
    options = [none_label] + columns

    left, right = st.columns(2)

    for i, field in enumerate(required_fields):
        target = left if i % 2 == 0 else right

        with target:
            default_col = detected.get(field)
            default_index = options.index(default_col) if default_col in options else 0

            choice = st.selectbox(
                field,
                options,
                index=default_index,
                key=f"map_{field}",
            )

            mapping[field] = None if choice == none_label else choice

    st.session_state.mapping = mapping

    st.markdown("---")

    if not mapping_ready(mapping):
        st.error(
            "Minimum mapping required: Date + Ledger Account + either Debit/Credit columns "
            "or an Amount column."
        )
    else:
        if st.button("CONFIRM MAPPING & VALIDATE LEDGER", type="primary", use_container_width=True):
            standardized = standardize_ledger(df, mapping)
            st.session_state.standard_df = standardized

    if st.session_state.standard_df is not None:
        std = st.session_state.standard_df

        total_debit = float(std["Debit"].sum())
        total_credit = float(std["Credit"].sum())
        difference = total_debit - total_credit
        tolerance = max(1.0, max(abs(total_debit), abs(total_credit)) * 0.000001)
        balanced = abs(difference) <= tolerance

        valid_dates = std["Date"].notna().sum()
        date_min = std["Date"].min() if valid_dates else pd.NaT
        date_max = std["Date"].max() if valid_dates else pd.NaT

        st.markdown("### Ledger Validation")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Transaction Rows", f"{len(std):,}")
        m2.metric("Total Debit", inr(total_debit))
        m3.metric("Total Credit", inr(total_credit))
        m4.metric("Difference", inr(difference))

        if balanced:
            st.markdown(
                '<div class="success-box"><b>✓ Ledger debit and credit totals are balanced.</b></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="warning-box"><b>⚠ Debit and Credit totals differ by {inr(abs(difference))}.</b><br>'
                'Please verify whether the export is complete or whether the selected columns are correct.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("#### Data Quality")

        quality_col1, quality_col2 = st.columns(2)

        with quality_col1:
            st.write(f"✓ Rows imported: **{len(std):,}**")
            st.write(f"✓ Valid dates: **{valid_dates:,}**")
            st.write(f"✓ Date range: **{format_date(date_min)} to {format_date(date_max)}**")

        with quality_col2:
            st.write(f"✓ Ledger accounts identified: **{std['Ledger Account'].replace('', pd.NA).dropna().nunique():,}**")
            st.write(f"✓ Parties identified: **{std['Party Name'].replace('', pd.NA).dropna().nunique():,}**")
            st.write(f"✓ Voucher numbers identified: **{std['Voucher Number'].replace('', pd.NA).dropna().nunique():,}**")

        missing_notes = available_test_notes(mapping)

        if missing_notes:
            st.markdown("#### Optional fields not available")
            for note in missing_notes:
                st.warning(note)

        st.markdown("#### Standardized Ledger Preview")
        display = std.head(20).copy()

        if "Date" in display.columns:
            display["Date"] = display["Date"].dt.strftime("%d-%b-%Y")

        st.dataframe(display, use_container_width=True, hide_index=True)

        st.info(
            "The standardized ledger is the common AuditEye format. "
            "Click below to run the Stage 2 explainable red-flag tests."
        )

        c1, c2 = st.columns([1, 2])

        with c1:
            if st.button("← BACK TO UPLOAD", use_container_width=True):
                st.session_state.standard_df = None
                st.session_state.analysis_df = None
                st.session_state.patterns_df = None
                st.session_state.analysis_run = False
                st.session_state.ai_analysis_df = None
                st.session_state.ai_monthly_spikes_df = None
                st.session_state.ai_run = False
                st.session_state.final_export_bytes = None
                st.session_state.selected_voucher = ""
                st.session_state.step = 2
                st.rerun()

        with c2:
            if st.button("PROCEED TO AUDIT ANALYSIS →", type="primary", use_container_width=True):
                st.session_state.step = 4
                st.rerun()

# ------------------------------------------------------------
# STEP 4 — AUDIT RED-FLAG ANALYSIS
# ------------------------------------------------------------

elif st.session_state.step == 4:
    if st.session_state.standard_df is None:
        st.warning("Please complete ledger mapping and validation first.")
        if st.button("GO TO MAPPING"):
            st.session_state.step = 3
            st.rerun()
        st.stop()

    std = st.session_state.standard_df
    vouchers = build_voucher_view(std)

    st.markdown("## 4. Explainable Audit Red-Flag Analysis")
    st.caption(
        "AuditEye analyses voucher-level transactions so that the two sides of a normal double entry "
        "are treated as one accounting transaction."
    )

    info1, info2, info3, info4 = st.columns(4)
    info1.metric("Ledger Rows", f"{len(std):,}")
    info2.metric("Accounting Vouchers", f"{len(vouchers):,}")
    info3.metric("Materiality", inr(st.session_state.get("materiality", 0)))
    info4.metric("Approval Threshold", inr(st.session_state.get("approval_threshold", 0)))

    st.markdown("### Tests to be Run")

    test_names = [
        "1. High / material value",
        "2. Year-end entries",
        "3. Round-figure transactions",
        "4. Duplicate / near-duplicate transactions",
        "5. Possible split payments below approval threshold",
        "6. Related-party transactions",
        "7. New / dormant parties",
        "8. Unusual amount versus party history",
        "9. Manual journal entries",
        "10. Cash / director / borrowing end-use patterns",
        "11. Explicit reversals",
        "12. Multiple-risk combinations",
    ]

    c1, c2, c3 = st.columns(3)
    for i, name in enumerate(test_names):
        [c1, c2, c3][i % 3].write(f"✓ {name}")

    directors = split_names(st.session_state.get("directors", ""))
    related = split_names(st.session_state.get("related_parties", ""))
    related_names = directors + related

    with st.expander("Related parties used for Stage 2 matching"):
        if related_names:
            for name in related_names:
                st.write(f"• {name}")
        else:
            st.write("No related parties entered. Related-party testing will be skipped.")

    st.warning(
        "AuditEye identifies risk indicators requiring auditor review. "
        "A red flag is not evidence or a conclusion of fraud."
    )

    if st.button("🔍 RUN AUDIT ANALYSIS", type="primary", use_container_width=True):
        with st.spinner("Analysing ledger transactions and cross-transaction patterns..."):
            analysis, patterns = run_red_flag_analysis(
                vouchers=vouchers,
                materiality=float(st.session_state.get("materiality", 0)),
                approval_threshold=float(st.session_state.get("approval_threshold", 0)),
                fy_text=st.session_state.get("fy", "2025-26"),
                related_names=related_names,
            )

            st.session_state.analysis_df = analysis
            st.session_state.patterns_df = patterns
            st.session_state.analysis_run = True

        st.success("Audit analysis complete.")

    if st.session_state.analysis_run and st.session_state.analysis_df is not None:
        analysis = st.session_state.analysis_df
        patterns = st.session_state.patterns_df

        st.markdown("---")
        st.markdown("### Stage 2 Results")

        high = int((analysis["Priority"] == "HIGH").sum())
        medium = int((analysis["Priority"] == "MEDIUM").sum())
        low = int((analysis["Priority"] == "LOW").sum())
        normal = int((analysis["Priority"] == "NO SIGNIFICANT FLAG").sum())

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("🔴 High Priority", high)
        r2.metric("🟠 Medium Priority", medium)
        r3.metric("🟡 Low Priority", low)
        r4.metric("🟢 No Significant Flag", normal)

        st.caption(
            "The risk score is a relative audit-priority score. "
            "It is not a percentage probability of fraud."
        )

        st.markdown("#### Red-Flag Counts")

        flag_summary = pd.DataFrame([
            ["High / Material Value", count_flag(analysis, "High / Material Value")],
            ["Year-End Entry", count_flag(analysis, "Year-End Entry")],
            ["Round Figure", count_flag(analysis, "Round Figure")],
            ["Duplicate / Near-Duplicate", count_flag(analysis, "Duplicate / Near-Duplicate")],
            ["Possible Split Transaction", count_flag(analysis, "Possible Split Transaction")],
            ["Related Party", count_flag(analysis, "Related Party")],
            ["New / Dormant Party", count_flag(analysis, "New / Dormant Party")],
            ["Unusual Party Amount", count_flag(analysis, "Unusual Party Amount")],
            ["Manual Journal", count_flag(analysis, "Manual Journal")],
            ["Large Cash Transaction", count_flag(analysis, "Large Cash Transaction")],
            ["Director / Group Fund Movement", count_flag(analysis, "Director / Group Fund Movement")],
            ["Possible Fund-Use / Borrowing Risk", count_flag(analysis, "Possible Fund-Use / Borrowing Risk")],
            ["Explicit Reversal", count_flag(analysis, "Explicit Reversal")],
            ["Weekend / Unusual Timing", count_flag(analysis, "Weekend / Unusual Timing")],
        ], columns=["Red Flag", "Transactions Flagged"])

        st.dataframe(flag_summary, use_container_width=True, hide_index=True)

        st.markdown("#### Top Transactions Requiring Auditor Attention")

        top = analysis[
            analysis["Priority"] != "NO SIGNIFICANT FLAG"
        ].head(25)

        top_cols = [
            "Risk Score", "Priority", "Date", "Voucher Number",
            "Party Name", "Amount", "Voucher Type", "Flags"
        ]

        st.dataframe(
            analysis_display_frame(top[top_cols]),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Cross-Transaction Patterns Detected")

        if patterns is not None and not patterns.empty:
            st.dataframe(patterns, use_container_width=True, hide_index=True)
        else:
            st.info("No Stage 2 cross-transaction patterns were detected with the available fields.")

        st.markdown("#### Filter and Review Flagged Transactions")

        filter_priority = st.multiselect(
            "Priority",
            ["HIGH", "MEDIUM", "LOW", "NO SIGNIFICANT FLAG"],
            default=["HIGH", "MEDIUM"],
        )

        filtered = analysis[analysis["Priority"].isin(filter_priority)].copy()

        st.dataframe(
            analysis_display_frame(filtered),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.markdown("## Stage 3 — AI / Anomaly Layer")

        st.caption(
            "This layer does not replace the audit rules above. "
            "It looks for unusual behaviour that may not cross a fixed threshold."
        )

        ai1, ai2, ai3 = st.columns(3)

        with ai1:
            st.markdown("**Statistical Anomaly Detection**")
            st.write("Learns unusual combinations of amount, party history, timing and voucher characteristics.")

        with ai2:
            st.markdown("**Fuzzy Related-Party Matching**")
            st.write("Finds possible variants such as 'Mehta Indl Supplies' versus 'Mehta Industrial Supplies'.")

        with ai3:
            st.markdown("**Monthly Spike Detection**")
            st.write("Finds ledger months materially above their own historical pattern.")

        if st.button("🧠 RUN AI ANOMALY ANALYSIS", type="primary", use_container_width=True):
            with st.spinner("Running local statistical anomaly detection..."):
                ai_vouchers = run_isolation_forest(vouchers, contamination=0.08)

                ai_monthly = detect_monthly_account_spikes(
                    std,
                    float(st.session_state.get("materiality", 0)),
                )

                merged_analysis = merge_stage2_and_ai(
                    st.session_state.analysis_df,
                    ai_vouchers,
                    related_names,
                )

                st.session_state.ai_analysis_df = merged_analysis
                st.session_state.ai_monthly_spikes_df = ai_monthly
                st.session_state.ai_run = True
                st.session_state.final_export_bytes = None

            st.success("AI anomaly analysis complete.")

        if st.session_state.ai_run and st.session_state.ai_analysis_df is not None:
            ai_analysis = st.session_state.ai_analysis_df
            monthly_spikes = st.session_state.ai_monthly_spikes_df

            st.markdown("### AI Results")

            a1, a2, a3, a4 = st.columns(4)

            anomaly_count = int((ai_analysis["AI Anomaly"] == "YES").sum())
            possible_rp = int((ai_analysis["RP Match Type"] == "Possible fuzzy-name match").sum())
            high_after_ai = int((ai_analysis["Priority"] == "HIGH").sum())
            max_ai = int(ai_analysis["AI Anomaly Score"].max()) if len(ai_analysis) else 0

            a1.metric("AI Statistical Anomalies", anomaly_count)
            a2.metric("Possible Fuzzy RPT Matches", possible_rp)
            a3.metric("High Priority After AI", high_after_ai)
            a4.metric("Highest AI Anomaly Score", max_ai)

            st.caption(
                "AI Anomaly Score is a relative statistical outlier score within this uploaded ledger. "
                "It is not a probability of fraud."
            )

            st.markdown("#### Top AI Anomalies")

            ai_top = ai_analysis[
                ai_analysis["AI Anomaly"] == "YES"
            ].sort_values(
                ["AI Anomaly Score", "Risk Score"],
                ascending=[False, False],
            ).head(20)

            ai_cols = [
                "AI Anomaly Score",
                "Risk Score",
                "Priority",
                "Date",
                "Voucher Number",
                "Party Name",
                "Amount",
                "AI Reason",
                "Flags",
            ]

            if not ai_top.empty:
                st.dataframe(
                    analysis_display_frame(ai_top[ai_cols]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No statistical anomalies were identified.")

            st.markdown("#### Possible Related-Party Name Matches")

            fuzzy_df = ai_analysis[
                ai_analysis["RP Match Type"] == "Possible fuzzy-name match"
            ][[
                "Party Name",
                "AI Related Party Match",
                "RP Match Confidence",
                "Voucher Number",
                "Amount",
                "Risk Score",
            ]].copy()

            if not fuzzy_df.empty:
                fuzzy_df["Amount"] = fuzzy_df["Amount"].map(inr)
                st.dataframe(
                    fuzzy_df,
                    use_container_width=True,
                    hide_index=True,
                )
                st.warning(
                    "Fuzzy matches are POSSIBLE related-party matches only. "
                    "They require auditor confirmation before being treated as related parties."
                )
            else:
                st.info("No additional fuzzy related-party variants were identified in this ledger.")

            st.markdown("#### Monthly Ledger Spikes")

            if monthly_spikes is not None and not monthly_spikes.empty:
                spike_display = monthly_spikes.copy()
                spike_display["Current Month"] = spike_display["Current Month"].map(inr)
                spike_display["Prior Median"] = spike_display["Prior Median"].map(inr)

                st.dataframe(
                    spike_display,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No material monthly account spikes met the Stage 3 statistical criteria.")

            st.markdown("#### Combined Audit + AI Priority List")

            combined_cols = [
                "Risk Score",
                "Priority",
                "AI Anomaly Score",
                "AI Anomaly",
                "Date",
                "Voucher Number",
                "Party Name",
                "Amount",
                "Flags",
                "AI Reason",
            ]

            st.dataframe(
                analysis_display_frame(ai_analysis.head(30)[combined_cols]),
                use_container_width=True,
                hide_index=True,
            )

            st.success(
                "Stage 3 complete: AuditEye now combines transparent audit rules "
                "with local statistical anomaly detection and related-party name intelligence."
            )

        st.markdown("---")

        back1, next1 = st.columns([1, 2])

        with back1:
            if st.button("← BACK TO VALIDATION", use_container_width=True):
                st.session_state.step = 3
                st.rerun()

        with next1:
            if st.session_state.ai_run:
                if st.button(
                    "NEXT: DASHBOARD & INVESTIGATION →",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.step = 5
                    st.rerun()
            else:
                st.button(
                    "RUN AI ANALYSIS TO CONTINUE",
                    type="primary",
                    use_container_width=True,
                    disabled=True,
                )

# ------------------------------------------------------------
# STEP 5 — FINAL DASHBOARD & INVESTIGATION
# ------------------------------------------------------------

elif st.session_state.step == 5:
    if not st.session_state.ai_run or st.session_state.ai_analysis_df is None:
        st.warning("Please complete Stage 3 AI analysis first.")
        if st.button("GO TO AUDIT ANALYSIS"):
            st.session_state.step = 4
            st.rerun()
        st.stop()

    analysis = st.session_state.ai_analysis_df.copy()
    patterns = st.session_state.patterns_df
    monthly_spikes = st.session_state.ai_monthly_spikes_df
    std = st.session_state.standard_df

    company_name = st.session_state.get("company_name", "Company")
    fy = st.session_state.get("fy", "")

    st.markdown("## 5. Audit Risk Dashboard")
    st.caption(f"{company_name} | FY {fy}")

    # --------------------------------------------------------
    # TOP METRICS
    # --------------------------------------------------------
    high = int((analysis["Priority"] == "HIGH").sum())
    medium = int((analysis["Priority"] == "MEDIUM").sum())
    low = int((analysis["Priority"] == "LOW").sum())
    normal = int((analysis["Priority"] == "NO SIGNIFICANT FLAG").sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔴 High Priority", high)
    m2.metric("🟠 Medium Priority", medium)
    m3.metric("🟡 Low Priority", low)
    m4.metric("🟢 No Significant Flag", normal)

    st.caption(
        "Risk scores rank audit attention. They do not represent a percentage probability of fraud."
    )

    # --------------------------------------------------------
    # CHARTS
    # --------------------------------------------------------
    chart1, chart2 = st.columns(2)

    with chart1:
        priority_df = pd.DataFrame({
            "Priority": ["HIGH", "MEDIUM", "LOW", "NO SIGNIFICANT FLAG"],
            "Transactions": [high, medium, low, normal],
        })

        fig = px.pie(
            priority_df,
            names="Priority",
            values="Transactions",
            hole=0.58,
            title="Risk Distribution",
        )
        fig.update_layout(
            margin=dict(l=20, r=20, t=55, b=20),
            height=380,
            legend_title_text="Priority",
        )
        st.plotly_chart(fig, use_container_width=True)

    with chart2:
        flag_summary = flag_summary_from_analysis(analysis)

        if not flag_summary.empty:
            top_flags = flag_summary.sort_values(
                "Transactions Flagged",
                ascending=True,
            ).tail(10)

            fig2 = px.bar(
                top_flags,
                x="Transactions Flagged",
                y="Red Flag",
                orientation="h",
                title="Top Red-Flag Categories",
            )
            fig2.update_layout(
                margin=dict(l=20, r=20, t=55, b=20),
                height=380,
                yaxis_title="",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No red-flag categories to chart.")

    # --------------------------------------------------------
    # TOP RISKS
    # --------------------------------------------------------
    st.markdown("### Top Transactions Requiring Auditor Attention")

    flagged = analysis[
        analysis["Priority"] != "NO SIGNIFICANT FLAG"
    ].copy()

    top_risks = flagged.head(15)

    top_cols = [
        "Risk Score",
        "Priority",
        "AI Anomaly Score",
        "Date",
        "Voucher Number",
        "Party Name",
        "Amount",
        "Voucher Type",
        "Flags",
    ]

    st.dataframe(
        dashboard_display_frame(top_risks[top_cols]),
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # PATTERNS
    # --------------------------------------------------------
    st.markdown("### Patterns Detected")

    if patterns is not None and not patterns.empty:
        for _, p in patterns.head(10).iterrows():
            st.markdown(
                f"""
                <div class="section-card">
                    <b>⚠ {p['Pattern']}</b><br>
                    <span class="small-note">{p['Date / Window']} | {p['Party']}</span><br><br>
                    <b>{p['Amount / Value']}</b><br>
                    {p['Details']}<br>
                    <span class="small-note">Voucher(s): {p['Voucher(s)']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No cross-transaction patterns detected.")

    # --------------------------------------------------------
    # INVESTIGATION SELECTOR
    # --------------------------------------------------------
    st.markdown("---")
    st.markdown("## Transaction Investigation")
    st.caption("Choose a flagged transaction to see why AuditEye selected it and what the auditor may verify.")

    if flagged.empty:
        st.info("No flagged transaction is available for investigation.")
    else:
        options = ["— Select transaction —"] + [
            transaction_label(row)
            for _, row in flagged.iterrows()
        ]

        selected_label = st.selectbox(
            "Select transaction",
            options,
        )

        if selected_label != "— Select transaction —":
            selected_index = options.index(selected_label) - 1
            row = flagged.iloc[selected_index]

            st.session_state.selected_voucher = row["Voucher Number"]

            left, right = st.columns([1, 1.2])

            with left:
                st.markdown(
                    f"""
                    <div class="section-card">
                        <div class="metric-label">INDICATIVE AUDIT RISK SCORE</div>
                        <div class="metric-value">{int(row['Risk Score'])} / 100</div>
                        <b>{risk_badge(row['Priority'])}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                detail_rows = [
                    ["Date", format_date(row["Date"])],
                    ["Voucher", row["Voucher Number"]],
                    ["Voucher Type", row["Voucher Type"]],
                    ["Party", row["Party Name"] or "Not available"],
                    ["Amount", inr(row["Amount"])],
                    ["Debit Account(s)", row["Debit Accounts"]],
                    ["Credit Account(s)", row["Credit Accounts"]],
                    ["Narration", row["Narration"]],
                    ["Created By", row["Created By"] or "Not available"],
                    ["Entry Time", row["Entry Time"] or "Not available"],
                    ["AI Anomaly Score", int(row.get("AI Anomaly Score", 0))],
                ]

                st.dataframe(
                    pd.DataFrame(detail_rows, columns=["Field", "Value"]),
                    use_container_width=True,
                    hide_index=True,
                )

            with right:
                st.markdown("### Why AuditEye Flagged This")

                flags = [
                    x.strip()
                    for x in str(row["Flags"]).split("|")
                    if x.strip()
                ]

                if flags:
                    for flag in flags:
                        st.write(f"✓ **{flag}**")
                else:
                    st.write("No significant Stage 2 flag.")

                if str(row.get("AI Anomaly", "")) == "YES":
                    st.info(
                        f"🧠 **AI observation:** {row.get('AI Reason', '')}  \n"
                        f"Relative anomaly score: **{int(row.get('AI Anomaly Score', 0))}/100**"
                    )

                confirmed_rp = str(row.get("Related Party Match", "") or "")
                fuzzy_rp = str(row.get("AI Related Party Match", "") or "")
                fuzzy_type = str(row.get("RP Match Type", "") or "")
                fuzzy_conf = int(row.get("RP Match Confidence", 0) or 0)

                if confirmed_rp:
                    st.warning(
                        f"**Related Party Match: CONFIRMED**  \n"
                        f"Matched with: {confirmed_rp}"
                    )
                elif fuzzy_type == "Possible fuzzy-name match":
                    st.warning(
                        f"**Possible Related Party Match**  \n"
                        f"Matched with: {fuzzy_rp}  \n"
                        f"Name similarity confidence: {fuzzy_conf}%  \n\n"
                        "Auditor confirmation is required."
                    )

            st.markdown("### Suggested Auditor Procedures")

            actions = suggested_auditor_actions(row)

            for action in actions:
                st.checkbox(
                    action,
                    value=False,
                    key=f"proc_{row['Voucher Number']}_{abs(hash(action))}",
                )

            st.warning(
                "AuditEye identifies risk indicators for auditor review. "
                "A red flag is not evidence or a conclusion of fraud. "
                "Professional judgement and sufficient appropriate audit evidence remain necessary."
            )

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------
    st.markdown("---")
    st.markdown("## Export Audit Findings")

    if st.session_state.final_export_bytes is None:
        st.session_state.final_export_bytes = build_export_workbook_bytes(
            company_name=company_name,
            fy=fy,
            analysis=analysis,
            patterns=patterns,
            monthly_spikes=monthly_spikes,
            std=std,
        )

    safe_company = re.sub(r"[^A-Za-z0-9]+", "_", company_name).strip("_") or "Company"
    export_name = f"AuditEye_Findings_{safe_company}_{fy}.xlsx"

    st.download_button(
        "📥 DOWNLOAD AUDIT FINDINGS EXCEL",
        data=st.session_state.final_export_bytes,
        file_name=export_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )

    st.caption(
        "Export includes Executive Summary, High Priority transactions, All Red Flags, "
        "Related Parties, Duplicate/Split transactions, Fund Flow patterns, Year-End/Manual Journals, "
        "Patterns Detected, Monthly Spikes and Suggested Audit Procedures."
    )

    nav1, nav2 = st.columns([1, 2])

    with nav1:
        if st.button("← BACK TO ANALYSIS", use_container_width=True):
            st.session_state.step = 4
            st.rerun()

    with nav2:
        st.success(
            "AuditEye complete demo is ready: Upload → Validate → Audit Rules → AI → Dashboard → Investigation → Export."
        )

