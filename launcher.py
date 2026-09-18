import os, sys, time, threading, webbrowser
import streamlit.web.cli as stcli

def open_browser():
    time.sleep(5)
    webbrowser.open("http://localhost:8501")

base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(__file__)
app = os.path.join(base, "app.py")

threading.Thread(target=open_browser, daemon=True).start()

sys.argv = [
    "streamlit", "run", app,
    "--server.headless=true",
    "--global.developmentMode=false"
]

stcli.main()