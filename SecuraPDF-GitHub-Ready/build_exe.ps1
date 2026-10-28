$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Project Python environment not found. Create .venv and install requirements-build.txt first."
}

& $python -m PyInstaller --clean --noconfirm --onefile --windowed `
    --name "SecuraPDF" `
    --icon "pdf_tool\assets\pdf_utility.ico" `
    --add-data "pdf_tool\assets\pdf_utility.ico;pdf_tool\assets" `
    --collect-all pymupdf `
    --collect-all docx `
    --collect-all openpyxl `
    --hidden-import pymupdf.table `
    --hidden-import lxml.etree `
    run_pdf_utility.py

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Write-Output "Built dist\SecuraPDF.exe"
