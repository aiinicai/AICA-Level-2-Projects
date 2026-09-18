import sys
import subprocess
from typing import List, Dict, Any

def get_installed_printers() -> List[Dict[str, Any]]:
    """
    Enumerate installed Windows printers via win32print or PowerShell.
    """
    printers = []
    
    # Try win32print first
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printer_list = win32print.EnumPrinters(flags)
        default_printer = win32print.GetDefaultPrinter()
        
        for p in printer_list:
            p_name = p[2]
            printers.append({
                "name": p_name,
                "is_default": (p_name == default_printer),
                "driver_name": p[1],
                "port": p[3] if len(p) > 3 else "N/A"
            })
        return printers
    except Exception:
        pass

    # Fallback to PowerShell
    try:
        cmd = ["powershell", "-Command", "Get-Printer | Select-Object Name, Type, DriverName | ConvertTo-Json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout:
            import json
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                printers.append({
                    "name": item.get("Name", "Unknown"),
                    "is_default": False,
                    "driver_name": item.get("DriverName", ""),
                    "port": "PowerShell"
                })
            return printers
    except Exception:
        pass

    # Virtual/fallback mock printers for development/test
    if not printers:
        printers = [
            {"name": "Microsoft Print to PDF", "is_default": True, "driver_name": "Microsoft Print To PDF", "port": "PORTPROMPT:"},
            {"name": "Zebra ZD420 (Demo Thermal)", "is_default": False, "driver_name": "Zebra ZDesigner", "port": "USB001"},
            {"name": "Brother QL-800 (Demo)", "is_default": False, "driver_name": "Brother QL-800", "port": "USB002"},
            {"name": "DYMO LabelWriter 450", "is_default": False, "driver_name": "DYMO", "port": "USB003"},
            {"name": "TSC TTP-244 Pro", "is_default": False, "driver_name": "TSC", "port": "USB004"}
        ]
    return printers

def print_raw_or_pdf(printer_name: str, pdf_bytes: bytes) -> bool:
    """
    Submits a print job to the Windows Print Spooler.
    """
    try:
        import win32print
        import win32api
        
        # Save temp file for printing
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            temp_path = f.name
            
        try:
            # Use ShellExecute with 'printto' action
            win32api.ShellExecute(0, "printto", temp_path, f'"{printer_name}"', ".", 0)
            return True
        except Exception:
            # Fallback direct spool
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Asset Tag Print Job", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, pdf_bytes)
                    win32print.EndPagePrinter(hPrinter)
                finally:
                    win32print.EndDocPrinter(hPrinter)
                return True
            finally:
                win32print.ClosePrinter(hPrinter)
    except Exception as e:
        print(f"Printing error: {e}")
        return False
