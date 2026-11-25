<#
.SYNOPSIS
  Set this PC up as the intranet server for Cash Flow Forecast (run once, as Administrator).

.DESCRIPTION
  1. Checks the folder, the Python environment and that an Admin user exists.
  2. Uses the HTTPS certificate in instance\certs (server.crt + server.key), or the files you name.
     No certificate yet? Run:  .venv\Scripts\python.exe scripts\make_cert.py --csr  (for IT)
                          or:  .venv\Scripts\python.exe scripts\make_cert.py --self-signed  (trial)
  3. Writes .env: listen on the network with HTTPS on the chosen port (the old .env is kept as .env.bak).
  4. Opens that port in Windows Firewall for Domain and Private networks only.
  5. Registers a scheduled task that starts the app when Windows starts and restarts it if it stops.
  Undo everything with:  .\setup_server.ps1 -Remove

.EXAMPLE
  .\setup_server.ps1 -Port 8443 -BackupCopyDir "\\fileserver\finance\cff_backups"
#>
param(
    [int]$Port = 8443,
    [string]$CertFile = "",
    [string]$KeyFile = "",
    [string]$BackupCopyDir = "",
    [switch]$NoFirewall,
    [switch]$NoTask,
    [switch]$Remove
)
$ErrorActionPreference = "Stop"
$TaskName = "Cash Flow Forecast"
$RuleName = "Cash Flow Forecast (HTTPS)"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Root ".venv\Scripts\python.exe"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw "Run this script in PowerShell opened with 'Run as administrator'." }

if ($Remove) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Scheduled task removed."
    }
    Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Write-Host "Firewall rule removed (if it existed). .env was left as it is."
    return
}

Write-Host "== Cash Flow Forecast server setup ==" -ForegroundColor Cyan
if ($Root -like "*OneDrive*") {
    Write-Warning "This folder is inside OneDrive. Move it to a local folder such as C:\CashFlowApp first: OneDrive syncing a live database can damage it."
    if ((Read-Host "Continue anyway? (y/N)") -ne "y") { return }
}
if (-not (Test-Path $Py)) {
    throw "Python environment missing. In this folder run: py -3 -m venv .venv ; .venv\Scripts\python.exe -m pip install -r requirements.txt"
}
Push-Location $Root
try {
    & $Py -m app.cli has-users | Out-Null
    if ($LASTEXITCODE -eq 3) { throw "No users yet. Run start_app.bat once to create the first Admin, then run this script again." }

    # --- certificate
    if (-not $CertFile) { $CertFile = Join-Path $Root "instance\certs\server.crt" }
    if (-not $KeyFile) { $KeyFile = Join-Path $Root "instance\certs\server.key" }
    if (-not (Test-Path $CertFile) -or -not (Test-Path $KeyFile)) {
        throw "Certificate not found ($CertFile / $KeyFile). Make one with scripts\make_cert.py (--csr for IT, or --self-signed for a trial)."
    }

    # --- .env
    $envPath = Join-Path $Root ".env"
    if (Test-Path $envPath) { Copy-Item $envPath "$envPath.bak" -Force; Write-Host "Existing .env saved as .env.bak" }
    $lines = @(
        "# Written by setup_server.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm'). See .env.example for all settings.",
        "CFF_HOST=0.0.0.0",
        "CFF_PORT=$Port",
        "CFF_SSL_CERTFILE=$CertFile",
        "CFF_SSL_KEYFILE=$KeyFile"
    )
    if ($BackupCopyDir) { $lines += "CFF_BACKUP_COPY_DIR=$BackupCopyDir" }
    if (Test-Path "$envPath.bak") {   # keep any other settings the old .env had
        $keep = Get-Content "$envPath.bak" | Where-Object { $_ -match '^CFF_' -and $_ -notmatch '^CFF_(HOST|PORT|SSL_CERTFILE|SSL_KEYFILE|BACKUP_COPY_DIR)=' }
        $lines += $keep
    }
    [IO.File]::WriteAllLines($envPath, $lines)
    Write-Host ".env written: HTTPS on port $Port"
    & $Py -c "from app.core.config import get_settings; s=get_settings(); s.check_network_safety(); print('Settings OK:', s.host, s.port, 'https' if s.https_enabled else 'http')"
    if ($LASTEXITCODE -ne 0) { throw "The settings in .env are not valid (see the message above)." }

    # --- firewall
    if (-not $NoFirewall) {
        Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
        New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Protocol TCP -LocalPort $Port `
            -Profile Domain,Private -Action Allow | Out-Null
        Write-Host "Firewall: port $Port open for Domain and Private networks."
    }

    # --- start with Windows
    if (-not $NoTask) {
        $action = New-ScheduledTaskAction -Execute $Py -Argument "`"$(Join-Path $Root 'run.py')`"" -WorkingDirectory $Root
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
        if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
            Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        }
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
            -Principal $principal -Description "Cash Flow Forecast web app (HTTPS, port $Port)" | Out-Null
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "Scheduled task '$TaskName' registered and started (starts with Windows)."
    }

    $name = [System.Net.Dns]::GetHostEntry($env:COMPUTERNAME).HostName.ToLower()
    Write-Host ""
    Write-Host "Done. Users open:  https://${name}:$Port" -ForegroundColor Green
    Write-Host "Add users in the app: Admin -> Users. Backups: Admin -> Backups."
    Write-Host "Stop:  Stop-ScheduledTask -TaskName '$TaskName'    Start:  Start-ScheduledTask -TaskName '$TaskName'"
}
finally {
    Pop-Location
}
