import shutil
import tempfile
from pathlib import Path
from PyQt6.QtCore import Qt, QDate, QMarginsF, QTimer, QLockFile
from PyQt6.QtGui import QPainter, QPageSize, QImage
from PyQt6.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QTextEdit,QDateEdit,QTableWidget,QTableWidgetItem,QPushButton,QLabel,QCheckBox,QMessageBox,QDialog,QDialogButtonBox,QFileDialog,QHeaderView,QAbstractItemView,QSplitter)
from pdf_view import QPdfDocument,QPdfView
from PyQt6.QtPrintSupport import QPrinter,QPrintDialog
from billing_core import Store,calculate
from invoice_pdf import generate

THEME = '''
QWidget {font-family: Segoe UI; font-size: 10pt; color: #193452; background: #ffffff;}
QMainWindow {background: #edf3fb;}
QLineEdit,QTextEdit,QDateEdit {border: 1px solid #c7d5e8; border-radius: 4px; padding: 6px; background: white;}
QPushButton {background: #1557a5; color: white; border: none; border-radius: 4px; padding: 9px 16px;}
QPushButton:hover {background: #2675cf;} QPushButton#danger {background: #c73543;}
QHeaderView::section {background: #e5eefb; padding: 8px; border: 0; font-weight: bold;}
QTableWidget {gridline-color: #e2e9f2; alternate-background-color: #f5f8fd; selection-background-color: #d5e7ff; selection-color: #193452;}
QLabel#title {font-size: 22pt; font-weight: bold; color: #1557a5;}
QLabel#totals {font-size: 14pt; font-weight: bold; color: #1557a5; padding: 12px; background: #eaf2fe;}
'''

