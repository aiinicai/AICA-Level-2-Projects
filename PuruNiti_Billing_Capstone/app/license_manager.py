import os
import sys
import json
import hashlib
from datetime import datetime

# 25 Unique Keys (Case-insensitive, hyphen-insensitive matches)
LICENSE_MAP = {
    # 30 Days (5 Keys)
    "30D1A5B2C8D4E9F3": 30,
    "30D2K9L2M1N7P3Q8": 30,
    "30D3X7Y3Z1W9V4U8": 30,
    "30D4F5G6H1J2K9L0": 30,
    "30D5S3T7U1V9W2X8": 30,
    # 90 Days (5 Keys)
    "90D1Q8W2E3R9T1Y4": 90,
    "90D2A5S9D1F8G3H7": 90,
    "90D3Z2X8C4V1B9N3": 90,
    "90D4M1K9J2H8G3F7": 90,
    "90D5P5O1I9U2Y8T3": 90,
    # 180 Days (5 Keys)
    "180DU7I1O9P2L8K3": 180,
    "180DJ5H9G1F8D3S7": 180,
    "180DA2Q8W4E1R9T3": 180,
    "180DY1U9I2O8P3L7": 180,
    "180DX5C1V9B2N8M3": 180,
    # 365 Days (5 Keys)
    "365DQ1W9E2R8T3Y7": 365,
    "365DA4S8D2F9G1H3": 365,
    "365DZ5X1C9V2B8N3": 365,
    "365DM2K8J3H9G1F4": 365,
    "365DP6O2I8U3Y1T7": 365,
    # Perpetuity (5 Keys)
    "PERPF5D9S2A8K1L3": "perpetuity",
    "PERPH3J9G1F8D2S7": "perpetuity",
    "PERPX2C9V1B8N3M7": "perpetuity",
    "PERPQ5W1E9R2T8Y3": "perpetuity",
    "PERPA6S2D8F3G9H1": "perpetuity"
}

def get_base_dir():
    """Gets directory where the executable or main.py resides."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_config_path():
    """Gets absolute path to config.json."""
    return os.path.join(get_base_dir(), "config.json")

def get_config_hash(config):
    """Computes SHA256 checksum of license states to prevent notepad hacking."""
    key = config.get("license_key", "")
    activation = config.get("license_activation_date", "")
    last_run = config.get("last_run_date", "")
    # Obfuscated cryptographic salt
    salt = "puruniti_smart_secure_salt_2026"
    raw_data = f"{key}|{activation}|{last_run}|{salt}"
    return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

def load_config():
    """Loads config.json. If missing, returns default."""
    path = get_config_path()
    default_db = os.path.join(get_base_dir(), "database")
    default_config = {
        "database_path": default_db,
        "license_key": "",
        "license_activation_date": "",
        "last_run_date": "",
        "integrity_hash": ""
    }
    
    if not os.path.exists(path):
        save_config(default_config)
        return default_config
        
    try:
        with open(path, "r") as f:
            data = json.load(f)
            # Ensure all keys exist
            for k, v in default_config.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"Error loading config.json: {e}")
        return default_config

def save_config(config_data):
    """Saves config.json to disk, dynamically generating the security integrity hash."""
    path = get_config_path()
    try:
        # Calculate integrity hash before saving
        if config_data.get("license_key"):
            config_data["integrity_hash"] = get_config_hash(config_data)
        else:
            config_data["integrity_hash"] = ""
            
        with open(path, "w") as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config.json: {e}")
        return False

def clean_key(key):
    """Cleans spaces, hyphens, and converts to uppercase for comparison."""
    if not key:
        return ""
    return key.replace("-", "").replace(" ", "").upper().strip()

def validate_key(key):
    """Validates key against the 25 pre-generated keys."""
    cleaned = clean_key(key)
    if cleaned in LICENSE_MAP:
        return True, LICENSE_MAP[cleaned]
    return False, None

def check_license_status():
    """Verifies active license validity, remaining days, clock tampering, and file integrity."""
    config = load_config()
    key = config.get("license_key", "")
    activation_str = config.get("license_activation_date", "")
    last_run_str = config.get("last_run_date", "")
    recorded_hash = config.get("integrity_hash", "")
    
    if not key:
        return False, "License Not Activated", 0
        
    is_valid, duration = validate_key(key)
    if not is_valid:
        return False, "Invalid License Key", 0
        
    # Check integrity hash to prevent plaintext date spoofing
    calculated_hash = get_config_hash(config)
    if recorded_hash != calculated_hash:
        return False, "License Integrity Violation Detected! Please reactivate.", 0
        
    # Dates parsing
    try:
        activation_date = datetime.strptime(activation_str, "%Y-%m-%d").date()
        today = datetime.now().date()
    except Exception:
        return False, "Corrupted Activation Date", 0
        
    # Check system clock rollback
    if last_run_str:
        try:
            last_run_date = datetime.strptime(last_run_str, "%Y-%m-%d").date()
            if today < last_run_date:
                return False, "System Clock Tampering Detected! Please correct your clock.", 0
        except Exception:
            pass
            
    # Update last run date in config to today
    config["last_run_date"] = today.strftime("%Y-%m-%d")
    save_config(config)
    
    # Check duration expiration
    if duration == "perpetuity":
        return True, "Perpetual License", -1
    else:
        elapsed = (today - activation_date).days
        remaining = duration - elapsed
        
        if remaining <= 0:
            return False, f"License Expired {abs(remaining)} day(s) ago", 0
        else:
            return True, f"Active ({remaining} days remaining)", remaining

def activate_license(key):
    """Saves new license key to config with today's date if valid."""
    is_valid, duration = validate_key(key)
    if not is_valid:
        return False, "Key is not recognized. Please enter a valid 16-character license key."
        
    config = load_config()
    today_str = datetime.now().date().strftime("%Y-%m-%d")
    
    config["license_key"] = clean_key(key)
    config["license_activation_date"] = today_str
    config["last_run_date"] = today_str
    
    if save_config(config):
        return True, f"License activated successfully! Validity: {duration} days" if isinstance(duration, int) else "License activated successfully! Perpetual validity."
    return False, "Failed to save configuration settings."

def reset_license():
    """Removes current license from config.json."""
    config = load_config()
    config["license_key"] = ""
    config["license_activation_date"] = ""
    config["integrity_hash"] = ""
    # We preserve last run date to prevent resetting time cheats
    save_config(config)
