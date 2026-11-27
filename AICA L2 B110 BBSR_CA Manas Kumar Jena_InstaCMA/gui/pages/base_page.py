"""Common page frame: title, subtitle, scrollable body."""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame


class BasePage(QWidget):
    title = ""
    subtitle = ""
    scroll = True

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 14, 22, 14)
        t = QLabel(self.title)
        t.setObjectName("PageTitle")
        s = QLabel(self.subtitle)
        s.setObjectName("PageSub")
        s.setWordWrap(True)
        outer.addWidget(t)
        outer.addWidget(s)
        body = QWidget()
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(0, 0, 0, 0)
        if self.scroll:
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QFrame.NoFrame)
            sa.setWidget(body)
            outer.addWidget(sa)
        else:
            outer.addWidget(body)
        self.build()

    def build(self):
        pass

    def refresh(self):
        pass

    @property
    def project(self):
        return self.app.project

    @property
    def result(self):
        return self.app.result
