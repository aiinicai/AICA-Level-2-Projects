
import os
from services.word_export_service import export_word_financial_report
import docx2pdf

def export_pdf_financial_report(client_id: int, export_dir: str, db) -> str:
    # Generate Word first
    word_path = export_word_financial_report(client_id, export_dir, db)
    pdf_path = word_path.replace('.docx', '.pdf')
    
    try:
        # Convert to PDF using Microsoft Word (win32com)
        docx2pdf.convert(word_path, pdf_path)
    except Exception as e:
        print(f"Failed to generate PDF via docx2pdf: {e}")
        # Return word path as fallback or raise
        raise RuntimeError(f"PDF generation failed: {e}")
        
    return pdf_path
