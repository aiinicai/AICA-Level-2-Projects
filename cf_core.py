"""CertifyFlow & Saral Bridge - core logic (Python port, standard library only)."""
import base64
import copy
import datetime as _dt
import io
import json
import os
import random
import re
import smtplib
import ssl
import tempfile
import time
import zipfile
from email.message import EmailMessage
from xml.sax.saxutils import escape as _esc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STORAGE_FILE = os.path.join(DATA_DIR, "app_storage.json")
CERT_DIR = os.path.join(BASE_DIR, "Certificates")

DEFAULT_CA = {
    "firmName": "Amruta & Associates", "caName": "CA Amruta Joshi",
    "membershipNumber": "148920", "firmRegNumber": "112233W",
    "address": "Suite 302, Business Guild, Senapati Bapat Road, Pune - 411016",
    "commonEmail": "caamruta21@gmail.com", "phone": "+91 98230 45678",
    "city": "Pune", "state": "Maharashtra", "stateCode": "27",
    "gstin": "27AABCJ4411K1Z2", "pan": "AABCJ4411K",
}
DEFAULT_SMTP = {"host": "smtp.gmail.com", "port": "587", "secure": False,
                "user": "caamruta21@gmail.com", "password": "", "senderName": "CertifyFlow System"}
DEFAULT_SARAL = {"host": "localhost", "port": "1433", "database": "SaralAccountsDB",
                 "username": "sa", "password": "", "salesVoucherType": "Tax Invoice",
                 "autoCreateLedger": True}


def _load_defaults():
    with open(os.path.join(BASE_DIR, "defaults.json"), encoding="utf-8") as f:
        return json.load(f)


_DEFAULTS = _load_defaults()
DEFAULT_PARTIES = _DEFAULTS["parties"]
TEMPLATES = _DEFAULTS["templates"]  # metadata; bodies are produced by RENDERERS


# ----------------------------------------------------------------- helpers
def pf(x, default=0.0):
    """JavaScript-style parseFloat."""
    m = re.match(r"\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", str(x if x is not None else ""))
    return float(m.group(0)) if m else default


def fx(x, digits=2):
    """JavaScript Number.toFixed (rounds halves away from zero on the exact value)."""
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(1).scaleb(-digits)
    return str(Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP))


def js_num(n):
    """Print a number the way JavaScript template strings do."""
    n = float(n)
    return str(int(n)) if n == int(n) else repr(n)


def fmt_in(n, max_frac=3):
    """Equivalent of Number.toLocaleString('en-IN')."""
    n = round(float(n), max_frac)
    neg = n < 0
    n = abs(n)
    s = f"{n:.{max_frac}f}".rstrip("0").rstrip(".")
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts) + "," + tail
    return ("-" if neg else "") + whole + ("." + frac if frac else "")


def now_iso():
    n = _dt.datetime.now(_dt.timezone.utc)
    return n.strftime("%Y-%m-%dT%H:%M:%S.") + f"{n.microsecond // 1000:03d}Z"


def rand4():
    return random.randint(1000, 9999)


def new_cert_number():
    return f"CERT-{_dt.date.today().year}-{rand4()}"


def new_invoice_number():
    return f"INV-{_dt.date.today().year}-{rand4()}"


def uid(prefix):
    return f"{prefix}-{int(time.time() * 1000)}"


def long_date(d=None):
    d = d or _dt.date.today()
    return f"{d.day:02d} {d.strftime('%B')} {d.year}"


def short_date(d=None):
    d = d or _dt.date.today()
    return f"{d.day}/{d.month}/{d.year}"


def v(values, key, default=""):
    """JS  values.key || default"""
    x = values.get(key)
    return x if x not in (None, "", 0) else default


# --------------------------------------------------------------- templates
def _sig(ca, role):
    return (f"For {ca['firmName']}\nChartered Accountants\nFirm Reg. No.: {ca['firmRegNumber']}\n\n"
            f"{ca['caName']}\n{role}\nMembership No.: {ca['membershipNumber']}")


def _r_net_worth(p, x, ca):
    im, li, bu, lb = (pf(x.get(k) or "0") for k in
                      ("immovableProperty", "liquidInvestments", "businessAssets", "totalLiabilities"))
    ta = im + li + bu
    nw = ta - lb
    return f"""TO WHOMSOEVER IT MAY CONCERN

This is to certify that we have verified the books of accounts, title deeds, valuation reports, bank balance confirmation statements, and relevant records produced before us by {p['name']} having Permanent Account Number (PAN): {p['pan']} and registered office / residential address at {p['address']}.

Based on our examination and according to the information and explanations given to us, the statement of Net Worth as on {v(x, 'asOnDate', '31st March 2026')} is computed as under:

A. ASSETS & INVESTMENTS:
1. Immovable Properties (Valued as per approved valuer): ₹ {fx(im)} Lakhs
2. Movable & Liquid Assets (Bank Balances, Mutual Funds, Equities): ₹ {fx(li)} Lakhs
3. Capital & Shareholdings in Business Enterprises: ₹ {fx(bu)} Lakhs
TOTAL GROSS ASSETS (A): ₹ {fx(ta)} Lakhs

B. LIABILITIES:
1. Secured & Unsecured Bank Borrowings / Loans: ₹ {fx(lb)} Lakhs
TOTAL LIABILITIES (B): ₹ {fx(lb)} Lakhs

C. COMPUTATION OF NET WORTH:
NET WORTH (A - B): ₹ {fx(nw)} Lakhs (Rupees {fx(nw)} Lakhs Only)

PURPOSE OF CERTIFICATION:
This certificate is issued at the specific request of {p['name']} for the purpose of {v(x, 'issuingBankName', 'bank credit facility appraisal')} and is true and correct to the best of our knowledge and belief based on the verified records.

{_sig(ca, 'Partner / Proprietor')}"""


