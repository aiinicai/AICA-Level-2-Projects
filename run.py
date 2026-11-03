"""Dune Company - Physical Stock Count App launcher.
Installs missing libraries automatically, then starts the server.
Run:  python run.py
"""
import subprocess
import sys

REQUIRED = {"flask": "flask", "openpyxl": "openpyxl"}  # import name -> pip name


def ensure_libs():
    import importlib
    for mod, pipname in REQUIRED.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            print(f"[setup] Installing {pipname} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pipname])


if __name__ == "__main__":
    if not getattr(sys, "frozen", False):  # the packaged .exe already contains the libraries
        ensure_libs()
    import server
    server.init_db()
    print("\n  Dune Count is running")
    print("  Count Admin   : http://localhost:5000/admin/")
    print("  Count Persons : http://localhost:5000/counter/")
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        print("\n  SHARE THIS LINK with the count team (same Wi-Fi / network):")
        print("  http://%s:5000/counter/" % ip)
    except Exception:
        pass
    print("  Keep this window open while using the app. Press CTRL+C to stop.\n")
    import logging, threading, webbrowser
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import flask.cli
    flask.cli.show_server_banner = lambda *a, **k: None
    threading.Timer(1.2, lambda: webbrowser.open("http://localhost:5000/admin/")).start()
    server.app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
