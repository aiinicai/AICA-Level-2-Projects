import os
import sys

APP_FOLDER_NAME = "AssetDepPro"


def is_frozen():
    return getattr(sys, "frozen", False)


def get_app_data_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/.local/share")
    path = os.path.join(base, APP_FOLDER_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def get_database_path():
    d = os.path.join(get_app_data_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "assetdeppro.db")


def get_report_directory():
    d = os.path.join(get_app_data_dir(), "reports_output")
    os.makedirs(d, exist_ok=True)
    return d


def get_log_directory():
    d = os.path.join(get_app_data_dir(), "logs")
    os.makedirs(d, exist_ok=True)
    return d


def get_backup_directory():
    d = os.path.join(get_app_data_dir(), "backups")
    os.makedirs(d, exist_ok=True)
    return d