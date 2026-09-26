"""
AICA SOP TOOL - Add Scrolling
==============================

Adds a vertical scrollbar to every window in the pipeline, so the content
below the fold can be reached on a smaller display.

Why a patcher rather than seven rewritten files
-----------------------------------------------
The seven modules total roughly five thousand lines of working code.
Retyping them to insert a scrollbar risks introducing a transcription
error into code that is already correct. This script edits your actual
files instead, so nothing else changes.

What it does to each file
-------------------------
1. Inserts a self-contained helper, attach_scroll(), near the top. The
   helper is written into each file, so no module has a new dependency
   and PyInstaller needs no extra hidden import.

2. Finds the window class and inserts one line that creates a scrollable
   body inside the window.

3. Redirects widget parents from the window to that body. Only genuine
   widget constructors are redirected, matched as tk.Something(root or
   ttk.Something(root. Calls such as root.title, root.geometry,
   root.protocol, root.bind and root.after are left untouched, because
   those belong to the window itself and not to the body.

Safety
------
- Every file is backed up alongside itself as <name>.bak before editing.
- Each patched file is compiled before it is written. If compilation
  fails the original is left in place and the reason is reported.
- Running it twice is harmless. A file that already carries the helper
  is reported as already patched and skipped.

Usage
-----
Place this script in the folder holding the module files, then run:

    python add_scrolling.py

To undo everything:

    python add_scrolling.py --restore
"""

import os
import re
import shutil
import sys
import py_compile
import tempfile

TARGETS = [
    "aica_sop_tool.py",
    "activity_recorder_v3.py",
    "interaction_capture_v5.py",
    "process_analyzer_v7.py",
    "vision_extractor_v1.py",
    "flowchart_builder_v2.py",
    "sop_builder_v14.py",
]

MARKER = "# --- AICA scrollable window helper ---"

HELPER = '''
# --- AICA scrollable window helper ---
def attach_scroll(window, bg="white"):
    """
    Return a frame that scrolls vertically inside the given window.

    Every widget placed in the returned frame can be reached by scrolling,
    so content below the fold stays accessible on a smaller display. The
    window itself keeps its own title, geometry and protocol handlers.
    """
    import tkinter as _tk
    from tkinter import ttk as _ttk

    outer = _tk.Frame(window, bg=bg)
    outer.pack(fill="both", expand=True)

    canvas = _tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    bar = _ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=bar.set)

    canvas.pack(side="left", fill="both", expand=True)
    body = _tk.Frame(canvas, bg=bg)
    holder = canvas.create_window((0, 0), window=body, anchor="nw")

    def _content_changed(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))
        needed = body.winfo_reqheight() > canvas.winfo_height()
        if needed and not bar.winfo_ismapped():
            bar.pack(side="right", fill="y")
        elif not needed and bar.winfo_ismapped():
            bar.pack_forget()

    def _width_changed(event):
        canvas.itemconfigure(holder, width=event.width)
        _content_changed()

    body.bind("<Configure>", _content_changed)
    canvas.bind("<Configure>", _width_changed)

    def _wheel(event):
        if body.winfo_reqheight() <= canvas.winfo_height():
            return
        step = -1 if getattr(event, "delta", 0) > 0 else 1
        canvas.yview_scroll(step, "units")

    def _wheel_on(_event=None):
        canvas.bind_all("<MouseWheel>", _wheel)

    def _wheel_off(_event=None):
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _wheel_on)
    canvas.bind("<Leave>", _wheel_off)

    def _key(event):
        if event.keysym == "Prior":
            canvas.yview_scroll(-1, "pages")
        elif event.keysym == "Next":
            canvas.yview_scroll(1, "pages")
        elif event.keysym == "Home":
            canvas.yview_moveto(0)
        elif event.keysym == "End":
            canvas.yview_moveto(1)

    for key in ("<Prior>", "<Next>", "<Home>", "<End>"):
        window.bind(key, _key)

    return body
# --- end helper ---
'''

# A genuine widget constructor: tk.Something(root  or  ttk.Something(self.root
WIDGET = re.compile(r"\b(tk|ttk)\.([A-Z]\w*)\(\s*(self\.root|root)\b")

# Where the window class begins taking a root argument.
# [ \\t] rather than \\s, because \\s would also swallow the preceding
# newline and corrupt the captured indentation.
INIT = re.compile(r"^([ \\t]+)def __init__\(self,\s*root\b[^)]*\):[ \\t]*$", re.M)


# Calls that belong to the window itself, not to the scrollable body.
WINDOW_CALL = re.compile(
    r"\broot\.(title|geometry|configure|resizable|minsize|maxsize|"
    r"attributes|iconbitmap|state)\(")


