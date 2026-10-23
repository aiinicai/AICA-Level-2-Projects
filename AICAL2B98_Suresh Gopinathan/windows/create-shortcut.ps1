# Puts a TickTrail icon on this computer's desktop.
# It opens TickTrail in its own window (through Microsoft Edge), or in the default browser if Edge is missing.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$cfg  = Get-Content (Join-Path $root "config.json") -Raw | ConvertFrom-Json
$url  = "http://localhost:$($cfg.port)"
$desk = [Environment]::GetFolderPath("Desktop")   # also finds a desktop kept in OneDrive

$lnkPath = Join-Path $desk "TickTrail.lnk"
$urlPath = Join-Path $desk "TickTrail.url"
Remove-Item $lnkPath, $urlPath -ErrorAction SilentlyContinue

$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
          "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1

if($edge){
  $ws  = New-Object -ComObject WScript.Shell
  $lnk = $ws.CreateShortcut($lnkPath)
  $lnk.TargetPath   = $edge
  $lnk.Arguments    = "--app=$url"
  $lnk.IconLocation = "$edge,0"
  $lnk.Description  = "TickTrail audit compliance register"
  $lnk.Save()
}else{
  Set-Content -Path $urlPath -Value "[InternetShortcut]`r`nURL=$url`r`n" -Encoding ASCII
}
Write-Host "A TickTrail icon is now on the desktop. It opens $url" -ForegroundColor Green
Read-Host "Press Enter to close"
