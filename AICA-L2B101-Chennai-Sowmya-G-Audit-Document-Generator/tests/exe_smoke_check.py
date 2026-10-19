# Smoke test, run by GitHub Actions on the packed (frozen) program.
# Reads the sample master data PDF, fills the window, generates all four
# documents and fails the build if anything is missing.
import glob
import os
import sys
import tkinter as tk

import desktop_app as app

problems = []
print("frozen:", getattr(sys, "frozen", False))
if not app.default_logo():
    problems.append("logo not bundled")

found, _ = app.extract_master_data(sys.argv[1])
print("company:", found["company"], "| address:", found["address"])
print("directors:", found["directors"])
if not found["address"] or "books" in found["address"].lower():
    problems.append("registered office not read correctly")
if len(found["directors"]) < 2:
    problems.append("directors not read")

messages = []
for name in ("showinfo", "showwarning", "showerror"):
    setattr(app.messagebox, name, lambda title, text, n=name: messages.append(n + ": " + text))
app.messagebox.askyesno = lambda *a, **k: False
app.filedialog.askopenfilename = lambda **k: sys.argv[1]

root = tk.Tk()
gui = app.GeneratorApp(root)
gui.load_from_pdf()
gui.vars["frn"].set("012345S")
gui.vars["membership"].set("234567")
gui.generate()
root.destroy()
print("\n".join(messages))

files = glob.glob(os.path.join(app.OUTPUT_FOLDER, "*", "*.docx"))
print("documents:", [os.path.basename(f) for f in files])
if len(files) != 4:
    problems.append("expected 4 documents, got " + str(len(files)))

if problems:
    print("FAILED:", "; ".join(problems))
    sys.exit(1)
print("PASSED")
