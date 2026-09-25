param(
    [switch]$Clean,
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "Prepare the production wheelhouse on Windows using the same Python major/minor and architecture as the target PCs."
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$Python = (Get-Command $PythonCommand -ErrorAction Stop).Source
$Wheelhouse = Join-Path $ProjectRoot "wheelhouse"

$Version = & $Python -c "import struct,sys; print(f'{sys.version_info.major}.{sys.version_info.minor}|{struct.calcsize(chr(80))*8}')"
if ($LASTEXITCODE -ne 0) { throw "Could not inspect Python version." }
$Parts = $Version.Trim().Split("|")
if ($Parts[0] -ne "3.14") { throw "Use CPython 3.14.x to prepare the production wheelhouse for Build 15." }
if ($Parts[1] -ne "64") { throw "Use 64-bit Python for the Windows customer build." }

if ($Clean) {
    Remove-Item -Recurse -Force $Wheelhouse -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $Wheelhouse -Force | Out-Null

Write-Host "[1/4] Updating pip tooling used only to prepare the wheelhouse..."
& $Python -m pip install --disable-pip-version-check --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip update failed." }

Write-Host "[2/4] Downloading pinned requirements and all transitive dependencies as wheels..."
& $Python -m pip download --disable-pip-version-check --only-binary=:all: --dest $Wheelhouse -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    throw "Wheel download failed. Do not distribute an incomplete wheelhouse."
}

Write-Host "[3/4] Writing SHA-256 manifest..."
& $Python scripts\verify_wheelhouse.py $Wheelhouse --requirements requirements.txt --write-manifest --skip-resolution
if ($LASTEXITCODE -ne 0) { throw "Wheelhouse manifest creation failed." }

Write-Host "[4/4] Proving that pinned dependencies resolve with internet disabled..."
& $Python scripts\verify_wheelhouse.py $Wheelhouse --requirements requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Offline wheelhouse verification failed." }

Write-Host "Offline wheelhouse is ready: $Wheelhouse"
Write-Host "Copy the entire wheelhouse folder, including SHA256SUMS.txt, with a source installation when offline bootstrap is required."
