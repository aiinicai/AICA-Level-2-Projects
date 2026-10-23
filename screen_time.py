"""Opt-in-friendly, local-only foreground app use statistics for Windows.

No keylogging, screenshots, browsing history, network calls, or background scanning.
Window titles are displayed live, but NOT stored unless the user opts in.
"""
import csv
import datetime as dt
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

from .config import USER, load_json, save_json

IS_WINDOWS = sys.platform == 'win32'


def foreground_window():
    """Return (application.exe, visible title) without third-party packages."""
    if not IS_WINDOWS:
        return None, None
    try:
        import ctypes
        from ctypes import wintypes
        u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
        u32.GetForegroundWindow.restype = wintypes.HWND
        hwnd = u32.GetForegroundWindow()
        if not hwnd:
            return None, None
        u32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        u32.GetWindowTextLengthW.restype = ctypes.c_int
        u32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u32.GetWindowTextW.restype = ctypes.c_int
        u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        length = u32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(min(1024, max(1, length + 1)))
        u32.GetWindowTextW(hwnd, buf, len(buf))
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                    wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        k32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        handle = k32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
        name = f'Process {pid.value}'
        if handle:
            try:
                process_path = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(process_path))
                if k32.QueryFullProcessImageNameW(handle, 0, process_path, ctypes.byref(size)):
                    name = os.path.basename(process_path.value) or name
            finally:
                k32.CloseHandle(handle)
        return name, buf.value.strip()[:160]
    except Exception:
        return None, None


class ScreenTimeMonitor:
    FILE = USER / 'screen_time.json'

    def __init__(self, settings):
        self.settings = settings
        data = load_json(self.FILE, {})
        self.records = data if isinstance(data, dict) else {}
        self.live_app = 'Not available'
        self.live_title = ''
        self._last_sample = None
        self._last_save = time.monotonic()
        self._dirty = False
        self.prune()

    def prune(self):
        # Retain 30 days of app-use data (privacy + bounded local storage).
        threshold = (dt.date.today() - dt.timedelta(days=29)).isoformat()
        stale = [day for day in self.records if day < threshold]
        for day in stale:
            self.records.pop(day, None)
        self._dirty |= bool(stale)

    def sample(self, idle_seconds=0):
        now = time.monotonic()
        # An irregular GUI delay must not result in hours of phantom usage.
        elapsed = min(2.5, max(0, now - self._last_sample)) if self._last_sample is not None else 0
        self._last_sample = now
        if not IS_WINDOWS:
            self.live_app, self.live_title = 'Windows only', ''
            return
        if not self.settings.get('app_monitor_on', True):
            self.live_app, self.live_title = 'Monitoring paused', ''
            return
        app, title = foreground_window()
        self.live_app = app or 'Unknown application'
        self.live_title = title or '(No window title)'
        if not app or app.lower() in ('python.exe', 'pythonw.exe') and ('breakbuddy' in title.lower()):
            return
        if idle_seconds >= self.settings.get('idle_limit_sec', 120) or elapsed <= 0:
            return
        day = dt.date.today().isoformat()
        data = self.records.setdefault(day, {'apps': {}, 'windows': {}})
        data['apps'][app] = round(data['apps'].get(app, 0) + elapsed, 2)
        if self.settings.get('monitor_window_titles', False) and title:
            label = f'{app}  |  {title[:120]}'
            data['windows'][label] = round(data['windows'].get(label, 0) + elapsed, 2)
        self._dirty = True
        if now - self._last_save > 30:
            self.save()

    def totals(self, period='Today', key='apps'):
        today = dt.date.today()
        if period == 'Yesterday':
            dates = [(today - dt.timedelta(days=1)).isoformat()]
        elif period == 'Last 7 days':
            dates = [(today - dt.timedelta(days=x)).isoformat() for x in range(7)]
        else:
            dates = [today.isoformat()]
        out = defaultdict(float)
        for day in dates:
            for app, secs in self.records.get(day, {}).get(key, {}).items():
                out[app] += secs
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def save(self):
        if self._dirty:
            self.prune()
            save_json(self.FILE, self.records)
            self._dirty = False
        self._last_save = time.monotonic()

    def stop_saving_titles(self):
        # Explicitly erase titles already recorded when the user disables this setting.
        for obj in self.records.values():
            obj['windows'] = {}
        self._dirty = True
        self.save()

    def clear(self):
        self.records = {}
        self._dirty = True
        self.save()

    def export(self, filename):
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Category', 'Application or Window', 'Minutes'])
            for day, obj in sorted(self.records.items()):
                for category in ('apps', 'windows'):
                    for label, seconds in sorted(obj.get(category, {}).items()):
                        writer.writerow([day, category, label, round(seconds / 60, 2)])
