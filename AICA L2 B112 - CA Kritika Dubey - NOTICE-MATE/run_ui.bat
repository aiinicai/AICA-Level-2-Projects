@echo off
cd /d %~dp0
streamlit run frontend\app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
