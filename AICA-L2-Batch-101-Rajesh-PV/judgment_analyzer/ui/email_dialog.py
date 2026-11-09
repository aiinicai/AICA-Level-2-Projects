"""'Email' window: sender details, recipient list (clients and employees), two editable
versions (client / team), review & approval gate, and delivery through Outlook, any
email account (Gmail / SMTP) or .eml files."""

from __future__ import annotations

import html
import logging
import os
import queue
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import hashlib

from ..audience_check import client_markers_in_team, recipient_warnings, team_markers_in_client
from ..email_composer import (BLANK_GREETING, DEFAULT_INTERNAL_INTRO, DEFAULT_INTRO, EMAIL_SECTION_CHOICES,
                              INTERNAL_SECTION_CHOICES, EmailContent, SenderProfile,
                              build_client_body, build_internal_body, default_subject, extract_case_title,
                              extract_citation, extract_judgment_date, find_review_items,
                              load_sender_profile, render_email, save_sender_profile)
from ..key_store import KeyStoreError, delete_secret, load_secret, save_secret, secret_account
from ..config import save_settings
from ..mailer import (MODE_DRAFT, MODE_EML, MODE_SEND, MODE_SMTP, MODE_TEST, SMTP_PRESETS, SMTP_SECURITY,
                      OutlookMailer, SmtpMailer, SmtpSettings, audit_log_path, carry_over_audit, deliver_batch,
                      load_smtp_settings, outlook_available, save_smtp_settings, audit_xlsx_path, write_audit_xlsx, looks_like_gmail_app_password, normalise_password, repair_audit_log)
from ..pdf_processor import CancelledError
from ..prompts import REPORT_SECTIONS
from ..recipients import (RecipientStore, GROUP_CLIENT, GROUP_EMPLOYEE, Recipient, RecipientFileError, create_template,
                          load_recipients)
from . import theme
from .widgets import Card, MarkupEditor, ScrollFrame2D, bring_to_front

# Minimum layout size (logical px); smaller windows scroll instead of clipping.
CONTENT_MIN_W, CONTENT_MIN_H = 1180, 1080

log = logging.getLogger(__name__)

DELIVERY_LABELS = {
    "Create drafts in Outlook": MODE_DRAFT,
    "Send now via Outlook": MODE_SEND,
    "Send via email account (Gmail / SMTP)": MODE_SMTP,
    "Save as .eml files": MODE_EML,
}
VERSION_TAB = {GROUP_CLIENT: "Client version", GROUP_EMPLOYEE: "Team version (employees)"}
AUDIENCES = {"Clients": [GROUP_CLIENT], "Employees": [GROUP_EMPLOYEE], "Both": [GROUP_CLIENT, GROUP_EMPLOYEE]}





def _conf(widget, **options) -> None:
    """Configure only what actually changed. Re-setting the same text/state on every refresh makes Tk
    re-measure the button row on Windows, which shows as flickering buttons."""
    changed = {}
    for key, value in options.items():
        try:
            if widget.cget(key) == value:
                continue
        except Exception:  # noqa: BLE001 - option not readable: set it
            pass
        changed[key] = value
    if changed:
        widget.configure(**changed)

