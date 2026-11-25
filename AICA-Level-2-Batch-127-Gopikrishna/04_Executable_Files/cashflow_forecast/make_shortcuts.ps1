<#
Creates Windows shortcuts that start or stop the app with NO window at all (they run pythonw.exe directly).

    powershell -ExecutionPolicy Bypass -File make_shortcuts.ps1            # shortcuts in this folder
    powershell -ExecutionPolicy Bypass -File make_shortcuts.ps1 -Desktop   # also on your Desktop
#>
param([switch]$Desktop)

$root = $PSScriptRoot
$pyw = Join-Path $root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pyw)) { Write-Error "Missing $pyw - create the virtual environment first (see README)."; exit 1 }

$items = @(
    @{ Name = "Cash Flow Forecast";             Args = "-m app.launcher";               Icon = "shell32.dll,13"  },
    @{ Name = "Cash Flow Forecast - Demo";      Args = "-m app.launcher --demo";        Icon = "shell32.dll,165" },
    @{ Name = "Stop Cash Flow Forecast";        Args = "-m app.launcher --stop";        Icon = "shell32.dll,131" },
    @{ Name = "Stop Cash Flow Forecast - Demo"; Args = "-m app.launcher --demo --stop"; Icon = "shell32.dll,131" }
)
$targets = @($root)
if ($Desktop) { $targets += [Environment]::GetFolderPath("Desktop") }

$shell = New-Object -ComObject WScript.Shell
foreach ($dir in $targets) {
    foreach ($i in $items) {
        $lnk = $shell.CreateShortcut((Join-Path $dir ($i.Name + ".lnk")))
        $lnk.TargetPath = $pyw
        $lnk.Arguments = $i.Args
        $lnk.WorkingDirectory = $root
        $lnk.IconLocation = Join-Path $env:SystemRoot ("System32\" + $i.Icon)
        $lnk.Description = $i.Name
        $lnk.Save()
        Write-Output "Created $(Join-Path $dir ($i.Name + '.lnk'))"
    }
}
