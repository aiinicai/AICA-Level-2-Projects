"""Optional local OCR; one page at a time, no network."""
import os, shutil, subprocess, tempfile
from pathlib import Path

def executable():
    candidates=[os.environ.get('TESSERACT_CMD'),shutil.which('tesseract'),str(Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Tesseract-OCR'/'tesseract.exe'),str(Path(os.environ.get('LOCALAPPDATA',''))/'Programs'/'Tesseract-OCR'/'tesseract.exe')]
    return next((p for p in candidates if p and Path(p).is_file()),None)

def languages():
    exe=executable()
    if not exe: return []
    r=subprocess.run([exe,'--list-langs'],capture_output=True,text=True,timeout=15,check=True)
    return [x.strip() for x in r.stdout.splitlines() if x.strip() and not x.startswith('List of')]

def read_page(page,lang='eng'):
    exe=executable()
    if not exe: raise ValueError('Tesseract not installed. See OCR_SETUP.txt, then restart the app.')
    import fitz
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'page.png'
        scale=min(200/72,2200/max(page.rect.width,page.rect.height))
        page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False).save(str(path))
        env=dict(os.environ,OMP_THREAD_LIMIT='2')
        r=subprocess.run([exe,str(path),'stdout','-l',lang,'--psm','3'],capture_output=True,timeout=90,env=env)
        if r.returncode: raise ValueError(r.stderr.decode('utf-8','replace')[:500])
        return r.stdout.decode('utf-8','replace').strip()
