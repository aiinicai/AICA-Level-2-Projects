import io
import os
from typing import List, Dict, Any
import docx
from docx.shared import Inches, Pt, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn
from .barcode_service import generate_barcode_image, generate_qr_image

def set_cell_border(cell, **kwargs):
    """
    Set cell borders
    kwargs: top, bottom, left, right
    values: dict(sz=12, val='single', color='334155', space='0')
    """
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(r'<w:tcBorders %s/>' % nsdecls('w'))
    for border_name in ['top', 'left', 'bottom', 'right']:
        edge = parse_xml(r'<w:%s %s w:val="single" w:sz="6" w:space="0" w:color="475569"/>' % (border_name, nsdecls('w')))
        tcBorders.append(edge)
    tcPr.append(tcBorders)

def generate_sheet_docx(
    assets_data: List[Dict[str, Any]],
    columns: int = 2,
    rows_per_page: int = 7,
    page_size: str = "A4"
) -> io.BytesIO:
    """
    Generates an editable Microsoft Word (.docx) document formatted with asset label tables.
    """
    doc = docx.Document()

    # Configure Margins to 10mm
    sections = doc.sections
    for s in sections:
        s.top_margin = Mm(10)
        s.bottom_margin = Mm(10)
        s.left_margin = Mm(10)
        s.right_margin = Mm(10)
        if page_size.upper() == "A3":
            s.page_width = Mm(297)
            s.page_height = Mm(420)
        else:
            s.page_width = Mm(210)
            s.page_height = Mm(297)

    labels_per_page = columns * rows_per_page
    total_assets = len(assets_data)

    # Chunk assets by page
    for p_start in range(0, total_assets, labels_per_page):
        if p_start > 0:
            doc.add_page_break()

        page_assets = assets_data[p_start : p_start + labels_per_page]
        
        # Create Table for this page
        table = doc.add_table(rows=rows_per_page, cols=columns)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        cell_w_in = 7.5 / columns      # plain float inches
        cell_h_in = 10.0 / rows_per_page  # plain float inches

        for row_idx in range(rows_per_page):
            # Set row height
            table.rows[row_idx].height = Inches(cell_h_in)
            for col_idx in range(columns):
                item_idx = (row_idx * columns) + col_idx
                cell = table.cell(row_idx, col_idx)
                cell.width = Inches(cell_w_in)
                set_cell_border(cell)

                if item_idx < len(page_assets):
                    ast = page_assets[item_idx]
                    p = cell.paragraphs[0]
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.space_after = Pt(2)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

                    # Company Header
                    run_comp = p.add_run(f"{(ast.get('company_name') or 'COMPANY').upper()}\n")
                    run_comp.font.name = 'Arial'
                    run_comp.font.size = Pt(8)
                    run_comp.font.bold = True
                    run_comp.font.color.rgb = RGBColor(15, 23, 42)

                    # Details
                    p_details = cell.add_paragraph()
                    p_details.paragraph_format.space_before = Pt(0)
                    p_details.paragraph_format.space_after = Pt(2)
                    p_details.paragraph_format.line_spacing = 1.0

                    sap = ast.get('sap_number') or '-'
                    desc = (ast.get('description') or '').upper()
                    loc = (ast.get('location') or '-').upper()
                    code_type = (ast.get('code_type') or 'BARCODE').upper()
                    asset_id = ast.get('asset_id') or 'AST-000000'

                    run_txt = p_details.add_run(f"SAP NO: {sap}\nDESC: {desc[:24]}\nLOC: {loc[:20]}\n")
                    run_txt.font.name = 'Arial'
                    run_txt.font.size = Pt(7)
                    run_txt.font.bold = True

                    # Embed Barcode or QR Image
                    p_img = cell.add_paragraph()
                    p_img.paragraph_format.space_before = Pt(1)
                    p_img.paragraph_format.space_after = Pt(1)
                    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER

                    if "QR" in code_type:
                        qr_img = generate_qr_image(asset_id, box_size=4, border=1)
                        img_buf = io.BytesIO()
                        qr_img.save(img_buf, format="PNG")
                        img_buf.seek(0)
                        p_img.add_run().add_picture(img_buf, width=Inches(0.6))
                    else:
                        bc_img = generate_barcode_image(asset_id)
                        img_buf = io.BytesIO()
                        bc_img.save(img_buf, format="PNG")
                        img_buf.seek(0)
                        p_img.add_run().add_picture(img_buf, width=Inches(1.8), height=Inches(0.35))

                    run_id = p_img.add_run(f"\n{asset_id}")
                    run_id.font.name = 'Arial'
                    run_id.font.size = Pt(7)
                    run_id.font.bold = True

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

def generate_single_label_docx(
    asset_data: Dict[str, Any],
    width_mm: float = 70.0,
    height_mm: float = 35.0
) -> io.BytesIO:
    """
    Generates a single label formatted Microsoft Word (.docx) document.
    """
    return generate_sheet_docx([asset_data], columns=1, rows_per_page=1, page_size="A4")

