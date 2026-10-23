import sys


class Tray:
    """Optional system-tray icon (needs: pip install pystray pillow). Commands go through a queue."""

    def __init__(self, q):
        self.q = q
        self.icon = None
        self.ok = False

    def start(self):
        if sys.platform == "darwin":
            return False  # pystray conflicts with Tk mainloop on macOS
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            return False
        try:
            img = Image.new("RGB", (64, 64), "#0f172a")
            d = ImageDraw.Draw(img)
            d.ellipse((6, 6, 58, 58), fill="#3b82f6", outline="#60a5fa", width=3)
            d.rectangle((28, 16, 36, 48), fill="white")
            d.rectangle((16, 28, 48, 36), fill="white")
            put = lambda cmd: (lambda icon, item: self.q.put(cmd))
            menu = pystray.Menu(
                pystray.MenuItem("Open BreakBuddy Pro", put("open"), default=True),
                pystray.MenuItem("Toggle Floating Mini-HUD", put("hud")),
                pystray.MenuItem("Take a Break Now", put("break")),
                pystray.MenuItem("Start 25m Pomodoro Sprint", put("pomo")),
                pystray.MenuItem("I Drank Water (+1)", put("water")),
                pystray.MenuItem("Focus Mode 30m (DND)", put("dnd30")),
                pystray.MenuItem("Quit", put("quit")),
            )
            self.icon = pystray.Icon("BreakBuddyPro", img, "BreakBuddy Pro", menu)
            self.icon.run_detached()
            self.ok = True
        except Exception:
            self.ok = False
        return self.ok

    def stop(self):
        try:
            if self.icon:
                self.icon.stop()
        except Exception:
            pass
