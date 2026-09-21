"""Layout helpers that keep every control reachable on any screen size / Windows scaling.

The earlier tool used a fixed 760x650 window with no scrolling, so at 125-150% Windows
display scaling the lower sections and the Analyse/Generate buttons were pushed off
screen. Here: the body scrolls (mouse wheel + scrollbar) and action buttons live in a
footer that is packed first, so it is always visible."""
import sys
import tkinter as tk
from tkinter import ttk


def enable_windows_dpi_awareness():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def fit_to_screen(win, pref_w=1150, pref_h=860, margin_w=60, margin_h=110):
    """Size a window to the preferred size or the available screen, whichever is smaller, and centre it."""
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w, h = min(pref_w, sw - margin_w), min(pref_h, sh - margin_h)
    x, y = max((sw - w) // 2, 0), max((sh - h) // 2 - 20, 0)
    win.geometry(f"{w}x{h}+{x}+{y}")
    win.minsize(min(640, w), min(420, h))


class ScrollFrame(ttk.Frame):
    """A vertically scrolling container. Put widgets inside `self.body`."""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = ttk.Frame(self.canvas, padding=(14, 8, 14, 14))
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.canvas.bind("<Leave>", lambda e: self._bind_wheel(False))

    def _bind_wheel(self, on):
        top = self.winfo_toplevel()
        if on:
            top.bind_all("<MouseWheel>", self._wheel)
            top.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
            top.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        else:
            top.unbind_all("<MouseWheel>"); top.unbind_all("<Button-4>"); top.unbind_all("<Button-5>")

    def _wheel(self, e):
        # Let comboboxes / listboxes / treeviews scroll themselves
        cls = e.widget.winfo_class() if hasattr(e.widget, "winfo_class") else ""
        if cls in ("TCombobox", "Listbox", "Treeview", "Text"):
            return
        self.canvas.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")


def open_path(path):
    import os, subprocess
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass
