"""Launcher used only when packaging with PyInstaller. Normal use: streamlit run app.py
Developed by CA Sapan"""
import os
import sys

from streamlit.web import cli as stcli


def bundled(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


if __name__ == "__main__":
    # Keep the database next to the .exe, not inside PyInstaller's temporary folder,
    # otherwise the data would be lost every time the program closes.
    exe_dir = os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                              else os.path.abspath(__file__))
    os.environ.setdefault("WORK_DIARY_DB", os.path.join(exe_dir, "work_diary.db"))
    sys.argv = ["streamlit", "run", bundled("app.py"), "--global.developmentMode=false"]
    sys.exit(stcli.main())
