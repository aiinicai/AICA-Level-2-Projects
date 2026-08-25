# -*- coding: utf-8 -*-
"""
Tally Financial Intelligence - CLIENT EXE V12

Important architecture:
- No Streamlit subprocess.
- No dependency on the client's Python installation.
- Tkinter is used only as the small native extraction control panel.
- The existing Tally extraction engine is imported and run directly.
- The original HTML MIS is served locally after extraction.
"""
from __future__ import annotations

import importlib.util
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))

OUTPUT_DIR = APP_DIR / "Tally_Output"
DASHBOARD_DIR = APP_DIR / "dashboard"
ASSETS_DIR = DASHBOARD_DIR / "assets"
DATA_DIR = DASHBOARD_DIR / "data"
HTML_FILE = DASHBOARD_DIR / "Tally_Financial_Intelligence_Dashboard.html"
EXTRACTOR_FILE = RESOURCE_DIR / "Tally_Accounting_Extractor_Full_Financial_Rev13.py"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def ensure_dashboard_files():
    # In V8 the files are bundled by PyInstaller. Copy them to the writable
    # application folder so the browser can serve them.
    bundled_html = RESOURCE_DIR / "dashboard" / "Tally_Financial_Intelligence_Dashboard.html"
    bundled_plotly = RESOURCE_DIR / "dashboard" / "assets" / "plotly.min.js"
    # Also support PyInstaller placing data under _internal.
    candidates_html = [bundled_html, RESOURCE_DIR / "Tally_Financial_Intelligence_Dashboard.html"]
    candidates_plotly = [bundled_plotly, RESOURCE_DIR / "assets" / "plotly.min.js"]

    html_src = next((p for p in candidates_html if p.exists()), None)
    plotly_src = next((p for p in candidates_plotly if p.exists()), None)

    if html_src is None:
        raise FileNotFoundError("Bundled HTML dashboard was not found.")
    if plotly_src is None:
        raise FileNotFoundError("Bundled Plotly library was not found.")

    import shutil
    shutil.copy2(html_src, HTML_FILE)
    shutil.copy2(plotly_src, ASSETS_DIR / "plotly.min.js")

def load_engine():
    if not EXTRACTOR_FILE.exists():
        # PyInstaller may put data under _internal/dashboard etc.
        candidates = [
            RESOURCE_DIR / "Tally_Accounting_Extractor_Full_Financial_Rev13.py",
            RESOURCE_DIR / "_internal" / "Tally_Accounting_Extractor_Full_Financial_Rev13.py",
        ]
        found = next((p for p in candidates if p.exists()), None)
        if found is None:
            raise FileNotFoundError("Tally extraction engine was not bundled.")
        path = found
    else:
        path = EXTRACTOR_FILE

    engine = load_module(path, "tally_extractor_v12")

    # Force all generated workbooks into the writable application folder.
    engine.OUTPUT_DIR = OUTPUT_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Keep the engine's other path-dependent behaviour aligned to the client
    # folder where possible.
    return engine

