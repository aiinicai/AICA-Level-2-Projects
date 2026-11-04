"""Multi-level review workflow: Preparer -> L1 (first) review -> rework -> L2 (Manager) -> rework -> L3 (Partner) -> sign-off.
Offline, one SQLite file per firm folder. Engine output (the .json each review writes) is ingested at each round, and every
finding becomes a tracked review point with an owner, response, reviewer decision and a full audit trail.
Honour-system identity (names from rules/workflow.yaml) - no passwords; every action records name, role and time."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent
RANK = {"preparer": 0, "L1": 1, "L2": 2, "L3": 3}
RESPONSES = ("Corrected", "Disputed", "Not applicable", "Will correct in next version")
DECISIONS = ("Cleared", "Reopen", "Waived")
OPEN = ("OPEN", "RESPONDED", "REOPENED")

SCHEMA = """
create table if not exists engagement(ref text primary key, module text, client text, period text, state text, level_idx integer, created text);
create table if not exists point(id integer primary key autoincrement, ref text, fp text, check_id text, title text, severity text, detail text,
  location text, source text, raised_level text, raised_round integer, status text, response text, response_note text, decision_note text, updated text);
create table if not exists round(id integer primary key autoincrement, ref text, level text, seq integer, reviewer text, run_at text, json_sha text, closed text, outcome text);
create table if not exists staff(name text primary key, role text, email text);
create table if not exists signoff(id integer primary key autoincrement, ref text, stage text, who text, role text, at text, comment text);
create table if not exists assign(ref text, role text, name text, primary key(ref, role));
create table if not exists attachment(id integer primary key autoincrement, ref text, at text, who text, level text, kind text, filename text, stored text, sha text, note text);
create table if not exists audit(id integer primary key autoincrement, ref text, at text, who text, role text, action text, detail text);
"""


def load_cfg(path=None):
    return yaml.safe_load(Path(path or HERE / "rules" / "workflow.yaml").read_text(encoding="utf-8"))


def fmt_dt(iso):
    try:
        return datetime.fromisoformat(iso).strftime('%d-%b-%Y %H:%M')
    except Exception:
        return iso or ''


def fingerprint(check_id, title, expected=""):
    return hashlib.sha1(f"{check_id}|{title.strip().lower()}|{str(expected).strip().lower()}".encode()).hexdigest()[:12]


class WorkflowError(Exception):
    pass


class Workflow:
    def __init__(self, db_path, cfg=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cfg = cfg or load_cfg()
        self.levels = [l["code"] for l in self.cfg["levels"]]
        self.names = {l["code"]: l["name"] for l in self.cfg["levels"]}
        self.c = sqlite3.connect(str(self.db_path))
        self.c.row_factory = sqlite3.Row
        self.c.executescript(SCHEMA)

    # ---------------------------------------------------------------- helpers
    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def log(self, ref, who, role, action, detail=""):
        self.c.execute("insert into audit(ref,at,who,role,action,detail) values(?,?,?,?,?,?)", (ref, self._now(), who, role, action, detail))
        self.c.commit()

    def eng(self, ref):
        r = self.c.execute("select * from engagement where ref=?", (ref,)).fetchone()
        if not r:
            raise WorkflowError(f"Engagement '{ref}' not found")
        return r

    def engagements(self):
        return [dict(r) for r in self.c.execute("select * from engagement order by created desc")]

    def _need_role(self, role, minimum):
        if RANK[role] < RANK[minimum]:
            raise WorkflowError(f"Your role ({role}) cannot do this; needs {minimum} or above")

    def points(self, ref, status=None):
        q, a = "select * from point where ref=?", [ref]
        if status:
            q += " and status in (%s)" % ",".join("?" * len(status)); a += list(status)
        return [dict(r) for r in self.c.execute(q + " order by case severity when 'High' then 0 when 'Medium' then 1 when 'Low' then 2 else 3 end, id", a)]

    def blocking_open(self, ref):
        bl = set(self.cfg["blocking_severities"])
        return [p for p in self.points(ref, OPEN) if p["severity"] in bl]

    # ---------------------------------------------------------------- state machine
    # PREPARED -> L1_REVIEW -> L1_REWORK -> L2_READY ... represented by state text:
    #   "<LEVEL>_REVIEW"  reviewer working   |  "<LEVEL>_REWORK"  with preparer   |  "<LEVEL>_READY" preparer submitted, awaiting that reviewer
    def create(self, ref, module, client, period, who):
        if self.c.execute("select 1 from engagement where ref=?", (ref,)).fetchone():
            raise WorkflowError(f"Engagement '{ref}' already exists")
        self.c.execute("insert into engagement values(?,?,?,?,?,?,?)", (ref, module, client, period, f"{self.levels[0]}_READY", 0, self._now()))
        self.c.commit()
        self.log(ref, who, "preparer", "CREATED", f"{module} / {client} / {period}")
        self._sign(ref, "preparer", who, "preparer", "Prepared and submitted for first review")
        self._notify(ref)

    def state_text(self, ref):
        e = self.eng(ref)
        s = e["state"]
        if s == "SIGNED_OFF":
            return "Signed off - file locked"
        lv, kind = s.split("_")
        return {"READY": f"Ready for {self.names[lv]}", "REVIEW": f"{self.names[lv]} in progress", "REWORK": f"With preparer - rework after {self.names[lv]}"}[kind]

    def ingest(self, ref, json_path, who, role):
        """Reviewer loads the latest engine run (JSON) for the current level: new findings become points, vanished ones are auto-cleared."""
        e = self.eng(ref)
        if e["state"] == "SIGNED_OFF":
            raise WorkflowError("Engagement is signed off")
        lv = e["state"].split("_")[0]
        self._need_role(role, lv)
        if not e["state"].endswith(("READY", "REVIEW")):
            raise WorkflowError("File is with the preparer for rework; the preparer must submit it first")
        raw = Path(json_path).read_bytes()
        data = json.loads(raw)
        sha = hashlib.sha256(raw).hexdigest()
        seq = (self.c.execute("select max(seq) from round where ref=? and level=?", (ref, lv)).fetchone()[0] or 0) + 1
        self.c.execute("insert into round(ref,level,seq,reviewer,run_at,json_sha) values(?,?,?,?,?,?)", (ref, lv, seq, who, self._now(), sha))
        seen = set(); new = reopened = cleared = 0
        for r in data["results"]:
            for f in r.get("findings", []):
                if r["status"] != "EXC":
                    continue
                fp = fingerprint(f["check_id"], f["title"], f.get("expected", ""))
                seen.add(fp)
                row = self.c.execute("select * from point where ref=? and fp=?", (ref, fp)).fetchone()
                if row is None:
                    self.c.execute("insert into point(ref,fp,check_id,title,severity,detail,location,source,raised_level,raised_round,status,updated) values(?,?,?,?,?,?,?,?,?,?,?,?)",
                                   (ref, fp, f["check_id"], f["title"], f["severity"], f["detail"], f.get("location", ""), "engine", lv, seq, "OPEN", self._now()))
                    new += 1
                elif row["status"] in ("CLEARED", "RESPONDED"):
                    # claimed corrected / previously cleared but the engine still finds it
                    self.c.execute("update point set status='REOPENED', location=?, detail=?, decision_note=?, updated=? where id=?",
                                   (f.get("location", ""), f["detail"], "Re-run still finds this point" , self._now(), row["id"]))
                    reopened += 1
                else:
                    self.c.execute("update point set location=?, detail=?, updated=? where id=?", (f.get("location", ""), f["detail"], self._now(), row["id"]))
        for row in self.points(ref, OPEN):
            if row["source"] == "engine" and row["fp"] not in seen:
                self.c.execute("update point set status='CLEARED', decision_note=?, updated=? where id=?",
                               (f"Not reproduced in {lv} round {seq} re-run (auto-cleared; reviewer to confirm)", self._now(), row["id"]))
                cleared += 1
        self.c.execute("update engagement set state=? where ref=?", (f"{lv}_REVIEW", ref))
        self.c.commit()
        self.log(ref, who, role, f"{lv} ROUND {seq} INGESTED", f"sha {sha[:12]}; new {new}, reopened {reopened}, auto-cleared {cleared}")
        return {"round": seq, "new": new, "reopened": reopened, "auto_cleared": cleared}

    def add_manual_point(self, ref, title, severity, detail, location, who, role):
        e = self.eng(ref)
        lv = e["state"].split("_")[0]
        self._need_role(role, "L1")
        if not e["state"].endswith("REVIEW"):
            raise WorkflowError("Load the review run first (reviewer round must be in progress)")
        seq = self.c.execute("select max(seq) from round where ref=? and level=?", (ref, lv)).fetchone()[0] or 1
        self.c.execute("insert into point(ref,fp,check_id,title,severity,detail,location,source,raised_level,raised_round,status,updated) values(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (ref, "m" + hashlib.sha1((title + self._now()).encode()).hexdigest()[:10], "MANUAL", title, severity, detail, location, f"manual:{who}", lv, seq, "OPEN", self._now()))
        self.c.commit()
        self.log(ref, who, role, "MANUAL POINT", f"{severity}: {title}")

    def respond(self, point_id, response, note, who, role):
        p = self.c.execute("select * from point where id=?", (point_id,)).fetchone()
        if not p:
            raise WorkflowError("Point not found")
        e = self.eng(p["ref"])
        if not e["state"].endswith("REWORK"):
            raise WorkflowError("Responses are taken while the file is with the preparer (rework stage)")
        if response not in RESPONSES:
            raise WorkflowError(f"Response must be one of {RESPONSES}")
        if response in ("Disputed", "Not applicable") and not note.strip():
            raise WorkflowError("A comment is required when disputing or marking not applicable")
        self.c.execute("update point set status='RESPONDED', response=?, response_note=?, updated=? where id=?", (response, note, self._now(), point_id))
        self.c.commit()
        self.log(p["ref"], who, role, "RESPONSE", f"#{point_id} {response}: {note[:120]}")

    def submit_for_review(self, ref, who, role):
        """Preparer hands the corrected file back to the reviewer who sent it back."""
        e = self.eng(ref)
        if not e["state"].endswith("REWORK"):
            raise WorkflowError("File is not in rework")
        unanswered = [p for p in self.points(ref, ("OPEN", "REOPENED"))]
        if unanswered:
            raise WorkflowError(f"{len(unanswered)} point(s) still have no preparer response: " + ", ".join(f"#{p['id']}" for p in unanswered[:10]))
        lv = e["state"].split("_")[0]
        self.c.execute("update engagement set state=? where ref=?", (f"{lv}_READY", ref))
        self.c.commit()
        self.log(ref, who, role, "SUBMITTED", f"back to {self.names[lv]}")
        self._sign(ref, "preparer", who, role, f"Corrections made; resubmitted to {self.names[lv]}")
        self._notify(ref)

    def decide(self, point_id, decision, note, who, role):
        p = self.c.execute("select * from point where id=?", (point_id,)).fetchone()
        if not p:
            raise WorkflowError("Point not found")
        e = self.eng(p["ref"])
        lv = e["state"].split("_")[0]
        if not e["state"].endswith("REVIEW"):
            raise WorkflowError("Reviewer round is not in progress")
        self._need_role(role, lv)
        if decision not in DECISIONS:
            raise WorkflowError(f"Decision must be one of {DECISIONS}")
        if decision == "Waived":
            if role not in self.cfg["waive_roles"]:
                raise WorkflowError(f"Only {self.cfg['waive_roles']} may waive a point")
        if decision in ("Reopen", "Waived") and not note.strip():
            raise WorkflowError("A comment is required to reopen or waive")
        st = {"Cleared": "CLEARED", "Reopen": "REOPENED", "Waived": "WAIVED"}[decision]
        self.c.execute("update point set status=?, decision_note=?, updated=? where id=?", (st, f"{lv} {who}: {note}", self._now(), point_id))
        self.c.commit()
        self.log(p["ref"], who, role, f"DECISION {decision.upper()}", f"#{point_id} {note[:120]}")

    def complete_round(self, ref, who, role, signed=False, comment=""):
        """Reviewer closes the round: open points -> back to preparer; none -> forward to the next level (or sign-off after L3)."""
        e = self.eng(ref)
        if not e["state"].endswith("REVIEW"):
            raise WorkflowError("Reviewer round is not in progress")
        lv = e["state"].split("_")[0]
        self._need_role(role, lv)
        still = self.points(ref, OPEN)
        blocking = [p for p in still if p["severity"] in self.cfg["blocking_severities"]]
        seq = self.c.execute("select max(seq) from round where ref=? and level=?", (ref, lv)).fetchone()[0]
        if still:
            # any open point returns the file to the preparer (non-blocking ones must also be answered), blocking ones may not pass forward
            self.c.execute("update engagement set state=? where ref=?", (f"{lv}_REWORK", ref))
            outcome = f"Returned to preparer: {len(still)} open ({len(blocking)} blocking)"
        else:
            if not signed:
                raise WorkflowError(f"Tick the sign-off confirmation: you are signing off the {self.names[lv]} stage")
            self._sign(ref, lv, who, role, comment or f"{self.names[lv]} completed - no open points")
            i = self.levels.index(lv)
            if i + 1 < len(self.levels):
                self.c.execute("update engagement set state=?, level_idx=? where ref=?", (f"{self.levels[i + 1]}_READY", i + 1, ref))
                outcome = f"Passed to {self.names[self.levels[i + 1]]}"
            else:
                self.c.execute("update engagement set state='SIGNED_OFF' where ref=?", (ref,))
                outcome = "Partner sign-off - file locked"
        self.c.execute("update round set closed=?, outcome=? where ref=? and level=? and seq=?", (self._now(), outcome, ref, lv, seq))
        self.c.commit()
        self.log(ref, who, role, f"{lv} ROUND {seq} CLOSED", outcome)
        self._notify(ref)
        return outcome

    # ---------------------------------------------------------------- sign-off and flow control
    def _sign(self, ref, stage, who, role, comment):
        self.c.execute("insert into signoff(ref,stage,who,role,at,comment) values(?,?,?,?,?,?)", (ref, stage, who, role, self._now(), comment))
        self.c.commit()
        self.log(ref, who, role, f"SIGN-OFF {stage}", comment)

    def signoffs(self, ref):
        return [dict(r) for r in self.c.execute("select * from signoff where ref=? order by id", (ref,))]

    def flow(self, ref):
        """Stage-by-stage control view: who has signed, who has it now, who is next, and whether the file changed after a sign-off."""
        e = self.eng(ref)
        asg = self.assignees(ref)
        sos = self.signoffs(ref)
        files = self.attachments(ref)
        state = e["state"]
        cur = self.actor_role(ref)
        stages = ["preparer"] + self.levels
        label = {"preparer": "Preparer", **self.names}
        rows, cur_seen = [], False
        for st in stages:
            mine = [x for x in sos if x["stage"] == st]
            last = mine[-1] if mine else None
            owner = asg.get(st, "")
            if state == "SIGNED_OFF":
                status = "Signed off" if last else "-"
            elif st == cur:
                status, cur_seen = ("With preparer for corrections" if st == "preparer" else (f"In review" if state.endswith("REVIEW") else "Pending - awaiting review")), True
            elif last and not cur_seen:
                status = "Signed off"
            else:
                status = "Pending"
            changed = bool(last and status == "Signed off" and any(f["at"] > last["at"] and f["kind"] == "Corrected file" for f in files))
            rows.append({"stage": st, "label": label[st], "owner": owner or "(not assigned)", "status": status, "signed_by": last["who"] if last else "",
                         "signed_at": last["at"] if last else "", "comment": last["comment"] if last else "", "changed_after_signoff": changed})
        nxt = None
        if state != "SIGNED_OFF":
            lv = state.split("_")[0]
            kind = state.split("_")[1]
            if kind == "REWORK":
                nxt = f"{label[lv]} (after the preparer resubmits)"
            elif lv != self.levels[-1]:
                nxt = self.names[self.levels[self.levels.index(lv) + 1]]
            else:
                nxt = "Final sign-off"
        return {"rows": rows, "with": asg.get(cur, cur) if cur else None, "with_role": cur, "next": nxt, "headline": self.status_headline(ref)}

    def status_headline(self, ref):
        e = self.eng(ref)
        if e["state"] == "SIGNED_OFF":
            return "REVIEW COMPLETE - all levels signed off"
        lv, kind = e["state"].split("_")
        who = self.assignees(ref).get(self.actor_role(ref), "") or "unassigned"
        if kind == "REWORK":
            return f"PENDING - corrections by preparer ({who}) after {self.names[lv]}"
        return f"PENDING - {self.names[lv]} {'in progress' if kind == 'REVIEW' else 'awaiting start'} ({who})"

    def trail_events(self, ref):
        """Chronological movement of the file: who completed which stage, when, and who it went to next."""
        asg = self.assignees(ref)
        label = {"preparer": "Preparer", **self.names}
        order = ["preparer"] + self.levels
        ev = []
        for a in self.c.execute("select * from audit where ref=? order by id", (ref,)):
            act = a["action"]
            if act.startswith("SIGN-OFF "):
                stage = act.split(" ", 1)[1]
                i = order.index(stage)
                nxt = order[i + 1] if i + 1 < len(order) else None
                to = f"{label[nxt]} - {asg.get(nxt, 'unassigned')}" if nxt else "Review complete - signed off"
                what = ("Prepared / corrected and submitted" if stage == "preparer" else f"Completed {label[stage]} and signed off")
                ev.append({"at": a["at"], "who": a["who"], "what": what, "to": to, "note": a["detail"]})
            elif "CLOSED" in act and "Returned" in (a["detail"] or ""):
                ev.append({"at": a["at"], "who": a["who"], "what": f"{act.split(' ROUND')[0]} review - points raised", "to": f"Preparer - {asg.get('preparer', 'unassigned')}", "note": a["detail"]})
        return ev

    def stamp_docx(self, ref, in_path, out_path):
        """Put the live control status, stage table and movement trail at the top of a Final Review Paper and fill its sign-off table
        (name + date/time) from the recorded sign-offs. Safe to run again: any earlier control block is replaced."""
        import docx
        from docx.shared import Pt, RGBColor
        e = self.eng(ref)
        fl = self.flow(ref)
        d = docx.Document(str(in_path))
        body = d.element.body
        # remove an earlier control block (from the 'REVIEW STATUS' line to the end marker)
        kids = list(body.iterchildren())
        start = next((i for i, k in enumerate(kids) if k.tag.endswith("}p") and "".join(k.itertext()).startswith("REVIEW STATUS:")), None)
        end = next((i for i, k in enumerate(kids) if k.tag.endswith("}p") and "".join(k.itertext()).startswith("-- end of review control block")), None)
        if start is not None and end is not None and end >= start:
            for k in kids[start:end + 1]:
                body.remove(k)
        first = d.paragraphs[0] if d.paragraphs else None
        blocks = []
        def para(text, bold=False, size=10, color=None):
            p = d.add_paragraph(text)
            for r in p.runs:
                r.bold = bold; r.font.size = Pt(size)
                if color: r.font.color.rgb = RGBColor(*color)
            blocks.append(p._p); return p
        def table(head, rows):
            t = d.add_table(rows=1 + len(rows), cols=len(head)); t.style = "Table Grid"
            for i, h in enumerate(head):
                t.rows[0].cells[i].text = h
            for r, vals in zip(t.rows[1:], rows):
                for c, v in zip(r.cells, vals):
                    c.text = str(v)
            blocks.append(t._tbl)
            for row in t.rows:
                for c in row.cells:
                    for pp in c.paragraphs:
                        for rr in pp.runs: rr.font.size = Pt(8.5)
        para(f"REVIEW STATUS: {fl['headline']}", True, 12, (0xB4, 0x23, 0x18) if e["state"] != "SIGNED_OFF" else (0x1E, 0x7A, 0x3C))
        para(f"Engagement {ref} - {e['client']} - {e['module']} - {e['period']}. Status as at {fmt_dt(self._now())}. Then: {fl['next'] or 'none'}.", False, 9)
        table(["Stage", "Owner", "Status", "Signed off by", "Date / time"],
              [(r["label"], r["owner"], r["status"] + (" (file changed after sign-off)" if r["changed_after_signoff"] else ""), r["signed_by"], fmt_dt(r["signed_at"])) for r in fl["rows"]])
        ev = self.trail_events(ref)
        if ev:
            para("Review movement trail", True, 10)
            table(["Date / time", "Person", "Action", "Passed to", "Note"], [(fmt_dt(x["at"]), x["who"], x["what"], x["to"], x["note"][:90]) for x in ev])
        para("-- end of review control block --", False, 7)
        # place the block before the original first paragraph
        anchor = first._p if first is not None else None
        for el in blocks:
            body.remove(el)
            if anchor is not None:
                anchor.addprevious(el)
            else:
                body.append(el)
        # fill the report's own sign-off table: name + date/time + sign
        stage_col = {"Prepared by": "preparer", "First review": "L1", "Manager review": "L2", "Partner review": "L3"}
        by = {row["stage"]: row for row in fl["rows"]}
        for t in d.tables:
            heads = [c.text.strip() for c in t.rows[0].cells]
            if "Prepared by" in heads and "Manager review" in heads and len(t.rows) >= 4 and t.rows[1].cells[0].text.strip() == "Name":
                for ci, h in enumerate(heads):
                    row = by.get(stage_col.get(h))
                    if row and row["signed_by"]:
                        t.rows[1].cells[ci].text = row["signed_by"]
                        t.rows[2].cells[ci].text = fmt_dt(row["signed_at"])
                        t.rows[3].cells[ci].text = "Signed in system"
        d.save(str(out_path))
        return out_path

    # ---------------------------------------------------------------- staff list
    ROLE_LABELS = {"Preparer": "preparer", "First reviewer": "L1", "Manager": "L2", "Partner": "L3"}

    @classmethod
    def role_code(cls, text):
        t = str(text or "").strip().lower()
        for lab, code in cls.ROLE_LABELS.items():
            if t in (lab.lower(), code.lower()):
                return code
        if any(k in t for k in ("prepar", "staff", "junior", "accountant", "associate")):
            return "preparer"
        if any(k in t for k in ("first", "senior", "l1", "reviewer", "supervisor", "in-charge", "incharge")):
            return "L1"
        if "manager" in t or t == "l2":
            return "L2"
        if "partner" in t or "director" in t or t == "l3":
            return "L3"
        raise WorkflowError(f"Unrecognised role '{text}'. Use Preparer, First reviewer, Manager or Partner")

    def staff(self):
        rows = [dict(r) for r in self.c.execute("select * from staff order by case role when 'L3' then 0 when 'L2' then 1 when 'L1' then 2 else 3 end, name")]
        return rows or [{"name": u["name"], "role": u["role"], "email": ""} for u in self.cfg.get("users", [])]

    def users(self):
        return {r["name"]: r["role"] for r in self.staff()}

    def add_staff(self, name, role, email=""):
        name = str(name).strip()
        if not name:
            raise WorkflowError("Name is required")
        self.c.execute("insert or replace into staff values(?,?,?)", (name, self.role_code(role), email or ""))
        self.c.commit()

    def remove_staff(self, name):
        self.c.execute("delete from staff where name=?", (name,))
        self.c.commit()

    def import_staff(self, path, replace=False):
        """Excel/CSV with columns Name, Role (Preparer / First reviewer / Manager / Partner), optional Email."""
        p = Path(path)
        if p.suffix.lower() == ".csv":
            import csv
            rows = list(csv.reader(open(p, newline="", encoding="utf-8-sig")))
        else:
            import openpyxl
            rows = [list(r) for r in openpyxl.load_workbook(p, data_only=True).worksheets[0].iter_rows(values_only=True)]
        rows = [r for r in rows if r and any(c not in (None, "") for c in r)]
        if not rows:
            raise WorkflowError("The staff file is empty")
        head = [str(c or "").strip().lower() for c in rows[0]]
        if "name" not in head or "role" not in head:
            raise WorkflowError("Header row must contain 'Name' and 'Role' (optional 'Email')")
        ni, ri = head.index("name"), head.index("role")
        ei = head.index("email") if "email" in head else None
        added, bad = 0, []
        if replace:
            self.c.execute("delete from staff")
        for r in rows[1:]:
            nm = str(r[ni] or "").strip()
            if not nm:
                continue
            try:
                self.add_staff(nm, r[ri], str(r[ei] or "") if ei is not None and ei < len(r) else "")
                added += 1
            except WorkflowError as ex:
                bad.append(f"{nm}: {ex}")
        return {"added": added, "rejected": bad}

    # ---------------------------------------------------------------- people, files, hand-off
    def assign(self, ref, role, name, who, who_role):
        self.eng(ref)
        if role not in RANK:
            raise WorkflowError("Unknown role")
        self.c.execute("insert or replace into assign values(?,?,?)", (ref, role, name))
        self.c.commit()
        self.log(ref, who, who_role, "ASSIGNED", f"{role} = {name}")

    def assignees(self, ref):
        return {r["role"]: r["name"] for r in self.c.execute("select role,name from assign where ref=?", (ref,))}

    def actor_role(self, ref):
        """Role that must act next."""
        s = self.eng(ref)["state"]
        if s == "SIGNED_OFF":
            return None
        lv, kind = s.split("_")
        return "preparer" if kind == "REWORK" else lv

    def my_queue(self, name):
        out = []
        for e in self.engagements():
            r = self.actor_role(e["ref"])
            if r and self.assignees(e["ref"]).get(r) == name:
                out.append({**e, "action": self.state_text(e["ref"]), "open": len(self.points(e["ref"], OPEN))})
        return out

    def attach(self, ref, src_path, who, role, kind, note=""):
        """Store a copy of the updated working file / marked-up paper in the workflow folder (versioned, hashed)."""
        import shutil
        e = self.eng(ref)
        src = Path(src_path)
        raw = src.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        folder = self.db_path.parent / "files" / ref
        folder.mkdir(parents=True, exist_ok=True)
        stored = folder / f"{datetime.now():%Y%m%d_%H%M%S}_{src.name}"
        shutil.copyfile(src, stored)
        lv = e["state"].split("_")[0] if e["state"] != "SIGNED_OFF" else "L3"
        self.c.execute("insert into attachment(ref,at,who,level,kind,filename,stored,sha,note) values(?,?,?,?,?,?,?,?,?)",
                       (ref, self._now(), who, lv, kind, src.name, str(stored), sha, note))
        self.c.commit()
        self.log(ref, who, role, f"FILE ATTACHED ({kind})", f"{src.name} sha {sha[:12]}")
        return str(stored)

    def attachments(self, ref):
        return [dict(r) for r in self.c.execute("select * from attachment where ref=? order by id desc", (ref,))]

    def handoff_message(self, ref, app_url="http://<this-pc>:8501"):
        e = self.eng(ref)
        r = self.actor_role(ref)
        who = self.assignees(ref).get(r, r or "-")
        bl = len(self.blocking_open(ref))
        return (f"[AuditSignOff Suite UAE] {ref} - {e['client']} ({e['module']}, {e['period']})\n"
                f"Now with: {who} ({r or 'closed'})\nStatus: {self.status_headline(ref)}\n"
                f"Open points: {len(self.points(ref, OPEN))} (blocking {bl})\nOpen the Review workflow tab: {app_url}")

    def _notify(self, ref):
        """Optional Teams notification. Off unless teams_webhook is set in rules/workflow.yaml. Sends only reference, stage and counts - no client figures."""
        url = (self.cfg.get("teams_webhook") or "").strip()
        if not url:
            return
        try:
            import urllib.request
            body = json.dumps({"text": self.handoff_message(ref, self.cfg.get("app_url", "")).replace("\\n", "\n")}).encode()
            urllib.request.urlopen(urllib.request.Request(url, body, {"Content-Type": "application/json"}), timeout=8)
        except Exception as ex:  # never block the review because Teams is unreachable
            self.log(ref, "system", "-", "TEAMS NOTIFY FAILED", str(ex)[:150])

    # ---------------------------------------------------------------- reporting
    def trail_rows(self, ref):
        return ([dict(r) for r in self.c.execute("select * from round where ref=? order by id", (ref,))],
                self.points(ref), [dict(r) for r in self.c.execute("select * from audit where ref=? order by id", (ref,))])

    def export_trail(self, ref, out_path):
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        e = self.eng(ref); rounds, pts, aud = self.trail_rows(ref)
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Review points"
        ws.append([f"Review trail - {e['client']} - {e['module']} - {e['period']} - ref {ref}"]); ws.append([f"Status: {self.state_text(ref)}"]); ws.append([])
        head = ["#", "Raised at", "Check", "Severity", "Review point", "Page / evidence", "Status", "Preparer response", "Preparer comment", "Reviewer decision / note"]
        ws.append(head)
        for c in ws[4]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F3864")
        for p in pts:
            ws.append([p["id"], f"{p['raised_level']} R{p['raised_round']}", p["check_id"], p["severity"], p["title"], p["location"], p["status"], p["response"] or "", p["response_note"] or "", p["decision_note"] or ""])
        for col, w in zip("ABCDEFGHIJ", (5, 9, 9, 9, 52, 34, 12, 20, 36, 40)):
            ws.column_dimensions[col].width = w
        for row in ws.iter_rows(min_row=5):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        w2 = wb.create_sheet("Rounds"); w2.append(["Level", "Round", "Reviewer", "Run at", "Closed", "Outcome", "Run file SHA-256"])
        for r in rounds:
            w2.append([r["level"], r["seq"], r["reviewer"], r["run_at"], r["closed"] or "", r["outcome"] or "", r["json_sha"]])
        wf_ = wb.create_sheet("Flow", 0)
        fl = self.flow(ref)
        wf_.append([f"STATUS: {fl['headline']}"]); wf_.append([f"Next: {fl['next'] or 'none'}"]); wf_.append([])
        wf_.append(["Stage", "Owner", "Status", "Signed off by", "Signed at", "Comment", "File changed after sign-off"])
        for r in fl["rows"]:
            wf_.append([r["label"], r["owner"], r["status"], r["signed_by"], r["signed_at"], r["comment"], "YES" if r["changed_after_signoff"] else ""])
        for col, w in zip("ABCDEFG", (28, 20, 34, 20, 20, 50, 14)):
            wf_.column_dimensions[col].width = w
        w4 = wb.create_sheet("Files"); w4.append(["When", "By", "Level", "Kind", "File", "SHA-256", "Note"])
        for a in self.attachments(ref):
            w4.append([a["at"], a["who"], a["level"], a["kind"], a["filename"], a["sha"], a["note"] or ""])
        w3 = wb.create_sheet("Audit log"); w3.append(["When", "Who", "Role", "Action", "Detail"])
        for a in aud:
            w3.append([a["at"], a["who"], a["role"], a["action"], a["detail"]])
        wb.save(str(out_path))
        return out_path
