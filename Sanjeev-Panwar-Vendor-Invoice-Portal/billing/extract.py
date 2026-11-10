"""Entirely local PDF text / raster OCR. No cloud services."""
import io,re
from pathlib import Path
PIN_RE=re.compile(r'\b[A-Z][0-9]{9}[A-Z]\b',re.I)
CURRENCY_RE=re.compile(r'\b(KES|USD|EUR|GBP|INR|UGX|TZS|RWF|ZAR)\b',re.I)

class ExtractError(Exception):pass

def read_document(raw,filename):
    suffix=Path(filename).suffix.lower()
    if suffix=='.pdf':
        try: import fitz
        except ImportError:raise ExtractError('PyMuPDF is missing. Please run SETUP_WINDOWS.bat.')
        try:
            pdf=fitz.open(stream=raw,filetype='pdf')
            if pdf.needs_pass:raise ExtractError('Password-protected PDFs are not supported.')
            if pdf.page_count>30:raise ExtractError('Maximum 30 pages per document.')
            text='\n'.join(page.get_text(sort=True) for page in pdf)
            if len(text.strip())>40:return text[:200000]
            try:
                import pytesseract
                from PIL import Image
                from io import BytesIO
                ocr=[]
                for page in pdf:
                    pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
                    ocr.append(pytesseract.image_to_string(Image.open(BytesIO(pix.tobytes('png')))))
                return '\n'.join(ocr)[:200000]
            except Exception:raise ExtractError('This PDF is scanned. Install Tesseract OCR to read it locally.')
        except ExtractError:raise
        except Exception as e:raise ExtractError('Unable to read PDF: '+str(e)[:160])
    try:
        import pytesseract
        from PIL import Image
        img=Image.open(io.BytesIO(raw));img.verify()
        img=Image.open(io.BytesIO(raw))
        if img.width*img.height>30000000:raise ExtractError('Image exceeds 30 megapixels.')
        return pytesseract.image_to_string(img)[:200000]
    except ExtractError:raise
    except Exception as e:raise ExtractError('Unable to OCR image. Check Tesseract installation: '+str(e)[:160])

def validate_recipient_pin(text,company):
    """Fail closed if we cannot connect the PIN to the recipient company."""
    lines=[re.sub(r'\s+',' ',s).strip().upper() for s in text.splitlines()]
    wanted=company.kra_pin.upper()
    pins=set(x.upper() for x in PIN_RE.findall(text))
    if wanted not in pins:
        if pins:raise ExtractError('Invoice PIN does not match the selected group company. PINs detected: '+', '.join(sorted(pins)[:3]))
        raise ExtractError('No readable KRA PIN was found on the invoice.')
    # Guard against accidentally accepting the supplier's PIN.
    keywords=('BILL TO','BILLED TO','CUSTOMER','BUYER','RECIPIENT','INVOICE TO','SOLD TO','CLIENT','TO:')
    supplier_words=('SUPPLIER','VENDOR','SELLER','FROM:')
    for i,line in enumerate(lines):
        if wanted not in line:continue
        block=' '.join(lines[max(0,i-3):i+2])
        close_context=any(k in block for k in keywords) or company.name.upper() in block
        supplier_only=any(k in block for k in supplier_words) and not close_context
        if close_context and not supplier_only:return True
    raise ExtractError('The company PIN appears, but the system cannot confirm it belongs to the invoice recipient. Check the Bill To/Customer section.')

def guess_fields(text):
    from decimal import Decimal,InvalidOperation
    from datetime import datetime
    d={};lines=text.splitlines()
    pats={'invoice_number':r'(?im)^\s*(?:invoice\s*(?:no\.?|number|#)|inv\s*#)\s*[:#-]?\s*([A-Za-z0-9/-]+)',
          'po_number':r'(?im)^\s*(?:purchase\s*order\s*(?:no\.?|number|#)?|PO\s*(?:no\.?|number|#))\s*[:#-]?\s*([A-Za-z0-9/-]+)',
          'invoice_date':r'(?im)^\s*(?:invoice\s*date|date)\s*[:#-]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})'}
    for key,pat in pats.items():
        m=re.search(pat,text)
        if m:d[key]=m.group(1)
    if 'invoice_date' in d:
        date=d['invoice_date']
        for fmt in ('%Y-%m-%d','%d/%m/%Y','%d-%m-%Y'):
            try:d['invoice_date']=datetime.strptime(date,fmt).date();break
            except ValueError:pass
        if isinstance(d['invoice_date'],str):d.pop('invoice_date')
    m=CURRENCY_RE.search(text)
    if m:d['currency']=m.group(1).upper()
    money_patterns={'net_amount':r'(?im)^\s*(?:net(?:\s*amount)?|subtotal|sub-total|amount\s*before\s*vat)\s*[:=-]?\s*(?:KES|USD|EUR|GBP)?\s*([0-9,]+\.\d{2})',
     'vat_amount':r'(?im)^\s*(?:VAT|VAT\s*amount|tax\s*amount)\s*[:=-]?\s*(?:KES|USD|EUR|GBP)?\s*([0-9,]+\.\d{2})',
     'total_amount':r'(?im)^\s*(?:grand\s*total|total\s*(?:amount|due)?)\s*[:=-]?\s*(?:KES|USD|EUR|GBP)?\s*([0-9,]+\.\d{2})'}
    for key,pat in money_patterns.items():
        m=re.search(pat,text)
        if m:
            try:d[key]=Decimal(m.group(1).replace(',',''))
            except InvalidOperation:pass
    return d
