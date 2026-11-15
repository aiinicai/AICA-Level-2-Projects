"""Office Manager launcher.

  python run_desktop.py            -> starts the server and opens the desktop window (the office "host" PC, or a single-PC setup)
  python run_desktop.py --server   -> server only, no window (leave running on the host PC; staff use their browsers)
  python run_desktop.py --window http://192.168.1.10:8765
                                   -> window only, for another PC that connects to the host PC
"""
import argparse
import socket
import sys
import threading
import time
import webbrowser


def lan_address() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def wait_for(port: int, seconds: float = 15) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            return True
        except OSError:
            time.sleep(0.2)
    return False


class Api:
    """Functions the screens can call when running inside the desktop window."""

    def pick_folder(self):
        import webview

        try:
            kind = getattr(webview, "FOLDER_DIALOG", None)
            if kind is None:
                kind = webview.FileDialog.FOLDER
            result = webview.windows[0].create_file_dialog(kind)
            return result[0] if result else ""
        except Exception:
            return ""


def open_window(url: str) -> None:
    try:
        import webview
    except Exception:
        print("Desktop window support is not available; opening your web browser instead.")
        webbrowser.open(url)
        return
    try:
        webview.settings["ALLOW_DOWNLOADS"] = True  # lets the window save PDF / Excel / backup files
    except Exception:
        pass
    # Fit whatever screen this PC has: open maximised; if that is not supported, use 92% of the screen.
    width, height = 1360, 860
    try:
        scr = webview.screens[0]
        width, height = max(1000, int(scr.width * 0.92)), max(650, int(scr.height * 0.88))
    except Exception:
        pass
    try:
        webview.create_window("Office Manager", url, width=width, height=height, min_size=(900, 600), maximized=True, js_api=Api())
    except TypeError:  # older pywebview without "maximized"
        webview.create_window("Office Manager", url, width=width, height=height, min_size=(900, 600), js_api=Api())
    webview.start()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", action="store_true", help="run the server only (no window)")
    ap.add_argument("--window", metavar="URL", help="open a window to an Office Manager server running on another PC")
    args = ap.parse_args()

    if args.window:
        open_window(args.window)
        return 0

    from waitress import serve
    from audit_manager import create_app
    from audit_manager.config import network_settings

    cfg = network_settings()
    port = int(cfg["port"])
    app = create_app()
    t = threading.Thread(target=lambda: serve(app, host=cfg["host"], port=port, threads=8), daemon=True)
    t.start()
    if not wait_for(port):
        print("The server did not start. Is another program using port", port, "?")
        return 1
    print(f"Office Manager is running.\n  On this PC:      http://127.0.0.1:{port}\n  Other office PCs: http://{lan_address()}:{port}")
    def backup_on_close():
        try:
            with app.app_context():
                from audit_manager.services import backup

                if backup.on_close():
                    print("Backup saved on closing.")
        except Exception as exc:  # never block closing
            print("Backup on closing failed:", exc)

    if args.server:
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            backup_on_close()
            return 0
    open_window(f"http://127.0.0.1:{port}")
    backup_on_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