class MainWindow(QMainWindow):
    def __init__(self,root):
        super().__init__()
        import json
        self.app_root=Path(root)
        self.config_path=self.app_root/'settings.json'
        config=json.loads(self.config_path.read_text()) if self.config_path.exists() else {}
        self.store=Store(root,config.get('database_dir'))
        self.db_lock=self.acquire_database(self.store)
        from licensing import License
        self.license=License(self.app_root)
        self.number=None
        self.dirty=False
        self.loading=True
        self.setWindowTitle('Smart Billing Manager')
        self.resize(1200,820)
        self.setMinimumSize(900,650)
        self.setStyleSheet(THEME)
        central=QWidget(); self.setCentralWidget(central)
        layout=QVBoxLayout(central); layout.setContentsMargins(24,18,24,18); layout.setSpacing(12)
        heading=QHBoxLayout(); title=QLabel('Smart Billing Manager'); title.setObjectName('title'); heading.addWidget(title); heading.addStretch(); layout.addLayout(heading)
        self.license_label=QLabel(); self.license_label.setStyleSheet('color: #d02030; font-weight: bold;'); heading.addWidget(self.license_label)
        self.button(heading,'Activate',self.activate)
        options=QHBoxLayout(); layout.addLayout(options)
        self.path_label=QLabel(); self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); options.addWidget(self.path_label,1)
        self.button(options,'Database Folder',self.database_folder)
        self.button(heading,'Seller Details',self.seller_dialog)
        toolbar=QHBoxLayout(); layout.addLayout(toolbar)
        for label,action in [('New',self.new),('Save',self.save),('Print',self.print_invoice),('Export PDF',self.export),('Search',self.search),('Delete',self.delete),('Clear',self.new),('Invoice Preview',self.preview)]:
            self.button(toolbar,label,action,label=='Delete')
        meta=QHBoxLayout(); layout.addLayout(meta)
        self.number_label=QLabel(); meta.addWidget(self.number_label); meta.addStretch()
        meta.addWidget(QLabel('Invoice Date'))
        self.date=QDateEdit(QDate.currentDate()); self.date.setCalendarPopup(True); self.date.setDisplayFormat('dd MMM yyyy'); meta.addWidget(self.date); self.date.dateChanged.connect(self.changed)
        self.date.setMinimumWidth(180)
        form=QFormLayout(); layout.addLayout(form)
        self.customer={}
        for key,label in [('name','Customer Name *'),('address','Address *'),('mobile','Mobile'),('gst','GSTIN (optional)')]:
            field=QLineEdit(); field.setMaxLength(500 if key=='address' else 150); form.addRow(label,field); self.customer[key]=field; field.textChanged.connect(self.changed)
        layout.addWidget(QLabel('ITEMS  •  Double-click a cell to edit. Rates exclude GST. Currency: INR'))
        self.table=QTableWidget(0,7); self.table.setHorizontalHeaderLabels(['Item Name','Quantity','Rate','GST %','Amount','GST','Total']); self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        for col in range(1,7): self.table.setColumnWidth(col,115)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self.recalculate); layout.addWidget(self.table,1)
        row=QHBoxLayout(); layout.addLayout(row); self.button(row,'+ Add Item',self.add_row); self.button(row,'Remove Selected',self.remove_rows,True); row.addStretch()
        self.rounded=QCheckBox('Round grand total to nearest rupee'); row.addWidget(self.rounded); self.rounded.stateChanged.connect(self.recalculate)
        self.totals=QLabel(); self.totals.setObjectName('totals'); self.totals.setAlignment(Qt.AlignmentFlag.AlignRight); layout.addWidget(self.totals)
        self.statusBar().showMessage('Offline • Your data stays in '+str(self.store.root/'database'))
        self.loading=False
        self.reset()
        self.refresh_path()
        self.timer=QTimer(self); self.timer.timeout.connect(self.license_tick); self.timer.start(1000); self.license_tick()

    def acquire_database(self,store):
        lock=QLockFile(str(store.path.parent/'database.lock'))
        if not lock.tryLock(100): raise ValueError('This database is already in use by another running application.')
        return lock

    def refresh_path(self):
        self.path_label.setText('Database: '+str(self.store.path))
        self.statusBar().showMessage('Offline | Database: '+str(self.store.path))

    def database_folder(self):
        import json
        if not self.confirm_discard(): return
        folder=QFileDialog.getExistingDirectory(self,'Select folder containing billing.json (or an empty folder)',str(self.store.path.parent))
        if not folder or Path(folder).resolve()==self.store.path.parent.resolve(): return
        try:
            target=Path(folder)/'billing.json'
            if not target.exists():
                answer=QMessageBox.question(self,'New database location','Copy the current database to this folder? Choose No for an empty database.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No|QMessageBox.StandardButton.Cancel)
                if answer==QMessageBox.StandardButton.Cancel: return
                if answer==QMessageBox.StandardButton.Yes: shutil.copy2(self.store.path,target)
            store=Store(self.app_root,folder); lock=self.acquire_database(store)
            config={'database_dir':str(Path(folder).resolve())}
            temp=self.config_path.with_suffix('.tmp'); temp.write_text(json.dumps(config,indent=2)); temp.replace(self.config_path)
            self.db_lock.unlock(); self.db_lock=lock; self.store=store; self.reset(); self.refresh_path()
        except Exception as exc: self.error(exc)

    def activate(self):
        from PyQt6.QtWidgets import QInputDialog
        key,ok=QInputDialog.getMultiLineText(self,'Activate Smart Billing Manager','Paste activation key (validity starts immediately):')
        if ok:
            try: self.license.activate(key.strip()); self.license_tick(); QMessageBox.information(self,'Activated','Activation successful.')
            except Exception as exc: self.error(exc)

    def license_tick(self):
        import time
        if time.time()-getattr(self,'last_license_check',0)>60:
            self.license.checkpoint(); self.last_license_check=time.time()
        left=self.license.remaining()
        days=int(left//86400); hours=int(left%86400//3600); minutes=int(left%3600//60); seconds=int(left%60)
        self.license_label.setText(f'{days} days {hours:02}:{minutes:02}:{seconds:02} left' if left else 'EXPIRED - activation required')
        # Freeze billing while retaining the current form and access to activation.
        for widget in self.centralWidget().findChildren(QWidget):
            if isinstance(widget,(QLineEdit,QDateEdit,QTableWidget,QCheckBox)):
                widget.setEnabled(left>0)
            if isinstance(widget,QPushButton) and widget.text() not in ('Activate','Database Folder'):
                widget.setEnabled(left>0)

    def button(self,layout,label,callback,danger=False):
        button=QPushButton(label)
        if danger: button.setObjectName('danger')
        button.clicked.connect(callback); layout.addWidget(button); return button

    def changed(self,*args):
        if not self.loading: self.dirty=True

    def confirm_discard(self):
        return not self.dirty or QMessageBox.question(self,'Unsaved changes','Discard unsaved changes?',QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)==QMessageBox.StandardButton.Discard

    def reset(self):
        self.loading=True; self.number=None; self.invoice_seller=None
        for field in self.customer.values(): field.clear()
        self.date.setDate(QDate.currentDate()); self.table.setRowCount(0); self.rounded.setChecked(False)
        self.number_label.setText(f"New invoice • next number INV-{self.store.read()['next_number']:06d} (assigned on save)")
        self.add_row(); self.loading=False; self.recalculate(); self.dirty=False

    def new(self):
        if self.confirm_discard(): self.reset()

    def add_row(self,*args, item=None):
        self.table.blockSignals(True)
        row=self.table.rowCount(); self.table.insertRow(row)
        values=[item.get(k,'') for k in ('name','quantity','rate','gst')] if item else ['','1','0','0']
        for col,value in enumerate(values+['0.00']*3):
            cell=QTableWidgetItem(str(value))
            if col>=4: cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col: cell.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row,col,cell)
        self.table.blockSignals(False); self.recalculate()

    def remove_rows(self):
        for row in sorted({x.row() for x in self.table.selectedIndexes()},reverse=True): self.table.removeRow(row)
        self.recalculate()

    def raw_items(self):
        result=[]
        for row in range(self.table.rowCount()):
            values=[self.table.item(row,c).text().strip() for c in range(4)]
            if not values[0] and values[1:]==['1','0','0']: continue
            result.append(dict(zip(('name','quantity','rate','gst'),values)))
        return result

    def recalculate(self,*args):
        self.changed(); self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            try:
                data=dict(zip(('name','quantity','rate','gst'),[self.table.item(row,c).text() for c in range(4)]))
                data['name']=data['name'] or 'Item'
                line=calculate([data])['items'][0]
                for col,key in [(4,'amount'),(5,'tax'),(6,'total')]: self.table.item(row,col).setText(line[key])
            except ValueError:
                for col in (4,5,6): self.table.item(row,col).setText('Invalid')
        self.table.blockSignals(False)
        try:
            data=calculate(self.raw_items(),self.rounded.isChecked())
            self.totals.setText(f"Subtotal: {data['subtotal']}    |    GST: {data['total_gst']}    |    Round off: {data['round_off']}    |    Total INR {data['grand_total']}")
        except ValueError as exc: self.totals.setText(str(exc))

    def collect(self):
        if self.license.remaining()<=0: raise ValueError('License expired. Enter an activation key to continue.')
        customer={k:f.text().strip() for k,f in self.customer.items()}
        if not customer['name'] or not customer['address']: raise ValueError('Customer name and address are required.')
        seller=self.invoice_seller or self.store.read()['seller']
        if not seller.get('trade_name') or not seller.get('address'): raise ValueError('Enter the seller trade name and address in Seller Details first.')
        return dict(number=self.number,date=self.date.date().toString('yyyy-MM-dd'),customer=customer,seller=seller,rounded=self.rounded.isChecked(),**calculate(self.raw_items(),self.rounded.isChecked()))

    def error(self,exc): QMessageBox.warning(self,'Unable to complete',str(exc))

    def save(self):
        try:
            invoice=self.store.save(self.collect()); self.number=invoice['number']; self.invoice_seller=invoice['seller']; self.number_label.setText(self.number); self.dirty=False
            self.statusBar().showMessage(self.number+' saved successfully'); return invoice
        except Exception as exc: self.error(exc)

    def seller_dialog(self):
        dialog=QDialog(self); dialog.setWindowTitle('Seller / Business Details'); dialog.resize(550,620); form=QFormLayout(dialog)
        seller=self.store.read()['seller']; fields={}
        for key,label in [('trade_name','Trade Name *'),('address','Address *'),('mobile','Phone'),('email','Email'),('gst','GSTIN'),('bank','Bank / Account / IFSC'),('declaration','Declaration')]:
            field=QTextEdit() if key in ('address','bank','declaration') else QLineEdit()
            if isinstance(field,QTextEdit): field.setFixedHeight(65); field.setPlainText(seller.get(key,''))
            else: field.setText(seller.get(key,''))
            fields[key]=field; form.addRow(label,field)
        logo=QLineEdit(seller.get('logo','')); form.addRow('Logo file',logo)
        def browse():
            path,_=QFileDialog.getOpenFileName(dialog,'Select Logo','','Images (*.png *.jpg *.jpeg)')
            if path: logo.setText(path)
        self.button(form,'Browse Logo',browse)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel); form.addRow(buttons); buttons.rejected.connect(dialog.reject)
        def accept():
            try:
                data={k:(f.toPlainText() if isinstance(f,QTextEdit) else f.text()).strip() for k,f in fields.items()}
                if not data['trade_name'] or not data['address']: raise ValueError('Trade name and address are required.')
                path=logo.text().strip()
                if path:
                    image=QImage(path)
                    if image.isNull(): raise ValueError('Select a readable PNG or JPEG logo.')
                    import hashlib
                    target=self.store.root/'database'/('logo_'+hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]+Path(path).suffix.lower())
                    if Path(path).resolve()!=target.resolve(): shutil.copy2(path,target)
                    path=str(target)
                import base64
                data['logo']=path
                if path: data['logo_data']=base64.b64encode(Path(path).read_bytes()).decode('ascii')
                self.store.seller(data)
                self.invoice_seller=data; self.changed(); dialog.accept()
            except Exception as exc: self.error(exc)
        buttons.accepted.connect(accept); dialog.exec()

    def search(self):
        if not self.confirm_discard(): return
        dialog=QDialog(self); dialog.setWindowTitle('Search Saved Invoices'); dialog.resize(850,450); layout=QVBoxLayout(dialog)
        query=QLineEdit(); query.setPlaceholderText('Search number, customer, mobile or date...'); layout.addWidget(query)
        table=QTableWidget(0,4); table.setHorizontalHeaderLabels(['Invoice','Date','Customer','Total INR']); table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); layout.addWidget(table)
        invoices=self.store.read()['invoices']; found=[]
        def refresh():
            found[:]=[x for x in reversed(invoices) if query.text().lower() in (' '.join([x['number'],x['date'],*x['customer'].values()])).lower()]
            table.setRowCount(len(found))
            for row,x in enumerate(found):
                for col,value in enumerate([x['number'],x['date'],x['customer']['name'],x['grand_total']]): table.setItem(row,col,QTableWidgetItem(value))
        def open_selected():
            if table.currentRow()<0: return
            self.load(found[table.currentRow()]); dialog.accept()
        query.textChanged.connect(refresh); table.cellDoubleClicked.connect(lambda *_:open_selected()); self.button(layout,'Open Selected',open_selected); refresh(); dialog.exec()

    def load(self,invoice):
        self.loading=True; self.number=invoice['number']; self.invoice_seller=invoice['seller']; self.number_label.setText(self.number)
        self.date.setDate(QDate.fromString(invoice['date'],'yyyy-MM-dd'))
        for k,f in self.customer.items(): f.setText(invoice['customer'].get(k,''))
        self.table.setRowCount(0)
        for item in invoice['items']: self.add_row(item=item)
        self.rounded.setChecked(invoice.get('rounded',False)); self.recalculate(); self.loading=False; self.dirty=False

    def delete(self):
        if not self.number: self.error('Open a saved invoice to delete it.'); return
        if QMessageBox.question(self,'Delete Invoice','Permanently delete '+self.number+' from the database? Exported PDFs are retained.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            try: self.store.delete(self.number); self.dirty=False; self.reset()
            except Exception as exc: self.error(exc)

    def export(self):
        invoice=self.save()
        if not invoice: return
        path,_=QFileDialog.getSaveFileName(self,'Export Invoice',str(self.store.root/'invoices_pdf'/(self.number+'.pdf')),'PDF (*.pdf)')
        if path:
            try:
                if not path.lower().endswith('.pdf'): path+='.pdf'
                generate(invoice,path); self.statusBar().showMessage('PDF exported: '+path)
            except Exception as exc: self.error(exc)

    def pdf_document(self,path,parent):
        doc=QPdfDocument(parent)
        if doc.load(str(path)) != QPdfDocument.Error.None_: raise ValueError('Unable to load generated PDF.')
        return doc

    def preview(self):
        try:
            invoice=self.collect()
            with tempfile.TemporaryDirectory(prefix='smart_billing_') as temp:
                path=generate(invoice,Path(temp)/'preview.pdf')
                dialog=QDialog(self); dialog.setWindowTitle('Invoice Preview'+(' • unsaved draft' if self.dirty else '')); dialog.resize(850,850); layout=QVBoxLayout(dialog)
                doc=self.pdf_document(path,dialog); view=QPdfView(dialog); view.setDocument(doc); view.setPageMode(QPdfView.PageMode.MultiPage); view.setZoomMode(QPdfView.ZoomMode.FitToWidth); layout.addWidget(view); dialog.exec(); doc.close()
        except Exception as exc: self.error(exc)

    def print_invoice(self):
        invoice=self.save()
        if not invoice: return
        try:
            with tempfile.TemporaryDirectory(prefix='smart_billing_') as temp:
                path=generate(invoice,Path(temp)/'print.pdf'); doc=self.pdf_document(path,self)
                printer=QPrinter(QPrinter.PrinterMode.HighResolution); printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4)); printer.setPageMargins(QMarginsF(0,0,0,0)); printer.setDocName(self.number)
                if QPrintDialog(printer,self).exec()==QDialog.DialogCode.Accepted:
                    self.render_print(doc,printer)
                doc.close(); doc.deleteLater()
        except Exception as exc: self.error(exc)

    @staticmethod
    def render_print(doc,printer):
        from PyQt6.QtCore import QSize, QRectF
        painter=QPainter()
        if not painter.begin(printer): raise ValueError('Printer could not be started.')
        try:
            start=max(0,printer.fromPage()-1); end=min(doc.pageCount(),printer.toPage() or doc.pageCount())
            for page in range(start,end):
                if page>start and not printer.newPage(): raise ValueError('Printer failed to create a page.')
                rect=printer.pageLayout().paintRectPixels(printer.resolution())
                size=doc.pagePointSize(page); size.scale(float(rect.width()),float(rect.height()),Qt.AspectRatioMode.KeepAspectRatio)
                # Render at 200 DPI to preserve text without excessive memory use.
                pts=doc.pagePointSize(page); image=doc.render(page,QSize(round(pts.width()*200/72),round(pts.height()*200/72)))
                target=QRectF(rect.x()+(rect.width()-size.width())/2,rect.y()+(rect.height()-size.height())/2,size.width(),size.height())
                painter.drawImage(target,image)
        finally: painter.end()

    def closeEvent(self,event):
        if self.confirm_discard():
            self.db_lock.unlock(); self.timer.stop(); event.accept()
        else: event.ignore()
