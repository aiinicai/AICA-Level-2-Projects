"""CA Task Mitra launcher. Run:  python run.py   (or build CA-Task-Mitra.exe with build_exe.bat)"""
import sys
from core import server

if __name__ == "__main__":
    port = 8765
    for a in sys.argv[1:]:
        if a.startswith("--port="):
            port = int(a.split("=")[1])
    server.run(port, open_browser="--no-browser" not in sys.argv)
