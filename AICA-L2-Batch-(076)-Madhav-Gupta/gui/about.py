import tkinter as tk
import sys
from config import APP_NAME, APP_SUBTITLE, APP_FOOTER, APP_VERSION, DB_VERSION


class AboutFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F3F4F6")
        self.app = app
        self._build()

    def _build(self):
        tk.Label(self, text=APP_NAME, font=("Segoe UI", 24, "bold"), bg="#F3F4F6").pack(pady=(40, 5))
        tk.Label(self, text=APP_SUBTITLE, font=("Segoe UI", 13), bg="#F3F4F6").pack(pady=5)
        tk.Label(self, text=f"Version: {APP_VERSION}", bg="#F3F4F6").pack(pady=2)
        tk.Label(self, text=f"Database Version: {DB_VERSION}", bg="#F3F4F6").pack(pady=2)
        tk.Label(self, text=f"Python Version: {sys.version.split()[0]}", bg="#F3F4F6").pack(pady=2)
        tk.Label(self, text=APP_FOOTER, font=("Segoe UI", 11, "bold"), bg="#F3F4F6").pack(pady=20)

        disclaimer = ("This application is designed for calculation and educational purposes. "
                      "Users must verify the applicable provisions of the Companies Act, applicable "
                      "accounting standards, Income-tax Act, Income-tax Rules, notifications, circulars "
                      "and other applicable requirements before relying on the calculations for "
                      "statutory, tax, audit or reporting purposes.")
        tk.Label(self, text=disclaimer, wraplength=700, justify="left", bg="#F3F4F6",
                 fg="#7F1D1D").pack(padx=40, pady=10)

    def on_show(self):
        pass