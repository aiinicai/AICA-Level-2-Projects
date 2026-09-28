"""
Broker contract-note parsers -> normalized trade dict.

Consolidated for the AutoContract2Tally offline app from the AICA capstone
project's earlier work (see project progress log). Only the Zerodha path
has been validated against a real (redacted) contract-note structure via
pdfplumber table extraction. Angel One and Upstox parsers below use a
plain-text stand-in format and MUST be re-validated against real sample
notes from those brokers before being trusted for live filings.

Normalized trade dict shape (per contract note):
{
    "broker": "zerodha" | "angelone" | "upstox",
    "contract_note_no": str,
    "account_code": str,          # client's account/UCC code with the broker
    "trade_date": "YYYY-MM-DD",
    "trades": [
        {
            "segment": "equity_intraday" | "equity_delivery" | "futures" | "options",
            "symbol": str,
            "buy_sell": "B" | "S",
            "quantity": float,
            "price": float,
            "value": float,        # quantity * price, pure trade value
        },
        ...
    ],
    "charges": {
        "brokerage": float,
        "stt": float,
        "stamp_duty": float,
        "exchange_txn_charges": float,
        "sebi_charges": float,
        "gst": float,
        "net_total": float,        # grand total including all charges
    },
}
"""
from __future__ import annotations
import re
from datetime import datetime

BROKER_EMAIL_MARKERS = {
    "zerodha": ["contractnotes@zerodha.com", "zerodha.com"],
    "angelone": ["angelone.in", "angel-one.in"],
    "upstox": ["upstox.com"],
}

BROKER_LETTERHEAD_MARKERS = {
    "zerodha": ["ZERODHA BROKING", "zerodha.com"],
    "angelone": ["ANGEL ONE LIMITED", "angelone.in"],
    "upstox": ["UPSTOX SECURITIES", "RKSV Securities"],
}


def detect_broker(sender_email: str) -> str:
    """Stage-A (Gmail) broker detection, from the message's From header."""
    sender_email = (sender_email or "").lower()
    for broker, markers in BROKER_EMAIL_MARKERS.items():
        if any(m in sender_email for m in markers):
            return broker
    raise ValueError(f"Could not identify broker from sender address: {sender_email}")


def detect_broker_from_text(text: str) -> str:
    """Stage-B (folder scan) broker detection, from the note's own letterhead."""
    for broker, markers in BROKER_LETTERHEAD_MARKERS.items():
        if any(m in text for m in markers):
            return broker
    raise ValueError("Could not identify broker from document letterhead")


def _num(s: str) -> float:
    return float(s.replace(",", "").replace("₹", "").strip())


def _charge_value(text: str, *label_patterns: str) -> float:
    """Zerodha's real 'Charges Summary' table prints three columns per
    charge row -- NCL-Cash, NCL-F&O, NET TOTAL -- e.g.:
        Securities transaction tax (n) (110.92) 0.00 (110.92)
    so the LAST number on the matching line is the combined total to book
    (the figure in parentheses is a negative/deduction convention -- the
    parens themselves are simply not part of the digit pattern, so this
    naturally returns the positive magnitude). Tries each label pattern in
    turn (most specific/real-format first) and is case-insensitive, since
    real notes use sentence case ("Securities transaction tax") rather
    than the title case an earlier, unvalidated version of this parser
    assumed."""
    for pattern in label_patterns:
        m = re.search(rf"^.*(?:{pattern}).*$", text, re.IGNORECASE | re.MULTILINE)
        if not m:
            continue
        nums = re.findall(r"[\d,]+\.\d+", m.group(0))
        if nums:
            return _num(nums[-1])
    return 0.0


# --------------------------------------------------------------------------
# Zerodha: parsed from pdfplumber's flat page text (not table extraction --
# a real contract note has three layouts to reckon with: an Equity/
# Derivatives summary section (prices there are WAP *after* brokerage is
# folded in -- unsuitable for trade value, since brokerage is booked
# separately below and would be double-counted), a Charges Summary table
# (3 columns: NCL-Cash / NCL-F&O / NET TOTAL), and a per-trade "Annexure A"
# table (Order No/Time, Trade No/Time, Contract Description, B/S, Exchange,
# Quantity, Brokerage, Net Rate per Unit, Net Total) where the Net Rate is
# the pure trade value with no brokerage folded in -- that's the one this
# parser reads trades from.
# --------------------------------------------------------------------------

FNO_CODE_RE = re.compile(
    r"^(?P<symbol>[A-Z]+)"
    r"(?P<expiry>\d{2}[A-Z]{3}\d{2}|\d{2}[A-Z]{3}|\d{2}[1-9OND]\d{2})"
    r"(?:(?P<strike>\d+)(?P<opttype>CE|PE)|(?P<fut>FUT))$"
)
# The third expiry alternative (\d{2}[1-9OND]\d{2}) is Zerodha's REAL
# trading-symbol format for weekly index F&O contracts -- YY + a single
# month code (1-9 for Jan-Sep, O/N/D for Oct/Nov/Dec) + DD, all numeric
# except that one letter, e.g. "NIFTY2680424200PE" = year 26, month 8,
# day 04, strike 24200, PE. This has NO letters at all in the date portion,
# unlike the monthly "24SEP24200PE" format the first two alternatives
# cover -- without it, every weekly F&O symbol fails to match here at all
# and silently falls through to being treated as an equity delivery trade
# (confirmed against a real contract note that was 100% NIFTY/SENSEX
# weekly options: every single leg was misclassified as equity_delivery,
# which would have posted phantom "stock items" for option contracts).

