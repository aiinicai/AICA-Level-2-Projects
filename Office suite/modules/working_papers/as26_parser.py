import re
import io
import csv
import logging
import pdfplumber

logger = logging.getLogger("AS26Parser")

def parse_num(val) -> float:
    if not val: return 0.0
    s = str(val).replace('"', '').replace(' ', '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

def parse_26as_csv(csv_bytes: bytes) -> list:
    """
    Parses TRACES Form 26AS CSV export files to extract ONLY Section 194A (Interest income u/s 194A) entries:
    - Deductor Name (Bank Name)
    - TAN of Deductor
    - Total Amount Paid / Credited (Gross Interest Income u/s 194A)
    - Total Tax Deducted (TDS Amount u/s 194A)
    Excludes non-194A entries such as 194Q, 194C, 194H, 194I, 194O, etc.
    """
    try:
        text = csv_bytes.decode("utf-8-sig", errors="ignore")
    except Exception:
        text = csv_bytes.decode("latin1", errors="ignore")

    lines = text.splitlines()
    entries = []

    current_deductor = None
    current_tan = None
    header_amt = 0.0
    header_tds = 0.0
    tx_194a_list = []
    has_194a = False

    def finalize_deductor_block():
        nonlocal current_deductor, current_tan, header_amt, header_tds, tx_194a_list, has_194a
        if current_deductor and current_tan and has_194a:
            if tx_194a_list:
                net_amt = sum(t[0] for t in tx_194a_list)
                net_tds = sum(t[1] for t in tx_194a_list)
            else:
                net_amt = header_amt
                net_tds = header_tds

            entries.append({
                "deductor_name": current_deductor.strip(),
                "tan": current_tan.strip(),
                "section": "194A",
                "amount_paid": round(net_amt, 2),
                "tds_deducted": round(net_tds, 2)
            })

        current_deductor = None
        current_tan = None
        header_amt = 0.0
        header_tds = 0.0
        tx_194a_list = []
        has_194a = False

    # Read line-by-line using csv reader for robust field handling
    csv_reader = csv.reader(lines)
    
    in_part1 = False

    for row in csv_reader:
        if not row or not any(row):
            continue

        row_str = " ".join(row).upper()

        if "PART-I" in row_str or "DETAILS OF TAX DEDUCTED AT SOURCE" in row_str:
            in_part1 = True
            continue
        
        if in_part1 and ("PART-II" in row_str or "PART-III" in row_str or "PART-IV" in row_str or "PART-VIII" in row_str):
            finalize_deductor_block()
            in_part1 = False
            break

        if not in_part1:
            continue

        # Check for Deductor Summary Header Row e.g.:
        # ["1", "NATIONAL DAIRY DEVELOPMENT BOARD", "BRDN00717D", "", "", "", "", "3122950", " 2,95,343 ", "295343"]
        first_col = row[0].strip() if len(row) > 0 else ""
        sec_col = row[1].strip() if len(row) > 1 else ""

        # Case A: Deductor Summary Header Row
        if first_col.isdigit() and len(row) >= 3 and re.match(r"^[A-Z]{4}\d{5}[A-Z]$", row[2].strip()):
            finalize_deductor_block()
            current_deductor = row[1].strip()
            current_tan = row[2].strip()
            # Extract header totals if present
            header_amt = parse_num(row[7]) if len(row) > 7 else 0.0
            header_tds = parse_num(row[8]) if len(row) > 8 else 0.0
            continue

        # Case B: Transaction Detail Row e.g.:
        # ["", "1", "194A", "31-Mar-26", "F", "04-Jun-26", "-", "1215250", "121525", "121525"]
        if current_deductor and len(row) >= 9:
            sec_val = ""
            amt_val = 0.0
            tds_val = 0.0

            # Find Section (e.g. 194A, 194C, 194Q)
            for c in row:
                c_clean = c.strip().upper()
                if c_clean.startswith("194"):
                    sec_val = c_clean
                    break

            if sec_val == "194A":
                has_194a = True
                amt_val = parse_num(row[7]) if len(row) > 7 else 0.0
                tds_val = parse_num(row[8]) if len(row) > 8 else 0.0
                tx_194a_list.append((amt_val, tds_val))

    finalize_deductor_block()
    return entries


def parse_26as_pdf(pdf_bytes: bytes) -> list:
    """
    Parses TRACES Form 26AS PDF files to extract ONLY Section 194A (Interest income u/s 194A) entries.
    """
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    except Exception as e:
        logger.warning(f"pdfplumber exception reading 26AS PDF: {e}")

    if not text.strip():
        try:
            text = pdf_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    entries = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    header_regex = re.compile(
        r"^(?:Sr\.\s*No\.\s*)?(\d+)\s+([A-Za-z0-9\s\.\&\,\-\(\)\/\']+?)\s+([A-Z]{4}\d{5}[A-Z])\s+([\d\.\,\-]+)\s+([\d\.\,\-]+)\s+([\d\.\,\-]+)$",
        re.IGNORECASE
    )

    tx_regex = re.compile(
        r"^\d+\s+(194[A-Z0-9\(struct\)]+)\s+([0-9]{1,2}\-[A-Za-z]{3}\-[0-9]{4}).*?([\d\.\,\-]+)\s+([\d\.\,\-]+)\s+([\d\.\,\-]+)$",
        re.IGNORECASE
    )

    current_deductor = None
    current_tan = None
    header_amt = 0.0
    header_tds = 0.0
    tx_194a_list = []
    has_194a = False

    def finalize_deductor_block():
        nonlocal current_deductor, current_tan, header_amt, header_tds, tx_194a_list, has_194a
        if current_deductor and current_tan and has_194a:
            if tx_194a_list:
                net_amt = sum(t[0] for t in tx_194a_list)
                net_tds = sum(t[1] for t in tx_194a_list)
            else:
                net_amt = header_amt
                net_tds = header_tds

            entries.append({
                "deductor_name": current_deductor.strip(),
                "tan": current_tan.strip(),
                "section": "194A",
                "amount_paid": round(net_amt, 2),
                "tds_deducted": round(net_tds, 2)
            })

        current_deductor = None
        current_tan = None
        header_amt = 0.0
        header_tds = 0.0
        tx_194a_list = []
        has_194a = False

    for idx, line in enumerate(lines):
        if "PART-II" in line.upper() or "PART II" in line.upper() or "PART-III" in line.upper():
            finalize_deductor_block()
            break

        hm = header_regex.match(line)
        if hm:
            finalize_deductor_block()

            c_name = hm.group(2).strip()
            c_tan = hm.group(3).strip()
            try:
                c_amt = float(hm.group(4).replace(",", ""))
                c_tds = float(hm.group(5).replace(",", ""))
            except ValueError:
                c_amt, c_tds = 0.0, 0.0

            if "NAME OF DEDUCTOR" not in c_name.upper():
                current_deductor = c_name
                current_tan = c_tan
                header_amt = c_amt
                header_tds = c_tds
            continue

        if "TAN of Deductor" in line or "Total Amount Paid" in line:
            continue

        tm = tx_regex.match(line)
        if tm and current_deductor:
            sec_code = tm.group(1).upper()
            if sec_code == "194A":
                has_194a = True
                try:
                    amt_val = float(tm.group(3).replace(",", ""))
                    tds_val = float(tm.group(4).replace(",", ""))
                    tx_194a_list.append((amt_val, tds_val))
                except ValueError:
                    pass

    finalize_deductor_block()

    if not entries:
        ded_blocks = re.split(r"(?:Sr\.\s*No\.|\n)\s*(\d+)\s+([A-Z0-9\s\.\&\,\-\/]+?)\s+([A-Z]{4}\d{5}[A-Z])\s+([\d\.\,]+)\s+([\d\.\,]+)", text)
        i = 1
        while i < len(ded_blocks) - 4:
            d_name = ded_blocks[i+1].strip()
            d_tan = ded_blocks[i+2].strip()
            d_amt_str = ded_blocks[i+3].strip()
            d_tds_str = ded_blocks[i+4].strip()
            block_content = ded_blocks[i+5] if i+5 < len(ded_blocks) else ""

            if "194A" in block_content or "194A" in d_name:
                try:
                    d_amt = float(d_amt_str.replace(",", ""))
                    d_tds = float(d_tds_str.replace(",", ""))
                    
                    tx_matches = re.findall(r"194A\s+[0-9]{1,2}\-[A-Za-z]{3}\-[0-9]{4}.*?([\d\.\,\-]+)\s+([\d\.\,\-]+)", block_content)
                    if tx_matches:
                        net_amt = sum(float(m[0].replace(",", "")) for m in tx_matches)
                        net_tds = sum(float(m[1].replace(",", "")) for m in tx_matches)
                    else:
                        net_amt = d_amt
                        net_tds = d_tds

                    entries.append({
                        "deductor_name": d_name,
                        "tan": d_tan,
                        "section": "194A",
                        "amount_paid": round(net_amt, 2),
                        "tds_deducted": round(net_tds, 2)
                    })
                except Exception:
                    pass
            i += 6

    return entries


def parse_26as_content(file_bytes: bytes, filename: str = "") -> list:
    """
    Parses Form 26AS content from either PDF or CSV files.
    """
    fn_lower = filename.lower() if filename else ""
    if fn_lower.endswith(".csv") or b"Annual Tax Statement" in file_bytes[:500] or b"PART-I" in file_bytes[:1000]:
        return parse_26as_csv(file_bytes)
    else:
        return parse_26as_pdf(file_bytes)
