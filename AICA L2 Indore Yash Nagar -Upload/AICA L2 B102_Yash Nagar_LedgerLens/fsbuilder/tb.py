"""Trial balance model and loaders.

Sign convention everywhere in this package: Dr is positive, Cr is negative ("signed").

Sources:
  - load_snapshot(): CSV export of a ledger-level trial balance (tested, used by the demo/tests)
  - fetch_from_tally(): TallyPrime XML over HTTP, default localhost:9000 (written to Tally's
    documented request format; NOT yet verified against a live Tally in development)
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, replace
from datetime import date

import pandas as pd

from .format import rs

# Tally's 28 reserved groups: name -> (parent, nature). Used when no group list is supplied.
DEFAULT_GROUPS = {
    "Capital Account": ("", "Liabilities"), "Loans (Liability)": ("", "Liabilities"),
    "Current Liabilities": ("", "Liabilities"), "Fixed Assets": ("", "Assets"),
    "Investments": ("", "Assets"), "Current Assets": ("", "Assets"),
    "Branch / Divisions": ("", "Liabilities"), "Misc. Expenses (ASSET)": ("", "Assets"),
    "Suspense A/c": ("", "Liabilities"), "Reserves & Surplus": ("Capital Account", "Liabilities"),
    "Bank OD A/c": ("Loans (Liability)", "Liabilities"), "Secured Loans": ("Loans (Liability)", "Liabilities"),
    "Unsecured Loans": ("Loans (Liability)", "Liabilities"), "Duties & Taxes": ("Current Liabilities", "Liabilities"),
    "Provisions": ("Current Liabilities", "Liabilities"), "Sundry Creditors": ("Current Liabilities", "Liabilities"),
    "Stock-in-Hand": ("Current Assets", "Assets"), "Deposits (Asset)": ("Current Assets", "Assets"),
    "Loans & Advances (Asset)": ("Current Assets", "Assets"), "Sundry Debtors": ("Current Assets", "Assets"),
    "Cash-in-Hand": ("Current Assets", "Assets"), "Bank Accounts": ("Current Assets", "Assets"),
    "Sales Accounts": ("", "Income"), "Purchase Accounts": ("", "Expenses"),
    "Direct Incomes": ("", "Income"), "Direct Expenses": ("", "Expenses"),
    "Indirect Incomes": ("", "Income"), "Indirect Expenses": ("", "Expenses"),
}
LEDGER_COLS = ["name", "group", "primary_group", "nature", "opening", "closing", "period_dr", "period_cr"]


class TallyError(RuntimeError):
    """Raised with a message a user can act on."""


@dataclass(frozen=True)
class TrialBalance:
    ledgers: pd.DataFrame            # LEDGER_COLS; opening/closing signed (Dr +, Cr -)
    groups: dict                     # name -> (parent, nature)
    company: str = ""
    from_date: date | None = None
    to_date: date | None = None
    adjustments: list = field(default_factory=list)   # plain-language notes on anything we changed
    warnings: list = field(default_factory=list)
    inferred: dict = field(default_factory=dict)   # ledger -> (group, "high"|"low") where the file gave no group

    def chain(self, group: str) -> list[str]:
        """Group, its parent, ... up to the primary group."""
        out, seen = [], set()
        while group and group not in seen and group != "Primary":
            out.append(group)
            seen.add(group)
            group = self.groups.get(group, ("", ""))[0]
        return out or [group or "Primary"]


def _signed(amount, drcr) -> float:
    if pd.isna(amount) or str(drcr).strip() not in ("Dr", "Cr"):
        return 0.0
    return float(amount) if str(drcr).strip() == "Dr" else -float(amount)


def _resolve(groups: dict, group: str) -> tuple[str, str]:
    """(primary group, nature) for a ledger's immediate group."""
    seen, g = set(), group
    while g and g not in seen:
        seen.add(g)
        parent, nature = groups.get(g, ("", ""))
        if not parent:
            return g, nature or "Liabilities"
        g = parent
    return group, "Liabilities"


