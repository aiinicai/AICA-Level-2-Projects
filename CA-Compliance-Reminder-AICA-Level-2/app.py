import os, sqlite3, base64, json
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from email.utils import formataddr
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
load_dotenv()
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "reminders.db")
TOKEN_PATH = os.path.join(APP_DIR, "token.json")
CLIENT_SECRET_PATH = os.path.join(APP_DIR, "credentials.json")

# Minimum practical scopes for this app.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-local-secret")

def config_value(name, default=""):
    return os.environ.get(name, default).strip()

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT, client_name TEXT, compliance_type TEXT,
            period TEXT, due_date TEXT, action TEXT, status TEXT,
            detail TEXT, created_at TEXT
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS sent_reminders (
            reminder_key TEXT PRIMARY KEY,
            sent_at TEXT,
            message_id TEXT
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            event_key TEXT PRIMARY KEY,
            event_id TEXT,
            created_at TEXT
        )""")

def log_activity(client, action, status, detail=""):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """INSERT INTO activity
            (client_id, client_name, compliance_type, period, due_date, action, status, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (client.get("client_id",""), client.get("client_name",""),
             client.get("compliance_type",""), client.get("period",""),
             client.get("due_date",""), action, status, str(detail)[:1000],
             datetime.now().isoformat(timespec="seconds"))
        )

def get_credentials():
    if not os.path.exists(CLIENT_SECRET_PATH):
        raise RuntimeError(
            "credentials.json was not found. Download your OAuth Desktop App credentials "
            "from Google Cloud Console and save the file as credentials.json in this folder."
        )
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds

def google_services():
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
    calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return sheets, gmail, calendar

def read_clients():
    spreadsheet_id = config_value("GOOGLE_SHEET_ID")
    sheet_range = config_value("GOOGLE_SHEET_RANGE", "Sheet1!A1:H")
    if not spreadsheet_id:
        raise RuntimeError("Set GOOGLE_SHEET_ID in your environment or .env file.")
    sheets, _, _ = google_services()
    response = sheets.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=sheet_range
    ).execute()
    rows = response.get("values", [])
    if not rows:
        return []
    headers = [str(x).strip().lower() for x in rows[0]]
    required = ["client id", "client name", "email address", "compliance type",
                "return period / financial year", "due date", "remarks", "active"]
    missing = [h for h in required if h not in headers]
    if missing:
        raise RuntimeError("Google Sheet is missing these column headers: " + ", ".join(missing))
    result = []
    for row in rows[1:]:
        row = row + [""] * (len(headers) - len(row))
        item = {headers[i]: str(row[i]).strip() for i in range(len(headers))}
        active = item.get("active", "").lower() in ("yes", "y", "true", "1", "active")
        due = item.get("due date", "")
        try:
            due = date.fromisoformat(due).isoformat()
        except ValueError:
            # Ignore invalid/blank dates, but log them for visibility.
            log_activity({
                "client_id": item.get("client id",""),
                "client_name": item.get("client name",""),
                "compliance_type": item.get("compliance type",""),
                "period": item.get("return period / financial year",""),
                "due_date": due
            }, "Validate due date", "ERROR", "Due Date must be YYYY-MM-DD.")
            continue
        result.append({
            "client_id": item.get("client id",""),
            "client_name": item.get("client name",""),
            "email": item.get("email address",""),
            "compliance_type": item.get("compliance type",""),
            "period": item.get("return period / financial year",""),
            "due_date": due,
            "remarks": item.get("remarks",""),
            "active": active
        })
    return [x for x in result if x["active"]]

def reminder_key(client):
    return "|".join([client.get("client_id",""), client["compliance_type"],
                    client["period"], client["due_date"]])

def send_email(gmail, client, test_mode=False, test_address=None):
    recipient = test_address or client["email"]
    if not recipient or "@" not in recipient:
        raise ValueError("Client email address is missing or invalid.")
    due = date.fromisoformat(client["due_date"]).strftime("%d-%m-%Y")
    subject = f"Reminder: {client['compliance_type']} due on {due}"
    body = f"""Dear {client['client_name']},

This is a polite reminder that the following compliance is due tomorrow.

Compliance: {client['compliance_type']}
Return period / Financial year: {client['period']}
Due date: {due}
{("Remarks: " + client['remarks']) if client.get('remarks') else ""}

Please arrange to complete the applicable filing/payment by the due date. Kindly contact our office if you have already completed it or require any clarification.

Regards,
CA Office
"""
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = recipient
    message["subject"] = ("TEST - " if test_mode else "") + subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    sent = gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent.get("id", "")

def ensure_calendar_event(calendar, client):
    key = reminder_key(client)
    with sqlite3.connect(DB_PATH) as con:
        existing = con.execute("SELECT event_id FROM calendar_events WHERE event_key=?", (key,)).fetchone()
    if existing:
        return "Already exists"
    due = date.fromisoformat(client["due_date"])
    end = due + timedelta(days=1)
    summary = f"{client['compliance_type']} - {client['client_name']}"
    description = (
        f"Client: {client['client_name']}\n"
        f"Compliance: {client['compliance_type']}\n"
        f"Return period / Financial year: {client['period']}\n"
        f"Due date: {due.strftime('%d-%m-%Y')}\n"
        f"Client ID: {client['client_id']}\n"
        f"Remarks: {client.get('remarks','')}"
    )
    event = {
        "summary": summary,
        "description": description,
        "start": {"date": due.isoformat()},
        "end": {"date": end.isoformat()},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 1440}]}
    }
    created = calendar.events().insert(calendarId="primary", body=event).execute()
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT OR IGNORE INTO calendar_events(event_key,event_id,created_at) VALUES(?,?,?)",
                    (key, created.get("id",""), datetime.now().isoformat(timespec="seconds")))
    return created.get("id", "Created")

