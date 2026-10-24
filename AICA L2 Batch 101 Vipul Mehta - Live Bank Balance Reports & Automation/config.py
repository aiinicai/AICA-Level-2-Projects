import os
import sys
import json
from pathlib import Path

# --- Directory Configuration ---
SCRIPT_DIR = Path(__file__).parent.resolve()

env_data_dir = os.environ.get("BANK_DATA_DIR")
if env_data_dir and env_data_dir.strip():
    DATA_DIR = Path(env_data_dir).resolve()
else:
    DATA_DIR = SCRIPT_DIR

HDFC_DIR = DATA_DIR / "HDFC"
RBL_DIR = DATA_DIR / "RBL"

# Ensure directories exist
HDFC_DIR.mkdir(parents=True, exist_ok=True)
RBL_DIR.mkdir(parents=True, exist_ok=True)

# Helper to find file in subfolder or root folder
def resolve_file(folder: Path, filename: str) -> Path:
    subpath = folder / filename
    rootpath = DATA_DIR / filename
    if subpath.exists():
        return subpath
    elif rootpath.exists():
        return rootpath
    return subpath

# --- File Paths ---
HDFC_BALANCES_FILE = resolve_file(HDFC_DIR, "HDFC balances.xlsx")
HDFC_TRANSACTIONS_FILE = resolve_file(HDFC_DIR, "HDFC transactions.xlsx")
RBL_BALANCES_FILE = resolve_file(RBL_DIR, "RBL Balances.xlsx")
RBL_TRANSACTIONS_FILE = resolve_file(RBL_DIR, "RBL Transactions.xlsx")
BANK_SUMMARY_HTML = DATA_DIR / "bank_summary_latest.html"
BANK_SUMMARY_SNIPPET = DATA_DIR / "bank_summary_snippet.html"
BANK_ACCOUNTS_FILE = DATA_DIR / "bank_accounts.json"

# --- Centralized Bank Accounts & Banks Registry ---
DEFAULT_CONFIG = {
    "banks": {
        "HDFC": {"name": "HDFC Bank", "id_label": "Customer ID", "folder": "HDFC"},
        "RBL": {"name": "RBL Bank", "id_label": "User ID", "folder": "RBL"}
    },
    "accounts": {
        "HDFC": [
            {"code": "AB", "name": "ABCD", "id": "12345678", "active": True},
            {"code": "XY", "name": "PQRS", "id": "87654321", "active": True},
        ],
        "RBL": [
            {"code": "JK", "name": "LMNOP", "id": "XYZ", "active": True},
        ]
    }
}

def load_bank_config():
    """Load full config {'banks': {...}, 'accounts': {...}} from bank_accounts.json."""
    if BANK_ACCOUNTS_FILE.exists():
        try:
            with open(BANK_ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "banks" in data and "accounts" in data:
                        return data
                    # Backward compatibility if data was directly { "HDFC": [...], "RBL": [...] }
                    banks = {}
                    for k in data.keys():
                        banks[k] = {"name": f"{k} Bank", "id_label": "Customer ID", "folder": k}
                    return {"banks": banks, "accounts": data}
        except Exception as e:
            print(f"[WARN] Failed to read {BANK_ACCOUNTS_FILE}: {e}")
    save_bank_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG

def save_bank_config(config_data):
    """Save full config data to bank_accounts.json."""
    try:
        with open(BANK_ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save {BANK_ACCOUNTS_FILE}: {e}")
        return False

def load_bank_accounts():
    """Returns the dictionary of accounts by bank: {'HDFC': [...], 'RBL': [...]}."""
    cfg = load_bank_config()
    return cfg.get("accounts", {})

def save_bank_accounts(accounts_data):
    """Update only accounts in the config."""
    cfg = load_bank_config()
    cfg["accounts"] = accounts_data
    return save_bank_config(cfg)

def add_bank(bank_code, bank_name, balances_script="", txns_script="", balances_excel="", txns_excel=""):
    """Register a new bank with script and file mappings, and create its dedicated folder."""
    code = bank_code.strip().upper()
    if not code:
        return False, "Bank code cannot be empty"
    cfg = load_bank_config()
    if code in cfg.get("banks", {}):
        return False, f"Bank '{code}' already exists"
    
    # Create subfolder
    bank_dir = DATA_DIR / code
    bank_dir.mkdir(parents=True, exist_ok=True)
    
    cfg.setdefault("banks", {})[code] = {
        "name": bank_name.strip() or f"{code} Bank",
        "folder": code,
        "balances_script": balances_script.strip() or f"{code} balances.py",
        "txns_script": txns_script.strip() or f"{code} Transactions.py",
        "balances_excel": balances_excel.strip() or f"{code} balances.xlsx",
        "txns_excel": txns_excel.strip() or f"{code} transactions.xlsx"
    }
    cfg.setdefault("accounts", {})
    if code not in cfg["accounts"]:
        cfg["accounts"][code] = []
        
    if save_bank_config(cfg):
        return True, cfg
    return False, "Failed to save bank configuration"

def delete_bank(bank_code):
    """Delete a bank from config."""
    code = bank_code.strip().upper()
    cfg = load_bank_config()
    if code not in cfg.get("banks", {}):
        return False, f"Bank '{code}' does not exist"
    
    del cfg["banks"][code]
    if "accounts" in cfg and code in cfg["accounts"]:
        del cfg["accounts"][code]
        
    if save_bank_config(cfg):
        return True, cfg
    return False, "Failed to delete bank configuration"

def get_entity_names():
    """Returns a dictionary mapping account codes to full entity names."""
    accs = load_bank_accounts()
    mapping = {}
    for bank_code, items in accs.items():
        for item in items:
            code = item.get("code") or item.get("name")
            name = item.get("name") or code
            if code:
                mapping[code] = name
    return mapping

# --- Chrome/Chromium Detection ---
def get_chrome_path():
    """Return the Chrome executable path based on OS."""
    if sys.platform == "darwin":
        return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    elif sys.platform == "win32":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return paths[0]
    else:
        return "/usr/bin/google-chrome"

CHROME_PATH = get_chrome_path()

# --- Cross-Platform Password Prompt ---
def get_password(prompt="Enter Password (hidden): "):
    """Read password from stdin without echoing. Uses getpass on macOS/Linux."""
    if os.name == 'nt':
        import msvcrt
        print(prompt, end='', flush=True)
        password = ""
        while True:
            key = msvcrt.getch()
            if key in (b'\r', b'\n'):
                print('')
                break
            elif key == b'\x08':
                if len(password) > 0:
                    password = password[:-1]
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            elif key == b'\x03':
                raise KeyboardInterrupt
            else:
                try:
                    char = key.decode('utf-8')
                    password += char
                    sys.stdout.write('*')
                    sys.stdout.flush()
                except UnicodeDecodeError:
                    pass
        return password
    else:
        import getpass
        return getpass.getpass(prompt)
