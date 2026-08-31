# Installation Guide

This covers three separate audiences - pick the section you need:

1. **[Run from source for development](#1-run-from-source-for-development)**
   - you have Python/Node installed and want to run/modify the code
2. **[Build the Windows installer (TallyConverterSetup.exe)](#2-build-the-windows-installer)**
   - you want to produce the .exe to hand to end users
3. **[Install the finished app as an end user](#3-installing-as-an-end-user)**
   - you just received TallyConverterSetup.exe from someone else

---

## 1. Run from source for development

### 1.1 Install prerequisites

| Tool | Version | Download |
|---|---|---|
| Python | 3.12 | https://www.python.org/downloads/ (check "Add to PATH" during install) |
| Node.js | LTS (20.x) | https://nodejs.org/ |
| Tesseract OCR | latest | https://github.com/UB-Mannheim/tesseract/wiki (Windows installer) |

On Windows, the Tesseract installer defaults to
`C:\Program Files\Tesseract-OCR\tesseract.exe` - the app auto-detects
this path, so you don't need to configure anything unless you install
it somewhere else (in which case set the path in Settings once the
app is running).

### 1.2 Backend setup

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

If you're on Linux/Mac for development, `pip install` may need
`--break-system-packages` depending on your Python install:
```bash
pip install -r requirements.txt --break-system-packages
```

Run the tests to confirm everything installed correctly:
```bash
pytest tests -v
```

Generate the sample data files (used by the tests and for trying out
the app):
```bash
cd ../sample_data
python generate_samples.py
cd ../backend
```

Start the backend:
```bash
python run.py
```

This starts the API on `http://127.0.0.1:8000` (or the next available
port up to 8050) and opens your browser automatically. Database and
files are stored in `./data/` during development.

### 1.3 Frontend setup (only needed if you're editing the UI)

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

This starts a Vite dev server (typically `http://127.0.0.1:5173`) that
proxies `/api` calls to the backend on port 8000. For day-to-day use
of the *built* app, you don't need this - `python run.py` alone serves
the production frontend build once you've run `npm run build` at
least once (see below).

---

## 2. Build the Windows installer

This must be done **on a Windows machine** - PyInstaller and Inno
Setup both produce Windows-native output.

### 2.1 Install build tools (Windows machine)

1. Python 3.12 - https://www.python.org/downloads/ (check "Add to PATH")
2. Node.js LTS - https://nodejs.org/
3. Tesseract OCR - https://github.com/UB-Mannheim/tesseract/wiki
   - Install to the default path (`C:\Program Files\Tesseract-OCR`) so
     `build_windows.bat` can bundle it automatically into the
     installer. If you skip this, the installer will still work, but
     end users will need to install Tesseract separately.
4. Inno Setup 6 - https://jrsoftware.org/isdl.php
   - After installing, either add its folder to your PATH, or note
     the path to `iscc.exe` (typically
     `C:\Program Files (x86)\Inno Setup 6\iscc.exe`) to run manually.

### 2.2 Run the build script

From the project root (in Command Prompt or PowerShell):
```powershell
build_windows.bat
```

This will, in order:
1. Build the React frontend (`npm install && npm run build`)
2. Create a Python virtual environment and install requirements
3. **Run the full test suite** - the build stops here if any test fails
4. Package everything with PyInstaller into `dist\TallyConverter\`
5. Check whether Tesseract got bundled
6. Compile the installer with Inno Setup

If everything succeeds, you'll find the finished installer at:
```
installer\output\TallyConverterSetup.exe
```

### 2.3 Manual steps (if you prefer not to use the .bat file)

```powershell
cd frontend
npm install
npm run build
cd ..\backend
python -m venv build_venv
build_venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pytest tests -v
cd ..
pyinstaller TallyConverter.spec --noconfirm --clean
iscc installer\installer.iss
```

### 2.4 Testing the packaged app

Before shipping the installer to anyone:
1. Run `dist\TallyConverter\TallyConverter.exe` directly and confirm
   the browser opens and the app works.
2. Run the installer itself (`installer\output\TallyConverterSetup.exe`)
   on a clean Windows machine or VM if possible - this catches missing
   DLLs or files that happened to exist on your dev machine but
   wouldn't on a customer's machine.
3. **Test the generated Tally XML against a real TallyPrime test
   company** before trusting it with real books - see the warning in
   [README.md](README.md).

---

## 3. Installing as an end user

1. Double-click `TallyConverterSetup.exe`.
2. Follow the installer prompts. Administrator rights are required
   (it installs to `C:\Program Files`).
3. Optionally check "Create Desktop Icon" and/or "Launch after
   installation."
4. Once installed, launch **Tally Converter** from the Start Menu or
   Desktop. It opens automatically in your default web browser.
5. If Tesseract wasn't bundled with your installer, you'll see a
   notice on the Settings page - install it from
   https://github.com/UB-Mannheim/tesseract/wiki and the app will
   detect it automatically.

Your data is stored at `C:\ProgramData\TallyConverter\` and is
preserved across upgrades/reinstalls (uninstalling does not delete
it - see USER_GUIDE.md for how to fully remove it if you want to).

See [USER_GUIDE.md](USER_GUIDE.md) for how to use the app day to day.
