"""XML to create a supplier ledger or a stock item in Tally. Used only after the user confirmed in the UI;
the result is checked by reading the masters back from Tally."""
from __future__ import annotations

from decimal import Decimal

from ipt.core.states import state_name
from ipt.services.tally.client import esc


def _envelope(company: str, body: str) -> str:
    return ("<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC>"
            "<REPORTNAME>All Masters</REPORTNAME><STATICVARIABLES>"
            f"<SVCURRENTCOMPANY>{esc(company)}</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC><REQUESTDATA>"
            f'<TALLYMESSAGE xmlns:UDF="TallyUDF">{body}</TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>')


def _ledger_gst(name: str, gstin: str) -> str:
    """GST registration and the party's state, in the old fields and in the detail tables TallyPrime 3 and later
    read (Mailing Details, GST Registration Details) - without the state there, GSTR-3B lists the vouchers under
    'GST Registration Details of the Party are invalid or not specified'."""
    state = state_name(gstin[:2]) if gstin else ""
    x = "<COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>"
    if state:
        x += (f"<LEDSTATENAME>{esc(state)}</LEDSTATENAME><STATENAME>{esc(state)}</STATENAME>"
              "<LEDMAILINGDETAILS.LIST><APPLICABLEFROM>20170701</APPLICABLEFROM>"
              f"<MAILINGNAME>{esc(name)}</MAILINGNAME><STATE>{esc(state)}</STATE><COUNTRY>India</COUNTRY>"
              "</LEDMAILINGDETAILS.LIST>")
    if gstin:
        x += ("<GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE>"
              f"<PARTYGSTIN>{esc(gstin)}</PARTYGSTIN>"
              "<LEDGSTREGDETAILS.LIST><APPLICABLEFROM>20170701</APPLICABLEFROM>"
              f"<GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE><STATE>{esc(state)}</STATE>"
              f"<PLACEOFSUPPLY>{esc(state)}</PLACEOFSUPPLY><GSTIN>{esc(gstin)}</GSTIN>"
              "<ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE><CONSIDERPURCHASEFOREXPORT>No"
              "</CONSIDERPURCHASEFOREXPORT><ISTRANSPORTER>No</ISTRANSPORTER><ISCOMMONPARTY>No</ISCOMMONPARTY>"
              "</LEDGSTREGDETAILS.LIST>")
    return x


def ledger_xml(company: str, name: str, gstin: str, parent: str = "Sundry Creditors") -> str:
    """A supplier ledger with GST registration (Regular), state from the GSTIN, bill-wise on."""
    body = (f'<LEDGER NAME="{esc(name)}" ACTION="Create"><NAME.LIST><NAME>{esc(name)}</NAME></NAME.LIST>'
            f"<PARENT>{esc(parent)}</PARENT><ISBILLWISEON>Yes</ISBILLWISEON>"
            + _ledger_gst(name, gstin) + "</LEDGER>")
    return _envelope(company, body)


def _fill(rows: list[str], fields: dict[str, str]) -> list[str]:
    """Put values into EMPTY / missing tags of the ledger's own detail rows; every other tag stays as Tally sent it
    (address lines, pincode, transporter flags ...). Only the newest row is filled."""
    import xml.etree.ElementTree as ET
    els = [ET.fromstring(r) for r in rows]
    newest = max(els, key=lambda e: (e.findtext("APPLICABLEFROM") or ""))
    for tag, val in fields.items():
        node = newest.find(tag)
        if node is None:
            node = ET.SubElement(newest, tag)
        if not (node.text or "").strip():
            node.text = val
    return [ET.tostring(e, encoding="unicode") for e in els]


def ledger_gst_alter_xml(company: str, name: str, gstin: str, mailing: list[str] | None = None,
                         gstreg: list[str] | None = None) -> str:
    """Add the party's state / GST registration to an existing ledger. When Tally already has detail rows for the
    ledger they are sent back with only the empty fields filled - nothing the user entered is replaced."""
    state = state_name(gstin[:2]) if gstin else ""
    parts = ""
    if mailing:
        parts += "".join(_fill(mailing, {"STATE": state, "COUNTRY": "India"}))
    elif state:
        parts += ("<LEDMAILINGDETAILS.LIST><APPLICABLEFROM>20170701</APPLICABLEFROM>"
                  f"<MAILINGNAME>{esc(name)}</MAILINGNAME><STATE>{esc(state)}</STATE><COUNTRY>India</COUNTRY>"
                  "</LEDMAILINGDETAILS.LIST>")
    if gstreg:
        parts += "".join(_fill(gstreg, {"GSTREGISTRATIONTYPE": "Regular", "STATE": state, "PLACEOFSUPPLY": state,
                                        "GSTIN": gstin}))
    elif gstin:
        parts += ("<LEDGSTREGDETAILS.LIST><APPLICABLEFROM>20170701</APPLICABLEFROM>"
                  f"<GSTREGISTRATIONTYPE>Regular</GSTREGISTRATIONTYPE><STATE>{esc(state)}</STATE>"
                  f"<PLACEOFSUPPLY>{esc(state)}</PLACEOFSUPPLY><GSTIN>{esc(gstin)}</GSTIN></LEDGSTREGDETAILS.LIST>")
    body = (f'<LEDGER NAME="{esc(name)}" ACTION="Alter"><NAME.LIST><NAME>{esc(name)}</NAME></NAME.LIST>'
            + parts + "</LEDGER>")
    return _envelope(company, body)


