"""XML request builders for TallyPrime's HTTP server (port 9000).

Inline-TDL collections are used so we fetch only the fields we need.
Field lists target TallyPrime 7.x; unknown fields are simply returned empty by Tally.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

LEDGER_FIELDS = ["NAME", "GUID", "MASTERID", "ALTERID", "PARENT", "ISBILLWISEON", "GSTAPPLICABLE",
                 "TAXTYPE", "GSTDUTYHEAD", "TAXCLASSIFICATIONNAME", "PARTYGSTIN", "LEDGSTREGDETAILS.LIST",
                 "LEDSTATENAME", "INCOMETAXNUMBER", "ISTDSAPPLICABLE", "TDSDEDUCTEETYPE",
                 "TDSAPPLICABLE", "BILLCREDITPERIOD", "OPENINGBALANCE", "CURRENCYNAME"]
GROUP_FIELDS = ["NAME", "GUID", "PARENT", "PRIMARYGROUP", "ISREVENUE", "AFFECTSGROSSPROFIT", "ISDEEMEDPOSITIVE"]
STOCK_FIELDS = ["NAME", "GUID", "MASTERID", "PARENT", "CATEGORY", "BASEUNITS", "GSTAPPLICABLE",
                "GSTTYPEOFSUPPLY", "HSNDETAILS.LIST", "GSTDETAILS.LIST"]
UNIT_FIELDS = ["NAME", "GUID", "ISSIMPLEUNIT", "BASEUNITS", "ADDITIONALUNITS", "CONVERSION"]
GODOWN_FIELDS = ["NAME", "GUID", "PARENT"]
VTYPE_FIELDS = ["NAME", "GUID", "PARENT", "NUMBERINGMETHOD", "ISACTIVE", "AFFECTSSTOCK"]
# Plain fields only. Asking Tally for sub-lists (COMPANYGSTREGDETAILS.LIST) or all methods (NATIVEMETHOD *) of
# the Company object makes some TallyPrime releases crash with "Memory Access Violation".
COMPANY_FIELDS = ["NAME", "GUID", "BASICCOMPANYFORMALNAME", "STARTINGFROM", "BOOKSFROM", "STATENAME",
                  "GSTREGISTRATIONNUMBER", "INCOMETAXNUMBER"]
COMPANY_GST_FIELDS = ["NAME", "GSTREGISTRATIONNUMBER", "GSTIN", "STATENAME", "INCOMETAXNUMBER"]
VOUCHER_FIELDS = ["DATE", "GUID", "MASTERID", "VOUCHERTYPENAME", "VOUCHERNUMBER", "PARTYLEDGERNAME",
                  "NARRATION", "REFERENCE", "ISCANCELLED", "ISOPTIONAL",
                  "ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST", "ALLINVENTORYENTRIES.LIST"]

KIND_SPEC = {
    "ledger": ("Ledger", LEDGER_FIELDS),
    "group": ("Group", GROUP_FIELDS),
    "stock_item": ("StockItem", STOCK_FIELDS),
    "unit": ("Unit", UNIT_FIELDS),
    "godown": ("Godown", GODOWN_FIELDS),
    "voucher_type": ("VoucherType", VTYPE_FIELDS),
}


_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def tally_date(yyyymmdd: str) -> str:
    return f"{int(yyyymmdd[6:8])}-{_MON[int(yyyymmdd[4:6]) - 1]}-{yyyymmdd[:4]}"


def _static_vars(company: str | None, extra: dict[str, str] | None = None) -> str:
    parts = ["<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>"]
    if company:
        parts.append(f"<SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY>")
    for k, v in (extra or {}).items():
        if k in ("SVFROMDATE", "SVTODATE"):          # Tally wants typed dates: 1-Nov-2025
            parts.append(f'<{k} TYPE="Date">{escape(tally_date(v))}</{k}>')
        else:
            parts.append(f"<{k}>{escape(v)}</{k}>")
    return "<STATICVARIABLES>" + "".join(parts) + "</STATICVARIABLES>"


def collection_request(coll_id: str, tally_type: str, fields: list[str], company: str | None = None,
                       static_extra: dict[str, str] | None = None, filters: list[str] | None = None,
                       all_native: bool = False) -> str:
    filter_tag = ""
    systems = ""
    if filters:
        names = ",".join(f"F{i}" for i in range(len(filters)))
        filter_tag = f"<FILTERS>{names}</FILTERS>"
        systems = "".join(f'<SYSTEM TYPE="Formulae" NAME="F{i}">{escape(f)}</SYSTEM>'
                          for i, f in enumerate(filters))
    return (
        "<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>"
        f"<TYPE>Collection</TYPE><ID>{coll_id}</ID></HEADER><BODY><DESC>"
        f"{_static_vars(company, static_extra)}"
        "<TDL><TDLMESSAGE>"
        f'<COLLECTION NAME="{coll_id}" ISMODIFY="No"><TYPE>{tally_type}</TYPE>'
        f"<FETCH>{','.join(fields)}</FETCH>{'<NATIVEMETHOD>*</NATIVEMETHOD>' if all_native else ''}"
        f"{filter_tag}</COLLECTION>{systems}"
        "</TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>"
    )


def companies_request() -> str:
    return collection_request("AAListOfCompanies", "Company", COMPANY_FIELDS)


def company_detail_request(company: str) -> str:
    """All native fields of one company: GSTIN tag names differ across Prime releases."""
    return collection_request("AACompanyDetail", "Company", COMPANY_GST_FIELDS, company,
                              filters=[f'$Name = "{company}"'])


def gst_registrations_request(company: str) -> str:
    """TallyPrime 3.0+ keeps GSTINs in GST Registration masters (TaxUnit), not on the company."""
    return collection_request("AAGSTRegColl", "TaxUnit", ["NAME", "GUID", "GSTREGNUMBER", "STATENAME",
                                                          "GSTREGISTRATIONTYPE"], company)


def masters_request(kind: str, company: str) -> str:
    tally_type, fields = KIND_SPEC[kind]
    return collection_request(f"AA{tally_type}Coll", tally_type, fields, company)


_BASE_TYPE_FN = {"purchase": "$$IsPurchase", "journal": "$$IsJournal", "payment": "$$IsPayment",
                 "receipt": "$$IsReceipt", "sales": "$$IsSales", "debit_note": "$$IsDebitNote",
                 "credit_note": "$$IsCreditNote"}


def vouchers_request(company: str, from_yyyymmdd: str, to_yyyymmdd: str,
                     base_types: list[str] | None = None) -> str:
    """base_types: e.g. ["purchase", "journal"] -> includes custom types under those parents."""
    filters = ["NOT $IsCancelled", "NOT $IsOptional"]
    if base_types:
        cond = " OR ".join(f"{_BASE_TYPE_FN[b]}:$VoucherTypeName" for b in base_types)
        filters.append(f"({cond})")
    return collection_request("AAVoucherColl", "Voucher", VOUCHER_FIELDS, company,
                              {"SVFROMDATE": from_yyyymmdd, "SVTODATE": to_yyyymmdd}, filters)


def voucher_numbers_request(company: str, vtype: str, from_yyyymmdd: str, to_yyyymmdd: str) -> str:
    """Just the numbers (and dates) of one voucher type in a period - to find the next free number."""
    safe = vtype.replace('"', '\\"')
    return collection_request("AAVchNumbers", "Voucher", ["DATE", "VOUCHERNUMBER", "VOUCHERTYPENAME"], company,
                              {"SVFROMDATE": from_yyyymmdd, "SVTODATE": to_yyyymmdd},
                              [f'$VoucherTypeName = "{safe}"', "NOT $IsCancelled"])


def voucher_ids_request(company: str, from_yyyymmdd: str, to_yyyymmdd: str) -> str:
    """Master IDs only - cheap way to see whether the app's copy of the day book is complete."""
    return collection_request("AAVchIds", "Voucher", ["MASTERID", "DATE"], company,
                              {"SVFROMDATE": from_yyyymmdd, "SVTODATE": to_yyyymmdd},
                              ["NOT $IsCancelled", "NOT $IsOptional"])


