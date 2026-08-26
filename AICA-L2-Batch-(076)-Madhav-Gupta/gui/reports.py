import tkinter as tk
from tkinter import filedialog, messagebox
import os
import database
from services import report_service
from reports.csv_report import export_dataframe_to_csv
from reports.excel_report import export_workbook
from reports.pdf_report import export_dataframe_to_pdf
from utils.paths import get_report_directory

class ReportsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F3F4F6")
        self.app = app
        self._build()

    def _build(self):
        tk.Label(self, text="Reports", font=("Segoe UI", 18, "bold"), bg="#F3F4F6").pack(
            anchor="w", padx=20, pady=(20, 10))

        frame = tk.Frame(self, bg="#F3F4F6")
        frame.pack(anchor="w", padx=20, pady=10)
        
        buttons = [
            ("Asset Register - Excel", self.export_asset_register_excel),
            ("Asset Register - CSV", self.export_asset_register_csv),
            ("Asset Register - PDF", self.export_asset_register_pdf),
            ("Deferred Tax Report - Excel", self.export_deferred_tax_excel),
            ("Disposal Report - Excel", self.export_disposal_excel),
        ]
        
        for text, cmd in buttons:
            tk.Button(frame, text=text, command=cmd, width=35, height=2, bg="white", relief="flat").pack(pady=5, anchor="w")

        tk.Label(self, text="Quick Access:", font=("Segoe UI", 10, "bold"), bg="#F3F4F6").pack(anchor="w", padx=20, pady=(20,5))
        
        tk.Button(self, text="📁 Open Reports Folder", command=self.open_reports_folder, 
                  bg="#1F2937", fg="white", width=25, height=2).pack(anchor="w", padx=20, pady=5)

        self.status_label = tk.Label(self, text="", bg="#F3F4F6", fg="#059669", font=("Segoe UI", 9, "italic"))
        self.status_label.pack(anchor="w", padx=20, pady=10)

    def open_reports_folder(self):
        path = get_report_directory()
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showerror("Error", f"Folder does not exist yet:\n{path}")

    def _verify_and_notify(self, path):
        """Checks if the file actually exists on disk after the export function runs."""
        if path and os.path.exists(path):
            self.status_label.config(text=f"Last Saved: {os.path.basename(path)}")
            messagebox.showinfo("Report Saved", f"Successfully saved to:\n{path}")
        elif path:
            messagebox.showerror("Save Failed", f"The app tried to save the file, but it was not found on disk at:\n{path}\n\nPlease check if you have write permissions to this folder.")

    def export_asset_register_excel(self):
        conn = database.get_connection()
        try:
            df = report_service.asset_register_dataframe(conn)
            path = filedialog.asksaveasfilename(initialdir=get_report_directory(), initialfile="AssetRegister.xlsx",
                                               defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if path:
                export_workbook({"Asset Register": df}, path)
                self._verify_and_notify(path)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate Excel: {str(e)}")
        finally:
            conn.close()

    def export_asset_register_csv(self):
        conn = database.get_connection()
        try:
            df = report_service.asset_register_dataframe(conn)
            path = filedialog.asksaveasfilename(initialdir=get_report_directory(), initialfile="AssetRegister.csv",
                                               defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if path:
                export_dataframe_to_csv(df, path)
                self._verify_and_notify(path)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate CSV: {str(e)}")
        finally:
            conn.close()

    def export_asset_register_pdf(self):
        conn = database.get_connection()
        try:
            df = report_service.asset_register_dataframe(conn)
            path = filedialog.asksaveasfilename(initialdir=get_report_directory(), initialfile="AssetRegister.pdf",
                                               defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
            if path:
                export_dataframe_to_pdf(df, path, "Asset Register Report")
                self._verify_and_notify(path)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate PDF: {str(e)}")
        finally:
            conn.close()

    def export_deferred_tax_excel(self):
        conn = database.get_connection()
        try:
            df = report_service.deferred_tax_dataframe(conn)
            path = filedialog.asksaveasfilename(initialdir=get_report_directory(), initialfile="DeferredTax.xlsx",
                                               defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if path:
                export_workbook({"Deferred Tax": df}, path)
                self._verify_and_notify(path)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate Excel: {str(e)}")
        finally:
            conn.close()

    def export_disposal_excel(self):
        conn = database.get_connection()
        try:
            df = report_service.disposal_dataframe(conn)
            path = filedialog.asksaveasfilename(initialdir=get_report_directory(), initialfile="DisposalReport.xlsx",
                                               defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if path:
                export_workbook({"Disposals": df}, path)
                self._verify_and_notify(path)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate Excel: {str(e)}")
        finally:
            conn.close()

    def on_show(self):
        pass