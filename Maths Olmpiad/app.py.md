```python
"""
Olympiad Quest - adaptive olympiad practice for children aged 4-16 (Flask + SQLite)

Run:    pip install flask
        python app.py              -> open http://127.0.0.1:5000
Check:  python app.py --check      -> validates questions.txt and prints counts

Files next to this one:
    questions.txt   the question bank (format explained at the top of that file)
    questions.json  optional extra questions:
                    [{"subject":"Math","band":"c","diff":2,"q":"...","opts":["..",".."],"ans":0,"why":"..."}]

How it adapts: every child has a skill level (0-17) per subject. It starts in the
middle of their age band and moves up after right answers and down after wrong
ones. Questions are picked close to that level, new questions first, and missed
questions come back later for review.
"""
import hashlib, json, math, os, random, sqlite3, sys, datetime as dt
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from jinja2 import DictLoader

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")
app.permanent_session_lifetime = dt.timedelta(days=365)
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "olympiad.db")

SUBJECTS = {"Math": ("🧮", "#4f46e5"), "Science": ("🔬", "#059669"),
            "English": ("📖", "#db2777"), "Reasoning": ("🧩", "#d97706")}
MIN_AGE, MAX_AGE = 4, 16
# band: (min age, max age, title, icon)
BANDS = {"a": (4, 5, "Little Explorer", "🌱"), "b": (6, 7, "Young Thinker", "🚀"),
         "c": (8, 9, "Rising Star", "⭐"), "d": (10, 11, "Challenger", "🧭"),
         "e": (12, 13, "Achiever", "🏅"), "f": (14, 16, "Olympiad Pro", "🏆")}
BAND_KEYS = list(BANDS)
MAX_LEVEL = 18  # 6 bands x 3 difficulty steps


def band_index(age):
    return next(i for i, b in enumerate(BAND_KEYS) if BANDS[b][0] <= age <= BANDS[b][1])


def round_size(age):
    return 5 if age <= 5 else 8 if age <= 7 else 10


# ----------------------------------------------------------------- questions
BANK = {s: [] for s in SUBJECTS}
BYID = {}


def add_question(subject, band, diff, q, correct, wrong, why):
    if subject not in SUBJECTS or band not in BANDS or diff not in (1, 2, 3):
        raise ValueError(f"bad subject/band/difficulty for question: {q[:40]}")
    qid = hashlib.md5(f"{subject}|{q}".encode("utf-8")).hexdigest()[:10]
    if qid in BYID:
        return
    opts = [correct] + list(wrong)
    random.Random(qid).shuffle(opts)  # same order every run
    item = dict(id=qid, subject=subject, band=band, lvl=BAND_KEYS.index(band) * 3 + diff - 1,
                q=q, opts=opts, ans=opts.index(correct), why=why)
    BANK[subject].append(item)
    BYID[qid] = item


def load_bank():
    path = os.path.join(HERE, "questions.txt")
    if os.path.exists(path):
        lines = open(path, encoding="utf-8").read().splitlines()
    else:
        lines = EMBEDDED_BANK.splitlines()  # built-in copy, so app.py also works on its own
    subject = None
    for n, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("# "):
            subject = line[2:].strip()
            continue
        p = [x.strip() for x in line.split("|")]
        if len(p) != 7 or len(p[0]) != 2 or not p[0][1].isdigit():
            raise SystemExit(f"questions.txt line {n}: expected code|question|correct|wrong|wrong|wrong|why")
        add_question(subject, p[0][0], int(p[0][1]), p[1], p[2], p[3:6], p[6])
    extra = os.path.join(HERE, "questions.json")
    if os.path.exists(extra):
        for d in json.load(open(extra, encoding="utf-8")):
            correct = d["opts"][d["ans"]]
            add_question(d["subject"], d["band"], int(d.get("diff", 2)), d["q"], correct,
                         [o for i, o in enumerate(d["opts"]) if i != d["ans"]], d["why"])


def report():
    print("Question bank:")
    for s in SUBJECTS:
        per = {b: sum(1 for q in BANK[s] if q["band"] == b) for b in BAND_KEYS}
        print(f"  {s:10} {len(BANK[s]):4}   " + "  ".join(f"{b}({BANDS[b][0]}-{BANDS[b][1]}):{n}" for b, n in per.items()))
    bad = [q["q"] for q in BYID.values() if len(set(q["opts"])) != len(q["opts"])]
    print("Problems:", bad or "none")


# ----------------------------------------------------------------------- db
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def init_db():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT UNIQUE COLLATE NOCASE, age INTEGER, created TEXT);
    CREATE TABLE IF NOT EXISTS answers(id INTEGER PRIMARY KEY, user_id INTEGER, qid TEXT, subject TEXT, correct INTEGER, day TEXT);
    CREATE TABLE IF NOT EXISTS skill(user_id INTEGER, subject TEXT, rating REAL, PRIMARY KEY(user_id, subject));
    CREATE TABLE IF NOT EXISTS rounds(id INTEGER PRIMARY KEY, user_id INTEGER, subject TEXT, score INTEGER, total INTEGER, day TEXT);
    """)
    c.commit(); c.close()


def current_user():
    uid = session.get("uid")
    row = db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() if uid else None
    if not row:
        return None
    u = dict(row)
    u["age"] = max(MIN_AGE, min(MAX_AGE, u["age"] or MIN_AGE))
    return u


# ------------------------------------------------------------------ adaptive
def rating_range(age):
    i = band_index(age) * 3
    return max(0.0, i - 3.0), min(MAX_LEVEL - 0.01, i + 5.99)  # up to one band easier or harder


def get_rating(uid, subject, age):
    row = db().execute("SELECT rating FROM skill WHERE user_id=? AND subject=?", (uid, subject)).fetchone()
    lo, hi = rating_range(age)
    r = row["rating"] if row else band_index(age) * 3 + 1.0
    return max(lo, min(hi, r))


def history(uid, subject):
    """qid -> (times answered, last answer correct?)"""
    h = {}
    for r in db().execute("SELECT qid, correct FROM answers WHERE user_id=? AND subject=? ORDER BY id", (uid, subject)):
        h[r["qid"]] = (h.get(r["qid"], (0, 0))[0] + 1, bool(r["correct"]))
    return h


def pick_question(uid, subject, age, seen, review):
    hist = history(uid, subject)
    pool = [q for q in BANK[subject] if q["id"] not in seen]
    if review:
        pool = [q for q in pool if q["id"] in hist and not hist[q["id"]][1]]
        return random.choice(pool) if pool else None
    if not pool:
        return None
    rating = get_rating(uid, subject, age)
    for width in (1.2, 2.2, 4, 99):
        near = [q for q in pool if abs(q["lvl"] - rating) <= width]
        if near:
            break
    fresh = [q for q in near if q["id"] not in hist]
    missed = [q for q in near if q["id"] in hist and not hist[q["id"]][1]]
    if missed and (not fresh or random.random() < 0.3):
        return random.choice(missed)
    if fresh:
        return random.choice(fresh)
    return min(near, key=lambda q: (hist[q["id"]][0], random.random()))  # least practised


def stats(uid):
    d = db()
    tot, ok = d.execute("SELECT COUNT(*), COALESCE(SUM(correct),0) FROM answers WHERE user_id=?", (uid,)).fetchone()
    days = {r[0] for r in d.execute("SELECT DISTINCT day FROM answers WHERE user_id=?", (uid,))}
    today = dt.date.today()
    cur = today if today.isoformat() in days else today - dt.timedelta(days=1)
    streak = 0
    while cur.isoformat() in days:
        streak += 1; cur -= dt.timedelta(days=1)
    age = d.execute("SELECT age FROM users WHERE id=?", (uid,)).fetchone()[0]
    age = max(MIN_AGE, min(MAX_AGE, age or MIN_AGE))
    subj = {s: dict(total=0, ok=0) for s in SUBJECTS}
    for r in d.execute("SELECT subject, COUNT(*), SUM(correct) FROM answers WHERE user_id=? GROUP BY subject", (uid,)):
        if r[0] in subj:
            subj[r[0]] = dict(total=r[1], ok=r[2] or 0)
    for s, v in subj.items():
        v["pct"] = round(100 * v["ok"] / v["total"]) if v["total"] else 0
        r = get_rating(uid, s, age)
        key = BAND_KEYS[min(5, int(r // 3))]
        v.update(lvl=int(r) + 1, mastery=round(100 * (r + 0.5) / MAX_LEVEL), title=BANDS[key][2], icon=BANDS[key][3])
    week = []
    for i in range(6, -1, -1):
        day = today - dt.timedelta(days=i)
        n, k = d.execute("SELECT COUNT(*), COALESCE(SUM(correct),0) FROM answers WHERE user_id=? AND day=?", (uid, day.isoformat())).fetchone()
        week.append(dict(label=day.strftime("%a"), n=n, ok=k))
    acc = round(100 * ok / tot) if tot else 0
    perfect = d.execute("SELECT 1 FROM rounds WHERE user_id=? AND score=total AND total>=5 LIMIT 1", (uid,)).fetchone() is not None
    xp = ok * 10 + (tot - ok) * 2
    badges = [("🌟", "First answer", tot >= 1), ("🧠", "25 answers", tot >= 25), ("💯", "100 answers", tot >= 100),
              ("🚀", "500 answers", tot >= 500), ("🔥", "3-day streak", streak >= 3), ("⚡", "7-day streak", streak >= 7),
              ("🎯", "80%+ accuracy", tot >= 20 and acc >= 80), ("🌍", "All 4 subjects", all(v["total"] for v in subj.values())),
              ("🥇", "Perfect round", perfect)]
    return dict(total=tot, ok=ok, acc=acc, streak=streak, subj=subj, week=week, xp=xp,
                plevel=1 + int(math.sqrt(xp / 50)), badges=badges, maxday=max([w["n"] for w in week] + [1]))


# ------------------------------------------------------------------- routes
def ages():
    return range(MIN_AGE, MAX_AGE + 1)


@app.route("/")
def home():
    if current_user():
        return redirect(url_for("dashboard"))
    return render_template("home.html", user=None, ages=ages())


@app.post("/start")
def start():
    name = " ".join(request.form.get("name", "").split())[:20]
    try:
        age = int(request.form.get("age", 0))
    except ValueError:
        age = 0
    if len(name) < 2 or not MIN_AGE <= age <= MAX_AGE:
        return render_template("home.html", user=None, ages=ages(), error="Please enter a name (2+ letters) and choose your age.")
    d = db()
    row = d.execute("SELECT id FROM users WHERE name=?", (name,)).fetchone()
    if row:
        d.execute("UPDATE users SET age=? WHERE id=?", (age, row["id"])); uid = row["id"]
    else:
        uid = d.execute("INSERT INTO users(name,age,created) VALUES(?,?,?)", (name, age, dt.date.today().isoformat())).lastrowid
    d.commit(); session["uid"] = uid; session.permanent = True
    return redirect(url_for("dashboard"))


@app.post("/age")
def set_age():
    u = current_user()
    if u:
        try:
            age = max(MIN_AGE, min(MAX_AGE, int(request.form.get("age", u["age"]))))
        except ValueError:
            age = u["age"]
        db().execute("UPDATE users SET age=? WHERE id=?", (age, u["id"])); db().commit()
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    u = current_user()
    if not u:
        return redirect(url_for("home"))
    return render_template("dash.html", user=u, st=stats(u["id"]), subjects=SUBJECTS, ages=ages())


@app.route("/practice/<subject>")
def practice(subject):
    u = current_user()
    if not u or subject not in SUBJECTS:
        return redirect(url_for("home"))
    return render_template("practice.html", user=u, subject=subject, icon=SUBJECTS[subject][0],
                           total=round_size(u["age"]), review=request.args.get("review") == "1")


@app.get("/api/question")
def api_question():
    u = current_user()
    subject = request.args.get("subject")
    if not u or subject not in SUBJECTS:
        return jsonify(error="bad request"), 400
    seen = set(request.args.get("seen", "").split(","))
    review = request.args.get("review") == "1"
    q = pick_question(u["id"], subject, u["age"], seen, review)
    if not q:
        return jsonify(done=True, review_empty=review)
    return jsonify(id=q["id"], q=q["q"], opts=q["opts"])


@app.post("/api/answer")
def api_answer():
    u = current_user()
    data = request.get_json(force=True, silent=True) or {}
    q = BYID.get(str(data.get("id")))
    try:
        choice = int(data.get("choice"))
    except (TypeError, ValueError):
        choice = -1
    if not u or not q or not 0 <= choice < len(q["opts"]):
        return jsonify(error="bad request"), 400
    ok = int(choice == q["ans"])
    d = db()
    d.execute("INSERT INTO answers(user_id,qid,subject,correct,day) VALUES(?,?,?,?,?)",
              (u["id"], q["id"], q["subject"], ok, dt.date.today().isoformat()))
    r = get_rating(u["id"], q["subject"], u["age"])
    expected = 1 / (1 + math.exp(-(r - q["lvl"]) * 0.8))  # Elo-style: surprises move you more
    lo, hi = rating_range(u["age"])
    r = max(lo, min(hi, r + 0.5 * (ok - expected)))
    d.execute("INSERT OR REPLACE INTO skill(user_id,subject,rating) VALUES(?,?,?)", (u["id"], q["subject"], r))
    d.commit()
    return jsonify(correct=bool(ok), answer=q["ans"], why=q["why"])


@app.post("/api/finish")
def api_finish():
    u = current_user()
    data = request.get_json(force=True, silent=True) or {}
    s = data.get("subject")
    if not u or s not in SUBJECTS:
        return jsonify(error="bad request"), 400
    try:
        total = max(1, min(int(data.get("total", 1)), 20)); score = max(0, min(int(data.get("score", 0)), total))
    except (TypeError, ValueError):
        return jsonify(error="bad request"), 400
    db().execute("INSERT INTO rounds(user_id,subject,score,total,day) VALUES(?,?,?,?,?)",
                 (u["id"], s, score, total, dt.date.today().isoformat()))
    db().commit()
    r = get_rating(u["id"], s, u["age"])
    return jsonify(title=BANDS[BAND_KEYS[min(5, int(r // 3))]][2], lvl=int(r) + 1)


# ---------------------------------------------------------------- templates
BASE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Olympiad Quest</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{--blue:#1d4ed8;--deep:#1e3a8a;--indigo:#4f46e5;--yellow:#facc15;--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f1f5f9}
*{box-sizing:border-box;margin:0}body{font-family:Outfit,system-ui,sans-serif;color:var(--ink);background:var(--bg);min-height:100vh}
a{text-decoration:none;color:inherit}
nav{background:#fff;display:flex;align-items:center;justify-content:space-between;padding:14px 5vw;box-shadow:0 1px 0 var(--line);position:sticky;top:0;z-index:5}
.logo{font-size:26px;font-weight:800;color:var(--indigo)}.logo span{color:var(--yellow);text-shadow:0 0 1px #ca8a04}
nav .links{display:flex;gap:26px;font-weight:500;color:#334155}nav .links a:hover{color:var(--indigo)}
.btn{display:inline-block;border:0;cursor:pointer;font:600 16px Outfit;padding:13px 24px;border-radius:12px;transition:.15s}
.btn:hover{transform:translateY(-2px)}.b-ind{background:var(--indigo);color:#fff}.b-yel{background:var(--yellow);color:#111;box-shadow:0 8px 24px #facc1566}
.b-out{background:transparent;color:#fff;border:1px solid #ffffff66}.b-ghost{background:#fff;border:1px solid var(--line)}
.hero{background:linear-gradient(135deg,#1d4ed8,#1e3a8a);color:#fff;padding:60px 5vw 80px;display:grid;grid-template-columns:1.1fr 1fr;gap:40px;align-items:center;min-height:calc(100vh - 66px);position:relative;overflow:hidden}
.pill{display:inline-block;background:#ffffff1f;border:1px solid #ffffff33;padding:8px 16px;border-radius:99px;font-size:14px;font-weight:600;margin-bottom:22px}
h1{font-size:clamp(40px,5.4vw,72px);line-height:1.02;font-weight:800;letter-spacing:-1.5px}h1 em{font-style:normal;color:var(--yellow)}
.hero p{font-size:19px;line-height:1.6;opacity:.9;margin:22px 0 30px;max-width:560px}
.card{background:#fff;border-radius:22px;box-shadow:0 30px 60px #0b1b5055;color:var(--ink)}
.signup{padding:32px}.signup h2{font-size:26px;margin-bottom:6px}.signup .sub{color:var(--mut);margin-bottom:20px}
label{font-weight:600;font-size:14px;display:block;margin:14px 0 6px}
input,select{width:100%;padding:14px 16px;border:1.5px solid var(--line);border-radius:12px;font:500 16px Outfit;background:#fff;outline:none}
input:focus,select:focus{border-color:var(--indigo);box-shadow:0 0 0 4px #4f46e51f}
.err{background:#fee2e2;color:#b91c1c;padding:10px 14px;border-radius:10px;margin-top:14px;font-weight:500}
.feats{display:flex;gap:26px;flex-wrap:wrap;margin-top:44px;padding-top:24px;border-top:1px solid #ffffff2e;font-size:14px;font-weight:600}
.float{position:absolute;font-size:42px;animation:fl 5s ease-in-out infinite}@keyframes fl{50%{transform:translateY(-16px)}}
.wrap{max-width:1180px;margin:28px auto;padding:0 20px}
.dash{display:grid;grid-template-columns:230px 1fr;overflow:hidden}.side{padding:24px 16px;border-right:1px solid var(--line)}
.side a{display:block;padding:12px 16px;border-radius:10px;font-weight:500;color:#475569;margin-bottom:4px}.side a.on{background:var(--indigo);color:#fff;font-weight:600}
.main{padding:28px}.top{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px}
.top h2{font-size:28px}.top p{color:var(--mut)}.who{display:flex;align-items:center;gap:10px;font-weight:600}
.av{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,var(--indigo),#06b6d4);color:#fff;display:grid;place-items:center;font-weight:700}
.who select{width:auto;padding:8px 12px}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:24px 0}
.stat{border:1px solid var(--line);border-radius:14px;padding:16px;background:#f8fafc}.stat small{color:var(--mut);font-size:13px}.stat b{display:block;font-size:28px;margin-top:4px}
h3{margin:6px 0 14px;font-size:18px}.grid2{display:grid;grid-template-columns:1.5fr 1fr;gap:20px}
.subj{display:flex;align-items:center;gap:14px;border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:12px;transition:.15s;background:#fff}
.subj:hover{border-color:var(--indigo);box-shadow:0 8px 20px #4f46e51a;transform:translateY(-2px)}
.ic{width:46px;height:46px;border-radius:12px;display:grid;place-items:center;font-size:22px}.subj .m{flex:1}.subj b{display:block}.subj small{color:var(--mut)}
.bar{height:8px;background:#e2e8f0;border-radius:9px;margin-top:8px;overflow:hidden}.bar i{display:block;height:100%;background:var(--indigo);border-radius:9px;transition:width .5s}
.go{width:34px;height:34px;border-radius:50%;background:#eef2ff;color:var(--indigo);display:grid;place-items:center;font-weight:800}
.week{display:flex;align-items:flex-end;gap:10px;height:170px;border:1px solid var(--line);border-radius:14px;padding:16px;background:#f8fafc}
.col{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;font-size:12px;color:var(--mut);gap:6px}
.col .b{width:100%;max-width:32px;background:#c7d2fe;border-radius:8px 8px 0 0;position:relative;min-height:3px}.col .b i{position:absolute;bottom:0;left:0;right:0;background:var(--indigo);border-radius:8px 8px 0 0}
.legend{font-size:12px;color:var(--mut);margin-top:8px}
.q{max-width:760px;margin:30px auto;padding:34px}.qh{display:flex;justify-content:space-between;font-weight:600;color:var(--mut);margin-bottom:12px}
.qt{font-size:26px;font-weight:700;margin:22px 0}.opt{display:block;width:100%;text-align:left;padding:16px 18px;margin-bottom:12px;border:2px solid var(--line);border-radius:14px;background:#fff;font:500 18px Outfit;cursor:pointer;transition:.15s}
.opt:hover:not(:disabled){border-color:var(--indigo);background:#eef2ff}.opt.ok{border-color:#16a34a;background:#dcfce7}.opt.no{border-color:#dc2626;background:#fee2e2}.opt:disabled{cursor:default}
.exp{margin-top:18px;padding:18px;border-radius:14px;background:#fffbeb;border:1px solid #fde68a;line-height:1.55}.exp b{display:block;margin-bottom:4px}
.res{text-align:center;padding:20px 0}.res .big{font-size:70px}.res h2{font-size:32px;margin:8px 0}
.kid .qt{font-size:34px}.kid .opt{font-size:24px;padding:22px}.badges{display:flex;flex-wrap:wrap;gap:10px;margin:6px 0 24px}.badge{border:1px solid var(--line);border-radius:12px;padding:8px 12px;font-size:13px;font-weight:600;background:#fff}.badge.off{opacity:.4;filter:grayscale(1)}.tag{display:inline-block;font-size:12px;font-weight:600;color:var(--indigo);background:#eef2ff;border-radius:99px;padding:3px 10px;margin-left:6px}.lnk{color:var(--indigo);font-weight:600;margin-right:12px}
@media(max-width:860px){.hero,.grid2,.dash{grid-template-columns:1fr}.side{display:none}.stats{grid-template-columns:1fr 1fr}nav .links{display:none}}
</style></head><body>
<nav><a href="/" class="logo">Olympiad<span>Quest</span></a>
<div class="links"><a href="/">Home</a><a href="/dashboard">Dashboard</a>{% for s in ['Math','Science','English','Reasoning'] %}{% if user %}<a href="/practice/{{s}}">{{s}}</a>{% endif %}{% endfor %}</div>
<div>{% if user %}<a class="btn b-ghost" href="/logout">Switch user</a>{% else %}<a class="btn b-ind" href="#start">Start</a>{% endif %}</div></nav>
{% block body %}{% endblock %}</body></html>"""

HOME = """{% extends 'base.html' %}{% block body %}
<section class="hero"><span class="float" style="top:90px;left:46%">🎓</span><span class="float" style="top:140px;right:4%;animation-delay:1s">🏆</span><span class="float" style="bottom:90px;right:3%;animation-delay:2s">💡</span>
<div><span class="pill">✨ Smart olympiad practice for ages 4 to 16</span>
<h1>Olympiads are not just exams. <em>They are a learning journey.</em></h1>
<p>Questions that match your age and adapt to how you are doing: a little easier when you need a boost, harder when you are flying. Learn from every explanation and watch your level grow!</p>
<div class="feats"><span>🛡️ Safe &amp; ad-free</span><span>🧠 Explanations for every answer</span><span>🎯 Adapts to your level</span><span>📈 Track your progress</span></div></div>
<form id="start" class="card signup" method="post" action="/start"><h2>Let's get started 🚀</h2><p class="sub">No password needed. Just your name!</p>
<label>Your name</label><input name="name" placeholder="e.g. Aarav" maxlength="20" required autofocus>
<label>Your age</label><select name="age" required><option value="">Choose age…</option>{% for a in ages %}<option value="{{a}}">{{a}} years</option>{% endfor %}</select>
{% if error %}<div class="err">{{error}}</div>{% endif %}
<button class="btn b-yel" style="width:100%;margin-top:22px">Start Free Learning →</button>
<p class="sub" style="margin:14px 0 0;font-size:13px">Coming back? Enter the same name to continue where you left off.</p></form></section>{% endblock %}"""

DASH = """{% extends 'base.html' %}{% block body %}<div class="wrap"><div class="card dash">
<div class="side"><a class="on" href="/dashboard">🏠 Dashboard</a>{% for s,(i,c) in subjects.items() %}<a href="/practice/{{s}}">{{i}} {{s}}</a>{% endfor %}</div>
<div class="main"><div class="top"><div><h2>Welcome back, {{user['name']}}! 👋</h2><p>Let's continue your learning journey.</p></div>
<form class="who" method="post" action="/age"><div class="av">{{user['name'][0]|upper}}</div>Age
<select name="age" onchange="this.form.submit()">{% for a in ages %}<option value="{{a}}" {{'selected' if a==user['age']}}>{{a}}</option>{% endfor %}</select></form></div>
<div class="stats"><div class="stat"><small>Questions answered</small><b>{{st.total}}</b></div><div class="stat"><small>Correct answers</small><b>{{st.ok}}</b></div>
<div class="stat"><small>Accuracy</small><b>{{st.acc}}%</b></div><div class="stat"><small>Current streak</small><b>{{st.streak}} day{{'' if st.streak==1 else 's'}} 🔥</b></div><div class="stat"><small>Player level</small><b>⭐ {{st.plevel}}</b></div></div>
<h3>Your badges</h3><div class="badges">{% for ic,nm,on in st.badges %}<span class="badge {{'' if on else 'off'}}">{{ic}} {{nm}}</span>{% endfor %}</div>
<div class="grid2"><div><h3>Choose a subject to practice</h3>
{% for s,(i,c) in subjects.items() %}<a class="subj" href="/practice/{{s}}"><div class="ic" style="background:{{c}}22">{{i}}</div>
<div class="m"><b>{{s}} Olympiad</b><span class="tag">{{st.subj[s].icon}} {{st.subj[s].title}}</span><small>Level {{st.subj[s].lvl}} of 18 · {{st.subj[s].total}} answered · {{st.subj[s].pct}}% correct</small><div class="bar"><i style="width:{{st.subj[s].mastery}}%;background:{{c}}"></i></div></div><div class="go">→</div></a>{% endfor %}<p class="legend">Review mistakes: {% for s in subjects %}<a class="lnk" href="/practice/{{s}}?review=1">{{s}}</a>{% endfor %}</p></div>
<div><h3>Weekly progress</h3><div class="week">{% for w in st.week %}<div class="col"><div class="b" style="height:{{(w.n/st.maxday*100)|round}}%" title="{{w.ok}}/{{w.n}} correct"><i style="height:{{(w.ok/w.n*100)|round if w.n else 0}}%"></i></div>{{w.label}}</div>{% endfor %}</div>
<div class="legend">Dark = correct · Light = attempted</div></div></div></div></div></div>{% endblock %}"""

PRACTICE = """{% extends 'base.html' %}{% block body %}<div class="card q{{' kid' if user['age']<=7}}" id="box">
<div class="qh"><span>{{icon}} {{subject}} · Age {{user['age']}}</span><span id="cnt"></span></div><div class="bar"><i id="pg" style="width:0"></i></div>
<div id="area"></div></div>
<script>
const SUB={{subject|tojson}},TOTAL={{total}},REVIEW={{review|tojson}},AGE={{user['age']}};let seen=[],n=0,score=0,cur=null;
const $=id=>document.getElementById(id),el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
function speak(r){if(!window.speechSynthesis)return;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(r.q+'. '+r.opts.map((o,i)=>String.fromCharCode(65+i)+', '+o).join('. '));u.rate=.85;speechSynthesis.speak(u)}
async function next(){
  const r=await (await fetch(`/api/question?subject=${SUB}&seen=${seen.join(',')}&review=${REVIEW?1:0}`)).json();
  if(r.done||n>=TOTAL)return finish(r.review_empty);
  cur=r;seen.push(r.id);$('cnt').textContent=`Question ${n+1} of ${TOTAL}`;$('pg').style.width=(n/TOTAL*100)+'%';
  const a=$('area');a.innerHTML='';a.append(el('div','qt',r.q));const sp=el('button','btn b-ghost','🔊 Read aloud');sp.style.marginBottom='14px';sp.onclick=()=>speak(r);a.append(sp);
  r.opts.forEach((o,i)=>{const b=el('button','opt',String.fromCharCode(65+i)+'.  '+o);b.onclick=()=>answer(i,b);a.append(b)});if(AGE<=5)speak(r);
}
async function answer(i,btn){
  const bs=[...document.querySelectorAll('.opt')];bs.forEach(b=>b.disabled=true);
  const r=await (await fetch('/api/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:cur.id,choice:i})})).json();
  bs[r.answer].classList.add('ok');if(!r.correct)btn.classList.add('no');else score++;
  n++;$('pg').style.width=(n/TOTAL*100)+'%';
  const e=el('div','exp');e.append(el('b','',r.correct?'🎉 Correct! Well done.':'💡 Not quite — here is why:'),el('span','',r.why));$('area').append(e);
  const nb=el('button','btn b-ind',n>=TOTAL?'See my result →':'Next question →');nb.style.marginTop='18px';nb.onclick=next;$('area').append(nb);
}
async function finish(empty){
  const a=$('area');a.innerHTML='';$('pg').style.width='100%';$('cnt').textContent='Done!';
  if(empty&&!n){const d=el('div','res');d.append(el('div','big','🎉'),el('h2','','No mistakes to review!'),el('p','','Everything you answered so far was right. Try a normal round.'));const b=el('a','btn b-ind','Dashboard');b.href='/dashboard';d.append(el('br'),b);a.append(d);return}
  let info=null;if(n){try{info=await (await fetch('/api/finish',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subject:SUB,score:score,total:n})})).json()}catch(e){}}
  const t=n||1,p=score/t,d=el('div','res');
  d.append(el('div','big',p>=.8?'🏆':p>=.5?'🌟':'💪'),el('h2','',`You scored ${score} / ${n}`),
    el('p','',p>=.8?'Brilliant work, Olympiad star!':p>=.5?'Good job! A little more practice and you will shine.':'Every mistake is a lesson. Try again!'));if(info&&info.title)d.append(el('p','',`Your ${SUB} level: ${info.title} · Level ${info.lvl} of 18`));
  const b1=el('a','btn b-ind','Practice again');b1.href=location.href;const b2=el('a','btn b-ghost','Dashboard');b2.href='/dashboard';b2.style.marginLeft='10px';
  d.append(el('br'),b1,b2);a.append(d);
}
next();
</script>{% endblock %}"""

app.jinja_loader = DictLoader({"base.html": BASE, "home.html": HOME, "dash.html": DASH, "practice.html": PRACTICE})

def free_port(start):
    import socket
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:  # nothing is listening there
                return port
    return start


def main():
    if "--check" in sys.argv:
        report()
        return
    import threading, webbrowser
    port = free_port(int(os.environ.get("PORT", 5000)))
    url = f"http://127.0.0.1:{port}"
    print(f"\n  Olympiad Quest is running -> {url}\n  (press Ctrl+C to stop)\n")
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False)


EMBEDDED_BANK = r'''
// Olympiad Quest question bank. One question per line, 7 fields separated by |
//   code|question|correct answer|wrong 1|wrong 2|wrong 3|explanation
// code = age band letter + difficulty 1-3.  Bands: a=4-5  b=6-7  c=8-9  d=10-11  e=12-13  f=14-16
// A line starting with "# " starts a subject. Lines starting with // are comments. Do not use | inside text.
// Answer order is shuffled automatically. Run:  python app.py --check

# Math
a1|How many? 🍎🍎🍎|3|2|4|5|Count each apple one by one: 1, 2, 3.
a1|What number comes after 4?|5|3|6|7|Counting goes 3, 4, 5. After 4 comes 5.
a1|Which shape has no corners?|Circle|Square|Triangle|Rectangle|A circle is perfectly round, so it has no corners.
a1|1 + 1 = ?|2|1|3|4|One and one more makes two.
a2|2 + 3 = ?|5|4|6|7|Start at 2 and count on 3 more: 3, 4, 5.
a2|How many? ⭐⭐⭐⭐⭐⭐|6|5|7|8|Count the stars one by one: there are 6.
a2|Which number is the biggest?|9|6|3|7|9 is more than 6, 3 and 7.
a2|You have 5 cookies 🍪 and eat 2. How many are left?|3|2|4|7|5 take away 2 leaves 3.
a2|What comes next? 1, 2, 3, ?|4|5|2|6|We count up by one each time, so after 3 comes 4.
a3|What comes next? 2, 4, 6, ?|8|7|9|10|We count in twos: 2, 4, 6, 8.
a3|Which is the smallest number? 12, 8, 15, 10|8|12|15|10|8 is less than 10, 12 and 15.
a3|How many sides does a triangle have?|3|4|2|5|Tri means three. A triangle has 3 sides.
b1|What is 9 + 6?|15|14|16|13|9 + 1 = 10, then add the other 5: 15.
b1|What is 14 − 5?|9|8|10|19|Take away 4 to reach 10, then 1 more: 14 − 5 = 9.
b1|How many sides does a square have?|4|3|5|6|A square has 4 equal sides.
b1|What is double 8?|16|18|14|12|Double means twice as much: 8 + 8 = 16.
b1|Which of these is an even number?|18|13|15|17|Even numbers end in 0, 2, 4, 6 or 8. 18 ends in 8.
b2|What is 5 × 3?|15|8|12|18|Five groups of 3: 3 + 3 + 3 + 3 + 3 = 15.
b2|What is 36 + 27?|63|53|62|64|30 + 20 = 50 and 6 + 7 = 13. Then 50 + 13 = 63.
b2|What comes next? 5, 10, 15, 20, ?|25|30|24|22|We count in fives: 20 + 5 = 25.
b2|The short hand of a clock points at 3. What time is it (on the hour)?|3 o'clock|12 o'clock|6 o'clock|9 o'clock|The short (hour) hand shows the hour. At 3 o'clock it points at the 3.
b2|How many minutes are in one hour?|60|30|100|12|One hour is 60 minutes.
b2|Sam has 24 stickers and gives 9 away. How many are left?|15|14|33|16|24 − 9 = 15.
b3|What is 48 ÷ 6?|8|6|7|9|6 × 8 = 48, so 48 ÷ 6 = 8.
b3|What is the missing number? 7 + ? = 15|8|7|9|22|15 − 7 = 8.
b3|Which is greater: 3 tens and 5 ones, or 4 tens?|4 tens|3 tens and 5 ones|They are equal|Cannot tell|3 tens and 5 ones is 35. 4 tens is 40. 40 is greater.
b3|A rectangle is 6 cm long and 3 cm wide. What is its perimeter?|18 cm|9 cm|12 cm|24 cm|Add all four sides: 6 + 3 + 6 + 3 = 18 cm.
b3|What is 100 − 37?|63|73|67|53|100 − 40 = 60, then add back 3: 63.
c1|What is 7 × 8?|56|54|48|63|7 × 8 = 56. A tip: 5, 6, 7, 8 → 56 = 7 × 8.
c1|What is 345 + 278?|623|613|523|633|300 + 200 = 500 and 45 + 78 = 123. Then 500 + 123 = 623.
c1|Which fraction is equal to one half?|2/4|1/4|3/4|2/3|2/4 simplifies to 1/2 because both numbers divide by 2.
c1|How many centimetres are in 1 metre?|100|10|1000|50|1 metre = 100 centimetres.
c1|What is 1000 − 456?|544|554|644|534|456 + 544 = 1000, so 1000 − 456 = 544.
c1|What comes next? 3, 6, 12, 24, ?|48|36|30|27|Each number doubles. 24 × 2 = 48.
c2|What is 3/5 of 20?|12|15|8|10|20 ÷ 5 = 4 (one fifth). 4 × 3 = 12.
c2|Pens cost $12 each. How much do 7 pens cost?|$84|$74|$82|$94|7 × 12 = 84.
c2|What is the area of a rectangle 8 m long and 5 m wide?|40 m²|13 m²|26 m²|45 m²|Area = length × width = 8 × 5 = 40 m².
c2|Round 4,672 to the nearest hundred.|4,700|4,600|4,670|5,000|The tens digit is 7, so we round up: 4,700.
c2|How many degrees are in a right angle?|90°|180°|45°|100°|A right angle is a quarter turn: 360° ÷ 4 = 90°.
c2|What is 0.5 + 0.25?|0.75|0.7|0.30|0.55|Half is 0.50. Adding 0.25 gives 0.75.
c3|What is 144 ÷ 12?|12|11|14|13|12 × 12 = 144.
c3|Digits 1, 2 and 3 are each used once to make a 3-digit number. How many different numbers can be made?|6|3|9|4|3 choices for the first digit × 2 for the second × 1 for the last = 6.
c3|A train leaves at 9:45 and the journey takes 2 hours 30 minutes. When does it arrive?|12:15|11:75|12:45|11:45|9:45 + 2 hours = 11:45. Add 30 minutes: 12:15.
c3|What is the smallest 4-digit number?|1000|999|1001|9999|1000 is the first number with four digits.
c3|5 pencils cost $10. How much do 8 pencils cost?|$16|$14|$18|$20|One pencil costs $2. So 8 pencils cost 8 × 2 = $16.
c3|What is the perimeter of a square with sides of 9 cm?|36 cm|18 cm|81 cm|27 cm|A square has 4 equal sides: 4 × 9 = 36 cm. (81 would be the area.)
d1|What is 25% of 80?|20|25|40|16|25% is one quarter. 80 ÷ 4 = 20.
d1|What is the value of 3 + 4 × 5?|23|35|27|32|Multiply before adding (BODMAS): 4 × 5 = 20, then 3 + 20 = 23.
d1|Which is the largest number? 0.6, 0.58, 0.605, 0.059|0.605|0.6|0.58|0.059|Compare as thousandths: 0.605 > 0.600 > 0.580 > 0.059.
d1|What is the greatest common factor of 12 and 18?|6|3|12|9|Common factors are 1, 2, 3 and 6. The greatest is 6.
d1|What is 2/3 + 1/6?|5/6|3/9|1/2|2/9|2/3 = 4/6. Then 4/6 + 1/6 = 5/6.
d1|How many prime numbers are there between 1 and 10?|4|3|5|6|The primes are 2, 3, 5 and 7.
d2|What is the average of 4, 8 and 12?|8|6|12|24|(4 + 8 + 12) ÷ 3 = 24 ÷ 3 = 8.
d2|A car travels 60 km in 1 hour. How far does it go in 2.5 hours at the same speed?|150 km|120 km|130 km|62.5 km|60 × 2.5 = 150 km.
d2|What is (−3) + (−5)?|−8|8|−2|2|Adding two negative numbers gives a bigger negative number: −8.
d2|Boys to girls is 3 : 2. There are 12 boys. How many girls are there?|8|6|18|10|12 ÷ 3 = 4 per part. Girls = 2 × 4 = 8.
d2|The angles in a triangle always add up to...|180°|90°|360°|270°|The three angles of any triangle add up to 180°.
d2|What is 15% of 200?|30|15|20|35|10% of 200 = 20 and 5% = 10. So 15% = 30.
d3|How many diagonals does a pentagon have?|5|10|3|7|Use n(n − 3) ÷ 2 = 5 × 2 ÷ 2 = 5.
d3|What is the smallest number that both 6 and 8 divide into?|24|48|12|14|Multiples of 8: 8, 16, 24. 24 is also a multiple of 6. So the LCM is 24.
d3|A number is doubled and then 7 is added to give 25. What was the number?|9|18|16|14|Work backwards: 25 − 7 = 18, then 18 ÷ 2 = 9.
d3|The sum of three consecutive numbers is 48. What is the largest of them?|17|16|15|18|The numbers are 15, 16 and 17 (their sum is 48). The largest is 17.
d3|What is the value of 2³ × 3²?|72|36|54|216|2³ = 8 and 3² = 9. Then 8 × 9 = 72.
d3|What is the volume of a cuboid 5 cm × 4 cm × 3 cm?|60 cm³|12 cm³|36 cm³|94 cm³|Volume = length × width × height = 5 × 4 × 3 = 60 cm³.
e1|Solve: 2x + 7 = 19|x = 6|x = 5|x = 13|x = 12|Subtract 7: 2x = 12. Divide by 2: x = 6.
e1|What is the square root of 169?|13|12|14|17|13 × 13 = 169.
e1|Simplify: 3(x + 4)|3x + 12|3x + 4|x + 12|3x + 7|Multiply each term inside the brackets by 3.
e1|What is −7 × −6?|42|−42|13|−13|A negative times a negative is positive. 7 × 6 = 42.
e1|What is the area of a triangle with base 10 cm and height 6 cm?|30 cm²|60 cm²|16 cm²|36 cm²|Area = ½ × base × height = ½ × 10 × 6 = 30 cm².
e1|What is 3/8 as a decimal?|0.375|0.425|0.325|0.83|3 ÷ 8 = 0.375.
e2|Solve: 5x − 3 = 2x + 12|x = 5|x = 3|x = 15|x = 4|Subtract 2x from both sides: 3x − 3 = 12. Then 3x = 15, so x = 5.
e2|The interior angles of a quadrilateral add up to...|360°|180°|270°|540°|A quadrilateral splits into 2 triangles: 2 × 180° = 360°.
e2|A shirt costs $40 after a 20% discount. What was the original price?|$50|$48|$60|$45|$40 is 80% of the original. 40 ÷ 0.8 = $50.
e2|What is the circumference of a circle with radius 7 cm? (use π = 22/7)|44 cm|22 cm|154 cm|49 cm|C = 2πr = 2 × 22/7 × 7 = 44 cm.
e2|If y = 2x + 1 and x = 4, what is y?|9|8|10|7|y = 2 × 4 + 1 = 9.
e2|What is the median of 3, 9, 4, 7, 12?|7|4|9|6|Put them in order: 3, 4, 7, 9, 12. The middle one is 7.
e3|Two numbers add up to 20 and their difference is 4. What is the larger number?|12|8|16|10|Larger = (20 + 4) ÷ 2 = 12. The smaller is 8.
e3|In how many different ways can 4 people stand in a line?|24|16|12|8|4 × 3 × 2 × 1 = 24.
e3|What is the value of 2⁻²?|1/4|−4|−1/4|4|A negative power means reciprocal: 2⁻² = 1/2² = 1/4.
e3|A right-angled triangle has short sides 6 and 8. How long is the longest side?|10|14|12|9|By Pythagoras: 6² + 8² = 100, and √100 = 10.
e3|What is the next term? 1, 4, 9, 16, 25, ?|36|30|35|49|These are square numbers. The next is 6² = 36.
e3|A bag has 3 red and 2 blue balls. What is the probability of picking a blue ball?|2/5|2/3|3/5|1/2|There are 2 blue balls out of 5 in total, so 2/5.
f1|Solve: x² − 5x + 6 = 0|x = 2 or x = 3|x = −2 or x = −3|x = 1 or x = 6|x = 5 or x = 1|Factorise: (x − 2)(x − 3) = 0, so x = 2 or x = 3.
f1|What is log₁₀ 1000?|3|10|100|2|10³ = 1000, so the logarithm is 3.
f1|What is the slope (gradient) of the line y = 4x − 7?|4|−7|7|−4|In y = mx + c, m is the slope. Here m = 4.
f1|What is sin 30°?|1/2|√3/2|1|0|sin 30° = 1/2 is one of the standard trigonometric values.
f1|Expand (a + b)²|a² + 2ab + b²|a² + b²|a² + ab + b²|2a + 2b|(a + b)(a + b) = a² + ab + ab + b² = a² + 2ab + b².
f1|What is the sum of the first 10 positive whole numbers?|55|45|50|100|n(n + 1) ÷ 2 = 10 × 11 ÷ 2 = 55.
f2|If log₂(x) = 5, what is x?|32|10|25|64|log₂(x) = 5 means x = 2⁵ = 32.
f2|What is the sum of the roots of x² − 7x + 10 = 0?|7|10|−7|−10|The roots are 2 and 5. Their sum is 7 (which equals −b/a).
f2|How many diagonals does a hexagon have?|9|6|12|15|n(n − 3) ÷ 2 = 6 × 3 ÷ 2 = 9.
f2|What is the distance between the points (0, 0) and (5, 12)?|13|17|7|12|√(5² + 12²) = √169 = 13.
f2|In how many ways can 2 students be chosen from a group of 6?|15|12|30|36|6C2 = (6 × 5) ÷ 2 = 15.
f2|What is the sum of the interior angles of an octagon (8 sides)?|1080°|1440°|720°|1260°|(n − 2) × 180° = 6 × 180° = 1080°.
f3|What is the sum of the first 10 terms of 2, 5, 8, 11, ...?|155|145|150|160|The 10th term is 2 + 9 × 3 = 29. Sum = 10 × (2 + 29) ÷ 2 = 155.
f3|How many positive divisors does 36 have?|9|8|6|12|36 = 2² × 3². Add 1 to each power and multiply: (2 + 1) × (2 + 1) = 9.
f3|If x + 1/x = 3, what is x² + 1/x²?|7|9|6|11|Square both sides: x² + 2 + 1/x² = 9. So x² + 1/x² = 7.
f3|How many zeros are at the end of 25! (25 factorial)?|6|5|4|7|Count the factors of 5: 25 ÷ 5 = 5, and 25 ÷ 25 = 1. Total 6.
f3|What is the remainder when 2¹⁰ is divided by 7?|2|1|4|6|2³ = 8 leaves remainder 1. So 2¹⁰ = (2³)³ × 2 leaves remainder 2.
f3|Two fair dice are rolled. What is the probability that the sum is 7?|1/6|1/12|7/36|5/36|6 of the 36 outcomes add to 7, so 6/36 = 1/6.

# Science
a1|Which animal says "moo"?|Cow|Dog|Cat|Duck|A cow says moo.
a1|What do we use our eyes for?|To see|To hear|To smell|To taste|Our eyes help us see the world.
a1|Which of these is very hot?|The Sun ☀️|Ice cream|Snow|A fridge|The Sun is a giant ball of very hot gas.
a1|What colour are most leaves?|Green|Red|Blue|Purple|Leaves are green because of a substance called chlorophyll.
a2|What do plants need to grow?|Water and sunlight|Candy|Toys|Plastic|Plants drink water and use sunlight to make their food.
a2|Which animal can fly?|Bird|Elephant|Fish|Turtle|Birds have wings and feathers that help them fly.
a2|Where do fish live?|In water|In trees|In the sky|In snow|Fish breathe underwater using gills.
a2|Which part of our body do we use to smell?|Nose|Eyes|Ears|Hands|Our nose smells things.
a2|What do we call a baby cat?|Kitten|Puppy|Cub|Calf|A baby cat is called a kitten.
a3|What do we need to breathe?|Air|Juice|Sand|Milk|We breathe in air, which has oxygen in it.
a3|Which of these gives us light in the daytime?|The Sun|The Moon|A cloud|A rock|The Sun lights up our days.
a3|Which season is usually the coldest?|Winter|Summer|Spring|Autumn|Winter is usually the coldest time of the year.
b1|What do bees make?|Honey|Milk|Bread|Cheese|Bees make honey from the nectar of flowers.
b1|Which of these is a reptile?|Snake|Frog|Whale|Parrot|Snakes have dry, scaly skin. They are reptiles.
b1|How many legs does an insect have?|6|4|8|2|All insects have six legs.
b1|Which part of a plant makes seeds?|Flower|Root|Stem|Leaf|Flowers make seeds so new plants can grow.
b1|What do we call a baby frog?|Tadpole|Cub|Chick|Calf|A frog starts life as a tadpole in the water.
b2|Which material is attracted to a magnet?|Iron|Wood|Plastic|Glass|Magnets attract iron and some other metals.
b2|Which of these makes its own light?|The Sun|The Moon|A mirror|A book|The Sun makes light. The Moon only reflects sunlight.
b2|What happens to water when it freezes?|It turns into ice|It turns into steam|It disappears|It turns into sand|Below 0 °C liquid water becomes solid ice.
b2|Which animal is a herbivore (eats only plants)?|Cow|Lion|Tiger|Crocodile|Cows eat grass and other plants.
b2|Which part of the body pumps blood?|Heart|Lungs|Brain|Stomach|The heart pumps blood around the body.
b2|Which planet do we live on?|Earth|Mars|Venus|Jupiter|We live on planet Earth.
b3|Which of these is a living thing?|A tree|A rock|A chair|A cloud|Living things grow, need food and water, and make new life.
b3|What do we call animals that eat both plants and meat?|Omnivores|Herbivores|Carnivores|Insects|Omni means "all". Humans and bears are omnivores.
b3|Why do we wear a coat in winter?|To keep our body warm|To stay cool|To get wet|To grow taller|A coat traps body heat so we do not get cold.
b3|Which gas do humans breathe in to stay alive?|Oxygen|Carbon dioxide|Helium|Smoke|Our bodies use oxygen from the air.
b3|Which star is closest to Earth?|The Sun|The Moon|Sirius|Mars|The Sun is a star, and it is much closer to us than any other star.
c1|Which organ do we use to think?|Brain|Heart|Liver|Kidney|The brain controls thinking, memory and movement.
c1|What is it called when water vapour cools and turns back into liquid water?|Condensation|Evaporation|Melting|Freezing|Cooling vapour condenses into tiny water droplets.
c1|Which is the largest planet in our solar system?|Jupiter|Saturn|Earth|Neptune|Jupiter is bigger than all the other planets put together.
c1|Which part of a plant takes in water from the soil?|Roots|Leaves|Flowers|Fruits|Roots soak up water and minerals and hold the plant in the soil.
c1|Which of these is a mammal?|Dolphin|Shark|Eagle|Frog|Dolphins breathe air and feed their babies milk, so they are mammals.
c1|Which force pulls objects towards the ground?|Gravity|Magnetism|Friction|Wind|Gravity pulls things towards the centre of the Earth.
c2|Which gas makes up most of the air we breathe?|Nitrogen|Oxygen|Carbon dioxide|Hydrogen|Air is about 78% nitrogen and 21% oxygen.
c2|Which of these conducts electricity well?|Copper wire|Rubber|Wood|Plastic|Metals like copper let electricity flow easily.
c2|Which gas do plants release during photosynthesis?|Oxygen|Carbon dioxide|Nitrogen|Methane|Plants take in carbon dioxide and release oxygen.
c2|About how many bones does an adult human have?|206|106|306|56|An adult human skeleton has 206 bones.
c2|Which state of matter has a fixed shape?|Solid|Liquid|Gas|Steam|Solids keep their shape. Liquids and gases take the shape of their container.
c2|About how long does the Moon take to orbit the Earth?|About 1 month|1 day|1 year|1 week|The Moon goes around the Earth about once every 27 to 29 days.
c3|What is the Earth's outer layer called?|Crust|Mantle|Core|Atmosphere|The crust is the thin, rocky outer layer where we live.
c3|Which type of rock forms when hot lava cools down?|Igneous|Sedimentary|Metamorphic|Fossil|Igneous rocks form when molten rock cools and hardens.
c3|Which of these is a producer (makes its own food)?|Grass|Lion|Snake|Eagle|Plants make food using sunlight, so they start every food chain.
c3|Which body part detects sound?|Ear|Nose|Skin|Tongue|Our ears pick up sound waves and send signals to the brain.
c3|Which of these is a renewable source of energy?|Solar power|Coal|Petrol|Natural gas|Sunlight will not run out, so solar power is renewable.
c3|What causes day and night?|Earth spinning on its axis|Earth orbiting the Sun|The Moon blocking the Sun|Clouds|Earth spins once about every 24 hours, so each place faces the Sun and then turns away.
d1|What is the chemical formula of water?|H₂O|CO₂|O₂|NaCl|A water molecule has two hydrogen atoms and one oxygen atom.
d1|Which body system carries blood around the body?|Circulatory system|Digestive system|Nervous system|Respiratory system|The heart, blood and blood vessels form the circulatory system.
d1|What is the process plants use to make their food?|Photosynthesis|Respiration|Digestion|Evaporation|Plants turn carbon dioxide, water and light into glucose and oxygen.
d1|Why does Mars look red?|Its soil contains iron oxide (rust)|It is covered in lava|It is very close to the Sun|It has red oceans|Rusty iron minerals in the soil give Mars its red colour.
d1|What is the SI unit of force?|Newton|Joule|Watt|Metre|Force is measured in newtons (N).
d1|Sound cannot travel through...|A vacuum (empty space)|Water|Air|Steel|Sound needs particles to travel through. A vacuum has almost none.
d2|Which blood cells help fight infection?|White blood cells|Red blood cells|Platelets|Plasma|White blood cells defend the body against germs.
d2|At what temperature does pure water boil at sea level?|100 °C|0 °C|50 °C|90 °C|Water boils at 100 °C at normal air pressure.
d2|Which of these gases traps heat in the atmosphere (a greenhouse gas)?|Carbon dioxide|Argon|Helium|Neon|Carbon dioxide traps heat and warms the planet.
d2|What is the centre of an atom called?|Nucleus|Electron|Cell wall|Orbit|The nucleus contains protons and neutrons.
d2|What kind of energy is stored in a stretched rubber band?|Elastic potential energy|Kinetic energy|Sound energy|Light energy|A stretched band stores energy that is released when it springs back.
d2|Which vitamin does our skin make with the help of sunlight?|Vitamin D|Vitamin C|Vitamin A|Vitamin B12|Sunlight on skin helps the body make vitamin D.
d3|Which part of a cell contains the DNA?|Nucleus|Cell membrane|Cytoplasm|Vacuole|The nucleus holds the cell's DNA, its instructions.
d3|What is the pH of a neutral solution such as pure water?|7|0|14|10|pH 7 is neutral. Below 7 is acidic and above 7 is alkaline.
d3|About how fast does light travel?|300,000 km per second|3,000 km per second|300 km per second|30,000 km per second|Light moves at roughly 300,000 kilometres every second.
d3|Which of these is a chemical change?|Burning wood|Melting ice|Cutting paper|Boiling water|Burning makes new substances (ash, smoke) that cannot be changed back.
d3|Which lens is thicker in the middle and brings light rays together?|Convex lens|Concave lens|Flat glass|Plane mirror|A convex lens bulges outwards and focuses light.
d3|What are the three main types of rock?|Igneous, sedimentary and metamorphic|Hard, soft and medium|Red, grey and black|Solid, liquid and gas|Rocks are grouped by how they form: cooling, layering or heat and pressure.
e1|Which part of a cell is the "powerhouse" that releases energy?|Mitochondrion|Nucleus|Ribosome|Golgi body|Mitochondria release energy from food during respiration.
e1|What is the SI unit of electric current?|Ampere|Volt|Ohm|Watt|Current is measured in amperes (amps).
e1|Which element has the symbol Fe?|Iron|Fluorine|Lead|Zinc|Fe comes from the Latin word "ferrum", meaning iron.
e1|Which of these is a vector quantity (has size and direction)?|Velocity|Speed|Mass|Time|Velocity tells us speed and direction. Speed alone has no direction.
e1|Acids have a pH...|Less than 7|Exactly 7|More than 7|Above 10|Acids have a pH below 7.
e1|What is the process by which a cell divides into two identical cells?|Mitosis|Meiosis|Osmosis|Diffusion|Mitosis makes two identical body cells for growth and repair.
e2|What is the formula for speed?|Distance ÷ time|Time ÷ distance|Distance × time|Mass × acceleration|Speed = distance ÷ time.
e2|Which gas is released when zinc reacts with dilute acid?|Hydrogen|Oxygen|Carbon dioxide|Nitrogen|Metal + acid → salt + hydrogen.
e2|The movement of water through a semi-permeable membrane is called...|Osmosis|Diffusion|Respiration|Evaporation|Osmosis is the movement of water from a dilute to a concentrated solution through a membrane.
e2|What is the atomic number of carbon?|6|12|8|14|Carbon has 6 protons, so its atomic number is 6.
e2|Which colour of light bends the most in a prism?|Violet|Red|Green|Yellow|Violet has the shortest wavelength of visible light, so it bends the most.
e2|Which law says every action has an equal and opposite reaction?|Newton's third law|Newton's first law|Newton's second law|Ohm's law|That is Newton's third law of motion.
e3|A 10 V battery drives a current of 2 A. What is the power?|20 W|5 W|12 W|8 W|Power = voltage × current = 10 × 2 = 20 W.
e3|Which structure is found in plant cells but not in animal cells?|Cell wall|Nucleus|Mitochondria|Cell membrane|Plant cells have a rigid cell wall (and chloroplasts).
e3|How many chromosomes are in a normal human body cell?|46|23|44|48|Humans have 23 pairs of chromosomes, which is 46 in total.
e3|Which type of bond is formed by sharing electrons?|Covalent bond|Ionic bond|Metallic bond|Gravity bond|In a covalent bond, atoms share pairs of electrons.
e3|What is the kinetic energy of a 2 kg object moving at 3 m/s?|9 J|6 J|18 J|12 J|KE = ½ × m × v² = ½ × 2 × 9 = 9 J.
e3|In which layer of the atmosphere is the ozone layer?|Stratosphere|Troposphere|Mesosphere|Thermosphere|The ozone layer sits in the stratosphere and absorbs harmful UV rays.
f1|Which value is Avogadro's number (per mole)?|6.02 × 10²³|6.67 × 10⁻¹¹|3.0 × 10⁸|1.6 × 10⁻¹⁹|One mole contains about 6.02 × 10²³ particles.
f1|Which law is written V = IR?|Ohm's law|Hooke's law|Boyle's law|Newton's law|Ohm's law: voltage = current × resistance.
f1|What is the pH of 0.01 M hydrochloric acid (a strong acid)?|2|1|0.01|12|pH = −log₁₀(0.01) = 2.
f1|What shape is a DNA molecule?|Double helix|Single strand|Triple ring|Cube|DNA is two strands twisted together in a double helix.
f1|Which particles carry a negative charge?|Electrons|Protons|Neutrons|Photons|Electrons are negatively charged. Protons are positive and neutrons are neutral.
f1|What is the acceleration due to gravity near Earth's surface?|About 9.8 m/s²|About 98 m/s²|About 0.98 m/s²|About 3.0 m/s²|Falling objects speed up by about 9.8 m/s every second.
f2|Which organelle is the site of photosynthesis?|Chloroplast|Mitochondrion|Ribosome|Lysosome|Chloroplasts contain chlorophyll that captures light energy.
f2|Which law says the pressure of a gas is inversely proportional to its volume at constant temperature?|Boyle's law|Charles's law|Ohm's law|Hooke's law|Boyle's law: P × V stays constant at constant temperature.
f2|A 2 kg object is lifted 5 m. How much gravitational potential energy does it gain? (g = 10 m/s²)|100 J|10 J|50 J|20 J|PE = m × g × h = 2 × 10 × 5 = 100 J.
f2|A reaction that releases heat to its surroundings is called...|Exothermic|Endothermic|Reversible|Catalytic|Exothermic reactions give out heat, so the surroundings warm up.
f2|Which blood vessels carry blood away from the heart?|Arteries|Veins|Capillaries|Valves|Arteries carry blood away from the heart. Veins bring it back.
f2|What is the molar mass of CO₂? (C = 12, O = 16)|44 g/mol|28 g/mol|32 g/mol|56 g/mol|12 + 2 × 16 = 44 g/mol.
f3|Resistors of 4 Ω and 6 Ω are connected in parallel. What is the total resistance?|2.4 Ω|10 Ω|5 Ω|1.2 Ω|1/R = 1/4 + 1/6 = 5/12, so R = 12/5 = 2.4 Ω.
f3|Where in the cell does the Krebs cycle take place?|Mitochondrial matrix|Cytoplasm|Nucleus|Ribosome|The Krebs cycle runs inside the mitochondrial matrix.
f3|A ball is thrown straight up at 20 m/s (g = 10 m/s²). How long does it take to reach its highest point?|2 s|4 s|1 s|20 s|At the top v = 0. Using v = u − gt gives 0 = 20 − 10t, so t = 2 s.
f3|Which of these is a noble gas?|Argon|Nitrogen|Chlorine|Oxygen|Argon is in Group 18. Noble gases are very unreactive.
f3|Which scientist proposed the theory of evolution by natural selection?|Charles Darwin|Gregor Mendel|Louis Pasteur|Isaac Newton|Darwin published On the Origin of Species in 1859.
f3|Which type of electromagnetic wave has the highest frequency?|Gamma rays|Radio waves|Visible light|Microwaves|Gamma rays have the highest frequency and the most energy.

# English
a1|Which letter does "Apple" start with?|A|B|C|D|Apple starts with the letter A.
a1|Which word rhymes with "cat"?|Hat|Dog|Sun|Pen|Cat and hat end with the same sound.
a1|What is the first letter of the alphabet?|A|Z|M|B|The alphabet begins A, B, C...
a1|Which animal's name starts with D?|Dog|Cat|Fish|Bird|Dog starts with the letter D.
a2|Which letter comes after B?|C|A|D|E|The alphabet goes A, B, C.
a2|What is the opposite of "up"?|Down|Over|High|Top|Up and down are opposites.
a2|Which word is a colour?|Red|Run|Sit|Eat|Red is a colour.
a2|Which word starts with the same sound as "ball"?|Bat|Cat|Sun|Dog|Ball and bat both start with the "b" sound.
a2|Which sound does the word "snake" start with?|sss|mmm|bbb|ttt|Snake starts with the "s" sound, like a hissing snake.
a3|Which spelling is correct?|cat|kat|cet|cot|The word for a pet that purrs is spelled c-a-t.
a3|Which word names an animal?|Rabbit|Table|Spoon|Chair|A rabbit is an animal.
a3|Which word finishes the sentence? "A dog can ___ ."|run|table|blue|cup|"Run" is something a dog can do. It is a doing word.
b1|Which word is a noun (a naming word)?|Table|Run|Quickly|Happy|A noun names a person, place or thing. A table is a thing.
b1|Which word is the opposite of "hot"?|Cold|Warm|Sunny|Big|Hot and cold are opposites.
b1|Choose the right word: "Yesterday, the cat ___ on the mat."|sat|sit|sitting|sits|"Yesterday" tells us it already happened, so we use the past tense: sat.
b1|Which letter is a vowel?|E|T|M|K|The vowels are A, E, I, O and U.
b1|Which word rhymes with "tree"?|Bee|Bat|Bag|Ten|Tree and bee both end with the "ee" sound.
b2|Choose the right word: "She ___ a book every day."|reads|read|reading|readed|"She" is one person, so the verb ends in -s: reads.
b2|What is the plural of "box"?|Boxes|Boxs|Boxen|Boxies|Words ending in x add -es: boxes.
b2|Which word is a verb (a doing word)?|Jump|Blue|Chair|Soft|Jump is something we do.
b2|Which sentence is written correctly?|I have two dogs.|i have two dogs|I has two dogs.|I have to dog.|It starts with a capital letter, uses "have" with I, and the number word "two".
b2|What is the opposite of "early"?|Late|Soon|Fast|Slow|Early and late are opposites.
b2|Which word has the same first sound as "chair"?|Cheese|Shoe|Sun|Phone|Chair and cheese both start with "ch".
b3|Which word is an adjective (a describing word)?|Tall|Jump|Table|Quickly|"Tall" describes a noun, for example "a tall tree".
b3|Choose the right word: "I can see ___ birds in the sky."|two|too|to|tow|"Two" is the number 2. The other words sound the same but mean different things.
b3|Which word is spelled correctly?|friend|freind|frend|frind|Remember: a friend is there until the end.
b3|What is the past tense of "go"?|Went|Goed|Gone|Going|"Go" is an irregular verb. Yesterday I went.
b3|Which punctuation mark ends a question?|?|.|!|,|A question mark ends a question.
c1|Which word means the same as "big"?|Large|Tiny|Thin|Short|Big and large are synonyms.
c1|Choose the right word: "They ___ playing football."|are|is|am|be|"They" is plural, so we use "are".
c1|What is the plural of "child"?|Children|Childs|Childes|Childrens|"Child" is irregular. The plural is children.
c1|Which of these is a proper noun?|Paris|city|country|river|A proper noun names one particular place or person and begins with a capital letter.
c1|Which word is the opposite of "brave"?|Cowardly|Bold|Strong|Fearless|Cowardly means afraid. It is the opposite of brave.
c1|Choose the right word: "I want to ___ a letter."|write|right|rite|wright|"Write" means to put words on paper. "Right" means correct or the opposite of left.
c2|Find the adverb: "She sang beautifully."|beautifully|She|sang|There is none|"Beautifully" tells us how she sang, so it is an adverb.
c2|Which sentence uses a comma correctly?|After lunch, we went home.|After, lunch we went home.|After lunch we, went home.|After lunch we went, home.|The comma goes after the opening phrase "After lunch".
c2|What does the prefix "un-" mean in "unhappy"?|Not|Again|Before|Very|"Un-" means "not", so unhappy means not happy.
c2|Which of these is a compound word?|Sunflower|Flowers|Running|Happily|Sunflower joins two words: sun + flower.
c2|"The wind whispered through the trees." is an example of...|Personification|Simile|Hyperbole|Alliteration|Personification gives human actions (whispering) to something that is not human.
c2|Which is the correct spelling of the word meaning "very pretty"?|Beautiful|Beutiful|Beatiful|Bueatiful|Beautiful: b-e-a-u-t-i-f-u-l.
c3|Which sentence is correct?|She doesn't like tea.|She don't like tea.|She not like tea.|She doesn't likes tea.|With "she" we use "doesn't", followed by the base verb "like".
c3|What does the idiom "a piece of cake" mean?|Very easy|Delicious|Very small|Expensive|It means something is very easy to do.
c3|Which word means the same as "enormous"?|Gigantic|Tiny|Ordinary|Slow|Enormous and gigantic both mean extremely big.
c3|What is the past tense of "teach"?|Taught|Teached|Taughted|Tought|"Teach" is irregular: teach, taught, taught.
c3|"As cold as ice" is an example of a...|Simile|Metaphor|Rhyme|Question|A simile compares two things using "as" or "like".
c3|Choose the right word: "___ going to the park."|They're|Their|There|Thier|"They're" is short for "they are".
d1|Which word is the noun? "The elephant trumpeted loudly."|elephant|trumpeted|loudly|The|"Elephant" names an animal, so it is the noun.
d1|Which word means the same as "rapid"?|Swift|Slow|Late|Heavy|Rapid and swift both mean fast.
d1|Choose the right word: "She is taller ___ her sister."|than|then|that|thin|"Than" is used to compare two things.
d1|Which word is a conjunction (a joining word)?|but|run|blue|quickly|"But" joins two parts of a sentence.
d1|What is the past participle of "write"?|Written|Wrote|Writed|Writing|We say "I have written" (not "I have wrote").
d1|What is the opposite of "generous"?|Selfish|Kind|Giving|Helpful|A generous person shares. A selfish person does not.
d2|Which sentence is in the passive voice?|The cake was eaten by Tom.|Tom ate the cake.|Tom is eating the cake.|Tom will eat the cake.|In the passive voice the thing receiving the action comes first: "The cake was eaten".
d2|What does the idiom "spill the beans" mean?|Reveal a secret|Make a mess|Cook dinner|Waste food|It means to tell something that was meant to be secret.
d2|Which word has a silent letter?|Knight|Table|Mother|Planet|The k in knight is silent.
d2|Choose the right word: "The team ___ celebrating its win."|is|are|were|be|A team is one group, so we use the singular verb "is".
d2|What is a metaphor?|Saying one thing IS another|Comparing with "like" or "as"|Repeating a starting sound|A word that sounds like its meaning|Example of a metaphor: "The classroom was a zoo."
d2|Which word is the opposite of "ancient"?|Modern|Old|Historic|Aged|Ancient means very old. Modern means of the present time.
d3|"Peter Piper picked a peck of pickled peppers" is an example of...|Alliteration|Onomatopoeia|Simile|Metaphor|Alliteration repeats the same starting sound in nearby words.
d3|Which sentence is punctuated correctly?|"Let's go," said Maya.|"Lets go" said Maya.|"Let's go", said Maya|Let's go, said Maya.|The comma goes inside the speech marks, and Let's needs an apostrophe.
d3|Which word means "to make something better"?|Improve|Worsen|Ignore|Destroy|Improve means to make or become better.
d3|Choose the right word: "He ___ the ball over the fence."|threw|through|though|thought|"Threw" is the past tense of throw.
d3|Which is the correct spelling?|Necessary|Neccessary|Necesary|Necessery|Necessary has one c and two s: n-e-c-e-s-s-a-r-y.
d3|What does the prefix "re-" mean in "rewrite"?|Again|Not|Before|Under|"Re-" means again. To rewrite is to write again.
e1|Which sentence contains a simile?|He runs like the wind.|Time is a thief.|The sun smiled.|Silence is golden.|A simile compares using "like" or "as".
e1|Choose the right word: "The weather will ___ our plans."|affect|effect|afect|effects|"Affect" is a verb meaning to influence. "Effect" is usually a noun.
e1|What is the opposite of "benevolent"?|Malevolent|Generous|Kind|Gentle|Benevolent means well-meaning. Malevolent means wishing harm.
e1|A word that sounds like the noise it names is called...|Onomatopoeia|Alliteration|Simile|Metaphor|Words like buzz, boom and splash are onomatopoeia.
e1|Which is a complex sentence?|Although it rained, we played outside.|We played outside.|It rained and we played.|Rain fell.|A complex sentence has a main clause and a dependent clause ("Although it rained").
e1|Which word is closest in meaning to "reluctant"?|Unwilling|Eager|Cheerful|Quick|Reluctant means not wanting to do something.
e2|Which sentence contains a metaphor?|Time is a thief.|He runs like the wind.|As brave as a lion.|She sings loudly.|A metaphor says one thing IS another. It does not use "like" or "as".
e2|What does "ubiquitous" mean?|Found everywhere|Very rare|Extremely old|Easily broken|Something ubiquitous seems to be in every place at once.
e2|Choose the right word: "___ a beautiful day."|It's|Its|Its'|Is it|"It's" is short for "it is". "Its" shows ownership.
e2|Choose the right word: "I haven't seen him ___ Monday."|since|for|from|by|"Since" is used with a point in time (Monday). "For" is used with a length of time.
e2|Which word is a preposition?|Beneath|Quickly|Dream|Brilliant|A preposition shows position or relationship, like beneath, over or between.
e2|What is the "main idea" of a paragraph?|Its central point|Its first word|Its longest sentence|Its last word|The main idea is what the paragraph is mostly about.
e3|What is an oxymoron?|Two opposite words put together|An exaggeration|A repeated sound|A comparison using "like"|Examples are "deafening silence" and "bittersweet".
e3|Which sentence uses a semicolon correctly?|I like tea; she likes coffee.|I like; tea she likes coffee.|I like tea; and coffee.|I; like tea she likes coffee.|A semicolon joins two closely related complete sentences.
e3|What does "hyperbole" mean?|Deliberate exaggeration|Understatement|Repetition|A comparison using "like"|Example: "I've told you a million times."
e3|Which word is closest in meaning to "meticulous"?|Careful|Careless|Quick|Lazy|Meticulous means showing great attention to detail.
e3|Choose the right verb: "Neither the teacher nor the students ___ ready."|were|was|is|be|With "neither...nor" the verb agrees with the nearer subject, "students" (plural).
e3|What does "ephemeral" mean?|Lasting a very short time|Very large|Extremely loud|Hidden|Ephemeral things, like morning dew, last only briefly.
f1|What is irony?|A contrast between what is expected and what happens|Repetition of sounds|A comparison using "like"|An exaggeration|Irony is when the outcome is the opposite of what we expect.
f1|Which sentence is grammatically correct?|Each of the students has a book.|Each of the students have a book.|Each students has a book.|Each of student has a book.|"Each" is singular, so it takes "has".
f1|What is an antonym of "verbose"?|Concise|Wordy|Lengthy|Loud|Verbose means using too many words. Concise means short and clear.
f1|What does "pragmatic" mean?|Practical and realistic|Dreamy|Angry|Careless|A pragmatic person focuses on what works in reality.
f1|Which is the correct spelling of the word meaning "something that happens"?|Occurrence|Occurence|Ocurrence|Occurrance|Occurrence has a double c and a double r.
f1|"Her voice was music to his ears." is an example of a...|Metaphor|Simile|Pun|Question|It says her voice WAS music, without "like" or "as". That is a metaphor.
f2|Choose the right phrase: "Had I known, I ___ come earlier."|would have|will have|would|had|This is the third conditional: Had + past participle, would have + past participle.
f2|What is a "protagonist"?|The main character|The villain|The narrator only|The setting|The protagonist is the central character of a story.
f2|Which word means "to make less severe"?|Mitigate|Aggravate|Exacerbate|Intensify|To mitigate a problem is to reduce its seriousness.
f2|Which phrase uses "fewer" correctly?|Fewer apples|Fewer water|Fewer sugar|Fewer rice|"Fewer" is for things we can count. "Less" is for things we cannot count.
f2|In "Despite the rain, the match continued", what is "Despite"?|A preposition|A conjunction|A verb|An adverb|"Despite" is followed by a noun phrase, so it is a preposition.
f2|What is an allegory?|A story with a hidden deeper meaning|A short poem|A list of facts|A type of rhyme|An allegory uses characters and events to represent bigger ideas, like in Animal Farm.
f3|Which of these is a paradox?|Less is more.|Cold as ice.|Boom!|He ran fast.|A paradox seems contradictory but can still contain truth.
f3|"The pen is mightier than the sword" is an example of...|Metonymy|Simile|Onomatopoeia|Alliteration|Metonymy uses one thing to stand for another: pen = writing, sword = force.
f3|What does "ambiguous" mean?|Open to more than one meaning|Very clear|Extremely angry|Very loud|An ambiguous sentence can be understood in more than one way.
f3|What is a euphemism?|A mild word used for something harsh|A harsh word used for something mild|A repeated word|A rhyming word|"Passed away" is a euphemism for "died".
f3|"It was the best of times, it was the worst of times" is an example of...|Antithesis|Alliteration|Simile|Onomatopoeia|Antithesis places opposite ideas next to each other for effect.
f3|Which sentence uses the subjunctive mood correctly?|If I were you, I would apologise.|If I was you, I would apologise.|If I am you, I would apologise.|If I be you, I will apologise.|For wishes and imaginary situations we use "were", even with "I".

# Reasoning
a1|Which one is different? 🍎 🍌 🚗 🍇|🚗|🍎|🍌|🍇|The car is not a fruit.
a1|What comes next? 🔴 🔵 🔴 🔵 ?|🔴|🔵|🟢|🟡|The colours repeat: red, blue, red, blue, so red comes next.
a1|Which is bigger?|An elephant|An ant|They are the same|Cannot say|An elephant is much bigger than an ant.
a1|Which shape has 3 sides?|Triangle|Circle|Square|Star|A triangle has 3 sides.
a2|Which one is different? Dog, Cat, Cow, Spoon|Spoon|Dog|Cat|Cow|A spoon is not an animal.
a2|What comes next? 🔺 ⬜ 🔺 ⬜ ?|🔺|⬜|⭕|⭐|The pattern repeats: triangle, square, triangle, square, triangle.
a2|Which is heavier?|A rock|A feather|They are the same|Cannot tell|A rock is much heavier than a feather.
a2|What do we use to cut paper?|Scissors|Spoon|Shoe|Pencil|Scissors are made for cutting.
a2|What happens first in a day?|Morning|Night|Evening|Afternoon|The day begins with morning.
a3|Which goes with shoes?|Socks|Hat|Spoon|Book|We wear socks with shoes.
a3|What comes next? 1, 2, 1, 2, 1, ?|2|1|3|4|The pattern is 1, 2, 1, 2... so 2 comes next.
a3|Mum is older than me. Who is younger?|Me|Mum|Both|Neither|Mum is older, so I am younger.
b1|Which word does not belong? Red, Blue, Green, Chair|Chair|Red|Blue|Green|Red, blue and green are colours. A chair is not.
b1|Hot is to cold as up is to ___ .|Down|High|Sky|Top|Hot and cold are opposites, and so are up and down.
b1|What comes next? 2, 4, 6, 8, ?|10|9|12|11|We add 2 each time: 8 + 2 = 10.
b1|What comes next? ⭕ 🔺 ⭕ 🔺 ?|⭕|🔺|⬜|⭐|The pattern repeats circle, triangle, so circle comes next.
b1|A bird lives in a nest. A bee lives in a ___ .|Hive|Honey|Flower|Wing|A hive is a bee's home.
b2|Tom is taller than Sam. Sam is taller than Raj. Who is the tallest?|Tom|Sam|Raj|Cannot tell|Tom > Sam > Raj, so Tom is the tallest.
b2|What comes next? 5, 10, 15, 20, ?|25|30|22|24|We add 5 each time.
b2|Which number is different? 3, 6, 9, 11|11|3|6|9|3, 6 and 9 are in the 3 times table. 11 is not.
b2|If A = 1, B = 2 and C = 3, what is D?|4|5|3|6|The letters follow the alphabet: D is the 4th letter.
b2|What day comes after Monday?|Tuesday|Sunday|Wednesday|Friday|The days go Monday, Tuesday, Wednesday...
b2|There are 3 red balls and 2 blue balls. How many balls altogether?|5|6|4|1|3 + 2 = 5.
b3|Which number is missing? 1, 3, 5, ?, 9|7|6|8|10|These are odd numbers going up by 2. After 5 comes 7.
b3|Sara is 7th in the line from the front and 7th from the back. How many children are in the line?|13|14|12|15|7 + 7 − 1 = 13 (Sara is counted twice, so we take one away).
b3|A pen is used to write. A knife is used to ___ .|Cut|Eat|Cook|Sharp|A pen is for writing and a knife is for cutting.
b3|What comes next? A, C, E, G, ?|I|H|J|K|We skip one letter each time. After G (skip H) comes I.
b3|A clock shows 6 o'clock. What will it show after 3 hours?|9 o'clock|3 o'clock|8 o'clock|12 o'clock|6 + 3 = 9 o'clock.
c1|Which number is the odd one out? 16, 25, 36, 40|40|16|25|36|16, 25 and 36 are square numbers. 40 is not.
c1|What comes next? 3, 6, 12, 24, ?|48|36|30|27|Each number is doubled.
c1|A book is for reading. A fork is for ___ .|Eating|Cooking|Washing|Cutting|A fork is used for eating.
c1|What letter comes next? A, B, D, G, ?|K|J|H|L|The gaps grow by 1 each time: +1, +2, +3, +4. G + 4 = K.
c1|If Monday is day 1, which day is day 5?|Friday|Thursday|Saturday|Sunday|Monday 1, Tuesday 2, Wednesday 3, Thursday 4, Friday 5.
c1|Which is the odd one out? Square, Triangle, Cube, Circle|Cube|Square|Triangle|Circle|A cube is 3D. The others are flat 2D shapes.
c2|If CAT is written as DBU, how is DOG written?|EPH|DPH|EOH|FPI|Each letter moves one step forward in the alphabet: D→E, O→P, G→H.
c2|Ria is taller than Mia. Mia is taller than Zoe. Who is the shortest?|Zoe|Mia|Ria|Cannot tell|Ria > Mia > Zoe, so Zoe is the shortest.
c2|What comes next? 1, 4, 9, 16, ?|25|20|24|36|These are square numbers: 1², 2², 3², 4², so next is 5² = 25.
c2|What number is missing? 2, 6, 12, 20, ?|30|28|24|26|The gaps are 4, 6, 8, so the next gap is 10: 20 + 10 = 30.
c2|A farmer has 17 sheep. All but 9 run away. How many are left?|9|8|17|0|"All but 9" means 9 stay behind.
c2|You face north and turn right. Which way are you facing?|East|West|South|North|Turning right from north points you east.
c3|Which does not belong? Mercury, Venus, Moon, Mars|Moon|Mercury|Venus|Mars|Mercury, Venus and Mars are planets. The Moon is not.
c3|A square is cut along both diagonals. How many small triangles are made?|4|2|6|8|Two crossing diagonals cut a square into 4 triangles.
c3|Today is Wednesday. What day will it be in 10 days?|Saturday|Friday|Sunday|Monday|10 = 7 + 3. After 7 days it is Wednesday again, then 3 more days: Saturday.
c3|Four friends sit in a row. Ali is left of Ben, Ben is left of Chen and Chen is left of Dev. Who is second from the left?|Ben|Ali|Chen|Dev|The order is Ali, Ben, Chen, Dev. Ben is second.
c3|How many faces does a cube have?|6|4|8|12|A cube has 6 square faces.
c3|4 → 16, 5 → 25, 6 → ?|36|30|11|42|The rule is "multiply the number by itself": 6 × 6 = 36.
d1|What is the missing number? 5, 11, 23, 47, ?|95|94|93|96|Double and add 1: 47 × 2 + 1 = 95.
d1|Your mother's father is your...|Grandfather|Uncle|Cousin|Nephew|Your parent's father is your grandfather.
d1|If TOP is written as 20-15-16, how is CAT written?|3-1-20|1-3-20|3-1-19|2-1-20|The letters become their place in the alphabet. C = 3, A = 1, T = 20.
d1|Which is the odd one out? 27, 64, 125, 100|100|27|64|125|27, 64 and 125 are cube numbers (3³, 4³, 5³). 100 is not.
d1|Doctor : Hospital :: Teacher : ?|School|Class|Book|Student|A doctor works in a hospital. A teacher works in a school.
d1|What comes next? Z, X, V, T, ?|R|S|Q|P|We go backwards skipping one letter each time. After T (skip S) comes R.
d2|A is B's sister. B is C's father. How is A related to C?|Aunt|Mother|Cousin|Sister|A is the sister of C's father, so she is C's aunt.
d2|What comes next? 2, 3, 5, 8, 13, ?|21|18|20|24|Each number is the sum of the two before it: 8 + 13 = 21.
d2|A train 100 m long passes a pole in 10 seconds. What is its speed?|10 m/s|100 m/s|1 m/s|20 m/s|Speed = distance ÷ time = 100 ÷ 10 = 10 m/s.
d2|Two numbers add up to 15 and multiply to 56. What is the larger number?|8|7|9|6|7 + 8 = 15 and 7 × 8 = 56. The larger one is 8.
d2|3 workers dig a hole in 6 days. How many days would 6 workers take at the same speed?|3|12|2|9|Double the workers means half the time: 6 ÷ 2 = 3 days.
d2|2 pencils cost 10 coins. How many pencils can you buy with 50 coins?|10|5|25|20|One pencil costs 5 coins. 50 ÷ 5 = 10 pencils.
d3|In a code, S = 2, E = 1, A = 4, R = 6, C = 7 and H = 3. What is the code for SEARCH?|214673|214763|241673|214637|Replace each letter: S2 E1 A4 R6 C7 H3 gives 214673.
d3|P, Q, R, S and T run a race. P finished after R but before Q. S finished last. T finished before R. Who won?|T|R|P|Q|The order is T, R, P, Q, S. T won.
d3|A clock gains 5 minutes every hour. It is set right at 12:00 noon. What time will it show after 6 real hours?|6:30|6:05|6:25|7:00|It gains 6 × 5 = 30 minutes. So it shows 6:30.
d3|How many squares of all sizes are in a 3 × 3 grid of small squares?|14|9|10|13|9 small squares + 4 squares of size 2 × 2 + 1 big square = 14.
d3|Which pair is the odd one out? AZ, BY, CX, DW, EU|EU|AZ|BY|DW|The pairs mirror each other in the alphabet (their places add up to 27). E + U = 5 + 21 = 26, so EU is the odd one.
d3|A bat and a ball cost $1.10 together. The bat costs $1.00 more than the ball. How much is the ball?|5 cents|10 cents|1 cent|15 cents|Ball = x, bat = x + 1.00. So 2x + 1.00 = 1.10 and x = 0.05.
e1|What is the next number? 2, 5, 10, 17, 26, ?|37|36|35|38|The gaps are 3, 5, 7, 9, so the next gap is 11. 26 + 11 = 37.
e1|Which is the odd one out? 121, 144, 169, 200|200|121|144|169|The others are perfect squares: 11², 12², 13².
e1|Raj points to a photo and says, "He is my mother's only brother's son." How is the man in the photo related to Raj?|Cousin|Brother|Uncle|Nephew|Raj's mother's brother is his uncle. The uncle's son is Raj's cousin.
e1|5 machines make 5 items in 5 minutes. How long would 100 machines take to make 100 items?|5 minutes|100 minutes|20 minutes|1 minute|Each machine makes 1 item in 5 minutes. So 100 machines make 100 items in 5 minutes.
e1|Ice : Cold :: Fire : ?|Hot|Smoke|Burn|Red|Ice is cold and fire is hot. The link is the main quality.
e1|What comes next? ABD, BCE, CDF, ?|DEG|DFG|CEG|DEF|Every letter moves one step forward each time: CDF → DEG.
e2|If MANGO is written as NBOHP, how is APPLE written?|BQQMF|BQQLF|AQQMF|BPPMF|Each letter moves one step forward: A→B, P→Q, P→Q, L→M, E→F.
e2|A's age is twice B's age. In 10 years A will be 1.5 times as old as B. How old is B now?|10|5|15|20|If B = 10, then A = 20. In 10 years they will be 30 and 20, and 30 = 1.5 × 20.
e2|What comes next? 3, 9, 27, 81, ?|243|162|324|729|Each number is multiplied by 3.
e2|Mia walks 4 km east, then 3 km north. How far is she from where she started in a straight line?|5 km|7 km|4 km|3 km|This is a 3-4-5 right triangle, so the straight-line distance is 5 km.
e2|Which number does not belong? 2, 3, 5, 9, 11, 13|9|2|11|13|All the others are prime numbers. 9 = 3 × 3.
e2|Today is Thursday. What day was it 100 days ago?|Tuesday|Monday|Wednesday|Sunday|100 = 14 weeks + 2 days. Two days before Thursday is Tuesday.
e3|In a row of 40 students, Anu is 12th from the left. What is her position from the right?|29th|28th|30th|27th|40 − 12 + 1 = 29th.
e3|The sum of 3 consecutive odd numbers is 63. What is the largest?|23|21|25|19|The numbers are 19, 21 and 23. They add up to 63.
e3|A cube painted on all faces is cut into 27 equal small cubes. How many small cubes have exactly 2 painted faces?|12|8|6|24|Only the cubes in the middle of each of the cube's 12 edges have exactly 2 painted faces.
e3|6 people shake hands once with every other person. How many handshakes are there?|15|12|30|36|6 × 5 ÷ 2 = 15 (each handshake is counted twice if we just do 6 × 5).
e3|What comes next? 1, 1, 2, 6, 24, ?|120|60|96|48|Multiply by 1, 2, 3, 4, then 5: 24 × 5 = 120.
e3|Three boxes are labelled "Apples", "Oranges" and "Mixed", but every label is wrong. You take one fruit from the box labelled "Mixed" and it is an apple. What is inside that box?|Only apples|Only oranges|A mix|Cannot tell|The label "Mixed" is wrong, so the box is not mixed. It gave an apple, so it holds only apples.
f1|What comes next? 1, 8, 27, 64, ?|125|100|216|81|These are cube numbers: 1³, 2³, 3³, 4³ and then 5³ = 125.
f1|If a : b = 2 : 3 and b : c = 4 : 5, what is a : c?|8 : 15|2 : 5|3 : 5|6 : 5|Make b equal: a : b : c = 8 : 12 : 15. So a : c = 8 : 15.
f1|All birds have wings. A penguin is a bird. What must be true?|A penguin has wings|A penguin can fly|All animals have wings|Wings always mean flying|If all birds have wings and a penguin is a bird, then a penguin has wings.
f1|x is 25% more than y. By what percent is y less than x?|20%|25%|15%|30%|x = 1.25y, so y = 0.8x. That is 20% less than x.
f1|What comes next? 7, 10, 16, 28, ?|52|40|44|46|The gaps double: 3, 6, 12, 24. So 28 + 24 = 52.
f1|8 people build a wall in 6 days. How many days would 12 people take at the same rate?|4|9|3|5|The job is 8 × 6 = 48 person-days. 48 ÷ 12 = 4 days.
f2|What comes next? 4, 6, 9, 13, 18, ?|24|23|25|22|The gaps go up by 1: 2, 3, 4, 5, then 6. 18 + 6 = 24.
f2|A can finish a job in 12 days and B in 24 days. How long will they take working together?|8 days|18 days|36 days|6 days|In one day they do 1/12 + 1/24 = 3/24 = 1/8 of the job. So 8 days.
f2|A man walks 10 m north, then 6 m east, then 6 m south. About how far is he from the start?|About 7.2 m|10 m|6 m|22 m|He ends 4 m north and 6 m east of the start. By Pythagoras √(16 + 36) = √52 ≈ 7.2 m.
f2|All pens are books. Some books are cups. Which conclusion is correct?|"Some pens are cups" does not necessarily follow|Some pens are definitely cups|No pens are cups|All cups are pens|The cups that are books might not be pens, so we cannot be sure.
f2|How many different arrangements can be made using the letters of the word MOM?|3|6|2|1|3! ÷ 2! = 3 (MOM, OMM, MMO), because the M is repeated.
f2|The average of 5 numbers is 20. One of them, 30, is removed. What is the average of the other 4?|17.5|20|15|22.5|Total = 100. 100 − 30 = 70. And 70 ÷ 4 = 17.5.
f3|A clock shows 3:15. What is the angle between the hour and minute hands?|7.5°|0°|15°|90°|The minute hand is at 90°. The hour hand is at 90° + 7.5° = 97.5°. The difference is 7.5°.
f3|The letters ABC repeat forever: ABCABC... What is the 100th letter?|A|B|C|D|100 = 33 groups of 3 + 1, so the 100th letter is the first letter of the pattern: A.
f3|Two trains are 100 km apart and move towards each other at 30 km/h and 20 km/h. How long until they meet?|2 hours|3 hours|5 hours|1 hour|They close the gap at 30 + 20 = 50 km/h. 100 ÷ 50 = 2 hours.
f3|What comes next? 2, 6, 12, 20, 30, ?|42|40|44|36|These numbers are n × (n + 1): 1 × 2, 2 × 3, 3 × 4... so next is 6 × 7 = 42.
f3|In a group of 100 people, 60 like tea, 50 like coffee and 20 like neither. How many like both?|30|10|20|40|80 like at least one drink. 60 + 50 − 80 = 30 like both.
f3|The 1st of a month is a Monday. What day is the 30th of that month?|Tuesday|Monday|Wednesday|Sunday|29 days later = 4 weeks + 1 day, so the 30th is a Tuesday.
'''

load_bank()
init_db()
if __name__ == "__main__":
    main()
```