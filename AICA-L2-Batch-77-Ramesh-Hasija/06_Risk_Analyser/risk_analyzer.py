import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

APP_TITLE = "CA Statutory Compliance Risk Analyzer"


def analyze_risk():
    compliance_type = compliance_type_var.get().strip()
    particulars = particulars_entry.get().strip()
    due_date_text = due_date_entry.get().strip()
    status = status_var.get().strip()
    risk = risk_var.get().strip()
    responsible = responsible_entry.get().strip()
    remarks = remarks_entry.get().strip()

    if not compliance_type or not particulars or not due_date_text or not status or not risk:
        messagebox.showwarning(
            "Missing Information",
            "Please complete Compliance Type, Particulars, Due Date, Status and Risk Level."
        )
        return

    try:
        due_date = datetime.strptime(due_date_text, "%d-%m-%Y").date()
    except ValueError:
        messagebox.showerror(
            "Invalid Date",
            "Please enter Due Date in DD-MM-YYYY format."
        )
        return

    today = datetime.today().date()
    difference = (due_date - today).days

    if status == "Completed":
        deadline_text = "Compliance already completed"
        priority = "COMPLETED / NO IMMEDIATE ACTION"
        action = "Maintain supporting records and evidence of completion."

    else:
        if difference < 0:
            deadline_text = f"Overdue by {abs(difference)} day(s)"
        elif difference == 0:
            deadline_text = "Due today"
        else:
            deadline_text = f"{difference} day(s) remaining"

        if status == "Overdue" and risk == "High":
            priority = "CRITICAL"
            action = "Immediate attention required. Escalate to the responsible team and complete the compliance without delay."
        elif risk == "High":
            priority = "HIGH PRIORITY"
            action = "Review immediately, collect supporting documents and assign responsibility for timely completion."
        elif risk == "Medium":
            priority = "MEDIUM PRIORITY"
            action = "Monitor closely and complete the required work before the due date."
        else:
            priority = "NORMAL MONITORING"
            action = "Track the compliance through the normal compliance calendar."

    result_text.config(state="normal")
    result_text.delete("1.0", tk.END)

    result_text.insert(tk.END, f"{APP_TITLE}\n")
    result_text.insert(tk.END, "-" * 62 + "\n\n")
    result_text.insert(tk.END, f"Compliance Type     : {compliance_type}\n")
    result_text.insert(tk.END, f"Particulars         : {particulars}\n")
    result_text.insert(tk.END, f"Due Date            : {due_date.strftime('%d-%m-%Y')}\n")
    result_text.insert(tk.END, f"Deadline Position   : {deadline_text}\n")
    result_text.insert(tk.END, f"Current Status      : {status}\n")
    result_text.insert(tk.END, f"Risk Level          : {risk}\n")
    result_text.insert(tk.END, f"Priority            : {priority}\n")
    result_text.insert(tk.END, f"Responsible Person  : {responsible or 'Not specified'}\n")
    result_text.insert(tk.END, f"Remarks             : {remarks or 'None'}\n\n")
    result_text.insert(tk.END, f"Recommended Action:\n{action}\n\n")
    result_text.insert(
        tk.END,
        "Disclaimer: Dummy Data / Demonstration Only.\n"
        "This application does not constitute legal, tax or professional advice."
    )

    result_text.config(state="disabled")


def clear_form():
    compliance_type_var.set("")
    particulars_entry.delete(0, tk.END)
    due_date_entry.delete(0, tk.END)
    status_var.set("")
    risk_var.set("")
    responsible_entry.delete(0, tk.END)
    remarks_entry.delete(0, tk.END)
    result_text.config(state="normal")
    result_text.delete("1.0", tk.END)
    result_text.config(state="disabled")


root = tk.Tk()
root.title(APP_TITLE)
root.geometry("1000x720")
root.minsize(900, 650)

title = tk.Label(
    root,
    text=APP_TITLE,
    font=("Segoe UI", 22, "bold"),
    pady=15
)
title.pack()

