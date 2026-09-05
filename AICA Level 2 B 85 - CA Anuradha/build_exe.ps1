# Run this script in PowerShell on Windows to convert launch_app.bat into a standalone .exe

Write-Host "Checking for ps2exe module..." -ForegroundColor Cyan
if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Write-Host "Installing ps2exe module..." -ForegroundColor Yellow
    Install-Module -Name ps2exe -Scope CurrentUser -Force
}

$scriptPath = Join-Path $PSScriptRoot "launch_app.bat"
$outputPath = Join-Path $PSScriptRoot "MaropostDashboard.exe"

Write-Host "Compiling $scriptPath to $outputPath..." -ForegroundColor Green

Invoke-PS2EXE `
    -InputFile $scriptPath `
    -OutputFile $outputPath `
    -title "Maropost India Financial Dashboard" `
    -description "Monthly Cash Requirements and Remittance Authorization" `
    -company "Maropost India" `
    -product "Treasury Management" `
    -version "1.0.0.0"

Write-Host "Done! Generated standalone executable: $outputPath" -ForegroundColor Green
