#!/bin/sh
# Builds ..\..\Lease116.exe (Windows launcher, .NET Framework 4.x - included with Windows 10/11) with the Mono C# compiler.
#   sudo apt-get install mono-mcs mono-devel
set -e
cd "$(dirname "$0")"
python3 make_icons.py >/dev/null
mcs -nologo -target:winexe -platform:anycpu -optimize+ -sdk:4.5 -out:../../Lease116.exe \
    -win32icon:lease116_launcher.ico -resource:lease116_tray.ico,Lease116.tray.ico \
    -r:System.dll -r:System.Drawing.dll -r:System.Windows.Forms.dll Lease116Launcher.cs
echo "built $(cd ../.. && pwd)/Lease116.exe"
