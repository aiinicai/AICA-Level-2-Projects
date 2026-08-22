# Income Tax Calculator — Tax Comp
**FY 2025-26 / FY 2026-27 | Old Regime vs New Regime**

---

## Files Required

| File | Purpose |
|------|---------|
| `IncomeTaxCalculator_SB.html` | The calculator (all logic inside) |
| `launcher.py` | Python script to open it as a desktop app |

Both files must be in the **same folder**.

---

## Step 1 — Install Python

Download from: https://www.python.org/downloads/

> During installation, tick **"Add Python to PATH"** — very important.

---

## Step 2 — Install Required Packages

Open **Command Prompt** and run:

```
pip uninstall pywebview -y
pip install pywebview==4.4.1
pip install pyinstaller
```

---

## Step 3 — Navigate to Your Folder

In Command Prompt:

```
cd C:\Users\YourName\Desktop\TaxCalculator
```

Replace the path with wherever you saved your files.

To verify both files are present:

```
dir
```

You should see `launcher.py` and `IncomeTaxCalculator_SB.html` listed.

---

## Step 4 — Test Before Building (Important)

Run this first to confirm everything works:

```
python launcher.py
```

If a clean app window opens → proceed to Step 5.

If you get an error, run:

```
pip install pythonnet
```

Then try again.

---

## Step 5 — Build the EXE

Paste this single line into CMD and press Enter:

```
pyinstaller --onefile --windowed --name "IncomeTaxCalculator_SB" --add-data "IncomeTaxCalculator_SB.html;." --hidden-import "webview" --hidden-import "webview.platforms.winforms" --hidden-import "clr" --collect-all "webview" launcher.py
```

Wait 2–3 minutes for it to finish.

---

## Step 6 — Get Your EXE

After the build completes, open the `dist` folder that was created:

```
📁 YourFolder\
   📁 dist\
      IncomeTaxCalculator_SB.exe   ← Your app
   📁 build\                        ← Can delete
   IncomeTaxCalculator_SB.spec      ← Can delete
   launcher.py
   IncomeTaxCalculator_SB.html
```

The `IncomeTaxCalculator_SB.exe` is your standalone app.
Copy it anywhere, share with anyone — no Python needed on their machine.

---

## launcher.py (Full Code)

```python
import webview
import os
import sys


def resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


html_file = resource_path('IncomeTaxCalculator_SB.html')
url = 'file:///' + html_file.replace('\\', '/')

webview.create_window(
    title='Income Tax Calculator | Tax Comp',
    url=url,
    width=1280,
    height=800,
    resizable=True,
    min_size=(900, 600),
)

webview.start()
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'webview'` | Run `pip install pywebview==4.4.1` then rebuild |
| `script file py don't exist` | You are not in the right folder. Use `cd` to navigate first |
| `No module named 'clr'` | Run `pip install pythonnet` then rebuild |
| App opens but shows blank | HTML file not found — ensure both files are in same folder |
| Build fails halfway | Delete `dist`, `build`, `.spec` and rebuild |

---

## Clean Rebuild (if needed)

If anything goes wrong, clean everything and start fresh:

```
rmdir /s /q dist
rmdir /s /q build
del IncomeTaxCalculator_SB.spec
```

Then run the pyinstaller command in Step 5 again.

---

## Notes

- EXE size will be approximately 15–25 MB
- Works on Windows 10 and Windows 11
- No internet connection required
- Prepared by: **Tax Comp**,  | 
