#!/usr/bin/env python3
import os
import sys
import signal
import subprocess
import time
from pathlib import Path

def kill_port(port=10001):
    """Kills any process currently listening on the specified port."""
    try:
        out = subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True).strip()
        pids = [int(p) for p in out.split() if p.isdigit()]
        for pid in pids:
            if pid != os.getpid():
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"Freed port {port} (killed PID {pid})")
                except ProcessLookupError:
                    pass
        if pids:
            time.sleep(0.5)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

def main():
    # Change to the directory of this script so relative paths work
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)
    
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    
    # Kill any existing process on port 10001
    kill_port(10001)
    
    # Launch the bank dashboard
    print("Starting Bank Dashboard...")
    subprocess.Popen([sys.executable, "-B", "bank_dashboard.py"])

if __name__ == "__main__":
    main()
