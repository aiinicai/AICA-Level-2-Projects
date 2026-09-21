"""Conversion engine: source invoice -> NIC eInvoice/Items records, with validation.

Design rule throughout: when a value is not on the invoice and cannot be derived by a
deterministic rule, it is left blank and a RED (blocking) or AMBER (confirm) issue is
raised. Nothing is invented."""
from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal
from pathlib import Path

from .logsetup import get_logger
from .mapping import EINVOICE_CODES, ITEMS_CODES, SOURCE_RULE
from .masters import Masters, load_masters
from .models import (AMBER, GREEN, RED, ConversionOptions, ConversionResult, Issues, MappedField, Party,
                     SourceInvoice, SourceValue, Supplier)
from .nic_template import TemplatePackage, verify_nic_file, write_nic_file
from .source_reader import SourceReader
from .util import clean_text, fmt, gstin_check, parse_date, q, safe_filename, to_decimal

log = get_logger()
ZERO = Decimal("0")
NIC_DOCNO = re.compile(r"^[1-9A-Za-z][0-9A-Za-z/-]{0,15}$")      # from template VBA RegDocno
NIC_TEXT_BAD = re.compile(r'["\\]')                               # template RegLoc/RegAdd reject these
SB_CHARS = re.compile(r"^[ A-Za-z0-9\-/.]{1,20}$")               # template AlphaNumeric + length check
HSN_RE = re.compile(r"^(?!0+$)([0-9]{4}|[0-9]{6}|[0-9]{8})$")
ALLOWED_GST_RATES = {Decimal(x) for x in ("0", "0.1", "0.25", "1.5", "3", "5", "7.5", "12", "18", "28", "40")}
DOMESTIC_SUPPLY_TYPES = {"B2B", "SEZWP", "SEZWOP", "DEXP"}
EXPORT_SUPPLY_TYPES = {"EXPWP", "EXPWOP"}    # from template VBA RegPhsn
PROFILE_CTRL = {"gstin": "txtGstin", "legal_name": "txtLegal", "trade_name": "txtTrade", "address1": "txtAdd1",
                "address2": "txtAdd2", "location": "txtLoc", "state": "ddState", "pin": "txtPin",
                "phone": "txtPhone", "email": "TxtEmail"}