def _r_turnover(p, x, ca):
    y1, y2, y3 = (pf(x.get(k) or "0") for k in ("fy1", "fy2", "fy3"))
    avg = (y1 + y2 + y3) / 3
    return f"""TO WHOMSOEVER IT MAY CONCERN

We have examined the audited Balance Sheets, Profit and Loss Accounts, and Statutory GST Returns (GSTR-1 and GSTR-3B) of M/s {p['name']}, having PAN: {p['pan']} and GSTIN: {p['gstin']}, with principal place of business at {p['address']}.

On the basis of our examination of books of accounts and records, we hereby certify that the Annual Turnover from operations for the last three completed Financial Years is as follows:

1. Financial Year 2024-2025: ₹ {fx(y1)} Lakhs (Audited)
2. Financial Year 2023-2024: ₹ {fx(y2)} Lakhs (Audited)
3. Financial Year 2022-2023: ₹ {fx(y3)} Lakhs (Audited)

AVERAGE ANNUAL TURNOVER: ₹ {fx(avg)} Lakhs (Rupees {fx(avg)} Lakhs Only)

We further certify that the figures mentioned above are in agreement with the statutory books of accounts and relevant tax records. This certificate is issued for submission towards {v(x, 'tenderRef', 'tender qualification')}.

{_sig(ca, 'Partner')}"""


def _r_15cb(p, x, ca):
    inr = pf(x.get("inrEquivalent") or "0")
    rate = pf(x.get("taxRateApplicable") or "10")
    tds = inr * rate / 100
    net = inr - tds
    return f"""FORM NO. 15CB
[See rule 37BB of Income-tax Rules, 1962]
Certificate of an Accountant for Foreign Remittance

We have examined the agreement, invoices, Tax Residency Certificate (TRC), Form 10F, and relevant documents relating to the proposed remittance by:
Remitter: {p['name']}
PAN: {p['pan']} | GSTIN: {p['gstin']}
Address: {p['address']}

To Beneficiary: {v(x, 'beneficiaryName', 'Foreign Entity')}
Country: {v(x, 'beneficiaryCountry', 'Germany')}

1. Proposed Remittance: {v(x, 'currencyAndAmount', 'EUR 45,000')} (Equivalent to ₹ {fmt_in(inr)})
2. Nature of Remittance: {x.get('natureOfRemittance') or ''}
3. Taxability in India: The remittance is in the nature of Royalties / Fees for Technical Services under Section 9(1)(vii) of the Income-tax Act, 1961 and Article 12 of Double Taxation Avoidance Agreement (DTAA).
4. Rate of Withholding Tax (TDS): {js_num(rate)}%
5. Tax Deducted at Source (TDS): ₹ {fmt_in(tds)}
6. Net Remittance Amount: ₹ {fmt_in(net)}
7. Authorised Dealer Bank: {v(x, 'adBankName', 'AD Bank')}

In our opinion, the tax has been appropriately determined in accordance with the provisions of Section 195 and the relevant Double Taxation Avoidance Agreement.

For {ca['firmName']}
Chartered Accountants
Firm Reg. No.: {ca['firmRegNumber']}

{ca['caName']}
Membership No.: {ca['membershipNumber']}"""


