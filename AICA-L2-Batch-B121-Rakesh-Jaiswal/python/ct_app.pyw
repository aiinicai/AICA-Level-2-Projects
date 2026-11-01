"""UAE Corporate Tax Workpaper Assistant - desktop app.

Double-click this file to open it (needs Python installed).
Uses ct_workpaper.py in the same folder for the calculation.
"""
import csv
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv and sys.argv[0] else __file__))
sys.path.insert(0, HERE)
import ct_workpaper as ct  # noqa: E402

SAMPLE = os.path.join(HERE, "..", "data", "sample_trial_balance.csv")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UAE Corporate Tax Workpaper Assistant")
        self.geometry("820x640")
        self.minsize(700, 520)
        self.path = None
        self.lines = []

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Button(top, text="Open trial balance (CSV)...", command=self.pick).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(top, text="Load sample data", command=self.sample).grid(row=0, column=1, padx=(0, 8))
        self.file_lbl = ttk.Label(top, text="No file loaded", foreground="#555")
        self.file_lbl.grid(row=0, column=2, sticky="w")

        opt = ttk.Frame(self, padding=(10, 0))
        opt.pack(fill="x")
        ttk.Label(opt, text="Tax losses brought forward (AED):").grid(row=0, column=0, sticky="w")
        self.loss = tk.StringVar(value="0")
        ttk.Entry(opt, textvariable=self.loss, width=14).grid(row=0, column=1, padx=8)
        self.sbr = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="Elect Small Business Relief (revenue up to AED 3m)", variable=self.sbr).grid(row=0, column=2, padx=8)
        ttk.Button(opt, text="Calculate", command=self.calc).grid(row=0, column=3, padx=8)

        self.msg = ttk.Label(self, text="", foreground="#a15c00", wraplength=780, justify="left")
        self.msg.pack(fill="x", padx=10, pady=(8, 0))

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=("item", "aed"), show="headings")
        self.tree.heading("item", text="Item")
        self.tree.heading("aed", text="AED")
        self.tree.column("item", width=560)
        self.tree.column("aed", width=180, anchor="e")
        self.tree.tag_configure("bold", font=("Segoe UI", 10, "bold"), background="#eef3fa")
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Export workpaper to CSV...", command=self.export).pack(side="left")
        ttk.Label(bottom, text="Educational tool. Verify against current FTA guidance.", foreground="#777").pack(side="right")

    def pick(self):
        p = filedialog.askopenfilename(title="Select trial balance", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if p:
            self.path = p
            self.calc()

    def sample(self):
        if not os.path.exists(SAMPLE):
            messagebox.showerror("Sample not found", "Keep the 'data' folder next to the 'python' folder, or open a CSV yourself.")
            return
        self.path = SAMPLE
        self.calc()

    def calc(self):
        if not self.path:
            messagebox.showinfo("No file", "Open a trial balance CSV or click 'Load sample data' first.")
            return
        try:
            loss = float(self.loss.get().replace(",", "") or 0)
            rows = ct.load_tb(self.path)
            if not rows:
                raise ValueError("The file has no rows.")
            r = ct.compute(rows, loss, self.sbr.get())
        except Exception as e:
            messagebox.showerror("Could not calculate", f"{e}\n\nCheck the file columns: account_code, account_name, debit, credit.")
            return
        self.file_lbl.config(text=os.path.basename(self.path))
        notes = []
        if abs(r["tb_diff"]) > 1:
            notes.append(f"Trial balance is out of balance by {r['tb_diff']:,.2f}.")
        if r["review"]:
            notes.append(f"{r['review']} account(s) were auto-classified. Add a 'category' column to control this.")
        if self.sbr.get():
            notes.append("Small Business Relief applied (confirm it covers this tax period)." if r["sbr_applied"]
                         else "Small Business Relief NOT applied: revenue is above AED 3m.")
        self.msg.config(text="  ".join(notes))
        self.lines = [("Accounting profit", r["profit"], True), *[(k, v, False) for k, v in r["adj"]],
                      ("Taxable income before losses", r["before"], True), ("Losses utilised (max 75%)", -r["used"], False),
                      ("Taxable income", r["ti"], True), ("Corporate tax payable", r["tax"], True),
                      ("Tax losses carried forward", r["loss_cf"], False)]
        self.tree.delete(*self.tree.get_children())
        for k, v, b in self.lines:
            self.tree.insert("", "end", values=(k, f"{v:,.2f}"), tags=("bold",) if b else ())

    def export(self):
        if not self.lines:
            messagebox.showinfo("Nothing to export", "Calculate first.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="ct_workpaper.csv", filetypes=[("CSV", "*.csv")])
        if p:
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Item", "AED"])
                w.writerows([(k, round(v, 2)) for k, v, _ in self.lines])
            messagebox.showinfo("Saved", f"Saved to {p}")


if __name__ == "__main__":
    App().mainloop()
