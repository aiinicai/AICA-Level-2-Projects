"""File Type and PDF Type Detection Module."""

import os
import io
from typing import Tuple, Optional
import pypdf
import fitz  # PyMuPDF

def detect_file_type(file_path_or_bytes: any, filename: str = "") -> str:
    """
    Detect file format: 'pdf', 'excel', 'csv', 'word', 'image', or 'unknown'.
    """
    fname = filename or (file_path_or_bytes if isinstance(file_path_or_bytes, str) else "")
    ext = os.path.splitext(fname)[1].lower()
    
    if ext in ('.pdf',):
        return 'pdf'
    elif ext in ('.xlsx', '.xls', '.xlsm'):
        return 'excel'
    elif ext in ('.csv', '.tsv'):
        return 'csv'
    elif ext in ('.docx', '.doc'):
        return 'word'
    elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'):
        return 'image'
    
    return 'unknown'

def check_pdf_encrypted(file_path_or_bytes: any) -> bool:
    """Check if a PDF file is password-protected/encrypted."""
    try:
        if isinstance(file_path_or_bytes, str):
            with open(file_path_or_bytes, "rb") as f:
                reader = pypdf.PdfReader(f)
                return reader.is_encrypted
        elif isinstance(file_path_or_bytes, (bytes, bytearray)):
            reader = pypdf.PdfReader(io.BytesIO(file_path_or_bytes))
            return reader.is_encrypted
    except Exception:
        pass
    return False

def decrypt_pdf(file_path_or_bytes: any, password: str) -> Optional[bytes]:
    """Decrypt a PDF with given password and return decrypted bytes."""
    try:
        stream = open(file_path_or_bytes, "rb") if isinstance(file_path_or_bytes, str) else io.BytesIO(file_path_or_bytes)
        reader = pypdf.PdfReader(stream)
        if reader.is_encrypted:
            res = reader.decrypt(password)
            if res in (pypdf.PasswordResult.ALREADY_DECRYPTED, pypdf.PasswordResult.USER_PASSWORD, pypdf.PasswordResult.OWNER_PASSWORD, 1, 2):
                writer = pypdf.PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                out_stream = io.BytesIO()
                writer.write(out_stream)
                out_stream.seek(0)
                return out_stream.getvalue()
            return None
        else:
            if isinstance(file_path_or_bytes, str):
                with open(file_path_or_bytes, "rb") as f:
                    return f.read()
            return file_path_or_bytes
    except Exception as e:
        print(f"Error decrypting PDF: {e}")
        return None

def is_scanned_pdf(file_path_or_bytes: any, password: Optional[str] = None, text_threshold_per_page: int = 60) -> bool:
    """
    Check if a PDF is image-based/scanned by measuring average text character density.
    Returns True if scanned (OCR required), False if digital text PDF.
    """
    try:
        doc = None
        if isinstance(file_path_or_bytes, str):
            doc = fitz.open(file_path_or_bytes)
        else:
            doc = fitz.open(stream=file_path_or_bytes, filetype="pdf")
            
        if doc.is_encrypted and password:
            doc.authenticate(password)
            
        total_chars = 0
        page_count = len(doc)
        if page_count == 0:
            return True
            
        for page in doc:
            text = page.get_text()
            total_chars += len(text.strip())
            
        avg_chars = total_chars / page_count
        return avg_chars < text_threshold_per_page
    except Exception as e:
        print(f"Error checking PDF scan status: {e}")
        return False