def _r_wc(p, x, ca):
    stock, debtors, cred = (pf(x.get(k) or "0") for k in ("inventoryValue", "bookDebts", "tradeCreditors"))
    gross = stock + debtors
    gap = gross - cred
    margin = gap * 0.25
    mpbf = gap - margin
    return f"""WORKING CAPITAL APPRAISAL CERTIFICATE

This is to certify that we have verified the stock statements, debtor aging schedules, creditor ledgers, and books of accounts of M/s {p['name']} (PAN: {p['pan']}, GSTIN: {p['gstin']}), having works / business premises at {p['address']}.

Based on our scrutiny of audited/provisional financial statements, the working capital position is certified as below:

1. Value of Inventory & Raw Material / Finished Goods: ₹ {fx(stock)} Lakhs
2. Eligible Book Debts & Trade Receivables (Less than 90 days): ₹ {fx(debtors)} Lakhs
GROSS CURRENT ASSETS (A): ₹ {fx(gross)} Lakhs

3. Sundry Trade Creditors & Statutory Dues (B): ₹ {fx(cred)} Lakhs
WORKING CAPITAL GAP (WCG = A - B): ₹ {fx(gap)} Lakhs

4. Minimum Borrower Margin Contribution (25% of WCG): ₹ {fx(margin)} Lakhs
5. Maximum Permissible Bank Finance (MPBF): ₹ {fx(mpbf)} Lakhs
6. Existing Sanctioned Bank Limit: ₹ {fx(pf(x.get('existingLimit') or '0'))} Lakhs
7. Proposed / Recommended Limit: ₹ {fx(pf(x.get('proposedLimit') or '0'))} Lakhs

We confirm that the books of accounts have been verified and reflect a true and fair view of the current assets and liabilities position.

{_sig(ca, 'Partner')}"""


def _r_stat(p, x, ca):
    return f"""STATUTORY TAX COMPLIANCE CERTIFICATE

TO WHOMSOEVER IT MAY CONCERN

We have examined the statutory tax records, portal dashboards, challans, and returns filed by M/s {p['name']}, having Permanent Account Number: {p['pan']} and GSTIN: {p['gstin']}, situated at {p['address']}.

On the basis of our examination of the official GSTN portal and Income Tax Department records, we hereby certify that:

1. GST Compliance: The registered entity has filed all monthly/quarterly returns in Form GSTR-1 and GSTR-3B up to date for the period {v(x, 'financialYear', 'FY 2025-2026')}.
2. Income Tax Compliance: The entity has filed its Income Tax Return for the preceding Assessment Year under Acknowledgement No. {v(x, 'itrAckNo', 'N/A')}.
3. Tax Arrears: There are {v(x, 'undisputedDues', 'NIL undisputed tax dues')} outstanding against the entity as on date.
4. Tax Deduction (TDS/TCS): All applicable tax deductions and quarterly statements in Form 26Q/24Q have been submitted in accordance with Chapter XVII-B of the Income-tax Act, 1961.

This certificate is issued for official vendor empanelment and statutory verification purposes.

{_sig(ca, 'Partner')}"""


RENDERERS = {
    "tmpl-net-worth": _r_net_worth, "tmpl-turnover": _r_turnover,
    "tmpl-form-15cb": _r_15cb, "tmpl-working-capital": _r_wc,
    "tmpl-statutory-clearance": _r_stat,
}


def get_template(tid):
    return next((t for t in TEMPLATES if t["id"] == tid), None)


def render_body(template, party, values, ca):
    return RENDERERS[template["id"]](party, values, ca)


def default_values(template):
    return {f["id"]: f.get("defaultValue", "") for f in template["fields"]}


# -------------------------------------------------------------------- DOCX
def _run(text, size=21, bold=False, italic=False, underline=False, color=None):
    rpr = '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
    if bold: rpr += "<w:b/>"
    if italic: rpr += "<w:i/>"
    if underline: rpr += '<w:u w:val="single"/>'
    if color: rpr += f'<w:color w:val="{color}"/>'
    rpr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{_esc(text)}</w:t></w:r>'


def _para(text="", align="left", after=0, before=0, **kw):
    ppr = f'<w:spacing w:before="{before}" w:after="{after}"/><w:jc w:val="{align}"/>'
    if kw.pop("rule", False):
        ppr = '<w:pBdr><w:bottom w:val="single" w:sz="8" w:space="1" w:color="000000"/></w:pBdr>' + ppr
    run = _run(text, **kw) if text else ""
    return f"<w:p><w:pPr>{ppr}</w:pPr>{run}</w:p>"


def _cell(text, width, bold=False):
    return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="pct"/></w:tcPr>'
            f'{_para(text, size=19, bold=bold, after=40, before=40)}</w:tc>')