def load_dashboard_server():
    # Use a small local HTTP server module shipped with the EXE.
    path = RESOURCE_DIR / "dashboard_server_v8.py"
    if not path.exists():
        path = RESOURCE_DIR / "_internal" / "dashboard_server_v8.py"
    if not path.exists():
        raise FileNotFoundError("Dashboard server was not bundled.")
    mod = load_module(path, "dashboard_server_v8")
    mod.BASE = APP_DIR
    mod.DASHBOARD = DASHBOARD_DIR
    mod.DATA = DATA_DIR
    mod.OUTPUT = OUTPUT_DIR
    mod.ASSETS = ASSETS_DIR
    mod.HTML = HTML_FILE
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return mod

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tally Financial Intelligence")
        self.root.geometry("900x650")
        self.root.minsize(800, 560)

        style = ttk.Style()
        try: style.theme_use("vista")
        except Exception: pass

        self.from_var = tk.StringVar(value=f"01-04-{datetime.now().year-1}")
        self.to_var = tk.StringVar(value=datetime.now().strftime("%d-%m-%Y"))
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="9000")
        self.dsn_var = tk.StringVar(value="TallyODBC64_9000")
        self.company_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)

        self.build_ui()

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=22)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Tally Financial Intelligence",
                  font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(outer, text="TallyPrime extraction + HTML Management MIS",
                  font=("Segoe UI", 11)).pack(anchor="w", pady=(3,18))

        card = ttk.LabelFrame(outer, text="Extraction Settings", padding=16)
        card.pack(fill="x")

        fields = [
            ("From Date (DD-MM-YYYY)", self.from_var),
            ("To Date (DD-MM-YYYY)", self.to_var),
            ("Tally Host", self.host_var),
            ("Tally Port", self.port_var),
            ("ODBC DSN", self.dsn_var),
            ("Company (optional)", self.company_var),
        ]
        for i, (label, var) in enumerate(fields):
            r = i // 2; c = (i % 2) * 2
            ttk.Label(card, text=label).grid(row=r, column=c, sticky="w", padx=8, pady=7)
            ttk.Entry(card, textvariable=var, width=32).grid(row=r, column=c+1, sticky="ew", padx=8, pady=7)
        card.columnconfigure(1, weight=1); card.columnconfigure(3, weight=1)

        ttk.Label(outer, text=f"Output: {OUTPUT_DIR}", foreground="#555").pack(anchor="w", pady=(16,4))
        ttk.Label(outer, text="The dashboard is fully local and does not require internet.",
                  foreground="#555").pack(anchor="w")

        self.progress = ttk.Progressbar(outer, variable=self.progress_var, maximum=100)
        self.progress.pack(fill="x", pady=(18,6))

        ttk.Label(outer, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.log = tk.Text(outer, height=17, wrap="word")
        self.log.pack(fill="both", expand=True, pady=12)

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(4,0))

        # Four primary client controls requested for the final application.
        self.extract_btn = ttk.Button(buttons, text="1. Extract Data", command=self.start)
        self.extract_btn.pack(side="left", padx=(0,8))

        ttk.Button(buttons, text="2. Open Output Folder", command=self.open_output_folder).pack(side="left", padx=8)
        ttk.Button(buttons, text="3. Open MIS", command=self.open_mis).pack(side="left", padx=8)
        ttk.Button(buttons, text="4. MIS from Selected File", command=self.open_selected_file_mis).pack(side="left", padx=8)

    def write_log(self, text):
        self.root.after(0, lambda: (self.log.insert("end", text + "\n"), self.log.see("end")))

    def set_status(self, value, msg):
        def f():
            self.progress_var.set(max(0, min(100, float(value)*100)))
            self.status_var.set(msg)
        self.root.after(0, f)

    def start(self):
        if not self.extract_btn.instate(["!disabled"]): return
        self.extract_btn.state(["disabled"])
        threading.Thread(target=self.extract, daemon=True).start()

    def extract(self):
        try:
            f = datetime.strptime(self.from_var.get().strip(), "%d-%m-%Y").date()
            t = datetime.strptime(self.to_var.get().strip(), "%d-%m-%Y").date()
            host = self.host_var.get().strip()
            port = int(self.port_var.get().strip())
            dsn = self.dsn_var.get().strip()
            company = self.company_var.get().strip() or None

            self.write_log("="*70)
            self.write_log("Starting Tally extraction...")
            self.write_log(f"Period: {f:%d-%m-%Y} to {t:%d-%m-%Y}")
            self.write_log(f"Tally: {host}:{port}")
            self.write_log(f"Output: {OUTPUT_DIR}")

            ensure_dashboard_files()
            engine = load_engine()

            result = engine.run_extraction(
                from_date=f,
                to_date=t,
                host=host,
                port=port,
                dsn=dsn,
                company=company,
                progress=lambda v,m: self.set_status(v,m),
                log_callback=self.write_log,
            )

            files = list(OUTPUT_DIR.glob("*.xlsx"))
            if not files:
                raise RuntimeError(
                    "Tally extraction returned, but no Excel workbook was created in:\n"
                    + str(OUTPUT_DIR)
                )

            self.write_log("")
            self.write_log(f"Extraction completed. Excel files created: {len(files)}")
            for p in files:
                self.write_log("  " + p.name)

            # IMPORTANT: Extract Data is extraction-only.
            # It must NOT build, start, or open the MIS dashboard.
            self.set_status(1, "Extraction completed. Output files are ready. Click '3. Open MIS' to view MIS.")
            self.write_log("MIS was not opened automatically.")
            self.write_log("Use '3. Open MIS' to build the dashboard data and open the HTML MIS.")

        except Exception as exc:
            self.write_log("\nERROR:\n" + str(exc))
            self.write_log(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("Extraction failed", str(exc)))
            self.set_status(0, "Extraction failed")
        finally:
            self.root.after(0, lambda: self.extract_btn.state(["!disabled"]))

    def open_output_folder(self):
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(str(OUTPUT_DIR))
        except Exception as exc:
            messagebox.showerror("Output Folder", str(exc))

    def open_selected_file_mis(self):
        """Select any Excel workbook from Tally_Output and build MIS from it.

        Voucher-wise/Day Book workbooks provide the full transaction MIS.
        Trial Balance / ledger-style workbooks are normalized into the common
        ledger/debit/credit structure so the applicable MIS sections can still
        be used. The selected source is never modified.
        """
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            selected = filedialog.askopenfilename(
                parent=self.root,
                title="Select Tally Excel file for MIS",
                initialdir=str(OUTPUT_DIR),
                filetypes=[("Excel files", "*.xlsx;*.xlsm;*.xltx;*.xltm"), ("All files", "*.*")],
            )
            if not selected:
                return

            selected_path = Path(selected).resolve()
            try:
                selected_path.relative_to(OUTPUT_DIR.resolve())
            except ValueError:
                messagebox.showwarning(
                    "Select from Tally Output",
                    "Please select an Excel file from the Tally_Output folder."
                )
                return

            ensure_dashboard_files()
            mod = load_dashboard_server()
            diagnostics = mod.ensure_data_from_selected_file(selected_path)
            self.write_log("\nSelected-file MIS mode")
            self.write_log(f"Source: {selected_path.name}")
            self.write_log(f"Detected type: {diagnostics.get('source_type','Unknown')}")
            self.write_log(f"Rows loaded: {diagnostics.get('daybook_rows', 0)}")
            self.set_status(1, f"MIS ready from selected file: {selected_path.name}")
            threading.Thread(target=self.serve_dashboard, args=(mod,), daemon=True).start()
        except Exception as exc:
            self.write_log("Selected-file MIS error: " + str(exc))
            self.write_log(traceback.format_exc())
            messagebox.showerror("MIS from Selected File", str(exc))

    def serve_dashboard(self, mod):
        try:
            port = mod.free_port(8765)
            (DATA_DIR / "dashboard_port.txt").write_text(str(port), encoding="utf-8")
            server = mod.ThreadingHTTPServer(("127.0.0.1", port), mod.Handler)
            self.write_log(f"HTML MIS server started: http://127.0.0.1:{port}/")
            self.set_status(1, "MIS dashboard ready.")
            webbrowser.open(f"http://127.0.0.1:{port}/")
            server.serve_forever()
        except Exception as exc:
            self.write_log("Dashboard server error: " + repr(exc))
            self.root.after(0, lambda: messagebox.showerror("Dashboard error", str(exc)))

    def open_mis(self):
        try:
            ensure_dashboard_files()
            mod = load_dashboard_server()
            # Create bridge if Excel output already exists.
            mod.ensure_data_from_excel()
            threading.Thread(target=self.serve_dashboard, args=(mod,), daemon=True).start()
        except Exception as exc:
            messagebox.showerror("MIS", str(exc))

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    App().run()
