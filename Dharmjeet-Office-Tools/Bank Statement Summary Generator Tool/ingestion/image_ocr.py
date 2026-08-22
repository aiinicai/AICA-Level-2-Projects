"""Advanced Image Preprocessing and OCR Pipeline for Scanned Statements and Photos.
Powered by RapidOCR (ONNX Runtime) with OpenCV preprocessing and Tesseract fallback.
"""

import os
import io
import re
import numpy as np
import pandas as pd
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from rapidocr_onnxruntime import RapidOCR
    rapid_engine = RapidOCR()
except Exception as e:
    rapid_engine = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

from normalization.schema_mapper import (
    normalize_dataframe, load_bank_templates, detect_bank_from_header_text, extract_account_number
)

def preprocess_image_advanced(image_input: any) -> Optional[np.ndarray]:
    """
    Apply OpenCV preprocessing: CLAHE contrast adjustment, Grayscale conversion,
    and adaptive thresholding for optimal OCR on camera images and scans.
    """
    if cv2 is None:
        return None
        
    try:
        if isinstance(image_input, (bytes, bytearray)):
            nparr = np.frombuffer(image_input, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image_input, str):
            img = cv2.imread(image_input)
        elif isinstance(image_input, Image.Image):
            img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            return None

        if img is None:
            return None

        # Convert to Grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Resize if image is too small (e.g. height < 800px) for better OCR accuracy
        h, w = gray.shape[:2]
        if w < 1200:
            scale = 1600.0 / max(w, 1)
            if scale > 1.0 and scale < 3.0:
                gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        return enhanced
    except Exception as e:
        print(f"Error in OCR image preprocessing: {e}")
        return None

def cluster_rapidocr_boxes_into_rows(ocr_results: list, y_tolerance_ratio: float = 0.5) -> List[List[Dict[str, Any]]]:
    """
    Group RapidOCR word bounding boxes into tabular rows based on Y-center coordinates.
    ocr_results format: [ [box_coords, text, confidence], ... ]
    """
    if not ocr_results:
        return []

    items = []
    avg_height = 15.0
    heights = []

    for item in ocr_results:
        box = item[0]
        text = str(item[1]).strip()
        conf = float(item[2]) if len(item) > 2 else 1.0
        
        if not text:
            continue

        # Box is 4 points: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        y_center = sum(ys) / len(ys)
        x_min = min(xs)
        height = max(ys) - min(ys)
        if height > 5:
            heights.append(height)

        items.append({
            "text": text,
            "y_center": y_center,
            "x_min": x_min,
            "height": height,
            "conf": conf
        })

    if heights:
        avg_height = sum(heights) / len(heights)

    y_tolerance = max(avg_height * y_tolerance_ratio, 10.0)

    # Sort items top-to-bottom
    items.sort(key=lambda x: x["y_center"])

    rows = []
    current_row = []
    current_y = None

    for item in items:
        if current_y is None:
            current_y = item["y_center"]
            current_row.append(item)
        elif abs(item["y_center"] - current_y) <= y_tolerance:
            current_row.append(item)
            # Update running average Y for the row
            current_y = sum(w["y_center"] for w in current_row) / len(current_row)
        else:
            # Sort previous row left-to-right
            current_row.sort(key=lambda w: w["x_min"])
            rows.append(current_row)
            current_y = item["y_center"]
            current_row = [item]

    if current_row:
        current_row.sort(key=lambda w: w["x_min"])
        rows.append(current_row)

    return rows

def parse_row_items_to_transactions(rows: List[List[Dict[str, Any]]]) -> pd.DataFrame:
    """
    Convert clustered OCR row elements into standardized transaction records.
    """
    date_regex = re.compile(r'(\b\d{1,2}[\/\-\.](?:\d{1,2}|[A-Za-z]{3})[\/\-\.]\d{2,4}\b)')
    amount_clean_regex = re.compile(r'^[₹Rs\.\s]*(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)[A-Za-z\s]*$')

    parsed_records = []
    current_txn = None

    for row in rows:
        row_texts = [w["text"].strip() for w in row if w["text"].strip()]
        full_line = " ".join(row_texts)
        if not full_line:
            continue

        # Look for date in the row
        date_matches = list(date_regex.finditer(full_line))

        if date_matches:
            # Found a new transaction row starting with a date
            first_match = date_matches[0]
            txn_date_str = first_match.group(1)

            # Analyze remaining tokens in this row
            tokens_after_date = full_line[first_match.end():].strip()
            
            # Find numbers with decimals or commas (candidate amounts)
            candidate_amounts = []
            words_in_row = row_texts
            
            for w_idx, w in enumerate(words_in_row):
                w_clean = re.sub(r'[₹$,]', '', w).strip()
                # Check if word is an amount
                if re.match(r'^\d+\.\d{2}$', w_clean) or (w_clean.isdigit() and len(w_clean) >= 3 and not re.match(r'^\d{6,16}$', w_clean)):
                    try:
                        val = float(w_clean)
                        candidate_amounts.append((w_idx, val, w))
                    except ValueError:
                        pass

            # Extract narration, debit, credit, balance
            debit = 0.0
            credit = 0.0
            balance = 0.0

            narration_words = []
            for w_idx, w in enumerate(words_in_row):
                # Ignore date token
                if date_regex.search(w):
                    continue
                # If word is in candidate amounts, determine position
                is_amt = any(w_idx == ca[0] for ca in candidate_amounts)
                if not is_amt:
                    narration_words.append(w)

            narration = " ".join(narration_words).strip()

            # Assign amounts based on indicators or column counts
            line_upper = full_line.upper()
            amt_values = [ca[1] for ca in candidate_amounts]

            if len(amt_values) == 1:
                amt = amt_values[0]
                if any(k in line_upper for k in ["DR", "WDL", "DEBIT", "PAID", "TO "]):
                    debit = amt
                else:
                    credit = amt
            elif len(amt_values) == 2:
                amt = amt_values[0]
                balance = amt_values[1]
                if any(k in line_upper for k in ["DR", "WDL", "DEBIT", "PAID", "TO "]):
                    debit = amt
                else:
                    credit = amt
            elif len(amt_values) >= 3:
                debit = amt_values[0]
                credit = amt_values[1]
                balance = amt_values[2]

            current_txn = {
                "Date": txn_date_str,
                "Narration": narration,
                "Debit": debit,
                "Credit": credit,
                "Balance": balance
            }
            parsed_records.append(current_txn)

        elif current_txn and len(parsed_records) > 0:
            # Continuation / multiline narration of previous transaction
            if not any(k in full_line.upper() for k in ["PAGE", "STATEMENT", "ACCOUNT NUMBER", "OPENING BALANCE", "TOTAL"]):
                parsed_records[-1]["Narration"] += " " + full_line

    return pd.DataFrame(parsed_records)

