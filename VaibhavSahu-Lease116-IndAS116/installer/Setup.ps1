<#
  Lease116 - one-time setup for Windows (x64 and ARM64)

  * Finds a suitable 64-bit Python 3.10-3.13 (x64 preferred: every OCR / computer-vision wheel exists for it;
    on Windows-on-ARM it runs under the built-in x64 emulation).
  * If none is found, installs Python 3.12 (x64, per-user) with winget.
  * Creates a private environment in %LOCALAPPDATA%\Lease116\venv and installs the packages.
  * Creates Desktop and Start-menu shortcuts.
  Safe to re-run: it repairs / upgrades the environment. Use -Rebuild to recreate it from scratch.
  Log: %LOCALAPPDATA%\Lease116\setup.log
#>
param([switch]$Rebuild, [switch]$SkipOCR, [switch]$NoShortcut, [switch]$NoWinget)

$ErrorActionPreference = 'Continue'
$AppDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Base = Join-Path $env:LOCALAPPDATA 'Lease116'
$Venv = Join-Path $Base 'venv'
$VPy = Join-Path $Venv 'Scripts\python.exe'
New-Item -ItemType Directory -Force -Path $Base | Out-Null
$Log = Join-Path $Base 'setup.log'
try { Start-Transcript -Path $Log -Append | Out-Null } catch { }

function Say([string]$msg, [string]$color = 'Gray') { Write-Host $msg -ForegroundColor $color }

function Probe([string]$exe, [string[]]$pre) {
    $code = "import sys,platform,struct;print('%d.%d|%s|%d|%s' % (sys.version_info[0],sys.version_info[1],platform.machine(),struct.calcsize('P')*8,sys.executable))"
    try {
        # stdin is closed (piped $null) so a launcher that asks a question can never wait for input
        $out = $null | & $exe @pre -c $code 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            $p = ([string]($out | Select-Object -Last 1)).Split('|')
            if ($p.Count -ge 4) {
                return [pscustomobject]@{ Ver = [version]$p[0]; Machine = $p[1].ToUpper(); Bits = [int]$p[2]; Exe = $p[3].Trim() }
            }
        }
    } catch { }
    return $null
}

function Find-Pythons {
    $found = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($t in @('-3.12-64', '-3.11-64', '-3.10-64', '-3.13-64', '-3.12-arm64', '-3.11-arm64', '-3.13-arm64', '-3')) {
            $i = Probe 'py' @($t)
            if ($i) { $found += $i }
        }
    }
    # classic installer (per-user / all-users) and the new Python install manager (pythoncore-<tag>)
    $dirs = @()
    foreach ($r in @((Join-Path $env:LOCALAPPDATA 'Programs\Python'), $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if ($r -and (Test-Path $r)) { $dirs += Get-ChildItem $r -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue }
    }
    $pm = Join-Path $env:LOCALAPPDATA 'Python'
    if (Test-Path $pm) { $dirs += Get-ChildItem $pm -Directory -Filter 'pythoncore-3*' -ErrorAction SilentlyContinue }
    foreach ($d in $dirs) {
        $exe = Join-Path $d.FullName 'python.exe'
        if (Test-Path $exe) { $i = Probe $exe @(); if ($i) { $found += $i } }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike '*WindowsApps*') { $i = Probe $cmd.Source @(); if ($i) { $found += $i } }
    return $found
}

# The offline OCR stack (RapidOCR) supports Python 3.10 - 3.12 and ships x64 wheels only, so x64 3.12 is ideal.
function Rank($c) {
    $r = 0
    if ($c.Machine -eq 'AMD64') { $r += 100 }
    switch ("$($c.Ver.Major).$($c.Ver.Minor)") { '3.12' { $r += 40 } '3.11' { $r += 30 } '3.10' { $r += 20 } '3.13' { $r += 10 } }
    return $r
}
function Is-Ideal($c) { return ($c -and $c.Machine -eq 'AMD64' -and $c.Ver -ge [version]'3.10' -and $c.Ver -lt [version]'3.13') }

function Pick-Python([string]$maxExclusive = '3.14') {
    $ok = @(Find-Pythons | Where-Object { $_.Bits -eq 64 -and $_.Ver -ge [version]'3.10' -and $_.Ver -lt [version]$maxExclusive })
    if ($ok.Count -eq 0) { return $null }
    return ($ok | Sort-Object Exe -Unique | Sort-Object @{ Expression = { Rank $_ }; Descending = $true } | Select-Object -First 1)
}

Say ''
Say '  Lease116 setup' 'Cyan'
Say "  Application folder : $AppDir"
Say "  Environment        : $Venv"
Say "  Windows            : $([Environment]::OSVersion.VersionString)  ($env:PROCESSOR_ARCHITECTURE)"
Say ''

$py = Pick-Python
if (-not (Is-Ideal $py) -and -not $NoWinget -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    if ($py) { Say "  Found Python $($py.Ver) ($($py.Machine)) - installing Python 3.12 (x64) for the offline OCR / computer-vision packages..." 'Yellow' }
    else { Say '  No suitable Python found - installing Python 3.12 (x64, current user) with winget...' 'Yellow' }
    # per-user, silent, no launcher / PATH changes (no administrator rights or UAC prompt needed)
    & winget install -e --id Python.Python.3.12 --architecture x64 --scope user --silent --accept-package-agreements --accept-source-agreements --override '/quiet InstallAllUsers=0 Include_launcher=0 PrependPath=0 Include_test=0 Shortcuts=0' | Out-Host
    $py2 = Pick-Python
    if ($py2 -and ((Rank $py2) -ge (Rank $py))) { $py = $py2 }
}
if (-not $py) { $py = Pick-Python '3.15' }   # last resort: newer Python for the core app (OCR packages may be unavailable)
if (-not $py) {
    Say '  Python 3.10 - 3.13 (64-bit) was not found and could not be installed automatically.' 'Red'
    Say '  Install Python 3.12 (Windows installer, 64-bit x64) from https://www.python.org/downloads/windows/ and run Setup again.' 'Red'
    try { Stop-Transcript | Out-Null } catch { }
    exit 1
}
Say "  Using Python $($py.Ver) ($($py.Machine)) : $($py.Exe)" 'Green'
if (-not (Is-Ideal $py)) {
    Say '  Note: the accounting engine and UI work fully on this Python; offline OCR for scanned agreements needs x64 Python 3.10-3.12 (or Tesseract).' 'Yellow'
}

