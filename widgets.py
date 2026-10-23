import math
import random
import time
import tkinter as tk
from tkinter import ttk

from .config import IMAGES
from .engine import beep, speak

CW, CH = 500, 210  # animation canvas size


class GuidedBreak(tk.Toplevel):
    """Interactive, step-by-step break with rich vector animations, confetti, and mood check-in."""

    def __init__(self, app, ch, act, line, manual=False):
        super().__init__(app.root)
        self.app, self.ch, self.act, self.manual = app, ch, act, manual
        t = self.t = app.t
        self.steps = act["steps"]
        self.total = sum(s["sec"] for s in self.steps) or 1
        self.i, self.step_t, self.done_t = 0, 0.0, 0.0
        self.paused = self.finished = False
        self.alive = True
        self.last = time.monotonic()
        self.confetti = []

        self.title("BreakBuddy Pro — Guided Break")
        self.configure(bg=t["pop"])
        self.attributes("-topmost", True)
        self.geometry("560x700")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Center on screen
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"560x700+{(sw - 560) // 2}+{(sh - 700) // 2}")

        # --- Top Accent Banner
        banner = tk.Frame(self, bg=t["accent"], height=6)
        banner.pack(fill="x")

        # --- Character Header Card
        hdr = tk.Frame(self, bg=t["card_alt"], padx=16, pady=12)
        hdr.pack(fill="x", padx=18, pady=(14, 8))

        shown = False
        if ch.get("image"):
            try:
                self._img = tk.PhotoImage(file=str(IMAGES / ch["image"]))
                tk.Label(hdr, image=self._img, bg=t["card_alt"]).pack(side="left", padx=(0, 12))
                shown = True
            except Exception:
                pass
        if not shown:
            tk.Label(hdr, text=ch.get("avatar", "🙂"), font=("Segoe UI Emoji", 38), bg=t["card_alt"], fg=t["fg"]).pack(side="left", padx=(0, 12))

        txt_box = tk.Frame(hdr, bg=t["card_alt"])
        txt_box.pack(side="left", fill="both", expand=True)
        tk.Label(txt_box, text=ch["name"], font=("Segoe UI", 12, "bold"), bg=t["card_alt"], fg=t["accent"], anchor="w").pack(fill="x")
        self.quote = tk.Label(txt_box, text=f"“{line}”", wraplength=390, justify="left", font=("Segoe UI", 10, "italic"),
                              bg=t["card_alt"], fg=t["fg"], anchor="w")
        self.quote.pack(fill="x", pady=(2, 0))

        # --- Activity Title & Why
        tk.Label(self, text=act["name"], font=("Segoe UI", 16, "bold"), bg=t["pop"], fg=t["fg"]).pack(pady=(4, 0))
        if act.get("why"):
            tk.Label(self, text=act["why"], font=("Segoe UI", 9), bg=t["pop"], fg=t["sub"], wraplength=500).pack(pady=(0, 6))

        # --- Step Pill Indicators
        self.pill_canvas = tk.Canvas(self, width=480, height=18, bg=t["pop"], highlightthickness=0)
        self.pill_canvas.pack(pady=(2, 4))

        self.step_lbl = tk.Label(self, text="", wraplength=500, font=("Segoe UI", 12, "bold"),
                                 bg=t["pop"], fg=t["fg"])
        self.step_lbl.pack(pady=(4, 6))

        # --- Main Animation Canvas
        self.canvas = tk.Canvas(self, width=CW, height=CH, bg=t["card_alt"], highlightthickness=1, highlightbackground=t["border"])
        self.canvas.pack(pady=4)

        # --- Overall Progress Bar
        self.bar = ttk.Progressbar(self, maximum=100, length=500)
        self.bar.pack(pady=(10, 4))
        self.count_lbl = tk.Label(self, text="", font=("Segoe UI", 9), bg=t["pop"], fg=t["sub"])
        self.count_lbl.pack()

        # --- Action Buttons
        self.btns = tk.Frame(self, bg=t["pop"])
        self.btns.pack(pady=12)
        self.b_pause = ttk.Button(self.btns, text="⏸ Pause (Space)", command=self.toggle_pause)
        self.b_pause.grid(row=0, column=0, padx=5)
        ttk.Button(self.btns, text="⏭ Next Step (→)", command=self.next_step).grid(row=0, column=1, padx=5)
        if not manual:
            ttk.Button(self.btns, text="⏰ Snooze 5m", command=self.snooze).grid(row=0, column=2, padx=5)
        ttk.Button(self.btns, text="✖ Skip", command=self.skip).grid(row=0, column=3, padx=5)

        self.bind("<space>", lambda e: self.toggle_pause())
        self.bind("<Right>", lambda e: self.next_step())
        self.bind("<Escape>", lambda e: self.on_close())
        self.focus_force()

        if app.e.s["sound"]:
            beep(app.root)
        if app.e.s["voice"]:
            speak(line)
        self.show_step()
        self.after(35, self.frame)

    def draw_pills(self):
        c, t = self.pill_canvas, self.t
        c.delete("all")
        n = max(1, len(self.steps))
        gap = 6
        w = (460 - gap * (n - 1)) / n
        for idx in range(n):
            x0 = 10 + idx * (w + gap)
            col = t["good"] if idx < self.i else (t["accent"] if idx == self.i else t["bar"])
            c.create_rectangle(x0, 4, x0 + w, 12, fill=col, outline="")

    # ---- flow
    def show_step(self):
        s = self.steps[self.i]
        self.draw_pills()
        self.step_lbl.config(text=f"Step {self.i + 1} of {len(self.steps)}: {s['t']}")
        if self.app.e.s["voice"]:
            speak(s["t"])

    def next_step(self):
        if self.finished:
            return
        self.done_t += self.steps[self.i]["sec"]
        self.i += 1
        self.step_t = 0.0
        if self.i >= len(self.steps):
            self.finish()
        else:
            self.show_step()

    def toggle_pause(self):
        self.paused = not self.paused
        self.b_pause.config(text="▶ Resume (Space)" if self.paused else "⏸ Pause (Space)")

    def frame(self):
        if not self.alive:
            return
        now = time.monotonic()
        dt_ = now - self.last
        self.last = now
        if not self.finished:
            if not self.paused:
                self.step_t += dt_
            step = self.steps[self.i]
            if self.step_t >= step["sec"]:
                self.next_step()
            if not self.finished:
                step = self.steps[self.i]
                left = max(0, step["sec"] - self.step_t)
                self.draw(step, left)
                prog = 100 * (self.done_t + self.step_t) / self.total
                self.bar["value"] = min(100, prog)
                rem = self.total - self.done_t - self.step_t
                self.count_lbl.config(text=f"Total remaining: {int(max(0, rem)) // 60}:{int(max(0, rem)) % 60:02d}"
                                           + ("   •   PAUSED" if self.paused else "   •   Press Space to pause, → to skip step"))
        else:
            self.draw_confetti()
        self.after(35, self.frame)

    # ---- animations
    def draw(self, step, left):
        c, t = self.canvas, self.t
        c.delete("all")
        cx, cy = CW / 2, CH / 2
        anim = step.get("anim", "ring")

        if anim == "breathe":
            ph = self.step_t % 14
            if ph < 4:
                r, label, sub = 28 + 48 * (ph / 4), "Inhale Slowly...", f"{4 - int(ph)}s"
                col = t["accent"]
            elif ph < 8:
                r, label, sub = 76, "Hold Breath...", f"{8 - int(ph)}s"
                col = t["accent2"]
            else:
                r, label, sub = 76 - 48 * ((ph - 8) / 6), "Exhale Gently...", f"{14 - int(ph)}s"
                col = t["good"]
            c.create_oval(cx - 82, cy - 82, cx + 82, cy + 82, outline=t["bar"], width=2, dash=(4, 4))
            c.create_oval(cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8, outline=col, width=2)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="")
            c.create_text(cx, cy - 8, text=label, fill="white", font=("Segoe UI", 12, "bold"))
            c.create_text(cx, cy + 14, text=sub, fill="white", font=("Segoe UI", 10))

        elif anim == "box_breathe":
            ph = self.step_t % 16
            sz = 68
            x0, y0, x1, y1 = cx - sz, cy - sz, cx + sz, cy + sz
            c.create_rectangle(x0, y0, x1, y1, outline=t["bar"], width=4)
            side = int(ph // 4)
            frac = (ph % 4) / 4.0
            if side == 0:
                px, py = x0 + frac * (2 * sz), y0
                lbl = "Inhale (4s)"
            elif side == 1:
                px, py = x1, y0 + frac * (2 * sz)
                lbl = "Hold Full (4s)"
            elif side == 2:
                px, py = x1 - frac * (2 * sz), y1
                lbl = "Exhale (4s)"
            else:
                px, py = x0, y1 - frac * (2 * sz)
                lbl = "Hold Empty (4s)"
            c.create_oval(px - 10, py - 10, px + 10, py + 10, fill=t["accent"], outline="white", width=2)
            c.create_text(cx, cy - 10, text=lbl, fill=t["fg"], font=("Segoe UI", 13, "bold"))
            c.create_text(cx, cy + 14, text=f"{int(left) + 1}s left", fill=t["sub"], font=("Segoe UI", 10))

        elif anim in ("eyes", "figure8"):
            # Lissajous figure-8 curve
            for k in range(60):
                ang = k * 2 * math.pi / 60
                gx = cx + 175 * math.sin(ang)
                gy = cy + 55 * math.sin(2 * ang)
                c.create_oval(gx - 1, gy - 1, gx + 1, gy + 1, fill=t["bar"], outline="")
            ang = self.step_t * 1.6
            x = cx + 175 * math.sin(ang)
            y = cy + 55 * math.sin(2 * ang)
            c.create_oval(x - 18, y - 18, x + 18, y + 18, outline=t["accent"], width=2)
            c.create_oval(x - 11, y - 11, x + 11, y + 11, fill=t["good"], outline="")
            c.create_text(cx, CH - 16, text=f"Track the glowing dot smoothly • {int(left) + 1}s", fill=t["sub"], font=("Segoe UI", 9))

        elif anim == "far":
            for ring_i in range(3):
                p = ((self.step_t * 25 + ring_i * 28) % 84)
                c.create_oval(cx - p, cy - p, cx + p, cy + p, outline=t["accent"], width=2)
            c.create_text(cx, cy, text="🏔️", font=("Segoe UI Emoji", 36))
            c.create_text(cx, CH - 16, text=f"Focus 20ft (6m) away • {int(left) + 1}s", fill=t["sub"], font=("Segoe UI", 10))

        elif anim == "posture":
            sway = math.sin(self.step_t * 2.5) * 14
            # Head
            c.create_oval(cx - 14 + sway * 0.4, cy - 68, cx + 14 + sway * 0.4, cy - 40, outline=t["accent"], width=3)
            # Spine
            c.create_line(cx + sway * 0.2, cy - 40, cx, cy + 25, fill=t["good"], width=4)
            # Arms
            c.create_line(cx - 42, cy - 15 - sway * 0.5, cx + sway * 0.2, cy - 28, cx + 42, cy - 15 + sway * 0.5, fill=t["accent"], width=3)
            # Base
            c.create_line(cx - 30, cy + 25, cx + 30, cy + 25, fill=t["bar"], width=4)
            c.create_text(cx, cy + 55, text=f"Hold & Breathe Smoothly • {int(left) + 1}s", fill=t["fg"], font=("Segoe UI", 11, "bold"))

        elif anim == "rep_counter":
            # Up-down rhythm bar for pushups/squats/calf raises
            cycle = (math.sin(self.step_t * 2.4) + 1) / 2  # 0 to 1
            reps_done = int(self.step_t / 2.6) + 1
            bar_h = 110
            y_top = cy - 55
            y_bot = cy + 55
            cur_y = y_bot - cycle * bar_h
            c.create_rectangle(cx - 90, y_top, cx - 60, y_bot, outline=t["bar"], width=2)
            c.create_rectangle(cx - 88, cur_y, cx - 62, y_bot, fill=t["good"], outline="")
            phase_txt = "⬆️  PUSH / UP" if cycle > 0.5 else "⬇️  LOWER / DOWN"
            c.create_text(cx + 25, cy - 22, text=f"Rep Pace #{reps_done}", fill=t["accent"], font=("Segoe UI", 20, "bold"))
            c.create_text(cx + 25, cy + 12, text=phase_txt, fill=t["fg"], font=("Segoe UI", 12, "bold"))
            c.create_text(cx + 25, cy + 42, text=f"{int(left) + 1}s remaining", fill=t["sub"], font=("Segoe UI", 10))

        else:  # ring countdown
            frac = left / max(1, step["sec"])
            c.create_oval(cx - 72, cy - 72, cx + 72, cy + 72, outline=t["bar"], width=12)
            if frac > 0.003:
                c.create_arc(cx - 72, cy - 72, cx + 72, cy + 72, start=90, extent=-359.9 * frac,
                             style="arc", outline=t["good"], width=12)
            c.create_text(cx, cy - 6, text=str(int(left) + 1), fill=t["fg"], font=("Segoe UI", 32, "bold"))
            c.create_text(cx, cy + 28, text="seconds", fill=t["sub"], font=("Segoe UI", 9))

    # ---- finish / confetti / mood
    def finish(self):
        self.finished = True
        self.draw_pills()
        colors = [self.t["accent"], self.t["good"], self.t["gold"], self.t["warn"], "#a855f7"]
        self.confetti = [
            [random.randint(20, CW - 20), random.randint(-CH, 0), random.uniform(-1.5, 1.5), random.uniform(2.5, 5.5), random.choice(colors)]
            for _ in range(38)
        ]
        done = self.app.e.line(self.ch, "done_lines")
        self.step_lbl.config(text=done)
        self.bar["value"] = 100
        self.count_lbl.config(text="Rate your post-break energy (+15 XP):")
        for w in self.btns.winfo_children():
            w.destroy()
        for emo, label, val in (("😫", "Drained", 1), ("😐", "Okay", 2), ("🙂", "Good", 3), ("😄", "Energised", 4)):
            b = ttk.Button(self.btns, text=f"{emo}  {label}", command=lambda v=val: self.complete(v))
            b.grid(row=0, column=val, padx=5)
        if self.app.e.s["voice"]:
            speak(done)

    def draw_confetti(self):
        c, t = self.canvas, self.t
        c.delete("all")
        for p in self.confetti:
            p[0] += p[2]
            p[1] += p[3]
            if p[1] > CH:
                p[1] = -10
                p[0] = random.randint(20, CW - 20)
            c.create_oval(p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4, fill=p[4], outline="")
        c.create_text(CW / 2, CH / 2 - 12, text="🎉 Break Complete! +15 XP", font=("Segoe UI", 22, "bold"), fill=t["good"])
        c.create_text(CW / 2, CH / 2 + 22, text="Select how you feel below to log your session", font=("Segoe UI", 10), fill=t["sub"])

    def complete(self, mood):
        if not self.alive:
            return
        self.close()
        self.app.on_break_done(self.act, mood)

    def snooze(self):
        self.close()
        self.app.on_break_snooze()

    def skip(self):
        self.close()
        self.app.on_break_skip()

    def on_close(self):
        if self.finished:
            self.complete(None)
        else:
            self.skip()

    def close(self):
        self.alive = False
        self.app.popup = None
        self.destroy()


class MiniHUD(tk.Toplevel):
    """Draggable, always-on-top compact floating HUD widget for second monitors or corner tracking."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        t = app.t
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.93)
        except Exception:
            pass
        self.configure(bg=t["accent"])
        sw = self.winfo_screenwidth()
        self.geometry(f"250x76+{sw - 270}+40")

        inner = tk.Frame(self, bg=t["card"], padx=10, pady=6)
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=t["card"])
        top.pack(fill="x")
        tk.Label(top, text="⚡ BreakBuddy HUD", font=("Segoe UI", 8, "bold"), bg=t["card"], fg=t["accent"]).pack(side="left")
        close_btn = tk.Label(top, text="✕", font=("Segoe UI", 9, "bold"), bg=t["card"], fg=t["sub"], cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: app.toggle_hud())

        mid = tk.Frame(inner, bg=t["card"])
        mid.pack(fill="x", pady=(4, 0))
        self.lbl_time = tk.Label(mid, text="45:00", font=("Segoe UI", 16, "bold"), bg=t["card"], fg=t["fg"])
        self.lbl_time.pack(side="left")

        btn_water = tk.Label(mid, text="🥤+1", font=("Segoe UI", 9, "bold"), bg=t["card_alt"], fg=t["accent"], padx=6, pady=2, cursor="hand2")
        btn_water.pack(side="right", padx=3)
        btn_water.bind("<Button-1>", lambda e: app.drink())

        btn_brk = tk.Label(mid, text="▶ Break", font=("Segoe UI", 9, "bold"), bg=t["accent"], fg="white", padx=6, pady=2, cursor="hand2")
        btn_brk.pack(side="right", padx=3)
        btn_brk.bind("<Button-1>", lambda e: app.show_break(manual=True))

        # Dragging support
        for w in (inner, top, self.lbl_time):
            w.bind("<ButtonPress-1>", self._start_move)
            w.bind("<B1-Motion>", self._on_move)

    def _start_move(self, event):
        self._x = event.x
        self._y = event.y

    def _on_move(self, event):
        x = self.winfo_x() + event.x - self._x
        y = self.winfo_y() + event.y - self._y
        self.geometry(f"+{x}+{y}")

    def update_hud(self):
        e = self.app.e
        if e.pomo_active:
            m, s = int(e.pomo_left) // 60, int(e.pomo_left) % 60
            self.lbl_time.config(text=f"🍅 {m:02d}:{s:02d}", fg=self.app.t["gold"])
        else:
            left = max(0, e.interval_sec() - e.since_break)
            m, s = int(left) // 60, int(left) % 60
            self.lbl_time.config(text=f"⏱ {m:02d}:{s:02d}", fg=self.app.t["fg"])


class Toast(tk.Toplevel):
    """Sleek corner notification with interactive buttons and auto-dismiss."""

    def __init__(self, app, title, text, buttons=(), avatar="🙂", timeout=25):
        super().__init__(app.root)
        t = app.t
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=t["accent"])
        inner = tk.Frame(self, bg=t["card"], padx=10, pady=8)
        inner.pack(padx=2, pady=2, fill="both", expand=True)
        tk.Label(inner, text=avatar, font=("Segoe UI Emoji", 28), bg=t["card"], fg=t["fg"]).grid(row=0, column=0, rowspan=2, padx=(4, 10), pady=4)
        tk.Label(inner, text=title, font=("Segoe UI", 10, "bold"), bg=t["card"], fg=t["accent"], anchor="w").grid(row=0, column=1, sticky="w")
        tk.Label(inner, text=text, wraplength=260, justify="left", font=("Segoe UI", 9),
                 bg=t["card"], fg=t["fg"]).grid(row=1, column=1, sticky="w", padx=(0, 6))
        row = tk.Frame(inner, bg=t["card"])
        row.grid(row=2, column=0, columnspan=2, pady=(6, 2), sticky="e")
        for label, cb in buttons:
            ttk.Button(row, text=label, command=lambda cb=cb: self.act(cb)).pack(side="left", padx=3)
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 76}")
        if app.e.s["sound"]:
            beep(app.root)
        self._timer = self.after(timeout * 1000, self.safe_destroy)

    def act(self, cb):
        try:
            cb()
        finally:
            self.safe_destroy()

    def safe_destroy(self):
        try:
            self.destroy()
        except Exception:
            pass
