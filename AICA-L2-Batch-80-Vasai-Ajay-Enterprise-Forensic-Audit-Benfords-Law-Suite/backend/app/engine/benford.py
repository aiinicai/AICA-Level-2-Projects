"""
Forensic Benford's Law Analytics Engine.

Implements the complete Nigrini financial forensic methodology:
1. First Digit (1D) Test (Digits 1 to 9).
2. Second Digit (2D) Test (Digits 0 to 9).
3. First-Two Digits (F2D) Test (Digits 10 to 99).
4. First-Three Digits (F3D) Test (Digits 100 to 999).
5. Last-Two Digits (L2D / Number Uniformity) Test (Digits 00 to 99).
6. Mantissa Arc & Distribution Test (Mean, Variance, Center of Gravity).
7. Nigrini Mean Absolute Deviation (MAD) Conformity Grading.
8. Z-Scores with Yates Continuity Correction.
9. Chi-Square (χ²) & Kolmogorov-Smirnov (K-S) Goodness-of-Fit Tests.
10. Interactive Digit-to-Transaction Row Indexing for Audit Drilldown.
"""

import math
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from scipy import stats


# ============================================================================
# NIGRINI MAD THRESHOLDS & BENCHMARKS
# ============================================================================

MAD_THRESHOLDS = {
    'first_digit': [
        (0.006, "Close Conformity", "LOW_RISK", "#10B981"),
        (0.012, "Acceptable Conformity", "MODERATE_RISK", "#3B82F6"),
        (0.015, "Marginally Acceptable", "ELEVATED_RISK", "#F59E0B"),
        (float('inf'), "Non-Conformity (High Risk)", "HIGH_RISK", "#EF4444")
    ],
    'second_digit': [
        (0.008, "Close Conformity", "LOW_RISK", "#10B981"),
        (0.018, "Acceptable Conformity", "MODERATE_RISK", "#3B82F6"),
        (0.022, "Marginally Acceptable", "ELEVATED_RISK", "#F59E0B"),
        (float('inf'), "Non-Conformity (High Risk)", "HIGH_RISK", "#EF4444")
    ],
    'first_two_digits': [
        (0.0012, "Close Conformity", "LOW_RISK", "#10B981"),
        (0.0018, "Acceptable Conformity", "MODERATE_RISK", "#3B82F6"),
        (0.0022, "Marginally Acceptable", "ELEVATED_RISK", "#F59E0B"),
        (float('inf'), "Non-Conformity (High Risk)", "HIGH_RISK", "#EF4444")
    ],
    'first_three_digits': [
        (0.00036, "Close Conformity", "LOW_RISK", "#10B981"),
        (0.00070, "Acceptable Conformity", "MODERATE_RISK", "#3B82F6"),
        (0.00090, "Marginally Acceptable", "ELEVATED_RISK", "#F59E0B"),
        (float('inf'), "Non-Conformity (High Risk)", "HIGH_RISK", "#EF4444")
    ],
    'last_two_digits': [
        (0.0012, "Close Conformity (Uniform)", "LOW_RISK", "#10B981"),
        (0.0022, "Acceptable Uniformity", "MODERATE_RISK", "#3B82F6"),
        (0.0030, "Marginal Uniformity", "ELEVATED_RISK", "#F59E0B"),
        (float('inf'), "Non-Uniform (Fabrication Alert)", "HIGH_RISK", "#EF4444")
    ]
}


def evaluate_mad_rating(test_type: str, mad_value: float) -> Tuple[str, str, str]:
    """Returns (Conformity Rating, Risk Level, Hex Color) based on Nigrini benchmarks."""
    benchmarks = MAD_THRESHOLDS.get(test_type, MAD_THRESHOLDS['first_digit'])
    for threshold, rating, risk_level, color in benchmarks:
        if mad_value <= threshold:
            return rating, risk_level, color
    return "Non-Conformity", "HIGH_RISK", "#EF4444"


# ============================================================================
# BENFORD'S LAW THEORETICAL PROBABILITIES
# ============================================================================

def get_theoretical_first_digit() -> Dict[int, float]:
    """P(d) = log10(1 + 1/d) for d in 1..9"""
    return {d: math.log10(1 + 1.0 / d) for d in range(1, 10)}


def get_theoretical_second_digit() -> Dict[int, float]:
    """P(d2) = sum_{d1=1..9} log10(1 + 1/(10*d1 + d2)) for d2 in 0..9"""
    res = {}
    for d2 in range(10):
        prob = sum(math.log10(1 + 1.0 / (10 * d1 + d2)) for d1 in range(1, 10))
        res[d2] = prob
    return res


