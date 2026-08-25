# DocDeskew AI - Document Processing App 📄✨

**DocDeskew AI** is a Python desktop application for document processing, deskewing, OCR enhancement, and document management.

## 🚀 Features

- **Document Deskewing & Alignment**: Automated detection and rotation correction for scanned documents.
- **OCR Text Extraction**: Powered by PyTesseract and OpenCV for text recognition.
- **PDF Processing**: Seamless PDF manipulation and extraction using PyMuPDF (fitz).
- **Interactive GUI**: User-friendly desktop interface built with Tkinter.
- **Batch Processing**: Tools to generate, process, and verify test documents.

## 📋 Requirements

- Python 3.9+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed on system path

### Python Dependencies

Dependencies are listed in `requirements.txt`:
```bash
opencv-python>=4.8.0
pytesseract>=0.3.10
pillow>=10.0.0
pymupdf>=1.23.0
numpy>=1.24.0
```

## 🛠️ Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
   cd "App 4.0"
   ```

2. **Create a Virtual Environment** (Optional but recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🏃 Launching the Application

### On Windows
Double-click `run_app.bat` or run in terminal:
```cmd
run_app.bat
```

### Direct Python Launch
```bash
python main.py
```

## 🧪 Testing & Verification

Run document generation or verification tools:
```bash
# Verify processing engine
python verify_engine.py

# Run tests batch script
run_tests.bat
```

## 📄 License
MIT License
