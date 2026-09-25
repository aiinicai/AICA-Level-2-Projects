"""Individual income-tax computation tool for FY 2026-27 (India).

Self-contained Tkinter desktop application converted from the accompanying
Excel model. It is a preparation aid, not a return-filing utility.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import xml.etree.ElementTree as ET


FY_START = date(2026, 4, 1)
AY_START = date(2027, 4, 1)
MONEY = "₹{:,.0f}"

# Restrained desktop palette: blue-grey, muted sage and warm neutrals.
PALETTE = {
    "window": "#E9EEF0",
    "surface": "#FFFFFF",
    "surface_alt": "#F4F6F7",
    "header": "#334D5A",
    "header_soft": "#DCE5E8",
    "accent": "#607F8C",
    "accent_hover": "#4F6F7C",
    "sage": "#789486",
    "sage_soft": "#E1E9E4",
    "sand": "#F3EEE4",
    "sand_border": "#C9BDA7",
    "ink": "#263740",
    "muted": "#66757C",
    "line": "#C8D2D6",
    "white": "#FFFFFF",
}


def number(value: str | float | int) -> float:
    try:
        return max(0.0, float(str(value).replace(",", "").replace("₹", "").strip() or 0))
    except (TypeError, ValueError):
        return 0.0


def parse_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def nested(data, *path, default=None):
    """Safely read a nested JSON path."""
    node = data
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def flatten_records(node, path=""):
    """Yield (path, scalar value) pairs from portal JSON or converted XML."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from flatten_records(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from flatten_records(value, f"{path}[{index}]")
    else:
        yield path, node


def xml_to_data(element):
    """Convert XML to a lightweight nested structure without executing content."""
    children = list(element)
    if not children:
        return (element.text or "").strip()
    result = {}
    for child in children:
        tag = child.tag.split("}")[-1]
        value = xml_to_data(child)
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(value)
        else:
            result[tag] = value
    return result


def months_or_part(start: date | None, end: date | None, include_start_month: bool = False) -> int:
    if not start or not end or end <= start:
        return 0
    months = (end.year - start.year) * 12 + end.month - start.month
    if include_start_month:
        return months + 1
    return months + (1 if end.day > start.day else 0)


def slab_tax(income: float, regime: str, age: str, residential_status: str) -> float:
    income = max(0.0, income)
    if regime == "New":
        bands = [(400000, 0), (800000, .05), (1200000, .10), (1600000, .15),
                 (2000000, .20), (2400000, .25), (math.inf, .30)]
    elif residential_status == "Resident" and age == "80 or above":
        bands = [(500000, 0), (1000000, .20), (math.inf, .30)]
    elif residential_status == "Resident" and age == "60 to 79":
        bands = [(300000, 0), (500000, .05), (1000000, .20), (math.inf, .30)]
    else:
        bands = [(250000, 0), (500000, .05), (1000000, .20), (math.inf, .30)]
    tax, lower = 0.0, 0.0
    for upper, rate in bands:
        tax += max(0.0, min(income, upper) - lower) * rate
        if income <= upper:
            break
        lower = upper
    return tax


def surcharge_rate(total_income: float, regime: str) -> float:
    if total_income <= 5_000_000:
        return 0
    if total_income <= 10_000_000:
        return .10
    if total_income <= 20_000_000:
        return .15
    if regime == "New" or total_income <= 50_000_000:
        return .25
    return .37


class ScrollFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        canvas = tk.Canvas(self, highlightthickness=0, bg=PALETTE["surface_alt"])
        bar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.body = ttk.Frame(canvas, padding=18)
        self.body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))


