# Creates a "ChatVault" shortcut on the Desktop and in the Start menu.
# The shortcut opens ChatVault.html in its own app window (Chrome or Edge) with the ChatVault icon.
# Nothing is installed and nothing is downloaded. Run it again if you move the folder.

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$app  = Join-Path $root 'ChatVault.html'
$ico  = Join-Path $root 'assets\chatvault.ico'

if (-not (Test-Path $app)) { Write-Host "ChatVault.html was not found in $root" -ForegroundColor Red; exit 1 }

$candidates = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LocalAppData\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)
$browser = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $browser) { Write-Host 'Google Chrome or Microsoft Edge is needed. Please install one and run this again.' -ForegroundColor Red; exit 1 }

$url = ([System.Uri]$app).AbsoluteUri
$shell = New-Object -ComObject WScript.Shell
$targets = @(
  [Environment]::GetFolderPath('Desktop'),
  (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs')
)
foreach ($dir in $targets) {
  $lnk = $shell.CreateShortcut((Join-Path $dir 'ChatVault.lnk'))
  $lnk.TargetPath       = $browser
  $lnk.Arguments        = "--app=`"$url`""
  $lnk.IconLocation     = "$ico,0"
  $lnk.WorkingDirectory = $root
  $lnk.Description      = 'ChatVault - WhatsApp chat archiver'
  $lnk.Save()
}

$name = if ($browser -like '*msedge*') { 'Microsoft Edge' } else { 'Google Chrome' }
Write-Host ''
Write-Host 'ChatVault shortcut created on your Desktop and in the Start menu.' -ForegroundColor Green
Write-Host "It opens ChatVault in its own window using $name."
Write-Host 'If you move this folder, run "Create Desktop Shortcut" again.'
