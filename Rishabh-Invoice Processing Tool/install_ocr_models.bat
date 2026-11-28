@echo off
REM Installs RapidOCR + ONNX Runtime (the PP-OCRv6 OCR engine) from the wheels folder - no internet needed.
REM The models themselves are in ipt\models\ocr. Log: ocr_models_log.txt
cd /d "%~dp0"
echo Installing the OCR engine... > ocr_models_log.txt
".venv\Scripts\python.exe" -m pip install --no-index --find-links wheels "rapidocr==3.10.0" "onnxruntime>=1.20,<2" >> ocr_models_log.txt 2>&1
".venv\Scripts\python.exe" -c "from ipt.services.extraction.sources import ocr_engine, rapid_available; print('RapidOCR ready:', rapid_available(), '- engine:', ocr_engine())" >> ocr_models_log.txt 2>&1
type ocr_models_log.txt
pause