def get_theoretical_first_two_digits() -> Dict[int, float]:
    """P(d12) = log10(1 + 1/d12) for d12 in 10..99"""
    return {d: math.log10(1 + 1.0 / d) for d in range(10, 100)}


def get_theoretical_first_three_digits() -> Dict[int, float]:
    """P(d123) = log10(1 + 1/d123) for d123 in 100..999"""
    return {d: math.log10(1 + 1.0 / d) for d in range(100, 1000)}


def get_theoretical_last_two_digits() -> Dict[int, float]:
    """P(last2) = 0.01 for last2 in 00..99 (Uniform distribution)"""
    return {d: 0.01 for d in range(100)}


# ============================================================================
# DIGIT EXTRACTION & NORMALIZATION
# ============================================================================

def extract_digits(value: Any) -> Optional[Tuple[int, int, int, int, int, float]]:
    """
    Extracts (d1, d2, d12, d123, last2, mantissa) from a numeric value.
    Ignores zero, negative values, and non-numeric inputs.
    """
    if value is None:
        return None
    try:
        if isinstance(value, str):
            # Clean currency symbols, commas, whitespace
            cleaned = value.replace('₹', '').replace('$', '').replace(',', '').replace(' ', '').strip()
            num = float(cleaned)
        else:
            num = float(value)
    except (ValueError, TypeError):
        return None

    # Benford's Law applies to positive numbers > 0
    if num <= 0 or math.isnan(num) or math.isinf(num):
        return None

    # Calculate mantissa: fractional part of log10(num)
    log_val = math.log10(num)
    mantissa = log_val - math.floor(log_val)

    # Convert to scientific notation string to safely get leading digits regardless of decimals
    # e.g., 0.00452 -> '4.52e-03' -> '452000'
    sci_str = f"{num:.10e}"
    base_digits = sci_str.split('e')[0].replace('.', '')

    if len(base_digits) < 3:
        base_digits = base_digits.ljust(4, '0')

    d1 = int(base_digits[0])
    d2 = int(base_digits[1])
    d12 = int(base_digits[:2])
    d123 = int(base_digits[:3])

    # For last 2 digits, use integer cents/pennies or last 2 digits before decimal if large
    # Standard Nigrini practice: use rounded integer or 2 decimal places if present
    int_str = f"{abs(round(num * 100))}"
    if len(int_str) >= 2:
        last2 = int(int_str[-2:])
    else:
        last2 = int(int_str)

    return d1, d2, d12, d123, last2, mantissa


# ============================================================================
# BENFORD TEST EXECUTION ENGINE
# ============================================================================

