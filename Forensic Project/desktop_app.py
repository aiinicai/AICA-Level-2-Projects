"""
Red Flag Engine — Standalone Native Desktop Application
Launches the application in dedicated Native Desktop App Window Mode (Chromium/Edge App Window).
Opens as an independent desktop window (no browser tabs, no URL bar, pure native application).
Closing the window cleanly terminates the background engine.
"""
import os
import sys
import time
import socket
import shutil
import subprocess
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if os.getcwd() != APP_DIR:
    os.chdir(APP_DIR)

def find_free_port(start_port=8501, max_attempts=50):
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start_port

def wait_for_server(url, timeout=45):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            time.sleep(0.4)
    return False

def find_app_browser():
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        shutil.which("msedge"),
        shutil.which("chrome")
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def main():
    print("===============================================================")
    print("  Starting Red Flag Engine Desktop Application...")
    print("===============================================================")
    
    port = find_free_port(8501)
    url = f"http://127.0.0.1:{port}"
    print(f"Allocated local port: {port}")
    
    # 1. Start Streamlit headless background server
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        os.path.join(APP_DIR, "app.py"),
        "--server.port", str(port),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ]
    
    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        
    proc = subprocess.Popen(
        cmd,
        cwd=APP_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )
    
    try:
        print("Waiting for analytical engine backend to initialize...")
        if not wait_for_server(url, timeout=35):
            print("Error: Engine backend initialization timed out.")
            proc.terminate()
            return 1
            
        print("Backend ready. Launching standalone desktop window...")
        browser_exe = find_app_browser()
        if browser_exe:
            # Isolated app profile to keep window process independent and alive
            profile_dir = os.path.join(
                os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", APP_DIR)),
                "RedFlagEngine_DesktopProfile"
            )
            os.makedirs(profile_dir, exist_ok=True)
            
            app_args = [
                browser_exe,
                f"--app={url}",
                f"--user-data-dir={profile_dir}",
                "--window-size=1340,890",
                "--window-position=50,50",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-features=TranslateUI",
                "--disable-extensions"
            ]
            win_proc = subprocess.Popen(app_args)
            print("Desktop application active. (Closing the window will stop the application)")
            win_proc.wait()
        else:
            # Fallback to web browser or pywebview
            try:
                import webview
                webview.create_window(
                    "Red Flag Engine — Forensic Accounting",
                    url=url,
                    width=1340,
                    height=890
                )
                webview.start(gui="edgechromium")
            except Exception:
                import webbrowser
                webbrowser.open(url)
                while proc.poll() is None:
                    time.sleep(1)
                    
    except KeyboardInterrupt:
        print("\nStopping desktop application...")
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        print("Application stopped cleanly.")

if __name__ == "__main__":
    sys.exit(main())
