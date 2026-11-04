"""
extract_and_parse_tariff_table.py

Purpose: Extracts and parses the full TABLE I preferential tariff schedule
(India-UK CETA Notification No. 29/2026-Customs) from its zip-based PDF
container into structured JSON rows, ready for bulk-loading into the n8n
`hs_rates_india_uk` data table.

Pipeline:
  1. extract_full_text()  -- reads manifest.json inside the zip-format PDF,
     concatenates the per-page OCR'd .txt files in page order.
  2. Locate the TABLE I data segment (between the header markers and TABLE II).
  3. Linear-scan token parser -- walks the flattened whitespace text token by
     token, using the expected Sl.No sequence to delimit entries. Handles:
       - multi-word / multi-line descriptions ("All goods other than Tukmaria")
       - compound ad-valorem + specific duty rates
         ("22.3% or Rs.26.9/- per kg which ever is lower")
       - multi-HS-code entries sharing one row (comma-separated HS codes)
  4. Expand multi-HS-code entries into individual per-code rows.
  5. Write out as a single JSON array, ready for CSV export / bulk insert.

Verified against a known-good manual lookup: HS 27101971 -> BCD 4.1%,
AIDC 0.0%, Health Cess 0.0% (cross-checked directly against the source PDF).

Output: table1_final_rows.json (11,116 rows), later exported to
hs_rates_india_uk.csv for import into the n8n data table.
"""

import zipfile
import json
import re


def extract_full_text(path):
    """Read a zip-format 'PDF' (image+OCR-text container) and return the
    full concatenated OCR text in page order."""
    z = zipfile.ZipFile(path)
    m = json.loads(z.read('manifest.json').decode('utf-8', errors='replace'))
    pages = sorted(m['pages'], key=lambda p: p['page_number'])
    texts = []
    for p in pages:
        txt_path = p['text']['path']
        try:
            t = z.read(txt_path).decode('utf-8', errors='replace')
        except KeyError:
            t = ''
        texts.append(t)
    return '\n\n'.join(texts), m['num_pages']


def parse_table1(text):
    """Linear-scan parser for TABLE I of Notification 29/2026-Customs.

    Handles multi-line descriptions, compound specific-duty rates, and
    multi-HS-code entries by walking the flattened token stream and using
    the expected serial-number sequence to delimit entries.
    """
    i1 = text.find('TABLE I \n')
    i2 = text.find('TABLE II \n')
    segment = text[i1:i2]
    hdr_end = segment.find('(1) (2) (3) (4) (5) (6)')
    data = segment[hdr_end + len('(1) (2) (3) (4) (5) (6)'):]
    flat = re.sub(r'\s+', ' ', data).strip()

    tokens = flat.split(' ')
    n = len(tokens)
    entries = []
    i = 0
    expected_sl = 1
    while i < n:
        tok = tokens[i]
        if tok.isdigit() and int(tok) == expected_sl:
            sl_no = tok
            j = i + 1
            hs_codes = []
            while j < n and re.match(r'^\d{2,10},?$', tokens[j]):
                hs_codes.append(tokens[j].rstrip(','))
                j += 1
                if not tokens[j - 1].endswith(','):
                    break
            desc_tokens = []
            k = j
            while k < n:
                t0 = tokens[k]
                is_pure_decimal = re.match(r'^\d+\.\d+$', t0) or re.match(r'^\d+\.\d+%$', t0)
                is_compound_start = re.match(r'^\d+(\.\d+)?%$', t0) or t0 == 'Rs.' or re.match(r'^Rs\.\d', t0)
                if is_pure_decimal or is_compound_start:
                    break
                desc_tokens.append(t0)
                k += 1

            next_sl_str = str(expected_sl + 1)
            next_start_idx = None
            for m_ in range(k, min(k + 60, n)):
                if tokens[m_] == next_sl_str and m_ + 1 < n and re.match(r'^\d{4,10}', tokens[m_ + 1]):
                    next_start_idx = m_
                    break
            if next_start_idx is None:
                next_start_idx = n
            rate_tokens = tokens[k:next_start_idx]
            if len(rate_tokens) >= 3:
                health = rate_tokens[-1]
                aidc = rate_tokens[-2]
                bcd = ' '.join(rate_tokens[:-2])
            else:
                bcd, aidc, health = (rate_tokens + ['', '', ''])[:3]

            entries.append({
                'sl_no': sl_no,
                'hs_codes': hs_codes,
                'description': ' '.join(desc_tokens).strip(),
                'bcd': bcd,
                'aidc': aidc,
                'health_cess': health,
            })
            expected_sl += 1
            i = next_start_idx
        else:
            i += 1

    return entries


def expand_rows(entries, fta_code='India-UK CETA', notification_no='29/2026-Customs'):
    """Expand multi-HS-code entries into individual per-code rows, ready
    for the hs_rates_india_uk table schema."""
    rows = []
    for e in entries:
        for hs in e['hs_codes']:
            rows.append({
                'hs_code': hs,
                'description': e['description'],
                'bcd_rate': e['bcd'],
                'aidc_rate': e['aidc'],
                'health_cess_rate': e['health_cess'],
                'fta_code': fta_code,
                'notification_no': notification_no,
            })
    return rows


if __name__ == '__main__':
    text, num_pages = extract_full_text('cst-29-2026.pdf')
    print(f'Extracted {len(text)} characters across {num_pages} pages')

    entries = parse_table1(text)
    print(f'Parsed {len(entries)} tariff-line entries')

    rows = expand_rows(entries)
    print(f'Expanded to {len(rows)} individual HS-code rate rows')

    # Sanity check against a known value
    check = [r for r in rows if r['hs_code'] == '27101971']
    print('Verification (HS 27101971):', check)

    with open('table1_final_rows.json', 'w') as f:
        json.dump(rows, f)
    print('Wrote table1_final_rows.json')