subtitle = tk.Label(
    root,
    text="Dummy Data / Demonstration Only",
    font=("Segoe UI", 11, "bold")
)
subtitle.pack()

main_frame = ttk.Frame(root, padding=20)
main_frame.pack(fill="both", expand=True)

form_frame = ttk.LabelFrame(main_frame, text="Compliance Details", padding=15)
form_frame.pack(fill="x")

compliance_type_var = tk.StringVar()
status_var = tk.StringVar()
risk_var = tk.StringVar()

ttk.Label(form_frame, text="Compliance Type").grid(row=0, column=0, sticky="w", padx=5, pady=7)
compliance_type_combo = ttk.Combobox(
    form_frame,
    textvariable=compliance_type_var,
    values=[
        "GST",
        "Income Tax",
        "TDS",
        "ROC",
        "PF",
        "ESI",
        "Internal Compliance"
    ],
    state="readonly",
    width=28
)
compliance_type_combo.grid(row=0, column=1, sticky="w", padx=5, pady=7)

ttk.Label(form_frame, text="Particulars").grid(row=1, column=0, sticky="w", padx=5, pady=7)
particulars_entry = ttk.Entry(form_frame, width=55)
particulars_entry.grid(row=1, column=1, sticky="w", padx=5, pady=7)

ttk.Label(form_frame, text="Due Date (DD-MM-YYYY)").grid(row=2, column=0, sticky="w", padx=5, pady=7)
due_date_entry = ttk.Entry(form_frame, width=30)
due_date_entry.grid(row=2, column=1, sticky="w", padx=5, pady=7)

ttk.Label(form_frame, text="Current Status").grid(row=3, column=0, sticky="w", padx=5, pady=7)
status_combo = ttk.Combobox(
    form_frame,
    textvariable=status_var,
    values=[
        "Completed",
        "Pending",
        "In Progress",
        "Not Started",
        "Overdue"
    ],
    state="readonly",
    width=28
)
status_combo.grid(row=3, column=1, sticky="w", padx=5, pady=7)

ttk.Label(form_frame, text="Risk Level").grid(row=4, column=0, sticky="w", padx=5, pady=7)
risk_combo = ttk.Combobox(
    form_frame,
    textvariable=risk_var,
    values=["High", "Medium", "Low"],
    state="readonly",
    width=28
)
risk_combo.grid(row=4, column=1, sticky="w", padx=5, pady=7)

ttk.Label(form_frame, text="Responsible Person").grid(row=5, column=0, sticky="w", padx=5, pady=7)
responsible_entry = ttk.Entry(form_frame, width=55)
responsible_entry.grid(row=5, column=1, sticky="w", padx=5, pady=7)

ttk.Label(form_frame, text="Remarks").grid(row=6, column=0, sticky="w", padx=5, pady=7)
remarks_entry = ttk.Entry(form_frame, width=55)
remarks_entry.grid(row=6, column=1, sticky="w", padx=5, pady=7)

button_frame = ttk.Frame(main_frame)
button_frame.pack(fill="x", pady=15)

analyze_button = ttk.Button(
    button_frame,
    text="ANALYZE RISK",
    command=analyze_risk
)
analyze_button.pack(side="left", padx=5)

clear_button = ttk.Button(
    button_frame,
    text="CLEAR",
    command=clear_form
)
clear_button.pack(side="left", padx=5)

result_frame = ttk.LabelFrame(main_frame, text="Risk Analysis Result", padding=10)
result_frame.pack(fill="both", expand=True)

result_text = tk.Text(
    result_frame,
    height=15,
    wrap="word",
    font=("Consolas", 11)
)
result_text.pack(fill="both", expand=True)
result_text.config(state="disabled")

footer = tk.Label(
    root,
    text="Developed for ICAI AICA Level-2 Capstone Demonstration",
    font=("Segoe UI", 10),
    pady=8
)
footer.pack()

root.mainloop()