# GST Unit Quantity Codes (UQC) for the units Indian purchase bills use
UQC = {"MT": "MTS-METRIC TON", "MTS": "MTS-METRIC TON", "TON": "TON-TONNES", "TONNE": "TON-TONNES",
       "TONNES": "TON-TONNES", "KG": "KGS-KILOGRAMS", "KGS": "KGS-KILOGRAMS", "G": "GMS-GRAMMES",
       "GM": "GMS-GRAMMES", "GMS": "GMS-GRAMMES", "QTL": "QTL-QUINTAL", "NOS": "NOS-NUMBERS", "NO": "NOS-NUMBERS",
       "NOS.": "NOS-NUMBERS", "PCS": "PCS-PIECES", "PC": "PCS-PIECES", "PIECE": "PCS-PIECES", "LTR": "LTR-LITRES",
       "LTRS": "LTR-LITRES", "L": "LTR-LITRES", "ML": "MLT-MILILITRE", "MTR": "MTR-METERS", "MTRS": "MTR-METERS",
       "M": "MTR-METERS", "SQM": "SQM-SQUARE METERS", "SQFT": "SQF-SQUARE FEET", "CBM": "CBM-CUBIC METERS",
       "BAG": "BAG-BAGS", "BAGS": "BAG-BAGS", "BOX": "BOX-BOX", "BOXES": "BOX-BOX", "ROLL": "ROL-ROLLS",
       "ROLLS": "ROL-ROLLS", "ROL": "ROL-ROLLS", "SET": "SET-SETS", "SETS": "SET-SETS", "PAIR": "PRS-PAIRS",
       "PRS": "PRS-PAIRS", "DOZ": "DOZ-DOZENS", "DOZEN": "DOZ-DOZENS", "BTL": "BTL-BOTTLES", "CAN": "CAN-CANS",
       "CTN": "CTN-CARTONS", "DRM": "DRM-DRUMS", "PAC": "PAC-PACKS", "PKT": "PAC-PACKS", "TBS": "TBS-TABLETS",
       "UNT": "UNT-UNITS", "UNIT": "UNT-UNITS", "KLR": "KLR-KILOLITRE", "KME": "KME-KILOMETRE"}


def uqc_for(unit: str) -> str:
    return UQC.get((unit or "").strip().upper(), "")


def unit_uqc_alter_xml(company: str, unit: str, uqc: str) -> str:
    """Map a Tally unit to its GST UQC (GSTR-3B: 'UOM is not mapped to the Unit Quantity Code')."""
    body = (f'<UNIT NAME="{esc(unit)}" ACTION="Alter"><NAME>{esc(unit)}</NAME>'
            f"<GSTREPUOM>{esc(uqc)}</GSTREPUOM></UNIT>")
    return _envelope(company, body)


def stock_item_xml(company: str, name: str, unit: str, hsn: str = "", gst_rate: Decimal | None = None) -> str:
    """A stock item with its unit and, when known, HSN and GST rate (IGST = rate, CGST = SGST = half)."""
    gst = ""
    if hsn or gst_rate is not None:
        rates = ""
        if gst_rate is not None:
            half = (Decimal(gst_rate) / 2).normalize()
            for head, r in (("CGST", half), ("SGST/UTGST", half), ("IGST", Decimal(gst_rate).normalize()),
                            ("Cess", Decimal(0))):
                rates += (f"<RATEDETAILS.LIST><GSTRATEDUTYHEAD>{head}</GSTRATEDUTYHEAD>"
                          f"<GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>"
                          f"<GSTRATE>{r:f}</GSTRATE></RATEDETAILS.LIST>")
        gst = ("<GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE><GSTDETAILS.LIST><APPLICABLEFROM>20170701"
               "</APPLICABLEFROM><CALCULATIONTYPE>On Value</CALCULATIONTYPE>"
               + (f"<HSNCODE>{esc(hsn)}</HSNCODE>" if hsn else "")
               + "<TAXABILITY>Taxable</TAXABILITY><ISREVERSECHARGEAPPLICABLE>No</ISREVERSECHARGEAPPLICABLE>"
               + (f"<STATEWISEDETAILS.LIST><STATENAME>&#4; Any</STATENAME>{rates}</STATEWISEDETAILS.LIST>"
                  if rates else "")
               + "</GSTDETAILS.LIST>")
    body = (f'<STOCKITEM NAME="{esc(name)}" ACTION="Create"><NAME.LIST><NAME>{esc(name)}</NAME></NAME.LIST>'
            f"<PARENT/><BASEUNITS>{esc(unit)}</BASEUNITS>{gst}</STOCKITEM>")
    return _envelope(company, body)
