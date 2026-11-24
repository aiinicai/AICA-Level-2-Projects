#Requires -Version 5.1
#Requires -RunAsAdministrator
param([ValidateRange(1024,65535)][int]$Port = 8080)
$ErrorActionPreference = 'Stop'
try {
    $install = Join-Path $env:ProgramData 'Net Worth Office'
    $files = @('networth.py','udin_workflow.py','udin-autofill.js','requirements.txt','Run Net Worth Office.ps1')
    foreach ($file in $files) {
        if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $file) -PathType Leaf)) {
            throw "Missing $file. Extract the entire setup ZIP first."
        }
    }
    function Find-Python {
        foreach ($version in (Get-ChildItem 'HKLM:\SOFTWARE\Python\PythonCore' -ErrorAction SilentlyContinue |
                Sort-Object PSChildName -Descending)) {
            $entry = Get-Item -LiteralPath ($version.PSPath + '\InstallPath') -ErrorAction SilentlyContinue
            if (!$entry -or !$entry.GetValue('')) { continue }
            $path = Join-Path ($entry.GetValue('')) 'python.exe'
            if (Test-Path -LiteralPath $path) {
                & $path -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'
                if ($LASTEXITCODE -eq 0) { return $path }
            }
        }
    }
    $python = Find-Python
    if (!$python) {
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (!$winget) { throw 'Install Python 3.13 for all users, then rerun Setup. Windows Package Manager is unavailable.' }
        Write-Host 'Installing Python 3.13...'
        & $winget.Source install --id Python.Python.3.13 --exact --source winget --scope machine --silent --accept-package-agreements --accept-source-agreements
        $python = Find-Python
        if (!$python) { throw 'Setup could not install Python. Install Python 3.13 for all users, then rerun Setup.' }
    }
    $task = 'Net Worth Office'
    $existingTask = Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
    if ($existingTask) { throw 'Net Worth Office is already installed on this server. The existing installation was left running.' }
    New-Item -ItemType Directory -Path $install -Force | Out-Null
    & icacls.exe $install /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not secure the app directory.' }
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $Port is busy. Close the app using it and rerun Setup."
    }
    foreach ($file in $files) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination $install -Force }
    $venv = Join-Path $install '.venv'
    $appPython = Join-Path $venv 'Scripts\python.exe'
    if (!(Test-Path -LiteralPath $appPython)) {
        & $python -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the app environment.' }
    }
    Write-Host 'Installing app libraries...'
    & $appPython -m pip --disable-pip-version-check install -r (Join-Path $install 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the app libraries. Check internet access and rerun Setup.' }
    $db = Join-Path $install 'networth.sqlite3'
    $backup = Join-Path $PSScriptRoot 'networth-backup.sqlite3'
    if (!(Test-Path -LiteralPath $db) -and (Test-Path -LiteralPath $backup)) {
        & $appPython -c 'import pathlib,sqlite3,sys; c=sqlite3.connect(pathlib.Path(sys.argv[1]).resolve().as_uri()+"?mode=ro",uri=True); assert c.execute("PRAGMA quick_check").fetchone()==("ok",); assert c.execute("SELECT 1 FROM sqlite_master WHERE name=?",("reports",)).fetchone()' $backup
        if ($LASTEXITCODE -ne 0) { throw 'The report backup is invalid.' }
        Copy-Item -LiteralPath $backup -Destination $db
        Write-Host 'Existing reports imported.'
    }
    $runner = Join-Path $install 'Run Net Worth Office.ps1'
    $arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Port {1}' -f $runner,$Port
    $action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument $arguments -WorkingDirectory $install
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    $rule = 'NetWorthOffice-PrivateLAN'
    $registered = $false
    $firewall = $false
    try {
        Register-ScheduledTask -TaskName $task -Action $action -Trigger (New-ScheduledTaskTrigger -AtStartup) -User 'SYSTEM' -Settings $settings | Out-Null
        $registered = $true
        New-NetFirewallRule -Name $rule -DisplayName 'Net Worth Office (private subnet)' -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -RemoteAddress LocalSubnet -Profile Domain,Private | Out-Null
        $firewall = $true
        Start-ScheduledTask -TaskName $task
        $ready = $false
        for ($i=0; $i -lt 20; $i++) {
            try {
                $reply = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri "http://127.0.0.1:$Port/health"
                if ($reply.Content -eq 'net-worth-office') { $ready = $true; break }
            } catch { Start-Sleep -Seconds 1 }
        }
        if (!$ready) { throw "The server did not start. See networth-server.log in $install." }
    } catch {
        if ($firewall) { Remove-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue }
        if ($registered) {
            Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $task -Confirm:$false -ErrorAction SilentlyContinue
        }
        throw
    }
    $link = "http://$($env:COMPUTERNAME):$Port/"
    Write-Host "Staff link: $link" -ForegroundColor Green
    Write-Host 'Use only on a trusted private office network. Anyone who can reach the app can access its reports.'
    Start-Process "http://127.0.0.1:$Port/"
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
} finally {
    Read-Host 'Press Enter to close' | Out-Null
}