# Annexure A row. desc is matched non-greedily up to the last standalone
# "B"/"S" token on the line, so it safely swallows a derivatives contract's
# spelled-out expiry ("NIFTY26SEPFUT / 24 September 2026") without the "S"
# in "September" being mistaken for the Sell flag -- a bare "B"/"S" token
# can only land on an actual whitespace boundary, and the only such token
# on a real row is the genuine Buy/Sell flag. The "Closing Rate per Unit"
# column is optional -- it's only populated for a leg still open (not
# squared off) at day end, so most rows have just 4 numbers (qty,
# brokerage, net rate, net total) but an open position has 5. "total" (and,
# less commonly, a still-open leg's own figures) can be printed in
# parentheses rather than with a leading "-" -- real notes use standard
# accounting negative-in-parens notation for a Buy leg's net total, e.g.
# "(5694.50)" -- so total must accept parens too; without this, EVERY Buy
# leg failed to match this regex at all (only Sell legs, which print a
# plain positive number, ever matched), silently dropping every buy-side
# trade from parsing entirely.
ANNEXURE_ROW_RE = re.compile(
    r"^\s*\d+\s+[\d:]+\s+\d+\s+[\d:]+\s+"
    r"(?P<desc>.+?)\s+(?P<bs>B|S)\s+[A-Z]+\s+"
    r"(?P<qty>[\d,]+(?:\.\d+)?)\s+(?P<brokerage>[\d,]+\.\d+)\s+"
    r"(?P<price>[\d,]+\.\d+)\s+(?:(?P<closing>[\d,]+\.\d+)\s+)?"
    r"(?P<total>\(?-?[\d,]+\.\d+\)?)\s*$",
    re.MULTILINE,
)


def _classify_equity_trades(equity_rows: list[dict]) -> None:
    """Real Zerodha Annexure/summary rows for this note carry no MIS/CNC
    product flag per trade, so intraday vs delivery is decided the way an
    accountant would read it off the note: a symbol whose buy and sell
    quantities net to zero within this contract note was squared off
    same-day and never actually went into/out of stock -- that's
    speculative business income. A symbol left with a net open quantity
    was a genuine delivery-based transaction (stock-in-trade). Mutates
    each row's "segment" in place."""
    by_symbol: dict[str, list[dict]] = {}
    for row in equity_rows:
        by_symbol.setdefault(row["symbol"], []).append(row)
    for rows in by_symbol.values():
        net_qty = sum(r["quantity"] if r["buy_sell"] == "B" else -r["quantity"] for r in rows)
        segment = "equity_intraday" if abs(net_qty) < 1e-6 else "equity_delivery"
        for r in rows:
            r["segment"] = segment


def parse_zerodha_pdf(text: str) -> dict:
    """Parse a Zerodha 'Contract Note cum Tax Invoice' whose text has
    already been extracted via pdfplumber."""
    contract_note_no = _first_match(r"Contract Note No\.?\s*[:\-]?\s*([A-Za-z0-9\-/]+)", text)
    # Real notes print "UCC" (Unique Client Code); some formats/older
    # samples used "Client ID" -- accept either.
    account_code = _first_match(r"(?:UCC|Client ID)\s*[:\-]?\s*([A-Za-z0-9]+)", text)
    trade_date_raw = _first_match(r"Trade Date\s*[:\-]?\s*(\d{2}[-/]\d{2}[-/]\d{4})", text)
    trade_date = _to_iso_date(trade_date_raw) if trade_date_raw else datetime.now().strftime("%Y-%m-%d")

    trades: list[dict] = []
    equity_rows: list[dict] = []
    for m in ANNEXURE_ROW_RE.finditer(text):
        desc = m.group("desc").strip()
        symbol = desc.split("/")[0].strip().upper().replace(" ", "")
        qty = _num(m.group("qty"))
        price = _num(m.group("price"))
        row = {
            "symbol": symbol,
            "buy_sell": m.group("bs"),
            "quantity": qty,
            "price": price,
            "value": round(qty * price, 2),
        }
        fno = FNO_CODE_RE.match(symbol)
        if fno and fno.group("opttype"):
            row["segment"] = "options"
            trades.append(row)
        elif fno and fno.group("fut"):
            row["segment"] = "futures"
            trades.append(row)
        else:
            equity_rows.append(row)
    _classify_equity_trades(equity_rows)
    trades.extend(equity_rows)

    charges = {
        "brokerage": _charge_value(text, r"Taxable value of Supply\s*\(Brokerage\)", r"\bBrokerage\b"),
        "stt": _charge_value(text, r"Securities transaction tax"),
        "stamp_duty": _charge_value(text, r"Stamp duty"),
        "exchange_txn_charges": _charge_value(text, r"Exchange transaction charges"),
        "sebi_charges": _charge_value(text, r"SEBI turnover fees", r"SEBI charges"),
        "gst": round(
            _charge_value(text, r"\bCGST\b") + _charge_value(text, r"\bSGST\b") + _charge_value(text, r"\bIGST\b"),
            2,
        ) or _charge_value(text, r"Goods and Services Tax"),
        "net_total": _charge_value(text, r"Net amount receivable", r"\bNet Total\b"),
    }

    return {
        "broker": "zerodha",
        "contract_note_no": contract_note_no or "UNKNOWN",
        "account_code": account_code or "UNKNOWN",
        "trade_date": trade_date,
        "trades": trades,
        "charges": charges,
    }


