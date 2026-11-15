"""Portable local letterpad assets. PDF is rasterized, never executed."""
import io,copy,hashlib,base64
from pathlib import Path
from PIL import Image
from signature_asset import select_image,image_bytes,fit_dimensions

def packed_image(image,name):
    stream=io.BytesIO();image.save(stream,format='PNG');data=stream.getvalue()
    return dict(name=name,data_base64=base64.b64encode(data).decode('ascii'),sha256=hashlib.sha256(data).hexdigest())

def load_letterpad(path,mode='Header image'):
    p=Path(path)
    if mode not in ('Header image','Whole-page letterpad'):raise ValueError('Choose Header image or Whole-page letterpad.')
    if p.stat().st_size>20*1024*1024:raise ValueError('Letterpad file must be 20 MB or smaller.')
    if p.suffix.lower()=='.pdf':
        import pymupdf
        with pymupdf.open(p) as doc:
            if doc.needs_pass:raise ValueError('Choose an unlocked letterpad PDF.')
            if len(doc)!=1:raise ValueError('Use a one-page letterpad PDF; extra pages are not silently discarded.')
            if doc[0].rect.width*doc[0].rect.height*2.25>20000000:raise ValueError('Letterpad PDF dimensions are too large.')
            pix=doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False);image=Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    else:
        asset=select_image(p);image=Image.open(io.BytesIO(image_bytes(dict(signature_enabled=True,signature_image=asset)))).convert('RGB')
    if mode=='Whole-page letterpad':
        w,h=image.size;header=image.crop((0,0,w,max(1,int(h*.118))));footer=image.crop((0,int(h*.933),w,h))
        result=dict(header=packed_image(header,p.stem+' header.png'),footer=packed_image(footer,p.stem+' footer.png'),background=packed_image(image,p.stem+' whole page.png'))
    else:result=dict(header=packed_image(image,p.stem+' header.png'),footer=None)
    return dict(result,enabled=True,mode=mode,source_name=p.name,include_first_page=True)

def get_bytes(letterpad,position):
    if not letterpad or not letterpad.get('enabled'):return None
    asset=letterpad.get(position)
    return image_bytes(dict(signature_enabled=True,signature_image=asset)) if asset else None

def add_excel_letterpad(wb,case):
    from openpyxl.drawing.image import Image as XLImage
    letterpad=effective_letterpad(case.settings)
    if not letterpad.get('enabled') or letterpad.get('background'):return
    from print_layout import layout_from
    selected=layout_from(case.report,case.settings)['sections']
    first=next((sh.title for sh in wb if sh.title in selected),None)
    for sh in wb:
        if sh.title==first and not letterpad.get('include_first_page',True):continue
        if sh.title in ('SUMMARY','Sheet1'):continue
        for position in ('header','footer'):
            data=get_bytes(letterpad,position)
            if not data:continue
            image=XLImage(io.BytesIO(data));image.width,image.height=fit_dimensions(data,700,90 if position=='header' else 65)
            row=3 if position=='header' else sh.max_row+2
            sh.row_dimensions[row].height=max(sh.row_dimensions[row].height or 25,image.height*.75+8)
            sh.add_image(image,'A'+str(row))
            if position=='footer':sh.cell(row,1,' ')

def effective_letterpad(settings):
    selected=settings.get('letterpad') or {}
    # A selected custom pad can be disabled independently. Otherwise retain the
    # original app's firm-logo header, now embedded rather than path-dependent.
    if selected.get('header') or selected.get('footer') or selected.get('background'):return selected
    if settings.get('logo_image'):
        return dict(enabled=settings.get('letterhead_enabled',True),header=settings['logo_image'],footer=None,include_first_page=settings.get('letterhead_first_page',True))
    return selected
