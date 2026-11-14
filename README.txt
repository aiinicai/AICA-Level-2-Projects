DUNE COUNT - Physical stock count app

1) Install libraries (optional - run.py also installs them automatically). Paste into cmd:
   pip install flask openpyxl

2) Start:   python run.py
   Count Admin   -> http://localhost:5000/admin/
   Count Persons -> http://localhost:5000/counter/

Flow
 - First person to sign up on the Admin portal becomes Admin.
 - Admin adds employees (name + email). Employees sign up once with that email, then sign in.
 - Admin: Counts & Completion -> choose location (SHW1/SHW2/SHW3/WHS4) -> upload book Excel
   (Row 1 header, column "Barcode", optional "Description", one row per unit). Template is downloadable there.
 - Counters: pick location, type last 4 digits, choose barcode from dropdown, enter sticker number, Record unit.
 - Counter presses Confirm completion -> Admin confirms completion -> enters stickers used.
   Must equal units counted or submission is blocked. Then the variance report (0 / -1 / +1) is generated.
 - Exports: Count table CSV, Results CSV, Audit CSV, Excel (barcode, sticker no, book qty, counted, difference).
Data is stored in dune_count.db (SQLite) in this folder.
