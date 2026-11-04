# ============================================================
#  desktop_app.py  -  window version (also the source of the .exe)
#  Statutory Audit Document Generator  |  Sowmya G & Associates
#
#  How to run: open this file in IDLE and press F5
#  (audit_engine.py and ca_logo.jpeg must be in the same folder).
#
#  Install once from Command Prompt:
#     py -m pip install python-docx pdfplumber
# ============================================================

import os
import re
import sys
import subprocess
from datetime import date
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from audit_engine import *          # documents, PDF reading and settings


# ------------------------------------------------------------
# 1. The form window (four tabs)
# ------------------------------------------------------------


DOCUMENTS = [
    ("gen_eng", "Letter of Engagement", "1_Letter_of_Engagement", make_engagement_letter),
    ("gen_dsc", "DSC Authorisation Letter", "2_DSC_Authorisation_Letter", make_dsc_letters),
    ("gen_mrl", "Letter of Representation", "3_Letter_of_Representation",
     make_mrl),
    ("gen_report", "Audit Report (with CARO / IFC annexures)", "4_Independent_Auditors_Report",
     make_audit_report),
]


class GeneratorApp:

    def __init__(self, root):
        self.root = root
        self.vars = {}
        self.texts = {}
        self.caro_buttons = []
        today = date.today().strftime("%d/%m/%Y")

        root.title("Statutory Audit Document Generator - " + FIRM_DEFAULTS["firm"])
        root.resizable(False, False)
        outer = ttk.Frame(root, padding=10)
        outer.grid(row=0, column=0)

        tabs = ttk.Notebook(outer)
        tabs.grid(row=0, column=0, sticky="ew")
        tab_company = ttk.Frame(tabs, padding=10)
        tab_opinion = ttk.Frame(tabs, padding=10)
        tab_caro = ttk.Frame(tabs, padding=10)
        tab_auditor = ttk.Frame(tabs, padding=10)
        tabs.add(tab_company, text="  1. Company & Directors  ")
        tabs.add(tab_opinion, text="  2. Opinion  ")
        tabs.add(tab_caro, text="  3. Company facts  ")
        tabs.add(tab_auditor, text="  4. Auditor & Dates  ")

        # ----- Tab 1: company -----
        box = self.make_box(tab_company, "Company")
        ttk.Button(box, text="Load from MCA master data PDF...",
                   command=self.load_from_pdf).grid(row=0, column=0, columnspan=2,
                                                    sticky="ew", pady=(0, 6))
        self.add_entry(box, "company", "Company name *", width=52)
        self.add_entry(box, "cin", "CIN *", width=52)
        self.add_entry(box, "address", "Registered office *", width=52)
        self.add_entry(box, "constitution", "Constitution", width=52)
        self.add_check(box, "private", "Private company", True)

        box = self.make_box(tab_company, "Financial statements (Accounting Standards)")
        self.add_combo(box, "fy", "Financial year", financial_year_choices())
        self.add_combo(box, "result", "Result for the year", ["profit", "loss"])
        self.add_check(box, "cash_flow", "Cash Flow Statement prepared "
                       "(not required for small companies / OPC)", True)

        box = self.make_box(tab_company, "Directors (first two sign the letters)")
        for col, text in enumerate(("Name", "DIN", "Designation")):
            ttk.Label(box, text=text, foreground="gray").grid(row=0, column=col, sticky="w")
        for i in range(NUMBER_OF_DIRECTORS):
            self.vars["dir_name_" + str(i)] = tk.StringVar()
            self.vars["dir_din_" + str(i)] = tk.StringVar()
            self.vars["dir_desig_" + str(i)] = tk.StringVar(value="Director")
            ttk.Entry(box, textvariable=self.vars["dir_name_" + str(i)], width=32).grid(
                row=i + 1, column=0, pady=2, padx=(0, 6))
            ttk.Entry(box, textvariable=self.vars["dir_din_" + str(i)], width=12).grid(
                row=i + 1, column=1, pady=2, padx=(0, 6))
            ttk.Combobox(box, textvariable=self.vars["dir_desig_" + str(i)],
                         values=DIRECTOR_DESIGNATIONS, width=20).grid(row=i + 1, column=2,
                                                                      pady=2)

        # ----- Tab 2: opinion -----
        box = self.make_box(tab_opinion, "Opinion")
        self.add_combo(box, "opinion", "Type of opinion", OPINIONS,
                       on_change=self.update_opinion_fields)
        self.add_text(box, "basis_text", "Matter giving rise to the modification")
        self.add_text(box, "eom", "Emphasis of Matter (leave blank if none)")
        box = self.make_box(tab_opinion, "Reporting")
        self.add_check(box, "caro", "CARO 2020 applies (adds Annexure)", True,
                       on_change=self.update_caro_tab)
        self.add_check(box, "ifc", "Report on Internal Financial Controls required "
                       "(adds Annexure)", False)
        self.add_check(box, "litigation", "Company has pending litigations", False)

        box = self.make_box(tab_opinion, "Audit trail (edit log) in accounting software")
        self.add_combo(box, "audit_trail", "Audit trail maintained?", AUDIT_TRAIL_OPTIONS,
                       on_change=self.update_audit_trail)
        self.add_entry(box, "audit_trail_from", "Enabled from (dd/mm/yyyy)", width=14)
        self.audit_trail_entry = box.grid_slaves(row=self.next_row(box) - 1, column=1)[0]

        # ----- Tab 3: CARO -----
        ttk.Label(tab_caro, text="Tick what applies. These drive the CARO 2020 annexure and "
                  "the Letter of Representation.\nUnticked items are reported as 'not "
                  "applicable' or 'nil'. Yellow highlights in the documents need your input.",
                  foreground="gray").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        for number, (key, label, default) in enumerate(CARO_ITEMS):
            self.vars[key] = tk.BooleanVar(value=default)
            button = ttk.Checkbutton(tab_caro, text=label, variable=self.vars[key])
            button.grid(row=1 + number // 2, column=number % 2, sticky="w", pady=3,
                        padx=(0, 20))
            self.caro_buttons.append(button)

        # ----- Tab 4: auditor and dates -----
        box = self.make_box(tab_auditor, "Auditor")
        self.add_entry(box, "firm", "Firm name *", FIRM_DEFAULTS["firm"])
        self.add_entry(box, "auditor", "Signing auditor *", FIRM_DEFAULTS["auditor"])
        self.add_combo(box, "designation", "Designation", ["Proprietor", "Partner"])
        self.add_entry(box, "frn", "FRN *", FIRM_DEFAULTS["frn"])
        self.add_entry(box, "membership", "Membership no. *", FIRM_DEFAULTS["membership"])
        self.add_entry(box, "udin", "UDIN (audit report)")
        self.add_entry(box, "place", "Place *", FIRM_DEFAULTS["place"])

        box = self.make_box(tab_auditor, "Letterhead")
        self.add_entry(box, "firm_address1", "Address line 1", FIRM_DEFAULTS["firm_address1"])
        self.add_entry(box, "firm_address2", "Address line 2", FIRM_DEFAULTS["firm_address2"])
        self.add_entry(box, "phone", "Phone", FIRM_DEFAULTS["phone"])
        self.add_entry(box, "email", "Email", FIRM_DEFAULTS["email"])
        self.add_entry(box, "website", "Website", FIRM_DEFAULTS["website"])
        row = self.next_row(box)
        ttk.Label(box, text="Logo").grid(row=row, column=0, sticky="w", pady=2)
        self.vars["logo"] = tk.StringVar(value=default_logo())
        logo_row = ttk.Frame(box)
        logo_row.grid(row=row, column=1, sticky="w", padx=(8, 0))
        ttk.Entry(logo_row, textvariable=self.vars["logo"], width=30).grid(row=0, column=0)
        ttk.Button(logo_row, text="Browse...", command=self.choose_logo).grid(
            row=0, column=1, padx=(6, 0))

        box = self.make_box(tab_auditor, "Dates (dd/mm/yyyy)")
        self.add_entry(box, "engagement_date", "Engagement letter & DSC *", today)
        self.add_entry(box, "mrl_date", "Management representation *", today)
        self.add_entry(box, "report_date", "Signing of audit report *", today)

        # ----- Below the tabs: what to create and where -----
        bottom = ttk.Frame(outer)
        bottom.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        box = ttk.LabelFrame(bottom, text="Documents to create", padding=8)
        box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        for number, (key, label, _, _) in enumerate(DOCUMENTS):
            self.vars[key] = tk.BooleanVar(value=True)
            ttk.Checkbutton(box, text=label, variable=self.vars[key]).grid(
                row=number, column=0, sticky="w")

        box = ttk.LabelFrame(bottom, text="Save in (a sub-folder is created per company)",
                             padding=8)
        box.grid(row=0, column=1, sticky="nsew")
        self.vars["folder"] = tk.StringVar(value=OUTPUT_FOLDER)
        ttk.Entry(box, textvariable=self.vars["folder"], width=38).grid(row=0, column=0)
        ttk.Button(box, text="Browse...", command=self.choose_folder).grid(
            row=0, column=1, padx=(6, 0))
        buttons = ttk.Frame(box)
        buttons.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="Generate documents", command=self.generate).grid(
            row=0, column=0, padx=(0, 6))
        ttk.Button(buttons, text="Close", command=root.destroy).grid(row=0, column=1)
        self.status = ttk.Label(box, text="", foreground="gray", wraplength=330)
        self.status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.update_opinion_fields()
        self.update_caro_tab()
        self.update_audit_trail()

    # ----- helpers that place widgets -----

    def make_box(self, parent, title):
        box = ttk.LabelFrame(parent, text=title, padding=8)
        box.grid(sticky="ew", pady=(0, 8))
        return box

    def next_row(self, box):
        return box.grid_size()[1]

    def add_entry(self, box, key, label, default="", width=40):
        row = self.next_row(box)
        ttk.Label(box, text=label).grid(row=row, column=0, sticky="w", pady=2)
        self.vars[key] = tk.StringVar(value=default)
        ttk.Entry(box, textvariable=self.vars[key], width=width).grid(
            row=row, column=1, sticky="w", pady=2, padx=(8, 0))

    def add_combo(self, box, key, label, options, on_change=None):
        row = self.next_row(box)
        ttk.Label(box, text=label).grid(row=row, column=0, sticky="w", pady=2)
        self.vars[key] = tk.StringVar(value=options[0])
        combo = ttk.Combobox(box, textvariable=self.vars[key], values=options,
                             state="readonly", width=24)
        combo.grid(row=row, column=1, sticky="w", pady=2, padx=(8, 0))
        if on_change:
            combo.bind("<<ComboboxSelected>>", lambda event: on_change())

    def add_check(self, box, key, label, default, on_change=None):
        row = self.next_row(box)
        self.vars[key] = tk.BooleanVar(value=default)
        ttk.Checkbutton(box, text=label, variable=self.vars[key],
                        command=on_change).grid(row=row, column=0, columnspan=2,
                                                sticky="w", pady=1)

    def add_text(self, box, key, label):
        row = self.next_row(box)
        ttk.Label(box, text=label).grid(row=row, column=0, columnspan=2,
                                        sticky="w", pady=(6, 2))
        text = tk.Text(box, height=4, width=70, wrap="word", font=("Segoe UI", 9))
        text.grid(row=row + 1, column=0, columnspan=2, sticky="ew")
        self.texts[key] = text

    # ----- behaviour -----

    def set_text_enabled(self, key, enabled):
        text = self.texts[key]
        if enabled:
            text.config(state="normal", background="white")
        else:
            text.config(state="normal")
            text.delete("1.0", "end")
            text.config(state="disabled", background="#e8e8e8")

    def update_opinion_fields(self):
        opinion = self.vars["opinion"].get()
        self.set_text_enabled("basis_text", opinion != "Unmodified")
        self.set_text_enabled("eom", opinion != "Disclaimer")

    def update_audit_trail(self):
        """The 'enabled from' date is needed only when it started mid-year."""
        if self.vars["audit_trail"].get() == AUDIT_TRAIL_OPTIONS[1]:
            self.audit_trail_entry.config(state="normal")
        else:
            self.vars["audit_trail_from"].set("")
            self.audit_trail_entry.config(state="disabled")

    def update_caro_tab(self):
        # The facts on tab 3 are also used by the Letter of Representation,
        # so they stay available even when CARO does not apply.
        pass

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.vars["folder"].get(),
                                         title="Choose where to save the documents")
        if folder:
            self.vars["folder"].set(folder)

    def choose_logo(self):
        path = filedialog.askopenfilename(title="Choose the logo for the letterhead",
                                          filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if path:
            self.vars["logo"].set(path)

    def load_from_pdf(self):
        if not PDF_AVAILABLE:
            messagebox.showerror("pdfplumber not installed",
                                 "To read PDFs, run this once in Command Prompt:\n\n"
                                 "py -m pip install pdfplumber\n\nThen restart the program.")
            return
        path = filedialog.askopenfilename(title="Choose the MCA master data PDF",
                                          filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        try:
            found, line_count = extract_master_data(path)
        except Exception as error:
            messagebox.showerror("Could not read PDF", str(error))
            return
        if line_count == 0:
            messagebox.showerror("No text found",
                                 "This PDF has no readable text (it may be a scanned image). "
                                 "Download the master data again from the MCA portal, or "
                                 "type the details in.")
            return

        labels = {"company": "Company name", "cin": "CIN",
                  "address": "Registered office", "constitution": "Constitution"}
        filled, not_found = [], []
        for key, label in labels.items():
            if found[key]:
                self.vars[key].set(found[key])
                filled.append(label)
            else:
                not_found.append(label)
        if found["constitution"]:
            text = found["constitution"].lower()
            self.vars["private"].set("private" in text or "one person" in text)

        directors = found["directors"][:NUMBER_OF_DIRECTORS]
        for i in range(NUMBER_OF_DIRECTORS):
            if i < len(directors):
                self.vars["dir_name_" + str(i)].set(directors[i]["name"])
                self.vars["dir_din_" + str(i)].set(directors[i]["din"])
                self.vars["dir_desig_" + str(i)].set("Director")   # not taken from MCA
            elif directors:
                self.vars["dir_name_" + str(i)].set("")
                self.vars["dir_din_" + str(i)].set("")
        if directors:
            filled.append(str(len(directors)) + " director(s)")
        else:
            not_found.append("Directors")

        message = ("Filled from PDF: " + ", ".join(filled)) if filled else "Nothing could be read."
        if not_found:
            message = message + "\n\nNot found, please type in: " + ", ".join(not_found)
        if found["cin"].startswith("L"):
            message = message + "\n\nNote: the CIN shows this is a listed company."
        messagebox.showinfo("MCA master data", message + "\n\nPlease check before generating.")

    def collect_details(self):
        d = {}
        for key, var in self.vars.items():
            value = var.get()
            d[key] = value.strip() if isinstance(value, str) else value
        for key, text in self.texts.items():
            d[key] = text.get("1.0", "end").strip()
        d["directors"] = []
        for i in range(NUMBER_OF_DIRECTORS):
            name = d["dir_name_" + str(i)]
            if name:
                d["directors"].append({"name": name, "din": d["dir_din_" + str(i)],
                                       "designation": d["dir_desig_" + str(i)] or "Director"})
        d.update(fy_details(d["fy"]))
        if d["udin"] == "":
            d["udin"] = "____________________"
        return d

    def check_details(self, d):
        """Return a list of problems; an empty list means all is well."""
        problems = []
        required = {"company": "Company name", "cin": "CIN", "address": "Registered office",
                    "firm": "Firm name", "auditor": "Signing auditor", "frn": "FRN",
                    "membership": "Membership no.", "place": "Place"}
        for key, label in required.items():
            if d[key] == "":
                problems.append(label + " is empty")
        for key, label in (("engagement_date", "Engagement date"),
                           ("mrl_date", "MRL date"), ("report_date", "Audit report date")):
            if not check_date(d[key]):
                problems.append(label + " must be dd/mm/yyyy")
        if d["audit_trail"] == AUDIT_TRAIL_OPTIONS[1] and not check_date(d["audit_trail_from"]):
            problems.append("Audit trail 'enabled from' date must be dd/mm/yyyy (tab 2)")
        if d["opinion"] != "Unmodified" and d["basis_text"] == "":
            problems.append("Describe the matter giving rise to the modification (tab 2)")
        needs_directors = d["gen_eng"] or d["gen_dsc"] or d["gen_mrl"]
        if needs_directors and not d["directors"]:
            problems.append("Enter at least one director (tab 1)")
        for director in d["directors"]:
            if not re.fullmatch(r"\d{8}", director["din"]):
                problems.append("DIN of " + director["name"] + " should be 8 digits")
        if not any(d[key] for key, _, _, _ in DOCUMENTS):
            problems.append("Tick at least one document to create")
        return problems

    def generate(self):
        if not WORD_AVAILABLE:
            messagebox.showerror("python-docx not installed",
                                 "Run this once in Command Prompt:\n\n"
                                 "py -m pip install python-docx\n\nThen restart the program.")
            return
        d = self.collect_details()
        problems = self.check_details(d)
        if problems:
            messagebox.showwarning("Please check", "- " + "\n- ".join(problems))
            return
        if not re.fullmatch(CIN_PATTERN, d["cin"]):
            if not messagebox.askyesno("CIN format",
                                       "The CIN does not look like the usual 21-character "
                                       "format.\n\nContinue anyway?"):
                return
        if d["folder"] == OUTPUT_FOLDER:
            os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        if not os.path.isdir(d["folder"]):
            messagebox.showerror("Folder not found", "This folder does not exist:\n" +
                                 d["folder"])
            return

        out_folder = os.path.join(d["folder"], safe_name(d["company"]) + "_FY_" + d["fy"])
        os.makedirs(out_folder, exist_ok=True)
        created = []
        try:
            for key, label, file_name, maker in DOCUMENTS:
                if d[key]:
                    maker(d, os.path.join(out_folder, file_name + ".docx"))
                    created.append(file_name + ".docx")
        except PermissionError:
            messagebox.showerror("Could not save", "A file with the same name may be open in "
                                 "Word. Close it and try again.")
            return
        except Exception as error:
            messagebox.showerror("Could not save", str(error))
            return

        self.status.config(text="Saved " + str(len(created)) + " document(s) in " +
                           out_folder, foreground="green")
        if messagebox.askyesno("Documents created",
                               "Saved in:\n" + out_folder + "\n\n" + "\n".join(created) +
                               "\n\nReview all wording before issuing.\n\nOpen the folder now?"):
            open_folder(out_folder)


def open_folder(folder):
    if sys.platform.startswith("win"):
        os.startfile(folder)
    elif sys.platform == "darwin":
        subprocess.run(["open", folder])
    else:
        subprocess.run(["xdg-open", folder])


# ------------------------------------------------------------
# 2. Start the program
# ------------------------------------------------------------

def main():
    root = tk.Tk()
    GeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
