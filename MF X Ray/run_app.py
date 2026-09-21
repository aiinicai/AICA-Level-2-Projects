#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MF X-RAY V1.0 Application Launcher
Starts the local server and automatically opens the modern desktop interface.
"""
import os
import sys
import time
import subprocess
import webbrowser
import threading

PORT = 5055
URL = f"http://127.0.0.1:{PORT}"

def launch_browser():
    time.sleep(1.2)
    # Check if Microsoft Edge is available for frameless app mode
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
    ]
    for p in edge_paths:
        if os.path.exists(p):
            try:
                subprocess.Popen([p, f"--app={URL}", "--window-size=1280,820"])
                print(f"Launched MF X-Ray in standalone desktop window via Edge.")
                return
            except Exception:
                pass
    
    # Fallback to default browser
    print(f"Opening MF X-Ray in default browser: {URL}")
    webbrowser.open(URL)

if __name__ == "__main__":
    print("=" * 60)
    print("  MF X-RAY V1.0 -- AI-Powered Mutual Fund Intelligence")
    print("  ICAI AI Level 2 Capstone Project")
    print(f"  Starting local application at: {URL}")
    print("=" * 60)
    
    # Launch browser/app in a separate thread
    threading.Thread(target=launch_browser, daemon=True).start()
    
    # Run the server
    from backend_server import app
    app.run(host="127.0.0.1", port=PORT, debug=False)