class BenfordAnalysisEngine:
    """Core mathematical engine executing Benford tests, MAD grading, and Z-scores."""

    @classmethod
    def run_full_benford_suite(
        cls,
        records: List[Dict[str, Any]],
        amount_column: str
    ) -> Dict[str, Any]:
        """
        Executes all Benford tests (1D, 2D, F2D, F3D, L2D, Mantissa Arc) on the dataset.
        Returns comprehensive metrics, charts data, and row drilldowns.
        """
        valid_records = []
        valid_indices = []
        d1_list = []
        d2_list = []
        d12_list = []
        d123_list = []
        last2_list = []
        mantissa_list = []

        d1_row_map: Dict[int, List[int]] = {d: [] for d in range(1, 10)}
        d2_row_map: Dict[int, List[int]] = {d: [] for d in range(10)}
        d12_row_map: Dict[int, List[int]] = {d: [] for d in range(10, 100)}
        d123_row_map: Dict[int, List[int]] = {d: [] for d in range(100, 1000)}
        last2_row_map: Dict[int, List[int]] = {d: [] for d in range(100)}

        for idx, row in enumerate(records):
            val = row.get(amount_column)
            extracted = extract_digits(val)
            if extracted is not None:
                d1, d2, d12, d123, last2, mantissa = extracted
                valid_records.append(row)
                valid_indices.append(idx)
                d1_list.append(d1)
                d2_list.append(d2)
                d12_list.append(d12)
                d123_list.append(d123)
                last2_list.append(last2)
                mantissa_list.append(mantissa)

                d1_row_map[d1].append(idx)
                d2_row_map[d2].append(idx)
                d12_row_map[d12].append(idx)
                d123_row_map[d123].append(idx)
                last2_row_map[last2].append(idx)

        total_valid = len(valid_records)
        total_rows = len(records)
        excluded_rows = total_rows - total_valid

        if total_valid < 10:
            return {
                "success": False,
                "error_message": f"Insufficient valid numeric data points (found {total_valid}, minimum required is 10).",
                "recommendation": "Benford's Law analysis requires at least 10 positive transaction amounts spanning multiple orders of magnitude.",
                "total_rows": total_rows,
                "valid_rows": total_valid
            }

        # 1. First Digit Test
        res_1d = cls._compute_digit_test(
            digits=d1_list,
            theoretical=get_theoretical_first_digit(),
            test_type='first_digit',
            total_n=total_valid,
            row_map=d1_row_map
        )

        # 2. Second Digit Test
        res_2d = cls._compute_digit_test(
            digits=d2_list,
            theoretical=get_theoretical_second_digit(),
            test_type='second_digit',
            total_n=total_valid,
            row_map=d2_row_map
        )

        # 3. First-Two Digits Test
        res_f2d = cls._compute_digit_test(
            digits=d12_list,
            theoretical=get_theoretical_first_two_digits(),
            test_type='first_two_digits',
            total_n=total_valid,
            row_map=d12_row_map
        )

        # 4. First-Three Digits Test
        res_f3d = cls._compute_digit_test(
            digits=d123_list,
            theoretical=get_theoretical_first_three_digits(),
            test_type='first_three_digits',
            total_n=total_valid,
            row_map=d123_row_map
        )

        # 5. Last-Two Digits Test (Uniformity)
        res_l2d = cls._compute_digit_test(
            digits=last2_list,
            theoretical=get_theoretical_last_two_digits(),
            test_type='last_two_digits',
            total_n=total_valid,
            row_map=last2_row_map
        )

        # 6. Mantissa Arc Test
        mantissa_res = cls._compute_mantissa_arc_test(mantissa_list)

        # 7. Summary Risk Synthesis
        mad_scores = {
            "first_digit_mad": res_1d["mad"],
            "second_digit_mad": res_2d["mad"],
            "first_two_digits_mad": res_f2d["mad"]
        }
        overall_mad_rating, overall_risk, overall_color = evaluate_mad_rating('first_two_digits', res_f2d["mad"])

        return {
            "success": True,
            "total_rows": total_rows,
            "valid_rows": total_valid,
            "excluded_rows": excluded_rows,
            "amount_column": amount_column,
            "overall_summary": {
                "conformity_rating": overall_mad_rating,
                "risk_level": overall_risk,
                "badge_color": overall_color,
                "mad_f2d": res_f2d["mad"],
                "mad_1d": res_1d["mad"],
                "mad_2d": res_2d["mad"],
                "sample_size_adequate": total_valid >= 50,
                "nigrini_primary_test": "First-Two Digits (F2D) Test is primary standard for forensic audit."
            },
            "first_digit": res_1d,
            "second_digit": res_2d,
            "first_two_digits": res_f2d,
            "first_three_digits": res_f3d,
            "last_two_digits": res_l2d,
            "mantissa_arc": mantissa_res
        }

    # ------------------------------------------------------------------------
    # DIGIT TEST COMPUTATION (MAD, Z-SCORE, CHI-SQ, KS)
    # ------------------------------------------------------------------------

    @classmethod
    def _compute_digit_test(
        cls,
        digits: List[int],
        theoretical: Dict[int, float],
        test_type: str,
        total_n: int,
        row_map: Dict[int, List[int]]
    ) -> Dict[str, Any]:
        """Calculates observed frequencies, theoretical expected values, Z-scores, MAD, Chi-sq, KS."""
        counts = {}
        for d in theoretical.keys():
            counts[d] = 0
        for d in digits:
            if d in counts:
                counts[d] += 1

        items = []
        observed_probs = []
        expected_probs = []
        cum_obs = 0.0
        cum_exp = 0.0
        max_ks_dist = 0.0

        for d in sorted(theoretical.keys()):
            count = counts[d]
            obs_prob = count / total_n
            exp_prob = theoretical[d]
            exp_count = exp_prob * total_n
            diff = obs_prob - exp_prob
            abs_diff = abs(diff)

            # Yates continuity corrected Z-score for binomial proportion
            term = abs_diff - (1.0 / (2.0 * total_n))
            term = max(0.0, term)
            denom = math.sqrt((exp_prob * (1.0 - exp_prob)) / total_n)
            z_score = term / denom if denom > 0 else 0.0

            # Cumulative probabilities for Kolmogorov-Smirnov
            cum_obs += obs_prob
            cum_exp += exp_prob
            ks_dist = abs(cum_obs - cum_exp)
            if ks_dist > max_ks_dist:
                max_ks_dist = ks_dist

            is_significant_95 = z_score > 1.96
            is_significant_99 = z_score > 2.576

            items.append({
                "digit": d,
                "digit_label": str(d) if len(str(d)) == 2 and test_type == 'last_two_digits' else f"{d:02d}" if test_type == 'last_two_digits' else str(d),
                "count": count,
                "expected_count": round(exp_count, 1),
                "observed_prob": round(obs_prob, 5),
                "expected_prob": round(exp_prob, 5),
                "observed_pct": round(obs_prob * 100, 2),
                "expected_pct": round(exp_prob * 100, 2),
                "difference": round(diff, 5),
                "abs_diff": round(abs_diff, 5),
                "z_score": round(z_score, 2),
                "is_spike": is_significant_95 and diff > 0,
                "is_significant_95": is_significant_95,
                "is_significant_99": is_significant_99,
                "row_indices": row_map.get(d, [])
            })

            observed_probs.append(obs_prob)
            expected_probs.append(exp_prob)

        # Nigrini MAD (Mean Absolute Deviation)
        mad = float(np.mean([item["abs_diff"] for item in items]))
        rating, risk_level, badge_color = evaluate_mad_rating(test_type, mad)

        # Chi-Square Test
        obs_counts = [item["count"] for item in items]
        exp_counts = [item["expected_count"] for item in items]
        chi2_stat = float(sum(((o - e) ** 2) / e for o, e in zip(obs_counts, exp_counts) if e > 0))
        dof = len(items) - 1
        p_value = float(stats.chi2.sf(chi2_stat, dof)) if dof > 0 else 1.0

        # Kolmogorov-Smirnov critical threshold (alpha=0.05)
        ks_crit_95 = 1.36 / math.sqrt(total_n)
        ks_significant = max_ks_dist > ks_crit_95

        # Identify top anomaly digits
        spike_digits = [item["digit"] for item in items if item["is_spike"]]

        return {
            "test_type": test_type,
            "mad": round(mad, 6),
            "conformity_rating": rating,
            "risk_level": risk_level,
            "badge_color": badge_color,
            "chi2_statistic": round(chi2_stat, 2),
            "chi2_dof": dof,
            "chi2_p_value": round(p_value, 6),
            "ks_statistic": round(max_ks_dist, 5),
            "ks_critical_95": round(ks_crit_95, 5),
            "ks_significant": ks_significant,
            "spike_digits": spike_digits,
            "items": items
        }

    # ------------------------------------------------------------------------
    # MANTISSA ARC TEST
    # ------------------------------------------------------------------------

    @classmethod
    def _compute_mantissa_arc_test(cls, mantissas: List[float]) -> Dict[str, Any]:
        """
        Calculates Mantissa Distribution and Center of Gravity.
        Under Benford's law:
        - Mean mantissa = 0.5
        - Variance = 1/12 ≈ 0.08333
        - Center of gravity vector (X, Y) near (0, 0)
        """
        if not mantissas:
            return {"success": False}

        arr = np.array(mantissas)
        mean_m = float(np.mean(arr))
        var_m = float(np.var(arr))
        skew_m = float(stats.skew(arr))
        kurt_m = float(stats.kurtosis(arr))

        # Center of gravity polar vector
        angles = 2 * math.pi * arr
        cog_x = float(np.mean(np.cos(angles)))
        cog_y = float(np.mean(np.sin(angles)))
        cog_radius = math.sqrt(cog_x**2 + cog_y**2)

        # Mantissa histogram (10 bins: 0.0 to 1.0)
        hist, bin_edges = np.histogram(arr, bins=10, range=(0.0, 1.0))
        hist_data = []
        expected_bin_prob = 0.10
        total_n = len(mantissas)

        for i in range(10):
            cnt = int(hist[i])
            obs_p = cnt / total_n
            hist_data.append({
                "bin_label": f"{bin_edges[i]:.1f} - {bin_edges[i+1]:.1f}",
                "count": cnt,
                "observed_prob": round(obs_p, 4),
                "expected_prob": expected_bin_prob,
                "difference": round(obs_p - expected_bin_prob, 4)
            })

        # Conformity evaluation for mantissas
        mean_diff = abs(mean_m - 0.5)
        var_diff = abs(var_m - (1.0 / 12.0))
        is_normal = mean_diff < 0.03 and var_diff < 0.015

        return {
            "mean_mantissa": round(mean_m, 5),
            "expected_mean": 0.50000,
            "variance_mantissa": round(var_m, 5),
            "expected_variance": round(1.0 / 12.0, 5),
            "skewness": round(skew_m, 4),
            "kurtosis": round(kurt_m, 4),
            "center_of_gravity_x": round(cog_x, 4),
            "center_of_gravity_y": round(cog_y, 4),
            "center_of_gravity_radius": round(cog_radius, 4),
            "is_conforming": is_normal,
            "status": "Conforming Distribution" if is_normal else "Potential Truncation / Outlier Bias",
            "histogram": hist_data
        }
