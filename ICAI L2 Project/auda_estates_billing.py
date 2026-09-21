"""AUDA ESTATES Billing Desk - a single-file, offline billing application.

Run with:  python auda_estates_billing.py
First sign-in: admin / admin123  (change it from the Users screen)

Everything is stored in auda_estates.sqlite3 beside this file.  The app uses
only Python's standard library and starts with fictional member records.
"""
import csv
import hashlib
import os
import shutil
import sqlite3
import tempfile
import webbrowser
import subprocess
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
import zipfile
import xml.etree.ElementTree as ET
from calendar import monthrange
from pathlib import Path
from datetime import date, datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from html import escape

APP = "AUDA ESTATES"
HERE = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(HERE, "auda_estates.sqlite3")


def money(value):
    return f"₹ {float(value or 0):,.2f}"


def today():
    return date.today().isoformat()


def month_end(period):
    """Accept YYYY-MM or any ISO date and return the month's final calendar day."""
    year, month = map(int, period[:7].split("-"))
    return f"{year:04d}-{month:02d}-{monthrange(year, month)[1]:02d}"


def column_letter(number):
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def save_xlsx(path, sheets):
    """Create a simple, portable Excel workbook without a third-party module."""
    def cell(ref, value):
        if isinstance(value, (int, float)) and not isinstance(value, bool): return f'<c r="{ref}"><v>{value}</v></c>'
        text = escape(str(value or "")); return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'
    worksheet_xml = []
    for _, rows in sheets:
        body = "".join(f'<row r="{idx}">' + "".join(cell(f"{column_letter(col)}{idx}", value) for col, value in enumerate(row, 1)) + "</row>" for idx, row in enumerate(rows, 1))
        worksheet_xml.append(f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{body}</sheetData></worksheet>')
    content_types = ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets)+1))
    sheet_names = ''.join(f'<sheet name="{escape(name[:31])}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_) in enumerate(sheets,1))
    sheet_rels = ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as book:
        book.writestr("[Content_Types].xml", f'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{content_types}</Types>')
        book.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        book.writestr("xl/workbook.xml", f'<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{sheet_names}</sheets></workbook>')
        book.writestr("xl/_rels/workbook.xml.rels", f'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{sheet_rels}</Relationships>')
        for i, xml in enumerate(worksheet_xml, 1): book.writestr(f"xl/worksheets/sheet{i}.xml", xml)


def save_ledger_pdf(path, reports):
    """Produce a printable plain-text PDF ledger, including one section/page per member."""
    pages = []
    for member, entries in reports:
        lines = [APP, "MEMBER LEDGER", f"Member: {member['name']} ({member['code']})", f"Plot: {member['plot'] or '-'}", "", "Date        Particulars                         Reference       Debit       Credit     Balance", "-" * 88]
        for row in entries:
            lines.append(f"{row['entry_date']:<11} {row['particulars'][:34]:<34} {(row['reference'] or '')[:12]:<12} {float(row['debit']):>10.2f} {float(row['credit']):>10.2f} {float(row['balance']):>10.2f}")
        if not entries: lines.append("No ledger entries.")
        lines.append(""); lines.append(f"Outstanding balance: Rs. {float(entries[-1]['balance']) if entries else 0:,.2f}")
        pages.append(lines)
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", ""]
    page_ids=[]
    for lines in pages:
        content = "BT /F1 10 Tf 40 800 Td " + " ".join("(" + line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1", "replace").decode("latin-1") + ") Tj 0 -14 Td" for line in lines[:52]) + " ET"
        page_id=len(objects)+1; content_id=page_id+1; page_ids.append(page_id)
        objects.extend([f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {content_id+1} 0 R >> >> /Contents {content_id} 0 R >>", f"<< /Length {len(content.encode('latin-1'))} >>\nstream\n{content}\nendstream", "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"])
    objects[1] = "<< /Type /Pages /Kids [" + " ".join(f"{i} 0 R" for i in page_ids) + f"] /Count {len(page_ids)} >>"
    data = "%PDF-1.4\n"; offsets=[0]
    for i,obj in enumerate(objects,1): offsets.append(len(data.encode("latin-1"))); data += f"{i} 0 obj\n{obj}\nendobj\n"
    start=len(data.encode("latin-1")); data += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets[1:]) + f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF"
    Path(path).write_bytes(data.encode("latin-1"))


def save_document_batch_pdf(path, documents):
    """Render saved A4 invoice/receipt HTML layouts as one multi-page PDF."""
    if HAS_REPORTLAB:
        pdf=canvas.Canvas(path,pagesize=A4); width,height=A4
        for d in documents:
            title="TAX INVOICE" if d["doc_type"]=="Invoice" else "RECEIPT"
            pdf.setFont("Helvetica-Bold",18); pdf.drawCentredString(width/2,height-55,APP)
            pdf.setFont("Helvetica-Bold",15); pdf.drawCentredString(width/2,height-82,title)
            pdf.line(45,height-95,width-45,height-95); pdf.setFont("Helvetica",11)
            y=height-125
            for text in (f"{d['doc_type']} No: {d['number']}",f"Date: {d['doc_date']}",f"Member: {d['member_name']}",f"Description: {d['description']}",f"Amount: Rs. {float(d['amount']):,.2f}",f"Amount in words: {number_words(d['amount'])}"):
                pdf.drawString(55,y,text[:100]); y-=28
            pdf.line(55,y-8,width-55,y-8); pdf.setFont("Helvetica-Bold",12); pdf.drawRightString(width-55,y-35,f"Grand Total: Rs. {float(d['amount']):,.2f}")
            pdf.setFont("Helvetica",10); pdf.drawString(55,55,"This is a system-generated document from AUDA ESTATES."); pdf.showPage()
        pdf.save(); return
    html_path=os.path.join(tempfile.gettempdir(),"auda_estates_batch_print.html")
    pages=[]
    for d in documents:
        body=d["html"]
        start=body.find("<body>"); end=body.rfind("</body>")
        content=body[start+6:end] if start>=0 and end>=0 else body
        style=body[body.find("<style>"):body.find("</style>")+8] if "<style>" in body else ""
        pages.append(f"<section class='batch-page'>{style}{content}</section>")
    with open(html_path,"w",encoding="utf-8") as f: f.write("<html><head><style>@page{size:A4;margin:10mm}.batch-page{page-break-after:always}</style></head><body>"+"".join(pages)+"</body></html>")
    edge=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    profile=os.path.join(tempfile.gettempdir(),"auda_estates_pdf_profile")
    result=subprocess.run([edge,"--headless","--disable-gpu",f"--user-data-dir={profile}",f"--print-to-pdf={path}","file:///"+html_path.replace("\\","/")],capture_output=True,timeout=45)
    if result.returncode==0 and os.path.exists(path): return
    raise RuntimeError("Could not create the formatted PDF batch.")
    """Create one A4 page per generated invoice or receipt - never a ledger."""
    objects=["<< /Type /Catalog /Pages 2 0 R >>", ""]; page_ids=[]
    for d in documents:
        title="TAX INVOICE" if d["doc_type"]=="Invoice" else "RECEIPT"
        lines=[APP,title,"",f"{d['doc_type']} No: {d['number']}",f"Date: {d['doc_date']}",f"Member: {d['member_name']}","",f"Description: {d['description']}",f"Amount: Rs. {float(d['amount']):,.2f}","",f"Amount in words: {number_words(d['amount'])}","","This is a system-generated document."]
        text="BT /F1 13 Tf 50 790 Td " + " ".join("("+line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)').encode('latin-1','replace').decode('latin-1')+") Tj 0 -24 Td" for line in lines)+" ET"
        page_id=len(objects)+1; content_id=page_id+1; page_ids.append(page_id)
        objects.extend([f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {content_id+1} 0 R >> >> /Contents {content_id} 0 R >>",f"<< /Length {len(text.encode('latin-1'))} >>\nstream\n{text}\nendstream","<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"])
    objects[1]="<< /Type /Pages /Kids ["+" ".join(f"{i} 0 R" for i in page_ids)+f"] /Count {len(page_ids)} >>"
    data="%PDF-1.4\n"; offsets=[0]
    for i,obj in enumerate(objects,1): offsets.append(len(data.encode('latin-1'))); data+=f"{i} 0 obj\n{obj}\nendobj\n"
    start=len(data.encode('latin-1')); data+=f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"+"".join(f"{o:010d} 00000 n \n" for o in offsets[1:])+f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF"
    Path(path).write_bytes(data.encode('latin-1'))

def save_documents_pdf(path, documents):
    """Write a single multi-page PDF summary for a generated invoice/receipt batch."""
    reports=[]
    for d, member in documents:
        rows=[{"entry_date":d["doc_date"],"particulars":d["description"],"reference":d["number"],"debit":d["amount"] if d["doc_type"]=="Invoice" else 0,"credit":d["amount"] if d["doc_type"]=="Receipt" else 0,"balance":0}]
        reports.append((member,rows))
    save_ledger_pdf(path,reports)


def xlsx_rows(path):
    """Read plain-value Excel sheets without requiring an external package."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as book:
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ET.fromstring(book.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in node.iter(ns + "t")) for node in root.findall(ns + "si")]
        sheet_name = next(n for n in book.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        root = ET.fromstring(book.read(sheet_name)); result = []
        for row in root.iter(ns + "row"):
            values = []
            for cell in row.findall(ns + "c"):
                letters = "".join(ch for ch in cell.get("r", "A1") if ch.isalpha())
                column = 0
                for char in letters: column = column * 26 + ord(char.upper()) - 64
                while len(values) < column: values.append("")
                cell_type = cell.get("t"); value = cell.findtext(ns + "v", "")
                if cell_type == "s": value = shared[int(value)] if value else ""
                elif cell_type == "inlineStr": value = "".join(t.text or "" for t in cell.iter(ns + "t"))
                values[column - 1] = value
            result.append(values)
    if not result: return []
    header_at = next((i for i, row in enumerate(result) if "code" in row or "member_code" in row), 0)
    headers = [str(x).strip() for x in result[header_at]]
    return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in result[header_at + 1:] if any(str(x).strip() for x in row)]


def number_words(n):
    # A compact Indian-number formatter for document wording.
    ones = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    def below_100(x): return ones[x] if x < 20 else tens[x//10] + (" " + ones[x % 10] if x % 10 else "")
    def below_1000(x): return (ones[x//100] + " Hundred " if x >= 100 else "") + (below_100(x % 100) if x % 100 else "")
    n = int(round(float(n)))
    if n == 0: return "Zero Rupees Only"
    parts = []
    for divisor, label in ((10000000, "Crore"), (100000, "Lakh"), (1000, "Thousand")):
        if n >= divisor:
            parts.append(below_100(n // divisor) + " " + label); n %= divisor
    if n: parts.append(below_1000(n))
    return " ".join(parts) + " Rupees Only"


class Store:
    def __init__(self):
        self.db = sqlite3.connect(DB_FILE)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.setup()

    def setup(self):
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, display_name TEXT);
        CREATE TABLE IF NOT EXISTS members (
          id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
          plot TEXT, address TEXT, gstin TEXT, phone TEXT, active INTEGER DEFAULT 1, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents (
          id INTEGER PRIMARY KEY AUTOINCREMENT, doc_type TEXT NOT NULL, number TEXT UNIQUE NOT NULL,
          member_id INTEGER NOT NULL, doc_date TEXT NOT NULL, period TEXT, amount REAL NOT NULL,
          description TEXT, payment_mode TEXT, reference_no TEXT, payment_date TEXT, status TEXT DEFAULT 'Active',
          html TEXT, created_at TEXT NOT NULL, reversed_at TEXT, FOREIGN KEY(member_id) REFERENCES members(id));
        CREATE TABLE IF NOT EXISTS ledger (
          id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, entry_date TEXT NOT NULL,
          particulars TEXT NOT NULL, reference TEXT, debit REAL DEFAULT 0, credit REAL DEFAULT 0,
          balance REAL NOT NULL, document_id INTEGER, created_at TEXT NOT NULL,
          FOREIGN KEY(member_id) REFERENCES members(id), FOREIGN KEY(document_id) REFERENCES documents(id));
        """)
        # Safe migration for databases made by earlier versions of this file.
        existing = {r["name"] for r in self.all("PRAGMA table_info(members)")}
        if "connection_size" not in existing: self.db.execute("ALTER TABLE members ADD COLUMN connection_size TEXT DEFAULT '20MM'")
        if "plot_area" not in existing: self.db.execute("ALTER TABLE members ADD COLUMN plot_area REAL DEFAULT 0")
        document_columns = {r["name"] for r in self.all("PRAGMA table_info(documents)")}
        if "payment_date" not in document_columns: self.db.execute("ALTER TABLE documents ADD COLUMN payment_date TEXT")
        if not self.one("SELECT username FROM users WHERE username='admin'"):
            self.db.execute("INSERT INTO users VALUES (?,?,?)", ("admin", self.hash("admin123"), "Administrator"))
        if not self.one("SELECT id FROM members LIMIT 1"):
            rows = [("AE-001", "Aarav Shah", "A-101", "12 Garden Avenue, Ahmedabad", "24AAAAA0000A1Z5", "9000000001", 1, today(), "20MM", 180),
                    ("AE-002", "Diya Mehta", "B-204", "45 Lake Road, Ahmedabad", "24BBBBB0000B1Z6", "9000000002", 1, today(), "30MM", 245),
                    ("AE-003", "Kabir Patel", "C-309", "8 Sunrise Lane, Ahmedabad", "24CCCCC0000C1Z7", "9000000003", 1, today(), "40MM", 325)]
            self.db.executemany("INSERT INTO members(code,name,plot,address,gstin,phone,active,created_at,connection_size,plot_area) VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
        self.db.commit()

    @staticmethod
    def hash(password): return hashlib.sha256(password.encode()).hexdigest()
    def one(self, sql, args=()): return self.db.execute(sql, args).fetchone()
    def all(self, sql, args=()): return self.db.execute(sql, args).fetchall()
    def next_number(self, kind):
        prefix = {"Invoice":"INV", "Receipt":"RCP", "Credit Note":"CRN"}[kind]
        last = self.one("SELECT number FROM documents WHERE doc_type=? ORDER BY id DESC LIMIT 1", (kind,))
        seq = int(last["number"].split("-")[-1]) + 1 if last else 1
        return f"{prefix}-{date.today():%Y}-{seq:04d}"
    def balance(self, member_id):
        r = self.one("SELECT balance FROM ledger WHERE member_id=? ORDER BY id DESC LIMIT 1", (member_id,))
        return float(r["balance"]) if r else 0.0
    def add_ledger(self, member_id, entry_date, particulars, reference, debit=0, credit=0, doc_id=None):
        balance = round(self.balance(member_id) + float(debit) - float(credit), 2)
        self.db.execute("INSERT INTO ledger(member_id,entry_date,particulars,reference,debit,credit,balance,document_id,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                        (member_id, entry_date, particulars, reference, debit, credit, balance, doc_id, datetime.now().isoformat(timespec="seconds")))

    def add_document(self, doc_type, member_id, doc_date, amount, description, period="", payment_mode="", reference_no="", document_no="", payment_date=""):
        number = document_no.strip() or self.next_number(doc_type)
        if self.one("SELECT id FROM documents WHERE number=?", (number,)): raise ValueError(f"Document number {number} already exists.")
        cur = self.db.execute("INSERT INTO documents(doc_type,number,member_id,doc_date,period,amount,description,payment_mode,reference_no,payment_date,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                              (doc_type, number, member_id, doc_date, period, amount, description, payment_mode, reference_no, payment_date, datetime.now().isoformat(timespec="seconds")))
        doc_id = cur.lastrowid
        member = self.one("SELECT * FROM members WHERE id=?", (member_id,))
        html = self.receipt_html(number, member, doc_date, amount, description, payment_mode, reference_no, payment_date) if doc_type == "Receipt" else self.document_html(doc_type, number, member, doc_date, amount, description, period, payment_mode, reference_no)
        self.db.execute("UPDATE documents SET html=? WHERE id=?", (html, doc_id))
        if doc_type == "Invoice": self.add_ledger(member_id, doc_date, f"Invoice raised: {description}", number, debit=amount, doc_id=doc_id)
        elif doc_type == "Receipt": self.add_ledger(member_id, doc_date, f"Receipt received: {description}", number, credit=amount, doc_id=doc_id)
        else: self.add_ledger(member_id, doc_date, f"Credit note issued: {description}", number, credit=amount, doc_id=doc_id)
        self.db.commit()
        return doc_id

    def reverse(self, doc_id):
        d = self.one("SELECT * FROM documents WHERE id=?", (doc_id,))
        if not d or d["status"] != "Active": raise ValueError("Only active documents can be reversed.")
        if d["doc_type"] != "Receipt": raise ValueError("Only receipts can be reversed individually.")
        if d["doc_type"] == "Invoice": debit, credit = 0, d["amount"]
        else: debit, credit = d["amount"], 0
        self.add_ledger(d["member_id"], today(), f"Reversal of {d['doc_type']} {d['number']}", d["number"], debit, credit, doc_id)
        self.db.execute("UPDATE documents SET status='Reversed', reversed_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), doc_id))
        self.db.commit()

    def erase_entries_from(self, entered_from):
        stamp = datetime.strptime(entered_from, "%Y-%m-%d").strftime("%Y-%m-%d")
        self.db.execute("DELETE FROM ledger WHERE created_at >= ?", (stamp,))
        self.db.execute("DELETE FROM documents WHERE created_at >= ?", (stamp,))
        self.db.execute("DELETE FROM members WHERE created_at >= ?", (stamp,))
        self.db.commit()

    def add_monthly_invoice(self, member_id, billing_period, maintenance_rate, past_reading, present_reading, interest_penalty=0, invoice_no=None, invoice_date=None):
        member = self.one("SELECT * FROM members WHERE id=?", (member_id,))
        if not member: raise ValueError("Member was not found.")
        invoice_date = invoice_date or month_end(billing_period)
        datetime.strptime(invoice_date, "%Y-%m-%d")
        period = invoice_date[:7]
        if self.one("SELECT id FROM documents WHERE doc_type='Invoice' AND member_id=? AND period=?", (member_id, period)):
            raise ValueError(f"An invoice already exists for {member['name']} for {period}.")
        past, present = float(past_reading), float(present_reading)
        if past < 0 or present < past: raise ValueError("Present meter reading must be at least the past meter reading.")
        connection = (member["connection_size"] or "20MM").upper()
        minimum = {"20MM": 300, "30MM": 350, "40MM": 400}.get(connection)
        if minimum is None: raise ValueError("Member water connection size must be 20MM, 30MM, or 40MM.")
        maintenance = round(float(member["plot_area"] or 0) * float(maintenance_rate), 2)
        units = present - past
        water = round(max(units * 5, minimum), 2)
        interest = round(float(interest_penalty or 0), 2)
        if interest < 0: raise ValueError("Interest penalty cannot be negative.")
        lines = [("Yearly Maintenance Charges", maintenance, f"{member['plot_area'] or 0:g} sq mtr × {money(maintenance_rate)}"),
                 ("Monthly Water Charges", water, f"{units:g} units × ₹ 5.00; minimum {money(minimum)} for {connection}"),
                 ("Interest Penalty", interest, "")]
        lines = [line for line in lines if line[1] != 0]
        taxable = round(sum(line[1] for line in lines) + interest, 2); gst = round(taxable * .18, 2); total = float(round(taxable + gst))
        number = (invoice_no or self.next_number("Invoice")).strip()
        if not number: raise ValueError("Invoice number is required.")
        if self.one("SELECT id FROM documents WHERE number=?", (number,)): raise ValueError(f"Invoice number {number} already exists.")
        previous_outstanding = self.balance(member_id)
        details = f"Monthly invoice for {period}; past meter {past:g}, present meter {present:g}"
        cur = self.db.execute("INSERT INTO documents(doc_type,number,member_id,doc_date,period,amount,description,created_at) VALUES(?,?,?,?,?,?,?,?)",
            ("Invoice", number, member_id, invoice_date, period, total, details, datetime.now().isoformat(timespec="seconds")))
        doc_id = cur.lastrowid
        html = self.invoice_html(number, member, invoice_date, period, lines, taxable, gst, total, previous_outstanding)
        self.db.execute("UPDATE documents SET html=? WHERE id=?", (html, doc_id))
        self.add_ledger(member_id, invoice_date, "Monthly invoice raised", number, debit=total, doc_id=doc_id)
        self.db.commit()
        return doc_id

    def invoice_html(self, number, m, invoice_date, period, lines, taxable, gst, total, previous):
        entries = "".join(f"<tr><td class='center'>{index}</td><td><b>{escape(name)}</b><br><span>{escape(note)}</span></td><td class='center'>999999</td><td class='center'>18%</td><td class='amount'>{float(amount):,.2f}</td></tr>" for index,(name,amount,note) in enumerate(lines,1))
        cgst = round(gst / 2, 2); current = previous + total
        return f"""<!doctype html><html><head><meta charset='utf-8'><title>Invoice {number}</title><style>
        @page{{size:A4;margin:15mm}}body{{font-family:Arial,sans-serif;color:#111;font-size:14px}}.page{{width:760px;margin:auto}}.company{{text-align:center;border-bottom:1px solid #333;padding-bottom:10px}}.company h1{{margin:4px 0;font-size:21px}}.company p{{margin:3px 0;font-size:15px}}h2{{text-align:center;font-size:20px;margin:12px 0}}.meta{{width:100%;margin:10px 0;border-collapse:collapse}}.meta td{{padding:3px}}table.grid{{width:100%;border-collapse:collapse;margin-top:12px}}.grid th,.grid td{{border:1px solid #222;padding:7px;vertical-align:top}}.grid th{{text-align:center}}.center{{text-align:center}}.amount{{text-align:right;white-space:nowrap}}span{{display:block;font-size:12px;line-height:1.5;margin-top:5px}}.totals td{{border-top:0;border-bottom:0;padding:3px 7px}}.summary{{width:60%;margin:20px auto;border-collapse:collapse}}.summary td{{border:1px solid #222;padding:5px;text-align:center}}.notes{{margin-top:26px;font-size:12px;line-height:1.5}}.sign{{text-align:right;margin-top:35px;font-size:14px}}</style></head><body><div class='page'>
        <div class='company'><h1>{APP}</h1><p>Estate Office, Ahmedabad - 380001</p><p><b>GST:</b> 24AUDAE0000A1Z5 &nbsp;&nbsp; <b>Email:</b> accounts@audaestates.example</p></div><h2>Tax Invoice</h2>
        <table class='meta'><tr><td><b>Invoice No:</b> {number}</td><td class='amount'><b>Invoice Date:</b> {invoice_date}</td></tr><tr><td colspan='2'><b>Party name:</b> {escape(m['name'])}<br><b>Plot:</b> {escape(m['plot'] or '-')} &nbsp; <b>Address:</b> {escape(m['address'] or '-')}<br><b>GST:</b> {escape(m['gstin'] or 'N.A.')} &nbsp; <b>Billing month:</b> {period}</td></tr></table>
        <table class='grid'><tr><th>Sr.<br>No.</th><th>Particulars</th><th>SAC</th><th>Tax<br>Rate</th><th>Amount</th></tr>{entries}<tr class='totals'><td colspan='4' class='amount'><b>Total</b></td><td class='amount'>{taxable:,.2f}</td></tr><tr class='totals'><td colspan='4' class='amount'><b>CGST</b></td><td class='amount'>{cgst:,.2f}</td></tr><tr class='totals'><td colspan='4' class='amount'><b>SGST</b></td><td class='amount'>{cgst:,.2f}</td></tr><tr><td colspan='4' class='amount'><b>Grand Total</b></td><td class='amount'><b>{total:,.2f}</b></td></tr><tr><td colspan='5'><b>Amount in words:</b> {number_words(total)}</td></tr></table>
        <table class='summary'><tr><td><b>Previous Outstanding</b></td><td>{money(previous)}</td></tr><tr><td><b>Current Invoice</b></td><td>{money(total)}</td></tr><tr><td><b>Current Outstanding</b></td><td>{money(current)}</td></tr></table><div class='notes'>The charges shown above should be paid within 15 days. Interest penalty may apply thereafter according to estate rules.</div><div class='sign'>For, {APP}<br><br><br>Manager</div></div></body></html>"""

    def receipt_html(self, number, m, receipt_date, amount, description, mode, reference, payment_date=""):
        payment = escape(mode or "Payment")
        if reference: payment += " reference no. " + escape(reference)
        copy = f"""<section class='copy'><div class='company'><h1>{APP}</h1><p>Estate Office, Ahmedabad - 380001</p><p><b>GST:</b> 24AUDAE0000A1Z5 &nbsp;&nbsp; <b>Email:</b> accounts@audaestates.example</p></div><h2>RECEIPT</h2><table><tr><td><b>Receipt No: {number}</b><br><b>Receipt Date: {receipt_date}</b><br><b>Payment Date: {payment_date or receipt_date}</b></td><td class='amount'><b>Amount: {money(amount)}/-</b></td></tr></table><p>Received from <b>Plot No. {escape(m['plot'] or '-')} {escape(m['name'])}</b> a sum of <b>{money(amount)}/- ({number_words(amount)})</b> vide {payment}.</p><p>{escape(description)}</p><div class='sign'>____________________<br>Manager</div></section>"""
        return f"""<!doctype html><html><head><meta charset='utf-8'><title>Receipt {number}</title><style>@page{{size:A4;margin:15mm}}body{{font-family:Arial,sans-serif;color:#111;font-size:16px}}.page{{width:760px;margin:auto}}.copy{{padding:3px 0 26px}}.copy:first-child{{border-bottom:1px dashed #555;margin-bottom:25px}}.company{{text-align:center;border-bottom:1px solid #333;padding-bottom:7px}}.company h1{{font-size:20px;margin:0}}.company p{{font-size:14px;margin:3px}}h2{{text-align:center;font-size:19px;margin:9px}}table{{width:100%}}td{{vertical-align:top;line-height:1.6}}.amount{{text-align:right}}p{{font-size:17px;line-height:1.45;margin:13px 0}}.sign{{text-align:center;width:250px;margin:30px auto 0}}</style></head><body><div class='page'>{copy}{copy}</div></body></html>"""

    def document_html(self, kind, number, m, doc_date, amount, description, period, mode, ref):
        label = kind.upper()
        extra = f"<tr><th>Billing period</th><td>{escape(period)}</td></tr>" if period else ""
        if kind == "Receipt": extra += f"<tr><th>Payment mode</th><td>{escape(mode)}</td></tr><tr><th>Reference</th><td>{escape(ref or '-')}</td></tr>"
        return f"""<!doctype html><html><head><meta charset='utf-8'><title>{label} {number}</title><style>
        body{{font-family:Arial,sans-serif;margin:48px;color:#182535}} .head{{border-bottom:3px solid #126c64;padding-bottom:14px}} h1{{color:#126c64;margin:0}} .right{{float:right;text-align:right}} table{{width:100%;border-collapse:collapse;margin-top:26px}} th,td{{border:1px solid #8ea4a3;padding:11px;text-align:left}} th{{background:#e8f3f1}} .total{{font-size:20px;font-weight:bold;text-align:right}} footer{{margin-top:48px;border-top:1px solid #aaa;padding-top:12px;color:#555}}</style></head><body>
        <div class='head'><div class='right'><b>{label}</b><br>{number}<br>{doc_date}</div><h1>{APP}</h1><div>Property billing and member accounts</div></div>
        <h2>Member details</h2><table><tr><th>Member</th><td>{escape(m['name'])} ({escape(m['code'])})</td></tr><tr><th>Plot / Unit</th><td>{escape(m['plot'] or '-')}</td></tr><tr><th>Address</th><td>{escape(m['address'] or '-')}</td></tr><tr><th>GSTIN</th><td>{escape(m['gstin'] or '-')}</td></tr>{extra}</table>
        <h2>Charge details</h2><table><tr><th>Description</th><th>Amount</th></tr><tr><td>{escape(description)}</td><td>{money(amount)}</td></tr></table><p class='total'>Total: {money(amount)}</p><p>Amount in words: <b>{number_words(amount)}</b></p><footer>This is a system-generated {kind.lower()} from {APP}.</footer></body></html>"""


class BillingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.store = Store(); self.user = None
        self.title(f"{APP} | Billing Desk"); self.geometry("1180x720"); self.minsize(950, 600)
        self.style = ttk.Style(self); self.style.theme_use("clam")
        self.style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground="#126c64")
        self.style.configure("Treeview", rowheight=28); self.style.configure("Accent.TButton", padding=7)
        self.login()

    def clear(self):
        for w in self.winfo_children(): w.destroy()
    def login(self):
        self.clear(); frame = ttk.Frame(self, padding=50); frame.place(relx=.5, rely=.5, anchor="center")
        ttk.Label(frame, text=APP, style="Title.TLabel").grid(row=0, column=0, columnspan=2, pady=(0,8))
        ttk.Label(frame, text="Billing Desk", font=("Segoe UI", 12)).grid(row=1, column=0, columnspan=2, pady=(0,24))
        ttk.Label(frame, text="Username").grid(row=2, column=0, sticky="w", pady=6); username = ttk.Entry(frame, width=28); username.grid(row=2, column=1, pady=6)
        ttk.Label(frame, text="Password").grid(row=3, column=0, sticky="w", pady=6); password = ttk.Entry(frame, width=28, show="●"); password.grid(row=3, column=1, pady=6)
        def submit(*_):
            u = self.store.one("SELECT * FROM users WHERE username=?", (username.get().strip(),))
            if u and u["password"] == self.store.hash(password.get()): self.user=u; self.home()
            else: messagebox.showerror(APP, "Invalid username or password.")
        ttk.Button(frame, text="Sign in", command=submit, style="Accent.TButton").grid(row=4, column=0, columnspan=2, pady=18)
        ttk.Label(frame, text="Initial sign-in: admin / admin123", foreground="#666").grid(row=5, column=0, columnspan=2)
        username.focus(); self.bind("<Return>", submit)

    def home(self):
        self.clear(); self.unbind("<Return>")
        top=ttk.Frame(self,padding=(22,16)); top.pack(fill="x")
        ttk.Label(top,text=APP,style="Title.TLabel").pack(side="left")
        ttk.Button(top,text="Refresh",command=self.home).pack(side="right",padx=8)
        ttk.Label(top,text=f"Signed in as {self.user['display_name'] or self.user['username']}").pack(side="right", padx=12)
        ttk.Button(top,text="Sign out",command=self.login).pack(side="right")
        book=ttk.Notebook(self); book.pack(fill="both",expand=True,padx=18,pady=(0,18))
        self.dashboard_tab(book); self.members_tab(book); self.invoice_upload_tab(book); self.receipt_upload_tab(book); self.register_tab(book); self.ledger_tab(book); self.tools_tab(book)

    def tab(self, book, title):
        f=ttk.Frame(book,padding=18); book.add(f,text=title); return f
    def dashboard_tab(self, book):
        f=self.tab(book,"Dashboard")
        active=self.store.one("SELECT COUNT(*) c FROM members WHERE active=1")["c"]
        outstanding=self.store.one("SELECT COALESCE(SUM(balance),0) b FROM (SELECT member_id,balance FROM ledger GROUP BY member_id HAVING id=MAX(id))")["b"]
        docs=self.store.one("SELECT COUNT(*) c FROM documents WHERE status='Active'")["c"]
        for label,value in (("Active members",active),("Outstanding balance",money(outstanding)),("Active documents",docs)):
            card=ttk.LabelFrame(f,text=label,padding=24); card.pack(side="left",padx=10,pady=10,fill="x",expand=True); ttk.Label(card,text=str(value),font=("Segoe UI",20,"bold")).pack()
        ttk.Label(f,text="Use the tabs to maintain members, issue documents, review registers and export a backup.",font=("Segoe UI",12)).pack(anchor="w",pady=32)

    def members_tab(self, book):
        f=self.tab(book,"Members"); bar=ttk.Frame(f); bar.pack(fill="x",pady=(0,10))
        tree=self.tree(f,("Code","Name","Plot","Area (sq mtr)","Connection","Phone","Status"),(100,190,100,110,100,135,80)); tree.pack(fill="both",expand=True)
        def refresh():
            tree.delete(*tree.get_children())
            for r in self.store.all("SELECT * FROM members ORDER BY code"):
                tree.insert("","end",iid=r["id"],values=(r["code"],r["name"],r["plot"],r["plot_area"],r["connection_size"],r["phone"],"Active" if r["active"] else "Inactive"))
        def edit(existing=None):
            r=self.store.one("SELECT * FROM members WHERE id=?",(existing,)) if existing else None
            dialog=tk.Toplevel(self); dialog.title("Edit member" if r else "Add member"); dialog.transient(self); dialog.grab_set(); form=ttk.Frame(dialog,padding=18); form.pack()
            fields=[("Member code","code"),("Name","name"),("Plot / unit","plot"),("Plot area (sq mtr)","plot_area"),("Address","address"),("GSTIN","gstin"),("Phone","phone")]; entries={}
            for i,(label,key) in enumerate(fields):
                ttk.Label(form,text=label).grid(row=i,column=0,sticky="w",padx=(0,10),pady=5); e=ttk.Entry(form,width=42); e.grid(row=i,column=1,pady=5); e.insert(0,r[key] if r else ""); entries[key]=e
            ttk.Label(form,text="Water connection").grid(row=7,column=0,sticky="w",padx=(0,10),pady=5)
            connection=ttk.Combobox(form,values=("20MM","30MM","40MM"),state="readonly",width=39); connection.set(r["connection_size"] if r and r["connection_size"] else "20MM"); connection.grid(row=7,column=1,sticky="w",pady=5)
            active=tk.IntVar(value=r["active"] if r else 1); ttk.Checkbutton(form,text="Active member",variable=active).grid(row=8,column=1,sticky="w")
            def save():
                data=[entries[k].get().strip() for _,k in fields]
                if not data[0] or not data[1]: return messagebox.showerror(APP,"Member code and name are required.",parent=dialog)
                try: data[3]=float(data[3] or 0)
                except ValueError: return messagebox.showerror(APP,"Plot area must be a number.",parent=dialog)
                try:
                    if r: self.store.db.execute("UPDATE members SET code=?,name=?,plot=?,plot_area=?,address=?,gstin=?,phone=?,connection_size=?,active=? WHERE id=?",(*data,connection.get(),active.get(),r["id"]))
                    else: self.store.db.execute("INSERT INTO members(code,name,plot,plot_area,address,gstin,phone,connection_size,active,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(*data,connection.get(),active.get(),today()))
                    self.store.db.commit(); dialog.destroy(); refresh()
                except sqlite3.IntegrityError: messagebox.showerror(APP,"That member code is already in use.",parent=dialog)
            ttk.Button(form,text="Save",command=save).grid(row=9,column=1,sticky="e",pady=(12,0))
        ttk.Button(bar,text="Add member",command=lambda:edit()).pack(side="left"); ttk.Button(bar,text="Edit selected",command=lambda: edit(tree.selection()[0]) if tree.selection() else messagebox.showinfo(APP,"Select a member first.")).pack(side="left",padx=6)
        ttk.Button(bar,text="Import members Excel",command=lambda:self.import_members_excel(refresh)).pack(side="right"); refresh()

    def member_choice(self, parent):
        records=self.store.all("SELECT * FROM members WHERE active=1 ORDER BY code")
        choices=[f"{r['id']} | {r['code']} — {r['name']}" for r in records]
        var=tk.StringVar(value=choices[0] if choices else "")
        box=ttk.Combobox(parent,textvariable=var,values=choices,state="readonly",width=46); return var,box

    def new_document_tab(self, book, kind):
        if kind == "Invoice":
            self.monthly_invoice_tab(book)
            return
        f=self.tab(book, "New " + kind); form=ttk.Frame(f); form.pack(anchor="nw")
        if kind == "Receipt":
            ttk.Label(f, text="Create a receipt only after payment has been received and verified.", foreground="#555").pack(anchor="w", pady=(0,10))
        member_var, member_box=self.member_choice(form)
        rows=[("Member",member_box),("Date",ttk.Entry(form,width=30)),("Amount",ttk.Entry(form,width=30)),("Description",ttk.Entry(form,width=50))]
        rows[1][1].insert(0,today()); rows[3][1].insert(0,"Monthly maintenance charges" if kind=="Invoice" else ("Payment received" if kind=="Receipt" else "Adjustment against charges"))
        widgets={"date":rows[1][1],"amount":rows[2][1],"description":rows[3][1]}
        if kind=="Invoice": rows.append(("Billing period",ttk.Entry(form,width=30))); rows[-1][1].insert(0,date.today().strftime("%B %Y")); widgets["period"]=rows[-1][1]
        if kind=="Receipt":
            mode=ttk.Combobox(form,values=("Cash","Cheque","NEFT","RTGS","IMPS","UPI"),state="readonly",width=27); mode.set("NEFT"); rows.extend([("Payment mode",mode),("Reference number",ttk.Entry(form,width=30))]); widgets["mode"]=mode; widgets["reference"]=rows[-1][1]
        for i,(label,w) in enumerate(rows): ttk.Label(form,text=label).grid(row=i,column=0,sticky="w",padx=(0,12),pady=7); w.grid(row=i,column=1,sticky="w",pady=7)
        def create():
            try:
                mid=int(member_var.get().split(" | ")[0]); amount=float(widgets["amount"].get()); assert amount>0
                datetime.strptime(widgets["date"].get(),"%Y-%m-%d")
            except Exception: return messagebox.showerror(APP,"Enter a member, ISO date (YYYY-MM-DD), and an amount greater than zero.")
            doc_id=self.store.add_document(kind,mid,widgets["date"].get(),amount,widgets["description"].get().strip() or kind,widgets.get("period",tk.StringVar()).get() if "period" in widgets else "",widgets.get("mode",tk.StringVar()).get() if "mode" in widgets else "",widgets.get("reference",tk.StringVar()).get() if "reference" in widgets else "")
            d=self.store.one("SELECT * FROM documents WHERE id=?",(doc_id,)); messagebox.showinfo(APP,f"{kind} {d['number']} created."); self.open_html(d["html"],d["number"])
        ttk.Button(form,text=f"Create {kind}",command=create,style="Accent.TButton").grid(row=len(rows),column=1,sticky="w",pady=16)

    def invoice_upload_tab(self, book):
        f=self.tab(book, "Invoice upload")
        ttk.Label(f, text="Monthly invoices are created only through the Excel upload.", font=("Segoe UI",14,"bold")).pack(anchor="w", pady=(0,10))
        ttk.Label(f, text="Each row must contain the member code, billing month, maintenance rate, past and present meter readings, and any interest penalty. The invoice date is set to the selected month's final day.", wraplength=760).pack(anchor="w", pady=(0,18))
        ttk.Button(f, text="Open invoice Excel sample", command=lambda:self.open_sample("AUDA_Estates_Invoice_Creation_Template_v2.xlsx"), style="Accent.TButton").pack(anchor="w", pady=5)
        ttk.Button(f, text="Upload and create monthly invoices", command=self.import_invoices_excel, style="Accent.TButton").pack(anchor="w", pady=5)

    def receipt_upload_tab(self, book):
        f=self.tab(book, "Receipt upload")
        ttk.Label(f,text="Receipts are created only from an Excel upload after payment is received.",font=("Segoe UI",14,"bold")).pack(anchor="w",pady=(0,12))
        ttk.Label(f,text="Required columns: member_code, receipt_no, receipt_date, amount, payment_mode, reference_no, description").pack(anchor="w",pady=(0,12))
        ttk.Button(f,text="Upload and create receipts",command=self.import_receipts_excel,style="Accent.TButton").pack(anchor="w")

    def monthly_invoice_tab(self, book):
        f=self.tab(book, "Monthly invoices"); form=ttk.Frame(f); form.pack(anchor="nw")
        ttk.Label(f, text="Invoice date is automatically set to the last day of the selected billing month.", foreground="#555").pack(anchor="w", pady=(0,10))
        member_var, member_box=self.member_choice(form)
        period=ttk.Entry(form,width=30); period.insert(0,date.today().strftime("%Y-%m"))
        rate=ttk.Entry(form,width=30); rate.insert(0,"0")
        past=ttk.Entry(form,width=30); past.insert(0,"0")
        present=ttk.Entry(form,width=30); present.insert(0,"0")
        interest=ttk.Entry(form,width=30); interest.insert(0,"0")
        rows=[("Member",member_box),("Billing month (YYYY-MM)",period),("Yearly maintenance rate / sq mtr",rate),("Past meter reading",past),("Present meter reading",present),("Interest penalty",interest)]
        for i,(label,w) in enumerate(rows): ttk.Label(form,text=label).grid(row=i,column=0,sticky="w",padx=(0,12),pady=7); w.grid(row=i,column=1,sticky="w",pady=7)
        preview=ttk.Label(form,text="Enter values to preview the taxable amount and GST.",foreground="#126c64"); preview.grid(row=6,column=1,sticky="w",pady=(10,5))
        def calculate(show_error=False):
            try:
                member=self.store.one("SELECT * FROM members WHERE id=?",(int(member_var.get().split(" | ")[0]),)); p=float(past.get()); q=float(present.get()); r=float(rate.get()); i=float(interest.get())
                if q < p or min(p,q,r,i) < 0: raise ValueError
                minimum={"20MM":300,"30MM":350,"40MM":400}[member["connection_size"]]
                maintenance=float(member["plot_area"] or 0)*r; water=max((q-p)*5,minimum); taxable=maintenance+water+i; gst=taxable*.18; total=taxable+gst
                preview.config(text=f"Invoice date: {month_end(period.get())}  |  Maintenance {money(maintenance)}  |  Water {money(water)}  |  GST {money(gst)}  |  Total {money(total)}")
                return True
            except Exception:
                preview.config(text="Enter valid non-negative figures and a billing month in YYYY-MM format.")
                if show_error: messagebox.showerror(APP,"Check the billing month, meter readings, maintenance rate and interest penalty.")
                return False
        def create():
            if not calculate(True): return
            try:
                doc_id=self.store.add_monthly_invoice(int(member_var.get().split(" | ")[0]),period.get(),float(rate.get()),float(past.get()),float(present.get()),float(interest.get()))
                d=self.store.one("SELECT * FROM documents WHERE id=?",(doc_id,)); messagebox.showinfo(APP,f"Invoice {d['number']} created."); self.open_html(d["html"],d["number"])
            except Exception as e: messagebox.showerror(APP,str(e))
        ttk.Button(form,text="Preview calculation",command=calculate).grid(row=7,column=0,sticky="w",pady=16)
        ttk.Button(form,text="Create month-end invoice",command=create,style="Accent.TButton").grid(row=7,column=1,sticky="w",pady=16)

    def register_tab(self, book):
        f=self.tab(book,"Documents & reversals"); bar=ttk.Frame(f); bar.pack(fill="x",pady=(0,10)); kind=tk.StringVar(value="All")
        ttk.Label(bar,text="Show").pack(side="left"); chooser=ttk.Combobox(bar,textvariable=kind,values=("All","Invoice","Receipt","Credit Note"),state="readonly",width=16); chooser.pack(side="left",padx=6)
        tree=self.tree(f,("Type","Number","Member","Date","Period / mode","Amount","Status"),(105,135,220,100,155,110,100)); tree.pack(fill="both",expand=True)
        def refresh(*_):
            tree.delete(*tree.get_children()); q="SELECT d.*,m.name FROM documents d JOIN members m ON m.id=d.member_id"; args=[]
            if kind.get()!="All": q+=" WHERE d.doc_type=?"; args=[kind.get()]
            for r in self.store.all(q+" ORDER BY d.id DESC",args): tree.insert("","end",iid=r["id"],values=(r["doc_type"],r["number"],r["name"],r["doc_date"],r["period"] or r["payment_mode"],money(r["amount"]),r["status"]))
        def selected(): return self.store.one("SELECT * FROM documents WHERE id=?",(tree.selection()[0],)) if tree.selection() else None
        def view():
            d=selected(); self.open_html(d["html"],d["number"]) if d else messagebox.showinfo(APP,"Select a document first.")
        def reverse():
            d=selected()
            if not d: return messagebox.showinfo(APP,"Select a document first.")
            if d["doc_type"] != "Receipt": return messagebox.showwarning(APP,"Individual reversal is available for receipts only.")
            if d["status"]!="Active": return messagebox.showwarning(APP,"This document has already been reversed.")
            if messagebox.askyesno(APP,f"Reverse {d['number']}? This adds an equal and opposite ledger entry."):
                self.store.reverse(d["id"]); refresh()
        ttk.Button(bar,text="Refresh",command=refresh).pack(side="right"); ttk.Button(bar,text="Reverse selected",command=reverse).pack(side="right",padx=6); ttk.Button(bar,text="Open / print selected",command=view).pack(side="right",padx=6); chooser.bind("<<ComboboxSelected>>",refresh); refresh()

    def ledger_tab(self, book):
        f=self.tab(book,"Member ledger"); bar=ttk.Frame(f); bar.pack(fill="x",pady=(0,10)); member_var, member_box=self.member_choice(bar); ttk.Label(bar,text="Member").pack(side="left"); member_box.pack(side="left",padx=7)
        balance_label=ttk.Label(bar,text="Balance: —",font=("Segoe UI",11,"bold")); balance_label.pack(side="right")
        tree=self.tree(f,("Date","Particulars","Reference","Debit","Credit","Balance"),(105,360,135,110,110,120)); tree.pack(fill="both",expand=True)
        def refresh():
            tree.delete(*tree.get_children())
            if not member_var.get(): return
            mid=int(member_var.get().split(" | ")[0]); records=self.store.all("SELECT * FROM ledger WHERE member_id=? ORDER BY id",(mid,))
            for r in records: tree.insert("","end",values=(r["entry_date"],r["particulars"],r["reference"] or "",money(r["debit"]),money(r["credit"]),money(r["balance"])))
            balance_label.config(text="Outstanding balance: " + money(self.store.balance(mid)))
        ttk.Button(bar,text="Load ledger",command=refresh).pack(side="left",padx=6)
        ttk.Button(bar,text="Selected member PDF",command=lambda:self.export_ledgers_pdf(member_var)).pack(side="left",padx=4)
        ttk.Button(bar,text="Selected member Excel",command=lambda:self.export_ledgers_excel(member_var)).pack(side="left",padx=4)
        ttk.Button(bar,text="All members PDF",command=lambda:self.export_ledgers_pdf()).pack(side="left",padx=4)
        ttk.Button(bar,text="All members Excel",command=lambda:self.export_ledgers_excel()).pack(side="left",padx=4)
        member_box.bind("<<ComboboxSelected>>",lambda _ : refresh()); refresh()

    def tools_tab(self, book):
        f=self.tab(book,"Tools & backup")
        ttk.Label(f,text="Data tools",font=("Segoe UI",15,"bold")).pack(anchor="w",pady=(0,12))
        ttk.Button(f,text="Create database backup",command=self.backup).pack(anchor="w",pady=5)
        ttk.Button(f,text="Export ledger CSV",command=self.export_ledger).pack(anchor="w",pady=5)
        ttk.Button(f,text="Import members Excel",command=self.import_members_excel).pack(anchor="w",pady=5)
        ttk.Button(f,text="Create monthly invoices from Excel",command=self.import_invoices_excel).pack(anchor="w",pady=5)
        ttk.Button(f,text="Open member master Excel sample",command=lambda:self.open_sample("AUDA_Estates_Member_Master_Template.xlsx")).pack(anchor="w",pady=5)
        ttk.Button(f,text="Open monthly invoice Excel sample",command=lambda:self.open_sample("AUDA_Estates_Invoice_Creation_Template_v2.xlsx")).pack(anchor="w",pady=5)
        ttk.Separator(f).pack(fill="x",pady=22)
        ttk.Label(f,text="Delete data entered on or after a date",font=("Segoe UI",12,"bold")).pack(anchor="w")
        rollback=ttk.Frame(f); rollback.pack(anchor="w",pady=5); cutoff=ttk.Entry(rollback,width=18); cutoff.insert(0,today()); cutoff.pack(side="left")
        def erase():
            try: datetime.strptime(cutoff.get(),"%Y-%m-%d")
            except ValueError: return messagebox.showerror(APP,"Enter the date as YYYY-MM-DD.")
            if messagebox.askyesno(APP, f"Delete documents, receipts, ledger entries and members entered on or after {cutoff.get()}? This cannot be undone without restoring a backup."):
                self.store.erase_entries_from(cutoff.get()); messagebox.showinfo(APP,"Requested data has been deleted."); self.home()
        ttk.Button(rollback,text="Delete entered data",command=erase).pack(side="left",padx=7)
        ttk.Separator(f).pack(fill="x",pady=22)
        ttk.Label(f,text="CSV templates",font=("Segoe UI",12,"bold")).pack(anchor="w")
        ttk.Label(f,text="Member master upload: code, name, plot, plot_area_sq_mtr, connection_size, address, gstin, phone, active\nInvoice upload: member_code, invoice_no, invoice_date, billing_month, maintenance_rate_per_sq_mtr, past_meter_reading, present_meter_reading, interest_penalty\nA receipt is entered only after a payment is received.").pack(anchor="w",pady=6)

    def tree(self,parent,columns,widths):
        frame=ttk.Frame(parent); frame.pack(fill="both",expand=True)
        tree=ttk.Treeview(frame,columns=columns,show="headings")
        for c,w in zip(columns,widths): tree.heading(c,text=c); tree.column(c,width=w,anchor="w")
        y=ttk.Scrollbar(frame,orient="vertical",command=tree.yview); tree.configure(yscrollcommand=y.set); tree.pack(side="left",fill="both",expand=True); y.pack(side="right",fill="y")
        return tree
    def open_html(self, html, name):
        path=os.path.join(tempfile.gettempdir(),f"{name}.html")
        with open(path,"w",encoding="utf-8") as fh: fh.write(html)
        webbrowser.open("file:///"+path.replace("\\","/"))
    def backup(self):
        target=filedialog.asksaveasfilename(title="Save database backup",defaultextension=".sqlite3",initialfile=f"auda_estates_backup_{date.today():%Y%m%d}.sqlite3",filetypes=[("SQLite database","*.sqlite3")])
        if target: self.store.db.commit(); shutil.copy2(DB_FILE,target); messagebox.showinfo(APP,"Backup saved successfully.")
    def export_ledger(self):
        target=filedialog.asksaveasfilename(defaultextension=".csv",initialfile="auda_estates_ledger.csv",filetypes=[("CSV","*.csv")])
        if not target:return
        rows=self.store.all("SELECT m.code,m.name,l.entry_date,l.particulars,l.reference,l.debit,l.credit,l.balance FROM ledger l JOIN members m ON m.id=l.member_id ORDER BY l.id")
        with open(target,"w",newline="",encoding="utf-8-sig") as f: w=csv.writer(f); w.writerow(["member_code","member_name","date","particulars","reference","debit","credit","balance"]); w.writerows([tuple(r) for r in rows])
        messagebox.showinfo(APP,"Ledger CSV exported.")
    def ledger_reports(self, member_var=None):
        if member_var and member_var.get():
            member_ids=[int(member_var.get().split(" | ")[0])]
        else:
            member_ids=[r["id"] for r in self.store.all("SELECT id FROM members WHERE active=1 ORDER BY code")]
        reports=[]
        for member_id in member_ids:
            member=self.store.one("SELECT * FROM members WHERE id=?",(member_id,))
            entries=self.store.all("SELECT * FROM ledger WHERE member_id=? ORDER BY id",(member_id,))
            if member: reports.append((member,entries))
        return reports
    def export_ledgers_pdf(self, member_var=None):
        reports=self.ledger_reports(member_var)
        if not reports:return messagebox.showinfo(APP,"Select a member or create active members first.")
        path=filedialog.asksaveasfilename(defaultextension=".pdf",initialfile="auda_estates_ledgers.pdf",filetypes=[("PDF file","*.pdf")])
        if not path:return
        save_ledger_pdf(path,reports); messagebox.showinfo(APP,"Ledger PDF saved.")
    def export_ledgers_excel(self, member_var=None):
        reports=self.ledger_reports(member_var)
        if not reports:return messagebox.showinfo(APP,"Select a member or create active members first.")
        path=filedialog.asksaveasfilename(defaultextension=".xlsx",initialfile="auda_estates_ledgers.xlsx",filetypes=[("Excel workbook","*.xlsx")])
        if not path:return
        sheets=[]
        for member, entries in reports:
            rows=[[APP,"Member Ledger"],["Member",member["name"]],["Member Code",member["code"]],["Plot",member["plot"] or ""],[],["Date","Particulars","Reference","Debit","Credit","Balance"]]
            rows += [[e["entry_date"],e["particulars"],e["reference"] or "",float(e["debit"]),float(e["credit"]),float(e["balance"])] for e in entries]
            rows.append([]); rows.append(["Outstanding balance","", "", "", "", float(entries[-1]["balance"]) if entries else 0])
            sheets.append((f"{member['code']}_{member['name']}",rows))
        save_xlsx(path,sheets); messagebox.showinfo(APP,"Ledger Excel workbook saved.")
    def import_members(self, callback):
        path=filedialog.askopenfilename(title="Select members CSV",filetypes=[("CSV","*.csv")]);
        if not path:return
        try:
            with open(path,newline="",encoding="utf-8-sig") as f:
                for r in csv.DictReader(f): self.store.db.execute("INSERT OR REPLACE INTO members(code,name,plot,address,gstin,phone,active,created_at) VALUES(?,?,?,?,?,?,?,?)",(r["code"],r["name"],r.get("plot",""),r.get("address",""),r.get("gstin",""),r.get("phone",""),int(r.get("active","1")),today()))
            self.store.db.commit(); callback(); messagebox.showinfo(APP,"Members imported.")
        except Exception as e: messagebox.showerror(APP,"Could not import members CSV: "+str(e))

    def open_sample(self, filename):
        path=os.path.join(HERE,filename)
        if not os.path.exists(path): return messagebox.showwarning(APP,"The sample workbook is not beside the application. Keep the supplied sample Excel files in this folder.")
        os.startfile(path)

    def import_members_excel(self, after_import=None):
        path=filedialog.askopenfilename(title="Select member master Excel file",filetypes=[("Excel workbook","*.xlsx")])
        if not path:return
        try:
            count=0
            for r in xlsx_rows(path):
                code=r["code"].strip(); name=r["name"].strip(); connection=r.get("connection_size","20MM").upper()
                if connection not in ("20MM","30MM","40MM"): raise ValueError(f"{code}: connection_size must be 20MM, 30MM or 40MM.")
                area=float(r.get("plot_area_sq_mtr",0) or 0); active=int(float(r.get("active",1) or 1))
                existing=self.store.one("SELECT id FROM members WHERE code=?",(code,))
                values=(name,r.get("plot",""),area,connection,r.get("address",""),r.get("gstin",""),r.get("phone",""),active)
                if existing: self.store.db.execute("UPDATE members SET name=?,plot=?,plot_area=?,connection_size=?,address=?,gstin=?,phone=?,active=? WHERE code=?",(*values,code))
                else: self.store.db.execute("INSERT INTO members(code,name,plot,plot_area,connection_size,address,gstin,phone,active,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(code,*values,today()))
                count+=1
            self.store.db.commit()
            if after_import: after_import()
            messagebox.showinfo(APP,f"{count} member record(s) imported or updated.")
        except Exception as e: self.store.db.rollback(); messagebox.showerror(APP,"Member import stopped: "+str(e))

    def import_invoices_excel(self):
        path=filedialog.askopenfilename(title="Select monthly invoice Excel file",filetypes=[("Excel workbook","*.xlsx")])
        if not path:return
        try:
            count=0; created=[]
            for r in xlsx_rows(path):
                m=self.store.one("SELECT id FROM members WHERE code=?",(r["member_code"].strip(),))
                if not m: raise ValueError("Unknown member code: "+r["member_code"])
                doc_id=self.store.add_monthly_invoice(m["id"],r["billing_month"],float(r["maintenance_rate_per_sq_mtr"] or 0),float(r["past_meter_reading"] or 0),float(r["present_meter_reading"] or 0),float(r.get("interest_penalty",0) or 0),r.get("invoice_no",""),r.get("invoice_date","") or None); created.append(doc_id); count+=1
            docs=self.store.all("SELECT d.*,m.name member_name FROM documents d JOIN members m ON m.id=d.member_id WHERE d.id IN ("+",".join("?"*len(created))+")",created)
            pdf=os.path.join(HERE,f"Invoices_{datetime.now():%Y%m%d_%H%M%S}.pdf"); save_document_batch_pdf(pdf,docs); os.startfile(pdf)
            messagebox.showinfo(APP,f"{count} monthly invoice(s) created."); self.home()
        except Exception as e: self.store.db.rollback(); messagebox.showerror(APP,"Invoice upload stopped: "+str(e))
    def import_receipts_excel(self):
        path=filedialog.askopenfilename(title="Select receipts Excel file",filetypes=[("Excel workbook","*.xlsx")])
        if not path:return
        try:
            count=0; created=[]
            for r in xlsx_rows(path):
                m=self.store.one("SELECT id FROM members WHERE code=?",(r["member_code"].strip(),))
                if not m: raise ValueError("Unknown member code: "+r["member_code"])
                doc_id=self.store.add_document("Receipt",m["id"],r["receipt_date"],float(r["amount"]),r.get("description") or "Payment received","",r.get("payment_mode",""),r.get("reference_no",""),r.get("receipt_no",""),r.get("payment_date","") or r["receipt_date"]); created.append(doc_id); count+=1
            docs=self.store.all("SELECT d.*,m.name member_name FROM documents d JOIN members m ON m.id=d.member_id WHERE d.id IN ("+",".join("?"*len(created))+")",created)
            pdf=os.path.join(HERE,f"Receipts_{datetime.now():%Y%m%d_%H%M%S}.pdf"); save_document_batch_pdf(pdf,docs); os.startfile(pdf)
            messagebox.showinfo(APP,f"{count} receipt(s) created."); self.home()
        except Exception as e: self.store.db.rollback(); messagebox.showerror(APP,"Receipt upload stopped: "+str(e))
    def import_invoices(self):
        path=filedialog.askopenfilename(title="Select invoices CSV",filetypes=[("CSV","*.csv")]);
        if not path:return
        count=0
        try:
            with open(path,newline="",encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    m=self.store.one("SELECT id FROM members WHERE code=?",(r["member_code"],))
                    if not m: raise ValueError("Unknown member code: "+r["member_code"])
                    self.store.add_document("Invoice",m["id"],r["date"],float(r["amount"]),r.get("description") or "Maintenance charges",r.get("period", "")); count+=1
            messagebox.showinfo(APP,f"{count} invoice(s) imported.")
        except Exception as e: messagebox.showerror(APP,"Import stopped: "+str(e))


if __name__ == "__main__":
    BillingApp().mainloop()
