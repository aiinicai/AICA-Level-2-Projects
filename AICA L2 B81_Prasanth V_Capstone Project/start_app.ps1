Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   ASSET TAGGING & LABEL MANAGEMENT SYSTEM (ENTERPRISE v1.0)" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting Asset Tagging Server at http://localhost:8000 ..." -ForegroundColor Green
Write-Host "Database: SQLite WAL Mode" -ForegroundColor Gray
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$scriptDir\launcher.py"
