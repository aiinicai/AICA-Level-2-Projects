"""
capex_npv.desktop_app
======================
A native desktop dashboard for the Capex NPV model — no browser
involved. Built with CustomTkinter (light theme) + an embedded
matplotlib chart + ttk tables for the projection and sensitivity grid.

Run with:
    capex-npv-desktop
or:
    python -m capex_npv.desktop_app
"""

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .model import CapexNPVModel

# ---------------------------------------------------------------
# THEME
# ---------------------------------------------------------------
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

BG = "#F7F9FA"
PANEL = "#FFFFFF"
BORDER = "#E3E8EC"
TEXT = "#1D2939"
MUTED = "#667085"
TEAL = "#1FA98B"
TEAL_SOFT = "#E4F7F1"
AMBER = "#D97706"
AMBER_SOFT = "#FDF1E1"
ACCENT = "#2F6FED"


class CapexDesktopApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Capex Ledger — NPV Appraisal")
        self.geometry("1280x820")
        self.configure(fg_color=BG)

        # ---- state variables ----
        self.currency = tk.StringVar(value="₹")
        self.capex = tk.DoubleVar(value=50_000_000)
        self.base_revenue = tk.DoubleVar(value=40_000_000)
        self.growth_mode = tk.StringVar(value="Flat rate")
        self.growth_flat = tk.DoubleVar(value=8.0)
        self.growth_custom = [tk.DoubleVar(value=8.0) for _ in range(10)]
        self.margin_mode = tk.StringVar(value="Flat rate")
        self.margin_flat = tk.DoubleVar(value=20.0)
        self.margin_custom = [tk.DoubleVar(value=20.0) for _ in range(10)]
        self.wacc = tk.DoubleVar(value=12.0)
        self.tax = tk.DoubleVar(value=25.0)
        self.life = tk.IntVar(value=10)
        self.maint = tk.DoubleVar(value=2.0)
        self.wc = tk.DoubleVar(value=5.0)
        self.term = tk.DoubleVar(value=0.0)
        self.salvage = tk.DoubleVar(value=0.0)

        self._build_layout()
        self.recompute()

    # -------------------------------------------------------------
    # LAYOUT
    # -------------------------------------------------------------
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        sidebar = ctk.CTkScrollableFrame(self, width=300, fg_color=PANEL,
                                          border_width=1, border_color=BORDER,
                                          corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")

        ctk.CTkLabel(sidebar, text="Capex Ledger", font=("Georgia", 20, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=18, pady=(20, 0))
        ctk.CTkLabel(sidebar, text="10-YEAR NPV APPRAISAL", font=("Segoe UI", 10),
                     text_color=MUTED).pack(anchor="w", padx=18, pady=(0, 18))

        self._section(sidebar, "Project Basics")
        self._entry_row(sidebar, "Currency symbol", self.currency, is_text=True)
        self._entry_row(sidebar, "Initial Capex", self.capex)
        self._entry_row(sidebar, "Base Year Revenue", self.base_revenue)

        self._section(sidebar, "Growth & Margin")
        self._mode_toggle(sidebar, "Sales growth mode", self.growth_mode)
        growth_area = ctk.CTkFrame(sidebar, fg_color="transparent")
        growth_area.pack(fill="x")
        self.growth_flat_frame = ctk.CTkFrame(growth_area, fg_color="transparent")
        self._slider_row(self.growth_flat_frame, "Growth % (all 10 yrs)", self.growth_flat, -20, 40)
        self.growth_custom_frame = ctk.CTkFrame(growth_area, fg_color="transparent")
        self._custom_grid(self.growth_custom_frame, self.growth_custom)
        self.growth_flat_frame.pack(fill="x", padx=18)

        self._mode_toggle(sidebar, "EBITDA margin mode", self.margin_mode, kind="margin")
        margin_area = ctk.CTkFrame(sidebar, fg_color="transparent")
        margin_area.pack(fill="x")
        self.margin_flat_frame = ctk.CTkFrame(margin_area, fg_color="transparent")
        self._slider_row(self.margin_flat_frame, "EBITDA margin %", self.margin_flat, 0, 60)
        self.margin_custom_frame = ctk.CTkFrame(margin_area, fg_color="transparent")
        self._custom_grid(self.margin_custom_frame, self.margin_custom)
        self.margin_flat_frame.pack(fill="x", padx=18)

        self._section(sidebar, "Financing & Tax")
        self._slider_row(sidebar, "Discount Rate / WACC %", self.wacc, 1, 30)
        self._slider_row(sidebar, "Tax Rate %", self.tax, 0, 45)
        self._slider_row(sidebar, "Useful Life (yrs)", self.life, 1, 10, is_int=True)

        self._section(sidebar, "Working Capital & Capex")
        self._slider_row(sidebar, "Maintenance Capex % of Revenue", self.maint, 0, 15)
        self._slider_row(sidebar, "Working Capital % of Δ Sales", self.wc, 0, 25)

        self._section(sidebar, "Terminal Value")
        self._slider_row(sidebar, "Terminal Growth %", self.term, 0, 8)
        self._entry_row(sidebar, "Salvage Value (Yr 10)", self.salvage)

        self.warn_label = ctk.CTkLabel(sidebar, text="", text_color=AMBER,
                                        font=("Segoe UI", 11), wraplength=250, justify="left")
        self.warn_label.pack(anchor="w", padx=18, pady=(6, 10))

        ctk.CTkButton(sidebar, text="Reset to defaults", fg_color="transparent",
                      border_width=1, border_color=BORDER, text_color=MUTED,
                      hover_color=TEAL_SOFT, command=self.reset_defaults
                      ).pack(fill="x", padx=18, pady=(6, 24))

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew", padx=24, pady=20)
        main.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(main, text="Appraisal Dashboard", font=("Georgia", 24, "bold"),
                     text_color=TEXT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(main, text="Updated live as you adjust assumptions on the left.",
                     font=("Segoe UI", 12), text_color=MUTED).grid(row=1, column=0, sticky="w", pady=(0, 14))

        self.decision_banner = ctk.CTkLabel(main, text="", font=("Segoe UI", 13, "bold"),
                                             corner_radius=8, height=40, anchor="w", padx=16)
        self.decision_banner.grid(row=2, column=0, sticky="ew", pady=(0, 16))

        kpi_frame = ctk.CTkFrame(main, fg_color="transparent")
        kpi_frame.grid(row=3, column=0, sticky="ew", pady=(0, 18))
        for i in range(5):
            kpi_frame.grid_columnconfigure(i, weight=1)
        self.kpi_labels = {}
        for i, key in enumerate(["NPV", "IRR", "Payback", "Profitability Index", "Total PV Inflows"]):
            card = ctk.CTkFrame(kpi_frame, fg_color=PANEL, border_width=1,
                                 border_color=BORDER, corner_radius=10)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            ctk.CTkLabel(card, text=key.upper(), font=("Segoe UI", 10),
                         text_color=MUTED).pack(anchor="w", padx=14, pady=(10, 2))
            val = ctk.CTkLabel(card, text="—", font=("Consolas", 18, "bold"), text_color=TEXT)
            val.pack(anchor="w", padx=14, pady=(0, 12))
            self.kpi_labels[key] = val

        chart_panel = ctk.CTkFrame(main, fg_color=PANEL, border_width=1,
                                    border_color=BORDER, corner_radius=10)
        chart_panel.grid(row=4, column=0, sticky="ew", pady=(0, 18))
        ctk.CTkLabel(chart_panel, text="Cash Flow Ledger", font=("Georgia", 15, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=18, pady=(14, 0))
        ctk.CTkLabel(chart_panel, text="Bars: annual free cash flow.  Line: cumulative discounted value vs. outlay.",
                     font=("Segoe UI", 11), text_color=MUTED).pack(anchor="w", padx=18, pady=(0, 8))

        self.fig = plt.Figure(figsize=(9, 3.6), dpi=100, facecolor=PANEL)
        self.ax1 = self.fig.add_subplot(111)
        self.ax2 = self.ax1.twinx()
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 14))

        tabs = ctk.CTkTabview(main, fg_color=PANEL, border_width=1, border_color=BORDER,
                               segmented_button_selected_color=ACCENT)
        tabs.grid(row=5, column=0, sticky="nsew")
        main.grid_rowconfigure(5, weight=1)
        tab_proj = tabs.add("10-Year Projection")
        tab_sens = tabs.add("Sensitivity")

        self.proj_tree = self._make_table(tab_proj,
            ["Year", "Revenue", "EBITDA", "Deprec.", "EBIT", "Tax", "NOPAT",
             "Maint. Capex", "Δ WC", "FCF", "PV of FCF"])
        self.sens_tree = self._make_table(tab_sens, ["WACC \\ Growth"])

        # wire live updates
        for var in ([self.capex, self.base_revenue, self.growth_flat, self.margin_flat,
                     self.wacc, self.tax, self.life, self.maint, self.wc, self.term,
                     self.salvage] + self.growth_custom + self.margin_custom):
            var.trace_add("write", lambda *a: self.recompute())
        self.currency.trace_add("write", lambda *a: self.recompute())
        self.growth_mode.trace_add("write", lambda *a: self._on_growth_mode())
        self.margin_mode.trace_add("write", lambda *a: self._on_margin_mode())

    # -------------------------------------------------------------
    # SMALL WIDGET BUILDERS
    # -------------------------------------------------------------
    def _section(self, parent, title):
        ctk.CTkLabel(parent, text=title.upper(), font=("Segoe UI", 10, "bold"),
                     text_color=MUTED).pack(anchor="w", padx=18, pady=(16, 6))

    def _entry_row(self, parent, label, var, is_text=False):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=18, pady=4)
        ctk.CTkLabel(f, text=label, font=("Segoe UI", 11), text_color=MUTED).pack(anchor="w")
        ctk.CTkEntry(f, textvariable=var, fg_color="#F2F4F6", border_color=BORDER,
                     text_color=TEXT, width=260 if not is_text else 60).pack(anchor="w", pady=(2, 0))

    def _slider_row(self, parent, label, var, lo, hi, is_int=False):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=18, pady=6)
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=label, font=("Segoe UI", 11), text_color=MUTED).pack(side="left")
        val_lbl = ctk.CTkLabel(top, text="", font=("Consolas", 11, "bold"), text_color=TEAL)
        val_lbl.pack(side="right")

        def update_label(*_):
            v = var.get()
            val_lbl.configure(text=(f"{int(v)}" if is_int else f"{v:.1f}%"))

        slider = ctk.CTkSlider(f, from_=lo, to=hi, variable=var,
                                number_of_steps=int((hi - lo) * (1 if is_int else 2)),
                                progress_color=TEAL, button_color=TEAL, button_hover_color=AMBER)
        slider.pack(fill="x", pady=(4, 0))
        var.trace_add("write", update_label)
        update_label()

    def _mode_toggle(self, parent, label, var, kind="growth"):
        ctk.CTkLabel(parent, text=label, font=("Segoe UI", 11), text_color=MUTED
                     ).pack(anchor="w", padx=18, pady=(6, 2))
        seg = ctk.CTkSegmentedButton(parent, values=["Flat rate", "Per year"], variable=var,
                                      selected_color=TEAL, selected_hover_color=TEAL)
        seg.pack(anchor="w", padx=18, pady=(0, 6), fill="x")

    def _custom_grid(self, parent, varlist):
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=18, pady=(0, 6))
        for i, v in enumerate(varlist):
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=i // 5, column=i % 5, padx=2, pady=2)
            ctk.CTkLabel(cell, text=f"Y{i+1}", font=("Segoe UI", 9), text_color=MUTED).pack()
            ctk.CTkEntry(cell, textvariable=v, width=44, height=24,
                         fg_color="#F2F4F6", border_color=BORDER, text_color=TEXT,
                         font=("Consolas", 10)).pack()

    def _make_table(self, parent, columns):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Light.Treeview", background=PANEL, fieldbackground=PANEL,
                         foreground=TEXT, rowheight=26, font=("Consolas", 10), borderwidth=0)
        style.configure("Light.Treeview.Heading", background="#F2F4F6", foreground=MUTED,
                         font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Light.Treeview", background=[("selected", TEAL_SOFT)])

        tree = ttk.Treeview(parent, columns=columns, show="headings", style="Light.Treeview")
        for c in columns:
            tree.heading(c, text=c)
            tree.column(c, width=95, anchor="e" if c != columns[0] else "w")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        return tree

    # -------------------------------------------------------------
    # MODE SWITCHING
    # -------------------------------------------------------------
    def _on_growth_mode(self):
        if self.growth_mode.get() == "Flat rate":
            self.growth_custom_frame.pack_forget()
            self.growth_flat_frame.pack(fill="x", padx=18)
        else:
            self.growth_flat_frame.pack_forget()
            self.growth_custom_frame.pack(fill="x", padx=18)
        self.recompute()

    def _on_margin_mode(self):
        if self.margin_mode.get() == "Flat rate":
            self.margin_custom_frame.pack_forget()
            self.margin_flat_frame.pack(fill="x", padx=18)
        else:
            self.margin_flat_frame.pack_forget()
            self.margin_custom_frame.pack(fill="x", padx=18)
        self.recompute()

    # -------------------------------------------------------------
    # MODEL + RENDER
    # -------------------------------------------------------------
    def _get_model(self, wacc_override=None, growth_override=None):
        sales_growth = ([g.get() / 100 for g in self.growth_custom]
                         if self.growth_mode.get() == "Per year" else self.growth_flat.get() / 100)
        if growth_override is not None:
            sales_growth = growth_override
        ebitda_margin = ([m.get() / 100 for m in self.margin_custom]
                          if self.margin_mode.get() == "Per year" else self.margin_flat.get() / 100)
        try:
            return CapexNPVModel(
                initial_capex=self.capex.get(),
                base_revenue=self.base_revenue.get(),
                sales_growth=sales_growth,
                ebitda_margin=ebitda_margin,
                tax_rate=self.tax.get() / 100,
                discount_rate=(wacc_override if wacc_override is not None else self.wacc.get() / 100),
                useful_life=int(self.life.get()),
                maintenance_capex_pct=self.maint.get() / 100,
                wc_pct_of_sales=self.wc.get() / 100,
                terminal_growth=self.term.get() / 100,
                salvage_value=self.salvage.get(),
            )
        except (tk.TclError, ValueError):
            return None

    def recompute(self):
        model = self._get_model()
        if model is None:
            return
        cur = self.currency.get() or ""

        self.warn_label.configure(text="")
        if self.wacc.get() / 100 <= self.term.get() / 100 and self.term.get() > 0:
            self.warn_label.configure(text="⚠ WACC must exceed terminal growth rate.")
            return

        proj = model.build_projection()
        npv_val = model.npv()
        irr_val = model.irr()
        payback = model.payback_period()
        pi = model.profitability_index()
        pv_inflows = npv_val + self.capex.get()

        # decision banner
        if npv_val >= 0:
            self.decision_banner.configure(text=f"  ✓  ACCEPT — NPV is positive at {cur}{npv_val:,.0f}",
                                            fg_color=TEAL_SOFT, text_color=TEAL)
        else:
            self.decision_banner.configure(text=f"  ✕  REJECT — NPV is negative at {cur}{npv_val:,.0f}",
                                            fg_color=AMBER_SOFT, text_color=AMBER)

        self.kpi_labels["NPV"].configure(text=f"{cur}{npv_val:,.0f}",
                                          text_color=TEAL if npv_val >= 0 else AMBER)
        self.kpi_labels["IRR"].configure(text=(f"{irr_val:.1%}" if irr_val is not None else "n/a"))
        self.kpi_labels["Payback"].configure(text=(f"{payback:.2f} yrs" if payback else "> horizon"))
        self.kpi_labels["Profitability Index"].configure(text=f"{pi:.2f}x",
                                                           text_color=TEAL if pi >= 1 else AMBER)
        self.kpi_labels["Total PV Inflows"].configure(text=f"{cur}{pv_inflows:,.0f}")

        self._draw_chart(proj)
        self._fill_projection_table(proj)
        self._fill_sensitivity_table(model)

    def _draw_chart(self, proj):
        self.ax1.clear()
        self.ax2.clear()
        years = proj["Year"]
        fcf = proj["FCF"]
        colors = [TEAL if v >= 0 else AMBER for v in fcf]
        self.ax1.bar(years, fcf, color=colors, width=0.6)
        self.ax1.set_facecolor(PANEL)
        self.ax1.tick_params(colors=MUTED, labelsize=8)
        self.ax1.set_xticks(years)

        cum = proj["PV of FCF"].cumsum() - self.capex.get()
        self.ax2.plot(years, cum, color=AMBER, marker="o", markersize=4, linewidth=1.6)
        self.ax2.tick_params(colors=MUTED, labelsize=8)
        self.ax2.axhline(0, color=BORDER, linewidth=1)

        for spine in list(self.ax1.spines.values()) + list(self.ax2.spines.values()):
            spine.set_color(BORDER)
        self.fig.tight_layout()
        self.canvas.draw()

    def _fill_projection_table(self, proj):
        self.proj_tree.delete(*self.proj_tree.get_children())
        for _, row in proj.iterrows():
            self.proj_tree.insert("", "end", values=[
                f"Year {int(row['Year'])}", f"{row['Revenue']:,.0f}", f"{row['EBITDA']:,.0f}",
                f"{row['Depreciation']:,.0f}", f"{row['EBIT']:,.0f}", f"{row['Tax']:,.0f}",
                f"{row['NOPAT']:,.0f}", f"{row['Maintenance Capex']:,.0f}",
                f"{row['Change in WC']:,.0f}", f"{row['FCF']:,.0f}", f"{row['PV of FCF']:,.0f}",
            ])

    def _fill_sensitivity_table(self, model):
        base_growth = (self.growth_flat.get() if self.growth_mode.get() == "Flat rate" else 8.0)
        wacc_list = [max(1, self.wacc.get() - 4), max(1, self.wacc.get() - 2), self.wacc.get(),
                     self.wacc.get() + 2, self.wacc.get() + 4]
        growth_list = [base_growth - 8, base_growth - 4, base_growth, base_growth + 4, base_growth + 8]

        cols = ["WACC \\ Growth"] + [f"{g:.1f}%" for g in growth_list]
        self.sens_tree.configure(columns=cols)
        for c in cols:
            self.sens_tree.heading(c, text=c)
            self.sens_tree.column(c, width=95, anchor="e" if c != cols[0] else "w")
        self.sens_tree.delete(*self.sens_tree.get_children())

        for w in wacc_list:
            row_vals = [f"{w:.1f}%"]
            for g in growth_list:
                m = self._get_model(wacc_override=w / 100, growth_override=g / 100)
                if m is None:
                    row_vals.append("—")
                    continue
                m.build_projection()
                try:
                    npv_val = m.npv()
                    row_vals.append(f"{npv_val:,.0f}")
                except ValueError:
                    row_vals.append("—")
            self.sens_tree.insert("", "end", values=row_vals)

    def reset_defaults(self):
        self.currency.set("₹")
        self.capex.set(50_000_000)
        self.base_revenue.set(40_000_000)
        self.growth_mode.set("Flat rate")
        self.growth_flat.set(8.0)
        for v in self.growth_custom:
            v.set(8.0)
        self.margin_mode.set("Flat rate")
        self.margin_flat.set(20.0)
        for v in self.margin_custom:
            v.set(20.0)
        self.wacc.set(12.0)
        self.tax.set(25.0)
        self.life.set(10)
        self.maint.set(2.0)
        self.wc.set(5.0)
        self.term.set(0.0)
        self.salvage.set(0.0)
        self.recompute()


def main():
    app = CapexDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