class PillButton(tk.Canvas):
    """Canvas-based rounded button used for actions and section toggles."""
    def __init__(self, parent, text, command, color, hover=None, selected=None,
                 width=122, height=42, text_color="#FFFFFF", font=("Arial", 9, "bold")):
        try:
            parent_bg = parent.cget("bg")
        except (tk.TclError, KeyError):
            parent_bg = PALETTE["surface_alt"]
        super().__init__(parent, width=width, height=height, bg=parent_bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.label = text
        self.command = command
        self.base_color = color
        self.hover_color = hover or color
        self.selected_color = selected or self.hover_color
        self.text_color = text_color
        self.font_spec = font
        self.is_selected = False
        self.bind("<Enter>", lambda _e: self._draw(self.selected_color if self.is_selected else self.hover_color))
        self.bind("<Leave>", lambda _e: self._draw(self.selected_color if self.is_selected else self.base_color))
        self.bind("<Button-1>", lambda _e: self.command())
        self._draw(self.base_color)

    def _draw(self, fill):
        self.delete("all")
        w, h = int(self["width"]), int(self["height"])
        border = self._shade(fill, 0.78 if self.is_selected else 0.84)

        # Paint a complete outer pill, then a slightly inset inner pill. This
        # creates one clean, continuous boundary without seams at the curves.
        outer_pad, outer_radius = 1, (h - 2) / 2
        self.create_oval(outer_pad, outer_pad, outer_pad + outer_radius * 2, h - outer_pad,
                         fill=border, outline=border)
        self.create_oval(w - outer_pad - outer_radius * 2, outer_pad, w - outer_pad, h - outer_pad,
                         fill=border, outline=border)
        self.create_rectangle(outer_pad + outer_radius, outer_pad,
                              w - outer_pad - outer_radius, h - outer_pad,
                              fill=border, outline=border)

        inner_pad, inner_radius = 2, (h - 4) / 2
        self.create_oval(inner_pad, inner_pad, inner_pad + inner_radius * 2, h - inner_pad,
                         fill=fill, outline=fill)
        self.create_oval(w - inner_pad - inner_radius * 2, inner_pad, w - inner_pad, h - inner_pad,
                         fill=fill, outline=fill)
        self.create_rectangle(inner_pad + inner_radius, inner_pad,
                              w - inner_pad - inner_radius, h - inner_pad,
                              fill=fill, outline=fill)
        self.create_text(w / 2, h / 2, text=self.label, fill=self.text_color, font=self.font_spec)

    @staticmethod
    def _shade(hex_color, factor):
        """Return a darker shade of a #RRGGBB colour for a matching outline."""
        value = hex_color.lstrip("#")
        if len(value) != 6:
            return hex_color
        red, green, blue = (int(value[i:i + 2], 16) for i in (0, 2, 4))
        return f"#{int(red * factor):02X}{int(green * factor):02X}{int(blue * factor):02X}"

    def set_selected(self, selected):
        self.is_selected = bool(selected)
        self._draw(self.selected_color if self.is_selected else self.base_color)


class TaxApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Income-tax Computation FY 2026-27")
        self.geometry("1120x760")
        self.minsize(940, 650)
        self.configure(bg=PALETTE["window"])
        self.vars: dict[str, tk.StringVar] = {}
        self.result_vars: dict[str, tk.StringVar] = {}
        self.last_calculation: dict[str, float | str] = {}
        self._configure_style()
        self._build_header()
        self.nav_bar = tk.Frame(self, bg=PALETTE["window"], padx=20, pady=12)
        self.nav_bar.pack(fill="x")
        self.tabs = ttk.Notebook(self, style="Hidden.TNotebook")
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self._build_profile_tab()
        self._build_income_tab()
        self._build_interest_tab()
        self._build_results_tab()
        self._build_email_tab()
        self._build_tab_navigation()
        footer = tk.Frame(self, bg=PALETTE["header"], padx=20, pady=6)
        footer.pack(fill="x", side="bottom")
        self.status_bar = tk.Label(
            footer,
            text="Ready · Review imported values before filing",
            bg=PALETTE["header"], fg="#DDE7EA", anchor="w",
            font=("Arial", 9),
        )
        self.status_bar.pack(side="left", fill="x", expand=True)
        tk.Label(
            footer,
            text="Powered by – AICA-Level-2 Projects – Sandeep (512632)",
            bg=PALETTE["header"], fg="#CBD8DC", anchor="e",
            font=("Arial", 8, "bold"),
        ).pack(side="right", padx=(18, 0))
        self.tabs.bind("<<NotebookTabChanged>>", self._tab_changed)
        self.calculate(False)

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=PALETTE["surface_alt"])
        style.configure("TLabel", background=PALETTE["surface_alt"], foreground=PALETTE["ink"], font=("Arial", 10))
        style.configure("Sub.TLabel", font=("Arial", 9, "italic"), foreground=PALETTE["muted"], background=PALETTE["surface_alt"])
        style.configure("Section.TLabel", font=("Arial", 11, "bold"), foreground=PALETTE["header"], background=PALETTE["header_soft"], padding=(10, 9))
        style.configure("TNotebook", background=PALETTE["window"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", font=("Arial", 10, "bold"), padding=(16, 10), background="#D5DDE0", foreground=PALETTE["muted"], borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", PALETTE["surface"]), ("active", "#E2E8EA")], foreground=[("selected", PALETTE["header"]), ("active", PALETTE["ink"])])
        style.configure("Hidden.TNotebook", background=PALETTE["window"], borderwidth=0, tabmargins=0)
        style.layout("Hidden.TNotebook.Tab", [])
        style.configure("Primary.TButton", font=("Arial", 10, "bold"), padding=(14, 9), background=PALETTE["accent"], foreground=PALETTE["white"], borderwidth=0, focusthickness=0)
        style.map("Primary.TButton", background=[("active", PALETTE["accent_hover"]), ("pressed", PALETTE["header"]), ("disabled", "#A9B6BB")])
        style.configure("Secondary.TButton", font=("Arial", 9, "bold"), padding=(12, 8), background="#D7E0E3", foreground=PALETTE["header"], borderwidth=0, focusthickness=0)
        style.map("Secondary.TButton", background=[("active", "#C5D1D5"), ("pressed", "#B6C5CA")])
        style.configure("Quiet.TButton", font=("Arial", 9), padding=(11, 8), background="#EEF2F3", foreground=PALETTE["ink"], borderwidth=1, relief="solid")
        style.map("Quiet.TButton", background=[("active", "#E0E7E9")])
        style.configure("TCombobox", padding=7, fieldbackground=PALETTE["sand"], background=PALETTE["sand"], foreground=PALETTE["ink"], bordercolor=PALETTE["sand_border"], arrowcolor=PALETTE["header"])
        style.map("TCombobox", fieldbackground=[("readonly", PALETTE["sand"]), ("focus", PALETTE["white"])], bordercolor=[("focus", PALETTE["accent"])])

    def _build_header(self):
        brand_strip = tk.Frame(
            self, bg=PALETTE["white"], padx=24, pady=7,
            highlightbackground=PALETTE["line"], highlightthickness=0,
        )
        brand_strip.pack(fill="x")
        logo_path = Path(__file__).resolve().parent / "assets" / "income_tax_efiling_logo.png"
        try:
            self.income_tax_logo = tk.PhotoImage(file=str(logo_path))
            tk.Label(
                brand_strip, image=self.income_tax_logo,
                bg=PALETTE["white"], borderwidth=0,
            ).pack(side="left", anchor="w")
        except tk.TclError:
            # Text fallback keeps the identity visible if the image asset is moved.
            fallback = tk.Frame(brand_strip, bg=PALETTE["white"])
            fallback.pack(side="left", anchor="w", pady=4)
            tk.Label(
                fallback, text="e-Filing", bg=PALETTE["white"],
                fg="#174A8B", font=("Arial", 17),
            ).pack(side="left")
            tk.Label(
                fallback, text=" Anywhere Anytime", bg=PALETTE["white"],
                fg="#D62828", font=("Arial", 9, "italic"),
            ).pack(side="left", anchor="s", pady=(0, 4))

        tk.Label(
            brand_strip, text="Tax computation workspace  ·  FY 2026–27",
            bg=PALETTE["white"], fg=PALETTE["muted"], font=("Arial", 9),
        ).pack(side="right", anchor="e", padx=(20, 4))

        top = tk.Frame(self, bg=PALETTE["header"], padx=24, pady=16)
        top.pack(fill="x")
        title_area = tk.Frame(top, bg=PALETTE["header"])
        title_area.pack(side="left", fill="x", expand=True)
        tk.Label(title_area, text="Income-tax computation", bg=PALETTE["header"], fg=PALETTE["white"], font=("Arial", 18, "bold")).pack(anchor="w")
        tk.Label(title_area, text="Financial Year 2026–27  ·  Individual tax workspace", bg=PALETTE["header"], fg="#CBD8DC", font=("Arial", 9)).pack(anchor="w", pady=(3, 0))
        actions = tk.Frame(top, bg=PALETTE["header"])
        actions.pack(side="right", anchor="e")
        action_specs = [
            ("Calculate", lambda: self.calculate(True), "#476775", "#385A69", 116),
            ("Import prefill", self.load_prefill, "#557582", "#476A78", 126),
            ("Export PDF", self.export_pdf, "#63828D", "#557682", 118),
            ("Save", self.save_inputs, "#708F98", "#61818B", 92),
            ("Open", self.load_inputs, "#7D9CA2", "#6E8E96", 92),
            ("Reset", self.reset, "#8AA7AB", "#78999E", 92),
        ]
        for index, (label, command, color, hover, width) in enumerate(action_specs):
            PillButton(actions, label, command, color, hover, width=width, height=40).pack(side="left", padx=(0 if index == 0 else 4, 4))

    def _build_tab_navigation(self):
        shades = ["#6D8791", "#78919A", "#839BA3", "#8EA5AC", "#99AFB4"]
        labels = ["Profile", "Income & Deductions", "Interest 234", "Results", "Payment Email"]
        widths = [106, 178, 122, 104, 142]
        self.nav_buttons = []
        for index, (label, color, width) in enumerate(zip(labels, shades, widths)):
            button = PillButton(
                self.nav_bar, label, lambda i=index: self.tabs.select(i), color,
                hover="#5F7B87", selected=PALETTE["header"], width=width, height=38,
                font=("Arial", 9, "bold"),
            )
            button.pack(side="left", padx=(0, 8))
            self.nav_buttons.append(button)
        self.nav_buttons[0].set_selected(True)

    def _tab_changed(self, _event=None):
        selected = self.tabs.index(self.tabs.select())
        for index, button in enumerate(self.nav_buttons):
            button.set_selected(index == selected)
        self.calculate(False)

    def var(self, key: str, default: str = "0") -> tk.StringVar:
        if key not in self.vars:
            self.vars[key] = tk.StringVar(value=default)
        return self.vars[key]

    def result(self, key: str) -> tk.StringVar:
        if key not in self.result_vars:
            self.result_vars[key] = tk.StringVar(value="-")
        return self.result_vars[key]

    @staticmethod
    def section(parent, text: str, row: int):
        ttk.Label(parent, text=text, style="Section.TLabel").grid(row=row, column=0, columnspan=4, sticky="ew", pady=(14, 8))

    def entry(self, parent, row, label, key, default="0", help_text="", width=24):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(4, 12), pady=5)
        e = tk.Entry(parent, textvariable=self.var(key, default), width=width, bg=PALETTE["sand"], fg=PALETTE["header"], insertbackground=PALETTE["header"], relief="solid", bd=1, highlightthickness=1, highlightbackground=PALETTE["sand_border"], highlightcolor=PALETTE["accent"], font=("Arial", 10))
        e.grid(row=row, column=1, sticky="ew", pady=5)
        if help_text:
            ttk.Label(parent, text=help_text, style="Sub.TLabel", wraplength=390).grid(row=row, column=2, sticky="w", padx=14)
        return e

    def combo(self, parent, row, label, key, choices, default):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(4, 12), pady=6)
        box = ttk.Combobox(parent, textvariable=self.var(key, default), values=choices, state="readonly", width=25)
        box.grid(row=row, column=1, sticky="ew", pady=6)
        return box

    def _new_scroll_tab(self, title):
        frame = ScrollFrame(self.tabs)
        self.tabs.add(frame, text=title)
        frame.body.columnconfigure(1, weight=1)
        frame.body.columnconfigure(2, weight=1)
        return frame.body

    def _build_profile_tab(self):
        p = self._new_scroll_tab("Profile")
        self.section(p, "Taxpayer profile", 0)
        self.entry(p, 1, "Name", "name", "", "Optional; used in the email draft")
        self.entry(p, 2, "PAN", "pan", "", "Optional working-paper reference")
        self.combo(p, 3, "Residential status", "residential_status", ["Resident", "Non-resident"], "Resident")
        self.combo(p, 4, "Age category", "age", ["Below 60", "60 to 79", "80 or above"], "Below 60")
        self.combo(p, 5, "Tax regime", "regime", ["New", "Old"], "New")
        self.combo(p, 6, "Business / professional income?", "has_business", ["No", "Yes"], "No")
        ttk.Label(p, text="Choose the profile first, then enter annual amounts on the Income & Deductions tab. All expenses and deductions are entered as positive numbers.", style="Sub.TLabel", wraplength=800).grid(row=8, column=0, columnspan=3, sticky="w", pady=18)

    def _build_income_tab(self):
        p = self._new_scroll_tab("Income & Deductions")
        rows = [
            ("Income from salary", [("Gross salary", "salary_gross"), ("Exempt allowances (old regime)", "salary_exempt"), ("Professional tax (old regime)", "professional_tax")]),
            ("Income from house property", [("Gross rent / annual value", "rent"), ("Municipal taxes paid", "municipal_tax"), ("Interest on borrowed capital", "housing_interest")]),
            ("Business or profession", [("Gross receipts", "business_receipts"), ("Operating expenses", "business_expenses"), ("Income-tax depreciation", "depreciation")]),
            ("Capital gains", [("STCG under section 111A", "stcg_111a"), ("LTCG under section 112A", "ltcg_112a"), ("LTCG under section 112", "ltcg_112"), ("Other short-term capital gain", "other_stcg")]),
            ("Other sources", [("Savings-account interest", "savings_interest"), ("Deposit / bond interest", "deposit_interest"), ("Dividend income", "dividend"), ("Family pension", "family_pension"), ("Other taxable income / gifts", "other_income"), ("Lottery / game winnings", "lottery"), ("Virtual digital asset income", "vda")]),
            ("Chapter VI-A deductions", [("80C investments / payments", "d80c"), ("80CCD(1B) additional NPS", "d80ccd1b"), ("80D medical insurance", "d80d"), ("80E education-loan interest", "d80e"), ("80G eligible donation deduction", "d80g"), ("80TTA / 80TTB claimed", "d80tt"), ("Other old-regime deduction", "d_other"), ("80CCD(2) employer NPS", "d80ccd2"), ("80CCH(2) Agniveer Corpus", "d80cch"), ("Eligible loss set-off", "loss_setoff")]),
            ("Tax credits and payments", [("TDS / TCS", "tds"), ("Advance tax paid", "advance_tax"), ("Relief under section 89 / foreign tax credit", "relief"), ("Marginal relief adjustment", "marginal_relief")]),
        ]
        row = 0
        for heading, fields in rows:
            self.section(p, heading, row); row += 1
            for label, key in fields:
                self.entry(p, row, label, key); row += 1

    def _build_interest_tab(self):
        p = self._new_scroll_tab("Interest 234")
        self.section(p, "Filing and payment inputs", 0)
        self.combo(p, 1, "Advance-tax method", "advance_method", ["Regular", "Presumptive 44AD / 44ADA"], "Regular")
        self.entry(p, 2, "Original return due date", "return_due_date", "", "Use DD-MM-YYYY")
        self.entry(p, 3, "Actual return filing date", "filing_date", "", "Use DD-MM-YYYY")
        self.entry(p, 4, "Self-assessment payment / computation date", "sat_date", "", "Used as the 234B end date")
        self.entry(p, 5, "Self-assessment tax paid", "self_assessment_tax")
        self.entry(p, 6, "Of which paid by return due date", "sat_by_due_date")
        self.section(p, "Cumulative advance tax paid", 8)
        self.entry(p, 9, "By 15 June 2026", "at_june")
        self.entry(p, 10, "By 15 September 2026", "at_sep")
        self.entry(p, 11, "By 15 December 2026", "at_dec")
        self.entry(p, 12, "By 15 March 2027", "at_mar")
        ttk.Label(p, text="The schedule uses the familiar 234A/234B/234C labels. For FY 2026–27 the corresponding Income-tax Act, 2025 provisions are renumbered. Review late-arising capital gains/dividend relief and multiple self-assessment payments separately.", style="Sub.TLabel", wraplength=820).grid(row=14, column=0, columnspan=3, sticky="w", pady=16)

    def _build_results_tab(self):
        p = self._new_scroll_tab("Results")
        self.section(p, "Computation summary", 0)
        cards = ttk.Frame(p)
        cards.grid(row=1, column=0, columnspan=3, sticky="ew", pady=8)
        for i, (label, key) in enumerate((("Total income", "total_income"), ("Gross tax liability", "gross_tax"), ("Total interest", "total_interest"), ("Final amount payable", "final_payable"))):
            card_colors = ("#E7ECEE", PALETTE["sage_soft"], "#EEEAE2", "#DDE7E9")
            card_bg = card_colors[i]
            card = tk.Frame(cards, bg=card_bg, highlightbackground=PALETTE["line"], highlightthickness=1, padx=22, pady=16)
            card.grid(row=0, column=i, sticky="nsew", padx=5)
            cards.columnconfigure(i, weight=1)
            tk.Label(card, text=label, bg=card_bg, fg=PALETTE["header"], font=("Arial", 9, "bold")).pack()
            tk.Label(card, textvariable=self.result(key), bg=card_bg, fg=PALETTE["ink"], font=("Arial", 16, "bold")).pack(pady=(8, 0))
        self.section(p, "Taxable income by head", 3)
        for r, (label, key) in enumerate((("Salary", "salary"), ("House property", "house_property"), ("Business / profession", "business"), ("Ordinary capital gains", "ordinary_cg"), ("Other sources", "other_sources"), ("Special-rate income", "special_income")), start=4):
            ttk.Label(p, text=label).grid(row=r, column=0, sticky="w", pady=4)
            ttk.Label(p, textvariable=self.result(key), font=("Arial", 10, "bold")).grid(row=r, column=1, sticky="e")
        self.section(p, "Interest breakdown", 11)
        for r, (label, key) in enumerate((("Interest u/s 234A", "interest_234a"), ("Interest u/s 234B", "interest_234b"), ("Interest u/s 234C", "interest_234c")), start=12):
            ttk.Label(p, text=label).grid(row=r, column=0, sticky="w", pady=4)
            ttk.Label(p, textvariable=self.result(key), font=("Arial", 10, "bold")).grid(row=r, column=1, sticky="e")
        ttk.Label(p, textvariable=self.result("status"), style="Sub.TLabel", wraplength=820).grid(row=16, column=0, columnspan=3, sticky="w", pady=18)

    def _build_email_tab(self):
        p = self._new_scroll_tab("Payment Email")
        self.section(p, "Payment reminder details", 0)
        self.entry(p, 1, "Recipient email address", "email", "")
        self.combo(p, 2, "Type of tax", "tax_type", ["Advance Tax", "Self-Assessment Tax"], "Advance Tax")
        self.entry(p, 3, "Payment amount override", "email_amount_override", "0", "Leave zero to use the calculated final payable amount")
        self.entry(p, 4, "Payment due date", "email_due_date", "", "Use DD-MM-YYYY")
        self.entry(p, 5, "Your name / firm's name", "sender_name", "", "Used in the email sign-off")
        self.section(p, "Draft email", 7)
        ttk.Label(p, text="Subject").grid(row=8, column=0, sticky="nw", pady=5)
        self.email_subject = tk.Text(p, height=2, width=75, wrap="word", bg=PALETTE["surface"], fg=PALETTE["ink"], insertbackground=PALETTE["header"], relief="solid", bd=1, highlightthickness=1, highlightbackground=PALETTE["line"], highlightcolor=PALETTE["accent"], font=("Arial", 10))
        self.email_subject.grid(row=8, column=1, columnspan=2, sticky="ew", pady=5)
        ttk.Label(p, text="Body").grid(row=9, column=0, sticky="nw", pady=5)
        self.email_body = tk.Text(p, height=22, width=75, wrap="word", bg=PALETTE["surface"], fg=PALETTE["ink"], insertbackground=PALETTE["header"], relief="solid", bd=1, highlightthickness=1, highlightbackground=PALETTE["line"], highlightcolor=PALETTE["accent"], font=("Arial", 10))
        self.email_body.grid(row=9, column=1, columnspan=2, sticky="ew", pady=5)
        copy_button = PillButton(p, "Copy email body", self.copy_email, "#607F8C", "#4F6F7C", width=150, height=40)
        copy_button.grid(row=10, column=1, sticky="w", pady=8)
        ttk.Label(p, text="This application prepares a draft only. Review the recipient, amount and due date before sending it.", style="Sub.TLabel").grid(row=11, column=0, columnspan=3, sticky="w", pady=12)

    def get(self, key):
        return number(self.var(key).get())

    def calculate(self, show_message=True):
        regime = self.var("regime", "New").get()
        resident = self.var("residential_status", "Resident").get()
        age = self.var("age", "Below 60").get()

        gross_salary = self.get("salary_gross")
        salary_deduction = (self.get("salary_exempt") + self.get("professional_tax") if regime == "Old" else 0)
        if gross_salary > 0:
            salary_deduction += 75_000 if regime == "New" else 50_000
        salary = max(0, gross_salary - salary_deduction)
        rent = self.get("rent"); municipal = self.get("municipal_tax")
        house = rent - municipal - max(0, rent - municipal) * .30 - self.get("housing_interest")
        business = self.get("business_receipts") - self.get("business_expenses") - self.get("depreciation")
        ordinary_cg = self.get("other_stcg")
        family_deduction = min(self.get("family_pension") / 3, 25_000 if regime == "New" else 15_000)
        other_sources = self.get("savings_interest") + self.get("deposit_interest") + self.get("dividend") + self.get("family_pension") + self.get("other_income") - family_deduction
        ordinary_gti = salary + house + business + ordinary_cg + other_sources

        old_deductions = 0
        if regime == "Old":
            old_deductions = min(self.get("d80c"), 150_000) + min(self.get("d80ccd1b"), 50_000) + self.get("d80d") + self.get("d80e") + self.get("d80g") + self.get("d_other")
            tt_cap = 50_000 if resident == "Resident" and age in ("60 to 79", "80 or above") else 10_000
            old_deductions += min(self.get("d80tt"), tt_cap)
        deductions = old_deductions + self.get("d80ccd2") + self.get("d80cch")
        ordinary_taxable = max(0, ordinary_gti - deductions - self.get("loss_setoff"))

        stcg = self.get("stcg_111a"); ltcg112a_taxable = max(0, self.get("ltcg_112a") - 125_000)
        ltcg112 = self.get("ltcg_112"); lottery = self.get("lottery"); vda = self.get("vda")
        special_income = self.get("stcg_111a") + self.get("ltcg_112a") + ltcg112 + lottery + vda
        total_income = round(ordinary_taxable + special_income, -1)
        normal_tax = slab_tax(ordinary_taxable, regime, age, resident)
        special_tax = stcg * .20 + ltcg112a_taxable * .125 + ltcg112 * .125 + lottery * .30 + vda * .30
        tax_before_rebate = normal_tax + special_tax
        rebate = 0.0
        if resident == "Resident":
            if regime == "Old" and total_income <= 500_000:
                rebate = min(12_500, normal_tax)
            elif regime == "New":
                if total_income <= 1_200_000:
                    rebate = min(60_000, normal_tax)
                elif normal_tax > total_income - 1_200_000:
                    rebate = min(normal_tax, normal_tax - (total_income - 1_200_000))
        tax_after_rebate = max(0, tax_before_rebate - rebate)
        sr = surcharge_rate(total_income, regime)
        capped_special_tax = stcg * .20 + ltcg112a_taxable * .125 + ltcg112 * .125
        surcharge = max(0, (tax_after_rebate - capped_special_tax) * sr + capped_special_tax * min(sr, .15))
        surcharge = max(0, surcharge - self.get("marginal_relief"))
        cess = (tax_after_rebate + surcharge) * .04
        gross_tax = tax_after_rebate + surcharge + cess

        tds, advance, relief = self.get("tds"), self.get("advance_tax"), self.get("relief")
        assessed_tax = max(0, gross_tax - tds - relief)
        sat = self.get("self_assessment_tax")
        sat_due = min(sat, self.get("sat_by_due_date"))
        due = parse_date(self.var("return_due_date").get())
        filing = parse_date(self.var("filing_date").get())
        sat_date = parse_date(self.var("sat_date").get()) or filing
        base_234a = max(0, gross_tax - tds - advance - relief - sat_due)
        interest_234a = round(base_234a * .01 * months_or_part(due, filing))

        senior_exempt = resident == "Resident" and age in ("60 to 79", "80 or above") and self.var("has_business").get() == "No"
        shortfall_234b = 0 if assessed_tax < 10_000 or advance >= assessed_tax * .90 or senior_exempt else max(0, assessed_tax - advance)
        months_234b = months_or_part(AY_START, sat_date, include_start_month=True) if shortfall_234b else 0
        interest_234b = round(shortfall_234b * .01 * months_234b)
        method = self.var("advance_method").get()
        percentages = (0, 0, 0, 1) if method.startswith("Presumptive") else (.15, .45, .75, 1)
        cumulative = (self.get("at_june"), self.get("at_sep"), self.get("at_dec"), self.get("at_mar"))
        multipliers = (3, 3, 3, 1)
        interest_234c = 0 if assessed_tax < 10_000 or senior_exempt else round(sum(max(0, assessed_tax * p - paid) * .01 * m for p, paid, m in zip(percentages, cumulative, multipliers)))
        total_interest = interest_234a + interest_234b + interest_234c
        credits = tds + advance + relief + sat
        net_before_interest = gross_tax - credits
        final_payable = round((net_before_interest + total_interest) / 10) * 10

        values = {
            "total_income": total_income, "gross_tax": gross_tax, "total_interest": total_interest,
            "final_payable": final_payable, "salary": salary, "house_property": house,
            "business": business, "ordinary_cg": ordinary_cg, "other_sources": other_sources,
            "special_income": special_income, "interest_234a": interest_234a,
            "interest_234b": interest_234b, "interest_234c": interest_234c,
        }
        self.last_calculation = {
            **values,
            "ordinary_taxable": ordinary_taxable,
            "deductions": deductions,
            "normal_tax": normal_tax,
            "special_tax": special_tax,
            "rebate": rebate,
            "surcharge": surcharge,
            "cess": cess,
            "tax_before_rebate": tax_before_rebate,
            "credits": credits,
            "net_before_interest": net_before_interest,
            "assessed_tax": assessed_tax,
            "regime": regime,
            "residential_status": resident,
            "age": age,
        }
        for key, val in values.items():
            self.result(key).set(MONEY.format(val))
        status = "234B/234C not applied: resident senior citizen without business income." if senior_exempt else "Calculation updated. Review statutory eligibility, dates, instalment relief and unusual transactions before filing."
        self.result("status").set(status)
        self._update_email(final_payable)
        if hasattr(self, "status_bar"):
            self.status_bar.configure(text=f"Calculation updated  ·  Final payable: {MONEY.format(final_payable)}")
        if show_message:
            messagebox.showinfo("Calculation updated", f"Final amount payable including interest: {MONEY.format(final_payable)}")

    def _update_email(self, final_payable):
        override = self.get("email_amount_override")
        amount = override if override > 0 else max(0, final_payable)
        due_text = self.var("email_due_date").get().strip()
        parsed = parse_date(due_text)
        due_display = parsed.strftime("%d %b %Y") if parsed else due_text or "[enter due date]"
        name = self.var("name").get().strip() or "[Client Name]"
        tax_type = self.var("tax_type", "Advance Tax").get()
        sender = self.var("sender_name").get().strip() or "[Your Name / Your Firm's Name]"
        subject = "Important: Notice of Income Tax Liability (Advance Tax / Self-Assessment Tax) & Payment Due Date"
        body = (
            f"Dear {name},\n\n"
            "I hope this email finds you well.\n\n"
            "We have computed your estimated income tax liability for the assessment period. "
            "Below are the details regarding your payable tax amount and the upcoming due date:\n\n"
            f"• Type of Tax: {tax_type}\n"
            f"• Outstanding Amount Payable: ₹{amount:,.0f}\n"
            f"• Due Date for Payment: {due_display}\n\n"
            "Please ensure that the payment is remitted on or before the due date mentioned above.\n\n"
            "Important Note: Failure to pay or any further delay in depositing the tax amount will attract "
            "statutory interest under Sections 234B and 234C of the Income Tax Act, as applicable, and "
            "potential penalties for non-compliance.\n\n"
            "Once the payment is completed, please share the tax payment challan/receipt with us for our "
            "records and for updating your file.\n\n"
            "If you have any questions or require assistance with the payment process, please feel free to reach out.\n\n"
            f"Best regards,\n\n{sender}"
        )
        for widget, text in ((self.email_subject, subject), (self.email_body, body)):
            widget.delete("1.0", "end"); widget.insert("1.0", text)

    def copy_email(self):
        self.calculate(False)
        self.clipboard_clear(); self.clipboard_append(self.email_body.get("1.0", "end-1c"))
        messagebox.showinfo("Copied", "Email body copied to the clipboard.")

    def export_pdf(self):
        """Create a formatted PDF report from the current calculation."""
        self.calculate(False)
        default_name = "Income_Tax_Computation_FY_2026-27.pdf"
        file = filedialog.asksaveasfilename(
            title="Save tax computation PDF",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF document", "*.pdf")],
        )
        if not file:
            return
        try:
            self.create_pdf(file)
            messagebox.showinfo("PDF created", f"The tax computation report was saved to:\n{file}")
        except ImportError:
            messagebox.showerror("PDF dependency missing", "PDF export requires ReportLab. Install it with:\n\npip install reportlab")
        except Exception as exc:
            messagebox.showerror("Could not create PDF", str(exc))

    def create_pdf(self, output_path):
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        calc = self.last_calculation
        if not calc:
            self.calculate(False)
            if hasattr(self, "status_bar"):
                self.status_bar.configure(text=f"Prefill imported  ·  {len(mapped)} supported fields mapped")
            calc = self.last_calculation

        navy = colors.HexColor("#214D68")
        pale = colors.HexColor("#EAF3F8")
        sky = colors.HexColor("#DDEEF7")
        mint = colors.HexColor("#E8F5EC")
        line = colors.HexColor("#C9D8E2")
        muted = colors.HexColor("#667784")
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=navy, spaceAfter=4))
        styles.add(ParagraphStyle(name="ReportSub", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=9, textColor=muted, spaceAfter=14))
        styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, textColor=navy, spaceBefore=10, spaceAfter=6))
        styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=11, textColor=muted))
        styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=9))
        styles.add(ParagraphStyle(name="Center", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9))

        doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=16*mm, bottomMargin=16*mm, title="Income-tax Computation FY 2026-27")
        story = [
            Paragraph("Income-tax Computation", styles["ReportTitle"]),
            Paragraph("Financial Year 2026-27 | Individual", styles["ReportSub"]),
        ]

        def fmt(value):
            return f"INR {float(value):,.0f}"

        def make_table(rows, widths=(100*mm, 70*mm), header=True, highlight_last=False):
            table = Table(rows, colWidths=list(widths), repeatRows=1 if header else 0, hAlign="LEFT")
            commands = [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#243447")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), .35, line),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (1, 1 if header else 0), (1, -1), "RIGHT"),
            ]
            if header:
                commands += [("BACKGROUND", (0, 0), (-1, 0), sky), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("TEXTCOLOR", (0, 0), (-1, 0), navy)]
            if highlight_last:
                commands += [("BACKGROUND", (0, -1), (-1, -1), mint), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("LINEABOVE", (0, -1), (-1, -1), 1, navy)]
            table.setStyle(TableStyle(commands))
            return table

        story.append(Paragraph("Taxpayer profile", styles["Section"]))
        profile = [
            ["Taxpayer", self.var("name").get().strip() or "Not entered"],
            ["PAN", self.var("pan").get().strip() or "Not entered"],
            ["Residential status", str(calc["residential_status"])],
            ["Age category", str(calc["age"])],
            ["Tax regime", str(calc["regime"])],
        ]
        story.append(make_table(profile, header=False))

        story.append(Paragraph("Taxable income", styles["Section"]))
        income_rows = [["Income head", "Taxable amount"],
                       ["Salary", fmt(calc["salary"])],
                       ["House property", fmt(calc["house_property"])],
                       ["Business / profession", fmt(calc["business"])],
                       ["Capital gains taxable at slab rates", fmt(calc["ordinary_cg"])],
                       ["Other sources taxable at slab rates", fmt(calc["other_sources"])],
                       ["Special-rate income", fmt(calc["special_income"])],
                       ["Total income", fmt(calc["total_income"])]]
        story.append(make_table(income_rows, highlight_last=True))

        tax_rows = [["Particular", "Amount"],
                    ["Tax on ordinary income", fmt(calc["normal_tax"])],
                    ["Tax on special-rate income", fmt(calc["special_tax"])],
                    ["Income-tax before rebate", fmt(calc["tax_before_rebate"])],
                    ["Rebate", fmt(calc["rebate"])],
                    ["Surcharge after adjustment", fmt(calc["surcharge"])],
                    ["Health and education cess", fmt(calc["cess"])],
                    ["Gross tax liability", fmt(calc["gross_tax"])],
                    ["Tax credits and payments", fmt(calc["credits"])],
                    ["Net tax before interest", fmt(calc["net_before_interest"])],
                    ["Interest u/s 234A", fmt(calc["interest_234a"])],
                    ["Interest u/s 234B", fmt(calc["interest_234b"])],
                    ["Interest u/s 234C", fmt(calc["interest_234c"])],
                    ["Total interest", fmt(calc["total_interest"])],
                    ["Final amount payable / (refund)", fmt(calc["final_payable"])]]
        story.append(KeepTogether([
            Paragraph("Tax and interest computation", styles["Section"]),
            make_table(tax_rows, highlight_last=True),
        ]))

        story += [Spacer(1, 8), Paragraph("Preparation notes", styles["Section"])]
        notes = [
            "This report is generated from user-entered and imported prefill information. Reconcile it with AIS, Form 26AS, Form 16, books, challans and the applicable return utility.",
            "Sections 234A, 234B and 234C are calculated from the dates and cumulative advance-tax payments entered in the application. Review late-arising income relief, multiple tax payments and notified due-date extensions.",
            "For FY 2026-27, the Income-tax Act, 2025 applies. Familiar legacy section descriptions are retained for working-paper continuity where the corresponding provisions are renumbered.",
        ]
        for item in notes:
            story.append(Paragraph(f"- {item}", styles["Small"]))
            story.append(Spacer(1, 3))

        generated = datetime.now().strftime("%d %b %Y, %I:%M %p")
        def footer(canvas, document):
            canvas.saveState()
            canvas.setStrokeColor(line); canvas.line(16*mm, 12*mm, 194*mm, 12*mm)
            canvas.setFont("Helvetica", 7); canvas.setFillColor(muted)
            canvas.drawString(16*mm, 8*mm, f"Generated {generated}")
            canvas.drawRightString(194*mm, 8*mm, f"Page {document.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=footer, onLaterPages=footer)

    def save_inputs(self):
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file:
            Path(file).write_text(json.dumps({k: v.get() for k, v in self.vars.items()}, indent=2), encoding="utf-8")

    def load_inputs(self):
        file = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file:
            return
        try:
            data = json.loads(Path(file).read_text(encoding="utf-8"))
            for key, value in data.items():
                self.var(key).set(str(value))
            self.calculate(False)
        except Exception as exc:
            messagebox.showerror("Could not load inputs", str(exc))

    def load_prefill(self):
        """Import recognized fields from Income Tax portal JSON/XML prefills."""
        file = filedialog.askopenfilename(
            title="Select Income Tax prefill file",
            filetypes=[("Income Tax prefill", "*.json *.xml"), ("JSON files", "*.json"), ("XML files", "*.xml"), ("All files", "*.*")],
        )
        if not file:
            return
        try:
            source = Path(file)
            if source.suffix.lower() == ".xml":
                root = ET.parse(source).getroot()
                data = {root.tag.split("}")[-1]: xml_to_data(root)}
            else:
                data = json.loads(source.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("The prefill does not contain a recognized object structure.")
            mapped, notes = self._map_prefill(data)
            self.calculate(False)
            summary = "Imported fields:\n• " + "\n• ".join(mapped) if mapped else "No supported fields were found."
            if notes:
                summary += "\n\nReview notes:\n• " + "\n• ".join(notes)
            messagebox.showinfo("Income Tax prefill import", summary)
        except Exception as exc:
            messagebox.showerror("Could not import prefill", f"The file could not be mapped.\n\n{exc}")

    def _map_prefill(self, data):
        mapped, notes = [], []

        def set_text(key, value, label):
            if value not in (None, ""):
                self.var(key).set(str(value))
                mapped.append(label)

        def set_amount(key, value, label):
            amount = number(value)
            if amount:
                self.var(key).set(f"{amount:.2f}")
                mapped.append(label)

        # Taxpayer identity and profile.
        personal = data.get("personalInfo", {}) if isinstance(data.get("personalInfo"), dict) else {}
        name_block = personal.get("assesseeName") or nested(personal, "orgFirmInfo", "AssesseeName", default={}) or {}
        if isinstance(name_block, dict):
            parts = []
            for key in ("firstName", "middleName", "surNameOrOrgName", "FirstName", "MiddleName", "SurNameOrOrgName"):
                value = name_block.get(key)
                if value and str(value).strip() not in parts:
                    parts.append(str(value).strip())
            set_text("name", " ".join(parts), "Taxpayer name")
        set_text("pan", personal.get("pan") or personal.get("assesseVerPan"), "PAN")
        address = personal.get("address", {}) if isinstance(personal.get("address"), dict) else {}
        set_text("email", address.get("emailAddress") or address.get("emailAddressSecondary"), "Email address")

        residence = str(nested(personal, "filingStatus", "residentialStatus", default="") or "").upper()
        if residence:
            self.var("residential_status").set("Non-resident" if "NON" in residence or residence in {"NRI", "NR"} else "Resident")
            mapped.append("Residential status")
        dob_raw = personal.get("dob") or nested(personal, "orgFirmInfo", "DateOFFormOrIncorp", default="")
        dob = parse_date(str(dob_raw)) if dob_raw else None
        if dob:
            age = (date(2027, 3, 31) - dob).days // 365
            self.var("age").set("80 or above" if age >= 80 else "60 to 79" if age >= 60 else "Below 60")
            mapped.append("Age category")

        regime_raw = nested(data, "form10IF", "newTaxRegime", default=None)
        if regime_raw is not None:
            flag = str(regime_raw).strip().upper()
            self.var("regime").set("New" if flag in {"Y", "YES", "TRUE", "1", "NEW"} else "Old")
            mapped.append("Tax regime indicator")

        # Portal insight fields. Prefer the Insights block because it is already consolidated.
        insights = data.get("insights", {}) if isinstance(data.get("insights"), dict) else {}
        form26 = data.get("form26as", {}) if isinstance(data.get("form26as"), dict) else {}
        form24 = data.get("form24q", {}) if isinstance(data.get("form24q"), dict) else {}
        savings = insights.get("intrstFrmSavingBank", form24.get("intrstFrmSavingBank", 0))
        deposits = insights.get("intrstFrmTermDeposit", form26.get("intrstFrmTermDeposit", 0))
        set_amount("savings_interest", savings, "Savings-account interest")
        set_amount("deposit_interest", deposits, "Term-deposit interest")

        presumptive = nested(form26, "persumptiveInc44ADA", "grsReceipt", default=0)
        if number(presumptive):
            set_amount("business_receipts", presumptive, "Presumptive professional receipts")
            self.var("has_business").set("Yes")
            self.var("advance_method").set("Presumptive 44AD / 44ADA")
            mapped.append("Business-income and presumptive-method flags")

        # Other-source rows are mapped by description; unknown rows stay in Other income.
        rows = insights.get("incomeDeductionsOthersInc") or form26.get("incomeDeductionsOthersInc") or []
        totals = {"dividend": 0.0, "family_pension": 0.0, "other_income": 0.0}
        if isinstance(rows, dict):
            rows = [rows]
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            desc = str(row.get("othSrcNatureDesc", "")).lower()
            amount = number(row.get("othSrcOthAmount", 0))
            if "dividend" in desc:
                totals["dividend"] += amount
            elif "family" in desc and "pension" in desc:
                totals["family_pension"] += amount
            elif not any(term in desc for term in ("saving", "term deposit", "fixed deposit")):
                totals["other_income"] += amount
        for key, label in (("dividend", "Dividend income"), ("family_pension", "Family pension"), ("other_income", "Other-source income")):
            set_amount(key, totals[key], label)

        # TDS/TCS credits: sum claimed credit fields rather than gross receipts.
        flat = list(flatten_records(form26, "/form26as"))
        tds = sum(number(value) for path, value in flat if path.lower().endswith(("/taxclaimedownhands", "/tdsclaimed", "/tdscredit")))
        tcs = sum(number(value) for path, value in flat if path.lower().endswith(("/taxcollected", "/tcsclaimed", "/tcscredit")))
        set_amount("tds", tds + tcs, "TDS/TCS credit")

        # Salary and head-wise gross receipts, when present in 26AS structures.
        salary = rent = business = 0.0
        def scan_records(node):
            nonlocal salary, rent, business
            if isinstance(node, dict):
                head = str(node.get("headOfIncome", "")).lower()
                gross = number(node.get("grossAmount", 0))
                if gross:
                    if "salary" in head:
                        salary += gross
                    elif "house" in head or "property" in head:
                        rent += gross
                    elif "business" in head or "profession" in head:
                        business += gross
                for value in node.values():
                    scan_records(value)
            elif isinstance(node, list):
                for value in node:
                    scan_records(value)
        scan_records(form26)
        set_amount("salary_gross", salary, "Salary receipts")
        set_amount("rent", rent, "House-property receipts")
        if business and not number(presumptive):
            set_amount("business_receipts", business, "Business/professional receipts")
            self.var("has_business").set("Yes")

        # Chapter VI-A deductions found in Insights/Form 24Q.
        deduction_blocks = []
        for block in (insights.get("UsrDeductUndChapVIAType"), form24.get("usrDeductUndChapVIAType")):
            if isinstance(block, dict):
                deduction_blocks.append(block)
        aliases = {
            "80c": "d80c", "80ccd1b": "d80ccd1b", "80d": "d80d", "80e": "d80e",
            "80g": "d80g", "80tta": "d80tt", "80ttb": "d80tt", "80ccd2": "d80ccd2", "80cch": "d80cch",
        }
        deduction_totals = {value: 0.0 for value in aliases.values()}
        for block in deduction_blocks:
            for key, value in block.items():
                normalized = re.sub(r"[^0-9a-z]", "", key.lower().replace("section", ""))
                for token, target in aliases.items():
                    if token in normalized:
                        deduction_totals[target] += number(value)
                        break
        for key, amount in deduction_totals.items():
            set_amount(key, amount, f"Deduction {key.replace('d', '', 1).upper()}")

        if not mapped:
            notes.append("The file was readable, but its field names did not match the supported prefill mappings.")
        notes.append("Prefill values are provisional. Reconcile them with AIS, Form 26AS, Form 16, books and the applicable ITR utility.")
        notes.append("Capital gains, house-property deductions, business expenses and advance/self-assessment challans may require manual entry if absent or ambiguous in the prefill.")
        return mapped, notes

    def reset(self):
        if not messagebox.askyesno("Reset", "Clear all entered values?"):
            return
        keep = {"residential_status": "Resident", "age": "Below 60", "regime": "New", "has_business": "No", "advance_method": "Regular", "tax_type": "Advance Tax"}
        for key, var in self.vars.items():
            var.set(keep.get(key, "" if key in {"name", "pan", "email", "return_due_date", "filing_date", "sat_date", "email_due_date", "sender_name"} else "0"))
        self.calculate(False)


if __name__ == "__main__":
    TaxApp().mainloop()
