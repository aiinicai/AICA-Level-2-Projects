"""Run with the same Python as main.py. Tests use isolated temporary data."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'.vendor'))
import tempfile
import unittest
from billing_core import calculate,Store
from invoice_pdf import generate
from PyQt6.QtWidgets import QApplication
from PyQt6.QtPrintSupport import QPrinter
from pdf_view import QPdfDocument
from gui import MainWindow

APP=QApplication.instance() or QApplication([])
SELLER={'trade_name':'Blue River Supplies','address':'12 Market Road\nMumbai, Maharashtra 400001','mobile':'9876543210','gst':'27ABCDE1234F1Z5','bank':'Example Bank | A/c 1234567890\nIFSC: EXAM0001234','declaration':'Goods supplied as described. Thank you for your business.'}
ITEMS=[dict(name='Office stationery bundle',quantity='2',rate='125.25',gst='18'),dict(name='Printer paper - A4',quantity='3',rate='249.50',gst='12')]
def invoice(items=ITEMS):
    return dict(number=None,date='2026-11-03',seller=SELLER,customer=dict(name='Sample Customer',address='45 Business Avenue\nMumbai 400002',mobile='9123456780',gst=''),rounded=True,**calculate(items,True))

class Tests(unittest.TestCase):
    def test_database_selection_and_expired_controls(self):
        from unittest.mock import patch
        from PyQt6.QtWidgets import QMessageBox,QPushButton
        import time
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); window=MainWindow(root); window.store.seller(SELLER)
            selected=root/'alternate'; selected.mkdir()
            with patch('gui.QFileDialog.getExistingDirectory',return_value=str(selected)),patch('gui.QMessageBox.question',return_value=QMessageBox.StandardButton.Yes):
                window.database_folder()
            self.assertEqual(window.store.path,selected/'billing.json')
            self.assertEqual(window.store.read()['seller']['trade_name'],SELLER['trade_name'])
            import json
            self.assertEqual(Path(json.loads(window.config_path.read_text())['database_dir']).resolve(),selected.resolve())
            window.license.state['expires']=time.time()-1; window.license_tick()
            self.assertFalse(window.table.isEnabled())
            self.assertTrue(next(b for b in window.findChildren(QPushButton) if b.text()=='Activate').isEnabled())
            window.dirty=False; window.close()
            reopened=MainWindow(root); self.assertEqual(reopened.store.path.resolve(),(selected/'billing.json').resolve()); reopened.dirty=False; reopened.close()

    def test_calculations(self):
        result=calculate(ITEMS,True)
        self.assertEqual(result['subtotal'],'999.00'); self.assertEqual(result['total_gst'],'134.91'); self.assertEqual(result['grand_total'],'1134.00'); self.assertEqual(result['round_off'],'0.09')
        self.assertEqual(calculate([dict(name='x',quantity=1,rate='0.05',gst=10)])['total_gst'],'0.01')
        for key,value in [('quantity','0'),('rate','-1'),('gst','101'),('rate','NaN'),('gst','Infinity'),('name','')]:
            item=ITEMS[0].copy(); item[key]=value
            with self.assertRaises(ValueError): calculate([item])

    def test_database(self):
        with tempfile.TemporaryDirectory() as temp:
            store=Store(temp); store.seller(SELLER)
            first=store.save(invoice()); self.assertEqual(first['number'],'INV-000001')
            first['customer']['name']='Edited'; store.save(first)
            self.assertEqual(Store(temp).read()['invoices'][0]['customer']['name'],'Edited')
            store.delete(first['number']); self.assertEqual(store.save(invoice())['number'],'INV-000002')
            self.assertTrue(Path(str(store.path)+'.bak').exists())
            store.path.write_text('{bad')
            with self.assertRaises(ValueError): Store(temp)
            self.assertEqual(store.path.read_text(),'{bad')

    def test_gui_pdf_and_print(self):
        with tempfile.TemporaryDirectory() as temp:
            window=MainWindow(temp); window.store.seller(SELLER)
            window.customer['name'].setText('Sample Customer'); window.customer['address'].setText('Customer address')
            window.table.item(0,0).setText('Test item'); window.table.item(0,2).setText('100'); window.table.item(0,3).setText('18')
            saved=window.save(); self.assertEqual(saved['grand_total'],'118.00'); self.assertFalse(window.dirty)
            window.load(saved); self.assertEqual(window.collect()['grand_total'],'118.00')
            window.table.item(0,1).setText('2'); self.assertTrue(window.dirty); self.assertEqual(window.collect()['grand_total'],'236.00')
            path=generate(window.collect(),Path(temp)/'test.pdf'); doc=QPdfDocument(); self.assertEqual(doc.load(str(path)),QPdfDocument.Error.None_)
            self.assertGreater(doc.pageCount(),0); self.assertFalse(doc.render(0,__import__('PyQt6.QtCore',fromlist=['QSize']).QSize(800,1100)).isNull())
            printer=QPrinter(); printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat); printer.setOutputFileName(str(Path(temp)/'printed.pdf')); window.render_print(doc,printer)
            self.assertGreater((Path(temp)/'printed.pdf').stat().st_size,1000); doc.close()
            window.dirty=False; window.close()

    def test_multipage(self):
        with tempfile.TemporaryDirectory() as temp:
            path=generate(invoice([dict(name='Long description with symbols < > & and wrapping. '*3,quantity='1',rate='25',gst='18') for _ in range(90)]),Path(temp)/'long.pdf')
            doc=QPdfDocument(); doc.load(str(path)); self.assertGreater(doc.pageCount(),3)
            text=' '.join(doc.getAllText(i).text() for i in range(doc.pageCount()))
            self.assertIn('GRAND TOTAL',text); self.assertIn('Authorised Signatory',text); doc.close()

if __name__=='__main__':
    if '--sample' in sys.argv:
        output=Path(__file__).parent/'invoices_pdf'; output.mkdir(exist_ok=True)
        sample=invoice(); sample['number']='SAMPLE-001'; generate(sample,output/'Sample Invoice.pdf')
        doc=QPdfDocument(); doc.load(str(output/'Sample Invoice.pdf'))
        from PyQt6.QtCore import QSize
        doc.render(0,QSize(1190,1684)).save(str(output/'Sample Invoice.png')); doc.close()
    else: unittest.main(verbosity=2)
