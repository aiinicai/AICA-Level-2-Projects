"""
app.py - Task Tracker for a CA office (AICA Level 2 Project)

A Flask web application. Python does the work:
    database.py : stores sections, people and tasks in SQLite
    cycles.py   : works out the current cycle, due date and status of each task
    reports.py  : CSV export and the "Needs Attention" PDF report
and the page in static/index.html is the screen the user sees. The page talks
to this file through the small JSON API below.

Run with:   python app.py        (the browser opens automatically)
"""

import sys
import threading
import webbrowser
from datetime import date

from flask import Flask, Response, jsonify, request

import cycles
import database as db
import reports
from sample_data import load_sample_data

HOST, PORT = "127.0.0.1", 5000

app = Flask(__name__, static_folder="static", static_url_path="/static")


def describe(task, today):
    """Add the calculated status (from cycles.py) to a task before sending it."""
    i = cycles.info(task, today)
    c = i["c"]
    task["_info"] = {
        "c": {"key": c["key"], "label": c["label"],
              "deadline": c["deadline"].isoformat() if c["deadline"] else None,
              "start": c["start"].isoformat() if c["start"] else None},
        "done": i["done"], "state": i["state"], "days": i["days"],
        "free": i["free"], "checked": i["checked"],
        "dueText": cycles.due_text(task, today),
        "pill": cycles.pill_text(task, i, today),
    }
    task["_hist"] = {key: cycles.cycle_key_label(key) for key in task.get("history", {})}
    return task


def clean(doc):
    """Drop the calculated fields (names starting with '_') sent back by the page."""
    return {key: value for key, value in (doc or {}).items() if not key.startswith("_")}


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
@app.get("/")
def home():
    return app.send_static_file("index.html")


# --------------------------------------------------------------------------
# API - reading
# --------------------------------------------------------------------------
@app.get("/api/state")
def state():
    today = date.today()
    return jsonify(today=today.isoformat(),
                   sections=db.get_sections(),
                   people=db.get_people(),
                   tasks=[describe(task, today) for task in db.get_tasks()])


@app.post("/api/preview")
def preview():
    """Due-date hint shown in the task form while the repeat rule is being set."""
    return jsonify(html=cycles.due_preview(clean(request.get_json(silent=True))))


# --------------------------------------------------------------------------
# API - writing.  PUT replaces the whole record, PATCH changes some fields.
# --------------------------------------------------------------------------
@app.route("/api/tasks/<task_id>", methods=["PUT", "PATCH"])
def write_task(task_id):
    db.save_task(task_id, clean(request.get_json(silent=True)), replace=request.method == "PUT")
    return jsonify(ok=True)


@app.delete("/api/tasks/<task_id>")
def remove_task(task_id):
    db.delete_task(task_id)
    return jsonify(ok=True)


@app.route("/api/sections/<section_id>", methods=["PUT", "PATCH"])
def write_section(section_id):
    db.save_section(section_id, clean(request.get_json(silent=True)),
                    replace=request.method == "PUT")
    return jsonify(ok=True)


@app.delete("/api/sections/<section_id>")
def remove_section(section_id):
    db.delete_section(section_id)
    return jsonify(ok=True)


@app.put("/api/people")
def write_people():
    db.set_people((request.get_json(silent=True) or {}).get("names", []))
    return jsonify(ok=True)


# --------------------------------------------------------------------------
# Exports
# --------------------------------------------------------------------------
def download(data, mimetype, filename):
    return Response(data, mimetype=mimetype,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/export.csv")
def export_csv():
    data = reports.tasks_csv(db.get_sections(), db.get_tasks())
    return download(data.encode("utf-8"), "text/csv", f"Task Tracker {date.today()}.csv")


@app.get("/api/report.pdf")
def report_pdf():
    today = date.today()
    data = reports.needs_attention_pdf(db.get_sections(), db.get_tasks(), today)
    name = f"Needs Attention {cycles.fmt(today, today, with_year=True)}.pdf"
    return download(data, "application/pdf", name)


# --------------------------------------------------------------------------
# Start-up
# --------------------------------------------------------------------------
def prepare_database():
    """Create the database; on the very first run fill it with the sample data."""
    first_run = not db.DB_PATH.exists()
    db.init_db()
    if first_run:
        load_sample_data()


if __name__ == "__main__":
    prepare_database()
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, webbrowser.open, args=[f"http://{HOST}:{PORT}"]).start()
    print(f"Task Tracker is running at http://{HOST}:{PORT}   (press Ctrl+C to stop)")
    app.run(host=HOST, port=PORT, debug=False)
