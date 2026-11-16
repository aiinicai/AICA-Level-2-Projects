$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Create the Python 3.12/3.13 .venv and install requirements-dev.txt first. See README.md.' }
& $pythonExe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; build stopped.' }
& $pythonExe scripts/make_icon.py
& $pythonExe scripts/collect_notices.py
& $pythonExe -m PyInstaller --noconfirm FinstockEventScope.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
Write-Output 'Build available at dist\FinstockEventScope\FinstockEventScope.exe. Distribute the complete folder.'

