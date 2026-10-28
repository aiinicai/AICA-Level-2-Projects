"""CA GST Filing Assistant - entry point."""
import sys
import tkinter as tk
from tkinter import messagebox

from app import config


def main():
    config.setup_logging()
    try:
        from app.ui import App
        App().mainloop()
    except Exception as e:  # noqa
        import logging
        logging.getLogger("main").exception("Fatal error")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(config.APP_NAME, f"The application could not start:\n{e}\n\n"
                                 f"See log: {config.LOG_DIR / 'app.log'}")
        finally:
            sys.exit(1)


if __name__ == "__main__":
    main()