def import_vouchers_envelope(company: str, voucher_xml_fragments: list[str]) -> str:
    """Wrap pre-built <VOUCHER> fragments into an import request (used from Phase 3)."""
    body = "".join(f'<TALLYMESSAGE xmlns:UDF="TallyUDF">{v}</TALLYMESSAGE>' for v in voucher_xml_fragments)
    return (
        "<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Import</TALLYREQUEST>"
        "<TYPE>Data</TYPE><ID>Vouchers</ID></HEADER><BODY><DESC>"
        f"<STATICVARIABLES><SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY></STATICVARIABLES>"
        f"</DESC><DATA>{body}</DATA></BODY></ENVELOPE>"
    )


def ledger_balance_request(company: str, ledger: str, from_yyyymmdd: str, to_yyyymmdd: str) -> str:
    """Closing balance of one ledger as at to-date (Tally sign: negative = Dr)."""
    safe = ledger.replace('"', '\\"')
    return collection_request("AALedgerBal", "Ledger", ["NAME", "PARENT", "OPENINGBALANCE", "CLOSINGBALANCE"],
                              company, {"SVFROMDATE": from_yyyymmdd, "SVTODATE": to_yyyymmdd},
                              filters=[f'$Name = "{safe}"'])


def _q(s: str) -> str:
    return s.replace('"', '\\"')


