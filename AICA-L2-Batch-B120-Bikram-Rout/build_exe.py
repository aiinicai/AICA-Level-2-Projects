import os
import subprocess
import sys

def build():
    print("Building BRS_Tool.exe with PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=BRS_Tool",
        "--onefile",
        "--clean",
        "--add-data=frontend/static;frontend/static",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=fastapi",
        "--hidden-import=openpyxl",
        "--hidden-import=pandas",
        "--hidden-import=reportlab",
        "main.py"
    ]
    print("Executing command:", " ".join(cmd))
    res = subprocess.run(cmd, check=True)
    print("PyInstaller build finished with code:", res.returncode)

if __name__ == "__main__":
    build()
