"""Wellness Lab: persistent break scratchpad, optional Schulte game, guided meditation."""
import datetime as dt
import random
import time
import tkinter as tk
from tkinter import ttk

from .config import USER, load_json, save_json

SCRATCH_FILE = USER / 'where_i_left_off.json'
TOOLS_FILE = USER / 'wellness_tools.json'


class WellnessLab:
    def __init__(self, app, parent):
        self.app, self.parent, self.t = app, parent, app.t
        self._scratch_job = None
        self._loading = False
        self._last_frame = time.monotonic()
        self.game_running = False
        self.game_next = 1
        self.game_errors = 0
        self.game_started = None
        self.game_end = 25
        self.med_running = False
        self.med_left = 120.0
        self.med_total = 120
        self.med_elapsed = 0.0
        self.tools = load_json(TOOLS_FILE, {})
        if not isinstance(self.tools, dict):
            self.tools = {}
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill='both', expand=True)
        for title, builder in [
            ('  Where I Left Off  ', self.build_scratch),
            ('  Schulte Focus Game  ', self.build_schulte),
            ('  Meditation & Breathing  ', self.build_meditation),
        ]:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=title)
            builder(tab)

    def go_scratch(self):
        self.notebook.select(0)
        self.app.select_page(8)
        self.next_text.focus_set()

    def build_scratch(self, parent):
        t = self.t
        area = tk.Frame(parent, bg=t['card'], padx=22, pady=20)
        area.pack(fill='both', expand=True, pady=10)
        tk.Label(area, text='WHERE I LEFT OFF', bg=t['card'], fg=t['accent'], font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        tk.Label(area, text='Before a break, note your current work and the precise next action. Saved locally and automatically.',
                 bg=t['card'], fg=t['sub'], wraplength=690, justify='left').pack(anchor='w', pady=(3, 16))
        data = load_json(SCRATCH_FILE, {})
        self._loading = True
        self.scratch_client = tk.StringVar(value=data.get('client', ''))
        self.scratch_client.trace_add('write', lambda *_: self.queue_save())
        tk.Label(area, text='CLIENT / PROJECT / ENGAGEMENT', bg=t['card'], fg=t['fg'], font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        tk.Entry(area, textvariable=self.scratch_client, bg=t['card_alt'], fg=t['fg'], insertbackground=t['fg'],
                 relief='flat', font=('Segoe UI', 11)).pack(fill='x', ipady=7, pady=(4, 12))
        tk.Label(area, text='WHAT I WAS DOING', bg=t['card'], fg=t['fg'], font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.work_text = tk.Text(area, height=4, wrap='word', bg=t['card_alt'], fg=t['fg'], insertbackground=t['fg'],
                                 relief='flat', font=('Segoe UI', 11), undo=True)
        self.work_text.pack(fill='x', pady=(4, 12))
        self.work_text.insert('1.0', data.get('work', ''))
        tk.Label(area, text='MY VERY NEXT STEP WHEN I RETURN', bg=t['card'], fg=t['fg'], font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.next_text = tk.Text(area, height=4, wrap='word', bg=t['card_alt'], fg=t['fg'], insertbackground=t['fg'],
                                 relief='flat', font=('Segoe UI', 11), undo=True)
        self.next_text.pack(fill='x', pady=(4, 12))
        self.next_text.insert('1.0', data.get('next', ''))
        for w in (self.work_text, self.next_text):
            w.bind('<<Modified>>', lambda ev, x=w: self._on_modified(x))
            w.edit_modified(False)
        controls = tk.Frame(area, bg=t['card'])
        controls.pack(fill='x', pady=(8, 0))
        ttk.Button(controls, text='Save Now', style='Accent.TButton', command=self.save_scratch).pack(side='left')
        ttk.Button(controls, text='Copy My Return Plan', command=self.copy_plan).pack(side='left', padx=10)
        ttk.Button(controls, text='Clear Fields', command=self.clear_scratch).pack(side='left')
        self.scratch_status = tk.Label(area, bg=t['card'], fg=t['good'], anchor='w',
                                       text=f"Last saved: {data.get('saved', 'Not yet saved')}")
        self.scratch_status.pack(fill='x', pady=10)
        self._loading = False

    def _on_modified(self, widget):
        if widget.edit_modified():
            widget.edit_modified(False)
            self.queue_save()

    def queue_save(self):
        if self._loading:
            return
        if self._scratch_job is not None:
            self.app.root.after_cancel(self._scratch_job)
        self._scratch_job = self.app.root.after(800, self.save_scratch)

    def save_scratch(self):
        if not hasattr(self, 'work_text'):
            return
        if self._scratch_job is not None:
            try:
                self.app.root.after_cancel(self._scratch_job)
            except Exception:
                pass
        self._scratch_job = None
        data = {
            'client': self.scratch_client.get().strip(),
            'work': self.work_text.get('1.0', 'end-1c'),
            'next': self.next_text.get('1.0', 'end-1c'),
            'saved': dt.datetime.now().strftime('%d %b %Y, %I:%M %p'),
        }
        save_json(SCRATCH_FILE, data)
        self.scratch_status.configure(text=f"Saved locally: {data['saved']}")

    def copy_plan(self):
        self.save_scratch()
        msg = (f"Client / Project: {self.scratch_client.get()}\n"
               f"Where I left off: {self.work_text.get('1.0', 'end-1c')}\n"
               f"Next step: {self.next_text.get('1.0', 'end-1c')}")
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(msg)
        self.scratch_status.configure(text='Return plan copied to clipboard')

    def clear_scratch(self):
        self.scratch_client.set('')
        self.work_text.delete('1.0', 'end')
        self.next_text.delete('1.0', 'end')
        self.save_scratch()

    def build_schulte(self, parent):
        t = self.t
        wrap = tk.Frame(parent, bg=t['card'], padx=18, pady=12)
        wrap.pack(fill='both', expand=True, pady=8)
        tk.Label(wrap, text='SCHULTE NUMBER SEARCH', bg=t['card'], fg=t['accent'],
                 font=('Segoe UI', 15, 'bold')).pack(anchor='w')
        tk.Label(wrap, text='Find the numbers in ascending order as quickly as you comfortably can. You may stop at any time.',
                 bg=t['card'], fg=t['sub'], wraplength=670, justify='left').pack(anchor='w', pady=(3, 10))
        row = tk.Frame(wrap, bg=t['card'])
        row.pack(fill='x')
        tk.Label(row, text='Grid:', bg=t['card'], fg=t['fg']).pack(side='left')
        self.schulte_size = tk.StringVar(value='5 × 5')
        ttk.Combobox(row, state='readonly', textvariable=self.schulte_size, values=['4 × 4', '5 × 5', '6 × 6'], width=8).pack(side='left', padx=8)
        ttk.Button(row, text='New Game', style='Accent.TButton', command=self.new_game).pack(side='left', padx=6)
        self.game_info = tk.Label(row, bg=t['card'], fg=t['good'], font=('Segoe UI', 11, 'bold'))
        self.game_info.pack(side='right')
        self.game_board = tk.Frame(wrap, bg=t['card'])
        self.game_board.pack(pady=9)
        self.game_hint = tk.Label(wrap, bg=t['card'], fg=t['sub'],
                                  text='Visual attention practice only — not a treatment or replacement for distance-viewing breaks.')
        self.game_hint.pack(anchor='w')
        self.new_game()

    def new_game(self):
        t = self.t
        self.game_running = True
        self.game_started = None
        self.game_next = 1
        self.game_errors = 0
        n = int(self.schulte_size.get()[0])
        self.game_end = n*n
        for w in self.game_board.winfo_children():
            w.destroy()
        digits = list(range(1, n*n+1))
        random.shuffle(digits)
        self.game_buttons = {}
        for i, v in enumerate(digits):
            btn = tk.Button(self.game_board, text=str(v), font=('Segoe UI', 13, 'bold'), width=4, height=1,
                            bg=t['card_alt'], fg=t['fg'], activebackground=t['accent'],
                            relief='flat', cursor='hand2', command=lambda k=v: self.hit_number(k))
            btn.grid(row=i//n, column=i%n, padx=4, pady=3, ipadx=6, ipady=5)
            self.game_buttons[v] = btn
        best = self.tools.get('schulte_best', {}).get(str(n))
        self.game_info.config(text=f'Find 1  •  00:00  •  Best: {best:.1f}s' if best is not None else 'Find 1  •  00:00')
        self.game_hint.config(text='Start by finding number 1. Timer begins on your first correct click.')

    def hit_number(self, value):
        if not self.game_running:
            return
        if value != self.game_next:
            self.game_errors += 1
            self.game_hint.configure(text=f'Try {self.game_next} next  •  {self.game_errors} mistake(s)')
            return
        if self.game_started is None:
            self.game_started = time.monotonic()
        self.game_buttons[value].config(state='disabled', bg=self.t['good'], disabledforeground='white')
        self.game_next += 1
        if self.game_next > self.game_end:
            secs = time.monotonic() - self.game_started
            n = int(self.schulte_size.get()[0])
            bests = self.tools.setdefault('schulte_best', {})
            if secs < bests.get(str(n), float('inf')):
                bests[str(n)] = round(secs, 2)
            self.tools['schulte_plays'] = self.tools.get('schulte_plays', 0) + 1
            save_json(TOOLS_FILE, self.tools)
            self.game_info.configure(text=f'Finished: {secs:.1f}s • Mistakes: {self.game_errors}')
            self.game_hint.configure(text='Done! Look away from your screen to rest your eyes.')
            self.game_running = False
        else:
            self.game_info.configure(text=f'Find {self.game_next}  •  {int(time.monotonic()-self.game_started)}s')

    def build_meditation(self, parent):
        t = self.t
        wrap = tk.Frame(parent, bg=t['card'], padx=23, pady=15)
        wrap.pack(fill='both', expand=True, pady=8)
        tk.Label(wrap, text='MINDFUL BREATHING BREAK', bg=t['card'], fg=t['accent'],
                 font=('Segoe UI', 15, 'bold')).pack(anchor='w')
        tk.Label(wrap, text='Comfortable paced breathing: inhale 4 seconds, exhale 6 seconds. Breathe naturally if this pace feels uncomfortable.',
                 bg=t['card'], fg=t['sub'], wraplength=650, justify='left').pack(anchor='w', pady=(5, 9))
        row = tk.Frame(wrap, bg=t['card'])
        row.pack(fill='x')
        self.med_duration = tk.StringVar(value='2 min')
        ttk.Combobox(row, state='readonly', textvariable=self.med_duration,
                     values=['2 min', '5 min', '10 min'], width=9).pack(side='left')
        self.med_duration.trace_add('write', lambda *_: self.reset_meditation())
        self.med_btn = ttk.Button(row, text='Start Meditation', style='Accent.TButton', command=self.toggle_meditation)
        self.med_btn.pack(side='left', padx=10)
        ttk.Button(row, text='Reset', command=self.reset_meditation).pack(side='left')
        self.med_label = tk.Label(wrap, text='Ready to unwind', font=('Segoe UI', 16, 'bold'), bg=t['card'], fg=t['fg'])
        self.med_label.pack(pady=(12, 3))
        self.med_clock = tk.Label(wrap, text='02:00 left', font=('Segoe UI', 12), bg=t['card'], fg=t['sub'])
        self.med_clock.pack()
        self.med_canvas = tk.Canvas(wrap, width=320, height=230, bg=t['card'], highlightthickness=0)
        self.med_canvas.pack(pady=6)
        self.med_progress = ttk.Progressbar(wrap, maximum=100)
        self.med_progress.pack(fill='x', pady=(2, 8))
        self.med_notice = tk.Label(wrap, bg=t['card'], fg=t['sub'],
                                   text='Optional wellness exercise. Stop if you feel dizzy or uncomfortable.')
        self.med_notice.pack(anchor='w')
        self.draw_meditation()

    def reset_meditation(self):
        self.med_running = False
        self.med_total = int(self.med_duration.get().split()[0])*60
        self.med_left = float(self.med_total)
        self.med_elapsed = 0.0
        self._last_frame = time.monotonic()
        self.med_btn.config(text='Start Meditation')
        self.med_label.config(text='Ready to unwind')
        self.draw_meditation()

    def toggle_meditation(self):
        self.med_running = not self.med_running
        self._last_frame = time.monotonic()
        self.med_btn.config(text='Pause Meditation' if self.med_running else 'Resume Meditation')
        self.draw_meditation()

    def draw_meditation(self):
        c = self.med_canvas
        c.delete('all')
        phase = self.med_elapsed % 10.0
        inhale = phase < 4
        size = (phase / 4) if inhale else (1 - (phase - 4) / 6)
        radius = 52 + 38 * size
        c.create_oval(160-radius, 115-radius, 160+radius, 115+radius,
                      fill=self.t['card_alt'], outline=self.t['accent'], width=4)
        c.create_text(160, 115, text='Breathe in' if inhale else 'Breathe out', fill=self.t['fg'],
                      font=('Segoe UI', 14, 'bold'))
        self.med_clock.config(text=f'{int(max(0,self.med_left)+0.99)//60:02d}:{int(max(0,self.med_left)+0.99)%60:02d} left')
        self.med_progress['value'] = 100 * (1 - self.med_left / max(1, self.med_total))
        if self.med_running:
            self.med_label.config(text='Inhale gently' if inhale else 'Exhale slowly')

    def tick(self):
        now = time.monotonic()
        diff = min(2, max(0, now - self._last_frame))
        self._last_frame = now
        if self.game_running and self.game_started is not None:
            secs = int(now - self.game_started)
            self.game_info.configure(text=f'Find {self.game_next}  •  {secs//60:02d}:{secs%60:02d}  •  Errors: {self.game_errors}')
        if not self.med_running:
            return
        self.med_left = max(0, self.med_left - diff)
        self.med_elapsed += diff
        self.draw_meditation()
        if self.med_left <= 0:
            self.med_running = False
            self.med_btn.config(text='Start Meditation')
            self.med_label.config(text='Session complete. Well done.')
            date = dt.date.today().isoformat()
            days = self.tools.setdefault('meditation_days', {})
            days[date] = days.get(date, 0) + self.med_total // 60
            save_json(TOOLS_FILE, self.tools)
            self.med_notice.config(text=f'Meditation minutes logged today: {days[date]}')

    def flush(self):
        self.save_scratch()
