# Builds dist\TallyMIS.exe (one file). Run from the project folder:  powershell -File tools\build_exe.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path app\static\index.html)) { Push-Location web; npm install; npm run build; Pop-Location }
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name TallyMIS `
  --add-data "app\static;app\static" --add-data "app\demo_data;app\demo_data" `
  --collect-all webview --collect-all pythonnet --collect-all clr_loader `
  --collect-binaries duckdb --collect-submodules uvicorn --hidden-import duckdb --hidden-import pyarrow `
  --exclude-module pandas --exclude-module numpy.testing --exclude-module tkinter --exclude-module matplotlib `
  tally_mis.py
Write-Host "Built: dist\TallyMIS.exe"
