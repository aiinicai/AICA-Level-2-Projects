import sys
import os
import io
import queue
from threading import Thread

# PyQt5 Imports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QRadioButton, QComboBox,
    QTextEdit, QFileDialog, QMessageBox, QGroupBox, QFrame, QListWidget,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem,
    QGraphicsItem, QSplitter
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont, QPen, QColor, QBrush, QPainter

# PDF Engine Imports
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas


# ==========================================
# MODERN STYLESHEET (GLOBAL THEME)
# ==========================================
MODERN_STYLE = """
QMainWindow { background-color: #f4f6f8; }
QFrame#Sidebar { background-color: #1e2530; border-right: 1px solid #141923; }
QPushButton#NavButton {
    background-color: transparent; color: #a0aabe; text-align: left;
    padding: 10px 12px; border: none; border-radius: 6px; font-size: 9.5pt; font-weight: 600;
}
QPushButton#NavButton:hover { background-color: #2a3447; color: #ffffff; }
QPushButton#NavButton:checked { background-color: #0078d4; color: #ffffff; }
QGroupBox {
    background-color: #ffffff; border: 1px solid #e1e5eb; border-radius: 8px;
    margin-top: 10px; font-size: 8.5pt; font-weight: bold; color: #333333; padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 0 6px; background-color: #ffffff; color: #0078d4;
}
QLineEdit, QComboBox, QTextEdit {
    background-color: #fcfdfe; border: 1px solid #dcdfe6; border-radius: 5px;
    padding: 5px 8px; font-size: 8.5pt; color: #2c3e50;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid #0078d4; background-color: #ffffff; }
QRadioButton { font-size: 8.5pt; color: #4a5568; spacing: 5px; }
QPushButton#PrimaryBtn {
    background-color: #0078d4; color: white; font-weight: bold; font-size: 8.5pt;
    padding: 7px 14px; border: none; border-radius: 5px;
}
QPushButton#PrimaryBtn:hover { background-color: #005a9e; }
QPushButton#HeaderActionBtn {
    background-color: #ffffff; color: #2c3e50; font-weight: bold; font-size: 8.5pt;
    padding: 6px 12px; border: 1px solid #dcdfe6; border-radius: 5px;
}
QPushButton#HeaderActionBtn:hover { background-color: #f0f4f8; border-color: #0078d4; }
QPushButton#SuccessBtn {
    background-color: #107c41; color: white; font-weight: bold; font-size: 8.5pt;
    padding: 7px 14px; border: none; border-radius: 5px;
}
QPushButton#SuccessBtn:hover { background-color: #0b5a2f; }
"""


# ==========================================
# RESIZABLE SIGNATURE ITEM
# ==========================================
class ResizableSignatureItem(QGraphicsItem):
    def __init__(self, content_item, is_text=True):
        super().__init__()
        self.content_item = content_item
        self.content_item.setParentItem(self)
        self.is_text = is_text
        
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        
        self.handle_size = 10
        self.resizing = False
        self.scale_factor = 1.0

    def boundingRect(self):
        rect = self.content_item.boundingRect()
        return rect.adjusted(-5, -5, self.handle_size + 5, self.handle_size + 5)

    def paint(self, painter, option, widget):
        rect = self.content_item.boundingRect()
        
        if self.isSelected():
            painter.setPen(QPen(QColor("#0078d4"), 1.5, Qt.DashLine))
            painter.setBrush(Qt.transparent)
            painter.drawRect(rect)
            
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(QBrush(QColor("#ff4d4d")))
            painter.drawRect(QRectF(rect.right(), rect.bottom(), self.handle_size, self.handle_size))

    def mousePressEvent(self, event):
        rect = self.content_item.boundingRect()
        handle_rect = QRectF(rect.right(), rect.bottom(), self.handle_size, self.handle_size)
        if handle_rect.contains(event.pos()) and self.isSelected():
            self.resizing = True
        else:
            self.resizing = False
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            pos = event.pos()
            rect = self.content_item.boundingRect()
            new_w = max(30, pos.x() - rect.left())
            orig_w = rect.width()
            if orig_w > 0:
                self.scale_factor = new_w / orig_w
                self.setScale(self.scale_factor)
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        super().mouseReleaseEvent(event)


# ==========================================
# CUSTOM GRAPHICS VIEW
# ==========================================
class InteractivePDFView(QGraphicsView):
    def __init__(self, scene, viewer_widget):
        super().__init__(scene)
        self.viewer = viewer_widget
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            if hasattr(self.viewer, 'app') and self.viewer.app.stack.currentIndex() == 3:
                if hasattr(self.viewer, 'signer_panel') and self.viewer.signer_panel.interactive_mode:
                    if not getattr(self.viewer.signer_panel, 'is_signing_active', False):
                        return
                        
                    scene_pos = self.mapToScene(event.pos())
                    item = self.scene().itemAt(scene_pos, self.transform())
                    if item is None or isinstance(item, QGraphicsPixmapItem):
                        self.viewer.signer_panel.add_interactive_signature(scene_pos)