class Engine:
    def __init__(self, template_path: str | Path):
        self.template = Path(template_path)
        pkg = TemplatePackage(self.template)
        try:
            self.e_codes, self.e_labels, _ = pkg.header_codes("eInvoice")
            self.i_codes, self.i_labels, _ = pkg.header_codes("Items")
            self.items_existing = pkg.data_row_count("Items", 5)
            ctrls = pkg.profile_controls()
        finally:
            pkg.close()
        self.template_profile = {k: ctrls.get(v, "") for k, v in PROFILE_CTRL.items()}
        self.masters: Masters = load_masters(self.template)
        missing = [c for c in EINVOICE_CODES if c not in self.e_codes] + \
                  [c for c in ITEMS_CODES if c not in self.i_codes]
        self.template_missing_codes = missing

    # ---------------------------------------------------------------- helpers for GUI
    def read_source(self, path, profile, ocr_exe: str = "") -> SourceInvoice:
        return SourceReader(path, profile, set(self.masters.currencies), ocr_exe).read()

    def read_sources(self, path, profile, ocr_exe: str = "") -> list[SourceInvoice]:
        """Every invoice contained in the file (a PDF may hold many; scans are read by OCR)."""
        return SourceReader(path, profile, set(self.masters.currencies), ocr_exe).read_all()

    def supplier_from_template(self) -> Supplier:
        s = Supplier()
        for k, v in self.template_profile.items():
            setattr(s, k, v or "")
        s.state_code = self.masters.states.get((s.state or "").upper(), "")
        return s

    def _country_names(self, inv) -> set:
        names = {re.sub(r"[^A-Z]", "", v.upper()) for v in self.masters.countries.values()}
        for k in ("country_final_destination", "final_destination"):
            if k in inv.fields:
                names.add(re.sub(r"[^A-Z]", "", inv.fields[k].text.upper()))
        names |= {"INDIA", "UAE", "USA", "UK", "NEWZEALAND", "NZ"}
        return names

    def party_location(self, lines: list[str], countries: set | None = None) -> str:
        """City from an address: scan from the bottom, skipping phone/e-mail lines, dropping a
        trailing country name, ZIP/PIN digits, a two-letter state code next to a ZIP, and
        street-type words."""
        skip_line = re.compile(r"\b(MOB|MOBILE|TEL|PHONE|PH|FAX|CELL|E-?MAIL|CONTACT|ATTN)\b|@", re.I)
        street = re.compile(r"\b(ROAD|RD|STREET|ST|AVENUE|AVE|DRIVE|FLOOR|OFFICE|BUILDING|BLDG|ZONE|ZON|"
                            r"SUITE|UNIT|LANE|BLVD|PLOT|BOX)\b", re.I)
        for ln in reversed(lines):
            if skip_line.search(ln):
                continue
            for tok in reversed([t for t in re.split(r"[,;]|\.\s|\s{2,}", ln) if t.strip()]):
                if street.search(tok) or re.search(r"P\.?\s*O\.?\s*BOX", tok, re.I):
                    continue
                words = re.findall(r"[A-Za-z][A-Za-z'.\-]*", tok)
                for size in (4, 3, 2, 1):                       # drop a trailing country name
                    if len(words) >= size and self.masters.is_exact_country(" ".join(words[-size:])):
                        words = words[:-size]
                        break
                if re.search(r"\d", tok):                       # 'CUMMING GA 30041' -> drop the state code
                    while words and len(words[-1].strip(".")) <= 2:
                        words.pop()
                city = " ".join(words).strip(" .-")
                if city.upper() in self.masters.states:      # 'Surat, Gujarat' -> the city, not the State
                    continue
                if len(re.sub(r"[^A-Za-z]", "", city)) >= 3 and not self.masters.is_exact_country(city):
                    return city
        return ""

    # ================================================================ AUTOMATIC MODE
    def auto_supplier(self, inv: SourceInvoice, saved: Supplier | None = None) -> tuple[Supplier, list]:
        """Supplier from the invoice's EXPORTER block and GSTIN; gaps filled from the NIC template
        Profile, then from any saved override. Returns (supplier, notes)."""
        notes = []
        s = Supplier()
        ex = inv.exporter_block
        g = inv.fields.get("exporter_gstin")
        if g and g.text:
            s.gstin = g.text.upper()
        s.legal_name = ex.name
        lines = list(ex.lines)
        pin_line = next((ln for ln in lines if re.search(r"\b[1-9][0-9]{5}\b", ln)), "")
        if pin_line:
            s.pin = re.search(r"\b[1-9][0-9]{5}\b", pin_line).group(0)
            toks = [t.strip(" .") for t in pin_line.split(",") if t.strip(" .")]
            for t in toks:
                if t.upper() in self.masters.states:
                    s.state = t.upper()
            s.location = next((t for t in toks if not re.search(r"\d", t) and t.upper() not in self.masters.states
                               and t.upper() not in {"INDIA"}), "")
        addr = [ln for ln in lines]
        if addr:
            s.address1 = addr[0][:100]
            s.address2 = ", ".join(addr[1:])[:100]
        if not s.legal_name and inv.all_text:
            texts = [t for _, t in inv.all_text]
            gi = next((i for i, t in enumerate(texts) if re.search(r"GSTIN|GST\s*NO", t, re.I)), None)
            head = [t for t in texts[:gi][:4] if len(t) > 3 and not re.search(r"TAX\s*INVOICE|^INVOICE\b", t, re.I)] if gi else []
            if head:
                s.legal_name = head[0][:100]
                rest = head[1:]
                if rest:
                    s.address1 = rest[0][:100]
                    s.address2 = ", ".join(rest[1:])[:100]
                pin_line = next((ln for ln in head if re.search(r"\b[1-9][0-9]{5}\b", ln)), "")
                if pin_line:
                    s.pin = re.search(r"\b[1-9][0-9]{5}\b", pin_line).group(0)
                    toks = [t.strip(" .") for t in pin_line.split(",") if t.strip(" .")]
                    for t in toks:
                        if t.upper() in self.masters.states:
                            s.state = t.upper()
                    s.location = next((t for t in toks if not re.search(r"\d", t) and t.upper() not in self.masters.states
                                       and t.upper() not in {"INDIA"}), "")
                notes.append((AMBER, "Supplier", f"Supplier details read from the top of the invoice ('{s.legal_name}')."))
        tp = self.supplier_from_template()
        src = []
        for k in ("gstin", "legal_name", "address1", "location", "state", "pin", "phone", "email", "trade_name"):
            if not getattr(s, k) and getattr(tp, k):
                setattr(s, k, getattr(tp, k)); src.append(k)
        if saved:
            for k in vars(saved):
                if getattr(saved, k) and not getattr(s, k):
                    setattr(s, k, getattr(saved, k))
        if s.gstin and not s.state:
            s.state = next((n for n, c in self.masters.states.items() if c == s.gstin[:2]), "")
        s.state_code = self.masters.states.get(s.state.upper(), "") if s.state else ""
        if src:
            notes.append((AMBER, "Supplier", "Not printed on invoice, taken from NIC template Profile: " + ", ".join(src)))
        return s, notes

    def auto_options(self, inv: SourceInvoice, app_settings: dict | None = None) -> ConversionOptions:
        """Derives every conversion input from the invoice itself. Each automatic decision is
        recorded in opt.auto_notes so it appears in the report."""
        st = app_settings or {}
        m = self.masters
        o = ConversionOptions()
        N = o.auto_notes
        f = inv.fields
        text = " | ".join(t.upper() for _, t in inv.all_text)

        # --- document type (debit / credit notes are recognised, not assumed to be invoices)
        head = " | ".join(t.upper() for _, t in inv.all_text[:40])
        if re.search(r"\bDEBIT\s*NOTE\b", head):
            o.doc_type = "Debit Note"
            N.append((AMBER, "Document Type", "Read as a DEBIT NOTE from the heading."))
        elif re.search(r"\bCREDIT\s*NOTE\b", head):
            o.doc_type = "Credit Note"
            N.append((AMBER, "Document Type", "Read as a CREDIT NOTE from the heading."))

        # --- buyer GSTIN: a GSTIN other than the supplier's belongs to the recipient
        gstins = []
        for _, t in inv.all_text:
            for g in re.findall(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}\b", t.upper()):
                if g not in gstins:
                    gstins.append(g)
        sup_g = (self.template_profile.get("gstin") or "").upper()
        inv_g = inv.fields.get("exporter_gstin", SourceValue()).text.upper()
        buyer_g = next((g for g in gstins if g not in {sup_g, inv_g}), "")
        if not buyer_g and len(gstins) > 1:
            buyer_g = gstins[1]
        o.buyer_gstin = buyer_g

        # --- currency: what is actually printed on the invoice
        money_text = text
        inr_marks = bool(re.search(r"\u20b9|\bRS\.?\b|\bINR\b|RUPEES|\(cid:", money_text))
        foreign = {}
        for code, pat in (("USD", r"\bUSD\b|\bUS\$|\$"), ("EUR", r"\bEUR\b|EURO|\u20ac"), ("GBP", r"\bGBP\b|\u00a3"),
                          ("AED", r"\bAED\b|DIRHAM"), ("AUD", r"\bAUD\b"), ("CAD", r"\bCAD\b"),
                          ("SGD", r"\bSGD\b"), ("JPY", r"\bJPY\b|\u00a5")):
            if re.search(pat, money_text) and code in m.currencies:
                foreign[code] = True
        if not inv.currency.value:
            if len(foreign) == 1:
                code = next(iter(foreign))
                inv.currency = SourceValue(code, "invoice text", "currency symbol/word printed on the invoice")
            elif inr_marks and not foreign:
                inv.currency = SourceValue("INR", "invoice text", "rupee symbol / 'Rs.' printed on the invoice")

        # --- evidence of an export
        export_words = re.search(r"\bLUT\b|LETTER\s+OF\s+UNDERTAKING|WITHOUT\s+PAYMENT\s+OF\s+(IGST|TAX)|"
                                 r"WITH\s+PAYMENT\s+OF\s+(IGST|TAX)|ZERO\s*RATED|EXPORT\b|SHIPPING\s*BILL|"
                                 r"PORT\s*OF\s*(LOADING|DISCHARGE)|BILL\s*OF\s*LADING", text)
        foreign_cur = bool(inv.currency.text and inv.currency.text != "INR")
        buyer_country = ""
        for key in ("country_final_destination", "final_destination"):
            if key in f:
                cands = m.country_candidates(f[key].text)
                if cands:
                    buyer_country = cands[0][0]
        foreign_buyer = bool(buyer_country and buyer_country != "IN")
        evidence = [x for x in ("wording" if export_words else "", "foreign currency" if foreign_cur else "",
                                "foreign destination" if foreign_buyer else "") if x]

        if buyer_g and not evidence:
            o.transaction_type = "Domestic"
            bstate = next((n for n, c in m.states.items() if c == buyer_g[:2]), "")
            N.append((AMBER, "Buyer GSTIN", f"Buyer GSTIN {buyer_g} found on the invoice - domestic supply to "
                                            f"{bstate or 'state ' + buyer_g[:2]}."))
        elif evidence:
            o.transaction_type = "Export"
            if buyer_g:
                N.append((AMBER, "Transaction Type", f"The invoice shows export wording and also a buyer GSTIN "
                                                     f"({buyer_g}); treated as an export - correct it on the check "
                                                     "screen if it is a domestic or SEZ supply."))
        elif (to_decimal(f["tax_cgst"].value) if "tax_cgst" in f else None) or \
             (to_decimal(f["tax_sgst"].value) if "tax_sgst" in f else None):
            o.transaction_type = "Domestic"
            N.append((AMBER, "Transaction Type", "CGST/SGST is charged, so this is treated as a domestic supply."))
        elif inv.currency.text == "INR" or inr_marks:
            o.transaction_type = "Domestic"
            N.append((AMBER, "Transaction Type", "Amounts are in rupees and nothing points to an export, so this is "
                                                 "treated as a domestic supply. Change it on the check screen if wrong."))
        else:
            o.transaction_type = "Unknown"
            N.append((RED, "Transaction Type", "The transaction type could not be determined from the invoice - there "
                                               "is no export wording, foreign currency, foreign destination or buyer "
                                               "GSTIN. Choose it on the check screen."))
        if o.transaction_type == "Domestic" and inv.currency.text in ("", "INR"):
            o.exchange_rate, o.exchange_rate_source = Decimal("1"), "Domestic invoice in INR"
            if not inv.currency.value:
                inv.currency = SourceValue("INR", "assumed", "domestic invoice - amounts taken as INR")

        # --- supply type follows from the classification
        igst_sum = sum((it.num("igst") or ZERO) for it in inv.items) if "igst" in inv.columns else ZERO
        printed_igst = to_decimal(f["tax_igst"].value) if "tax_igst" in f else None
        if o.transaction_type == "Domestic":
            o.supply_type = "B2B"
        elif o.transaction_type == "Export":
            if re.search(r"WITH\s+PAYMENT\s+OF\s+(IGST|TAX)|IGST\s*REFUND", text) or igst_sum > 0 or (printed_igst or ZERO) > 0:
                o.supply_type = "EXPWP"
                o.supplier_refund = "Yes" if "REFUND" in text else ""
                N.append((AMBER, "Export under", "EXPWP - the invoice charges IGST / mentions payment of IGST."))
            else:
                o.supply_type = "EXPWOP"
                N.append((AMBER, "Export under", "EXPWOP - the invoice mentions LUT / export without payment of IGST."))
        else:
            o.supply_type = ""

        # --- buyer
        same = not inv.notify_party.name and any("SAME AS" in ln.upper() for ln in inv.notify_party.lines)
        if not inv.consignee.name and "buyer_name" in f:
            o.buyer_party = "buyer_fields"
        elif getattr(inv, "buyer_block2", None) and inv.buyer_block2.name:
            o.buyer_party = "buyer_block2"
        elif getattr(inv, "buyer_block", None) and inv.buyer_block.name:
            o.buyer_party = "buyer_block"
        else:
            o.buyer_party = "consignee"
            if inv.notify_party.name and not same:
                N.append((AMBER, "Buyer", f"Buyer taken as Consignee '{inv.consignee.name}'; notify party "
                                          f"'{inv.notify_party.name}' is not treated as buyer."))
        # --- currency / exchange rate
        cur = inv.currency.text
        if cur == "INR":
            o.exchange_rate, o.exchange_rate_source = Decimal("1"), "Invoice amounts are in INR"
        # --- quantity & UQC
        uqc_default = st.get("default_uqc_box", "")
        if "qty" in inv.columns:
            o.quantity_basis = "source_qty"
            if "uqc" in inv.columns:
                seen = [m.unit_from_text(it.values["uqc"].value if it.values.get("uqc") else "") for it in inv.items]
                seen = [u for u in seen if u]
                if seen:
                    o.uqc = max(set(seen), key=seen.count)
                    N.append((AMBER, "GST UQC", f"Quantity and unit taken from the invoice's own columns "
                                                f"(most common unit: {o.uqc})."))
        elif "cartons" in inv.columns:
            o.quantity_basis = "cartons"
            head = inv.header_labels.get("cartons", "").upper()
            if uqc_default and uqc_default in m.unit_descriptions:
                o.uqc = uqc_default
            elif re.search(r"\bBOX", head) and "BOX" in m.unit_descriptions:
                o.uqc = "BOX"
            elif re.search(r"CTN|CARTON", head) and "CARTONS" in m.unit_descriptions:
                o.uqc = "CARTONS"
            if o.uqc:
                N.append((AMBER, "GST UQC", f"Quantity = '{inv.header_labels.get('cartons')}' column, UQC {o.uqc} "
                                            f"({m.unit_code(o.uqc)}). Change default in Settings if you report another unit."))
        # --- port
        pol = inv.fields.get("port_of_loading", SourceValue()).text
        learned = st.get("port_map", {}).get(pol.upper())
        if learned in m.ports:
            o.port_code = learned
        else:
            cands = m.port_candidates(pol)
            key = " ".join(w for w in re.findall(r"[A-Z]{3,}", pol.upper()) if w not in {"PORT", "INDIA"})
            exact = [c for c, d in cands if re.sub(r"\s+", " ", d.upper().strip()) == key]
            pick = exact[0] if len(exact) == 1 else (cands[0][0] if len(cands) == 1 else "")
            if pick:
                o.port_code = pick
                others = ", ".join(f"{c} {d}" for c, d in cands if c != pick)
                N.append((AMBER, "Port", f"Port {pick} ({m.ports[pick].strip()}) matched from '{pol}'."
                                         + (f" Other codes containing this name: {others}." if others else "")))
        # --- rate printed on the CGST/SGST/IGST lines under the table
        line_rate = None
        cg = to_decimal(f["tax_cgst_rate"].value) if "tax_cgst_rate" in f else None
        sg = to_decimal(f["tax_sgst_rate"].value) if "tax_sgst_rate" in f else None
        ig = to_decimal(f["tax_igst_rate"].value) if "tax_igst_rate" in f else None
        if o.transaction_type == "Domestic" and (f.get("tax_cgst") and to_decimal(f["tax_cgst"].value)):
            line_rate = (cg or ZERO) + (sg or ZERO)
        elif ig is not None:
            line_rate = ig
        elif cg is not None and sg is not None:
            line_rate = cg + sg
        if line_rate is not None:
            for it in inv.items:
                if it.num("gst_rate") is None:
                    o.item_gst_rates[it.sl_no] = line_rate
            N.append((AMBER, "GST Rate", f"GST rate {fmt(line_rate, 3)}% taken from the tax line printed under the "
                                         "item table."))

        # --- GST rate from invoice column, else remembered by HSN, else 0 when no tax is charged
        mem = st.get("hsn_rates", {})
        zero_used = False
        for it in inv.items:
            r = it.num("gst_rate")
            if r is not None:
                o.item_gst_rates[it.sl_no] = r
                continue
            hsn = re.sub(r"[\s.]", "", it.hsn.text)
            if hsn in mem and to_decimal(mem[hsn]) is not None:
                o.item_gst_rates[it.sl_no] = to_decimal(mem[hsn]); o.rate_from_memory.add(it.sl_no)
            elif o.supply_type == "EXPWOP":
                o.item_gst_rates[it.sl_no] = ZERO; zero_used = True
        if zero_used:
            N.append((AMBER, "GST Rate", "Invoice has no GST % column; GST rate 0 used as no tax is charged (EXPWOP). "
                                         "Add a 'GST %' column to the invoice to report the applicable rate."))
        return o

    # ---------------------------------------------------------------- analyse
    def analyse(self, inv: SourceInvoice, opt: ConversionOptions, supplier: Supplier, profile: dict) -> ConversionResult:
        res = ConversionResult(inv, opt)
        iss: Issues = res.issues
        iss.extend(inv.read_issues)
        for note in opt.auto_notes:
            lvl, fld, msg = note
            (iss.red if lvl == RED else iss.amber)(fld, msg)
        m = self.masters
        H, flog = res.header, res.field_log

        def logf(field, source, value, code_or_target, remarks=""):
            target = code_or_target
            if code_or_target in self.e_codes:
                target = f"eInvoice / {self.e_labels.get(code_or_target, code_or_target)} ({self.e_codes[code_or_target]})"
            elif code_or_target in self.i_codes:
                target = f"Items / {self.i_labels.get(code_or_target, code_or_target)} ({self.i_codes[code_or_target]})"
            flog.append(MappedField(field, source, str(value), target, "", remarks))

        if self.template_missing_codes:
            iss.red("NIC template", "The NIC template does not contain expected columns: "
                    + ", ".join(self.template_missing_codes) + ". The utility version may differ - mapping must be reviewed.")

        # ---------------- transaction
        domestic = opt.supply_type in DOMESTIC_SUPPLY_TYPES
        export_supply = opt.supply_type in EXPORT_SUPPLY_TYPES
        if not domestic and opt.supply_type not in EXPORT_SUPPLY_TYPES:
            iss.red("Export under", "The invoice does not say whether the export is with or without payment of IGST "
                                    "(add 'EXPORT UNDER LUT WITHOUT PAYMENT OF IGST' or 'EXPORT UNDER IGST REFUND').")
        elif opt.supply_type and opt.supply_type not in m.supply_types:
            iss.red("Supply Type", f"'{opt.supply_type}' is not in the NIC Supply master of this template.")
        elif not opt.supply_type:
            iss.red("Supply Type", "Supply type not determined - choose it on the check screen (B2B, EXPWP, EXPWOP...).")
        H["colSupType"] = opt.supply_type
        H["colRevCharge"] = opt.reverse_charge or "No"
        H["colIgstIntra"] = opt.igst_on_intra or "No"
        logf("Supply Type", "User selection", opt.supply_type, "colSupType")
        logf("Reverse Charge", "User selection", H["colRevCharge"], "colRevCharge")
        logf("IGST on Intra", "User selection", H["colIgstIntra"], "colIgstIntra")
        self._validate_transaction_flags(opt, supplier, iss)

        # ---------------- supplier (lives in the NIC utility's Profile sheet, not in eInvoice rows)
        self._check_supplier(supplier, inv, iss, logf)

        # ---------------- document
        if opt.doc_type in {"Debit Note", "Credit Note"}:
            neg = any(re.search(r"\bMINUS\b|^-", (it.description.text + " " +
                      str((it.values.get("amount") or it.values.get("taxable_value") or SourceValue()).value or "")).upper())
                      for it in inv.items)
            if neg:
                iss.red("Document Type", f"This is a {opt.doc_type} carrying a negative amount. A {opt.doc_type} must "
                                         "report positive values on the portal (a reduction is reported through a credit "
                                         "note), so it has not been converted.")
        if opt.doc_type not in m.doc_types:
            iss.red("Document Type", f"Document type '{opt.doc_type}' is not in the NIC Doctype master.")
        H["colDoctype"] = opt.doc_type
        logf("Document Type", "Mapping profile", opt.doc_type, "colDoctype")

        f = inv.fields
        docno = f.get("invoice_no", SourceValue()).text
        if not docno:
            iss.red("Invoice Number", "Invoice number not found on the invoice (label 'INVOICE NO').")
        elif not NIC_DOCNO.match(docno):
            iss.red("Invoice Number", f"'{docno}' does not meet NIC document-number rules (max 16 characters; letters, "
                                      "digits, '/' and '-' only; cannot start with 0, '/' or '-').")
        H["colDocno"] = docno
        logf("Invoice Number", f.get("invoice_no", SourceValue()).where(), docno, "colDocno")

        dsv = f.get("invoice_date", SourceValue())
        d, ambiguous = parse_date(dsv.value, opt.dayfirst)
        res.doc_date = d
        if dsv.formula_uncached:
            pass
        elif not dsv.text:
            iss.red("Invoice Date", "Invoice date not found on the invoice.")
        elif d is None:
            iss.red("Invoice Date", f"Invoice date '{dsv.text}' could not be read as a valid date.")
        else:
            if d > dt.date.today():
                iss.red("Invoice Date", f"Invoice date {d:%d/%m/%Y} is in the future - the NIC utility rejects future dates.")
            if not 2010 <= d.year <= 2029:
                iss.red("Invoice Date", "The NIC utility accepts document years 2010-2029 only.")
            if d < dt.date(2020, 10, 1):
                iss.red("Invoice Date", "E-invoice requests for document dates before 01/10/2020 are not accepted.")
            if opt.reporting_30d_applies and (dt.date.today() - d).days > 30:
                iss.red("30-day reporting", "Invoice is more than 30 days old. For taxpayers covered by the current 30-day reporting restriction, IRP reporting is not permitted after 30 days.")
            elif opt.reporting_30d_applies and (dt.date.today() - d).days > 25:
                iss.amber("30-day reporting", "Invoice is approaching the 30-day reporting limit. Confirm reporting within time.")
            fy = re.search(r"(\d{2})-(\d{2})$", docno or "")
            if fy and int(fy.group(2)) == (int(fy.group(1)) + 1) % 100:
                start = dt.date(2000 + int(fy.group(1)), 4, 1)
                if not start <= d <= dt.date(start.year + 1, 3, 31):
                    iss.amber("Invoice Date", f"Date {d:%d/%m/%Y} falls outside financial year {fy.group(0)} suggested by the invoice number.")
        H["colDocdate"] = d.strftime("%d/%m/%Y") if d else ""
        logf("Invoice Date", dsv.where(), H["colDocdate"], "colDocdate", "day-first" if opt.dayfirst else "month-first")

        # ---------------- buyer / ship-to
        self._buyer(inv, opt, iss, H, logf)

        # ---------------- export / domestic details
        if domestic:
            H["colForCur"] = ""
            if not opt.exchange_rate:
                opt.exchange_rate, opt.exchange_rate_source = Decimal("1"), "Domestic invoice in INR"
        else:
            self._export_details(inv, opt, profile, iss, H, logf)

        # ---------------- exchange rate
        rate = opt.exchange_rate
        if rate is None:
            er = f.get("exchange_rate")
            if er and to_decimal(er.value):
                rate = to_decimal(er.value)
                opt.exchange_rate, opt.exchange_rate_source = rate, er.cell
                iss.amber("Exchange Rate", f"Exchange rate {rate} read from the invoice at {er.cell}. Confirm it is the rate "
                                           "applicable for GST valuation of this supply.")
        if rate is None or rate <= 0:
            iss.red("Exchange Rate", f"Invoice is in {inv.currency.text or 'foreign currency'} and shows no exchange rate. "
                                     "Type 'EXCHANGE RATE : 83.50' (your rate) in any cell of the invoice, or enter it when prompted.")
            rate = None
        logf("Exchange Rate", opt.exchange_rate_source or "User input", rate or "", "Used for INR conversion (not a NIC column)")

        # ---------------- items
        self._items(inv, opt, rate, iss, res, logf, supplier)

        # ---------------- totals & reconciliation
        self._totals(inv, opt, rate, iss, res, logf)

        # ---------------- final offline business-rule checks + exact JSON schema preflight
        self._offline_business_checks(inv, opt, supplier, res, iss)
        try:
            from .nic_json import build_json
            from .json_validator import validate_documents
            schema_errors = validate_documents(build_json(res, supplier, self.masters))
            for msg in schema_errors:
                iss.red("JSON Schema 1.1", msg)
        except Exception as e:
            iss.red("JSON Schema 1.1", f"Offline JSON Schema validator could not run: {type(e).__name__}: {e}")

        # ---------------- structure change detection
        sig = profile.get("signature") or {}
        if sig:
            diffs = []
            if sig.get("invoice_sheet") != inv.signature.get("invoice_sheet"):
                diffs.append(f"invoice sheet '{sig.get('invoice_sheet')}' -> '{inv.signature.get('invoice_sheet')}'")
            for role, col in sig.get("columns", {}).items():
                now = inv.signature["columns"].get(role)
                if now != col:
                    diffs.append(f"column '{role}' {col} -> {now or 'missing'}")
            for role in inv.signature["columns"]:
                if role not in sig.get("columns", {}):
                    diffs.append(f"new column '{role}'")
            for role, lab in sig.get("header_labels", {}).items():
                if role in inv.signature["header_labels"] and inv.signature["header_labels"][role] != lab:
                    diffs.append(f"heading of '{role}' changed")
            if diffs:
                iss.amber("Source format", "The source invoice structure appears to have changed. Please review the mapping. ("
                          + "; ".join(diffs[:8]) + ")")

        # field-log status = worst issue raised for that field
        rank = {GREEN: 0, AMBER: 1, RED: 2}
        worst: dict[str, str] = {}
        for i in iss:
            if i.item_no is None:
                worst[i.field] = max(worst.get(i.field, GREEN), i.level, key=rank.get)
        for mf in flog:
            mf.status = worst.get(mf.field, GREEN)
            if mf.status != GREEN and not mf.remarks:
                mf.remarks = "; ".join(i.message for i in iss if i.field == mf.field and i.item_no is None)[:250]
        return res

    # ---------------------------------------------------------------- offline IRP/GST rules
    def _validate_transaction_flags(self, opt: ConversionOptions, supplier: Supplier, iss: Issues):
        st = (opt.supply_type or "").upper()
        rcm = (opt.reverse_charge or "No").strip().upper()
        igi = (opt.igst_on_intra or "No").strip().upper()
        if rcm not in {"YES", "NO", "Y", "N"}:
            iss.red("Reverse Charge", "Reverse Charge must be Yes/No.")
        elif rcm in {"YES", "Y"} and st not in {"B2B", "SEZWP", "SEZWOP"}:
            iss.red("Reverse Charge", f"Reverse Charge is not applicable for supply type {st}.")
        if igi not in {"YES", "NO", "Y", "N"}:
            iss.red("IGST on Intra", "IGST on Intra-State must be Yes/No.")
        elif igi in {"YES", "Y"} and st not in {"B2B"}:
            iss.red("IGST on Intra", "IGST on Intra-State is permitted only for applicable B2B transactions; it cannot be used for exports/SEZ/deemed exports.")
        if igi in {"YES", "Y"} and rcm not in {"YES", "Y"}:
            iss.red("IGST on Intra", "When IGST on Intra-State is selected, Reverse Charge must also be Yes where required by IRP validation.")

    def _offline_business_checks(self, inv, opt, supplier, res, iss: Issues):
        # GSTIN equality and state/POS relationship
        sg = (supplier.gstin or "").strip().upper()
        bg = (res.header.get("colBgstin") or opt.buyer_gstin or "").strip().upper()
        if sg and bg and bg != "URP" and sg == bg:
            iss.red("Buyer GSTIN", "Supplier GSTIN and Buyer GSTIN cannot be the same.")
        supplier_state = supplier.state_code.zfill(2) if supplier.state_code else (sg[:2] if len(sg) >= 2 else "")
        buyer_state = (res.header.get("colBState") or "").strip().upper()
        buyer_code = self.masters.states.get(buyer_state, "") or ((bg[:2] if len(bg) >= 2 and bg != "URP" else "96"))
        pos_code = self.masters.states.get((res.header.get("colPos") or "").strip().upper(), "") or ("96" if bg == "URP" else "")
        if bg != "URP" and bg and len(bg) == 15 and supplier_state and bg[:2] != buyer_code.zfill(2):
            iss.red("Buyer GSTIN", "Buyer GSTIN state code does not match the buyer state/POS.")
        if opt.supply_type in {"EXPWP", "EXPWOP"}:
            if bg != "URP":
                iss.red("Buyer GSTIN", "Export recipient must be URP in the e-Invoice JSON.")
            if pos_code != "96":
                iss.red("Buyer POS", "Export recipient POS must be 96.")
        elif bg == "URP":
            iss.red("Buyer GSTIN", f"URP is not permitted for supply type {opt.supply_type}.")
        if supplier_state and pos_code and opt.supply_type in DOMESTIC_SUPPLY_TYPES and pos_code == "96":
            iss.red("Buyer POS", "Domestic/SEZ/deemed-export transaction cannot have foreign POS 96.")

        # Item count / duplicate serials / GST rates
        if not res.items:
            iss.red("Line items", "At least one item is required.")
        if len(res.items) > 1000:
            iss.red("Line items", "Maximum 1000 line items are permitted.")
        sl = [str(r.get("colProdSlno", "")).strip() for r in res.items]
        dup = sorted({x for x in sl if x and sl.count(x) > 1})
        if dup:
            iss.red("Item Sl.No.", "Duplicate item serial number(s): " + ", ".join(dup) + ".")

        for r in res.items:
            try:
                rate = Decimal(str(r.get("colGstrate", "")))
            except Exception:
                rate = None
            if rate is not None and rate not in ALLOWED_GST_RATES:
                iss.red("GST Rate", f"GST rate {rate}% is not in the offline configured notified GST rate master. Update the local rate master if a later notified rate applies.", int(r.get("colProdSlno") or 0) or None)

        # PIN/state consistency
        for label, pin, state_name in (("Supplier PIN", supplier.pin, supplier.state),
                                       ("Buyer PIN", res.header.get("colBPin", ""), res.header.get("colBState", "")),
                                       ("Ship-to PIN", res.header.get("colSPin", ""), res.header.get("colSState", ""))):
            if not pin or str(pin) == "999999" or not state_name or state_name == "OTHER COUNTRIES":
                continue
            p = re.sub(r"\D", "", str(pin))
            if not re.fullmatch(r"[1-9][0-9]{5}", p):
                iss.red(label, f"{label} must be a valid 6-digit Indian PIN.")
            else:
                # Offline PIN master is intentionally optional; use the well-known first-3-digit routing fallback only if available.
                pin3 = int(p[:3])
                expected = self._pin_state_fallback(pin3)
                state_code = self.masters.states.get(str(state_name).upper(), "")
                if expected and state_code and expected != state_code:
                    iss.red(label, f"PIN {p} does not map to State {state_name} under the offline PIN-State master.")

        # CGST/SGST equality and tax applicability from generated values
        cg = sum((to_decimal(r.get("colCgst")) or ZERO) for r in res.items)
        sg = sum((to_decimal(r.get("colSgst")) or ZERO) for r in res.items)
        ig = sum((to_decimal(r.get("colIgst")) or ZERO) for r in res.items)
        if abs(cg - sg) > Decimal("0.01"):
            iss.red("Tax totals", "Total CGST and SGST must be equal for applicable intra-State supplies.")
        if opt.supply_type in {"EXPWP", "EXPWOP"} and (cg > 0 or sg > 0):
            iss.red("Tax totals", "Exports must not carry CGST/SGST in the e-Invoice JSON.")
        if opt.supply_type == "EXPWOP" and ig > 0:
            iss.red("Tax totals", "EXPWOP must not carry IGST.")
        if opt.supply_type == "EXPWP" and ig <= 0 and res.items:
            iss.red("Tax totals", "EXPWP requires IGST where taxable items are present.")
        if opt.igst_on_intra.upper() in {"YES", "Y"} and ig <= 0 and res.items:
            iss.red("IGST on Intra", "IGST on Intra-State is selected but no IGST is calculated.")

    @staticmethod
    def _pin_state_fallback(pin3: int) -> str:
        # Conservative first-three-digit fallback. Return empty when no reliable mapping is known.
        ranges = [
            (110, 129, "07"), (130, 160, "06"), (170, 179, "02"), (180, 194, "01"),
            (200, 229, "09"), (230, 249, "09"), (250, 285, "09"), (300, 342, "08"),
            (360, 396, "24"), (400, 449, "27"), (450, 488, "23"), (490, 497, "22"),
            (500, 509, "36"), (510, 599, "29"), (600, 643, "33"), (670, 695, "32"),
            (700, 743, "19"), (744, 744, "35"), (750, 799, "21"), (800, 855, "10"),
            (860, 899, "10"), (900, 999, ""),
        ]
        for lo, hi, code in ranges:
            if lo <= pin3 <= hi:
                return code
        return ""

    # ---------------------------------------------------------------- sections
    def _check_supplier(self, s: Supplier, inv, iss: Issues, logf):
        if not s.gstin.strip():
            iss.red("Supplier GSTIN", "Supplier GSTIN is required for e-Invoice generation.")
        else:
            ok, why = gstin_check(s.gstin)
            if not ok:
                iss.red("Supplier GSTIN", f"Supplier GSTIN '{s.gstin}': {why}.")
            elif s.state_code and s.gstin[:2] != s.state_code.zfill(2):
                iss.red("Supplier GSTIN", f"GSTIN state code {s.gstin[:2]} does not match supplier state code {s.state_code}.")
        for attr, label in (("legal_name", "Supplier Legal Name"), ("address1", "Supplier Address"),
                            ("location", "Supplier Location"), ("state", "Supplier State"), ("pin", "Supplier PIN Code")):
            if not getattr(s, attr).strip():
                iss.red(label, f"{label} is missing in Supplier Settings.")
        if s.pin and not re.fullmatch(r"[1-9][0-9]{5}", s.pin.strip()):
            iss.red("Supplier PIN Code", "Supplier PIN must be a 6-digit Indian PIN code.")
        if s.state and s.state.upper() not in self.masters.states:
            iss.red("Supplier State", f"Supplier state '{s.state}' is not in the NIC state master.")
        tp = self.template_profile.get("gstin", "")
        if not tp:
            iss.amber("Supplier GSTIN", "Could not read the GSTIN from the NIC template's Profile sheet. The NIC utility "
                                        "takes seller details from its own Profile sheet - confirm it matches Supplier Settings.")
        elif s.gstin and tp.upper() != s.gstin.strip().upper():
            iss.amber("Supplier GSTIN", f"This invoice is of GSTIN {s.gstin}, while the NIC utility you have set up "
                                        f"carries {tp}. The JSON produced here is correct for {s.gstin}; if you want to "
                                        "use the NIC utility route as well, open that client's own copy of it.")
        src = inv.fields.get("exporter_gstin")
        if src and src.text:
            if s.gstin and src.text.upper() != s.gstin.strip().upper():
                iss.red("Supplier GSTIN", f"Invoice prints exporter GSTIN {src.text} ({src.cell}) which differs from Supplier Settings.")
        logf("Supplier GSTIN", "Supplier Settings", s.gstin,
             "NIC 'Profile' sheet (seller details are held in the utility, not in eInvoice rows)",
             f"NIC Profile GSTIN read from template: {tp or 'not readable'}")
        logf("Supplier Legal Name", "Supplier Settings", s.legal_name, "NIC 'Profile' sheet")

    def _buyer(self, inv: SourceInvoice, opt: ConversionOptions, iss: Issues, H, logf):
        domestic = opt.transaction_type == "Domestic"
        choice = {"consignee": inv.consignee, "notify_party": inv.notify_party,
                  "buyer_block": getattr(inv, "buyer_block", None),
                  "buyer_block2": getattr(inv, "buyer_block2", None)}.get(opt.buyer_party)
        label = {"consignee": "Consignee", "notify_party": "Notify Party", "buyer_block": "Buyer block",
                 "buyer_block2": "Buyer details block",
                 "buyer_fields": "Buyer details"}.get(opt.buyer_party, "Buyer")
        if opt.buyer_party == "buyer_fields":
            choice = self.buyer_from_fields(inv)
        if choice is None or not (choice.name or choice.lines):
            iss.red("Buyer", "The buyer could not be identified on the invoice (no Consignee / Buyer / Company block).")
            return
        if not choice.name:
            iss.red("Buyer Legal Name", f"{label} name not found on the invoice.")
        elif not 3 <= len(choice.name) <= 100 or NIC_TEXT_BAD.search(choice.name):
            iss.red("Buyer Legal Name", f"{label} name must be 3-100 characters without \" or \\ (NIC rule).")
        H["colBLegalname"] = choice.name
        addr_text = " ".join(choice.lines)
        addr1 = choice.lines[0] if choice.lines else ""
        addr2 = ", ".join(choice.lines[1:])
        if not addr1:
            iss.red("Buyer Address", f"{label} address not found on the invoice.")
        for v, nm in ((addr1, "line 1"), (addr2, "line 2")):
            if len(v) > 100:
                iss.red("Buyer Address", f"Buyer address {nm} exceeds 100 characters (NIC limit) - shorten it.")
            if NIC_TEXT_BAD.search(v):
                iss.red("Buyer Address", f"Buyer address {nm} contains \" or \\ which the NIC utility rejects.")
        loc = opt.buyer_location.strip() or self.party_location(choice.lines)
        loc_src = "User override" if opt.buyer_location.strip() else f"{choice.cell} (city in address)"
        if not 3 <= len(loc) <= 100:
            tail = [t.strip(" .") for t in re.split(r"[,;]", addr_text) if t.strip(" .")]
            loc = tail[-1][:100] if tail else ""
            loc_src = f"{choice.cell} (address)"
            if 3 <= len(loc) <= 100:
                iss.amber("Buyer Location", f"No city is printed in the buyer's address, so '{loc}' was used as the "
                                            "location. Print the buyer's city on the invoice if a city is needed.")
            else:
                iss.red("Buyer Location", "Buyer location (city) could not be read from the address.")
        if domestic:
            gst = opt.buyer_gstin
            ok, why = gstin_check(gst)
            if not ok:
                iss.red("Buyer GSTIN", f"Buyer GSTIN on the invoice is not valid: {why}.")
            state = next((n for n, c in self.masters.states.items() if c == gst[:2]), "")
            pin = re.search(r"\b[1-9][0-9]{5}\b", opt.buyer_pin or addr_text)
            if not state:
                iss.red("Buyer State", f"State code {gst[:2]} of the buyer GSTIN is not in the NIC state master.")
            if not pin:
                iss.red("Buyer PIN", "Buyer PIN code is mandatory for a domestic supply and is not printed in the "
                                     "buyer's address on the invoice.")
            H.update({"colBgstin": gst, "colPos": state, "colBaddr1": addr1, "colBaddr2": addr2, "colBLoc": loc,
                      "colBPin": pin.group(0) if pin else "", "colBState": state})
            logf("Buyer GSTIN", f"Invoice ({choice.cell})", gst, "colBgstin")
            logf("Buyer POS", "Buyer GSTIN state", state, "colPos")
        else:
            H.update({"colBgstin": "URP", "colPos": "OTHER COUNTRIES", "colBaddr1": addr1, "colBaddr2": addr2,
                      "colBLoc": loc, "colBPin": (opt.buyer_pin or "999999"), "colBState": "OTHER COUNTRIES"})
            logf("Buyer GSTIN", "Rule (export)", "URP", "colBgstin")
            logf("Buyer POS", "Rule (export)", "OTHER COUNTRIES", "colPos")
        if choice.email and re.fullmatch(r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+", choice.email) and 6 <= len(choice.email) <= 100:
            H["colBEmail"] = choice.email
        if choice.phone and 6 <= len(choice.phone) <= 12:
            H["colBPhno"] = choice.phone
        logf("Buyer Legal Name", f"{label} {choice.cell}", choice.name, "colBLegalname")
        logf("Buyer Address", f"{label} {choice.cell}", addr1, "colBaddr1")
        logf("Buyer Location", loc_src, loc, "colBLoc")
        logf("Buyer State", "Buyer GSTIN" if domestic else "Rule (export)", H.get("colBState", ""), "colBState")

        if not domestic and opt.buyer_party == "notify_party" and inv.consignee.name and inv.consignee.name != inv.notify_party.name:
            c = inv.consignee
            sl = self.party_location(c.lines)
            H.update({"colSLegalname": c.name, "colSaddr1": c.lines[0] if c.lines else "",
                      "colSaddr2": ", ".join(c.lines[1:]), "colSLoc": sl, "colSPin": "999999",
                      "colSState": "OTHER COUNTRIES"})
            if not c.lines or not 3 <= len(sl) <= 100:
                iss.red("Ship-to", "Consignee (ship-to) address/location incomplete for NIC shipping details.")
            iss.amber("Ship-to", f"Shipping details filled from Consignee '{c.name}' because the buyer is the Notify Party.")
            logf("Ship-to", f"Consignee {c.cell}", c.name, "colSLegalname")

    def buyer_from_fields(self, inv: SourceInvoice) -> Party:
        """Buyer written as a label line ('Bill To: XYZ LLP') followed by its address lines."""
        f = inv.fields
        raw = f.get("buyer_name", SourceValue())
        text = raw.text
        lines: list[str] = []
        if f.get("buyer_address") and f["buyer_address"].text:
            lines.append(f["buyer_address"].text)
        # everything printed under the buyer line, until a blank line or another label
        idx = next((i for i, (cell, _t) in enumerate(inv.all_text) if cell == raw.cell), None)
        if idx is not None:
            for cell, t in inv.all_text[idx + 1: idx + 7]:
                if not t:
                    break
                if re.search(r"(?i)\bGSTIN?\b", t) and re.search(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]", t.upper()):
                    lines.append(t)                 # buyer GSTIN line: keep it for the GSTIN, drop later
                    continue
                if self._is_label(t) or re.search(r"^\s*(SR\.?\s*NO|DESCRIPTION|PARTICULARS|ITEM)\b", t, re.I):
                    break
                lines.append(t)
        blob = " | ".join([text] + lines)
        gst = next((g for g in re.findall(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}\b", blob.upper())), "")
        blob = re.sub(r"(?i)\bGSTI?N?\s*(NO\.?)?\s*[:\-]?\s*[0-9A-Z]{15}\b", "|", blob)
        clean = [p.strip(" ,|:-") for p in re.split(r"\||\s{2,}", blob) if p.strip(" ,|:-")]
        name = clean[0] if clean else text
        name = re.sub(r"(?i)^(BILL(ED)?\s*TO|SOLD\s*TO|SHIP\s*TO|BUYER|CUSTOMER|CONSIGNEE|PARTY)\s*[:\-]?\s*", "", name)
        rest = clean[1:]
        m = re.search(r"\s(?=[A-Za-z0-9][^,]*?(?:ROAD|STREET|PLOT|NAGAR|MARG|LANE|AVENUE|ESTATE|FLOOR|BLOCK|"
                      r"SECTOR|CHOWK|COMPLEX|TOWER|HOUSE)\b)", name, re.I)
        if m and m.start() > 3:
            rest = [name[m.start():].strip()] + rest
            name = name[:m.start()]
        party = Party(name.strip(), rest, raw.cell, f.get("buyer_email", SourceValue()).text)
        party.gstin = gst
        return party

    @staticmethod
    def _is_label(t: str) -> bool:
        return bool(re.search(r"(?i)\b(INVOICE\s*NO|DATE|GSTIN|HSN|QTY|RATE|TAXABLE|TOTAL|TERMS|BANK|DECLARATION|"
                              r"E-?WAY|TRANSPORT|PLACE\s*OF\s*SUPPLY|STATE\s*CODE)\b", t)) and len(t) < 60

    def _export_details(self, inv, opt: ConversionOptions, profile, iss: Issues, H, logf):
        m, f = self.masters, inv.fields
        cur = inv.currency.text
        if not cur:
            iss.red("Currency", "Foreign currency code could not be identified from the invoice column headings.")
        H["colForCur"] = cur
        logf("Currency", inv.currency.where(), cur, "colForCur", inv.currency.note)

        code, src = opt.country_code.strip().upper(), "User selection"
        if code:
            if code not in m.countries:
                iss.red("Country", f"Country code '{code}' is not in the NIC country master.")
        else:
            # country of final destination first, then final destination, then the buyer / consignee address
            sources = [(k, f[k].text, f[k].where()) for k in ("country_final_destination", "final_destination") if k in f]
            addr_line = " ".join(x for x in (H.get("colBaddr1", ""), H.get("colBaddr2", "")) if x)
            if addr_line:
                sources.append(("buyer address", addr_line, "buyer address"))
            party = {"notify_party": inv.notify_party, "buyer_block": inv.buyer_block}.get(opt.buyer_party, inv.consignee)
            for p in (party, inv.consignee):
                if p and p.lines:
                    sources.append(("address", " ".join(p.lines), p.cell))
            resolved = []
            for kind, txt, where in sources:
                c = m.country_candidates(txt)
                if len(c) == 1:
                    resolved.append((c[0][0], txt, where))
            if resolved:
                code, txt, src = resolved[0]
                iss.amber("Country", f"Country code {code} ({m.countries[code]}) read from '{txt}'.")
                others = {c for c, _, _ in resolved} - {code}
                if others:
                    iss.amber("Country", f"The invoice also points to {', '.join(sorted(others))} elsewhere "
                                         f"({'; '.join(t for c, t, _ in resolved if c != code)}). {code} used from the destination field.")
            else:
                shown = " / ".join(t for _, t, _ in sources if t) or "nothing"
                iss.red("Country", f"Destination country could not be recognised from: {shown}. Write the country name "
                                   "(e.g. 'COUNTRY OF FINAL DESTINATION : USA') on the invoice.")
        H["colCntryCode"] = code
        logf("Country", src, code, "colCntryCode")

        pol = f.get("port_of_loading", SourceValue())
        port = opt.port_code.strip().upper()
        if not port and not pol.text and not opt.shipping_bill_no and "hsn" not in inv.columns:
            iss.amber("Port", "No port of loading is printed (usual for export of services). The NIC utility demands a "
                              "port code whenever any export detail is filled, so currency, country and port were left "
                              "blank. Add a port of loading to the invoice if these must be reported.")
            H["colForCur"] = H["colCntryCode"] = H["colPort"] = ""
            logf("Export details", "Not printed on a services invoice", "left blank", "colPort")
            return
        if not port:
            cands = m.port_candidates(pol.text)
            hint = f" Candidates for '{pol.text}': " + ", ".join(f"{c} ({d})" for c, d in cands[:6]) if cands else ""
            iss.red("Port", "Port code is mandatory once export details are entered (NIC template rule) and is not printed "
                            "on the invoice. Select the port code." + hint)
        elif port not in m.ports:
            iss.red("Port", f"Port code '{port}' is not in the NIC port master.")
        elif opt.port_from_profile:
            saved = profile.get("conversion", {}).get("port_source_text", "")
            if saved and saved.upper() != pol.text.upper():
                iss.red("Port", f"Port of loading on this invoice is '{pol.text}' but the saved profile port {port} was chosen "
                                f"for '{saved}'. Re-select the port.")
            else:
                iss.amber("Port", f"Port {port} ({m.ports[port]}) applied from the saved mapping profile. Confirm.")
        H["colPort"] = port
        logf("Port", f"User selection (invoice port of loading: '{pol.text}' {pol.where()})", port, "colPort",
             m.ports.get(port, ""))

        sb = opt.shipping_bill_no.strip() or f.get("shipping_bill_no", SourceValue()).text
        sbd_raw = opt.shipping_bill_date.strip() or f.get("shipping_bill_date", SourceValue()).text
        if not sb and not sbd_raw:
            iss.amber("Shipping Bill", "Shipping Bill No./date not on invoice - left blank (optional; add 'SHIPPING BILL NO :' to the invoice if available).")
        if sb and not SB_CHARS.match(sb):
            iss.red("Shipping Bill", "Shipping Bill number must be 1-20 characters (letters, digits, space, - / .).")
        sbd = ""
        if sbd_raw:
            dd, _ = parse_date(sbd_raw, True)
            if not dd:
                iss.red("Shipping Bill", f"Shipping Bill date '{sbd_raw}' is not a valid DD/MM/YYYY date.")
            else:
                sbd = dd.strftime("%d/%m/%Y")
        H["colShipBilNo"], H["colShipBilDt"] = sb, sbd
        logf("Shipping Bill", "User input / invoice", sb, "colShipBilNo")
        logf("Shipping Bill", "User input / invoice", sbd, "colShipBilDt")

        if opt.supplier_refund not in {"", "Yes", "No"}:
            iss.red("Supplier Refund", "Supplier refund must be Yes, No or blank.")
        if not opt.supplier_refund and opt.supply_type == "EXPWP":
            iss.amber("Supplier Refund", "Supplier refund claim (Yes/No) not selected for export with payment of IGST.")
        H["colSupRefund"] = opt.supplier_refund
        logf("Supplier Refund", "User selection", opt.supplier_refund, "colSupRefund")
        if opt.export_duty is not None:
            if opt.export_duty < 0:
                iss.red("Export Duty", "Export duty cannot be negative.")
            H["colExpDty"] = fmt(opt.export_duty, 2)
        logf("Export Duty", "User input", H.get("colExpDty", ""), "colExpDty")

    def _items(self, inv: SourceInvoice, opt: ConversionOptions, rate, iss: Issues, res: ConversionResult, logf,
               supplier: Supplier | None = None):
        m = self.masters
        domestic = opt.supply_type in DOMESTIC_SUPPLY_TYPES
        export_supply = opt.supply_type in EXPORT_SUPPLY_TYPES
        sac = inv.fields.get("sac_code")
        service = bool(getattr(inv, "is_service", False)) or ("hsn" not in inv.columns and sac is not None and sac.text)
        printed_cgst = to_decimal(inv.fields["tax_cgst"].value) if "tax_cgst" in inv.fields else None
        same_state = bool(supplier and supplier.state_code and opt.buyer_gstin[:2] == supplier.state_code.zfill(2))
        intra = bool(domestic and ((printed_cgst or ZERO) > 0 or (same_state and printed_cgst is None)))
        inv_igst = sum((it.num("igst") or ZERO) for it in inv.items) if "igst" in inv.columns else ZERO
        if domestic and same_state and (inv_igst > 0 or (to_decimal(inv.fields["tax_igst"].value)
                                                         if "tax_igst" in inv.fields else ZERO) or ZERO) > 0:
            iss.red("Tax type", f"The invoice charges IGST, but the supplier and the buyer are both in State "
                                f"{opt.buyer_gstin[:2]}; an intra-State supply carries CGST + SGST. Correct the "
                                "invoice or the tax type on the check screen.")
        if domestic and intra and opt.buyer_gstin and not same_state:
            iss.red("Tax type", f"The invoice charges CGST+SGST but the buyer's State code ({opt.buyer_gstin[:2]}) "
                                f"differs from the supplier's ({supplier.state_code if supplier else '?'}); an "
                                "inter-State supply must carry IGST. Correct the invoice before reporting it.")
        if not inv.items:
            iss.red("Line items", "No line items were detected on the invoice.")
            return
        basis, uqc = opt.quantity_basis, opt.uqc
        unit_col = "uqc" in inv.columns
        if service:
            # Service supplies do not require GST quantity/UQC.
            # Keep an internal service basis for price arithmetic, but never force
            # a UQC such as OTHERS into validation or final JSON.
            iss.amber("Line items", f"Service invoice: SAC code {sac.text} applied to every line (Is_Service = Yes). "
                                    "GST quantity/UQC are not required for service supply and will be omitted from JSON.")
            uqc = ""
            opt.uqc = ""
            if not basis:
                basis = opt.quantity_basis = "service"
        else:
            if not basis:
                iss.red("GST Quantity", "GST quantity basis not selected. Boxes, packs and weight are all on the invoice - "
                         "confirm which one is the GST quantity.")
            if not uqc and not unit_col:
                iss.red("GST UQC", "GST UQC could not be determined - the invoice has no unit column and the quantity "
                                   "column heading does not say box/carton. Set a default in Settings.")
            elif uqc and uqc not in m.unit_descriptions:
                iss.red("GST UQC", f"UQC '{uqc}' is not in the NIC Units master.")
        need = {"service": [], "cartons": ["cartons"], "packs": ["cartons", "packs_per_carton"],
                "net_kg_computed": ["cartons", "packs_per_carton", "pack_size"], "net_kg_packing": [],
                "source_qty": ["qty"]}.get(basis, [])
        for role in need:
            if role not in inv.columns:
                iss.red("GST Quantity", f"The chosen quantity basis needs a '{role}' column which was not found on the invoice.")
        if basis == "net_kg_computed":
            iss.amber("GST Quantity", "Quantity derived as boxes x packs per carton x pack size (grams) / 1000. Pack size "
                                      "headings in grams may not equal net weight (e.g. liquids in ml, gross pack weight).")
        if basis == "net_kg_packing" and not inv.packing_sheet:
            iss.red("GST Quantity", "No packing list sheet was found to read net weights from.")

        rate_role = {"cartons": "rate_per_carton", "packs": "rate_per_piece", "source_qty": "rate"}.get(basis)
        exp_wp = opt.supply_type == "EXPWP"
        igst_note_done = derived_note_done = False
        tol_fc, tol_inr = opt.tolerance_fc, opt.tolerance_inr
        head = res.header
        for it in inv.items:
            n = it.sl_no
            desc = it.description.text
            if not desc:
                iss.red("Description", f"Description missing for Item {n} (row {it.row}).", n)
            elif NIC_TEXT_BAD.search(desc):
                iss.red("Description", f"Description of Item {n} contains \" or \\ which breaks the NIC JSON.", n)
            elif len(desc) > 300:
                iss.amber("Description", f"Description of Item {n} is {len(desc)} characters; confirm NIC length limit.", n)
            if it.hidden_row:
                iss.amber("Line items", f"Item {n} is on hidden row {it.row} of the invoice - confirm it belongs to the invoice.", n)
            if it.packing_desc and it.packing_desc.upper() != desc.upper():
                iss.amber("Packing list", f"Item {n} description differs between invoice and packing list.", n)

            raw_hsn = sac.text if service else it.hsn.text
            hsn = re.sub(r"[\s.]", "", raw_hsn)
            if not hsn:
                iss.red("HSN", f"HSN code missing for Item {n}", n)
            else:
                if hsn != raw_hsn:
                    iss.amber("HSN", f"HSN '{raw_hsn}' for Item {n} normalised to '{hsn}'.", n)
                if it.hsn_was_number and len(hsn) in (3, 5, 7):
                    iss.red("HSN", f"HSN for Item {n} is stored as a number ({hsn}) - a leading zero may have been lost. "
                                   "Format the HSN cell as text in the invoice.", n)
                elif not HSN_RE.match(hsn):
                    iss.red("HSN", f"HSN '{hsn}' for Item {n} is not 4, 6 or 8 digits (NIC template rule).", n)
                elif len(hsn) == 4:
                    iss.amber("HSN", f"Item {n} carries a 4-digit HSN ({hsn}); confirm the digit level required for your turnover.", n)
                if hsn.startswith("99") and not service:
                    iss.amber("HSN", f"Item {n} HSN starts with 99 (services) but is billed as goods (Is_Service = No).", n)

            amount_sv = it.values.get("amount") or it.values.get("taxable_value")
            amount = it.num("amount")
            if amount is None:
                amount = it.num("taxable_value")
            if amount_sv is not None and amount_sv.formula_uncached:
                iss.red("Amount", f"Amount for Item {n} ({amount_sv.cell}) is a formula with no calculated value - open and save in Excel.", n)
            if amount is None:
                iss.red("Amount", f"Amount / taxable value missing for Item {n}", n)
            elif amount < 0:
                iss.red("Amount", f"Negative amount for Item {n}", n)

            qty, unit_fc, derived = None, None, False
            if basis == "cartons":
                qty = it.num("cartons")
            elif basis == "packs":
                c, p = it.num("cartons"), it.num("packs_per_carton")
                qty = c * p if c is not None and p is not None else None
            elif basis == "net_kg_computed":
                c, p, g = it.num("cartons"), it.num("packs_per_carton"), it.num("pack_size")
                qty = c * p * g / 1000 if None not in (c, p, g) else None
                if qty is not None and it.packing_net_kg is not None and abs(qty - it.packing_net_kg) > Decimal("0.001"):
                    iss.amber("GST Quantity", f"Item {n}: computed {fmt(qty, 3)} kg but packing list shows "
                                              f"{fmt(it.packing_net_kg, 3)} kg.", n)
            elif basis == "net_kg_packing":
                qty = it.packing_net_kg
            elif basis == "source_qty":
                qty = it.num("qty")
            elif basis == "service":
                qty = Decimal("1")
            if basis and basis != "service" and (qty is None or qty <= 0):
                iss.red("GST Quantity", f"Quantity missing or zero for Item {n} under the chosen basis.", n)
                qty = None
            if qty is not None and q(qty, 3) != qty:
                iss.amber("GST Quantity", f"Quantity {qty} for Item {n} rounded to 3 decimals ({fmt(qty, 3)}).", n)
            if rate_role and it.num(rate_role) is not None:
                unit_fc = it.num(rate_role)
            elif qty and amount is not None:
                unit_fc, derived = amount / qty, True
                if not derived_note_done and basis:
                    iss.amber("Unit Price", "Unit price derived as item amount / quantity (no rate column for this unit).")
                    derived_note_done = True
            if qty and unit_fc is not None and amount is not None and not derived:
                diff = qty * unit_fc - amount
                if abs(diff) > tol_fc:
                    iss.amber("Reconciliation", f"Item {n}: quantity x rate = {fmt(qty * unit_fc, 2)} but amount is "
                                                f"{fmt(amount, 2)} {inv.currency.text} (difference {fmt(diff, 2)}).", n)

            gst = opt.item_gst_rates.get(n)
            if gst is None:
                iss.red("GST Rate", f"GST rate not entered for Item {n}.", n)
            elif gst < 0 or gst > 100:
                iss.red("GST Rate", f"GST rate {gst} for Item {n} is not a valid percentage.", n)
            elif gst not in ALLOWED_GST_RATES:
                iss.red("GST Rate", f"GST rate {gst}% for Item {n} is not in the offline configured notified rate master.", n)
            elif n in opt.rate_from_memory:
                iss.amber("GST Rate", f"GST rate {fmt(gst, 3)}% for Item {n} taken from earlier invoice with HSN {hsn}.", n)
            if exp_wp and gst == 0:
                iss.red("GST Rate", f"Item {n}: export with payment of IGST but GST rate is 0.", n)
            if not domestic and not exp_wp and "igst" in inv.columns and (it.num("igst") or ZERO) > 0:
                iss.red("IGST", f"Item {n}: the invoice charges IGST but the export is treated as without payment.", n)

            item_uqc = "" if service else uqc
            if not service and unit_col:
                raw_unit = clean_text(it.values.get("uqc").value) if it.values.get("uqc") else ""
                mapped = m.unit_from_text(raw_unit)
                if mapped:
                    item_uqc = mapped
                elif raw_unit:
                    iss.red("GST UQC", f"Unit '{raw_unit}' of Item {n} is not in the NIC Units master.", n)
                    item_uqc = ""
                elif not uqc:
                    iss.red("GST UQC", f"Unit missing for Item {n}.", n)
            rec = {"colIDoctype": opt.doc_type, "colIDocno": head.get("colDocno", ""), "colIDocdate": head.get("colDocdate", ""),
                   "colProdSlno": str(n), "colProddesc": desc, "colProdservice": "Yes" if service else "No",
                   "colHsn": hsn,
                   "colFreeQuanty": "0", "colUnit": item_uqc, "colDiscount": "0", "colSgst": "0", "colCgst": "0",
                   "colCessrate": "0", "colCessadval": "0", "colCessnonad": "0", "colStCessrate": "0",
                   "colStCessadval": "0", "colStCessnonad": "0", "colOthChrgs": "0"}
            vals = {"qty": qty, "unit_fc": unit_fc, "amount_fc": amount, "gst": gst}
            if qty is not None:
                rec["colQuantity"] = fmt(qty, 3)
            if gst is not None:
                rec["colGstrate"] = fmt(gst, 3)
            if rate is not None and amount is not None:
                disc_fc = it.num("discount") or ZERO
                gross = q(amount * rate, 2)
                disc = q(disc_fc * rate, 2)
                taxable = gross - disc
                if "taxable_value" in inv.columns and it.num("taxable_value") is not None:
                    src_tax = q(it.num("taxable_value") * rate, 2)
                    if abs(src_tax - taxable) > tol_inr:
                        iss.amber("Reconciliation", f"Item {n}: printed taxable value differs from amount - discount.", n)
                unit_inr = None
                if qty:
                    unit_inr = q(gross / qty, 3) if derived or unit_fc is None else q(unit_fc * rate, 3)
                    d_inr = q(qty, 3) * unit_inr - gross
                    if abs(d_inr) > tol_inr:
                        iss.amber("Reconciliation", f"Item {n}: quantity x unit price (INR) = {fmt(q(qty, 3) * unit_inr, 2)} "
                                                    f"vs gross amount {fmt(gross, 2)} (difference {fmt(d_inr, 2)}).", n)
                igst = cgst = sgst = ZERO
                if domestic and gst is not None:
                    if intra:
                        cgst = sgst = q(taxable * gst / 200, 2)
                    else:
                        igst = q(taxable * gst / 100, 2)
                elif exp_wp and gst is not None:
                    igst = q(taxable * gst / 100, 2)
                    if "igst" in inv.columns and it.num("igst") is not None:
                        src_igst = q(it.num("igst") * rate, 2)
                        if abs(src_igst - igst) > tol_inr:
                            iss.amber("IGST", f"Item {n}: printed IGST {fmt(src_igst, 2)} differs from taxable x rate "
                                              f"{fmt(igst, 2)}; computed value used.", n)
                    elif not igst_note_done:
                        iss.amber("IGST", "IGST is not printed on the invoice; computed as taxable value x GST rate.")
                        igst_note_done = True
                total = taxable + igst + cgst + sgst
                rec.update({"colCgst": fmt(cgst, 2), "colSgst": fmt(sgst, 2)})
                rec.update({"colUnitPrice": fmt(unit_inr, 3) if unit_inr is not None else "",
                            "colTotal": fmt(gross, 2), "colDiscount": fmt(disc, 2), "colAssValue": fmt(taxable, 2),
                            "colIgst": fmt(igst, 2), "colTolitemval": fmt(total, 2)})
                vals.update({"gross": gross, "taxable": taxable, "igst": igst, "cgst": cgst, "sgst": sgst,
                             "total": total, "unit_inr": unit_inr})
            rec["_vals"] = vals
            res.items.append(rec)
        logf("Line items", f"{inv.sheet} rows {inv.items[0].row}-{inv.items[-1].row}", f"{len(inv.items)} items",
             "Items sheet", f"columns detected: {', '.join(f'{k}={v}' for k, v in inv.columns.items())}")
        logf("GST Quantity", "Mapping profile", basis, "colQuantity", SOURCE_RULE["colQuantity"])
        logf("GST UQC", "User confirmation", uqc, "colUnit", f"code {m.unit_code(uqc)}" if uqc else "")
        logf("HSN", f"{inv.sheet} column {inv.columns.get('hsn', '?')}", "per item", "colHsn")
        logf("GST Rate", "User input per item", "per item", "colGstrate")

    def _totals(self, inv: SourceInvoice, opt: ConversionOptions, rate, iss: Issues, res: ConversionResult, logf):
        H, tol = res.header, opt.tolerance_inr
        cur = inv.currency.text or "FC"
        sum_fc = sum((v["_vals"]["amount_fc"] for v in res.items if v["_vals"]["amount_fc"] is not None), ZERO)
        res.totals["amount_fc"] = sum_fc
        st = inv.source_total
        printed = to_decimal(st.value) if st and st.value is not None else None
        if printed is not None:
            diff = sum_fc - printed
            status = GREEN if abs(diff) <= opt.tolerance_fc else AMBER
            res.recon.append((f"Sum of item amounts ({cur}) vs printed total {st.cell}", fmt(sum_fc, 2), fmt(printed, 2), fmt(diff, 2), status))
            if status == AMBER:
                iss.amber("Reconciliation", f"Sum of items {fmt(sum_fc, 2)} {cur} differs from printed total {fmt(printed, 2)} ({st.cell}).")
        else:
            iss.amber("Reconciliation", "Printed invoice total not found - item sum could not be cross-checked.")
        words = inv.fields.get("amount_in_words")
        if words and words.text:
            from .words import words_to_amounts
            cands = words_to_amounts(words.text)
            refs = [x for x in (to_decimal(inv.source_grand_total.value) if inv.source_grand_total.value is not None else None,
                                printed, sum_fc) if x is not None]
            w = next((c for c in cands for rf in refs if abs(c - q(rf, 2)) <= Decimal("0.01")), cands[0] if cands else None)
            gt = inv.source_grand_total
            grand = to_decimal(gt.value) if gt and gt.value is not None else None
            ref = printed if printed is not None else sum_fc
            if grand is not None and w is not None and abs(w - q(grand, 2)) <= Decimal("0.01"):
                ref = grand
            if w is None:
                iss.amber("Amount in words", f"'Amount in words' ({words.cell}) could not be interpreted for cross-check.")
            else:
                diff = w - q(ref, 2)
                status = GREEN if abs(diff) <= Decimal("0.01") else AMBER
                res.recon.append((f"Amount in words {words.cell} vs invoice total ({cur})", fmt(w, 2), fmt(ref, 2), fmt(diff, 2), status))
                if status == AMBER:
                    iss.amber("Amount in words", f"AMOUNT IN WORDS reads {fmt(w, 2)} {cur} but the invoice total is "
                                                 f"{fmt(ref, 2)} {cur}. Correct the commercial invoice before issue.")
        if rate is None or not res.items or any("colAssValue" not in r for r in res.items):
            return
        tax = sum((r["_vals"]["taxable"] for r in res.items), ZERO)
        igst = sum((r["_vals"]["igst"] for r in res.items), ZERO)
        cgst = sum((r["_vals"].get("cgst", ZERO) for r in res.items), ZERO)
        sgst = sum((r["_vals"].get("sgst", ZERO) for r in res.items), ZERO)
        item_total = sum((r["_vals"]["total"] for r in res.items), ZERO)
        other, disc = ZERO, ZERO
        grand = item_total + other - disc
        ro = ZERO
        if opt.round_off:
            ro = q(grand, 0) - grand
            if abs(ro) > Decimal("99.99"):
                iss.red("Round off", "Round-off exceeds the NIC limit of +/-99.99.")
        final = grand + ro
        H.update({"colTotTaxval": fmt(tax, 2), "colTsgstval": fmt(sgst, 2), "colTcgstval": fmt(cgst, 2),
                  "colTigstval": fmt(igst, 2),
                  "colTcessval": "0", "colTstcessval": "0", "colTDiscount": "0", "colTOthChrgs": "0",
                  "colRoundOff": fmt(ro, 2), "colTinvoiceval": fmt(final, 2)})
        res.totals.update({"taxable": tax, "igst": igst, "invoice_value": final, "round_off": ro})
        # reconciliation (item level -> header), mirrors the NIC utility's own checks
        h_tax, h_igst, h_tot = to_decimal(H["colTotTaxval"]), to_decimal(H["colTigstval"]), to_decimal(H["colTinvoiceval"])
        checks = [("Sum of item taxable values vs header taxable value", sum(to_decimal(r["colAssValue"]) for r in res.items), h_tax),
                  ("Sum of item IGST vs header IGST", sum(to_decimal(r["colIgst"]) for r in res.items), h_igst),
                  ("Sum of item CGST vs header CGST", sum(to_decimal(r["colCgst"]) for r in res.items), cgst),
                  ("Sum of item SGST vs header SGST", sum(to_decimal(r["colSgst"]) for r in res.items), sgst),
                  ("Item totals + other charges - discount + round-off vs header invoice value",
                   sum(to_decimal(r["colTolitemval"]) for r in res.items) + other - disc + ro, h_tot)]
        for label, a, b in checks:
            diff = a - b
            status = GREEN if abs(diff) <= tol else RED
            res.recon.append((label, fmt(a, 2), fmt(b, 2), fmt(diff, 2), status))
            if status == RED:
                iss.red("Reconciliation", f"{label}: difference {fmt(diff, 2)} exceeds tolerance {tol}.")
        bad_item = [r["colProdSlno"] for r in res.items
                    if abs(to_decimal(r["colAssValue"]) + to_decimal(r["colIgst"]) - to_decimal(r["colTolitemval"])) > tol]
        res.recon.append(("Each item: taxable + taxes + other charges - discount = item total",
                          f"{len(res.items) - len(bad_item)} ok", f"{len(bad_item)} differ", "", GREEN if not bad_item else RED))
        conv = q(sum_fc * rate, 2)
        d2 = conv - tax
        res.recon.append((f"Invoice {cur} total x exchange rate vs sum of item-wise rounded INR", fmt(conv, 2), fmt(tax, 2),
                          fmt(d2, 2), GREEN if abs(d2) <= tol else AMBER))
        if abs(d2) > tol:
            iss.amber("Rounding", f"Item-wise INR rounding differs from whole-invoice conversion by {fmt(d2, 2)}.")
        for key, label, printed_key in (("colTcgstval", "CGST", "tax_cgst"), ("colTsgstval", "SGST", "tax_sgst"),
                                        ("colTigstval", "IGST", "tax_igst"), ("colTinvoiceval", "Invoice total", "grand_total")):
            pv = inv.fields.get(printed_key)
            pd = to_decimal(pv.value) if pv is not None else None
            if pd is not None and rate is not None:
                shown = q(pd * (rate if printed_key == "grand_total" and (inv.currency.text or "INR") != "INR" else 1), 2)
                diff = to_decimal(H[key]) - shown
                st = GREEN if abs(diff) <= tol else AMBER
                res.recon.append((f"{label} printed on the invoice vs computed", fmt(shown, 2), H[key], fmt(diff, 2), st))
                if st == AMBER:
                    iss.amber("Reconciliation", f"{label} printed on the invoice ({fmt(shown, 2)}) differs from the "
                                                f"computed value ({H[key]}).")
        inr_printed = to_decimal(inv.fields["inr_total"].value) if "inr_total" in inv.fields else None
        if inr_printed is not None:
            diff = tax - inr_printed
            st = GREEN if abs(diff) <= tol else AMBER
            res.recon.append(("INR value printed on the invoice vs converted taxable value", fmt(inr_printed, 2),
                              fmt(tax, 2), fmt(diff, 2), st))
            if st == AMBER:
                iss.amber("Reconciliation", f"The INR value printed on the invoice ({fmt(inr_printed, 2)}) differs from "
                                            f"the converted taxable value ({fmt(tax, 2)}).")
        for code, label in (("colTotTaxval", "Total Taxable Value"), ("colTigstval", "Total IGST"),
                            ("colRoundOff", "Round off"), ("colTinvoiceval", "Total Invoice Value")):
            logf(label, "Computed from items (INR)", H[code], code)

    # ---------------------------------------------------------------- output
    def output_names(self, res: ConversionResult) -> tuple[str, str]:
        base = safe_filename(res.header.get("colDocno") or Path(res.source.path).stem)
        return f"{base}_NIC_READY.xlsm", f"{base}_Validation_Report.xlsx"

    def generate(self, res: ConversionResult, out_dir: str | Path, supplier: Supplier) -> dict:
        if res.issues.has_red:
            raise RuntimeError("Generation blocked: RED errors remain.")
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        nic_name, rep_name = self.output_names(res)
        header = {k: v for k, v in res.header.items() if k in self.e_codes}
        items = [{k: v for k, v in r.items() if k in self.i_codes} for r in res.items]
        nic_path = out_dir / nic_name
        info = write_nic_file(self.template, nic_path, [header], items, res.options.write_mode)
        info["mode"] = res.options.write_mode
        problems = verify_nic_file(self.template, nic_path, [header], items, info)
        from .nic_json import build_json, write_json
        json_path = out_dir / nic_name.replace("_NIC_READY.xlsm", "_eInvoice.json")
        json_data = build_json(res, supplier, self.masters)
        write_json(json_path, json_data)
        # Final validation of the exact JSON bytes/object that will be uploaded.
        import json as _json
        from .json_validator import validate_documents
        post_errors = validate_documents(_json.loads(json_path.read_text(encoding="utf-8")))
        if post_errors:
            try:
                json_path.unlink()
            except OSError:
                pass
            raise RuntimeError("Final JSON Schema 1.1 validation failed: " + " | ".join(post_errors[:8]))
        from .report import write_report
        rep_path = out_dir / rep_name
        write_report(rep_path, res, supplier, self, info, problems)
        return {"nic": nic_path, "json": json_path, "report": rep_path, "info": info, "problems": problems}
