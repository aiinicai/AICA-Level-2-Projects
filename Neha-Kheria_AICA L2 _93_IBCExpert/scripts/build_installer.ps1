param(
    [string]$InnoSetupCompiler,
    [string]$AppVersion = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "The Windows installer must be built on Windows." }

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$Python = (Get-Command python -ErrorAction Stop).Source
if (-not $AppVersion) {
    $AppVersion = (& $Python -c "from app import __version__; print(__version__.split('-')[0])").Trim()
    if ($LASTEXITCODE -ne 0 -or -not $AppVersion) { throw "Could not determine application version." }
}
$PackageDir = Join-Path $ProjectRoot "dist\IBCExpert"

Write-Host "[1/4] Re-verifying customer package before installer creation..."
& $Python "scripts\verify_customer_package.py" $PackageDir --require-executable
if ($LASTEXITCODE -ne 0) { throw "Customer package verification failed; installer will not be created." }

if (-not $InnoSetupCompiler) {
    $Candidates = @(
        "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $InnoSetupCompiler = $Candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}
if (-not $InnoSetupCompiler -or -not (Test-Path $InnoSetupCompiler)) {
    throw "Inno Setup 6 compiler (ISCC.exe) was not found. Install Inno Setup 6 or pass -InnoSetupCompiler <path>."
}

New-Item -ItemType Directory -Path "release" -Force | Out-Null
Write-Host "[2/4] Building installer from the already verified PyInstaller onedir package..."
$SourceDefine = "/DSourceDir=$PackageDir"
$OutputDefine = "/DOutputDir=$(Join-Path $ProjectRoot 'release')"
$VersionDefine = "/DAppVersion=$AppVersion"
& $InnoSetupCompiler $SourceDefine $OutputDefine $VersionDefine "packaging\installer\IBCExpert.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }

$Installer = Join-Path $ProjectRoot "release\IBCExpert-Setup-$AppVersion.exe"
if (-not (Test-Path $Installer)) { throw "Expected installer was not created: $Installer" }

Write-Host "[3/4] Hashing installer..."
$InstallerHash = (Get-FileHash $Installer -Algorithm SHA256).Hash.ToLowerInvariant()
$Manifest = Join-Path $ProjectRoot "release\SHA256SUMS.txt"
$Existing = @()
if (Test-Path $Manifest) { $Existing = Get-Content $Manifest | Where-Object { $_ -notmatch "IBCExpert-Setup-" } }
@($Existing + "$InstallerHash  $(Split-Path $Installer -Leaf)") | Set-Content -Encoding ascii $Manifest

Write-Host "[4/4] Installer build completed."
Write-Host "Installer: $Installer"
Write-Host "This installer contains only the previously verified customer package."