# ==========================================
# PDF VIEWER WIDGET
# ==========================================
class PDFViewerWidget(QWidget):
    def __init__(self, app_ref=None):
        super().__init__()
        self.app = app_ref
        self.doc = None
        self.current_file_path = ""
        self.is_modified = False
        self.on_file_loaded_callbacks = []
        self.page_render_y_offsets = []
        self.signer_panel = None

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.scene = QGraphicsScene(self)
        self.graphics_view = InteractivePDFView(self.scene, self)
        self.graphics_view.setAlignment(Qt.AlignCenter)
        self.graphics_view.setStyleSheet("background-color: #525659; border: none;")

        layout.addWidget(self.graphics_view)
        self.setLayout(layout)
        self.show_placeholder()

    def add_file_loaded_callback(self, callback):
        self.on_file_loaded_callbacks.append(callback)

    def get_working_dir(self):
        if self.current_file_path and os.path.exists(self.current_file_path):
            return os.path.dirname(self.current_file_path)
        return ""

    def show_placeholder(self):
        self.scene.clear()
        text_item = self.scene.addText("📄 No Document Opened\n\nClick '📂 Open' on top bar")
        text_item.setDefaultTextColor(QColor("#d1d5db"))
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        text_item.setFont(font)
        text_item.setPos(-160, -30)

        for cb in self.on_file_loaded_callbacks:
            cb(0)

    def load_pdf(self, file_path_or_bytes):
        try:
            self.scene.clear()
            self.page_render_y_offsets.clear()

            if isinstance(file_path_or_bytes, str):
                self.current_file_path = file_path_or_bytes
                self.doc = fitz.open(self.current_file_path)
            else:
                self.doc = fitz.open("pdf", file_path_or_bytes)

            y_offset = 0
            spacing = 15
            max_width = 0

            for page_num in range(len(self.doc)):
                page = self.doc.load_page(page_num)
                pix = page.get_pixmap(dpi=130)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(img)

                if pixmap.width() > max_width:
                    max_width = pixmap.width()

                self.page_render_y_offsets.append((y_offset, pixmap.width(), pixmap.height(), page.rect.width, page.rect.height))

                pix_item = QGraphicsPixmapItem(pixmap)
                pix_item.setPos(0, y_offset)
                pix_item.setZValue(-100)
                self.scene.addItem(pix_item)

                y_offset += pixmap.height() + spacing

            self.scene.setSceneRect(-20, -20, max_width + 40, y_offset + 40)

            QTimer.singleShot(50, lambda: self.graphics_view.fitInView(0, 0, max_width, max_width * 0.8, Qt.KeepAspectRatio))

            for cb in self.on_file_loaded_callbacks:
                cb(len(self.doc))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load PDF Preview: {str(e)}")

    def close_document(self):
        if self.doc:
            self.doc.close()
            self.doc = None
        self.current_file_path = ""
        self.is_modified = False
        self.show_placeholder()


# ==========================================
# 1. MASKED CONTENT PANEL
# ==========================================
class MaskerPanel(QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.processing_queue = queue.Queue()

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_title = QLabel("Masked Content")
        lbl_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #1e2530;")
        layout.addWidget(lbl_title)

        mask_box = QGroupBox("Sensitive Terms / Text to Redact")
        m_layout = QVBoxLayout()
        self.text_entry = QLineEdit()
        self.text_entry.setPlaceholderText("Enter terms separated by commas")
        m_layout.addWidget(self.text_entry)
        mask_box.setLayout(m_layout)
        layout.addWidget(mask_box)

        self.process_btn = QPushButton("🔒 Apply Masking to Active Document")
        self.process_btn.setObjectName("PrimaryBtn")
        self.process_btn.clicked.connect(self.start_processing)
        layout.addWidget(self.process_btn)

        log_box = QGroupBox("Status Log")
        l_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        l_layout.addWidget(self.log_text)
        log_box.setLayout(l_layout)

        layout.addWidget(log_box)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_queue)

    def start_processing(self):
        if not self.viewer.doc:
            QMessageBox.critical(self, "Error", "Please open a PDF document first.")
            return

        mask_text = self.text_entry.text().strip()
        if not mask_text:
            QMessageBox.critical(self, "Error", "Enter text to mask.")
            return

        self.mask_texts = [t.strip().lower() for t in mask_text.split(",") if t.strip()]
        self.process_btn.setEnabled(False)
        Thread(target=self.process_in_place, daemon=True).start()
        self.timer.start(100)

    def process_in_place(self):
        try:
            doc = self.viewer.doc
            total_matches = 0

            for page in doc:
                for text in self.mask_texts:
                    insts = page.search_for(text)
                    for inst in insts:
                        page.add_redact_annot(inst, fill=(0, 0, 0))
                        total_matches += 1

                try:
                    tp = page.get_text("words")
                    for w in tp:
                        if w[4].lower() in self.mask_texts:
                            rect = fitz.Rect(w[:4])
                            page.add_redact_annot(rect, fill=(0, 0, 0))
                            total_matches += 1
                except Exception:
                    pass

                page.apply_redactions()

            pdf_bytes = doc.write()
            self.processing_queue.put(("SUCCESS", pdf_bytes, total_matches))
        except Exception as e:
            self.processing_queue.put(("ERROR", str(e)))

    def check_queue(self):
        while not self.processing_queue.empty():
            item = self.processing_queue.get()
            self.process_btn.setEnabled(True)
            self.timer.stop()
            if item[0] == "SUCCESS":
                _, pdf_bytes, count = item
                self.viewer.load_pdf(pdf_bytes)
                self.viewer.is_modified = True
                self.log_text.append(f"✅ Masking applied ({count} instances redacted). Saved in memory.")
            else:
                QMessageBox.critical(self, "Error", f"Masking failed: {item[1]}")


