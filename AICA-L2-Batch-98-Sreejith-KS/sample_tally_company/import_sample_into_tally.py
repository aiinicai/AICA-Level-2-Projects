# -*- coding: utf-8 -*-
"""
import_sample_into_tally.py
Sends the sample company files straight into Tally Prime through its HTTP port (9000),
so nothing has to be typed in Tally's Import screen.

Before running:
  1. Open Tally Prime and LOAD the company  Sample Engineering Private Limited  (the one you created).
  2. Tally must be listening on port 9000 (F1 Help > Settings > Connectivity > Client/Server configuration).
  3. Keep this file in the same folder as 1_Masters.xml, 2_Vouchers_FY2024-25.xml and 3_Vouchers_FY2025-26.xml.

Run:   python import_sample_into_tally.py
Repair run (only if the first run reported the Closing Stock error):  python import_sample_into_tally.py --fix
Optional: python import_sample_into_tally.py http://localhost:9000
"""
import os
import re
import sys

try:
    import requests
except ImportError:
    print("The 'requests' library is missing. Run:  python -m pip install requests   and try again.")
    sys.exit(1)

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
FIX = "--fix" in sys.argv
URL = ARGS[0] if ARGS else "http://localhost:9000"
HERE = os.path.dirname(os.path.abspath(__file__))
FILES = ["1_Masters.xml", "2_Vouchers_FY2024-25.xml", "3_Vouchers_FY2025-26.xml"]
if FIX:      # repair run: update the Closing Stock ledger, then add only the two closing-stock journals
    FILES = ["1_Masters.xml", "4_Closing_Stock_Journals_ONLY.xml"]


def num(tag, text):
    m = re.search(r"<%s>\s*(\d+)\s*</%s>" % (tag, tag), text)
    return int(m.group(1)) if m else 0


def send(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        print("  File not found: %s" % path)
        return False
    with open(path, "rb") as f:
        data = f.read()
    try:
        r = requests.post(URL, data=data, headers={"Content-Type": "text/xml; charset=utf-8"}, timeout=300)
    except requests.exceptions.ConnectionError:
        print("  Could not connect to Tally at %s. Is Tally open, the company loaded, and port 9000 enabled?" % URL)
        return False
    text = r.text
    created, altered, errors = num("CREATED", text), num("ALTERED", text), num("ERRORS", text)
    print("  Created: %d | Altered: %d | Errors: %d | Ignored: %d | Combined: %d" % (
        created, altered, errors, num("IGNORED", text), num("COMBINED", text)))
    for e in re.findall(r"<LINEERROR>(.*?)</LINEERROR>", text, re.S)[:10]:
        print("  Tally says: %s" % e.strip())
    if "Unknown Request" in text or "No company" in text:
        print("  Tally did not accept the request. Check that the sample company is loaded (not another company).")
    return errors == 0


def main():
    print("Importing into Tally at %s\n" % URL)
    for name in FILES:
        print(name)
        send(name)
        print()
    print("Done. In Tally open Display More Reports > Trial Balance and compare with Expected_Trial_Balance.csv.")
    print("Masters showing 'Errors' because the ledgers already exist is fine - the ledgers you created earlier are kept.")


if __name__ == "__main__":
    main()
