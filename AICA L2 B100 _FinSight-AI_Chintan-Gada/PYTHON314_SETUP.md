# FinSight AI — Windows Python 3.14.8 (64-bit) Setup

## Important: do not enter these commands at `>>>`
The black window in your screenshot is the Python interactive interpreter (`>>>`). Type `exit()` and press Enter to close it. Use **Command Prompt (cmd)**, Windows Terminal or PowerShell to run commands, or simply double-click `run_windows.bat`.

## Recommended: one-click launcher
1. Download `FinSight_AI_Python314.zip` and extract it fully using **Extract All** (do not run from inside the ZIP).
2. Open the extracted `FinSight_AI` folder.
3. If you previously installed FinSight AI, do **not** copy over an old `.venv` folder. Delete an old `.venv` if one exists.
4. Double-click `run_windows.bat`.
5. The launcher locates **Python 3.14 64-bit**, creates `.venv`, updates pip, installs compatible dependencies and starts Streamlit.
6. Open `http://localhost:8501` if the browser does not open automatically.
7. Download/upload the sample workbook and follow the review/approval steps.

## Manual installation in Command Prompt
Open Command Prompt **in the extracted FinSight_AI folder** (click File Explorer address bar, type `cmd`, press Enter), then run:

```bat
py -3.14 --version
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

If `py -3.14` is unavailable but `python --version` says Python 3.14.8, replace `py -3.14` with `python` in the first two commands.

## Test suite
After installation, double-click `run_tests_windows.bat` or run:

```bat
.venv\Scripts\python.exe -m pytest -q
```

## OpenAI commentary (optional)
Offline financial advisory works without an API key. To enable optional AI commentary, in the SAME Command Prompt session before launching:

```bat
set OPENAI_API_KEY=your_api_key_here
.venv\Scripts\python.exe -m streamlit run app.py
```

Never share API keys or submit confidential client data without approval. API usage may incur costs.

## Troubleshooting
- `>>>` prompt: you are inside the Python interpreter, not Command Prompt. Run `exit()`.
- `No matching distribution found`: upgrade pip, verify Python 3.14 64-bit, and check internet access. The package versions are minimums, not exact pins.
- `.venv` points to old Python: delete the `.venv` folder and rerun `run_windows.bat`.
- `py` not recognised: use `python` if `python --version` confirms 3.14, or repair the Python launcher.
- `Permission denied`: extract to a writable folder such as Documents, not Program Files.
- `Port 8501 already in use`: run `.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502`.
- Missing `OPENAI_API_KEY`: switch off the optional OpenAI toggle to use the offline advisory.

## Scope
Structured Excel input, explainable rule-based anomaly flags, optional AI commentary, financial dashboards, SQLite review workflow and Excel/PDF exports. This is an educational application and not a statutory financial statement validation or audit opinion tool.
