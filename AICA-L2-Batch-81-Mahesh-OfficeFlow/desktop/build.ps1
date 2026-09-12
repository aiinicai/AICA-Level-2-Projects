# Builds the OfficeFlow desktop client from the single source page.
#
#   desktop/officeflow.html   <- the ONLY file to edit
#     -> desktop/OfficeFlowDesktop.cs   (generated: page embedded as base64)
#     -> desktop/OfficeFlow.exe         (self-contained launcher, hand this to staff)
#     -> public/index.html              (same page, for `firebase deploy --only hosting`)
#
# Run:  powershell -ExecutionPolicy Bypass -File desktop\build.ps1

$ErrorActionPreference = "Stop"
$dir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $dir

$source = Join-Path $dir "officeflow.html"
if (-not (Test-Path $source)) { throw "Missing $source" }

$html = [System.IO.File]::ReadAllText($source)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# 1. Generate the C# with the page embedded, so the EXE is a single self-contained file.
$generatedCs = Join-Path $dir "OfficeFlowDesktop.cs"
$exePath     = Join-Path $dir "OfficeFlow.exe"

$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($html))
$tpl = [System.IO.File]::ReadAllText((Join-Path $dir "OfficeFlowDesktop.cs.template"))
[System.IO.File]::WriteAllText($generatedCs, $tpl.Replace("__HTML_BASE64__", $b64), $utf8NoBom)

# 2. Compile. Paths go in variables first: PowerShell does not expand a parenthesised
# expression into an argument for a native command.
$csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path $csc)) { $csc = "C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe" }
if (-not (Test-Path $csc)) { throw "No C# compiler found. Install the .NET Framework 4 developer tools." }

& $csc /nologo /target:exe /platform:anycpu /optimize "/out:$exePath" $generatedCs
if ($LASTEXITCODE -ne 0) { throw "Compilation failed." }

# 3. Publish the same page for Firebase Hosting, so the browser and desktop builds never drift.
$publicDir = Join-Path $root "public"
if (-not (Test-Path $publicDir)) { New-Item -ItemType Directory -Path $publicDir | Out-Null }
[System.IO.File]::WriteAllText((Join-Path $publicDir "index.html"), $html, $utf8NoBom)

Write-Host "Built:"
Write-Host ("  {0}  ({1:N0} KB)" -f $exePath, ((Get-Item $exePath).Length / 1KB))
Write-Host ("  {0}" -f (Join-Path $publicDir "index.html"))
