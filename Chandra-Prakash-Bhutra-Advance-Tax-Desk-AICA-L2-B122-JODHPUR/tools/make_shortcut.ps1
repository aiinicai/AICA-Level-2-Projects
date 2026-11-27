# Puts an "Advance Tax Desk" icon on the Desktop. Run by "Start Advance Tax Desk.bat".
$ErrorActionPreference = 'Stop'
$root    = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$shell   = New-Object -ComObject WScript.Shell
$link    = $shell.CreateShortcut((Join-Path $desktop 'Advance Tax Desk.lnk'))
$link.TargetPath       = Join-Path $root 'Start Advance Tax Desk.bat'
$link.WorkingDirectory = $root
$link.IconLocation     = (Join-Path $root 'assets\icon.ico') + ',0'
$link.WindowStyle      = 7   # start minimised; the browser comes to the front
$link.Description      = 'Advance Tax Desk'
$link.Save()
