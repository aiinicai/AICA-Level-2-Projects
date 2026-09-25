param(
    [Parameter(Mandatory = $true)]
    [string]$PublicKeyPath,
    [switch]$SkipDependencyInstall,
    [switch]$BuildInstaller,
    [string]$InnoSetupCompiler
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "IBC Expert customer packaging must be performed on Windows."
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
$Python = (Get-Command python -ErrorAction Stop).Source
& $Python "scripts\validate_python_target.py" --require-windows
if ($LASTEXITCODE -ne 0) { throw "CPython 3.14 x64 release-target validation failed." }
$ResolvedPublicKey = (Resolve-Path $PublicKeyPath -ErrorAction Stop).Path

Write-Host "[1/7] Validating public licence verification key..."
& $Python "scripts\validate_public_key.py" $ResolvedPublicKey
if ($LASTEXITCODE -ne 0) { throw "Public key validation failed." }

$Wheelhouse = Join-Path $ProjectRoot "wheelhouse"
$HasWheels = (Test-Path $Wheelhouse) -and ((Get-ChildItem $Wheelhouse -File -ErrorAction SilentlyContinue).Count -gt 0)
if ($HasWheels) {
    Write-Host "[2/7] Verifying offline wheelhouse hashes and dependency resolution..."
    & $Python "scripts\verify_wheelhouse.py" $Wheelhouse --requirements requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Offline wheelhouse verification failed." }
} else {
    Write-Host "[2/7] No wheelhouse selected; build may use the internet package index for dependency setup."
}

if (-not $SkipDependencyInstall) {
    Write-Host "[3/7] Installing pinned build/runtime dependencies..."
    if ($HasWheels) {
        & $Python -m pip install --disable-pip-version-check --no-index --find-links $Wheelhouse -r requirements.txt
    } else {
        & $Python -m pip install --disable-pip-version-check -r requirements.txt
    }
    if ($LASTEXITCODE -ne 0) { throw "Pinned dependency installation failed." }
} else {
    Write-Host "[3/7] Dependency installation skipped by request."
}

Write-Host "[4/7] Cleaning previous customer package output..."
Remove-Item -Recurse -Force "build\IBCExpert" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "dist\IBCExpert" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "release" -Force | Out-Null

Write-Host "[5/7] Building PyInstaller onedir customer package..."
$env:IBC_EXPERT_PUBLIC_KEY = $ResolvedPublicKey
try {
    & $Python -m PyInstaller --clean --noconfirm "packaging\IBCExpert.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
} finally {
    Remove-Item Env:IBC_EXPERT_PUBLIC_KEY -ErrorAction SilentlyContinue
}

Write-Host "[6/7] Verifying owner/private-key exclusion and customer package contents..."
& $Python "scripts\verify_customer_package.py" "dist\IBCExpert" --require-executable
if ($LASTEXITCODE -ne 0) { throw "Customer package security verification failed." }

Write-Host "[7/7] Creating release archive and SHA-256 manifest..."
$Archive = Join-Path $ProjectRoot "release\IBCExpert-Windows.zip"
Remove-Item -Force $Archive -ErrorAction SilentlyContinue
Compress-Archive -Path "dist\IBCExpert\*" -DestinationPath $Archive -CompressionLevel Optimal
$ExeHash = (Get-FileHash "dist\IBCExpert\IBCExpert.exe" -Algorithm SHA256).Hash.ToLowerInvariant()
$ZipHash = (Get-FileHash $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
@(
    "$ExeHash  IBCExpert.exe",
    "$ZipHash  IBCExpert-Windows.zip"
) | Set-Content -Encoding ascii "release\SHA256SUMS.txt"

Write-Host "Customer build completed successfully."
Write-Host "Package folder: $ProjectRoot\dist\IBCExpert"
Write-Host "Release archive: $Archive"
Write-Host "Owner tools/private signing keys were not packaged."

if ($BuildInstaller) {
    Write-Host "Building Windows installer from the verified customer package..."
    $InstallerArgs = @()
    if ($InnoSetupCompiler) { $InstallerArgs += @("-InnoSetupCompiler", $InnoSetupCompiler) }
    & (Join-Path $PSScriptRoot "build_installer.ps1") @InstallerArgs
    if ($LASTEXITCODE -ne 0) { throw "Installer build failed." }
}
