import shutil
import os
from datetime import datetime
from utils.paths import get_database_path, get_backup_directory


def backup_database(destination_path=None):
    src = get_database_path()
    if destination_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination_path = os.path.join(get_backup_directory(),
                                         f"assetdeppro_backup_{timestamp}.db")
    shutil.copy2(src, destination_path)
    return destination_path


def restore_database(source_path):
    dest = get_database_path()
    backup_database()  # safety backup before restore
    shutil.copy2(source_path, dest)
    return dest