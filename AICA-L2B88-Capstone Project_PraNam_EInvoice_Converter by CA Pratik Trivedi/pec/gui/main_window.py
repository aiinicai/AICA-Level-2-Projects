"""One-button screen: select the invoice -> everything is read from the Excel -> files generated."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .. import APP_NAME, APP_VERSION
from ..engine import Engine
from ..logsetup import get_logger
from ..nic_template import TemplateError
from ..paths import app_dir, output_dir
from ..settings import load_app_settings, load_profile, save_app_settings
from ..source_reader import SourceReadError
from ..util import fmt, to_decimal
from .widgets import enable_windows_dpi_awareness, fit_to_screen, open_path

log = get_logger()
COLORS = {"RED": "#FFC7CE", "AMBER": "#FFF2CC", "GREEN": "#E2EFDA"}
UI = {"bg": "#F4F7FB", "card": "#FFFFFF", "navy": "#17365D", "blue": "#2563EB", "muted": "#64748B", "border": "#D8E0EA", "dark": "#0F172A"}


def find_template(settings) -> str:
    p = settings.get("template_path", "")
    if p and Path(p).exists():
        return p
    for folder in (app_dir() / "Template", app_dir()):
        c = sorted(folder.glob("NIC-GePP*.xlsm")) if folder.exists() else []
        if c:
            return str(c[0])
    return ""


class MainWindow(tk.Tk):
    def __init__(self):
        enable_windows_dpi_awareness()
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        fit_to_screen(self, 1400, 900)
        self.configure(bg=UI["bg"])
        try:
            self.state("zoomed")
        except Exception:
            pass
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TFrame", background=UI["bg"])
        st.configure("Card.TLabelframe", background=UI["card"], bordercolor=UI["border"], relief="solid", borderwidth=1)
        st.configure("Card.TLabelframe.Label", background=UI["card"], foreground=UI["navy"], font=("Segoe UI", 10, "bold"))
        st.configure("Big.TButton", font=("Segoe UI", 12, "bold"), padding=(18, 11), foreground="white", background=UI["blue"])
        st.map("Big.TButton", background=[("active", "#1D4ED8")])
        st.configure("Modern.TButton", font=("Segoe UI", 10, "bold"), padding=(11, 7), background=UI["card"])
        st.map("Modern.TButton", background=[("active", "#E8F0FE")])
        self.settings = load_app_settings()
        self.profile = load_profile(None)
        self._engine = None
        self.last = None
        self._build()
        self.after(400, self._check_packages)

    # ---------------------------------------------------------------- UI
    def _build(self):
        """Premium glass-style dashboard. Functional layout remains simple and fast."""
        # Header / brand
        head = tk.Frame(self, bg=UI["navy"], height=112)
        head.pack(side="top", fill="x"); head.pack_propagate(False)
        tk.Label(head, text="P", bg=UI["blue"], fg="white", font=("Segoe UI", 21, "bold"), width=2).pack(side="left", padx=(24, 12), pady=18)
        brand = tk.Frame(head, bg=UI["navy"]); brand.pack(side="left", pady=14)
        tk.Label(brand, text="PraNam E-Invoice Converter", bg=UI["navy"], fg="white", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(brand, text=f"Offline GST / IRP pre-validation  •  v{APP_VERSION}", bg=UI["navy"], fg="#C7D9F2", font=("Segoe UI", 9)).pack(anchor="w")
        self.header_status = tk.Label(head, text="READY", bg="#176B4D", fg="white", font=("Segoe UI", 10, "bold"), padx=16, pady=8)
        self.header_status.pack(side="right", padx=24, pady=18)

        # Fixed command bar. Use a grid so buttons never get pushed below the visible window.
        foot = tk.Frame(self, bg="#FFFFFF", height=74, highlightbackground=UI["border"], highlightthickness=1)
        foot.pack(side="bottom", fill="x"); foot.pack_propagate(False)
        foot.grid_columnconfigure(2, weight=1)
        ttk.Button(foot, text="⚙  Settings", style="Modern.TButton", command=self.open_settings).grid(row=0, column=0, padx=(16, 6), pady=10, sticky="w")
        ttk.Button(foot, text="Open Output Folder", style="Modern.TButton", command=lambda: open_path(self.out_dir())).grid(row=0, column=1, padx=6, pady=10, sticky="w")
        self.status = tk.Label(foot, text="Ready to import an invoice.", bg="#FFFFFF", fg=UI["muted"], font=("Segoe UI", 9), anchor="w")
        self.status.grid(row=0, column=2, padx=14, pady=10, sticky="ew")
        ttk.Button(foot, text="Exit", style="Modern.TButton", command=self.destroy).grid(row=0, column=3, padx=(6, 16), pady=10, sticky="e")

        body = tk.Frame(self, bg=UI["bg"]); body.pack(fill="both", expand=True, padx=14, pady=10)

        # Action card — two-row layout keeps every action reachable even on smaller screens.
        action = tk.Frame(body, bg="#F8FBFF", highlightbackground="#D8E5F3", highlightthickness=1)
        action.pack(fill="x", pady=(0, 12))
        action.grid_columnconfigure(5, weight=1)
        tk.Label(action, text="Invoice workspace", bg="#F8FBFF", fg=UI["navy"], font=("Segoe UI", 13, "bold")).grid(row=0, column=0, padx=(18, 12), pady=(11, 4), sticky="w")
        ttk.Button(action, text="Import Invoice  •  Validate  •  Generate", style="Big.TButton", command=self.pick_and_process).grid(row=0, column=1, columnspan=2, padx=5, pady=9, sticky="w")
        self.again = ttk.Button(action, text="Process same file again", style="Modern.TButton", command=lambda: self.process(self.last))
        self.again.grid(row=1, column=0, padx=(18, 4), pady=(0, 9), sticky="w"); self.again.state(["disabled"])
        self.check_btn = ttk.Button(action, text="Review & Correct", style="Modern.TButton", command=self.open_editor)
        self.check_btn.grid(row=1, column=1, padx=4, pady=(0, 9), sticky="w"); self.check_btn.state(["disabled"])
        self.generate_btn = ttk.Button(action, text="3  •  Generate Files", style="Primary.TButton", command=self.generate_current)
        self.generate_btn.grid(row=1, column=2, padx=4, pady=(0, 9), sticky="w"); self.generate_btn.state(["disabled"])
        self.file_lbl = tk.Label(action, text="No invoice loaded", bg="#F8FBFF", fg=UI["muted"], font=("Segoe UI", 9))
        self.file_lbl.grid(row=1, column=3, columnspan=3, padx=(10, 18), pady=(0, 9), sticky="w")

        # Status banner
        self.banner = tk.Label(body, text="Import an invoice to begin.", bg="#E8F0F8", fg=UI["navy"], font=("Segoe UI", 11, "bold"), anchor="w", padx=16, pady=10)
        self.banner.pack(fill="x", pady=(0, 12))

        # Glass summary cards
        cards = tk.Frame(body, bg=UI["bg"]); cards.pack(fill="x", pady=(0, 12))
        for i in range(4): cards.grid_columnconfigure(i, weight=1)
        self.summary_cards = {}
        for i, (key, title) in enumerate((("invoice", "Invoice"), ("buyer", "Buyer"), ("taxable", "Taxable Value"), ("total", "Invoice Value"))):
            card = tk.Frame(cards, bg="#FFFFFF", highlightbackground=UI["border"], highlightthickness=1, height=78)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0)); card.grid_propagate(False)
            tk.Label(card, text=title.upper(), bg="#FFFFFF", fg=UI["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=12, pady=(10, 0))
            val = tk.Label(card, text="—", bg="#FFFFFF", fg=UI["dark"], font=("Segoe UI", 11, "bold"), anchor="w")
            val.pack(anchor="w", padx=12, pady=(2, 0)); self.summary_cards[key] = val

        # Files/action links
        self.summary = tk.Frame(body, bg=UI["bg"]); self.summary.pack(fill="x")
        self.files = tk.Frame(body, bg=UI["bg"]); self.files.pack(fill="x", pady=(0, 8))

        box = tk.Frame(body, bg="#FFFFFF", highlightbackground=UI["border"], highlightthickness=1)
        box.pack(fill="both", expand=True)
        top = tk.Frame(box, bg="#FFFFFF", height=42); top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top, text="Validation results", bg="#FFFFFF", fg=UI["navy"], font=("Segoe UI", 12, "bold")).pack(side="left", padx=14, pady=10)
        tk.Label(top, text="Offline checks • RED blocks generation • AMBER requires review", bg="#FFFFFF", fg=UI["muted"], font=("Segoe UI", 8)).pack(side="right", padx=14)
        table = tk.Frame(box, bg="#FFFFFF"); table.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree = ttk.Treeview(table, columns=("lvl", "item", "msg"), show="headings")
        for c, h, w, stretch in (("lvl", "Type", 80, False), ("item", "Item", 60, False), ("msg", "Detail", 900, True)):
            self.tree.heading(c, text=h); self.tree.column(c, width=w, stretch=stretch, anchor="w")
        ys = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y"); self.tree.pack(fill="both", expand=True)
        for k, v in COLORS.items(): self.tree.tag_configure(k, background=v)
    def _check_packages(self):
        missing = []
        for mod, pkg in (("openpyxl", "openpyxl"), ("pdfplumber", "pdfplumber"), ("docx", "python-docx"),
                         ("cv2", "opencv-python-headless"), ("numpy", "numpy"), ("pytesseract", "pytesseract"),
                         ("pypdfium2", "pypdfium2"), ("PIL", "pillow"), ("jsonschema", "jsonschema")):
            try:
                __import__(mod)
            except ImportError:
                missing.append(pkg)
        if missing:
            self.banner.config(text="  Missing packages: " + ", ".join(missing) +
                                    "  -  run install_requirements.bat in this folder once, then restart.",
                               bg=COLORS["AMBER"], fg="#7F6000")
            self.status.config(text="Some file types will not open until these are installed.")

    def out_dir(self):
        return self.settings.get("output_dir") or str(output_dir())

    # ---------------------------------------------------------------- engine
    def engine(self):
        path = find_template(self.settings)
        if not path:
            messagebox.showinfo("NIC template (one time)", "Please locate NIC-GePP_V2.0.xlsm once. It will be remembered.", parent=self)
            path = filedialog.askopenfilename(parent=self, filetypes=[("NIC-GePP utility", "*.xlsm")])
            if not path:
                return None
        if self._engine and str(self._engine.template) == path:
            return self._engine
        try:
            self._busy("Loading NIC masters...")
            self._engine = Engine(path)
            self.settings["template_path"] = path
            save_app_settings(self.settings)
            return self._engine
        except (TemplateError, Exception) as e:
            log.exception("template")
            messagebox.showerror("NIC template", f"Could not use the NIC template: {e}", parent=self)
            self.settings["template_path"] = ""
            return None
        finally:
            self._busy(None)

    def _busy(self, msg):
        self.config(cursor="watch" if msg else "")
        if msg:
            self.status.config(text=msg)
        self.update()

    # ---------------------------------------------------------------- process
    def pick_and_process(self):
        p = filedialog.askopenfilename(parent=self, title="Select invoice (Excel / PDF / Word / scan)",
                                       initialdir=self.settings.get("last_dir") or None,
                                       filetypes=[("Invoice (Excel, PDF, Word, scan)", "*.xlsx *.xlsm *.pdf *.docx *.png *.jpg *.jpeg *.tif *.tiff"),
                                                  ("Excel", "*.xlsx *.xlsm"), ("PDF", "*.pdf"), ("Word", "*.docx"),
                                                  ("Scan / image", "*.png *.jpg *.jpeg *.tif *.tiff"),
                                                  ("All files", "*.*")])
        if p:
            self.settings["last_dir"] = str(Path(p).parent)
            save_app_settings(self.settings)
            self.process(p)

    def process(self, path):
        if not path:
            return
        self.last = path
        self.again.state(["!disabled"])
        self.file_lbl.config(text=Path(path).name)
        eng = self.engine()
        if not eng:
            return
        try:
            self._busy("Reading invoice...")
            invoices = eng.read_sources(path, self.profile, self.settings.get("tesseract_path", ""))
            if len(invoices) > 1:
                self._busy(f"Found {len(invoices)} invoices in this file - converting...")
            results, failures = [], []
            for k, inv in enumerate(invoices, 1):
                opt = eng.auto_options(inv, self.settings)
                sup, notes = eng.auto_supplier(inv)
                opt.auto_notes += notes
                res = eng.analyse(inv, opt, sup, self.profile)
                if len(invoices) == 1:
                    # the one value a foreign-currency invoice may not print
                    if opt.exchange_rate is None and any(i.field == "Exchange Rate" and i.level == "RED" for i in res.issues):
                        self._busy(None)
                        v = simpledialog.askstring(
                            "Exchange rate not on invoice",
                            f"Invoice {res.header.get('colDocno', '')} is in {inv.currency.text} and has no exchange "
                            f"rate.\n\nEnter INR per 1 {inv.currency.text} (or Cancel and add "
                            "'EXCHANGE RATE : xx.xx' to the invoice):", parent=self)
                        rate = to_decimal(v) if v else None
                        if rate and rate > 0:
                            opt.exchange_rate, opt.exchange_rate_source = rate, "Entered when prompted"
                            res = eng.analyse(inv, opt, sup, self.profile)
                    if not opt.port_code and any(i.field == "Port" and i.level == "RED" for i in res.issues):
                        self._busy(None)
                        pol = inv.fields.get("port_of_loading")
                        pol_text = pol.text if pol else ""
                        code = PortDialog(self, eng.masters, pol_text).result
                        if code:
                            opt.port_code = code
                            self.settings.setdefault("port_map", {})[pol_text.upper()] = code
                            save_app_settings(self.settings)
                            res = eng.analyse(inv, opt, sup, self.profile)
                self._last_state = (eng, inv, opt, sup, res)
                self.check_btn.state(["!disabled"])
                if res.issues.has_red:
                    if len(invoices) == 1:
                        self._busy(None)
                        self.show(res, None)
                        self.open_editor()          # correct the values and generate from there
                        return
                    failures.append((res, inv))
                    continue
                self._busy(f"Generating files ({k}/{len(invoices)})...")
                out = eng.generate(res, self.out_dir(), sup)
                mem = self.settings.setdefault("hsn_rates", {})
                for it, rec in zip(inv.items, res.items):
                    if it.num("gst_rate") is not None:
                        mem[rec["colHsn"]] = rec.get("colGstrate", "")
                results.append((res, out))
            save_app_settings(self.settings)
            if len(invoices) > 1:
                self.show_batch(results, failures)
            elif results:
                self.show(results[0][0], results[0][1])
            else:
                self.show(failures[0][0], None)
        except SourceReadError as e:
            self._error(str(e))
        except PermissionError:
            self._error("An output file is open in Excel. Close it and click 'Process same file again'.")
        except Exception as e:
            log.exception("process failed")
            self._error(f"Unexpected problem ({type(e).__name__}: {e}). Details saved in logs/app.log.")
        finally:
            self._busy(None)

    def generate_current(self):
        st = getattr(self, "_last_state", None)
        if not st:
            return
        eng, inv, opt, sup, _res = st
        try:
            res = eng.analyse(inv, opt, sup, self.profile)
        except Exception as e:
            self._error(f"Validation failed before generation: {e}")
            return
        self._last_state = (eng, inv, opt, sup, res)
        self.show(res, None)
        if res.issues.has_red:
            self.open_editor()
            return
        try:
            self._busy("Generating files...")
            out = eng.generate(res, self.out_dir(), sup)
            self.show(res, out)
        except Exception as e:
            log.exception("generation failed")
            self._error(f"Generation failed ({type(e).__name__}: {e}). Details saved in logs/app.log.")
        finally:
            self._busy(None)

    def open_editor(self):
        st = getattr(self, "_last_state", None)
        if not st:
            return
        eng, inv, opt, sup, res = st

        def state_changed(res2, inv2, opt2, sup2):
            # One authoritative working invoice state. Keep the main screen synchronized
            # with every correction made in the review window.
            self._last_state = (eng, inv2, opt2, sup2, res2)
            self.show(res2, None)

        def make(res2, inv2, opt2):
            self._last_state = (eng, inv2, opt2, sup, res2)
            out2 = eng.generate(res2, self.out_dir(), sup)
            self.show(res2, out2)
            return out2
        from .editor import InvoiceEditor
        InvoiceEditor(self, eng, inv, opt, sup, self.profile, res, make, on_state_change=state_changed)

    def _error(self, msg):
        for w in self.summary.winfo_children() + self.files.winfo_children():
            w.destroy()
        self.tree.delete(*self.tree.get_children())
        self.banner.config(text="  " + msg, bg=COLORS["RED"], fg="#9C0006")
        self.status.config(text="Stopped.")

    def show(self, res, out):
        h = res.header
        if hasattr(self, "check_btn"):
            self.check_btn.state(["!disabled"])
        if hasattr(self, "generate_btn"):
            self.generate_btn.state(["disabled"] if res.issues.has_red else ["!disabled"])
        for w in self.summary.winfo_children() + self.files.winfo_children():
            w.destroy()
        cur = h.get("colForCur", "")
        if hasattr(self, "summary_cards"):
            self.summary_cards["invoice"].config(text=f"{h.get('colDocno', '')}  •  {h.get('colDocdate', '')}")
            self.summary_cards["buyer"].config(text=h.get('colBLegalname', '') or "—")
            self.summary_cards["taxable"].config(text=str(h.get('colTotTaxval', '—')))
            self.summary_cards["total"].config(text=str(h.get('colTinvoiceval', '—')))
        rows = [("Invoice", f"{h.get('colDocno', '')}   dated {h.get('colDocdate', '')}"),
                ("Export type", f"{h.get('colSupType', '')}" + ("  (refund claim: Yes)" if h.get("colSupRefund") == "Yes" else "")),
                ("Buyer", f"{h.get('colBLegalname', '')}, {h.get('colBLoc', '')} ({h.get('colCntryCode', '')})"),
                ("Items", f"{len(res.items)}    Port: {h.get('colPort', '')}    Currency: {cur}"),
                ("Taxable value (INR)", h.get("colTotTaxval", "-")), ("IGST (INR)", h.get("colTigstval", "-")),
                ("Invoice value (INR)", h.get("colTinvoiceval", "-")),
                ("Exchange rate", str(res.options.exchange_rate or "-"))]
        for i, (k, v) in enumerate(rows):
            ttk.Label(self.summary, text=k + ":", font=("Segoe UI", 10, "bold")).grid(row=i // 2, column=(i % 2) * 2, sticky="w", padx=(0, 8), pady=1)
            ttk.Label(self.summary, text=v, font=("Segoe UI", 10)).grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="w", padx=(0, 40))
        if out:
            ok = not out["problems"]
            self.header_status.config(text="GENERATED", bg="#176B4D")
            self.banner.config(text=("  Files generated  -  upload the JSON on the e-Invoice portal, or open the NIC file in the NIC utility"
                                     if ok else "  Files generated, but the post-write check reported a problem (see report)"),
                               bg=COLORS["GREEN"] if ok else COLORS["AMBER"], fg="#006100" if ok else "#7F6000")
            for label, key in (("Open e-Invoice JSON folder", "json"), ("Open NIC utility file", "nic"), ("Open check report", "report")):
                ttk.Button(self.files, text=label, command=lambda p=out[key]: open_path(p if key != "json" else Path(p).parent)).pack(side="left", padx=(0, 8))
            ttk.Label(self.files, text=Path(out["json"]).name, foreground="#555").pack(side="left", padx=8)
            self.status.config(text=f"Saved in {Path(out['nic']).parent}")
        else:
            n = res.issues.n("RED")
            if n == 0:
                self.header_status.config(text="READY TO GENERATE", bg="#176B4D")
                self.banner.config(text="  STEP 3  •  Corrections saved and validation passed.  Click 3 • Generate Files above to create the JSON/NIC files.",
                                   bg=COLORS["GREEN"], fg="#006100")
                self.status.config(text="Ready. Next step: click 3 • Generate Files above.")
            else:
                self.header_status.config(text="ACTION REQUIRED", bg="#7F1D1D")
                self.banner.config(text=f"  Not generated - {n} item(s) in the invoice must be corrected (shown in red below)",
                                   bg=COLORS["RED"], fg="#9C0006")
                self.status.config(text="Open Review & Correct to resolve the remaining errors.")
        self.tree.delete(*self.tree.get_children())
        order = {"RED": 0, "AMBER": 1, "GREEN": 2}
        for i in sorted(res.issues, key=lambda x: (order[x.level], x.item_no or 0)):
            label = {"RED": "Fix", "AMBER": "Note", "GREEN": "OK"}[i.level]
            self.tree.insert("", "end", tags=(i.level,), values=(label, i.item_no or "", i.message))

    def show_batch(self, results, failures):
        for w in self.summary.winfo_children() + self.files.winfo_children():
            w.destroy()
        total = len(results) + len(failures)
        ok = len(results)
        self.banner.config(text=f"  {ok} of {total} invoices converted  -  files are in the output folder"
                                + ("" if not failures else f";  {len(failures)} need a correction (listed below)"),
                           bg=COLORS["GREEN"] if not failures else COLORS["AMBER"],
                           fg="#006100" if not failures else "#7F6000")
        ttk.Label(self.summary, text=f"{total} invoices found in this file", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w")
        if results:
            tot = sum(float(r.header.get("colTinvoiceval") or 0) for r, _ in results)
            ttk.Label(self.summary, text=f"Converted value (INR): {tot:,.2f}").grid(row=0, column=1, sticky="w", padx=30)
            ttk.Button(self.files, text="Open output folder", command=lambda: open_path(self.out_dir())).pack(side="left")
        self.tree.delete(*self.tree.get_children())
        for res, out in results:
            self.tree.insert("", "end", tags=("GREEN",), values=(
                "Done", res.header.get("colDocno", ""),
                f"{res.header.get('colSupType', '')}  {res.header.get('colBLegalname', '')}  -  "
                f"INR {res.header.get('colTinvoiceval', '')}   ->   {out['json'].name}"))
        for res, inv in failures:
            first = next((i.message for i in res.issues if i.level == "RED"), "")
            self.tree.insert("", "end", tags=("RED",), values=(
                "Fix", res.header.get("colDocno", "") or inv.sheet, first))
            for i in res.issues:
                if i.level == "RED" and i.message != first:
                    self.tree.insert("", "end", tags=("RED",), values=("", "", "    " + i.message))
        self.status.config(text=f"Saved in {self.out_dir()}")

    # ---------------------------------------------------------------- settings
    def open_settings(self):
        SettingsDialog(self)


class PortDialog(tk.Toplevel):
    """Asked once per port name; the choice is remembered for later invoices."""

    def __init__(self, app, masters, port_text):
        super().__init__(app)
        self.title("Port of loading")
        self.transient(app)
        fit_to_screen(self, 640, 480)
        self.result = None
        self.all = [f"{c} - {d.strip()}" for c, d in sorted(masters.ports.items())]
        ttk.Label(self, text=f"The invoice shows port of loading '{port_text or '(not printed)'}', which does not match "
                             "a NIC port name. Pick the correct port code once - it will be remembered.",
                  wraplength=600, padding=10).pack(fill="x")
        self.q = tk.StringVar(value=" ".join(w for w in port_text.upper().split() if w not in ("PORT,", "PORT", "INDIA"))[:20])
        e = ttk.Entry(self, textvariable=self.q); e.pack(fill="x", padx=12)
        e.bind("<KeyRelease>", lambda _e: self.refresh())
        self.lb = tk.Listbox(self); self.lb.pack(fill="both", expand=True, padx=12, pady=8)
        bar = ttk.Frame(self, padding=10); bar.pack(fill="x")
        ttk.Button(bar, text="Skip", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Use this port", command=self.choose).pack(side="right", padx=6)
        self.lb.bind("<Double-1>", lambda _e: self.choose())
        self.refresh()
        self.grab_set()
        app.wait_window(self)

    def refresh(self):
        t = self.q.get().upper().strip()
        self.lb.delete(0, "end")
        for p in (x for x in self.all if all(w in x.upper() for w in t.split())):
            self.lb.insert("end", p)

    def choose(self):
        sel = self.lb.curselection()
        if sel:
            self.result = self.lb.get(sel[0]).split(" - ")[0]
        self.destroy()


class SettingsDialog(tk.Toplevel):
    """Rarely needed. Everything here is remembered."""

    def __init__(self, app: MainWindow):
        super().__init__(app)
        self.app = app
        self.title("Settings")
        self.transient(app)
        fit_to_screen(self, 760, 360)
        s = app.settings
        self.tpl = tk.StringVar(value=find_template(s))
        self.out = tk.StringVar(value=app.out_dir())
        self.uqc = tk.StringVar(value=s.get("default_uqc_box", ""))
        from ..ocr import tesseract_path
        self.tess = tk.StringVar(value=s.get("tesseract_path", "") or tesseract_path())
        foot = ttk.Frame(self, padding=10); foot.pack(side="bottom", fill="x")
        ttk.Button(foot, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(foot, text="Save", command=self.save).pack(side="right", padx=6)
        b = ttk.Frame(self, padding=14); b.pack(fill="both", expand=True)
        b.columnconfigure(1, weight=1)
        for r, (label, var, cmd) in enumerate((("NIC-GePP template", self.tpl, self.pick_tpl),
                                               ("Output folder", self.out, self.pick_out))):
            ttk.Label(b, text=label).grid(row=r, column=0, sticky="w", pady=6)
            ttk.Entry(b, textvariable=var).grid(row=r, column=1, sticky="ew", padx=8)
            ttk.Button(b, text="Browse", command=cmd).grid(row=r, column=2)
        units = [""]
        eng = app._engine
        if eng:
            units += eng.masters.unit_descriptions
        ttk.Label(b, text="Tesseract OCR program (scans)").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(b, textvariable=self.tess).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(b, text="Browse", command=self.pick_tess).grid(row=2, column=2)
        ttk.Label(b, text="UQC for 'No of Box' quantity").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Combobox(b, textvariable=self.uqc, values=units, state="readonly", width=24).grid(row=3, column=1, sticky="w", padx=8)
        ttk.Label(b, text="Blank = decided from the column heading (BOX / CARTONS).", foreground="#555").grid(row=4, column=1, sticky="w", padx=8)
        ttk.Label(b, text="Supplier details are read from the EXPORTER block and GSTIN on your invoice; "
                          "anything missing there is taken from the NIC template's Profile.",
                  foreground="#555", wraplength=680).grid(row=5, column=0, columnspan=3, sticky="w", pady=(16, 0))
        self.grab_set()

    def pick_tpl(self):
        p = filedialog.askopenfilename(parent=self, filetypes=[("NIC-GePP utility", "*.xlsm")])
        if p:
            self.tpl.set(p)

    def pick_tess(self):
        p = filedialog.askopenfilename(parent=self, title="tesseract.exe",
                                       filetypes=[("Tesseract", "tesseract.exe"), ("All files", "*.*")])
        if p:
            self.tess.set(p)

    def pick_out(self):
        p = filedialog.askdirectory(parent=self)
        if p:
            self.out.set(p)

    def save(self):
        s = self.app.settings
        s["template_path"], s["output_dir"], s["default_uqc_box"] = self.tpl.get(), self.out.get(), self.uqc.get()
        s["tesseract_path"] = self.tess.get()
        save_app_settings(s)
        self.destroy()


def run():
    MainWindow().mainloop()
