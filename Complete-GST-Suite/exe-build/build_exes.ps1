# Builds the two one-file exes of the web app (new design):
#   dist\Complete GST Suite.exe          (this computer only, same as Start_Local.bat)
#   dist\Complete GST Suite Server.exe   (office server, same as Start_Server.bat)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$web  = Join-Path $root "dist\GST Suite Web"
$work = Join-Path $here "work"
New-Item -ItemType Directory -Force $work | Out-Null
python (Join-Path $here "make_icon.py") (Join-Path $here "app.ico")

foreach ($m in @(@{mode="local"; name="Complete GST Suite"}, @{mode="server"; name="Complete GST Suite Server"})) {
    $src = Join-Path $work $m.mode
    New-Item -ItemType Directory -Force $src | Out-Null
    Copy-Item (Join-Path $here "gst_web_launcher.py") $src -Force
    Set-Content (Join-Path $src "_mode.py") "MODE = `"$($m.mode)`"" -Encoding ascii
    python -m PyInstaller --noconfirm --clean --onefile --windowed `
        --name $m.name `
        --icon (Join-Path $here "app.ico") `
        --add-data "$(Join-Path $here 'app.ico');." `
        --add-data "$(Join-Path $web 'node');node" `
        --add-data "$(Join-Path $web 'app');app" `
        --paths $src `
        --hidden-import _mode `
        --distpath (Join-Path $root "dist") `
        --workpath (Join-Path $work "build_$($m.mode)") `
        --specpath $work `
        (Join-Path $src "gst_web_launcher.py")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed for $($m.name)" }
}
Get-ChildItem (Join-Path $root "dist") -Filter *.exe | Select-Object Name, @{n="MB";e={[math]::Round($_.Length/1MB,1)}}
