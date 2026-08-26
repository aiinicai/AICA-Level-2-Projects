import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import database
from repositories import category_repository, asset_repository, settings_repository
from services import asset_service, import_service
from utils.validation import ValidationError

class AssetMasterFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F3F4F6")
        self.app = app
        self.category_map = {}
        self.block_map = {}
        self.editing_asset_id = None
        
        # --- SCROLLABLE CONTAINER SETUP ---
        # Create a canvas and a scrollbar
        self.canvas = tk.Canvas(self, bg="#F3F4F6", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # Create the frame that will hold all the content
        self.scrollable_content = tk.Frame(self.canvas, bg="#F3F4F6")

        # Configure canvas
        self.scrollable_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        
        # Ensure the internal frame expands to the canvas width
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack scrollbar and canvas
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bind Mousewheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._build()

    def _on_canvas_configure(self, event):
        # Match the width of the internal frame to the canvas width
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def _on_mousewheel(self, event):
        # Allow scrolling with mouse wheel
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _build(self):
        # Use self.scrollable_content as the parent for all widgets
        container = self.scrollable_content

        # --- HEADER ---
        tk.Label(container, text="Asset Master", font=("Segoe UI", 18, "bold"), bg="#F3F4F6").pack(
            anchor="w", padx=20, pady=(20, 10))

        # --- MAIN FORM SECTION ---
        form = tk.Frame(container, bg="#F3F4F6")
        form.pack(fill="x", padx=20)

        fields = [
            ("Asset Name", "asset_name", "entry"),
            ("Category", "category", "combo"),
            ("Purchase Date (YYYY-MM-DD)", "purchase_date", "entry"),
            ("Date Put to Use (YYYY-MM-DD)", "date_put_to_use", "entry"),
            ("Original Cost", "original_cost", "entry"),
            ("Opening Accum. Dep", "opening_accum_dep", "entry"),
            ("Residual Value", "residual_value", "entry"),
            ("Useful Life (Years)", "useful_life_years", "entry"),
            ("Companies Act Method", "companies_act_method", "combo_method"),
            ("Companies Act Rate % (WDV)", "companies_act_rate", "entry_with_calc"),
            ("Income-tax Block", "income_tax_block", "combo_block"),
            ("Department", "department", "entry"),
            ("Location", "location", "entry"),
        ]
        
        self.vars = {}
        for i, (label, key, kind) in enumerate(fields):
            tk.Label(form, text=label, bg="#F3F4F6").grid(row=i, column=0, sticky="w", pady=2)
            
            if kind == "combo":
                self.category_combo = ttk.Combobox(form, width=35, state="readonly")
                self.category_combo.grid(row=i, column=1, sticky="w", padx=5)
                self.vars[key] = self.category_combo
            elif kind == "combo_method":
                var = tk.StringVar(value="SLM")
                cb = ttk.Combobox(form, textvariable=var, values=["SLM", "WDV"], width=33, state="readonly")
                cb.grid(row=i, column=1, sticky="w", padx=5)
                self.vars[key] = var
            elif kind == "combo_block":
                self.block_combo = ttk.Combobox(form, width=35, state="readonly")
                self.block_combo.grid(row=i, column=1, sticky="w", padx=5)
                self.vars[key] = self.block_combo
            elif kind == "entry_with_calc":
                rate_container = tk.Frame(form, bg="#F3F4F6")
                rate_container.grid(row=i, column=1, sticky="w", padx=5)
                var = tk.StringVar()
                tk.Entry(rate_container, textvariable=var, width=20).pack(side="left")
                tk.Button(rate_container, text="Calc Rate", command=self.auto_calc_wdv_rate, 
                          font=("Segoe UI", 8), bg="#E5E7EB").pack(side="left", padx=5)
                self.vars[key] = var
            else:
                var = tk.StringVar()
                tk.Entry(form, textvariable=var, width=38).grid(row=i, column=1, sticky="w", padx=5)
                self.vars[key] = var

        # --- FORM BUTTONS ---
        btns = tk.Frame(form, bg="#F3F4F6")
        btns.grid(row=len(fields), column=0, columnspan=2, pady=15, sticky="w")
        
        self.btn_save = tk.Button(btns, text="Save New Asset", command=self.save_new_asset, 
                                  bg="#2563EB", fg="white", width=15)
        self.btn_save.pack(side="left", padx=5)
        
        self.btn_update = tk.Button(btns, text="Update Selected", command=self.update_asset, 
                                    state="disabled", width=15)
        self.btn_update.pack(side="left", padx=5)
        
        tk.Button(btns, text="Clear Form", command=self.clear_form, width=15).pack(side="left", padx=5)

        # --- BULK IMPORT SECTION ---
        import_frame = tk.LabelFrame(container, text="Bulk Import Assets", bg="#F3F4F6", font=("Segoe UI", 10, "bold"))
        import_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(import_frame, text="1. Download Excel Template", command=self.download_template, 
                  bg="#4B5563", fg="white").pack(side="left", padx=10, pady=10)

        tk.Button(import_frame, text="2. Upload & Import Excel", command=self.upload_import, 
                  bg="#059669", fg="white").pack(side="left", padx=10, pady=10)

        # --- SEARCH & LIST SECTION ---
        search_bar = tk.Frame(container, bg="#F3F4F6")
        search_bar.pack(fill="x", padx=20, pady=(5, 0))
        
        tk.Label(search_bar, text="Search Name/ID:", bg="#F3F4F6").pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(search_bar, textvariable=self.search_var, width=20).pack(side="left", padx=5)
        tk.Button(search_bar, text="Search", command=self.refresh_asset_list).pack(side="left")
        
        tk.Button(search_bar, text="Load for Edit", command=self.load_selected_for_edit, 
                  bg="#059669", fg="white").pack(side="left", padx=10)
        
        tk.Button(search_bar, text="Delete Asset", command=self.delete_selected_asset, 
                  bg="#DC2626", fg="white").pack(side="left", padx=5)

        # --- TREEVIEW ---
        tree_container = tk.Frame(container)
        tree_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        columns = ("asset_id", "asset_name", "category", "status")
        self.list_tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=8)
        
        for col, head in zip(columns, ["Asset ID", "Name", "Category", "Status"]):
            self.list_tree.heading(col, text=head)
            self.list_tree.column(col, width=150)
            
        scrollbar_tree = ttk.Scrollbar(tree_container, orient="vertical", command=self.list_tree.yview)
        self.list_tree.configure(yscrollcommand=scrollbar_tree.set)
        
        self.list_tree.pack(side="left", fill="both", expand=True)
        scrollbar_tree.pack(side="right", fill="y")

    # --- LOGIC METHODS ---

    def auto_calc_wdv_rate(self):
        try:
            cost = float(self.vars["original_cost"].get())
            residual = float(self.vars["residual_value"].get())
            life = float(self.vars["useful_life_years"].get())
            if cost <= 0 or life <= 0: raise ValueError
            s = residual if residual > 0 else 0.01
            rate = (1 - (s / cost) ** (1 / life)) * 100
            self.vars["companies_act_rate"].set(f"{round(rate, 2)}")
        except Exception:
            messagebox.showwarning("Input Error", "Enter valid Original Cost, Residual Value, and Useful Life.")

    def download_template(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", 
                                             filetypes=[("Excel", "*.xlsx")],
                                             initialfile="Asset_Import_Template.xlsx")
        if path:
            try:
                template_data = import_service.get_import_template()
                with open(path, "wb") as f: f.write(template_data)
                messagebox.showinfo("Success", "Import template saved.")
            except Exception as e: messagebox.showerror("Error", f"Save failed: {e}")

    def upload_import(self):
        path = filedialog.askopenfilename(filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv")])
        if not path: return
        if not messagebox.askyesno("Confirm", "Import assets from this file?"): return
        conn = database.get_connection()
        try:
            count, errors = import_service.bulk_import_assets(conn, path)
            msg = f"Successfully imported {count} assets."
            if errors: msg += f"\n\nNote: {len(errors)} rows failed."
            messagebox.showinfo("Import Complete", msg)
            self.refresh_asset_list()
        except Exception as e: messagebox.showerror("Error", f"Bulk import failed: {e}")
        finally: conn.close()

    def on_show(self):
        conn = database.get_connection()
        try:
            categories = category_repository.list_categories(conn, active_only=True)
            blocks = settings_repository.list_tax_blocks(conn, active_only=True)
            self.category_map = {f"{c['category_name']} ({c['category_code']})": c["category_id"] for c in categories}
            self.vars["category"]["values"] = list(self.category_map.keys())
            self.block_map = {f"{b['block_name']} ({b['block_code']})": b["block_id"] for b in blocks}
            self.vars["income_tax_block"]["values"] = list(self.block_map.keys())
        finally: conn.close()
        self.refresh_asset_list()

    def refresh_asset_list(self):
        for row in self.list_tree.get_children(): self.list_tree.delete(row)
        conn = database.get_connection()
        try:
            search = self.search_var.get().strip() or None
            assets = asset_repository.list_assets(conn, search=search)
            for a in assets:
                self.list_tree.insert("", "end", iid=a["asset_id"], values=(
                    a["asset_id"], a["asset_name"], a["category_code"], a["status"]))
        finally: conn.close()

    def delete_selected_asset(self):
        selection = self.list_tree.selection()
        if not selection: return
        asset_id = selection[0]
        if not messagebox.askyesno("Confirm", f"Permanently delete asset {asset_id}?"): return
        conn = database.get_connection()
        try:
            asset_service.delete_asset(conn, asset_id)
            messagebox.showinfo("Success", "Asset deleted.")
            self.refresh_asset_list()
            self.clear_form()
        except Exception as e: messagebox.showerror("Error", str(e))
        finally: conn.close()

    def load_selected_for_edit(self):
        selection = self.list_tree.selection()
        if not selection: return
        asset_id = selection[0]
        conn = database.get_connection()
        try:
            asset = asset_repository.get_asset(conn, asset_id)
            if not asset: return
            self.editing_asset_id = asset_id
            self.vars["asset_name"].set(asset["asset_name"])
            self.vars["purchase_date"].set(asset["purchase_date"])
            self.vars["date_put_to_use"].set(asset["date_put_to_use"] or "")
            self.vars["original_cost"].set(str(asset["original_cost"]))
            self.vars["opening_accum_dep"].set(str(asset["opening_accum_dep"] or 0))
            self.vars["residual_value"].set(str(asset["residual_value"]))
            self.vars["useful_life_years"].set(str(asset["useful_life_years"] or ""))
            self.vars["companies_act_method"].set(asset["companies_act_method"])
            self.vars["companies_act_rate"].set(str(asset["companies_act_rate"] or ""))
            self.vars["department"].set(asset["department"] or "")
            self.vars["location"].set(asset["location"] or "")
            cat_lbl = next((k for k, v in self.category_map.items() if v == asset["category_id"]), "")
            self.vars["category"].set(cat_lbl)
            self.vars["category"].config(state="disabled")
            block_lbl = next((k for k, v in self.block_map.items() if v == asset["income_tax_block_id"]), "")
            self.vars["income_tax_block"].set(block_lbl)
            self.btn_save.config(state="disabled")
            self.btn_update.config(state="normal")
        finally: conn.close()

    def clear_form(self):
        for k, v in self.vars.items():
            if isinstance(v, tk.StringVar): v.set("SLM" if k == "companies_act_method" else "")
            else: v.set("")
        self.vars["category"].config(state="readonly")
        self.btn_save.config(state="normal")
        self.btn_update.config(state="disabled")
        self.editing_asset_id = None

    def save_new_asset(self):
        conn = database.get_connection()
        try:
            data = self._get_form_data()
            data["category_id"] = self.category_map.get(self.vars["category"].get())
            asset_id = asset_service.create_asset(conn, data)
            messagebox.showinfo("Success", f"Asset created: {asset_id}")
            self.refresh_asset_list()
            self.clear_form()
        except Exception as e: messagebox.showerror("Error", str(e))
        finally: conn.close()

    def update_asset(self):
        conn = database.get_connection()
        try:
            data = self._get_form_data()
            asset_service.update_asset(conn, self.editing_asset_id, data)
            messagebox.showinfo("Success", "Asset updated.")
            self.refresh_asset_list()
            self.clear_form()
        except Exception as e: messagebox.showerror("Error", str(e))
        finally: conn.close()

    def _get_form_data(self):
        return {
            "asset_name": self.vars["asset_name"].get(),
            "purchase_date": self.vars["purchase_date"].get(),
            "date_put_to_use": self.vars["date_put_to_use"].get(),
            "original_cost": self.vars["original_cost"].get(),
            "opening_accum_dep": self.vars["opening_accum_dep"].get(),
            "residual_value": self.vars["residual_value"].get(),
            "useful_life_years": self.vars["useful_life_years"].get(),
            "companies_act_method": self.vars["companies_act_method"].get(),
            "companies_act_rate": self.vars["companies_act_rate"].get(),
            "income_tax_block_id": self.block_map.get(self.vars["income_tax_block"].get()),
            "department": self.vars["department"].get(),
            "location": self.vars["location"].get(),
        }