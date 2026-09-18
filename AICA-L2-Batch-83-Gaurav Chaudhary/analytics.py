import datetime
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import database as db

STAGE_ORDER = {
    "Not Started": 0,
    "Data Awaited from Bank": 1,
    "Data Awaited from Borrower": 2,
    "Documents Under Review": 3,
    "Visit Planned": 4,
    "Visit Completed": 5,
    "Stock Verification Completed": 6,
    "Report Preparation": 7,
    "Review Pending": 8,
    "Partner Review Completed": 9,
    "Report Submitted": 10,
    "Closed": 10,
    "Delayed": 3
}

def parse_date(date_str: Any) -> datetime.date | None:
    if not date_str or pd.isna(date_str):
        return None
    date_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(date_str[:10] if len(date_str)>=10 else date_str, fmt).date()
        except Exception:
            continue
    return None

def compute_delay_prediction(assignment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates milestone progress vs elapsed time to predict delay risk.
    """
    status = assignment.get("audit_status", "Not Started")
    if status in ["Report Submitted", "Closed"]:
        return {"risk_level": "Completed", "risk_score": 0, "prediction": "Assignment Completed", "color": "#10B981"}
        
    allotment_date = parse_date(assignment.get("allotment_date"))
    target_date = parse_date(assignment.get("report_target_date"))
    visit_target = parse_date(assignment.get("target_visit_date"))
    actual_visit = parse_date(assignment.get("actual_visit_date"))
    today = datetime.date.today()
    
    stage_num = STAGE_ORDER.get(status, 0)
    
    # If already past target date
    if target_date and today > target_date:
        overdue_days = (today - target_date).days
        return {
            "risk_level": "Critical",
            "risk_score": 95,
            "prediction": f"Overdue by {overdue_days} day(s)",
            "color": "#EF4444"
        }
        
    # Check visit target date
    if visit_target and not actual_visit and today > visit_target:
        return {
            "risk_level": "High",
            "risk_score": 80,
            "prediction": "Visit Target missed; high delay probability",
            "color": "#F97316"
        }
        
    if allotment_date and target_date:
        total_span = max((target_date - allotment_date).days, 1)
        elapsed = max((today - allotment_date).days, 0)
        time_ratio = min(elapsed / total_span, 1.0)
        expected_stage = time_ratio * 9.0
        
        lag = expected_stage - stage_num
        if lag > 3:
            return {"risk_level": "High", "risk_score": 75, "prediction": "Pacing significantly behind schedule", "color": "#EF4444"}
        elif lag > 1.5:
            return {"risk_level": "Medium", "risk_score": 50, "prediction": "Moderate risk of deadline slippage", "color": "#F59E0B"}
        else:
            return {"risk_level": "Low", "risk_score": 20, "prediction": "On track for timely submission", "color": "#10B981"}
            
    return {"risk_level": "Low", "risk_score": 25, "prediction": "In progress (insufficient timeline data)", "color": "#64748B"}

def compute_team_productivity(assignments: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Computes performance scorecard for each team member.
    """
    records = []
    members = {}
    
    for a in assignments:
        member = a.get("team_person_name") or "Unassigned"
        if member not in members:
            members[member] = {
                "Member": member,
                "Total Assigned": 0,
                "Completed On-Time": 0,
                "Completed Delayed": 0,
                "In Progress": 0,
                "Overdue": 0,
                "Total TAT Days": 0,
                "TAT Count": 0
            }
            
        m = members[member]
        m["Total Assigned"] += 1
        
        status = a.get("audit_status", "")
        allotment = parse_date(a.get("allotment_date"))
        target = parse_date(a.get("report_target_date"))
        submitted = parse_date(a.get("report_submission_date"))
        today = datetime.date.today()
        
        if status in ["Report Submitted", "Closed"]:
            if submitted and target and submitted <= target:
                m["Completed On-Time"] += 1
            else:
                m["Completed Delayed"] += 1
                
            if allotment and submitted:
                tat = (submitted - allotment).days
                m["Total TAT Days"] += max(tat, 0)
                m["TAT Count"] += 1
        else:
            m["In Progress"] += 1
            if target and today > target:
                m["Overdue"] += 1
                
    for m in members.values():
        total = m["Total Assigned"]
        on_time = m["Completed On-Time"]
        in_prog = m["In Progress"] - m["Overdue"]
        
        score = round(((on_time * 1.0 + in_prog * 0.7) / max(total, 1)) * 100, 1)
        avg_tat = round(m["Total TAT Days"] / m["TAT Count"], 1) if m["TAT Count"] > 0 else "N/A"
        
        records.append({
            "Team Member": m["Member"],
            "Total Assigned": total,
            "Completed (On-Time)": on_time,
            "Completed (Delayed)": m["Completed Delayed"],
            "In Progress": m["In Progress"],
            "Overdue Alert": m["Overdue"],
            "Avg TAT (Days)": avg_tat,
            "Productivity Score (%)": score
        })
        
    df = pd.DataFrame(records)
    if not df.empty:
        df = df.sort_values(by="Productivity Score (%)", ascending=False)
    return df

def compute_bank_turnaround_times(assignments: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Computes TAT metrics bank-wise.
    """
    bank_data = {}
    for a in assignments:
        bank = a.get("bank_name") or "Unknown Bank"
        if bank not in bank_data:
            bank_data[bank] = {
                "Bank": bank,
                "Total Audits": 0,
                "Completed": 0,
                "Pending": 0,
                "Allotment_to_Visit": [],
                "Visit_to_Report": [],
                "Total_TAT": []
            }
            
        b = bank_data[bank]
        b["Total Audits"] += 1
        status = a.get("audit_status", "")
        
        allotment = parse_date(a.get("allotment_date"))
        visit = parse_date(a.get("actual_visit_date"))
        submission = parse_date(a.get("report_submission_date"))
        
        if status in ["Report Submitted", "Closed"]:
            b["Completed"] += 1
        else:
            b["Pending"] += 1
            
        if allotment and visit and visit >= allotment:
            b["Allotment_to_Visit"].append((visit - allotment).days)
        if visit and submission and submission >= visit:
            b["Visit_to_Report"].append((submission - visit).days)
        if allotment and submission and submission >= allotment:
            b["Total_TAT"].append((submission - allotment).days)
            
    rows = []
    for b in bank_data.values():
        rows.append({
            "Bank Name": b["Bank"],
            "Total Assignments": b["Total Audits"],
            "Completed": b["Completed"],
            "Pending": b["Pending"],
            "Avg Days: Allotment to Visit": round(np.mean(b["Allotment_to_Visit"]), 1) if b["Allotment_to_Visit"] else "-",
            "Avg Days: Visit to Report": round(np.mean(b["Visit_to_Report"]), 1) if b["Visit_to_Report"] else "-",
            "Avg Overall TAT (Days)": round(np.mean(b["Total_TAT"]), 1) if b["Total_TAT"] else "-"
        })
        
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by="Total Assignments", ascending=False)
    return df

def generate_monthly_mis(assignments: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Generates monthly breakdown of allotments, completions, pending and delay counts.
    """
    rows = []
    for a in assignments:
        allotment = parse_date(a.get("allotment_date"))
        month_label = allotment.strftime("%Y-%m (%b)") if allotment else "Undated"
        status = a.get("audit_status", "")
        is_completed = (status in ["Report Submitted", "Closed"])
        
        rows.append({
            "Month": month_label,
            "Bank": a.get("bank_name", ""),
            "Status": status,
            "Is_Completed": 1 if is_completed else 0,
            "Is_Pending": 0 if is_completed else 1,
            "Is_Delayed": 1 if status == "Delayed" else 0
        })
        
    if not rows:
        return pd.DataFrame()
        
    df = pd.DataFrame(rows)
    grouped = df.groupby("Month").agg(
        Total_Allotted=('Status', 'count'),
        Completed=('Is_Completed', 'sum'),
        Pending=('Is_Pending', 'sum'),
        Delayed=('Is_Delayed', 'sum')
    ).reset_index()
    return grouped
