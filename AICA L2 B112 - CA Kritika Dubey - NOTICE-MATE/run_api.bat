@echo off
cd /d %~dp0
python scripts\init_db.py || exit /b 1
python -m noticemate.api.main
