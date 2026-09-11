"""
Form 3CD Tax Audit Analyzer - GUI

Tkinter front-end for the extraction/report-building logic in
analyze_form3cd.py. Produces the same Excel workbook + HTML dashboard as the
console tool, driven from a file-picker window instead of the command line.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from analyze_form3cd import ALL_FORMATS, DEFAULT_FORMATS, process_one

FORMAT_LABELS = {
    "xlsx": "Excel workbook (.xlsx)",
    "html": "HTML dashboard (.html)",
    "pdf": "PDF report (.pdf)",
    "docx": "Word report (.docx)",
}

PURPLE_DARK = "#4A148C"
PURPLE = "#6A1B9A"
PURPLE_MID = "#8E24AA"
PURPLE_LIGHT = "#F3E5F5"
WHITE = "#FFFFFF"
TEXT_DARK = "#2B0A3D"

DONE_OK = "__DONE_OK__"
DONE_ERROR = "__DONE_ERROR__"


class CheckOption:
    """A small purple/white checkbox with a real checkmark glyph.

    ttk's 'clam' theme (used for the purple button styling elsewhere in this
    app) draws its native Checkbutton indicator as an "x", not a tick, and
    that glyph isn't restylable per-widget - so this draws its own box.
    """

    def __init__(self, parent, text: str, checked: bool):
        self.var = tk.BooleanVar(value=checked)
        self.frame = tk.Frame(parent, bg=WHITE, cursor="hand2")
        self.box = tk.Label(self.frame, width=2, bg=WHITE, fg=PURPLE_DARK,
                             highlightbackground=PURPLE, highlightthickness=1,
                             font=("Segoe UI", 10, "bold"))
        self.box.pack(side="left")
        self.label = tk.Label(self.frame, text=text, bg=WHITE, fg=TEXT_DARK,
                               font=("Segoe UI", 10), cursor="hand2")
        self.label.pack(side="left", padx=(6, 0))
        for widget in (self.frame, self.box, self.label):
            widget.bind("<Button-1>", self._toggle)
        self._render()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def _toggle(self, _event=None):
        self.var.set(not self.var.get())
        self._render()

    def _render(self):
        if self.var.get():
            self.box.configure(bg=PURPLE_DARK, fg=WHITE, text="✓")
        else:
            self.box.configure(bg=WHITE, fg=WHITE, text="")

    def get(self) -> bool:
        return self.var.get()


class QueueWriter:
    """file-like object so print() in the worker thread reaches the GUI thread safely."""

    def __init__(self, q: "queue.Queue[str]"):
        self.q = q

    def write(self, msg):
        if msg.strip():
            self.q.put(msg)

    def flush(self):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Form 3CD Tax Audit Analyzer")
        self.geometry("840x620")
        self.minsize(740, 540)
        self.configure(bg=WHITE)

        self.selected_files: list[Path] = []
        self.output_dirs: list[Path] = []
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_style()
        self._build_header()
        self._build_body()
        self._build_log()
        self._build_statusbar()

        self.after(100, self._poll_log_queue)

    # ------------------------------------------------------------------ UI

    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Purple.TButton", background=PURPLE, foreground=WHITE,
                         font=("Segoe UI", 10, "bold"), padding=8, borderwidth=0)
        style.map("Purple.TButton", background=[("active", PURPLE_DARK), ("disabled", "#D8BEE8")])
        style.configure("Ghost.TButton", background=WHITE, foreground=PURPLE_DARK,
                         font=("Segoe UI", 9), padding=6, borderwidth=1)
        style.map("Ghost.TButton", background=[("active", PURPLE_LIGHT)])
        style.configure("TFrame", background=WHITE)
        style.configure("TLabel", background=WHITE, foreground=TEXT_DARK, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=PURPLE_DARK, foreground=WHITE, font=("Segoe UI", 16, "bold"))
        style.configure("SubHeader.TLabel", background=PURPLE_DARK, foreground=PURPLE_LIGHT, font=("Segoe UI", 9))
        style.configure("Section.TLabel", background=WHITE, foreground=PURPLE_DARK, font=("Segoe UI", 10, "bold"))
        style.configure("Vertical.TScrollbar", background=PURPLE_LIGHT, troughcolor=WHITE, arrowcolor=PURPLE_DARK)

    def _build_header(self):
        # No fixed height / pack_propagate(False) here: the exact pixel height
        # of two stacked labels varies with the system's font metrics and
        # DPI scaling, so a hardcoded height risks clipping the subtitle on
        # some machines. Let the frame size itself to its content instead.
        header = tk.Frame(self, bg=PURPLE_DARK)
        header.pack(fill="x", side="top")
        ttk.Label(header, text="Form 3CD Tax Audit Analyzer", style="Header.TLabel").pack(anchor="w", padx=20, pady=(14, 2))
        ttk.Label(header,
                  text="Clause-referenced financial summary, 44-clause dashboard and tax computation draft from a Form 3CD JSON",
                  style="SubHeader.TLabel").pack(anchor="w", padx=20, pady=(0, 14))

    def _build_body(self):
        body = ttk.Frame(self)
        body.pack(fill="x", padx=20, pady=(16, 6))
        body.columnconfigure(0, weight=1)

        ttk.Label(body, text="1.  Form 3CD JSON file(s)", style="Section.TLabel").grid(row=0, column=0, sticky="w")

        list_border = tk.Frame(body, bg=PURPLE, bd=0)
        list_border.grid(row=1, column=0, sticky="ew", pady=(6, 8))
        self.file_listbox = tk.Listbox(list_border, height=5, activestyle="none",
                                        bg=WHITE, fg=TEXT_DARK, selectbackground=PURPLE_MID,
                                        selectforeground=WHITE, borderwidth=0, highlightthickness=0)
        self.file_listbox.pack(fill="x", padx=1, pady=1)

        btn_row = ttk.Frame(body)
        btn_row.grid(row=2, column=0, sticky="w")
        ttk.Button(btn_row, text="Add File(s)...", style="Purple.TButton", command=self.add_files).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Remove Selected", style="Ghost.TButton", command=self.remove_selected).pack(side="left", padx=(0, 8))
        ttk.Button(btn_row, text="Clear All", style="Ghost.TButton", command=self.clear_files).pack(side="left")

        ttk.Label(body, text="2.  Output format(s)", style="Section.TLabel").grid(row=3, column=0, sticky="w", pady=(18, 6))
        formats_row = ttk.Frame(body)
        formats_row.grid(row=4, column=0, sticky="w")
        self.format_options: dict[str, CheckOption] = {}
        for fmt in ALL_FORMATS:
            opt = CheckOption(formats_row, FORMAT_LABELS[fmt], checked=fmt in DEFAULT_FORMATS)
            opt.pack(side="left", padx=(0, 20))
            self.format_options[fmt] = opt

        ttk.Label(body, text="3.  Output folder  (optional - default: same folder as each JSON file)",
                  style="Section.TLabel").grid(row=5, column=0, sticky="w", pady=(18, 6))
        out_row = ttk.Frame(body)
        out_row.grid(row=6, column=0, sticky="ew")
        out_row.columnconfigure(0, weight=1)
        self.outdir_var = tk.StringVar()
        out_entry = tk.Entry(out_row, textvariable=self.outdir_var, bg=WHITE, fg=TEXT_DARK,
                              relief="solid", highlightbackground=PURPLE, highlightcolor=PURPLE, highlightthickness=1, bd=0)
        out_entry.grid(row=0, column=0, sticky="ew", ipady=5, padx=(0, 8))
        ttk.Button(out_row, text="Browse...", style="Ghost.TButton", command=self.browse_outdir).grid(row=0, column=1)

        action_row = ttk.Frame(body)
        action_row.grid(row=7, column=0, sticky="w", pady=(18, 4))
        self.analyze_btn = ttk.Button(action_row, text="Analyze", style="Purple.TButton", command=self.start_analysis)
        self.analyze_btn.pack(side="left", padx=(0, 10))
        self.open_output_btn = ttk.Button(action_row, text="Open Output Folder", style="Ghost.TButton",
                                           command=self.open_output_folder, state="disabled")
        self.open_output_btn.pack(side="left")

    def _build_log(self):
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=(10, 6))
        ttk.Label(frame, text="4.  Progress log", style="Section.TLabel").pack(anchor="w")
        log_container = tk.Frame(frame, bg=PURPLE, bd=0)
        log_container.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text = tk.Text(log_container, bg=WHITE, fg=TEXT_DARK, wrap="word",
                                 font=("Consolas", 9), borderwidth=0, highlightthickness=0)
        scroll = ttk.Scrollbar(log_container, command=self.log_text.yview, style="Vertical.TScrollbar")
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        scroll.pack(side="right", fill="y")
        self.log_text.configure(state="disabled")

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Ready")
        bar = tk.Frame(self, bg=PURPLE_LIGHT, height=30)
        bar.pack(fill="x", side="bottom")
        tk.Label(bar, textvariable=self.status_var, bg=PURPLE_LIGHT, fg=PURPLE_DARK,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=14, pady=5)

    # ------------------------------------------------------------ actions

    def add_files(self):
        paths = filedialog.askopenfilenames(title="Select Form 3CD JSON file(s)",
                                             filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        for p in paths:
            pp = Path(p)
            if pp not in self.selected_files:
                self.selected_files.append(pp)
                self.file_listbox.insert("end", str(pp))

    def remove_selected(self):
        for idx in reversed(self.file_listbox.curselection()):
            self.file_listbox.delete(idx)
            del self.selected_files[idx]

    def clear_files(self):
        self.file_listbox.delete(0, "end")
        self.selected_files.clear()

    def browse_outdir(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.outdir_var.set(d)

    def open_output_folder(self):
        if self.output_dirs:
            try:
                os.startfile(str(self.output_dirs[-1]))
            except OSError as exc:
                messagebox.showerror("Could not open folder", str(exc))

    def log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg if msg.endswith("\n") else msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == DONE_OK:
                    self.status_var.set("Done")
                    self.analyze_btn.configure(state="normal")
                    self.open_output_btn.configure(state="normal")
                    messagebox.showinfo("Analysis complete", "All files processed successfully.")
                elif msg == DONE_ERROR:
                    self.status_var.set("Completed with errors")
                    self.analyze_btn.configure(state="normal")
                    self.open_output_btn.configure(state="normal")
                    messagebox.showwarning("Completed with errors",
                                            "Some files could not be processed. See the log for details.")
                else:
                    self.log(msg)
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    def start_analysis(self):
        if not self.selected_files:
            messagebox.showwarning("No files selected", "Please add at least one Form 3CD JSON file.")
            return
        formats = tuple(fmt for fmt, opt in self.format_options.items() if opt.get())
        if not formats:
            messagebox.showwarning("No output format selected", "Please tick at least one output format.")
            return
        if self.worker and self.worker.is_alive():
            return
        self.analyze_btn.configure(state="disabled")
        self.open_output_btn.configure(state="disabled")
        self.status_var.set("Processing...")
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        outdir = Path(self.outdir_var.get()) if self.outdir_var.get().strip() else None
        files = list(self.selected_files)
        self.worker = threading.Thread(target=self._run_analysis, args=(files, outdir, formats), daemon=True)
        self.worker.start()

    def _run_analysis(self, files: list[Path], outdir: Path | None, formats: tuple[str, ...]):
        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.log_queue)
        had_error = False
        out_dirs = []
        try:
            for jp in files:
                try:
                    process_one(jp, outdir, formats)
                    out_dirs.append(outdir or jp.parent)
                except Exception as exc:
                    had_error = True
                    print(f"[ERROR] Could not process {jp}: {exc}")
        finally:
            sys.stdout = old_stdout
        self.output_dirs = out_dirs
        self.log_queue.put(DONE_ERROR if had_error else DONE_OK)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
