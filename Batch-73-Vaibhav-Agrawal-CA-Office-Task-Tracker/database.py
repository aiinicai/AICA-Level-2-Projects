"""
database.py - Data layer of the Task Tracker (SQLite).

All data lives in one file, task_tracker.db, created automatically next to
this script. The rest of the application never writes SQL; it calls the
functions below, which accept and return plain Python dictionaries.

Tables
------
sections : headings under which work is grouped (GST, TDS, Audit ...)
people   : persons who handle the work ("With" column)
tasks    : one row per task, including its repeat rule
subtasks : steps inside a task
history  : for repeating tasks, the cycles in which the task was completed
"""

import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).parent / "task_tracker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sections (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    color             TEXT NOT NULL DEFAULT 'navy',
    default_frequency TEXT NOT NULL DEFAULT 'One-time',
    sort_order        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS people (
    name       TEXT PRIMARY KEY,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
    id           TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    section_id   TEXT,
    owner        TEXT,
    tag          TEXT,
    remarks      TEXT,
    frequency    TEXT NOT NULL DEFAULT 'One-time',
    due_date     TEXT,
    due_day      INTEGER,
    due_from     INTEGER,
    due_rule     TEXT,
    due_weekday  INTEGER,
    due_q_offset INTEGER,
    status       TEXT NOT NULL DEFAULT 'open',
    done_for     TEXT,
    done_at      TEXT,
    checked_on   TEXT,
    starred      INTEGER NOT NULL DEFAULT 0,
    later        INTEGER NOT NULL DEFAULT 0,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT
);

