import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import database
from repositories import settings_repository
from utils.backup import backup_database, restore_database


class SettingsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F3F4F6")
        self.app = app
        self._build()

    def _build(self):
        tk.Label(self, text="Settings", font=("Segoe UI", 18, "bold"), bg="#F3F4F6").pack(
            anchor="w", padx=20, pady=(20, 10))

        form = tk.Frame(self, bg="#F3F4F6")
        form.pack(fill="x", padx=20)

        tk.Label(form, text="Company / Entity Name", bg="#F3F4F6").grid(row=0, column=0, sticky="w", pady=5)
        self.company_var = tk.StringVar()
        tk.Entry(form, textvariable=self.company_var, width=35).grid(row=0, column=1)

        tk.Label(form, text="Default Deferred Tax Rate %", bg="#F3F4F6").grid(row=1, column=0, sticky="w", pady=5)
        self.tax_rate_var = tk.StringVar()
        tk.Entry(form, textvariable=self.tax_rate_var, width=10).grid(row=1, column=1, sticky="w")

        tk.Label(form, text="Asset ID Generation Mode", bg="#F3F4F6").grid(row=2, column=0, sticky="w", pady=5)
        self.mode_var = tk.StringVar()
        ttk.Combobox(form, textvariable=self.mode_var, values=["CATEGORY", "GLOBAL"], width=15,
                     state="readonly").grid(row=2, column=1, sticky="w")

        tk.Label(form, text="Decimal Places", bg="#F3F4F6").grid(row=3, column=0, sticky="w", pady=5)
        self.decimals_var = tk.StringVar()
        tk.Entry(form, textvariable=self.decimals_var, width=10).grid(row=3, column=1, sticky="w")

        tk.Button(form, text="Save Settings", command=self.save_settings).grid(row=4, column=0, pady=15)
        tk.Button(form, text="Load Sample Data", command=self.load_sample_data).grid(
            row=4, column=1, pady=15, sticky="w")
        tk.Button(form, text="Backup Database", command=self.backup_db).grid(row=5, column=0, pady=5, sticky="w")
        tk.Button(form, text="Restore Database", command=self.restore_db).grid(row=5, column=1, pady=5, sticky="w")

        tk.Label(self, text="Income-tax Block Master (Block of Assets)", font=("Segoe UI", 13, "bold"),
                 bg="#F3F4F6").pack(anchor="w", padx=20, pady=(20, 5))

        block_form = tk.Frame(self, bg="#F3F4F6")
        block_form.pack(fill="x", padx=20)
        tk.Label(block_form, text="Block Name", bg="#F3F4F6").grid(row=0, column=0, sticky="w")
        self.block_name_var = tk.StringVar()
        tk.Entry(block_form, textvariable=self.block_name_var, width=25).grid(row=0, column=1, padx=5)

        tk.Label(block_form, text="Block Code", bg="#F3F4F6").grid(row=0, column=2, sticky="w")
        self.block_code_var = tk.StringVar()
        tk.Entry(block_form, textvariable=self.block_code_var, width=12).grid(row=0, column=3, padx=5)

        tk.Label(block_form, text="Rate %", bg="#F3F4F6").grid(row=0, column=4, sticky="w")
        self.block_rate_var = tk.StringVar()
        tk.Entry(block_form, textvariable=self.block_rate_var, width=8).grid(row=0, column=5, padx=5)

        tk.Button(block_form, text="Add Block", command=self.add_tax_block).grid(row=0, column=6, padx=5)

        block_columns = ("code", "name", "rate", "active")
        self.block_tree = ttk.Treeview(self, columns=block_columns, show="headings", height=8)
        for col, head in zip(block_columns, ["Code", "Name", "Rate %", "Active"]):
            self.block_tree.heading(col, text=head)
            self.block_tree.column(col, width=140)
        self.block_tree.pack(fill="both", expand=True, padx=20, pady=10)

    def on_show(self):
        conn = database.get_connection()
        try:
            settings = settings_repository.all_settings(conn)
            dt_rate = settings_repository.get_current_deferred_tax_rate(conn)
            blocks = settings_repository.list_tax_blocks(conn)
        finally:
            conn.close()
        self.company_var.set(settings.get("company_name", ""))
        self.tax_rate_var.set(str(dt_rate))
        self.mode_var.set(settings.get("asset_id_mode", "CATEGORY"))
        self.decimals_var.set(settings.get("decimal_places", "2"))

        for row in self.block_tree.get_children():
            self.block_tree.delete(row)
        for b in blocks:
            self.block_tree.insert("", "end", values=(
                b["block_code"], b["block_name"], b["default_rate"], "Yes" if b["active"] else "No"))

    def save_settings(self):
        conn = database.get_connection()
        try:
            settings_repository.set_setting(conn, "company_name", self.company_var.get())
            settings_repository.set_setting(conn, "asset_id_mode", self.mode_var.get())
            settings_repository.set_setting(conn, "decimal_places", self.decimals_var.get())
            settings_repository.set_deferred_tax_rate(conn, float(self.tax_rate_var.get()))
            messagebox.showinfo("Settings Saved", "Application settings updated successfully.")
        except Exception:
            messagebox.showerror("Error", "Unable to save settings. Please check the entered values.")
        finally:
            conn.close()

    def add_tax_block(self):
        conn = database.get_connection()
        try:
            name = self.block_name_var.get().strip()
            code = self.block_code_var.get().strip().upper()
            rate = float(self.block_rate_var.get())
            if not name or not code:
                raise ValueError("Block name and code are required.")
            settings_repository.create_tax_block(conn, name, code, "", rate)
            messagebox.showinfo("Block Added", f"Income-tax block '{name}' ({code}) created.")
            self.block_name_var.set("")
            self.block_code_var.set("")
            self.block_rate_var.set("")
            self.on_show()
        except Exception:
            messagebox.showerror("Error", "Unable to save the tax block. Please check the entered "
                                  "values (code must be unique).")
        finally:
            conn.close()

    def load_sample_data(self):
        import sample_data
        conn = database.get_connection()
        try:
            created = sample_data.load_sample_data(conn)
            messagebox.showinfo("Sample Data Loaded", f"{len(created)} sample assets created.")
        except Exception:
            messagebox.showerror("Error", "Unable to load sample data.")
        finally:
            conn.close()

    def backup_db(self):
        path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite DB", "*.db")])
        if path:
            backup_database(path)
            messagebox.showinfo("Backup Complete", f"Database backed up to:\n{path}")

    def restore_db(self):
        if not messagebox.askyesno(
                "Confirm Restore",
                "WARNING: Restoring the database may replace the current application data.\n"
                "Please ensure you have a backup before continuing.\n\nDo you want to continue?"):
            return
        path = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db")])
        if path:
            restore_database(path)
            messagebox.showinfo("Restore Complete", "Database restored successfully. "
                                 "Please restart the application.")