"""Reusable widgets: a read-only rich-text Markdown viewer and a card frame."""

from __future__ import annotations

import re
import tkinter as tk

import customtkinter as ctk

from ..exporter import parse_blocks, split_inline
from . import theme

_LABEL_RE = re.compile(r"(\[Court Findings?\]|\[AI Observations?\]|\[AI Generated\]|\[Uncertain\][^.\n]*|"
                       r"Not stated in the judgment)")


def bring_to_front(win, focus_widget=None, delay: int = 150) -> None:
    """Show a new window in front of the main window and put the cursor in it. On Windows a window
    opened from a button click can stay behind the main window; briefly making it 'topmost' fixes that."""
    def _raise():
        try:
            if not win.winfo_exists():
                return
            win.deiconify()
            win.lift()
            win.attributes("-topmost", True)
            win.focus_force()
            if focus_widget is not None:
                focus_widget.focus_set()
            win.after(400, lambda: win.winfo_exists() and win.attributes("-topmost", False))
        except Exception:  # noqa: BLE001 - cosmetic only
            pass
    win.after(delay, _raise)


class Card(ctk.CTkFrame):
    """A rounded white panel with a numbered title."""

    def __init__(self, master, title: str, **kwargs):
        super().__init__(master, fg_color=theme.CARD, corner_radius=14, border_width=1,
                         border_color=theme.CARD_BORDER, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        ctk.CTkFrame(header, width=5, height=20, fg_color=theme.GOLD, corner_radius=3).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(theme.FONT_FAMILY, 15, "bold"),
                     text_color=(theme.NAVY, theme.GOLD)).pack(side="left")
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        self.body.grid_columnconfigure(0, weight=1)


