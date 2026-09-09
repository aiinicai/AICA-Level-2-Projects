from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from config import APP_NAME, APP_SUBTITLE, APP_FOOTER

def export_dataframe_to_pdf(df, filepath, title, financial_year=""):
    styles = getSampleStyleSheet()
    
    # Style for standard body cells
    style_n = styles["Normal"]
    style_n.fontSize = 7
    style_n.leading = 9

    # Style specifically for centered headers
    style_h = getSampleStyleSheet()["Normal"]
    style_h.fontSize = 7
    style_h.leading = 9
    style_h.alignment = 1 # Center alignment

    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4), 
                            leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=30)
    
    elements = [
        Paragraph(f"<b>{APP_NAME}</b>", styles["Title"]),
        Paragraph(title, styles["Heading2"]),
        Paragraph(f"Report Date: {datetime.now().strftime('%d-%b-%Y')}", styles["Normal"]),
        Spacer(1, 12),
    ]

    # --- HEADER FIX: Wrapped in White Font Tag ---
    headers = [Paragraph(f'<b><font color="white">{str(col)}</font></b>', style_h) for col in df.columns]
    data = [headers]
    
    for row in df.values.tolist():
        formatted_row = []
        for cell in row:
            clean_text = str(cell) if cell is not None and str(cell) != 'nan' else ""
            formatted_row.append(Paragraph(clean_text, style_n))
        data.append(formatted_row)
    
    num_cols = len(df.columns)
    available_width = 780 
    col_width = available_width / num_cols

    table = Table(data, repeatRows=1, colWidths=[col_width] * num_cols)
    table.setStyle(TableStyle([
        # Header Styling
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")), # Dark Blue/Grey background
        ("ALIGN", (0, 0), (-1, 0), 'CENTER'),
        ("VALIGN", (0, 0), (-1, 0), 'MIDDLE'),
        
        # Grid and Body Styling
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 1), (-1, -1), 'TOP'),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(APP_FOOTER, styles["Normal"]))
    
    doc.build(elements)
    return filepath