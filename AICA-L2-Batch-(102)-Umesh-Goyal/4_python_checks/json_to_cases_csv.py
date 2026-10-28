r"""Take the JSON made in Google AI Studio (2_ai_studio) and add the due dates to cases.csv.

cases.csv has the columns client, matter, last_date, status, and is the file the n8n reminder reads.
Two rows are added: the reply due date and, if the notice prints it, the personal hearing date.

Run:  py json_to_cases_csv.py scn_output.json cases.csv

The reply date is the date printed in the notice (field reply_period_stated). If no date is printed,
SCN date + 30 days is used and the script says so; check that against the notice. Rows that are
already in the file are not added twice. Read the rows before you rely on them.
"""
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta

DATE = re.compile(r"(\d{1,2})[-./](\d{1,2})[-./](\d{4})")


def find_date(text):
    m = DATE.search(str(text or ""))
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    try:
        return datetime(y, mth, d).date()
    except ValueError:
        return None


def load_json(path):
    raw = open(path, encoding="utf-8").read()
    start, end = raw.find("{"), raw.rfind("}")      # AI Studio may wrap the JSON in ``` fences
    if start < 0 or end < start:
        sys.exit("No JSON object found in " + path)
    return json.loads(raw[start:end + 1])


def main():
    if len(sys.argv) < 3:
        sys.exit("Usage: py json_to_cases_csv.py scn_output.json cases.csv")
    data = load_json(sys.argv[1])
    out = sys.argv[2]

    client = data.get("noticee_name")
    number = data.get("scn_number")
    scn_date = find_date(data.get("scn_date"))
    if not (client and number and scn_date):
        sys.exit("noticee_name, scn_number and scn_date must all be present in the JSON.")

    rows = []
    reply = find_date(data.get("reply_period_stated"))
    if reply:
        note = "date printed in the notice"
    else:
        reply = scn_date + timedelta(days=30)
        note = "NOT printed - SCN date + 30 days assumed, check against the notice"
    rows.append([client, "SCN %s - reply due" % number, reply.isoformat(), "open"])
    print("Reply due: %s (%s)" % (reply.strftime("%d-%m-%Y"), note))

    hearing = find_date(data.get("personal_hearing_date"))
    if hearing:
        rows.append([client, "SCN %s - personal hearing" % number, hearing.isoformat(), "open"])
        print("Hearing  : %s" % hearing.strftime("%d-%m-%Y"))

    existing = []
    if os.path.exists(out):
        with open(out, newline="", encoding="utf-8-sig") as f:
            existing = [(r.get("client"), r.get("matter")) for r in csv.DictReader(f)]
    new_file = not os.path.exists(out)
    with open(out, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["client", "matter", "last_date", "status"])
        for r in rows:
            if (r[0], r[1]) in existing:
                print("Already in file, skipped:", r[1])
            else:
                w.writerow(r)
                print("Added:", r)


if __name__ == "__main__":
    main()
