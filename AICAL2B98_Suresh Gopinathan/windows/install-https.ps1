#Requires -RunAsAdministrator
# Runs Caddy in front of TickTrail so staff can reach it over the internet with HTTPS.
# Before running: put caddy.exe in the caddy folder, and replace ticktrail.example.in in caddy\Caddyfile with your own address.
$ErrorActionPreference = "Stop"
$root  = Split-Path -Parent $PSScriptRoot
$dir   = Join-Path $root "caddy"
$caddy = Join-Path $dir "caddy.exe"
$file  = Join-Path $dir "Caddyfile"

if(-not (Test-Path $caddy)){
  Write-Host "caddy.exe is missing. Download 'Windows amd64' from https://caddyserver.com/download, rename it to caddy.exe and put it in:  $dir" -ForegroundColor Red
  Read-Host "Press Enter to close"; exit 1
}
if((Get-Content $file -Raw) -match "ticktrail\.example\.in"){
  Write-Host "Open caddy\Caddyfile in Notepad and replace ticktrail.example.in with your own web address first." -ForegroundColor Red
  Read-Host "Press Enter to close"; exit 1
}
& $caddy validate --config $file --adapter caddyfile
if($LASTEXITCODE -ne 0){ Write-Host "The Caddyfile has a mistake (see above)." -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

# Let web traffic in (ports 80 and 443 are needed for HTTPS and its certificate)
foreach($p in 80, 443){
  if(-not (Get-NetFirewallRule -DisplayName "TickTrail HTTPS $p" -ErrorAction SilentlyContinue)){
    New-NetFirewallRule -DisplayName "TickTrail HTTPS $p" -Direction Inbound -Protocol TCP -LocalPort $p -Action Allow | Out-Null
  }
}

$action    = New-ScheduledTaskAction -Execute $caddy -Argument "run --config `"$file`" --adapter caddyfile" -WorkingDirectory $dir
$trigger   = New-ScheduledTaskTrigger -AtStartup
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "TickTrail HTTPS (Caddy)" -Description "HTTPS front door for TickTrail" `
  -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Stop-ScheduledTask -TaskName "TickTrail HTTPS (Caddy)" -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName "TickTrail HTTPS (Caddy)"

$site = ((Get-Content $file) | Where-Object { $_ -match "^\s*[A-Za-z0-9.-]+\.[A-Za-z]{2,}\s*\{" } | Select-Object -First 1) -replace "\s*\{.*", ""
Write-Host ""
Write-Host "HTTPS is set up. In a minute or two, open  https://$($site.Trim())" -ForegroundColor Green
Write-Host "The first visit can take up to a minute while the certificate is issued."
Read-Host "Press Enter to close"
