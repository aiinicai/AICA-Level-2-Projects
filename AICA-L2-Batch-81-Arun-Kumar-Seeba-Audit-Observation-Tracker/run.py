import os
import sys
import time
import socket
import threading
import subprocess
import webbrowser

def get_free_port(preferred_ports=[8000, 8008, 8080, 8888, 5000]):
    for port in preferred_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'

def open_browser(url):
    time.sleep(1.2)
    try:
        webbrowser.open(url)
    except Exception:
        pass

def main():
    port = get_free_port()
    local_ip = get_local_ip()
    local_url = f"http://127.0.0.1:{port}/"
    network_url = f"http://{local_ip}:{port}/"

    print("=" * 68)
    print("   AUDIT OBSERVATION & QUERY TRACKER - CA PRACTICE PORTAL")
    print("=" * 68)
    print(f"  [Local Access (This PC)]:     {local_url}")
    print(f"  [Network Access (LAN/Wi-Fi)]: {network_url}")
    print("=" * 68)
    print()
    print("  Demo Login Credentials (Password for all: Password@123)")
    print("    - Partner:    partner1@firm.com       (CA Rajesh Sharma)")
    print("    - Manager:    manager1@firm.com       (CA Amit Verma)")
    print("    - Senior:     senior1@firm.com        (Rohan Deshmukh)")
    print("    - Article:    article1@firm.com       (Vikram Malhotra)")
    print("    - Client CFO: cfo@apexindustries.com  (Suresh Menon)")
    print("    - Admin:      admin@firm.com          (System Administrator)")
    print("-" * 68)
    print(f"  Starting server on 0.0.0.0:{port} ...")
    print("  Keep this window open while using the application.")
    print("  Press Ctrl+C in this window to stop the server.")
    print("=" * 68)

    # Launch browser in background thread
    threading.Thread(target=open_browser, args=(local_url,), daemon=True).start()

    # Start Django Server
    manage_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manage.py')
    cmd = [sys.executable, manage_py, 'runserver', f'0.0.0.0:{port}']
    try:
        subprocess.call(cmd)
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == '__main__':
    main()