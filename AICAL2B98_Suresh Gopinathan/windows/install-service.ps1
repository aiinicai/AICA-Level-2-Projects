#Requires -RunAsAdministrator
# Sets TickTrail to start when this computer starts (even before anyone logs in),
# restart by itself if it stops, and take a backup every evening.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$node = (Get-Command node -ErrorAction SilentlyContinue).Source
if(-not $node){
  Write-Host "Node.js was not found. Install the LTS version from https://nodejs.org (tick 'Add to PATH'), then run this again." -ForegroundColor Red
  Read-Host "Press Enter to close"; exit 1
}
$ver = [version](& $node -p "process.versions.node")
if($ver -lt [version]"22.13.0"){
  Write-Host "TickTrail needs Node.js 22.13 or later; this computer has $ver. Install the current LTS from https://nodejs.org." -ForegroundColor Red
  Read-Host "Press Enter to close"; exit 1
}
New-Item -ItemType Directory -Force -Path (Join-Path $root "data") | Out-Null

# The data and backup folders hold client data: only administrators and the SYSTEM account may read it.
foreach($sub in "data", "backups"){
  $dir = Join-Path $root $sub; New-Item -ItemType Directory -Force -Path $dir | Out-Null
  icacls $dir /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null   # SYSTEM and Administrators, by id so it works in any Windows language
}

$runArgs = "/c `"`"$node`" --disable-warning=ExperimentalWarning server.js >> data\server.log 2>&1`""
$action    = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $runArgs -WorkingDirectory $root
$trigger   = New-ScheduledTaskTrigger -AtStartup
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
               -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "TickTrail" -Description "TickTrail audit compliance register (web server)" `
  -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

$bAction  = New-ScheduledTaskAction -Execute $node -Argument "--disable-warning=ExperimentalWarning server.js --backup" -WorkingDirectory $root
$bTrigger = New-ScheduledTaskTrigger -Daily -At "8:30pm"
$bSet     = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName "TickTrail daily backup" -Description "Copies the TickTrail database and PDFs into the backups folder" `
  -Action $bAction -Trigger $bTrigger -Settings $bSet -Principal $principal -Force | Out-Null

Stop-ScheduledTask -TaskName "TickTrail" -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName "TickTrail"
Start-Sleep -Seconds 3

$cfg = Get-Content (Join-Path $root "config.json") -Raw | ConvertFrom-Json
try{
  Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:{0}/healthz" -f $cfg.port) -TimeoutSec 5 | Out-Null
  Write-Host ""
  Write-Host "TickTrail is installed and running." -ForegroundColor Green
  Write-Host ("On this computer, open  http://localhost:{0}" -f $cfg.port)
  Write-Host "It starts by itself when the computer starts, and a backup is taken every evening at 8:30 pm."
}catch{
  Write-Host "The task was installed but TickTrail did not answer yet. Look in data\server.log for the reason." -ForegroundColor Yellow
}
Read-Host "Press Enter to close"