def read_image_statement(
    image_input: any,
    filename: str = ""
) -> pd.DataFrame:
    """
    Run OCR on image statement (JPEG, PNG, scanned photos) and return normalized DataFrame.
    """
    templates = load_bank_templates()
    fname = filename or "scanned_statement.png"

    # Preprocess image
    preprocessed = preprocess_image_advanced(image_input)
    
    # 1. Primary Engine: RapidOCR
    if rapid_engine is not None and preprocessed is not None:
        try:
            results, _ = rapid_engine(preprocessed)
            if results:
                # Extract header metadata
                full_text = " ".join([r[1] for r in results])
                bank_name, bank_tmpl = detect_bank_from_header_text(full_text, templates)
                acc_no = extract_account_number(full_text)

                rows = cluster_rapidocr_boxes_into_rows(results)
                df_parsed = parse_row_items_to_transactions(rows)

                if not df_parsed.empty:
                    return normalize_dataframe(
                        df_parsed,
                        source_file=fname,
                        source_bank=bank_name,
                        account_number=acc_no,
                        bank_template=bank_tmpl
                    )
        except Exception as e:
            print(f"RapidOCR parsing failed on {fname}: {e}")

    # 2. Secondary Engine: Pytesseract Fallback (if installed)
    if pytesseract is not None:
        try:
            pil_img = Image.fromarray(preprocessed) if preprocessed is not None else Image.open(
                io.BytesIO(image_input) if isinstance(image_input, (bytes, bytearray)) else image_input
            )
            full_text = pytesseract.image_to_string(pil_img)
            bank_name, bank_tmpl = detect_bank_from_header_text(full_text, templates)
            acc_no = extract_account_number(full_text)
            
            lines = [line.strip() for line in full_text.splitlines() if line.strip()]
            from ingestion.image_ocr import parse_ocr_lines_to_transactions
            df_parsed = parse_ocr_lines_to_transactions(lines)
            if not df_parsed.empty:
                return normalize_dataframe(
                    df_parsed,
                    source_file=fname,
                    source_bank=bank_name,
                    account_number=acc_no,
                    bank_template=bank_tmpl
                )
        except Exception as e:
            print(f"Pytesseract fallback failed on {fname}: {e}")

    return pd.DataFrame()

def parse_ocr_lines_to_transactions(raw_lines: List[str]) -> pd.DataFrame:
    """Fallback line-based transaction parser."""
    date_regex = re.compile(r'(\b\d{1,2}[\/\-\.](?:\d{1,2}|[A-Za-z]{3})[\/\-\.]\d{2,4}\b)')
    amount_regex = re.compile(r'(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})?)')

    rows = []
    for line in raw_lines:
        line_str = " ".join(line) if isinstance(line, list) else str(line)
        line_str = line_str.strip()
        if not line_str:
            continue

        d_match = date_regex.search(line_str)
        if not d_match:
            continue

        txn_date = d_match.group(1)
        amounts = amount_regex.findall(line_str[d_match.end():])
        valid_amounts = [float(a.replace(',', '')) for a in amounts if '.' in a or len(a) >= 3]

        narration = line_str[d_match.end():]
        if amounts:
            first_amt_pos = narration.find(amounts[0])
            if first_amt_pos != -1:
                narration = narration[:first_amt_pos].strip()

        debit = 0.0
        credit = 0.0
        balance = 0.0

        if len(valid_amounts) == 1:
            if "DR" in line_str.upper() or "WDL" in line_str.upper() or "DEBIT" in line_str.upper():
                debit = valid_amounts[0]
            else:
                credit = valid_amounts[0]
        elif len(valid_amounts) == 2:
            if "DR" in line_str.upper() or "WDL" in line_str.upper():
                debit = valid_amounts[0]
            else:
                credit = valid_amounts[0]
            balance = valid_amounts[1]
        elif len(valid_amounts) >= 3:
            debit = valid_amounts[0]
            credit = valid_amounts[1]
            balance = valid_amounts[2]

        rows.append({
            "Date": txn_date,
            "Narration": narration,
            "Debit": debit,
            "Credit": credit,
            "Balance": balance
        })

    return pd.DataFrame(rows)