def build_docx(template, party, values, ca, cert_no, udin=None, approval_date=None):
    """Return (bytes, filename) for a certificate Word document."""
    date_str = approval_date or long_date()
    full = render_body(template, party, values, ca)
    blocks = [b for b in re.split(r"\n\n", full) if b.strip()]

    body = [
        _para(f"Certificate Ref: {cert_no}", "right", 120, size=20, bold=True),
        _para(f"Date of Issue: {date_str}", "right", 200, size=20),
        _para(template["title"].upper(), "center", 100, 200, size=28, bold=True, underline=True),
        _para(template["subtitle"], "center", 280, size=20, italic=True, color="555555"),
    ]
    rows = [("Client / Party Name:", party["name"], True),
            ("Permanent Account Number (PAN):", party["pan"], False),
            ("GST Identification No (GSTIN):", party.get("gstin") or "Unregistered / Exempt", False),
            ("Registered Office Address:", party["address"], False)]
    tbl = ('<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>'
           + "".join(f'<w:{s} w:val="single" w:sz="4" w:color="999999"/>'
                     for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
           + '</w:tblBorders></w:tblPr><w:tblGrid><w:gridCol w:w="2700"/><w:gridCol w:w="6300"/></w:tblGrid>')
    for lab, val, b in rows:
        tbl += f"<w:tr>{_cell(lab, 1500, True)}{_cell(val, 3500, b)}</w:tr>"
    tbl += "</w:tbl>"
    body.append(tbl)
    body.append(_para(""))

    for block in blocks:
        if block.startswith("For ") and "Chartered Accountants" in block:
            continue
        if block.startswith("TO WHOMSOEVER IT MAY CONCERN"):
            body.append(_para("TO WHOMSOEVER IT MAY CONCERN", "center", 180, 180, size=24, bold=True))
            continue
        for line in block.split("\n"):
            head = line.startswith(("A. ", "B. ", "C. ", "PURPOSE OF CERTIFICATION:"))
            body.append(_para(line, "both", 140, size=21, bold=head))

    body.append(_para(
        "This certificate is issued on the basis of examination of statutory books of account, financial "
        "statements, and vouchers produced before us, and explanations provided by the management. This "
        "document is strictly for the intended purpose and shall not be reproduced without prior written consent.",
        "both", 300, 200, size=18, italic=True, color="555555"))
    sig = [(f"For {ca['firmName']}", 22, True), ("Chartered Accountants", 20, False),
           (f"Firm Registration No.: {ca['firmRegNumber']}", 19, False), ("", 19, False),
           (ca["caName"], 22, True), ("Partner / Proprietor", 19, False),
           (f"Membership No.: {ca['membershipNumber']}", 19, False),
           (f"Place: {ca.get('city') or 'Pune'}", 19, False), (f"Date: {date_str}", 19, False),
           (f"UDIN: {udin or 'Pending Online Generation at icai.org'}", 20, True)]
    for text, size, bold in sig:
        body.append(_para(text, "right", 60, size=size, bold=bold))

    ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
    sect = ('<w:sectPr><w:headerReference w:type="default" r:id="rId1"/><w:footerReference w:type="default" r:id="rId2"/>'
            '<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
            'w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>')
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {ns}><w:body>{"".join(body)}{sect}</w:body></w:document>'
    header = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {ns}>'
              + _para(f"{ca['firmName']} — CHARTERED ACCOUNTANTS", "center", 40, size=18, bold=True)
              + _para(f"{ca['address']} | FRN: {ca['firmRegNumber']} | Email: {ca['commonEmail']}",
                      "center", 120, size=16, color="555555", rule=True) + "</w:hdr>")
    footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {ns}>'
              + _para("Page 1 of 1 — Generated via CertifyFlow Professional Suite — Confidential Document",
                      "center", size=16, color="777777") + "</w:ftr>")
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
          '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    docrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>'
               '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/_rels/document.xml.rels", docrels)
        z.writestr("word/header1.xml", header)
        z.writestr("word/footer1.xml", footer)
    safe = re.sub(r"[^a-zA-Z0-9]", "_", party["name"])[:20]
    return buf.getvalue(), f"{cert_no}_{safe}.docx"


