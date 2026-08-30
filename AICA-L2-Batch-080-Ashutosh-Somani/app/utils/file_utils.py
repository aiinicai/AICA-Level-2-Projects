from pathlib import Path
import configparser

def ensure_directories(config: configparser.ConfigParser):
    """
    Creates required folders if missing at startup.
    Uses paths specified in config or defaults.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    
    directories = [
        config.get('paths', 'output', fallback='output'),
        config.get('paths', 'logs', fallback='logs'),
        config.get('paths', 'temp', fallback='temp'),
        config.get('paths', 'profiles', fallback='profiles'),
        config.get('paths', 'backups', fallback='backups'),
        config.get('paths', 'sample_data', fallback='sample_data'),
        config.get('paths', 'docs', fallback='docs'),
    ]
    
    # Database dir is derived from database file path
    db_path = config.get('paths', 'database', fallback='database/bank_statement_converter.db')
    directories.append(str(Path(db_path).parent))
    
    for dir_path in directories:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
