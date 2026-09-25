# ============================================================
# NSE NEAR-52W-LOW STOCK SCREENER
# NSE ONLY - NO YAHOO FINANCE
#
# Six tests:
# 1. <= 20% above 52W low
# 2. >= 30% below 52W high
# 3. 5D return >= -2%
# 4. 20D return >= -5%
# 5. Volume ratio >= 0.8x previous 20D average
# 6. Price vs 20DMA >= -3%
#
# ONLY 6/6 candidates go to the final candidate sheet.
#
# Data:
# - NSE CM-UDiFF Bhavcopy through nselib
# - Direct NSE UDiFF archive fallback
# - NSE 52 Week High Low Report through nselib
#
# Output:
# Desktop\NSE_Screener_DDMMYYYY.xlsx
# ============================================================

import os
import io
import zipfile
import threading
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

import pandas as pd

# ------------------------------------------------------------
# REQUIRED LIBRARIES
# ------------------------------------------------------------

try:
    from nselib import capital_market
except Exception as e:
    raise SystemExit(
        "nselib is not installed.\n\n"
        "Run this command in Command Prompt:\n"
        "python -m pip install --upgrade nselib pandas openpyxl curl_cffi"
    ) from e

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter


# ============================================================
# SETTINGS
# ============================================================

APP_TITLE = "NSE Near-52W-Low Stock Screener"

# Maximum number of calendar days to search backwards
MAX_LOOKBACK_CALENDAR_DAYS = 45

