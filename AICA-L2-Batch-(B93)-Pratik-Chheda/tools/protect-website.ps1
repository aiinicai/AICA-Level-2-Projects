# Creates the protected website copy of the tracker in "DealFlow_Tracker_Website".
# Asks for the first admin's username, name and password; the password is used once to
# lock the data key and is never saved.
$ErrorActionPreference = 'Stop'
$tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $tools
$app = Join-Path $root 'tracker\app'
$out = Join-Path $root 'dist-website'

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js is needed on this computer (nodejs.org)' }

Write-Host 'Protected website copy of the Sample Advisory tracker' -ForegroundColor Yellow
Write-Host 'This creates the first ADMIN login. More users are added later inside the tracker (Users and access).'
Write-Host ''
$user = (Read-Host 'Admin username (for example pc)').Trim().ToLower()
$name = (Read-Host 'Admin full name').Trim()
function Plain($s) { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)) }
while ($true) {
  $p1 = Plain (Read-Host 'Admin password, at least 10 characters (not shown)' -AsSecureString)
  $p2 = Plain (Read-Host 'Repeat the password' -AsSecureString)
  if ($p1.Length -lt 10) { Write-Host 'Too short, use at least 10 characters.' -ForegroundColor Yellow; continue }
  if ($p1 -ne $p2) { Write-Host 'The two passwords do not match.' -ForegroundColor Yellow; continue }
  break
}

New-Item -ItemType Directory -Force $out | Out-Null
$env:DF_ADMIN_USER = $user; $env:DF_ADMIN_NAME = $name; $env:DF_ADMIN_PASS = $p1
try {
  & node (Join-Path $tools 'protect.js') (Join-Path $app 'index.html') (Join-Path $out 'index.html')
  if ($LASTEXITCODE -ne 0) { throw 'Protection failed' }
} finally {
  Remove-Item Env:DF_ADMIN_PASS -ErrorAction SilentlyContinue; $p1 = $null; $p2 = $null
}

Copy-Item (Join-Path $app 'config.json') $out -Force
Copy-Item (Join-Path $app 'icons') $out -Recurse -Force
$manifest = [IO.File]::ReadAllText((Join-Path $app 'manifest.webmanifest')).Replace('"theme_color": "#0E5E54"', '"theme_color": "#0B1F3A"').Replace('"background_color": "#F6F8FA"', '"background_color": "#0B1F3A"')
[IO.File]::WriteAllText((Join-Path $out 'manifest.webmanifest'), $manifest, (New-Object Text.UTF8Encoding $false))
$sw = [IO.File]::ReadAllText((Join-Path $app 'sw.js')) -replace "df-tracker-v\d+", 'df-tracker-v3'
[IO.File]::WriteAllText((Join-Path $out 'sw.js'), $sw, (New-Object Text.UTF8Encoding $false))

Write-Host ''
Write-Host 'Done. Upload EVERYTHING in this folder to the tracker folder on the website:' -ForegroundColor Green
Write-Host "  $out"
Write-Host 'Then sign in with the admin username and password you just chose.'
