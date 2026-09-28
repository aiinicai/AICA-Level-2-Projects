@echo off
rem Builds ..\..\Lease116.exe with the C# compiler that ships with Windows (.NET Framework 4.x).
cd /d "%~dp0"
"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /platform:anycpu /optimize+ ^
  /out:..\..\Lease116.exe /win32icon:lease116_launcher.ico /resource:lease116_tray.ico,Lease116.tray.ico ^
  /r:System.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll Lease116Launcher.cs