# ----------------------------------------------------------------- storage
class Store:
    """Reads/writes data/app_storage.json (same file format as the Node version)."""

    def __init__(self, path=STORAGE_FILE):
        self.path = path
        self.data = {}
        self.load()

    def load(self):
        raw = {}
        try:
            if os.path.exists(self.path):
                with open(self.path, encoding="utf-8") as f:
                    raw = json.load(f)
        except Exception as e:  # corrupt file: keep a copy, start from defaults
            try:
                os.replace(self.path, self.path + f".corrupt-{int(time.time())}")
            except OSError:
                pass
            print("[Storage] Could not read storage file:", e)
        d = raw if isinstance(raw, dict) else {}
        d["caDetails"] = {**DEFAULT_CA, **(d.get("caDetails") or {})}
        d["smtpConfig"] = {**DEFAULT_SMTP, **(d.get("smtpConfig") or {})}
        d["saralConfig"] = {**DEFAULT_SARAL, **(d.get("saralConfig") or {})}
        d["parties"] = d.get("parties") if d.get("parties") else copy.deepcopy(DEFAULT_PARTIES)
        for k in ("certificates", "invoices", "emailLogs"):
            d[k] = d.get(k) or []
        self.data = d
        saral_profiles(self)

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data["lastSavedAt"] = now_iso()
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def __getitem__(self, k):
        return self.data[k]

    # convenience
    def party(self, pid):
        return next((p for p in self.data["parties"] if p["id"] == pid), None)

    def cert(self, cid):
        return next((c for c in self.data["certificates"] if c["id"] == cid), None)

    def backup_to(self, path):
        self.save()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def restore_from(self, path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Invalid backup file.")
        self.data = data
        self.save()
        self.load()


# ---------------------------------------------------------------- services
def make_certificate(store, template, party, values, status="draft"):
    ca = store["caDetails"]
    no = new_cert_number()
    data, filename = build_docx(template, party, values, ca, no)
    cert = {
        "id": uid("cert"), "certificateNumber": no, "templateId": template["id"],
        "templateTitle": template["title"], "partyId": party["id"], "partyName": party["name"],
        "partyPan": party["pan"], "partyGstin": party.get("gstin", ""),
        "partyAddress": party["address"], "values": dict(values),
        "renderedText": render_body(template, party, values, ca),
        "docxBase64": base64.b64encode(data).decode("ascii"),
        "createdAt": now_iso(), "status": status, "emailStatus": "not_sent",
    }
    store["certificates"].insert(0, cert)
    store.save()
    return cert, data, filename


def save_docx_file(data, filename, folder=CERT_DIR):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path


def cert_filename(cert):
    safe = re.sub(r"\s+", "_", cert["partyName"])
    return f"{cert['certificateNumber']}_{safe}.docx"


def regenerate_docx(store, cert):
    """Rebuild the Word file of a stored certificate (adds UDIN once approved)."""
    t = get_template(cert["templateId"])
    party = store.party(cert["partyId"]) or {
        "name": cert["partyName"], "pan": cert["partyPan"],
        "gstin": cert.get("partyGstin", ""), "address": cert.get("partyAddress", "")}
    approval = None
    if cert.get("approvalDate"):
        try:
            approval = long_date(_dt.date.fromisoformat(cert["approvalDate"][:10]))
        except ValueError:
            pass
    data, _ = build_docx(t, party, cert.get("values", {}), store["caDetails"],
                         cert["certificateNumber"], cert.get("udin"), approval)
    return data


def approve(store, cert, udin="", notes=""):
    ca = store["caDetails"]
    cert["status"] = "approved"
    cert["approvalDate"] = now_iso()
    cert["udin"] = (udin or "").strip().upper() or f"26{ca['membershipNumber']}BK{rand4()}"
    cert["approvalNotes"] = notes or "Verified against statutory books of accounts."
    try:
        cert["docxBase64"] = base64.b64encode(regenerate_docx(store, cert)).decode("ascii")
    except Exception:
        pass
    store.save()
    return cert["udin"]


def reject(store, cert, notes=""):
    cert["status"] = "rejected"
    cert["approvalNotes"] = notes or "Rejected by reviewing partner."
    store.save()


def send_email(smtp, to_email, subject, body, filename, docx_bytes):
    """Live SMTP if configured, otherwise the same 'simulated' mode as the Node version."""
    if not to_email:
        raise ValueError("Recipient CA email address is required.")
    if not docx_bytes:
        raise ValueError("Word document attachment is required.")
    if smtp.get("host") and smtp.get("user") and smtp.get("password"):
        msg = EmailMessage()
        msg["From"] = f'"{smtp.get("senderName") or "CertifyFlow System"}" <{smtp["user"]}>'
        msg["To"] = to_email
        msg["Subject"] = subject or f"Generated Certificate: {filename}"
        msg.set_content(body or f"Please find attached the generated certificate ({filename}) for verification and review.")
        msg.add_attachment(docx_bytes, maintype="application",
                           subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
                           filename=filename)
        port = int(smtp.get("port") or 587)
        ctx = ssl.create_default_context()
        if smtp.get("secure") is True or port == 465:
            server = smtplib.SMTP_SSL(smtp["host"], port, timeout=30, context=ctx)
        else:
            server = smtplib.SMTP(smtp["host"], port, timeout=30)
            server.ehlo()
            if server.has_extn("starttls"):
                server.starttls(context=ctx)
                server.ehlo()
        try:
            server.login(smtp["user"], smtp["password"])
            server.send_message(msg)
        finally:
            try:
                server.quit()
            except Exception:
                pass
        return {"mode": "live_smtp", "messageId": msg.get("Message-ID", f"smtp-{int(time.time())}"), "note": ""}
    return {"mode": "simulated_smtp", "messageId": f"sim-{int(time.time() * 1000)}-{random.randint(0, 9999)}",
            "note": "No SMTP password set - simulated locally. Add your SMTP details in Settings to send real emails."}


def dispatch_certificate(store, cert, to_email, subject, body):
    docx_bytes = base64.b64decode(cert["docxBase64"]) if cert.get("docxBase64") else regenerate_docx(store, cert)
    fname = cert_filename(cert)
    res = send_email(store["smtpConfig"], to_email, subject, body, fname, docx_bytes)
    store["emailLogs"].insert(0, {
        "id": uid("log"), "certificateId": cert["id"], "certificateNumber": cert["certificateNumber"],
        "partyName": cert["partyName"], "recipientEmail": to_email, "subject": subject,
        "timestamp": now_iso(), "status": "delivered" if res["mode"] == "live_smtp" else "simulated",
        "messageId": res["messageId"], "filename": fname, "notes": res["note"]})
    cert.update(emailStatus="sent", lastSentTo=to_email, lastSentAt=now_iso())
    store.save()
    return res


def default_email(store, cert, kind="dispatch"):
    ca = store["caDetails"]
    if kind == "studio":
        subj = f"[CertifyFlow] Generated Certificate {cert['certificateNumber']} - {cert['partyName']}"
        body = (f"Dear {ca['caName']},\n\nPlease find attached the generated Word certificate for {cert['partyName']} "
                f"(PAN: {cert['partyPan']}) for your professional review and signature.\n\n"
                f"Template: {cert['templateTitle']}\nRef No: {cert['certificateNumber']}\nDate: {short_date()}\n\n"
                f"This email has been dispatched directly to your designated CA email address ({ca['commonEmail']}).")
    else:
        subj = f"[CertifyFlow] Certificate {cert['certificateNumber']} for {cert['partyName']}"
        body = (f"Dear {ca['caName']},\n\nPlease find attached the generated Microsoft Word (.docx) certificate for "
                f"{cert['partyName']} (PAN: {cert['partyPan']}).\n\nCertificate Ref: {cert['certificateNumber']}\n"
                f"Template: {cert['templateTitle']}\nStatus: {cert['status'].upper()}\nUDIN: {cert.get('udin') or 'Pending'}\n\n"
                "This copy is sent to your designated CA email address for review, physical/digital signing, and record keeping.\n\n"
                "Regards,\nCertifyFlow Automated Mailer")
    return subj, body


def test_smtp(smtp):
    if not (smtp.get("host") and smtp.get("user") and smtp.get("password")):
        raise ValueError("Enter host, user and password first.")
    port = int(smtp.get("port") or 587)
    ctx = ssl.create_default_context()
    if smtp.get("secure") is True or port == 465:
        s = smtplib.SMTP_SSL(smtp["host"], port, timeout=20, context=ctx)
    else:
        s = smtplib.SMTP(smtp["host"], port, timeout=20)
        s.ehlo()
        if s.has_extn("starttls"):
            s.starttls(context=ctx)
            s.ehlo()
    try:
        s.login(smtp["user"], smtp["password"])
    finally:
        s.quit()
    return "SMTP login successful."


def calc_tax(taxable, home_state, party_state):
    taxable = max(0, taxable or 0)
    inter = home_state != party_state

    def rnd(x):  # JS Math.round
        return int(x + 0.5) if x >= 0 else -int(-x + 0.5)
    if inter:
        igst = rnd(taxable * 18.0 / 100)
        return dict(isInterState=True, cgstRate=0, cgstAmount=0, sgstRate=0, sgstAmount=0,
                    igstRate=18.0, igstAmount=igst, taxable=taxable, total=taxable + igst)
    c = rnd(taxable * 9.0 / 100)
    return dict(isInterState=False, cgstRate=9.0, cgstAmount=c, sgstRate=9.0, sgstAmount=c,
                igstRate=0, igstAmount=0, taxable=taxable, total=taxable + 2 * c)


def _q(s):
    return str(s).replace("'", "''")


def build_saral_sql(inv):
    pan = inv.get("partyPan") or ""
    name = _q(inv["partyName"])
    gstin = inv.get("partyGstin") or ""
    sac = inv.get("sacCode") or "998222"
    return f"""
-- =========================================================================
-- Saral Accounts (Relyon) Direct Sales Voucher Injection
-- Generated by CertifyFlow Bridge for Certificate: {inv.get('certificateNumber') or 'N/A'}
-- Party: {inv['partyName']} (PAN: {pan or 'N/A'}, GSTIN: {gstin or 'Unregistered'})
-- =========================================================================

BEGIN TRANSACTION;

DECLARE @PartyLedgerID INT;
SELECT @PartyLedgerID = LedgerID FROM dbo.Acc_LedgerMaster 
WHERE PAN = '{pan}' OR LedgerName LIKE '%{name}%';

IF @PartyLedgerID IS NULL
BEGIN
    -- Auto-trace party or create Ledger in Sundry Debtors
    INSERT INTO dbo.Acc_LedgerMaster (LedgerName, GroupID, PAN, GSTIN, StateCode, IsActive)
    VALUES ('{name}', 104, '{pan}', '{gstin}', '{(gstin or '27')[:2]}', 1);
    SET @PartyLedgerID = SCOPE_IDENTITY();
END

-- Insert Sales Voucher Header
INSERT INTO dbo.Acc_SalesVoucher (
    VoucherNo, VoucherDate, PartyID, ReferenceDoc, UDIN,
    TaxableAmount, CGST, SGST, IGST, TotalAmount, Remarks
) VALUES (
    '{inv['invoiceNumber']}',
    '{inv['invoiceDate']}',
    @PartyLedgerID,
    '{inv.get('certificateNumber') or ''}',
    '{inv.get('udin') or ''}',
    {js_num(inv['taxableAmount'])},
    {js_num(inv['cgstAmount'])},
    {js_num(inv['sgstAmount'])},
    {js_num(inv['igstAmount'])},
    {js_num(inv['totalAmount'])},
    'Professional fees for Certificate drafting - SAC {sac}'
);

-- Insert Item / Service Line (SAC {sac})
INSERT INTO dbo.Acc_SalesVoucherDetails (
    VoucherID, SACCode, Description, Qty, Rate, TaxableValue, CGSTRate, SGSTRate, IGSTRate
) VALUES (
    SCOPE_IDENTITY(),
    '{sac}',
    '{inv.get('hsnDescription') or 'Accounting & Certificate Services'}',
    1.0,
    {js_num(inv['taxableAmount'])},
    {js_num(inv['taxableAmount'])},
    {'9.0' if inv['cgstAmount'] else '0.0'},
    {'9.0' if inv['sgstAmount'] else '0.0'},
    {'18.0' if inv['igstAmount'] else '0.0'}
);

COMMIT TRANSACTION;
""".strip()


# ------------------------------------------------- Saral logins (SQL Server)
def saral_profiles(store):
    """List of Saral logins/companies. Migrates the old single 'saralConfig' on first use."""
    d = store.data
    if not d.get("saralProfiles"):
        c = {**DEFAULT_SARAL, **(d.get("saralConfig") or {})}
        d["saralProfiles"] = [{"name": "Default login", "host": c["host"], "port": c["port"],
                               "database": c["database"], "username": c["username"],
                               "password": c.get("password", ""), "windowsAuth": False}]
    return d["saralProfiles"]


def _odbc_driver(pyodbc):
    names = pyodbc.drivers()
    for pref in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server",
                 "ODBC Driver 13 for SQL Server", "SQL Server Native Client 11.0", "SQL Server"):
        if pref in names:
            return pref
    raise RuntimeError("No SQL Server ODBC driver found on this PC. Install 'ODBC Driver 17 for SQL Server' "
                       "from Microsoft, then try again.")


