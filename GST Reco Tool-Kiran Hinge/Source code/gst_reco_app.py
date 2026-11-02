"""
GST Reco Tool - desktop app (Windows).

A native window around the engine in gst_reco_tool.py: pick the Tax Power and Tally
exports, check what was read, and generate the two formula-linked reco workbooks.
Packaged as a single .exe with build_exe.bat - staff need no Python, no libraries and
no browser.

Run from source:  python gst_reco_app.py
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

import gst_reco_tool as engine

APP_NAME = "GST Reco Tool"
ACCENT = "#1F4E78"
ACCENT_HOVER = "#163A5A"
OK_GREEN = "#2E7D32"
MUTED = "#6B7280"
CARD_BG = "#FFFFFF"
PAGE_BG = "#F3F5F8"
BORDER = "#E2E6EC"
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME


def resource(name: str) -> Path:
    """Path to a bundled file, both from source and inside the PyInstaller exe."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / name


def log_error(exc: BaseException) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / "error.log"
    with log.open("a", encoding="utf-8") as f:
        f.write("\n" + "=" * 80 + "\n")
        f.write("".join(traceback.format_exception(exc)))
    return log


def fmt_amt(v: float) -> str:
    """Indian digit grouping: 12,34,567.89"""
    neg = v < 0
    s = f"{abs(v):.2f}"
    whole, dec = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return ("-" if neg else "") + whole + "." + dec


# --------------------------------------------------------------------------------------
# Widgets
# --------------------------------------------------------------------------------------
class Card(ctk.CTkFrame):
    def __init__(self, master, title: str, subtitle: str = ""):
        super().__init__(master, fg_color=CARD_BG, corner_radius=10, border_width=1,
                         border_color=BORDER)
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(head, text=title, font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#111827").pack(side="left")
        if subtitle:
            ctk.CTkLabel(head, text=subtitle, font=ctk.CTkFont(size=12),
                         text_color=MUTED).pack(side="left", padx=(12, 0))
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=12, pady=(0, 10))


class FilePicker(ctk.CTkFrame):
    """One input file: title, chosen file name, Browse and Clear buttons."""

    def __init__(self, master, kind: str, title: str, hint: str, on_change):
        super().__init__(master, fg_color="#F8FAFC", corner_radius=8)
        self.kind, self.on_change = kind, on_change
        self.path: Path | None = None
        self.columnconfigure(1, weight=1)
        self.dot = ctk.CTkLabel(self, text="○", width=22, font=ctk.CTkFont(size=16),
                                text_color="#9CA3AF")
        self.dot.grid(row=0, column=0, rowspan=2, padx=(10, 4), pady=5)
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").grid(row=0, column=1, sticky="ew", pady=(5, 0))
        self.name = ctk.CTkLabel(self, text=hint, font=ctk.CTkFont(size=12),
                                 text_color=MUTED, anchor="w")
        self.name.grid(row=1, column=1, sticky="ew", pady=(0, 5))
        self.clear_btn = ctk.CTkButton(self, text="✕", width=30, height=30,
                                       fg_color="transparent", text_color=MUTED,
                                       hover_color="#E5E7EB", command=self.clear)
        self.clear_btn.grid(row=0, column=2, rowspan=2, padx=(4, 2))
        ctk.CTkButton(self, text="Browse", width=84, height=30, fg_color="#E8EEF6",
                      text_color=ACCENT, hover_color="#D6E2F0",
                      command=self.browse).grid(row=0, column=3, rowspan=2, padx=(2, 10))
        self.hint = hint

    def browse(self):
        p = filedialog.askopenfilename(title="Select file",
                                       filetypes=[("Excel workbook", "*.xlsx")])
        if p:
            self.set(Path(p))

    def set(self, path: Path | None):
        self.path = path
        if path:
            self.dot.configure(text="●", text_color=OK_GREEN)
            self.name.configure(text=path.name, text_color="#111827")
        else:
            self.dot.configure(text="○", text_color="#9CA3AF")
            self.name.configure(text=self.hint, text_color=MUTED)
        self.on_change()

    def clear(self):
        self.set(None)