def bills_request(company: str, party: str = "", on_date: str = "") -> str:
    """Pending bills (Tally's Bills collection). party="" -> every party's bills (for dashboards)."""
    filters = [f'$Parent = "{_q(party)}"'] if party else []
    extra = {"SVFROMDATE": on_date, "SVTODATE": on_date} if on_date else None
    return collection_request("AABillsColl", "Bills", ["NAME", "PARENT", "BILLDATE", "CLOSINGBALANCE",
                                                       "BILLCREDITPERIOD", "BILLDUEDATE"], company, extra, filters)


def ledger_closings_request(company: str, from_yyyymmdd: str, to_yyyymmdd: str) -> str:
    """Every ledger with its opening and closing balance for the period, computed by Tally."""
    return collection_request("AALedgerClosings", "Ledger", ["NAME", "PARENT", "OPENINGBALANCE", "CLOSINGBALANCE"],
                              company, {"SVFROMDATE": from_yyyymmdd, "SVTODATE": to_yyyymmdd})


def groups_request(company: str) -> str:
    return collection_request("AAGroupTree", "Group", ["NAME", "PARENT", "ISREVENUE", "AFFECTSGROSSPROFIT",
                                                       "ISDEEMEDPOSITIVE", "ISADDABLE"], company)


def stock_values_request(company: str, from_yyyymmdd: str, to_yyyymmdd: str) -> str:
    return collection_request("AAStockValues", "StockItem", ["NAME", "OPENINGVALUE", "CLOSINGVALUE"], company,
                              {"SVFROMDATE": from_yyyymmdd, "SVTODATE": to_yyyymmdd})


def trial_balance_report_request(company: str, from_yyyymmdd: str, to_yyyymmdd: str, explode: bool = False) -> str:
    """Tally's own Trial Balance report (top-level groups, or exploded), used to cross-check the app's figures."""
    return ("<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Data</TYPE>"
            "<ID>Trial Balance</ID></HEADER><BODY><DESC>"
            + _static_vars(company, {"SVFROMDATE": from_yyyymmdd, "SVTODATE": to_yyyymmdd,
                                     "EXPLODEFLAG": "Yes" if explode else "No"})
            + "</DESC></BODY></ENVELOPE>")