def saral_connect(p, timeout=8):
    try:
        import pyodbc
    except ImportError:
        raise RuntimeError("The 'pyodbc' package is not installed. Double-click INSTALL_SQL_SUPPORT.bat once "
                           "(needs internet), then restart the app.")
    drv = _odbc_driver(pyodbc)
    host = (p.get("host") or "localhost").strip()
    server = host if ("\\" in host or not p.get("port")) else f"{host},{p['port']}"
    parts = [f"DRIVER={{{drv}}}", f"SERVER={server}"]
    if p.get("database"):
        parts.append(f"DATABASE={p['database']}")
    if p.get("windowsAuth"):
        parts.append("Trusted_Connection=yes")
    else:
        parts.append(f"UID={p.get('username', '')}")
        parts.append("PWD={" + str(p.get("password", "")).replace("}", "}}") + "}")
    if "ODBC Driver 18" in drv:
        parts.append("Encrypt=no;TrustServerCertificate=yes")
    return pyodbc.connect(";".join(parts), timeout=timeout)


def saral_test(p):
    """Real login test: returns a human-readable summary."""
    cn = saral_connect(p)
    try:
        cur = cn.cursor()
        ver = cur.execute("SELECT @@VERSION").fetchone()[0].split("\n")[0]
        db = cur.execute("SELECT DB_NAME()").fetchone()[0]
        ntab = cur.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'").fetchone()[0]
        try:
            dbs = [r[0] for r in cur.execute(
                "SELECT name FROM sys.databases WHERE HAS_DBACCESS(name)=1 "
                "AND name NOT IN ('master','tempdb','model','msdb') ORDER BY name").fetchall()]
        except Exception:
            dbs = []
        out = f"Login OK.\n{ver}\nConnected database: {db} ({ntab} tables)"
        if dbs:
            out += "\nDatabases this login can open: " + ", ".join(dbs)
        return out
    finally:
        cn.close()


