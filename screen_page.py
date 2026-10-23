"""Application-level screen time dashboard with privacy and export controls."""
import datetime as dt
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def readable(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds//3600}h {seconds%3600//60:02d}m {seconds%60:02d}s'


class ScreenTimePage:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.t = app.t
        self.monitor = app.e.monitor
        self.period = tk.StringVar(value='Today')
        self.track_var = tk.BooleanVar(value=app.e.s.get('app_monitor_on', True))
        self.window_var = tk.BooleanVar(value=app.e.s.get('monitor_window_titles', False))
        self.build()

    def build(self):
        t = self.t
        header = tk.Frame(self.parent, bg=t['bg'])
        header.pack(fill='x', pady=(0, 10))
        tk.Label(header, text='ACTIVE APPLICATION SCREEN TIME', bg=t['bg'], fg=t['fg'],
                 font=('Segoe UI', 15, 'bold')).pack(side='left')
        ttk.Button(header, text='Export Screen-Time CSV', command=self.export).pack(side='right')
        desc = 'Windows foreground applications; idle time is excluded. No screenshots, keystrokes or cloud sync.'
        tk.Label(self.parent, text=desc, bg=t['bg'], fg=t['sub'], anchor='w').pack(fill='x', pady=(0, 8))
        if sys.platform != 'win32':
            tk.Label(self.parent, text='Per-app foreground monitoring is available on Windows only.',
                     bg=t['bg'], fg=t['warn']).pack(anchor='w')
        controls = tk.Frame(self.parent, bg=t['card'], padx=14, pady=10)
        controls.pack(fill='x', pady=(0, 8))
        tk.Label(controls, text='Period', bg=t['card'], fg=t['fg']).pack(side='left')
        cb = ttk.Combobox(controls, values=['Today', 'Yesterday', 'Last 7 days'], state='readonly',
                           textvariable=self.period, width=13)
        cb.pack(side='left', padx=8)
        cb.bind('<<ComboboxSelected>>', lambda ev: self.refresh())
        self.pause_btn = ttk.Button(controls, command=self.toggle_track)
        self.pause_btn.pack(side='left', padx=12)
        ttk.Button(controls, text='Erase Usage History', command=self.clear).pack(side='right')
        self.live = tk.Label(self.parent, text='', bg=t['card'], fg=t['accent'],
                             anchor='w', padx=12, pady=9, wraplength=685, justify='left')
        self.live.pack(fill='x', pady=(0, 8))
        self.total = tk.Label(self.parent, text='', bg=t['bg'], fg=t['fg'],
                              font=('Segoe UI', 11, 'bold'), anchor='w')
        self.total.pack(fill='x', pady=(0, 6))
        self.chart = tk.Canvas(self.parent, height=110, bg=t['card'], highlightthickness=0)
        self.chart.pack(fill='x', pady=(0, 8))
        grid = tk.Frame(self.parent, bg=t['bg'])
        grid.pack(fill='both', expand=True)
        self.apps = ttk.Treeview(grid, columns=('app', 'duration', 'share'), show='headings', height=7)
        for key, title, width in [('app','Application',270),('duration','Active Time',130),('share','Share',80)]:
            self.apps.heading(key, text=title)
            self.apps.column(key, width=width, stretch=(key == 'app'), anchor='w')
        scr = ttk.Scrollbar(grid, orient='vertical', command=self.apps.yview)
        self.apps.configure(yscrollcommand=scr.set)
        self.apps.pack(side='left', fill='both', expand=True)
        scr.pack(side='right', fill='y')
        below = tk.Frame(self.parent, bg=t['bg'])
        below.pack(fill='x', pady=(8, 0))
        cb_titles = ttk.Checkbutton(below, text='Store window titles (may contain sensitive client details)',
                                    variable=self.window_var, command=self.toggle_titles)
        cb_titles.pack(side='left')
        ttk.Button(below, text='View Saved Window Titles', command=self.show_titles).pack(side='right')
        tk.Label(self.parent, text='Only app names are saved by default. Turning title history off also erases saved titles.',
                 bg=t['bg'], fg=t['sub'], font=('Segoe UI', 9)).pack(anchor='w', pady=(4, 0))
        self.refresh()

    def toggle_track(self):
        s = self.app.e.s
        s['app_monitor_on'] = not s.get('app_monitor_on', True)
        self.track_var.set(s['app_monitor_on'])
        self.app.e.save_settings()
        self.refresh()

    def toggle_titles(self):
        on = self.window_var.get()
        if on and not messagebox.askyesno('Window Title Privacy',
                  'Window titles may contain client names, document names, email subjects, or other private details. '
                  'Store this information locally in usage history?', parent=self.app.root):
            self.window_var.set(False)
            return
        self.app.e.s['monitor_window_titles'] = on
        self.app.e.save_settings()
        if not on:
            self.monitor.stop_saving_titles()

    def refresh(self):
        self.pause_btn.configure(text='Pause Monitoring' if self.app.e.s.get('app_monitor_on', True) else 'Resume Monitoring')
        app, title = self.monitor.live_app, self.monitor.live_title
        self.live.configure(text=f'CURRENT APP: {app}\nCURRENT WINDOW: {title[:115] or "—"}')
        totals = self.monitor.totals(self.period.get())
        seconds = sum(totals.values())
        self.total.config(text=f'{self.period.get()}: {readable(seconds)} in {len(totals)} tracked applications')
        for row in self.apps.get_children():
            self.apps.delete(row)
        for name, val in list(totals.items())[:120]:
            self.apps.insert('', 'end', values=(name, readable(val), f'{val/seconds*100:.1f}%' if seconds else '0%'))
        self.chart.delete('all')
        w = max(450, self.chart.winfo_width())
        maxsec = max(totals.values(), default=1)
        for i, (name, val) in enumerate(list(totals.items())[:5]):
            y = 8 + i*20
            width = max(2, (w-260) * val/maxsec)
            self.chart.create_text(12, y+8, text=name[:22], anchor='w', fill=self.t['fg'], font=('Segoe UI', 9))
            self.chart.create_rectangle(185, y+2, 185+width, y+15, fill=self.t['accent'], outline='')
            self.chart.create_text(w-8, y+8, anchor='e', text=readable(val), fill=self.t['sub'], font=('Segoe UI', 8))
        if not totals:
            self.chart.create_text(w/2, 55, text='No application activity recorded for this period', fill=self.t['sub'])

    def show_titles(self):
        win = tk.Toplevel(self.app.root)
        win.title('Saved Window Titles — Local Only')
        win.geometry('720x400')
        win.configure(bg=self.t['bg'])
        tk.Label(win, text=f'Saved window-title history ({self.period.get()})', bg=self.t['bg'], fg=self.t['fg'],
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=12, pady=10)
        tree = ttk.Treeview(win, columns=('title','duration'), show='headings')
        tree.heading('title', text='Application | Window title')
        tree.heading('duration', text='Active time')
        tree.column('title', width=580)
        tree.column('duration', width=115)
        tree.pack(fill='both', expand=True, padx=12, pady=10)
        for title, seconds in self.monitor.totals(self.period.get(), key='windows').items():
            tree.insert('', 'end', values=(title, readable(seconds)))
        tk.Label(win, text='Window titles are saved only after you enable the opt-in setting.',
                 bg=self.t['bg'], fg=self.t['sub']).pack(pady=(0, 8))

    def clear(self):
        if messagebox.askyesno('Erase Usage History', 'Permanently delete locally saved application and window usage history?', parent=self.app.root):
            self.monitor.clear()
            self.refresh()

    def export(self):
        path = filedialog.asksaveasfilename(parent=self.app.root, title='Export Application Screen-Time',
                                           defaultextension='.csv', initialfile=f'BreakBuddy_App_Usage_{dt.date.today()}.csv',
                                           filetypes=[('CSV file','*.csv')])
        if path:
            self.monitor.save()
            try:
                self.monitor.export(path)
                messagebox.showinfo('Exported', f'Saved to:\n{path}', parent=self.app.root)
            except OSError as ex:
                messagebox.showerror('Export failed', str(ex), parent=self.app.root)
