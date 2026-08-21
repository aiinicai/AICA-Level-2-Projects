import datetime as _dt
import tkinter as tk
from tkinter import ttk, messagebox
import database
from services import depreciation_service
from utils.date_utils import get_financial_year, financial_year_bounds, to_iso
from utils.formatting import format_indian_currency, to_decimal


class DepreciationRunFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F3F4F6")
        self.app = app
        self.eligible_assets = []
        self.calc_output = None
        self.current_run_id = None
        self._build()

    def _build(self):
        tk.Label(self, text="Depreciation Run", font=("Segoe UI", 18, "bold"), bg="#F3F4F6").pack(
            anchor="w", padx=20, pady=(20, 10))

        # --- SELECTION BAR ---
        bar = tk.Frame(self, bg="#F3F4F6")
        bar.pack(fill="x", padx=20)

        tk.Label(bar, text="Financial Year", bg="#F3F4F6").grid(row=0, column=0, sticky="w")
        self.fy_var = tk.StringVar(value=get_financial_year(_dt.date.today()))
        tk.Entry(bar, textvariable=self.fy_var, width=12).grid(row=0, column=1, padx=5)

        tk.Label(bar, text="Period Start", bg="#F3F4F6").grid(row=0, column=2, sticky="w")
        self.start_var = tk.StringVar()
        tk.Entry(bar, textvariable=self.start_var, width=12).grid(row=0, column=3, padx=5)

        tk.Label(bar, text="Period End", bg="#F3F4F6").grid(row=0, column=4, sticky="w")
        self.end_var = tk.StringVar()
        tk.Entry(bar, textvariable=self.end_var, width=12).grid(row=0, column=5, padx=5)

        tk.Label(bar, text="Basis", bg="#F3F4F6").grid(row=0, column=6, sticky="w")
        self.basis_var = tk.StringVar(value="DAYS")
        ttk.Combobox(bar, textvariable=self.basis_var, values=["DAYS", "MONTHS", "EXACT"],
                     width=8, state="readonly").grid(row=0, column=7, padx=5)

        tk.Button(bar, text="Auto-fill FY Dates", command=self.autofill_dates).grid(row=0, column=8, padx=5)

        # --- ACTION TOOLBAR ---
        btn_bar = tk.Frame(self, bg="#F3F4F6")
        btn_bar.pack(fill="x", padx=20, pady=5)
        
        tk.Button(btn_bar, text="1. LOAD ELIGIBLE ASSETS", command=self.load_assets).pack(side="left", padx=5)
        tk.Button(btn_bar, text="2. VALIDATE", command=self.validate_assets).pack(side="left", padx=5)
        tk.Button(btn_bar, text="3. CALCULATE ALL", command=self.calculate_all).pack(side="left", padx=5)
        tk.Button(btn_bar, text="4. POST RUN", command=self.post_run, bg="#2563EB", fg="white").pack(side="left", padx=5)
        
        # NEW: Reversal Button
        tk.Button(btn_bar, text="5. REVERSE LAST RUN", command=self.reverse_last_run, 
                  bg="#991B1B", fg="white").pack(side="left", padx=5)

        # --- ASSET TABLE (COMPANIES ACT) ---
        tk.Label(self, text="Companies Act - Asset Level (Actual Dates Basis)", bg="#F3F4F6",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 0))
        asset_columns = ("asset_id", "asset_name", "opening_ca", "method", "ca_dep", "closing_ca", "status")
        asset_headings = ["Asset ID", "Name", "Opening CA", "Method", "CA Depreciation", "Closing CA",
                           "Status/Exception"]
        self.asset_tree = ttk.Treeview(self, columns=asset_columns, show="headings", height=8)
        for col, head in zip(asset_columns, asset_headings):
            self.asset_tree.heading(col, text=head)
            self.asset_tree.column(col, width=130)
        self.asset_tree.tag_configure("error", background="#FEE2E2")
        self.asset_tree.tag_configure("ok", background="#ECFDF5")
        self.asset_tree.pack(fill="both", expand=True, padx=20, pady=5)

        # --- BLOCK TABLE (INCOME TAX) ---
        tk.Label(self, text="Income-tax - Block of Assets Level", bg="#F3F4F6",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=(10, 0))
        block_columns = ("block_code", "opening_wdv", "additions", "disposals", "wdv_before_dep",
                          "rate", "dep", "closing_wdv", "closing_ca_total", "temp_diff", "dt", "dt_type")
        block_headings = ["Block", "Opening WDV", "Additions", "Disposals", "WDV Before Dep",
                           "Rate %", "Depreciation", "Closing WDV", "Closing CA (Total)",
                           "Temp. Difference", "Deferred Tax", "DTL/DTA"]
        self.block_tree = ttk.Treeview(self, columns=block_columns, show="headings", height=6)
        for col, head in zip(block_columns, block_headings):
            self.block_tree.heading(col, text=head)
            self.block_tree.column(col, width=110)
        self.block_tree.pack(fill="both", expand=True, padx=20, pady=5)

        self.summary_label = tk.Label(self, text="", bg="#F3F4F6", font=("Segoe UI", 10, "bold"),
                                       justify="left")
        self.summary_label.pack(anchor="w", padx=20, pady=5)

    # --- LOGIC METHODS ---

    def autofill_dates(self):
        try:
            start, end = financial_year_bounds(self.fy_var.get())
            self.start_var.set(to_iso(start))
            self.end_var.set(to_iso(end))
        except Exception:
            messagebox.showerror("Error", "Invalid financial year format. Use e.g. FY 2026-27")

    def load_assets(self):
        conn = database.get_connection()
        try:
            self.eligible_assets = depreciation_service.load_eligible_assets(conn, self.fy_var.get())
        finally:
            conn.close()
        for row in self.asset_tree.get_children():
            self.asset_tree.delete(row)
        for a in self.eligible_assets:
            self.asset_tree.insert("", "end", iid=a["asset_id"], values=(
                a["asset_id"], a["asset_name"], "", a["companies_act_method"], "", "", "LOADED"))
        messagebox.showinfo("Assets Loaded", f"{len(self.eligible_assets)} eligible assets loaded.")

    def validate_assets(self):
        if not self.eligible_assets:
            messagebox.showwarning("No Assets", "Please load eligible assets first.")
            return
        conn = database.get_connection()
        try:
            valid, exceptions = depreciation_service.validate_depreciation_run(
                conn, self.eligible_assets, self.fy_var.get())
        finally:
            conn.close()
        self.eligible_assets = valid
        for exc in exceptions:
            if self.asset_tree.exists(exc["asset_id"]):
                self.asset_tree.set(exc["asset_id"], "status", exc["reason"])
                self.asset_tree.item(exc["asset_id"], tags=("error",))
        messagebox.showinfo("Validation Complete",
                             f"{len(valid)} assets valid. {len(exceptions)} assets skipped (already posted).")

    def calculate_all(self):
        if not self.eligible_assets:
            messagebox.showwarning("No Assets", "Please load and validate eligible assets first.")
            return
        conn = database.get_connection()
        try:
            self.calc_output = depreciation_service.calculate_depreciation_run(
                conn, self.eligible_assets, self.start_var.get(), self.end_var.get(),
                self.basis_var.get(), self.fy_var.get())
        finally:
            conn.close()

        asset_results = self.calc_output["asset_results"]
        block_results = self.calc_output["block_results"]

        total_ca = to_decimal(0)
        errors = 0
        for r in asset_results:
            asset_id = r["asset_id"]
            if not self.asset_tree.exists(asset_id):
                continue
            if r["status"] == "OK":
                self.asset_tree.item(asset_id, tags=("ok",))
                self.asset_tree.set(asset_id, "opening_ca", format_indian_currency(r["opening_carrying_amount"]))
                self.asset_tree.set(asset_id, "ca_dep", format_indian_currency(r["companies_act_depreciation"]))
                self.asset_tree.set(asset_id, "closing_ca", format_indian_currency(r["closing_carrying_amount"]))
                self.asset_tree.set(asset_id, "status", r["exception"] if r["exception"] else "CALCULATED")
                total_ca += to_decimal(r["companies_act_depreciation"])
            else:
                self.asset_tree.item(asset_id, tags=("error",))
                self.asset_tree.set(asset_id, "status", r["exception"])
                errors += 1

        for row in self.block_tree.get_children():
            self.block_tree.delete(row)
        total_it = to_decimal(0)
        total_dt = to_decimal(0)
        for br in block_results:
            self.block_tree.insert("", "end", values=(
                br["block_code"], format_indian_currency(br["opening_wdv"]),
                format_indian_currency(br["additions_full_rate"] + br["additions_half_rate"]),
                format_indian_currency(br["disposals"]),
                format_indian_currency(br["wdv_before_depreciation"]), br["tax_rate"],
                format_indian_currency(br["depreciation"]), format_indian_currency(br["closing_wdv"]),
                format_indian_currency(br["closing_carrying_amount_total"]),
                format_indian_currency(br["temporary_difference"]),
                format_indian_currency(br["deferred_tax"]), br["deferred_tax_type"]))
            total_it += to_decimal(br["depreciation"])
            total_dt += to_decimal(br["deferred_tax"])

        self.summary_label.config(text=(
            f"Assets Calculated: {len(asset_results) - errors}   Errors: {errors}   "
            f"Total CA Dep: {format_indian_currency(total_ca)}   "
            f"Total IT Dep (Block Level): {format_indian_currency(total_it)}   "
            f"Total Deferred Tax (Block Level): {format_indian_currency(total_dt)}"))

    def post_run(self):
        if not self.calc_output:
            messagebox.showwarning("Nothing to Post", "Please calculate depreciation before posting.")
            return
        conn = database.get_connection()
        try:
            run_id = depreciation_service.create_depreciation_run(
                conn, self.fy_var.get(), self.start_var.get(), self.end_var.get(), self.basis_var.get())
            totals = depreciation_service.post_depreciation_run(
                conn, run_id, self.calc_output, self.fy_var.get(), self.start_var.get(), self.end_var.get())
            self.current_run_id = run_id
            messagebox.showinfo("Run Posted", f"Depreciation Run {run_id} posted successfully.\n"
                                 f"Assets: {totals['total_assets']}")
        except Exception as e:
            messagebox.showerror("Error", f"Unable to post depreciation run.\n{e}")
        finally:
            conn.close()

    def reverse_last_run(self):
        """Finds the most recent posted run and triggers reversal."""
        if not messagebox.askyesno("Confirm Reversal", 
            "This will reverse the LAST posted depreciation run and revert assets to their previous state. "
            "Are you sure you want to continue?"):
            return

        conn = database.get_connection()
        try:
            # Get the latest posted run
            cursor = conn.execute("SELECT run_id FROM depreciation_runs WHERE status='POSTED' ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            
            if not row:
                messagebox.showwarning("Not Found", "No posted depreciation runs found to reverse.")
                return

            last_run_id = row["run_id"]
            
            # Call the service to reverse
            reversal_id = depreciation_service.reverse_depreciation_run(conn, last_run_id)
            
            messagebox.showinfo("Success", f"Run {last_run_id} has been reversed successfully.\nNew Reversal Run ID: {reversal_id}")
            
            # Clear the UI
            for row in self.asset_tree.get_children(): self.asset_tree.delete(row)
            for row in self.block_tree.get_children(): self.block_tree.delete(row)
            self.summary_label.config(text="")
            
        except Exception as e:
            messagebox.showerror("Error", f"Reversal failed: {str(e)}")
        finally:
            conn.close()

    def on_show(self):
        pass