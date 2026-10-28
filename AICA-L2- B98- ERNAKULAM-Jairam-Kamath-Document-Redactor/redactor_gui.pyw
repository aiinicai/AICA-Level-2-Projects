"""
RedactIn60 - simple window: drop / browse / paste, redact, copy AI prompt, restore.
Started by the Desktop shortcut made by install.bat
"""
import os, sys, json, subprocess, threading, queue
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
import redactor_core as core

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND = True
except Exception:
    DND = False

CFG = Path.home() / ".notice_redactor.json"
# theme: Emerald Green #0FA36B, Dark Navy #0A1F3D, White
BG, CARD, BORDER = "#F2F7F5", "#FFFFFF", "#BFD9CE"
ACCENT, ACCENT_D, MUTED, INK = "#0FA36B", "#0B7F54", "#4F6378", "#0A1F3D"
OK, BAD, SOFT = "#0B7F54", "#B3261E", "#E1F0E9"
FONT = "Segoe UI"
APP_NAME = "RedactIn60"          # <- name + tagline: change here (window title + header)
TAGLINE = "Spend 60 seconds additionally to Redact, reply, restore. Confidential for good."
APP_VERSION = "v9"


def load_cfg():
    try:
        return json.loads(CFG.read_text())
    except Exception:
        return {}


def save_cfg(c):
    try:
        CFG.write_text(json.dumps(c))
    except Exception:
        pass


def open_path(p):
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except Exception:
        pass


def clipboard_files(root):
    """Files copied in Explorer (Ctrl+C) or a path copied as text."""
    try:
        t = root.clipboard_get()
    except Exception:
        t = ""
    ok = [p.strip().strip('"') for p in t.splitlines() if os.path.isfile(p.strip().strip('"'))]
    if ok:
        return ok
    if sys.platform.startswith("win"):
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Clipboard -Format FileDropList | ForEach-Object { $_.FullName }"],
                capture_output=True, text=True, timeout=10, creationflags=0x08000000).stdout
            return [p.strip() for p in out.splitlines() if os.path.isfile(p.strip())]
        except Exception:
            pass
    return []


def native_text_box(title, initial="", prompt=""):
    """Opens a plain Windows text box (dictation tools such as Wispr Flow work in it). Returns the text, or None if cancelled."""
    ps = r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$f = New-Object System.Windows.Forms.Form