if ($Rebuild -and (Test-Path $Venv)) { Say '  Removing the previous environment...'; Remove-Item -Recurse -Force $Venv }
if (Test-Path $VPy) {
    $cur = Probe $VPy @()
    if (-not $cur -or $cur.Machine -ne $py.Machine -or $cur.Ver -ne $py.Ver) {
        Say '  Existing environment uses a different Python - recreating it...' 'Yellow'
        Remove-Item -Recurse -Force $Venv
    }
}
if (-not (Test-Path $VPy)) {
    Say '  Creating the Python environment...'
    & $py.Exe -m venv $Venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VPy)) { Say '  Could not create the environment.' 'Red'; try { Stop-Transcript | Out-Null } catch { }; exit 1 }
}

$pipArgs = @('--disable-pip-version-check', '--no-input')
Say '  Upgrading pip...'
& $VPy -m pip install --upgrade pip setuptools wheel @pipArgs | Out-Host
Say '  Installing core packages (accounting engine, database, web UI, exports)...'
& $VPy -m pip install -r (Join-Path $AppDir 'requirements.txt') @pipArgs | Out-Host
if ($LASTEXITCODE -ne 0) { Say '  Core package installation failed - check the internet connection and the log.' 'Red'; try { Stop-Transcript | Out-Null } catch { }; exit 1 }

$optional = @()
if (-not $SkipOCR) {
    Say '  Installing document-intelligence packages (PDF rendering, OCR, computer vision)...'
    foreach ($pkg in @('PyMuPDF>=1.24', 'onnxruntime>=1.17', 'rapidocr-onnxruntime>=1.3.24')) {
        & $VPy -m pip install $pkg @pipArgs | Out-Host
        if ($LASTEXITCODE -ne 0) { $optional += $pkg; Say "    not available on this Python: $pkg" 'Yellow' }
    }
    & $VPy -c "import cv2" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $VPy -m pip install 'opencv-python-headless>=4.9' @pipArgs | Out-Host
        if ($LASTEXITCODE -ne 0) { $optional += 'opencv-python-headless'; Say '    OpenCV not available on this Python (basic image clean-up will be used)' 'Yellow' }
    }
}
Say '  Installing the optional Claude API connector (used only with explicit consent)...'
& $VPy -m pip install 'anthropic>=0.30' @pipArgs | Out-Host
if ($LASTEXITCODE -ne 0) { $optional += 'anthropic'; Say '    Claude connector not installed (offline reading unaffected)' 'Yellow' }

Say '  Self-test...'
Push-Location $AppDir
$test = "from app.engine.lessee import ENGINE_VERSION; from app.docintel import ocr, vision, ingest; import app.main; print('engine', ENGINE_VERSION, '| OCR:', ', '.join(ocr.available_engines()) or 'none', '| vision:', 'OpenCV' if vision.HAS_CV2 else 'Pillow', '| PDF:', 'PyMuPDF' if ingest.HAS_FITZ else 'pypdf+pdfium')"
& $VPy -c $test
$selfOk = ($LASTEXITCODE -eq 0)
Pop-Location
if (-not $selfOk) { Say '  Self-test failed - see the log.' 'Red'; try { Stop-Transcript | Out-Null } catch { }; exit 1 }

if (-not $NoShortcut) {
    try {
        $ws = New-Object -ComObject WScript.Shell
        $exe = Join-Path $AppDir 'Lease116.exe'
        if (Test-Path $exe) { $target = $exe; $icon = "$exe,0" }      # launcher: no console window, tray icon to stop
        else { $target = Join-Path $AppDir 'Start.bat'; $icon = Join-Path $AppDir 'app\static\img\lease116.ico' }
        foreach ($dir in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
            if (-not $dir) { continue }
            $lnk = $ws.CreateShortcut((Join-Path $dir 'Lease116.lnk'))
            $lnk.TargetPath = $target
            $lnk.WorkingDirectory = $AppDir
            $lnk.IconLocation = $icon
            $lnk.Description = 'Lease116 - Ind AS 116 / IFRS 16 lease accounting'
            $lnk.Save()
        }
        Say '  Shortcuts created on the Desktop and in the Start menu.' 'Green'
    } catch { Say '  Shortcut could not be created (start with Start.bat instead).' 'Yellow' }
}

Set-Content -Path (Join-Path $Base 'install.json') -Value (@{ app_dir = $AppDir; python = $py.Exe; python_version = "$($py.Ver)"; machine = $py.Machine; optional_missing = $optional; installed_at = (Get-Date).ToString('s') } | ConvertTo-Json)
Say ''
Say '  Setup complete.' 'Green'
Say '  Start Lease116 from the desktop shortcut (Lease116.exe) - it opens http://127.0.0.1:8116 in your browser.'
Say '  First sign-in: admin / admin116 (you will be asked to change it).'
if ($optional.Count -gt 0) { Say "  Optional components not installed: $($optional -join ', ')" 'Yellow' }
try { Stop-Transcript | Out-Null } catch { }
exit 0
