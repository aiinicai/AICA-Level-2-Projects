@echo off
REM Run on ONE office PC; colleagues open http://<this-pc-name>:8501 in their browser on the office network.
cd /d %~dp0
echo Colleagues open:  http://%COMPUTERNAME%:8501
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
