"""Main application window.

All slow work (PDF reading, OCR, Gemini calls, model listing) runs on a
background thread. Workers post messages to a queue that the Tk main loop
polls, so the interface never freezes.
"""

from __future__ import annotations

import logging
import queue
import threading
import sys
import time
import tkinter.font as tkfont
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Callable

import customtkinter as ctk
from PIL import Image

from .. import APP_NAME
from ..analyzer import AnalysisResult, Analyzer
from ..config import (MAX_VIEW_FONT, MIN_VIEW_FONT, OCR_MODES, SUGGESTED_MODELS, AppSettings,
                      effective_temperature, register_path, save_settings)
from ..exporter import build_final_document, build_json, safe_filename, save_docx, save_json, save_pdf, save_text
from ..gemini_client import GeminiClient, GeminiError
from ..key_store import (KeyStoreError, delete_api_key, load_api_key, mask_key, save_api_key,
                         normalize_api_key, validate_api_key_format)
from ..pdf_processor import (CancelledError, DocumentInfo, PDFError, configure_tesseract, tesseract_available,
                             text_layer_ratio, validate_pdf)
from ..repository import RegisterError, Repository
from ..response_parser import EDITED_NOTE, TAB_GROUPS, apply_edit
from . import theme
from .widgets import Card, MarkdownView, bring_to_front

log = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parents[2] / "assets"
TABS = ("Full Report", *TAB_GROUPS.keys(), "Source Check")
EDITABLE_TABS = ("Full Report", *TAB_GROUPS.keys())

# The analysis always uses the detailed prompt, and OCR always uses English.
FIXED_DEPTH = "Detailed"
FIXED_OCR_LANGUAGE = "eng"
OCR_DOWNLOAD_URL = "https://github.com/UB-Mannheim/tesseract/wiki"

_PREFERRED_FONTS = ("Segoe UI", "Calibri", "Arial", "Cambria", "Georgia", "Times New Roman", "Verdana",
                    "Helvetica Neue", "Helvetica", "DejaVu Sans", "DejaVu Serif", "Liberation Sans",
                    "Liberation Serif")


def available_fonts(root) -> list[str]:
    """Readable fonts that are actually installed (theme default first)."""
    try:
        installed = set(tkfont.families(root))
    except Exception:
        installed = set()
    fonts = [f for f in _PREFERRED_FONTS if f in installed and f != theme.FONT_FAMILY]
    return [theme.FONT_FAMILY, *fonts]