CREATE TABLE IF NOT EXISTS subtasks (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id  TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    text     TEXT NOT NULL,
    done     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS history (
    task_id   TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    cycle_key TEXT NOT NULL,
    done_at   TEXT,
    PRIMARY KEY (task_id, cycle_key)
);
"""

# Name used by the application (left)  ->  column in the table (right)
TASK_COLUMNS = {
    "title": "title", "section": "section_id", "owner": "owner", "tag": "tag",
    "remarks": "remarks", "frequency": "frequency", "dueDate": "due_date",
    "dueDay": "due_day", "dueFrom": "due_from", "dueRule": "due_rule",
    "dueWeekday": "due_weekday", "dueQOffset": "due_q_offset", "status": "status",
    "doneFor": "done_for", "doneAt": "done_at", "checkedOn": "checked_on",
    "starred": "starred", "later": "later", "order": "sort_order",
    "createdAt": "created_at",
}
SECTION_COLUMNS = {"name": "name", "color": "color",
                   "defaultFrequency": "default_frequency", "order": "sort_order"}

# Values stored when a field is left blank
DEFAULTS = {"title": "", "frequency": "One-time", "status": "open", "starred": 0,
            "later": 0, "order": 0, "color": "navy", "defaultFrequency": "One-time",
            "name": ""}
FLAGS = ("starred", "later")            # stored as 0 / 1, used as False / True


# --------------------------------------------------------------------------
# Connection helpers
# --------------------------------------------------------------------------
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the tables if they do not exist yet."""
    with closing(connect()) as conn, conn:
        conn.executescript(SCHEMA)


def _to_row(doc, columns):
    """Application dictionary -> {column: value}, only for the keys supplied."""
    row = {}
    for key, column in columns.items():
        if key in doc:
            value = doc[key]
            if value is None or value == "":
                value = DEFAULTS.get(key)
            if key in FLAGS:
                value = int(bool(value))
            row[column] = value
    return row


def _save(conn, table, columns, doc_id, doc, replace):
    """Insert or update one row. replace=True overwrites every column (blank
    ones are cleared); replace=False changes only the fields supplied."""
    exists = conn.execute(f"SELECT 1 FROM {table} WHERE id=?", (doc_id,)).fetchone()
    if replace or not exists:
        doc = {key: doc.get(key) for key in columns}
    row = _to_row(doc, columns)
    if not row:
        return
    if exists:
        assignments = ", ".join(f"{column}=?" for column in row)
        conn.execute(f"UPDATE {table} SET {assignments} WHERE id=?", (*row.values(), doc_id))
    else:
        names = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        conn.execute(f"INSERT INTO {table} (id, {names}) VALUES (?, {marks})",
                     (doc_id, *row.values()))


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
def get_sections():
    with closing(connect()) as conn:
        rows = conn.execute("SELECT * FROM sections ORDER BY sort_order, name").fetchall()
    return [{"id": r["id"], "name": r["name"], "color": r["color"],
             "defaultFrequency": r["default_frequency"], "order": r["sort_order"]}
            for r in rows]


def save_section(section_id, doc, replace=True):
    with closing(connect()) as conn, conn:
        _save(conn, "sections", SECTION_COLUMNS, section_id, doc, replace)


def delete_section(section_id):
    with closing(connect()) as conn, conn:
        conn.execute("DELETE FROM sections WHERE id=?", (section_id,))


# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------
def get_people():
    with closing(connect()) as conn:
        rows = conn.execute("SELECT name FROM people ORDER BY sort_order").fetchall()
    return [r["name"] for r in rows]


def set_people(names):
    """Replace the list of people, keeping the order given."""
    unique = list(dict.fromkeys(n.strip() for n in names if n and n.strip()))
    with closing(connect()) as conn, conn:
        conn.execute("DELETE FROM people")
        conn.executemany("INSERT INTO people (name, sort_order) VALUES (?, ?)",
                         [(name, position) for position, name in enumerate(unique)])


# --------------------------------------------------------------------------
# Tasks
# --------------------------------------------------------------------------
def get_tasks():
    """Every task as a dictionary, with its steps and completion history."""
    with closing(connect()) as conn:
        task_rows = conn.execute("SELECT * FROM tasks").fetchall()
        step_rows = conn.execute("SELECT * FROM subtasks ORDER BY task_id, position").fetchall()
        history_rows = conn.execute("SELECT * FROM history").fetchall()

    steps, history = {}, {}
    for r in step_rows:
        steps.setdefault(r["task_id"], []).append({"text": r["text"], "done": bool(r["done"])})
    for r in history_rows:
        history.setdefault(r["task_id"], {})[r["cycle_key"]] = r["done_at"]

    tasks = []
    for r in task_rows:
        task = {"id": r["id"]}
        for key, column in TASK_COLUMNS.items():
            value = r[column]
            if key in FLAGS:
                value = bool(value)
            if value is not None:
                task[key] = value
        task["subtasks"] = steps.get(r["id"], [])
        task["history"] = history.get(r["id"], {})
        tasks.append(task)
    return tasks


def save_task(task_id, doc, replace=True):
    """
    Create or change a task.
      replace=True  : the dictionary is the whole task (used for add / edit / undo)
      replace=False : only the fields supplied are changed (e.g. {'starred': True})
    """
    with closing(connect()) as conn, conn:
        _save(conn, "tasks", TASK_COLUMNS, task_id, doc, replace)

        if replace or "subtasks" in doc:
            conn.execute("DELETE FROM subtasks WHERE task_id=?", (task_id,))
            steps = [s for s in (doc.get("subtasks") or []) if str(s.get("text", "")).strip()]
            conn.executemany(
                "INSERT INTO subtasks (task_id, position, text, done) VALUES (?, ?, ?, ?)",
                [(task_id, n, s["text"].strip(), int(bool(s.get("done"))))
                 for n, s in enumerate(steps)])

        if replace or "history" in doc:
            conn.execute("DELETE FROM history WHERE task_id=?", (task_id,))
            conn.executemany(
                "INSERT INTO history (task_id, cycle_key, done_at) VALUES (?, ?, ?)",
                [(task_id, key, done_at) for key, done_at in (doc.get("history") or {}).items()])


def delete_task(task_id):
    with closing(connect()) as conn, conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))


def clear_all_data():
    with closing(connect()) as conn, conn:
        for table in ("history", "subtasks", "tasks", "sections", "people"):
            conn.execute(f"DELETE FROM {table}")


def is_empty():
    with closing(connect()) as conn:
        return conn.execute("SELECT COUNT(*) FROM sections").fetchone()[0] == 0
