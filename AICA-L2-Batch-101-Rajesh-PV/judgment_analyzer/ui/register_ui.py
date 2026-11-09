"""Precedent register windows: confirm key facts and save, browse/search, view, verify, compare."""

from __future__ import annotations

import logging
from dataclasses import dataclass
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from ..compare import compare_records
from ..consistency import DIFFERS, FAVOUR, FIELDS, OUTCOMES, facts_without_ai
from ..email_composer import (extract_case_title, extract_citation, extract_judgment_date,
                              load_sender_profile)
from ..exporter import build_export_document, build_final_document, safe_filename, save_docx
from ..prompts import DISCLAIMER_TITLE
from ..repository import (ACT_1961, ACT_2025, ACT_EITHER, STATUS_RETURNED, STATUSES, STATUS_VERIFIED, JudgmentRecord, RegisterError, Repository, export_xlsx,
                          file_sha256, record_from_result)
from ..prompts import REPORT_SECTIONS
from ..response_parser import ParsedReport, parse_report
from ..sections_act import definite_act, sort_sections
from . import theme
from .widgets import Card, MarkdownView, bring_to_front

log = logging.getLogger(__name__)


def _font(size=13, weight="normal"):
    return ctk.CTkFont(theme.FONT_FAMILY, size, weight)


def _button(parent, text, cmd, kind="navy", **kw):
    colors = {"navy": (theme.BTN_NAVY, theme.BTN_NAVY_HOVER, theme.WHITE),
              "purple": (theme.PURPLE, theme.PURPLE_HOVER, theme.WHITE),
              "gold": (theme.GOLD, theme.GOLD_HOVER, theme.NAVY),
              "danger": (theme.DANGER, theme.DANGER_HOVER, theme.WHITE),
              "amber": ("#B7791F", "#975A16", theme.WHITE),
              "slate": ("#6B7285", "#565D70", theme.WHITE),
              "ghost": ("transparent", theme.CARD_BORDER, theme.TEXT)}[kind]
    extra = {"border_width": 1, "border_color": theme.CARD_BORDER} if kind == "ghost" else {}
    return ctk.CTkButton(parent, text=text, command=cmd, fg_color=colors[0], hover_color=colors[1],
                         text_color=colors[2], font=_font(12, "bold"), **extra, **kw)


