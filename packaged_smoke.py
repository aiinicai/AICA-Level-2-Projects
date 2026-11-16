"""Smoke check executed inside the frozen executable; does not alter real invoices."""
def run(app, output):
    import tempfile,json
    from pathlib import Path
    from gui import MainWindow
    from invoice_pdf import generate
    from pdf_view import QPdfDocument
    from PyQt6.QtCore import QSize
    from PyQt6.QtPrintSupport import QPrinter
    with tempfile.TemporaryDirectory() as temp:
        window=MainWindow(temp); window.show(); app.processEvents()
        window.store.seller({'trade_name':'Smoke Test Seller','address':'Test address'})
        window.customer['name'].setText('Test customer'); window.customer['address'].setText('Test address')
        window.table.item(0,0).setText('Test item'); window.table.item(0,2).setText('100'); window.table.item(0,3).setText('18')
        record=window.save(); assert record['grand_total']=='118.00'
        window.load(record)
        pdf=generate(record,Path(temp)/'invoice.pdf'); doc=QPdfDocument(); doc.load(str(pdf)); assert doc.pageCount()>0
        assert not doc.render(0,QSize(600,850)).isNull()
        printer=QPrinter(); printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat); printer.setOutputFileName(str(Path(temp)/'print.pdf')); window.render_print(doc,printer); doc.close()
        window.grab().save(str(Path(output).with_suffix('.png')))
        window.dirty=False; window.close()
    Path(output).write_text(json.dumps({'passed':True,'checks':['frozen startup','Qt GUI','JSON save and reload','GST calculation','ReportLab PDF','PDF rendering','virtual printing','license countdown']},indent=2))