class JudgmentAnalyzerApp(ctk.CTk):
    def __init__(self, settings: AppSettings, log_file: Path | None = None):
        super().__init__()
        self.settings = settings
        self.log_file = log_file
        self.document: DocumentInfo | None = None
        self.result: AnalysisResult | None = None
        self.cancel_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.ui_queue: queue.Queue = queue.Queue()
        self.busy = False
        self._started_at = 0.0
        self._repo: Repository | None = None

        ctk.set_appearance_mode(settings.appearance_mode)
        ctk.set_default_color_theme("blue")
        configure_tesseract(settings.tesseract_cmd)

        self.title(APP_NAME)
        self._fit_to_screen()
        self.configure(fg_color=theme.BG)
        self._set_icon()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_sidebar()
        self._build_main()
        self._load_saved_key()
        self._refresh_action_state()
        self.after(300, self.refresh_register_badge)
        if not settings.register_location_confirmed:
            self.after(700, self._ask_register_location)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_queue)

    # ================================================================ layout
    def _set_icon(self) -> None:
        try:
            from PIL import ImageTk

            self._icon_img = ImageTk.PhotoImage(Image.open(ASSETS / "logo_256.png"))
            self.iconphoto(True, self._icon_img)
        except Exception as exc:  # icon is cosmetic only
            log.debug("Icon not set: %s", exc)

    def _fit_to_screen(self) -> None:
        """Open at 1360x860 (logical units) or smaller so the window fits at any display scaling."""
        try:
            from customtkinter import ScalingTracker
            scale = ScalingTracker.get_window_scaling(self)
        except Exception:
            scale = 1.0
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = int(min(1360, sw * 0.96 / scale))
        h = int(min(860, sh * 0.88 / scale))
        self.geometry(f"{w}x{h}+0+0")
        self.minsize(min(900, w), min(600, h))
        if sys.platform.startswith("win") and (w < 1360 or h < 860):
            self.after(50, lambda: self.state("zoomed"))  # small/scaled screens: start maximised

    def _font(self, size=13, weight="normal"):
        return ctk.CTkFont(theme.FONT_FAMILY, size, weight)

    def _hint(self, parent, row, text):
        ctk.CTkLabel(parent, text=text, font=self._font(11), text_color=theme.MUTED, wraplength=320, justify="left",
                     anchor="w").grid(row=row, column=0, sticky="ew", padx=(46, 0))

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.NAVY, corner_radius=0, height=84)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        try:
            logo = ctk.CTkImage(Image.open(ASSETS / "logo_256.png"), size=(56, 56))
            ctk.CTkLabel(header, image=logo, text="").grid(row=0, column=0, rowspan=2, padx=(20, 12), pady=12)
        except Exception:
            ctk.CTkLabel(header, text="⚖", font=self._font(40), text_color=theme.GOLD).grid(
                row=0, column=0, rowspan=2, padx=(20, 12))
        ctk.CTkLabel(header, text=APP_NAME, font=self._font(26, "bold"), text_color=theme.GOLD,
                     anchor="w").grid(row=0, column=1, sticky="sw", pady=(14, 0))
        ctk.CTkLabel(header, text="AI-assisted analysis of judicial decisions  •  source-checked  •  precedent register"
                                  "  •  powered by Google Gemini",
                     font=self._font(13), text_color="#D6DBEA", anchor="w").grid(row=1, column=1, sticky="nw",
                                                                                 pady=(0, 14))
        self.register_badge = ctk.CTkButton(
            header, text="📚 Precedent register", font=self._font(12, "bold"), fg_color=theme.NAVY_2,
            hover_color=theme.PURPLE, text_color="#F0D27A", height=34, command=self.open_register)
        self.register_badge.grid(row=0, column=2, rowspan=2, padx=(20, 0))
        self.appearance = ctk.CTkSegmentedButton(
            header, values=["Light", "Dark"], command=self._change_appearance,
            selected_color=theme.PURPLE, selected_hover_color=theme.PURPLE_HOVER,
            unselected_color=theme.NAVY_2, unselected_hover_color=theme.NAVY_2, text_color=theme.WHITE)
        self.appearance.set("Dark" if self.settings.appearance_mode == "Dark" else "Light")
        self.appearance.grid(row=0, column=3, rowspan=2, padx=(20, 10))
        ctk.CTkButton(header, text="✕  Close", width=100, height=34, font=self._font(13, "bold"),
                      fg_color=theme.DANGER, hover_color=theme.DANGER_HOVER, text_color=theme.WHITE,
                      command=self._on_close).grid(row=0, column=4, rowspan=2, padx=(0, 20))

    def _build_sidebar(self) -> None:
        side = ctk.CTkScrollableFrame(self, width=372, fg_color="transparent")
        side.grid(row=1, column=0, sticky="nsew", padx=(14, 6), pady=14)
        side.grid_columnconfigure(0, weight=1)

        # --- 1. Document ---------------------------------------------------
        doc_card = Card(side, "1  •  Judicial Decision")
        doc_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        b = doc_card.body
        self.upload_btn = ctk.CTkButton(b, text="📄  Upload Judicial Decision PDF", height=42,
                                        font=self._font(14, "bold"), fg_color=theme.PURPLE,
                                        hover_color=theme.PURPLE_HOVER, command=self.choose_pdf)
        self.upload_btn.grid(row=0, column=0, sticky="ew", pady=(4, 10))
        self.doc_labels: dict[str, ctk.CTkLabel] = {}
        for i, key in enumerate(("File", "Size", "Pages", "Text layer")):
            row = ctk.CTkFrame(b, fg_color="transparent")
            row.grid(row=i + 1, column=0, sticky="ew")
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=f"{key}:", width=78, anchor="w", font=self._font(12, "bold"),
                         text_color=theme.MUTED).grid(row=0, column=0, sticky="nw")
            lbl = ctk.CTkLabel(row, text="—", anchor="w", justify="left", wraplength=250, font=self._font(12),
                               text_color=theme.TEXT)
            lbl.grid(row=0, column=1, sticky="w")
            self.doc_labels[key] = lbl

        # --- 2. Gemini API -------------------------------------------------
        api_card = Card(side, "2  •  Gemini API Settings")
        api_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        b = api_card.body
        ctk.CTkLabel(b, text="API key", anchor="w", font=self._font(12, "bold"), text_color=theme.MUTED).grid(
            row=0, column=0, sticky="w")
        key_row = ctk.CTkFrame(b, fg_color="transparent")
        key_row.grid(row=1, column=0, sticky="ew")
        key_row.grid_columnconfigure(0, weight=1)
        self.key_var = ctk.StringVar()
        self.key_entry = ctk.CTkEntry(key_row, textvariable=self.key_var, show="•", height=34,
                                      placeholder_text="Paste your Gemini API key", fg_color=theme.ENTRY_BG)
        self.key_entry.grid(row=0, column=0, sticky="ew")
        self.show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(key_row, text="Show", width=60, variable=self.show_key_var, command=self._toggle_key,
                        fg_color=theme.PURPLE, hover_color=theme.PURPLE_HOVER).grid(row=0, column=1, padx=(8, 0))
        self.key_status = ctk.CTkLabel(b, text="", anchor="w", justify="left", wraplength=320, font=self._font(11),
                                       text_color=theme.MUTED)
        self.key_status.grid(row=2, column=0, sticky="ew", pady=(2, 4))
        self.remember_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(b, text="Remember key securely on this computer", variable=self.remember_var,
                        fg_color=theme.PURPLE, hover_color=theme.PURPLE_HOVER, font=self._font(12)).grid(
            row=3, column=0, sticky="w", pady=(2, 8))
        btns = ctk.CTkFrame(b, fg_color="transparent")
        btns.grid(row=4, column=0, sticky="ew")
        btns.grid_columnconfigure((0, 1), weight=1)
        self.test_btn = ctk.CTkButton(btns, text="Test API Key", fg_color=theme.BTN_NAVY, hover_color=theme.BTN_NAVY_HOVER,
                                      command=self.test_api_key)
        self.test_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(btns, text="Forget Saved Key", fg_color="transparent", border_width=1,
                      border_color=theme.CARD_BORDER, text_color=theme.TEXT, hover_color=theme.CARD_BORDER,
                      command=self.forget_key).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        ctk.CTkLabel(b, text="Gemini model", anchor="w", font=self._font(12, "bold"), text_color=theme.MUTED).grid(
            row=5, column=0, sticky="w", pady=(10, 0))
        model_row = ctk.CTkFrame(b, fg_color="transparent")
        model_row.grid(row=6, column=0, sticky="ew")
        model_row.grid_columnconfigure(0, weight=1)
        models = list(dict.fromkeys([self.settings.model, *SUGGESTED_MODELS]))
        self.model_box = ctk.CTkComboBox(model_row, values=models, height=34, fg_color=theme.ENTRY_BG,
                                         button_color=theme.PURPLE, button_hover_color=theme.PURPLE_HOVER)
        self.model_box.set(self.settings.model)
        self.model_box.grid(row=0, column=0, sticky="ew")
        self.refresh_models_btn = ctk.CTkButton(model_row, text="↻", width=38, height=34, fg_color=theme.BTN_NAVY,
                                                hover_color=theme.BTN_NAVY_HOVER, command=self.refresh_models)
        self.refresh_models_btn.grid(row=0, column=1, padx=(6, 0))

        # --- 3. Options ----------------------------------------------------
        opt_card = Card(side, "3  •  Analysis Options")
        opt_card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        b = opt_card.body
        ocr_row = ctk.CTkFrame(b, fg_color="transparent")
        ocr_row.grid(row=2, column=0, sticky="ew")
        ocr_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(ocr_row, text="OCR for scanned pages", anchor="w", font=self._font(12, "bold"),
                     text_color=theme.MUTED).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(ocr_row, text="OCR language", anchor="w", font=self._font(12, "bold"),
                     text_color=theme.MUTED).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.ocr_mode = ctk.CTkOptionMenu(ocr_row, values=list(OCR_MODES), fg_color=theme.BTN_NAVY,
                                          button_color=theme.NAVY_2, button_hover_color=theme.PURPLE)
        self.ocr_mode.set(self.settings.ocr_mode)
        self.ocr_mode.grid(row=1, column=0, sticky="ew")
        # OCR language is fixed to English; other languages need extra Tesseract
        # language packs and would fail on most installations.
        self.ocr_lang = ctk.CTkEntry(ocr_row, fg_color=theme.ENTRY_BG, text_color=theme.TEXT)
        self.ocr_lang.insert(0, "English")
        self.ocr_lang.configure(state="disabled")
        self.ocr_lang.grid(row=1, column=1, sticky="ew", padx=(8, 0))
        self.ocr_status = ctk.CTkLabel(b, anchor="w", justify="left", wraplength=320, font=self._font(11))
        self.ocr_status.grid(row=3, column=0, sticky="ew", pady=(2, 2))
        self.ocr_help = ctk.CTkFrame(b, fg_color="transparent")
        self.ocr_help.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(self.ocr_help, text="Get OCR (free)", height=28, font=self._font(12),
                      fg_color=theme.BTN_NAVY, hover_color=theme.BTN_NAVY_HOVER,
                      command=self.open_ocr_download).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(self.ocr_help, text="Locate installed OCR…", height=28, font=self._font(12),
                      fg_color="transparent", border_width=1, border_color=theme.CARD_BORDER,
                      text_color=theme.TEXT, hover_color=theme.CARD_BORDER,
                      command=self.locate_tesseract).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self._refresh_ocr_status()

        self.force_sections_var = ctk.BooleanVar(value=self.settings.force_sectioned)
        ctk.CTkSwitch(b, text="Process long judgments in parts", variable=self.force_sections_var,
                      progress_color=theme.PURPLE, font=self._font(12)).grid(row=5, column=0, sticky="w", pady=(6, 0))
        self._hint(b, 6, "Always read the judgment in parts. Use it if a long judgment gives an incomplete "
                         "result or a 'limit reached' message.")
        self.para_refs_var = ctk.BooleanVar(value=self.settings.include_para_refs)
        ctk.CTkSwitch(b, text="Paragraph references", variable=self.para_refs_var,
                      progress_color=theme.PURPLE, font=self._font(12)).grid(row=7, column=0, sticky="w", pady=(6, 0))
        self._hint(b, 8, "Points in the analysis refer to the judgment's own paragraph numbers, e.g. (para 12), "
                         "which are the same in every copy of the judgment.")
        self.consistency_var = ctk.BooleanVar(value=self.settings.consistency_check)
        ctk.CTkSwitch(b, text="Double-check key facts", variable=self.consistency_var,
                      progress_color=theme.PURPLE, font=self._font(12)).grid(row=9, column=0, sticky="w", pady=(6, 0))
        self._hint(b, 10, "The AI reads the court, date, assessment year, sections and outcome a second time. "
                          "If the two readings differ, you choose the correct one when you approve.")
        ctk.CTkLabel(b, text="After every analysis the app looks up each quotation, citation, section, date and "
                             "amount in the judgment. Anything it cannot find is listed in the 'Source Check' tab - "
                             "check those items before you approve.", font=self._font(11), text_color=theme.MUTED,
                     wraplength=320, justify="left", anchor="w").grid(row=11, column=0, sticky="ew", pady=(10, 0))

        # --- Run controls --------------------------------------------------
        self.analyze_btn = ctk.CTkButton(side, text="⚖  Analyze Judgment", height=50, font=self._font(16, "bold"),
                                         fg_color=theme.GOLD, hover_color=theme.GOLD_HOVER, text_color=theme.NAVY,
                                         command=self.start_analysis)
        self.analyze_btn.grid(row=3, column=0, sticky="ew", pady=(4, 8))
        self.cancel_btn = ctk.CTkButton(side, text="✕  Cancel", height=38, fg_color=theme.DANGER,
                                        hover_color=theme.DANGER_HOVER, command=self.cancel, state="disabled")
        self.cancel_btn.grid(row=4, column=0, sticky="ew")
        ctk.CTkLabel(side, text="The judgment text is sent only to the Google Gemini API for analysis.\n"
                                "Review and approve the analysis before you save, send or rely on it.",
                     font=self._font(11), text_color=theme.MUTED, justify="center", wraplength=340).grid(
            row=5, column=0, pady=(12, 0))

    def _build_main(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=1, sticky="nsew", padx=(6, 14), pady=14)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        # Progress panel
        prog = ctk.CTkFrame(main, fg_color=theme.CARD, corner_radius=14, border_width=1,
                            border_color=theme.CARD_BORDER)
        prog.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        prog.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(prog, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        top.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(top, text="Ready. Upload a judgment PDF to begin.", anchor="w",
                                         justify="left", wraplength=720, font=self._font(13, "bold"),
                                         text_color=theme.TEXT)
        self.status_label.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.elapsed_label = ctk.CTkLabel(top, text="", font=self._font(12), text_color=theme.MUTED)
        self.elapsed_label.grid(row=0, column=1, sticky="ne")
        self.progress = ctk.CTkProgressBar(prog, height=12, progress_color=theme.GOLD)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 6))
        self.notes_label = ctk.CTkLabel(prog, text="", anchor="w", justify="left", font=self._font(11),
                                        text_color=theme.WARNING, wraplength=860)
        self.notes_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))

        # Reading options for the results (font family and size)
        bar_top = ctk.CTkFrame(main, fg_color="transparent")
        bar_top.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        bar_top.grid_columnconfigure(1, weight=1)
        # Edit controls (left): correct the AI text before exporting / emailing.
        edit_box = ctk.CTkFrame(bar_top, fg_color="transparent")
        edit_box.grid(row=0, column=0, sticky="w")
        self.edit_btn = ctk.CTkButton(edit_box, text="✎  Edit this tab", width=130, font=self._font(12, "bold"),
                                      fg_color=theme.PURPLE, hover_color=theme.PURPLE_HOVER,
                                      command=self.start_edit, state="disabled")
        self.edit_btn.pack(side="left")
        self.approve_btn = ctk.CTkButton(edit_box, text="✔  Review & Approve", width=160, font=self._font(12, "bold"),
                                         fg_color=theme.GOLD, hover_color=theme.GOLD_HOVER, text_color=theme.NAVY,
                                         command=self.review_and_approve, state="disabled")
        self.approve_btn.pack(side="left", padx=(8, 0))
        self.approval_label = ctk.CTkLabel(edit_box, text="", font=self._font(12, "bold"), text_color=theme.SUCCESS)
        self.approval_label.pack(side="left", padx=(10, 0))
        self.save_edit_btn = ctk.CTkButton(edit_box, text="✔  Save edits", width=120, font=self._font(12, "bold"),
                                           fg_color=theme.SUCCESS, hover_color="#16603D", command=self.save_edit)
        self.cancel_edit_btn = ctk.CTkButton(edit_box, text="Discard edits", width=110, font=self._font(12),
                                             fg_color="transparent", border_width=1, border_color=theme.CARD_BORDER,
                                             text_color=theme.TEXT, hover_color=theme.CARD_BORDER,
                                             command=self.cancel_edit)
        self._editing_tab: str | None = None
        tools = ctk.CTkFrame(bar_top, fg_color="transparent")
        tools.grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(tools, text="Results text:", font=self._font(12, "bold"), text_color=theme.MUTED).pack(
            side="left", padx=(0, 6))
        families = available_fonts(self)
        if self.settings.view_font_family not in families:
            self.settings.view_font_family = families[0]
        self.font_menu = ctk.CTkOptionMenu(tools, values=families, width=170, command=self._change_font,
                                           fg_color=theme.BTN_NAVY, button_color=theme.NAVY_2,
                                           button_hover_color=theme.PURPLE)
        self.font_menu.set(self.settings.view_font_family)
        self.font_menu.pack(side="left", padx=(0, 10))
        ctk.CTkButton(tools, text="A−", width=36, fg_color=theme.BTN_NAVY, hover_color=theme.BTN_NAVY_HOVER,
                      command=lambda: self._change_size(-1)).pack(side="left")
        self.size_label = ctk.CTkLabel(tools, text="", width=48, font=self._font(12, "bold"), text_color=theme.TEXT)
        self.size_label.pack(side="left")
        ctk.CTkButton(tools, text="A+", width=36, fg_color=theme.BTN_NAVY, hover_color=theme.BTN_NAVY_HOVER,
                      command=lambda: self._change_size(+1)).pack(side="left")

        # Results tabs
        self.tabview = ctk.CTkTabview(main, fg_color=theme.CARD, corner_radius=14, border_width=1,
                                      border_color=theme.CARD_BORDER, segmented_button_selected_color=theme.PURPLE,
                                      segmented_button_selected_hover_color=theme.PURPLE_HOVER,
                                      segmented_button_unselected_color=theme.NAVY,
                                      segmented_button_unselected_hover_color=theme.NAVY_2,
                                      text_color=theme.WHITE, command=self._refresh_action_state)
        self.tabview.grid(row=2, column=0, sticky="nsew")
        self.views: dict[str, MarkdownView] = {}
        for name in TABS:
            tab = self.tabview.add(name)
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            view = MarkdownView(tab, self.settings.view_font_family, self.settings.view_font_size)
            view.grid(row=0, column=0, sticky="nsew")
            self.views[name] = view
        self.tabview.set("Summary")
        self.size_label.configure(text=f"{self.settings.view_font_size} pt")

        # Action bar
        bar = ctk.CTkFrame(main, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        specs = [
            ("💾 Save  ▾", self.open_save_menu, theme.BTN_NAVY, theme.BTN_NAVY_HOVER),
            ("✉ Email", self.open_email, theme.PURPLE, theme.PURPLE_HOVER),
            ("🧹 Clear", self.clear_analysis, "#6B7285", "#565D70"),
            ("➕  New Analysis", self.analyze_another, theme.GOLD, theme.GOLD_HOVER),
        ]
        self.action_buttons: dict[str, ctk.CTkButton] = {}
        # Fixed-width buttons: Save and Email on the left, Clear and New Analysis on the right, so they keep
        # their size on a wide screen instead of stretching across the window.
        for label, cmd, color, hover in specs:
            btn = ctk.CTkButton(bar, text=label, command=cmd, height=38, fg_color=color, hover_color=hover,
                                font=self._font(12, "bold"), width=150,
                                text_color=theme.NAVY if color == theme.GOLD else theme.WHITE)
            self.action_buttons[label] = btn
        for label, btn in self.action_buttons.items():
            if "Clear" not in label and "New Analysis" not in label:
                btn.pack(side="left", padx=(0, 8))
        for label in reversed(list(self.action_buttons)):
            if "Clear" in label or "New Analysis" in label:
                self.action_buttons[label].pack(side="right", padx=(8, 0))

    # ============================================================ utilities
    def _change_appearance(self, mode: str) -> None:
        ctk.set_appearance_mode(mode)
        self.settings.appearance_mode = mode
        self._restyle_views()
        self._save_settings_quietly()

    def _restyle_views(self) -> None:
        for view in self.views.values():
            view.apply_theme(self.settings.view_font_family, self.settings.view_font_size)

    def _change_font(self, family: str) -> None:
        self.settings.view_font_family = family
        self._restyle_views()
        self._save_settings_quietly()

    def _change_size(self, delta: int) -> None:
        size = max(MIN_VIEW_FONT, min(MAX_VIEW_FONT, self.settings.view_font_size + delta))
        if size != self.settings.view_font_size:
            self.settings.view_font_size = size
            self._restyle_views()
            self._save_settings_quietly()
        self.size_label.configure(text=f"{size} pt")

    def _toggle_key(self) -> None:
        self.key_entry.configure(show="" if self.show_key_var.get() else "•")

    def _set_status(self, text: str, fraction: float | None = None) -> None:
        self.status_label.configure(text=text)
        if fraction is not None:
            self.progress.set(fraction)

    def _run_background(self, fn: Callable[[], Any], on_done: Callable[[Any], None],
                        on_error: Callable[[BaseException], None]) -> None:
        """Run ``fn`` on a worker thread and deliver the outcome on the GUI thread."""
        def target():
            try:
                value = fn()
                self.ui_queue.put(("call", on_done, value))
            except BaseException as exc:  # noqa: BLE001 - delivered to GUI
                self.ui_queue.put(("call", on_error, exc))

        threading.Thread(target=target, daemon=True).start()

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.ui_queue.get_nowait()
                kind = item[0]
                if kind == "progress":
                    _, fraction, message = item
                    self._set_status(message, fraction)
                elif kind == "call":
                    _, callback, value = item
                    callback(value)
        except queue.Empty:
            pass
        if self.busy and self._started_at:
            self.elapsed_label.configure(text=f"Elapsed {int(time.monotonic() - self._started_at)}s")
        self.after(100, self._poll_queue)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        for w in (self.upload_btn, self.analyze_btn, self.test_btn, self.refresh_models_btn):
            w.configure(state=state)
        self.cancel_btn.configure(state="normal" if busy else "disabled")
        if busy:
            self._started_at = time.monotonic()
        self._refresh_action_state()

    def _refresh_action_state(self) -> None:
        editing = bool(getattr(self, "_editing_tab", None))
        has_result = self.result is not None and not self.busy and not editing
        if hasattr(self, "edit_btn") and has_result and self.tabview.get() not in EDITABLE_TABS:
            has_edit = False
        else:
            has_edit = has_result
        approved = has_result and self.result.is_approved
        for label, btn in self.action_buttons.items():
            if "New Analysis" in label or "Clear" in label:
                btn.configure(state="disabled" if self.busy or editing else "normal")
            else:
                btn.configure(state="normal" if approved else "disabled")
        if hasattr(self, "edit_btn"):
            self.edit_btn.configure(state="normal" if has_edit else "disabled")
            self.approve_btn.configure(state="normal" if has_result else "disabled")
            if has_result and approved:
                self.approval_label.configure(text=f"✓ Approved by {self.result.approved_by}", text_color=theme.SUCCESS)
            elif has_result and self.result.approved_fingerprint:
                self.approval_label.configure(text="Changed after approval - approve again", text_color=theme.WARNING)
            elif has_result:
                self.approval_label.configure(text="Not yet approved", text_color=theme.MUTED)
            else:
                self.approval_label.configure(text="")

    def _error(self, title: str, message: str) -> None:
        messagebox.showerror(title, message, parent=self)

    def _current_settings(self) -> AppSettings | None:
        """Copy GUI values into settings, validating them. Returns None if invalid."""
        s = self.settings
        s.model = self.model_box.get().strip()
        s.analysis_depth = FIXED_DEPTH
        s.ocr_mode = self.ocr_mode.get()
        s.ocr_language = FIXED_OCR_LANGUAGE
        s.force_sectioned = bool(self.force_sections_var.get())
        s.include_para_refs = bool(self.para_refs_var.get())
        s.consistency_check = bool(self.consistency_var.get())
        problems = s.validate()
        if problems:
            self._error("Please check the settings", "\n".join(f"• {p}" for p in problems))
            return None
        return s

    def _save_settings_quietly(self) -> None:
        try:
            if not self.settings.validate():
                save_settings(self.settings)
        except OSError as exc:
            log.warning("Could not save settings: %s", exc)

    def _make_client(self) -> GeminiClient | None:
        key = normalize_api_key(self.key_var.get())
        if key != self.key_var.get():
            self.key_var.set(key)  # show the cleaned value (quotes/spaces/prefix removed)
        problem = validate_api_key_format(key)
        if problem:
            self._error("Gemini API key", problem)
            self.key_entry.focus_set()
            return None
        s = self.settings
        try:
            return GeminiClient(key, s.model, effective_temperature(s), s.max_output_tokens, s.request_timeout_s,
                                s.max_retries)
        except Exception as exc:
            self._error("Gemini", f"Could not initialise the Gemini client: {exc}")
            return None

    # ============================================================ API key
    def _load_saved_key(self) -> None:
        key, source = load_api_key()
        if key:
            self.key_var.set(key)
            self.remember_var.set(source == "keyring")
            where = "secure system store" if source == "keyring" else "environment (.env)"
            self.key_status.configure(text=f"Key loaded from {where}: {mask_key(key)}", text_color=theme.MUTED)
        else:
            self.key_status.configure(text="No key saved. Get one free at aistudio.google.com/apikey",
                                      text_color=theme.MUTED)

    def _persist_key_if_requested(self) -> None:
        key = normalize_api_key(self.key_var.get())
        if not self.remember_var.get():
            return
        try:
            save_api_key(key)
            self.key_status.configure(text=f"Key saved securely: {mask_key(key)}", text_color=theme.SUCCESS)
        except KeyStoreError as exc:
            self.key_status.configure(text=f"Key not saved: {exc}", text_color=theme.WARNING)

    def test_api_key(self) -> None:
        if self._current_settings() is None:
            return
        client = self._make_client()
        if client is None:
            return
        self.test_btn.configure(state="disabled", text="Testing…")
        self.key_status.configure(text="Contacting Gemini…", text_color=theme.MUTED)

        def done(message: str):
            self.test_btn.configure(state="normal", text="Test API Key")
            self.key_status.configure(text=f"✓ {message}", text_color=theme.SUCCESS)
            self._persist_key_if_requested()
            self._save_settings_quietly()

        def failed(exc: BaseException):
            self.test_btn.configure(state="normal", text="Test API Key")
            msg = str(exc) if isinstance(exc, GeminiError) else f"Unexpected error: {exc}"
            self.key_status.configure(text=f"✗ {msg}", text_color=theme.DANGER)

        self._run_background(client.test_connection, done, failed)

    def forget_key(self) -> None:
        delete_api_key()
        self.key_var.set("")
        self.remember_var.set(False)
        self.key_status.configure(text="Saved key removed from this computer.", text_color=theme.MUTED)

    def refresh_models(self) -> None:
        if self._current_settings() is None:
            return
        client = self._make_client()
        if client is None:
            return
        self.refresh_models_btn.configure(state="disabled")
        self.key_status.configure(text="Fetching available models…", text_color=theme.MUTED)

        def done(models: list[str]):
            self.refresh_models_btn.configure(state="normal")
            if models:
                current = self.model_box.get()
                self.model_box.configure(values=models)
                self.model_box.set(current if current in models else models[0])
                self.key_status.configure(text=f"✓ {len(models)} text models available to this key.",
                                          text_color=theme.SUCCESS)
            else:
                self.key_status.configure(text="No text models were returned for this key.", text_color=theme.WARNING)

        def failed(exc: BaseException):
            self.refresh_models_btn.configure(state="normal")
            self.key_status.configure(text=f"✗ {exc}", text_color=theme.DANGER)

        self._run_background(client.list_text_models, done, failed)

    # ============================================================ document
    def choose_pdf(self) -> None:
        if self.busy:
            return
        path = filedialog.askopenfilename(
            parent=self, title="Select a judicial decision (PDF)",
            filetypes=[("PDF documents", "*.pdf *.PDF"), ("All files", "*.*")])
        if not path:
            return
        self._set_status("Checking the selected PDF…", 0)
        self.upload_btn.configure(state="disabled")
        max_mb = self.settings.max_file_size_mb

        def work():
            info = validate_pdf(path, max_mb)
            ratio = text_layer_ratio(info)
            return info, ratio

        def done(value):
            info, ratio = value
            self.upload_btn.configure(state="normal")
            self.document = info
            self.doc_labels["File"].configure(text=info.file_name)
            self.doc_labels["Size"].configure(text=info.file_size_display)
            self.doc_labels["Pages"].configure(text=str(info.page_count))
            ocr = tesseract_available()
            if ratio >= 0.8:
                layer = "Text-based PDF ✓ (OCR not needed)"
            elif ratio > 0:
                layer = ("Partly scanned - OCR will be used where needed" if ocr else
                         "Partly scanned - install OCR, or scanned pages will be skipped")
            else:
                layer = "Scanned PDF - OCR will be used" if ocr else "Scanned PDF - install OCR to read it"
            self.doc_labels["Text layer"].configure(text=layer)
            self._refresh_ocr_status(needed=ratio < 0.8)
            self._set_status(f"Loaded “{info.file_name}”. Click Analyze Judgment to begin.", 0)
            log.info("Document selected: %s (%d pages, %s)", info.file_name, info.page_count, info.file_size_display)

        def failed(exc: BaseException):
            self.upload_btn.configure(state="normal")
            self._set_status("Ready. Upload a judgment PDF to begin.", 0)
            if isinstance(exc, PDFError):
                self._error("Cannot use this file", str(exc))
            else:
                log.exception("PDF validation failed", exc_info=exc)
                self._error("Cannot use this file", "The file could not be read as a PDF. It may be corrupted.")

        self._run_background(work, done, failed)

    # ============================================================ analysis
    def start_analysis(self) -> None:
        if self.busy:
            return
        if self.document is None:
            self._error("No document", "Please upload a judicial decision PDF first.")
            return
        if not self.document.path.exists():
            self._error("File missing", "The selected PDF no longer exists. Please upload it again.")
            return
        settings = self._current_settings()
        if settings is None:
            return
        client = self._make_client()
        if client is None:
            return
        self._persist_key_if_requested()
        self._save_settings_quietly()
        configure_tesseract(settings.tesseract_cmd)

        self.cancel_event = threading.Event()
        self.result = None
        self.notes_label.configure(text="")
        for view in self.views.values():
            view.set_placeholder("Analysis in progress…")
        self._set_busy(True)

        analyzer = Analyzer(settings, client,
                            progress=lambda f, m: self.ui_queue.put(("progress", f, m)),
                            cancel_event=self.cancel_event)
        info = self.document
        self._run_background(lambda: analyzer.run(info), self._analysis_done, self._analysis_failed)

    def _analysis_done(self, result: AnalysisResult) -> None:
        self.result = result
        self._set_busy(False)
        self._render_results()
        self.tabview.set("Summary")
        to_check = len(result.verification.not_found) if result.verification else 0
        differ = len(result.consistency.disagreements) if result.consistency and result.consistency.ok else 0
        missing_facts = bool(getattr(result, "facts_problem", ""))
        if to_check or differ or missing_facts:
            bits = []
            if missing_facts:
                bits.append("key facts incomplete - fill them in Review & Approve")
            if to_check:
                bits.append(f"{to_check} item(s) not found in the judgment (Source Check tab)")
            if differ:
                bits.append(f"{differ} key fact(s) to confirm")
            self._set_status("✓ Analysis complete. Please check: " + "; ".join(bits) + ". Then click Review & "
                             "Approve.", 1.0)
        else:
            self._set_status("✓ Analysis complete. Read it, then click Review & Approve.", 1.0)
        self.elapsed_label.configure(text=f"Completed in {result.elapsed_s:.0f}s")
        notes = [w for w in result.warnings if not w.startswith("Two AI readings differ")]
        self.notes_label.configure(text="  |  ".join(notes))

    def _render_results(self) -> None:
        report = self.result.report
        self.views["Full Report"].set_markdown(report.to_markdown())
        for tab in TAB_GROUPS:
            self.views[tab].set_markdown(report.tab_markdown(tab))
        self.views["Source Check"].set_markdown(self._quality_markdown())

    def _quality_markdown(self) -> str:
        r = self.result
        parts = []
        if r.verification is not None:
            parts.append(r.verification.to_markdown())
        if r.consistency is not None:
            parts.append(r.consistency.to_markdown())
        else:
            parts.append("## Consistency Check\n\nNot run for this analysis (switch it on under Analysis Options).")
        if r.register_ref:
            parts.append(f"## Precedent Register\n\n- Saved as **{r.register_ref}**. Key facts confirmed by the reviewer.")
        return "\n\n".join(parts)

    def _quality_lines(self) -> list[str]:
        r = self.result
        lines = []
        if r.verification is not None:
            lines.append(r.verification.summary_line())
        if r.consistency is not None:
            lines.append(r.consistency.summary_line())
        if r.register_ref:
            lines.append(f"Precedent register reference: {r.register_ref}")
        return lines

    # ============================================================ editing
    def start_edit(self) -> None:
        if not self.result or self.busy or self._editing_tab:
            return
        tab = self.tabview.get()
        self._editing_tab = tab
        self.views[tab].start_editing()
        self._set_tabs_enabled(False)
        self.edit_btn.pack_forget()
        self.save_edit_btn.pack(side="left")
        self.cancel_edit_btn.pack(side="left", padx=(6, 0))
        self._refresh_action_state()
        self._set_status(f"Editing the {tab} tab - change the text but keep the '## ' heading lines "
                         "(- = bullet, **text** = bold). Click 'Save edits' when done.")

    def save_edit(self) -> None:
        tab = self._editing_tab
        if not tab:
            return
        try:
            changed = apply_edit(self.result.report, tab, self.views[tab].editing_text())
        except ValueError as exc:
            self._error("Cannot save these edits", str(exc))
            return
        self._end_edit()
        if changed:
            self.result.recheck_sources()  # the Source Check always reflects the current text
        self._render_results()
        if changed:
            if EDITED_NOTE not in self.result.warnings:
                self.result.warnings.append(EDITED_NOTE)
            again = " The analysis was changed after approval - click Review & Approve again." \
                if self.result.approved_fingerprint else ""
            self._set_status(f"✓ Edits saved ({len(changed)} section(s) changed).{again}")
            self._refresh_action_state()
        else:
            self._set_status("No changes were made.")

    def cancel_edit(self) -> None:
        tab = self._editing_tab
        if not tab:
            return
        if self.views[tab].editing_text().strip() != self.views[tab].markdown.strip() and not messagebox.askyesno(
                "Discard edits", "Discard the changes you made in this tab?", parent=self):
            return
        self.views[tab].stop_editing()
        self._end_edit()
        self._set_status("Edits discarded.")

    def _end_edit(self) -> None:
        tab = self._editing_tab
        if tab:
            self.views[tab].editing = False
            self.views[tab].text.configure(cursor="arrow", undo=False)
        self._editing_tab = None
        self.save_edit_btn.pack_forget()
        self.cancel_edit_btn.pack_forget()
        self.edit_btn.pack(side="left")
        self._set_tabs_enabled(True)
        self._refresh_action_state()

    def _set_tabs_enabled(self, enabled: bool) -> None:
        """Stop switching tabs while one is being edited."""
        try:
            self.tabview._segmented_button.configure(state="normal" if enabled else "disabled")
        except Exception:  # private attribute; editing still works without the lock
            pass

    def _analysis_failed(self, exc: BaseException) -> None:
        self._set_busy(False)
        self.progress.set(0)
        for view in self.views.values():
            view.set_placeholder("Results will appear here after analysis.")
        if isinstance(exc, CancelledError):
            self._set_status("Analysis cancelled.", 0)
            return
        if isinstance(exc, (PDFError, GeminiError)):
            message = str(exc)
        else:
            log.exception("Unexpected analysis failure", exc_info=exc)
            message = f"An unexpected error occurred: {exc}"
            if self.log_file:
                message += f"\n\nDetails were written to the log file:\n{self.log_file}"
        self._set_status("Analysis failed.", 0)
        self._error("Analysis failed", message)

    def cancel(self) -> None:
        if self.busy:
            self.cancel_event.set()
            self.cancel_btn.configure(state="disabled")
            self._set_status("Cancelling… (waiting for the current step to stop)")

    # ============================================================ results
    DRAFT_NOTE = "DRAFT - for internal review (not yet verified by a reviewer)"

    def register_status(self, ref: str) -> str:
        """Current register status of an entry ('' if not in the register or the register is unavailable)."""
        if not ref:
            return ""
        try:
            rec = self.repository().get_by_ref(ref)
        except Exception:  # noqa: BLE001
            return ""
        return rec.status if rec else ""

    def _export_document(self):
        r = self.result
        verified = self.register_status(r.register_ref) == "Verified"
        return build_final_document(r.report, r.key_facts, approved_by=r.approved_by,
                                    status_note="" if verified else self.DRAFT_NOTE)

    def _require_approval(self) -> bool:
        if self.result is None:
            return False
        if not self.result.is_approved:
            self._error("Approval needed", "Click 'Review & Approve' first. The analysis can be saved, emailed or "
                                           "added to the register only after you have approved it.")
            return False
        return True

    def _ask_save_path(self, ext: str, label: str) -> str:
        stem = self.result.key_facts.get("case_title") or Path(self.result.document.info.file_name).stem
        return filedialog.asksaveasfilename(parent=self, title=f"Save analysis as {label}", defaultextension=ext,
                                            initialfile=safe_filename(stem, ext), filetypes=[(label, f"*{ext}")])

    def _save_with(self, ext: str, label: str, writer) -> None:
        if not self._require_approval():
            return
        path = self._ask_save_path(ext, label)
        if not path:
            return
        try:
            writer(self._export_document(), path)
            self._set_status(f"✓ Saved {Path(path).name}")
        except PermissionError:
            self._error("Save failed", "The file is open in another program or the folder is read-only.")
        except Exception as exc:
            log.exception("Export failed", exc_info=exc)
            self._error("Save failed", f"Could not save the file: {exc}")

    SAVE_FORMATS = (("Word document (.docx)", ".docx", "Word document"), ("PDF document (.pdf)", ".pdf", "PDF document"),
                    ("Text file (.txt)", ".txt", "Text file"), ("Data file (.json)", ".json", "JSON data"))

    def open_save_menu(self) -> None:
        """One Save button: choose the format from a short menu."""
        if not self._require_approval():
            return
        import tkinter as tk

        menu = tk.Menu(self, tearoff=0, font=(theme.FONT_FAMILY, 11))
        for text, ext, label in self.SAVE_FORMATS:
            menu.add_command(label=text, command=lambda e=ext, lb=label: self.save_as(e, lb))
        btn = self.action_buttons["💾 Save  ▾"]
        try:
            menu.tk_popup(btn.winfo_rootx(), btn.winfo_rooty() - 4 - 30 * len(self.SAVE_FORMATS))
        finally:
            menu.grab_release()

    def save_as(self, ext: str, label: str = "") -> None:
        writers = {".txt": save_text, ".docx": save_docx, ".pdf": save_pdf, ".json": self._write_json}
        self._save_with(ext, label or ext, writers[ext])

    def _write_json(self, doc, path) -> None:
        r = self.result
        save_json(build_json(doc, r.key_facts, r.approved_by, r.approved_at or "", r.register_ref or ""), path)

    # kept for compatibility (tests / older shortcuts)
    def save_txt(self) -> None:
        self.save_as(".txt", "Text file")

    def export_docx(self) -> None:
        self.save_as(".docx", "Word document")

    def export_pdf(self) -> None:
        self.save_as(".pdf", "PDF document")

    def open_email(self) -> None:
        if not self._require_approval():
            return
        if getattr(self, "_email_win", None) is not None and self._email_win.winfo_exists():
            bring_to_front(self._email_win, delay=10)
            return
        from .email_dialog import EmailDialog

        self._email_win = EmailDialog(self, self.result)

    # ============================================================ register
    def repository(self) -> Repository:
        path = register_path(self.settings)
        if self._repo is None or self._repo.path != path:
            if self._repo is not None:
                self._repo.close()
            self._repo = Repository(path)
        return self._repo

    def set_register_path(self, path: str) -> None:
        self.settings.register_path = path
        self._save_settings_quietly()
        self.refresh_register_badge()

    def refresh_register_badge(self) -> None:
        try:
            st = self.repository().stats()
            self.register_badge.configure(text=f"📚 Register: {st['total']} judgment(s) • {st['verified']} verified")
        except Exception as exc:  # the badge is informational only
            log.info("Register not available: %s", exc)
            self.register_badge.configure(text="📚 Precedent register")

    def _ask_register_location(self) -> None:
        """First start: ask where the precedent register should be kept, so the user knows the path."""
        default = register_path(AppSettings())
        win = ctk.CTkToplevel(self)
        win.title("Where should the precedent register be kept?")
        win.configure(fg_color=theme.BG)
        win.geometry("760x330+120+120")
        win.after(200, win.lift)
        win.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(win, text="Precedent register location", font=self._font(16, "bold"),
                     text_color=(theme.NAVY, theme.GOLD)).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 6))
        ctk.CTkLabel(win, text="Approved analyses and a copy of each judgment are stored in one register file. Keep "
                               "it on this computer, or in a shared folder (OneDrive / SharePoint / network drive) so "
                               "the whole team uses the same register. You can change this later in the register "
                               "window ('Change location…').", wraplength=700, justify="left", anchor="w",
                     font=self._font(12), text_color=theme.TEXT).grid(row=1, column=0, sticky="ew", padx=20)
        ctk.CTkLabel(win, text=f"This computer:  {default}", wraplength=700, justify="left", anchor="w",
                     font=self._font(11), text_color=theme.MUTED).grid(row=2, column=0, sticky="ew", padx=20,
                                                                       pady=(10, 0))

        def finish(path: str = "") -> None:
            self.settings.register_path = path
            self.settings.register_location_confirmed = True
            self._save_settings_quietly()
            self.refresh_register_badge()
            win.destroy()
            self._set_status(f"Precedent register: {register_path(self.settings)}")

        def choose() -> None:
            folder = filedialog.askdirectory(parent=win, title="Choose the folder for the precedent register")
            if folder:
                finish(str(Path(folder) / "precedent_register.db"))

        row = ctk.CTkFrame(win, fg_color="transparent")
        row.grid(row=3, column=0, sticky="ew", padx=20, pady=20)
        ctk.CTkButton(row, text="Keep it on this computer", height=38, font=self._font(13, "bold"),
                      fg_color=theme.GOLD, hover_color=theme.GOLD_HOVER, text_color=theme.NAVY,
                      command=finish).pack(side="left")
        ctk.CTkButton(row, text="Choose a folder…", height=38, font=self._font(13, "bold"),
                      fg_color=theme.PURPLE, hover_color=theme.PURPLE_HOVER, command=choose).pack(side="left",
                                                                                                 padx=10)
        win.protocol("WM_DELETE_WINDOW", finish)

    def open_register(self) -> None:
        win = getattr(self, "_register_win", None)
        if win is not None and win.winfo_exists():
            win.refresh()
            win.focus()
            return
        from .register_ui import RegisterWindow

        try:
            self._register_win = RegisterWindow(self)
        except RegisterError as exc:
            self._error("Precedent register", str(exc))

    def review_and_approve(self) -> None:
        if not self.result or self.busy or self._editing_tab:
            return
        open_lines = self.result.uncertain_lines()
        if open_lines:
            shown = "\n".join(f"• {ln[:120]}" for ln in open_lines[:6])
            self._error("Resolve [Uncertain] points first",
                        f"{len(open_lines)} line(s) in the analysis are still marked [Uncertain]:\n\n{shown}\n\n"
                        "Use 'Edit this tab' to correct or delete them (the AI was not sure of these points), "
                        "then approve.")
            return
        from .register_ui import ApprovalDialog

        try:
            repo = self.repository()
        except RegisterError as exc:
            self._error("Precedent register", str(exc))
            return

        def done(saved: bool) -> None:
            self._render_results()
            self._refresh_action_state()
            self.refresh_register_badge()
            ref = f" Saved to the precedent register as {self.result.register_ref}." if self.result.register_ref else ""
            self._set_status(f"✓ Approved by {self.result.approved_by}.{ref} You can now save it as Word / PDF or "
                             "email it.")
            win = getattr(self, "_register_win", None)
            if win is not None and win.winfo_exists():
                win.refresh()

        ApprovalDialog(self, self.result, repo, on_done=done)

    def clear_analysis(self) -> None:
        if self.busy:
            return
        self.result = None
        for view in self.views.values():
            view.set_placeholder("Results will appear here after analysis.")
        self.notes_label.configure(text="")
        self.elapsed_label.configure(text="")
        self._set_status("Analysis cleared." if self.document else "Ready. Upload a judgment PDF to begin.", 0)
        self._refresh_action_state()

    def analyze_another(self) -> None:
        if self.busy:
            return
        self.clear_analysis()
        self.document = None
        for lbl in self.doc_labels.values():
            lbl.configure(text="—")
        self.choose_pdf()

    # ============================================================ OCR helpers
    def _refresh_ocr_status(self, needed: bool = False) -> None:
        """OCR is only needed for scanned (image) PDFs. Without it, a neutral note is shown; it becomes a
        warning only when the loaded PDF actually has scanned pages."""
        if tesseract_available():
            self.ocr_status.configure(text="OCR for scanned PDFs: ready ✓", text_color=theme.SUCCESS)
            self.ocr_help.grid_forget()
        elif needed:
            self.ocr_status.configure(
                text="⚠ This PDF has scanned pages, and the free OCR program (Tesseract) is not installed, so "
                     "those pages cannot be read. Install OCR, or use a text-based copy of the judgment.",
                text_color=theme.WARNING)
            self.ocr_help.grid(row=4, column=0, sticky="ew", pady=(2, 6))
        else:
            self.ocr_status.configure(
                text="OCR not installed - not needed for normal (text) PDFs such as Taxmann, TaxTMI or "
                     "ITAT website copies. Needed only for scanned copies.", text_color=theme.MUTED)
            self.ocr_help.grid_forget()

    def open_ocr_download(self) -> None:
        webbrowser.open(OCR_DOWNLOAD_URL)
        messagebox.showinfo(
            "Install OCR", "The download page has opened in your browser.\n\n"
            "1. Download and run the Windows installer (64-bit).\n"
            "2. Keep the default install location.\n"
            "3. Restart Judgement Insights Analyser - OCR will be detected automatically.\n\n"
            "If you installed it somewhere else, use 'Locate installed OCR…'.", parent=self)

    def locate_tesseract(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title="Locate tesseract.exe (usually in C:\\Program Files\\Tesseract-OCR)",
            filetypes=[("Tesseract", "tesseract.exe tesseract"), ("All files", "*.*")])
        if not path:
            return
        configure_tesseract(path)
        if tesseract_available():
            self.settings.tesseract_cmd = path
            self._save_settings_quietly()
        else:
            self._error("OCR not found", "That file is not a working Tesseract OCR program.")
        self._refresh_ocr_status()

    def _on_close(self) -> None:
        """Close button and window [X]: confirm if work is in progress, then exit."""
        if getattr(self, "_editing_tab", None) and not messagebox.askyesno(
                "Unsaved edits", "You have unsaved edits in the results. Close without saving them?", parent=self):
            return
        if self.busy and not messagebox.askyesno(
                "Analysis running", "An analysis is in progress. Cancel it and exit?", parent=self):
            return
        email_win = getattr(self, "_email_win", None)
        if email_win is not None and email_win.winfo_exists():
            if getattr(email_win, "busy", False) and not messagebox.askyesno(
                    "Emails in progress", "Emails are still being created. Stop and exit?", parent=self):
                return
            email_win.cancel_event.set()
        self.cancel_event.set()
        self._current_settings_silent()
        self.destroy()

    def _current_settings_silent(self) -> None:
        try:
            self.settings.model = self.model_box.get().strip() or self.settings.model
            self.settings.analysis_depth = FIXED_DEPTH
            self.settings.ocr_mode = self.ocr_mode.get()
            self.settings.force_sectioned = bool(self.force_sections_var.get())
            self.settings.include_para_refs = bool(self.para_refs_var.get())
            self.settings.consistency_check = bool(self.consistency_var.get())
            self._save_settings_quietly()
        except Exception:  # never block exit
            pass