def load_snapshot(tb_csv, groups_csv=None, company: str = "", from_date=None, to_date=None) -> TrialBalance:
    """Load a ledger-level trial balance CSV with columns:
    name, group, opening_amount, opening_dr_cr, period_debit, period_credit, closing_amount, closing_dr_cr
    (the shape of Tally's own trial balance exports). `groups_csv` lists name,parent,nature."""
    raw = pd.read_csv(tb_csv)
    groups = dict(DEFAULT_GROUPS)
    if groups_csv is not None:
        g = pd.read_csv(groups_csv).fillna("")
        groups.update({r["name"]: (r["parent"], r["nature"]) for _, r in g.iterrows()})
    return _build(raw.rename(columns={"period_debit": "period_dr", "period_credit": "period_cr"}).assign(
        opening=[_signed(a, d) for a, d in zip(raw["opening_amount"], raw["opening_dr_cr"])],
        closing=[_signed(a, d) for a, d in zip(raw["closing_amount"], raw["closing_dr_cr"])]),
        groups, company, from_date, to_date)


def _build(df: pd.DataFrame, groups: dict, company, from_date, to_date) -> TrialBalance:
    df = df.copy()
    df["group"] = df["group"].fillna("").astype(str)
    prim_nat = [_resolve(groups, g) if g != "Primary" else ("Profit & Loss A/c", "Liabilities") for g in df["group"]]
    df["primary_group"] = [p for p, _ in prim_nat]
    df["nature"] = [n for _, n in prim_nat]
    for c in ("period_dr", "period_cr"):
        if c not in df:
            df[c] = float("nan")
    return TrialBalance(df[LEDGER_COLS].reset_index(drop=True), groups, company, from_date, to_date)


def normalise(tb: TrialBalance) -> TrialBalance:
    """Make the trial balance safe to build statements from.

    TallyPrime can show the year's profit inside a Reserves ledger's closing balance while the
    income/expense ledgers still carry it, so Dr and Cr differ by exactly the profit. If that is
    what we see, remove it from the reserve (profit is reported separately as surplus in P&L).
    """
    L = tb.ledgers.copy()
    notes, warns = list(tb.adjustments), list(tb.warnings)
    profit = -L.loc[L["nature"].isin(["Income", "Expenses"]), "closing"].sum()
    diff = L["closing"].sum()
    if abs(diff) > 1.0 and abs(diff + profit) <= 1.0:
        is_res = (L["group"] == "Reserves & Surplus") | (
            (L["primary_group"] == "Capital Account") & L["name"].str.contains(r"reserve|surplus", case=False))
        cr_move = (L["opening"] - L["closing"]).where(is_res, 0.0)   # credit movement in the year
        i = cr_move.idxmax() if len(L) else None
        if i is not None and cr_move[i] >= profit - 1.0:
            L.loc[i, "closing"] += profit
            notes.append(f"Tally's trial balance already included the year's profit of {rs(profit, 2)} inside "
                         f"'{L.loc[i, 'name']}', so Dr and Cr differed by that amount. It was removed from the "
                         "reserve; the profit is shown once, as surplus in the statement of profit and loss.")
        else:
            warns.append(f"Trial balance is out by {rs(abs(diff), 2)}, equal to the profit, but no reserve ledger "
                         "carries it. Statements will not balance until this is resolved.")
    if abs(L["closing"].sum()) > 1.0 and not notes:
        warns.append(f"Closing trial balance does not agree: Dr - Cr = {rs(L['closing'].sum(), 2)}.")
    elif abs(L["closing"].sum()) > 1.0:
        warns.append(f"After adjustment, closing trial balance still differs by {rs(L['closing'].sum(), 2)}.")
    if abs(L["opening"].sum()) > 1.0:
        warns.append(f"Opening balances do not agree: Dr - Cr = {rs(L['opening'].sum(), 2)}.")
    return replace(tb, ledgers=L, adjustments=notes, warnings=warns)


# ---- TallyPrime XML over HTTP --------------------------------------------------------

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]|&#(?:[0-8]|1[12]|1[4-9]|2\d|3[01]);")


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _collection_request(company: str, from_date: date, to_date: date, kind: str, fetch: str) -> bytes:
    return f"""<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>FSB{kind}</ID></HEADER>
<BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
<SVCURRENTCOMPANY>{_esc(company)}</SVCURRENTCOMPANY><SVFROMDATE>{from_date:%Y%m%d}</SVFROMDATE><SVTODATE>{to_date:%Y%m%d}</SVTODATE></STATICVARIABLES>
<TDL><TDLMESSAGE><COLLECTION NAME="FSB{kind}" ISMODIFY="No"><TYPE>{kind}</TYPE><FETCH>{fetch}</FETCH></COLLECTION></TDLMESSAGE></TDL>
</DESC></BODY></ENVELOPE>""".encode("utf-8")


