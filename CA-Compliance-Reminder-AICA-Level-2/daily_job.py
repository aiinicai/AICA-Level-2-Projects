"""Run this file from Windows Task Scheduler once every morning."""
from app import init_db, process_due_reminders

if __name__ == "__main__":
    init_db()
    result = process_due_reminders(send_emails=True, create_events=True)
    print("Compliance reminder job finished:", result)
