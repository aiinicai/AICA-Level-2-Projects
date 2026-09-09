import sys
import os
import traceback
from utils.logging_utils import get_logger
from utils import paths

def main():
    # ENSURE DIRECTORIES EXIST
    paths.get_app_data_dir()
    paths.get_report_directory()
    paths.get_log_directory()
    paths.get_backup_directory()

    logger = get_logger()
    try:
        import database
        database.initialize_database()
        from gui.main_window import run_app
        run_app()
    except Exception as exc:
        logger.exception("Fatal error while starting AssetDepPro")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("AssetDepPro - Startup Error",
                                  f"Startup error: {exc}\nCheck logs/assetdeppro.log")
            root.destroy()
        except Exception:
            print("Fatal error:", exc)
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()