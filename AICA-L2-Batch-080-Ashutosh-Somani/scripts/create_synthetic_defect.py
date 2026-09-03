from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pathlib import Path

def create_synthetic_pdf():
    samples_dir = Path('c:/Users/Ashutosh/Downloads/PDF to Excel Capstone/Antigravity/samples')
    samples_dir.mkdir(exist_ok=True)
    pdf_path = samples_dir / 'synthetic_defect_test.pdf'
    
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    
    # Write Bank Name
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Bank of Synthetic Baroda")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, "Account: XXXXXX1234")
    c.drawString(50, height - 85, "Period: 01-Jan-2023 to 31-Jan-2023")
    
    # Headers
    c.setFont("Helvetica-Bold", 10)
    y = height - 120
    c.drawString(15, y, "Date")
    c.drawString(87, y, "Value Date")
    c.drawString(165, y, "Narration")
    c.drawString(450, y, "Chq/RefNo")
    c.drawString(518, y, "Withdrawal")
    c.drawString(631, y, "Deposit")
    c.drawString(738, y, "Balance")
    
    # Add a single bounding box around the whole thing to trick pdfplumber into 1 column
    c.rect(10, height - 300, 800, 200) # One big rect
    
    # Transaction 1
    c.setFont("Helvetica", 9)
    y -= 20
    c.drawString(15, y, "01/01/2023")
    c.drawString(87, y, "01/01/2023")
    c.drawString(165, y, "Opening Balance")
    c.drawString(738, y, "1000.00")
    
    # Transaction 2
    y -= 20
    c.drawString(15, y, "02/01/2023")
    c.drawString(87, y, "02/01/2023")
    c.drawString(165, y, "ATM Withdrawal")
    c.drawString(518, y, "200.00")
    c.drawString(738, y, "800.00")
    
    # Transaction 3
    y -= 20
    c.drawString(15, y, "05/01/2023")
    c.drawString(87, y, "05/01/2023")
    c.drawString(165, y, "Salary Credit")
    c.drawString(631, y, "2500.50")
    c.drawString(738, y, "3300.50")
    
    c.save()
    print("Created synthetic PDF:", pdf_path)

if __name__ == '__main__':
    create_synthetic_pdf()
