"""XML request builders for Tally's XML-over-HTTP interface (ported from requests.ts, byte-for-byte equivalent).

Lessons learned live by the Node project and kept here:
* Voucher date ranges MUST be enforced by a filter formula inside the collection; TallyPrime ignores
  SVFROMDATE/SVTODATE for Voucher collections and would export the whole company.
* Monthly batches use whole months (Educational mode only honours the 1st, 2nd and 31st).
"""
from __future__ import annotations

from datetime import date, timedelta

_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def tally_date(iso: str) -> str:
    """'2024-04-01' -> '1-Apr-2024'"""
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d}-{_MON[m - 1]}-{y}"


def add_days(iso: str, n: int) -> str:
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def month_end(iso: str) -> str:
    d = date.fromisoformat(iso[:7] + "-01")
    nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return (nxt - timedelta(days=1)).isoformat()


def months_between(from_iso: str, to_iso: str) -> list[str]:
    """First day of every month touched by [from, to]."""
    out, y, m = [], int(from_iso[:4]), int(from_iso[5:7])
    while f"{y:04d}-{m:02d}-01" <= to_iso:
        out.append(f"{y:04d}-{m:02d}-01")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _static_vars(company: str | None = None, frm: str | None = None, to: str | None = None) -> str:
    return "".join([
        "<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>",
        f"<SVCURRENTCOMPANY>{xml_escape(company)}</SVCURRENTCOMPANY>" if company else "",
        f'<SVFROMDATE TYPE="Date">{tally_date(frm)}</SVFROMDATE>' if frm else "",
        f'<SVTODATE TYPE="Date">{tally_date(to)}</SVTODATE>' if to else "",
    ])


def collection_request(*, id: str, type: str, fetch: list[str], company: str | None = None,
                       frm: str | None = None, to: str | None = None,
                       filters: list[str] | None = None, formulae: dict[str, str] | None = None) -> str:
    eid = xml_escape(id)
    flt = f"<FILTERS>{','.join(xml_escape(f) for f in filters)}</FILTERS>" if filters else ""
    frm_x = "".join(f'<SYSTEM TYPE="Formulae" NAME="{xml_escape(k)}">{xml_escape(v)}</SYSTEM>'
                    for k, v in (formulae or {}).items())
    return (f"<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE>"
            f"<ID>{eid}</ID></HEADER><BODY><DESC><STATICVARIABLES>{_static_vars(company, frm, to)}</STATICVARIABLES>"
            f'<TDL><TDLMESSAGE><COLLECTION NAME="{eid}" ISMODIFY="No"><TYPE>{xml_escape(type)}</TYPE>'
            f"<FETCH>{', '.join(xml_escape(f) for f in fetch)}</FETCH>{flt}</COLLECTION>{frm_x}</TDLMESSAGE></TDL>"
            f"</DESC></BODY></ENVELOPE>")


FETCH = {
    "company": ["Name", "GUID", "StartingFrom", "BooksFrom", "LastVoucherDate", "BaseCurrencySymbol"],
    "group": ["Name", "Parent", "IsRevenue", "AffectsGrossProfit", "IsDeemedPositive", "GUID", "AlterID"],
    "ledger": [
        "Name", "Parent", "GUID", "MasterID", "AlterID", "OpeningBalance", "ClosingBalance", "IsBillWiseOn",
        "BillCreditPeriod", "CreditLimit", "PartyGSTIN", "LedStateName", "CurrencyName",
        "BillAllocations.Name", "BillAllocations.BillDate", "BillAllocations.OpeningBalance",
        "BillAllocations.BillCreditPeriod", "BillAllocations.IsAdvance",
        "LedgerClosingValues",
    ],
    "voucherType": ["Name", "Parent"],
    "costCentre": ["Name", "Parent", "Category", "GUID"],
    "stockGroup": ["Name", "Parent", "GUID"],
    "unit": ["Name", "IsSimpleUnit", "BaseUnits", "AdditionalUnits", "Conversion", "DecimalPlaces"],
    "godown": ["Name", "Parent"],
    "stockItem": ["Name", "Parent", "BaseUnits", "GUID", "MasterID", "AlterID", "OpeningBalance", "OpeningValue",
                  "ClosingBalance", "ClosingValue", "CostingMethod", "GSTHSNCode"],
    "voucher": [
        "Date", "VoucherTypeName", "VoucherNumber", "Reference", "PartyLedgerName", "Narration", "GUID", "MasterID",
        "AlterID", "IsCancelled", "IsOptional", "IsPostDated", "IsInvoice",
        "AllLedgerEntries.LedgerName", "AllLedgerEntries.Amount", "AllLedgerEntries.IsDeemedPositive",
        "AllLedgerEntries.BillAllocations", "AllLedgerEntries.CategoryAllocations",
        "AllInventoryEntries", "InventoryEntriesIn", "InventoryEntriesOut",
    ],
}


def master_requests(company: str, as_of: str | None = None, books_from: str | None = None) -> dict[str, str]:
    """Opening balances are 'as at the start of the period', so ledgers/stock items start at the books' beginning."""
    def c(id, type, key, dated=False):
        return collection_request(id=id, type=type, fetch=FETCH[key], company=company,
                                  frm=books_from if dated else None, to=as_of if dated else None)
    return {
        "groups": c("MIS_Groups", "Group", "group"),
        "ledgers": c("MIS_Ledgers", "Ledger", "ledger", True),
        "voucherTypes": c("MIS_VchTypes", "VoucherType", "voucherType"),
        "costCentres": c("MIS_CostCentres", "CostCentre", "costCentre"),
        "stockGroups": c("MIS_StockGroups", "StockGroup", "stockGroup"),
        "units": c("MIS_Units", "Unit", "unit"),
        "godowns": c("MIS_Godowns", "Godown", "godown"),
        "stockItems": c("MIS_StockItems", "StockItem", "stockItem", True),
    }


def company_list_request() -> str:
    return collection_request(id="MIS_Companies", type="Company", fetch=FETCH["company"])


def stock_valuation_request(company: str, frm: str, as_of: str) -> str:
    return collection_request(id="MIS_StockVal", type="StockItem", fetch=["Name", "ClosingBalance", "ClosingValue"],
                              company=company, frm=frm, to=as_of)


def voucher_range_request(company: str, frm: str, to: str, after_alter_id: int | None = None) -> str:
    """Vouchers in [from, to]; exclusive upper bound on the following day (see module note)."""
    formulae = {"MISInRange": f'$Date >= $$Date:"{tally_date(frm)}" AND $Date < $$Date:"{tally_date(add_days(to, 1))}"'}
    if after_alter_id is not None:
        formulae["MISAltered"] = f"$AlterID > {int(after_alter_id)}"
    return collection_request(id="MIS_Vouchers" if after_alter_id is None else "MIS_VchDelta", type="Voucher",
                              fetch=FETCH["voucher"], company=company, frm=frm, to=to,
                              filters=list(formulae), formulae=formulae)
