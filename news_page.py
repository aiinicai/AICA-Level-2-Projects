"""Live (refreshable) India tax and finance RSS reader tab for BreakBuddy Pro."""
import datetime as dt
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from urllib.parse import urlsplit

from .news_service import TOPICS


IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def pretty_date(timestamp):
    if not timestamp:
        return 'Undated'
    return dt.datetime.fromtimestamp(timestamp, tz=IST).strftime('%d %b %Y %I:%M %p')


class IndiaNewsPage:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.t = app.t
        self.manager = app.news
        self.version = -1
        self.selected_url = ''
        self.shown = []
        self.topic_var = tk.StringVar(value='All Topics')
        self.search_var = tk.StringVar(value='')
        self.official_var = tk.BooleanVar(value=False)
        self.auto_var = tk.BooleanVar(value=bool(app.e.s.get('news_auto_refresh', True)))
        self.search_var.trace_add('write', lambda *_: self.render(force=True))
        self._build()
        self.render(force=True)

    def _build(self):
        t = self.t
        head = tk.Frame(self.parent, bg=t['bg'])
        head.pack(fill='x', pady=(0, 8))
        tk.Label(head, text='INDIA TAX & FINANCE NEWS', bg=t['bg'], fg=t['fg'],
                 font=('Segoe UI', 16, 'bold')).pack(side='left')
        ttk.Button(head, text='↻  Refresh Live News', style='Accent.TButton', command=self.refresh_now).pack(side='right')
        tk.Label(self.parent, text='CBDT • RBI • GST • Markets • Audit | Internet is required for live refresh; last successful feed is available offline.',
                 bg=t['bg'], fg=t['sub'], anchor='w', justify='left',
                 wraplength=805).pack(fill='x', pady=(0, 10))
        controls = tk.Frame(self.parent, bg=t['card'], padx=10, pady=10)
        controls.pack(fill='x')
        tk.Label(controls, text='Topic:', fg=t['fg'], bg=t['card']).pack(side='left')
        category = ttk.Combobox(controls, textvariable=self.topic_var, values=TOPICS, state='readonly', width=20)
        category.pack(side='left', padx=(6, 12))
        category.bind('<<ComboboxSelected>>', lambda ev: self.render(force=True))
        ttk.Checkbutton(controls, text='Official only', variable=self.official_var,
                        command=lambda: self.render(force=True)).pack(side='left', padx=(0, 10))
        tk.Label(controls, text='Find:', fg=t['fg'], bg=t['card']).pack(side='left')
        tk.Entry(controls, textvariable=self.search_var, width=18, relief='flat',
                 bg=t['card_alt'], fg=t['fg'], insertbackground=t['fg']).pack(side='left', padx=6, ipady=4)
        self.status = tk.Label(self.parent, text='Loading cached headlines…', bg=t['bg'], fg=t['sub'],
                               font=('Segoe UI', 9), anchor='w', wraplength=820)
        self.status.pack(fill='x', pady=(7, 4))

        digest = tk.Frame(self.parent, bg=t['card'], padx=13, pady=9)
        digest.pack(fill='x', pady=(0, 8))
        tk.Label(digest, text='AT A GLANCE — HEADLINE DIGEST', bg=t['card'], fg=t['accent'],
                 font=('Segoe UI', 10, 'bold'), anchor='w').pack(fill='x')
        self.digest_text = tk.Label(digest, text='', bg=t['card'], fg=t['fg'], wraplength=790,
                                    font=('Segoe UI', 9), anchor='w', justify='left')
        self.digest_text.pack(fill='x', pady=(3, 0))

        grid = tk.Frame(self.parent, bg=t['bg'])
        grid.pack(fill='both', expand=True, pady=(0, 8))
        self.table = ttk.Treeview(grid, columns=('date', 'topic', 'source', 'title'),
                                  show='headings', selectmode='browse', height=7)
        for key, text, width, stretch in [
            ('date', 'Published (IST)', 126, False), ('topic', 'Topic', 112, False),
            ('source', 'Publisher', 130, False), ('title', 'Latest Headlines', 350, True),
        ]:
            self.table.heading(key, text=text)
            self.table.column(key, width=width, minwidth=68, stretch=stretch, anchor='w')
        sc = ttk.Scrollbar(grid, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=sc.set)
        self.table.pack(side='left', fill='both', expand=True)
        sc.pack(side='right', fill='y')
        self.table.bind('<<TreeviewSelect>>', self.show_selected)
        self.table.bind('<Double-1>', lambda ev: self.open_story())

        details = tk.Frame(self.parent, bg=t['card'], padx=12, pady=8)
        details.pack(fill='x')
        tk.Label(details, text='HEADLINE & SOURCE EXCERPT', bg=t['card'], fg=t['accent'],
                 font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.detail = tk.Text(details, height=4, wrap='word', bg=t['card'], fg=t['fg'],
                              borderwidth=0, highlightthickness=0, font=('Segoe UI', 10),
                              insertbackground=t['fg'])
        self.detail.pack(fill='x', pady=(4, 3))
        self.detail.configure(state='disabled')
        foot = tk.Frame(self.parent, bg=t['bg'])
        foot.pack(fill='x', pady=(7, 0))
        ttk.Checkbutton(foot, text='Auto-refresh every 15 minutes while reading', variable=self.auto_var,
                        command=self.set_auto).pack(side='left')
        self.open_btn = ttk.Button(foot, text='Open Original Article ↗', command=self.open_story)
        self.open_btn.pack(side='right')
        self.copy_btn = ttk.Button(foot, text='Copy Article Link', command=self.copy_story_link)
        self.copy_btn.pack(side='right', padx=8)
        tk.Label(self.parent,
                 text='Source excerpts, where provided, are not legal advice. Verify effective dates, circulars and filing deadlines on official portals.',
                 bg=t['bg'], fg=t['sub'], wraplength=810, anchor='w', justify='left',
                 font=('Segoe UI', 8)).pack(fill='x', pady=(7, 0))
        self._enable_links(False)

    def set_auto(self):
        self.app.e.s['news_auto_refresh'] = self.auto_var.get()
        self.app.e.save_settings()
        if self.auto_var.get():
            self.manager.refresh()
        self.render(force=True)

    def enter(self):
        self.render(force=True)
        if self.auto_var.get() or not self.manager.snapshot()['items']:
            self.manager.refresh()
        self.render(force=True)

    def refresh_now(self):
        self.manager.refresh(force=True)
        self.render(force=True)

    def tick(self):
        if self.auto_var.get():
            self.manager.refresh()
        self.render()

    def render(self, force=False):
        snapshot = self.manager.snapshot()
        if not force and snapshot['version'] == self.version:
            return
        self.version = snapshot['version']
        items = snapshot['items']
        kind = self.topic_var.get()
        search = self.search_var.get().casefold().strip()
        shown = [item for item in items
                 if (kind == 'All Topics' or item['topic'] == kind)
                 and (not self.official_var.get() or item['kind'] == 'Official')
                 and (not search or any(search in str(item.get(k, '')).casefold()
                                        for k in ('title', 'summary', 'source', 'topic')))]
        self.shown = shown
        old_url = self.selected_url
        self.table.delete(*self.table.get_children())
        for idx, item in enumerate(shown):
            stamp = dt.datetime.fromtimestamp(item['published'], tz=IST).strftime('%d %b %H:%M') if item['published'] else 'Undated'
            if item['kind'] == 'Official':
                publisher = '[Official] ' + item['source']
            else:
                publisher = item['source']
            self.table.insert('', 'end', iid=str(idx), values=(stamp, item['topic'], publisher, item['title']))
        found = next((i for i, it in enumerate(shown) if it['url'] == old_url), None)
        if found is None and shown:
            found = 0
        if found is not None:
            self.table.selection_set(str(found))
            self.table.see(str(found))
            self._display_item(shown[found])
        else:
            self._display_item(None)
        now = dt.datetime.now().strftime('%I:%M %p')
        if snapshot['loading']:
            note = 'Updating live feeds in the background…'
        elif snapshot['updated']:
            elapsed = max(0, (dt.datetime.now().timestamp() - snapshot['updated']) / 60)
            note = (f'Last successful refresh: {pretty_date(snapshot["updated"])} • '
                    f'{int(elapsed)} min ago' + (' • Cached/offline' if snapshot['failures'] and elapsed > 15 else ''))
        else:
            note = 'No online update yet — select Refresh Live News.'
        if snapshot['failures'] and not snapshot['loading']:
            note += f' • {len(snapshot["failures"])} sources unavailable'
        self.status.configure(text=f'{len(shown)} headlines shown / {len(items)} in cache • {note}')
        if shown:
            digest_rows = [f'• {it["title"][:115]}' for it in shown[:3]]
            self.digest_text.configure(text='\n'.join(digest_rows))
        else:
            self.digest_text.configure(text='No matching headlines. Change the filters or refresh the news feeds.')

    def show_selected(self, event=None):
        chosen = self.table.selection()
        if not chosen:
            return
        try:
            item = self.shown[int(chosen[0])]
        except (ValueError, IndexError):
            return
        self._display_item(item)

    def _display_item(self, item):
        self.detail.configure(state='normal')
        self.detail.delete('1.0', 'end')
        if item:
            summary = item.get('summary') or (
                'This feed provides a headline but no verified article summary. '
                'Open the full article to review details before acting.'
            )
            msg = (f'{item["title"]}\n\n'
                   f'{item["source"]}  |  {item["topic"]}  |  {pretty_date(item["published"])}\n'
                   f'{"Official publisher" if item["kind"] == "Official" else "News publisher"}\n\n'
                   f'{summary}')
            self.detail.insert('1.0', msg)
            self.selected_url = item.get('url', '')
        else:
            self.detail.insert('1.0', 'Select a headline to see its available source excerpt.')
            self.selected_url = ''
        self.detail.configure(state='disabled')
        self._enable_links(bool(self.selected_url))

    def _enable_links(self, enabled):
        self.open_btn.state(['!disabled'] if enabled else ['disabled'])
        self.copy_btn.state(['!disabled'] if enabled else ['disabled'])

    def open_story(self):
        if urlsplit(self.selected_url).scheme in ('http', 'https'):
            webbrowser.open(self.selected_url)
        elif self.selected_url:
            messagebox.showwarning('Invalid link', 'The source link is not a valid web address.', parent=self.app.root)

    def copy_story_link(self):
        if self.selected_url:
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(self.selected_url)
