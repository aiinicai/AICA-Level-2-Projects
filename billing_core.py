"""Money calculations and crash-safe local JSON storage."""
import copy
import json
import os
import shutil
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

def money(value):
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calculate(items, rounded=False):
    lines, taxes = [], {}
    for item in items:
        name = str(item['name']).strip()
        try:
            qty, rate, gst = (Decimal(str(item[k])) for k in ('quantity', 'rate', 'gst'))
        except (InvalidOperation, KeyError):
            raise ValueError('Enter valid numbers for quantity, rate and GST.')
        if not all(x.is_finite() for x in (qty, rate, gst)) or qty <= 0 or rate < 0 or not 0 <= gst <= 100:
            raise ValueError('Quantity must be positive, rate non-negative, and GST between 0 and 100.')
        if not name or len(name) > 500:
            raise ValueError('Each item needs a name (maximum 500 characters).')
        amount = money(qty * rate)
        tax = money(amount * gst / 100)
        lines.append(dict(name=name, quantity=str(qty), rate=str(rate), gst=str(gst), amount=str(amount), tax=str(tax), total=str(amount+tax)))
        key = str(gst.normalize())
        group = taxes.setdefault(key, {'taxable': Decimal(0), 'tax': Decimal(0)})
        group['taxable'] += amount
        group['tax'] += tax
    if not lines:
        raise ValueError('Add at least one item.')
    subtotal = sum((Decimal(x['amount']) for x in lines), Decimal(0))
    tax = sum((Decimal(x['tax']) for x in lines), Decimal(0))
    raw = subtotal + tax
    total = raw.quantize(Decimal('1'), rounding=ROUND_HALF_UP) if rounded else raw
    return dict(items=lines, subtotal=str(money(subtotal)), total_gst=str(money(tax)), round_off=str(money(total-raw)), grand_total=str(money(total)), tax_summary={k: {n: str(money(v)) for n,v in group.items()} for k,group in taxes.items()})

class Store:
    def __init__(self, root, database_dir=None):
        self.root = Path(root)
        (self.root/'database').mkdir(parents=True, exist_ok=True)
        (self.root/'invoices_pdf').mkdir(parents=True, exist_ok=True)
        self.path = (Path(database_dir) if database_dir else self.root/'database')/'billing.json'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if not self.path.exists():
            self.write({'version': 1, 'next_number': 1, 'seller': {}, 'invoices': []})
        self.read()

    def read(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            assert data['version'] == 1 and isinstance(data['invoices'], list) and isinstance(data['seller'], dict)
            assert isinstance(data['next_number'], int) and data['next_number'] > 0
            return data
        except (ValueError, KeyError, AssertionError) as exc:
            raise ValueError('Database is damaged. Original file is preserved. Restore database/billing.json.bak after reviewing it.') from exc

    def write(self, data):
        temp = self.path.with_suffix('.tmp')
        with temp.open('w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        if self.path.exists():
            shutil.copy2(self.path, str(self.path)+'.bak')
        os.replace(temp, self.path)

    def save(self, invoice):
        data = self.read()
        record = copy.deepcopy(invoice)
        if record.get('number'):
            index = next((i for i,x in enumerate(data['invoices']) if x['number'] == record['number']), None)
            if index is None:
                raise ValueError('This invoice was deleted. Create a new invoice.')
            data['invoices'][index] = record
        else:
            record['number'] = f"INV-{data['next_number']:06d}"
            data['next_number'] += 1
            data['invoices'].append(record)
        self.write(data)
        return record

    def delete(self, number):
        data = self.read()
        data['invoices'] = [x for x in data['invoices'] if x['number'] != number]
        self.write(data)

    def seller(self, seller):
        data = self.read()
        data['seller'] = seller
        self.write(data)
