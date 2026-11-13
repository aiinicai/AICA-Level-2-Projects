# How to Turn This Code into a Standalone Desktop App (.exe)

This package contains everything you need to compile **CA Firm Invoice & Practice Automation Pro** into a standalone Windows executable (`.exe`) that runs on any computer without needing Python or command prompt!

---

## Method 1: 1-Click Automatic Builder (Easiest)

1. Unzip the downloaded folder on your Windows computer.
2. Double-click the file named **`build_exe.bat`**.
3. It will automatically:
   - Check and install `pyinstaller` and dependencies.
   - Embed the custom CA Firm desktop icon (`app_icon.ico`).
   - Hide the black console window so it launches like a native Windows software.
   - Output your standalone executable into:
     ```
     dist\CA_Firm_Invoice_Pro.exe
     ```
4. **Done!** Right-click `CA_Firm_Invoice_Pro.exe` and choose **"Send to -> Desktop (create shortcut)"**. You can now double-click the icon anytime to open your billing app.

---

## Method 2: Manual Command via Terminal / Command Prompt

Open your Command Prompt (CMD) in this folder and run:
```bash
python -m pip install pyinstaller
python build_executable.py
```
Or directly with PyInstaller:
```bash
pyinstaller --noconsole --onefile --icon="app_icon.ico" --name="CA_Firm_Invoice_Pro" ca_firm_invoice_automation_pro.py
```

---

## Method 3: Create a Professional Setup Wizard (Installer)

If you want an installer (`CAFirmBillingSetup.exe`) that installs the software into `C:\Program Files`, creates Start Menu entries, and adds a Desktop icon:
1. Build the `.exe` using Method 1 above (which creates `dist\CA_Firm_Invoice_Pro.exe`).
2. Download and install the free [Inno Setup Compiler](https://jrsoftware.org/isdl.php).
3. Right-click **`installer_setup.iss`** and select **"Compile"**.
4. Inno Setup will output `CAFirmBillingSetup.exe`, which you can share with your partners or staff!