def process_due_reminders(send_emails=True, create_events=True, only_tomorrow=False):
    clients = read_clients()
    _, gmail, calendar = google_services()
    today = date.today()
    counts = {"checked": 0, "sent": 0, "events": 0, "skipped": 0, "errors": 0}
    for client in clients:
        counts["checked"] += 1
        try:
            due = date.fromisoformat(client["due_date"])
            if create_events:
                try:
                    result = ensure_calendar_event(calendar, client)
                    if result != "Already exists":
                        counts["events"] += 1
                        log_activity(client, "Create calendar event", "SUCCESS", result)
                except Exception as exc:
                    counts["errors"] += 1
                    log_activity(client, "Create calendar event", "ERROR", exc)
            if send_emails and due == today + timedelta(days=1):
                key = reminder_key(client)
                with sqlite3.connect(DB_PATH) as con:
                    sent_before = con.execute("SELECT 1 FROM sent_reminders WHERE reminder_key=?", (key,)).fetchone()
                if sent_before:
                    counts["skipped"] += 1
                    continue
                try:
                    message_id = send_email(gmail, client)
                    with sqlite3.connect(DB_PATH) as con:
                        con.execute("INSERT OR IGNORE INTO sent_reminders(reminder_key,sent_at,message_id) VALUES(?,?,?)",
                                    (key, datetime.now().isoformat(timespec="seconds"), message_id))
                    counts["sent"] += 1
                    log_activity(client, "Send reminder", "SUCCESS", "Gmail message ID: " + message_id)
                except Exception as exc:
                    counts["errors"] += 1
                    log_activity(client, "Send reminder", "ERROR", exc)
        except Exception as exc:
            counts["errors"] += 1
            log_activity(client, "Process compliance", "ERROR", exc)
    return counts

def dashboard_data():
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        activity = [dict(r) for r in con.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 100")]
        sent = con.execute("SELECT COUNT(*) FROM sent_reminders").fetchone()[0]
        events = con.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
    try:
        clients = read_clients()
        today = date.today()
        upcoming = [c for c in clients if today <= date.fromisoformat(c["due_date"]) <= today + timedelta(days=7)]
        tomorrow = [c for c in clients if date.fromisoformat(c["due_date"]) == today + timedelta(days=1)]
        return {"clients": clients, "upcoming": sorted(upcoming, key=lambda x: x["due_date"]),
                "tomorrow": tomorrow, "sent": sent, "events": events, "activity": activity, "error": ""}
    except Exception as exc:
        return {"clients": [], "upcoming": [], "tomorrow": [], "sent": sent,
                "events": events, "activity": activity, "error": str(exc)}

@app.route("/")
def index():
    init_db()
    return render_template("index.html", data=dashboard_data(), today=date.today().isoformat())

@app.post("/sync")
def sync():
    try:
        clients = read_clients()
        flash(f"Google Sheet synchronised. Active valid compliance rows: {len(clients)}.", "success")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("index"))

@app.post("/process")
def process():
    try:
        result = process_due_reminders(send_emails=True, create_events=True)
        flash(f"Processing complete: {result}", "success")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("index"))

@app.post("/events")
def events():
    try:
        clients = read_clients()
        _, _, calendar = google_services()
        created = 0
        for client in clients:
            try:
                result = ensure_calendar_event(calendar, client)
                if result != "Already exists":
                    created += 1
                    log_activity(client, "Create calendar event", "SUCCESS", result)
            except Exception as exc:
                log_activity(client, "Create calendar event", "ERROR", exc)
        flash(f"Calendar processing complete. New events created: {created}.", "success")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("index"))

@app.post("/test-email")
def test_email():
    try:
        address = request.form.get("test_address", "").strip()
        if not address or "@" not in address:
            raise ValueError("Enter a valid test email address.")
        clients = read_clients()
        if not clients:
            raise ValueError("No active valid compliance rows found in Google Sheet.")
        _, gmail, _ = google_services()
        client = clients[0]
        send_email(gmail, client, test_mode=True, test_address=address)
        log_activity(client, "Send test email", "SUCCESS", "Sent to " + address)
        flash(f"Test email sent to {address}.", "success")
    except Exception as exc:
        flash(str(exc), "danger")
    return redirect(url_for("index"))

@app.route("/export")
def export():
    import csv
    from flask import Response
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = [dict(r) for r in con.execute("SELECT * FROM activity ORDER BY id DESC")]
    import io
    output = io.StringIO()
    fields = ["id","client_id","client_name","compliance_type","period","due_date","action","status","detail","created_at"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=reminder_history.csv"})

if __name__ == "__main__":
    init_db()
    # Local-only development server. Do not expose this directly to the internet.
    app.run(host="127.0.0.1", port=5000, debug=False)
