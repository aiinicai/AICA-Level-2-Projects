param(
    [string]$Root = $PSScriptRoot
)

$startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
if (-not (Test-Path $startup)) {
    New-Item -ItemType Directory -Path $startup -Force | Out-Null
}

$linkPath = Join-Path $startup "HARSH RESTRORECO.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($linkPath)
$shortcut.TargetPath = Join-Path $Root "run.bat"
$shortcut.WorkingDirectory = $Root
$shortcut.WindowStyle = 1
$shortcut.Description = "HARSH RESTRORECO"
$shortcut.Save()
Write-Output $linkPath
