$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "First-time setup: creating a virtual environment and installing dependencies..."
    Write-Host "(this only happens once, and may take a minute or two)"
    py -m venv "$PSScriptRoot\.venv"
    & $venvPython -m pip install --upgrade pip -q
    & $venvPython -m pip install -r "$PSScriptRoot\requirements.txt" -q
    Write-Host "Setup complete."
    Write-Host ""
}

$tesseract = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (Test-Path $tesseract) {
    $env:TESSERACT_CMD = $tesseract
} else {
    Write-Host "NOTE: Tesseract-OCR was not found at the default install location."
    Write-Host "Scanned/photographed invoices will be flagged for manual review instead of OCR'd."
    Write-Host "See README.md for the installer link."
    Write-Host ""
}

Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://127.0.0.1:5000"
} | Out-Null

Write-Host "Starting the app - your browser will open automatically in a couple of seconds."
Write-Host "Leave this window open while you use the app. Press Ctrl+C here to stop it."
Write-Host ""

& $venvPython "$PSScriptRoot\app.py"
