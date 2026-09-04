@echo off
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "Depreciation-3CB-3CD" "Depreciation-3CB-3CD.py"
pause