class MarkdownView(ctk.CTkFrame):
    """Scrollable, styled view of a Markdown string.

    Normally read-only (formatted). ``start_editing()`` switches to the raw Markdown text so the
    user can correct it; ``finish_editing()`` returns the edited text.
    """

    def __init__(self, master, font_family: str | None = None, font_size: int = 12, **kwargs):
        super().__init__(master, fg_color=theme.CARD, corner_radius=10, **kwargs)
        self.font_family = font_family or theme.FONT_FAMILY
        self.font_size = font_size
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.text = tk.Text(self, wrap="word", relief="flat", borderwidth=0, highlightthickness=0,
                            padx=18, pady=14, cursor="arrow", undo=False)
        self.text.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        scroll = ctk.CTkScrollbar(self, command=self.text.yview)
        scroll.grid(row=0, column=1, sticky="ns", pady=6)
        self.text.configure(yscrollcommand=scroll.set)
        # Allow selection + Ctrl+C but block edits.
        self.text.bind("<Key>", self._block_edit)
        for seq in ("<<Paste>>", "<<Cut>>", "<<Clear>>", "<<PasteSelection>>"):
            self.text.bind(seq, lambda e: None if self.editing else "break")
        self.editing = False
        self._markdown = ""
        self.apply_theme()
        self.set_placeholder("Results will appear here after analysis.")

    def _block_edit(self, event):
        if self.editing:
            return None
        if (event.state & 0x4 or event.state & 0x8) and event.keysym.lower() in ("c", "a"):
            return None
        if event.keysym in ("Up", "Down", "Left", "Right", "Prior", "Next", "Home", "End"):
            return None
        return "break"

    def apply_theme(self, font_family: str | None = None, font_size: int | None = None) -> None:
        """Apply colours for the current light/dark mode and the chosen font."""
        if font_family:
            self.font_family = font_family
        if font_size:
            self.font_size = font_size
        mode = "Dark" if ctk.get_appearance_mode() == "Dark" else "Light"
        c = theme.TEXTVIEW[mode]
        f, n = self.font_family, self.font_size
        t = self.text
        t.configure(bg=c["bg"], fg=c["fg"], insertbackground=c["fg"], selectbackground=c["select"],
                    font=(f, n), spacing1=2, spacing3=3)
        t.tag_configure("h1", font=(f, n + 5, "bold"), foreground=c["h1"], spacing1=16, spacing3=6)
        t.tag_configure("h2", font=(f, n + 3, "bold"), foreground=c["h2"], spacing1=14, spacing3=4)
        t.tag_configure("h3", font=(f, n + 1, "bold"), foreground=c["h3"], spacing1=8, spacing3=2)
        t.tag_configure("bold", font=(f, n, "bold"))
        t.tag_configure("italic", font=(f, n, "italic"))
        t.tag_configure("bolditalic", font=(f, n, "bold italic"))
        indent = max(14, n + 2)
        t.tag_configure("list0", lmargin1=indent, lmargin2=indent + n + 6)
        t.tag_configure("list1", lmargin1=indent * 2 + 8, lmargin2=indent * 2 + n + 14)
        t.tag_configure("list2", lmargin1=indent * 3 + 16, lmargin2=indent * 3 + n + 22)
        t.tag_configure("quote", lmargin1=24, lmargin2=24, foreground=c["quote"], font=(f, n, "italic"))
        t.tag_configure("court", foreground=c["court"], font=(f, n - 1, "bold"))
        t.tag_configure("ai", foreground=c["ai"], font=(f, n - 1, "bold"))
        t.tag_configure("uncertain", foreground=c["uncertain"])
        t.tag_configure("placeholder", foreground=c["muted"], font=(f, n + 1, "italic"), justify="center",
                        spacing1=60)

    def set_placeholder(self, message: str) -> None:
        self._markdown = ""
        self.text.delete("1.0", "end")
        self.text.insert("end", message, ("placeholder",))

    def set_markdown(self, markdown: str) -> None:
        self._markdown = markdown
        t = self.text
        t.delete("1.0", "end")
        for b in parse_blocks(markdown):
            if b.kind == "heading":
                tag = "h1" if b.level <= 1 else "h2" if b.level == 2 else "h3"
                self._insert_inline(b.text, (tag,), heading=True)
                t.insert("end", "\n")
            elif b.kind == "bullet":
                lvl = f"list{min(b.level, 2)}"
                t.insert("end", "•  ", (lvl,))
                self._insert_inline(b.text, (lvl,))
                t.insert("end", "\n")
            elif b.kind == "numbered":
                lvl = f"list{min(b.level, 2)}"
                t.insert("end", f"{b.number}.  ", (lvl,))
                self._insert_inline(b.text, (lvl,))
                t.insert("end", "\n")
            elif b.kind == "quote":
                self._insert_inline(b.text, ("quote",))
                t.insert("end", "\n")
            elif b.kind == "paragraph":
                self._insert_inline(b.text, ())
                t.insert("end", "\n")
            elif b.kind == "blank":
                t.insert("end", "\n")
        t.yview_moveto(0)

    def _insert_inline(self, text: str, base: tuple, heading: bool = False) -> None:
        for content, bold, italic in split_inline(text):
            style = ()
            if not heading:
                style = ("bolditalic",) if bold and italic else ("bold",) if bold else ("italic",) if italic else ()
            for piece in _LABEL_RE.split(content):
                if not piece:
                    continue
                extra = ()
                if piece.startswith("[Court Finding"):
                    extra = ("court",)
                elif piece.startswith("[AI "):
                    extra = ("ai",)
                elif piece.startswith("[Uncertain]") or piece == "Not stated in the judgment":
                    extra = ("uncertain",)
                self.text.insert("end", piece, base + style + extra)

    def start_editing(self) -> None:
        """Show the raw Markdown (## headings, - bullets, **bold**) for editing."""
        self.editing = True
        t = self.text
        t.delete("1.0", "end")
        t.insert("1.0", self._markdown)
        t.configure(cursor="xterm", undo=True, insertwidth=2)
        t.edit_reset()
        t.mark_set("insert", "1.0")
        t.focus_set()

    def editing_text(self) -> str:
        return self.text.get("1.0", "end-1c")

    def stop_editing(self, markdown: str | None = None) -> None:
        """Leave edit mode and show ``markdown`` (or the original) formatted again."""
        self.editing = False
        self.text.configure(cursor="arrow", undo=False)
        self.set_markdown(self._markdown if markdown is None else markdown)

    @property
    def markdown(self) -> str:
        return self._markdown


