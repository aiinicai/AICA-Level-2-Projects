# Downloads a portable Node.js (LTS 22.x) into the app's "runtime\node" folder.
# No administrator rights and no system-wide install required.
param([Parameter(Mandatory = $true)][string]$Dest)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

$arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x64' }
$runtimeDir = Split-Path $Dest -Parent
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

# Find the newest Node 22 LTS build (falls back to a known version if the lookup fails)
$base = 'https://nodejs.org/dist/latest-v22.x/'
$file = $null; $hash = $null
try {
  $sums = (Invoke-WebRequest -UseBasicParsing -Uri ($base + 'SHASUMS256.txt')).Content
  $line = ($sums -split "`n") | Where-Object { $_ -match "node-v[\d\.]+-win-$arch\.zip\s*$" } | Select-Object -First 1
  $parts = $line.Trim() -split '\s+'
  $hash = $parts[0]; $file = $parts[1]
} catch {}
if (-not $file) { $base = 'https://nodejs.org/dist/v22.12.0/'; $file = "node-v22.12.0-win-$arch.zip" }

$zip = Join-Path $runtimeDir $file
Write-Host "      Downloading $file (about 30 MB)..."
Invoke-WebRequest -UseBasicParsing -Uri ($base + $file) -OutFile $zip

if ($hash) {
  $actual = (Get-FileHash -Algorithm SHA256 -Path $zip).Hash
  if ($actual -ne $hash.ToUpper()) { Remove-Item $zip -Force; throw 'Downloaded file is corrupted (checksum mismatch). Please run again.' }
}

Write-Host '      Extracting...'
$extract = Join-Path $runtimeDir '_extract'
if (Test-Path $extract) { Remove-Item $extract -Recurse -Force }
New-Item -ItemType Directory -Force -Path $extract | Out-Null
$tar = Join-Path $env:SystemRoot 'System32\tar.exe'
if (Test-Path $tar) { & $tar -xf $zip -C $extract }
if (-not (Get-ChildItem $extract -Directory)) { Expand-Archive -Path $zip -DestinationPath $extract -Force }

$inner = Get-ChildItem $extract -Directory | Select-Object -First 1
if (Test-Path $Dest) { Remove-Item $Dest -Recurse -Force }
Move-Item -Path $inner.FullName -Destination $Dest
Remove-Item $zip, $extract -Recurse -Force -ErrorAction SilentlyContinue
if (-not (Test-Path (Join-Path $Dest 'node.exe'))) { throw 'node.exe not found after extraction.' }
Write-Host '      Portable Node.js installed.'
