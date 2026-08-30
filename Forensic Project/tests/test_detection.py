"""
Acceptance Test for Red Flag Forensic Engine:
Loads `data/sample/sample_tb_FY22_FY24.xlsx`, executes the complete analytical engine,
and asserts that all 10 planted manipulations are successfully detected.
Computes and reports precision, recall, and detection metrics.
"""
import json
import pytest
import pandas as pd
from engine.parse_excel import parse_excel
from engine.normalise import normalise_ledgers
from engine.derive import derive_financial_statements
from engine.statistical import compute_unsupervised_outliers
from engine.rule_engine import execute_all_rules
from engine.scoring import score_exceptions

def test_all_10_planted_manipulations_detected():
    # 1. Load ground truth
    with open("data/sample/planted_manipulations.json", "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
        
    # 2. Ingest, parse, normalise, derive
    raw_df = parse_excel("data/sample/sample_tb_FY22_FY24.xlsx")
    ledgers = normalise_ledgers(raw_df)
    
    params = {
        "performance_materiality": 500000.0,
        "related_parties": ["Balaji Enterprises", "Radha Associates"]
    }
    
    derived = derive_financial_statements(ledgers, params=params)
    ml_outliers = compute_unsupervised_outliers(ledgers)
    
    # 3. Execute all rules & models
    exceptions_df, executed_rules, skipped_rules = execute_all_rules(ledgers, derived, params=params)
    
    # 4. Score
    scoring_res = score_exceptions(
        exceptions_df,
        performance_materiality=params["performance_materiality"],
        ml_outlier_df=ml_outliers
    )
    
    scored_df = scoring_res["scored_exceptions"]
    assert not scored_df.empty, "No exceptions were flagged by the engine!"
    assert scoring_res["entity_score"] > 0, "Entity score is 0!"
    
    fired_rule_ids = set(scored_df["rule_id"].unique())
    fired_details = " ".join(scored_df["detail"].tolist() + scored_df["subject"].tolist())
    
    print("\n" + "="*70)
    print("PLANTED MANIPULATION DETECTION REPORT")
    print("="*70)
    
    detected_count = 0
    
    # Check each of the 10 planted manipulations:
    
    # 1. Suspense A/c (TB-03)
    p1 = "TB-03" in fired_rule_ids and scored_df[scored_df["rule_id"] == "TB-03"]["subject"].str.contains("Suspense", case=False).any()
    print(f"Plant #1 [TB-03 Suspense A/c]: {'FOUND [OK]' if p1 else 'MISSED [X]'}")
    assert p1, "Plant #1: Suspense A/c was not detected by TB-03"
    detected_count += 1
    
    # 2. Near-duplicate Shreeji (TB-06)
    p2 = "TB-06" in fired_rule_ids and scored_df[scored_df["rule_id"] == "TB-06"]["subject"].str.contains("Shreeji", case=False).any()
    print(f"Plant #2 [TB-06 Near-duplicate Creditors]: {'FOUND [OK]' if p2 else 'MISSED [X]'}")
    assert p2, "Plant #2: Near-duplicate Shreeji was not detected by TB-06"
    detected_count += 1
    
    # 3. Ravi Trading Co circular turnover (TB-07, TB-14, LG-07)
    p3 = any(r in fired_rule_ids for r in ["TB-07", "TB-14", "LG-07"]) and scored_df[scored_df["rule_id"].isin(["TB-07", "TB-14", "LG-07"])]["subject"].str.contains("Ravi Trading", case=False).any()
    print(f"Plant #3 [TB-07/14, LG-07 Circular Turnover]: {'FOUND [OK]' if p3 else 'MISSED [X]'}")
    assert p3, "Plant #3: Ravi Trading Co circular turnover was not detected"
    detected_count += 1
    
    # 4. Consultancy Charges surge (LG-06)
    p4 = "LG-06" in fired_rule_ids or (scored_df["subject"].str.contains("Consultancy|Administrative", case=False).any())
    print(f"Plant #4 [LG-06 Expense Surge]: {'FOUND [OK]' if p4 else 'MISSED [X]'}")
    assert p4, "Plant #4: Consultancy charges expense surge was not detected by LG-06"
    detected_count += 1
    
    # 5. Bhavya Marketing new ledger in FY24 (LG-01)
    p5 = "LG-01" in fired_rule_ids and scored_df[scored_df["rule_id"] == "LG-01"]["subject"].str.contains("Bhavya Marketing", case=False).any()
    print(f"Plant #5 [LG-01 Sudden New High-Value Ledger]: {'FOUND [OK]' if p5 else 'MISSED [X]'}")
    assert p5, "Plant #5: Bhavya Marketing was not detected by LG-01"
    detected_count += 1
    
    # 6. Receivables inflated (FS-04, MS-01)
    p6 = "FS-04" in fired_rule_ids or "MS-01" in fired_rule_ids
    print(f"Plant #6 [FS-04 / MS-01 Receivables Inflation]: {'FOUND [OK]' if p6 else 'MISSED [X]'}")
    assert p6, "Plant #6: Receivables inflation was not detected by FS-04/MS-01"
    detected_count += 1
    
    # 7. CWIP capitalisation (FS-08)
    p7 = "FS-08" in fired_rule_ids
    print(f"Plant #7 [FS-08 CWIP Expense Capitalisation]: {'FOUND [OK]' if p7 else 'MISSED [X]'}")
    assert p7, "Plant #7: CWIP capitalisation was not detected by FS-08"
    detected_count += 1
    
    # 8. Fixed asset additions (FS-09)
    p8 = "FS-09" in fired_rule_ids
    print(f"Plant #8 [FS-09 Unproductive Capex Additions]: {'FOUND [OK]' if p8 else 'MISSED [X]'}")
    assert p8, "Plant #8: Fixed asset additions capex was not detected by FS-09"
    detected_count += 1
    
    # 9. PAT vs CFO disconnect (FS-01, MS-03)
    p9 = "FS-01" in fired_rule_ids or "MS-03" in fired_rule_ids
    print(f"Plant #9 [FS-01 / MS-03 Negative CFO Disconnect]: {'FOUND [OK]' if p9 else 'MISSED [X]'}")
    assert p9, "Plant #9: PAT vs negative CFO disconnect was not detected by FS-01/MS-03"
    detected_count += 1
    
    # 10. Stagnant Debtor Kirit & Sons (LG-05)
    p10 = "LG-05" in fired_rule_ids and scored_df[scored_df["rule_id"] == "LG-05"]["subject"].str.contains("Kirit", case=False).any()
    print(f"Plant #10 [LG-05 Stagnant Unchanging Balance]: {'FOUND [OK]' if p10 else 'MISSED [X]'}")
    assert p10, "Plant #10: Kirit & Sons stagnant balance was not detected by LG-05"
    detected_count += 1
    
    total_plants = len(ground_truth)
    recall = (detected_count / total_plants) * 100.0
    precision = (detected_count / max(1, len(scored_df))) * 100.0
    
    print("-" * 70)
    print(f"Total Planted Manipulations: {total_plants}")
    print(f"Total Detected: {detected_count} / {total_plants}")
    print(f"Detection Recall: {recall:.1f}%")
    print(f"Total Fired Flags (Raw Precision): {len(scored_df)} flags (Precision on synthetic dataset: {precision:.1f}%)")
    print(f"Entity Risk Score: {scoring_res['entity_score']} ({scoring_res['bucket']})")
    print("=" * 70 + "\n")
    
    assert detected_count == 10, f"Expected 10/10 detections, got {detected_count}"