def saral_export_structure(p, path):
    """Write table/column structure + row counts (NO accounting data) to a text file."""
    cn = saral_connect(p, timeout=15)
    try:
        cur = cn.cursor()
        db = cur.execute("SELECT DB_NAME()").fetchone()[0]
        lines = [f"# Saral structure export | database={db} | {_dt.datetime.now():%Y-%m-%d %H:%M:%S}", "",
                 "## ROW COUNTS (schema.table <TAB> rows)"]
        try:
            for n, r in cur.execute(
                    "SELECT s.name + '.' + t.name, SUM(pt.rows) FROM sys.tables t "
                    "JOIN sys.schemas s ON s.schema_id = t.schema_id "
                    "JOIN sys.partitions pt ON pt.object_id = t.object_id AND pt.index_id IN (0,1) "
                    "GROUP BY s.name, t.name ORDER BY 1").fetchall():
                lines.append(f"{n}\t{r}")
        except Exception as e:
            lines.append(f"(row counts unavailable: {e})")
        lines += ["", "## COLUMNS (table <TAB> column <TAB> type <TAB> length <TAB> nullable)"]
        for r in cur.execute(
                "SELECT c.TABLE_SCHEMA + '.' + c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, "
                "c.CHARACTER_MAXIMUM_LENGTH, c.IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS c "
                "JOIN INFORMATION_SCHEMA.TABLES t ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_SCHEMA = c.TABLE_SCHEMA "
                "WHERE t.TABLE_TYPE = 'BASE TABLE' ORDER BY 1, c.ORDINAL_POSITION").fetchall():
            lines.append("\t".join("" if x is None else str(x) for x in r))
        lines += ["", "## PRIMARY / FOREIGN KEYS"]
        try:
            for r in cur.execute(
                    "SELECT kc.TABLE_SCHEMA + '.' + kc.TABLE_NAME, kc.COLUMN_NAME, tc.CONSTRAINT_TYPE "
                    "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kc "
                    "ON kc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' ORDER BY 1").fetchall():
                lines.append("PK\t" + "\t".join(str(x) for x in r))
            for r in cur.execute(
                    "SELECT OBJECT_NAME(fk.parent_object_id), cp.name, OBJECT_NAME(fk.referenced_object_id), cr.name "
                    "FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id "
                    "JOIN sys.columns cp ON cp.object_id = fkc.parent_object_id AND cp.column_id = fkc.parent_column_id "
                    "JOIN sys.columns cr ON cr.object_id = fkc.referenced_object_id AND cr.column_id = fkc.referenced_column_id "
                    "ORDER BY 1").fetchall():
                lines.append("FK\t" + "\t".join(str(x) for x in r))
        except Exception as e:
            lines.append(f"(keys unavailable: {e})")
    finally:
        cn.close()
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return f"Saved structure of '{db}' to {path}"


