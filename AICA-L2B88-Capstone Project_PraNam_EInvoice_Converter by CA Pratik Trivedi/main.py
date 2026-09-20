"""PraNam E-Invoice Converter - start the desktop application."""
import sys
import traceback


def main():
    try:
        from pec.gui.main_window import run
        run()
    except Exception:
        from pec.logsetup import get_logger
        get_logger().error("Fatal: %s", traceback.format_exc())
        try:
            import tkinter.messagebox as mb
            mb.showerror("PraNam E-Invoice Converter", "The application hit an unexpected error. See logs/app.log.")
        except Exception:
            print(traceback.format_exc(), file=sys.stderr)


if __name__ == "__main__":
    main()
