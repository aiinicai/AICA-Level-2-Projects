BankDoc Processor & Renamer - quick start
=========================================
1. Install Python 3.9 or newer from python.org (tick "Add Python to PATH").
2. Keep bankdoc_processor.py and Start_BankDoc.bat in the same folder.
3. Double-click Start_BankDoc.bat. (First run installs components - internet needed only then.)
   Manual alternative:  pip install customtkinter pymupdf pillow openpyxl reportlab
                        python bankdoc_processor.py
4. Start LM Studio (Local Server ON) or Ollama on the same computer and load a model.
   Scanned PDFs / photos need a vision model (e.g. Gemma 3, Qwen2.5-VL, Llama 3.2 Vision).

Files the tool creates inside your document folder:
  rename_session.json            - exact record of what was renamed (needed for Undo / crash recovery)
  bankdoc_processing_log.txt     - events and errors
  bankdoc_rename_log_<time>.csv  - detailed rename log (optional)
Passwords are never saved anywhere.
