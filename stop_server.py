import subprocess
import os

def stop():
    print("==================================================================")
    print("             STOPPING GS STOCK AUDIT TRACKER SERVER               ")
    print("==================================================================")
    print()
    
    stopped = False
    try:
        out = subprocess.check_output('netstat -ano | findstr :8501', shell=True).decode()
        for line in out.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5 and 'LISTENING' in parts:
                pid = parts[-1]
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[OK] Terminated background process (PID: {pid})")
                stopped = True
    except Exception:
        pass
        
    if stopped:
        print("\n[SUCCESS] GS Stock Audit Tracker background server has been stopped cleanly.")
    else:
        print("[INFO] No running server found on port 8501.")
    print()
    print("==================================================================")

if __name__ == "__main__":
    stop()
