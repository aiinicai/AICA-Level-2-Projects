"""Extract the Edit Log from TallyPrime's own screens and track which voucher types and months are covered.

Why this exists: Tally documents that the Edit Log is a display report. It cannot be read through the XML/TDL connection on
this release, but the 'Edit Log Summary - Vouchers' list can be exported with Ctrl+E. This module drives exactly those screens
with keystrokes (Windows only), exports one file per voucher type and month, and then CHECKS each file before moving on.

Path recorded on the user's TallyPrime EDU (Oct 2026):
  Alt+G, type 'Edit Log Summary', Enter  ->  Voucher Type-wise Summary (F5 = all vouchers, F9 = all versions)
  Enter on a voucher type                ->  monthly summary (April ... March)
  Enter on a month                       ->  Edit Log Summary - Vouchers  (Alt+F5 = detailed: one line per version)
  Ctrl+E                                 ->  Export dialog (File Format / Folder Path / File Name; 'Export' is highlighted)

It never types a user name or password, never changes a voucher or master, and stops at the first screen that is not what
was expected.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

import editlog_import as EI

FORMATS = {"ASCII (Comma Delimited)": ".txt", "Excel (Spreadsheet)": ".xlsx", "HTML (Web-Publishing)": ".html",
           "JSON (Data Exchange)": ".json", "XML (Data Interchange)": ".xml"}
SUGGESTED_FORMAT = "ASCII (Comma Delimited)"
MONTHS = ["April", "May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March"]


@dataclass
class Item:
    vtype: str
    type_idx: int
    month: str
    month_idx: int
    year: int

    @property
    def key(self) -> str:
        return f"{self.vtype}|{self.month} {self.year}"

    @property
    def filename_stem(self) -> str:
        return re.sub(r"[^A-Za-z0-9]+", "_", f"EL_{self.vtype}_{self.month}_{self.year}").strip("_")


def month_year(fy_start: date, month_idx: int) -> int:
    m = (fy_start.month - 1 + month_idx) % 12 + 1
    return fy_start.year + ((fy_start.month - 1 + month_idx) // 12)


def month_name(fy_start: date, mi: int) -> str:
    import calendar
    return calendar.month_name[(fy_start.month - 1 + mi) % 12 + 1]


def build_plan(types_in_screen_order: list[str], fy_start: date, register: pd.DataFrame | None = None,
               months: list[int] | None = None) -> list[Item]:
    """One item per voucher type and month. With a register, only type-months that hold vouchers are planned.
    types_in_screen_order is the order Tally lists the voucher types (alphabetical on the screens recorded)."""
    have = None
    if register is not None and len(register):
        d = EI._dt(register["VoucherDate"])
        have = set(zip(register["VoucherType"].astype(str), d.dt.year, d.dt.month))
    out = []
    for ti, t in enumerate(types_in_screen_order):
        for mi in (months if months is not None else range(12)):
            yr = month_year(fy_start, mi)
            mo = (fy_start.month - 1 + mi) % 12 + 1
            if have is not None and (t, yr, mo) not in have:
                continue
            out.append(Item(t, ti, month_name(fy_start, mi), mi, yr))
    return out


build_plan_fy = build_plan


def keys_for(item: Item, detailed_toggle: bool, escapes_after: int = 2) -> list[tuple]:
    """The key steps for one item, starting from the Voucher Type-wise Summary list."""
    s = [("key", "Home"), ("key", "Down", item.type_idx), ("key", "Return"), ("wait", 0.8),
         ("key", "Home"), ("key", "Down", item.month_idx), ("key", "Return"), ("wait", 1.0)]
    if detailed_toggle:
        s += [("key", "alt+F5"), ("wait", 0.6)]
    s += [("key", "ctrl+e"), ("wait", 0.8), ("key", "Return")]
    return s


def unwind_keys(escapes_after: int = 2) -> list[tuple]:
    return [("wait", 0.8), ("key", "Escape", escapes_after), ("wait", 0.6)]


# ------------------------------------------------------------------------------------------------ keyboard (Windows)
class WinKeys:
    """Sends keystrokes to the Tally window with SendInput. No extra packages."""
    VK = {"Home": 0x24, "Down": 0x28, "Up": 0x26, "Return": 0x0D, "Escape": 0x1B, "F5": 0x74, "F9": 0x78, "Tab": 0x09}

    def __init__(self):
        if sys.platform != "win32":
            raise RuntimeError("Keyboard control works on Windows only.")
        import ctypes
        self.ct = ctypes

    def _vk(self, name: str) -> int:
        return self.VK[name] if name in self.VK else ord(name.upper())

    def _send(self, vk: int, up: bool):
        import ctypes.wintypes as wt
        ct = self.ct
        class KI(ct.Structure):
            _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ct.c_void_p)]
        class IN(ct.Structure):
            class U(ct.Union):
                _fields_ = [("ki", KI), ("pad", ct.c_byte * 32)]
            _anonymous_ = ("u",)
            _fields_ = [("type", wt.DWORD), ("u", U)]
        ext = 0x0001 if vk in (0x24, 0x28, 0x26) else 0
        i = IN(type=1, ki=KI(vk, 0, ext | (0x0002 if up else 0), 0, None))
        ct.windll.user32.SendInput(1, ct.byref(i), ct.sizeof(i))

    def press(self, combo: str, n: int = 1):
        parts = combo.split("+")
        mods = [{"ctrl": 0x11, "alt": 0x12, "shift": 0x10}[p.lower()] for p in parts[:-1]]
        k = self._vk(parts[-1])
        for _ in range(n):
            for m in mods:
                self._send(m, False)
            self._send(k, False); self._send(k, True)
            for m in reversed(mods):
                self._send(m, True)
            time.sleep(0.12)

    def type_text(self, text: str):
        punct = {"-": 0xBD, "/": 0xBF, " ": 0x20, ".": 0xBE}
        for ch in text:
            vk = punct.get(ch, ord(ch.upper()) if ch.isalnum() else 0x20)
            self._send(vk, False); self._send(vk, True)
            time.sleep(0.06)

    def _exe(self, h) -> str:
        import ctypes.wintypes as wt
        ct = self.ct
        pid = wt.DWORD(); ct.windll.user32.GetWindowThreadProcessId(h, ct.byref(pid))
        hp = ct.windll.kernel32.OpenProcess(0x1000, False, pid.value)
        name = ""
        if hp:
            buf = ct.create_unicode_buffer(520); n = wt.DWORD(520)
            if ct.windll.kernel32.QueryFullProcessImageNameW(hp, 0, buf, ct.byref(n)):
                name = buf.value
            ct.windll.kernel32.CloseHandle(hp)
        return name

    def _title(self, h) -> str:
        L = self.ct.windll.user32.GetWindowTextLengthW(h)
        b = self.ct.create_unicode_buffer(L + 2)
        self.ct.windll.user32.GetWindowTextW(h, b, L + 1)
        return b.value

    def tally_in_front(self) -> bool:
        h = self.ct.windll.user32.GetForegroundWindow()
        return bool(h) and "tally" in self._exe(h).lower()

    def focus_tally(self) -> bool:
        import ctypes.wintypes as wt
        ct = self.ct
        user32, kernel32 = ct.windll.user32, ct.windll.kernel32
        self.why = ""
        found = []

        @ct.WINFUNCTYPE(ct.c_bool, wt.HWND, wt.LPARAM)
        def cb(h, _):
            if user32.IsWindowVisible(h) and user32.GetWindowTextLengthW(h) > 0 and "tally" in self._exe(h).lower():
                found.append(h)
            return True
        user32.EnumWindows(cb, 0)
        if not found:
            self.why = "No TallyPrime window was found (looked for a program with 'tally' in its name)."
            return False

        def area(h):
            r = wt.RECT(); user32.GetWindowRect(h, ct.byref(r))
            return max(0, r.right - r.left) * max(0, r.bottom - r.top)
        h = max(found, key=area)
        for _try in range(5):
            if self.tally_in_front():
                return True
            if user32.IsIconic(h):
                user32.ShowWindow(h, 9)
            self._send(0x12, False); self._send(0x12, True)
            fg = user32.GetForegroundWindow()
            cur_t = kernel32.GetCurrentThreadId()
            fg_t = user32.GetWindowThreadProcessId(fg, None) if fg else 0
            if fg_t and fg_t != cur_t:
                user32.AttachThreadInput(cur_t, fg_t, True)
            user32.BringWindowToTop(h)
            user32.SetForegroundWindow(h)
            if fg_t and fg_t != cur_t:
                user32.AttachThreadInput(cur_t, fg_t, False)
            time.sleep(0.6)
        fg = user32.GetForegroundWindow()
        self.why = f"In front instead: '{self._title(fg)}' ({Path(self._exe(fg)).name})."
        return False


def tally_date(d: date) -> str:
    return f"{d.day}-{d.month}-{d.year}"


def goto_edit_log_summary(sender, sleep=time.sleep, period: tuple[date, date] | None = None):
    """Gateway of Tally > Display More Reports > Edit Log Summary (reached with Go To), F5 = all vouchers, F9 = all versions,
    then F2 to set the same period as the Settings tab."""
    sender.press("alt+g"); sleep(0.8)
    sender.type_text("EditLogSummary"); sleep(0.8)
    sender.press("Return"); sleep(1.5)
    sender.press("F5"); sleep(0.5)
    sender.press("F9"); sleep(0.8)
    if period:
        sender.press("F2"); sleep(0.8)
        sender.type_text(tally_date(period[0])); sender.press("Return"); sleep(0.4)
        sender.type_text(tally_date(period[1])); sender.press("Return"); sleep(1.2)


# ------------------------------------------------------------------------------------------------ checking a file
def read_export(path: Path) -> pd.DataFrame:
    kind, df = EI.parse_file(path.name, path.read_bytes())
    return df if kind == "summary" else pd.DataFrame()


def check_file(df: pd.DataFrame, item: Item) -> tuple[bool, str]:
    """Is this the voucher type and month that was asked for, with one line per version?"""
    if not len(df):
        return False, "the file has no Edit Log Summary lines (an empty month, or the screen was not what was expected)"
    types = set(df["VoucherType"].astype(str).str.strip()) - {"", "nan"}
    if types and item.vtype not in types:
        return False, f"the file holds {sorted(types)} but {item.vtype} was expected: the screen is out of step"
    d = EI._dt(df["VoucherDate"]).dropna()
    want_m = pd.Timestamp(f"1 {item.month} {item.year}").month
    if len(d) and not ((d.dt.year == item.year) & (d.dt.month == want_m)).all():
        return False, f"vouchers outside {item.month} {item.year} are in the file: the screen is out of step"
    return True, "ok"


def has_versions(df: pd.DataFrame) -> bool:
    return len(df) > 0 and "Version" in df and bool((pd.to_numeric(df["Version"], errors="coerce") >= 1).any())


# ------------------------------------------------------------------------------------------------ the run
def run(plan: list[Item], sender, export_dir: Path, drop_dir: Path, ext: str, state_file: Path, stop_file: Path,
        detailed_toggle: bool = False, escapes_after: int = 2, wait_s: float = 25.0, start_at_types: bool = True,
        sleep=time.sleep, period: tuple[date, date] | None = None) -> dict:
    """Export every item; verify each file; stop at the first problem. Progress is written to state_file (JSON)."""
    export_dir, drop_dir = Path(export_dir), Path(drop_dir)
    drop_dir.mkdir(parents=True, exist_ok=True)
    out = Path(export_dir) / f"Tally{ext}"
    st = {"total": len(plan), "done": 0, "current": "", "status": "running", "message": "", "files": [], "started": time.time()}

    def save():
        state_file.write_text(json.dumps(st))

    save()
    if hasattr(sender, "tally_in_front"):
        st.update(message="Click on the TallyPrime window now (Gateway of Tally, logged in). Starting in 8 seconds…"); save()
        for _ in range(16):
            if sender.tally_in_front():
                break
            sleep(0.5)
    st["message"] = ""
    if not sender.focus_tally():
        st.update(status="stopped", message="Could not bring TallyPrime to the front, so no key was sent. " + getattr(sender, "why", "")
                  + " Click once on the Tally window (logged in, on the Gateway of Tally), then press the button again."); save(); return st
    if start_at_types:
        goto_edit_log_summary(sender, sleep, period)
    for it in plan:
        if stop_file.exists():
            st.update(status="stopped", message="Stopped by you."); save(); return st
        st["current"] = it.key; save()
        if not sender.focus_tally():
            st.update(status="stopped", message=f"Tally lost the keyboard focus before {it.key} (another window came to the front). " + getattr(sender, "why", "") + " "
                      "Nothing more was sent. Close the pop-up, click on Tally and start again."); save(); return st
        t0 = time.time()
        if out.exists():
            out.unlink()
        for step in keys_for(it, detailed_toggle):
            if step[0] == "key":
                sender.press(step[1], step[2] if len(step) > 2 else 1)
            else:
                sleep(step[1])
        ok = False
        while time.time() - t0 < wait_s:
            if out.exists() and out.stat().st_size > 0:
                s1 = out.stat().st_size; sleep(0.6)
                if out.stat().st_size == s1:
                    ok = True; break
            sleep(0.3)
        if not ok:
            st.update(status="stopped", message=f"No export file appeared for {it.key} within {wait_s:.0f} seconds. Check the Tally export folder "
                                                f"({export_dir}) and that Tally shows the vouchers list or the export dialog.")
            save(); return st
        df = read_export(out)
        good, why = check_file(df, it)
        if not good and not detailed_toggle and len(df) and not has_versions(df):
            why = "no version lines: press Alt+F5 on the Tally list to switch to the detailed view"
        if not good:
            keep = drop_dir / f"PROBLEM_{it.filename_stem}{ext}"
            shutil.move(str(out), keep)
            st.update(status="stopped", message=f"{it.key}: {why}. The file was kept as {keep.name}.")
            save(); return st
        dest = drop_dir / f"{it.filename_stem}{ext}"
        shutil.move(str(out), dest)
        st["files"].append(dest.name); st["done"] += 1; save()
        for step in unwind_keys(escapes_after):
            if step[0] == "key":
                sender.press(step[1], step[2] if len(step) > 2 else 1)
            else:
                sleep(step[1])
    st.update(status="finished", message=f"{st['done']} export(s) saved in {drop_dir}.", current=""); save()
    return st


# ------------------------------------------------------------------------------------------------ coverage tracker
def coverage(register: pd.DataFrame | None, log_raw: pd.DataFrame | None, fy_start: date) -> pd.DataFrame:
    """Per voucher type and month: vouchers in the register, vouchers found in the loaded Edit Log files, and a status."""
    rows = {}

    def add(df, col, dcol, tcol):
        if df is None or not len(df):
            return
        d = EI._dt(df[dcol])
        t = df[tcol].astype(str)
        for (ty, y, m), n in pd.DataFrame({"t": t, "y": d.dt.year, "m": d.dt.month}).dropna().groupby(["t", "y", "m"]).size().items():
            rows.setdefault((ty, int(y), int(m)), {"Register": 0, "Edit Log": 0})[col] += int(n)

    add(register, "Register", "VoucherDate", "VoucherType")
    if log_raw is not None and len(log_raw):
        lg = log_raw.copy()
        if "MasterID" in lg:
            lg = lg.drop_duplicates(subset=["MasterID"])
        elif {"VoucherNo", "VoucherType"} <= set(lg):
            lg = lg.drop_duplicates(subset=["VoucherType", "VoucherNo", "VoucherDate"])
        lg = lg[lg["VoucherType"].astype(str).str.strip() != ""]
        add(lg, "Edit Log", "VoucherDate", "VoucherType")
    out = []
    for (ty, y, m), v in sorted(rows.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        r, e = v["Register"], v["Edit Log"]
        stt = "Not exported yet" if e == 0 and r > 0 else ("Complete" if e >= r else "Partly exported") if r > 0 else "In Edit Log only"
        out.append({"Voucher type": ty, "Month": f"{pd.Timestamp(year=y, month=m, day=1):%b-%Y}", "Vouchers in register": r,
                    "Vouchers in Edit Log files": e, "Difference": e - r, "Status": stt})
    return pd.DataFrame(out, columns=["Voucher type", "Month", "Vouchers in register", "Vouchers in Edit Log files", "Difference", "Status"])