# ==========================================
# 2. EXTRACT PAGES PANEL
# ==========================================
class ExtractorPanel(QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_title = QLabel("Extract Pages")
        lbl_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #1e2530;")
        layout.addWidget(lbl_title)

        range_box = QGroupBox("Select Target Pages")
        r_layout = QVBoxLayout()

        self.radio_current = QRadioButton("Current Page Only")
        self.radio_custom = QRadioButton("Custom Range / Pages:")
        self.radio_custom.setChecked(True)

        self.pages_entry = QLineEdit()
        self.pages_entry.setPlaceholderText("e.g. 1, 3-5, 8")

        r_layout.addWidget(self.radio_current)
        r_layout.addWidget(self.radio_custom)
        r_layout.addWidget(self.pages_entry)
        range_box.setLayout(r_layout)
        layout.addWidget(range_box)

        mode_box = QGroupBox("Output Mode")
        m_layout = QVBoxLayout()
        self.radio_single = QRadioButton("Single Combined PDF")
        self.radio_single.setChecked(True)
        self.radio_separate = QRadioButton("Separate File Per Selection")
        m_layout.addWidget(self.radio_single)
        m_layout.addWidget(self.radio_separate)
        mode_box.setLayout(m_layout)
        layout.addWidget(mode_box)

        btn_extract = QPushButton("🚀 Extract Pages")
        btn_extract.setObjectName("PrimaryBtn")
        btn_extract.clicked.connect(self.process_extraction)
        layout.addWidget(btn_extract)

        layout.addStretch()
        self.setLayout(layout)

    def parse_part(self, part, total_pages):
        pages = []
        if '-' in part:
            s, e = map(int, part.split('-'))
            for p in range(s - 1, e):
                if 0 <= p < total_pages: pages.append(p)
        else:
            p = int(part) - 1
            if 0 <= p < total_pages: pages.append(p)
        return pages

    def process_extraction(self):
        if not self.viewer.doc:
            QMessageBox.warning(self, "Error", "Please open a PDF document first.")
            return

        try:
            doc = self.viewer.doc
            total_pages = len(doc)
            work_dir = self.viewer.get_working_dir()

            if self.radio_current.isChecked():
                parts = ["1"]
            else:
                page_str = self.pages_entry.text().strip()
                if not page_str:
                    QMessageBox.warning(self, "Error", "Please specify pages.")
                    return
                parts = [p.strip() for p in page_str.split(',') if p.strip()]

            if self.radio_single.isChecked():
                init_file = os.path.join(work_dir, "Extracted_Pages.pdf") if work_dir else "Extracted_Pages.pdf"
                save_path, _ = QFileDialog.getSaveFileName(self, "Save Extracted PDF", init_file, "PDF Files (*.pdf)")
                if not save_path: return

                new_doc = fitz.open()
                for part in parts:
                    for p_idx in self.parse_part(part, total_pages):
                        new_doc.insert_pdf(doc, from_page=p_idx, to_page=p_idx)

                new_doc.save(save_path)
                new_doc.close()
                QMessageBox.information(self, "Success", "Pages extracted successfully!")

            else:
                dest_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory", work_dir)
                if not dest_dir: return

                count = 0
                for part in parts:
                    new_doc = fitz.open()
                    p_indices = self.parse_part(part, total_pages)
                    for p_idx in p_indices:
                        new_doc.insert_pdf(doc, from_page=p_idx, to_page=p_idx)

                    out_file = os.path.join(dest_dir, f"Extracted_Page_{part.replace('-', '_')}.pdf")
                    new_doc.save(out_file)
                    new_doc.close()
                    count += 1

                QMessageBox.information(self, "Success", f"Extracted {count} files successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Extraction failed: {str(e)}")


# ==========================================
# 3. INSERT PAGES PANEL
# ==========================================
class InsertPagesPanel(QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.viewer.add_file_loaded_callback(self.update_total_pages)
        self.insert_pdf_path = ""

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_title = QLabel("Insert Pages")
        lbl_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #1e2530;")
        layout.addWidget(lbl_title)

        file_box = QGroupBox("Select File to Insert")
        f_layout = QVBoxLayout()
        btn_select_file = QPushButton("📁 Browse Insert File...")
        btn_select_file.setObjectName("SuccessBtn")
        btn_select_file.clicked.connect(self.select_insert_file)

        self.lbl_file_name = QLabel("No file selected")
        self.lbl_file_name.setStyleSheet("color: #718096; font-style: italic;")

        f_layout.addWidget(btn_select_file)
        f_layout.addWidget(self.lbl_file_name)
        file_box.setLayout(f_layout)
        layout.addWidget(file_box)

        place_box = QGroupBox("Position")
        p_layout = QGridLayout()

        p_layout.addWidget(QLabel("Location:"), 0, 0)
        self.combo_location = QComboBox()
        self.combo_location.addItems(["After", "Before"])
        p_layout.addWidget(self.combo_location, 0, 1)

        self.radio_first = QRadioButton("First Page")
        self.radio_last = QRadioButton("Last Page")
        self.radio_page = QRadioButton("Specific Page:")
        self.radio_page.setChecked(True)

        self.input_page = QLineEdit("1")
        self.input_page.setFixedWidth(50)
        self.lbl_total = QLabel("of 0")

        pg_num_box = QHBoxLayout()
        pg_num_box.addWidget(self.input_page)
        pg_num_box.addWidget(self.lbl_total)
        pg_num_box.addStretch()

        p_layout.addWidget(self.radio_first, 1, 0, 1, 2)
        p_layout.addWidget(self.radio_last, 2, 0, 1, 2)
        p_layout.addWidget(self.radio_page, 3, 0)
        p_layout.addLayout(pg_num_box, 3, 1)

        place_box.setLayout(p_layout)
        layout.addWidget(place_box)

        btn_ok = QPushButton("📌 Insert Pages into Current PDF")
        btn_ok.setObjectName("PrimaryBtn")
        btn_ok.clicked.connect(self.process_insertion)
        layout.addWidget(btn_ok)

        layout.addStretch()
        self.setLayout(layout)

    def update_total_pages(self, total):
        self.lbl_total.setText(f"of {total}")

    def select_insert_file(self):
        work_dir = self.viewer.get_working_dir()
        path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Insert", work_dir, "PDF Files (*.pdf)")
        if path:
            self.insert_pdf_path = path
            self.lbl_file_name.setText(os.path.basename(path))

    def process_insertion(self):
        if not self.viewer.doc:
            QMessageBox.warning(self, "Error", "Please open a base PDF document first.")
            return

        if not self.insert_pdf_path:
            QMessageBox.warning(self, "Error", "Please select a PDF file to insert.")
            return

        try:
            doc = self.viewer.doc
            total_pages = len(doc)

            if self.radio_first.isChecked():
                target_pg = 0
            elif self.radio_last.isChecked():
                target_pg = total_pages - 1
            else:
                try: target_pg = int(self.input_page.text().strip()) - 1
                except Exception: target_pg = 0

            target_pg = max(0, min(target_pg, total_pages - 1))
            location = self.combo_location.currentText()
            insert_idx = target_pg + 1 if location == "After" else target_pg

            ins_doc = fitz.open(self.insert_pdf_path)
            doc.insert_pdf(ins_doc, start_at=insert_idx)
            ins_doc.close()

            pdf_bytes = doc.write()
            self.viewer.load_pdf(pdf_bytes)
            self.viewer.is_modified = True
            QMessageBox.information(self, "Success", "Pages inserted into current document!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Insertion failed: {str(e)}")


# ==========================================
# 4. SIGN DOCUMENT PANEL
# ==========================================
class SignerPanel(QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.viewer.signer_panel = self
        self.image_path = ""
        self.interactive_mode = True
        self.is_signing_active = False
        self.placed_items = []

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_title = QLabel("Sign Document")
        lbl_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #1e2530;")
        layout.addWidget(lbl_title)

        sign_group = QGroupBox("1. Signature Content")
        s_layout = QGridLayout()
        self.text_radio = QRadioButton("Text:")
        self.text_radio.setChecked(True)
        self.text_input = QLineEdit("Approved / Signed")

        self.image_radio = QRadioButton("Image:")
        self.image_btn = QPushButton("Browse Image")
        self.image_btn.clicked.connect(self.select_image)

        s_layout.addWidget(self.text_radio, 0, 0)
        s_layout.addWidget(self.text_input, 0, 1)
        s_layout.addWidget(self.image_radio, 1, 0)
        s_layout.addWidget(self.image_btn, 1, 1)
        sign_group.setLayout(s_layout)
        layout.addWidget(sign_group)

        size_group = QGroupBox("2. Size")
        sz_layout = QHBoxLayout()
        self.size_combo = QComboBox()
        self.size_combo.addItems(["Small (1 Sq Inch)", "Medium (1.25 Sq Inch)", "Large (1.5 Sq Inch)"])
        self.size_combo.setCurrentText("Medium (1.25 Sq Inch)")
        sz_layout.addWidget(self.size_combo)
        size_group.setLayout(sz_layout)
        layout.addWidget(size_group)

        mode_box = QGroupBox("3. Placement Mode")
        m_layout = QVBoxLayout()
        self.radio_interactive_mode = QRadioButton("Interactive Drag & Drop")
        self.radio_preset_mode = QRadioButton("Preset (9-Grid Options)")
        self.radio_interactive_mode.setChecked(True)

        self.radio_preset_mode.toggled.connect(self.toggle_mode_ui)
        m_layout.addWidget(self.radio_interactive_mode)
        m_layout.addWidget(self.radio_preset_mode)
        mode_box.setLayout(m_layout)
        layout.addWidget(mode_box)

        self.preset_group = QGroupBox("Preset Location (9-Grid)")
        opt_layout = QHBoxLayout()
        self.pos_combo = QComboBox()
        self.pos_combo.addItems([
            "Top Left", "Top Center", "Top Right",
            "Center Left", "Center", "Center Right",
            "Bottom Left", "Bottom Center", "Bottom Right"
        ])
        self.pos_combo.setCurrentText("Bottom Right")
        opt_layout.addWidget(self.pos_combo)
        self.preset_group.setLayout(opt_layout)
        layout.addWidget(self.preset_group)

        self.info_lbl = QLabel("👉 Click 'Start Signing' to place signs on Preview.\n👉 Drag / Resize signature on preview.")
        self.info_lbl.setStyleSheet("color: #0078d4; font-weight: bold; background-color: #e6f2ff; padding: 6px; border-radius: 4px;")
        layout.addWidget(self.info_lbl)

        self.btn_start_signing = QPushButton("✍️ Start Signing")
        self.btn_start_signing.setCheckable(True)
        self.btn_start_signing.clicked.connect(self.toggle_signing)
        layout.addWidget(self.btn_start_signing)

        clear_layout = QHBoxLayout()
        btn_clear_page = QPushButton("🗑️ Clear Active Page")
        btn_clear_page.clicked.connect(self.clear_active_page_signatures)
        btn_clear_all = QPushButton("🗑️ Clear All")
        btn_clear_all.clicked.connect(self.clear_placed_signatures)
        
        clear_layout.addWidget(btn_clear_page)
        clear_layout.addWidget(btn_clear_all)
        layout.addLayout(clear_layout)

        apply_btn = QPushButton("✒️ Apply Signature to Document")
        apply_btn.setObjectName("PrimaryBtn")
        apply_btn.clicked.connect(self.apply_signature)
        layout.addWidget(apply_btn)

        layout.addStretch()
        self.setLayout(layout)
        self.toggle_mode_ui()

    def toggle_mode_ui(self):
        is_interactive = self.radio_interactive_mode.isChecked()
        self.interactive_mode = is_interactive
        self.preset_group.setVisible(not is_interactive)
        self.info_lbl.setVisible(is_interactive)
        self.btn_start_signing.setVisible(is_interactive)

    def toggle_signing(self, checked):
        self.is_signing_active = checked
        if checked:
            self.btn_start_signing.setText("🛑 Stop Signing")
            self.btn_start_signing.setStyleSheet("background-color: #ff4d4d; color: white; font-weight: bold;")
        else:
            self.btn_start_signing.setText("✍️ Start Signing")
            self.btn_start_signing.setStyleSheet("")

    def select_image(self):
        work_dir = self.viewer.get_working_dir()
        path, _ = QFileDialog.getOpenFileName(self, "Select Image Stamp", work_dir, "Images (*.png *.jpg *.jpeg)")
        if path:
            self.image_path = path

    def clear_placed_signatures(self):
        for item in self.placed_items:
            self.viewer.scene.removeItem(item)
        self.placed_items.clear()

    def clear_active_page_signatures(self):
        if not self.viewer.page_render_y_offsets or not self.placed_items:
            return

        viewport = self.viewer.graphics_view.viewport()
        center_viewport_pt = viewport.rect().center()
        scene_center = self.viewer.graphics_view.mapToScene(center_viewport_pt)
        center_y = scene_center.y()

        active_page_idx = -1
        for pg_idx, (y_start, render_w, render_h, pdf_w, pdf_h) in enumerate(self.viewer.page_render_y_offsets):
            if y_start <= center_y <= (y_start + render_h):
                active_page_idx = pg_idx
                break

        if active_page_idx == -1:
            active_page_idx = min(
                range(len(self.viewer.page_render_y_offsets)),
                key=lambda i: abs(self.viewer.page_render_y_offsets[i][0] + (self.viewer.page_render_y_offsets[i][2] / 2) - center_y)
            )

        if active_page_idx != -1:
            y_start, render_w, render_h, _, _ = self.viewer.page_render_y_offsets[active_page_idx]
            items_to_remove = []

            for item in self.placed_items:
                pos = item.scenePos()
                if y_start <= pos.y() <= (y_start + render_h):
                    items_to_remove.append(item)

            for item in items_to_remove:
                self.viewer.scene.removeItem(item)
                self.placed_items.remove(item)

    def get_selected_square_dimens(self):
        size_str = self.size_combo.currentText()
        if "Small" in size_str: return 72, 12
        elif "Large" in size_str: return 108, 20
        else: return 90, 15

    def add_interactive_signature(self, point):
        is_text = self.text_radio.isChecked()
        side_dim, font_sz = self.get_selected_square_dimens()

        if is_text:
            txt = self.text_input.text().strip() or "Signed"
            content = QGraphicsTextItem(txt)
            content.setDefaultTextColor(QColor("#000080"))
            content.setFont(QFont("Helvetica", font_sz, QFont.Bold))
        else:
            if not self.image_path or not os.path.exists(self.image_path):
                QMessageBox.warning(self, "Error", "Please select an image file first!")
                return
            pixmap = QPixmap(self.image_path).scaled(side_dim, side_dim, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            content = QGraphicsPixmapItem(pixmap)

        group_item = ResizableSignatureItem(content, is_text=is_text)
        rect = group_item.boundingRect()
        group_item.setPos(QPointF(point.x() - (rect.width() / 2), point.y() - (rect.height() / 2)))
        group_item.setZValue(100)

        self.viewer.scene.addItem(group_item)
        self.placed_items.append(group_item)

    def get_preset_position(self, page_w, page_h, item_w, item_h):
        pos = self.pos_combo.currentText()
        margin = 30
        x = margin if "Left" in pos else (page_w - item_w - margin if "Right" in pos else (page_w - item_w) / 2)
        y = page_h - item_h - margin if "Top" in pos else (margin if "Bottom" in pos else (page_h - item_h) / 2)
        return x, y

    def apply_signature(self):
        if not self.viewer.doc:
            QMessageBox.warning(self, "Error", "Please open a PDF file first.")
            return

        try:
            doc = self.viewer.doc
            if self.interactive_mode:
                if not self.placed_items:
                    QMessageBox.warning(self, "Error", "No signatures placed!")
                    return

                page_stamps = {i: [] for i in range(len(doc))}
                for item in self.placed_items:
                    pos = item.pos()
                    x_sc, y_sc = pos.x(), pos.y()
                    for pg_idx, (y_start, render_w, render_h, pdf_w, pdf_h) in enumerate(self.viewer.page_render_y_offsets):
                        if y_start <= y_sc <= y_start + render_h:
                            scale_x = pdf_w / render_w
                            scale_y = pdf_h / render_h
                            pdf_x = x_sc * scale_x
                            rel_y = (y_sc - y_start) * scale_y
                            rect = item.boundingRect()
                            target_w = rect.width() * item.transform().m11() * scale_x
                            target_h = rect.height() * item.transform().m22() * scale_y
                            pdf_y = pdf_h - rel_y - target_h
                            page_stamps[pg_idx].append((item, pdf_x, pdf_y, target_w, target_h))
                            break

                for pg_idx, page in enumerate(doc):
                    stamps = page_stamps[pg_idx]
                    if stamps:
                        packet = io.BytesIO()
                        can = canvas.Canvas(packet, pagesize=(page.rect.width, page.rect.height))
                        for group, x, y, tw, th in stamps:
                            content = group.content_item
                            if group.is_text:
                                can.setFont("Helvetica-Bold", int(max(10, th * 0.6)))
                                can.drawString(x, y, content.toPlainText())
                            else:
                                temp_img = "temp_stamp.png"
                                content.pixmap().save(temp_img)
                                can.drawImage(temp_img, x, y, width=tw, height=th, mask='auto')
                                if os.path.exists(temp_img): os.remove(temp_img)
                        can.save()
                        packet.seek(0)
                        
                        stamp_doc = fitz.open("pdf", packet.read())
                        page.show_pdf_page(page.rect, stamp_doc, 0)

            else:
                side_dim, font_sz = self.get_selected_square_dimens()
                item_w = len(self.text_input.text()) * (font_sz * 0.5) if self.text_radio.isChecked() else side_dim
                item_h = font_sz if self.text_radio.isChecked() else side_dim

                for page in doc:
                    x, y = self.get_preset_position(page.rect.width, page.rect.height, item_w, item_h)
                    packet = io.BytesIO()
                    can = canvas.Canvas(packet, pagesize=(page.rect.width, page.rect.height))
                    if self.text_radio.isChecked():
                        can.setFont("Helvetica-Bold", font_sz)
                        can.drawString(x, y, self.text_input.text())
                    elif self.image_radio.isChecked() and self.image_path:
                        can.drawImage(self.image_path, x, y, width=item_w, height=item_h, mask='auto')
                    can.save()
                    packet.seek(0)
                    stamp_doc = fitz.open("pdf", packet.read())
                    page.show_pdf_page(page.rect, stamp_doc, 0)

            pdf_bytes = doc.write()
            self.clear_placed_signatures()
            self.toggle_signing(False)
            self.viewer.load_pdf(pdf_bytes)
            self.viewer.is_modified = True
            QMessageBox.information(self, "Success", "Signature applied to active document!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply signature: {str(e)}")


# ==========================================
# 5. CLEAR RESTRICTIONS PANEL (WITH SUMMARY)
# ==========================================
class RestrictionRemoverPanel(QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.viewer.add_file_loaded_callback(self.update_restriction_summary)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        lbl_title = QLabel("Clear Restrictions")
        lbl_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #1e2530;")
        layout.addWidget(lbl_title)

        # Document Restrictions Summary Group
        summary_box = QGroupBox("Document Restriction Summary")
        s_layout = QVBoxLayout()
        s_layout.setSpacing(6)

        self.lbl_encrypted = QLabel("🔒 Protection: -")
        self.lbl_print = QLabel("🖨️ Printing: -")
        self.lbl_edit = QLabel("✏️ Editing / Modifying: -")
        self.lbl_copy = QLabel("📋 Content Copying: -")
        self.lbl_annot = QLabel("💬 Annotations / Forms: -")

        summary_labels = [self.lbl_encrypted, self.lbl_print, self.lbl_edit, self.lbl_copy, self.lbl_annot]
        for lbl in summary_labels:
            lbl.setStyleSheet("font-size: 9pt; font-weight: bold; color: #333333;")
            s_layout.addWidget(lbl)

        summary_box.setLayout(s_layout)
        layout.addWidget(summary_box)

        # Action Box
        box = QGroupBox("Remove Permissions Lock")
        b_layout = QVBoxLayout()
        lbl_info = QLabel("Remove print, edit, and copy restrictions directly from active document.")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #4a5568;")

        btn_unlock = QPushButton("🔓 Clear Document Restrictions")
        btn_unlock.setObjectName("PrimaryBtn")
        btn_unlock.clicked.connect(self.unlock_pdf)

        b_layout.addWidget(lbl_info)
        b_layout.addSpacing(10)
        b_layout.addWidget(btn_unlock)
        box.setLayout(b_layout)

        layout.addWidget(box)
        layout.addStretch()
        self.setLayout(layout)
        self.update_restriction_summary()

    def update_restriction_summary(self, total_pages=0):
        if not self.viewer.doc:
            self.lbl_encrypted.setText("🔒 Protection: No Document Loaded")
            self.lbl_encrypted.setStyleSheet("font-size: 9pt; font-weight: bold; color: #718096;")
            self.lbl_print.setText("🖨️ Printing: -")
            self.lbl_print.setStyleSheet("font-size: 9pt; font-weight: bold; color: #718096;")
            self.lbl_edit.setText("✏️ Editing / Modifying: -")
            self.lbl_edit.setStyleSheet("font-size: 9pt; font-weight: bold; color: #718096;")
            self.lbl_copy.setText("📋 Content Copying: -")
            self.lbl_copy.setStyleSheet("font-size: 9pt; font-weight: bold; color: #718096;")
            self.lbl_annot.setText("💬 Annotations / Forms: -")
            self.lbl_annot.setStyleSheet("font-size: 9pt; font-weight: bold; color: #718096;")
            return

        doc = self.viewer.doc
        perms = doc.permissions
        is_encrypted = doc.is_encrypted

        # Status text & style update
        if is_encrypted:
            self.lbl_encrypted.setText("🔒 Protection: Password / Restricted Document")
            self.lbl_encrypted.setStyleSheet("font-size: 9pt; font-weight: bold; color: #d9534f;")
        else:
            self.lbl_encrypted.setText("🔓 Protection: Unlocked / Standard Document")
            self.lbl_encrypted.setStyleSheet("font-size: 9pt; font-weight: bold; color: #107c41;")

        # Check PyMuPDF permissions flags
        can_print = bool(perms & fitz.PDF_PERM_PRINT)
        can_edit = bool(perms & fitz.PDF_PERM_MODIFY)
        can_copy = bool(perms & fitz.PDF_PERM_COPY)
        can_annot = bool(perms & fitz.PDF_PERM_ANNOTATE)

        def set_label_status(lbl, prefix, is_allowed):
            if is_allowed:
                lbl.setText(f"{prefix} Allowed ✅")
                lbl.setStyleSheet("font-size: 9pt; font-weight: bold; color: #107c41;")
            else:
                lbl.setText(f"{prefix} Restricted / Blocked ❌")
                lbl.setStyleSheet("font-size: 9pt; font-weight: bold; color: #d9534f;")

        set_label_status(self.lbl_print, "🖨️ Printing:", can_print)
        set_label_status(self.lbl_edit, "✏️ Editing / Modifying:", can_edit)
        set_label_status(self.lbl_copy, "📋 Content Copying:", can_copy)
        set_label_status(self.lbl_annot, "💬 Annotations / Forms:", can_annot)

    def unlock_pdf(self):
        if not self.viewer.doc:
            QMessageBox.warning(self, "Error", "Please open a PDF file first.")
            return

        try:
            pdf_bytes = self.viewer.doc.write(clean=True)
            self.viewer.load_pdf(pdf_bytes)
            self.viewer.is_modified = True
            self.update_restriction_summary()
            QMessageBox.information(self, "Success", "Document restrictions removed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to unlock: {str(e)}")


# ==========================================
# 6. COMBINE MERGER PANEL
# ==========================================
class MergerPanel(QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.pdf_files = []

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_title = QLabel("Combine PDFs")
        lbl_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #1e2530;")
        layout.addWidget(lbl_title)

        btn_add = QPushButton("➕ Add PDF Files")
        btn_add.setObjectName("SuccessBtn")
        btn_add.clicked.connect(self.add_files)
        layout.addWidget(btn_add)

        self.file_list_widget = QListWidget()
        layout.addWidget(self.file_list_widget)

        action_layout = QHBoxLayout()
        btn_up = QPushButton("🔼 Up")
        btn_up.clicked.connect(self.move_up)
        btn_down = QPushButton("🔽 Down")
        btn_down.clicked.connect(self.move_down)
        btn_remove = QPushButton("❌ Remove")
        btn_remove.clicked.connect(self.remove_selected)

        action_layout.addWidget(btn_up)
        action_layout.addWidget(btn_down)
        action_layout.addWidget(btn_remove)
        layout.addLayout(action_layout)

        btn_merge = QPushButton("📂 Merge All Files")
        btn_merge.setObjectName("PrimaryBtn")
        btn_merge.clicked.connect(self.merge_pdfs)
        layout.addWidget(btn_merge)

        self.setLayout(layout)

    def add_files(self):
        work_dir = self.viewer.get_working_dir()
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDFs", work_dir, "PDF Files (*.pdf)")
        if files:
            for f in files:
                if f not in self.pdf_files:
                    self.pdf_files.append(f)
                    self.file_list_widget.addItem(os.path.basename(f))

    def move_up(self):
        row = self.file_list_widget.currentRow()
        if row > 0:
            item = self.file_list_widget.takeItem(row)
            self.file_list_widget.insertItem(row - 1, item)
            self.file_list_widget.setCurrentRow(row - 1)
            self.pdf_files.insert(row - 1, self.pdf_files.pop(row))

    def move_down(self):
        row = self.file_list_widget.currentRow()
        if row < self.file_list_widget.count() - 1 and row != -1:
            item = self.file_list_widget.takeItem(row)
            self.file_list_widget.insertItem(row + 1, item)
            self.file_list_widget.setCurrentRow(row + 1)
            self.pdf_files.insert(row + 1, self.pdf_files.pop(row))

    def remove_selected(self):
        row = self.file_list_widget.currentRow()
        if row != -1:
            self.file_list_widget.takeItem(row)
            self.pdf_files.pop(row)

    def merge_pdfs(self):
        if len(self.pdf_files) < 2:
            QMessageBox.warning(self, "Error", "Select at least 2 files.")
            return

        work_dir = self.viewer.get_working_dir()
        init_file = os.path.join(work_dir, "Merged_Output.pdf") if work_dir else "Merged_Output.pdf"
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Merged PDF", init_file, "PDF Files (*.pdf)")
        
        if save_path:
            merged_doc = fitz.open()
            for pdf in self.pdf_files:
                doc = fitz.open(pdf)
                merged_doc.insert_pdf(doc)
                doc.close()
            merged_doc.save(save_path)
            merged_doc.close()
            QMessageBox.information(self, "Success", "PDFs Merged Successfully!")
            self.viewer.load_pdf(save_path)


# ==========================================
# 7. OPTIMIZE PANEL
# ==========================================
class ProEngineCompressorPanel(QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_title = QLabel("Optimize")
        lbl_title.setStyleSheet("font-size: 13pt; font-weight: bold; color: #1e2530;")
        layout.addWidget(lbl_title)

        box = QGroupBox("Compression Level")
        b_layout = QVBoxLayout()
        self.combo_profile = QComboBox()
        self.combo_profile.addItems([
            "Aggressive (~70-80% reduction)",
            "Balanced (~50% reduction)",
            "Light (Minimal reduction)"
        ])
        b_layout.addWidget(self.combo_profile)

        lbl_hint = QLabel("💡 Optimizes & rebuilds document pages in-memory.")
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet("color: #718096; font-size: 8pt;")
        b_layout.addWidget(lbl_hint)

        box.setLayout(b_layout)
        layout.addWidget(box)

        btn_optimize = QPushButton("🚀 Run Optimization")
        btn_optimize.setObjectName("PrimaryBtn")
        btn_optimize.clicked.connect(self.run_pro_compression)
        layout.addWidget(btn_optimize)

        layout.addStretch()
        self.setLayout(layout)

    def run_pro_compression(self):
        if not self.viewer.doc:
            QMessageBox.warning(self, "Error", "Please open a PDF document first.")
            return

        profile_index = self.combo_profile.currentIndex()
        if profile_index == 0: dpi, jpg_quality = 110, 40
        elif profile_index == 1: dpi, jpg_quality = 150, 60
        else: dpi, jpg_quality = 200, 80

        try:
            src_doc = self.viewer.doc
            new_doc = fitz.open()

            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)

            for page in src_doc:
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                img_data = pix.tobytes("jpeg", jpg_quality=jpg_quality)
                rect = page.rect
                new_page = new_doc.new_page(width=rect.width, height=rect.height)
                new_page.insert_image(rect, stream=img_data)

            pdf_bytes = new_doc.write(garbage=4, deflate=True, clean=True)
            new_doc.close()

            self.viewer.load_pdf(pdf_bytes)
            self.viewer.is_modified = True
            QMessageBox.information(self, "Optimization Successful", "Document optimized successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Optimization failed: {str(e)}")


# ==========================================
# MAIN APPLICATION
# ==========================================
class PDFSuiteApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RAA PDF Utility - CA Reetesh Agarwal")
        self.setGeometry(100, 80, 1280, 780)

        container = QWidget()
        app_layout = QVBoxLayout()
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)

        # Header Bar
        header_bar = QFrame()
        header_bar.setFixedHeight(55)
        header_bar.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #e1e5eb;")

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 5, 15, 5)

        btn_open_file = QPushButton("📂 Open")
        btn_open_file.setObjectName("HeaderActionBtn")
        btn_open_file.clicked.connect(self.global_open_file)

        btn_save = QPushButton("💾 Save")
        btn_save.setObjectName("HeaderActionBtn")
        btn_save.clicked.connect(self.save_file)

        btn_save_as = QPushButton("💾 Save As")
        btn_save_as.setObjectName("HeaderActionBtn")
        btn_save_as.clicked.connect(self.save_file_as)

        btn_close = QPushButton("❌ Close Document")
        btn_close.setObjectName("HeaderActionBtn")
        btn_close.clicked.connect(self.close_current_file)

        btn_quit = QPushButton("🚪 Quit")
        btn_quit.setObjectName("HeaderActionBtn")
        btn_quit.clicked.connect(self.quit_application)

        self.lbl_active_file = QLabel("No File Opened")
        self.lbl_active_file.setStyleSheet("color: #718096; font-size: 9.5pt; font-weight: bold; margin-left: 10px;")

        lbl_brand = QLabel("CA Reetesh Agarwal (AICA L2 B77)")
        lbl_brand.setStyleSheet("color: #0078d4; font-size: 10pt; font-weight: bold;")

        header_layout.addWidget(btn_open_file)
        header_layout.addWidget(btn_save)
        header_layout.addWidget(btn_save_as)
        header_layout.addWidget(btn_close)
        header_layout.addWidget(btn_quit)
        header_layout.addWidget(self.lbl_active_file)
        header_layout.addStretch()
        header_layout.addWidget(lbl_brand)

        header_bar.setLayout(header_layout)

        # Splitter Layout
        main_splitter = QSplitter(Qt.Horizontal)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(160)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(6, 12, 6, 12)
        sidebar_layout.setSpacing(5)

        title = QLabel(" UTILITIES")
        title.setStyleSheet("color: #64748b; font-weight: bold; font-size: 10pt; padding-bottom: 4px;")
        sidebar_layout.addWidget(title)

        self.viewer = PDFViewerWidget(app_ref=self)

        self.stack = QStackedWidget()
        self.stack.addWidget(MaskerPanel(self.viewer))
        self.stack.addWidget(ExtractorPanel(self.viewer))
        self.stack.addWidget(InsertPagesPanel(self.viewer))
        self.stack.addWidget(SignerPanel(self.viewer))
        self.stack.addWidget(RestrictionRemoverPanel(self.viewer))
        self.stack.addWidget(MergerPanel(self.viewer))
        self.stack.addWidget(ProEngineCompressorPanel(self.viewer))

        tools = [
            ("Masked Content", 0),
            ("Extract Pages", 1),
            ("Insert Pages", 2),
            ("Sign Document", 3),
            ("Unrestrict", 4),
            ("Combine PDFs", 5),
            ("Optimize", 6)
        ]

        self.nav_buttons = []
        for text, idx in tools:
            btn = QPushButton(text)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, i=idx: self.switch_panel(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)

        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)

        main_splitter.addWidget(sidebar)
        main_splitter.addWidget(self.stack)
        main_splitter.addWidget(self.viewer)

        main_splitter.setSizes([160, 260, 860])

        app_layout.addWidget(header_bar)
        app_layout.addWidget(main_splitter)

        container.setLayout(app_layout)
        self.setCentralWidget(container)

    def switch_panel(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def global_open_file(self):
        work_dir = self.viewer.get_working_dir()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF Document", work_dir, "PDF Files (*.pdf)")
        if file_path:
            self.viewer.load_pdf(file_path)
            self.lbl_active_file.setText(f"Active Document: {os.path.basename(file_path)}")

    def save_file(self):
        if not self.viewer.doc:
            QMessageBox.warning(self, "Warning", "No active document opened.")
            return

        if self.viewer.current_file_path:
            try:
                self.viewer.doc.save(self.viewer.current_file_path, incremental=False, encryption=0)
                self.viewer.is_modified = False
                QMessageBox.information(self, "Saved", "File saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save file: {str(e)}")
        else:
            self.save_file_as()

    def save_file_as(self):
        if not self.viewer.doc:
            QMessageBox.warning(self, "Warning", "No active document opened.")
            return

        work_dir = self.viewer.get_working_dir()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save As PDF", work_dir, "PDF Files (*.pdf)")
        if file_path:
            try:
                self.viewer.doc.save(file_path)
                self.viewer.current_file_path = file_path
                self.viewer.is_modified = False
                self.lbl_active_file.setText(f"Active Document: {os.path.basename(file_path)}")
                QMessageBox.information(self, "Saved", "File saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Could not save file: {str(e)}")

    def close_current_file(self):
        if not self.viewer.doc:
            return True

        if self.viewer.is_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "Do you want to save changes to the document before closing?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return False

        self.viewer.close_document()
        self.lbl_active_file.setText("No File Opened")
        return True

    def quit_application(self):
        if self.close_current_file():
            QApplication.quit()

    def closeEvent(self, event):
        if self.close_current_file():
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLE)
    window = PDFSuiteApp()
    window.show()
    sys.exit(app.exec_())