def open_path(path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        log.info("Could not open %s: %s", path, exc)


def _fit(win, w=1100, h=820):
    try:
        from customtkinter import ScalingTracker
        scale = ScalingTracker.get_window_scaling(win)
    except Exception:
        scale = 1.0
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{int(min(w, sw * 0.94 / scale))}x{int(min(h, sh * 0.88 / scale))}+30+20")


def facts_from_report(report) -> dict:
    """Fallback key facts (when the consistency check was not run) from the report's Case Details."""
    return {"case_title": extract_case_title(report), "citation": extract_citation(report),
            "judgment_date": extract_judgment_date(report)}


# ======================================================================
class ApprovalDialog(ctk.CTkToplevel):
    """Review & Approve: the reviewer confirms the key facts (choosing between the two AI readings where
    they differ), acknowledges the Source Check, optionally saves to the register, and approves. Only an
    approved analysis can be saved as Word / PDF / text or emailed."""

    def __init__(self, app, result, repo: Repository, on_done=None):
        super().__init__(app)
        self.app, self.result, self.repo, self.on_done = app, result, repo, on_done
        self.title("Review and approve the analysis")
        self.configure(fg_color=theme.BG)
        _fit(self, 1040, 900)
        bring_to_front(self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.q: queue.Queue = queue.Queue()

        cons = result.consistency
        self.comparisons = {f.key: f for f in cons.fields} if cons and cons.ok else {}
        if result.key_facts:
            base = dict(result.key_facts)
        else:
            try:
                source = result.source_text
            except Exception:  # noqa: BLE001
                source = ""
            base = facts_without_ai(result.report, source)
        self.filled = set(getattr(result, "facts_filled", []) or ([] if result.key_facts else list(base)))

        ctk.CTkLabel(self, text="Approve only after you have read the analysis. Approval is required before the "
                                "analysis can be saved as Word / PDF, emailed or added to the precedent register. "
                                "If you edit the analysis later, it must be approved again.",
                     wraplength=980, justify="left", anchor="w", font=_font(12), text_color=theme.TEXT).grid(
            row=0, column=0, sticky="ew", padx=16, pady=(14, 6))

        body = ctk.CTkScrollableFrame(self, fg_color=theme.CARD)
        body.grid(row=1, column=0, sticky="nsew", padx=16)
        body.grid_columnconfigure(1, weight=1)
        self.body = body
        r = self._heading(body, 0, "1  •  Key facts")
        intro = ("The AI read the key facts twice, independently. Where the two readings differ (marked ✗ in red), "
                 "choose Reading 1 or Reading 2 - or type the correct value yourself - after checking the judgment.")
        if not self.comparisons:
            intro = "The AI read the key facts once (double-check is switched off). Check each fact against the judgment."
        if getattr(result, "facts_problem", "") and not self.comparisons:
            intro = "Check each fact against the judgment."
        ctk.CTkLabel(body, text=intro, wraplength=900, justify="left", anchor="w", font=_font(12),
                     text_color=theme.MUTED).grid(row=r, column=0, columnspan=2, sticky="ew", padx=10)
        r += 1
        problem = getattr(result, "facts_problem", "")
        if problem:
            ctk.CTkLabel(body, text=f"⚠ {problem}\nFields marked ⓘ below were taken from the report and the judgment "
                                    "text instead; empty fields could not be found - fill them in from the judgment.",
                         wraplength=900, justify="left", anchor="w", font=_font(12, "bold"),
                         text_color=theme.WARNING).grid(row=r, column=0, columnspan=2, sticky="ew", padx=10,
                                                        pady=(4, 0))
            r += 1
        self.widgets: dict[str, tuple[str, object]] = {}
        self.choice_vars: dict[str, ctk.StringVar] = {}
        for key, label, kind in FIELDS:
            comp = self.comparisons.get(key)
            value = base.get(key, [] if kind in ("list", "issues") else "")
            ctk.CTkLabel(body, text=label, font=_font(12, "bold"), text_color=theme.MUTED, anchor="w").grid(
                row=r, column=0, sticky="nw", padx=(10, 12), pady=(10, 0))
            w = self._make_widget(body, key, kind, value, comp)
            w.grid(row=r, column=1, sticky="ew", padx=(0, 10), pady=(10, 0))
            self.widgets[key] = (kind, w)
            r += 1
            if comp and comp.status == DIFFERS:
                r = self._choice_row(body, r, key, kind, comp)
            elif comp and comp.status != "Agree":
                ctk.CTkLabel(body, text="ⓘ Both readings say the same thing in different words.", font=_font(11),
                             text_color=theme.MUTED, anchor="w").grid(row=r, column=1, sticky="w")
                r += 1
            if key in self.filled:
                ctk.CTkLabel(body, text="ⓘ taken from the report / judgment text (not the AI reading) - check",
                             font=_font(11), text_color=theme.MUTED, anchor="w").grid(row=r, column=1, sticky="w")
                r += 1
            if comp and comp.in_source is not None:
                ctk.CTkLabel(body, text="✓ found in the judgment text" if comp.in_source else
                             "⚠ not found in the judgment text - check", font=_font(11),
                             text_color=theme.SUCCESS if comp.in_source else theme.WARNING, anchor="w").grid(
                    row=r, column=1, sticky="w")
                r += 1
            if key == "citation":
                r = self._citation_tools(body, r)
            if key == "sections_2025":
                r = self._act_tools(body, r)

        # 2. Source Check
        r = self._heading(body, r, "2  •  Source Check")
        v = result.verification
        self.sources_var = ctk.BooleanVar(value=False)
        self.needs_source_ack = bool(v and v.not_found)
        if v is None:
            text = "Source Check was not run."
        elif not v.not_found:
            text = f"✓ {v.summary_line()}"
        else:
            items = "\n".join(f"   • {i.kind}: {i.text}" + (f"  ({i.section})" if i.section else "")
                              for i in v.not_found[:8])
            more = f"\n   … and {len(v.not_found) - 8} more (see the Source Check tab)" if len(v.not_found) > 8 else ""
            text = (f"{len(v.not_found)} item(s) in the analysis were not found in the judgment text:\n{items}{more}\n"
                    "Correct or delete them with 'Edit this tab' if they are wrong.")
        ctk.CTkLabel(body, text=text, wraplength=900, justify="left", anchor="w", font=_font(12),
                     text_color=theme.WARNING if self.needs_source_ack else theme.TEXT).grid(
            row=r, column=0, columnspan=2, sticky="ew", padx=10)
        r += 1
        if self.needs_source_ack:
            ctk.CTkCheckBox(body, text="I have checked these items against the judgment.", variable=self.sources_var,
                            fg_color=theme.PURPLE, hover_color=theme.PURPLE_HOVER, font=_font(12)).grid(
                row=r, column=0, columnspan=2, sticky="w", padx=10, pady=(4, 0))
            r += 1

        # 3. Register
        r = self._heading(body, r, "3  •  Precedent register")
        self.save_var = ctk.BooleanVar(value=not result.register_ref)
        ctk.CTkCheckBox(body, text=f"Save to the precedent register  ({repo.path})", variable=self.save_var,
                        fg_color=theme.PURPLE, hover_color=theme.PURPLE_HOVER, font=_font(12)).grid(
            row=r, column=0, columnspan=2, sticky="w", padx=10)
        r += 1
        ctk.CTkLabel(body, text="Tags", font=_font(12, "bold"), text_color=theme.MUTED, anchor="w").grid(
            row=r, column=0, sticky="nw", padx=(10, 12), pady=(8, 0))
        self.tags = ctk.CTkEntry(body, fg_color=theme.ENTRY_BG,
                                 placeholder_text="comma separated, e.g. reassessment, audit objection, change of opinion")
        self.tags.grid(row=r, column=1, sticky="ew", padx=(0, 10), pady=(8, 0))
        r += 1
        self.copy_pdf = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(body, text="Store a copy of the PDF with the register (so the team can open the original)",
                        variable=self.copy_pdf, fg_color=theme.PURPLE, hover_color=theme.PURPLE_HOVER,
                        font=_font(12)).grid(row=r, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 0))
        r += 1

        # 4. Approver
        r = self._heading(body, r, "4  •  Approval")
        ctk.CTkLabel(body, text="Approved by", font=_font(12, "bold"), text_color=theme.MUTED, anchor="w").grid(
            row=r, column=0, sticky="nw", padx=(10, 12), pady=(4, 12))
        self.by = ctk.CTkEntry(body, fg_color=theme.ENTRY_BG, placeholder_text="Your name")
        self.by.insert(0, result.approved_by or load_sender_profile().name)
        self.by.grid(row=r, column=1, sticky="ew", padx=(0, 10), pady=(4, 12))

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", padx=16, pady=12)
        foot.grid_columnconfigure(0, weight=1)
        _button(foot, "Cancel", self.destroy, "ghost", width=110, height=38).grid(row=0, column=1, padx=6)
        _button(foot, "✔  Approve", self._approve, "gold", width=200, height=38).grid(row=0, column=2)
        self.after(200, self._poll)

    # ------------------------------------------------------------ building
    @staticmethod
    def _heading(body, r, text) -> int:
        ctk.CTkLabel(body, text=text, font=_font(14, "bold"), text_color=(theme.NAVY, theme.GOLD), anchor="w").grid(
            row=r, column=0, columnspan=2, sticky="w", padx=10, pady=(16, 4))
        return r + 1

    def _make_widget(self, body, key, kind, value, comp):
        if kind in ("list", "issues"):
            w = ctk.CTkTextbox(body, height=80 if kind == "list" else 120, fg_color=theme.ENTRY_BG, wrap="word")
            w.insert("1.0", "\n".join(value or []))
        elif kind == "choice":
            choices = OUTCOMES if key == "outcome" else FAVOUR
            values = list(dict.fromkeys([*(comp.display_values() if comp else []), *choices]))
            w = ctk.CTkComboBox(body, values=values, fg_color=theme.ENTRY_BG)
            w.set(value or "Not stated")
        elif kind == "prose":
            w = ctk.CTkTextbox(body, height=64, fg_color=theme.ENTRY_BG, wrap="word")
            w.insert("1.0", value or "")
        else:
            if key == "citation" and not self._has_citation(value):
                value = ""  # leave the box empty for the reviewer to type or look up
            w = ctk.CTkEntry(body, fg_color=theme.ENTRY_BG,
                             placeholder_text="Not reported in this copy" if key == "citation" else None)
            if value:
                w.insert(0, value)
        return w

    def _choice_row(self, body, r, key, kind, comp) -> int:
        frame = ctk.CTkFrame(body, fg_color=("#FBEDEC", "#3A1F22"), corner_radius=8)
        frame.grid(row=r, column=1, sticky="ew", padx=(0, 10), pady=(4, 0))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="✗ The two AI readings differ - choose the correct one:", font=_font(11, "bold"),
                     text_color=theme.DANGER, anchor="w").grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
        var = ctk.StringVar(value="1")
        self.choice_vars[key] = var
        options = [("1", f"Reading 1:  {comp.display_values()[0]}"), ("2", f"Reading 2:  {comp.display_values()[1]}")]
        if kind == "list":
            options.append(("both", "Both readings combined"))
        options.append(("own", "My own value (type it in the box above)"))
        for i, (val, text) in enumerate(options, 1):
            ctk.CTkRadioButton(frame, text=text, variable=var, value=val, font=_font(11), fg_color=theme.PURPLE,
                               hover_color=theme.PURPLE_HOVER,
                               command=lambda k=key: self._apply_choice(k)).grid(row=i, column=0, sticky="w",
                                                                                 padx=12, pady=2)
        ctk.CTkLabel(frame, text="").grid(row=len(options) + 1, column=0, pady=1)
        return r + 1

    def _apply_choice(self, key):
        choice = self.choice_vars[key].get()
        comp = self.comparisons[key]
        kind, w = self.widgets[key]
        if choice == "own":
            w.focus_set()
            return
        if choice == "both":
            value = list(dict.fromkeys([*comp.values[0], *comp.values[1]]))
        else:
            value = comp.values[0 if choice == "1" else 1]
        self._set_widget(w, value)
        if key in ("sections", "sections_2025"):
            self._refresh_act_notes()

    @staticmethod
    def _set_widget(w, value):
        if isinstance(w, ctk.CTkTextbox):
            w.delete("1.0", "end")
            w.insert("1.0", "\n".join(value) if isinstance(value, list) else (value or ""))
        elif isinstance(w, ctk.CTkComboBox):
            w.set(value or "Not stated")
        else:
            w.delete(0, "end")
            w.insert(0, value or "")

    CITATION_EMPTY_HINT = ("Not reported in this copy. Type the citation if you know it, or search the web. Recent "
                           "orders are often not yet reported - leave it blank and add it later in the precedent "
                           "register ('Update details…').")

    def _citation_tools(self, body, r) -> int:
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.grid(row=r, column=1, sticky="ew", padx=(0, 10), pady=(4, 0))
        row.grid_columnconfigure(1, weight=1)
        self.lookup_btn = _button(row, "🔎 Find reported citation online", self._lookup, "navy", height=28, width=230)
        self.use_btn = _button(row, "Use this citation", self._use_citation, "purple", height=28, width=150)
        self.lookup_label = ctk.CTkLabel(row, text="", wraplength=620, justify="left", anchor="w", font=_font(11),
                                         text_color=theme.MUTED)
        self.lookup_label.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self._suggestion = None
        _kind, entry = self.widgets["citation"]
        entry.bind("<KeyRelease>", lambda _e: self._refresh_citation_tools())
        self._refresh_citation_tools()
        return r + 1

    @staticmethod
    def _has_citation(text: str) -> bool:
        t = (text or "").strip().lower()
        return bool(t) and t not in ("not stated", "not reported", "n/a", "-", "nil")

    def _refresh_citation_tools(self):
        """The online search is offered only when the citation box is empty."""
        if self._suggestion is not None:
            return
        _kind, entry = self.widgets["citation"]
        if self._has_citation(entry.get()):
            self.lookup_btn.grid_remove()
            self.lookup_label.configure(text="")
        else:
            self.lookup_btn.grid(row=0, column=0, sticky="w")
            self.lookup_label.configure(text=self.CITATION_EMPTY_HINT, text_color=theme.MUTED)

    def _act_tools(self, body, r) -> int:
        ctk.CTkLabel(body, text="Sections are kept separately for the Income-tax Act, 1961 and the Income-tax Act, "
                                "2025. The 1961 Act has no section above 298, so higher numbers belong to the 2025 Act. "
                                "For numbers up to 298 check which Act the judgment names. Leave the 2025 box empty "
                                "if the judgment does not refer to the 2025 Act.",
                     wraplength=700, justify="left", anchor="w", font=_font(11), text_color=theme.MUTED).grid(
            row=r, column=1, sticky="ew", padx=(0, 10), pady=(4, 0))
        self.act_label = ctk.CTkLabel(body, text="", wraplength=700, justify="left", anchor="w", font=_font(11, "bold"),
                                      text_color=theme.WARNING)
        self.act_label.grid(row=r + 1, column=1, sticky="ew", padx=(0, 10))
        for key in ("sections", "sections_2025"):
            self.widgets[key][1].bind("<KeyRelease>", lambda _e: self._refresh_act_notes())
        self._refresh_act_notes()
        return r + 2

    def _act_check(self, values: dict | None = None):
        values = values or self._values()
        try:
            source = self.result.source_text
        except Exception:  # noqa: BLE001
            source = ""
        return sort_sections(values.get("sections", []), values.get("sections_2025", []), source)

    def _refresh_act_notes(self):
        notes = self._act_check().notes
        self.act_label.configure(text="\n".join(f"⚠ {n}" for n in notes))

    # ------------------------------------------------------------ actions
    def _values(self) -> dict:
        out = {}
        for key, (kind, w) in self.widgets.items():
            if isinstance(w, ctk.CTkTextbox):
                text = w.get("1.0", "end").strip()
                out[key] = [x.strip(" -•\t") for x in text.splitlines() if x.strip()] if kind in ("list", "issues") \
                    else text
            else:
                out[key] = w.get().strip()
        return out

    def _lookup(self):
        client = self.app._make_client()
        if client is None:
            return
        facts = self._values()
        self.lookup_btn.configure(state="disabled", text="Searching…")
        self.lookup_label.configure(text="Searching the web with Gemini (only the appeal number, forum, parties and "
                                         "date are sent)…", text_color=theme.MUTED)
        from ..citation_lookup import lookup_citation

        def work():
            try:
                self.q.put(("lookup", lookup_citation(client, facts)))
            except Exception as exc:  # noqa: BLE001
                self.q.put(("lookup_error", str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind, value = self.q.get_nowait()
                self.lookup_btn.configure(state="normal", text="🔎 Find reported citation online")
                if kind == "lookup_error":
                    self.lookup_label.configure(text=f"Online lookup is not available: {value}", text_color=theme.WARNING)
                elif value.found:
                    self._suggestion = value
                    srcs = "\n".join(f"   • {t or 'source'}: {u}" for t, u in value.sources)
                    self.lookup_label.configure(
                        text=f"Suggested citation: {value.citation}   (confidence: {value.confidence or 'n/a'})\n"
                             f"{value.note}\nSources:\n{srcs}\nCheck the source before using it.",
                        text_color=theme.TEXT)
                    self.use_btn.grid(row=0, column=1, sticky="w", padx=8)
                else:
                    self.lookup_label.configure(text="No reported citation was found online. " + (value.note or "")
                                                + " Type it if you have it, or leave it blank: the output will "
                                                  "identify the order by appeal number, forum and date, and you can "
                                                  "add the citation later in the register.", text_color=theme.MUTED)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(250, self._poll)

    def _use_citation(self):
        if self._suggestion:
            _kind, w = self.widgets["citation"]
            w.delete(0, "end")
            w.insert(0, self._suggestion.citation)
            self.use_btn.grid_remove()
            self.lookup_btn.grid_remove()

    def _approve(self):
        facts = self._values()
        by = self.by.get().strip()
        problems = []
        if not by:
            problems.append("Enter your name under 'Approved by'.")
        if not facts.get("case_title"):
            problems.append("Enter the case title.")
        wrong = [s for s in facts.get("sections", []) if definite_act(s) == "2025"]
        if wrong:
            problems.append(f"Section {', '.join(wrong)} cannot be a 1961 Act section (the 1961 Act ends at section "
                            "298). Move it to the 2025 Act box.")
        if self.needs_source_ack and not self.sources_var.get():
            problems.append("Tick the box confirming you checked the items the Source Check could not find.")
        if problems:
            messagebox.showerror("Cannot approve yet", "\n".join(f"• {p}" for p in problems), parent=self)
            return
        self.result.key_facts = facts
        self.result.key_facts_confirmed = True
        saved = False
        if self.save_var.get():
            ref = self._save_to_register(facts, by)
            if ref is None:
                return
            saved = True
        self.result.approve(by)
        if self.on_done:
            self.on_done(saved)
        self.destroy()

    def _save_to_register(self, facts: dict, by: str) -> str | None:
        info = self.result.document.info
        try:
            existing = self.repo.find_by_sha(file_sha256(info.path))
        except OSError:
            existing = []
        if existing:
            e = existing[-1]
            choice = messagebox.askyesnocancel(
                "Already in the register",
                f"This PDF is already in the register as {e.ref} ({e.status}"
                f"{', verified by ' + e.reviewed_by if e.reviewed_by else ''}).\n\n"
                "Yes = save this analysis as a NEW entry\nNo = do not save again; link to the existing entry\n"
                "Cancel = go back", parent=self)
            if choice is None:
                return None
            if choice is False:
                self.result.register_ref = e.ref
                return e.ref
        tags = [t for t in self.tags.get().split(",") if t.strip()]
        try:
            rec = record_from_result(self.result, facts, tags, created_by=by)
            rec = self.repo.add(rec, pdf_path=info.path, copy_pdf=bool(self.copy_pdf.get()))
        except (RegisterError, OSError) as exc:
            messagebox.showerror("Register", f"Could not save to the register: {exc}", parent=self)
            return None
        self.result.register_ref = rec.ref
        return rec.ref


# ======================================================================
@dataclass
class RecordForEmail:
    """A register entry presented to the email window in the same shape as a fresh analysis."""
    report: object
    document: object
    register_ref: str
    key_facts: dict
    approved_by: str
    approved_at: str
    status_line: tuple = ()
    register_status: str = ""
    is_approved: bool = True
    email_blocked: str = ""

    @classmethod
    def from_record(cls, rec: JudgmentRecord) -> "RecordForEmail":
        from types import SimpleNamespace

        if rec.status == STATUS_VERIFIED:
            line = (f"✓ Register {rec.ref} - verified by {rec.reviewed_by} on {rec.reviewed_at}", theme.SUCCESS)
        else:
            line = (f"⚠ Register {rec.ref} - Draft: approved by {rec.created_by or 'the preparer'}, not yet verified "
                    "by a reviewer", theme.WARNING)   # client emails are blocked until verified
        facts = {k: getattr(rec, k) for k in ("case_title", "citation", "case_number", "court", "judgment_date",
                                              "assessment_year", "sections", "sections_2025")}
        return cls(report=parse_report(rec.report_md or ""),
                   document=SimpleNamespace(info=SimpleNamespace(file_name=rec.file_name or rec.ref)),
                   register_ref=rec.ref, key_facts=facts, approved_by=rec.created_by, approved_at=rec.created_at,
                   status_line=line, register_status=rec.status,
                   email_blocked="" if rec.status != STATUS_RETURNED else "This entry was returned for correction.")


# ======================================================================
class RecordViewer(ctk.CTkToplevel):
    def __init__(self, master, rec: JudgmentRecord, repo: Repository, font_family=None, font_size=12):
        super().__init__(master)
        self.rec, self.repo = rec, repo
        self.title(f"{rec.ref} - {rec.case_title or rec.file_name}")
        self.configure(fg_color=theme.BG)
        _fit(self, 1000, 820)
        bring_to_front(self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        view = MarkdownView(self, font_family, font_size)
        view.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 6))
        view.set_markdown(self._markdown())
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        _button(bar, "📕 Open original PDF", self._open_pdf, "purple", height=34).pack(side="left")
        _button(bar, "📝 Save as Word", self._save_word, "navy", height=34).pack(side="left", padx=6)
        _button(bar, "Close", self.destroy, "ghost", height=34).pack(side="right")

    def _markdown(self) -> str:
        r = self.rec
        if r.status == STATUS_VERIFIED:
            status = f"Verified by {r.reviewed_by} on {r.reviewed_at}"
        elif r.status == STATUS_RETURNED:
            status = (f"Returned for correction by {r.returned_by} on {r.returned_at}"
                      + (f" - correct: {', '.join(r.return_fields)}" if r.return_fields else "")
                      + (f". Note: {r.return_reason}" if r.return_reason else ""))
        else:
            status = "Draft - approved by the preparer, not yet verified by a reviewer; do not rely on it yet"
        head = [f"# {r.case_title or r.file_name}", "",
                f"- **Register reference:** {r.ref}", f"- **Status:** {status}",
                f"- **Approved by (preparer):** {r.created_by or '-'} on {r.created_at}",
                f"- **Court:** {r.court}", f"- **Citation:** {r.citation or 'Not yet reported'}"
                + (f" (updated by {r.citation_updated_by} on {r.citation_updated_at})" if r.citation_updated_by else ""),
                f"- **Case number:** {r.case_number}",
                f"- **Date of judgment:** {r.judgment_date}", f"- **Assessment year:** {r.assessment_year}",
                f"- **Sections - Income-tax Act, 1961:** {', '.join(r.sections) or '-'}",
                f"- **Sections - Income-tax Act, 2025:** {', '.join(r.sections_2025) or '-'}", f"- **Outcome:** {r.outcome} (in favour of {r.in_favour_of})",
                f"- **Ratio:** {r.ratio}", f"- **Tags:** {', '.join(r.issue_tags)}",
                f"- **{r.source_check_summary or 'Source check: not recorded'}**",
                f"- **{r.consistency_summary or 'Consistency check: not recorded'}**", ""]
        return "\n".join(head) + "\n" + (r.report_md or "")

    def _open_pdf(self):
        path = self.repo.pdf_folder / self.rec.pdf_copy if self.rec.pdf_copy else None
        if path and path.exists():
            open_path(path)
        else:
            messagebox.showinfo("Original PDF", "No copy of the PDF was stored with this entry "
                                f"(original file name: {self.rec.file_name}).", parent=self)

    def _save_word(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".docx",
                                            initialfile=safe_filename(self.rec.case_title or self.rec.ref, ".docx"),
                                            filetypes=[("Word document", "*.docx")])
        if not path:
            return
        r = self.rec
        facts = {k: getattr(r, k) for k in ("case_title", "citation", "case_number", "court", "judgment_date")}
        try:
            note = "" if r.status == STATUS_VERIFIED else "DRAFT - for internal review (not yet verified by a reviewer)"
            save_docx(build_final_document(parse_report(r.report_md or ""), facts, approved_by=r.reviewed_by,
                                           status_note=note), path)
        except Exception as exc:
            messagebox.showerror("Save", f"Could not save: {exc}", parent=self)


# ======================================================================
class CompareWindow(ctk.CTkToplevel):
    def __init__(self, master, app, a: JudgmentRecord, b: JudgmentRecord):
        super().__init__(master)
        self.app, self.a, self.b = app, a, b
        self.title(f"Compare {a.ref} and {b.ref}")
        self.configure(fg_color=theme.BG)
        _fit(self, 1050, 860)
        bring_to_front(self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.markdown = ""
        self.q: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        ctk.CTkLabel(self, text=f"Ruling A: {a.label}\nRuling B: {b.label}", justify="left", anchor="w",
                     font=_font(12, "bold"), text_color=theme.TEXT, wraplength=980).grid(
            row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        self.view = MarkdownView(self, app.settings.view_font_family, app.settings.view_font_size)
        self.view.grid(row=1, column=0, sticky="nsew", padx=12)
        self.view.set_placeholder("Asking Gemini to compare the two rulings…")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", padx=12, pady=12)
        self.copy_btn = _button(bar, "📋 Copy", self._copy, "navy", height=34, state="disabled")
        self.copy_btn.pack(side="left")
        self.word_btn = _button(bar, "📝 Save as Word", self._save_word, "purple", height=34, state="disabled")
        self.word_btn.pack(side="left", padx=6)
        _button(bar, "Close", self._close, "ghost", height=34).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._start()

    def _start(self):
        client = self.app._make_client()
        if client is None:
            self.view.set_placeholder("Enter and test your Gemini API key in the main window first.")
            return

        def work():
            try:
                self.q.put(("ok", compare_records(client, self.a, self.b, self.cancel_event)))
            except Exception as exc:  # noqa: BLE001
                self.q.put(("error", str(exc)))

        threading.Thread(target=work, daemon=True).start()
        self.after(200, self._poll)

    def _poll(self):
        try:
            kind, value = self.q.get_nowait()
        except queue.Empty:
            if self.winfo_exists():
                self.after(250, self._poll)
            return
        if kind == "ok":
            self.markdown = value
            self.view.set_markdown(value)
            self.copy_btn.configure(state="normal")
            self.word_btn.configure(state="normal")
        else:
            self.view.set_placeholder(f"The comparison failed: {value}")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.markdown)

    def _save_word(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".docx",
                                            initialfile=safe_filename(f"Compare_{self.a.ref}_{self.b.ref}", ".docx"),
                                            filetypes=[("Word document", "*.docx")])
        if not path:
            return
        sections, heading, buf = [], None, []
        for line in self.markdown.splitlines():
            if line.startswith("## "):
                if heading:
                    sections.append((heading, "\n".join(buf)))
                heading, buf = line[3:].strip(), []
            else:
                buf.append(line)
        if heading:
            sections.append((heading, "\n".join(buf)))
        if not any(h.lower() == DISCLAIMER_TITLE.lower() for h, _ in sections):
            sections.append((DISCLAIMER_TITLE, "AI-assisted comparison for internal research. Not legal advice."))
        try:
            doc = build_export_document(sections, f"{self.a.ref} vs {self.b.ref}", None, self.app.settings.model,
                                        "Comparison of two register entries")
            doc.title = "Comparison of Rulings"
            save_docx(doc, path)
        except Exception as exc:
            messagebox.showerror("Save", f"Could not save: {exc}", parent=self)

    def _close(self):
        self.cancel_event.set()
        self.destroy()


# ======================================================================
class DetailsDialog(ctk.CTkToplevel):
    """Update a register entry later: any key detail (citation once reported, a missing name or year,
    sections, outcome, tags) and, if needed, the summary text. Correcting anything other than the
    citation or tags sends a Verified / Returned entry back to Draft for the reviewer."""

    def __init__(self, master, app, rec: JudgmentRecord, on_saved=None):
        super().__init__(master)
        rec = app.repository().get(rec.id) or rec   # always start from the saved entry (status may have changed)
        self.app, self.rec, self.on_saved = app, rec, on_saved
        self.title(f"Update details - {rec.ref}")
        self.configure(fg_color=theme.BG)
        _fit(self, 980, 860)
        bring_to_front(self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.q: queue.Queue = queue.Queue()
        self._suggestion = None
        head = f"{rec.ref}  •  {rec.status}"
        self.to_fix = set(rec.return_fields or []) if rec.status == STATUS_RETURNED else set()
        if rec.status == STATUS_RETURNED:
            head += f"\nReturned by {rec.returned_by} on {rec.returned_at}"
            if self.to_fix:
                head += " - correct: " + ", ".join(sorted(self.to_fix))
            if rec.return_reason:
                head += f"\nReviewer's note: {rec.return_reason}"
            head += "\nItems to correct are marked ⚠ in red below."
        ctk.CTkLabel(self, text=head, font=_font(13, "bold"), justify="left", anchor="w", wraplength=920,
                     text_color=theme.WARNING if rec.status == STATUS_RETURNED else theme.TEXT).grid(
            row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        tabs = ctk.CTkTabview(self, fg_color=theme.CARD, segmented_button_selected_color=theme.PURPLE,
                              segmented_button_selected_hover_color=theme.PURPLE_HOVER)
        tabs.grid(row=1, column=0, sticky="nsew", padx=16)
        body = ctk.CTkScrollableFrame(tabs.add("Key details"), fg_color=theme.CARD)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(1, weight=1)
        self.widgets: dict[str, tuple[str, object]] = {}
        r = 0
        for key, label, kind in [*FIELDS, ("issue_tags", "Tags", "list")]:
            flagged = label in self.to_fix
            ctk.CTkLabel(body, text=("⚠ " if flagged else "") + label, font=_font(12, "bold"),
                         text_color=theme.DANGER if flagged else theme.MUTED, anchor="w", wraplength=200,
                         justify="left").grid(row=r, column=0, sticky="nw", padx=(8, 12), pady=(8, 0))
            value = getattr(rec, key, "")
            if kind in ("list", "issues", "prose"):
                w = ctk.CTkTextbox(body, height=60 if kind == "list" else 90, fg_color=theme.ENTRY_BG, wrap="word")
                w.insert("1.0", "\n".join(value) if isinstance(value, list) else (value or ""))
            elif kind == "choice":
                w = ctk.CTkComboBox(body, values=OUTCOMES if key == "outcome" else FAVOUR, fg_color=theme.ENTRY_BG)
                w.set(value or "Not stated")
            else:
                w = ctk.CTkEntry(body, fg_color=theme.ENTRY_BG)
                if value:
                    w.insert(0, value)
            w.grid(row=r, column=1, sticky="ew", padx=(0, 8), pady=(8, 0))
            self.widgets[key] = (kind, w)
            r += 1
            if key == "citation":
                row = ctk.CTkFrame(body, fg_color="transparent")
                row.grid(row=r, column=1, sticky="ew", padx=(0, 8), pady=(4, 0))
                self.lookup_btn = _button(row, "🔎 Find reported citation online", self._lookup, "navy", height=28,
                                          width=230)
                self.lookup_btn.grid(row=0, column=0, sticky="w")
                self.use_btn = _button(row, "Use this citation", self._use, "purple", height=28, width=150)
                self.label = ctk.CTkLabel(row, text="Only the appeal number, forum, parties and date are sent.",
                                          wraplength=700, justify="left", anchor="w", font=_font(11),
                                          text_color=theme.MUTED)
                self.label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
                r += 1
        # Every section of the analysis as its own box (e.g. 'Important Precedents Cited')
        sec_tab = tabs.add("Analysis sections")
        sec_tab.grid_columnconfigure(0, weight=1)
        sec_tab.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(sec_tab, text="Correct or complete any section. Use only what the judgment says - after saving, "
                                   "the app checks your text against the judgment PDF stored with the register.",
                     font=_font(11), text_color=theme.MUTED, anchor="w", wraplength=880, justify="left").grid(
            row=0, column=0, sticky="ew")
        sbody = ctk.CTkScrollableFrame(sec_tab, fg_color=theme.CARD)
        sbody.grid(row=1, column=0, sticky="nsew")
        sbody.grid_columnconfigure(0, weight=1)
        parsed = parse_report(rec.report_md or "")
        self._disclaimer = parsed.disclaimer
        self.section_boxes: dict[int, ctk.CTkTextbox] = {}
        for i, s in enumerate(REPORT_SECTIONS):
            flagged = s.title in self.to_fix
            ctk.CTkLabel(sbody, text=("⚠ " if flagged else "") + f"{s.number}. {s.title}", font=_font(12, "bold"),
                         text_color=theme.DANGER if flagged else (theme.NAVY, theme.GOLD), anchor="w").grid(
                row=i * 2, column=0, sticky="w", pady=(10, 2))
            box = ctk.CTkTextbox(sbody, height=150 if flagged else 110, fg_color=theme.ENTRY_BG, wrap="word",
                                 font=_font(12), border_width=2 if flagged else 0, border_color=theme.DANGER)
            box.insert("1.0", parsed.sections.get(s.number, "").strip())
            box.grid(row=i * 2 + 1, column=0, sticky="ew")
            self.section_boxes[s.number] = box
        flagged_secs = [i for i, s in enumerate(REPORT_SECTIONS) if s.title in self.to_fix]
        if flagged_secs and not self.to_fix & {lb for _k, lb, _ in FIELDS}:
            tabs.set("Analysis sections")
            # bring the first section to correct into view
            self.after(400, lambda: sbody._parent_canvas.yview_moveto(max(0.0, flagged_secs[0] / len(REPORT_SECTIONS)
                                                                        - 0.02)))

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", padx=16, pady=12)
        foot.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(foot, text="Updated by", font=_font(12, "bold"), text_color=theme.MUTED).grid(row=0, column=0)
        self.by = ctk.CTkEntry(foot, fg_color=theme.ENTRY_BG, placeholder_text="Your name", width=220)
        if load_sender_profile().name:
            self.by.insert(0, load_sender_profile().name)
        self.by.grid(row=0, column=1, sticky="w", padx=8)
        _button(foot, "Cancel", self.destroy, "slate", width=100, height=36).grid(row=0, column=2, padx=6)
        _button(foot, "Save changes", self._save, "gold", width=150, height=36).grid(row=0, column=3)
        self.after(250, self._poll)

    def _values(self) -> dict:
        out = {}
        for key, (kind, w) in self.widgets.items():
            if isinstance(w, ctk.CTkTextbox):
                text = w.get("1.0", "end").strip()
                out[key] = [x.strip(" -•\t") for x in text.splitlines() if x.strip()] if kind in ("list", "issues") \
                    else text
            else:
                out[key] = w.get().strip()
        return out

    def _lookup(self):
        client = self.app._make_client()
        if client is None:
            return
        facts = self._values()
        self.lookup_btn.configure(state="disabled", text="Searching…")
        from ..citation_lookup import lookup_citation

        def work():
            try:
                self.q.put(("ok", lookup_citation(client, facts)))
            except Exception as exc:  # noqa: BLE001
                self.q.put(("error", str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind, value = self.q.get_nowait()
                self.lookup_btn.configure(state="normal", text="🔎 Find reported citation online")
                if kind == "error":
                    self.label.configure(text=f"Online lookup is not available: {value}", text_color=theme.WARNING)
                elif value.found:
                    self._suggestion = value
                    srcs = "\n".join(f"   • {t or 'source'}: {u}" for t, u in value.sources)
                    self.label.configure(text=f"Suggested: {value.citation}  (confidence: {value.confidence or 'n/a'})"
                                              f"\n{value.note}\nSources:\n{srcs}\nCheck the source before using it.",
                                         text_color=theme.TEXT)
                    self.use_btn.grid(row=0, column=1, padx=8)
                else:
                    self.label.configure(text="No reported citation was found online yet. " + (value.note or ""),
                                         text_color=theme.MUTED)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(250, self._poll)

    def _source_check_ok(self, report) -> bool:
        """Check the corrected text against the judgment PDF stored with the register (quotations, citations,
        sections, dates, amounts, paragraph numbers). Anything not found must be confirmed by the user."""
        pdf = self.app.repository().pdf_folder / self.rec.pdf_copy if self.rec.pdf_copy else None
        if not pdf or not pdf.exists():
            return messagebox.askyesno("Update details", "No copy of the judgment is stored with this entry, so your "
                                       "changes cannot be checked against it. Save anyway?", parent=self)
        try:
            from ..paragraphs import detect_paragraphs
            from ..pdf_processor import extract_text, validate_pdf
            from ..verifier import verify_report

            doc = extract_text(validate_pdf(pdf), ocr_mode="Off")
            paras = {m.number for m in detect_paragraphs(doc.pages)}
            check = verify_report(report, doc.full_text(with_page_markers=False), paras, doc.info.page_count)
        except Exception as exc:  # noqa: BLE001 - the check is a help, not a gate
            log.warning("Source check on update failed: %s", exc)
            return True
        old = verify_report(parse_report(self.rec.report_md or ""), doc.full_text(with_page_markers=False), paras,
                            doc.info.page_count)
        old_missing = {(i.kind, i.text) for i in old.not_found}
        new_missing = [i for i in check.not_found if (i.kind, i.text) not in old_missing]
        if not new_missing:
            return True
        items = "\n".join(f"• {i.kind}: {i.text}" + (f"  ({i.section})" if i.section else "") for i in new_missing[:10])
        return messagebox.askyesno(
            "Not found in the judgment",
            f"{len(new_missing)} item(s) you added could not be found in the judgment:\n\n{items}\n\n"
            "Cases cited as precedents should be ones the judgment itself refers to. Save anyway?",
            icon="warning", parent=self)

    def _use(self):
        if self._suggestion:
            w = self.widgets["citation"][1]
            w.delete(0, "end")
            w.insert(0, self._suggestion.citation)

    def _save(self):
        values = self._values()
        wrong = [s for s in values.get("sections", []) if definite_act(s) == "2025"]
        if wrong:
            messagebox.showerror("Update details", f"Section {', '.join(wrong)} cannot be a 1961 Act section (the "
                                 "1961 Act ends at section 298). Move it to the 2025 Act box.", parent=self)
            return
        import dataclasses

        report = ParsedReport(sections={n: b.get("1.0", "end").strip() for n, b in self.section_boxes.items()
                                        if b.get("1.0", "end").strip()}, disclaimer=self._disclaimer)
        if not self._source_check_ok(report):
            return
        rec = dataclasses.replace(self.rec, **values, report_md=report.to_markdown())
        before = self.rec.status
        if before == STATUS_RETURNED and rec.report_md == (self.rec.report_md or "") and all(
                getattr(rec, k) == getattr(self.rec, k) for k in values) and not messagebox.askyesno(
                "Update details", "You have not changed anything. Send it back to the reviewer anyway?", parent=self):
            return
        try:
            status = self.app.repository().update_details(rec, self.by.get())
        except RegisterError as exc:
            messagebox.showerror("Update details", str(exc), parent=self)
            return
        if status != before:
            msg = (f"Saved. {rec.ref} goes back to the reviewer as Draft." if before == STATUS_RETURNED else
                   f"Saved. Because the content changed, {rec.ref} is back to Draft and needs to be verified again.")
            messagebox.showinfo("Update details", msg, parent=self)
        if self.on_saved:
            self.on_saved()
        self.destroy()


class ReturnDialog(ctk.CTkToplevel):
    """Reviewer sends an entry back to the preparer: tick what must be corrected and add a note.
    The preparer sees the ticked items marked in red in 'Update details'."""

    def __init__(self, master, app, rec: JudgmentRecord, on_saved=None):
        super().__init__(master)
        self.app, self.rec, self.on_saved = app, rec, on_saved
        self.title(f"Return for correction - {rec.ref}")
        self.configure(fg_color=theme.BG)
        _fit(self, 860, 820)
        bring_to_front(self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text=f"{rec.case_title}\nPrepared and approved by {rec.created_by or 'not recorded'}. Tick what "
                                "needs to be corrected; the preparer will see these items marked in red.",
                     font=_font(12), text_color=theme.TEXT, justify="left", anchor="w", wraplength=800).grid(
            row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        body = ctk.CTkScrollableFrame(self, fg_color=theme.CARD)
        body.grid(row=1, column=0, sticky="nsew", padx=16)
        body.grid_columnconfigure((0, 1), weight=1)
        self.vars: dict[str, ctk.BooleanVar] = {}
        groups = (("Key details", [lb for _k, lb, _kind in FIELDS] + ["Tags"]),
                  ("Analysis sections", [s.title for s in REPORT_SECTIONS]))
        for col, (title, labels) in enumerate(groups):
            ctk.CTkLabel(body, text=title, font=_font(13, "bold"), text_color=(theme.NAVY, theme.GOLD)).grid(
                row=0, column=col, sticky="w", padx=8, pady=(6, 4))
            for i, label in enumerate(labels, 1):
                var = ctk.BooleanVar(value=False)
                ctk.CTkCheckBox(body, text=label, variable=var, font=_font(12), fg_color=theme.PURPLE,
                                hover_color=theme.PURPLE_HOVER).grid(row=i, column=col, sticky="w", padx=8, pady=2)
                self.vars[label] = var
        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 0))
        foot.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(foot, text="Note to preparer", font=_font(12, "bold"), text_color=theme.MUTED).grid(
            row=0, column=0, sticky="nw")
        self.note = ctk.CTkTextbox(foot, height=70, fg_color=theme.ENTRY_BG, wrap="word")
        self.note.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(foot, text="Reviewer", font=_font(12, "bold"), text_color=theme.MUTED).grid(
            row=1, column=0, sticky="w", pady=(8, 0))
        self.by = ctk.CTkEntry(foot, fg_color=theme.ENTRY_BG, placeholder_text="Your name or initials", width=260)
        self.by.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="e", padx=16, pady=12)
        _button(btns, "Cancel", self.destroy, "slate", width=100, height=36).pack(side="left", padx=6)
        _button(btns, "↩ Return to preparer", self._save, "amber", width=190, height=36).pack(side="left")

    def selected(self) -> list[str]:
        return [label for label, var in self.vars.items() if var.get()]

    def _save(self):
        fields_to_fix, note, by = self.selected(), self.note.get("1.0", "end").strip(), self.by.get().strip()
        try:
            self.app.repository().set_returned(self.rec.id, by, note, fields_to_fix)
        except RegisterError as exc:
            messagebox.showerror("Return for correction", str(exc), parent=self)
            return
        if self.on_saved:
            self.on_saved()
        self.destroy()


# ======================================================================
class RegisterWindow(ctk.CTkToplevel):
    COLUMNS = (("ref", "Ref", 125), ("status", "Status", 80), ("case_title", "Case", 260), ("court", "Court", 170),
               ("judgment_date", "Date", 100), ("assessment_year", "AY", 80), ("citation", "Citation", 150),
               ("sections", "1961 Act s.", 110), ("sections_2025", "2025 Act s.", 100),
               ("outcome", "Outcome", 100), ("in_favour_of", "Favour", 90), ("score", "Source check", 90))

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Precedent Register - Judgement Insights Analyser")
        self.configure(fg_color=theme.BG)
        _fit(self, 1320, 820)
        bring_to_front(self)
        self.records: dict[str, JudgmentRecord] = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top = Card(self, "Precedent register")
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        self.stats_label = ctk.CTkLabel(top.body, text="", anchor="w", justify="left", font=_font(13),
                                        text_color=theme.TEXT, wraplength=1200)
        self.stats_label.grid(row=0, column=0, sticky="ew")
        loc = ctk.CTkFrame(top.body, fg_color="transparent")
        loc.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        loc.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(loc, text="Register file:", font=_font(12, "bold"), text_color=theme.MUTED).grid(row=0, column=0)
        self.path_label = ctk.CTkLabel(loc, text="", anchor="w", font=_font(12), text_color=theme.TEXT)
        self.path_label.grid(row=0, column=1, sticky="ew", padx=6)
        _button(loc, "Change location…", self._change_location, "ghost", height=28, width=140).grid(row=0, column=2)
        _button(loc, "Open folder", lambda: open_path(self.app.repository().path.parent), "ghost", height=28,
                width=110).grid(row=0, column=3, padx=(6, 0))

        filt = ctk.CTkFrame(self, fg_color="transparent")
        filt.grid(row=1, column=0, sticky="ew", padx=14)
        filt.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(filt, text="Search:", font=_font(12, "bold"), text_color=theme.MUTED).grid(row=0, column=0)
        self.search_text = ctk.CTkEntry(filt, fg_color=theme.ENTRY_BG, placeholder_text="case name, issue, tag, "
                                                                                        "citation, ratio…")
        self.search_text.grid(row=0, column=1, sticky="ew", padx=6)
        self.search_text.bind("<KeyRelease>", self._on_typing)
        ctk.CTkLabel(filt, text="Section:", font=_font(12, "bold"), text_color=theme.MUTED).grid(row=0, column=2)
        self.section = ctk.CTkEntry(filt, width=90, fg_color=theme.ENTRY_BG, placeholder_text="e.g. 68")
        self.section.grid(row=0, column=3, padx=6)
        self.section.bind("<KeyRelease>", self._on_typing)
        self._typing_job = None
        self.act = ctk.CTkOptionMenu(filt, values=[ACT_EITHER, ACT_1961, ACT_2025], width=110,
                                     command=lambda _: self.refresh(), fg_color=theme.BTN_NAVY,
                                     button_color=theme.NAVY_2, button_hover_color=theme.PURPLE)
        self.act.grid(row=0, column=4, padx=(0, 6))
        self.status = ctk.CTkOptionMenu(filt, values=["All statuses", *STATUSES], width=130,
                                        command=lambda _: self.refresh(), fg_color=theme.BTN_NAVY,
                                        button_color=theme.NAVY_2, button_hover_color=theme.PURPLE)
        self.status.grid(row=0, column=5, padx=6)
        self.favour = ctk.CTkOptionMenu(filt, values=["Any outcome", *FAVOUR], width=150,
                                        command=lambda _: self.refresh(), fg_color=theme.BTN_NAVY,
                                        button_color=theme.NAVY_2, button_hover_color=theme.PURPLE)
        self.favour.grid(row=0, column=6, padx=6)
        _button(filt, "✕ Clear filters", self._clear_filters, "slate", width=120, height=30).grid(row=0, column=7)

        frame = tk.Frame(self, bd=0, highlightthickness=0)
        frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self._style()
        self.tree = ttk.Treeview(frame, columns=[c for c, _, _ in self.COLUMNS], show="headings",
                                 selectmode="extended", style="Register.Treeview")
        for key, title, width in self.COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="w", stretch=key == "case_title")
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        ys.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.bind("<Double-1>", lambda e: self._open())
        self.tree.tag_configure("verified", foreground="#1E7B4F")
        self.tree.tag_configure("returned", foreground="#B7791F")

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))
        for text, cmd, kind in (("📖 Open summary", self._open, "purple"), ("📕 Open PDF", self._open_pdf, "navy"),
                                ("✎ Update details…", self._update_details, "navy"),
                                ("✔ Mark verified…", self._verify, "gold"),
                                ("↩ Return for correction…", self._return, "amber"),
                                ("✉ Email", self._email, "purple"),
                                ("⚖ Compare 2 selected", self._compare, "purple"),
                                ("📊 Export to Excel", self._export, "navy"), ("🗑 Delete", self._delete, "danger")):
            _button(bar, text, cmd, kind, height=36).pack(side="left", padx=(0, 6))
        _button(bar, "✕ Close", self.destroy, "slate", height=36).pack(side="right")
        ctk.CTkLabel(self, text="Two-level sign-off: 'Review & Approve' in the main window is the preparer's approval "
                                "(entry saved as Draft). 'Mark verified' is the reviewer's check - ideally a different, "
                                "senior person. If the reviewer does not agree, use 'Return for correction'; the "
                                "preparer fixes it with 'Update details' and it comes back as Draft.",
                     font=_font(11), text_color=theme.MUTED, wraplength=1250, justify="left", anchor="w").grid(
            row=4, column=0, sticky="ew", padx=14, pady=(0, 10))
        self.refresh()

    def _style(self):
        dark = ctk.get_appearance_mode() == "Dark"
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        bg, fg, head = ("#111A2E", "#E8EAF2", "#16305A") if dark else ("#FFFFFF", "#1B1F2A", "#0B1F3A")
        st.configure("Register.Treeview", background=bg, fieldbackground=bg, foreground=fg, rowheight=28,
                     font=(theme.FONT_FAMILY, 11))
        st.configure("Register.Treeview.Heading", background=head, foreground="#FFFFFF",
                     font=(theme.FONT_FAMILY, 11, "bold"))
        st.map("Register.Treeview", background=[("selected", theme.PURPLE)], foreground=[("selected", "#FFFFFF")])

    def refresh(self):
        try:
            repo = self.app.repository()
        except RegisterError as exc:
            messagebox.showerror("Register", str(exc), parent=self)
            return
        self.path_label.configure(text=str(repo.path))
        st = repo.stats()
        fav = ", ".join(f"{k}: {v}" for k, v in st["favour"].items()) or "-"
        top = ", ".join(f"s.{s} ({n})" for s, n in st["top_sections"]) or "-"
        self.stats_label.configure(text=f"{st['total']} judgment(s)  •  {st['verified']} verified  •  {st['draft']} "
                                        f"draft  •  {st['returned']} returned for correction\nIn favour of - {fav}\nMost frequent sections - {top}")
        status = self.status.get()
        favour = self.favour.get()
        recs = repo.search(self.search_text.get(), self.section.get(),
                           "" if status.startswith("All") else status, "" if favour.startswith("Any") else favour,
                           act=self.act.get())
        self.tree.delete(*self.tree.get_children())
        self.records = {}
        for r in recs:
            iid = str(r.id)
            self.records[iid] = r
            score = "" if r.source_check_score in (None, "") else f"{float(r.source_check_score) * 100:.0f}%"
            self.tree.insert("", "end", iid=iid, values=(r.ref, r.status, r.case_title, r.court, r.judgment_date,
                                                         r.assessment_year, r.citation or "Not yet reported",
                                                         ", ".join(r.sections), ", ".join(r.sections_2025), r.outcome,
                                                         r.in_favour_of, score),
                             tags=("verified",) if r.status == STATUS_VERIFIED else
                             ("returned",) if r.status == STATUS_RETURNED else ())
        self.app.refresh_register_badge()

    def _selected(self) -> list[JudgmentRecord]:
        return [self.records[i] for i in self.tree.selection() if i in self.records]

    def _one(self) -> JudgmentRecord | None:
        sel = self._selected()
        if len(sel) != 1:
            messagebox.showinfo("Register", "Select one judgment in the list.", parent=self)
            return None
        return sel[0]

    def _open(self):
        rec = self._one()
        if rec:
            RecordViewer(self, rec, self.app.repository(), self.app.settings.view_font_family,
                         self.app.settings.view_font_size)

    def _open_pdf(self):
        rec = self._one()
        if not rec:
            return
        path = self.app.repository().pdf_folder / rec.pdf_copy if rec.pdf_copy else None
        if path and path.exists():
            open_path(path)
        else:
            messagebox.showinfo("Original PDF", f"No copy of the PDF is stored for {rec.ref}.", parent=self)

    def _verify(self):
        rec = self._one()
        if not rec:
            return
        dialog = ctk.CTkInputDialog(text=f"Mark {rec.ref} as VERIFIED.\n\nConfirm you have read the summary against "
                                         "the original judgment.\nEnter your name or initials:", title="Verify entry")
        name = (dialog.get_input() or "").strip()
        if not name:
            return
        if rec.created_by and name.strip().lower() == rec.created_by.strip().lower() and not messagebox.askyesno(
                "Same person", f"{rec.ref} was approved by {rec.created_by}. Verification is meant to be a second "
                               "check by a different person (maker / checker).\n\nVerify it yourself anyway?",
                icon="warning", parent=self):
            return
        try:
            self.app.repository().set_verified(rec.id, name)
        except RegisterError as exc:
            messagebox.showerror("Register", str(exc), parent=self)
        self.refresh()

    def _on_typing(self, _event=None):
        """Filter as you type (short pause so the list doesn't flicker); an empty box shows everything again."""
        if self._typing_job is not None:
            self.after_cancel(self._typing_job)
        self._typing_job = self.after(300, self._typed)

    def _typed(self):
        self._typing_job = None
        self.refresh()

    def _clear_filters(self):
        self.search_text.delete(0, "end")
        self.section.delete(0, "end")
        self.act.set(ACT_EITHER)
        self.status.set("All statuses")
        self.favour.set("Any outcome")
        self.focus_set()
        self.refresh()

    def _update_details(self):
        rec = self._one()
        if rec:
            DetailsDialog(self, self.app, rec, on_saved=self.refresh)

    def _return(self):
        rec = self._one()
        if rec:
            ReturnDialog(self, self.app, rec, on_saved=self.refresh)

    def _email(self):
        """Email a judgment from the register (same window as after an analysis)."""
        rec = self._one()
        if not rec:
            return
        rec = self.app.repository().get(rec.id) or rec
        if rec.status == STATUS_RETURNED:
            messagebox.showerror("Email", f"{rec.ref} was returned for correction. Correct it with 'Update details' "
                                 "(it goes back to the reviewer) before emailing it.", parent=self)
            return
        if not (rec.report_md or "").strip():
            messagebox.showerror("Email", f"{rec.ref} has no summary text to send.", parent=self)
            return
        from .email_dialog import EmailDialog

        EmailDialog(self.app, RecordForEmail.from_record(rec))

    def _compare(self):
        sel = self._selected()
        if len(sel) != 2:
            messagebox.showinfo("Compare rulings", "Select exactly two judgments (Ctrl+click) to compare.", parent=self)
            return
        CompareWindow(self, self.app, sel[0], sel[1])

    def _export(self):
        recs = list(self.records.values())
        if not recs:
            messagebox.showinfo("Export", "There is nothing to export.", parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx",
                                            initialfile="Precedent_register.xlsx", filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            export_xlsx(recs, path)
            open_path(path)
        except PermissionError:
            messagebox.showerror("Export", "The file is open in Excel. Close it and try again.", parent=self)

    def _delete(self):
        rec = self._one()
        if rec and messagebox.askyesno("Delete", f"Permanently delete {rec.ref} ({rec.case_title}) from the register, "
                                                 "including its stored PDF copy?", icon="warning", parent=self):
            self.app.repository().delete(rec.id)
            self.refresh()

    def _change_location(self):
        path = filedialog.asksaveasfilename(
            parent=self, title="Register file (choose an existing register or a new file name)",
            defaultextension=".db", initialfile="precedent_register.db", confirmoverwrite=False,
            filetypes=[("Register database", "*.db")])
        if not path:
            return
        self.app.set_register_path(path)
        self.refresh()


def default_register_note(path: Path) -> str:
    return f"Register file: {path}"
