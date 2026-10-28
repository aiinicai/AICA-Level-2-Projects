import os
import sys
import webbrowser
import threading
import time
import streamlit.web.cli as stcli

def open_browser():
    time.sleep(2.5)
    webbrowser.open("http://localhost:8501")

def main():
    # Resolve the absolute path to app.py whether running as script or frozen exe
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    app_path = os.path.join(base_dir, "app.py")
    
    # Configure Streamlit CLI arguments
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.port=8501",
        "--server.headless=true",
        "--browser.serverAddress=localhost",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
    ]
    
    # Launch default browser in a background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start the Streamlit server
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()