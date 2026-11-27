"""Generate the four fictional reports for disposable test folders."""
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


def draw(path, title, headers, xs, records, cutoff="2026-11-20"):
    width, height = landscape(A4)
    c = canvas.Canvas(str(path), pagesize=(width, height), invariant=1)
    c.setTitle(title + " | Fictional demonstration")
    c.setAuthor("Construction Cash Flow Planner")
    for start in range(0, max(1, len(records)), 16):
        page = records[start:start+16]
        c.setFillColor(HexColor("#153B43"))
        c.rect(0, height-91, width, 91, fill=1, stroke=0)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", 23)
        c.drawString(42, height-43, title)
        c.setFont("Helvetica", 11)
        c.drawString(42, height-67, f"As of {cutoff} | Currency OMR | Demo v1")
        y = height - 121
        c.setFillColor(HexColor("#E6F1EF"))
        c.rect(36, y-9, width-72, 29, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(HexColor("#19564E"))
        for x, heading in zip(xs, headers):
            c.drawString(x, y, heading)
        c.setFont("Helvetica", 11)
        for row in page:
            y -= 23
            c.setFillColor(HexColor("#253D49"))
            for x, value in zip(xs, row):
                if str(value):
                    c.drawString(x, y, str(value))
            c.setStrokeColor(HexColor("#D5DFDF"))
            c.line(36, y-7, width-36, y-7)
        c.setFillColor(HexColor("#536970"))
        c.setFont("Helvetica", 9)
        c.drawString(42, 36, f"Records on page: {len(page)}")
        c.showPage()
    c.save()


def build(folder, cutoff="2026-11-20", replacement="LTR-704"):
    folder = Path(folder)
    summary = [
        ("Opening cash","44400.000"),("Collections","40500.000"),("Retention","1500.000"),("Other income","0.000"),
        ("Materials","-9400.250"),("Labour","-8600.000"),("Site overhead","-1650.000"),("Creditors","-6100.000"),
        ("Expenses payable","0.000"),("PDC","-2500.000"),("LC/LTR","-4200.000"),("Head office","-2800.000"),
        ("Management overhead","0.000"),("Marketing","0.000"),("Finance charges","0.000"),("Tax","0.000"),
        ("Fixed assets","0.000"),("Funding","-900.000"),("Closing cash","50249.750")]
    detail = [
        ("2026-11-04","RCPT-101","00107","Collections","29000.000"),("2026-11-14","RCPT-102","00213","Collections","11500.000"),
        ("2026-11-17","RTN-001","00107","Retention","1500.000"),("2026-11-05","M-101","00107","Materials","-9400.250"),
        ("2026-11-08","LAB-101","00213","Labour","-8600.000"),("2026-11-09","SITE-101","00107","Site overhead","-1650.000"),
        ("2026-11-12","VEND-201","","Creditors","-6100.000"),("2026-11-15","CH-019","","PDC","-2500.000"),
        ("2026-11-16","LC-610","","LC/LTR","-4200.000"),("2026-11-19","HO-111","","Head office","-2800.000"),
        ("2026-11-20","FIN-501","","Funding","-900.000")]
    cheques = [
        ("CH-020","Copper Sand","2026-10-28","1250.375","Outstanding",""),
        ("CH-021","Cedar Plant","2026-11-28","4750.000","Outstanding",""),
        ("CH-022","Birch Steel","2026-11-22","2000.125","Replaced",replacement),
        ("CH-023","Birch Steel","2026-11-29","1750.000","Replaced",replacement),
        ("CH-024","Cobalt Hire","2026-11-26","9600.000","Security",""),
        ("CH-019","Cedar Plant","2026-11-15","2500.000","Settled",""),
        ("CH-025","Arc Formwork","2026-12-17","6200.000","Outstanding",""),
        ("CH-026","Quartz Tools","2027-01-24","2400.000","Outstanding","")]
    projections = [(m,"PDC Payable",n) for m,n in zip(("2026-11","2026-12","2027-01"),("6000.375","6200.000","2400.000"))]
    projections.append(("2026-12","Gross creditor estimate","38000.000"))
    draw(folder/"CF.pdf","Actual cash summary",("Category","Amount"),(42,416),summary,cutoff)
    draw(folder/"CF-Detailed.pdf","Actual cash detail",("Date","Reference","Project","Category","Amount"),(42,191,343,449,691),detail,cutoff)
    draw(folder/"PDC.pdf","Cheque register",("Cheque","Party","Cheque date","Amount","Status","LTR"),(42,139,322,453,570,705),cheques,cutoff)
    draw(folder/"CF-Proj.pdf","Projected payments",("Month","Category","Amount"),(42,228,614),projections,cutoff)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="An existing empty output directory")
    args = parser.parse_args()
    if not args.folder.is_dir() or any(args.folder.iterdir()):
        parser.error("Use an existing empty directory to protect other reports.")
    build(args.folder)
