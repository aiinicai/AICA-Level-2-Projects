import traceback
import logging
from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    completed=Signal(object)
    failed=Signal(str)
    def __init__(self,function,parent=None):
        super().__init__(parent)
        self.function=function

    def run(self):
        try:
            self.completed.emit(self.function())
        except Exception as exc:
            logging.getLogger("finstock").error("Background task failed: %s",type(exc).__name__)
            self.failed.emit(str(exc))

