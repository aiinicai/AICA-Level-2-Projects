"""Create masters in TallyPrime (ledgers) through the XML import interface."""
from __future__ import annotations

from xml.sax.saxutils import escape

from ..gst_states import state_name


def ledger_xml(name: str, parent: str, gstin: str = "", pan: str = "", state: str = "", bill_wise: bool = False,
               mailing_name: str = "", address: list[str] | None = None, affects_stock: bool | None = None) -> str:
    n = escape(name)
    if affects_stock is None:
        # Tally's own default: purchase / sales ledgers carry stock. With No, item invoices through the ledger keep
        # only the amounts and silently drop the quantities (stock never moves)
        affects_stock = parent in ("Purchase Accounts", "Sales Accounts")
    state = state or (state_name(gstin[:2]) if gstin else "")
    parts = [f'<LEDGER NAME="{n}" ACTION="Create"><NAME.LIST TYPE="String"><NAME>{n}</NAME></NAME.LIST>',
             f"<PARENT>{escape(parent)}</PARENT>",
             f"<ISBILLWISEON>{'Yes' if bill_wise else 'No'}</ISBILLWISEON>",
             f"<AFFECTSSTOCK>{'Yes' if affects_stock else 'No'}</AFFECTSSTOCK><COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>"]
    if state:
        parts.append(f"<LEDSTATENAME>{escape(state)}</LEDSTATENAME>")
    if pan:
        parts.append(f"<INCOMETAXNUMBER>{escape(pan)}</INCOMETAXNUMBER>")
    if gstin:
        g = escape(gstin)
        parts.append(f"<GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE><PARTYGSTIN>{g}</PARTYGSTIN>"
                     f"<LEDGSTREGDETAILS.LIST><APPLICABLEFROM>20170701</APPLICABLEFROM>"
                     f"<GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>"
                     f"<PLACEOFSUPPLY>{escape(state)}</PLACEOFSUPPLY><GSTIN>{g}</GSTIN></LEDGSTREGDETAILS.LIST>")
    mail = escape(mailing_name or name)
    addr = "".join(f"<ADDRESS>{escape(a)}</ADDRESS>" for a in (address or []) if a)
    parts.append(f"<LEDMAILINGDETAILS.LIST><APPLICABLEFROM>20170701</APPLICABLEFROM><MAILINGNAME>{mail}</MAILINGNAME>"
                 + (f'<ADDRESS.LIST TYPE="String">{addr}</ADDRESS.LIST>' if addr else "")
                 + (f"<STATE>{escape(state)}</STATE>" if state else "")
                 + "<COUNTRY>India</COUNTRY></LEDMAILINGDETAILS.LIST>")
    parts.append("</LEDGER>")
    return "".join(parts)


def import_masters_envelope(company: str, fragments: list[str]) -> str:
    body = "".join(f'<TALLYMESSAGE xmlns:UDF="TallyUDF">{f}</TALLYMESSAGE>' for f in fragments)
    return ("<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Import</TALLYREQUEST><TYPE>Data</TYPE>"
            "<ID>All Masters</ID></HEADER><BODY><DESC><STATICVARIABLES>"
            f"<SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY></STATICVARIABLES></DESC>"
            f"<DATA>{body}</DATA></BODY></ENVELOPE>")
