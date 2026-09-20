"""CENTRAL MAPPING TABLE - the single place that says which NIC column receives what.

Keys are the NIC utility's own column codes from the hidden code row of each sheet
(e.g. colDocno). The writer resolves each code to its column letter at run time, so if
NIC moves a column in a later utility version nothing here needs to change.

Tuple: (NIC code, source / rule description)
"""

EINVOICE_MAP = [
    ("colSupType",     "User selection 'Export under' -> EXPWOP / EXPWP (NIC 'Supply' master)"),
    ("colRevCharge",   "Export: 'No' (template rule: reverse charge cannot be Yes for EXPORT)"),
    ("colEcomGstin",   "Not applicable - left blank"),
    ("colIgstIntra",   "Export: 'No' (template rule: cannot be Yes for EXPORT)"),
    ("colDoctype",     "Mapping profile document type (NIC 'Doctype' master), default 'Tax Invoice'"),
    ("colDocno",       "Source: 'INVOICE NO' label"),
    ("colDocdate",     "Source: 'DATE' next to invoice number -> DD/MM/YYYY"),
    ("colBgstin",      "Export: 'URP' (template rule for EXPWP/EXPWOP)"),
    ("colBLegalname",  "Source: first line of Consignee / Notify Party block (user chooses buyer)"),
    ("colBTradname",   "Not on invoice - left blank"),
    ("colPos",         "Export: 'OTHER COUNTRIES' (template rule)"),
    ("colBaddr1",      "Source: buyer block, address line 1"),
    ("colBaddr2",      "Source: buyer block, remaining address lines"),
    ("colBLoc",        "Source: last element of buyer address, or user override"),
    ("colBPin",        "Export: 999999 (template rule for foreign buyer)"),
    ("colBState",      "Export: 'OTHER COUNTRIES' (template rule)"),
    ("colSLegalname",  "Only when buyer is Notify Party: Consignee name as ship-to"),
    ("colSaddr1",      "Only when buyer is Notify Party: Consignee address line 1"),
    ("colSaddr2",      "Only when buyer is Notify Party: Consignee remaining lines"),
    ("colSLoc",        "Only when buyer is Notify Party: Consignee location"),
    ("colSPin",        "Only when buyer is Notify Party: 999999"),
    ("colSState",      "Only when buyer is Notify Party: OTHER COUNTRIES"),
    ("colTotTaxval",   "Sum of item taxable values (INR)"),
    ("colTsgstval",    "Sum of item SGST (0 for export)"),
    ("colTcgstval",    "Sum of item CGST (0 for export)"),
    ("colTigstval",    "Sum of item IGST"),
    ("colTcessval",    "Sum of item cess (0 - no cess on source)"),
    ("colTstcessval",  "Sum of item state cess (0)"),
    ("colTDiscount",   "Invoice-level discount (0 - none on source)"),
    ("colTOthChrgs",   "Invoice-level other charges (0 - none on source)"),
    ("colRoundOff",    "Round-off (only if user ticks rounding)"),
    ("colTinvoiceval", "Sum of item totals + other charges - discount + round-off"),
    ("colShipBilNo",   "Source 'SHIPPING BILL NO' label or user input; blank if unavailable"),
    ("colShipBilDt",   "Source 'SHIPPING BILL DATE' label or user input; blank if unavailable"),
    ("colPort",        "User selects from NIC port master (suggested from 'PORT OF LOADING')"),
    ("colSupRefund",   "User selection Yes / No / blank"),
    ("colForCur",      "Source: currency code in the Amount column heading, checked against NIC currency master"),
    ("colCntryCode",   "Source: country of final destination, matched to NIC country master"),
    ("colExpDty",      "User input (INR) if applicable; otherwise blank"),
]

ITEMS_MAP = [
    ("colIDoctype",    "Same as eInvoice Document Type"),
    ("colIDocno",      "Same as eInvoice Document Number"),
    ("colIDocdate",    "Same as eInvoice Document Date"),
    ("colProdSlno",    "Running serial number of detected item rows"),
    ("colProddesc",    "Source: Description column"),
    ("colProdservice", "'No' - goods (HSN not in chapter 99)"),
    ("colHsn",         "Source: HSN column (kept as text, leading zeros preserved)"),
    ("colQuantity",    "Per GST quantity basis chosen in mapping profile"),
    ("colFreeQuanty",  "0"),
    ("colUnit",        "User-confirmed UQC description from NIC 'Units' master"),
    ("colUnitPrice",   "Source rate for the chosen basis x exchange rate (or derived value / qty)"),
    ("colTotal",       "Source Amount (FC) x exchange rate, rounded to 2 decimals"),
    ("colDiscount",    "Source discount column if present, else 0"),
    ("colAssValue",    "Gross amount - discount"),
    ("colGstrate",     "User-entered GST rate per item (never assumed)"),
    ("colSgst",        "0 (export - inter-State)"),
    ("colCgst",        "0 (export - inter-State)"),
    ("colIgst",        "EXPWOP: 0; EXPWP: taxable value x GST rate"),
    ("colCessrate",    "0"),
    ("colCessadval",   "0"),
    ("colCessnonad",   "0"),
    ("colStCessrate",  "0"),
    ("colStCessadval", "0"),
    ("colStCessnonad", "0"),
    ("colOthChrgs",    "0"),
    ("colTolitemval",  "Taxable value + IGST + CGST + SGST + cess + other charges"),
]

EINVOICE_CODES = [c for c, _ in EINVOICE_MAP]
ITEMS_CODES = [c for c, _ in ITEMS_MAP]
SOURCE_RULE = dict(EINVOICE_MAP + ITEMS_MAP)
