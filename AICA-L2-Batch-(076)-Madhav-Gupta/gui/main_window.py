import tkinter as tk
from config import APP_NAME, APP_SUBTITLE, APP_FOOTER
from gui.dashboard import DashboardFrame
from gui.asset_master import AssetMasterFrame
from gui.categories import CategoriesFrame
from gui.asset_register import AssetRegisterFrame
from gui.depreciation_run import DepreciationRunFrame
from gui.disposal import DisposalFrame
from gui.reports import ReportsFrame
from gui.settings import SettingsFrame
from gui.about import AboutFrame


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - {APP_SUBTITLE}")
        self.geometry("1280x800")
        self.minsize(1024, 700)
        self._build_header()
        self._build_body()
        self._build_footer()
        self.show_frame("Dashboard")

    def _build_header(self):
        header = tk.Frame(self, bg="#1F2937", height=70)
        header.pack(side="top", fill="x")
        tk.Label(header, text=APP_NAME, bg="#1F2937", fg="white",
                 font=("Segoe UI", 20, "bold")).pack(side="left", padx=20, pady=10)
        tk.Label(header, text=APP_SUBTITLE, bg="#1F2937", fg="#D1D5DB",
                 font=("Segoe UI", 11)).pack(side="left", padx=10)

    def _build_body(self):
        body = tk.Frame(self)
        body.pack(side="top", fill="both", expand=True)

        sidebar = tk.Frame(body, bg="#111827", width=220)
        sidebar.pack(side="left", fill="y")

        self.container = tk.Frame(body, bg="#F3F4F6")
        self.container.pack(side="right", fill="both", expand=True)

        self.frames = {}
        nav_items = [
            ("Dashboard", DashboardFrame),
            ("Asset Master", AssetMasterFrame),
            ("Asset Categories", CategoriesFrame),
            ("Asset Register", AssetRegisterFrame),
            ("Depreciation Run", DepreciationRunFrame),
            ("Asset Disposal", DisposalFrame),
            ("Reports", ReportsFrame),
            ("Settings", SettingsFrame),
            ("About", AboutFrame),
        ]
        for name, frame_cls in nav_items:
            frame = frame_cls(self.container, self)
            self.frames[name] = frame
            frame.place(relwidth=1, relheight=1)

        for name, _ in nav_items:
            tk.Button(sidebar, text=name, anchor="w", bg="#111827", fg="white",
                      activebackground="#374151", activeforeground="white",
                      relief="flat", font=("Segoe UI", 11), padx=15, pady=10,
                      command=lambda n=name: self.show_frame(n)).pack(fill="x")

        tk.Button(sidebar, text="Exit", anchor="w", bg="#7F1D1D", fg="white",
                  relief="flat", font=("Segoe UI", 11), padx=15, pady=10,
                  command=self.destroy).pack(fill="x", side="bottom")

    def _build_footer(self):
        footer = tk.Frame(self, bg="#1F2937", height=30)
        footer.pack(side="bottom", fill="x")
        tk.Label(footer, text=APP_FOOTER, bg="#1F2937", fg="#D1D5DB",
                 font=("Segoe UI", 9)).pack(pady=4)

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()


def run_app():
    app = MainWindow()
    app.mainloop()