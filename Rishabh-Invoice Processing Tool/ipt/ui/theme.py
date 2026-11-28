"""Application stylesheet (professional, light)."""

STYLESHEET = """
QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #1f2937; }
QMainWindow, QDialog { background: #f5f7fa; }
#Sidebar { background: #1e293b; border: none; color: #e2e8f0; outline: 0; }
#Sidebar::item { padding: 8px 14px; border-radius: 6px; margin: 1px 6px; color: #e2e8f0; }
#Sidebar::item:selected { background: #2563eb; color: white; }
#Sidebar::item:hover:!selected { background: #334155; }
#Sidebar::item:disabled { color: #94a3b8; font-weight: 600; padding-top: 12px; background: transparent; }
#TopBar { background: white; border-bottom: 1px solid #e5e7eb; }
#PageTitle { font-size: 15pt; font-weight: 600; }
#Muted { color: #6b7280; }
#Card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; }
#CardValue { font-size: 16pt; font-weight: 600; }
#ErrorText { color: #b91c1c; }
#OkText { color: #15803d; }
QPushButton { background: white; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 14px; }
QPushButton:hover { background: #f1f5f9; }
QPushButton:disabled { color: #9ca3af; }
QPushButton#Primary { background: #2563eb; color: white; border-color: #2563eb; }
QPushButton#Primary:hover { background: #1d4ed8; }
QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit, QPlainTextEdit {
  background: white; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 6px; }
QTableWidget { background: white; border: 1px solid #e5e7eb; gridline-color: #f1f5f9;
  selection-background-color: #dbeafe; selection-color: #1f2937; }
QHeaderView::section { background: #f8fafc; border: none; border-bottom: 1px solid #e5e7eb;
  padding: 6px; font-weight: 600; }
"""
