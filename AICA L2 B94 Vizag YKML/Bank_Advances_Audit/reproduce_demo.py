"""Create fictional CSV/HTML working papers and one documented sample finding; no AI call."""
import json
from pathlib import Path
from audit_engine import SCHEMAS,load_audit,update_review,review_coverage,save_session,draft_prompt,dashboard
from reports import export_csv,export_html

def demo():
    root=Path(__file__).resolve().parent
    r=load_audit({k:root/'sample_data'/f'{k}_demo.csv' for k in SCHEMAS},'2026-09-30')
    update_review(r,'CC002:DP_DIFFERENCE',dict(review_status='Reviewed',disposition='Potential reporting point',reviewer='Demo auditor',
        evidence_assessment='Fictional account/sanction source and ST02 support the reported calculation inputs; actual documents are not authenticated.',
        management_response='Fictional branch response: current DP working and renewal evidence will be supplied.',
        auditor_conclusion='Bank DP 900000 differs from selected-method historical DP 705000. A 122-day-old statement prevents a current eligibility conclusion.',
        recommended_action='Obtain current statements, debtor ageing, and the sanction methodology; reperform before final reporting.',
        proposed_reporting_point='Reconcile DP to sanctioned creditor/margin methodology and current statements; branch evidence pending.'))
    review_coverage(r,'CC001','Demo auditor','Fictional account and supplied population checked under illustrative policy. Independent completeness/document authenticity remain auditor responsibilities.')
    out=root/'example_output';export_csv(r,out)
    export_html(r,out/'Fictional_Bank_Audit_Review.html');save_session(r,out/'fictional_audit_session.json')
    (out/'CC002_AI_Prompt.txt').write_text(draft_prompt(r,'CC002:DP_DIFFERENCE'),encoding='utf-8')
    (out/'dashboard.json').write_text(json.dumps(dashboard(r),default=str,indent=2),encoding='utf-8')
    print('Fictional example outputs created. No live AI call.')

if __name__=='__main__':demo()
