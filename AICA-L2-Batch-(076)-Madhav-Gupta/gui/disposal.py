import tkinter as tk
from tkinter import messagebox
import database
from services import disposal_service
from utils.formatting import format_indian_currency
from utils.validation import ValidationError


class DisposalFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F3F4F6")
        self.app = app
        self._build()

    def _build(self):
        tk.Label(self, text="Asset Disposal", font=("Segoe UI", 18, "bold"), bg="#F3F4F6").pack(
            anchor="w", padx=20, pady=(20, 10))

        form = tk.Frame(self, bg="#F3F4F6")
        form.pack(fill="x", padx=20)

        labels = ["Asset ID", "Disposal Date (YYYY-MM-DD)", "Sale Consideration", "Selling Expenses",
                  "Buyer Name", "Invoice Number", "Remarks"]
        keys = ["asset_id", "disposal_date", "sale_consideration", "selling_expenses",
                "buyer_name", "invoice_number", "remarks"]
        self.vars = {}
        for i, (label, key) in enumerate(zip(labels, keys)):
            tk.Label(form, text=label, bg="#F3F4F6").grid(row=i, column=0, sticky="w", pady=3)
            var = tk.StringVar()
            tk.Entry(form, textvariable=var, width=30).grid(row=i, column=1, sticky="w")
            self.vars[key] = var

        btn_container = tk.Frame(form, bg="#F3F4F6")
        btn_container.grid(row=len(labels), column=0, columnspan=2, pady=10, sticky="w")

        tk.Button(btn_container, text="Process Disposal", command=self.process_disposal, 
                  bg="#2563EB", fg="white", width=18).pack(side="left", padx=5)
        
        # NEW: Delete/Revert Button
        tk.Button(btn_container, text="Delete/Revert Disposal", command=self.revert_disposal, 
                  bg="#DC2626", fg="white", width=18).pack(side="left", padx=5)

        self.result_text = tk.Text(self, height=16, width=95, bg="white")
        self.result_text.pack(padx=20, pady=10, fill="both", expand=True)

    def process_disposal(self):
        conn = database.get_connection()
        try:
            data = disposal_service.create_disposal(
                conn,
                asset_id=self.vars["asset_id"].get().strip(),
                disposal_date=self.vars["disposal_date"].get().strip(),
                sale_consideration=self.vars["sale_consideration"].get().strip() or 0,
                selling_expenses=self.vars["selling_expenses"].get().strip() or 0,
                buyer_name=self.vars["buyer_name"].get().strip(),
                invoice_number=self.vars["invoice_number"].get().strip(),
                remarks=self.vars["remarks"].get().strip(),
            )
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, "COMPANIES ACT RESULT (based on actual dates)\n")
            self.result_text.insert(tk.END,
                                     f"Accumulated Depreciation (up to disposal date): "
                                     f"{format_indian_currency(data['accumulated_depreciation'])}\n")
            self.result_text.insert(tk.END, f"Net Book Value: {format_indian_currency(data['net_book_value'])}\n")
            self.result_text.insert(tk.END,
                                     f"Net Sale Proceeds: {format_indian_currency(data['net_sale_proceeds'])}\n")
            self.result_text.insert(tk.END,
                                     f"{data['profit_loss_type']}: {format_indian_currency(data['profit_loss'])}\n\n")
            self.result_text.insert(tk.END, "INCOME-TAX RESULT (Block of Assets concept)\n")
            self.result_text.insert(tk.END,
                                     "No separate depreciation or WDV is computed for this individual "
                                     "asset. The sale consideration reduces the WDV of its Income-tax "
                                     "Block; the tax effect is finalised in the next Depreciation Run.\n")
            self.result_text.insert(tk.END,
                                     f"Sale Consideration Reducing Block WDV: "
                                     f"{format_indian_currency(data['tax_impact'])}\n\n")
            self.result_text.insert(tk.END, "DEFERRED TAX\n")
            self.result_text.insert(tk.END,
                                     "Deferred tax on this asset was already reflected at the block "
                                     "level (based on closing carrying value) in the last posted "
                                     "Depreciation Run and will be revised in the next run.\n")
            messagebox.showinfo("Disposal Processed", "Asset disposal processed successfully.")
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception:
            messagebox.showerror("Error", "Unable to process disposal. Please check the entered values.")
        finally:
            conn.close()

    def revert_disposal(self):
        """Removes disposal record and reverts asset to ACTIVE status."""
        asset_id = self.vars["asset_id"].get().strip()
        if not asset_id:
            messagebox.showwarning("Input Required", "Please enter the Asset ID you wish to revert.")
            return

        if not messagebox.askyesno("Confirm Revert", f"Are you sure you want to delete the disposal record for {asset_id} and mark it as ACTIVE?"):
            return

        conn = database.get_connection()
        try:
            # Note: Ensure disposal_service.delete_disposal is implemented in your services file
            disposal_service.delete_disposal(conn, asset_id)
            messagebox.showinfo("Success", "Disposal record removed and Asset is now ACTIVE again.")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, f"Disposal record for {asset_id} has been deleted successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def on_show(self):
        pass