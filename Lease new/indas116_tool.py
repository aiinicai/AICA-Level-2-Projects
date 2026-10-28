import csv
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

# Configure theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class IndAS116CalculatorApp(ctk.CTk):

  def __init__(self):
    super().__init__()

    self.title(
        "Ind AS 116 Lease Accounting & Amortization Tool (with Escalations)"
    )
    self.geometry("1200x780")
    self.minsize(1050, 700)

    # Grid configuration
    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(0, weight=1)

    # --- Sidebar Input Panel ---
    self.sidebar_frame = ctk.CTkFrame(self, width=350, corner_radius=0)
    self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
    self.sidebar_frame.grid_rowconfigure(16, weight=1)

    self.logo_label = ctk.CTkLabel(
        self.sidebar_frame,
        text="Ind AS 116 Lease Tool",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    self.logo_label.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="w")

    row_idx = 1
    # Location / Asset Name
    self.create_label(self.sidebar_frame, "Location / Asset Name:", row_idx, 0)
    self.loc_entry = ctk.CTkEntry(self.sidebar_frame)
    self.loc_entry.grid(
        row=row_idx + 1, column=0, padx=20, pady=(0, 8), sticky="ew"
    )
    self.loc_entry.insert(0, "Branch Office - Chennai")
    row_idx += 2

    # Lease Term (Months)
    self.create_label(self.sidebar_frame, "Lease Term (Months):", row_idx, 0)
    self.term_entry = ctk.CTkEntry(self.sidebar_frame)
    self.term_entry.grid(
        row=row_idx + 1, column=0, padx=20, pady=(0, 8), sticky="ew"
    )
    self.term_entry.insert(0, "36")
    row_idx += 2

    # Initial Monthly Lease Payment
    self.create_label(
        self.sidebar_frame, "Initial Monthly Rent (₹):", row_idx, 0
    )
    self.payment_entry = ctk.CTkEntry(self.sidebar_frame)
    self.payment_entry.grid(
        row=row_idx + 1, column=0, padx=20, pady=(0, 8), sticky="ew"
    )
    self.payment_entry.insert(0, "50000")
    row_idx += 2

    # Escalation Type
    self.create_label(self.sidebar_frame, "Rent Escalation Type:", row_idx, 0)
    self.esc_type_var = ctk.StringVar(value="None (Flat Rent)")
    self.esc_type_menu = ctk.CTkOptionMenu(
        self.sidebar_frame,
        values=[
            "None (Flat Rent)",
            "Annual (% Increase)",
            "Biennial (2-Year % Increase)",
        ],
        variable=self.esc_type_var,
    )
    self.esc_type_menu.grid(
        row=row_idx + 1, column=0, padx=20, pady=(0, 8), sticky="ew"
    )
    row_idx += 2

    # Escalation Rate (%)
    self.create_label(self.sidebar_frame, "Escalation Rate (%):", row_idx, 0)
    self.esc_rate_entry = ctk.CTkEntry(self.sidebar_frame)
    self.esc_rate_entry.grid(
        row=row_idx + 1, column=0, padx=20, pady=(0, 8), sticky="ew"
    )
    self.esc_rate_entry.insert(0, "5.0")
    row_idx += 2

    # Annual Discount Rate (%)
    self.create_label(
        self.sidebar_frame, "Annual Discount Rate / IBR (%):", row_idx, 0
    )
    self.rate_entry = ctk.CTkEntry(self.sidebar_frame)
    self.rate_entry.grid(
        row=row_idx + 1, column=0, padx=20, pady=(0, 8), sticky="ew"
    )
    self.rate_entry.insert(0, "10.0")
    row_idx += 2

    # Initial Direct Costs
    self.create_label(
        self.sidebar_frame, "Initial Direct Costs (₹):", row_idx, 0
    )
    self.idc_entry = ctk.CTkEntry(self.sidebar_frame)
    self.idc_entry.grid(
        row=row_idx + 1, column=0, padx=20, pady=(0, 8), sticky="ew"
    )
    self.idc_entry.insert(0, "0")
    row_idx += 2

    # Payment Timing
    self.create_label(self.sidebar_frame, "Payment Timing:", row_idx, 0)
    self.timing_var = ctk.StringVar(value="Arrears (End of Month)")
    self.timing_menu = ctk.CTkOptionMenu(
        self.sidebar_frame,
        values=["Arrears (End of Month)", "Advance (Start of Month)"],
        variable=self.timing_var,
    )
    self.timing_menu.grid(
        row=row_idx + 1, column=0, padx=20, pady=(0, 15), sticky="ew"
    )
    row_idx += 2

    # Buttons
    self.calc_button = ctk.CTkButton(
        self.sidebar_frame,
        text="Generate Schedule",
        command=self.calculate_schedule,
        fg_color="#1f538d",
        hover_color="#14375e",
    )
    self.calc_button.grid(
        row=row_idx, column=0, padx=20, pady=(2, 8), sticky="ew"
    )
    row_idx += 1

    self.export_button = ctk.CTkButton(
        self.sidebar_frame,
        text="Export to CSV",
        command=self.export_csv,
        fg_color="green",
        hover_color="darkgreen",
    )
    self.export_button.grid(
        row=row_idx, column=0, padx=20, pady=(0, 15), sticky="ew"
    )

    # --- Main Display Panel ---
    self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
    self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
    self.main_frame.grid_columnconfigure(0, weight=1)
    self.main_frame.grid_rowconfigure(1, weight=1)

    # Summary Cards
    self.summary_frame = ctk.CTkFrame(self.main_frame, fg_color=("gray90", "gray16"))
    self.summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
    self.summary_frame.grid_columnconfigure((0, 1, 2), weight=1)

    self.sum_pv_label = ctk.CTkLabel(
        self.summary_frame,
        text="Initial Lease Liability:\n₹ 0.00",
        font=ctk.CTkFont(size=13, weight="bold"),
    )
    self.sum_pv_label.grid(row=0, column=0, padx=10, pady=15)

    self.sum_rou_label = ctk.CTkLabel(
        self.summary_frame,
        text="Initial ROU Asset:\n₹ 0.00",
        font=ctk.CTkFont(size=13, weight="bold"),
    )
    self.sum_rou_label.grid(row=0, column=1, padx=10, pady=15)

    self.sum_interest_label = ctk.CTkLabel(
        self.summary_frame,
        text="Total Interest Expense:\n₹ 0.00",
        font=ctk.CTkFont(size=13, weight="bold"),
    )
    self.sum_interest_label.grid(row=0, column=2, padx=10, pady=15)

    # Table View
    self.table_frame = ctk.CTkFrame(self.main_frame)
    self.table_frame.grid(row=0, column=0, sticky="nsew") # Adjusted grid layout for expansion
    # Wait, let's fix the grid layout inside main_frame
    self.main_frame.grid_rowconfigure(1, weight=1)
    self.summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
    self.table_frame.grid(row=1, column=0, sticky="nsew")

    self.table_frame.grid_columnconfigure(0, weight=1)
    self.table_frame.grid_rowconfigure(0, weight=1)

    self.columns = (
        "Month",
        "Opening Liability",
        "Interest",
        "Payment",
        "Closing Liability",
        "Opening ROU",
        "Depreciation",
        "Closing ROU",
    )
    self.tree = ttk.Treeview(
        self.table_frame, columns=self.columns, show="headings"
    )

    for col in self.columns:
      self.tree.heading(col, text=col)
      self.tree.column(col, width=110, anchor="center")

    self.tree_scroll_y = ttk.Scrollbar(
        self.table_frame, orient="vertical", command=self.tree.yview
    )
    self.tree_scroll_x = ttk.Scrollbar(
        self.table_frame, orient="horizontal", command=self.tree.xview
    )
    self.tree.configure(
        yscrollcommand=self.tree_scroll_y.set,
        xscrollcommand=self.tree_scroll_x.set,
    )

    self.tree.grid(row=0, column=0, sticky="nsew")
    self.tree_scroll_y.grid(row=0, column=1, sticky="ns")
    self.tree_scroll_x.grid(row=1, column=0, sticky="ew")

    self.schedule_data = []

  def create_label(self, parent, text, row, col):
    lbl = ctk.CTkLabel(
        parent, text=text, font=ctk.CTkFont(size=11, weight="bold")
    )
    lbl.grid(row=row, column=col, padx=20, pady=(4, 0), sticky="w")

  def calculate_schedule(self):
    try:
      term = int(self.term_entry.get())
      base_payment = float(self.payment_entry.get())
      esc_type = self.esc_type_var.get()
      esc_rate = float(self.esc_rate_entry.get()) / 100.0
      annual_rate = float(self.rate_entry.get()) / 100.0
      idc = float(self.idc_entry.get())
      timing = self.timing_var.get()
    except ValueError:
      messagebox.showerror(
          "Invalid Input",
          "Please verify that all inputs contain valid numbers.",
      )
      return

    if term <= 0 or base_payment <= 0:
      messagebox.showerror(
          "Invalid Input", "Lease term and base payment must be greater than zero."
      )
      return

    monthly_rate = annual_rate / 12.0

    # Step 1: Generate monthly payment stream based on escalation rules
    payments = []
    for m in range(1, term + 1):
      year_idx = (m - 1) // 12
      if "Annual" in esc_type:
        payment = base_payment * ((1 + esc_rate) ** year_idx)
      elif "Biennial" in esc_type:
        biennial_idx = year_idx // 2
        payment = base_payment * ((1 + esc_rate) ** biennial_idx)
      else:
        payment = base_payment
      payments.append(payment)

    # Step 2: Calculate Present Value (Lease Liability) for uneven cash flows
    pv = 0.0
    for i, pmt in enumerate(payments):
      month_num = i + 1
      if "Advance" in timing:
        # For advance payments, payment happens at start of month (month_num - 1 discounting period)
        discount_period = month_num - 1
      else:
        discount_period = month_num

      if monthly_rate == 0:
        pv += pmt
      else:
        pv += pmt / ((1 + monthly_rate) ** discount_period)

    initial_liability = pv
    initial_rou = initial_liability + idc
    monthly_depr = initial_rou / term

    self.schedule_data = []
    curr_liability = initial_liability
    curr_rou = initial_rou
    total_interest = 0.0

    for m in range(1, term + 1):
      open_liab = curr_liability
      pay_amt = payments[m - 1]

      if "Advance" in timing:
        liab_after_pmt = open_liab - pay_amt
        interest = liab_after_pmt * monthly_rate if monthly_rate > 0 else 0
        close_liab = liab_after_pmt + interest
      else:
        interest = open_liab * monthly_rate if monthly_rate > 0 else 0
        close_liab = open_liab + interest - pay_amt

      total_interest += interest
      open_rou = curr_rou
      close_rou = open_rou - monthly_depr

      self.schedule_data.append({
          "Month": m,
          "Opening Liability": round(open_liab, 2),
          "Interest": round(interest, 2),
          "Payment": round(pay_amt, 2),
          "Closing Liability": round(max(0.0, close_liab), 2),
          "Opening ROU": round(open_rou, 2),
          "Depreciation": round(monthly_depr, 2),
          "Closing ROU": round(max(0.0, close_rou), 2),
      })

      curr_liability = close_liab
      curr_rou = close_rou

    # Update summary cards
    self.sum_pv_label.configure(
        text=f"Initial Lease Liability:\n₹ {initial_liability:,.2f}"
    )
    self.sum_rou_label.configure(
        text=f"Initial ROU Asset:\n₹ {initial_rou:,.2f}"
    )
    self.sum_interest_label.configure(
        text=f"Total Interest Expense:\n₹ {total_interest:,.2f}"
    )

    # Populate table
    for row in self.tree.get_children():
      self.tree.delete(row)

    for item in self.schedule_data:
      self.tree.insert(
          "",
          "end",
          values=(
              item["Month"],
              f"₹ {item['Opening Liability']:,.2f}",
              f"₹ {item['Interest']:,.2f}",
              f"₹ {item['Payment']:,.2f}",
              f"₹ {item['Closing Liability']:,.2f}",
              f"₹ {item['Opening ROU']:,.2f}",
              f"₹ {item['Depreciation']:,.2f}",
              f"₹ {item['Closing ROU']:,.2f}",
          ),
      )

    messagebox.showinfo(
        "Success", "Schedule generated with rent escalation factored in!"
    )

  def export_csv(self):
    if not self.schedule_data:
      messagebox.showerror(
          "Error", "Please generate the schedule first before exporting."
      )
      return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        title="Save Schedule as CSV",
    )
    if not file_path:
      return

    try:
      with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Month",
            "Opening Liability",
            "Interest Expense",
            "Payment",
            "Closing Liability",
            "Opening ROU Asset",
            "Depreciation",
            "Closing ROU Asset",
        ])
        for row in self.schedule_data:
          writer.writerow([
              row["Month"],
              row["Opening Liability"],
              row["Interest"],
              row["Payment"],
              row["Closing Liability"],
              row["Opening ROU"],
              row["Depreciation"],
              row["Closing ROU"],
          ])
      messagebox.showinfo("Export Successful", f"Saved to:\n{file_path}")
    except Exception as e:
      messagebox.showerror("Export Failed", f"Error: {str(e)}")


if __name__ == "__main__":
  app = IndAS116CalculatorApp()
  app.mainloop()