import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import requests
from typing import Dict, Any, List, Tuple
import database as db

def get_smtp_config():
    return {
        "host": db.get_setting("smtp_host", "smtp.gmail.com"),
        "port": int(db.get_setting("smtp_port", "587")),
        "user": db.get_setting("smtp_user", ""),
        "password": db.get_setting("smtp_pass", ""),
        "sender": db.get_setting("smtp_sender", "audit-desk@ca-firm.com"),
        "partner_email": db.get_setting("partner_email", "partner@ca-firm.com"),
        "inactivity_days": int(db.get_setting("inactivity_days", "3")),
        "whatsapp_api_url": db.get_setting("whatsapp_api_url", ""),
        "whatsapp_api_key": db.get_setting("whatsapp_api_key", ""),
    }

def send_smtp_email(to_email: str, subject: str, body_text: str, body_html: str = "") -> Tuple[bool, str]:
    config = get_smtp_config()
    
    # If SMTP is not configured with credentials, log and simulate
    if not config["user"] or not config["password"]:
        return True, "Simulation: Email logged (SMTP credentials not configured in Settings)"
        
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["sender"]
        msg["To"] = to_email
        
        part1 = MIMEText(body_text, "plain")
        msg.attach(part1)
        if body_html:
            part2 = MIMEText(body_html, "html")
            msg.attach(part2)
            
        if config["port"] == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(config["host"], config["port"], context=context) as server:
                server.login(config["user"], config["password"])
                server.sendmail(config["sender"], to_email, msg.as_string())
        else:
            with smtplib.SMTP(config["host"], config["port"]) as server:
                server.starttls()
                server.login(config["user"], config["password"])
                server.sendmail(config["sender"], to_email, msg.as_string())
                
        return True, "Email sent successfully via SMTP"
    except Exception as e:
        return False, f"SMTP Error: {str(e)}"

def send_whatsapp_or_sms(phone: str, message: str) -> Tuple[bool, str]:
    config = get_smtp_config()
    if not config["whatsapp_api_url"]:
        return True, "Simulation: WhatsApp/SMS notification logged (API URL not configured in Settings)"
        
    try:
        headers = {}
        if config["whatsapp_api_key"]:
            headers["Authorization"] = f"Bearer {config['whatsapp_api_key']}"
            
        payload = {
            "to": phone,
            "message": message,
            "text": message
        }
        resp = requests.post(config["whatsapp_api_url"], json=payload, headers=headers, timeout=10)
        if resp.status_code in [200, 201, 202]:
            return True, f"WhatsApp/SMS dispatched: HTTP {resp.status_code}"
        else:
            return False, f"WhatsApp/SMS gateway returned status {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, f"Gateway Error: {str(e)}"