# --------------------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title(APP_NAME)
        self.geometry("1100x820")
        self.minsize(920, 640)
        self.after(0, lambda: self.state("zoomed"))  # open maximised
        self.configure(fg_color=PAGE_BG)
        try:
            self.iconbitmap(str(resource("app.ico")))
        except Exception:  # noqa: BLE001 - icon is cosmetic
            pass

        self.q: queue.Queue = queue.Queue()
        self.busy = False
        self.user_edited = {"client": False, "fy": False, "out": False}
        self.results: list[engine.GenResult] = []
        self._preview_token = 0

        self._header()
        self._body()
        self.after(100, self._poll)

    # ---- layout -------------------------------------------------------------------------
    def _header(self):
        bar = ctk.CTkFrame(self, fg_color=ACCENT, corner_radius=0, height=64)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text=APP_NAME, font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="white").pack(side="left", padx=(24, 12))
        ctk.CTkLabel(bar, text="Books vs GSTR-1 / GSTR-2B / GSTR-3B  •  formula-linked Excel "
                               "reconciliation", font=ctk.CTkFont(size=13),
                     text_color="#C9D8EA").pack(side="left")
        ctk.CTkButton(bar, text="Add files…", width=120, height=36, fg_color="white",
                      text_color=ACCENT, hover_color="#E8EEF6",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      command=self.add_files).pack(side="right", padx=24)

    def _body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(10, 14))
        body.columnconfigure((0, 1), weight=1, uniform="c")
        body.rowconfigure(4, weight=1)

        tip = ctk.CTkLabel(body, text="Tip: click “Add files…” and select all files together "
                                      "- the tool recognises each one automatically.",
                           font=ctk.CTkFont(size=12), text_color=MUTED, anchor="w")
        tip.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        self.pickers: dict[str, FilePicker] = {}
        out = Card(body, "Output  •  Sales", "Creates: GST Reco Output workbook")
        out.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        inp = Card(body, "Input  •  Purchases / ITC", "Creates: GST Reco Input workbook")
        inp.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        spec = [
            (out.body, "gstr1", "GSTR-1 Section-wise Summary", "Tax Power export"),
            (out.body, "sales", "Sales / Debit Note / Credit Note Register", "Tally export"),
            (inp.body, "gstr2b", "GSTR-2B Section-wise Summary", "Tax Power export"),
            (inp.body, "purchase", "Purchase / DN / CN / Journal Register", "Tally export"),
        ]
        for parent, kind, title, hint in spec:
            fp = FilePicker(parent, kind, title, hint, self.files_changed)
            fp.pack(fill="x", pady=3)
            self.pickers[kind] = fp

        common = Card(body, "Common", "GSTR-3B is used for both workbooks")
        common.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        cb = common.body
        cb.columnconfigure(0, weight=3)
        cb.columnconfigure((1, 2), weight=2)
        fp = FilePicker(cb, "gstr3b", "GSTR-3B Month-wise Annual Summary",
                        "Tax Power export", self.files_changed)
        fp.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.pickers["gstr3b"] = fp

        self.client = self._field(cb, "Client name", 1, 0, "client")
        self.fy = self._field(cb, "Financial year (e.g. 2025-26)", 1, 1, "fy")
        outf = ctk.CTkFrame(cb, fg_color="transparent")
        outf.grid(row=1, column=2, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(outf, text="Save reco files to", font=ctk.CTkFont(size=12),
                     text_color=MUTED).pack(anchor="w")
        row = ctk.CTkFrame(outf, fg_color="transparent")
        row.pack(fill="x")
        self.outdir = ctk.CTkEntry(row, height=34)
        self.outdir.pack(side="left", fill="x", expand=True)
        self.outdir.bind("<Key>", lambda _e: self.user_edited.__setitem__("out", True))
        ctk.CTkButton(row, text="…", width=36, height=34, fg_color="#E8EEF6",
                      text_color=ACCENT, hover_color="#D6E2F0",
                      command=self.pick_outdir).pack(side="left", padx=(6, 0))

        # Action bar
        act = ctk.CTkFrame(body, fg_color="transparent")
        act.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.gen_btn = ctk.CTkButton(act, text="Generate reco workbooks", height=44, width=240,
                                     font=ctk.CTkFont(size=15, weight="bold"),
                                     fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                     command=self.generate)
        self.gen_btn.pack(side="left")
        self.progress = ctk.CTkProgressBar(act, mode="indeterminate", width=160,
                                           progress_color=ACCENT)
        self.status = ctk.CTkLabel(act, text="Select the files to begin.",
                                   font=ctk.CTkFont(size=13), text_color=MUTED)
        self.status.pack(side="left", padx=16)
        self.open_frame = ctk.CTkFrame(act, fg_color="transparent")
        self.open_frame.pack(side="right")

        # Bottom panel (fills the rest of the window): what was read / messages
        panel = ctk.CTkFrame(body, fg_color=CARD_BG, corner_radius=10, border_width=1,
                             border_color=BORDER)
        panel.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        self.tab_btn = ctk.CTkSegmentedButton(
            panel, values=["Files read", "Messages"], command=self._show_tab,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER)
        self.tab_btn.pack(anchor="w", padx=12, pady=(10, 6))
        self.pages = {"Files read": ctk.CTkFrame(panel, fg_color="transparent"),
                      "Messages": ctk.CTkFrame(panel, fg_color="transparent")}
        self._tree(self.pages["Files read"])
        self.msgs = ctk.CTkTextbox(self.pages["Messages"], font=ctk.CTkFont(size=12),
                                   wrap="word", fg_color="#FAFAFA")
        self.msgs.pack(fill="both", expand=True)
        self.msgs.configure(state="disabled")
        self._show_tab("Files read")

    def _show_tab(self, name: str):
        for n, page in self.pages.items():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.tab_btn.set(name)

    def _field(self, parent, label, row, col, key):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
        ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=12), text_color=MUTED).pack(anchor="w")
        e = ctk.CTkEntry(f, height=34)
        e.pack(fill="x")
        e.bind("<Key>", lambda _e: self.user_edited.__setitem__(key, True))
        return e

    def _tree(self, parent):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Reco.Treeview", rowheight=24, font=("Segoe UI", 10),
                        background="white", fieldbackground="white", bordercolor=BORDER)
        style.configure("Reco.Treeview.Heading", font=("Segoe UI", 10, "bold"),
                        background="#EEF2F7", foreground="#1F2937", relief="flat")
        style.map("Reco.Treeview", background=[("selected", "#DCE7F3")],
                  foreground=[("selected", "#111827")])
        cols = ("file", "sheet", "rows", "tv", "igst", "cgst", "sgst")
        heads = ("File", "Sheet", "Rows", "Taxable value", "IGST", "CGST", "SGST")
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", style="Reco.Treeview")
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h, anchor="w" if c in ("file", "sheet") else "e")
            self.tree.column(c, anchor="w" if c in ("file", "sheet") else "e",
                             width=190 if c == "file" else (150 if c == "sheet" else 110))
        self.tree.tag_configure("odd", background="#F8FAFC")
        self.tree.tag_configure("empty", foreground="#9CA3AF")
        sb = ctk.CTkScrollbar(frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ---- actions ------------------------------------------------------------------------
    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select the Tax Power and Tally files",
                                            filetypes=[("Excel workbook", "*.xlsx")])
        if not paths:
            return
        unknown = []
        for p in paths:
            kind = engine.classify_workbook(Path(p).read_bytes())
            if kind in self.pickers:
                self.pickers[kind].path = Path(p)
                self.pickers[kind].set(Path(p))
            else:
                unknown.append(Path(p).name)
        if unknown:
            messagebox.showwarning(APP_NAME, "Could not recognise:\n\n" + "\n".join(unknown)
                                   + "\n\nUse the Browse button next to the right box.")

    def pick_outdir(self):
        d = filedialog.askdirectory(title="Save reco files to")
        if d:
            self._set_entry(self.outdir, d)
            self.user_edited["out"] = True

    @staticmethod
    def _set_entry(entry, text):
        entry.delete(0, "end")
        entry.insert(0, text)

    def _sources(self) -> dict[str, engine.SourceFile | None]:
        out = {}
        for kind, fp in self.pickers.items():
            out[kind] = (engine.SourceFile(engine.FILE_KINDS[kind], fp.path.name,
                                           fp.path.read_bytes()) if fp.path else None)
        return out

    def files_changed(self):
        chosen = [fp.path for fp in self.pickers.values() if fp.path]
        if not self.user_edited["out"] and chosen:
            first = (self.pickers["sales"].path or self.pickers["purchase"].path or chosen[0])
            self._set_entry(self.outdir, str(first.parent))
        self._clear_results()
        if not chosen:
            self.tree.delete(*self.tree.get_children())
            self.status.configure(text="Select the files to begin.", text_color=MUTED)
            return
        self.status.configure(text="Reading files…", text_color=MUTED)
        self._preview_token += 1
        token = self._preview_token
        threading.Thread(target=self._preview_worker, args=(token,), daemon=True).start()

    def _preview_worker(self, token: int):
        try:
            src = self._sources()
            rows, errors = [], []
            for kind in ("gstr1", "sales", "gstr2b", "purchase"):
                s = src[kind]
                if not s:
                    continue
                try:
                    rows += engine.preview_rows(s)
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{s.label}: could not read '{s.name}' ({e})")
            client, fy = engine.guess_client_fy(src["sales"], src["purchase"], src["gstr3b"])
            self.q.put(("preview", token, rows, errors, client, fy))
        except Exception as e:  # noqa: BLE001
            log_error(e)
            self.q.put(("preview", token, [], [f"Could not read the files: {e}"], "", ""))

    def generate(self):
        if self.busy:
            return
        p = self.pickers
        if not any(p[k].path for k in ("gstr1", "sales", "gstr2b", "purchase")):
            messagebox.showinfo(APP_NAME, "Select at least the GSTR-1 / Sales files or the "
                                          "GSTR-2B / Purchase files.")
            return
        outdir = self.outdir.get().strip()
        if not outdir:
            messagebox.showinfo(APP_NAME, "Choose the folder to save the reco files in.")
            return
        client = self.client.get().strip() or "Client"
        fy = self.fy.get().strip() or "2025-26"
        self.busy = True
        self.gen_btn.configure(state="disabled", text="Working…")
        self.progress.pack(side="left", padx=(16, 0), before=self.status)
        self.progress.start()
        self.status.configure(text="Building workbooks…", text_color=MUTED)
        self._clear_results()
        threading.Thread(target=self._gen_worker, args=(Path(outdir), client, fy),
                         daemon=True).start()

    def _gen_worker(self, outdir: Path, client: str, fy: str):
        try:
            s = self._sources()
            res = engine.generate(outdir, client, fy, s["gstr1"], s["gstr3b"], s["sales"],
                                  s["gstr2b"], s["purchase"])
            self.q.put(("done", res, None))
        except PermissionError as e:
            self.q.put(("done", [], str(e)))
        except Exception as e:  # noqa: BLE001
            log = log_error(e)
            self.q.put(("done", [], f"Something went wrong: {e}\n\nDetails saved in {log}"))

    # ---- results ------------------------------------------------------------------------
    def _poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "preview":
                    self._show_preview(*msg[1:])
                elif msg[0] == "done":
                    self._show_done(*msg[1:])
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _show_preview(self, token, rows, errors, client, fy):
        if token != self._preview_token:
            return
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            tags = ["odd"] if i % 2 else []
            if not r["Rows"]:
                tags.append("empty")
            self.tree.insert("", "end", tags=tags, values=(
                r["File"], r["Sheet"], r["Rows"], fmt_amt(r["Taxable"]), fmt_amt(r["IGST"]),
                fmt_amt(r["CGST"]), fmt_amt(r["SGST"])))
        if client and not self.user_edited["client"]:
            self._set_entry(self.client, client)
        if fy and not self.user_edited["fy"]:
            self._set_entry(self.fy, fy)
        self._log(errors, replace=True)
        if errors:
            self.status.configure(text="Some files could not be read - see Messages.",
                                  text_color="#B91C1C")
            self._show_tab("Messages")
        else:
            n = sum(1 for fp in self.pickers.values() if fp.path)
            self.status.configure(text=f"{n} file(s) ready. Check the totals, then Generate.",
                                  text_color=MUTED)

    def _show_done(self, results, error):
        self.busy = False
        self.progress.stop()
        self.progress.pack_forget()
        self.gen_btn.configure(state="normal", text="Generate reco workbooks")
        if error:
            self.status.configure(text="Not generated - see message.", text_color="#B91C1C")
            messagebox.showerror(APP_NAME, error)
            return
        self.results = results
        lines = []
        for r in results:
            lines.append(f"✔ {r.label}: {r.path}")
            lines += [f"   ⚠ {w}" for w in r.warnings]
        self._log(lines, replace=True)
        warn = any(r.warnings for r in results)
        self.status.configure(
            text=("Done - with warnings, see Messages." if warn else "Done."),
            text_color="#B45309" if warn else OK_GREEN)
        if warn:
            self._show_tab("Messages")
        for r in results:
            ctk.CTkButton(self.open_frame, text=f"Open {r.label}", height=36,
                          fg_color=OK_GREEN, hover_color="#1B5E20",
                          command=lambda p=r.path: os.startfile(p)).pack(side="left", padx=4)
        if results:
            ctk.CTkButton(self.open_frame, text="Open folder", height=36, width=110,
                          fg_color="#E8EEF6", text_color=ACCENT, hover_color="#D6E2F0",
                          command=lambda: os.startfile(results[0].path.parent)
                          ).pack(side="left", padx=4)

    def _clear_results(self):
        for w in self.open_frame.winfo_children():
            w.destroy()

    def _log(self, lines, replace=False):
        self.msgs.configure(state="normal")
        if replace:
            self.msgs.delete("1.0", "end")
        self.msgs.insert("end", "\n".join(lines) + ("\n" if lines else ""))
        self.msgs.configure(state="disabled")


def main():
    # Hidden command-line mode, e.g. for testing the packaged exe.
    if "--cli" in sys.argv:
        sys.exit(engine.run_cli(sys.argv[1:]))
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001
        pass
    App().mainloop()


if __name__ == "__main__":
    main()
