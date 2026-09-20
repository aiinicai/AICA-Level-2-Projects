"""Modern central review/correction workspace for PraNam E-Invoice Converter."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..models import Party, SourceValue
from ..util import to_decimal
from .widgets import fit_to_screen

COLORS = {"RED": "#FFE4E6", "AMBER": "#FFF7D6", "GREEN": "#DCFCE7"}
TEXT = {"RED": "#B42318", "AMBER": "#9A6700", "GREEN": "#18794E"}
UI = {
    "bg": "#EEF3F8", "card": "#FFFFFF", "glass": "#F8FBFF", "navy": "#102A43",
    "blue": "#2563EB", "blue2": "#60A5FA", "muted": "#64748B", "border": "#D7E1EC",
    "dark": "#0F172A", "field": "#FFFFFF", "disabled": "#EEF2F6"
}

HEADER_FIELDS = [
    ("supplier_gstin", "Supplier GSTIN"), ("docno", "Invoice / document number"),
    ("docdate", "Date (DD/MM/YYYY)"), ("suptype", "Supply type"),
    ("doctype", "Document type"), ("buyer_name", "Buyer name"),
    ("buyer_addr", "Buyer address"), ("buyer_city", "Buyer city"),
    ("buyer_gstin", "Buyer GSTIN"), ("buyer_pin", "Buyer PIN (999999 for export)"),
    ("country", "Country code (export)"), ("currency", "Currency"),
    ("rate", "Exchange rate (INR per 1 unit)"), ("port", "Port code (export of goods)"),
    ("uqc", "Default UQC (goods only)"), ("rcm", "Reverse Charge"),
    ("igst_intra", "IGST on Intra-State"), ("reporting30", "30-day rule applies (AATO ≥ ₹10 Cr)"),
]
ITEM_COLS = [
    ("sl", "Sl", 42), ("desc", "Description", 300), ("hsn", "HSN / SAC", 90),
    ("qty", "Qty", 70), ("unit", "UQC", 90), ("rate", "Rate", 90),
    ("value", "Taxable value", 115), ("gst", "GST %", 65),
]


class InvoiceEditor(tk.Toplevel):
    """One authoritative correction workspace; changes are retained by the parent app."""

    def __init__(self, app, engine, inv, opt, supplier, profile, res, on_generate, on_state_change=None):
        super().__init__(app)
        self.title("PraNam E-Invoice Converter  •  Review & Correct")
        self.transient(app)
        self.engine, self.inv, self.opt, self.supplier, self.profile = engine, inv, opt, supplier, profile
        self.res, self.on_generate, self.on_state_change = res, on_generate, on_state_change
        self.field_widgets = {}
        self.vars = {}
        self.service_invoice = bool(getattr(inv, "is_service", False) or ("hsn" not in inv.columns and bool(inv.fields.get("sac_code") and inv.fields["sac_code"].text)))
        inv.is_service = self.service_invoice
        self.issue_records = {}
        self._uqc_buffer = ""
        # Use the available desktop aggressively: this workspace is intended to be the
        # single place where the invoice is corrected. On Windows, maximize so all
        # fields, item columns and the action footer remain reachable.
        try:
            self.state("zoomed")
        except Exception:
            fit_to_screen(self, 1600, 960)
        self.minsize(1100, 720)
        self.configure(bg=UI["bg"])
        self.protocol("WM_DELETE_WINDOW", self.close_keep)
        self._styles()
        self._build()
        self.load()
        self.show_issues()
        self.grab_set()
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _event=None):
        # Keep the issue list readable as the window changes size.
        try:
            self.issues.column("msg", width=max(280, self.winfo_width() // 4))
        except Exception:
            pass

    def _styles(self):
        s = ttk.Style(self)
        try: s.theme_use("clam")
        except tk.TclError: pass
        s.configure("TFrame", background=UI["bg"])
        s.configure("Card.TLabelframe", background=UI["card"], bordercolor=UI["border"], relief="solid", borderwidth=1)
        s.configure("Card.TLabelframe.Label", background=UI["card"], foreground=UI["navy"], font=("Segoe UI", 10, "bold"))
        s.configure("Field.TEntry", fieldbackground=UI["field"], foreground=UI["dark"], padding=7)
        s.configure("Error.TEntry", fieldbackground="#FFF7F7", foreground=UI["dark"], padding=7, bordercolor="#EF4444", lightcolor="#EF4444", darkcolor="#EF4444")
        s.configure("Warn.TEntry", fieldbackground="#FFFCF0", foreground=UI["dark"], padding=7, bordercolor="#F59E0B", lightcolor="#F59E0B", darkcolor="#F59E0B")
        s.configure("Field.TCombobox", fieldbackground=UI["field"], foreground=UI["dark"], padding=6)
        s.configure("Modern.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8), background=UI["card"])
        s.map("Modern.TButton", background=[("active", "#E8F0FE")])
        s.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(15, 9), foreground="white", background=UI["blue"])
        s.map("Primary.TButton", background=[("active", "#1D4ED8")])

    def _card(self, parent, title):
        f = ttk.LabelFrame(parent, text=f"  {title}  ", style="Card.TLabelframe", padding=(12, 10))
        return f

    def _build(self):
        """Build a responsive correction workspace with a fixed action footer."""
        # Root grid is used instead of nested pack/expand so the footer and header can
        # never disappear behind the Windows taskbar/DPI scaling.
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=UI["navy"], height=78)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(header, text="P", bg=UI["blue"], fg="white", font=("Segoe UI", 20, "bold"),
                 width=2, height=1).pack(side="left", padx=(18, 10), pady=15)
        titlebox = tk.Frame(header, bg=UI["navy"]); titlebox.pack(side="left", pady=9)
        tk.Label(titlebox, text="PraNam E-Invoice Converter", bg=UI["navy"], fg="white",
                 font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(titlebox, text="Review  •  Correct  •  Re-check  •  Generate   |   Offline GST / IRP pre-validation",
                 bg=UI["navy"], fg="#C7D9F2", font=("Segoe UI", 9)).pack(anchor="w")
        self.status_badge = tk.Label(header, text="", bg="#183B62", fg="white",
                                     font=("Segoe UI", 10, "bold"), padx=14, pady=7)
        self.status_badge.pack(side="right", padx=18)

        # Fixed footer: the user always knows the next action and the buttons are always visible.
        footer = tk.Frame(self, bg="#FFFFFF", highlightbackground=UI["border"], highlightthickness=1, height=68)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)
        self.next_step = tk.Label(footer, text="STEP 1  •  Correct RED errors  →  STEP 2  •  Re-check / Revalidate  →  STEP 3  •  Generate Files",
                                  bg="#FFFFFF", fg=TEXT["RED"], font=("Segoe UI", 9, "bold"), anchor="w")
        self.next_step.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        actions = tk.Frame(footer, bg="#FFFFFF")
        actions.grid(row=0, column=1, sticky="e", padx=10)
        ttk.Button(actions, text="Return Home (save)", style="Modern.TButton", command=self.close_keep).pack(side="left", padx=3)
        ttk.Button(actions, text="↻  Re-check & Validate", style="Primary.TButton", command=self.recheck).pack(side="left", padx=3)
        self.gen = ttk.Button(actions, text="3  •  Generate Files", style="Primary.TButton", command=self.generate)
        self.gen.pack(side="left", padx=3)

        body = tk.Frame(self, bg=UI["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        body.grid_columnconfigure(0, weight=1, minsize=700)
        body.grid_columnconfigure(1, weight=0, minsize=390)
        body.grid_rowconfigure(0, weight=1)

        # Left side scrolls vertically so every invoice field and item control is reachable.
        left_shell = tk.Frame(body, bg=UI["bg"])
        left_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_shell.grid_rowconfigure(0, weight=1); left_shell.grid_columnconfigure(0, weight=1)
        canvas = tk.Canvas(left_shell, bg=UI["bg"], highlightthickness=0)
        left_scroll = ttk.Scrollbar(left_shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=left_scroll.set)
        canvas.grid(row=0, column=0, sticky="nsew"); left_scroll.grid(row=0, column=1, sticky="ns")
        left = tk.Frame(canvas, bg=UI["bg"])
        window_id = canvas.create_window((0, 0), window=left, anchor="nw")
        self._left_canvas, self._left_window_id = canvas, window_id
        def _left_config(_e=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(window_id, width=max(canvas.winfo_width(), left.winfo_reqwidth()))
        left.bind("<Configure>", _left_config)
        canvas.bind("<Configure>", _left_config)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        # Status strip is intentionally explicit: users do not need to remember what to do next.
        strip = tk.Frame(left, bg="#E7EEF7", highlightbackground=UI["border"], highlightthickness=1)
        strip.pack(fill="x", pady=(0, 7))
        self.counts = tk.Label(strip, text="", bg="#E7EEF7", fg=UI["dark"],
                               font=("Segoe UI", 10, "bold"), padx=12, pady=8)
        self.counts.pack(side="left")
        # Prominent in-workspace revalidation command: the user should never have to
        # leave this screen after correcting a value.
        ttk.Button(strip, text="↻  Re-check / Revalidate", style="Primary.TButton",
                   command=self.recheck).pack(side="right", padx=(8, 10), pady=5)
        tk.Label(strip, text="Correct fields → click Re-check → review remaining issues.",
                 bg="#E7EEF7", fg=UI["muted"], font=("Segoe UI", 9, "bold")).pack(side="right", padx=8)

        head = self._card(left, "Invoice details")
        head.pack(fill="x", pady=(0, 7))
        head.grid_columnconfigure(1, weight=1); head.grid_columnconfigure(4, weight=1)
        tk.Label(head, text="Correct a value → click Re-check & Validate → review the updated issues → Generate Files when RED = 0.",
                 bg=UI["card"], fg=UI["muted"], font=("Segoe UI", 9, "bold"),
                 wraplength=850, justify="left").grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 7))
        masters = self.engine.masters
        for i, (key, label) in enumerate(HEADER_FIELDS):
            r, c = 1 + i // 2, (i % 2) * 3
            tk.Label(head, text=label, bg=UI["card"], fg=UI["dark"],
                     font=("Segoe UI", 9, "bold")).grid(row=r, column=c, sticky="w", padx=(0, 5), pady=3)
            var = tk.StringVar(); self.vars[key] = var
            if key == "suptype":
                w = ttk.Combobox(head, textvariable=var, values=[""] + masters.supply_types,
                                 state="readonly", width=24, height=7, style="Field.TCombobox")
            elif key == "doctype":
                w = ttk.Combobox(head, textvariable=var, values=masters.doc_types,
                                 state="readonly", width=24, height=7, style="Field.TCombobox")
            elif key == "uqc":
                vals = [""] + masters.unit_descriptions
                w = ttk.Combobox(head, textvariable=var, values=vals, state="normal", width=24, height=10, style="Field.TCombobox")
                self._bind_uqc_search(w, vals)
            elif key in {"rcm", "igst_intra"}:
                w = ttk.Combobox(head, textvariable=var, values=["No", "Yes"], state="readonly", width=24, height=2, style="Field.TCombobox")
            elif key == "reporting30":
                w = ttk.Checkbutton(head, variable=var, onvalue="Yes", offvalue="No")
            else:
                w = ttk.Entry(head, textvariable=var, width=27, style="Field.TEntry")
            w.grid(row=r, column=c + 1, sticky="ew", padx=(0, 10), pady=2)
            self.field_widgets[key] = w
            var.trace_add("write", lambda *_args: self._mark_dirty())

        items = self._card(left, "Line items  •  double-click a cell to edit")
        items.pack(fill="both", expand=True)
        bar = tk.Frame(items, bg=UI["card"]); bar.pack(fill="x", pady=(0, 5))
        ttk.Button(bar, text="＋ Add row", style="Modern.TButton", command=self.add_row).pack(side="left")
        ttk.Button(bar, text="Delete selected", style="Modern.TButton", command=self.del_row).pack(side="left", padx=5)
        ttk.Button(bar, text="Set GST % for all", style="Modern.TButton", command=self.set_gst_all).pack(side="left")
        self.tree = ttk.Treeview(items, columns=[c[0] for c in ITEM_COLS], show="headings", height=8)
        for key, title, width in ITEM_COLS:
            self.tree.heading(key, text=title); self.tree.column(key, width=width, stretch=(key == "desc"), anchor="w")
        ys = ttk.Scrollbar(items, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(items, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side="right", fill="y"); xs.pack(side="bottom", fill="x"); self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.edit_cell)

        # Right-side issue workspace remains fixed while the invoice side scrolls.
        right = self._card(body, "Issues to correct")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1); right.grid_columnconfigure(0, weight=1)
        self.issue_hint = tk.Label(right,
            text="ALL current RED/AMBER issues appear here.\nCorrect them, then click Re-check / Revalidate.\nThe list will refresh automatically.",
            bg=UI["card"], fg=UI["muted"], font=("Segoe UI", 9), wraplength=340, justify="left")
        self.issue_hint.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.issue_status = tk.Label(right, text="", bg="#E7EEF7", fg=UI["dark"],
                                     font=("Segoe UI", 10, "bold"), padx=10, pady=8)
        self.issue_status.grid(row=1, column=0, sticky="ew", pady=(0, 7))
        self.issues = ttk.Treeview(right, columns=("lvl", "item", "msg"), show="headings")
        self.issues.heading("lvl", text="Status"); self.issues.column("lvl", width=66, stretch=False)
        self.issues.heading("item", text="Item"); self.issues.column("item", width=44, stretch=False)
        self.issues.heading("msg", text="What to correct"); self.issues.column("msg", width=300, stretch=True)
        sy = ttk.Scrollbar(right, orient="vertical", command=self.issues.yview)
        self.issues.configure(yscrollcommand=sy.set); sy.grid(row=2, column=1, sticky="ns"); self.issues.grid(row=2, column=0, sticky="nsew")
        for k in COLORS: self.issues.tag_configure(k, background=COLORS[k], foreground=TEXT[k])
        self.issues.bind("<<TreeviewSelect>>", self._jump_to_issue)

    def load(self):
        self._loading = True
        h, o, inv = self.res.header, self.opt, self.inv
        f = inv.fields; val = lambda k: f[k].text if k in f else ""
        self.vars["supplier_gstin"].set(self.supplier.gstin)
        self.vars["docno"].set(h.get("colDocno") or val("invoice_no"))
        self.vars["docdate"].set(h.get("colDocdate") or val("invoice_date"))
        self.vars["suptype"].set(o.supply_type); self.vars["doctype"].set(o.doc_type)
        self.vars["buyer_name"].set(h.get("colBLegalname", ""))
        self.vars["buyer_addr"].set(", ".join(x for x in (h.get("colBaddr1", ""), h.get("colBaddr2", "")) if x))
        self.vars["buyer_city"].set(h.get("colBLoc", "")); self.vars["buyer_gstin"].set(o.buyer_gstin)
        self.vars["buyer_pin"].set(h.get("colBPin", "")); self.vars["country"].set(h.get("colCntryCode", ""))
        self.vars["currency"].set(h.get("colForCur") or inv.currency.text); self.vars["rate"].set(str(o.exchange_rate or ""))
        self.vars["port"].set(h.get("colPort", "")); self.vars["uqc"].set(o.uqc)
        self.vars["rcm"].set("Yes" if str(o.reverse_charge).upper() in {"YES", "Y"} else "No")
        self.vars["igst_intra"].set("Yes" if str(o.igst_on_intra).upper() in {"YES", "Y"} else "No")
        self.vars["reporting30"].set("Yes" if o.reporting_30d_applies else "No")
        self.tree.delete(*self.tree.get_children())
        service = self.service_invoice
        for it in inv.items:
            rec = next((r for r in self.res.items if r.get("colProdSlno") == str(it.sl_no)), {})
            unit = "Not Applicable" if service else (rec.get("colUnit") or self._num(it, "uqc") or o.uqc)
            qty = "Not Applicable" if service else (rec.get("colQuantity") or self._num(it, "qty"))
            iid = self.tree.insert("", "end", values=(it.sl_no, it.description.text, rec.get("colHsn") or it.hsn.text,
                qty, unit, self._num(it, "rate") or self._num(it, "rate_per_carton") or self._num(it, "rate_per_piece"),
                self._num(it, "amount") or self._num(it, "taxable_value"), rec.get("colGstrate") or self._num(it, "gst_rate")))
            if service:
                self.tree.item(iid, tags=("NA",))
        self.tree.tag_configure("NA", foreground="#64748B")
        self._loading = False

    @staticmethod
    def _num(it, role):
        sv = it.values.get(role)
        return "" if sv is None or sv.value in (None, "") else str(sv.value)

    def _bind_uqc_search(self, combo, values):
        # Editable searchable UQC: P -> first P..., PA -> first PA..., etc.
        def on_key(event):
            if event.keysym in {"Up", "Down", "Left", "Right", "Return", "Escape", "Tab", "BackSpace"}:
                return
            ch = (event.char or "").strip()
            if not ch or not ch.isprintable(): return
            self._uqc_buffer += ch.upper()
            if hasattr(self, "_uqc_after") and self._uqc_after:
                try: self.after_cancel(self._uqc_after)
                except Exception: pass
            self._uqc_after = self.after(700, lambda: setattr(self, "_uqc_buffer", ""))
            match = next((v for v in values if v and v.upper().startswith(self._uqc_buffer)), None)
            if match:
                combo.set(match); combo.icursor(tk.END)
        combo.bind("<KeyPress>", on_key, add="+")

    def _apply_field_style(self, key, level=None):
        w = self.field_widgets.get(key)
        if not w: return
        # ttk state highlight is intentionally subtle; avoid confusing grey disabled-looking fields.
        try:
            if level == "RED": w.configure(style="Error.TEntry")
            elif level == "AMBER": w.configure(style="Warn.TEntry")
            else: w.configure(style="Field.TEntry")
        except Exception: pass

    def _mark_dirty(self):
        if getattr(self, "_loading", False):
            return
        try:
            self.next_step.config(text="Changes detected  •  Click  Re-check & Validate  to refresh RED/AMBER status.", fg=UI["navy"])
        except Exception:
            pass

    def apply(self):
        inv, o, g = self.inv, self.opt, self.vars
        corrected_supplier_gstin = g["supplier_gstin"].get().strip().upper()
        self.supplier.gstin = corrected_supplier_gstin
        set_field = lambda k, v: inv.fields.__setitem__(k, SourceValue(v, "user correction", "corrected on screen"))
        if corrected_supplier_gstin: set_field("exporter_gstin", corrected_supplier_gstin)
        if g["docno"].get().strip(): set_field("invoice_no", g["docno"].get().strip())
        if g["docdate"].get().strip(): set_field("invoice_date", g["docdate"].get().strip())
        o.supply_type = g["suptype"].get().strip(); o.doc_type = g["doctype"].get().strip() or o.doc_type
        o.transaction_type = "Domestic" if o.supply_type in {"B2B", "SEZWP", "SEZWOP", "DEXP"} else "Export"
        o.reverse_charge = g["rcm"].get().strip() or "No"; o.igst_on_intra = g["igst_intra"].get().strip() or "No"
        o.reporting_30d_applies = g["reporting30"].get().strip().lower() == "yes"
        corrected_buyer_gstin = g["buyer_gstin"].get().strip().upper(); o.buyer_gstin = corrected_buyer_gstin
        for party in (getattr(inv, "buyer_block", None), getattr(inv, "buyer_block2", None), getattr(inv, "consignee", None), getattr(inv, "notify_party", None)):
            if party is not None and corrected_buyer_gstin: party.gstin = corrected_buyer_gstin
        name, addr = g["buyer_name"].get().strip(), g["buyer_addr"].get().strip()
        if name or addr:
            inv.buyer_block2 = Party(name, [a.strip() for a in addr.split(",") if a.strip()], "user correction")
            inv.buyer_block2.gstin = corrected_buyer_gstin; o.buyer_party = "buyer_block2"
        o.buyer_location = g["buyer_city"].get().strip(); o.country_code = g["country"].get().strip().upper(); o.port_code = g["port"].get().strip().upper()
        o.exchange_rate = to_decimal(g["rate"].get()) if g["rate"].get().strip() else None
        if o.exchange_rate is not None: o.exchange_rate_source = "Corrected on screen"
        if g["currency"].get().strip(): inv.currency = SourceValue(g["currency"].get().strip().upper(), "user correction", "corrected on screen")
        o.uqc = g["uqc"].get().strip(); o.buyer_pin = g["buyer_pin"].get().strip()

        rows = [self.tree.item(i, "values") for i in self.tree.get_children()]
        items = []; from ..models import SourceItem
        service_invoice = self.service_invoice
        inv.is_service = service_invoice
        for n, row in enumerate(rows, 1):
            sl, desc, hsn, qty, unit, rate, value, gst = [str(x).strip() for x in row]
            src = next((it for it in inv.items if str(it.sl_no) == str(sl)), None)
            item = SourceItem(n, src.row if src else 0, SourceValue(desc, "user correction"), SourceValue(hsn, "user correction")); item.values = {}
            if not service_invoice:
                for role, raw in (("qty", qty), ("uqc", unit), ("rate", rate), ("amount", value), ("gst_rate", gst)):
                    if raw and raw != "Not Applicable": item.values[role] = SourceValue(raw, "user correction")
            else:
                for role, raw in (("rate", rate), ("amount", value), ("gst_rate", gst)):
                    if raw: item.values[role] = SourceValue(raw, "user correction")
            items.append(item)
            if gst and to_decimal(gst) is not None: o.item_gst_rates[n] = to_decimal(gst)
        if items:
            inv.items = items; inv.columns = {"description": "B", "amount": "G"}
            if not service_invoice:
                inv.columns["hsn"] = "C"
                if any("qty" in i.values for i in items): inv.columns["qty"] = "D"; o.quantity_basis = "source_qty"
                if any("uqc" in i.values for i in items): inv.columns["uqc"] = "E"
                if any("rate" in i.values for i in items): inv.columns["rate"] = "F"
            if any("gst_rate" in i.values for i in items): inv.columns["gst_rate"] = "H"

    def recheck(self, notify=True):
        self.apply()
        self.res = self.engine.analyse(self.inv, self.opt, self.supplier, self.profile)
        self.load(); self.show_issues()
        self._publish_state()
        if notify:
            try: self.bell()
            except Exception: pass

    def _publish_state(self):
        if self.on_state_change:
            try: self.on_state_change(self.res, self.inv, self.opt, self.supplier)
            except Exception: pass

    def show_issues(self):
        self.issues.delete(*self.issues.get_children()); self.issue_records.clear()
        order = {"RED": 0, "AMBER": 1, "GREEN": 2}
        for issue in sorted(self.res.issues, key=lambda x: (order[x.level], x.item_no or 0, x.field)):
            label = {"RED": "ERROR", "AMBER": "WARN", "GREEN": "OK"}[issue.level]
            iid = self.issues.insert("", "end", tags=(issue.level,), values=(label, issue.item_no or "—", f"{issue.field}: {issue.message}"))
            self.issue_records[iid] = issue
        red, amber = self.res.issues.n("RED"), self.res.issues.n("AMBER")
        if red:
            text, bg, fg = f"🔴 {red} errors   🟠 {amber} warnings", COLORS["RED"], TEXT["RED"]
            self.status_badge.config(text="ACTION REQUIRED", bg="#7F1D1D")
        elif amber:
            text, bg, fg = f"✓ 0 errors   🟠 {amber} warnings", COLORS["AMBER"], TEXT["AMBER"]
            self.status_badge.config(text="REVIEW WARNINGS", bg="#8A5A00")
        else:
            text, bg, fg = "✓ READY FOR JSON GENERATION", COLORS["GREEN"], TEXT["GREEN"]
            self.status_badge.config(text="READY", bg="#176B4D")
        self.counts.config(text=text, bg=bg, fg=fg); self.issue_status.config(text=text, bg=bg, fg=fg)
        self.gen.state(["disabled"] if red else ["!disabled"])
        if red:
            self.next_step.config(text="Step 1 of 3  •  Correct the RED errors. Then click  Re-check & Validate  to validate everything again.", fg=TEXT["RED"])
        elif amber:
            self.next_step.config(text="Step 2 of 3  •  No blocking errors. Review warnings if required, then click Generate Files.", fg=TEXT["AMBER"])
        else:
            self.next_step.config(text="Step 3 of 3  •  Validation passed. Click Generate Files to create the JSON/NIC files.", fg=TEXT["GREEN"])

    def _jump_to_issue(self, _event=None):
        sel = self.issues.selection()
        if not sel: return
        issue = self.issue_records.get(sel[0]);
        if not issue: return
        # Item-specific errors always jump to the item first. This is important for
        # UQC/HSN/Qty errors: do not send the user to the generic Default UQC field.
        if issue.item_no:
            target = None
            for iid in self.tree.get_children():
                vals = self.tree.item(iid, "values")
                if vals and str(vals[0]) == str(issue.item_no):
                    target = iid; break
            if target:
                self.tree.selection_set(target); self.tree.focus(target); self.tree.see(target)
                col = self._item_column(issue.field, issue.message)
                if col:
                    self._flash_item(target, col, issue.level)
                    return
        key = self._field_key(issue.field, issue.message)
        if key and key in self.field_widgets:
            w = self.field_widgets[key]; w.focus_set(); self._highlight_widget(w, issue.level)
            return

    @staticmethod
    def _field_key(field, message):
        f = (field + " " + message).lower()
        checks = [("supplier gstin", "supplier_gstin"), ("buyer gstin", "buyer_gstin"), ("invoice date", "docdate"),
                  ("document date", "docdate"), ("document number", "docno"), ("doc no", "docno"), ("supply type", "suptype"),
                  ("reverse charge", "rcm"), ("igst on intra", "igst_intra"), ("buyer pin", "buyer_pin"),
                  ("exchange rate", "rate"), ("currency", "currency"), ("port", "port"), ("gst uqc", "uqc")]
        for needle, key in checks:
            if needle in f: return key
        return None

    @staticmethod
    def _item_column(field, message):
        f = (field + " " + message).lower()
        if "uqc" in f or "unit" in f: return "#5"
        if "quantity" in f or "qty" in f: return "#4"
        if "rate" in f or "gst rate" in f: return "#8"
        if "hsn" in f or "sac" in f: return "#3"
        return None

    def _highlight_widget(self, widget, level):
        try:
            old = widget.cget("style")
            style = "Error.TEntry" if level == "RED" else "Warn.TEntry"
            widget.configure(style=style)
            self.after(1300, lambda: widget.configure(style=old or "Field.TEntry"))
        except Exception: pass

    def _flash_item(self, iid, col, level):
        try:
            self.tree.see(iid); self.tree.selection_set(iid)
            old = self.tree.item(iid, "tags")
            self.tree.tag_configure("FLASH", background=COLORS.get(level, "#E8F0FE"), foreground=TEXT.get(level, UI["dark"]))
            self.tree.item(iid, tags=("FLASH",))
            self.after(1300, lambda: self.tree.item(iid, tags=old))
        except Exception: pass

    def edit_cell(self, event):
        iid = self.tree.identify_row(event.y); col = self.tree.identify_column(event.x)
        if not iid or not col: return
        idx = int(col[1:]) - 1; x, y, w, h = self.tree.bbox(iid, col)
        vals = list(self.tree.item(iid, "values"));
        if idx in (3, 4) and vals[idx] == "Not Applicable": return
        var = tk.StringVar(value=vals[idx]); entry = ttk.Entry(self.tree, textvariable=var); entry.place(x=x, y=y, width=w, height=h); entry.focus_set()
        def done(_e=None):
            vals[idx] = var.get(); self.tree.item(iid, values=vals); entry.destroy()
        entry.bind("<Return>", done); entry.bind("<FocusOut>", done); entry.bind("<Escape>", lambda e: entry.destroy())

    def add_row(self):
        n = len(self.tree.get_children()) + 1; self.tree.insert("", "end", values=(n, "", "", "", "", "", "", ""))

    def del_row(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def set_gst_all(self):
        from tkinter import simpledialog
        v = simpledialog.askstring("GST rate", "GST rate (%) for every item:", parent=self)
        if v is None or to_decimal(v) is None: return
        for i in self.tree.get_children():
            vals = list(self.tree.item(i, "values")); vals[7] = v; self.tree.item(i, values=vals)

    def close_keep(self):
        try:
            self.apply(); self.res = self.engine.analyse(self.inv, self.opt, self.supplier, self.profile); self._publish_state()
        finally:
            self.destroy()

    def _discard(self):
        self.destroy()

    def generate(self):
        self.recheck(notify=False)
        if self.res.issues.has_red:
            messagebox.showerror("Cannot generate", "Some values still need correcting. See the Issues to correct panel.", parent=self); return
        try:
            out = self.on_generate(self.res, self.inv, self.opt)
        except Exception as e:
            messagebox.showerror("Generation failed", f"{type(e).__name__}: {e}", parent=self); return
        self._publish_state(); self.destroy(); return out