def run_automated_reminders(trigger_mode: str = "Live") -> List[Dict[str, Any]]:
    """
    Executes Condition 1, Condition 2, Condition 3 reminder scans.
    """
    config = get_smtp_config()
    inactivity_threshold = config["inactivity_days"]
    partner_email = config["partner_email"]
    
    today = datetime.date.today()
    assignments = db.get_all_assignments("Partner")
    results = []
    
    closed_statuses = ["Closed", "Report Submitted"]
    
    for a in assignments:
        status = a.get("audit_status", "")
        if status in closed_statuses:
            continue
            
        borrower = a.get("borrower_name", "Unknown Borrower")
        bank = a.get("bank_name", "Unknown Bank")
        team_person = a.get("team_person_name", "Team Member")
        team_phone = a.get("team_person_number", "")
        team_email = f"{team_person.lower().replace(' ', '.')}@ca-firm.com"
        
        # Check Condition 1: Inactivity (No status update for X days)
        last_update_str = a.get("last_status_update") or a.get("updated_at") or a.get("created_at")
        days_inactive = 0
        if last_update_str:
            try:
                last_dt = datetime.datetime.strptime(last_update_str[:19], "%Y-%m-%d %H:%M:%S")
                days_inactive = (datetime.datetime.now() - last_dt).days
            except Exception:
                pass
                
        if days_inactive >= inactivity_threshold:
            subject = f"⚠️ Action Required: Update Status for Stock Audit - {borrower} ({bank})"
            msg_text = (
                f"Dear {team_person},\n\n"
                f"The status of Stock Audit Assignment - '{borrower}' ({bank}) has not been updated since {last_update_str[:10] if last_update_str else 'several days'}.\n\n"
                f"Current Status: {status}\n"
                f"Target Visit Date: {a.get('target_visit_date') or 'Not Specified'}\n"
                f"Report Target Date: {a.get('report_target_date') or 'Not Specified'}\n\n"
                f"Please log into the Audit Tracker and update the latest status immediately.\n\n"
                f"Regards,\nAudit Management Desk\nCA Firm Portal"
            )
            success, msg_resp = send_smtp_email(team_email, subject, msg_text)
            status_tag = "Sent" if success else "Failed"
            db.log_reminder(a["id"], borrower, team_person, team_email, team_phone, "Inactivity", msg_text, "Email", status_tag)
            
            # Also trigger WhatsApp/SMS
            if team_phone:
                wa_msg = f"Stock Audit Alert: Status for {borrower} ({bank}) has not been updated for {days_inactive} days. Please update on portal."
                send_whatsapp_or_sms(team_phone, wa_msg)
                
            results.append({
                "assignment_id": a["id"],
                "borrower": borrower,
                "bank": bank,
                "type": f"Inactivity Alert ({days_inactive} days without update)",
                "recipient": f"{team_person} ({team_email})",
                "status": status_tag,
                "detail": msg_resp
            })
            
        # Check Condition 2 & 3: Target Dates
        report_target_str = a.get("report_target_date")
        if report_target_str:
            try:
                target_date = datetime.datetime.strptime(report_target_str[:10], "%Y-%m-%d").date()
                delta_days = (target_date - today).days
                
                # Condition 2: Upcoming in <= 3 days
                if 0 <= delta_days <= 3:
                    subject = f"⏳ Upcoming Deadline: Report Due in {delta_days} Days - {borrower} ({bank})"
                    msg_text = (
                        f"Dear {team_person},\n\n"
                        f"This is a reminder that the Report Target Date for '{borrower}' ({bank}) is approaching on {report_target_str}.\n\n"
                        f"Days Remaining: {delta_days} day(s)\n"
                        f"Current Audit Status: {status}\n"
                        f"Pending Documents: {a.get('pending_details') or 'None'}\n\n"
                        f"Please expedite the report preparation and schedule review with the Partner.\n\n"
                        f"Regards,\nCA Firm Portal"
                    )
                    success, msg_resp = send_smtp_email(team_email, subject, msg_text)
                    status_tag = "Sent" if success else "Failed"
                    db.log_reminder(a["id"], borrower, team_person, team_email, team_phone, "Upcoming Deadline", msg_text, "Email", status_tag)
                    results.append({
                        "assignment_id": a["id"],
                        "borrower": borrower,
                        "bank": bank,
                        "type": f"Upcoming Deadline ({delta_days} days left)",
                        "recipient": f"{team_person} ({team_email})",
                        "status": status_tag,
                        "detail": msg_resp
                    })
                    
                # Condition 3: Overdue deadline crossed -> Escalate to Partner
                elif delta_days < 0:
                    overdue_days = abs(delta_days)
                    subject = f"🚨 ESCALATION: Report Overdue by {overdue_days} Days - {borrower} ({bank})"
                    msg_text = (
                        f"PARTNER ESCALATION NOTICE\n\n"
                        f"Stock Audit Assignment for '{borrower}' ({bank}) is OVERDUE.\n\n"
                        f"Assigned Auditor: {team_person}\n"
                        f"Target Report Date: {report_target_str}\n"
                        f"Overdue By: {overdue_days} day(s)\n"
                        f"Current Status: {status}\n"
                        f"Remarks / Delay Reason: {a.get('remarks') or 'No reason provided'}\n\n"
                        f"Partner intervention required to prevent bank compliance penalties.\n\n"
                        f"Audit Management System"
                    )
                    success, msg_resp = send_smtp_email(partner_email, subject, msg_text)
                    status_tag = "Escalated" if success else "Failed"
                    db.log_reminder(a["id"], borrower, "Partner / Admin", partner_email, "", "Overdue Escalation", msg_text, "Email", status_tag)
                    results.append({
                        "assignment_id": a["id"],
                        "borrower": borrower,
                        "bank": bank,
                        "type": f"🚨 Partner Escalation (Overdue by {overdue_days} days)",
                        "recipient": f"Partner ({partner_email})",
                        "status": status_tag,
                        "detail": msg_resp
                    })
            except Exception:
                pass
                
    return results