def _post(host: str, port: int, body: bytes, timeout: float) -> bytes:
    req = urllib.request.Request(f"http://{host}:{port}", body, {"Content-Type": "text/xml; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
        raise TallyError(
            f"TallyPrime did not answer at {host}:{port} ({e}). Check that TallyPrime is open with the company "
            "loaded and that the XML server is enabled: F1 Help > Settings > Connectivity > Client/Server "
            "configuration, set 'TallyPrime acts as' to Server or Both, port 9000.") from e


def _decode_xml(raw: bytes) -> ET.Element:
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="replace")
    text = re.sub(r"^\s*<\?xml[^>]*\?>", "", _CTRL.sub("", text))
    try:
        return ET.fromstring(text)
    except ET.ParseError as e:
        raise TallyError(f"Could not read Tally's reply: {e}") from e


_AMT = re.compile(r"(-?[\d,]*\.?\d+)\s*(Dr|Cr)?", re.I)


def parse_amount(text: str | None) -> tuple[float, str | None]:
    """'-1,000.00' -> (-1000.0, None); '1,000.00 Dr' -> (1000.0, 'Dr')."""
    m = _AMT.search((text or "").replace("₹", "").strip())
    if not m:
        return 0.0, None
    return float(m.group(1).replace(",", "")), (m.group(2).capitalize() if m.group(2) else None)


def parse_ledger_xml(raw: bytes) -> list[dict]:
    out = []
    for el in _decode_xml(raw).iter("LEDGER"):
        def txt(tag):
            t = el.find(tag)
            return (t.text or "").strip() if t is not None else ""
        out.append({"name": el.get("NAME") or txt("NAME"), "parent": txt("PARENT"),
                    "opening": parse_amount(txt("OPENINGBALANCE")), "closing": parse_amount(txt("CLOSINGBALANCE"))})
    return out


def parse_group_xml(raw: bytes) -> dict:
    groups = {}
    for el in _decode_xml(raw).iter("GROUP"):
        name = el.get("NAME") or (el.findtext("NAME") or "").strip()
        parent = (el.findtext("PARENT") or "").strip()
        groups[name] = ("" if parent in ("Primary", "&#4; Primary") or parent.endswith("Primary") else parent, "")
    return groups


def fetch_from_tally(company: str, from_date: date, to_date: date, host="localhost", port=9000,
                     timeout: float = 60) -> TrialBalance:
    ledgers = parse_ledger_xml(_post(host, port, _collection_request(
        company, from_date, to_date, "Ledger", "Name, Parent, OpeningBalance, ClosingBalance"), timeout))
    xml_groups = parse_group_xml(_post(host, port, _collection_request(
        company, from_date, to_date, "Group", "Name, Parent"), timeout))
    if not ledgers:
        raise TallyError(f"Tally returned no ledgers for company '{company}'. Check the company name and period.")
    groups = dict(DEFAULT_GROUPS)
    for name, (parent, _) in xml_groups.items():
        groups[name] = (parent, groups.get(name, ("", ""))[1] or _resolve_nature(xml_groups, name))

    # Tally's raw sign is not documented consistently across versions: if no Dr/Cr suffix is given,
    # decide it from the data (asset ledgers should be debit balances).
    def nature_of(parent):
        return _resolve(groups, parent)[1]
    asset_raw = [v["closing"][0] for v in ledgers if v["closing"][1] is None and nature_of(v["parent"]) == "Assets" and v["closing"][0]]
    raw_dr_negative = bool(asset_raw) and sum(1 for x in asset_raw if x < 0) > len(asset_raw) / 2

    def sgn(val):
        amt, suffix = val
        if suffix:
            return amt if suffix == "Dr" else -amt
        return -amt if raw_dr_negative else amt

    df = pd.DataFrame({"name": [v["name"] for v in ledgers], "group": [v["parent"] for v in ledgers],
                       "opening": [sgn(v["opening"]) for v in ledgers], "closing": [sgn(v["closing"]) for v in ledgers]})
    return _build(df, groups, company, from_date, to_date)


def _resolve_nature(xml_groups: dict, name: str) -> str:
    seen, g = set(), name
    while g and g not in seen:
        seen.add(g)
        parent = xml_groups.get(g, ("", ""))[0]
        if not parent:
            return DEFAULT_GROUPS.get(g, ("", "Liabilities"))[1]
        g = parent
    return "Liabilities"
