param(
    [Parameter(Mandatory = $true)][string]$PublicKeyPath,
    [string]$Wheelhouse = "",
    [string]$InnoSetupCompiler = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "Windows release gating must be executed on a trusted Windows workstation." }

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$SystemPython = (Get-Command python -ErrorAction Stop).Source
& $SystemPython "scripts\validate_python_target.py" --require-windows
if ($LASTEXITCODE -ne 0) { throw "CPython 3.14 x64 release-target validation failed." }
$Version = (& $SystemPython -c "from app import __version__; print(__version__)").Trim()
$EvidenceDir = Join-Path $ProjectRoot "release\evidence"
$Evidence = Join-Path $EvidenceDir "windows_release_evidence.json"
$LogDir = Join-Path $EvidenceDir "logs"
New-Item -ItemType Directory -Force $LogDir | Out-Null
& $SystemPython "scripts\release_evidence.py" init $Evidence --version $Version

$Venv = Join-Path $ProjectRoot ".release-venv"
Remove-Item -Recurse -Force $Venv -ErrorAction SilentlyContinue
& $SystemPython -m venv $Venv
$Python = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Release virtual environment was not created." }

$ResolvedWheelhouse = ""
if ($Wheelhouse) { $ResolvedWheelhouse = (Resolve-Path $Wheelhouse -ErrorAction Stop).Path }
elseif (Test-Path (Join-Path $ProjectRoot "wheelhouse")) { $ResolvedWheelhouse = (Resolve-Path (Join-Path $ProjectRoot "wheelhouse")).Path }

Write-Host "[1/6] Installing pinned dependencies into a fresh Windows release environment..."
if ($ResolvedWheelhouse) {
    & $Python "scripts\verify_wheelhouse.py" $ResolvedWheelhouse --requirements requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Wheelhouse verification failed." }
    & $Python -m pip install --disable-pip-version-check --no-index --find-links $ResolvedWheelhouse -r requirements.txt
} else {
    & $Python -m pip install --disable-pip-version-check -r requirements.txt
}
if ($LASTEXITCODE -ne 0) { throw "Pinned dependency installation failed." }

Write-Host "[2/6] Running the monolithic pytest suite..."
$PytestLog = Join-Path $LogDir "pytest.log"
$Junit = Join-Path $EvidenceDir "pytest-junit.xml"
& $Python -m pytest -q --junitxml=$Junit *>&1 | Tee-Object -FilePath $PytestLog
$PytestExit = $LASTEXITCODE
if ($PytestExit -eq 0) {
    & $Python "scripts\release_evidence.py" set $Evidence windows_pinned_pytest PASS --note "Pinned Windows pytest suite exited 0." --file $PytestLog --file $Junit
} else {
    & $Python "scripts\release_evidence.py" set $Evidence windows_pinned_pytest FAIL --note "Pinned Windows pytest suite failed with exit code $PytestExit." --file $PytestLog --file $Junit
    throw "Pinned pytest release gate failed."
}

Write-Host "[3/6] Building and verifying the PyInstaller customer package..."
$BuildArgs = @("-PublicKeyPath", (Resolve-Path $PublicKeyPath).Path, "-SkipDependencyInstall")
if ($ResolvedWheelhouse) { Copy-Item -Recurse -Force $ResolvedWheelhouse (Join-Path $ProjectRoot "wheelhouse") -ErrorAction SilentlyContinue }
& (Join-Path $PSScriptRoot "build_windows.ps1") @BuildArgs
if ($LASTEXITCODE -ne 0) {
    & $Python "scripts\release_evidence.py" set $Evidence pyinstaller_build FAIL --note "PyInstaller customer build failed."
    throw "PyInstaller customer build failed."
}
$Exe = Join-Path $ProjectRoot "dist\IBCExpert\IBCExpert.exe"
$ReleaseZip = Join-Path $ProjectRoot "release\IBCExpert-Windows.zip"
& $Python "scripts\release_evidence.py" set $Evidence pyinstaller_build PASS --note "PyInstaller onedir customer package built." --file $Exe --file $ReleaseZip

& $Python "scripts\verify_customer_package.py" (Join-Path $ProjectRoot "dist\IBCExpert") --require-executable
if ($LASTEXITCODE -ne 0) {
    & $Python "scripts\release_evidence.py" set $Evidence customer_package_verify FAIL --note "Post-build customer-package verification failed."
    throw "Customer-package verification failed."
}
& $Python "scripts\release_evidence.py" set $Evidence customer_package_verify PASS --note "Customer package verification passed; owner tools/private signing key excluded." --file $Exe

Write-Host "[4/6] Building the Inno Setup installer..."
$InstallerArgs = @()
if ($InnoSetupCompiler) { $InstallerArgs += @("-InnoSetupCompiler", $InnoSetupCompiler) }
& (Join-Path $PSScriptRoot "build_installer.ps1") @InstallerArgs
if ($LASTEXITCODE -ne 0) {
    & $Python "scripts\release_evidence.py" set $Evidence installer_build FAIL --note "Inno Setup installer build failed."
    throw "Installer build failed."
}
$PlainVersion = (& $Python -c "from app import __version__; print(__version__.split('-')[0])").Trim()
$Installer = Join-Path $ProjectRoot "release\IBCExpert-Setup-$PlainVersion.exe"
& $Python "scripts\release_evidence.py" set $Evidence installer_build PASS --note "Inno Setup installer built from verified customer package." --file $Installer

Write-Host "[5/6] Preparing clean-machine acceptance kit..."
$Kit = Join-Path $ProjectRoot "release\clean-windows-acceptance"
Remove-Item -Recurse -Force $Kit -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Kit | Out-Null
Copy-Item $Installer $Kit
Copy-Item "scripts\clean_windows_acceptance.ps1" $Kit
Copy-Item "scripts\clean_windows_acceptance.bat" $Kit
Copy-Item $Evidence (Join-Path $Kit "windows_release_evidence.json")
@'
Run clean_windows_acceptance.bat on a genuinely clean Windows VM/PC using synthetic data only.
Copy the completed windows_release_evidence.json back to release\evidence on the trusted release workstation.
Do not use real client information during acceptance testing.
'@ | Set-Content -Encoding utf8 (Join-Path $Kit "README.txt")

Write-Host "[6/6] Reporting remaining gates..."
# Intentionally BLOCKED: these two must be exercised through the actual first-run bootstrap UI/path,
# not inferred from the successful pip install above.
& $Python "scripts\release_evidence.py" report $Evidence --output (Join-Path $EvidenceDir "WINDOWS_RELEASE_REPORT.md")
& $Python "scripts\release_evidence.py" validate $Evidence
if ($LASTEXITCODE -ne 0) { throw "Evidence file integrity validation failed." }

Write-Host "Release-workstation gates complete. Remaining first-run bootstrap and clean-machine gates require explicit execution."
Write-Host "Acceptance kit: $Kit"
Write-Host "Evidence: $Evidence"
