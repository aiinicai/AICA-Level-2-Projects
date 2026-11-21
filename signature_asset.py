"""Private, portable signer images. Never used as an architect/valuer identity."""
import base64,hashlib,io
from pathlib import Path

def select_image(path):
    from PIL import Image
    data=Path(path).read_bytes()
    if len(data)>8*1024*1024:raise ValueError('Choose a signature image smaller than 8 MB.')
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in ('JPEG','PNG'):raise ValueError('Choose a JPEG or PNG signature.')
        if image.width*image.height>20000000:raise ValueError('Signature dimensions are too large.')
        image.verify()
    return dict(name=Path(path).name,data_base64=base64.b64encode(data).decode('ascii'),sha256=hashlib.sha256(data).hexdigest())

def image_bytes(settings):
    if not settings.get('signature_enabled'):return None
    asset=settings.get('signature_image')
    if not asset:raise ValueError('Signature is enabled but no image is selected. Choose an image or untick Include signature.')
    try:
        data=base64.b64decode(asset['data_base64'],validate=True)
        if len(data)>8*1024*1024:raise ValueError('Saved image exceeds 8 MB.')
        if hashlib.sha256(data).hexdigest()!=asset['sha256']:raise ValueError('Signature image checksum mismatch.')
        from PIL import Image
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in ('JPEG','PNG') or image.width*image.height>20000000:raise ValueError('Unsupported or oversized saved image.')
            image.verify()
        return data
    except Exception as exc:raise ValueError('Saved signature image is invalid; select it again or disable it.') from exc

def fit_dimensions(data,max_width=180,max_height=65):
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:w,h=image.size
    factor=min(max_width/w,max_height/h)
    return w*factor,h*factor

def word_signature(doc,settings):
    data=image_bytes(settings)
    if data:
        from docx.shared import Inches
        width,height=fit_dimensions(data,180,65)
        doc.add_paragraph().add_run().add_picture(io.BytesIO(data),width=Inches(width/96),height=Inches(height/96))

def pdf_signature(settings):
    data=image_bytes(settings)
    if not data:return None
    from reportlab.platypus import Image
    w,h=fit_dimensions(data,135,49)
    return Image(io.BytesIO(data),width=w,height=h,hAlign='LEFT')

def excel_signature(ws,settings,anchor):
    data=image_bytes(settings)
    if data:
        from openpyxl.drawing.image import Image
        image=Image(io.BytesIO(data));image.width,image.height=fit_dimensions(data)
        ws.add_image(image,anchor)