def post_invoice(store, cert, amount, sac, desc, date_str, profile_name=""):
    if not cert:
        raise ValueError("Please select an approved certificate to generate an invoice.")
    if (amount or 0) <= 0:
        raise ValueError("Please enter a valid invoice taxable amount greater than ₹0.")
    party = store.party(cert["partyId"]) or next(
        (p for p in store["parties"] if p["pan"] == cert["partyPan"]), None)
    home = store["caDetails"].get("stateCode") or "27"
    pstate = (cert.get("partyGstin") or "")[:2] or (party or {}).get("stateCode") or "27"
    t = calc_tax(amount, home, pstate)
    inv = {
        "id": uid("inv"), "invoiceNumber": new_invoice_number(), "invoiceDate": date_str,
        "certificateId": cert["id"], "certificateNumber": cert["certificateNumber"],
        "partyId": cert["partyId"], "partyName": cert["partyName"], "partyPan": cert["partyPan"],
        "partyGstin": cert.get("partyGstin", ""), "partyAddress": cert.get("partyAddress", ""),
        "partyStateCode": pstate, "taxableAmount": t["taxable"], "sacCode": sac,
        "hsnDescription": desc, "isInterState": t["isInterState"],
        "cgstRate": t["cgstRate"], "cgstAmount": t["cgstAmount"], "sgstRate": t["sgstRate"],
        "sgstAmount": t["sgstAmount"], "igstRate": t["igstRate"], "igstAmount": t["igstAmount"],
        "totalAmount": t["total"], "saralSyncStatus": "staged", "saralProfile": profile_name,
        "saralVoucherNo": f"SARAL-SLS-{str(int(time.time() * 1000))[-6:]}",
        "createdDate": now_iso(), "udin": cert.get("udin"),
    }
    inv["sqlScript"] = build_saral_sql(inv)
    store["invoices"].insert(0, inv)
    cert["invoiceGenerated"] = True
    cert["invoiceNumber"] = inv["invoiceNumber"]
    store.save()
    return inv


def test_saral_connection(cfg):
    import socket
    host, port = cfg.get("host") or "localhost", int(cfg.get("port") or 1433)
    try:
        with socket.create_connection((host, port), timeout=3):
            return f"SQL Server port reachable at {host}:{port}. Database: {cfg.get('database')}."
    except OSError as e:
        raise ConnectionError(f"Cannot reach {host}:{port} ({e}). Is SQL Server running?")


# ------------------------------------------------------------- party CSV
PARTY_FIELDS = ["id", "name", "tradeName", "pan", "gstin", "stateCode", "stateName", "address",
                "email", "phone", "contactPerson", "saralLedgerCode", "defaultFee"]


def parties_to_csv(path, parties):
    import csv
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=PARTY_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(parties)


def parties_from_csv(path):
    import csv
    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if not (row.get("name") or "").strip():
                continue
            p = {k: (row.get(k) or "").strip() for k in PARTY_FIELDS}
            p["id"] = p["id"] or f"pty-{int(time.time() * 1000)}-{i}"
            p["defaultFee"] = pf(p["defaultFee"], 15000) or 15000
            if not p["stateCode"] and len(p["gstin"]) >= 2:
                p["stateCode"] = p["gstin"][:2]
            out.append(p)
    return out
