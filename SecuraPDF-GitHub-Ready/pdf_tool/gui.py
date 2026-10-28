from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .converter import (compress_pdf, convert_to_docx, convert_to_xlsx,
                        merge_pdfs, parse_ranges, split_pdf)


def _resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / relative_path


class PdfToolApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SecuraPDF")
        self.geometry("1280x820")
        self.minsize(980, 680)
        try:
            self.iconbitmap(str(_resource_path("pdf_tool/assets/pdf_utility.ico")))
        except tk.TclError:
            pass
        self.configure(bg="#F2F6FB")
        self.events = queue.Queue()
        self._build()
        self.after(100, self._poll)

    def _build(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("App.TFrame", background="#F2F6FB")
        style.configure("Card.TFrame", background="#FFFFFF")
        style.configure("TFrame", background="#FFFFFF")
        style.configure("TLabel", background="#FFFFFF", foreground="#2A3E52",
                        font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#F2F6FB", foreground="#163B65",
                        font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", background="#F2F6FB", foreground="#63758B",
                        font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#FFFFFF", foreground="#173B62",
                        font=("Segoe UI", 13, "bold"))
        style.configure("CardText.TLabel", background="#FFFFFF", foreground="#64758A",
                        font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7))
        style.configure("TEntry", padding=7)
        style.configure("TLabelframe", background="#FFFFFF")
        style.configure("TLabelframe.Label", background="#FFFFFF", foreground="#173B62",
                        font=("Segoe UI", 10, "bold"))

        shell = tk.Frame(self, bg="#F2F6FB")
        shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(shell, width=228, bg="#073765")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg="#073765")
        brand.pack(fill="x", padx=18, pady=(22, 28))
        tk.Label(brand, text="▤", font=("Segoe UI Symbol", 23, "bold"),
                 fg="#FFFFFF", bg="#0F5795", width=2, height=1).pack(side="left")
        tk.Label(brand, text="SecuraPDF", justify="left", anchor="w",
                 font=("Segoe UI", 13, "bold"), fg="#FFFFFF", bg="#073765").pack(side="left", padx=10)

        self.nav_buttons = {}
        nav_items = [
            ("home", "⌂", "Home"),
            ("word", "W", "PDF to Word"),
            ("excel", "X", "PDF to Excel"),
            ("merge", "↔", "Merge PDF"),
            ("split", "⇄", "Split PDF"),
            ("compress", "↓", "Compress PDF"),
            ("settings", "⚙", "Tool Settings"),
            ("help", "?", "Help"),
        ]
        for key, icon, label in nav_items:
            button = tk.Button(
                self.sidebar, text=f"  {icon}     {label}", anchor="w", relief="flat",
                bd=0, padx=14, pady=11, cursor="hand2", font=("Segoe UI", 10),
                fg="#EAF3FC", bg="#073765", activeforeground="#FFFFFF",
                activebackground="#175A96", command=lambda page=key: self._navigate(page),
            )
            button.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = button
        tk.Frame(self.sidebar, bg="#2A6599", height=1).pack(fill="x", padx=18, pady=(20, 12))
        tk.Label(self.sidebar, text="100% OFFLINE\nYour documents stay on this device.",
                 justify="left", anchor="w", font=("Segoe UI", 9), fg="#C6D9EE",
                 bg="#073765").pack(side="bottom", fill="x", padx=20, pady=20)

        main = tk.Frame(shell, bg="#F2F6FB")
        main.pack(side="left", fill="both", expand=True)
        topbar = tk.Frame(main, bg="#FFFFFF", height=60,
                          highlightbackground="#DDE6F0", highlightthickness=1)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self.breadcrumb = tk.StringVar(value="Home")
        tk.Label(topbar, textvariable=self.breadcrumb, bg="#FFFFFF", fg="#173B62",
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=26)
        tk.Label(topbar, text="●  OFFLINE", bg="#FFFFFF", fg="#18845B",
                 font=("Segoe UI", 9, "bold")).pack(side="right", padx=24)

        self.page_area = ttk.Frame(main, style="App.TFrame")
        self.page_area.pack(fill="both", expand=True)
        self.pages = {}
        self.home_page = ttk.Frame(self.page_area, style="App.TFrame", padding=(28, 12))
        self.pages["home"] = self.home_page
        self._build_home()

        self.convert_tab = self._make_page("word", "PDF to Word", "Convert PDF documents into editable Word files.")
        self.excel_tab = self._make_page("excel", "PDF to Excel", "Extract PDF tables and text into an Excel workbook.")
        self.merge_tab = self._make_page("merge", "Merge PDF", "Combine multiple PDF files in the order you choose.")
        self.split_tab = self._make_page("split", "Split PDF", "Extract a page range or create several smaller PDFs.")
        self.compress_tab = self._make_page("compress", "Compress PDF", "Reduce PDF file size with a quality level you choose.")
        self.settings_tab = self._make_page("settings", "Tool Settings", "Set defaults and review how the tool handles your files.")
        self.help_tab = self._make_page("help", "Help", "Quick guidance for using SecuraPDF.")

        self._build_convert()
        self._build_merge()
        self._build_split()
        self._build_excel()
        self._build_compress()
        self._build_settings()
        self._build_help()

        footer = tk.Frame(main, bg="#FFFFFF", highlightbackground="#DDE6F0", highlightthickness=1)
        footer.pack(fill="x", side="bottom")
        self.status = tk.StringVar(value="Ready · Files stay on this computer")
        status_row = tk.Frame(footer, bg="#FFFFFF")
        status_row.pack(fill="x", padx=20, pady=(8, 3))
        tk.Label(status_row, textvariable=self.status, bg="#FFFFFF", fg="#53677E",
                 font=("Segoe UI", 9), anchor="w").pack(side="left", fill="x", expand=True)
        self.cancel_button = ttk.Button(status_row, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_button.pack(side="right")
        self.progress = ttk.Progressbar(footer, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=20, pady=(2, 9))
        self._navigate("home")

    def _make_page(self, key: str, title: str, subtitle: str):
        page = ttk.Frame(self.page_area, style="App.TFrame", padding=(30, 26))
        ttk.Label(page, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(page, text=subtitle, style="Subtitle.TLabel").pack(anchor="w", pady=(4, 18))
        card = ttk.Frame(page, style="Card.TFrame", padding=24)
        card.pack(fill="both", expand=True)
        self.pages[key] = page
        return card

    def _navigate(self, key: str):
        for page in self.pages.values():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        labels = {"home": "Home", "word": "PDF to Word", "excel": "PDF to Excel",
                  "merge": "Merge PDF", "split": "Split PDF", "compress": "Compress PDF",
                  "settings": "Tool Settings", "help": "Help"}
        self.breadcrumb.set(labels[key])
        for button_key, button in self.nav_buttons.items():
            selected = button_key == key
            button.configure(bg="#155A95" if selected else "#073765",
                             fg="#FFFFFF" if selected else "#EAF3FC",
                             font=("Segoe UI", 10, "bold" if selected else "normal"))

    def _build_home(self):
        welcome_row = tk.Frame(self.home_page, bg="#F2F6FB")
        welcome_row.pack(fill="x")
        ttk.Label(welcome_row, text="Welcome to your SecuraPDF workspace",
                  style="Title.TLabel").pack(side="left", anchor="w")
        tk.Label(welcome_row, text="Created by - CA Gagan Jhavar", bg="#F2F6FB",
                 fg="#234F7D", font=("Segoe UI", 12, "bold italic")).pack(side="right", anchor="e", padx=(12, 2))
        ttk.Label(self.home_page, text="Fast, simple document tools that work offline.",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(4, 16))

        hero = tk.Frame(self.home_page, bg="#E5F1FC", highlightbackground="#C9DDF1",
                        highlightthickness=1, height=140)
        hero.pack(fill="x", pady=(0, 20))
        hero.pack_propagate(False)
        hero_copy = tk.Frame(hero, bg="#E5F1FC")
        hero_copy.pack(side="left", fill="both", expand=True, padx=24, pady=14)
        tk.Label(hero_copy, text="Your document workflow,\nall in one place.", justify="left",
                 anchor="w", bg="#E5F1FC", fg="#103E6D",
                 font=("Segoe UI", 19, "bold")).pack(anchor="w")
        tk.Label(hero_copy, text="Convert  ·  Extract  ·  Organize  ·  Compress",
                 bg="#E5F1FC", fg="#456887", font=("Segoe UI", 10)).pack(anchor="w", pady=(8, 12))
        ttk.Button(hero_copy, text="Get started", command=lambda: self._navigate("word")).pack(anchor="w")
        art = tk.Canvas(hero, width=150, height=128, bg="#E5F1FC", highlightthickness=0)
        art.pack(side="right", padx=(4, 22), pady=5)
        art.create_oval(22, 4, 128, 110, fill="#D2E7F8", outline="")
        art.create_rectangle(54, 18, 98, 91, fill="#FFFFFF", outline="#5D96C9", width=2)
        art.create_polygon(86, 18, 98, 30, 86, 30, fill="#C7DEF1", outline="#5D96C9")
        for y in (42, 53, 64):
            art.create_line(62, y, 90, y, fill="#82A9CC", width=2)
        art.create_rectangle(61, 73, 91, 86, fill="#D93A48", outline="")
        art.create_text(76, 80, text="PDF", fill="#FFFFFF", font=("Segoe UI", 8, "bold"))

        ttk.Label(self.home_page, text="Choose a tool", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))
        grid = tk.Frame(self.home_page, bg="#F2F6FB")
        grid.pack(fill="both", expand=True)
        tools = [
            ("word", "W", "PDF to Word", "Convert PDFs into editable Word documents.", "#E8F3FF", "#1373C8"),
            ("excel", "X", "PDF to Excel", "Extract tables and data into worksheets.", "#E8F7EE", "#16834B"),
            ("merge", "↔", "Merge PDF", "Combine multiple PDFs into one file.", "#F2ECFC", "#7739B5"),
            ("split", "⇄", "Split PDF", "Extract pages or split into multiple files.", "#FFF1E5", "#D25B18"),
            ("compress", "↓", "Compress PDF", "Reduce file size with quality presets.", "#E4F7F8", "#008B94"),
            ("settings", "⚙", "Tool Settings", "Choose defaults and view privacy details.", "#EAF0F8", "#365F8C"),
        ]
        for column in range(3):
            grid.columnconfigure(column, weight=1, uniform="toolcard")
        for index, (key, icon, title, description, tint, accent) in enumerate(tools):
            row, column = divmod(index, 3)
            card = tk.Frame(grid, bg="#FFFFFF", highlightbackground="#D8E3EE", highlightthickness=1,
                            cursor="hand2")
            card.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 8),
                      pady=(0, 8), ipady=2)
            grid.rowconfigure(row, weight=1, uniform="toolrow")
            icon_box = tk.Label(card, text=icon, bg=tint, fg=accent,
                                font=("Segoe UI Symbol", 21, "bold"), width=3, height=1)
            icon_box.pack(anchor="w", padx=14, pady=(8, 4))
            title_label = tk.Label(card, text=title, bg="#FFFFFF", fg=accent,
                                   font=("Segoe UI", 12, "bold"), anchor="w")
            title_label.pack(fill="x", padx=14)
            desc_label = tk.Label(card, text=description, bg="#FFFFFF", fg="#566B80",
                                  font=("Segoe UI", 9), anchor="w", justify="left", wraplength=230)
            desc_label.pack(fill="x", padx=14, pady=(3, 5))
            for widget in (card, icon_box, title_label, desc_label):
                widget.bind("<Button-1>", lambda _event, page=key: self._navigate(page))

        tk.Label(self.home_page, text="Privacy by Design. Security by Default",
                 bg="#0B4778", fg="#FFFFFF", font=("Segoe UI", 12, "bold"),
                 padx=14, pady=8).pack(fill="x", pady=(2, 0))

    def _build_settings(self):
        ttk.Label(self.settings_tab, text="Default compression quality",
                  style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(self.settings_tab, text="This default is selected whenever you open the Compress PDF page.",
                  style="CardText.TLabel").pack(anchor="w", pady=(5, 10))
        ttk.Combobox(
            self.settings_tab, textvariable=self.compress_preset,
            values=("High compress - Low quality", "Medium compress - Moderate quality",
                    "Low compress - High quality"), state="readonly", width=38,
        ).pack(anchor="w")
        ttk.Separator(self.settings_tab).pack(fill="x", pady=18)
        ttk.Label(self.settings_tab, text="Privacy and file handling", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(self.settings_tab,
                  text="SecuraPDF processes files locally. It does not upload documents or require an internet connection. Output files are saved only to the locations you select.",
                  style="CardText.TLabel", wraplength=650, justify="left").pack(anchor="w", pady=(6, 0))

    def _build_help(self):
        help_text = (
            "PDF to Word\nChoose a PDF, select editable content or a visual copy, and choose where to save the DOCX.\n\n"
            "PDF to Excel\nDetected tables are placed on separate worksheets. Other selectable text is saved by page. Scanned pages need OCR.\n\n"
            "Merge and split\nAdd PDFs in the order you want to merge them, or enter page ranges to create split files.\n\n"
            "Compress PDF\nChoose a compression and image-quality preset. Existing digital signatures will be invalidated when a PDF is rewritten.\n\n"
            "Offline processing\nAll processing is performed on this computer. Keep the source file until you have reviewed the result."
        )
        ttk.Label(self.help_tab, text=help_text, style="CardText.TLabel",
                  wraplength=720, justify="left").pack(anchor="nw")

    def _row(self, parent, label, variable, browse):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=7)
        ttk.Label(row, text=label, width=19).pack(side="left", anchor="w")
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True, padx=7)
        ttk.Button(row, text="Browse…", command=browse).pack(side="right")

    def _build_convert(self):
        self.cvt_src, self.cvt_out = tk.StringVar(), tk.StringVar()
        self._row(self.convert_tab, "Input PDF", self.cvt_src, self._pick_pdf)
        self._row(self.convert_tab, "Output Word file", self.cvt_out, self._pick_docx)
        options = ttk.LabelFrame(self.convert_tab, text="Conversion options", padding=12)
        options.pack(fill="x", pady=12)
        self.cvt_mode = tk.StringVar(value="Editable content")
        ttk.Label(options, text="Mode").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Combobox(options, textvariable=self.cvt_mode, values=("Editable content", "Visual copy (pages as images)"), state="readonly", width=34).grid(row=0, column=1, sticky="w")
        self.cvt_pages = tk.StringVar()
        ttk.Label(options, text="Page range (optional)").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(options, textvariable=self.cvt_pages, width=18).grid(row=1, column=1, sticky="w")
        ttk.Label(options, text="Example: 2-5", foreground="#666").grid(row=1, column=2, sticky="w", padx=8)
        self.cvt_ocr = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text="Use locally installed Tesseract OCR for scanned pages (English + Hindi)", variable=self.cvt_ocr).grid(row=2, column=0, columnspan=3, sticky="w", pady=5)
        ttk.Button(self.convert_tab, text="Convert to Word", command=self._convert).pack(anchor="e", pady=8)

    def _build_merge(self):
        ttk.Label(self.merge_tab, text="Select at least two PDFs. Their pages will be appended in the displayed order.", wraplength=600).pack(anchor="w", pady=(0, 12))
        self.merge_list = tk.Listbox(self.merge_tab, height=12, selectmode="extended")
        self.merge_list.pack(fill="both", expand=True)
        controls = ttk.Frame(self.merge_tab)
        controls.pack(fill="x", pady=10)
        ttk.Button(controls, text="Add PDFs…", command=self._merge_add).pack(side="left")
        ttk.Button(controls, text="Remove selected", command=self._merge_remove).pack(side="left", padx=8)
        ttk.Button(controls, text="Move up", command=lambda: self._move(-1)).pack(side="left")
        ttk.Button(controls, text="Move down", command=lambda: self._move(1)).pack(side="left", padx=8)
        ttk.Button(controls, text="Merge…", command=self._merge).pack(side="right")

    def _build_split(self):
        self.split_src = tk.StringVar()
        self._row(self.split_tab, "Input PDF", self.split_src, self._pick_split_pdf)
        ttk.Label(self.split_tab, text="Enter one or more page ranges. Each comma-separated item creates a separate PDF.", wraplength=620).pack(anchor="w", pady=(15, 5))
        self.split_ranges = tk.StringVar(value="1-2,3-4")
        ttk.Entry(self.split_tab, textvariable=self.split_ranges, width=32).pack(anchor="w")
        ttk.Label(self.split_tab, text="Example: 1-3,4,5-7 creates three output files.", foreground="#666").pack(anchor="w", pady=4)
        ttk.Button(self.split_tab, text="Split into folder…", command=self._split).pack(anchor="e", pady=18)

    def _build_excel(self):
        self.excel_src, self.excel_out = tk.StringVar(), tk.StringVar()
        self._row(self.excel_tab, "Input PDF", self.excel_src, self._pick_excel_pdf)
        self._row(self.excel_tab, "Output Excel file", self.excel_out, self._pick_xlsx)
        ttk.Label(
            self.excel_tab,
            text="Detected tables are saved on separate worksheets. Other selectable text is included in page text worksheets. Scanned pages need OCR before their text can be extracted.",
            wraplength=630, justify="left",
        ).pack(anchor="w", pady=(16, 8))
        ttk.Button(self.excel_tab, text="Convert to Excel", command=self._convert_excel).pack(anchor="e", pady=10)

    def _build_compress(self):
        self.compress_src, self.compress_out = tk.StringVar(), tk.StringVar()
        self._row(self.compress_tab, "Input PDF", self.compress_src, self._pick_compress_pdf)
        self._row(self.compress_tab, "Output PDF", self.compress_out, self._pick_compressed_pdf)
        options = ttk.LabelFrame(self.compress_tab, text="Compression options", padding=12)
        options.pack(fill="x", pady=12)
        self.compress_preset = tk.StringVar(value="Medium compress - Moderate quality")
        ttk.Label(options, text="Preset").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Combobox(
            options, textvariable=self.compress_preset,
            values=(
                "High compress - Low quality",
                "Medium compress - Moderate quality",
                "Low compress - High quality",
            ), state="readonly", width=36,
        ).grid(row=0, column=1, sticky="w")
        ttk.Label(
            options,
            text="High compression uses stronger image reduction (100 dpi target, quality 55). Medium uses 150 dpi and quality 78. Low compression keeps more image detail (225 dpi, quality 90). Image quality can decrease; results depend on the source PDF.",
            wraplength=600, justify="left", foreground="#555",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 2))
        ttk.Button(self.compress_tab, text="Compress PDF", command=self._compress).pack(anchor="e", pady=8)

    def _pick_pdf(self):
        value = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if value:
            self.cvt_src.set(value)
            self.cvt_out.set(str(Path(value).with_suffix(".docx")))

    def _pick_docx(self):
        value = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word document", "*.docx")])
        if value:
            self.cvt_out.set(value)

    def _pick_split_pdf(self):
        value = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if value:
            self.split_src.set(value)

    def _pick_excel_pdf(self):
        value = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if value:
            self.excel_src.set(value)
            self.excel_out.set(str(Path(value).with_suffix(".xlsx")))

    def _pick_xlsx(self):
        value = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel workbook", "*.xlsx")])
        if value:
            self.excel_out.set(value)

    def _pick_compress_pdf(self):
        value = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if value:
            self.compress_src.set(value)
            path = Path(value)
            self.compress_out.set(str(path.with_name(f"{path.stem}_compressed.pdf")))

    def _pick_compressed_pdf(self):
        value = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if value:
            self.compress_out.set(value)

    def _merge_add(self):
        for path in filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")]):
            self.merge_list.insert("end", path)

    def _merge_remove(self):
        for i in reversed(self.merge_list.curselection()):
            self.merge_list.delete(i)

    def _move(self, direction):
        selection = self.merge_list.curselection()
        if not selection:
            return
        i = selection[0]
        j = i + direction
        if 0 <= j < self.merge_list.size():
            value = self.merge_list.get(i)
            self.merge_list.delete(i)
            self.merge_list.insert(j, value)
            self.merge_list.selection_set(j)

    def _run(self, work):
        self.cancel_event = threading.Event()
        self.cancel_button.configure(state="normal")
        self.progress.configure(value=0, mode="determinate")
        self.status.set("Working…")
        def worker():
            try:
                result = work(self._report_progress)
                self.events.put(("done", result))
            except InterruptedError:
                self.events.put(("cancelled", None))
            except Exception as exc:
                self.events.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _report_progress(self, percent, message):
        if self.cancel_event.is_set():
            raise InterruptedError("Cancelled")
        self.events.put(("progress", (percent, message)))

    def _cancel(self):
        if hasattr(self, "cancel_event"):
            self.cancel_event.set()
            self.status.set("Cancelling after the current page or file…")

    def _convert(self):
        src, out = self.cvt_src.get().strip(), self.cvt_out.get().strip()
        if not src or not out:
            messagebox.showerror("Missing path", "Choose an input PDF and output Word file.")
            return
        if Path(src).resolve() == Path(out).resolve():
            messagebox.showerror("Invalid output", "The output must be a different file from the source.")
            return
        if Path(out).exists() and not messagebox.askyesno("Replace existing file?", f"{out} already exists. Replace it?"):
            return
        try:
            pages = parse_ranges(self.cvt_pages.get()) if self.cvt_pages.get().strip() else None
            page_range = (pages[0][0], pages[-1][1]) if pages else None
            if pages and (len(pages) > 1 or pages[0][0] != pages[0][1] and "," in self.cvt_pages.get()):
                raise ValueError("Conversion accepts one continuous range, such as 2-5.")
        except Exception as exc:
            messagebox.showerror("Invalid page range", str(exc))
            return
        mode = "visual" if self.cvt_mode.get().startswith("Visual") else "editable"
        use_ocr = self.cvt_ocr.get()
        self._run(lambda progress: convert_to_docx(src, out, mode=mode, page_range=page_range, ocr=use_ocr, progress=progress))

    def _merge(self):
        paths = list(self.merge_list.get(0, "end"))
        if len(paths) < 2:
            messagebox.showerror("Choose PDFs", "Add at least two PDF files.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not out:
            return
        if Path(out).exists() and not messagebox.askyesno("Replace existing file?", f"{out} already exists. Replace it?"):
            return
        if Path(out).resolve() in [Path(p).resolve() for p in paths]:
            messagebox.showerror("Invalid output", "Choose a new output file, not one of the inputs.")
            return
        self._run(lambda progress: f"Merged {merge_pdfs(paths, out, progress)} pages into {out}")

    def _split(self):
        src = self.split_src.get().strip()
        if not src:
            messagebox.showerror("Choose PDF", "Choose an input PDF.")
            return
        folder = filedialog.askdirectory()
        if not folder:
            return
        try:
            ranges = parse_ranges(self.split_ranges.get())
        except Exception as exc:
            messagebox.showerror("Invalid page ranges", str(exc))
            return
        self._run(lambda progress: "Created:\n" + "\n".join(map(str, split_pdf(src, folder, ranges, progress))))

    def _convert_excel(self):
        src, out = self.excel_src.get().strip(), self.excel_out.get().strip()
        if not src or not out:
            messagebox.showerror("Missing path", "Choose an input PDF and output Excel file.")
            return
        if Path(src).resolve() == Path(out).resolve():
            messagebox.showerror("Invalid output", "The output must be a different file from the source.")
            return
        if Path(out).exists() and not messagebox.askyesno("Replace existing file?", f"{out} already exists. Replace it?"):
            return
        def work(progress):
            result = convert_to_xlsx(src, out, progress)
            return (f"Saved Excel workbook to {out}. Extracted {result['tables']} table(s) "
                    f"and text from {result['text_pages']} page(s).")
        self._run(work)

    def _compress(self):
        src, out = self.compress_src.get().strip(), self.compress_out.get().strip()
        if not src or not out:
            messagebox.showerror("Missing path", "Choose an input PDF and output PDF.")
            return
        if Path(src).resolve() == Path(out).resolve():
            messagebox.showerror("Invalid output", "Choose a different output file so the source remains unchanged.")
            return
        if Path(out).exists() and not messagebox.askyesno("Replace existing file?", f"{out} already exists. Replace it?"):
            return
        preset = self.compress_preset.get()
        def work(progress):
            result = compress_pdf(src, out, preset=preset, progress=progress)
            saved = result["saved_bytes"]
            if saved > 0:
                detail = f"reduced by {saved / 1024:.1f} KB ({100 * saved / max(1, result['input_bytes']):.1f}%)"
            elif saved < 0:
                detail = f"increased by {-saved / 1024:.1f} KB; this source was already efficiently compressed"
            else:
                detail = "saved at the same size"
            return f"Saved compressed PDF to {out}; file size {detail}."
        self._run(work)

    def _poll(self):
        try:
            while True:
                kind, result = self.events.get_nowait()
                if kind == "progress":
                    percent, message = result
                    self.progress.configure(value=percent)
                    self.status.set(message)
                    continue
                self.cancel_button.configure(state="disabled")
                self.progress.configure(mode="determinate", value=100 if kind == "done" else 0)
                if kind == "cancelled":
                    self.status.set("Operation cancelled.")
                elif kind == "error":
                    self.status.set("Operation failed.")
                    messagebox.showerror("PDF operation failed", result)
                elif isinstance(result, dict):
                    self.status.set(f"Finished: {result['pages']} page(s), {result['tables']} table(s), {result['images']} image(s).")
                    details = "\n".join(result["warnings"]) or "No extraction warnings."
                    messagebox.showinfo("Conversion complete", f"Saved Word document.\n\n{details}")
                else:
                    self.status.set("Finished successfully.")
                    messagebox.showinfo("Complete", result)
        except queue.Empty:
            pass
        self.after(100, self._poll)


def main():
    PdfToolApp().mainloop()
