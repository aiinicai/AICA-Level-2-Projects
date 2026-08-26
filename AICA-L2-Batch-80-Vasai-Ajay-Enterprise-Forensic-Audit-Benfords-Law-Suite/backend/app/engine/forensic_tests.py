"""
Advanced Enterprise Forensic Anomaly Suite.

Implements:
1. Relative Size Factor (RSF) analysis across vendors and ledger accounts.
2. Duplicate Invoicing & Payment Detection (Exact, Fuzzy 30-day, Transposition errors).
3. Split Transactions / Smurfing Anomaly Scanner (Statutory PAN ₹50k, Cash ₹2L, TDS ₹10L, Custom limits).
4. Round Number Anomaly Scanner (₹1k, ₹10k, ₹50k, ₹1L rounded provision detection).
5. Weekend & Indian Statutory Holiday / Fiscal Year-End Posting Detection.
6. Multi-Factor Composite Forensic Risk Score (0-100) per transaction.
"""

import math
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict


# Indian Statutory National Holidays (Fixed Calendar Dates)
INDIAN_NATIONAL_HOLIDAYS = [
    (1, 26),   # Republic Day
    (8, 15),   # Independence Day
    (10, 2)    # Gandhi Jayanti
]


class ForensicAnalysisEngine:
    """Multi-dimensional financial forensic analysis and anomaly detection suite."""

    @classmethod
    def run_all_forensic_tests(
        cls,
        records: List[Dict[str, Any]],
        mapping: Dict[str, str],
        custom_thresholds: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Executes all forensic tests and generates composite risk scores.
        """
        amount_col = mapping.get('amount')
        date_col = mapping.get('date')
        vendor_col = mapping.get('vendor')
        invoice_col = mapping.get('invoice_no')
        desc_col = mapping.get('description')

        if not amount_col:
            return {"success": False, "error_message": "Amount column is required for forensic tests."}

        thresholds = custom_thresholds or [50000.0, 200000.0, 1000000.0, 100000.0]

        # 1. Relative Size Factor (RSF)
        rsf_results = cls.compute_relative_size_factor(records, amount_col, vendor_col)

        # 2. Duplicate Detection
        dup_results = cls.compute_duplicates(records, amount_col, vendor_col, invoice_col, date_col)

        # 3. Split Transaction / Smurfing Detection
        split_results = cls.compute_split_transactions(records, amount_col, vendor_col, date_col, thresholds)

        # 4. Round Number Detection
        round_results = cls.compute_round_numbers(records, amount_col)

        # 5. Temporal / Weekend / Year-End Postings
        temporal_results = cls.compute_temporal_anomalies(records, date_col)

        # 6. Synthesize Composite Risk Scores
        composite_results = cls.synthesize_composite_risk_scores(
            records=records,
            amount_col=amount_col,
            date_col=date_col,
            vendor_col=vendor_col,
            invoice_col=invoice_col,
            rsf_results=rsf_results,
            dup_results=dup_results,
            split_results=split_results,
            round_results=round_results,
            temporal_results=temporal_results
        )

        return {
            "success": True,
            "rsf_analysis": rsf_results,
            "duplicate_analysis": dup_results,
            "split_transaction_analysis": split_results,
            "round_number_analysis": round_results,
            "temporal_analysis": temporal_results,
            "composite_risk_summary": composite_results["summary"],
            "flagged_transactions": composite_results["flagged_transactions"]
        }

    # ------------------------------------------------------------------------
    # 1. RELATIVE SIZE FACTOR (RSF)
    # ------------------------------------------------------------------------

    @classmethod
    def compute_relative_size_factor(
        cls,
        records: List[Dict[str, Any]],
        amount_col: str,
        vendor_col: Optional[str]
    ) -> Dict[str, Any]:
        """
        RSF = (Largest Payment to Vendor) / (Second Largest Payment to Vendor).
        High RSF (> 5 or > 10) indicates anomalous outlier invoices.
        """
        if not vendor_col:
            return {"available": False, "reason": "No Vendor / Party column mapped."}

        vendor_amounts = defaultdict(list)
        vendor_row_indices = defaultdict(list)

        for idx, row in enumerate(records):
            vendor = str(row.get(vendor_col, '')).strip()
            val = row.get(amount_col)
            if not vendor or val is None:
                continue
            try:
                amt = float(str(val).replace(',', '').replace('₹', '').replace('$', '').strip())
                if amt > 0:
                    vendor_amounts[vendor].append(amt)
                    vendor_row_indices[vendor].append(idx)
            except (ValueError, TypeError):
                continue

        vendor_rsf_list = []
        for vendor, amounts in vendor_amounts.items():
            count = len(amounts)
            if count == 0:
                continue

            sorted_amts = sorted(amounts, reverse=True)
            max_amt = sorted_amts[0]
            
            if count == 1:
                # Only 1 transaction: RSF not directly applicable or set to 1.0 with single txn note
                rsf = 1.0
                second_amt = max_amt
                is_single = True
            else:
                second_amt = sorted_amts[1]
                rsf = max_amt / second_amt if second_amt > 0 else 1.0
                is_single = False

            risk = "CRITICAL" if rsf >= 10.0 else ("HIGH" if rsf >= 5.0 else ("MODERATE" if rsf >= 3.0 else "LOW"))
            is_outlier = rsf >= 5.0 and not is_single

            vendor_rsf_list.append({
                "vendor_name": vendor,
                "transaction_count": count,
                "total_spend": round(sum(amounts), 2),
                "largest_amount": round(max_amt, 2),
                "second_largest_amount": round(second_amt, 2),
                "rsf_value": round(rsf, 2),
                "is_single_transaction": is_single,
                "is_outlier": is_outlier,
                "risk_level": risk,
                "row_indices": vendor_row_indices[vendor]
            })

        vendor_rsf_list.sort(key=lambda x: (not x["is_single_transaction"], x["rsf_value"]), reverse=True)
        outlier_count = sum(1 for v in vendor_rsf_list if v["is_outlier"])

        return {
            "available": True,
            "total_vendors_analyzed": len(vendor_rsf_list),
            "outlier_vendor_count": outlier_count,
            "high_risk_vendors": vendor_rsf_list[:50]
        }

    # ------------------------------------------------------------------------
    # 2. DUPLICATE INVOICE & PAYMENT FINDER
    # ------------------------------------------------------------------------

    @classmethod
    def compute_duplicates(
        cls,
        records: List[Dict[str, Any]],
        amount_col: str,
        vendor_col: Optional[str],
        invoice_col: Optional[str],
        date_col: Optional[str]
    ) -> Dict[str, Any]:
        """
        Finds exact duplicates and fuzzy same-vendor/same-amount pairs.
        """
        exact_groups = defaultdict(list)
        fuzzy_vendor_amount = defaultdict(list)

        for idx, row in enumerate(records):
            amt_val = row.get(amount_col)
            if amt_val is None:
                continue
            try:
                amt = float(str(amt_val).replace(',', '').replace('₹', '').replace('$', '').strip())
            except (ValueError, TypeError):
                continue

            vendor = str(row.get(vendor_col, '')).strip().upper() if vendor_col else "ALL"
            invoice = str(row.get(invoice_col, '')).strip().upper() if invoice_col else ""
            date_str = str(row.get(date_col, '')).strip() if date_col else ""

            # Exact matching key
            exact_key = (vendor, amt, invoice, date_str) if invoice else (vendor, amt, date_str)
            exact_groups[exact_key].append(idx)

            # Fuzzy vendor-amount matching
            fuzzy_key = (vendor, amt)
            fuzzy_vendor_amount[fuzzy_key].append({"index": idx, "date": date_str, "invoice": invoice, "row": row})

        # Process exact duplicates
        exact_dups = []
        for key, indices in exact_groups.items():
            if len(indices) > 1:
                vendor = key[0]
                amt = key[1]
                exact_dups.append({
                    "vendor": vendor,
                    "amount": amt,
                    "duplicate_count": len(indices),
                    "total_duplicated_value": round(amt * len(indices), 2),
                    "row_indices": indices
                })

        # Process fuzzy duplicates (same vendor, same amount, multiple occurrences)
        fuzzy_dups = []
        for (vendor, amt), items in fuzzy_vendor_amount.items():
            if len(items) > 1 and vendor != "ALL":
                indices = [item["index"] for item in items]
                fuzzy_dups.append({
                    "vendor": vendor,
                    "amount": amt,
                    "count": len(items),
                    "total_value": round(amt * len(items), 2),
                    "dates": list(set([item["date"] for item in items if item["date"]])),
                    "invoices": list(set([item["invoice"] for item in items if item["invoice"]])),
                    "row_indices": indices
                })

        exact_dups.sort(key=lambda x: x["total_duplicated_value"], reverse=True)
        fuzzy_dups.sort(key=lambda x: x["total_value"], reverse=True)

        return {
            "exact_duplicate_clusters": len(exact_dups),
            "exact_duplicated_rows": sum(d["duplicate_count"] for d in exact_dups),
            "exact_duplicates": exact_dups[:50],
            "fuzzy_duplicates": fuzzy_dups[:50]
        }

    # ------------------------------------------------------------------------
    # 3. SPLIT TRANSACTIONS / SMURFING DETECTOR
    # ------------------------------------------------------------------------

    @classmethod
    def compute_split_transactions(
        cls,
        records: List[Dict[str, Any]],
        amount_col: str,
        vendor_col: Optional[str],
        date_col: Optional[str],
        thresholds: List[float]
    ) -> Dict[str, Any]:
        """
        Flags transactions falling in the evasion window [Threshold * 0.90, Threshold - 1].
        e.g., ₹45,000 to ₹49,999 for ₹50,000 PAN threshold.
        """
        flagged_clusters = []
        all_flagged_indices = set()

        for threshold in thresholds:
            lower_bound = threshold * 0.90
            upper_bound = threshold - 0.01

            matching_indices = []
            matching_rows = []
            vendor_counts = defaultdict(list)

            for idx, row in enumerate(records):
                amt_val = row.get(amount_col)
                if amt_val is None:
                    continue
                try:
                    amt = float(str(amt_val).replace(',', '').replace('₹', '').replace('$', '').strip())
                except (ValueError, TypeError):
                    continue

                if lower_bound <= amt <= upper_bound:
                    matching_indices.append(idx)
                    all_flagged_indices.add(idx)
                    vendor = str(row.get(vendor_col, 'GENERAL')).strip() if vendor_col else 'GENERAL'
                    vendor_counts[vendor].append(idx)

            if matching_indices:
                flagged_clusters.append({
                    "threshold_limit": threshold,
                    "evasion_window": f"₹{lower_bound:,.0f} to ₹{threshold:,.0f}",
                    "description": cls._get_threshold_description(threshold),
                    "transaction_count": len(matching_indices),
                    "row_indices": matching_indices,
                    "top_vendors": [
                        {"vendor": v, "count": len(idxs), "row_indices": idxs}
                        for v, idxs in sorted(vendor_counts.items(), key=lambda x: len(x[1]), reverse=True)[:10]
                    ]
                })

        return {
            "total_split_anomalies": len(all_flagged_indices),
            "threshold_evaluations": flagged_clusters,
            "all_flagged_row_indices": list(all_flagged_indices)
        }

    @staticmethod
    def _get_threshold_description(thresh: float) -> str:
        if abs(thresh - 50000.0) < 1.0:
            return "Indian Income Tax PAN Quoting & Cash Transaction Threshold (Rule 114B / Sec 139A)"
        elif abs(thresh - 200000.0) < 1.0:
            return "Cash Receipt / Transaction Prohibition Limit (Section 269ST of IT Act)"
        elif abs(thresh - 1000000.0) < 1.0:
            return "Statutory High-Value Transaction / SFT Reporting Threshold"
        elif abs(thresh - 100000.0) < 1.0:
            return "Standard Corporate Delegation of Authority (DoA) Approval Limit"
        return f"Custom Audit Threshold (Limit ₹{thresh:,.0f})"

    # ------------------------------------------------------------------------
    # 4. ROUND NUMBER ANOMALY SCANNER
    # ------------------------------------------------------------------------

    @classmethod
    def compute_round_numbers(
        cls,
        records: List[Dict[str, Any]],
        amount_col: str
    ) -> Dict[str, Any]:
        """
        Detects uncharacteristically round transaction values (multiples of 1k, 10k, 50k, 1L).
        """
        round_1k = []
        round_10k = []
        round_50k = []
        round_1l = []
        total_valid = 0

        for idx, row in enumerate(records):
            amt_val = row.get(amount_col)
            if amt_val is None:
                continue
            try:
                amt = float(str(amt_val).replace(',', '').replace('₹', '').replace('$', '').strip())
                if amt <= 0:
                    continue
                total_valid += 1

                if amt >= 100000 and amt % 100000 == 0:
                    round_1l.append(idx)
                elif amt >= 50000 and amt % 50000 == 0:
                    round_50k.append(idx)
                elif amt >= 10000 and amt % 10000 == 0:
                    round_10k.append(idx)
                elif amt >= 1000 and amt % 1000 == 0:
                    round_1k.append(idx)
            except (ValueError, TypeError):
                continue

        all_round = set(round_1k + round_10k + round_50k + round_1l)
        round_pct = (len(all_round) / total_valid * 100) if total_valid > 0 else 0.0

        return {
            "total_round_transactions": len(all_round),
            "round_percentage": round(round_pct, 2),
            "is_elevated_round_density": round_pct > 15.0,
            "breakdown": {
                "multiples_of_1Lakh": len(round_1l),
                "multiples_of_50k": len(round_50k),
                "multiples_of_10k": len(round_10k),
                "multiples_of_1k": len(round_1k)
            },
            "all_round_row_indices": list(all_round)
        }

    # ------------------------------------------------------------------------
    # 5. TEMPORAL & CALENDAR ANOMALIES
    # ------------------------------------------------------------------------

    @classmethod
    def compute_temporal_anomalies(
        cls,
        records: List[Dict[str, Any]],
        date_col: Optional[str]
    ) -> Dict[str, Any]:
        """
        Identifies weekend postings, statutory holiday postings, and fiscal year-end (March 31) clustering.
        """
        if not date_col:
            return {"available": False, "reason": "No Date column mapped."}

        weekend_indices = []
        holiday_indices = []
        fiscal_yearend_indices = []

        date_formats = [
            "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
            "%Y/%m/%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"
        ]

        for idx, row in enumerate(records):
            raw_date = row.get(date_col)
            if not raw_date:
                continue

            dt = None
            if isinstance(raw_date, datetime):
                dt = raw_date
            else:
                str_date = str(raw_date).strip().split('T')[0]
                for fmt in date_formats:
                    try:
                        dt = datetime.strptime(str_date, fmt)
                        break
                    except ValueError:
                        continue

            if not dt:
                continue

            # Saturday = 5, Sunday = 6
            if dt.weekday() in (5, 6):
                weekend_indices.append(idx)

            # Indian Statutory Holidays
            if (dt.month, dt.day) in INDIAN_NATIONAL_HOLIDAYS:
                holiday_indices.append(idx)

            # Fiscal Year-End (March 30-31)
            if dt.month == 3 and dt.day in (30, 31):
                fiscal_yearend_indices.append(idx)

        return {
            "available": True,
            "weekend_postings_count": len(weekend_indices),
            "holiday_postings_count": len(holiday_indices),
            "fiscal_year_end_count": len(fiscal_yearend_indices),
            "weekend_row_indices": weekend_indices,
            "holiday_row_indices": holiday_indices,
            "fiscal_year_end_row_indices": fiscal_yearend_indices
        }

    # ------------------------------------------------------------------------
    # 6. SYNTHESIZE MULTI-FACTOR COMPOSITE RISK SCORES
    # ------------------------------------------------------------------------

    @classmethod
    def synthesize_composite_risk_scores(
        cls,
        records: List[Dict[str, Any]],
        amount_col: str,
        date_col: Optional[str],
        vendor_col: Optional[str],
        invoice_col: Optional[str],
        rsf_results: Dict[str, Any],
        dup_results: Dict[str, Any],
        split_results: Dict[str, Any],
        round_results: Dict[str, Any],
        temporal_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculates multi-factor 0-100 risk score per transaction row."""
        # Precompute lookup sets
        rsf_outlier_rows = set()
        if rsf_results.get("available"):
            for v in rsf_results.get("high_risk_vendors", []):
                if v.get("is_outlier"):
                    rsf_outlier_rows.update(v.get("row_indices", []))

        dup_rows = set()
        for d in dup_results.get("exact_duplicates", []):
            dup_rows.update(d.get("row_indices", []))

        split_rows = set(split_results.get("all_flagged_row_indices", []))
        round_rows = set(round_results.get("all_round_row_indices", []))

        weekend_rows = set(temporal_results.get("weekend_row_indices", [])) if temporal_results.get("available") else set()
        holiday_rows = set(temporal_results.get("holiday_row_indices", [])) if temporal_results.get("available") else set()

        flagged_transactions = []
        risk_counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}

        for idx, row in enumerate(records):
            score = 0
            factors = []

            if idx in dup_rows:
                score += 35
                factors.append("Exact Duplicate Payment / Voucher")

            if idx in split_rows:
                score += 25
                factors.append("Split Transaction / Smurfing Anomaly")

            if idx in rsf_outlier_rows:
                score += 25
                factors.append("Abnormal Vendor RSF Invoice Outlier")

            if idx in round_rows:
                score += 15
                factors.append("Round Amount Estimation / Provision")

            if idx in holiday_rows:
                score += 20
                factors.append("National Statutory Holiday Posting")
            elif idx in weekend_rows:
                score += 10
                factors.append("Weekend Non-Business Day Posting")

            # Final normalized score (cap at 100)
            final_score = min(100, score)

            if final_score >= 70:
                tier = "CRITICAL"
            elif final_score >= 45:
                tier = "HIGH"
            elif final_score >= 20:
                tier = "MODERATE"
            else:
                tier = "LOW"

            risk_counts[tier] += 1

            if final_score >= 20:
                flagged_transactions.append({
                    "row_index": idx,
                    "risk_score": final_score,
                    "risk_tier": tier,
                    "anomaly_factors": factors,
                    "amount": row.get(amount_col),
                    "date": row.get(date_col) if date_col else "",
                    "vendor": row.get(vendor_col) if vendor_col else "",
                    "invoice_no": row.get(invoice_col) if invoice_col else "",
                    "record_data": row
                })

        flagged_transactions.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "summary": {
                "total_analyzed": len(records),
                "total_flagged": len(flagged_transactions),
                "risk_distribution": risk_counts
            },
            "flagged_transactions": flagged_transactions[:100]  # top 100 for UI responsiveness
        }
