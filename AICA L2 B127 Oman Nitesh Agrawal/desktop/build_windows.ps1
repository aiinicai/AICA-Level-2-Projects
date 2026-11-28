# PowerShell one-click builder for RealEstate360.exe, Portable ZIP, Setup.exe, and Update.exe
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "1. Installing PySide6 & PyInstaller..."
python -m pip install --upgrade pip
python -m pip install pyside6 pyinstaller

if (-not (Test-Path "Prerequisites")) { New-Item -ItemType Directory -Path "Prerequisites" | Out-Null }
if (-not (Test-Path "output")) { New-Item -ItemType Directory -Path "output" | Out-Null }

Write-Host "2. Packaging RealEstate360.exe..."
python -m PyInstaller --noconfirm --clean RealEstate360.spec

Write-Host "3. Creating RealEstate360_Portable.zip..."
Compress-Archive -Path "dist\RealEstate360\*" -DestinationPath "output\RealEstate360_Portable.zip" -Force

$isccCandidates = @(
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($iscc) {
  Write-Host "4. Compiling RealEstate360_Setup.exe & RealEstate360_Update.exe..."
  & $iscc "RealEstate360_Setup.iss"
  & $iscc "RealEstate360_Update.iss"
  Write-Host "Build Complete! Artifacts in desktop\output\ and desktop\dist\RealEstate360\"
} else {
  Write-Warning "Inno Setup 6 (ISCC.exe) not found. RealEstate360.exe and RealEstate360_Portable.zip created in desktop\dist\RealEstate360\ and desktop\output\."
}
