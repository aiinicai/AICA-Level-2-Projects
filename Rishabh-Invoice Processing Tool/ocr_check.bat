@echo off
REM Read-only OCR check of the Majisa sample scan (writes nothing to IPT). Output: ocr_check_log.txt
cd /d "%~dp0"
".venv\Scripts\python.exe" -m ipt.tools.ocr_check "Capstoone Projectsample_invoices\Scanned Document 37.pdf" 08IEWPS1264C1ZZ > ocr_check_log.txt 2>&1
type ocr_check_log.txt
pause
