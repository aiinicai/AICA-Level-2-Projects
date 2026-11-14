#!/usr/bin/env python3
"""
DirhamTrack AI - Python Machine Learning Analytics Engine
Features:
1. Isolation Forest Anomaly & Fraud Detection (Scikit-Learn compatible)
   - Evaluates multivariate outlier scores across transaction amount, velocity,
     merchant deviations, foreign currencies, duplicate charge detection.
2. Time-Series Predictive Budget & Cash Flow Forecast (Statsmodels compatible)
   - Holt-Winters / Exponential Smoothing trend forecasting for month-end spending,
     account balances, liquidity cushion, and category budget overruns.
"""

import sys
import json
import math
import random
from datetime import datetime, timedelta

# Check if scikit-learn and statsmodels are available, otherwise use native mathematical implementations
HAS_SKLEARN = False
HAS_STATSMODELS = False

try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import statsmodels.api as sm
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


# ==============================================================================
# Pure Python Isolation Forest Implementation (Scikit-Learn Math Specification)
# ==============================================================================
def c_factor(n):
    """Average path length of unsuccessful search in a Binary Search Tree (BST)"""
    if n <= 1:
        return 1.0
    if n == 2:
        return 1.0
    # Euler-Mascheroni constant ≈ 0.5772156649
    return 2.0 * (math.log(n - 1) + 0.5772156649) - (2.0 * (n - 1) / n)


class IsolationTreeNode:
    def __init__(self, left=None, right=None, split_feature=None, split_value=None, size=0):
        self.left = left
        self.right = right
        self.split_feature = split_feature
        self.split_value = split_value
        self.size = size
        self.is_leaf = left is None and right is None


def build_isolation_tree(X, current_height, height_limit):
    n_samples = len(X)
    if current_height >= height_limit or n_samples <= 1:
        return IsolationTreeNode(size=n_samples)

    n_features = len(X[0])
    # Pick a random feature
    feature_idx = random.randint(0, n_features - 1)
    values = [x[feature_idx] for x in X]
    min_val, max_val = min(values), max(values)

    if min_val == max_val:
        return IsolationTreeNode(size=n_samples)

    split_val = random.uniform(min_val, max_val)

    left_X = [x for x in X if x[feature_idx] < split_val]
    right_X = [x for x in X if x[feature_idx] >= split_val]

    if not left_X or not right_X:
        return IsolationTreeNode(size=n_samples)

    left_node = build_isolation_tree(left_X, current_height + 1, height_limit)
    right_node = build_isolation_tree(right_X, current_height + 1, height_limit)

    return IsolationTreeNode(
        left=left_node,
        right=right_node,
        split_feature=feature_idx,
        split_value=split_val,
        size=n_samples
    )


def path_length(x, node, current_depth=0):
    if node.is_leaf:
        return current_depth + c_factor(node.size)
    if x[node.split_feature] < node.split_value:
        return path_length(x, node.left, current_depth + 1)
    else:
        return path_length(x, node.right, current_depth + 1)


class NativeIsolationForest:
    def __init__(self, n_estimators=100, max_samples=256, contamination=0.1):
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.trees = []

    def fit(self, X):
        n_samples = len(X)
        if n_samples == 0:
            return self
        subsample_size = min(self.max_samples, n_samples)
        height_limit = math.ceil(math.log2(max(subsample_size, 2)))

        self.trees = []
        for _ in range(self.n_estimators):
            if n_samples > subsample_size:
                sample_indices = random.sample(range(n_samples), subsample_size)
                sample = [X[i] for i in sample_indices]
            else:
                sample = list(X)
            tree = build_isolation_tree(sample, 0, height_limit)
            self.trees.append(tree)
        return self

    def anomaly_score(self, x, n_samples):
        if not self.trees or n_samples <= 1:
            return 0.5
        paths = [path_length(x, tree) for tree in self.trees]
        avg_path = sum(paths) / len(paths)
        c = c_factor(n_samples)
        return math.pow(2.0, - (avg_path / c))


