"""
Enterprise Forensic Audit & Benford's Law Suite (Indian DPDP Act, 2023 Compliant)
Standalone Desktop Launcher.
"""

import os
import sys
import time
import webbrowser
import threading
import multiprocessing
import traceback

# Ensure console handles UTF-8 gracefully on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BANNER = """
================================================================================
   ENTERPRISE FORENSIC AUDIT & BENFORD'S LAW SUITE
   (INDIAN DIGITAL PERSONAL DATA PROTECTION ACT, 2023 COMPLIANT)
================================================================================
 [OK] Statistical Engine: Nigrini 1D, 2D, F2D, F3D, L2D, Mantissa Arc, MAD Scale
 [OK] Forensic Tests: RSF Outliers, Duplicate Payments, Smurfing Evasion, Round Numbers
 [OK] Indian DPDP 2023: Role & Governance, Verhoeff Aadhaar, PAN/GSTIN, HMAC Tokenizer
 [OK] Security Shell: Air-Gapped Zero Cloud Egress, SHA-256 Chained Audit Ledger
================================================================================
"""

def open_browser(url: str, delay: float = 1.5):
    """Opens default browser after server initializes."""
    time.sleep(delay)
    print(f"\n[*] Launching Executive Forensic Interface at: {url}\n")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[!] Could not auto-open browser: {e}")

def main():
    print(BANNER)
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"

    # Auto-open browser in background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    print(f"[*] Starting local air-gapped forensic audit server on {url} ...")
    print("[*] Press Ctrl+C to terminate the audit session gracefully.\n")

    # Import uvicorn and app directly as objects to support PyInstaller frozen binaries
    import uvicorn
    from backend.app.main import app

    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] Audit session terminated gracefully by auditor.")
    except Exception as e:
        print("\n" + "="*80)
        print("[!] CRITICAL APPLICATION LAUNCH EXCEPTION:")
        traceback.print_exc()
        print("="*80)
        input("\nPress Enter to exit...")