class EmailDialog(ctk.CTkToplevel):
    def __init__(self, master, result):
        super().__init__(master)
        self.result = result
        self.report = result.report
        self.app_settings = getattr(master, "settings", None)
        self._audit_warning = ""
        self.title("Email - Clients and Team - Judgement Insights Analyser")
        self.configure(fg_color=theme.BG)
        # A normal top-level window (not 'transient'), so Windows shows the
        # minimise and maximise buttons; sized to fit the screen at any scaling.
        self.resizable(True, True)
        self._fit_to_screen()

        self.recipients: list[Recipient] = []
        self._issues: list[str] = []
        self.recipient_vars: list[ctk.BooleanVar] = []
        self.approved_fingerprint: str | None = None
        self.approved_at = ""
        self.busy = False
        self.cancel_event = threading.Event()
        self.q: queue.Queue = queue.Queue()
        self.outlook_ok, self.outlook_reason = outlook_available()
        facts = getattr(result, "key_facts", None) or {}
        self.case_title = facts.get("case_title") or extract_case_title(self.report)
        self._citation = facts.get("citation") or extract_citation(self.report)
        self._date = facts.get("judgment_date") or extract_judgment_date(self.report)
        self.smtp_settings = load_smtp_settings()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.scroller = ScrollFrame2D(self, min_width=CONTENT_MIN_W, min_height=CONTENT_MIN_H)
        self.scroller.grid(row=0, column=0, sticky="nsew")
        self.page = self.scroller.inner
        self.page.grid_columnconfigure(1, weight=1)
        self.page.grid_rowconfigure(0, weight=1)
        self._build_left()
        self._build_right()
        self._load_profile()
        self._load_saved_lists()
        self._load_smtp_fields()
        self._rebuild_body(confirm=False)
        self._init_audit_location()
        self._on_delivery_change(self.delivery.get())
        self.protocol("WM_DELETE_WINDOW", self._close)
        if self._register_status() != "Verified":
            # not verified yet: start with the team; client emails stay blocked until a reviewer verifies it
            self.audience.set("Employees")
            self._on_audience()
        bring_to_front(self, self.version_widgets[GROUP_CLIENT]["subject"])
        self.after(150, self._poll)

    # ------------------------------------------------------------- helpers
    def _fit_to_screen(self):
        """Open at up to 1320x900 (logical units), never larger than ~92% of the screen."""
        try:
            from customtkinter import ScalingTracker
            scale = ScalingTracker.get_window_scaling(self)
        except Exception:
            scale = 1.0
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = int(min(1320, sw * 0.94 / scale))
        h = int(min(900, (sh * 0.88) / scale))  # leave room for the taskbar
        self.geometry(f"{w}x{h}+10+10")
        self.minsize(min(700, w), min(480, h))

    def _font(self, size=13, weight="normal"):
        return ctk.CTkFont(theme.FONT_FAMILY, size, weight)

    def _label(self, parent, text, row, bold=True, **grid):
        lbl = ctk.CTkLabel(parent, text=text, anchor="w", font=self._font(12, "bold" if bold else "normal"),
                           text_color=theme.MUTED)
        lbl.grid(row=row, column=0, sticky="w", **grid)
        return lbl

    def _button(self, parent, text, cmd, kind="navy", **kw):
        colors = {"navy": (theme.BTN_NAVY, theme.BTN_NAVY_HOVER, theme.WHITE),
                  "purple": (theme.PURPLE, theme.PURPLE_HOVER, theme.WHITE),
                  "gold": (theme.GOLD, theme.GOLD_HOVER, theme.NAVY),
                  "ghost": ("transparent", theme.CARD_BORDER, theme.TEXT)}[kind]
        extra = {"border_width": 1, "border_color": theme.CARD_BORDER} if kind == "ghost" else {}
        return ctk.CTkButton(parent, text=text, command=cmd, fg_color=colors[0], hover_color=colors[1],
                             text_color=colors[2], font=self._font(13, "bold"), **extra, **kw)

    def _active_versions(self) -> list[str]:
        return AUDIENCES.get(self.audience.get(), [GROUP_CLIENT])

    # -------------------------------------------------------------- layout
    def _build_left(self):
        left = ctk.CTkFrame(self.page, width=430, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(14, 6), pady=14)
        left.grid_columnconfigure(0, weight=1)

        # 1. Sender
        card = Card(left, "1  •  Your details (sender)")
        card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.sender_entries: dict[str, ctk.CTkEntry] = {}
        for i, (key, label, ph) in enumerate([
            ("name", "Your name *", "e.g. A. Kumar"), ("designation", "Designation", "e.g. Manager - Tax"),
            ("firm", "Firm", "e.g. ABC & Associates"), ("email", "Your email address *", "you@firm.com"),
            ("phone", "Phone", "+91 ..."),
        ]):
            self._label(card.body, label, row=i * 2, pady=(4 if i else 0, 0))
            e = ctk.CTkEntry(card.body, placeholder_text=ph, fg_color=theme.ENTRY_BG, height=32)
            e.grid(row=i * 2 + 1, column=0, sticky="ew")
            self.sender_entries[key] = e
        self._button(card.body, "Save my details", self._save_profile, "ghost", height=30).grid(
            row=10, column=0, sticky="ew", pady=(10, 0))

        # 2. Recipients
        card = Card(left, "2  •  Recipients (clients and employees)")
        card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self._label(card.body, "Send to", 0)
        self.audience = ctk.CTkSegmentedButton(card.body, values=list(AUDIENCES), command=self._on_audience,
                                               selected_color=theme.PURPLE, selected_hover_color=theme.PURPLE_HOVER)
        self.audience.set("Clients")
        self.audience.grid(row=1, column=0, sticky="w", pady=(0, 8))
        lists = ctk.CTkFrame(card.body, fg_color="transparent")
        lists.grid(row=2, column=0, sticky="ew")
        lists.grid_columnconfigure((1, 2), weight=1)
        self.list_labels: dict[str, ctk.CTkLabel] = {}
        for i, (group, title) in enumerate(((GROUP_CLIENT, "Clients"), (GROUP_EMPLOYEE, "Employees"))):
            ctk.CTkLabel(lists, text=title, font=self._font(12, "bold"), text_color=theme.MUTED, width=74,
                         anchor="w").grid(row=i * 2, column=0, sticky="w", pady=(4, 0))
            self._button(lists, "Template", lambda g=group: self._download_template(g), "ghost", height=30,
                         width=90).grid(row=i * 2, column=1, sticky="ew", padx=(0, 4), pady=(4, 0))
            self._button(lists, f"Load {title.lower()} list…", lambda g=group: self._load_recipients(g), "purple",
                         height=30).grid(row=i * 2, column=2, sticky="ew", pady=(4, 0))
            lbl = ctk.CTkLabel(lists, text="Not loaded", anchor="w", justify="left", font=self._font(11),
                               text_color=theme.MUTED, wraplength=230)
            lbl.grid(row=i * 2 + 1, column=1, columnspan=2, sticky="w")
            self.list_labels[group] = lbl
            forget = ctk.CTkButton(lists, text="Forget", width=58, height=22, font=self._font(11),
                                   fg_color="transparent", border_width=1, border_color=theme.CARD_BORDER,
                                   text_color=theme.TEXT, hover_color=theme.CARD_BORDER,
                                   command=lambda g=group: self._forget_list(g))
            forget.grid(row=i * 2 + 1, column=2, sticky="e")
            self.forget_btns = getattr(self, "forget_btns", {})
            self.forget_btns[group] = forget
        self.loaded: dict[str, list] = {GROUP_CLIENT: [], GROUP_EMPLOYEE: []}
        self.load_issues: dict[str, list] = {GROUP_CLIENT: [], GROUP_EMPLOYEE: []}
        self.recip_info = ctk.CTkLabel(card.body, text="", anchor="w", justify="left",
                                       wraplength=380, font=self._font(12), text_color=theme.MUTED)
        self.recip_info.grid(row=3, column=0, sticky="ew", pady=(6, 2))
        self.recip_issues_btn = self._button(card.body, "Show rows that were not loaded", self._show_issues,
                                             "ghost", height=26)
        sel = ctk.CTkFrame(card.body, fg_color="transparent")
        sel.grid(row=5, column=0, sticky="ew")
        ctk.CTkButton(sel, text="Select all", width=90, height=24, fg_color="transparent", text_color=theme.TEXT,
                      hover_color=theme.CARD_BORDER, command=lambda: self._select_all(True)).pack(side="left")
        ctk.CTkButton(sel, text="Select none", width=90, height=24, fg_color="transparent",
                      text_color=theme.TEXT, hover_color=theme.CARD_BORDER,
                      command=lambda: self._select_all(False)).pack(side="left")
        self.recip_list = ctk.CTkScrollableFrame(card.body, height=170, fg_color=theme.ENTRY_BG)
        self.recip_list.grid(row=6, column=0, sticky="ew", pady=(4, 0))
        self.recip_list.grid_columnconfigure(0, weight=1)

        # 3. Sections
        card = Card(left, "3  •  Sections to include")
        card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        grid = ctk.CTkFrame(card.body, fg_color="transparent")
        grid.grid(row=0, column=0, sticky="ew")
        grid.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(grid, text="Section", font=self._font(11, "bold"), text_color=theme.MUTED).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(grid, text="Clients", font=self._font(11, "bold"), text_color=theme.MUTED).grid(
            row=0, column=1, padx=6)
        ctk.CTkLabel(grid, text="Team", font=self._font(11, "bold"), text_color=theme.MUTED).grid(
            row=0, column=2, padx=6)
        client_default = dict(EMAIL_SECTION_CHOICES)
        team_default = dict(INTERNAL_SECTION_CHOICES)
        numbers = sorted(set(client_default) | set(team_default))
        self.section_vars: dict[str, dict[int, ctk.BooleanVar]] = {GROUP_CLIENT: {}, GROUP_EMPLOYEE: {}}
        for i, number in enumerate(numbers, 1):
            ctk.CTkLabel(grid, text=REPORT_SECTIONS[number - 1].title, font=self._font(12), anchor="w").grid(
                row=i, column=0, sticky="w", pady=1)
            for col, (group, defaults) in enumerate(((GROUP_CLIENT, client_default),
                                                     (GROUP_EMPLOYEE, team_default)), 1):
                var = ctk.BooleanVar(value=defaults.get(number, False))
                ctk.CTkCheckBox(grid, text="", width=24, variable=var, fg_color=theme.PURPLE,
                                hover_color=theme.PURPLE_HOVER).grid(row=i, column=col, padx=6)
                self.section_vars[group][number] = var
        ctk.CTkLabel(card.body, text="Client version: page references and [Court Finding] / [AI Observation] labels "
                                     "are removed. Team version keeps them, with paragraph references and the "
                                     "register reference.", wraplength=380, justify="left", anchor="w",
                     font=self._font(11), text_color=theme.MUTED).grid(row=1, column=0, sticky="ew", pady=(6, 4))
        self._button(card.body, "Rebuild email text from analysis", self._rebuild_body, "ghost", height=30).grid(
            row=2, column=0, sticky="ew")

    def _build_right(self):
        right = ctk.CTkFrame(self.page, fg_color=theme.CARD, corner_radius=14, border_width=1,
                             border_color=theme.CARD_BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 14), pady=14)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        pad = {"padx": 16}

        ctk.CTkLabel(right, text="4  •  Review and edit the email(s)", font=self._font(15, "bold"),
                     text_color=(theme.NAVY, theme.GOLD), anchor="w").grid(row=0, column=0, sticky="w",
                                                                           pady=(12, 4), **pad)
        self.version_tabs = ctk.CTkTabview(right, fg_color=theme.CARD, segmented_button_selected_color=theme.PURPLE,
                                           segmented_button_selected_hover_color=theme.PURPLE_HOVER,
                                           segmented_button_unselected_color=theme.NAVY,
                                           segmented_button_unselected_hover_color=theme.NAVY_2,
                                           text_color=theme.WHITE, height=420, command=self._on_version_tab)
        self.version_tabs.grid(row=1, column=0, sticky="nsew", **pad)
        self.version_widgets: dict[str, dict] = {}
        subject = default_subject(self.case_title, self._citation, self._date)
        for group in (GROUP_CLIENT, GROUP_EMPLOYEE):
            tab = self.version_tabs.add(VERSION_TAB[group])
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(5, weight=1)
            self._label(tab, "Subject", 0)
            subj = ctk.CTkEntry(tab, fg_color=theme.ENTRY_BG, height=32)
            subj.insert(0, subject if group == GROUP_CLIENT else f"[Precedent register] {subject}")
            subj.grid(row=1, column=0, sticky="ew")
            self._label(tab, "Opening paragraph  (each person is greeted by name automatically: “Dear Mr Rao,”)",
                        2, pady=(8, 0))
            intro = ctk.CTkTextbox(tab, height=58, fg_color=theme.ENTRY_BG, wrap="word", font=self._font(13))
            intro.insert("1.0", DEFAULT_INTRO if group == GROUP_CLIENT else DEFAULT_INTERNAL_INTRO)
            intro.grid(row=3, column=0, sticky="ew")
            ctk.CTkLabel(tab, text="Email content  (coloured labels are for your review - they are removed when sent)",
                         anchor="w",
                         font=self._font(12, "bold"), text_color=theme.MUTED).grid(row=4, column=0, sticky="w",
                                                                                  pady=(8, 0))
            body = MarkupEditor(tab, height=240, fg_color=theme.ENTRY_BG, wrap="word", font=self._font(13))
            body.grid(row=5, column=0, sticky="nsew")
            self._label(tab, "Closing note (optional - e.g. your firm's standard note)", 6, pady=(8, 0))
            note = ctk.CTkEntry(tab, fg_color=theme.ENTRY_BG, height=30)
            note.grid(row=7, column=0, sticky="ew")
            self.version_widgets[group] = {"subject": subj, "intro": intro, "body": body, "note": note}

        self.review_label = ctk.CTkLabel(right, text="", anchor="w", justify="left", wraplength=820,
                                         font=self._font(12))
        self.review_label.grid(row=2, column=0, sticky="ew", pady=(6, 0), **pad)

        # Approval
        appr = ctk.CTkFrame(right, fg_color=("#F4F1FA", "#1E1A33"), corner_radius=10)
        appr.grid(row=3, column=0, sticky="ew", pady=(8, 0), **pad)
        appr.grid_columnconfigure(0, weight=1)
        self.quality_label = ctk.CTkLabel(appr, text="", anchor="w", justify="left", wraplength=640,
                                          font=self._font(12))
        self.quality_label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 2))
        self.reviewed_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(appr, text="I have checked this email content and approve it for sending.",
                        variable=self.reviewed_var, fg_color=theme.PURPLE, hover_color=theme.PURPLE_HOVER,
                        font=self._font(12)).grid(row=2, column=0, sticky="w", padx=12, pady=(4, 4))
        self.approve_btn = self._button(appr, "✔  Approve content", self._approve, "purple", height=34, width=180)
        self.approve_btn.grid(row=0, column=1, rowspan=4, padx=12, pady=8, sticky="e")
        self.approval_label = ctk.CTkLabel(appr, text="", anchor="w", font=self._font(12, "bold"))
        self.approval_label.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 10))
        self._refresh_quality()

        # Delivery
        deliv = ctk.CTkFrame(right, fg_color="transparent")
        deliv.grid(row=4, column=0, sticky="ew", pady=(10, 0), **pad)
        deliv.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(deliv, text="Delivery:", font=self._font(12, "bold"), text_color=theme.MUTED).grid(
            row=0, column=0, padx=(0, 8))
        options = [k for k, v in DELIVERY_LABELS.items() if self.outlook_ok or v not in (MODE_DRAFT, MODE_SEND)]
        self.delivery = ctk.CTkSegmentedButton(deliv, values=options, selected_color=theme.PURPLE,
                                               selected_hover_color=theme.PURPLE_HOVER,
                                               command=self._on_delivery_change)
        self.delivery.set(options[0])
        self.delivery.grid(row=0, column=1, sticky="w")
        if not self.outlook_ok:
            ctk.CTkLabel(deliv, text=self.outlook_reason, font=self._font(11), text_color=theme.WARNING).grid(
                row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))

        # Email account (SMTP) settings - shown only for that delivery option
        self.smtp_frame = ctk.CTkFrame(right, fg_color=("#F7F8FC", "#111A2E"), corner_radius=10)
        sf = self.smtp_frame
        for c in (1, 3):
            sf.grid_columnconfigure(c, weight=1)
        ctk.CTkLabel(sf, text="Email account", font=self._font(13, "bold"), text_color=(theme.NAVY, theme.GOLD)).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(8, 2))
        ctk.CTkLabel(sf, text="Provider", font=self._font(12, "bold"), text_color=theme.MUTED).grid(
            row=1, column=0, sticky="w", padx=(12, 6))
        self.smtp_provider = ctk.CTkOptionMenu(sf, values=list(SMTP_PRESETS), command=self._on_provider,
                                               fg_color=theme.BTN_NAVY, button_color=theme.NAVY_2,
                                               button_hover_color=theme.PURPLE)
        self.smtp_provider.grid(row=1, column=1, sticky="ew", pady=3)
        ctk.CTkLabel(sf, text="Server", font=self._font(12, "bold"), text_color=theme.MUTED).grid(
            row=1, column=2, sticky="w", padx=(12, 6))
        self.smtp_host = ctk.CTkEntry(sf, fg_color=theme.ENTRY_BG, height=30, placeholder_text="smtp.example.com")
        self.smtp_host.grid(row=1, column=3, sticky="ew", padx=(0, 12), pady=3)
        ctk.CTkLabel(sf, text="Port", font=self._font(12, "bold"), text_color=theme.MUTED).grid(
            row=2, column=0, sticky="w", padx=(12, 6))
        port_row = ctk.CTkFrame(sf, fg_color="transparent")
        port_row.grid(row=2, column=1, sticky="ew", pady=3)
        self.smtp_port = ctk.CTkEntry(port_row, fg_color=theme.ENTRY_BG, height=30, width=70)
        self.smtp_port.pack(side="left")
        self.smtp_security = ctk.CTkSegmentedButton(port_row, values=list(SMTP_SECURITY),
                                                    selected_color=theme.PURPLE,
                                                    selected_hover_color=theme.PURPLE_HOVER)
        self.smtp_security.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(sf, text="User name", font=self._font(12, "bold"), text_color=theme.MUTED).grid(
            row=2, column=2, sticky="w", padx=(12, 6))
        self.smtp_user = ctk.CTkEntry(sf, fg_color=theme.ENTRY_BG, height=30, placeholder_text="you@gmail.com")
        self.smtp_user.grid(row=2, column=3, sticky="ew", padx=(0, 12), pady=3)
        ctk.CTkLabel(sf, text="Password", font=self._font(12, "bold"), text_color=theme.MUTED).grid(
            row=3, column=0, sticky="w", padx=(12, 6))
        self.smtp_password = ctk.CTkEntry(sf, fg_color=theme.ENTRY_BG, height=30, show="•",
                                          placeholder_text="Gmail: 16-character App Password")
        self.smtp_password.grid(row=3, column=1, sticky="ew", pady=3)
        self.smtp_remember = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(sf, text="Remember password securely", variable=self.smtp_remember, fg_color=theme.PURPLE,
                        hover_color=theme.PURPLE_HOVER, font=self._font(12)).grid(row=3, column=2, columnspan=2,
                                                                                 sticky="w", padx=(12, 0))
        sbtn = ctk.CTkFrame(sf, fg_color="transparent")
        sbtn.grid(row=4, column=0, columnspan=4, sticky="ew", padx=12, pady=(4, 2))
        self.smtp_test_btn = self._button(sbtn, "Test sign-in", self._test_smtp, "navy", height=28, width=120)
        self.smtp_test_btn.pack(side="left")
        self._button(sbtn, "Forget saved password", self._forget_smtp_password, "ghost", height=28,
                     width=170).pack(side="left", padx=(8, 0))
        self.smtp_status = ctk.CTkLabel(sf, text="", anchor="w", justify="left", wraplength=800, font=self._font(11),
                                        text_color=theme.MUTED)
        self.smtp_status.grid(row=5, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 8))

        btns = ctk.CTkFrame(right, fg_color="transparent")
        btns.grid(row=6, column=0, sticky="ew", pady=(10, 0), **pad)
        btns.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self._button(btns, "👁  Preview email", self._preview, "ghost", height=38).grid(
            row=0, column=0, sticky="ew", padx=(0, 4))
        self.test_btn = self._button(btns, "✉  Send test to me", self._send_test, "navy", height=38)
        self.test_btn.grid(row=0, column=1, sticky="ew", padx=4)
        self.audit_btn = self._button(btns, "📄  Open audit log", self._open_audit, "ghost", height=38)
        self.audit_btn.grid(row=0, column=2, sticky="ew", padx=4)
        self.send_btn = self._button(btns, "Create emails", self._send_all, "gold", height=38)
        self.send_btn.grid(row=0, column=3, sticky="ew", padx=4)
        ctk.CTkButton(btns, text="✕  Close", height=38, font=self._font(13, "bold"), fg_color=theme.DANGER,
                      hover_color=theme.DANGER_HOVER, text_color=theme.WHITE, command=self._close).grid(
            row=0, column=4, sticky="ew", padx=(4, 0))

        loc = ctk.CTkFrame(right, fg_color="transparent")
        loc.grid(row=7, column=0, sticky="ew", pady=(8, 0), **pad)
        loc.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(loc, text="Audit log saved in:", font=self._font(12, "bold"), text_color=theme.MUTED).grid(
            row=0, column=0, padx=(0, 8))
        self.audit_label = ctk.CTkLabel(loc, text="", anchor="w", font=self._font(12), text_color=theme.TEXT)
        self.audit_label.grid(row=0, column=1, sticky="ew")
        ctk.CTkButton(loc, text="Change…", width=90, height=26, fg_color="transparent", border_width=1,
                      border_color=theme.CARD_BORDER, text_color=theme.TEXT, hover_color=theme.CARD_BORDER,
                      command=self._change_audit_dir).grid(row=0, column=2, padx=(8, 4))
        ctk.CTkButton(loc, text="Open folder", width=100, height=26, fg_color="transparent", border_width=1,
                      border_color=theme.CARD_BORDER, text_color=theme.TEXT, hover_color=theme.CARD_BORDER,
                      command=lambda: self._open_path(self._audit_path().parent)).grid(row=0, column=3)

        prog = ctk.CTkFrame(right, fg_color="transparent")
        prog.grid(row=8, column=0, sticky="ew", pady=(8, 12), **pad)
        prog.grid_columnconfigure(0, weight=1)
        self.progress = ctk.CTkProgressBar(prog, height=10, progress_color=theme.GOLD)
        self.progress.set(0)
        self.progress.grid(row=0, column=0, sticky="ew")
        self.cancel_btn = ctk.CTkButton(prog, text="Cancel", width=80, height=26, fg_color=theme.DANGER,
                                        hover_color=theme.DANGER_HOVER, command=self.cancel_event.set,
                                        state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(8, 0))
        self.status = ctk.CTkLabel(prog, text="", anchor="w", justify="left", wraplength=820, font=self._font(12))
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    # ------------------------------------------------------------- sender
    def _load_profile(self):
        p = load_sender_profile()
        for key, entry in self.sender_entries.items():
            value = getattr(p, key, "")
            if value:
                entry.insert(0, value)

    def _profile(self) -> SenderProfile:
        return SenderProfile(**{k: e.get().strip() for k, e in self.sender_entries.items()})

    def _save_profile(self, quiet=False) -> bool:
        p = self._profile()
        problems = p.validate()
        if problems:
            if not quiet:
                messagebox.showerror("Sender details", "\n".join(f"• {x}" for x in problems), parent=self)
            return False
        save_sender_profile(p)
        if not quiet:
            self._set_status("✓ Your details were saved on this computer.", theme.SUCCESS)
        return True

    # ------------------------------------------------------------- SMTP
    def _load_smtp_fields(self):
        s = self.smtp_settings
        self.smtp_provider.set(s.provider if s.provider in SMTP_PRESETS else list(SMTP_PRESETS)[-1])
        self.smtp_host.insert(0, s.host)
        self.smtp_port.insert(0, str(s.port))
        self.smtp_security.set(s.security if s.security in SMTP_SECURITY else "SSL")
        user = s.username or self._profile().email
        if user:
            self.smtp_user.insert(0, user)
        saved = load_secret(secret_account("smtp", user)) if user else ""
        if saved:
            self.smtp_password.insert(0, saved)
            self.smtp_remember.set(True)
            self.smtp_status.configure(text="Password loaded from the secure system store.")
        else:
            self.smtp_status.configure(text="Gmail: turn on 2-Step Verification, then create an App Password "
                                            "(Google Account > Security > App passwords) and paste it here. "
                                            "Your normal Gmail password will not work.")

    def _on_provider(self, provider: str):
        host, port, security = SMTP_PRESETS[provider]
        self.smtp_host.delete(0, "end")
        self.smtp_host.insert(0, host)
        self.smtp_port.delete(0, "end")
        self.smtp_port.insert(0, str(port))
        self.smtp_security.set(security)

    def _smtp_from_fields(self) -> SmtpSettings:
        try:
            port = int(self.smtp_port.get().strip() or 0)
        except ValueError:
            port = 0
        return SmtpSettings(provider=self.smtp_provider.get(), host=self.smtp_host.get().strip(), port=port,
                            security=self.smtp_security.get(), username=self.smtp_user.get().strip())

    def _make_smtp(self) -> SmtpMailer | None:
        settings = self._smtp_from_fields()
        problems = settings.validate()
        password = self.smtp_password.get()
        if not password:
            problems.append("Enter the password (for Gmail: an App Password).")
        if problems:
            messagebox.showerror("Email account", "\n".join(f"• {p}" for p in problems), parent=self)
            return None
        if "gmail" in settings.host.lower() and not looks_like_gmail_app_password(password):
            n = len(normalise_password(settings.host, password))
            if not messagebox.askyesno(
                    "Gmail App Password needed",
                    f"The password you entered has {n} characters. Gmail no longer lets apps sign in with your "
                    "normal Gmail password (the one you use in the browser) - it needs an App Password: exactly "
                    "16 letters, created at myaccount.google.com/apppasswords (2-Step Verification must be on).\n\n"
                    "Try with this password anyway?", icon="warning", parent=self):
                return None
        try:
            save_smtp_settings(settings)
        except OSError as exc:
            log.warning("Could not save email account settings: %s", exc)
        account = secret_account("smtp", settings.username)
        if self.smtp_remember.get():
            try:
                save_secret(account, password)
            except KeyStoreError as exc:
                self.smtp_status.configure(text=f"Password not saved: {exc}", text_color=theme.WARNING)
        sender = self._profile()
        return SmtpMailer(settings, password, sender.name, sender.email or settings.username)

    def _test_smtp(self):
        mailer = self._make_smtp()
        if mailer is None:
            return
        self.smtp_test_btn.configure(state="disabled", text="Testing…")
        self.smtp_status.configure(text="Connecting…", text_color=theme.MUTED)

        def work():
            try:
                self.q.put(("smtp", True, mailer.test(), ""))
            except Exception as exc:  # noqa: BLE001
                try:  # run the step-by-step check so the user (or IT) sees exactly where it stops
                    report = mailer.diagnosis_text(mailer.diagnose())
                except Exception as dexc:  # noqa: BLE001
                    report = f"Diagnosis could not run: {dexc}"
                self.q.put(("smtp", False, str(exc), report))

        threading.Thread(target=work, daemon=True).start()

    def _show_diagnosis(self, report: str):
        """Step-by-step result of the connection test, selectable so it can be copied to IT / support."""
        win = ctk.CTkToplevel(self)
        win.title("Email account - connection test")
        win.configure(fg_color=theme.BG)
        win.geometry("860x420")
        win.after(200, win.lift)
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(win, text="Where the connection stopped (OK = step worked, FAIL = step failed). The password is "
                               "not shown. Select the text and copy it if you need to send it to IT.",
                     wraplength=820, justify="left", anchor="w", font=self._font(12), text_color=theme.TEXT).grid(
            row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        box = ctk.CTkTextbox(win, wrap="word", fg_color=theme.ENTRY_BG, font=self._font(12))
        box.grid(row=1, column=0, sticky="nsew", padx=14)
        box.insert("1.0", report)
        self._button(win, "Close", win.destroy, "ghost", height=32, width=100).grid(row=2, column=0, sticky="e",
                                                                                   padx=14, pady=12)

    def _forget_smtp_password(self):
        user = self.smtp_user.get().strip()
        if user:
            delete_secret(secret_account("smtp", user))
        self.smtp_password.delete(0, "end")
        self.smtp_remember.set(False)
        self.smtp_status.configure(text="Saved password removed from this computer.", text_color=theme.MUTED)

    def _on_delivery_change(self, label: str):
        if DELIVERY_LABELS.get(label) == MODE_SMTP:
            self.smtp_frame.grid(row=5, column=0, sticky="ew", padx=16, pady=(8, 0))
        else:
            self.smtp_frame.grid_forget()
        self._update_counts()

    # ---------------------------------------------------------- recipients
    def _download_template(self, group: str):
        name = "Client_list_template.xlsx" if group == GROUP_CLIENT else "Employee_list_template.xlsx"
        path = filedialog.asksaveasfilename(parent=self, title=f"Save {group.lower()} list template",
                                            defaultextension=".xlsx", initialfile=name,
                                            filetypes=[("Excel workbook", "*.xlsx")])
        if not path:
            return
        try:
            create_template(path, group)
            self._set_status(f"✓ Template saved: {Path(path).name}. Fill it in, save, then click "
                             f"'Load {group.lower()}s list…'.", theme.SUCCESS)
        except PermissionError:
            messagebox.showerror("Template", "The file is open in Excel or the folder is read-only.", parent=self)

    def _load_recipients(self, group: str):
        path = filedialog.askopenfilename(parent=self, title=f"Select the {group.lower()} list",
                                          filetypes=[("Excel or CSV", "*.xlsx *.xlsm *.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            result = load_recipients(path, default_group=group)
        except RecipientFileError as exc:
            messagebox.showerror("Recipient list", str(exc), parent=self)
            return
        except PermissionError:
            messagebox.showerror("Recipient list", "The file is open in another program. Close it and try again.",
                                 parent=self)
            return
        self.set_list(group, result.recipients, result.errors + result.skipped, Path(path).name)
        try:
            self.store.save(group, result.recipients, Path(path).name)
            self.list_labels[group].configure(text=self.list_labels[group].cget("text") + "  •  saved for next time")
        except Exception as exc:  # noqa: BLE001 - the list is still usable for this session
            log.warning("Could not save the recipient list: %s", exc)

    def _load_saved_lists(self):
        """Open with the lists saved last time (no need to load the Excel file again)."""
        try:
            self.store = RecipientStore()
        except Exception as exc:  # noqa: BLE001
            log.warning("Saved recipient lists unavailable: %s", exc)
            self.store = None
            return
        for group in (GROUP_CLIENT, GROUP_EMPLOYEE):
            people, info = self.store.load(group)
            if info:
                self.set_list(group, people, [], "")
                who = "client" if group == GROUP_CLIENT else "employee"
                self.list_labels[group].configure(
                    text=f"Saved list: {len(people)} {who}(s) - from {info['file_name'] or 'Excel'} on "
                         f"{info['saved_at']}", text_color=theme.TEXT)
            self.forget_btns[group].grid() if info else self.forget_btns[group].grid_remove()

    def _forget_list(self, group: str):
        who = "client" if group == GROUP_CLIENT else "employee"
        if not messagebox.askyesno("Forget saved list", f"Delete the saved {who} list from this computer? "
                                   "Your Excel file is not affected.", parent=self):
            return
        if self.store:
            self.store.forget(group)
        self.set_list(group, [], [], "")
        self.list_labels[group].configure(text="Not loaded", text_color=theme.MUTED)
        self.forget_btns[group].grid_remove()

    def set_list(self, group: str, recipients: list, issues: list, file_name: str = ""):
        for r in recipients:
            r.group = group
        self.loaded[group] = recipients
        self.load_issues[group] = issues
        n = len(recipients)
        text = f"{file_name}: {n} {'client' if group == GROUP_CLIENT else 'employee'}(s)"
        if issues:
            text += f", {len(issues)} row(s) not loaded"
        self.list_labels[group].configure(text=text, text_color=theme.WARNING if issues else theme.TEXT)
        if hasattr(self, "forget_btns"):
            self.forget_btns[group].grid() if recipients else self.forget_btns[group].grid_remove()
        self.recipients = self.loaded[GROUP_CLIENT] + self.loaded[GROUP_EMPLOYEE]
        self._issues = self.load_issues[GROUP_CLIENT] + self.load_issues[GROUP_EMPLOYEE]
        self._draw_recipients()

    def _draw_recipients(self):
        for w in self.recip_list.winfo_children():
            w.destroy()
        self.recipient_vars = []
        groups = self._active_versions()
        shown = 0
        for i, r in enumerate(self.recipients):
            var = ctk.BooleanVar(value=r.group in groups)
            if r.group in groups:
                tag = "Team" if r.group == GROUP_EMPLOYEE else "Client"
                label = f"[{tag}]  {r.name}  <{r.email}>" + (f"  –  {r.company}" if r.company else "")
                ctk.CTkCheckBox(self.recip_list, text=label, variable=var, command=self._update_counts,
                                fg_color=theme.PURPLE, hover_color=theme.PURPLE_HOVER, font=self._font(12)).grid(
                    row=i, column=0, sticky="w", pady=1)
                shown += 1
            self.recipient_vars.append(var)
        if not self.recipients:
            return
        msg = "" if shown else f"No one loaded in the '{self.audience.get()}' group yet."
        self.recip_info.configure(text=msg, text_color=theme.WARNING)
        if self._issues:
            self.recip_issues_btn.grid(row=4, column=0, sticky="ew", pady=(0, 4))
        else:
            self.recip_issues_btn.grid_forget()
        self._update_counts()

    def _on_audience(self, _value=None):
        self._draw_recipients()
        if self._tab_group() not in self._active_versions():
            self.version_tabs.set(VERSION_TAB[self._active_versions()[0]])
        self._update_counts()

    def _tab_group(self) -> str:
        return next((g for g, name in VERSION_TAB.items() if name == self.version_tabs.get()), GROUP_CLIENT)

    def _on_version_tab(self):
        """Opening the Team (employees) tab while 'Send to' is Clients (or the reverse) switches 'Send to' to
        that group, so the buttons always act on the version you are looking at. 'Both' stays 'Both'."""
        group = self._tab_group()
        if group not in self._active_versions():
            self.audience.set("Employees" if group == GROUP_EMPLOYEE else "Clients")
            self._draw_recipients()
            self._update_counts()
            self._refresh_approval()
            self._set_status(f"Send to: {self.audience.get()} (switched to match the {VERSION_TAB[group].lower()}).",
                             theme.MUTED)

    def _group_names(self) -> str:
        return " and ".join("employees" if g == GROUP_EMPLOYEE else "clients" for g in self._active_versions())

    def _show_issues(self):
        messagebox.showinfo("Rows not loaded", "\n".join(self._issues[:40]) +
                            ("\n…" if len(self._issues) > 40 else ""), parent=self)

    def _select_all(self, value: bool):
        groups = self._active_versions()
        for r, var in zip(self.recipients, self.recipient_vars):
            var.set(value and r.group in groups)
        self._update_counts()

    def _selected(self) -> list[Recipient]:
        groups = self._active_versions()
        return [r for r, v in zip(self.recipients, self.recipient_vars) if v.get() and r.group in groups]

    def _blank_drafts_allowed(self) -> bool:
        return DELIVERY_LABELS.get(self.delivery.get(), MODE_DRAFT) in (MODE_DRAFT, MODE_EML)

    def _update_counts(self):
        n = len(self._selected())
        mode = DELIVERY_LABELS.get(self.delivery.get(), MODE_DRAFT)
        if n == 0 and self._blank_drafts_allowed():
            k = len(self._active_versions())
            noun = "draft" if mode == MODE_DRAFT else "email file"
            _conf(self.send_btn, text=f"{'Create' if mode == MODE_DRAFT else 'Save'} {k} {noun}{'s' if k > 1 else ''}"
                                         " (no recipient)")
            return
        verb = {MODE_DRAFT: "Create", MODE_SEND: "Send", MODE_SMTP: "Send", MODE_EML: "Save"}.get(mode, "Create")
        noun = "draft" if mode == MODE_DRAFT else "email"
        _conf(self.send_btn, text=f"{verb} {n} {noun}{'s' if n != 1 else ''}")

    # ------------------------------------------------------------- content
    def _rebuild_body(self, confirm=True):
        numbers = {g: [n for n, var in self.section_vars[g].items() if var.get()] for g in self.section_vars}
        for g in self._active_versions():
            if not numbers[g]:
                messagebox.showerror("Sections", f"Select at least one section for the {VERSION_TAB[g].lower()}.",
                                     parent=self)
                return
        has_text = any(w["body"].get("1.0", "end").strip() for w in self.version_widgets.values())
        if confirm and has_text and not messagebox.askyesno(
                "Rebuild email text", "This replaces the email content of both versions (and any edits you made) "
                                      "with fresh text from the analysis. Continue?", parent=self):
            return
        texts = {
            GROUP_CLIENT: build_client_body(self.report, numbers[GROUP_CLIENT] or [2]),
            GROUP_EMPLOYEE: build_internal_body(self.report, numbers[GROUP_EMPLOYEE] or [2],
                                                getattr(self.result, "register_ref", "")),
        }
        for g, text in texts.items():
            self.version_widgets[g]["body"].set_text(text)

    def _content(self, group: str = GROUP_CLIENT) -> EmailContent:
        w = self.version_widgets[group]
        return EmailContent(subject=w["subject"].get().strip(), intro=w["intro"].get("1.0", "end").strip(),
                            body_markdown=w["body"].get("1.0", "end").strip(), sender=self._profile(),
                            disclaimer=w["note"].get().strip())

    def _fingerprint(self) -> str:
        """Hash of everything that will be sent (all versions in use) - stored in the audit log."""
        parts = [self.audience.get()] + [f"{g}:{self._content(g).fingerprint()}" for g in self._active_versions()]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]

    def _refresh_review(self):
        blocking, warnings = [], []
        for g in self._active_versions():
            w = self.version_widgets[g]
            items = find_review_items(w["body"].get("1.0", "end"))
            extra = find_review_items(w["subject"].get() + "\n" + w["intro"].get("1.0", "end"))
            blocking += [(g, i) for i in items + extra if i.blocking]
            warnings += [(g, i) for i in items if not i.blocking]
        if blocking:
            lines = "\n".join(f"  • {VERSION_TAB[g]}, line {i.line_no}: {i.text[:100]}" for g, i in blocking[:4])
            _conf(self.review_label,
                text=f"✗ {len(blocking)} point(s) marked [Uncertain] must be corrected or deleted before "
                     f"approval:\n{lines}", text_color=theme.DANGER)
        elif warnings:
            _conf(self.review_label,
                text=f"⚠ {len(warnings)} point(s) say 'Not stated in the judgment' - check they are appropriate "
                     "(e.g. " + ", ".join(f"{VERSION_TAB[g]} line {i.line_no}" for g, i in warnings[:4]) + ").",
                text_color=theme.WARNING)
        else:
            _conf(self.review_label, text="✓ No [Uncertain] points in the email content.",
                                        text_color=theme.SUCCESS)
        return blocking

    def _quality_blockers(self) -> list[str]:
        """The analysis itself must be approved in the main window (Review & Approve)."""
        blocked = getattr(self.result, "email_blocked", "")
        if blocked:
            return [blocked]
        if not getattr(self.result, "is_approved", False):
            return ["The analysis has changed since it was approved. Approve it again in the main window "
                    "(Review & Approve)."]
        return self._client_blockers()

    # ------------------------------------------------- who may receive what
    def _register_status(self) -> str:
        """Live status of the register entry (Draft / Returned / Verified), '' if not in the register."""
        ref = getattr(self.result, "register_ref", "")
        live = self.master.register_status(ref) if ref and hasattr(self.master, "register_status") else ""
        return live or getattr(self.result, "register_status", "")

    def _client_blockers(self) -> list[str]:
        """Client emails go out only for a VERIFIED register entry, and only with client content."""
        if GROUP_CLIENT not in self._active_versions():
            return []
        out = []
        ref, status = getattr(self.result, "register_ref", ""), self._register_status()
        if not ref:
            out.append("Client emails need a judgment that is in the precedent register and verified by a "
                       "reviewer. This analysis was not saved to the register - save it (Review & Approve), have it "
                       "verified, then email clients. You can send the Team version to employees now.")
        elif status != "Verified":
            why = {"Draft": "Draft - approved by the preparer but not yet checked by a reviewer. Ask the reviewer to "
                            "'Mark verified' in the register",
                   "Returned": "Returned for correction - correct it with 'Update details', then have it verified"
                   }.get(status, "not found in the register - check the register location")
            out.append(f"Client emails need a verified entry. {ref} is {why}. Meanwhile you can choose "
                       "Send to: Employees.")
        w = self.version_widgets[GROUP_CLIENT]
        marks = team_markers_in_client(w["subject"].get(), w["intro"].get("1.0", "end"),
                                       w["body"].get("1.0", "end"))
        if marks:
            out.append("The CLIENT version contains team (internal) material: " + "; ".join(marks) + ". Correct the "
                       "Client version or click 'Rebuild email text from analysis'.")
        return out

    def _audience_warnings(self) -> list[str]:
        warns = []
        if GROUP_EMPLOYEE in self._active_versions():
            w = self.version_widgets[GROUP_EMPLOYEE]
            marks = client_markers_in_team(w["subject"].get(), w["intro"].get("1.0", "end"),
                                           w["body"].get("1.0", "end"))
            if marks:
                warns.append("The TEAM version looks like client content: " + "; ".join(marks) + ".")
        if len(self._active_versions()) == 2 and self._content(GROUP_CLIENT).body_markdown.strip() == \
                self._content(GROUP_EMPLOYEE).body_markdown.strip():
            warns.append("The Client and Team versions have exactly the same content.")
        sel = self._selected()
        warns += recipient_warnings([r for r in sel if r.group == GROUP_CLIENT],
                                    [r for r in sel if r.group == GROUP_EMPLOYEE], self._profile().email)
        return warns

    def _refresh_quality(self):
        r = self.result
        status = self._register_status()
        if getattr(r, "status_line", ""):
            text, color = r.status_line
        elif getattr(r, "is_approved", False):
            ref = f"  •  Register {r.register_ref} ({status or 'not saved'})" if r.register_ref else \
                "  •  not in the register"
            text, color = f"✓ Analysis approved by {r.approved_by} on {r.approved_at}{ref}", theme.SUCCESS
        else:
            text, color = "⚠ The analysis is not approved (approve it in the main window first).", theme.WARNING
        if status != "Verified":
            text += "\nClient emails need a verified register entry; the Team version can be sent now."
            color = theme.WARNING
        self.quality_label.configure(text=text, text_color=color)

    def _approved_now(self) -> bool:
        return self.approved_fingerprint is not None and self.approved_fingerprint == self._fingerprint()

    def _refresh_approval(self):
        if self._approved_now():
            _conf(self.approval_label, text=f"✓ Approved by {self._profile().name} at {self.approved_at}",
                                          text_color=theme.SUCCESS)
            _conf(self.send_btn, state="normal" if not self.busy else "disabled")
        else:
            if self.approved_fingerprint is not None:
                self.approved_fingerprint = None
                self.reviewed_var.set(False)
                _conf(self.approval_label, text="Content or recipients group changed after approval - please "
                                                   "review and approve again.", text_color=theme.WARNING)
            elif not self.approval_label.cget("text").startswith("Content"):
                _conf(self.approval_label, text="Not yet approved. Emails cannot be created until you approve.",
                                              text_color=theme.MUTED)
            _conf(self.send_btn, state="disabled")

    def _approve(self):
        self._refresh_quality()
        if self._refresh_review():
            messagebox.showerror("Cannot approve yet", "Correct or delete every point marked [Uncertain] first. "
                                 "These are places where the AI was not sure; they must not be sent unverified.",
                                 parent=self)
            return
        quality = self._quality_blockers()
        if quality:
            messagebox.showerror("Cannot approve yet", "\n\n".join(f"• {p}" for p in quality), parent=self)
            return
        if not self.reviewed_var.get():
            messagebox.showerror("Confirm review", "Tick the box to confirm you have reviewed the content.",
                                 parent=self)
            return
        problems = self._profile().validate()
        for g in self._active_versions():
            content = self._content(g)
            if not content.subject:
                problems.append(f"Enter a subject for the {VERSION_TAB[g].lower()}.")
            if not content.body_markdown:
                problems.append(f"The {VERSION_TAB[g].lower()} is empty.")
        if problems:
            messagebox.showerror("Cannot approve yet", "\n".join(f"• {p}" for p in problems), parent=self)
            return
        warns = self._audience_warnings()
        if warns and not messagebox.askyesno("Check before approving", "\n\n".join(f"• {w}" for w in warns) +
                                             "\n\nApprove anyway?", icon="warning", parent=self):
            return
        from datetime import datetime

        self._save_profile(quiet=True)
        self.approved_fingerprint = self._fingerprint()
        self.approved_at = datetime.now().strftime("%d %b %Y %H:%M")
        log.info("Email content approved (fingerprint %s)", self.approved_fingerprint)
        self._refresh_approval()

    # ------------------------------------------------------------ delivery
    def _preview(self):
        group = self._tab_group()
        recips = [r for r in self._selected() if r.group == group]
        r = recips[0] if recips else Recipient(name="Recipient Name", email="someone@example.com", salutation="Mr")
        msg = render_email(self._content(group), r.name, r.email, r.salutation)
        esc = html.escape
        page = (f"<html><head><meta charset='utf-8'><title>{esc(msg.subject)}</title></head>"
                f"<body style='background:#EEF0F7;padding:24px;'><div style='max-width:760px;margin:auto;"
                f"background:#fff;padding:24px;border-radius:8px;'><p style='font:13px Calibri,Arial;color:#555'>"
                f"<b>{esc(VERSION_TAB[group])}</b><br><b>To:</b> {esc(r.name)} &lt;{esc(r.email)}&gt;<br>"
                f"<b>Subject:</b> {esc(msg.subject)}</p><hr>{msg.html}</div></body></html>")
        fd, path = tempfile.mkstemp(prefix="jia_preview_", suffix=".html")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(page)
        webbrowser.open(Path(path).as_uri())

    def _audit_base(self) -> dict:
        sender = self._profile()
        return {"Approved by": sender.name, "Sender email": sender.email,
                "Judgment file": self.result.document.info.file_name, "Case title": self.case_title,
                "Register ref": getattr(self.result, "register_ref", ""), "Content fingerprint": self._fingerprint()}

    def _send_test(self):
        sender = self._profile()
        problems = sender.validate()
        if problems:
            messagebox.showerror("Sender details", "\n".join(f"• {p}" for p in problems), parent=self)
            return
        versions = self._active_versions()
        messages = [render_email(self._content(g), sender.name, sender.email,
                                 subject_prefix="[TEST - DRAFT FOR INTERNAL REVIEW] ") for g in versions]
        mode = DELIVERY_LABELS.get(self.delivery.get())
        if mode == MODE_SMTP:
            smtp = self._make_smtp()
            if smtp is not None:
                self._start(messages, MODE_TEST, groups=versions, smtp=smtp)
        elif self.outlook_ok and mode in (MODE_DRAFT, MODE_SEND):
            self._start(messages, MODE_TEST, groups=versions)
        else:
            folder = filedialog.askdirectory(parent=self, title="Folder for the test email(s) (.eml)")
            if folder:
                self._start(messages, MODE_EML, groups=versions, eml_folder=folder)

    def _send_all(self):
        self._refresh_approval()
        if not self._approved_now():
            messagebox.showerror("Not approved", "Approve the content first.", parent=self)
            return
        blockers = self._client_blockers()     # the register status may have changed since approval
        if blockers:
            messagebox.showerror("Cannot send to clients", "\n\n".join(f"• {b}" for b in blockers), parent=self)
            return
        recips = self._selected()
        mode = DELIVERY_LABELS[self.delivery.get()]
        if not recips and mode in (MODE_SEND, MODE_SMTP):
            names = self._group_names()
            messagebox.showerror("No recipients", f"Sending needs at least one recipient. 'Send to' is set to "
                                 f"{self.audience.get()}: load the {names} list (section 2) and tick at least one "
                                 "person.\n\nTo prepare the email without recipients, choose 'Create drafts in "
                                 "Outlook' or 'Save as .eml files'.", parent=self)
            return
        if not recips:
            self._create_blank(mode)
            return
        eml_folder = None
        smtp = None
        if mode == MODE_EML:
            eml_folder = filedialog.askdirectory(parent=self, title="Folder to save the .eml files")
            if not eml_folder:
                return
        if mode == MODE_SMTP:
            smtp = self._make_smtp()
            if smtp is None:
                return
        n_client = sum(1 for r in recips if r.group == GROUP_CLIENT)
        who = f"{n_client} client(s) and {len(recips) - n_client} employee(s)"
        question = {
            MODE_DRAFT: f"Create {len(recips)} draft email(s) ({who}) in your Outlook Drafts folder?\n\n"
                        "Nothing is sent - you can open and send them from Outlook.",
            MODE_SEND: f"SEND {len(recips)} email(s) ({who}) now from your Outlook?\n\nThis cannot be undone. "
                       "Each person receives a separate, personalised email.",
            MODE_SMTP: f"SEND {len(recips)} email(s) ({who}) now from {self.smtp_user.get().strip()}?\n\n"
                       "This cannot be undone. Each person receives a separate, personalised email. "
                       "Providers limit how many emails an account may send per day.",
            MODE_EML: f"Save {len(recips)} email file(s) (.eml) to the chosen folder?",
        }[mode]
        if not messagebox.askyesno("Confirm", question, icon="warning" if mode in (MODE_SEND, MODE_SMTP) else "question",
                                   parent=self):
            return
        contents = {g: self._content(g) for g in self._active_versions()}
        messages = [render_email(contents[r.group], r.name, r.email, r.salutation) for r in recips]
        self._start(messages, mode, groups=[r.group for r in recips], eml_folder=eml_folder, smtp=smtp)

    def _create_blank(self, mode):
        """Drafts / .eml files without a recipient, one per version in use - you add the recipients in Outlook."""
        versions = self._active_versions()
        eml_folder = None
        if mode == MODE_EML:
            eml_folder = filedialog.askdirectory(parent=self, title="Folder to save the .eml file(s)")
            if not eml_folder:
                return
        names = ", ".join(VERSION_TAB[g].lower() for g in versions)
        where = "in your Outlook Drafts folder" if mode == MODE_DRAFT else "as .eml files"
        if not messagebox.askyesno("Create without recipients",
                                   f"No recipients are selected. Create one email ({names}) {where} with the "
                                   "'To' line empty and the greeting 'Dear <<Recipient name>>,'?\n\nIn Outlook, "
                                   "add the recipients and replace the name before sending.", parent=self):
            return
        messages = []
        for g in versions:
            msg = render_email(self._content(g), "", "", greeting=BLANK_GREETING)
            msg.to_name = f"(no recipient - {VERSION_TAB[g]})"
            messages.append(msg)
        self._start(messages, mode, groups=versions, eml_folder=eml_folder)

    def _start(self, messages, mode, groups=None, eml_folder=None, smtp=None):
        self.busy = True
        self.cancel_event = threading.Event()
        self.cancel_btn.configure(state="normal", command=self.cancel_event.set)
        for b in (self.send_btn, self.test_btn):
            b.configure(state="disabled")
        self.progress.set(0)
        base = self._audit_base()
        sender_email = self._profile().email
        audit_path = self._audit_path()
        self._audit_warning = ""

        def work():
            try:
                outlook = (OutlookMailer(sender_email) if smtp is None and mode in (MODE_DRAFT, MODE_SEND, MODE_TEST)
                           else None)
                results = deliver_batch(messages, mode, base, outlook=outlook, eml_folder=eml_folder,
                                        progress=lambda d, t, m: self.q.put(("progress", d / max(t, 1), m)),
                                        cancel_event=self.cancel_event, audit_path=audit_path,
                                        on_warning=lambda w: setattr(self, "_audit_warning", w),
                                        smtp=smtp, groups=groups, pause_s=1.0 if smtp else 0.4)
                self.q.put(("done", mode, results, eml_folder, smtp is not None))
            except CancelledError:
                self.q.put(("cancelled",))
            except Exception as exc:  # noqa: BLE001
                log.exception("Email delivery failed")
                self.q.put(("error", str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _finish(self, item):
        self.busy = False
        self.cancel_btn.configure(state="disabled")
        self.test_btn.configure(state="normal")
        kind = item[0]
        if kind == "cancelled":
            self._set_status("Stopped. Emails already created/sent are listed in the audit log.", theme.WARNING)
        elif kind == "error":
            self._set_status(f"✗ {item[1]}", theme.DANGER)
        else:
            _, mode, results, folder, via_smtp = item
            ok = sum(r.ok for r in results)
            failed = [r for r in results if not r.ok]
            where = {MODE_DRAFT: "in your Outlook Drafts folder", MODE_SEND: "sent from Outlook",
                     MODE_SMTP: "sent from your email account",
                     MODE_TEST: "sent to you", MODE_EML: f"saved to {folder}"}[mode]
            msg = f"✓ {ok} {'draft' if mode == MODE_DRAFT else 'email'}(s) {where}."
            if failed:
                msg += f"  ✗ {len(failed)} failed: " + "; ".join(f"{r.email} ({r.error})" for r in failed[:3])
            if failed and not ok and via_smtp:
                msg = ("✗ Nothing was sent - the email account could not sign in. Click 'Test sign-in' (email "
                       "account panel) for the step-by-step check, or choose 'Create drafts in Outlook' / "
                       f"'Save as .eml files'. Details: {failed[0].error[:200]}")
            if self._audit_warning:
                msg += "  ⚠ " + self._audit_warning
            self._set_status(msg, theme.DANGER if failed and not ok else
                             theme.WARNING if failed or self._audit_warning else theme.SUCCESS)
            self.progress.set(1)
            if mode == MODE_EML and folder and ok:
                self._open_path(folder)
        self._refresh_approval()

    # ------------------------------------------------------------ audit log
    def _audit_dir_setting(self) -> str:
        return getattr(self.app_settings, "audit_log_dir", "") if self.app_settings else ""

    def _audit_path(self) -> Path:
        folder = self._audit_dir_setting()
        if folder and not Path(folder).is_dir():
            log.warning("Audit log folder %s is not available; using Downloads", folder)
            folder = ""
        return audit_log_path(folder or None)

    def _init_audit_location(self):
        path = self._audit_path()
        if carry_over_audit(path):
            self._set_status(f"Earlier audit entries were copied to {path}.", theme.SUCCESS)
        self.audit_label.configure(text=str(path))

    def _change_audit_dir(self):
        folder = filedialog.askdirectory(parent=self, title="Choose the folder for the email audit log "
                                                            "(e.g. a OneDrive / SharePoint folder)",
                                         initialdir=str(self._audit_path().parent))
        if not folder:
            return
        if not os.access(folder, os.W_OK):
            messagebox.showerror("Audit log", "You don't have permission to save files in that folder.", parent=self)
            return
        if self.app_settings is not None:
            self.app_settings.audit_log_dir = folder
            try:
                save_settings(self.app_settings)
            except OSError as exc:
                log.warning("Could not save settings: %s", exc)
        self._init_audit_location()
        self._set_status(f"Audit log will be saved in {folder}.", theme.SUCCESS)

    def _open_audit(self):
        path = self._audit_path()
        if not path.exists():
            messagebox.showinfo("Audit log", f"No emails have been recorded yet.\n\nThe log will be created "
                                             f"here after the first email (including 'Send test to me'):\n{path}",
                                parent=self)
            return
        try:
            if repair_audit_log(path):
                self._set_status("The audit log from an earlier version had an old header - columns realigned "
                                 "(original kept as a backup copy in the same folder).", theme.SUCCESS)
        except OSError as exc:
            log.warning("Audit log not repaired: %s", exc)
        xlsx = write_audit_xlsx(path) or (audit_xlsx_path(path) if audit_xlsx_path(path).exists() else None)
        target = xlsx or path
        self._set_status(f"Audit log: {target}  (formatted Excel copy of {path.name})" if xlsx else
                         f"Audit log file: {path}")
        self._open_path(target)

    @staticmethod
    def _open_path(path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # noqa: S606 - opens with the default app
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            log.info("Could not open %s: %s", path, exc)

    def _set_status(self, text, color=None):
        self.status.configure(text=text, text_color=color or theme.TEXT)

    def _close(self):
        """Close button and window [X]. Warns if emails are being created or approved content would be lost."""
        if self.busy:
            if not messagebox.askyesno("Emails in progress", "Emails are still being created. Stop after the "
                                       "current one and close this window?", parent=self):
                return
            self.cancel_event.set()
        self._save_profile(quiet=True)
        if getattr(self, "store", None) is not None:
            self.store.close()
        self.destroy()

    def refresh_from_result(self):
        """Called by the main window after key facts are confirmed / the register reference changes."""
        self._refresh_quality()

    # ---------------------------------------------------------------- loop
    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "progress":
                    self.progress.set(item[1])
                    self._set_status(item[2])
                elif item[0] == "smtp":
                    _, ok, text, report = item
                    self.smtp_test_btn.configure(state="normal", text="Test sign-in")
                    self.smtp_status.configure(text=("✓ " if ok else "✗ ") + text,
                                               text_color=theme.SUCCESS if ok else theme.DANGER)
                    if not ok and report:
                        self._show_diagnosis(report)
                else:
                    self._finish(item)
        except queue.Empty:
            pass
        if not self.busy:
            self._refresh_review()
            self._refresh_approval()
            self._update_counts()
        if self.winfo_exists():
            self.after(400, self._poll)