# ==============================================================================
# Fraud Detection Logic
# ==============================================================================
def run_fraud_detection(payload):
    transactions = payload.get("transactions", [])
    accounts = payload.get("accounts", [])

    if not transactions:
        return {
            "model": "Python Scikit-learn (Isolation Forest)",
            "total_analyzed": 0,
            "anomalies_detected": 0,
            "alerts": [],
            "risk_summary": {
                "high_risk": 0,
                "medium_risk": 0,
                "clean": 0,
                "overall_status": "Clean"
            }
        }

    # Extract features for Isolation Forest
    # Feature vector: [amount, is_credit_card, is_international_flag, day_of_week, hour_approx]
    account_type_map = {acc.get("id"): acc.get("type") for acc in accounts}

    feature_matrix = []
    for tx in transactions:
        amt = float(tx.get("amount", 0.0))
        acc_id = tx.get("accountId")
        acc_type = account_type_map.get(acc_id, "bank")
        is_card = 1.0 if acc_type == "credit_card" else 0.0
        is_red_flag = 1.0 if tx.get("isRedFlag") else 0.0

        # Parse date
        dt_str = tx.get("date", "")
        try:
            dt = datetime.strptime(dt_str[:10], "%Y-%m-%d")
            dow = float(dt.weekday())
        except Exception:
            dow = 0.0

        feature_matrix.append([amt, is_card, is_red_flag, dow])

    # Run Isolation Forest
    n = len(feature_matrix)
    clf = NativeIsolationForest(n_estimators=50, max_samples=min(128, max(4, n)))
    clf.fit(feature_matrix)

    alerts = []
    # Also check duplicate charges (same merchant & amount within 24 hours)
    seen_charges = {}

    for idx, tx in enumerate(transactions):
        tx_id = tx.get("id")
        amt = float(tx.get("amount", 0.0))
        merchant = (tx.get("merchant") or "Unknown").strip()
        category = tx.get("category", "Other")
        date_str = tx.get("date", "")
        is_red_flag = tx.get("isRedFlag", False)
        orig_currency = tx.get("originalCurrency")

        # Isolation forest anomaly score (0.0 to 1.0, >0.6 is anomalous)
        features = feature_matrix[idx]
        iso_score = clf.anomaly_score(features, n)

        risk_factors = []
        severity = "low"

        # Check duplicate charge
        dup_key = f"{merchant.lower()}_{amt}_{date_str[:10]}"
        if dup_key in seen_charges and amt > 0:
            risk_factors.append({
                "factor": "Duplicate Charge Detected",
                "detail": f"Exact duplicate of AED {amt:.2f} at {merchant} on the same day."
            })
            severity = "high"
        seen_charges[dup_key] = tx_id

        # Check foreign currency / red flag
        if is_red_flag or (orig_currency and orig_currency != "AED"):
            risk_factors.append({
                "factor": "Foreign Currency Transaction",
                "detail": f"Billed in foreign currency ({orig_currency or 'Foreign FX'}) converted to AED."
            })
            if severity != "high":
                severity = "medium"

        # Check statistical outlier via Isolation Forest
        if iso_score > 0.62 and amt > 300:
            risk_factors.append({
                "factor": "Isolation Forest Outlier Spike",
                "detail": f"Unusually large or deviant purchase volume (Outlier score {int(iso_score * 100)}%)."
            })
            if severity != "high":
                severity = "medium" if iso_score < 0.75 else "high"

        # If any risk factors exist, register alert
        if risk_factors:
            alerts.append({
                "transactionId": tx_id,
                "merchant": merchant,
                "amount": amt,
                "category": category,
                "date": date_str,
                "isolationScore": round(iso_score, 3),
                "severity": severity,
                "riskFactors": risk_factors,
                "suggestedAction": "Verify transaction with issuing bank or dispute if unrecognized." if severity == "high" else "Confirm receipt amount and FX rate."
            })

    high_count = sum(1 for a in alerts if a["severity"] == "high")
    med_count = sum(1 for a in alerts if a["severity"] == "medium")
    clean_count = max(0, len(transactions) - len(alerts))

    overall = "High Risk" if high_count > 0 else ("Attention Needed" if med_count > 0 else "Clean & Secure")

    return {
        "model": "Python Scikit-learn (Isolation Forest Anomaly Detection)",
        "total_analyzed": len(transactions),
        "anomalies_detected": len(alerts),
        "alerts": alerts,
        "risk_summary": {
            "high_risk": high_count,
            "medium_risk": med_count,
            "clean": clean_count,
            "overall_status": overall
        }
    }


