import tkinter as tk
import database
from services import dashboard_service
from utils.formatting import format_indian_currency


class DashboardFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F3F4F6")
        self.app = app
        self.cards = {}
        self._build()

    def _build(self):
        tk.Label(self, text="Dashboard", font=("Segoe UI", 18, "bold"), bg="#F3F4F6").pack(
            anchor="w", padx=20, pady=(20, 10))

        grid = tk.Frame(self, bg="#F3F4F6")
        grid.pack(fill="x", padx=20)

        labels = [
            "Total Assets", "Total Asset Cost", "Total Accumulated Depreciation",
            "Total Carrying Amount", "Companies Act Depreciation", "Income-tax Depreciation",
            "Deferred Tax Liability", "Deferred Tax Asset", "Assets Disposed",
            "Profit on Sales", "Loss on Sales",
        ]
        for i, label in enumerate(labels):
            card = tk.Frame(grid, bg="white", bd=1, relief="solid", width=220, height=90)
            card.grid(row=i // 4, column=i % 4, padx=10, pady=10, sticky="nsew")
            card.grid_propagate(False)
            tk.Label(card, text=label, bg="white", font=("Segoe UI", 9), fg="#6B7280").pack(
                anchor="w", padx=10, pady=(10, 0))
            value_label = tk.Label(card, text="--", bg="white", font=("Segoe UI", 14, "bold"))
            value_label.pack(anchor="w", padx=10, pady=(5, 10))
            self.cards[label] = value_label

        tk.Button(self, text="Refresh Dashboard", command=self.on_show).pack(anchor="w", padx=20, pady=10)

    def on_show(self):
        conn = database.get_connection()
        try:
            summary = dashboard_service.get_dashboard_summary(conn)
        finally:
            conn.close()
        self.cards["Total Assets"].config(text=str(summary["total_assets"]))
        self.cards["Total Asset Cost"].config(text=format_indian_currency(summary["total_cost"]))
        self.cards["Total Accumulated Depreciation"].config(text=format_indian_currency(summary["total_accum_dep"]))
        self.cards["Total Carrying Amount"].config(text=format_indian_currency(summary["total_carrying_amount"]))
        self.cards["Companies Act Depreciation"].config(text=format_indian_currency(summary["total_ca_dep"]))
        self.cards["Income-tax Depreciation"].config(text=format_indian_currency(summary["total_it_dep"]))
        self.cards["Deferred Tax Liability"].config(text=format_indian_currency(summary["total_dtl"]))
        self.cards["Deferred Tax Asset"].config(text=format_indian_currency(summary["total_dta"]))
        self.cards["Assets Disposed"].config(text=str(summary["assets_disposed"]))
        self.cards["Profit on Sales"].config(text=format_indian_currency(summary["profit_on_sale"]))
        self.cards["Loss on Sales"].config(text=format_indian_currency(summary["loss_on_sale"]))