# --------------------------------------------------------------------------
# Angel One / Upstox: plain-text stand-in format (NOT yet validated
# against a real note -- flagged in the capstone progress log).
# --------------------------------------------------------------------------

def _generic_text_parser(broker: str, text: str) -> dict:
    contract_note_no = _first_match(r"Contract Note No\.?\s*[:\-]?\s*([A-Za-z0-9\-/]+)", text) or "UNKNOWN"
    account_code = _first_match(r"(?:Client ID|UCC)\s*[:\-]?\s*([A-Za-z0-9]+)", text) or "UNKNOWN"
    trade_date_raw = _first_match(r"Trade Date\s*[:\-]?\s*(\d{2}[-/]\d{2}[-/]\d{4})", text)
    trade_date = _to_iso_date(trade_date_raw) if trade_date_raw else datetime.now().strftime("%Y-%m-%d")

    trades = []
    row_re = re.compile(
        r"^\s*(?P<symbol>[A-Z0-9&\-]+)\s+(?P<segment>EQ-INTRADAY|EQ-DELIVERY|FUT|OPT)\s+"
        r"(?P<bs>BUY|SELL|B|S)\s+(?P<qty>[\d,]+(?:\.\d+)?)\s+(?P<price>[\d,]+\.\d+)\s*$",
        re.MULTILINE,
    )
    seg_map = {"EQ-INTRADAY": "equity_intraday", "EQ-DELIVERY": "equity_delivery", "FUT": "futures", "OPT": "options"}
    for m in row_re.finditer(text):
        bs = "B" if m.group("bs").upper().startswith("B") else "S"
        qty = _num(m.group("qty"))
        price = _num(m.group("price"))
        trades.append({
            "segment": seg_map[m.group("segment")],
            "symbol": m.group("symbol"),
            "buy_sell": bs,
            "quantity": qty,
            "price": price,
            "value": round(qty * price, 2),
        })

    charges = {
        "brokerage": _num_or_zero(_first_match(r"Brokerage\s*[:\-]?\s*([\d,]+\.\d+)", text)),
        "stt": _num_or_zero(_first_match(r"STT\s*[:\-]?\s*([\d,]+\.\d+)", text)),
        "stamp_duty": _num_or_zero(_first_match(r"Stamp Duty\s*[:\-]?\s*([\d,]+\.\d+)", text)),
        "exchange_txn_charges": _num_or_zero(_first_match(r"Exchange (?:Transaction )?Charges\s*[:\-]?\s*([\d,]+\.\d+)", text)),
        "sebi_charges": _num_or_zero(_first_match(r"SEBI [Cc]harges\s*[:\-]?\s*([\d,]+\.\d+)", text)),
        "gst": _num_or_zero(_first_match(r"GST\s*[:\-]?\s*([\d,]+\.\d+)", text)),
        "net_total": _num_or_zero(_first_match(r"Net Total\s*[:\-]?\s*([\d,]+\.\d+)", text)),
    }
    return {
        "broker": broker,
        "contract_note_no": contract_note_no,
        "account_code": account_code,
        "trade_date": trade_date,
        "trades": trades,
        "charges": charges,
    }


def parse_contract_note(broker: str, text: str) -> dict:
    broker = broker.lower()
    if broker == "zerodha":
        return parse_zerodha_pdf(text)
    if broker in ("angelone", "upstox"):
        return _generic_text_parser(broker, text)
    raise ValueError(f"Unsupported broker: {broker}")


def _first_match(pattern: str, text: str):
    """Safety net: even if a pattern's alternation accidentally matches a
    branch with no capturing group (e.g. a bare 'IGST' label instead of the
    'IGST 123.45' branch), this returns None instead of crashing the whole
    file with an AttributeError on None.strip()."""
    m = re.search(pattern, text)
    if not m:
        return None
    try:
        value = m.group(1)
    except IndexError:
        value = None
    return value.strip() if value else None


def _num_or_zero(s):
    return _num(s) if s else 0.0


def _to_iso_date(raw: str) -> str:
    for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw
