#Requires -RunAsAdministrator
# Stops TickTrail and removes its start-up and backup tasks. Your data folder is left untouched.
$ErrorActionPreference = "SilentlyContinue"
foreach($t in "TickTrail", "TickTrail daily backup", "TickTrail HTTPS (Caddy)"){
  Stop-ScheduledTask -TaskName $t
  Unregister-ScheduledTask -TaskName $t -Confirm:$false
}
Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" | Where-Object { $_.CommandLine -like "*server.js*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Write-Host "TickTrail has been stopped and will no longer start by itself. Your data folder has not been touched." -ForegroundColor Green
Read-Host "Press Enter to close"
