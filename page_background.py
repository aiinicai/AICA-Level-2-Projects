"""Whole-page print artwork: Word behind-text anchors and Excel header VML images.
No executable content/macros. Office-specific pagination needs native app QA.
"""
import io,zipfile,xml.etree.ElementTree as ET
from signature_asset import fit_dimensions


def word_background(section,data,layout):
    from docx.shared import Mm
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    w,h=fit_dimensions(data,layout['width_mm'],layout['height_mm'])
    paragraph=section.header.paragraphs[0]
    inline=paragraph.add_run().add_picture(io.BytesIO(data),width=Mm(w),height=Mm(h))._inline
    anchor=OxmlElement('wp:anchor')
    for k,v in dict(distT='0',distB='0',distL='0',distR='0',simplePos='0',relativeHeight='0',behindDoc='1',locked='0',layoutInCell='0',allowOverlap='1').items():anchor.set(k,v)
    simple=OxmlElement('wp:simplePos');simple.set('x','0');simple.set('y','0');anchor.append(simple)
    for axis,offset in [('H',(layout['width_mm']-w)/2),('V',(layout['height_mm']-h)/2)]:
        position=OxmlElement('wp:position'+axis);position.set('relativeFrom','page');pos=OxmlElement('wp:posOffset');pos.text=str(int(Mm(offset)));position.append(pos);anchor.append(position)
    for child in list(inline):
        anchor.append(child)
        if child.tag==qn('wp:extent'):anchor.append(OxmlElement('wp:wrapNone'))
    inline.getparent().replace(inline,anchor)


def excel_background(path,case):
    from letterpad_asset import effective_letterpad,get_bytes
    from print_layout import layout_from
    pad=effective_letterpad(case.settings);data=get_bytes(pad,'background')
    if not data:return
    layout=layout_from(case.report,case.settings);w,h=fit_dimensions(data,layout['width_mm'],layout['height_mm'])
    main='http://schemas.openxmlformats.org/spreadsheetml/2006/main';rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships';package='http://schemas.openxmlformats.org/package/2006/relationships';ct='http://schemas.openxmlformats.org/package/2006/content-types'
    with zipfile.ZipFile(path) as z:parts={n:z.read(n) for n in z.namelist()}
    workbook=ET.fromstring(parts['xl/workbook.xml']);relationships=ET.fromstring(parts['xl/_rels/workbook.xml.rels'])
    targets={r.attrib['Id']:r.attrib['Target'] for r in relationships}
    types=ET.fromstring(parts['[Content_Types].xml'])
    for extension,kind in [('vml','application/vnd.openxmlformats-officedocument.vmlDrawing'),('png','image/png')]:
        if not any(r.attrib.get('Extension')==extension for r in types):ET.SubElement(types,'{'+ct+'}Default',Extension=extension,ContentType=kind)
    index=0
    for sheet in workbook.find('{'+main+'}sheets'):
        if sheet.attrib['name'] not in layout['sections']:continue
        index+=1;target=targets[sheet.attrib['{'+rel+'}id']];sheetpath=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        tree=ET.fromstring(parts[sheetpath]);header=tree.find('{'+main+'}headerFooter')
        if header is None:header=ET.SubElement(tree,'{'+main+'}headerFooter')
        header.set('scaleWithDoc','0');header.set('alignWithMargins','0')
        if not pad.get('include_first_page',True) and index==1:
            header.set('differentFirst','1');first=header.find('{'+main+'}firstHeader')
            if first is None:first=ET.SubElement(header,'{'+main+'}firstHeader')
            first.text=''
        odd=header.find('{'+main+'}oddHeader')
        if odd is None:odd=ET.SubElement(header,'{'+main+'}oddHeader')
        odd.text='&C&G'
        order=['oddHeader','oddFooter','evenHeader','evenFooter','firstHeader','firstFooter']
        children=sorted(list(header),key=lambda e:order.index(e.tag.rsplit('}',1)[-1]))
        for child in list(header):header.remove(child)
        for child in children:header.append(child)
        margins=tree.find('{'+main+'}pageMargins')
        if margins is not None:margins.set('header','0')
        stem='letterpad'+str(index);vmlpath='xl/drawings/'+stem+'.vml';media='xl/media/'+stem+'.png'
        parts[media]=data
        # Header CH (centre header) is Excel's documented VML picture shape ID.
        widthpt=w*72/25.4;heightpt=h*72/25.4
        parts[vmlpath]=f'''<xml xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office"><o:shapelayout v:ext="edit"><o:idmap v:ext="edit" data="1"/></o:shapelayout><v:shapetype id="_x0000_t75" coordsize="21600,21600" o:spt="75" o:preferrelative="t" path="m@4@5l@4@11@9@11@9@5xe" filled="f" stroked="f"><v:stroke joinstyle="miter"/><v:formulas><v:f eqn="if lineDrawn pixelLineWidth 0"/><v:f eqn="sum @0 1 0"/><v:f eqn="sum 0 0 @1"/><v:f eqn="prod @2 1 2"/><v:f eqn="prod @3 21600 pixelWidth"/><v:f eqn="prod @3 21600 pixelHeight"/><v:f eqn="sum @0 0 1"/><v:f eqn="prod @6 1 2"/><v:f eqn="prod @7 21600 pixelWidth"/><v:f eqn="sum @8 21600 0"/><v:f eqn="prod @7 21600 pixelHeight"/><v:f eqn="sum @10 21600 0"/></v:formulas><v:path o:extrusionok="f" gradientshapeok="t" o:connecttype="rect"/><o:lock v:ext="edit" aspectratio="t"/></v:shapetype><v:shape id="CH" o:spid="_x0000_s1025" type="#_x0000_t75" style="position:absolute;margin-left:0;margin-top:{(layout["height_mm"]-h)*72/25.4/2:.4f}pt;width:{widthpt:.4f}pt;height:{heightpt:.4f}pt;z-index:1"><v:imagedata o:relid="rId1" o:title="Whole-page letterpad"/><o:lock v:ext="edit" rotation="t"/></v:shape></xml>'''.encode()
        vmlrels=ET.Element('{'+package+'}Relationships');ET.SubElement(vmlrels,'{'+package+'}Relationship',Id='rId1',Type=rel+'/image',Target='../media/'+stem+'.png');parts['xl/drawings/_rels/'+stem+'.vml.rels']=ET.tostring(vmlrels,xml_declaration=True)
        name=sheetpath.rsplit('/',1)[1];sr='xl/worksheets/_rels/'+name+'.rels';srTree=ET.fromstring(parts[sr]) if sr in parts else ET.Element('{'+package+'}Relationships')
        rid='rIdLetterpad';ET.SubElement(srTree,'{'+package+'}Relationship',Id=rid,Type=rel+'/vmlDrawing',Target='../drawings/'+stem+'.vml')
        legacy=ET.SubElement(tree,'{'+main+'}legacyDrawingHF');legacy.set('{'+rel+'}id',rid)
        parts[sr]=ET.tostring(srTree,xml_declaration=True);parts[sheetpath]=ET.tostring(tree,xml_declaration=True)
    parts['[Content_Types].xml']=ET.tostring(types,xml_declaration=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in parts.items():z.writestr(name,content)