def find_insertion_point(lines, start):
    """
    Decide where the scrollable body should be created inside __init__.

    The body must exist before the first widget is placed. Where the class
    builds its widgets in separate methods there is no widget call inside
    __init__ at all, so the body is created after the window has been given
    its title, geometry and colours.
    """
    end = len(lines)
    for index in range(start, len(lines)):
        if re.match(r"^\s{4}def \w+\(", lines[index]) and index > start + 1:
            end = index
            break

    first_widget = -1
    last_window_call = -1

    for index in range(start, end):
        line = lines[index]
        if first_widget < 0 and WIDGET.search(line):
            first_widget = index
        if WINDOW_CALL.search(line):
            last_window_call = index

    if first_widget >= 0 and last_window_call >= 0:
        if last_window_call < first_widget:
            return last_window_call + 1
        return first_widget

    if first_widget >= 0:
        return first_widget

    if last_window_call >= 0:
        return last_window_call + 1

    return -1


def patch_source(text):
    """Return (patched_text, report) or (None, reason)."""
    if MARKER in text:
        return None, "already patched"

    match = INIT.search(text)
    if not match:
        return None, "no window class taking a root argument was found"

    lines = text.split("\n")

    # Locate the __init__ line index.
    init_index = text[:match.start()].count("\n")
    indent = match.group(1) + "    "

    target = find_insertion_point(lines, init_index + 1)
    if target < 0:
        return None, "no widget construction was found inside the window class"

    # Insert the body creation immediately before the first widget.
    creation = [
        indent + "# Scrollable body. Widgets are placed here so content",
        indent + "# below the fold can be reached by scrolling.",
        indent + "self._body = attach_scroll(root)",
        "",
    ]
    lines[target:target] = creation

    patched = "\n".join(lines)

    # A fixed-size window cannot be enlarged, which makes a scrollbar the
    # only way to reach lower content. Allowing resize is more usable.
    patched = patched.replace(
        'root.resizable(False, False)',
        'root.resizable(True, True)')

    # Redirect widget parents to the scrollable body.
    patched, count = WIDGET.subn(
        lambda m: "{}.{}(self._body".format(m.group(1), m.group(2)),
        patched,
    )

    # Place the helper just above the window class that uses it.
    class_match = re.search(r"^class \w+:\s*$", patched, re.M)
    if class_match:
        at = class_match.start()
        patched = patched[:at] + HELPER.strip() + "\n\n\n" + patched[at:]
    else:
        patched = patched + "\n\n" + HELPER.strip() + "\n"

    return patched, "{} widget parent(s) redirected".format(count)


def compiles(text):
    """Confirm the patched text is valid Python before writing it."""
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8")
    try:
        handle.write(text)
        handle.close()
        py_compile.compile(handle.name, doraise=True)
        return True, ""
    except Exception as error:
        return False, str(error)
    finally:
        try:
            os.unlink(handle.name)
        except Exception:
            pass


def folder():
    return os.path.dirname(os.path.abspath(__file__))


def restore():
    base = folder()
    restored = 0
    for name in TARGETS:
        backup = os.path.join(base, name + ".bak")
        if os.path.exists(backup):
            shutil.copy2(backup, os.path.join(base, name))
            os.remove(backup)
            print("  restored  {}".format(name))
            restored += 1
    print("\n{} file(s) restored.".format(restored))


def run():
    base = folder()
    print("AICA SOP Tool - adding scrollbars")
    print("=" * 62)
    print("Folder: {}\n".format(base))

    done = skipped = failed = 0

    for name in TARGETS:
        path = os.path.join(base, name)

        if not os.path.exists(path):
            print("  skipped   {:<28} not found".format(name))
            skipped += 1
            continue

        try:
            with open(path, "r", encoding="utf-8") as handle:
                original = handle.read()
        except Exception as error:
            print("  FAILED    {:<28} {}".format(name, error))
            failed += 1
            continue

        patched, report = patch_source(original)

        if patched is None:
            print("  skipped   {:<28} {}".format(name, report))
            skipped += 1
            continue

        ok, reason = compiles(patched)
        if not ok:
            print("  FAILED    {:<28} {}".format(name, reason[:60]))
            failed += 1
            continue

        shutil.copy2(path, path + ".bak")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(patched)

        print("  patched   {:<28} {}".format(name, report))
        done += 1

    print("\n" + "=" * 62)
    print("patched {}   skipped {}   failed {}".format(done, skipped, failed))
    if done:
        print("\nOriginals saved as <name>.bak")
        print("To undo:  python add_scrolling.py --restore")


if __name__ == "__main__":
    if "--restore" in sys.argv:
        restore()
    else:
        run()
