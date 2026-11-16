import sys

from PySide6.QtCore import QObject, Signal


import logging
import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon


class WindowsNotificationSink(QObject):
    activated=Signal(str,str)
    failed=Signal(str,str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.toaster=None
        self.toaster_failed=False
        self.retained=[]
        self.current_job=None
        # Connect to parent's tray if available
        if parent and hasattr(parent, "tray"):
            try:
                parent.tray.messageClicked.connect(self._on_tray_clicked)
            except Exception:
                pass

    def _on_tray_clicked(self):
        if self.current_job:
            self.activated.emit(self.current_job["id"], self.current_job["event_id"])

    def initialize(self):
        if sys.platform!="win32":
            raise RuntimeError("Native Windows notifications require Windows 10/11")
        try:
            import winreg
            from windows_toasts import InteractableWindowsToaster
            app_id="Finstock.EventScope"
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,rf"SOFTWARE\Classes\AppUserModelId\{app_id}") as key:
                    winreg.SetValueEx(key,"DisplayName",0,winreg.REG_SZ,"Finstock EventScope")
            except Exception:
                pass
            self.toaster=InteractableWindowsToaster("Finstock EventScope",notifierAUMID=app_id)
        except Exception as exc:
            logging.getLogger("finstock").warning("Native WinRT toaster unavailable (%s); using system tray toast fallback", exc)
            self.toaster_failed=True

    def send(self,job):
        self.current_job = job
        if not self.toaster_failed and self.toaster is None:
            self.initialize()

        sent = False
        if not self.toaster_failed and self.toaster is not None:
            try:
                from windows_toasts import Toast,ToastDuration
                toast=Toast(text_fields=[job["title"],job["body"]],attribution_text="Finstock Capital · EventScope",duration=ToastDuration.Long)
                toast.tag=job["id"]
                toast.group="eventscope"
                toast.on_activated=lambda args:self.activated.emit(job["id"],job["event_id"])
                toast.on_failed=lambda args:self.failed.emit(job["id"],"Windows reported that this notification failed")
                self.toaster.show_toast(toast)
                self.retained.append(toast)
                self.retained=self.retained[-200:]
                sent = True
            except Exception as exc:
                logging.getLogger("finstock").warning("WinRT show_toast failed (%s); falling back to system tray notification", exc)
                self.toaster_failed = True

        if not sent:
            # Native Windows Shell / System Tray Notification Fallback
            parent = self.parent()
            tray = getattr(parent, "tray", None) if parent else None
            if tray is not None and QSystemTrayIcon.isSystemTrayAvailable():
                try:
                    tray.showMessage(job["title"], job["body"], QSystemTrayIcon.Information, 10000)
                    sent = True
                except Exception as exc:
                    self.failed.emit(job["id"], f"Tray notification error: {exc}")
                    raise
            else:
                self.failed.emit(job["id"], "No available notification channel on this system")
                raise RuntimeError("No available notification channel on this system")

