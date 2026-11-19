import hashlib
import json
import uuid

from app.models.events import Event
from app.services.validation import numeric
from app.utils.time import local_date, parse_instant, stamp, utc_now


def stable_id(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "finstock:" + "|".join(str(p) for p in parts)))


def unpack(row):
    result = json.loads(row["payload"])
    result.update({k: row[k] for k in ("id", "revision", "created_at", "retrieved_at", "updated_at")})
    return result


class EventRepository:
    def __init__(self, db):
        self.db = db

    def get(self, event_id):
        rows = self.db.rows("SELECT * FROM events WHERE id=?", (event_id,))
        return unpack(rows[0]) if rows else None

    def search(self, query="", filters=None, start=None, end=None, zone="Asia/Kolkata", date_basis="calendar", limit=2000, offset=0):
        filters = filters or {}
        conditions, params = [], []
        for key in ("kind", "country", "category", "importance", "authority", "status", "exchange"):
            if filters.get(key):
                conditions.append(f"{key}=?")
                params.append(filters[key])
        if filters.get("sample") is not None:
            conditions.append("sample=?")
            params.append(int(filters["sample"]))
        if filters.get("watchlist"):
            conditions.append("(symbol IN (SELECT member FROM watchlist_members WHERE watchlist_id=?) OR isin IN (SELECT member FROM watchlist_members WHERE watchlist_id=?) OR company IN (SELECT member FROM watchlist_members WHERE watchlist_id=?))")
            params.extend([filters["watchlist"]] * 3)
        if query.strip():
            conditions.append("(title LIKE ? ESCAPE '\\' OR company LIKE ? ESCAPE '\\' OR symbol LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\' OR authority LIKE ? ESCAPE '\\' OR country LIKE ? ESCAPE '\\')")
            pattern = "%" + query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            params.extend([pattern] * 6)
        sql = "SELECT * FROM events" + (" WHERE " + " AND ".join(conditions) if conditions else "")
        sort_dir = "DESC" if filters.get("period") == "Past" else "ASC"
        sql += f" ORDER BY COALESCE(scheduled_at,published_at,effective_at,deadline_at) {sort_dir}, id"
        # Timezone-aware date comparisons happen after SQLite's indexed categorical filtering.
        rows = self.db.rows(sql, params)
        result = []
        now_day = local_date(stamp(), zone)
        now_instant=utc_now()
        for row in rows:
            event = unpack(row)
            if date_basis == "all milestones":
                values = [event.get(k) for k in ("scheduled_at", "published_at", "effective_at", "deadline_at", "record_date", "ex_date")]
            elif date_basis in ("published_at", "effective_at", "deadline_at", "record_date", "ex_date"):
                values = [event.get(date_basis)]
            else:
                values = [event.get("scheduled_at") or event.get("published_at") or event.get("effective_at") or event.get("deadline_at")]
            days = [local_date(v, zone) for v in values if v]
            if start or end:
                if not any((not start or d >= start) and (not end or d <= end) for d in days):
                    continue
            period = filters.get("period")
            if period == "Past" and not any((parse_instant(v)<now_instant if len(v)>10 else v<now_day) for v in values if v):
                continue
            if period == "Today" and now_day not in days:
                continue
            if period == "Upcoming" and not any((parse_instant(v)>now_instant if len(v)>10 else v>now_day) for v in values if v):
                continue
            result.append(event)
        return result[offset:offset + limit], len(result)

    def facets(self, key):
        if key not in ("country", "category", "authority", "company", "symbol", "exchange"):
            raise ValueError("Invalid facet")
        return [r[key] for r in self.db.rows(f"SELECT DISTINCT {key} FROM events WHERE {key}!='' ORDER BY {key}")]

    def revisions(self, event_id):
        return self.db.rows("SELECT * FROM event_revisions WHERE event_id=? ORDER BY revision DESC", (event_id,))

    def sources(self, event_id):
        return self.db.rows("SELECT r.*,s.name FROM source_records r JOIN data_sources s ON r.source_id=s.id WHERE event_id=?", (event_id,))

    def history(self, event):
        if not event.get("series_key"):
            return []
        return self.db.rows("SELECT o.*,e.title,e.sample,e.scheduled_at,e.published_at FROM economic_observations o JOIN events e ON o.event_id=e.id WHERE o.series_key=? AND o.unit=? AND o.role='actual' AND o.revision=e.revision AND e.sample=? ORDER BY COALESCE(e.scheduled_at,e.published_at)", (event["series_key"],event.get("unit",""), int(event["sample"])))

    def save(self, conn, event: Event, now=None):
        now = now or stamp()
        payload = json.dumps(event.payload(), ensure_ascii=False, sort_keys=True)
        fingerprint = event.fingerprint()
        old_source = conn.execute("SELECT * FROM source_records WHERE source_id=? AND external_id=?", (event.source_id, event.external_id)).fetchone()
        if old_source and old_source["fingerprint"] == fingerprint:
            conn.execute("UPDATE source_records SET retrieved_at=?,source_updated_at=? WHERE source_id=? AND external_id=?", (now, event.source_updated_at, event.source_id, event.external_id))
            conn.execute("UPDATE events SET retrieved_at=? WHERE id=?", (now, old_source["event_id"]))
            return old_source["event_id"], "duplicate"
        event_id = old_source["event_id"] if old_source else stable_id(event.source_id, event.external_id)
        # Cross-exchange automatic grouping requires an exact supplied document digest and ISIN.
        if not old_source and event.kind == "Corporate" and event.isin and event.document_hash:
            same = conn.execute("SELECT e.id FROM events e JOIN corporate_announcements c ON e.id=c.event_id WHERE e.isin=? AND c.document_hash=? AND e.category=? AND e.reporting_period=? AND e.sample=?", (event.isin, event.document_hash, event.category, event.reporting_period, event.sample)).fetchone()
            if same:
                event_id = same["id"]
                conn.execute("INSERT INTO source_records VALUES(?,?,?,?,?,?,?,?)", (event.source_id,event.external_id,event_id,event.source_url,event.source_updated_at,now,fingerprint,payload))
                return event_id, "duplicate"
        previous = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        revision = previous["revision"] + 1 if previous else 1
        definition_id = stable_id(event.kind,event.series_key or event.indicator or event.category,event.country,event.unit)
        conn.execute("INSERT OR IGNORE INTO event_definitions VALUES(?,?,?,?)", (definition_id,event.indicator or event.category,event.kind,event.category))
        if event.kind == "Economic":
            conn.execute("INSERT OR IGNORE INTO economic_indicators VALUES(?,?,?,?,?)", (definition_id,event.country,event.authority,event.unit,event.series_key))
        values = dict(id=event_id, definition_id=definition_id)
        for key in ("kind","title","country","category","authority","company","symbol","isin","exchange","importance","status","sample","scheduled_at","published_at","effective_at","deadline_at","record_date","ex_date","date_confirmed","series_key","reporting_period"):
            values[key] = getattr(event,key)
        values.update(payload=payload,fingerprint=fingerprint,revision=revision,created_at=previous["created_at"] if previous else now,retrieved_at=now,updated_at=now)
        columns = list(values)
        updates = ",".join(f"{k}=excluded.{k}" for k in columns if k != "id")
        conn.execute(f"INSERT INTO events({','.join(columns)}) VALUES({','.join('?' for _ in columns)}) ON CONFLICT(id) DO UPDATE SET {updates}", list(values.values()))
        conn.execute("INSERT INTO source_records VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source_id,external_id) DO UPDATE SET event_id=excluded.event_id,source_url=excluded.source_url,source_updated_at=excluded.source_updated_at,retrieved_at=excluded.retrieved_at,fingerprint=excluded.fingerprint,payload=excluded.payload", (event.source_id,event.external_id,event_id,event.source_url,event.source_updated_at,now,fingerprint,payload))
        prior = json.loads(previous["payload"]) if previous else {}
        changes = [k for k,v in event.payload().items() if prior.get(k) != v]
        conn.execute("INSERT INTO event_revisions(event_id,revision,source_id,recorded_at,source_updated_at,payload,changed_fields) VALUES(?,?,?,?,?,?,?)", (event_id,revision,event.source_id,now,event.source_updated_at,payload,json.dumps(changes)))
        if event.kind == "Economic":
            for role in ("previous","forecast","actual","revised","provider_forecast"):
                value = getattr(event,role)
                number = numeric(value,event.unit)
                conn.execute("INSERT INTO economic_observations(event_id,revision,series_key,reporting_period,role,value_text,value_decimal,unit,source_id,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (event_id,revision,event.series_key,event.reporting_period,role,value,str(number) if number is not None else None,event.unit,event.source_id,now))
        elif event.kind == "Corporate":
            company_id = stable_id("company", event.isin or (event.exchange + ":" + (event.symbol or event.company)))
            conn.execute("INSERT OR IGNORE INTO companies VALUES(?,?,?)", (company_id,event.company,event.isin))
            conn.execute("INSERT OR IGNORE INTO exchange_listings VALUES(?,?,?,?,?)", (stable_id(company_id,event.exchange,event.symbol),company_id,event.exchange,event.symbol,event.isin))
            conn.execute("INSERT INTO corporate_announcements VALUES(?,?,?) ON CONFLICT(event_id) DO UPDATE SET company_id=excluded.company_id,document_hash=excluded.document_hash", (event_id,company_id,event.document_hash))
            candidates = conn.execute("SELECT id FROM events WHERE id!=? AND kind='Corporate' AND sample=? AND category=? AND reporting_period=? AND (isin=? AND isin!='' OR lower(company)=lower(?) AND company!='') AND title=?", (event_id,event.sample,event.category,event.reporting_period,event.isin,event.company,event.title)).fetchall()
            for c in candidates:
                a,b = sorted((event_id,c["id"]))
                conn.execute("INSERT OR IGNORE INTO duplicate_candidates(event_a,event_b,reason) VALUES(?,?,?)", (a,b,"Matching issuer, title, category and period; document equivalence not established"))
        else:
            conn.execute("INSERT INTO regulatory_notices VALUES(?,?,?) ON CONFLICT(event_id) DO UPDATE SET notice_number=excluded.notice_number,supersedes_external_id=excluded.supersedes_external_id", (event_id,event.notice_number,event.supersedes_external_id))
        if event.document_url:
            conn.execute("INSERT OR IGNORE INTO original_documents VALUES(?,?,?,?,?)", (stable_id(event_id,event.document_url),event_id,event.source_id,event.document_url,event.document_hash))
        return event_id, "updated" if previous else "inserted"
