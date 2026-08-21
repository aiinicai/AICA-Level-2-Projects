import tkinter as tk
from tkinter import ttk, messagebox
import database
from repositories import asset_repository
from services import asset_service
from utils.formatting import format_indian_currency

class AssetRegisterFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F3F4F6")
        self.app = app
        self._build()

    def _build(self):
        header = tk.Frame(self, bg="#F3F4F6")
        header.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(header, text="Asset Register", font=("Segoe UI", 18, "bold"), bg="#F3F4F6").pack(side="left")
        
        toolbar = tk.Frame(self, bg="#F3F4F6")
        toolbar.pack(fill="x", padx=20, pady=5)
        
        tk.Label(toolbar, text="Search Name/ID:", bg="#F3F4F6").pack(side="left")
        self.search_var = tk.StringVar()
        tk.Entry(toolbar, textvariable=self.search_var, width=30).pack(side="left", padx=5)
        
        # Fixed: Manual search to prevent UI lag
        tk.Button(toolbar, text="Search", command=self.on_show, bg="#2563EB", fg="white").pack(side="left")
        tk.Button(toolbar, text="Clear", command=self.clear_search).pack(side="left", padx=5)

        columns = ("asset_id", "asset_name", "category", "purchase_date", "cost", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=20)
        for col, head in zip(columns, ["Asset ID", "Name", "Category", "Purchase", "Cost", "Status"]):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=120)
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

    def clear_search(self):
        self.search_var.set("")
        self.on_show()

    def on_show(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        conn = database.get_connection()
        try:
            assets = asset_repository.list_assets(conn, search=self.search_var.get().strip() or None)
            for a in assets:
                self.tree.insert("", "end", values=(
                    a["asset_id"], a["asset_name"], a["category_code"], a["purchase_date"],
                    format_indian_currency(a["original_cost"]), a["status"]))
        finally: conn.close()