$f.Text = $env:RI_TITLE
$f.Width = 760; $f.Height = 460; $f.StartPosition = 'CenterScreen'; $f.TopMost = $true
$l = New-Object System.Windows.Forms.Label
$l.Text = $env:RI_PROMPT; $l.Left = 12; $l.Top = 8; $l.Width = 720; $l.Height = 36
$t = New-Object System.Windows.Forms.TextBox
$t.Multiline = $true; $t.ScrollBars = 'Vertical'; $t.AcceptsReturn = $true
$t.Left = 12; $t.Top = 48; $t.Width = 720; $t.Height = 280; $t.Font = New-Object System.Drawing.Font('Segoe UI', 11)
$t.Text = $env:RI_TEXT
$ok = New-Object System.Windows.Forms.Button
$ok.Text = 'OK'; $ok.Left = 540; $ok.Top = 345; $ok.Width = 90; $ok.Height = 34; $ok.DialogResult = 'OK'
$c = New-Object System.Windows.Forms.Button
$c.Text = 'Cancel'; $c.Left = 640; $c.Top = 345; $c.Width = 90; $c.Height = 34; $c.DialogResult = 'Cancel'
$f.AcceptButton = $null; $f.CancelButton = $c
$f.Controls.AddRange(@($l, $t, $ok, $c))
$f.Add_Shown({ $f.Activate(); $t.Focus(); $t.SelectionStart = $t.Text.Length })
if ($f.ShowDialog() -eq 'OK') {
  $b = [System.Text.Encoding]::UTF8.GetBytes($t.Text)
  [Console]::Out.Write([Convert]::ToBase64String($b))
}
"""
    import base64
    env = dict(os.environ, RI_TITLE=title, RI_PROMPT=prompt, RI_TEXT=initial.replace("\n", "\r\n").replace("\r\r", "\r"))
    enc = base64.b64encode(ps.encode("utf-16-le")).decode()
    flags = 0x08000000 if os.name == "nt" else 0
    out = subprocess.run(["powershell", "-NoProfile", "-STA", "-EncodedCommand", enc], env=env,
                         capture_output=True, text=True, creationflags=flags).stdout.strip()
    if not out:
        return None
    import base64 as b64
    return b64.b64decode(out).decode("utf-8")


def mkbtn(master, text, cmd, primary=True, **kw):
    return tk.Button(master, text=text, command=cmd, font=(FONT, 10, "bold" if primary else "normal"),
                     bg=ACCENT if primary else SOFT, fg="white" if primary else INK,
                     activebackground=ACCENT_D if primary else BORDER,
                     activeforeground="white" if primary else INK,
                     relief="flat", padx=14, pady=6, cursor="hand2", bd=0, **kw)


class DropZone(tk.Frame):
    def __init__(self, master, text, filetypes, on_files, multiple=False, height=110):
        super().__init__(master, bg=CARD, highlightbackground=BORDER, highlightthickness=2, height=height)
        self.pack_propagate(False)
        self.text, self.filetypes, self.on_files, self.multiple = text, filetypes, on_files, multiple
        self.lbl = tk.Label(self, bg=CARD, fg=MUTED, font=(FONT, 11), justify="center", cursor="hand2", wraplength=620)
        self.lbl.pack(expand=True, fill="both", padx=8)
        self.reset()
        for w in (self, self.lbl):
            w.bind("<Button-1>", lambda e: self.browse())
            if DND:
                try:
                    w.drop_target_register(DND_FILES)
                    w.dnd_bind("<<Drop>>", self._drop)
                except Exception:
                    pass

    def reset(self):
        self.lbl.config(text=self.text, fg=MUTED)
        self.config(highlightbackground=BORDER)

    def show(self, paths):
        self.lbl.config(text="✔  " + ", ".join(Path(p).name for p in paths), fg=OK)
        self.config(highlightbackground=OK)

    def _drop(self, event):
        files = [f for f in self.tk.splitlist(event.data) if os.path.isfile(f)]
        if files:
            self.on_files(files if self.multiple else files[:1])
        return event.action

    def browse(self):
        f = (filedialog.askopenfilenames if self.multiple else filedialog.askopenfilename)(filetypes=self.filetypes)
        if f:
            self.on_files(list(f) if self.multiple else [f])


class FillDialog(tk.Toplevel):
    """Asks for each {{FILL: ...}} blank and shows where it sits in the reply (highlighted yellow)."""

    def __init__(self, parent, paragraphs, items):
        super().__init__(parent)
        self.title("Fill in the blanks")
        self.geometry("940x740")
        self.minsize(780, 580)
        self.configure(bg=BG)
        self.items, self.i, self.values, self.occ = items, 0, {}, {}
        self.protocol("WM_DELETE_WINDOW", self.finish)

        # bottom rows first, so they can never be pushed off the screen
        br = tk.Frame(self, bg=BG)
        br.pack(side="bottom", fill="x", padx=18, pady=(6, 14))
        self.back_btn = mkbtn(br, "◀ Back", self.back, primary=False)
        self.back_btn.pack(side="left")
        mkbtn(br, "Skip this one", self.skip, primary=False).pack(side="left", padx=6)
        mkbtn(br, "Done (skip the rest)", self.finish, primary=False).pack(side="right")
        mkbtn(br, "Fill  ▶   (Enter)", self.fill).pack(side="right", padx=6)
        mkbtn(br, "Dictate…", self.dictate, primary=False).pack(side="right")
        er = tk.Frame(self, bg=BG)
        er.pack(side="bottom", fill="x", padx=18, pady=(6, 0))
        tk.Label(er, text="Fill with:", bg=BG, fg=INK, font=(FONT, 11, "bold")).pack(anchor="w")
        self.entry = tk.Text(er, height=3, font=(FONT, 13), relief="solid", bd=1, wrap="word", padx=6, pady=4)
        self.entry.pack(fill="x", pady=(2, 0))
        self.entry.bind("<Return>", self._enter)
        self.entry.bind("<KP_Enter>", self._enter)

        self.hdr = tk.Label(self, bg=BG, fg=MUTED, font=(FONT, 10))
        self.hdr.pack(anchor="w", padx=18, pady=(12, 0))
        tk.Label(self, text="The AI needs:", bg=BG, fg=MUTED, font=(FONT, 10)).pack(anchor="w", padx=18)
        self.q = tk.Label(self, bg=BG, fg=INK, font=(FONT, 15, "bold"), wraplength=860, justify="left")
        self.q.pack(anchor="w", padx=18, pady=(0, 4))
        self.hint = tk.Label(self, bg=SOFT, fg=INK, font=(FONT, 11), wraplength=860, justify="left", anchor="w", padx=10, pady=8)
        self.sub = tk.Label(self, text="Yellow below = where this blank appears in the reply (orange = other blanks).",
                            bg=BG, fg=MUTED, font=(FONT, 9))
        self.sub.pack(anchor="w", padx=18)

        fr = tk.Frame(self, bg=BG)
        fr.pack(fill="both", expand=True, padx=18, pady=6)
        self.txt = tk.Text(fr, wrap="word", height=8, font=(FONT, 11), bg=CARD, relief="solid", bd=1, padx=10, pady=8)
        sb = tk.Scrollbar(fr, command=self.txt.yview)
        self.txt.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt.pack(side="left", fill="both", expand=True)
        self.txt.tag_config("ctx", background="#E4F3EC")
        self.txt.tag_config("fill", background="#FFE0B2")
        self.txt.tag_config("cur", background="#FFEB3B", font=(FONT, 11, "bold"))
        for ln, para in enumerate(paragraphs, start=1):
            para = para.replace("\n", " ")
            shown, pos = "", 0
            spans = []
            for m in core.FILL_RX.finditer(para):          # show each blank WITHOUT its hint (the hint is above)
                shown += para[pos:m.start()]
                item_txt = core._split_hint(m.group(0))[0]
                spans.append((core._norm(m.group(0)), len(shown), len(shown) + len(item_txt)))
                shown += item_txt
                pos = m.end()
            shown += para[pos:]
            self.txt.insert("end", shown + "\n")
            for key, a, b in spans:
                self.occ.setdefault(key, []).append((ln, a, b))
                self.txt.tag_add("fill", f"{ln}.{a}", f"{ln}.{b}")
        self.txt.config(state="disabled")

        self.bind("<Escape>", lambda e: self.finish())
        self.show()
        try:
            self.transient(parent)
            self.grab_set()
            self.lift()
            self.focus_force()
            self.entry.focus_set()
        except Exception:
            pass

    def _enter(self, event):
        self.fill()
        return "break"

    def dictate(self):
        try:
            v = native_text_box("Fill with", self.entry.get("1.0", "end").strip(),
                                self.items[self.i]["label"])
        except Exception as e:
            self.sub.config(fg=BAD, text=f"Could not open the dictation box: {e}")
            return
        if v is not None:
            self.entry.delete("1.0", "end")
            self.entry.insert("1.0", v.strip())
        self.entry.focus_set()

    def _value(self):
        return self.entry.get("1.0", "end").strip().replace("\n", " ")

    def show(self):
        it = self.items[self.i]
        self.hdr.config(text=f"Blank {self.i + 1} of {len(self.items)}" +
                        (f"   -   appears {it['count']} times, one answer fills all" if it["count"] > 1 else ""))
        self.q.config(text=it["label"])
        if it.get("hint"):
            self.hint.config(text="AI's guidance:  " + it["hint"])
            self.hint.pack(fill="x", padx=18, pady=(0, 6), before=self.sub)
        else:
            self.hint.pack_forget()
        self.sub.config(fg=MUTED, text="Yellow below = where this blank appears in the reply (orange = other blanks).")
        self.entry.delete("1.0", "end")
        prev = self.values.get(it["key"])
        if prev:
            self.entry.insert("1.0", prev)
        self.txt.tag_remove("cur", "1.0", "end")
        self.txt.tag_remove("ctx", "1.0", "end")
        occ = self.occ.get(it["key"], [])
        for ln, a, b in occ:
            self.txt.tag_add("ctx", f"{ln}.0", f"{ln}.end")
            self.txt.tag_add("cur", f"{ln}.{a}", f"{ln}.{b}")
        if occ:
            self.txt.see(f"{occ[0][0]}.{occ[0][1]}")
        self.back_btn.config(state="normal" if self.i > 0 else "disabled")
        self.entry.focus_set()

    def _next(self):
        self.i += 1
        if self.i >= len(self.items):
            self.finish()
        else:
            self.show()

    def fill(self):
        v = self._value()
        if not v:
            self.sub.config(fg=BAD, text="Type a value first, or click 'Skip this one'.")
            return
        self.values[self.items[self.i]["key"]] = v
        self._next()

    def skip(self):
        self.values.pop(self.items[self.i]["key"], None)
        self._next()

    def back(self):
        if self.i > 0:
            self.i -= 1
            self.show()

    def finish(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class App:
    def __init__(self):
        r = self.root = TkinterDnD.Tk() if DND else tk.Tk()
        r.title(APP_NAME)
        r.geometry("800x920")
        r.minsize(700, 760)
        r.configure(bg=BG)
        self.cfg = load_cfg()
        self.rules = self.cfg.get("rules") or str(APP_DIR / "rules.xlsx")
        self.map = self.cfg.get("map")
        self.last_dir = None
        self.last_notices = None
        self.fmt = tk.StringVar(value=self.cfg.get("fmt", "word"))
        self.auto_prompt = tk.BooleanVar(value=self.cfg.get("auto_prompt", True))
        self.out_mode = tk.StringVar(value=self.cfg.get("out_mode", "same"))
        self.out_dir = tk.StringVar(value=self.cfg.get("out_dir", ""))
        self.make_md = tk.BooleanVar(value=self.cfg.get("make_md", True))
        self.fill_on = tk.BooleanVar(value=self.cfg.get("fill_on", True))
        self.last_file = None
        self.last_restored = None

        # ---------- header
        hd = tk.Frame(r, bg=INK)
        hd.pack(fill="x")
        tk.Label(hd, text=APP_NAME, font=(FONT, 20, "bold"), bg=INK, fg="white").pack(anchor="w", padx=22, pady=(12, 0))
        tk.Label(hd, text=TAGLINE, font=(FONT, 11), bg=INK, fg="#9FE3C8", wraplength=720, justify="left").pack(anchor="w", padx=22, pady=(0, 10))
        tk.Frame(r, bg=ACCENT, height=3).pack(fill="x")

        # ---------- big two-way switch (instant: both pages exist, one is raised)
        sw = tk.Frame(r, bg=BG)
        sw.pack(fill="x", padx=22, pady=(10, 0))
        self.tab_btn = {}
        for key, label in (("redact", "①  Redact document"), ("restore", "②  Restore AI reply")):
            b = tk.Button(sw, text=label, font=(FONT, 12, "bold"), relief="flat", bd=0, pady=9, cursor="hand2",
                          command=lambda k=key: self.show_page(k))
            b.pack(side="left", expand=True, fill="x", padx=(0, 6) if key == "redact" else (0, 0))
            self.tab_btn[key] = b

        holder = tk.Frame(r, bg=BG)
        holder.pack(fill="both", expand=True, padx=22, pady=(8, 0))
        holder.grid_rowconfigure(0, weight=1)
        holder.grid_columnconfigure(0, weight=1)
        self.pages = {}
        for key in ("redact", "restore"):
            f = tk.Frame(holder, bg=BG)
            f.grid(row=0, column=0, sticky="nsew")
            self.pages[key] = f
        self.build_redact(self.pages["redact"])
        self.build_restore(self.pages["restore"])

        # ---------- output location (shared)
        ob = tk.Frame(r, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        ob.pack(fill="x", padx=22, pady=(8, 0))
        tk.Label(ob, text="Save results to:", font=(FONT, 10, "bold"), bg=CARD, fg=INK).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 0))
        rb = dict(bg=CARD, font=(FONT, 10), fg=INK, activebackground=CARD, selectcolor=CARD, command=self.save_prefs)
        tk.Radiobutton(ob, text="Same folder as the file (default)", variable=self.out_mode, value="same", **rb).grid(row=1, column=0, sticky="w", padx=10)
        tk.Radiobutton(ob, text="Ask me for name & place each time", variable=self.out_mode, value="ask", **rb).grid(row=1, column=1, sticky="w")
        tk.Radiobutton(ob, text="This folder:", variable=self.out_mode, value="folder", **rb).grid(row=2, column=0, sticky="w", padx=10, pady=(0, 6))
        fr = tk.Frame(ob, bg=CARD)
        fr.grid(row=2, column=1, sticky="we", pady=(0, 6))
        self.out_entry = tk.Entry(fr, textvariable=self.out_dir, font=(FONT, 10), width=34, relief="solid", bd=1)
        self.out_entry.pack(side="left", padx=(0, 6))
        mkbtn(fr, "Browse…", self.pick_out_dir, primary=False).pack(side="left")
        ob.grid_columnconfigure(1, weight=1)

        # ---------- progress + log
        self.bar = ttk.Progressbar(r, mode="indeterminate", length=200)
        self.log = tk.Text(r, height=8, bg=CARD, fg=INK, font=("Consolas", 9), relief="flat",
                           highlightbackground=BORDER, highlightthickness=1, wrap="word", state="disabled")
        self.log.pack(fill="x", padx=22, pady=(8, 4))
        for tag, col in (("ok", OK), ("bad", BAD), ("mut", MUTED)):
            self.log.tag_config(tag, foreground=col)
        bot = tk.Frame(r, bg=BG)
        bot.pack(fill="x", padx=22, pady=(0, 12))
        mkbtn(bot, "Open last file", lambda: open_path(self.last_file) if self.last_file else None, primary=False).pack(side="left")
        mkbtn(bot, "Open folder", lambda: open_path(self.last_dir) if self.last_dir else None, primary=False).pack(side="left", padx=6)
        self.status = tk.Label(bot, text="", bg=BG, fg=MUTED, font=(FONT, 10))
        self.status.pack(side="left", padx=12)
        tk.Label(bot, text=f"{APP_NAME} {APP_VERSION}", bg=BG, fg=MUTED, font=(FONT, 9)).pack(side="right")

        r.bind_all("<Control-v>", self.on_ctrl_v)
        self.show_page("redact")
        self.write("Ready - everything runs on this computer. Drag a file in, click a box to browse, or copy a file and press Ctrl+V." if DND
                   else "Ready - everything runs on this computer. Click a box to browse, or copy a file and press Ctrl+V.", "mut")

    # ------------------------------------------------------------ pages
    def build_redact(self, p):
        tk.Label(p, text="Document  -  notice / order / appeal  (PDF, Word, Excel or text)", bg=BG, font=(FONT, 10, "bold"), fg=INK).pack(anchor="w", pady=(4, 3))
        self.z_notice = DropZone(p, "⬇  Drop the notice / order / appeal here\nor click to browse  •  or copy the file and press Ctrl+V\nRedaction starts automatically",
                                 [("Notices", "*.pdf *.docx *.xlsx *.txt *.csv *.md")], self.do_redact, multiple=True, height=104)
        self.z_notice.pack(fill="x")
        row = tk.Frame(p, bg=BG)
        row.pack(fill="x", pady=(6, 0))
        mkbtn(row, "Browse…", self.z_notice.browse).pack(side="left")
        mkbtn(row, "Paste copied file", self.paste_files, primary=False).pack(side="left", padx=6)
        mkbtn(row, "Redact again", lambda: self.do_redact(self.last_notices) if self.last_notices else None, primary=False).pack(side="left")
        tk.Checkbutton(p, text="Also make a Markdown (.md) copy for the AI  -  faster for the AI to read than a PDF (the PDF / Word copy is still made)",
                       variable=self.make_md, bg=BG, font=(FONT, 10), fg=INK, activebackground=BG, selectcolor=CARD,
                       command=self.save_prefs, wraplength=700, justify="left").pack(anchor="w", pady=(8, 0))

        rr = tk.Frame(p, bg=BG)
        rr.pack(fill="x", pady=(10, 0))
        tk.Label(rr, text="Rules:", bg=BG, font=(FONT, 10, "bold"), fg=INK).pack(side="left")
        self.rules_lbl = tk.Label(rr, text=Path(self.rules).name, bg=BG, font=(FONT, 10), fg=OK)
        self.rules_lbl.pack(side="left", padx=6)
        mkbtn(rr, "Edit in Excel", lambda: open_path(self.rules)).pack(side="right")
        mkbtn(rr, "Change…", self.pick_rules, primary=False).pack(side="right", padx=6)
        mkbtn(rr, "Add new standard patterns", self.add_patterns, primary=False).pack(side="right")

        tk.Label(p, text="Prompt for the AI (made after redaction)", bg=BG, font=(FONT, 10, "bold"), fg=INK).pack(anchor="w", pady=(12, 2))
        fr = tk.Frame(p, bg=BG)
        fr.pack(fill="x")
        tk.Label(fr, text="Ask the AI to reply as:", bg=BG, font=(FONT, 10), fg=MUTED).pack(side="left")
        for v, t in (("word", "Word"), ("excel", "Excel"), ("text", "Plain text")):
            tk.Radiobutton(fr, text=t, variable=self.fmt, value=v, bg=BG, font=(FONT, 10), fg=INK, activebackground=BG,
                           selectcolor=CARD, command=self.save_prefs).pack(side="left", padx=6)
        tk.Label(p, text="Special instructions for this document (added at the end of the prompt):", bg=BG, font=(FONT, 10), fg=MUTED).pack(anchor="w", pady=(6, 2))
        self.special = tk.Text(p, height=4, font=(FONT, 10), relief="solid", bd=1, wrap="word")
        self.special.pack(fill="x")
        pr = tk.Frame(p, bg=BG)
        pr.pack(fill="x", pady=(6, 0))
        mkbtn(pr, "Dictate…", self.dictate_special, primary=False).pack(side="left")
        mkbtn(pr, "Copy prompt", self.copy_prompt).pack(side="left", padx=(6, 0))
        mkbtn(pr, "Edit fixed part", self.edit_fixed_prompt, primary=False).pack(side="left", padx=6)
        tk.Checkbutton(pr, text="Copy automatically after redacting", variable=self.auto_prompt, bg=BG, font=(FONT, 10), fg=INK,
                       activebackground=BG, selectcolor=CARD, command=self.save_prefs).pack(side="left", padx=6)

    def build_restore(self, p):
        tk.Label(p, text="AI reply  (Word, Excel or text file)", bg=BG, font=(FONT, 10, "bold"), fg=INK).pack(anchor="w", pady=(4, 3))
        self.z_ans = DropZone(p, "⬇  Drop the AI's reply file here\nor click to browse  •  or copy the file and press Ctrl+V\nRestoring starts automatically",
                              [("AI reply", "*.docx *.txt *.md *.xlsx *.csv")], self.do_restore, height=104)
        self.z_ans.pack(fill="x")
        row = tk.Frame(p, bg=BG)
        row.pack(fill="x", pady=(6, 0))
        mkbtn(row, "Browse…", self.z_ans.browse).pack(side="left")
        mkbtn(row, "Paste copied file", self.paste_files, primary=False).pack(side="left", padx=6)

        tk.Label(p, text="…or paste the AI's reply text here", bg=BG, font=(FONT, 10, "bold"), fg=INK).pack(anchor="w", pady=(12, 3))
        self.ans_text = tk.Text(p, height=8, font=(FONT, 10), relief="solid", bd=1, wrap="word")
        self.ans_text.pack(fill="both", expand=True)
        tr = tk.Frame(p, bg=BG)
        tr.pack(fill="x", pady=(6, 0))
        mkbtn(tr, "Restore pasted text", self.restore_pasted).pack(side="left")
        mkbtn(tr, "Clear", lambda: self.ans_text.delete("1.0", "end"), primary=False).pack(side="left", padx=6)
        tk.Label(tr, text="(restored text is saved as a Word file and also copied)", bg=BG, font=(FONT, 9), fg=MUTED).pack(side="left", padx=6)

        tk.Checkbutton(p, text="After restoring, ask me to fill the {{ }} blanks one by one (shows where each appears)",
                       variable=self.fill_on, bg=BG, font=(FONT, 10), fg=INK, activebackground=BG, selectcolor=CARD,
                       command=self.save_prefs).pack(anchor="w", pady=(8, 0))
        cr = tk.Frame(p, bg=BG)
        cr.pack(fill="x", pady=(8, 0))
        mkbtn(cr, "Clear green / yellow colours", self.clear_colours, primary=False).pack(side="left")
        tk.Label(cr, text="green = restored client details, yellow = values you filled.  One click makes a clean copy.",
                 bg=BG, font=(FONT, 9), fg=MUTED).pack(side="left", padx=8)
        mr = tk.Frame(p, bg=BG)
        mr.pack(fill="x", pady=(8, 0))
        tk.Label(mr, text="Mapping file:", bg=BG, font=(FONT, 10, "bold"), fg=INK).pack(side="left")
        self.map_lbl = tk.Label(mr, bg=BG, font=(FONT, 10), fg=OK if self.map and os.path.isfile(self.map) else BAD)
        self.map_lbl.pack(side="left", padx=6)
        self.refresh_map_lbl()
        mkbtn(mr, "Change…", self.pick_map, primary=False).pack(side="right")
        tk.Label(p, text="The latest one from step 1 is used automatically. Drop a different …_MAP.json on the box above to switch.",
                 bg=BG, font=(FONT, 9), fg=MUTED).pack(anchor="w")

    # ------------------------------------------------------------ helpers
    def show_page(self, key):
        self.pages[key].tkraise()
        for k, b in self.tab_btn.items():
            on = k == key
            b.config(bg=INK if on else SOFT, fg="white" if on else INK,
                     activebackground=INK if on else BORDER, activeforeground="white" if on else INK)
        self.cur = key

    def write(self, msg, tag=None):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def save_prefs(self):
        self.cfg.update(fmt=self.fmt.get(), auto_prompt=self.auto_prompt.get(), out_mode=self.out_mode.get(),
                        out_dir=self.out_dir.get(), rules=self.rules, map=self.map,
                        make_md=self.make_md.get(), fill_on=self.fill_on.get())
        save_cfg(self.cfg)

    def refresh_map_lbl(self):
        good = bool(self.map and os.path.isfile(self.map))
        self.map_lbl.config(text=Path(self.map).name if good else "none yet - run step 1 first", fg=OK if good else BAD)

    def busy(self, on):
        if on:
            self.bar.pack(fill="x", padx=22, pady=(6, 0), before=self.log)
            self.bar.start(12)
            self.status.config(text="Working…")
        else:
            self.bar.stop()
            self.bar.pack_forget()
            self.status.config(text="")

    def bg(self, fn, done):
        q = queue.Queue()

        def run():
            try:
                q.put(("ok", fn()))
            except Exception as e:
                q.put(("err", e))
        threading.Thread(target=run, daemon=True).start()
        self.busy(True)

        def poll():
            try:
                kind, val = q.get_nowait()
            except queue.Empty:
                self.root.after(80, poll)
                return
            self.busy(False)
            done(kind, val)
        poll()

    def pick_rules(self):
        f = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if f:
            self.rules = f
            self.rules_lbl.config(text=Path(f).name)
            self.save_prefs()

    def pick_map(self):
        f = filedialog.askopenfilename(filetypes=[("Mapping file", "*.json")])
        if f:
            self.set_map(f)

    def set_map(self, f):
        self.map = f
        self.refresh_map_lbl()
        self.save_prefs()

    def pick_out_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir.set(d)
            self.out_mode.set("folder")
            self.save_prefs()

    def resolve_out(self, src, suffix):
        """-> (outdir, out_path) ; None if the user cancelled."""
        p = Path(src)
        mode = self.out_mode.get()
        if mode == "folder" and self.out_dir.get() and os.path.isdir(self.out_dir.get()):
            return self.out_dir.get(), None
        if mode == "ask":
            f = filedialog.asksaveasfilename(initialdir=str(p.parent), initialfile=f"{p.stem}_{suffix}{p.suffix}",
                                             defaultextension=p.suffix, filetypes=[(p.suffix[1:].upper() + " file", "*" + p.suffix)])
            return (str(Path(f).parent), f) if f else None
        return str(p.parent), None

    # ------------------------------------------------------------ clipboard / paste
    def on_ctrl_v(self, event):
        try:
            if isinstance(self.root.focus_get(), (tk.Text, tk.Entry)):
                return None                   # normal text paste
        except Exception:
            pass
        self.paste_files()
        return "break"

    def paste_files(self):
        files = clipboard_files(self.root)
        if not files:
            self.write("Nothing to paste. Copy a file in File Explorer first (right-click → Copy), then press Ctrl+V.", "bad")
            return
        if self.cur == "redact":
            self.do_redact(files)
        else:
            self.do_restore(files[:1])

    # ------------------------------------------------------------ prompt
    def dictate_special(self):
        """Plain Windows text box: dictation (Wispr Flow) types into it reliably; the text then comes back here."""
        cur = self.special.get("1.0", "end").strip()
        self.write("Dictation box opened - speak or type, then click OK.", "mut")

        def work():
            return native_text_box("Special instructions", cur, "Special instructions for this document - dictate or type, then click OK.")

        def done(kind, val):
            if kind == "err" or (val is None and kind != "ok"):
                self.write(f"✘ Could not open the dictation box: {val}", "bad")
                return
            if val is not None:
                self.special.delete("1.0", "end")
                self.special.insert("1.0", val)
                self.write("✔ Special instructions updated.", "ok")
        self.bg(work, done)

    def add_patterns(self):
        if not os.path.isfile(self.rules):
            self.write("Rules file not found.", "bad")
            return
        try:
            added = core.add_missing_patterns(self.rules)
        except PermissionError:
            self.write("✘ Close rules.xlsx in Excel first, then click again.", "bad")
            return
        except Exception as e:
            self.write(f"✘ {e}", "bad")
            return
        if added:
            self.write(f"✔ Added to the Patterns sheet: {', '.join(added)}  (a backup of your rules file was saved beside it).", "ok")
        else:
            self.write("Your Patterns sheet already has all the standard patterns.", "mut")

    def make_prompt(self):
        try:
            rl = core.load_rules(self.rules)
            op, cl = rl.open, rl.close
        except Exception:
            op, cl = "[[", "]]"
        return core.build_prompt(APP_DIR, self.fmt.get(), op, cl, self.special.get("1.0", "end"))

    def copy_prompt(self, quiet=False):
        txt = self.make_prompt()
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        self.root.update()
        if not quiet:
            self.write("✔ Prompt copied. Paste it in the AI chat (Ctrl+V), then attach the redacted .md file (and the redacted PDF for your reference).", "ok")

    def edit_fixed_prompt(self):
        p = core.ensure_prompt_file(APP_DIR)
        open_path(p)
        self.write("Opened prompt_fixed.txt - edit, save, close. Keep the @@…@@ words and the #PROMPT_VERSION line as they are.", "mut")

    # ------------------------------------------------------------ actions
    def do_redact(self, files):
        files = [f for f in files if Path(f).suffix.lower() != ".json"]
        if not files:
            return
        self.last_notices = files
        self.z_notice.show(files)
        if not os.path.isfile(self.rules):
            self.write("Rules file not found. Use 'Change…' to pick your rules.xlsx.", "bad")
            return
        jobs = []
        for f in files:
            r = self.resolve_out(f, "REDACTED")
            if r is not None:
                jobs.append((f, r[0], r[1]))
        if not jobs:
            return
        rules = self.rules
        md = self.make_md.get()

        def work():
            res = []
            for f, d, o in jobs:
                try:
                    res.append((f, core.redact_file(f, rules, d, o, md), None))
                except Exception as e:
                    res.append((f, None, e))
            return res

        def done(kind, val):
            if kind == "err":
                self.write(f"✘ {val}", "bad")
                return
            for f, r, e in val:
                self.write(f"— {Path(f).name}", "mut")
                if e:
                    self.write(f"✘ {e}", "bad")
                    continue
                for o, d in r["pairs"]:
                    self.write(f"   {o}  →  {d}")
                for w in r["warnings"]:
                    self.write(f"⚠ {w}", "bad")
                if r["out"]:
                    if r.get("replaced") or r.get("removed"):
                        self.write("✔ Replaced the earlier redacted version - only the latest is kept.", "ok")
                    self.write(f"✔ Saved (same format): {r['out']}", "ok")
                    if r.get("md"):
                        self.write(f"✔ Saved Markdown for the AI: {r['md']}   <- upload THIS one (faster)", "ok")
                    self.last_dir = str(Path(r["out"]).parent)
                    self.last_file = r.get("md") or r["out"]
                self.set_map(r["map"])
            self.write("Redacted items are coloured in the PDF / Word / Excel copy - read only the UNCOLOURED text for anything missed. Upload the .md + the redacted PDF/Word only; keep _MAP.json private.", "mut")
            if self.auto_prompt.get():
                self.copy_prompt(quiet=True)
                self.write("✔ Prompt copied to clipboard - paste it into the AI chat, then attach the redacted .md file (and the redacted PDF for your reference).", "ok")
        self.bg(work, done)

    def do_restore(self, files):
        f = files[0]
        if Path(f).suffix.lower() == ".json":
            self.set_map(f)
            self.write(f"Mapping file set: {Path(f).name}", "ok")
            return
        self.z_ans.show([f])
        if not (self.map and os.path.isfile(self.map)):
            self.write("No mapping file yet. Run step 1 first, or use 'Change…' to pick the …_MAP.json.", "bad")
            return
        r = self.resolve_out(f, "RESTORED")
        if r is None:
            return
        mp = self.map

        def work():
            return core.restore_file(f, mp, r[0], r[1])

        def done(kind, val):
            if kind == "err":
                self.write(f"✘ {val}", "bad")
                return
            for w in val["warnings"]:
                self.write(f"⚠ {w}", "bad")
            self.write(f"✔ Saved: {val['out']}  ({val['count']} items restored)", "ok")
            self.last_dir = str(Path(val["out"]).parent)
            self.last_file = val["out"]
            self.last_restored = val["out"]
            if val.get("notes"):
                self.write(f"✔ 'Notes for me' saved as a separate file: {val['notes']}", "ok")
            if self.fill_on.get():
                self.fill_flow(val["out"])
            self.write("Green = restored client details, yellow = values you filled. 'Clear green / yellow colours' gives a clean copy.", "mut")
        self.bg(work, done)

    def restore_pasted(self):
        text = self.ans_text.get("1.0", "end").rstrip()
        if not text:
            self.write("Paste the AI's reply text in the box first.", "bad")
            return
        if not (self.map and os.path.isfile(self.map)):
            self.write("No mapping file yet. Run step 1 first, or use 'Change…' to pick the …_MAP.json.", "bad")
            return
        base = Path(self.map).parent
        out = None
        if self.out_mode.get() == "ask":
            f = filedialog.asksaveasfilename(initialdir=str(base), initialfile="AI_reply_RESTORED.docx",
                                             defaultextension=".docx", filetypes=[("Word", "*.docx")])
            if not f:
                return
            out = Path(f)
        else:
            d = Path(self.out_dir.get()) if self.out_mode.get() == "folder" and os.path.isdir(self.out_dir.get()) else base
            out = d / "AI_reply_RESTORED.docx"
            n = 2
            while out.exists():
                out = d / f"AI_reply_RESTORED_{n}.docx"
                n += 1
        mp = self.map

        def work():
            return core.restore_text(text, mp, True)

        def done(kind, val):
            if kind == "err":
                self.write(f"✘ {val}", "bad")
                return
            t, w = val
            for x in w:
                self.write(f"⚠ {x}", "bad")
            t, notes_txt = core.split_notes_text(t)
            if self.fill_on.get():
                paras = core.strip_marks(t).split("\n")
                items = core.find_fill_items(paras)
                if items:
                    self.write(f"{len(items)} blank(s) to fill - a window will ask you one by one.", "mut")
                    vals = {k: v for k, v in self.ask_fills(paras, items).items() if v.strip()}
                    if vals:
                        t = core.fill_text(t, vals, True)
            try:
                core.save_text_as_docx(t, out)
                if notes_txt:
                    npath = out.with_name(out.stem + "_NOTES.docx")
                    core.save_text_as_docx(notes_txt, npath)
                    self.write(f"✔ 'Notes for me' saved as a separate file: {npath}", "ok")
            except Exception as e:
                self.write(f"✘ {e}", "bad")
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(core.strip_marks(t))
            self.root.update()
            self.write(f"✔ Saved: {out}  (restored text also copied to clipboard)", "ok")
            self.last_restored = str(out)
            self.last_dir = str(out.parent)
            self.last_file = str(out)
        self.bg(work, done)

    def clear_colours(self):
        f = self.last_restored if self.last_restored and os.path.isfile(self.last_restored) else None
        if not f:
            f = filedialog.askopenfilename(filetypes=[("Word / Excel", "*.docx *.xlsx")])
            if not f:
                return
        r = self.resolve_out(f, "CLEAN")
        if r is None:
            return
        p = Path(f)
        out = r[1] or str(Path(r[0]) / f"{p.stem}_CLEAN{p.suffix}")

        def work():
            return core.clear_colours(f, out)

        def done(kind, val):
            if kind == "err":
                self.write(f"✘ {val}", "bad")
                return
            self.write(f"✔ Clean copy (no colours): {val}", "ok")
            self.last_dir = str(Path(val).parent)
            self.last_file = val
        self.bg(work, done)

    # ------------------------------------------------------------ fill-in blanks
    def ask_fills(self, paras, items):
        dlg = FillDialog(self.root, paras, items)
        self.root.wait_window(dlg)
        return dlg.values

    def fill_flow(self, path):
        try:
            paras = core.doc_paragraphs(path)
            items = core.find_fill_items(paras)
        except Exception as e:
            self.write(f"⚠ Could not look for blanks: {e}", "bad")
            return
        if not items:
            self.write("No {{ }} blanks found in the reply.", "mut")
            return
        self.write(f"{len(items)} blank(s) to fill - a window will ask you one by one.", "mut")
        vals = {k: v for k, v in self.ask_fills(paras, items).items() if v.strip()}
        n = 0
        if vals:
            try:
                n = core.apply_fills(path, vals)
            except Exception as e:
                self.write(f"✘ Could not fill: {e}", "bad")
                return
        left_items = [i for i in items if i["key"] not in vals]
        c = 0
        try:
            c = core.hints_to_comments(path, left_items)
        except Exception as e:
            self.write(f"⚠ Could not add guidance comments: {e}", "bad")
        if n:
            self.write(f"✔ Filled {n} blank(s) in the file.", "ok")
        if left_items:
            self.write(f"{sum(i['count'] for i in left_items)} blank(s) left as {{ }} (yellow)." +
                       (f" The AI's how-to-fill guidance is in comments beside them (Word: Review > Show Comments / All Markup)." if c else ""), "mut")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
