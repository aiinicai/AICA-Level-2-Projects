import pytest
from app.utils.config_utils import load_config
from app.utils.file_utils import ensure_directories
import configparser

def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.ini")

def test_load_config_invalid_port(tmp_path):
    config_file = tmp_path / "test.ini"
    config_file.write_text("[application]\nport = 999999\n")
    with pytest.raises(ValueError, match="Invalid port"):
        load_config(str(config_file))

def test_ensure_directories(temp_config):
    # Ensure they don't exist yet
    for key, val in temp_config.items('paths'):
        if key != 'database':
            assert not __import__('pathlib').Path(val).exists()
            
    ensure_directories(temp_config)
    
    # Ensure they do exist now
    for key, val in temp_config.items('paths'):
        if key != 'database':
            assert __import__('pathlib').Path(val).exists()
        else:
            assert __import__('pathlib').Path(val).parent.exists()
