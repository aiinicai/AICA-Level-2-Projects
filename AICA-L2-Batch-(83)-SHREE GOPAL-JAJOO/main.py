"""
main.py
-------
LC Analyser - Modern Enterprise Trade Finance Desktop GUI.
Engineered with cohesive Blue-themed UI and SQLite Database Integration
for saving, retrieving, and searching LC analyses and amendment requests.

Run with:  python main.py
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional, Any

# Enable Windows Per-Monitor DPI awareness if available
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from models import (
    AnalysisResult, ClausePoint, VERDICT_OPTIONS,
    SECTION_MAIN_SUMMARY, SECTION_GOODS, SECTION_DOCUMENTS, SECTION_CHARGES,
    SUBSECTION_ORDER,
)
import pdf_extract
import lc_parser
import rules_engine
import exporter
import database

LC_TYPE_DRAFT = "Draft LC"
LC_TYPE_ISSUED = "Issued / Transmitted LC"

# ---------------------------------------------------------------------------
# Visual Palette - Cohesive Blue Tones & Accent Badges
# ---------------------------------------------------------------------------
COLOR_PRIMARY_DARK = "#0F2942"      # Deep Corporate Navy
COLOR_PRIMARY_NAVY = "#1E3A8A"      # Midnight Blue
COLOR_ACCENT_BLUE = "#2563EB"       # Vibrant Royal Blue
COLOR_ACCENT_HOVER = "#1D4ED8"      # Deep Royal Hover
COLOR_OCEAN_BLUE = "#0284C7"        # Ocean Blue Accent
COLOR_SKY_LIGHT = "#EBF3FA"         # Ice / Soft Blue Background
COLOR_CARD_BG = "#FFFFFF"           # Crisp Card White
COLOR_BORDER = "#CBD5E1"            # Subtle Border Grey
COLOR_BORDER_BLUE = "#93C5FD"       # Blue Border Accent
COLOR_TEXT_MAIN = "#0F172A"         # Slate Main Text
COLOR_TEXT_MUTED = "#64748B"        # Slate Muted Text

# Verdict Colors
COLOR_VERDICT_CORRECT = "#059669"   # Emerald Green
COLOR_VERDICT_AMEND = "#DC2626"     # Crimson Red
COLOR_VERDICT_CLARIFY = "#D97706"   # Amber Orange
COLOR_VERDICT_INFO = "#475569"      # Slate Grey

COLOR_BG_CORRECT = "#D1FAE5"
COLOR_BG_AMEND = "#FEE2E2"
COLOR_BG_CLARIFY = "#FEF3C7"
COLOR_BG_INFO = "#F1F5F9"


class RowWidgets:
    """Holds live Tk variables for a single clause row."""
    __slots__ = ("clause", "verdict_var", "remarks_var", "frame")

    def __init__(
        self,
        clause: ClausePoint,
        verdict_var: tk.StringVar,
        remarks_var: tk.StringVar,
        frame: Optional[tk.Widget] = None,
    ):
        self.clause = clause
        self.verdict_var = verdict_var
        self.remarks_var = remarks_var
        self.frame = frame


class LCAnalyserApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("LC Analyser — Enterprise Trade Finance Suite")
        self.root.geometry("1500x880")
        self.root.minsize(1050, 650)

        # Initialize Database
        database.init_db()

        self.selected_file: Optional[str] = None
        self.lc_type_var = tk.StringVar(value="")
        self.export_format_var = tk.StringVar(value="word")
        self.current_record_id: Optional[int] = None

        self.result: Optional[AnalysisResult] = None
        self.row_widgets: List[RowWidgets] = []
        self.section_tab_frames: Dict[str, ttk.Frame] = {}

        # Search variables for Database Tab
        self.search_lc_no_var = tk.StringVar()
        self.search_issuer_var = tk.StringVar()
        self.search_amount_var = tk.StringVar()
        self.search_beneficiary_var = tk.StringVar()
        self.search_general_var = tk.StringVar()

        self._configure_styles()
        self._build_header()
        self._build_main_tabs()

    # ------------------------------------------------------------------
    # Styles & Themes Configuration
    # ------------------------------------------------------------------
    def _configure_styles(self):
        self.style = ttk.Style()
        try:
            if "clam" in self.style.theme_names():
                self.style.theme_use("clam")
        except Exception:
            pass

        self.root.configure(bg=COLOR_SKY_LIGHT)

        # Global fonts
        self.font_title = ("Segoe UI", 12, "bold")
        self.font_heading = ("Segoe UI", 10, "bold")
        self.font_body = ("Segoe UI", 9)
        self.font_bold = ("Segoe UI", 9, "bold")
        self.font_mono = ("Consolas", 10)

        # Configure TTK styles
        self.style.configure(".", background=COLOR_SKY_LIGHT, foreground=COLOR_TEXT_MAIN, font=self.font_body)

        # Frames
        self.style.configure("Header.TFrame", background=COLOR_PRIMARY_DARK)
        self.style.configure("Card.TFrame", background=COLOR_CARD_BG, relief="solid", borderwidth=1)
        self.style.configure("Sky.TFrame", background=COLOR_SKY_LIGHT)
        self.style.configure("White.TFrame", background="#FFFFFF")

        # Labels
        self.style.configure("HeaderTitle.TLabel", background=COLOR_PRIMARY_DARK, foreground="#FFFFFF", font=("Segoe UI", 13, "bold"))
        self.style.configure("HeaderSub.TLabel", background=COLOR_PRIMARY_DARK, foreground="#93C5FD", font=("Segoe UI", 9))
        self.style.configure("HeaderBadge.TLabel", background="#1E3A8A", foreground="#BFDBFE", font=("Segoe UI", 9, "bold"), padding=(8, 3))

        self.style.configure("CardTitle.TLabel", background=COLOR_CARD_BG, foreground=COLOR_PRIMARY_NAVY, font=self.font_heading)
        self.style.configure("Muted.TLabel", foreground=COLOR_TEXT_MUTED, font=self.font_body)
        self.style.configure("Bold.TLabel", font=self.font_bold)

        # Buttons
        self.style.configure(
            "Primary.TButton",
            background=COLOR_ACCENT_BLUE,
            foreground="#FFFFFF",
            font=self.font_bold,
            padding=(10, 5),
            borderwidth=0,
        )
        self.style.map(
            "Primary.TButton",
            background=[("active", COLOR_ACCENT_HOVER), ("disabled", "#94A3B8")],
            foreground=[("disabled", "#E2E8F0")],
        )

        self.style.configure(
            "Success.TButton",
            background=COLOR_VERDICT_CORRECT,
            foreground="#FFFFFF",
            font=self.font_bold,
            padding=(10, 5),
            borderwidth=0,
        )
        self.style.map(
            "Success.TButton",
            background=[("active", "#047857"), ("disabled", "#94A3B8")],
            foreground=[("disabled", "#E2E8F0")],
        )

        self.style.configure(
            "Secondary.TButton",
            background="#FFFFFF",
            foreground=COLOR_PRIMARY_NAVY,
            font=self.font_body,
            padding=(8, 4),
            borderwidth=1,
        )
        self.style.map(
            "Secondary.TButton",
            background=[("active", "#EFF6FF"), ("disabled", "#F1F5F9")],
            foreground=[("disabled", "#94A3B8")],
        )

        self.style.configure(
            "Action.TButton",
            background=COLOR_OCEAN_BLUE,
            foreground="#FFFFFF",
            font=self.font_bold,
            padding=(10, 5),
            borderwidth=0,
        )
        self.style.map(
            "Action.TButton",
            background=[("active", "#0369A1"), ("disabled", "#94A3B8")],
            foreground=[("disabled", "#E2E8F0")],
        )

        self.style.configure(
            "Danger.TButton",
            background=COLOR_VERDICT_AMEND,
            foreground="#FFFFFF",
            font=self.font_bold,
            padding=(10, 5),
            borderwidth=0,
        )
        self.style.map(
            "Danger.TButton",
            background=[("active", "#B91C1C"), ("disabled", "#94A3B8")],
            foreground=[("disabled", "#E2E8F0")],
        )

        # Notebook
        self.style.configure("TNotebook", background=COLOR_SKY_LIGHT, tabmargins=[2, 4, 2, 0])
        self.style.configure(
            "TNotebook.Tab",
            background="#CBD5E1",
            foreground=COLOR_TEXT_MAIN,
            padding=[12, 5],
            font=self.font_bold,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", COLOR_PRIMARY_NAVY), ("active", "#94A3B8")],
            foreground=[("selected", "#FFFFFF"), ("active", "#0F172A")],
        )

        # Treeview (Table) styling for Database records
        self.style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground=COLOR_TEXT_MAIN,
            rowheight=26,
            fieldbackground="#FFFFFF",
            font=self.font_body,
        )
        self.style.configure(
            "Treeview.Heading",
            background=COLOR_PRIMARY_NAVY,
            foreground="#FFFFFF",
            font=self.font_bold,
            padding=(6, 5),
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", COLOR_ACCENT_HOVER)],
        )
        self.style.map(
            "Treeview",
            background=[("selected", "#DBEAFE")],
            foreground=[("selected", COLOR_PRIMARY_DARK)],
        )

        # Progressbar
        self.style.configure(
            "TProgressbar",
            troughcolor="#E2E8F0",
            background=COLOR_ACCENT_BLUE,
            thickness=6,
        )

    # ------------------------------------------------------------------
    # Top Branding Header
    # ------------------------------------------------------------------
    def _build_header(self):
        header_frame = ttk.Frame(self.root, style="Header.TFrame", padding=(14, 8))
        header_frame.pack(side="top", fill="x")

        left = ttk.Frame(header_frame, style="Header.TFrame")
        left.pack(side="left", fill="y")

        title_box = ttk.Frame(left, style="Header.TFrame")
        title_box.pack(side="left")

        ttk.Label(
            title_box,
            text="🛡️ LC ANALYSER — Enterprise Trade Finance Suite",
            style="HeaderTitle.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            title_box,
            text="Rule-Based Compliance Engine • UCP 600 Scrutiny • Clause Verification & Amendment Generator",
            style="HeaderSub.TLabel",
        ).pack(anchor="w", pady=(1, 0))

        right = ttk.Frame(header_frame, style="Header.TFrame")
        right.pack(side="right", fill="y")

        self.db_status_badge = ttk.Label(
            right,
            text="● SQLite Database Connected",
            style="HeaderBadge.TLabel",
        )
        self.db_status_badge.pack(side="right", padx=(8, 0))

        self.active_record_badge = ttk.Label(
            right,
            text="New Session",
            style="HeaderBadge.TLabel",
        )
        self.active_record_badge.pack(side="right")

    # ------------------------------------------------------------------
    # Main Tabs: Analysis Workspace vs. Database & History
    # ------------------------------------------------------------------
    def _build_main_tabs(self):
        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(fill="both", expand=True, padx=8, pady=(4, 6))

        # Tab 1: Analysis Workspace
        self.tab_workspace = ttk.Frame(self.main_notebook, style="Sky.TFrame")
        self.main_notebook.add(self.tab_workspace, text="   📄 LC Analysis & Workspace   ")

        # Tab 2: Database Records & History
        self.tab_database = ttk.Frame(self.main_notebook, style="Sky.TFrame")
        self.main_notebook.add(self.tab_database, text="   🗄️ Saved Analysis & Database Search   ")

        self._build_workspace_tab()
        self._build_database_tab()

        # Refresh database list when tab is clicked
        self.main_notebook.bind("<<NotebookTabChanged>>", self._on_main_tab_changed)

    # ------------------------------------------------------------------
    # TAB 1: WORKSPACE
    # ------------------------------------------------------------------
    def _build_workspace_tab(self):
        # 1. Top Control Bar (packed top)
        self._build_workspace_top_controls()

        # 2. KPI Summary Bar (packed top)
        self._build_kpi_summary_bar()

        # 3. Bottom Actions & Export Hub - PACKED BOTTOM FIRST so it is NEVER pushed off screen!
        self._build_workspace_bottom_bar()

        # 4. Paned Workspace Body (Tabs + Clause Viewer) - packed expand=True LAST
        self._build_workspace_body()

    def _build_workspace_top_controls(self):
        card = tk.Frame(self.tab_workspace, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER, highlightthickness=1, padx=10, pady=6)
        card.pack(side="top", fill="x", padx=4, pady=(2, 3))

        # Left: File Selector
        f_left = tk.Frame(card, bg=COLOR_CARD_BG)
        f_left.pack(side="left", fill="y")

        ttk.Button(f_left, text="📁 Select LC Copy (PDF)...", style="Secondary.TButton", command=self.on_select_file).pack(side="left")

        self.file_label = tk.Label(
            f_left, text="No PDF selected", bg="#F1F5F9", fg="#475569",
            font=self.font_bold, padx=8, pady=3, relief="groove", borderwidth=1,
        )
        self.file_label.pack(side="left", padx=(8, 12))

        # Center: LC Type Selector
        type_box = tk.LabelFrame(
            f_left, text=" LC Document Type ", bg=COLOR_CARD_BG, fg=COLOR_PRIMARY_NAVY,
            font=self.font_heading, padx=6, pady=1,
        )
        type_box.pack(side="left", padx=(0, 12))

        tk.Radiobutton(
            type_box, text="Draft LC", variable=self.lc_type_var, value=LC_TYPE_DRAFT,
            bg=COLOR_CARD_BG, fg=COLOR_TEXT_MAIN, activebackground=COLOR_CARD_BG,
            font=self.font_body,
        ).pack(side="left", padx=(3, 6))

        tk.Radiobutton(
            type_box, text="Issued / Transmitted LC", variable=self.lc_type_var, value=LC_TYPE_ISSUED,
            bg=COLOR_CARD_BG, fg=COLOR_TEXT_MAIN, activebackground=COLOR_CARD_BG,
            font=self.font_body,
        ).pack(side="left", padx=(0, 3))

        # Right: Action Buttons
        f_right = tk.Frame(card, bg=COLOR_CARD_BG)
        f_right.pack(side="left", fill="y")

        ttk.Button(f_right, text="▶ Run Analysis", style="Primary.TButton", command=self.on_analyze).pack(side="left", padx=(0, 6))

        self.top_save_btn = ttk.Button(
            f_right, text="💾 Save to Database", style="Success.TButton",
            command=self.on_save_to_database, state="disabled",
        )
        self.top_save_btn.pack(side="left", padx=(0, 6))

        ttk.Button(f_right, text="🔄 New / Reset", style="Secondary.TButton", command=self.on_refresh).pack(side="left")

        # Progress & Status row
        p_row = tk.Frame(self.tab_workspace, bg=COLOR_SKY_LIGHT, padx=4, pady=1)
        p_row.pack(side="top", fill="x")

        self.progress = ttk.Progressbar(p_row, orient="horizontal", mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True)

        self.status_label = tk.Label(
            p_row, text="Ready", bg=COLOR_SKY_LIGHT, fg=COLOR_PRIMARY_NAVY,
            font=self.font_bold, width=36, anchor="w",
        )
        self.status_label.pack(side="left", padx=(8, 0))

    def _build_kpi_summary_bar(self):
        """Live KPI metric chips showing counts of clauses in various states."""
        self.kpi_bar = tk.Frame(self.tab_workspace, bg=COLOR_SKY_LIGHT)
        self.kpi_bar.pack(side="top", fill="x", padx=4, pady=(1, 3))

        self.kpi_total_chip = self._create_kpi_chip(self.kpi_bar, "Total Points", "0", COLOR_PRIMARY_NAVY, "#DBEAFE")
        self.kpi_correct_chip = self._create_kpi_chip(self.kpi_bar, "Correct / In Order", "0", COLOR_VERDICT_CORRECT, COLOR_BG_CORRECT)
        self.kpi_amend_chip = self._create_kpi_chip(self.kpi_bar, "Requires Amendment", "0", COLOR_VERDICT_AMEND, COLOR_BG_AMEND)
        self.kpi_clarify_chip = self._create_kpi_chip(self.kpi_bar, "Needs Clarification", "0", COLOR_VERDICT_CLARIFY, COLOR_BG_CLARIFY)
        self.kpi_info_chip = self._create_kpi_chip(self.kpi_bar, "Informational / N/A", "0", COLOR_VERDICT_INFO, COLOR_BG_INFO)

    def _create_kpi_chip(self, parent, label_text: str, default_val: str, fg_color: str, bg_color: str) -> Dict[str, tk.Label]:
        frame = tk.Frame(parent, bg=bg_color, relief="groove", borderwidth=1, padx=8, pady=2)
        frame.pack(side="left", padx=(0, 6))

        lbl_title = tk.Label(frame, text=label_text, bg=bg_color, fg="#334155", font=("Segoe UI", 8, "bold"))
        lbl_title.pack(side="left", padx=(0, 5))

        lbl_val = tk.Label(frame, text=default_val, bg=bg_color, fg=fg_color, font=("Segoe UI", 9, "bold"))
        lbl_val.pack(side="left")

        return {"frame": frame, "val": lbl_val}

    def _set_progress(self, value: int, status: str):
        self.progress["value"] = value
        self.status_label.config(text=status)
        self.root.update_idletasks()

    def _update_kpi_counters(self):
        if not self.row_widgets:
            self.kpi_total_chip["val"].config(text="0")
            self.kpi_correct_chip["val"].config(text="0")
            self.kpi_amend_chip["val"].config(text="0")
            self.kpi_clarify_chip["val"].config(text="0")
            self.kpi_info_chip["val"].config(text="0")
            return

        total = len(self.row_widgets)
        correct = 0
        amend = 0
        clarify = 0
        info = 0

        for rw in self.row_widgets:
            v = rw.verdict_var.get()
            if v == "Correct / In Order":
                correct += 1
            elif v == "Requires Amendment":
                amend += 1
            elif v == "Needs Clarification":
                clarify += 1
            elif v == "Informational / Not Applicable":
                info += 1

        self.kpi_total_chip["val"].config(text=str(total))
        self.kpi_correct_chip["val"].config(text=str(correct))
        self.kpi_amend_chip["val"].config(text=str(amend))
        self.kpi_clarify_chip["val"].config(text=str(clarify))
        self.kpi_info_chip["val"].config(text=str(info))

    # ------------------------------------------------------------------
    # Bottom Actions & Export Hub (Always Visible & Prominent)
    # ------------------------------------------------------------------
    def _build_workspace_bottom_bar(self):
        outer = tk.Frame(self.tab_workspace, bg=COLOR_SKY_LIGHT, pady=3)
        outer.pack(side="bottom", fill="x", padx=4)

        # Card 1: Download Complete Analysis (Word / PDF)
        c1 = tk.Frame(outer, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER_BLUE, highlightthickness=1, padx=10, pady=6)
        c1.pack(side="left", fill="both", expand=True, padx=(0, 4))

        tk.Label(c1, text="⬇ Download Complete Analysis", bg=COLOR_CARD_BG, fg=COLOR_PRIMARY_NAVY, font=self.font_heading).pack(anchor="w")

        f_row = tk.Frame(c1, bg=COLOR_CARD_BG, pady=2)
        f_row.pack(anchor="w")

        tk.Radiobutton(
            f_row, text="Word (.docx)", variable=self.export_format_var, value="word",
            bg=COLOR_CARD_BG, font=self.font_body,
        ).pack(side="left", padx=(0, 6))

        tk.Radiobutton(
            f_row, text="PDF", variable=self.export_format_var, value="pdf",
            bg=COLOR_CARD_BG, font=self.font_body,
        ).pack(side="left", padx=(0, 8))

        self.download_btn = ttk.Button(
            f_row, text="⬇ Download Full Analysis", style="Action.TButton",
            command=self.on_download, state="disabled",
        )
        self.download_btn.pack(side="left")

        self.download_status_label = tk.Label(
            c1, text="Run Analyze first to enable download.", bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8),
        )
        self.download_status_label.pack(anchor="w", pady=(1, 0))

        # Card 2: Finalize & Generate Sign-off Documents (Finalized Summary & Amendment Request)
        c2 = tk.Frame(outer, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER_BLUE, highlightthickness=1, padx=10, pady=6)
        c2.pack(side="left", fill="both", expand=True, padx=(0, 4))

        tk.Label(c2, text="📋 Finalize & Issue Documents", bg=COLOR_CARD_BG, fg=COLOR_PRIMARY_NAVY, font=self.font_heading).pack(anchor="w")

        b_row = tk.Frame(c2, bg=COLOR_CARD_BG, pady=2)
        b_row.pack(anchor="w")

        self.finalize_btn = ttk.Button(
            b_row, text="📋 Download Finalized Summary (Word)", style="Secondary.TButton",
            command=self.on_download_final_summary, state="disabled",
        )
        self.finalize_btn.pack(side="left", padx=(0, 6))

        self.amendment_btn = ttk.Button(
            b_row, text="✉ Issue Amendment Request (Word)", style="Danger.TButton",
            command=self.on_generate_amendment_letter, state="disabled",
        )
        self.amendment_btn.pack(side="left")

        self.finalize_status_label = tk.Label(
            c2, text="Complete review above before generating final docs.", bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8),
        )
        self.finalize_status_label.pack(anchor="w", pady=(1, 0))

        # Card 3: Database Persistence
        c3 = tk.Frame(outer, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER_BLUE, highlightthickness=1, padx=10, pady=6)
        c3.pack(side="left", fill="both", expand=True)

        tk.Label(c3, text="💾 Database Persistence", bg=COLOR_CARD_BG, fg=COLOR_PRIMARY_NAVY, font=self.font_heading).pack(anchor="w")

        db_row = tk.Frame(c3, bg=COLOR_CARD_BG, pady=2)
        db_row.pack(anchor="w")

        self.bottom_save_btn = ttk.Button(
            db_row, text="💾 Save / Sync Record", style="Success.TButton",
            command=self.on_save_to_database, state="disabled",
        )
        self.bottom_save_btn.pack(side="left", padx=(0, 6))

        ttk.Button(
            db_row, text="🔍 Search History", style="Secondary.TButton",
            command=lambda: self.main_notebook.select(self.tab_database),
        ).pack(side="left")

        self.db_save_status_label = tk.Label(
            c3, text="Not saved in database yet.", bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8),
        )
        self.db_save_status_label.pack(anchor="w", pady=(1, 0))

    # ------------------------------------------------------------------
    # Workspace Body: Sections Notebook (Left) + Clause Viewer (Right)
    # ------------------------------------------------------------------
    def _build_workspace_body(self):
        self.paned = ttk.PanedWindow(self.tab_workspace, orient="horizontal")
        self.paned.pack(side="top", fill="both", expand=True, padx=4, pady=(2, 3))

        # Left Notebook for Analysis Sections
        self.left_frame = ttk.Frame(self.paned)
        self.paned.add(self.left_frame, weight=3)

        self.notebook = ttk.Notebook(self.left_frame)
        self.notebook.pack(fill="both", expand=True)

        for section in (SECTION_MAIN_SUMMARY, SECTION_GOODS, SECTION_DOCUMENTS, SECTION_CHARGES):
            tab = ttk.Frame(self.notebook, style="Sky.TFrame")
            self.notebook.add(tab, text=f"  {section}  ")
            self.section_tab_frames[section] = tab

        # Right Frame: Modern Clause & Raw Text Viewer
        self.right_frame = tk.Frame(self.paned, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER, highlightthickness=1)
        self.paned.add(self.right_frame, weight=2)

        # Viewer Header
        v_header = tk.Frame(self.right_frame, bg=COLOR_PRIMARY_NAVY, padx=10, pady=5)
        v_header.pack(side="top", fill="x")

        tk.Label(
            v_header, text="🔍 Clause & Document Text Viewer",
            bg=COLOR_PRIMARY_NAVY, fg="#FFFFFF", font=self.font_heading,
        ).pack(side="left")

        self.clause_title_frame = tk.Frame(self.right_frame, bg="#F1F5F9", padx=10, pady=5)
        self.clause_title_frame.pack(side="top", fill="x")

        self.clause_title_label = tk.Label(
            self.clause_title_frame,
            text="Select 'View' on any clause to inspect its original verbatim text.",
            bg="#F1F5F9", fg=COLOR_PRIMARY_NAVY, font=self.font_bold, wraplength=420, justify="left",
        )
        self.clause_title_label.pack(anchor="w")

        # Text Display Area
        text_frame = tk.Frame(self.right_frame, bg=COLOR_CARD_BG, padx=6, pady=4)
        text_frame.pack(fill="both", expand=True)

        yscroll = ttk.Scrollbar(text_frame, orient="vertical")
        self.clause_text = tk.Text(
            text_frame, wrap="word", yscrollcommand=yscroll.set, state="disabled",
            font=self.font_mono, bg="#F8FAFC", fg="#0F172A", relief="solid", borderwidth=1,
            padx=8, pady=8,
        )
        yscroll.config(command=self.clause_text.yview)
        self.clause_text.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        # Bottom Action buttons in Viewer
        v_actions = tk.Frame(self.right_frame, bg=COLOR_CARD_BG, padx=8, pady=5)
        v_actions.pack(side="bottom", fill="x")

        ttk.Button(
            v_actions, text="📄 Show Full Document Text", style="Secondary.TButton",
            command=self.show_full_document,
        ).pack(side="left", padx=(0, 6))

        ttk.Button(
            v_actions, text="📋 Copy Text", style="Secondary.TButton",
            command=self.on_copy_clause_text,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # TAB 2: DATABASE SEARCH & RETRIEVAL DASHBOARD
    # ------------------------------------------------------------------
    def _build_database_tab(self):
        # 1. Search Filter Box (packed top)
        search_card = tk.Frame(
            self.tab_database, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER,
            highlightthickness=1, padx=12, pady=8,
        )
        search_card.pack(side="top", fill="x", padx=4, pady=(2, 4))

        tk.Label(
            search_card, text="🔍 Search & Filter Historical LC Analysis Records",
            bg=COLOR_CARD_BG, fg=COLOR_PRIMARY_NAVY, font=self.font_title,
        ).pack(anchor="w", pady=(0, 4))

        # Inputs Grid
        grid_frame = tk.Frame(search_card, bg=COLOR_CARD_BG)
        grid_frame.pack(fill="x", pady=2)

        # Row 0: LC Number and Issuer / Applicant Bank
        tk.Label(grid_frame, text="Documentary Credit No. (LC No):", bg=COLOR_CARD_BG, font=self.font_bold).grid(row=0, column=0, sticky="w", padx=6, pady=2)
        e_lc = ttk.Entry(grid_frame, textvariable=self.search_lc_no_var, width=28)
        e_lc.grid(row=0, column=1, sticky="w", padx=6, pady=2)
        e_lc.bind("<Return>", lambda e: self.on_search_database())

        tk.Label(grid_frame, text="Applicant Bank Name:", bg=COLOR_CARD_BG, font=self.font_bold).grid(row=0, column=2, sticky="w", padx=12, pady=2)
        e_iss = ttk.Entry(grid_frame, textvariable=self.search_issuer_var, width=32)
        e_iss.grid(row=0, column=3, sticky="w", padx=6, pady=2)
        e_iss.bind("<Return>", lambda e: self.on_search_database())

        # Row 1: Amount and Beneficiary
        tk.Label(grid_frame, text="LC Amount / Currency:", bg=COLOR_CARD_BG, font=self.font_bold).grid(row=1, column=0, sticky="w", padx=6, pady=2)
        e_amt = ttk.Entry(grid_frame, textvariable=self.search_amount_var, width=28)
        e_amt.grid(row=1, column=1, sticky="w", padx=6, pady=2)
        e_amt.bind("<Return>", lambda e: self.on_search_database())

        tk.Label(grid_frame, text="Beneficiary Name:", bg=COLOR_CARD_BG, font=self.font_bold).grid(row=1, column=2, sticky="w", padx=12, pady=2)
        e_ben = ttk.Entry(grid_frame, textvariable=self.search_beneficiary_var, width=32)
        e_ben.grid(row=1, column=3, sticky="w", padx=6, pady=2)
        e_ben.bind("<Return>", lambda e: self.on_search_database())

        # Row 2: General Query + Action Buttons
        tk.Label(grid_frame, text="General Search Term:", bg=COLOR_CARD_BG, font=self.font_bold).grid(row=2, column=0, sticky="w", padx=6, pady=2)
        e_gen = ttk.Entry(grid_frame, textvariable=self.search_general_var, width=28)
        e_gen.grid(row=2, column=1, sticky="w", padx=6, pady=2)
        e_gen.bind("<Return>", lambda e: self.on_search_database())

        btn_box = tk.Frame(grid_frame, bg=COLOR_CARD_BG)
        btn_box.grid(row=2, column=2, columnspan=2, sticky="w", padx=12, pady=2)

        ttk.Button(btn_box, text="🔍 Search Records", style="Primary.TButton", command=self.on_search_database).pack(side="left", padx=(0, 6))
        ttk.Button(btn_box, text="🔄 Reset / Show All", style="Secondary.TButton", command=self.on_reset_search).pack(side="left", padx=(0, 6))

        # 2. Database Records Table Card
        table_card = tk.Frame(
            self.tab_database, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER,
            highlightthickness=1, padx=10, pady=8,
        )
        table_card.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        # Table Header & Controls (packed top of table card)
        t_header = tk.Frame(table_card, bg=COLOR_CARD_BG)
        t_header.pack(side="top", fill="x", pady=(0, 4))

        self.db_count_label = tk.Label(
            t_header, text="Saved Analysis (0 found)", bg=COLOR_CARD_BG, fg=COLOR_PRIMARY_NAVY, font=self.font_heading,
        )
        self.db_count_label.pack(side="left")

        tk.Label(
            t_header, text="💡 Tip: Double-click any record to load it directly into the Workspace",
            bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, font=("Segoe UI", 8, "italic"),
        ).pack(side="right")

        # 3. Action Toolbar below table - PACKED BOTTOM FIRST inside table_card so it is NEVER clipped!
        action_bar = tk.Frame(table_card, bg=COLOR_CARD_BG, pady=6)
        action_bar.pack(side="bottom", fill="x")

        self.load_record_btn = ttk.Button(
            action_bar, text="📂 Load into Workspace", style="Primary.TButton",
            command=self.on_load_selected_database_record, state="disabled",
        )
        self.load_record_btn.pack(side="left", padx=(0, 8))

        self.delete_record_btn = ttk.Button(
            action_bar, text="🗑️ Delete Selected Record", style="Danger.TButton",
            command=self.on_delete_selected_record, state="disabled",
        )
        self.delete_record_btn.pack(side="left", padx=(0, 8))

        self.db_quick_export_summary_btn = ttk.Button(
            action_bar, text="📋 Export Final Summary", style="Secondary.TButton",
            command=self.on_db_export_summary, state="disabled",
        )
        self.db_quick_export_summary_btn.pack(side="left", padx=(0, 8))

        self.db_quick_export_amend_btn = ttk.Button(
            action_bar, text="✉ Export Amendment Letter", style="Secondary.TButton",
            command=self.on_db_export_amendment, state="disabled",
        )
        self.db_quick_export_amend_btn.pack(side="left")

        # Treeview Table - PACKED EXPAND=TRUE LAST so action_bar has guaranteed space
        tree_frame = tk.Frame(table_card, bg=COLOR_CARD_BG)
        tree_frame.pack(side="top", fill="both", expand=True)

        columns = ("id", "dc_number", "issuer", "beneficiary", "amount", "lc_type", "points", "amendments", "status", "updated_at")
        self.db_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        self.db_tree.heading("id", text="ID")
        self.db_tree.heading("dc_number", text="LC Number (DC No)")
        self.db_tree.heading("issuer", text="Applicant Bank Name")
        self.db_tree.heading("beneficiary", text="Beneficiary Name")
        self.db_tree.heading("amount", text="LC Amount")
        self.db_tree.heading("lc_type", text="LC Type")
        self.db_tree.heading("points", text="Points")
        self.db_tree.heading("amendments", text="Amendments")
        self.db_tree.heading("status", text="Status")
        self.db_tree.heading("updated_at", text="Saved Date")

        self.db_tree.column("id", width=40, anchor="center")
        self.db_tree.column("dc_number", width=140, anchor="w")
        self.db_tree.column("issuer", width=190, anchor="w")
        self.db_tree.column("beneficiary", width=190, anchor="w")
        self.db_tree.column("amount", width=120, anchor="e")
        self.db_tree.column("lc_type", width=110, anchor="center")
        self.db_tree.column("points", width=55, anchor="center")
        self.db_tree.column("amendments", width=85, anchor="center")
        self.db_tree.column("status", width=130, anchor="w")
        self.db_tree.column("updated_at", width=130, anchor="center")

        tree_vscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.db_tree.yview)
        tree_hscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.db_tree.xview)
        self.db_tree.configure(yscrollcommand=tree_vscroll.set, xscrollcommand=tree_hscroll.set)

        self.db_tree.pack(side="left", fill="both", expand=True)
        tree_vscroll.pack(side="right", fill="y")
        tree_hscroll.pack(side="bottom", fill="x")

        self.db_tree.bind("<Double-1>", lambda e: self.on_load_selected_database_record())
        self.db_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _on_main_tab_changed(self, event):
        selected_tab = self.main_notebook.index(self.main_notebook.select())
        if selected_tab == 1:  # Database tab
            self.on_search_database()

    def _on_tree_select(self, event):
        selected = self.db_tree.selection()
        has_sel = bool(selected)
        state = "normal" if has_sel else "disabled"
        self.load_record_btn.config(state=state)
        self.delete_record_btn.config(state=state)
        self.db_quick_export_summary_btn.config(state=state)
        self.db_quick_export_amend_btn.config(state=state)

    def on_search_database(self):
        records = database.search_analyses(
            lc_no=self.search_lc_no_var.get(),
            issuer=self.search_issuer_var.get(),
            amount=self.search_amount_var.get(),
            beneficiary=self.search_beneficiary_var.get(),
            general_query=self.search_general_var.get(),
        )

        for item in self.db_tree.get_children():
            self.db_tree.delete(item)

        for r in records:
            bank_display = r.get("applicant_bank_name") or r.get("issuer_name") or "(Not detected)"
            ben_display = r.get("beneficiary_name") or "(Not detected)"
            self.db_tree.insert(
                "", "end", values=(
                    r["id"],
                    r["dc_number"] or "(None)",
                    bank_display,
                    ben_display,
                    r["amount_text"] or "(None)",
                    r["lc_type"] or "Draft LC",
                    r["total_points"],
                    r["amendment_count"],
                    r["status"],
                    r["updated_at"],
                )
            )

        self.db_count_label.config(text=f"Saved Analysis ({len(records)} found)")
        self._on_tree_select(None)

    def on_reset_search(self):
        self.search_lc_no_var.set("")
        self.search_issuer_var.set("")
        self.search_amount_var.set("")
        self.search_beneficiary_var.set("")
        self.search_general_var.set("")
        self.on_search_database()

    def _get_selected_record_id(self) -> Optional[int]:
        selected = self.db_tree.selection()
        if not selected:
            return None
        values = self.db_tree.item(selected[0], "values")
        return int(values[0]) if values else None

    def on_load_selected_database_record(self):
        rec_id = self._get_selected_record_id()
        if not rec_id:
            messagebox.showwarning("Database", "Please select a record from the table to load.")
            return

        loaded = database.get_analysis_by_id(rec_id)
        if not loaded:
            messagebox.showerror("Database", f"Record #{rec_id} could not be found.")
            return

        res, meta = loaded
        self.result = res
        self.current_record_id = rec_id
        self.selected_file = meta.get("source_filename") or "Database_Record.pdf"
        self.file_label.config(text=f"💾 DB #{rec_id}: {self.selected_file}")
        self.lc_type_var.set(res.lc_type)

        self._render_result()
        self._set_progress(100, f"Loaded record #{rec_id} from database")

        self.active_record_badge.config(text=f"DB Record #{rec_id} Loaded")
        self.download_btn.config(state="normal")
        self.download_status_label.config(
            text=f"Ready - {len(res.clauses)} points loaded. Export to Word or PDF.",
            fg=COLOR_VERDICT_CORRECT,
        )
        self.top_save_btn.config(state="normal")
        self.bottom_save_btn.config(state="normal")
        self.db_save_status_label.config(
            text=f"Synced with Database Record #{rec_id}",
            fg=COLOR_VERDICT_CORRECT,
        )
        self._refresh_finalize_controls_state()

        # Switch back to workspace tab
        self.main_notebook.select(self.tab_workspace)
        messagebox.showinfo("Record Loaded", f"Successfully loaded LC Analysis #{rec_id} ({res.dc_number or 'Draft'}).")

    def on_delete_selected_record(self):
        rec_id = self._get_selected_record_id()
        if not rec_id:
            messagebox.showwarning("Delete Record", "Please select a record from the table to delete.")
            return

        # Exact warning prompt required by user
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            "Do You Really Want To Delete Record - if you proceed record will be permanently deleted.",
        )
        if not confirm:
            return

        if database.delete_analysis(rec_id):
            if self.current_record_id == rec_id:
                self.current_record_id = None
                self.active_record_badge.config(text="New Session")
                self.db_save_status_label.config(text="Record deleted.", fg=COLOR_VERDICT_AMEND)
            self.on_search_database()
            messagebox.showinfo("Deleted", "Record has been permanently deleted from database.")
        else:
            messagebox.showerror("Error", "Could not delete record from database.")

    def on_db_export_summary(self):
        rec_id = self._get_selected_record_id()
        if not rec_id:
            return
        loaded = database.get_analysis_by_id(rec_id)
        if not loaded:
            return
        res, _ = loaded
        path = filedialog.asksaveasfilename(
            title="Save Finalized Summary", defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")], initialfile=f"LC_Finalized_Summary_{res.dc_number or rec_id}.docx",
        )
        if not path:
            return
        try:
            exporter.export_final_summary_word(res, path)
            messagebox.showinfo("Export Successful", f"Saved finalized summary to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def on_db_export_amendment(self):
        rec_id = self._get_selected_record_id()
        if not rec_id:
            return
        loaded = database.get_analysis_by_id(rec_id)
        if not loaded:
            return
        res, _ = loaded
        amend_clauses = [c for c in res.clauses if c.effective_verdict() == "Requires Amendment"]
        if not amend_clauses:
            messagebox.showinfo("Amendment Letter", "This record has no points marked 'Requires Amendment'.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Amendment Request Letter", defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")], initialfile=f"LC_Amendment_Request_Letter_{res.dc_number or rec_id}.docx",
        )
        if not path:
            return
        try:
            exporter.generate_amendment_letter(res, path, amend_clauses)
            messagebox.showinfo("Export Successful", f"Saved amendment letter to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    # ------------------------------------------------------------------
    # Actions & Analysis Pipeline
    # ------------------------------------------------------------------
    def on_select_file(self):
        path = filedialog.askopenfilename(title="Select LC Copy", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.selected_file = path
            self.file_label.config(text=os.path.basename(path))

    def on_refresh(self):
        self.selected_file = None
        self.current_record_id = None
        self.file_label.config(text="No PDF selected")
        self.active_record_badge.config(text="New Session")
        self.lc_type_var.set("")
        self.result = None
        self.row_widgets = []
        self._set_progress(0, "Ready")
        self._update_kpi_counters()

        for tab in self.section_tab_frames.values():
            for child in tab.winfo_children():
                child.destroy()

        self.clause_text.config(state="normal")
        self.clause_text.delete("1.0", "end")
        self.clause_text.config(state="disabled")
        self.clause_title_label.config(text="Select 'View' on any clause to inspect its original verbatim text.")
        self.export_format_var.set("word")

        self.download_btn.config(state="disabled")
        self.download_status_label.config(text="Run Analyze first to enable download.", fg=COLOR_TEXT_MUTED)
        self.finalize_btn.config(state="disabled")
        self.amendment_btn.config(state="disabled")
        self.finalize_status_label.config(text="Complete review above before generating final docs.", fg=COLOR_TEXT_MUTED)
        self.top_save_btn.config(state="disabled")
        self.bottom_save_btn.config(state="disabled")
        self.db_save_status_label.config(text="Not saved in database yet.", fg=COLOR_TEXT_MUTED)

    def on_analyze(self):
        if not self.selected_file:
            messagebox.showwarning("LC Analyser", "Please select an LC copy (PDF) first.")
            return
        if not self.lc_type_var.get():
            messagebox.showwarning("LC Analyser", "Please select whether this is a Draft LC or an Issued / Transmitted LC.")
            return

        try:
            self._set_progress(10, "Reading PDF document...")
            raw_text = pdf_extract.extract_text(self.selected_file)

            self._set_progress(30, "Cleaning extracted text...")
            text = pdf_extract.normalise_text(raw_text)

            self._set_progress(50, "Validating LC document structure...")
            declared = "draft" if self.lc_type_var.get() == LC_TYPE_DRAFT else "issued"
            classification = lc_parser.classify_document(text, declared)
            if not classification.is_lc:
                self._set_progress(0, "Ready")
                messagebox.showerror("LC Validation Failed", classification.reason)
                return

            self._set_progress(70, "Extracting clauses and field tags...")
            fields = lc_parser.extract_fields(text)

            self._set_progress(85, "Executing UCP 600 rule-based checklist engine...")
            clauses = rules_engine.build_clause_points(fields, declared)

            self.result = AnalysisResult(
                lc_type=self.lc_type_var.get(),
                dc_number=classification.dc_number,
                source_filename=os.path.basename(self.selected_file),
                full_text=text,
                clauses=clauses,
            )

            self._set_progress(95, "Rendering summary interface...")
            self._render_result()
            self._set_progress(100, f"Analysis complete — {len(clauses)} points evaluated.")

            # Auto-save to database
            self.current_record_id = database.save_or_update_analysis(self.result, self.current_record_id)
            self.active_record_badge.config(text=f"DB Record #{self.current_record_id}")
            self.db_save_status_label.config(
                text=f"Auto-saved to Database as Record #{self.current_record_id}",
                fg=COLOR_VERDICT_CORRECT,
            )

            self.download_btn.config(state="normal")
            self.download_status_label.config(
                text=f"Ready - {len(clauses)} points analysed. Choose format and download.",
                fg=COLOR_VERDICT_CORRECT,
            )
            self.top_save_btn.config(state="normal")
            self.bottom_save_btn.config(state="normal")
            self._refresh_finalize_controls_state()
            self.finalize_status_label.config(
                text="Review/edit verdicts and remarks above, then finalize below.",
                fg=COLOR_VERDICT_CORRECT,
            )

        except (pdf_extract.PDFExtractError, pdf_extract.PDFTextNotFoundError) as exc:
            self._set_progress(0, "Ready")
            self.download_btn.config(state="disabled")
            self.download_status_label.config(text="Analysis failed.", fg=COLOR_VERDICT_AMEND)
            self.finalize_btn.config(state="disabled")
            self.amendment_btn.config(state="disabled")
            messagebox.showerror("PDF Processing Error", str(exc))
        except Exception as exc:
            self._set_progress(0, "Ready")
            self.download_btn.config(state="disabled")
            self.download_status_label.config(text="Analysis failed.", fg=COLOR_VERDICT_AMEND)
            self.finalize_btn.config(state="disabled")
            self.amendment_btn.config(state="disabled")
            messagebox.showerror("Unexpected Error", f"An error occurred while analysing the document:\n{exc}")

    def on_save_to_database(self):
        if not self.result:
            messagebox.showwarning("Database", "No active analysis to save. Run Analyze first.")
            return

        self._sync_row_widgets_to_clauses()
        try:
            self.current_record_id = database.save_or_update_analysis(self.result, self.current_record_id)
            self.active_record_badge.config(text=f"DB Record #{self.current_record_id}")
            self.db_save_status_label.config(
                text=f"Saved successfully to Database (Record #{self.current_record_id})",
                fg=COLOR_VERDICT_CORRECT,
            )
            messagebox.showinfo(
                "Database Save",
                f"Analysis successfully saved to database as Record #{self.current_record_id}.\n"
                f"LC No: {self.result.dc_number or 'Draft'}\n"
                f"Total Points: {len(self.result.clauses)}",
            )
        except Exception as exc:
            self.db_save_status_label.config(text="Database save failed.", fg=COLOR_VERDICT_AMEND)
            messagebox.showerror("Database Error", f"Could not save analysis to database:\n{exc}")

    def show_full_document(self):
        if not self.result:
            return
        self.clause_title_label.config(text="Verbatim Extracted Full Document Text")
        self._set_clause_text(self.result.full_text)

    def _set_clause_text(self, text: str):
        self.clause_text.config(state="normal")
        self.clause_text.delete("1.0", "end")
        self.clause_text.insert("1.0", text)
        self.clause_text.config(state="disabled")

    def on_view_clause(self, clause: ClausePoint):
        self.clause_title_label.config(text=f"Field {clause.point_no} — {clause.header}")
        self._set_clause_text(clause.raw_text or "(No original verbatim text captured for this point)")

    def on_copy_clause_text(self):
        text = self.clause_text.get("1.0", "end-1c")
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Copied", "Text copied to clipboard.")

    # ------------------------------------------------------------------
    # Rendering Results into Tabs
    # ------------------------------------------------------------------
    def _render_result(self):
        assert self.result is not None
        self.row_widgets = []
        self._render_simple_section(SECTION_MAIN_SUMMARY)
        self._render_simple_section(SECTION_GOODS)
        self._render_documents_section()
        self._render_simple_section(SECTION_CHARGES)
        self._update_kpi_counters()

    def _render_simple_section(self, section: str):
        tab = self.section_tab_frames[section]
        for child in tab.winfo_children():
            child.destroy()
        clauses = self.result.by_section(section)
        scroll_frame = self._make_scrollable(tab)
        self._render_header_row(scroll_frame)
        if not clauses:
            tk.Label(
                scroll_frame, text="No points identified under this section.",
                bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, font=self.font_body, padx=12, pady=10,
            ).grid(row=1, column=0, columnspan=8, sticky="w")
            return
        for i, clause in enumerate(clauses, start=1):
            self._render_clause_row(scroll_frame, clause, i)

    def _render_documents_section(self):
        tab = self.section_tab_frames[SECTION_DOCUMENTS]
        for child in tab.winfo_children():
            child.destroy()
        sub_notebook = ttk.Notebook(tab)
        sub_notebook.pack(fill="both", expand=True, padx=2, pady=2)
        doc_clauses = self.result.by_section(SECTION_DOCUMENTS)
        for sub in SUBSECTION_ORDER:
            sub_tab = ttk.Frame(sub_notebook, style="Sky.TFrame")
            sub_notebook.add(sub_tab, text=f" {sub} ")
            sub_clauses = [c for c in doc_clauses if c.subsection == sub]
            scroll_frame = self._make_scrollable(sub_tab)
            self._render_header_row(scroll_frame)
            if not sub_clauses:
                tk.Label(
                    scroll_frame, text="No items identified under this category.",
                    bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, font=self.font_body, padx=12, pady=10,
                ).grid(row=1, column=0, columnspan=8, sticky="w")
                continue
            for i, clause in enumerate(sub_clauses, start=1):
                self._render_clause_row(scroll_frame, clause, i)

    def _make_scrollable(self, parent) -> tk.Frame:
        canvas = tk.Canvas(parent, highlightthickness=0, bg=COLOR_CARD_BG)
        vscroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=COLOR_CARD_BG)

        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _on_canvas_configure(e):
            canvas.itemconfig(window_id, width=e.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.configure(yscrollcommand=vscroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        return frame

    def _render_header_row(self, parent: tk.Frame):
        headers = [
            ("Sl No.", 50),
            ("Point No.", 85),
            ("Point Header", 170),
            ("Summary Text", 260),
            ("Rule-Engine Compliance Analysis", 260),
            ("Your Final Verdict", 210),
            ("Your Remarks / Amendment Notes", 220),
            ("Action", 70),
        ]
        h_frame = tk.Frame(parent, bg=COLOR_PRIMARY_NAVY, padx=4, pady=5)
        h_frame.grid(row=0, column=0, columnspan=8, sticky="ew")

        for col, (text, w) in enumerate(headers):
            tk.Label(
                h_frame, text=text, bg=COLOR_PRIMARY_NAVY, fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"), anchor="w",
            ).grid(row=0, column=col, sticky="w", padx=6, pady=2)

    def _render_clause_row(self, parent: tk.Frame, clause: ClausePoint, row: int):
        bg_color = "#FFFFFF" if row % 2 == 1 else "#F8FAFC"

        row_frame = tk.Frame(parent, bg=bg_color, highlightbackground="#E2E8F0", highlightthickness=1, padx=4, pady=5)
        row_frame.grid(row=row, column=0, columnspan=8, sticky="ew", pady=1)

        # 0. Sl No
        tk.Label(row_frame, text=str(clause.sl_no), width=4, bg=bg_color, fg=COLOR_TEXT_MUTED, font=self.font_bold).grid(row=0, column=0, sticky="nw", padx=4, pady=3)

        # 1. Point No
        tk.Label(row_frame, text=clause.point_no, width=9, bg=bg_color, fg=COLOR_PRIMARY_NAVY, font=self.font_bold, wraplength=75).grid(row=0, column=1, sticky="nw", padx=4, pady=3)

        # 2. Header
        tk.Label(row_frame, text=clause.header, width=18, bg=bg_color, fg=COLOR_TEXT_MAIN, font=self.font_bold, wraplength=145, justify="left").grid(row=0, column=2, sticky="nw", padx=4, pady=3)

        # 3. Summary
        tk.Label(row_frame, text=clause.summary, width=28, bg=bg_color, fg=COLOR_TEXT_MAIN, font=self.font_body, wraplength=225, justify="left").grid(row=0, column=3, sticky="nw", padx=4, pady=3)

        # 4. Analysis Note
        tk.Label(row_frame, text=clause.analysis_note, width=28, bg=bg_color, fg="#1E40AF", font=self.font_body, wraplength=225, justify="left").grid(row=0, column=4, sticky="nw", padx=4, pady=3)

        # 5. Verdict Radio Buttons
        initial_verdict = clause.user_verdict or clause.suggested_verdict or VERDICT_OPTIONS[0]
        verdict_var = tk.StringVar(value=initial_verdict)
        verdict_var.trace_add("write", lambda *args: self._on_verdict_changed())

        v_box = tk.Frame(row_frame, bg=bg_color)
        v_box.grid(row=0, column=5, sticky="nw", padx=4, pady=1)

        for opt in VERDICT_OPTIONS:
            rb_fg = COLOR_TEXT_MAIN
            if opt == "Correct / In Order":
                rb_fg = COLOR_VERDICT_CORRECT
            elif opt == "Requires Amendment":
                rb_fg = COLOR_VERDICT_AMEND
            elif opt == "Needs Clarification":
                rb_fg = COLOR_VERDICT_CLARIFY

            tk.Radiobutton(
                v_box, text=opt, variable=verdict_var, value=opt,
                bg=bg_color, fg=rb_fg, activebackground=bg_color,
                font=("Segoe UI", 8, "bold" if opt == initial_verdict else "normal"),
            ).pack(anchor="w", pady=1)

        # 6. Remarks Box
        remarks_var = tk.StringVar(value=clause.user_remarks or "")
        remarks_entry = ttk.Entry(row_frame, textvariable=remarks_var, width=24)
        remarks_entry.grid(row=0, column=6, sticky="nw", padx=4, pady=3)

        # 7. View Button
        ttk.Button(
            row_frame, text="👁 View", width=7, style="Secondary.TButton",
            command=lambda c=clause: self.on_view_clause(c),
        ).grid(row=0, column=7, sticky="nw", padx=4, pady=3)

        self.row_widgets.append(RowWidgets(clause, verdict_var, remarks_var, row_frame))

    def _on_verdict_changed(self):
        self._refresh_finalize_controls_state()
        self._update_kpi_counters()

    # ------------------------------------------------------------------
    # Export Handlers
    # ------------------------------------------------------------------
    def _sync_row_widgets_to_clauses(self):
        """Copies live GUI state back onto ClausePoint objects."""
        for rw in self.row_widgets:
            rw.clause.user_verdict = rw.verdict_var.get()
            rw.clause.user_remarks = rw.remarks_var.get()

    def _refresh_finalize_controls_state(self):
        if not self.result or not self.row_widgets:
            self.finalize_btn.config(state="disabled")
            self.amendment_btn.config(state="disabled")
            return
        self.finalize_btn.config(state="normal")
        has_amendment = any(rw.verdict_var.get() == "Requires Amendment" for rw in self.row_widgets)
        self.amendment_btn.config(state="normal" if has_amendment else "disabled")

    def on_download_final_summary(self):
        """Downloads the finalized single Word file: all points grouped by verdict."""
        if not self.result:
            messagebox.showwarning("LC Analyser", "Please run Analyze first.")
            return
        self._sync_row_widgets_to_clauses()
        path = filedialog.asksaveasfilename(
            title="Save Finalized Summary", defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")], initialfile="LC_Finalized_Summary.docx",
        )
        if not path:
            return
        try:
            exporter.export_final_summary_word(self.result, path)
            self.finalize_status_label.config(text=f"Finalized summary saved: {os.path.basename(path)}", fg=COLOR_VERDICT_CORRECT)
            messagebox.showinfo("Export Completed", f"Finalized summary saved to:\n{path}")
        except Exception as exc:
            self.finalize_status_label.config(text="Finalize failed.", fg=COLOR_VERDICT_AMEND)
            messagebox.showerror("Export Error", f"Could not save finalized summary:\n{exc}")

    def on_generate_amendment_letter(self):
        """Drafts formal amendment request letter to Applicant / Opener of LC."""
        if not self.result:
            messagebox.showwarning("LC Analyser", "Please run Analyze first.")
            return
        self._sync_row_widgets_to_clauses()
        amendment_clauses = [c for c in self.result.clauses if c.effective_verdict() == "Requires Amendment"]
        if not amendment_clauses:
            messagebox.showinfo(
                "No Amendments",
                "No points are currently marked 'Requires Amendment'. Mark at least one point "
                "for amendment and add your remarks before generating the letter.",
            )
            return
        dc_suffix = f"_{self.result.dc_number}" if self.result.dc_number else ""
        path = filedialog.asksaveasfilename(
            title="Save Amendment Request Letter", defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")], initialfile=f"LC_Amendment_Request_Letter{dc_suffix}.docx",
        )
        if not path:
            return
        try:
            exporter.generate_amendment_letter(self.result, path, amendment_clauses)
            self.finalize_status_label.config(text=f"Amendment letter saved: {os.path.basename(path)}", fg=COLOR_VERDICT_CORRECT)
            messagebox.showinfo("Export Completed", f"Amendment request letter saved to:\n{path}")
        except Exception as exc:
            self.finalize_status_label.config(text="Amendment generation failed.", fg=COLOR_VERDICT_AMEND)
            messagebox.showerror("Export Error", f"Could not generate amendment letter:\n{exc}")

    def on_download(self):
        """Downloads full section-wise analysis in Word or PDF."""
        if not self.result:
            messagebox.showwarning("LC Analyser", "Please run Analyze first.")
            return
        self.on_export(self.export_format_var.get())

    def on_export(self, fmt: str):
        if not self.result:
            return
        self._sync_row_widgets_to_clauses()

        if fmt == "word":
            path = filedialog.asksaveasfilename(
                title="Save Word Summary", defaultextension=".docx",
                filetypes=[("Word Document", "*.docx")], initialfile="LC_Analysis_Summary.docx",
            )
            if not path:
                return
            try:
                exporter.export_to_word(self.result, path)
                self.download_status_label.config(text=f"Downloaded: {os.path.basename(path)}", fg=COLOR_VERDICT_CORRECT)
                messagebox.showinfo("Export Completed", f"Complete analysis saved to:\n{path}")
            except Exception as exc:
                self.download_status_label.config(text="Download failed.", fg=COLOR_VERDICT_AMEND)
                messagebox.showerror("Export Error", f"Could not save Word file:\n{exc}")
        else:
            path = filedialog.asksaveasfilename(
                title="Save PDF Summary", defaultextension=".pdf",
                filetypes=[("PDF Document", "*.pdf")], initialfile="LC_Analysis_Summary.pdf",
            )
            if not path:
                return
            try:
                exporter.export_to_pdf(self.result, path)
                self.download_status_label.config(text=f"Downloaded: {os.path.basename(path)}", fg=COLOR_VERDICT_CORRECT)
                messagebox.showinfo("Export Completed", f"Complete analysis saved to:\n{path}")
            except Exception as exc:
                self.download_status_label.config(text="Download failed.", fg=COLOR_VERDICT_AMEND)
                messagebox.showerror("Export Error", f"Could not save PDF file:\n{exc}")


def main():
    root = tk.Tk()
    LCAnalyserApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
