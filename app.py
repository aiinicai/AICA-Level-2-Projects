"""
Smart Billing Manager
Simple desktop billing software for creating, storing, printing and exporting invoices.

Run:
    python app.py

Optional packages:
    pip install reportlab openpyxl
"""
import csv
import os
import platform
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "Smart Billing Manager"
DB_FILE = Path(__file__).with_name("smart_billing_manager.db")


def money(value):
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return "0.00"


def today_iso():
    return date.today().isoformat()


class Database:
    def __init__(self, path=DB_FILE):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            tax_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            invoice_date TEXT NOT NULL,
            customer_id INTEGER,
            customer_name TEXT NOT NULL,
            customer_address TEXT,
            status TEXT DEFAULT 'Unpaid',
            subtotal REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            quantity REAL DEFAULT 1,
            rate REAL DEFAULT 0,
            amount REAL DEFAULT 0,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        )
        """)
        defaults = {
            "business_name": "Your Business Name",
            "business_address": "Business Address",
            "business_phone": "Phone",
            "business_email": "Email",
            "tax_label": "VAT",
            "tax_rate": "18",
            "currency": "TZS",
            "invoice_prefix": "INV",
            "bank_details": "Bank details here",
            "footer_note": "Thank you for your business."
        }
        for k, v in defaults.items():
            cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))
        self.conn.commit()

    def get_settings(self):
        return {r["key"]: r["value"] for r in self.conn.execute("SELECT key, value FROM settings")}

    def save_settings(self, data):
        cur = self.conn.cursor()
        for k, v in data.items():
            cur.execute("REPLACE INTO settings(key, value) VALUES (?, ?)", (k, str(v)))
        self.conn.commit()

    def next_invoice_no(self):
        s = self.get_settings()
        prefix = s.get("invoice_prefix", "INV")
        year = date.today().year
        like = f"{prefix}-{year}-%"
        row = self.conn.execute("SELECT invoice_no FROM invoices WHERE invoice_no LIKE ? ORDER BY id DESC LIMIT 1", (like,)).fetchone()
        num = 1
        if row:
            try:
                num = int(row["invoice_no"].split("-")[-1]) + 1
            except Exception:
                num = 1
        return f"{prefix}-{year}-{num:04d}"

    def add_customer(self, name, phone, email, address, tax_id):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO customers(name, phone, email, address, tax_id) VALUES (?, ?, ?, ?, ?)",
                    (name, phone, email, address, tax_id))
        self.conn.commit()
        return cur.lastrowid

    def customers(self):
        return self.conn.execute("SELECT * FROM customers ORDER BY name").fetchall()

    def save_invoice(self, inv, items):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO invoices(invoice_no, invoice_date, customer_id, customer_name, customer_address, status,
                                 subtotal, discount, tax, total, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (inv["invoice_no"], inv["invoice_date"], inv.get("customer_id"), inv["customer_name"],
              inv.get("customer_address", ""), inv["status"], inv["subtotal"], inv["discount"], inv["tax"],
              inv["total"], inv.get("notes", "")))
        invoice_id = cur.lastrowid
        for it in items:
            cur.execute("INSERT INTO invoice_items(invoice_id, description, quantity, rate, amount) VALUES (?, ?, ?, ?, ?)",
                        (invoice_id, it["description"], it["quantity"], it["rate"], it["amount"]))
        self.conn.commit()
        return invoice_id

    def invoices(self, start=None, end=None, status=None, search=None):
        q = "SELECT * FROM invoices WHERE 1=1"
        params = []
        if start:
            q += " AND invoice_date >= ?"; params.append(start)
        if end:
            q += " AND invoice_date <= ?"; params.append(end)
        if status and status != "All":
            q += " AND status = ?"; params.append(status)
        if search:
            q += " AND (invoice_no LIKE ? OR customer_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        q += " ORDER BY invoice_date DESC, id DESC"
        return self.conn.execute(q, params).fetchall()

    def get_invoice(self, invoice_id):
        inv = self.conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        items = self.conn.execute("SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id", (invoice_id,)).fetchall()
        return inv, items

    def delete_invoice(self, invoice_id):
        self.conn.execute("DELETE FROM invoice_items WHERE invoice_id=?", (invoice_id,))
        self.conn.execute("DELETE FROM invoices WHERE id=?", (invoice_id,))
        self.conn.commit()

    def dashboard_numbers(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        def total_since(d):
            r = self.conn.execute("SELECT COALESCE(SUM(total),0) AS x FROM invoices WHERE invoice_date>=?", (d.isoformat(),)).fetchone()
            return r["x"]
        r = self.conn.execute("SELECT COUNT(*) c, COALESCE(SUM(total),0) t FROM invoices").fetchone()
        paid = self.conn.execute("SELECT COALESCE(SUM(total),0) t FROM invoices WHERE status='Paid'").fetchone()["t"]
        unpaid = self.conn.execute("SELECT COALESCE(SUM(total),0) t FROM invoices WHERE status!='Paid'").fetchone()["t"]
        return {
            "today": total_since(today), "week": total_since(week_start), "month": total_since(month_start),
            "year": total_since(year_start), "count": r["c"], "total": r["t"], "paid": paid, "unpaid": unpaid
        }

    def period_totals(self, period="month"):
        if period == "day": fmt = "%Y-%m-%d"
        elif period == "week": fmt = "%Y-W%W"
        elif period == "year": fmt = "%Y"
        else: fmt = "%Y-%m"
        rows = self.conn.execute("SELECT invoice_date, total FROM invoices ORDER BY invoice_date").fetchall()
        out = {}
        for r in rows:
            d = datetime.strptime(r["invoice_date"], "%Y-%m-%d")
            k = d.strftime(fmt)
            out[k] = out.get(k, 0) + (r["total"] or 0)
        return list(out.items())[-12:]


class InvoicePDF:
    @staticmethod
    def export(path, db, invoice_id):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        except ImportError:
            raise RuntimeError("ReportLab is not installed. Run: pip install reportlab")
        inv, items = db.get_invoice(invoice_id)
        s = db.get_settings()
        doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph(f"<b>{s.get('business_name','')}</b>", styles['Title']))
        story.append(Paragraph(s.get('business_address',''), styles['Normal']))
        story.append(Paragraph(f"{s.get('business_phone','')} | {s.get('business_email','')}", styles['Normal']))
        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>INVOICE</b>", styles['Heading1']))
        data = [["Invoice No", inv['invoice_no'], "Date", inv['invoice_date']],
                ["Customer", inv['customer_name'], "Status", inv['status']],
                ["Address", inv['customer_address'] or "", "Currency", s.get('currency','TZS')]]
        t = Table(data, colWidths=[28*mm, 70*mm, 25*mm, 45*mm])
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.25,colors.grey), ('BACKGROUND',(0,0),(-1,0),colors.whitesmoke)]))
        story.append(t); story.append(Spacer(1, 10))
        rows = [["Description", "Qty", "Rate", "Amount"]]
        for it in items:
            rows.append([it['description'], money(it['quantity']), money(it['rate']), money(it['amount'])])
        rows += [["", "", "Subtotal", money(inv['subtotal'])],
                 ["", "", "Discount", money(inv['discount'])],
                 ["", "", s.get('tax_label','VAT'), money(inv['tax'])],
                 ["", "", "Grand Total", money(inv['total'])]]
        table = Table(rows, colWidths=[85*mm, 20*mm, 35*mm, 35*mm])
        table.setStyle(TableStyle([
            ('GRID',(0,0),(-1,-1),0.25,colors.grey), ('BACKGROUND',(0,0),(-1,0),colors.lightgrey),
            ('ALIGN',(1,1),(-1,-1),'RIGHT'), ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('FONTNAME',(-2,-1),(-1,-1),'Helvetica-Bold'), ('BACKGROUND',(-2,-1),(-1,-1),colors.whitesmoke)
        ]))
        story.append(table); story.append(Spacer(1, 12))
        if inv['notes']:
            story.append(Paragraph(f"<b>Notes:</b> {inv['notes']}", styles['Normal']))
        story.append(Paragraph(f"<b>Bank Details:</b> {s.get('bank_details','')}", styles['Normal']))
        story.append(Spacer(1, 20))
        story.append(Paragraph(s.get('footer_note',''), styles['Italic']))
        doc.build(story)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.title(APP_NAME)
        self.geometry("1120x720")
        self.minsize(1000, 650)
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.configure(bg="#f5f7fb")
        self.create_ui()

    def create_ui(self):
        title = tk.Label(self, text=APP_NAME, font=("Segoe UI", 18, "bold"), bg="#1f4e79", fg="white", pady=10)
        title.pack(fill="x")
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)
        self.dashboard = ttk.Frame(nb); self.invoice_tab = ttk.Frame(nb); self.list_tab = ttk.Frame(nb)
        self.customer_tab = ttk.Frame(nb); self.report_tab = ttk.Frame(nb); self.settings_tab = ttk.Frame(nb)
        for frame, name in [(self.dashboard,"Dashboard"),(self.invoice_tab,"Create Invoice"),(self.list_tab,"Invoices"),(self.customer_tab,"Customers"),(self.report_tab,"Reports"),(self.settings_tab,"Settings")]:
            nb.add(frame, text=name)
        self.build_dashboard(); self.build_invoice(); self.build_invoice_list(); self.build_customers(); self.build_reports(); self.build_settings()

    def card(self, parent, title, value, row, col):
        f = tk.Frame(parent, bg="white", bd=1, relief="solid", padx=14, pady=12)
        f.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        tk.Label(f, text=title, bg="white", fg="#555", font=("Segoe UI", 10)).pack(anchor="w")
        lab = tk.Label(f, text=value, bg="white", fg="#1f4e79", font=("Segoe UI", 18, "bold"))
        lab.pack(anchor="w")
        return lab

    def build_dashboard(self):
        f = self.dashboard
        for i in range(4): f.columnconfigure(i, weight=1)
        self.dash_labels = {}
        names = [("today","Today's Billing"),("week","This Week"),("month","This Month"),("year","This Year"),("total","Total Billing"),("paid","Paid Amount"),("unpaid","Outstanding"),("count","Invoices")]
        for idx, (k, title) in enumerate(names):
            self.dash_labels[k] = self.card(f, title, "0", idx//4, idx%4)
        ttk.Button(f, text="Refresh Dashboard", command=self.refresh_dashboard).grid(row=2, column=0, padx=8, pady=12, sticky="w")
        self.chart_canvas = tk.Canvas(f, height=270, bg="white", bd=1, relief="solid")
        self.chart_canvas.grid(row=3, column=0, columnspan=4, sticky="nsew", padx=8, pady=8)
        f.rowconfigure(3, weight=1)
        self.refresh_dashboard()

    def refresh_dashboard(self):
        s = self.db.get_settings(); cur = s.get("currency", "TZS")
        d = self.db.dashboard_numbers()
        for k, lab in self.dash_labels.items():
            lab.config(text=str(d[k]) if k == "count" else f"{cur} {money(d[k])}")
        self.draw_chart()

    def draw_chart(self):
        c = self.chart_canvas; c.delete("all")
        data = self.db.period_totals("month")
        c.create_text(20, 20, text="Monthly Billing Summary", anchor="w", font=("Segoe UI", 12, "bold"), fill="#1f4e79")
        if not data:
            c.create_text(20, 70, text="No invoice data available yet.", anchor="w", fill="#555")
            return
        w = max(c.winfo_width(), 900); h = 250; left = 55; bottom = h - 25; top = 45
        maxv = max(v for _, v in data) or 1
        barw = max(25, int((w-left-30)/len(data))-10)
        for i, (label, val) in enumerate(data):
            x = left + i * (barw + 10)
            bh = int((val/maxv)*(bottom-top))
            c.create_rectangle(x, bottom-bh, x+barw, bottom, fill="#1f4e79", outline="")
            c.create_text(x+barw/2, bottom+12, text=label, font=("Segoe UI", 8))
            c.create_text(x+barw/2, bottom-bh-10, text=money(val), font=("Segoe UI", 8))

    def build_invoice(self):
        f = self.invoice_tab
        top = ttk.LabelFrame(f, text="Invoice Details")
        top.pack(fill="x", padx=8, pady=8)
        self.inv_no = tk.StringVar(value=self.db.next_invoice_no()); self.inv_date = tk.StringVar(value=today_iso())
        self.cust_name = tk.StringVar(); self.status = tk.StringVar(value="Unpaid")
        self.discount = tk.StringVar(value="0"); self.tax_rate = tk.StringVar(value=self.db.get_settings().get("tax_rate","18"))
        labels = [("Invoice No", self.inv_no), ("Date", self.inv_date), ("Customer Name", self.cust_name), ("Status", self.status), ("Discount", self.discount), ("Tax %", self.tax_rate)]
        for i, (lbl, var) in enumerate(labels):
            ttk.Label(top, text=lbl).grid(row=i//3, column=(i%3)*2, padx=6, pady=6, sticky="e")
            if lbl == "Status":
                ttk.Combobox(top, textvariable=var, values=["Paid","Unpaid","Partially Paid"], width=20).grid(row=i//3, column=(i%3)*2+1, padx=6, pady=6, sticky="w")
            else:
                ttk.Entry(top, textvariable=var, width=24).grid(row=i//3, column=(i%3)*2+1, padx=6, pady=6, sticky="w")
        ttk.Label(top, text="Customer Address").grid(row=2, column=0, padx=6, pady=6, sticky="ne")
        self.cust_addr = tk.Text(top, height=3, width=70)
        self.cust_addr.grid(row=2, column=1, columnspan=5, padx=6, pady=6, sticky="w")
        item_box = ttk.LabelFrame(f, text="Invoice Items")
        item_box.pack(fill="both", expand=True, padx=8, pady=8)
        cols = ("description","qty","rate","amount")
        self.item_tree = ttk.Treeview(item_box, columns=cols, show="headings", height=8)
        for col, txt, width in [("description","Description",520),("qty","Qty",90),("rate","Rate",120),("amount","Amount",130)]:
            self.item_tree.heading(col, text=txt); self.item_tree.column(col, width=width, anchor="e" if col != "description" else "w")
        self.item_tree.pack(fill="both", expand=True, padx=6, pady=6)
        form = ttk.Frame(item_box); form.pack(fill="x", padx=6, pady=6)
        self.item_desc = tk.StringVar(); self.item_qty = tk.StringVar(value="1"); self.item_rate = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.item_desc, width=55).pack(side="left", padx=4)
        ttk.Entry(form, textvariable=self.item_qty, width=10).pack(side="left", padx=4)
        ttk.Entry(form, textvariable=self.item_rate, width=12).pack(side="left", padx=4)
        ttk.Button(form, text="Add Item", command=self.add_item).pack(side="left", padx=4)
        ttk.Button(form, text="Remove Selected", command=lambda: [self.item_tree.delete(x) for x in self.item_tree.selection()] or self.update_totals()).pack(side="left", padx=4)
        bottom = ttk.Frame(f); bottom.pack(fill="x", padx=8, pady=8)
        self.total_label = ttk.Label(bottom, text="Total: 0.00", font=("Segoe UI", 13, "bold")); self.total_label.pack(side="left")
        ttk.Button(bottom, text="Save Invoice", command=self.save_invoice).pack(side="right", padx=4)
        ttk.Button(bottom, text="Clear", command=self.clear_invoice).pack(side="right", padx=4)

    def add_item(self):
        try:
            qty = float(self.item_qty.get() or 0); rate = float(self.item_rate.get() or 0); amt = qty * rate
        except ValueError:
            messagebox.showerror(APP_NAME, "Quantity and rate must be numeric."); return
        if not self.item_desc.get().strip():
            messagebox.showerror(APP_NAME, "Please enter item description."); return
        self.item_tree.insert("", "end", values=(self.item_desc.get().strip(), qty, rate, amt))
        self.item_desc.set(""); self.item_qty.set("1"); self.item_rate.set("0")
        self.update_totals()

    def totals(self):
        subtotal = sum(float(self.item_tree.item(i)['values'][3]) for i in self.item_tree.get_children())
        discount = float(self.discount.get() or 0)
        tax_rate = float(self.tax_rate.get() or 0)
        taxable = max(subtotal - discount, 0)
        tax = taxable * tax_rate / 100
        return subtotal, discount, tax, taxable + tax

    def update_totals(self):
        try:
            sub, dis, tax, total = self.totals()
            cur = self.db.get_settings().get("currency", "TZS")
            self.total_label.config(text=f"Subtotal: {cur} {money(sub)} | Tax: {cur} {money(tax)} | Total: {cur} {money(total)}")
        except Exception:
            pass

    def save_invoice(self):
        if not self.cust_name.get().strip():
            messagebox.showerror(APP_NAME, "Customer name is required."); return
        if not self.item_tree.get_children():
            messagebox.showerror(APP_NAME, "Please add at least one invoice item."); return
        try:
            sub, dis, tax, total = self.totals()
        except ValueError:
            messagebox.showerror(APP_NAME, "Discount and tax rate must be numeric."); return
        items = []
        for i in self.item_tree.get_children():
            v = self.item_tree.item(i)['values']
            items.append({"description": v[0], "quantity": float(v[1]), "rate": float(v[2]), "amount": float(v[3])})
        inv = {"invoice_no": self.inv_no.get().strip(), "invoice_date": self.inv_date.get().strip(), "customer_name": self.cust_name.get().strip(),
               "customer_address": self.cust_addr.get("1.0","end").strip(), "status": self.status.get(), "subtotal": sub, "discount": dis,
               "tax": tax, "total": total, "notes": ""}
        try:
            invoice_id = self.db.save_invoice(inv, items)
        except sqlite3.IntegrityError:
            messagebox.showerror(APP_NAME, "Invoice number already exists."); return
        messagebox.showinfo(APP_NAME, f"Invoice saved: {inv['invoice_no']}")
        self.refresh_invoice_list(); self.refresh_dashboard(); self.clear_invoice()
        if messagebox.askyesno(APP_NAME, "Export invoice to PDF now?"):
            self.export_invoice_pdf(invoice_id)

    def clear_invoice(self):
        self.inv_no.set(self.db.next_invoice_no()); self.inv_date.set(today_iso()); self.cust_name.set(""); self.status.set("Unpaid")
        self.cust_addr.delete("1.0","end"); self.discount.set("0"); self.tax_rate.set(self.db.get_settings().get("tax_rate","18"))
        for i in self.item_tree.get_children(): self.item_tree.delete(i)
        self.update_totals()

    def build_invoice_list(self):
        f = self.list_tab
        filter_frame = ttk.Frame(f); filter_frame.pack(fill="x", padx=8, pady=8)
        self.search_var = tk.StringVar(); self.status_filter = tk.StringVar(value="All")
        ttk.Label(filter_frame, text="Search").pack(side="left"); ttk.Entry(filter_frame, textvariable=self.search_var, width=25).pack(side="left", padx=4)
        ttk.Label(filter_frame, text="Status").pack(side="left", padx=(12,0)); ttk.Combobox(filter_frame, textvariable=self.status_filter, values=["All","Paid","Unpaid","Partially Paid"], width=16).pack(side="left", padx=4)
        ttk.Button(filter_frame, text="Refresh", command=self.refresh_invoice_list).pack(side="left", padx=4)
        ttk.Button(filter_frame, text="Export PDF", command=self.selected_pdf).pack(side="right", padx=4)
        ttk.Button(filter_frame, text="Print", command=self.selected_print).pack(side="right", padx=4)
        ttk.Button(filter_frame, text="Delete", command=self.delete_selected_invoice).pack(side="right", padx=4)
        cols = ("id","invoice_no","date","customer","status","total")
        self.inv_tree = ttk.Treeview(f, columns=cols, show="headings")
        for col, txt, width in [("id","ID",60),("invoice_no","Invoice No",150),("date","Date",110),("customer","Customer",300),("status","Status",120),("total","Total",130)]:
            self.inv_tree.heading(col, text=txt); self.inv_tree.column(col, width=width, anchor="e" if col in ("id","total") else "w")
        self.inv_tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.refresh_invoice_list()

    def refresh_invoice_list(self):
        for i in self.inv_tree.get_children(): self.inv_tree.delete(i)
        for r in self.db.invoices(status=self.status_filter.get(), search=self.search_var.get().strip()):
            self.inv_tree.insert("", "end", values=(r['id'], r['invoice_no'], r['invoice_date'], r['customer_name'], r['status'], money(r['total'])))

    def selected_invoice_id(self):
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showwarning(APP_NAME, "Please select an invoice."); return None
        return int(self.inv_tree.item(sel[0])['values'][0])

    def export_invoice_pdf(self, invoice_id):
        inv, _ = self.db.get_invoice(invoice_id)
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{inv['invoice_no']}.pdf", filetypes=[("PDF", "*.pdf")])
        if not path: return None
        try:
            InvoicePDF.export(path, self.db, invoice_id)
            messagebox.showinfo(APP_NAME, f"PDF exported:\n{path}")
            return path
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e)); return None

    def selected_pdf(self):
        iid = self.selected_invoice_id()
        if iid: self.export_invoice_pdf(iid)

    def selected_print(self):
        iid = self.selected_invoice_id()
        if not iid: return
        path = self.export_invoice_pdf(iid)
        if not path: return
        try:
            if platform.system() == "Windows":
                os.startfile(path, "print")
            elif platform.system() == "Darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as e:
            messagebox.showinfo(APP_NAME, f"PDF created. Please print manually.\n{path}\n\n{e}")

    def delete_selected_invoice(self):
        iid = self.selected_invoice_id()
        if iid and messagebox.askyesno(APP_NAME, "Delete selected invoice?"):
            self.db.delete_invoice(iid); self.refresh_invoice_list(); self.refresh_dashboard()

    def build_customers(self):
        f = self.customer_tab
        frm = ttk.LabelFrame(f, text="Add Customer"); frm.pack(fill="x", padx=8, pady=8)
        self.cn = tk.StringVar(); self.cp = tk.StringVar(); self.ce = tk.StringVar(); self.ct = tk.StringVar()
        for i, (lbl, var) in enumerate([("Name", self.cn),("Phone", self.cp),("Email", self.ce),("Tax ID", self.ct)]):
            ttk.Label(frm, text=lbl).grid(row=i//2, column=(i%2)*2, padx=6, pady=6, sticky="e")
            ttk.Entry(frm, textvariable=var, width=35).grid(row=i//2, column=(i%2)*2+1, padx=6, pady=6, sticky="w")
        ttk.Label(frm, text="Address").grid(row=2, column=0, padx=6, pady=6, sticky="ne")
        self.ca = tk.Text(frm, height=3, width=70); self.ca.grid(row=2, column=1, columnspan=3, padx=6, pady=6)
        ttk.Button(frm, text="Save Customer", command=self.save_customer).grid(row=3, column=1, pady=6, sticky="w")
        self.cust_tree = ttk.Treeview(f, columns=("name","phone","email","tax"), show="headings")
        for col in ("name","phone","email","tax"):
            self.cust_tree.heading(col, text=col.title()); self.cust_tree.column(col, width=220)
        self.cust_tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.refresh_customers()

    def save_customer(self):
        if not self.cn.get().strip(): messagebox.showerror(APP_NAME, "Customer name required."); return
        self.db.add_customer(self.cn.get(), self.cp.get(), self.ce.get(), self.ca.get("1.0","end").strip(), self.ct.get())
        self.cn.set(""); self.cp.set(""); self.ce.set(""); self.ct.set(""); self.ca.delete("1.0","end"); self.refresh_customers()

    def refresh_customers(self):
        for i in self.cust_tree.get_children(): self.cust_tree.delete(i)
        for r in self.db.customers(): self.cust_tree.insert("", "end", values=(r['name'], r['phone'], r['email'], r['tax_id']))

    def build_reports(self):
        f = self.report_tab
        top = ttk.Frame(f); top.pack(fill="x", padx=8, pady=8)
        self.rep_start = tk.StringVar(value=(date.today().replace(day=1)).isoformat()); self.rep_end = tk.StringVar(value=today_iso())
        ttk.Label(top, text="From").pack(side="left"); ttk.Entry(top, textvariable=self.rep_start, width=14).pack(side="left", padx=4)
        ttk.Label(top, text="To").pack(side="left"); ttk.Entry(top, textvariable=self.rep_end, width=14).pack(side="left", padx=4)
        ttk.Button(top, text="Generate", command=self.refresh_report).pack(side="left", padx=4)
        ttk.Button(top, text="Export CSV", command=self.export_csv).pack(side="right", padx=4)
        ttk.Button(top, text="Export Excel", command=self.export_excel).pack(side="right", padx=4)
        self.report_tree = ttk.Treeview(f, columns=("invoice","date","customer","status","subtotal","tax","total"), show="headings")
        for col in ("invoice","date","customer","status","subtotal","tax","total"):
            self.report_tree.heading(col, text=col.title()); self.report_tree.column(col, width=135, anchor="e" if col in ("subtotal","tax","total") else "w")
        self.report_tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.report_total = ttk.Label(f, text="Total: 0.00", font=("Segoe UI", 12, "bold")); self.report_total.pack(anchor="e", padx=12, pady=8)
        self.refresh_report()

    def report_rows(self):
        return self.db.invoices(start=self.rep_start.get(), end=self.rep_end.get())

    def refresh_report(self):
        for i in self.report_tree.get_children(): self.report_tree.delete(i)
        total = 0
        for r in self.report_rows():
            total += r['total'] or 0
            self.report_tree.insert("", "end", values=(r['invoice_no'], r['invoice_date'], r['customer_name'], r['status'], money(r['subtotal']), money(r['tax']), money(r['total'])))
        self.report_total.config(text=f"Total Billing: {self.db.get_settings().get('currency','TZS')} {money(total)}")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path: return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["Invoice No","Date","Customer","Status","Subtotal","Tax","Total"])
            for r in self.report_rows(): w.writerow([r['invoice_no'], r['invoice_date'], r['customer_name'], r['status'], r['subtotal'], r['tax'], r['total']])
        messagebox.showinfo(APP_NAME, f"CSV exported:\n{path}")

    def export_excel(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            messagebox.showerror(APP_NAME, "OpenPyXL is not installed. Run: pip install openpyxl"); return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not path: return
        wb = Workbook(); ws = wb.active; ws.title = "Billing Report"
        ws.append(["Invoice No","Date","Customer","Status","Subtotal","Tax","Total"])
        for r in self.report_rows(): ws.append([r['invoice_no'], r['invoice_date'], r['customer_name'], r['status'], r['subtotal'], r['tax'], r['total']])
        wb.save(path); messagebox.showinfo(APP_NAME, f"Excel exported:\n{path}")

    def build_settings(self):
        f = self.settings_tab; s = self.db.get_settings(); self.setting_vars = {}
        frm = ttk.LabelFrame(f, text="Business and Invoice Settings"); frm.pack(fill="x", padx=8, pady=8)
        keys = [("business_name","Business Name"),("business_address","Address"),("business_phone","Phone"),("business_email","Email"),("currency","Currency"),("tax_label","Tax Label"),("tax_rate","Tax Rate %"),("invoice_prefix","Invoice Prefix"),("bank_details","Bank Details"),("footer_note","Footer Note")]
        for i, (key, label) in enumerate(keys):
            self.setting_vars[key] = tk.StringVar(value=s.get(key,""))
            ttk.Label(frm, text=label).grid(row=i, column=0, padx=6, pady=5, sticky="e")
            ttk.Entry(frm, textvariable=self.setting_vars[key], width=75).grid(row=i, column=1, padx=6, pady=5, sticky="w")
        ttk.Button(frm, text="Save Settings", command=self.save_settings).grid(row=len(keys), column=1, pady=8, sticky="w")
        ttk.Label(f, text=f"Database location: {DB_FILE}").pack(anchor="w", padx=12, pady=8)

    def save_settings(self):
        self.db.save_settings({k:v.get() for k,v in self.setting_vars.items()})
        messagebox.showinfo(APP_NAME, "Settings saved.")
        self.refresh_dashboard(); self.clear_invoice()


if __name__ == "__main__":
    app = App()
    app.mainloop()
