"""Local SQLite persistence: leases, versions, events, calculation runs, journals, posting log, audit history, settings."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
import time

from .engine import EngineError, Timeline, build_timeline, preview_event
from .journals import default_map
from .models import Event, LeaseTerms, dumps, to_jsonable
from .money import dec

SCHEMA = """
CREATE TABLE IF NOT EXISTS leases(id INTEGER PRIMARY KEY, ref TEXT UNIQUE NOT NULL, terms_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS lease_versions(id INTEGER PRIMARY KEY, lease_id INTEGER NOT NULL, version INTEGER NOT NULL, kind TEXT, reason TEXT,
  terms_json TEXT, events_json TEXT, summary_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, lease_id INTEGER NOT NULL, seq INTEGER NOT NULL, version INTEGER NOT NULL, type TEXT, effective_date TEXT,
  label TEXT, params_json TEXT, result_json TEXT, committed_at TEXT, UNIQUE(lease_id, seq));
CREATE TABLE IF NOT EXISTS calc_runs(id INTEGER PRIMARY KEY, lease_id INTEGER NOT NULL, version INTEGER NOT NULL, created_at TEXT, initial_json TEXT, rows_json TEXT,
  final_json TEXT, warnings_json TEXT);
CREATE TABLE IF NOT EXISTS journals(id INTEGER PRIMARY KEY, lease_id INTEGER NOT NULL, ref TEXT UNIQUE NOT NULL, jdate TEXT, source TEXT, version INTEGER,
  narration TEXT, lines_json TEXT, trace_json TEXT, content_hash TEXT, status TEXT NOT NULL DEFAULT 'draft', approved_at TEXT, posting_state TEXT NOT NULL DEFAULT 'pending',
  voucher_id TEXT, posted_at TEXT);
CREATE TABLE IF NOT EXISTS posting_log(id INTEGER PRIMARY KEY, journal_ref TEXT NOT NULL, attempted_at TEXT, mode TEXT, request_xml TEXT, response_text TEXT,
  http_status INTEGER, outcome TEXT, voucher_id TEXT, failure_reason TEXT);
CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY, ts TEXT, lease_ref TEXT, action TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
"""

DEFAULT_SETTINGS = {
    'functional_currency': 'AED',
    'tally': {'host': 'localhost', 'port': 9000, 'company': '', 'voucher_type': 'Journal', 'timeout': 15, 'use_json': False, 'narration_prefix': 'IFRS16'},
    'account_map': default_map(),
}


def now():
    return dt.datetime.now().replace(microsecond=0).isoformat(sep=' ')


def _hash(lines, date):
    return hashlib.sha256(dumps({'d': date, 'l': lines}).encode()).hexdigest()


class StoreError(ValueError):
    pass


class Store:
    def __init__(self, path=':memory:'):
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False)   # UI runs long tasks in one worker at a time behind a modal dialog
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        self.db.close()

    # ---------------- settings & audit
    def get_setting(self, key):
        r = self.db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
        if r:
            return json.loads(r['value'])
        v = DEFAULT_SETTINGS.get(key)
        return json.loads(json.dumps(v))

    def set_setting(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (key, json.dumps(to_jsonable(value))))
        self.audit(None, 'setting_changed', key)
        self.db.commit()

    def audit(self, lease_ref, action, detail=''):
        self.db.execute('INSERT INTO audit_log(ts,lease_ref,action,detail) VALUES(?,?,?,?)', (now(), lease_ref, action, str(detail)))

    def audit_rows(self, lease_ref=None):
        q = 'SELECT * FROM audit_log' + (' WHERE lease_ref=?' if lease_ref else '') + ' ORDER BY id DESC'
        return [dict(r) for r in self.db.execute(q, (lease_ref,) if lease_ref else ())]

    # ---------------- leases
    def list_leases(self):
        return [dict(r) for r in self.db.execute('SELECT id,ref,status,updated_at FROM leases ORDER BY ref')]

    def _lease_row(self, ref):
        r = self.db.execute('SELECT * FROM leases WHERE ref=?', (ref,)).fetchone()
        if not r:
            raise StoreError(f'Lease {ref} not found.')
        return r

    def get_terms(self, ref) -> LeaseTerms:
        return LeaseTerms.from_dict(json.loads(self._lease_row(ref)['terms_json']))

    def get_terms_or_none(self, ref):
        r = self.db.execute('SELECT terms_json FROM leases WHERE ref=?', (ref,)).fetchone()
        return LeaseTerms.from_dict(json.loads(r['terms_json'])) if r else None

    def get_events(self, ref) -> list[Event]:
        lid = self._lease_row(ref)['id']
        return [Event(r['type'], dt.date.fromisoformat(r['effective_date']), json.loads(r['params_json']), r['label'])
                for r in self.db.execute('SELECT * FROM events WHERE lease_id=? ORDER BY seq', (lid,))]

    def event_rows(self, ref):
        lid = self._lease_row(ref)['id']
        return [dict(r) for r in self.db.execute('SELECT * FROM events WHERE lease_id=? ORDER BY seq', (lid,))]

    def is_locked(self, ref):
        lid = self._lease_row(ref)['id']
        n = self.db.execute("SELECT COUNT(*) c FROM journals WHERE lease_id=? AND status IN ('approved','posted')", (lid,)).fetchone()['c']
        e = self.db.execute('SELECT COUNT(*) c FROM events WHERE lease_id=?', (lid,)).fetchone()['c']
        return n > 0 or e > 0

    def save_lease(self, terms: LeaseTerms, reason='created/edited'):
        """Create or update a lease. Terms are locked once events exist or any journal is approved/posted (use an event instead)."""
        tl = build_timeline(terms, [])          # validates inputs; raises EngineError with a user-friendly message
        existing = self.db.execute('SELECT id FROM leases WHERE ref=?', (terms.ref,)).fetchone()
        if existing and self.is_locked(terms.ref):
            raise StoreError('This lease has approved/posted journals or committed events, so its original terms are locked to preserve history. Record the change as a reassessment, modification or termination event instead.')
        tj = dumps(terms.to_dict())
        if existing:
            self.db.execute('UPDATE leases SET terms_json=?, updated_at=? WHERE id=?', (tj, now(), existing['id']))
            lid = existing['id']
            self.db.execute('DELETE FROM lease_versions WHERE lease_id=? AND version=0', (lid,))
        else:
            cur = self.db.execute('INSERT INTO leases(ref,terms_json,created_at,updated_at) VALUES(?,?,?,?)', (terms.ref, tj, now(), now()))
            lid = cur.lastrowid
        self.db.execute('INSERT INTO lease_versions(lease_id,version,kind,reason,terms_json,events_json,summary_json,created_at) VALUES(?,?,?,?,?,?,?,?)',
                        (lid, 0, 'initial', reason, tj, '[]', dumps(tl.final | {'initial_liability': tl.initial['liability'], 'initial_rou': tl.initial['rou_cost']}), now()))
        self.audit(terms.ref, 'lease_saved', reason)
        self._sync(terms.ref, tl)
        self.db.commit()
        return tl

    def delete_lease(self, ref):
        r = self._lease_row(ref)
        if self.db.execute("SELECT COUNT(*) c FROM journals WHERE lease_id=? AND (status='posted' OR posting_state IN ('posted','unconfirmed'))", (r['id'],)).fetchone()['c']:
            raise StoreError('This lease has journals posted to Tally and cannot be deleted. Terminate it with an event instead.')
        for t in ('events', 'calc_runs', 'journals', 'lease_versions'):
            self.db.execute(f'DELETE FROM {t} WHERE lease_id=?', (r['id'],))
        self.db.execute('DELETE FROM leases WHERE id=?', (r['id'],))
        self.audit(ref, 'lease_deleted', '')
        self.db.commit()

    # ---------------- calculation
    def timeline(self, ref, extra_events=None) -> Timeline:
        return build_timeline(self.get_terms(ref), self.get_events(ref) + list(extra_events or []))

    def preview(self, ref, event: Event):
        terms, committed = self.get_terms(ref), self.get_events(ref)
        self._guard_event(ref, event)
        return preview_event(terms, committed, event)

    def _guard_event(self, ref, event):
        lid = self._lease_row(ref)['id']
        bad = self.db.execute("SELECT ref FROM journals WHERE lease_id=? AND status!='superseded' AND (posting_state IN ('posted','unconfirmed')) AND jdate>=?",
                              (lid, event.effective_date.isoformat())).fetchall()
        if bad:
            raise StoreError(f'{len(bad)} journal(s) dated on or after {event.effective_date} are already posted to (or awaiting confirmation from) Tally, so an event cannot be effective on that date. Choose a later effective date, or reverse the posted entries in Tally first.')
        evs = self.get_events(ref)
        if evs and event.effective_date < max(e.effective_date for e in evs):
            raise StoreError('Events must be recorded in date order: the effective date is before an earlier committed event.')

    def commit_event(self, ref, event: Event, reason=''):
        self._guard_event(ref, event)
        terms, committed = self.get_terms(ref), self.get_events(ref)
        tl, res = preview_event(terms, committed, event)
        lid = self._lease_row(ref)['id']
        seq = len(committed) + 1
        self.db.execute('INSERT INTO events(lease_id,seq,version,type,effective_date,label,params_json,result_json,committed_at) VALUES(?,?,?,?,?,?,?,?,?)',
                        (lid, seq, seq, event.type, event.effective_date.isoformat(), event.label, dumps(event.params), dumps(res.to_dict()), now()))
        allevs = committed + [event]
        self.db.execute('INSERT INTO lease_versions(lease_id,version,kind,reason,terms_json,events_json,summary_json,created_at) VALUES(?,?,?,?,?,?,?,?)',
                        (lid, seq, event.type, reason or event.label, dumps(terms.to_dict()), dumps([e.to_dict() for e in allevs]), dumps(res.after | {'decision': res.decision}), now()))
        self.audit(ref, 'event_committed', f"V{seq} {event.type} effective {event.effective_date}: {res.decision}")
        self._sync(ref, tl)
        self.db.execute('UPDATE leases SET updated_at=?, status=? WHERE id=?', (now(), 'terminated' if tl.final['terminated'] else 'active', lid))
        self.db.commit()
        return tl, res

    def _sync(self, ref, tl: Timeline):
        """Store the calculation and reconcile journals. Posted/approved history is never rewritten."""
        lid = self._lease_row(ref)['id']
        version = len(tl.events)
        self.db.execute('DELETE FROM calc_runs WHERE lease_id=? AND version=?', (lid, version))
        self.db.execute('INSERT INTO calc_runs(lease_id,version,created_at,initial_json,rows_json,final_json,warnings_json) VALUES(?,?,?,?,?,?,?)',
                        (lid, version, now(), dumps(tl.initial), dumps([r.to_dict() for r in tl.rows]), dumps(tl.final), dumps(tl.warnings)))
        existing = {r['ref']: r for r in self.db.execute('SELECT * FROM journals WHERE lease_id=?', (lid,))}
        seen = set()
        for j in tl.journals:
            seen.add(j.ref)
            lines = [l.__dict__ for l in j.lines]
            h = _hash(to_jsonable(lines), j.date.isoformat())
            row = existing.get(j.ref)
            if row is None:
                self.db.execute('INSERT INTO journals(lease_id,ref,jdate,source,version,narration,lines_json,trace_json,content_hash,status) VALUES(?,?,?,?,?,?,?,?,?,?)',
                                (lid, j.ref, j.date.isoformat(), j.source, j.version, j.narration, dumps(lines), dumps(j.trace), h, 'draft'))
            elif row['content_hash'] != h:
                if row['status'] in ('approved',) or row['posting_state'] in ('posted', 'unconfirmed'):
                    self.audit(ref, 'journal_conflict', f"{j.ref} changed after approval/posting; stored copy preserved")
                else:
                    self.db.execute('UPDATE journals SET jdate=?,narration=?,lines_json=?,trace_json=?,content_hash=?,status=? WHERE id=?',
                                    (j.date.isoformat(), j.narration, dumps(lines), dumps(j.trace), h, 'draft', row['id']))
            elif row['status'] == 'superseded':
                self.db.execute("UPDATE journals SET status='draft' WHERE id=?", (row['id'],))
        for r, row in existing.items():
            if r not in seen and row['status'] != 'superseded':
                if row['posting_state'] in ('posted', 'unconfirmed'):
                    self.audit(ref, 'journal_orphan', f'{r} is posted but no longer in the recalculated schedule – needs manual reversal in Tally')
                else:
                    self.db.execute("UPDATE journals SET status='superseded' WHERE id=?", (row['id'],))
                    self.audit(ref, 'journal_superseded', r)

    def journals(self, ref=None, status=None, include_superseded=False):
        q, a = 'SELECT j.*, l.ref lease_ref FROM journals j JOIN leases l ON l.id=j.lease_id WHERE 1=1', []
        if ref:
            q += ' AND l.ref=?'; a.append(ref)
        if status:
            q += ' AND j.status=?'; a.append(status)
        if not include_superseded:
            q += " AND j.status!='superseded'"
        q += ' ORDER BY j.jdate, j.id'
        out = []
        for r in self.db.execute(q, a):
            d = dict(r)
            d['lines'] = json.loads(d['lines_json'])
            d['trace'] = json.loads(d['trace_json'])
            out.append(d)
        return out

    def approve_journals(self, refs):
        n = 0
        for r in refs:
            row = self.db.execute('SELECT * FROM journals WHERE ref=?', (r,)).fetchone()
            if row and row['status'] == 'draft':
                lines = json.loads(row['lines_json'])
                if sum(dec(l['debit']) for l in lines) != sum(dec(l['credit']) for l in lines):
                    raise StoreError(f'Journal {r} is not balanced and cannot be approved.')
                self.db.execute("UPDATE journals SET status='approved', approved_at=? WHERE id=?", (now(), row['id']))
                self.audit(None, 'journal_approved', r)
                n += 1
        self.db.commit()
        return n

    # ---------------- posting log (connector writes here; it never touches calculations)
    def log_posting(self, journal_ref, mode, request_xml, response_text, http_status, outcome, voucher_id='', failure_reason=''):
        self.db.execute('INSERT INTO posting_log(journal_ref,attempted_at,mode,request_xml,response_text,http_status,outcome,voucher_id,failure_reason) VALUES(?,?,?,?,?,?,?,?,?)',
                        (journal_ref, now(), mode, request_xml, response_text, http_status, outcome, voucher_id, failure_reason))
        if mode == 'post':
            state = {'success': 'posted', 'failed': 'failed', 'unconfirmed': 'unconfirmed', 'unavailable': 'pending'}.get(outcome, 'pending')
            if outcome == 'success':
                self.db.execute("UPDATE journals SET posting_state='posted', voucher_id=?, posted_at=?, status='posted' WHERE ref=?", (voucher_id, now(), journal_ref))
            else:
                self.db.execute('UPDATE journals SET posting_state=? WHERE ref=? AND posting_state!="posted"', (state, journal_ref))
        self.audit(None, 'tally_' + mode, f'{journal_ref}: {outcome} {failure_reason}')
        self.db.commit()

    def resolve_unconfirmed(self, journal_ref, posted: bool, voucher_id=''):
        """User confirms (after checking Tally) whether an 'unconfirmed' voucher exists."""
        if posted:
            self.db.execute("UPDATE journals SET posting_state='posted', status='posted', voucher_id=?, posted_at=? WHERE ref=?", (voucher_id, now(), journal_ref))
        else:
            self.db.execute("UPDATE journals SET posting_state='pending' WHERE ref=? AND posting_state='unconfirmed'", (journal_ref,))
        self.audit(None, 'tally_resolved', f'{journal_ref}: posted={posted}')
        self.db.commit()

    def posting_rows(self, journal_ref=None):
        q = 'SELECT * FROM posting_log' + (' WHERE journal_ref=?' if journal_ref else '') + ' ORDER BY id DESC'
        return [dict(r) for r in self.db.execute(q, (journal_ref,) if journal_ref else ())]

    def journal(self, ref):
        r = self.db.execute('SELECT j.*, l.ref lease_ref FROM journals j JOIN leases l ON l.id=j.lease_id WHERE j.ref=?', (ref,)).fetchone()
        if not r:
            raise StoreError(f'Journal {ref} not found.')
        d = dict(r)
        d['lines'] = json.loads(d['lines_json'])
        d['trace'] = json.loads(d['trace_json'])
        return d

    def versions(self, ref):
        lid = self._lease_row(ref)['id']
        return [dict(r) for r in self.db.execute('SELECT * FROM lease_versions WHERE lease_id=? ORDER BY version, id', (lid,))]

    def stored_rows(self, ref):
        lid = self._lease_row(ref)['id']
        r = self.db.execute('SELECT * FROM calc_runs WHERE lease_id=? ORDER BY version DESC, id DESC LIMIT 1', (lid,)).fetchone()
        return json.loads(r['rows_json']) if r else []