# Need current session + previous 20 sessions
HISTORY_SESSIONS_NEEDED = 21


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_columns(df):
    """Remove spaces from column names."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_column(df, candidates):
    """
    Find a column using exact names first and fuzzy matching second.
    """

    column_map = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    # Exact match
    for candidate in candidates:
        key = candidate.lower()

        if key in column_map:
            return column_map[key]

    # Fuzzy match
    for col in df.columns:
        col_text = str(col).strip().lower()

        for candidate in candidates:
            if candidate.lower() in col_text:
                return col

    return None


def numeric_column(df, column):
    """Convert NSE numeric column safely to numbers."""

    if column is None:
        return pd.Series(index=df.index, dtype=float)

    return pd.to_numeric(
        df[column]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce"
    )


# ============================================================
# NSE BHAVCOPY NORMALISATION
# ============================================================

def normalize_bhavcopy(raw_df):
    """
    Convert NSE UDiFF bhavcopy into a simple structure:

    SYMBOL
    SERIES
    CLOSE
    VOLUME
    VALUE
    PREV_CLOSE
    TRADE_DATE
    """

    df = clean_columns(raw_df)

    symbol_col = find_column(
        df,
        [
            "TckrSymb",
            "SYMBOL",
            "Symbol"
        ]
    )

    series_col = find_column(
        df,
        [
            "SctySrs",
            "SERIES",
            "Series"
        ]
    )

    close_col = find_column(
        df,
        [
            "ClsPric",
            "CLOSE_PRICE",
            "CLOSE",
            "Close"
        ]
    )

    volume_col = find_column(
        df,
        [
            "TtlTradgVol",
            "TOTTRDQTY",
            "TotTrdQty",
            "VOLUME",
            "Volume"
        ]
    )

    value_col = find_column(
        df,
        [
            "TtlTrfVal",
            "TOTTRDVAL",
            "TotTrdVal",
            "TURNOVER",
            "TURNOVER_LACS"
        ]
    )

    prev_close_col = find_column(
        df,
        [
            "PrvsClsgPric",
            "PREV_CLOSE",
            "PREVCLOSE"
        ]
    )

    date_col = find_column(
        df,
        [
            "TradDt",
            "DATE1",
            "DATE",
            "TIMESTAMP"
        ]
    )

    missing = []

    if symbol_col is None:
        missing.append("SYMBOL")

    if series_col is None:
        missing.append("SERIES")

    if close_col is None:
        missing.append("CLOSE")

    if volume_col is None:
        missing.append("VOLUME")

    if missing:
        raise ValueError(
            "NSE bhavcopy is missing required columns: "
            + str(missing)
            + "\n\nColumns received:\n"
            + str(list(df.columns))
        )

    result = pd.DataFrame()

    result["SYMBOL"] = (
        df[symbol_col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result["SERIES"] = (
        df[series_col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result["CLOSE"] = numeric_column(df, close_col)

    result["VOLUME"] = numeric_column(df, volume_col)

    if value_col:
        result["VALUE"] = numeric_column(df, value_col)
    else:
        result["VALUE"] = float("nan")

    if prev_close_col:
        result["PREV_CLOSE"] = numeric_column(
            df,
            prev_close_col
        )
    else:
        result["PREV_CLOSE"] = float("nan")

    if date_col:
        result["TRADE_DATE"] = pd.to_datetime(
            df[date_col],
            errors="coerce"
        ).dt.date
    else:
        result["TRADE_DATE"] = pd.NaT

    # --------------------------------------------------------
    # ONLY NORMAL EQUITY SERIES
    # --------------------------------------------------------

    result = result[
        result["SERIES"].eq("EQ")
    ].copy()

    result = result[
        result["CLOSE"].notna()
        & (result["CLOSE"] > 0)
    ].copy()

    # One row per symbol
    result = result.drop_duplicates(
        subset=["SYMBOL"],
        keep="last"
    )

    return result.reset_index(drop=True)


# ============================================================
# NSE 52-WEEK REPORT NORMALISATION
# ============================================================

def normalize_52_week_report(raw_df):
    """
    Normalise NSE 52 Week High Low Report.

    NSE publishes adjusted 52W values in this report.
    """

    df = clean_columns(raw_df)

    symbol_col = find_column(
        df,
        [
            "SYMBOL",
            "Symbol",
            "TckrSymb"
        ]
    )

    high_col = find_column(
        df,
        [
            "52_WEEK_HIGH",
            "52 WEEK HIGH",
            "52W HIGH",
            "52_WEEK_HIGH_PRICE",
            "52 Week High",
            "Adjusted 52 Week High",
            "52W High"
        ]
    )

    low_col = find_column(
        df,
        [
            "52_WEEK_LOW",
            "52 WEEK LOW",
            "52W LOW",
            "52_WEEK_LOW_PRICE",
            "52 Week Low",
            "Adjusted 52 Week Low",
            "52W Low"
        ]
    )

    # Additional fuzzy search
    if high_col is None:

        for col in df.columns:

            text = str(col).lower()

            if "52" in text and "high" in text:
                high_col = col
                break

    if low_col is None:

        for col in df.columns:

            text = str(col).lower()

            if "52" in text and "low" in text:
                low_col = col
                break

    if symbol_col is None:
        raise ValueError(
            "Could not identify Symbol column in NSE 52W report.\n\n"
            "Columns received:\n"
            + str(list(df.columns))
        )

    if high_col is None or low_col is None:
        raise ValueError(
            "Could not identify NSE 52W high/low columns.\n\n"
            "Columns received:\n"
            + str(list(df.columns))
        )

    result = pd.DataFrame()

    result["SYMBOL"] = (
        df[symbol_col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result["52W_HIGH"] = numeric_column(
        df,
        high_col
    )

    result["52W_LOW"] = numeric_column(
        df,
        low_col
    )

    result = result[
        (result["52W_HIGH"] > 0)
        & (result["52W_LOW"] > 0)
    ].copy()

    result = result.drop_duplicates(
        subset=["SYMBOL"],
        keep="last"
    )

    return result.reset_index(drop=True)


# ============================================================
# PRIMARY NSE DATA SOURCE
# ============================================================

def get_nselib_bhavcopy(date_obj):

    raw = capital_market.bhav_copy_equities(
        trade_date=date_obj.strftime("%d-%m-%Y")
    )

    if raw is None or len(raw) == 0:

        raise ValueError(
            "nselib returned no CM-UDiFF bhavcopy rows"
        )

    return normalize_bhavcopy(raw)


# ============================================================
# DIRECT NSE UDIFF FALLBACK
# ============================================================

def get_direct_udiff_bhavcopy(date_obj):

    if curl_requests is None:

        raise RuntimeError(
            "curl_cffi is not installed"
        )

    yyyymmdd = date_obj.strftime("%Y%m%d")

    url = (
        "https://nsearchives.nseindia.com/content/cm/"
        f"BhavCopy_NSE_CM_0_0_0_{yyyymmdd}_F_0000.csv.zip"
    )

    session = curl_requests.Session(
        impersonate="chrome"
    )

    headers = {
        "User-Agent":
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/140.0 Safari/537.36",

        "Accept":
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8",

        "Referer":
            "https://www.nseindia.com/all-reports"
    }

    response = session.get(
        url,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:

        raise ValueError(
            f"NSE UDiFF archive HTTP "
            f"{response.status_code}"
        )

    with zipfile.ZipFile(
        io.BytesIO(response.content)
    ) as z:

        csv_files = [
            name
            for name in z.namelist()
            if name.lower().endswith(".csv")
        ]

        if not csv_files:
            raise ValueError(
                "NSE UDiFF ZIP contained no CSV."
            )

        with z.open(csv_files[0]) as f:

            raw = pd.read_csv(
                f,
                low_memory=False
            )

    return normalize_bhavcopy(raw)


# ============================================================
# GET DAILY DATA
# ============================================================

def get_bhavcopy(date_obj, cache, log):

    key = date_obj.isoformat()

    # Already downloaded
    if key in cache:
        return cache[key]

    errors = []

    # --------------------------------------------------------
    # FIRST: nselib
    # --------------------------------------------------------

    try:

        df = get_nselib_bhavcopy(
            date_obj
        )

        if not df.empty:

            cache[key] = df

            log(
                f"  ✓ {date_obj:%d-%m-%Y} "
                f"price data via nselib "
                f"({len(df):,} EQ rows)"
            )

            return df

    except Exception as e:

        errors.append(
            "nselib: " + str(e)
        )

    # --------------------------------------------------------
    # SECOND: DIRECT NSE ARCHIVE
    # --------------------------------------------------------

    try:

        df = get_direct_udiff_bhavcopy(
            date_obj
        )

        if not df.empty:

            cache[key] = df

            log(
                f"  ✓ {date_obj:%d-%m-%Y} "
                f"price data via direct NSE UDiFF "
                f"({len(df):,} EQ rows)"
            )

            return df

    except Exception as e:

        errors.append(
            "direct NSE: " + str(e)
        )

    raise ValueError(
        f"No usable NSE price data for "
        f"{date_obj:%d-%m-%Y}.\n"
        + " | ".join(errors)
    )


# ============================================================
# FIND LATEST TRADING DAY
# ============================================================

def find_latest_trading_day(
    selected_date,
    cache,
    log
):

    current_date = selected_date

    for _ in range(
        MAX_LOOKBACK_CALENDAR_DAYS + 1
    ):

        try:

            df = get_bhavcopy(
                current_date,
                cache,
                log
            )

            if not df.empty:

                return current_date, df

        except Exception:

            log(
                f"  - {current_date:%d-%m-%Y} "
                f"not available"
            )

        current_date -= timedelta(days=1)

    raise RuntimeError(
        "Could not find an NSE trading day "
        "on or before the selected date."
    )


# ============================================================
# GET NSE 52 WEEK REPORT
# ============================================================

def get_52_week_report(
    selected_date,
    log
):

    current_date = selected_date

    last_error = None

    # Search backward for NSE's latest available report.
    for _ in range(31):

        try:

            raw = (
                capital_market
                .week_52_high_low_report(
                    trade_date=current_date.strftime(
                        "%d-%m-%Y"
                    )
                )
            )

            if raw is not None and len(raw) > 0:

                df = normalize_52_week_report(
                    raw
                )

                if not df.empty:

                    log(
                        f"  ✓ NSE 52W report used: "
                        f"{current_date:%d-%m-%Y} "
                        f"({len(df):,} rows)"
                    )

                    return current_date, df

        except Exception as e:

            last_error = e

        current_date -= timedelta(days=1)

    raise RuntimeError(
        "Could not find an NSE 52 Week "
        "High/Low Report on or before the "
        f"selected date.\n\n"
        f"Last error: {last_error}"
    )


# ============================================================
# COMPANY NAME MASTER
# ============================================================

def get_company_names(log):

    try:

        raw = capital_market.equity_list()

        if raw is None or len(raw) == 0:

            return pd.DataFrame(
                columns=[
                    "SYMBOL",
                    "COMPANY_NAME"
                ]
            )

        df = clean_columns(raw)

        symbol_col = find_column(
            df,
            [
                "SYMBOL",
                "Symbol",
                "TckrSymb"
            ]
        )

        name_col = find_column(
            df,
            [
                "NAME OF COMPANY",
                "Company Name",
                "COMPANY_NAME",
                "NAME",
                "FinInstrmNm"
            ]
        )

        if (
            symbol_col is None
            or name_col is None
        ):

            return pd.DataFrame(
                columns=[
                    "SYMBOL",
                    "COMPANY_NAME"
                ]
            )

        result = pd.DataFrame()

        result["SYMBOL"] = (
            df[symbol_col]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        result["COMPANY_NAME"] = (
            df[name_col]
            .astype(str)
            .str.strip()
        )

        result = result.drop_duplicates(
            subset=["SYMBOL"]
        )

        log(
            f"  ✓ Company names loaded: "
            f"{len(result):,}"
        )

        return result

    except Exception as e:

        log(
            "  ! Company name master unavailable: "
            + str(e)
        )

        return pd.DataFrame(
            columns=[
                "SYMBOL",
                "COMPANY_NAME"
            ]
        )


# ============================================================
# BUILD 21-SESSION HISTORY
# ============================================================

def build_history(
    price_date,
    cache,
    log
):

    sessions = []

    current_date = price_date

    attempts = 0

    # Current + 20 previous sessions
    while (
        len(sessions)
        < HISTORY_SESSIONS_NEEDED + 1
        and attempts < 60
    ):

        try:

            df = get_bhavcopy(
                current_date,
                cache,
                log
            )

            if not df.empty:

                sessions.append(
                    (
                        current_date,
                        df
                    )
                )

        except Exception:
            pass

        current_date -= timedelta(days=1)

        attempts += 1

    if (
        len(sessions)
        < HISTORY_SESSIONS_NEEDED + 1
    ):

        raise RuntimeError(
            f"Only found "
            f"{len(sessions) - 1} prior NSE "
            "sessions.\n\n"
            "The screener needs 20 prior "
            "sessions for the six tests."
        )

    sessions.sort(
        key=lambda x: x[0]
    )

    return sessions


# ============================================================
# CALCULATE ALL SIX TESTS
# ============================================================

def calculate_screen(
    latest_df,
    sessions,
    report_52w,
    company_names
):

    # --------------------------------------------------------
    # CURRENT PRICE DATA
    # --------------------------------------------------------

    current = latest_df[
        [
            "SYMBOL",
            "CLOSE",
            "VOLUME",
            "VALUE",
            "PREV_CLOSE"
        ]
    ].copy()

    current.rename(
        columns={
            "CLOSE": "PRICE",
            "VOLUME": "VOLUME_TODAY",
            "VALUE": "VALUE_TODAY"
        },
        inplace=True
    )

    # --------------------------------------------------------
    # HISTORICAL DATA
    # --------------------------------------------------------

    history_parts = []

    for trade_date, df in sessions:

        part = df[
            [
                "SYMBOL",
                "CLOSE",
                "VOLUME"
            ]
        ].copy()

        part["DATE"] = pd.Timestamp(
            trade_date
        )

        history_parts.append(part)

    history = pd.concat(
        history_parts,
        ignore_index=True
    )

    history.sort_values(
        [
            "SYMBOL",
            "DATE"
        ],
        inplace=True
    )

    metrics = []

    # --------------------------------------------------------
    # CALCULATE STOCK-BY-STOCK METRICS
    # --------------------------------------------------------

    for symbol, group in history.groupby(
        "SYMBOL",
        sort=False
    ):

        group = group.sort_values(
            "DATE"
        ).reset_index(drop=True)

        # Need at least 21 sessions
        if len(group) < 21:
            continue

        latest = group.iloc[-1]

        # ----------------------------------------------------
        # 5 DAY RETURN
        # ----------------------------------------------------

        close_5d_ago = group.iloc[-6]["CLOSE"]

        if (
            pd.notna(close_5d_ago)
            and close_5d_ago != 0
        ):

            return_5d = (
                latest["CLOSE"]
                / close_5d_ago
                - 1
            )

        else:

            return_5d = float("nan")

        # ----------------------------------------------------
        # 20 DAY RETURN
        # ----------------------------------------------------

        close_20d_ago = group.iloc[-21]["CLOSE"]

        if (
            pd.notna(close_20d_ago)
            and close_20d_ago != 0
        ):

            return_20d = (
                latest["CLOSE"]
                / close_20d_ago
                - 1
            )

        else:

            return_20d = float("nan")

        # ----------------------------------------------------
        # PREVIOUS 20 DAY AVERAGE VOLUME
        # ----------------------------------------------------

        previous_20_volumes = pd.to_numeric(
            group.iloc[-21:-1]["VOLUME"],
            errors="coerce"
        )

        average_20_volume = (
            previous_20_volumes.mean()
        )

        if (
            pd.notna(average_20_volume)
            and average_20_volume > 0
        ):

            volume_ratio = (
                latest["VOLUME"]
                / average_20_volume
            )

        else:

            volume_ratio = float("nan")

        # ----------------------------------------------------
        # 5DMA
        # ----------------------------------------------------

        closes = pd.to_numeric(
            group["CLOSE"],
            errors="coerce"
        )

        dma_5 = closes.iloc[-5:].mean()

        # ----------------------------------------------------
        # 20DMA
        # ----------------------------------------------------

        dma_20 = closes.iloc[-20:].mean()

        # Previous 20DMA
        dma_20_previous = (
            closes.iloc[-21:-1].mean()
        )

        metrics.append(
            {
                "SYMBOL": symbol,
                "5D_RETURN": return_5d,
                "20D_RETURN": return_20d,
                "AVG20_VOLUME": average_20_volume,
                "VOLUME_RATIO": volume_ratio,
                "5DMA": dma_5,
                "20DMA": dma_20,
                "20DMA_PREVIOUS": dma_20_previous
            }
        )

    metrics_df = pd.DataFrame(
        metrics
    )

    # --------------------------------------------------------
    # MERGE EVERYTHING
    # --------------------------------------------------------

    result = current.merge(
        report_52w,
        on="SYMBOL",
        how="inner"
    )

    result = result.merge(
        metrics_df,
        on="SYMBOL",
        how="inner"
    )

    if not company_names.empty:

        result = result.merge(
            company_names,
            on="SYMBOL",
            how="left"
        )

    else:

        result["COMPANY_NAME"] = (
            result["SYMBOL"]
        )

    result["COMPANY_NAME"] = (
        result["COMPANY_NAME"]
        .fillna(result["SYMBOL"])
    )

    # ========================================================
    # DISTANCE FROM 52W LOW
    # ========================================================

    result["DIST_FROM_52W_LOW_%"] = (
        result["PRICE"]
        / result["52W_LOW"]
        - 1
    ) * 100

    # ========================================================
    # DISTANCE BELOW 52W HIGH
    # ========================================================

    result["BELOW_52W_HIGH_%"] = (
        1
        - result["PRICE"]
        / result["52W_HIGH"]
    ) * 100

    # ========================================================
    # PRICE VS 20DMA
    # ========================================================

    result["PRICE_VS_20DMA_%"] = (
        result["PRICE"]
        / result["20DMA"]
        - 1
    ) * 100

    # ========================================================
    # 20DMA SLOPE
    # ========================================================

    result["20DMA_SLOPE_%"] = (
        result["20DMA"]
        / result["20DMA_PREVIOUS"]
        - 1
    ) * 100

    # ========================================================
    # SIX TESTS
    # ========================================================

    # TEST 1
    result["TEST_1_52W_LOW"] = (
        result["DIST_FROM_52W_LOW_%"]
        <= 20
    )

    # TEST 2
    result["TEST_2_52W_HIGH"] = (
        result["BELOW_52W_HIGH_%"]
        >= 30
    )

    # TEST 3
    result["TEST_3_5D_RETURN"] = (
        result["5D_RETURN"]
        >= -0.02
    )

    # TEST 4
    result["TEST_4_20D_RETURN"] = (
        result["20D_RETURN"]
        >= -0.05
    )

    # TEST 5
    result["TEST_5_VOLUME"] = (
        result["VOLUME_RATIO"]
        >= 0.8
    )

    # TEST 6
    result["TEST_6_20DMA"] = (
        result["PRICE_VS_20DMA_%"]
        >= -3
    )

    tests = [
        "TEST_1_52W_LOW",
        "TEST_2_52W_HIGH",
        "TEST_3_5D_RETURN",
        "TEST_4_20D_RETURN",
        "TEST_5_VOLUME",
        "TEST_6_20DMA"
    ]

    result["PASS_COUNT"] = (
        result[tests]
        .sum(axis=1)
    )

    result["ALL_6_PASS"] = (
        result["PASS_COUNT"]
        == 6
    )

    # ========================================================
    # FALLING KNIFE / TREND REVERSAL
    # ONLY FOR 6/6 STOCKS
    # ========================================================

    result["TREND_CLASSIFICATION"] = (
        "Not Applicable"
    )

    six_pass = result["ALL_6_PASS"]

    # Falling Knife Risk
    falling_knife = (
        six_pass
        &
        (result["20D_RETURN"] < -0.05)
        &
        (result["5DMA"] < result["20DMA"])
        &
        (result["20DMA_SLOPE_%"] < 0)
    )

    # Stabilising
    stabilising = (
        six_pass
        &
        (result["5D_RETURN"] >= -0.02)
        &
        (result["PRICE"] >= result["20DMA"])
        &
        (result["5DMA"] >= result["20DMA"])
    )

    result.loc[
        falling_knife,
        "TREND_CLASSIFICATION"
    ] = "Falling Knife Risk"

    result.loc[
        stabilising,
        "TREND_CLASSIFICATION"
    ] = "Stabilising"

    result.loc[
        six_pass
        & ~falling_knife
        & ~stabilising,
        "TREND_CLASSIFICATION"
    ] = "Watch / Mixed Signals"

    # ========================================================
    # FINAL COLUMN ORDER
    # ========================================================

    final_columns = [

        "SYMBOL",
        "COMPANY_NAME",
        "PRICE",

        "52W_LOW",
        "52W_HIGH",

        "DIST_FROM_52W_LOW_%",
        "BELOW_52W_HIGH_%",

        "5D_RETURN",
        "20D_RETURN",

        "VOLUME_TODAY",
        "AVG20_VOLUME",
        "VOLUME_RATIO",

        "5DMA",
        "20DMA",

        "PRICE_VS_20DMA_%",
        "20DMA_SLOPE_%",

        "PASS_COUNT",
        "ALL_6_PASS",

        "TREND_CLASSIFICATION",

        "TEST_1_52W_LOW",
        "TEST_2_52W_HIGH",
        "TEST_3_5D_RETURN",
        "TEST_4_20D_RETURN",
        "TEST_5_VOLUME",
        "TEST_6_20DMA"
    ]

    result = result[
        [
            c
            for c in final_columns
            if c in result.columns
        ]
    ]

    result.sort_values(
        [
            "ALL_6_PASS",
            "PASS_COUNT",
            "DIST_FROM_52W_LOW_%"
        ],
        ascending=[
            False,
            False,
            True
        ],
        inplace=True
    )

    return result.reset_index(
        drop=True
    )


# ============================================================
# CREATE EXCEL REPORT
# ============================================================

def create_excel_report(
    df,
    selected_date,
    price_date,
    report_date,
    output_file,
    log
):

    workbook = Workbook()

    # --------------------------------------------------------
    # COLORS
    # --------------------------------------------------------

    title_fill = PatternFill(
        "solid",
        fgColor="1F4E78"
    )

    section_fill = PatternFill(
        "solid",
        fgColor="D9EAF7"
    )

    pass_fill = PatternFill(
        "solid",
        fgColor="E2F0D9"
    )

    fail_fill = PatternFill(
        "solid",
        fgColor="FCE4D6"
    )

    warning_fill = PatternFill(
        "solid",
        fgColor="FFF2CC"
    )

    white_font = Font(
        color="FFFFFF",
        bold=True
    )

    thin_side = Side(
        style="thin",
        color="D9E1F2"
    )

    border = Border(
        left=thin_side,
        right=thin_side,
        top=thin_side,
        bottom=thin_side
    )

    # ========================================================
    # DASHBOARD
    # ========================================================

    dashboard = workbook.active

    dashboard.title = "Dashboard"

    dashboard.sheet_view.showGridLines = False

    dashboard["A1"] = APP_TITLE

    dashboard["A1"].font = Font(
        size=18,
        bold=True,
        color="FFFFFF"
    )

    dashboard["A1"].fill = title_fill

    dashboard.merge_cells(
        "A1:H1"
    )

    dashboard["A3"] = "Selected Date"
    dashboard["B3"] = selected_date.strftime(
        "%d-%m-%Y"
    )

    dashboard["A4"] = (
        "Price / Volume Date Used"
    )

    dashboard["B4"] = price_date.strftime(
        "%d-%m-%Y"
    )

    dashboard["A5"] = (
        "NSE 52W Report Date Used"
    )

    dashboard["B5"] = report_date.strftime(
        "%d-%m-%Y"
    )

    dashboard["A6"] = (
        "Companies Analysed"
    )

    dashboard["B6"] = int(
        len(df)
    )

    dashboard["A7"] = (
        "6/6 Candidates"
    )

    dashboard["B7"] = int(
        df["ALL_6_PASS"].sum()
    )

    for cell in [
        "A3",
        "A4",
        "A5",
        "A6",
        "A7"
    ]:

        dashboard[cell].font = Font(
            bold=True
        )

        dashboard[cell].fill = section_fill

        dashboard[cell].border = border

    for cell in [
        "B3",
        "B4",
        "B5",
        "B6",
        "B7"
    ]:

        dashboard[cell].border = border

    # ========================================================
    # SIX TEST FUNNEL
    # ========================================================

    dashboard["A10"] = (
        "Six-Test Screening Funnel"
    )

    dashboard["A10"].font = Font(
        size=13,
        bold=True
    )

    headers = [
        "Test",
        "Rule",
        "Pass",
        "Fail"
    ]

    for col, header in enumerate(
        headers,
        1
    ):

        cell = dashboard.cell(
            11,
            col,
            header
        )

        cell.font = white_font
        cell.fill = title_fill
        cell.border = border

    funnel = [

        (
            "1. 52W Low",
            "≤ 20% above 52W low",
            df["DIST_FROM_52W_LOW_%"] <= 20
        ),

        (
            "2. 52W High",
            "≥ 30% below 52W high",
            df["BELOW_52W_HIGH_%"] >= 30
        ),

        (
            "3. 5D Return",
            "≥ -2%",
            df["5D_RETURN"] >= -0.02
        ),

        (
            "4. 20D Return",
            "≥ -5%",
            df["20D_RETURN"] >= -0.05
        ),

        (
            "5. Volume Ratio",
            "≥ 0.8× previous 20D average",
            df["VOLUME_RATIO"] >= 0.8
        ),

        (
            "6. Price vs 20DMA",
            "≥ -3%",
            df["PRICE_VS_20DMA_%"] >= -3
        )
    ]

    row = 12

    for name, rule, mask in funnel:

        values = [
            name,
            rule,
            int(mask.sum()),
            int((~mask).sum())
        ]

        for col, value in enumerate(
            values,
            1
        ):

            cell = dashboard.cell(
                row,
                col,
                value
            )

            cell.border = border

        row += 1

    # ========================================================
    # TREND REVERSAL SUMMARY
    # ========================================================

    dashboard["F10"] = (
        "6/6 Trend-Reversal Analysis"
    )

    dashboard["F10"].font = Font(
        size=13,
        bold=True
    )

    trend_headers = [
        "Classification",
        "Companies"
    ]

    for col, header in enumerate(
        trend_headers,
        6
    ):

        cell = dashboard.cell(
            11,
            col,
            header
        )

        cell.font = white_font
        cell.fill = title_fill
        cell.border = border

    candidates = df[
        df["ALL_6_PASS"]
    ]

    trend_counts = (
        candidates[
            "TREND_CLASSIFICATION"
        ]
        .value_counts()
    )

    trend_categories = [
        "Stabilising",
        "Watch / Mixed Signals",
        "Falling Knife Risk"
    ]

    row = 12

    for category in trend_categories:

        dashboard.cell(
            row,
            6,
            category
        ).border = border

        dashboard.cell(
            row,
            7,
            int(
                trend_counts.get(
                    category,
                    0
                )
            )
        ).border = border

        row += 1

    # ========================================================
    # FINAL 6/6 CANDIDATES
    # ========================================================

    candidate_sheet = workbook.create_sheet(
        "6_6_Candidates"
    )

    candidate_sheet.sheet_view.showGridLines = False

    candidate_columns = [

        "SYMBOL",
        "COMPANY_NAME",
        "PRICE",

        "52W_LOW",
        "52W_HIGH",

        "DIST_FROM_52W_LOW_%",
        "BELOW_52W_HIGH_%",

        "5D_RETURN",
        "20D_RETURN",

        "VOLUME_RATIO",

        "20DMA",
        "PRICE_VS_20DMA_%",

        "20DMA_SLOPE_%",

        "TREND_CLASSIFICATION"
    ]

    for col, header in enumerate(
        candidate_columns,
        1
    ):

        cell = candidate_sheet.cell(
            1,
            col,
            header
        )

        cell.font = white_font
        cell.fill = title_fill
        cell.border = border

        cell.alignment = Alignment(
            horizontal="center"
        )

    for row_number, (_, row_data) in enumerate(
        candidates.iterrows(),
        2
    ):

        for col, header in enumerate(
            candidate_columns,
            1
        ):

            value = row_data.get(
                header,
                ""
            )

            cell = candidate_sheet.cell(
                row_number,
                col,
                value
            )

            cell.border = border

            # Percentage formatting
            if header in [
                "5D_RETURN",
                "20D_RETURN"
            ]:

                cell.number_format = "0.00%"

            elif header in [
                "DIST_FROM_52W_LOW_%",
                "BELOW_52W_HIGH_%",
                "PRICE_VS_20DMA_%",
                "20DMA_SLOPE_%"
            ]:

                cell.number_format = "0.00"

            elif header == "VOLUME_RATIO":

                cell.number_format = "0.00x"

            elif header in [
                "PRICE",
                "52W_LOW",
                "52W_HIGH",
                "20DMA"
            ]:

                cell.number_format = "0.00"

        # Colour the classification
        classification = row_data[
            "TREND_CLASSIFICATION"
        ]

        if classification == "Stabilising":

            for col in range(
                1,
                len(candidate_columns) + 1
            ):

                candidate_sheet.cell(
                    row_number,
                    col
                ).fill = pass_fill

        elif classification == "Falling Knife Risk":

            for col in range(
                1,
                len(candidate_columns) + 1
            ):

                candidate_sheet.cell(
                    row_number,
                    col
                ).fill = fail_fill

        else:

            for col in range(
                1,
                len(candidate_columns) + 1
            ):

                candidate_sheet.cell(
                    row_number,
                    col
                ).fill = warning_fill

    candidate_sheet.freeze_panes = "A2"

    if candidate_sheet.max_row >= 2:

        candidate_sheet.auto_filter.ref = (
            candidate_sheet.dimensions
        )

    # ========================================================
    # DATA AUDIT
    # ========================================================

    audit_sheet = workbook.create_sheet(
        "Data_Audit"
    )

    audit_sheet.sheet_view.showGridLines = False

    audit_rows = [

        (
            "Selected Date",
            selected_date.strftime(
                "%d-%m-%Y"
            )
        ),

        (
            "Price / Volume Date Used",
            price_date.strftime(
                "%d-%m-%Y"
            )
        ),

        (
            "NSE 52W Report Date Used",
            report_date.strftime(
                "%d-%m-%Y"
            )
        ),

        (
            "Daily Price Source",
            "NSE CM-UDiFF Bhavcopy via "
            "nselib bhav_copy_equities(), "
            "with direct NSE UDiFF fallback"
        ),

        (
            "52W Source",
            "NSE 52 Week High Low Report "
            "via nselib"
        ),

        (
            "Test 1",
            "Price is ≤20% above NSE 52W low"
        ),

        (
            "Test 2",
            "Price is ≥30% below NSE 52W high"
        ),

        (
            "Test 3",
            "5D return ≥ -2%"
        ),

        (
            "Test 4",
            "20D return ≥ -5%"
        ),

        (
            "Test 5",
            "Today's volume / previous "
            "20-session average ≥ 0.8x"
        ),

        (
            "Test 6",
            "Price vs 20DMA ≥ -3%"
        ),

        (
            "Next Stage",
            "Only 6/6 candidates undergo "
            "Falling Knife / Trend-Reversal Analysis"
        )
    ]

    for row_number, (label, value) in enumerate(
        audit_rows,
        1
    ):

        audit_sheet.cell(
            row_number,
            1,
            label
        )

        audit_sheet.cell(
            row_number,
            1
        ).font = Font(
            bold=True
        )

        audit_sheet.cell(
            row_number,
            1
        ).fill = section_fill

        audit_sheet.cell(
            row_number,
            2,
            value
        )

        audit_sheet.cell(
            row_number,
            1
        ).border = border

        audit_sheet.cell(
            row_number,
            2
        ).border = border

    # ========================================================
    # AUTO COLUMN WIDTHS
    # ========================================================

    for sheet in workbook.worksheets:

        for column_number in range(
            1,
            sheet.max_column + 1
        ):

            maximum_length = 0

            for row_number in range(
                1,
                min(
                    sheet.max_row,
                    100
                ) + 1
            ):

                value = sheet.cell(
                    row_number,
                    column_number
                ).value

                if value is not None:

                    maximum_length = max(
                        maximum_length,
                        len(str(value))
                    )

            width = min(
                max(
                    maximum_length + 2,
                    10
                ),
                45
            )

            sheet.column_dimensions[
                get_column_letter(
                    column_number
                )
            ].width = width

    # ========================================================
    # SAVE
    # ========================================================

    workbook.save(
        output_file
    )

    log(
        f"Excel report saved:\n{output_file}"
    )


# ============================================================
# GUI
# ============================================================

class NSEScreenApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            APP_TITLE
        )

        self.root.geometry(
            "850x650"
        )

        self.root.minsize(
            760,
            560
        )

        self.running = False

        # ----------------------------------------------------
        # MAIN FRAME
        # ----------------------------------------------------

        main = ttk.Frame(
            root,
            padding=18
        )

        main.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title = ttk.Label(
            main,
            text=APP_TITLE,
            font=(
                "Segoe UI",
                18,
                "bold"
            )
        )

        title.pack(
            anchor="w"
        )

        subtitle = ttk.Label(
            main,
            text=(
                "NSE-only • Six transparent tests • "
                "6/6 candidates • No Yahoo Finance • "
                "No pie chart"
            ),
            font=(
                "Segoe UI",
                10
            )
        )

        subtitle.pack(
            anchor="w",
            pady=(2, 15)
        )

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        date_frame = ttk.Frame(
            main
        )

        date_frame.pack(
            fill="x"
        )

        ttk.Label(
            date_frame,
            text="Selected date (DD-MM-YYYY):",
            font=(
                "Segoe UI",
                10,
                "bold"
            )
        ).pack(
            side="left"
        )

        self.date_var = tk.StringVar(
            value=datetime.now().strftime(
                "%d-%m-%Y"
            )
        )

        ttk.Entry(
            date_frame,
            textvariable=self.date_var,
            width=16
        ).pack(
            side="left",
            padx=10
        )

        self.run_button = ttk.Button(
            date_frame,
            text="Run Screener",
            command=self.start_screening
        )

        self.run_button.pack(
            side="left"
        )

        # ----------------------------------------------------
        # RULES
        # ----------------------------------------------------

        rules_frame = ttk.LabelFrame(
            main,
            text="Six Screening Tests",
            padding=10
        )

        rules_frame.pack(
            fill="x",
            pady=15
        )

        rules_text = (
            "1. ≤20% above 52W low\n"
            "2. ≥30% below 52W high\n"
            "3. 5D return ≥ -2%\n"
            "4. 20D return ≥ -5%\n"
            "5. Volume ratio ≥ 0.8× previous 20D average\n"
            "6. Price vs 20DMA ≥ -3%\n\n"
            "ONLY stocks passing all 6 tests proceed "
            "to Falling Knife / Trend-Reversal Analysis."
        )

        ttk.Label(
            rules_frame,
            text=rules_text,
            justify="left"
        ).pack(
            anchor="w"
        )

        # ----------------------------------------------------
        # LOG
        # ----------------------------------------------------

        log_frame = ttk.LabelFrame(
            main,
            text="Run Log",
            padding=8
        )

        log_frame.pack(
            fill="both",
            expand=True
        )

        self.log_text = tk.Text(
            log_frame,
            height=20,
            wrap="word",
            font=(
                "Consolas",
                9
            )
        )

        self.log_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            log_frame,
            command=self.log_text.yview
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.log_text.configure(
            yscrollcommand=scrollbar.set
        )

        self.log(
            "Ready."
        )

        self.log(
            "Enter a date and click Run Screener."
        )

    # ========================================================
    # LOG
    # ========================================================

    def log(self, message):

        self.log_text.insert(
            "end",
            message + "\n"
        )

        self.log_text.see(
            "end"
        )

        self.root.update_idletasks()

    # ========================================================
    # START
    # ========================================================

    def start_screening(self):

        if self.running:
            return

        try:

            selected_date = datetime.strptime(
                self.date_var.get().strip(),
                "%d-%m-%Y"
            ).date()

        except ValueError:

            messagebox.showerror(
                "Invalid Date",
                "Please enter the date as:\n\n"
                "DD-MM-YYYY\n\n"
                "Example:\n"
                "11-09-2026"
            )

            return

        self.running = True

        self.run_button.configure(
            state="disabled"
        )

        self.log_text.delete(
            "1.0",
            "end"
        )

        thread = threading.Thread(
            target=self.worker,
            args=(selected_date,),
            daemon=True
        )

        thread.start()

    # ========================================================
    # MAIN WORKER
    # ========================================================

    def worker(
        self,
        selected_date
    ):

        try:

            self.log(
                "=========================================="
            )

            self.log(
                "NSE SCREENING STARTED"
            )

            self.log(
                "=========================================="
            )

            self.log(
                f"Selected date: "
                f"{selected_date:%d-%m-%Y}"
            )

            self.log(
                ""
            )

            self.log(
                "Step 1: Finding latest NSE trading day..."
            )

            cache = {}

            price_date, latest_df = (
                find_latest_trading_day(
                    selected_date,
                    cache,
                    self.log
                )
            )

            self.log(
                ""
            )

            self.log(
                f"Price / volume date used: "
                f"{price_date:%d-%m-%Y}"
            )

            self.log(
                ""
            )

            # ------------------------------------------------
            # 52W REPORT
            # ------------------------------------------------

            self.log(
                "Step 2: Finding NSE 52W report..."
            )

            report_date, report_52w = (
                get_52_week_report(
                    selected_date,
                    self.log
                )
            )

            self.log(
                ""
            )

            # ------------------------------------------------
            # COMPANY NAMES
            # ------------------------------------------------

            self.log(
                "Step 3: Loading company names..."
            )

            company_names = (
                get_company_names(
                    self.log
                )
            )

            self.log(
                ""
            )

            # ------------------------------------------------
            # HISTORY
            # ------------------------------------------------

            self.log(
                "Step 4: Loading historical "
                "NSE sessions..."
            )

            sessions = build_history(
                price_date,
                cache,
                self.log
            )

            # Make absolutely sure latest session
            # is the actual price date.
            sessions = [
                (d, df)
                for d, df in sessions
                if d <= price_date
            ]

            sessions.sort(
                key=lambda x: x[0]
            )

            if (
                len(sessions) == 0
                or sessions[-1][0] != price_date
            ):

                sessions.append(
                    (
                        price_date,
                        latest_df
                    )
                )

                sessions.sort(
                    key=lambda x: x[0]
                )

            sessions = sessions[-22:]

            self.log(
                ""
            )

            self.log(
                f"Historical sessions available: "
                f"{len(sessions)}"
            )

            self.log(
                ""
            )

            # ------------------------------------------------
            # SCREEN
            # ------------------------------------------------

            self.log(
                "Step 5: Running six-test screen..."
            )

            result = calculate_screen(
                latest_df,
                sessions,
                report_52w,
                company_names
            )

            candidates = result[
                result["ALL_6_PASS"]
            ].copy()

            self.log(
                ""
            )

            self.log(
                "=========================================="
            )

            self.log(
                "SCREENING RESULTS"
            )

            self.log(
                "=========================================="
            )

            self.log(
                f"Companies analysed: "
                f"{len(result):,}"
            )

            self.log(
                f"6/6 candidates: "
                f"{len(candidates):,}"
            )

            stabilising_count = (
                candidates[
                    "TREND_CLASSIFICATION"
                ]
                .eq("Stabilising")
                .sum()
            )

            mixed_count = (
                candidates[
                    "TREND_CLASSIFICATION"
                ]
                .eq(
                    "Watch / Mixed Signals"
                )
                .sum()
            )

            falling_count = (
                candidates[
                    "TREND_CLASSIFICATION"
                ]
                .eq(
                    "Falling Knife Risk"
                )
                .sum()
            )

            self.log(
                f"Stabilising: "
                f"{stabilising_count:,}"
            )

            self.log(
                f"Watch / Mixed Signals: "
                f"{mixed_count:,}"
            )

            self.log(
                f"Falling Knife Risk: "
                f"{falling_count:,}"
            )

            self.log(
                ""
            )

            # ------------------------------------------------
            # OUTPUT FILE
            # ------------------------------------------------

            desktop = (
                Path.home()
                / "Desktop"
            )

            try:

                desktop.mkdir(
                    parents=True,
                    exist_ok=True
                )

            except Exception:

                desktop = Path.cwd()

            output_file = (
                desktop
                / (
                    "NSE_Screener_"
                    + selected_date.strftime(
                        "%Y%m%d"
                    )
                    + ".xlsx"
                )
            )

            # ------------------------------------------------
            # EXCEL
            # ------------------------------------------------

            self.log(
                "Step 6: Creating Excel report..."
            )

            create_excel_report(
                result,
                selected_date,
                price_date,
                report_date,
                output_file,
                self.log
            )

            self.log(
                ""
            )

            self.log(
                "=========================================="
            )

            self.log(
                "DONE"
            )

            self.log(
                "=========================================="
            )

            self.log(
                f"Excel file:\n{output_file}"
            )

            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Screening Completed",
                    (
                        "NSE screening completed.\n\n"
                        f"Companies analysed: "
                        f"{len(result):,}\n\n"
                        f"6/6 candidates: "
                        f"{len(candidates):,}\n\n"
                        "Excel saved to:\n"
                        f"{output_file}"
                    )
                )
            )

        except Exception as error:

            self.log(
                ""
            )

            self.log(
                "=========================================="
            )

            self.log(
                "ERROR"
            )

            self.log(
                "=========================================="
            )

            self.log(
                str(error)
            )

            self.log(
                ""
            )

            self.log(
                traceback.format_exc()
            )

            error_text = str(error)

            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "NSE Screener Error",
                    error_text
                )
            )

        finally:

            self.running = False

            self.root.after(
                0,
                lambda: self.run_button.configure(
                    state="normal"
                )
            )


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    try:

        style = ttk.Style()

        style.theme_use(
            "clam"
        )

    except Exception:
        pass

    app = NSEScreenApp(
        root
    )

    root.mainloop()