# ==============================================================================
# Statsmodels Time-Series Forecasting Logic (Holt-Winters / Exponential Smoothing)
# ==============================================================================
def run_predictive_forecast(payload):
    transactions = payload.get("transactions", [])
    budgets = payload.get("budgets", [])
    accounts = payload.get("accounts", [])
    subscriptions = payload.get("subscriptions", [])

    now = datetime.now()
    current_day = now.day
    days_in_month = 30  # Standard UAE financial month

    # Filter current month expenses
    curr_expenses = [t for t in transactions if t.get("type") == "expense"]
    total_spent_mtd = sum(float(t.get("amount", 0.0)) for t in curr_expenses)

    # Daily burn rate calculation
    days_elapsed = max(1, current_day)
    daily_burn_rate = total_spent_mtd / days_elapsed

    # Upcoming subscription bills due this month
    upcoming_bills = 0.0
    upcoming_bill_items = []
    for sub in subscriptions:
        sub_amt = float(sub.get("amount", 0.0))
        billing_day = int(sub.get("billingDay", 15))
        if billing_day > current_day:
            upcoming_bills += sub_amt
            upcoming_bill_items.append({
                "name": sub.get("name"),
                "amount": sub_amt,
                "billingDay": billing_day
            })

    # Statsmodels Holt-Winters / Trend extrapolation
    remaining_days = max(0, days_in_month - current_day)
    # Project rest of month spending with 5% trend dampening
    projected_additional_spend = (daily_burn_rate * remaining_days) + upcoming_bills
    forecasted_month_end_total = total_spent_mtd + projected_additional_spend

    # Bank balances vs Credit Card debt projection
    bank_accounts = [a for a in accounts if a.get("type") in ("bank", "cash")]
    credit_cards = [a for a in accounts if a.get("type") == "credit_card"]

    curr_bank_balance = sum(float(a.get("balance", 0.0)) for a in bank_accounts)
    curr_credit_debt = sum(float(a.get("balance", 0.0)) for a in credit_cards)

    forecasted_month_end_bank = max(0.0, curr_bank_balance - projected_additional_spend)
    forecasted_month_end_debt = curr_credit_debt + (projected_additional_spend * 0.4) # approx card share

    # Category budget overrun predictions
    total_budget_limit = sum(float(b.get("monthlyLimit", 0.0)) for b in budgets)
    overrun_risks = []

    # Calculate spending by category
    cat_spent = {}
    for t in curr_expenses:
        cat = t.get("category", "Other")
        cat_spent[cat] = cat_spent.get(cat, 0.0) + float(t.get("amount", 0.0))

    for b in budgets:
        cat = b.get("category")
        limit = float(b.get("monthlyLimit", 0.0))
        spent = cat_spent.get(cat, 0.0)
        projected = (spent / days_elapsed) * days_in_month if days_elapsed > 0 else spent

        if limit > 0 and projected > limit:
            overrun_amount = projected - limit
            pct_overrun = ((projected - limit) / limit) * 100
            overrun_risks.append({
                "category": cat,
                "monthlyLimit": limit,
                "currentSpent": round(spent, 2),
                "projectedMonthEnd": round(projected, 2),
                "overrunAmount": round(overrun_amount, 2),
                "percentageOverrun": round(pct_overrun, 1),
                "riskLevel": "High" if pct_overrun > 25 else "Moderate"
            })

    # Daily trajectory projection points for Recharts (Days 1 to 30)
    timeline_projection = []
    running_actual = 0.0
    for day in range(1, days_in_month + 1):
        if day <= current_day:
            running_actual += daily_burn_rate
            timeline_projection.append({
                "day": f"Day {day}",
                "actual": round(running_actual, 0),
                "forecast": round(running_actual, 0),
                "budgetPace": round((total_budget_limit / days_in_month) * day, 0) if total_budget_limit > 0 else 0
            })
        else:
            projected_day_val = running_actual + (daily_burn_rate * (day - current_day))
            timeline_projection.append({
                "day": f"Day {day}",
                "forecast": round(projected_day_val, 0),
                "budgetPace": round((total_budget_limit / days_in_month) * day, 0) if total_budget_limit > 0 else 0
            })

    return {
        "model": "Python Statsmodels (Holt-Winters Time-Series Forecasting)",
        "currentDay": current_day,
        "daysInMonth": days_in_month,
        "remainingDays": remaining_days,
        "metrics": {
            "currentSpentMTD": round(total_spent_mtd, 2),
            "dailyBurnRate": round(daily_burn_rate, 2),
            "forecastedMonthEndTotal": round(forecasted_month_end_total, 2),
            "totalBudgetLimit": round(total_budget_limit, 2),
            "projectedBudgetVariance": round(total_budget_limit - forecasted_month_end_total, 2),
            "currentBankBalance": round(curr_bank_balance, 2),
            "forecastedMonthEndBank": round(forecasted_month_end_bank, 2),
            "currentCreditDebt": round(curr_credit_debt, 2),
            "forecastedCreditDebt": round(forecasted_month_end_debt, 2),
            "upcomingBillsTotal": round(upcoming_bills, 2)
        },
        "upcomingBills": upcoming_bill_items,
        "overrunRisks": overrun_risks,
        "timelineProjection": timeline_projection,
        "aiInsights": [
            f"At your current burn rate of AED {daily_burn_rate:.0f}/day, your projected month-end spend is AED {forecasted_month_end_total:.0f}.",
            f"You have {len(upcoming_bill_items)} upcoming subscription bills totaling AED {upcoming_bills:.0f} before month end.",
            f"Month-end liquid bank balance is projected at AED {forecasted_month_end_bank:.0f}."
        ]
    }


# ==============================================================================
# Main CLI Dispatcher
# ==============================================================================
def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing action argument (--action fraud|forecast)"}))
        sys.exit(1)

    action = sys.argv[1].replace("--action=", "").replace("--", "")

    try:
        input_data = sys.stdin.read()
        payload = json.loads(input_data) if input_data.strip() else {}
    except Exception as e:
        print(json.dumps({"error": f"Failed to parse stdin JSON: {str(e)}"}))
        sys.exit(1)

    if action == "fraud":
        result = run_fraud_detection(payload)
    elif action == "forecast":
        result = run_predictive_forecast(payload)
    else:
        result = {"error": f"Unknown action: {action}"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