class ScrollFrame2D(ctk.CTkFrame):
    """A frame whose content scrolls vertically and horizontally when the
    window is smaller than the content, and stretches to fill it when larger.

    Put child widgets in ``self.inner``. Mouse wheel scrolls vertically,
    Shift + wheel horizontally; text boxes and nested scroll areas keep their
    own wheel scrolling.
    """

    def __init__(self, master, min_width: int = 1200, min_height: int = 820, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._min_w, self._min_h = min_width, min_height
        bg = theme.BG[1] if ctk.get_appearance_mode() == "Dark" else theme.BG[0]
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, bg=bg)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview)
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar = ctk.CTkScrollbar(self, orientation="horizontal", command=self.canvas.xview)
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)
        self.inner = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._resize)
        self.inner.bind("<Configure>", self._resize)
        # CTk widgets forbid bind_all, so register the global wheel handlers on the plain Tk canvas.
        self.canvas.bind_all("<MouseWheel>", self._wheel, add="+")
        self.canvas.bind_all("<Shift-MouseWheel>", self._wheel_x, add="+")
        self.canvas.bind_all("<Button-4>", self._wheel, add="+")  # Linux
        self.canvas.bind_all("<Button-5>", self._wheel, add="+")

    def _scaled(self, value: int) -> int:
        try:
            from customtkinter import ScalingTracker
            return int(value * ScalingTracker.get_widget_scaling(self))
        except Exception:
            return value

    def _resize(self, _event=None):
        dark = ctk.get_appearance_mode() == "Dark"
        self.canvas.configure(bg=theme.BG[1] if dark else theme.BG[0])
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        w = max(cw, self._scaled(self._min_w))
        h = max(ch, self._scaled(self._min_h), self.inner.winfo_reqheight())
        self.canvas.itemconfigure(self._win, width=w, height=h)
        self.canvas.configure(scrollregion=(0, 0, w, h))
        if not getattr(self, "_bars_pending", False):
            self._bars_pending = True
            self.after_idle(self._update_bars)

    def _update_bars(self):
        """Show a scrollbar only when there is something to scroll (checked after layout settles)."""
        self._bars_pending = False
        for bar, view in ((self.hbar, self.canvas.xview()), (self.vbar, self.canvas.yview())):
            needed = view[0] > 0.0 or view[1] < 0.999
            shown = bool(bar.grid_info())
            if needed and not shown:
                bar.grid()
            elif not needed and shown:
                bar.grid_remove()

    def _owns(self, widget) -> bool:
        """True if the pointer is over this frame and not over a widget with its own scrolling."""
        try:
            path = str(widget)
        except Exception:
            return False
        if not path.startswith(str(self)):
            return False
        w = widget
        while w is not None and w is not self:
            if isinstance(w, (tk.Text, ctk.CTkTextbox, ctk.CTkScrollableFrame)):
                return False
            w = getattr(w, "master", None)
        return True

    def _wheel(self, event):
        if not self._owns(event.widget):
            return
        if getattr(event, "num", None) in (4, 5):
            step = -1 if event.num == 4 else 1
        else:
            step = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(step * 3, "units")

    def _wheel_x(self, event):
        if self._owns(event.widget):
            self.canvas.xview_scroll(-1 if event.delta > 0 else 1, "units")


class MarkupEditor(ctk.CTkTextbox):
    """Editable text box for email content that LOOKS formatted while keeping simple markup underneath:

    * '## Heading' lines show as bold headings (the '## ' is hidden),
    * '**bold**' shows as bold (the asterisks are hidden),
    * [Court Finding] in green bold, [AI Observation] / [AI Generated] in red bold, [Uncertain] in amber bold.

    The labels stay visible here so the reviewer can tell court findings from AI commentary; they are removed
    automatically from everything that is sent or saved.
    """

    _HEADING = re.compile(r"^(#{1,6}\s+)(.+)$", re.M)
    _BOLD = re.compile(r"(\*\*)(.+?)(\*\*)")
    _TAGS = (("court", re.compile(r"\[Court Findings?\]", re.I)),
             ("ai", re.compile(r"\[AI (?:Observations?|Generated)\]", re.I)),
             ("uncertain", re.compile(r"\[Uncertain\]", re.I)))

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._pending = None
        t = self._textbox
        family = theme.FONT_FAMILY
        t.tag_configure("hidden", elide=True)
        # Negative sizes are pixels, matching CTkFont, so tagged text has the same size as the rest.
        t.tag_configure("heading", font=(family, -15, "bold"), foreground="#0B1F3A", spacing1=8, spacing3=2)
        t.tag_configure("bold", font=(family, -13, "bold"))
        t.tag_configure("court", font=(family, -13, "bold"), foreground="#1E7B3A")
        t.tag_configure("ai", font=(family, -13, "bold"), foreground="#C62828")
        t.tag_configure("uncertain", font=(family, -13, "bold"), foreground="#B26A00")
        t.bind("<KeyRelease>", lambda e: self._schedule(), add="+")
        t.bind("<<Paste>>", lambda e: self.after(10, self._schedule), add="+")

    def _schedule(self):
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(250, self.highlight)

    def set_text(self, text: str) -> None:
        self.delete("1.0", "end")
        self.insert("1.0", text)
        self.highlight()

    def highlight(self) -> None:
        self._pending = None
        t = self._textbox
        text = t.get("1.0", "end-1c")
        for tag in ("hidden", "heading", "bold", "court", "ai", "uncertain"):
            t.tag_remove(tag, "1.0", "end")

        def span(a, b, tag):
            t.tag_add(tag, f"1.0+{a}c", f"1.0+{b}c")

        for m in self._HEADING.finditer(text):
            span(m.start(1), m.end(1), "hidden")
            span(m.start(2), m.end(2), "heading")
        for m in self._BOLD.finditer(text):
            span(m.start(1), m.end(1), "hidden")
            span(m.start(2), m.end(2), "bold")
            span(m.start(3), m.end(3), "hidden")
        for tag, rx in self._TAGS:
            for m in rx.finditer(text):
                span(m.start(), m.end(), tag)
