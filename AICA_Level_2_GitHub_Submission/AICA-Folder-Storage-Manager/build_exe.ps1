# Builds dist\AICA Folder Storage Manager.exe (single file, Windows 10/11 x64, no Python needed on target)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python tools\make_icon.py
$excl = @("PySide6.QtWebEngineCore","PySide6.QtWebEngineWidgets","PySide6.QtWebEngineQuick","PySide6.QtWebChannel",
          "PySide6.QtQuick","PySide6.QtQml","PySide6.QtQuickWidgets","PySide6.Qt3DCore","PySide6.QtMultimedia",
          "PySide6.QtPdf","PySide6.QtPdfWidgets","PySide6.QtCharts","PySide6.QtDataVisualization","PySide6.QtBluetooth",
          "PySide6.QtPositioning","PySide6.QtSql","PySide6.QtTest","PySide6.QtNetwork","PySide6.QtOpenGL",
          "PySide6.QtSvg","PySide6.QtDesigner","tkinter","pytest","pywinauto","pdf2docx","numpy","cv2","fitz")
$args = @("--noconfirm","--clean","--onefile","--windowed","--name","AICA Folder Storage Manager",
          "--icon","assets\app.ico","--add-data","assets\app.ico;assets",
          "--collect-submodules","winrt","--collect-binaries","winrt",
          "--collect-data","pypdfium2","--collect-binaries","pypdfium2","--collect-data","pypdfium2_raw","--collect-binaries","pypdfium2_raw",
          "--collect-data","docx","--hidden-import","send2trash")
foreach ($m in $excl) { $args += @("--exclude-module",$m) }
python -m PyInstaller @args main.py
Get-Item "dist\AICA Folder Storage Manager.exe" | Select-Object FullName, Length
