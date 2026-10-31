"""Inspect and exercise the bundled Python libraries without networking or pip."""
import importlib.metadata as metadata
import json,tempfile
from pathlib import Path
import reportlab,arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image
from reportlab.pdfgen import canvas
packages=['reportlab','arabic-reshaper','python-bidi','Pillow','charset-normalizer']
versions={name:metadata.version(name) for name in packages}
with tempfile.TemporaryDirectory() as folder:
    target=Path(folder)/'offline-check.pdf';pdf=canvas.Canvas(str(target));pdf.drawString(50,750,'SALES360 offline dependency check');pdf.save();assert target.read_bytes().startswith(b'%PDF-')
    assert get_display(arabic_reshaper.reshape('مرحبا'))
    Image.new('RGB',(2,2),'white').save(Path(folder)/'check.png')
print(json.dumps({'offline':True,'apiKeysRequired':False,'packages':versions,'pdf':True,'arabic':True,'image':True},indent=2))
