"""Minimal stand-in for tkinter so the application's UI logic can be executed on a machine without Tk
(layout is not rendered; trees, variables, combo boxes, notebooks and dialogs behave like the real thing)."""
import sys
import types

_NOOP = {"pack", "grid", "place", "configure", "config", "bind", "title", "geometry", "minsize", "update_idletasks",
         "mainloop", "destroy", "transient", "grab_set", "wait_window", "columnconfigure", "rowconfigure", "focus_set",
         "heading", "column", "tag_configure", "yview", "xview", "drop_target_register", "dnd_bind", "pack_forget",
         "lift", "set", "state", "protocol", "resizable", "see", "focus", "theme_use", "start", "stop", "insert_text"}


class W:
    def __init__(self, *a, **k):
        self._opts = dict(k)

    def after(self, ms, fn=None, *a):
        if fn:
            fn(*a)

    def __getattr__(self, name):
        if name in _NOOP:
            return lambda *a, **k: None
        raise AttributeError(name)

    def __setitem__(self, k, v):
        self._opts[k] = v

    def __getitem__(self, k):
        return self._opts.get(k)


class Var:
    def __init__(self, master=None, value=None, **k):
        self._v = value
        self._tr = []

    def get(self):
        return self._v

    def set(self, v):
        self._v = v
        for f in self._tr:
            f()

    def trace_add(self, mode, fn):
        self._tr.append(lambda: fn())


class StringVar(Var):
    def __init__(self, master=None, value="", **k):
        super().__init__(master, value)


class BooleanVar(Var):
    def __init__(self, master=None, value=False, **k):
        super().__init__(master, value)


class Treeview(W):
    def __init__(self, master=None, columns=(), **k):
        super().__init__(**k)
        self.cols = list(columns)
        self.items = {}
        self.order = []
        self.sel = []
        self._n = 0

    def configure(self, **kw):
        if "columns" in kw:
            self.cols = list(kw["columns"])

    config = configure

    def insert(self, parent, index, iid=None, values=(), tags=(), **k):
        iid = iid or f"I{self._n}"
        self._n += 1
        self.items[iid] = {"values": list(values), "tags": tuple(tags)}
        self.order.append(iid)
        return iid

    def delete(self, *ids):
        for i in ids:
            self.items.pop(i, None)
            if i in self.order:
                self.order.remove(i)

    def get_children(self, item=""):
        return list(self.order)

    def selection(self):
        return tuple(self.sel)

    def selection_set(self, ids):
        self.sel = [ids] if isinstance(ids, str) else list(ids)

    def set(self, iid, col=None):
        return self.items[iid]["values"][self.cols.index(col)]

    def index(self, iid):
        return self.order.index(iid)

    def move(self, iid, parent, n):
        self.order.remove(iid)
        self.order.insert(n, iid)

    def rows(self):
        return [self.items[i]["values"] for i in self.order]


class Combobox(W):
    def __init__(self, master=None, textvariable=None, values=(), **k):
        super().__init__(**k)
        self.var = textvariable or StringVar()
        self._opts["values"] = list(values)
        self._idx = -1

    def get(self):
        return self.var.get()

    def set(self, v):
        self.var.set(v)

    def current(self, i=None):
        vals = list(self._opts.get("values") or [])
        if i is None:
            v = self.var.get()
            return vals.index(v) if v in vals else self._idx
        self._idx = i
        if 0 <= i < len(vals):
            self.var.set(vals[i])


class Notebook(W):
    def __init__(self, *a, **k):
        super().__init__(**k)
        self._tabs, self._sel = [], 0

    def add(self, frame, text=""):
        self._tabs.append(text)

    def tabs(self):
        return [f"t{i}" for i in range(len(self._tabs))]

    def tab(self, tid, opt=None):
        return self._tabs[int(str(tid).lstrip("t"))]

    def select(self, arg=None):
        if arg is None:
            return f"t{self._sel}"
        self._sel = int(str(arg).lstrip("t"))


class Text(W):
    def __init__(self, *a, **k):
        super().__init__(**k)
        self.buf = ""

    def insert(self, idx, txt, *a):
        self.buf += txt

    def delete(self, a, b=None):
        self.buf = ""

    def get(self, a, b=None):
        return self.buf


class Toplevel(W):
    pass


class Tk(W):
    pass


class Style(W):
    pass


def install():
    tk = types.ModuleType("tkinter")
    ttk = types.ModuleType("tkinter.ttk")
    fd = types.ModuleType("tkinter.filedialog")
    mb = types.ModuleType("tkinter.messagebox")
    tk.Tk, tk.Toplevel, tk.StringVar, tk.BooleanVar, tk.Text = Tk, Toplevel, StringVar, BooleanVar, Text
    for n in ("Frame", "Label", "Button", "Entry", "Checkbutton", "Scrollbar", "Progressbar", "Separator", "LabelFrame",
              "Spinbox"):
        setattr(ttk, n, type(n, (W,), {}))
    ttk.Treeview, ttk.Combobox, ttk.Notebook, ttk.Style = Treeview, Combobox, Notebook, Style
    mb.calls = []
    for n in ("showinfo", "showwarning", "showerror"):
        setattr(mb, n, (lambda name: lambda *a, **k: mb.calls.append((name, a[1] if len(a) > 1 else "")))(n))
    mb.askyesno = lambda *a, **k: False
    mb.askyesnocancel = lambda *a, **k: True
    fd.asksaveasfilename = fd.askopenfilename = fd.askdirectory = lambda **k: ""
    fd.askopenfilenames = lambda **k: ()
    tk.ttk, tk.filedialog, tk.messagebox = ttk, fd, mb
    sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk, "tkinter.filedialog": fd, "tkinter.messagebox": mb})
    return tk
