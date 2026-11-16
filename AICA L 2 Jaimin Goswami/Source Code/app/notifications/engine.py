from datetime import timedelta
import json
import uuid

from app.database.events import stable_id, unpack
from app.utils.time import display_time, parse_instant, stamp, utc_now

FILTER_FIELDS = {"countries":"country", "categories":"category", "authorities":"authority", "importance":"importance", "kinds":"kind"}


class NotificationEngine:
    def __init__(self, db, clock=utc_now):
        self.db, self.clock = db, clock

    def rules(self, conn=None):
        rows = conn.execute("SELECT * FROM notification_rules").fetchall() if conn else self.db.rows("SELECT * FROM notification_rules ORDER BY name")
        result=[]
        for row in rows:
            rule=dict(row)
            for field in ("filters","offsets","triggers"):
                rule[field]=json.loads(rule[field])
            result.append(rule)
        return result

    def save_rule(self, name, filters, offsets, triggers, enabled=True, grace_seconds=300, include_samples=False, rule_id=None):
        if not name.strip():
            raise ValueError("A rule name is required")
        if any(not isinstance(v,list) for v in filters.values()):
            raise ValueError("Rule filters must contain lists")
        offsets=sorted(set(int(v) for v in offsets))
        if any(v < 1 or v > 31536000 for v in offsets):
            raise ValueError("Reminders must be between 1 second and 365 days")
        if any(v not in ("reminder","new","updated") for v in triggers):
            raise ValueError("Unknown notification trigger")
        if grace_seconds < 0:
            raise ValueError("Grace period cannot be negative")
        rule_id=rule_id or str(uuid.uuid4())
        self.db.execute("INSERT INTO notification_rules VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,enabled=excluded.enabled,filters=excluded.filters,offsets=excluded.offsets,triggers=excluded.triggers,grace_seconds=excluded.grace_seconds,include_samples=excluded.include_samples", (rule_id,name.strip(),int(enabled),json.dumps(filters),json.dumps(offsets),json.dumps(triggers),int(grace_seconds),int(include_samples),stamp(self.clock())))
        self.reconcile()
        return rule_id

    def matches(self, rule, event, conn):
        if not rule["enabled"] or (event["sample"] and not rule["include_samples"]):
            return False
        filters=rule["filters"]
        for filter_key, field in FILTER_FIELDS.items():
            wanted={str(v).casefold() for v in filters.get(filter_key,[])}
            if wanted and str(event.get(field,"")).casefold() not in wanted:
                return False
        companies=set(filters.get("companies",[]))
        watchlists=filters.get("watchlists",[])
        for watchlist in watchlists:
            companies.update(row[0] for row in conn.execute("SELECT member FROM watchlist_members WHERE watchlist_id=?", (watchlist,)))
        if companies or watchlists:
            wanted={v.casefold() for v in companies}
            if not wanted.intersection(str(event.get(k,"")).casefold() for k in ("company","symbol","isin")):
                return False
        return True

    def _job(self, conn, event, rule, trigger, generation, offset, due, expires):
        prefix="[SAMPLE] " if event["sample"] else ""
        title=f"{prefix}{event['title']}"
        zone=self.db.setting("timezone","Asia/Kolkata")
        when=event.get("scheduled_at") if trigger=="reminder" else event.get("published_at")
        body=f"{trigger.title()} · {event.get('authority') or event.get('source_id')}\n{display_time(when,zone)}"
        job_id=stable_id(event["id"],trigger,generation,offset)
        conn.execute("INSERT OR IGNORE INTO notification_jobs(id,event_id,rule_id,trigger,generation,offset_seconds,due_at,expires_at,created_at,title,body) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (job_id,event["id"],rule["id"],trigger,generation,offset,stamp(due),stamp(expires),stamp(self.clock()),title,body))
        conn.execute("UPDATE notification_jobs SET rule_id=?,due_at=?,expires_at=?,title=?,body=? WHERE id=? AND state='Pending'", (rule["id"],stamp(due),stamp(expires),title,body,job_id))
        return job_id

    def on_ingested(self, conn, event_id, action, mode):
        if mode != "live" or action not in ("inserted","updated"):
            return
        event=unpack(conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone())
        if action=="inserted" and (not event.get("published_at") or event["status"] not in ("Published","Updated")):
            return
        trigger="new" if action=="inserted" else "updated"
        now=self.clock()
        for rule in self.rules(conn):
            if trigger in rule["triggers"] and self.matches(rule,event,conn):
                self._job(conn,event,rule,trigger,str(event["revision"]),0,now,now+timedelta(seconds=rule["grace_seconds"]))

    def reconcile(self):
        now=self.clock()
        with self.db.transaction() as conn:
            conn.execute("UPDATE notification_jobs SET state='Expired',last_error='Missed while stopped, asleep or delayed; grace period elapsed' WHERE state='Pending' AND expires_at<?", (stamp(now),))
            rules=self.rules(conn)
            desired=set()
            events=[unpack(r) for r in conn.execute("SELECT * FROM events WHERE scheduled_at IS NOT NULL")]
            for event in events:
                release=parse_instant(event["scheduled_at"])
                if not release or release<=now or not event["date_confirmed"] or event["status"] not in ("Scheduled","Updated") or event.get("actual") is not None:
                    continue
                for rule in rules:
                    if "reminder" not in rule["triggers"] or not self.matches(rule,event,conn):
                        continue
                    for offset in rule["offsets"]:
                        due=release-timedelta(seconds=offset)
                        expires=min(release,due+timedelta(seconds=rule["grace_seconds"]))
                        if expires < now:
                            continue
                        job=self._job(conn,event,rule,"reminder",event["scheduled_at"],offset,due,expires)
                        desired.add(job)
                        conn.execute("UPDATE notification_jobs SET state='Pending',rule_id=? WHERE id=? AND state IN ('Cancelled','Superseded') AND due_at>?", (rule["id"],job,stamp(now)))
            pending=conn.execute("SELECT * FROM notification_jobs WHERE state='Pending'").fetchall()
            for job in pending:
                if job["trigger"]=="reminder" and job["id"] not in desired:
                    conn.execute("UPDATE notification_jobs SET state='Cancelled',last_error='Schedule, status or matching preferences changed' WHERE id=?", (job["id"],))
                elif job["trigger"] in ("new","updated"):
                    event=unpack(conn.execute("SELECT * FROM events WHERE id=?", (job["event_id"],)).fetchone())
                    if not any(job["trigger"] in r["triggers"] and self.matches(r,event,conn) for r in rules):
                        conn.execute("UPDATE notification_jobs SET state='Suppressed',last_error='No enabled rule matches' WHERE id=?", (job["id"],))

    def recover(self):
        # Do not replay a toast when a process died after OS submission but before DB acknowledgement.
        self.db.execute("UPDATE notification_jobs SET state='Uncertain',last_error='Application stopped during dispatch; visible delivery is unknown' WHERE state='Dispatching'")
        self.reconcile()

    def dispatch(self, sink, maximum=5):
        now=self.clock()
        with self.db.transaction() as conn:
            conn.execute("UPDATE notification_jobs SET state='Expired',last_error='Reminder missed while stopped, asleep, delayed or offline' WHERE state='Pending' AND expires_at<?", (stamp(now),))
            jobs=[dict(r) for r in conn.execute("SELECT * FROM notification_jobs WHERE state='Pending' AND due_at<=? ORDER BY due_at LIMIT ?", (stamp(now),maximum))]
            for job in jobs:
                conn.execute("UPDATE notification_jobs SET state='Dispatching',attempts=attempts+1 WHERE id=?", (job["id"],))
        count=0
        for job in jobs:
            try:
                sink.send(job)
                state,detail="Submitted","Submitted to desktop notification service; visibility depends on Windows settings"
                count+=1
            except Exception as exc:
                state,detail="Failed",str(exc)[:500]
            with self.db.transaction() as conn:
                conn.execute("UPDATE notification_jobs SET state=?,sent_at=?,last_error=? WHERE id=?", (state,stamp(now) if state=="Submitted" else None,"" if state=="Submitted" else detail,job["id"]))
                conn.execute("INSERT INTO notification_attempts(job_id,attempted_at,outcome,detail) VALUES(?,?,?,?)", (job["id"],stamp(now),state,detail))
        return count

    def opened(self, job_id):
        self.db.execute("UPDATE notification_jobs SET opened_at=? WHERE id=?", (stamp(self.clock()),job_id))

    def history(self):
        return self.db.rows("SELECT * FROM notification_jobs ORDER BY created_at DESC LIMIT 1000")

