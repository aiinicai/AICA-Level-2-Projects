"""Built-in mapping profile for label-based export commercial invoices.

Nothing here is tied to a particular invoice number, customer or product: fields are
located by their printed LABELS and item columns by their HEADER wording, so the rows
and columns may move between invoices. Every regex can be edited in a saved profile
(profiles/*.json) without touching program code."""

DEFAULT_PROFILE = {
    "profile_name": "Label-based Export Invoice (built-in)",
    "invoice_sheet": ["^INVOICE$", "INVOICE"],
    "exclude_sheet": ["PACKING"],
    "packing_sheet": ["PACKING"],
    "fields": {
        "invoice_no": {"label": r"INVOICE\s*NO|^\s*BILL\s*NO|TAX\s*INVOICE\s*NO|DOCUMENT\s*NO", "mode": "inline_below",
                       "value_pattern": r"(?=[A-Za-z0-9/\-]*\d)[A-Za-z0-9][A-Za-z0-9/\-]{0,15}",
                       "below_regex": r"^\s*((?=[A-Za-z0-9/\-]*\d)[A-Za-z0-9][A-Za-z0-9/\-]*)",
                       "regex": r"INVOICE\s*NO\.?\s*[:\-]?\s*((?=[A-Za-z0-9/\-]*\d)[A-Za-z0-9][A-Za-z0-9/\-]*)"},
        "invoice_date": {"label": r"\bI?DATE\b|DATED", "mode": "inline_right", "near": "invoice_no", "cell_of": "invoice_no",
                         "cell_regex": r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})",
                         "regex": r"DATE(?:\s*OF\s*(?:SUPPLY|ISSUE|INVOICE))?\s*[:\-]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}[\s\-]+[A-Za-z]{3,9}\.?[\s\-,]+\d{2,4})",
                         "value_pattern": r"\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}[\s\-]+[A-Za-z]{3,9}\.?[\s\-,]+\d{2,4}"},
        "exporter_gstin": {"label": r"\bGSTIN\b|\bGST\s*NO", "mode": "inline_right",
                           "regex": r"(?:GSTIN|GST\s*NO\.?)\s*(?:NO\.?)?\s*[:\-]?\s*([0-9]{2}[0-9A-Z]{13})", "value_pattern": r"[0-9]{2}[0-9A-Z]{13}"},
        "iec": {"label": r"\bIEC\b", "mode": "inline_right", "regex": r"IEC\s*(?:NO\.?)?\s*[:\-]?\s*([0-9A-Z]{10})"},
        "exporter_block": {"label": r"^\s*EXPORTER\s*$", "mode": "block_below"},
        "consignee": {"label": r"^\s*CONSIGNEE\b", "mode": "block_below"},
        "notify_party": {"label": r"^\s*NOTIFY\s*PARTY", "mode": "block_below"},
        "buyer_block": {"label": r"^\s*BUYER\b(?!.*ORDER)", "mode": "block_below"},
        "buyer_name": {"label": r"(?<!NOTIFY )\b(BILL(ED)?\s*TO|SOLD\s*TO|BUYER|CUSTOMER|CLIENT|RECEIVER|"
                                r"RECIPIENT|COMPANY)\b",
                       "mode": "inline_right", "gather_column": False,
                       "regex": r"(?:BILL(?:ED)?\s*TO|SOLD\s*TO|BUYER(?:\s*(?:NAME|DETAILS))?|"
                                r"CUSTOMER(?:\s*DETAILS)?|CLIENT|RECEIVER|RECIPIENT|COMPANY)"
                                r"\s*(?:NAME)?\s*[:\-]\s*([A-Za-z0-9][^|]{2,99})$"},
        "buyer_block2": {"label": r"DETAILS\s*OF\s*(BUYER|RECEIVER|RECIPIENT|CUSTOMER)|"
                                  r"^\s*(BILL(ED)?\s*TO|SOLD\s*TO|BUYER|CUSTOMER)\s*:?\s*$",
                         "mode": "block_below"},
        "buyer_address": {"label": r"^\s*ADDRESS\s*:?\s*$", "mode": "inline_right", "gather_column": True},
        "buyer_email": {"label": r"^\s*E-?MAIL\s*:?\s*$", "mode": "inline_right",
                        "value_pattern": r"[A-Za-z0-9+_.\-]+@[A-Za-z0-9.\-]+"},
        "sac_code": {"label": r"\bSAC\s*(CODE)?\b|HSN\s*/\s*SAC|SAC\s*/\s*HSN", "mode": "inline_right",
                     "regex": r"SAC\s*(?:CODE)?\s*[:\-]?\s*([0-9]{4,8})", "value_pattern": r"[0-9]{4,8}"},
        "country_of_origin": {"label": r"COUNTRY\s*OF\s*ORIGIN", "mode": "inline_below",
                              "regex": r"ORIGIN[^:]*:\s*([A-Za-z][A-Za-z .]+)$"},
        "country_final_destination": {"label": r"DESTINATION\s*:", "mode": "inline",
                                      "regex": r"DESTINATION\s*:\s*([A-Za-z][A-Za-z .,&()\-]+)$"},
        "final_destination": {"label": r"^\s*FINAL\s*DESTINATION\s*$", "mode": "below"},
        "port_of_loading": {"label": r"^\s*PORT\s*OF\s*LOADING", "mode": "below_or_above"},
        "port_of_discharge": {"label": r"^\s*PORT\s*OF\s*DISCHARGE", "mode": "below"},
        "place_of_receipt": {"label": r"^\s*PLACE\s*OF\s*RECEIPT", "mode": "below"},
        "pre_carriage": {"label": r"^\s*PRE[\s\-]*CARRIAGE", "mode": "below"},
        "vessel_flight": {"label": r"^\s*VESSEL", "mode": "below"},
        "terms": {"label": r"TERMS\s*OF\s*DELIVERY", "mode": "below"},
        "amount_in_words": {"label": r"AMOUNT\s*IN\s*WORDS", "mode": "inline",
                            "regex": r"AMOUNT\s*IN\s*WORDS\s*[:\-]?\s*(.+)$"},
        "exchange_rate": {"label": r"EXCHANGE\s*RATE|CONVERSION\s*RATE", "mode": "inline_right",
                          "regex": r"RATE\s*[:\-=@]?\s*(?:1\s*[A-Z]{3}\s*=\s*)?(?:INR|RS\.?)?\s*(\d+(?:\.\d+)?)"},
        "shipping_bill_no": {"label": r"SHIPPING\s*BILL\s*NO", "mode": "inline_right",
                             "regex": r"NO\.?\s*[:\-]?\s*([0-9A-Za-z/\-]{4,20})"},
        "shipping_bill_date": {"label": r"SHIPPING\s*BILL\s*DATE|S\.?\s*B\.?\s*DATE", "mode": "inline_right",
                               "regex": r"DATE\s*[:\-]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})"},
    },
    "items": {
        # role -> header patterns. Order of this dict = matching priority (specific first).
        "columns": {
            "rate_per_piece": [r"RATE.*PER\s*(PIECE|PCS?|PACK|UNIT)\b"],
            "rate_per_carton": [r"RATE.*(/|PER)\s*(CTN|CARTON|BOX)"],
            "packs_per_carton": [r"PACKS?\S*\s*(IN|PER)\s*C(TN|ARTON)", r"PCS\s*(IN|PER)\s*C(TN|ARTON)"],
            "cartons": [r"NO\.?\s*OF\s*(BOX|BOXES|CTN|CTNS|CARTON|CARTONS)\b", r"^\s*(BOXES|CARTONS|CTNS)\s*$"],
            "pack_size": [r"KIND\s*OF\s*PACKAGE", r"PACK\s*SIZE", r"^\s*(GMS|GRAMS)\s*$"],
            "sl_no": [r"^\s*SR\.?\s*(NO\.?)?\s*$", r"^\s*S\.?\s*NO\.?\s*$", r"^\s*SL\.?\s*NO\.?\s*$", r"^\s*#\s*$"],
            "hsn": [r"\bHSN\b", r"\bHS\s*CODE\b", r"\bITC\s*HS\b"],
            "description": [r"DESCRIPTION", r"PARTICULARS"],
            "gst_rate": [r"GST\s*RATE", r"^\s*I?GST\s*(%|\(%\)|RATE)", r"RATE\s*OF\s*(TAX|GST|IGST)"],
            "igst": [r"^\s*I?GST(\s*(AMT|AMOUNT|VALUE))?(\s*\(?\s*INR\s*\)?)?\s*$"],
            "cgst": [r"^\s*CGST(\s*(AMT|AMOUNT))?\s*$"],
            "sgst": [r"^\s*SGST(\s*(AMT|AMOUNT))?\s*$"],
            "cess": [r"^\s*CESS"],
            "discount": [r"DISCOUNT"],
            "taxable_value": [r"TAXABLE"],
            "net_weight": [r"NET\s*(WEIGHT|WT)"],
            "gross_weight": [r"GROSS\s*(WEIGHT|WT)"],
            "qty": [r"^\s*QTY", r"QUANTITY"],
            "uqc": [r"^\s*UNIT\s*$", r"\bUOM\b", r"\bUQC\b"],
            "rate": [r"^\s*(FOB\s*)?RATE\b", r"UNIT\s*PRICE", r"PRICE"],
            "amount": [r"^\s*AMOUNT", r"^\s*(TOTAL\s*)?VALUE\b", r"TOTAL\s*AMOUNT", r"\bFOB\s*(VALUE|AMOUNT)"],
        },
        "stop_labels": [r"^\s*TOTAL\b", r"AMOUNT\s*IN\s*WORDS", r"^\s*ORIGIN\b", r"NET\s*WT",
                        r"DECLARATION", r"^\s*GRAND\s*TOTAL"],
        "max_blank_rows": 15,
    },
    "conversion": {
        "quantity_basis": "", "uqc": "", "buyer_party": "", "doc_type": "Tax Invoice",
        "dayfirst": True, "port_code": "", "port_source_text": "", "supplier_refund": "",
        "tolerance_inr": "1.00", "tolerance_fc": "0.05", "write_mode": "replace",
        "round_off": False, "buyer_location": "",
    },
    "signature": {},
}

QUANTITY_BASES = {
    "cartons": "No. of boxes/cartons (source column), rate per carton",
    "packs": "Consumer packs = boxes x packs per carton, rate per piece",
    "net_kg_computed": "Net kg = boxes x packs per carton x pack grams / 1000 (derived)",
    "net_kg_packing": "Net kg from PACKING LIST 'Net Weight' column",
    "source_qty": "Quantity column printed on the invoice",
}
