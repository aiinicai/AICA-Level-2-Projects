import configparser
from pathlib import Path
import os

def load_config(config_path="config.ini"):
    """
    Loads and validates the configuration file.
    Raises ValueError if configuration is malformed.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path.absolute()}")

    config = configparser.ConfigParser()
    config.read(path)
    
    # Validation
    if 'application' not in config:
        raise ValueError("Missing [application] section in config.")
        
    try:
        port = config.getint('application', 'port', fallback=8765)
        if not (1024 <= port <= 65535):
            raise ValueError(f"Port {port} is out of valid range (1024-65535).")
    except ValueError as e:
        raise ValueError(f"Invalid port configuration: {e}")

    return config

def get_secret_key():
    """
    Generate or load a stable Flask secret key for local development.
    Stored in an ignored .secret file.
    """
    secret_path = Path(".secret")
    if secret_path.exists():
        return secret_path.read_bytes()
    else:
        new_secret = os.urandom(24)
        secret_path.write_bytes(new_secret)
        return new_secret
