@echo off
setlocal
cd /d "%~dp0"
set "PYEXE=py -3.12"
%PYEXE% -m pip install --upgrade pip setuptools wheel
%PYEXE% -m pip install openpyxl python-docx reportlab python-pptx pypdf cryptography nuitka ordered-set zstandard
%PYEXE% -m nuitka ^
 --mode=onefile ^
 --windows-console-mode=disable ^
 --enable-plugin=tk-inter ^
 --include-package=openpyxl ^
 --include-package=docx ^
 --include-package=reportlab ^
 --include-package=pptx ^
 --include-package=pypdf ^
 --include-package=cryptography ^
 --assume-yes-for-downloads ^
 --product-name="DCF Valuation Professional" ^
 --file-description="Hybrid offline and AI-assisted DCF valuation utility" ^
 --company-name="DCF Valuation Professional" ^
 --product-version=3.0.6.0 ^
 --file-version=3.0.6.0 ^
 --output-filename="DCF_Valuation_Professional_v3_0_6.exe" ^
 "DCF_Valuation_Professional_v3_0_6.py"
pause
