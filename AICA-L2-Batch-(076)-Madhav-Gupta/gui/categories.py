import tkinter as tk
from tkinter import ttk, messagebox
import database
from repositories import category_repository
from utils.validation import ValidationError, validate_category_code


class CategoriesFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F3F4F6")
        self.app = app
        self._build()

    def _build(self):
        tk.Label(self, text="Asset Categories", font=("Segoe UI", 18, "bold"), bg="#F3F4F6").pack(
            anchor="w", padx=20, pady=(20, 10))

        form = tk.Frame(self, bg="#F3F4F6")
        form.pack(fill="x", padx=20)

        tk.Label(form, text="Category Name", bg="#F3F4F6").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.name_var, width=25).grid(row=0, column=1, padx=5)

        tk.Label(form, text="Category Code", bg="#F3F4F6").grid(row=0, column=2, sticky="w")
        self.code_var = tk.StringVar()
        tk.Entry(form, textvariable=self.code_var, width=10).grid(row=0, column=3, padx=5)

        tk.Label(form, text="Default Method", bg="#F3F4F6").grid(row=0, column=4, sticky="w")
        self.method_var = tk.StringVar(value="SLM")
        ttk.Combobox(form, textvariable=self.method_var, values=["SLM", "WDV"], width=8,
                     state="readonly").grid(row=0, column=5, padx=5)

        tk.Label(form, text="Default Useful Life (yrs)", bg="#F3F4F6").grid(row=1, column=0, sticky="w", pady=5)
        self.life_var = tk.StringVar()
        tk.Entry(form, textvariable=self.life_var, width=10).grid(row=1, column=1, sticky="w")

        tk.Label(form, text="Default Residual %", bg="#F3F4F6").grid(row=1, column=2, sticky="w")
        self.residual_var = tk.StringVar(value="0")
        tk.Entry(form, textvariable=self.residual_var, width=10).grid(row=1, column=3, sticky="w")

        tk.Label(form, text="Default Tax Rate %", bg="#F3F4F6").grid(row=1, column=4, sticky="w")
        self.tax_rate_var = tk.StringVar()
        tk.Entry(form, textvariable=self.tax_rate_var, width=10).grid(row=1, column=5, sticky="w")

        tk.Button(form, text="Add Category", command=self.add_category).grid(row=2, column=0, pady=10)
        tk.Button(form, text="Refresh", command=self.on_show).grid(row=2, column=1, pady=10)

        columns = ("code", "name", "method", "life", "residual", "tax_rate", "active")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col, head in zip(columns, ["Code", "Name", "Method", "Useful Life", "Residual %",
                                        "Tax Rate %", "Active"]):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=120)
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)

    def add_category(self):
        conn = database.get_connection()
        try:
            existing = category_repository.existing_codes(conn)
            code = validate_category_code(self.code_var.get(), existing)
            name = self.name_var.get().strip()
            if not name:
                raise ValidationError("Category name cannot be blank.")
            life = float(self.life_var.get()) if self.life_var.get() else None
            residual = float(self.residual_var.get()) if self.residual_var.get() else 0
            tax_rate = float(self.tax_rate_var.get()) if self.tax_rate_var.get() else None
            category_repository.create_category(conn, name, code, "", self.method_var.get(),
                                                  life, residual, None, tax_rate)
            messagebox.showinfo("Success", f"Category '{name}' ({code}) created.")
            self.name_var.set("")
            self.code_var.set("")
            self.on_show()
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception:
            messagebox.showerror("Error", "Unable to save the category. Please check the entered values.")
        finally:
            conn.close()

    def on_show(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = database.get_connection()
        try:
            categories = category_repository.list_categories(conn)
        finally:
            conn.close()
        for c in categories:
            self.tree.insert("", "end", values=(
                c["category_code"], c["category_name"], c["default_method"],
                c["default_useful_life"], c["default_residual_pct"], c["default_tax_rate"],
                "Yes" if c["active"] else "No"))