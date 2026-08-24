# Building PDF Studio Pro as a standalone .exe

## What you're doing
Turning `pdf_studio_pro_v2.py` into one `.exe` file. You build it once, on
one Windows PC that has Python — then that `.exe` runs on any teammate's
Windows PC with **no Python install needed there**.

## Files in this kit
- `requirements-build.txt` — the packages needed to build (same libraries
  your script already uses, plus `pyinstaller`)
- `pdf_studio_pro.spec` — build configuration, already tuned for the
  trickier dependencies in your script (pyhanko, cryptography, scipy)
- `build.bat` — runs all the steps below automatically

## Steps

1. On a Windows PC with Python 3.9+ installed, put these files in the
   **same folder** as `pdf_studio_pro_v2.py`:
   - `requirements-build.txt`
   - `pdf_studio_pro.spec`
   - `build.bat`

2. Double-click `build.bat`. It will:
   - Create a clean virtual environment (`build_env`)
   - Install all dependencies
   - Run PyInstaller using the spec file
   - This takes 5-15 minutes and the window will show a lot of scrolling
     text — that's normal.

3. When it finishes, find **`dist\PDF Studio Pro.exe`**. That's the file
   to distribute. It will be roughly 150-200 MB — this is expected,
   because scipy and PyMuPDF are bundled inside it (single-file mode
   packs everything into one .exe).

4. Copy that one `.exe` to a shared drive or send it to teammates. They
   double-click it and the app opens — same as running the Python script
   does for you today, no install step for them.

## Things to expect / troubleshoot

- **First launch is slow (5-15 seconds).** A one-file .exe unpacks itself
  into a temp folder every time it starts. This is normal for
  `--onefile` builds. If it bothers your team, PyInstaller can build a
  "one-folder" version instead (`--onedir` instead of the packed exe) —
  starts faster but you distribute a folder instead of a single file.
  Ask me if you want that version instead.

- **Windows SmartScreen / antivirus warning on first run.** Unsigned
  .exe files from an unrecognized publisher often trigger a "Windows
  protected your PC" prompt. This is not a bug — it's because the file
  isn't digitally code-signed. Team members click "More info" → "Run
  anyway" the first time. To make this warning go away permanently, the
  firm would need to buy a code-signing certificate — not necessary for
  internal-only use.

- **"Missing DLL" error on a teammate's PC.** Almost always means that
  PC is missing the Microsoft Visual C++ Redistributable (needed by
  numpy/scipy). It's a free, tiny installer from Microsoft — search
  "Visual C++ Redistributable x64" — a one-time fix per PC, unrelated to
  Python.

- **Rebuilding after you edit the script.** Just re-run `build.bat`
  again — it rebuilds from scratch each time (delete the `build` and
  `dist` folders first if you want a fully clean rebuild).

## Note on this build kit
The spec file was tested against your exact script and dependency list
in a sandbox to confirm the import graph resolves cleanly (PyMuPDF,
pyhanko, cryptography, scipy all included without errors). That test ran
on Linux purely to validate imports — the real Windows `.exe` still needs
to be built by you on Windows, since PyInstaller doesn't cross-compile.
