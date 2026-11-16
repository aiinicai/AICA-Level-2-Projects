"""Local PDF rendering through PyMuPDF, displayed in native PyQt widgets."""
from enum import Enum
import pymupdf
from PyQt6.QtCore import QSizeF,Qt
from PyQt6.QtGui import QImage,QPixmap
from PyQt6.QtWidgets import QScrollArea,QWidget,QVBoxLayout,QLabel

class QPdfDocument:
    class Error(Enum):
        None_=0
        Failed=1
    def __init__(self,parent=None): self.document=None
    def load(self,path):
        try: self.document=pymupdf.open(path); return self.Error.None_
        except Exception: return self.Error.Failed
    def pageCount(self): return len(self.document)
    def pagePointSize(self,page):
        rect=self.document[page].rect; return QSizeF(rect.width,rect.height)
    def render(self,page,size):
        obj=self.document[page]; rect=obj.rect
        pix=obj.get_pixmap(matrix=pymupdf.Matrix(size.width()/rect.width,size.height()/rect.height),alpha=False)
        return QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
    def getAllText(self,page):
        class Text:
            def __init__(self,value): self.value=value
            def text(self): return self.value
        return Text(self.document[page].get_text())
    def close(self):
        if self.document: self.document.close(); self.document=None
    def deleteLater(self): self.close()

class QPdfView(QScrollArea):
    class PageMode: MultiPage=1
    class ZoomMode: FitToWidth=1
    def setPageMode(self,*args): pass
    def setZoomMode(self,*args): pass
    def setDocument(self,doc):
        from PyQt6.QtCore import QSize
        body=QWidget(); layout=QVBoxLayout(body)
        for page in range(doc.pageCount()):
            size=doc.pagePointSize(page); label=QLabel(); label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setPixmap(QPixmap.fromImage(doc.render(page,QSize(760,round(760*size.height()/size.width())))))
            layout.addWidget(label)
        self.setWidget(body); self.setWidgetResizable(True)
