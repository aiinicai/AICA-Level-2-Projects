#!/bin/bash
cd "$(dirname "$0")"
python3 -c "import openpyxl" 2>/dev/null || python3 -m pip install openpyxl
python3 -c "import pypdf" 2>/dev/null || python3 -m pip install pypdf
python3 -c "import pyodbc" 2>/dev/null || python3 -m pip install pyodbc
python3 nce_tool.py
