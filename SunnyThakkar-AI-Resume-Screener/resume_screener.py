"""
AI Resume Screener  -  AICA Level 2 Capstone (extra project)
=============================================================

Add a set of resumes (PDF, DOCX or TXT, scanned PDFs too), paste a job
description, and the app ranks the candidates with a match score and the
skills each one has or is missing.

How it works:
  1. Read      - get the text of every resume (pypdf for PDFs, python-docx
                 for Word files; scanned PDFs are read with offline OCR)
  2. Extract   - find skills (from a built-in list of ~115 skills and their
                 other names, e.g. "ML" = "machine learning"), years of
                 experience, email and phone
  3. Compare   - score each resume against the job description:
                   60%  skill match   (share of the job's skills found)
                   30%  text match    (TF-IDF + cosine similarity)
                   10%  experience    (years found vs years asked for)
  4. Rank      - sort by score and show matched / missing skills
  5. Optional  - AI review of one candidate with a free Gemini / Groq key

Run:   python resume_screener.py
CLI:   python resume_screener.py job.txt resume1.pdf resume2.docx ...
Demo:  python resume_screener.py --demo   (loads the sample files)
Needs: pip install -r requirements.txt
"""

import csv
import json
import math
import os
import re
import sys
import threading
import urllib.error
import urllib.request
from collections import Counter

APP_NAME = "AI Resume Screener"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".resume_screener_config.json")
WEIGHTS = {"skills": 0.60, "text": 0.30, "experience": 0.10}

# ----------------------------------------------------------------------------
# Skill list. Each line: skill name = other ways people write it
# ----------------------------------------------------------------------------
SKILLS_TEXT = """
python = python3
java
javascript = js, ecmascript
typescript
c++ = cpp
c#
c language = c programming
go language = golang
r language = r programming, rstudio
sql = mysql, postgresql, postgres, sql server, t-sql, pl/sql, sqlite, oracle sql
nosql = mongodb, cassandra, dynamodb, couchdb
html = html5
css = css3, sass, tailwind, bootstrap
php
ruby = ruby on rails, rails
swift
kotlin
rust
scala
matlab
bash = shell scripting, shell script, powershell
excel = ms excel, microsoft excel, advanced excel, vlookup, pivot tables, pivot table
power bi = powerbi
tableau
looker
google sheets
power query
dax
vba = excel macros
sas
spss
statistics = statistical analysis, hypothesis testing, regression analysis, a/b testing
data analysis = data analytics, data analyst, analysing data, analyzing data, analysed data, analyzed data
data visualization = data visualisation, dashboards, dashboard, data viz
data cleaning = data wrangling, data preprocessing, data preparation
etl = data pipelines, data pipeline, elt
data warehousing = data warehouse, snowflake, redshift, bigquery
big data = hadoop, spark, pyspark, hive
machine learning = ml, scikit-learn, sklearn
deep learning = neural networks, neural network, cnn, rnn, lstm
tensorflow = keras
pytorch
nlp = natural language processing, text mining, spacy, nltk
computer vision = opencv, image processing
generative ai = genai, gen ai, llm, llms, large language models, prompt engineering, chatgpt, rag
pandas
numpy
matplotlib = seaborn, plotly
jupyter = jupyter notebook
forecasting = time series
predictive modeling = predictive modelling, predictive analytics
django
flask
fastapi
react = react.js, reactjs
angular
vue = vue.js
node.js = nodejs, node, express.js, express
rest api = rest apis, restful, api development, apis
graphql
microservices
git = github, gitlab, version control, bitbucket
docker = containers
kubernetes = k8s
ci/cd = jenkins, github actions, continuous integration
aws = amazon web services, ec2, s3, lambda
azure = microsoft azure
gcp = google cloud, google cloud platform
linux = unix, ubuntu
cloud computing = cloud
devops
software testing = unit testing, pytest, junit, selenium, qa testing, test automation
agile = scrum, kanban, sprint planning
jira = confluence
project management = pmp, prince2, project planning
product management = product roadmap, product owner
business analysis = business analyst, requirements gathering, brd
stakeholder management = stakeholder engagement, stakeholders
sap = sap erp, sap fico, sap mm, s/4hana
erp = oracle erp, odoo, microsoft dynamics
crm = salesforce, hubspot, zoho crm
accounting = bookkeeping, general ledger, accounts payable, accounts receivable
financial analysis = financial modeling, financial modelling, financial reporting, budgeting
auditing = audit, internal audit
taxation = vat, tax
ifrs = gaap
quickbooks = tally, xero
digital marketing = online marketing, performance marketing
seo = search engine optimization
sem = google ads, ppc, adwords
social media marketing = social media, instagram marketing, facebook ads
content writing = copywriting, content creation, blogging
google analytics = ga4
email marketing = mailchimp
market research = market analysis, competitor analysis
sales* = sales executive, sales representative, sales manager, business development, lead generation, b2b sales, sales targets
customer service = customer support, client service, customer relationship
recruitment = talent acquisition, recruiting, hiring, sourcing
hr management = human resources, hrms, payroll, onboarding, employee relations
training = coaching, mentoring
ui/ux design = ui design, ux design, user experience, user interface, wireframing, figma, adobe xd
graphic design = photoshop, illustrator, canva, adobe creative suite, indesign
autocad = cad, solidworks
supply chain = logistics, procurement, inventory management, warehouse management
operations management = operations, process improvement, six sigma, lean
cybersecurity = information security, network security, penetration testing, siem
networking = ccna, tcp/ip, routing, switching
communication = communication skills, presentation skills, public speaking, presentations, presented, presenting
teamwork = team player, collaboration, cross-functional
leadership = team lead, team leadership, people management, managed a team
problem solving = analytical skills, critical thinking, analytical thinking
time management = multitasking, prioritization, organisational skills, organizational skills
english = english language, fluent english
arabic
hindi
french
"""


def _parse_skills(text):
    skills = {}
    for line in text.strip().splitlines():
        name, _, alts = line.partition("=")
        name = name.strip()
        names = [a.strip() for a in alts.split(",") if a.strip()]
        if name.endswith("*"):          # "*" = match only the other names
            name = name[:-1].strip()
        else:
            names.insert(0, name)
        skills[name] = names
    return skills


SKILLS = _parse_skills(SKILLS_TEXT)


def _skill_pattern(names):
    parts = []
    for n in sorted(names, key=len, reverse=True):
        p = re.escape(n.lower()).replace(r"\ ", r"[\s\-]*")
        parts.append(p)
    # no letter/number right before or after (so "r" does not match "rust")
    return re.compile(r"(?<![a-z0-9+#])(?:" + "|".join(parts) + r")(?![a-z0-9+#])")


# One-letter languages ("C", "R") make too many false hits, so they are only
# matched as "C language" / "R programming". A "*" after a skill name (like
# "sales*") means the bare word is too common ("sales data"), so only the
# other names count.
SKILL_PATTERNS = {s: _skill_pattern(n) for s, n in SKILLS.items()}


def find_skills(text):
    low = " " + text.lower() + " "
    return {s for s, pat in SKILL_PATTERNS.items() if pat.search(low)}


# ----------------------------------------------------------------------------
# 1. Read resumes (PDF / DOCX / TXT, scanned PDFs with OCR)
# ----------------------------------------------------------------------------
def clean_text(text):
    text = text.replace("•", " ").replace("", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"-\n(\w)", r"\1", text)
    return re.sub(r"\s*\n\s*", "\n", text).strip()


_word_cost, _max_word = None, 0


def _load_words():
    """English words sorted by frequency (wordninja, MIT), used to split
    words that the OCR glued together: 'machinelearning' -> 'machine learning'."""
    global _word_cost, _max_word
    import gzip
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "english_words.txt.gz")
    _word_cost = {}
    if not os.path.exists(path):
        return
    with gzip.open(path, "rt", encoding="utf-8") as f:
        words = f.read().split()
    log_n = math.log(len(words))
    _word_cost = {w: math.log((i + 1) * log_n) for i, w in enumerate(words)}
    _max_word = max(len(w) for w in words)


def split_glued(word):
    if _word_cost is None:
        _load_words()
    low = word.lower()
    if not _word_cost or len(word) < 6 or low in _word_cost:
        return word
    cost = [0.0]
    for i in range(1, len(low) + 1):
        cost.append(min(c + _word_cost.get(low[i - k - 1:i], 9e9)
                        for k, c in enumerate(reversed(cost[max(0, i - _max_word):i]))))
    parts, i = [], len(low)
    while i > 0:
        best = min((c + _word_cost.get(low[i - k - 1:i], 9e9), k + 1)
                   for k, c in enumerate(reversed(cost[max(0, i - _max_word):i])))
        parts.append(word[i - best[1]:i])
        i -= best[1]
    return " ".join(reversed(parts))


def fix_ocr_spacing(text):
    text = re.sub(r"([,;:!?])([A-Za-z])", r"\1 \2", text)               # "data,Strong"
    text = re.sub(r"(?<=[a-z])\.(?=[A-Z][a-z])", ". ", text)                 # "data.Strong"
    text = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", text)          # "with3years"
    text = re.sub(r"(?<=[A-Za-z])(?=\+\d)", " ", text)                     # "example.com+968"
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)                       # "SoharUniversity"
    text = re.sub(r"\bBl\b", "BI", text)                                     # "Power Bl"
    # Split long glued words, but never inside an email or web address.
    return re.sub(r"(?<![\w@.])[A-Za-z]{7,}(?![\w@])",
                  lambda m: split_glued(m.group(0)), text)


_ocr_engine = None


def ocr_available():
    try:
        import pypdfium2  # noqa: F401
        import rapidocr_onnxruntime  # noqa: F401
        return True
    except ImportError:
        return False


def _ocr_image(image):
    import numpy as np
    result, _ = _ocr_engine(np.array(image))
    if not result:
        return ""
    rows = sorted(result, key=lambda r: (r[0][0][1], r[0][0][0]))
    lines, current, last_y = [], [], None
    for box, text, _conf in rows:
        y, height = box[0][1], abs(box[3][1] - box[0][1]) or 10
        if last_y is not None and abs(y - last_y) > height / 2:
            lines.append(" ".join(current))
            current = []
        current.append(text)
        last_y = y
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def ocr_page(pdf_path, page_index):
    global _ocr_engine
    import pypdfium2 as pdfium
    from rapidocr_onnxruntime import RapidOCR
    if _ocr_engine is None:
        _ocr_engine = RapidOCR()
        _ocr_engine.text_score = 0.1
        _ocr_engine.use_angle_cls = False
        _ocr_engine.use_cls = False
        det = getattr(_ocr_engine, "text_detector", None) or getattr(_ocr_engine, "text_det", None)
        if det is not None and hasattr(det, "postprocess_op"):
            det.postprocess_op.unclip_ratio = 1.3
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        return _ocr_image(pdf[page_index].render(scale=1.6).to_pil().convert("RGB"))
    finally:
        pdf.close()


def read_pdf(path, progress=None):
    from pypdf import PdfReader
    reader = PdfReader(path)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError("password protected")
    texts, used_ocr = [], False
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if len(text.strip()) < 20:
            if not ocr_available():
                continue
            if progress:
                progress(f"OCR: {os.path.basename(path)} page {i + 1}...")
            text = fix_ocr_spacing(ocr_page(path, i))
            used_ocr = True
        texts.append(text)
    if not "".join(texts).strip() and not ocr_available():
        raise ValueError("scanned PDF; install OCR: pip install rapidocr_onnxruntime pypdfium2")
    return "\n".join(texts), used_ocr


def read_docx(path):
    import docx
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs]
    for table in d.tables:
        for row in table.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    return "\n".join(parts)


def read_document(path, progress=None):
    """Return (text, used_ocr) for a PDF, DOCX or TXT file."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text, used_ocr = read_pdf(path, progress)
    elif ext == ".docx":
        text, used_ocr = read_docx(path), False
    elif ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text, used_ocr = f.read(), False
    else:
        raise ValueError("unsupported file type (use PDF, DOCX or TXT)")
    return clean_text(text), used_ocr


# ----------------------------------------------------------------------------
# 2. Extract details
# ----------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-()]{7,}\d)")
YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years?|yrs?)", re.I)
YEAR_RANGE_RE = re.compile(
    r"((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current|now|date)", re.I)


def guess_name(text, path):
    for line in text.splitlines()[:6]:
        line = line.strip()
        words = line.split()
        if (1 < len(words) <= 4 and not EMAIL_RE.search(line)
                and not any(ch.isdigit() for ch in line)
                and all(w[0].isupper() for w in words if w[0].isalpha())
                and line.lower() not in ("curriculum vitae", "resume")):
            return line.title() if line.isupper() else line
    return os.path.splitext(os.path.basename(path))[0].replace("_", " ")


def years_of_experience(text):
    """Largest 'N years' written in the resume, or the span of work dates."""
    stated = [int(m.group(1)) for m in YEARS_RE.finditer(text) if int(m.group(1)) <= 45]
    from datetime import date
    this_year = date.today().year
    spans = []
    for a, b in YEAR_RANGE_RE.findall(text):
        end = this_year if not b[0].isdigit() else int(b)
        if 1970 <= int(a) <= end <= this_year:
            spans.append((int(a), end))
    span_years = 0
    if spans:
        # Education dates are also ranges, so only count ranges after the
        # earliest one ends (a rough but simple rule).
        spans.sort()
        work = spans[1:] if len(spans) > 1 else spans
        span_years = max(e for _, e in work) - min(s for s, _ in work)
    return max(stated + [span_years]) if (stated or span_years) else 0


def required_years(jd_text):
    found = [int(m.group(1)) for m in YEARS_RE.finditer(jd_text) if int(m.group(1)) <= 20]
    return min(found) if found else 0


# ----------------------------------------------------------------------------
# 3. TF-IDF and cosine similarity (written from scratch)
# ----------------------------------------------------------------------------
STOPWORDS = set("""
a about above after again all am an and any are as at be because been before
being below between both but by can could did do does doing during each few for
from further had has have having he her here him his how i if in into is it its
just me more most my no nor not now of off on once only or other our out over own
same she should so some such than that the their them then there these they this
those through to too under until up very was we were what when where which while
who will with would you your role job candidate candidates looking ideal strong
good excellent ability able work working experience required requirements preferred
plus responsibilities including must years year etc using use team company
""".split())


def stem(word):
    for suffix in ("ingly", "ing", "ies", "ed", "es", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def tokenize(text):
    words = re.findall(r"[a-z][a-z0-9+#.]*[a-z0-9+#]|[a-z]", text.lower())
    return [stem(w) for w in words if w not in STOPWORDS and len(w) > 1]


def tfidf_similarities(jd_text, resume_texts):
    """Cosine similarity between the job description and each resume."""
    docs = [Counter(tokenize(t)) for t in [jd_text] + resume_texts]
    n = len(docs)
    df = Counter()
    for d in docs:
        df.update(d.keys())
    idf = {t: math.log((1 + n) / (1 + f)) + 1 for t, f in df.items()}

    def vec(d):
        v = {t: (1 + math.log(c)) * idf[t] for t, c in d.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    jd = vec(docs[0])
    return [sum(jd.get(t, 0) * x for t, x in vec(d).items()) for d in docs[1:]]


# ----------------------------------------------------------------------------
# 4. Score and rank
# ----------------------------------------------------------------------------
class Candidate:
    def __init__(self, path, text, used_ocr=False):
        self.path, self.text, self.used_ocr = path, text, used_ocr
        self.file = os.path.basename(path)
        self.name = guess_name(text, path)
        m = EMAIL_RE.search(text)
        self.email = m.group(0) if m else ""
        m = PHONE_RE.search(text)
        self.phone = m.group(0).strip() if m else ""
        self.skills = find_skills(text)
        self.years = years_of_experience(text)
        self.score = 0.0
        self.parts = {}
        self.matched, self.missing, self.extra = [], [], []

    def verdict(self):
        if self.score >= 70:
            return "Strong match"
        if self.score >= 50:
            return "Good match"
        if self.score >= 30:
            return "Partial match"
        return "Weak match"


def rank_candidates(jd_text, candidates):
    if not jd_text.strip():
        raise ValueError("Please paste a job description first.")
    jd_skills = find_skills(jd_text)
    need_years = required_years(jd_text)
    sims = tfidf_similarities(jd_text, [c.text for c in candidates])
    best_sim = max(sims) if sims else 0
    for c, sim in zip(candidates, sims):
        c.matched = sorted(jd_skills & c.skills)
        c.missing = sorted(jd_skills - c.skills)
        c.extra = sorted(c.skills - jd_skills)
        skill_part = len(c.matched) / len(jd_skills) if jd_skills else sim
        # Long JDs and resumes rarely share many words, so the text score is
        # scaled against a realistic ceiling (0.5) instead of 1.0.
        text_part = min(1.0, sim / 0.5) if best_sim else 0.0
        if need_years:
            exp_part = min(1.0, c.years / need_years)
        else:
            exp_part = 1.0 if c.years else 0.5
        c.parts = {"skills": skill_part, "text": text_part, "experience": exp_part}
        c.score = round(100 * sum(WEIGHTS[k] * v for k, v in c.parts.items()), 1)
    return sorted(candidates, key=lambda c: c.score, reverse=True), sorted(jd_skills), need_years


def load_candidates(paths, progress=None):
    """Read every file. Returns (candidates, errors)."""
    candidates, errors = [], []
    for i, p in enumerate(paths, 1):
        if progress:
            progress(f"Reading {i}/{len(paths)}: {os.path.basename(p)}")
        try:
            text, used_ocr = read_document(p, progress)
            if len(text) < 30:
                raise ValueError("no readable text")
            candidates.append(Candidate(p, text, used_ocr))
        except Exception as e:
            errors.append(f"{os.path.basename(p)}: {e}")
    return candidates, errors


def report_text(c, jd_skills, need_years):
    lines = [f"{c.name}  ({c.file})",
             f"Score: {c.score}/100  -  {c.verdict()}",
             f"Email: {c.email or '-'}    Phone: {c.phone or '-'}",
             f"Experience found: {c.years} years" + (f" (job asks for {need_years}+)" if need_years else ""),
             "",
             "Score breakdown:",
             f"  Skill match  {round(100 * c.parts['skills'])}%  x 60%",
             f"  Text match   {round(100 * c.parts['text'])}%  x 30%",
             f"  Experience   {round(100 * c.parts['experience'])}%  x 10%",
             "",
             f"Matched skills ({len(c.matched)}/{len(jd_skills)}): " + (", ".join(c.matched) or "none"),
             "Missing skills: " + (", ".join(c.missing) or "none"),
             "Other skills: " + (", ".join(c.extra) or "none")]
    if c.used_ocr:
        lines.append("\n(Scanned resume: text was read with OCR.)")
    return "\n".join(lines)


def export_csv(path, ranked):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Rank", "Name", "File", "Score", "Verdict", "Years", "Email", "Phone",
                    "Matched skills", "Missing skills"])
        for i, c in enumerate(ranked, 1):
            w.writerow([i, c.name, c.file, c.score, c.verdict(), c.years, c.email, c.phone,
                        ", ".join(c.matched), ", ".join(c.missing)])


# ----------------------------------------------------------------------------
# 5. Optional AI review (free Gemini / Groq key)
# ----------------------------------------------------------------------------
PROVIDERS = {
    "Google Gemini (free key)": {
        "kind": "gemini", "model": "gemini-2.5-flash",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"},
    "Groq (free key)": {
        "kind": "openai", "model": "llama-3.3-70b-versatile",
        "url": "https://api.groq.com/openai/v1/chat/completions"},
    "OpenAI (paid key)": {
        "kind": "openai", "model": "gpt-4o-mini",
        "url": "https://api.openai.com/v1/chat/completions"},
}


def _post_json(url, payload, headers, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **headers},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API error {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")


def ai_review(provider, api_key, jd_text, c):
    prompt = ("You are an HR recruiter. Compare this resume to the job description. "
              "Reply in under 150 words with: a 1-line verdict, 3 strengths, 3 gaps, "
              "and 2 interview questions to ask.\n\n"
              f"JOB DESCRIPTION:\n{jd_text[:4000]}\n\nRESUME:\n{c.text[:6000]}")
    p = PROVIDERS[provider]
    if p["kind"] == "gemini":
        data = _post_json(p["url"].format(model=p["model"]),
                          {"contents": [{"parts": [{"text": prompt}]}]},
                          {"x-goog-api-key": api_key})
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError):
            raise RuntimeError(f"Unexpected reply: {str(data)[:300]}")
    data = _post_json(p["url"], {"model": p["model"], "temperature": 0.2,
                                 "messages": [{"role": "user", "content": prompt}]},
                      {"Authorization": f"Bearer {api_key}"})
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"Unexpected reply: {str(data)[:300]}")


# ----------------------------------------------------------------------------
# 6. Desktop app (Tkinter)
# ----------------------------------------------------------------------------
def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
    except Exception:
        pass


def run_app(demo=False):
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    cfg = load_config()
    state = {"paths": [], "ranked": [], "jd_skills": [], "need_years": 0}

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("1250x760")
    root.minsize(900, 560)
    BG, PANEL, ACCENT, TEXT = "#f4f6fb", "#ffffff", "#2f5bea", "#1d2433"
    root.configure(bg=BG)
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("H.TLabel", font=("Segoe UI", 10, "bold"))
    style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground=ACCENT)
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"),
                    foreground="white", background=ACCENT)
    style.map("Accent.TButton", background=[("active", "#2348c2")])
    style.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    top = ttk.Frame(root, padding=(12, 10))
    top.pack(fill="x")
    ttk.Label(top, text="🧑‍💼 " + APP_NAME, style="Title.TLabel").pack(side="left")
    status = ttk.Label(top, text="Add resumes and paste a job description.")
    status.pack(side="right")

    body = ttk.Frame(root, padding=(12, 0, 12, 12))
    body.pack(fill="both", expand=True)
    body.columnconfigure(0, weight=2)
    body.columnconfigure(1, weight=3)
    body.rowconfigure(1, weight=3)
    body.rowconfigure(3, weight=2)

    # --- left: job description + resume list ------------------------------
    jd_head = ttk.Frame(body)
    jd_head.grid(row=0, column=0, sticky="ew")
    ttk.Label(jd_head, text="1. Job description", style="H.TLabel").pack(side="left")
    jd_box = scrolledtext.ScrolledText(body, wrap="word", height=10, font=("Segoe UI", 10),
                                       bg=PANEL, fg=TEXT, relief="flat", padx=8, pady=6)
    jd_box.grid(row=1, column=0, sticky="nsew", pady=(4, 10))
    jd_box.insert("1.0", cfg.get("jd", ""))

    res_head = ttk.Frame(body)
    res_head.grid(row=2, column=0, sticky="ew")
    ttk.Label(res_head, text="2. Resumes", style="H.TLabel").pack(side="left")
    res_list = tk.Listbox(body, font=("Segoe UI", 10), bg=PANEL, fg=TEXT, relief="flat",
                          selectmode="extended", activestyle="none")
    res_list.grid(row=3, column=0, sticky="nsew", pady=(4, 6))
    left_btns = ttk.Frame(body)
    left_btns.grid(row=4, column=0, sticky="ew")

    # --- right: results ----------------------------------------------------
    ttk.Label(body, text="3. Ranking", style="H.TLabel").grid(row=0, column=1, sticky="w", padx=(12, 0))
    cols = ("rank", "name", "score", "verdict", "years", "matched", "missing")
    tree = ttk.Treeview(body, columns=cols, show="headings", height=8)
    for col, title, width, anchor in [("rank", "#", 34, "center"), ("name", "Candidate", 130, "w"),
                                      ("score", "Score", 60, "center"), ("verdict", "Verdict", 95, "w"),
                                      ("years", "Yrs", 40, "center"), ("matched", "Skills", 60, "center"),
                                      ("missing", "Missing skills", 150, "w")]:
        tree.heading(col, text=title)
        tree.column(col, width=width, anchor=anchor, stretch=(col in ("name", "missing")))
    tree.tag_configure("strong", background="#e3f6ec")
    tree.tag_configure("good", background="#eef4ff")
    tree.tag_configure("partial", background="#fff8e6")
    tree.tag_configure("weak", background="#fdecec")
    tree.grid(row=1, column=1, sticky="nsew", padx=(12, 0), pady=(4, 10))

    ttk.Label(body, text="Candidate details", style="H.TLabel").grid(row=2, column=1, sticky="w", padx=(12, 0))
    detail = scrolledtext.ScrolledText(body, wrap="word", font=("Consolas", 10), bg=PANEL,
                                       fg=TEXT, relief="flat", padx=10, pady=8)
    detail.grid(row=3, column=1, sticky="nsew", padx=(12, 0), pady=(4, 6))
    detail.configure(state="disabled")
    right_btns = ttk.Frame(body)
    right_btns.grid(row=4, column=1, sticky="ew", padx=(12, 0))

    def show_detail(text):
        detail.configure(state="normal")
        detail.delete("1.0", "end")
        detail.insert("1.0", text)
        detail.configure(state="disabled")

    def set_status(msg):
        root.after(0, lambda: status.configure(text=msg))

    def refresh_list():
        res_list.delete(0, "end")
        for p in state["paths"]:
            res_list.insert("end", os.path.basename(p))
        status.configure(text=f"{len(state['paths'])} resumes added.")

    def add_files():
        paths = filedialog.askopenfilenames(
            filetypes=[("Resumes", "*.pdf *.docx *.txt"), ("All files", "*.*")])
        for p in paths:
            if p not in state["paths"]:
                state["paths"].append(p)
        refresh_list()

    def add_folder():
        folder = filedialog.askdirectory()
        if not folder:
            return
        for f in sorted(os.listdir(folder)):
            p = os.path.join(folder, f)
            if f.lower().endswith((".pdf", ".docx", ".txt")) and p not in state["paths"]:
                state["paths"].append(p)
        refresh_list()

    def remove_selected():
        for i in reversed(res_list.curselection()):
            del state["paths"][i]
        refresh_list()

    def load_jd():
        path = filedialog.askopenfilename(filetypes=[("Job description", "*.txt *.pdf *.docx")])
        if path:
            try:
                text, _ = read_document(path)
            except Exception as e:
                messagebox.showerror(APP_NAME, f"Could not read the file:\n{e}")
                return
            jd_box.delete("1.0", "end")
            jd_box.insert("1.0", text)

    def rank():
        jd = jd_box.get("1.0", "end").strip()
        if not jd:
            messagebox.showinfo(APP_NAME, "Please paste a job description first.")
            return
        if not state["paths"]:
            messagebox.showinfo(APP_NAME, "Please add some resumes first.")
            return
        cfg["jd"] = jd
        save_config(cfg)
        rank_btn.configure(state="disabled")
        paths = list(state["paths"])

        def work():
            try:
                cands, errors = load_candidates(paths, set_status)
                if not cands:
                    raise ValueError("None of the files could be read.\n" + "\n".join(errors))
                result = (*rank_candidates(jd, cands), errors, None)
            except Exception as e:
                result = (None, None, None, None, str(e))
            root.after(0, lambda: done(*result))

        def done(ranked, jd_skills, need_years, errors, error):
            rank_btn.configure(state="normal")
            if error:
                status.configure(text="Ranking failed.")
                messagebox.showerror(APP_NAME, error)
                return
            state.update(ranked=ranked, jd_skills=jd_skills, need_years=need_years)
            tree.delete(*tree.get_children())
            for i, c in enumerate(ranked, 1):
                tag = c.verdict().split()[0].lower()
                tree.insert("", "end", iid=str(i - 1), tags=(tag,), values=(
                    i, c.name, c.score, c.verdict(), c.years,
                    f"{len(c.matched)}/{len(jd_skills)}", ", ".join(c.missing) or "-"))
            status.configure(text=f"Ranked {len(ranked)} resumes. Click a row for details.")
            summary = (f"Job asks for {len(jd_skills)} skills: " + ", ".join(jd_skills)
                       + (f"\nExperience asked: {need_years}+ years" if need_years else "")
                       + f"\n\nBest match: {ranked[0].name} ({ranked[0].score}/100)")
            if errors:
                summary += "\n\nCould not read:\n" + "\n".join(errors)
            show_detail(summary)
            tree.selection_set("0")

        threading.Thread(target=work, daemon=True).start()

    def on_select(_event=None):
        sel = tree.selection()
        if sel and state["ranked"]:
            c = state["ranked"][int(sel[0])]
            show_detail(report_text(c, state["jd_skills"], state["need_years"]))

    def export():
        if not state["ranked"]:
            messagebox.showinfo(APP_NAME, "Rank the resumes first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="ranking.csv",
                                            filetypes=[("CSV (opens in Excel)", "*.csv")])
        if path:
            export_csv(path, state["ranked"])
            status.configure(text=f"Saved {os.path.basename(path)}")

    def ai():
        sel = tree.selection()
        if not sel or not state["ranked"]:
            messagebox.showinfo(APP_NAME, "Rank the resumes and select a candidate first.")
            return
        win = tk.Toplevel(root)
        win.title("AI review (optional, needs internet)")
        win.configure(bg=BG)
        ttk.Label(win, text="Provider:").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        prov = tk.StringVar(value=cfg.get("provider", list(PROVIDERS)[0]))
        if prov.get() not in PROVIDERS:
            prov.set(list(PROVIDERS)[0])
        ttk.Combobox(win, textvariable=prov, values=list(PROVIDERS), state="readonly",
                     width=26).grid(row=0, column=1, padx=8)
        ttk.Label(win, text="API key:").grid(row=1, column=0, padx=8, sticky="w")
        key = tk.StringVar(value=cfg.get("api_key", ""))
        ttk.Entry(win, textvariable=key, show="•", width=30).grid(row=1, column=1, padx=8)
        out = scrolledtext.ScrolledText(win, wrap="word", width=70, height=16, font=("Segoe UI", 10))
        out.grid(row=3, column=0, columnspan=2, padx=8, pady=8)
        c = state["ranked"][int(sel[0])]
        jd = jd_box.get("1.0", "end").strip()

        def go():
            if not key.get().strip():
                messagebox.showinfo(APP_NAME, "Paste a free key from aistudio.google.com/apikey "
                                    "or console.groq.com/keys.", parent=win)
                return
            cfg.update(provider=prov.get(), api_key=key.get().strip())
            save_config(cfg)
            out.delete("1.0", "end")
            out.insert("end", f"Reviewing {c.name}...\n")

            def work():
                try:
                    msg = ai_review(prov.get(), key.get().strip(), jd, c)
                except Exception as e:
                    msg = f"Error: {e}"
                root.after(0, lambda: (out.delete("1.0", "end"), out.insert("end", msg)))
            threading.Thread(target=work, daemon=True).start()

        ttk.Button(win, text=f"Review {c.name}", style="Accent.TButton",
                   command=go).grid(row=2, column=1, sticky="e", padx=8)

    ttk.Button(jd_head, text="Load from file", command=load_jd).pack(side="right")
    ttk.Button(jd_head, text="Clear", command=lambda: jd_box.delete("1.0", "end")).pack(side="right", padx=6)
    ttk.Button(left_btns, text="Add files", command=add_files).pack(side="left")
    ttk.Button(left_btns, text="Add folder", command=add_folder).pack(side="left", padx=6)
    ttk.Button(left_btns, text="Remove", command=remove_selected).pack(side="left")
    rank_btn = ttk.Button(left_btns, text="Rank candidates ▶", style="Accent.TButton", command=rank)
    rank_btn.pack(side="right")
    ttk.Button(right_btns, text="Export to Excel (CSV)", command=export).pack(side="left")
    ttk.Button(right_btns, text="AI review (optional)", command=ai).pack(side="left", padx=6)
    tree.bind("<<TreeviewSelect>>", on_select)

    if demo:   # python resume_screener.py --demo : load the samples and rank
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
        jd_file = os.path.join(base, "sample_job_description.txt")
        folder = os.path.join(base, "sample_resumes")
        if os.path.exists(jd_file) and os.path.isdir(folder):
            jd_box.delete("1.0", "end")
            jd_box.insert("1.0", read_document(jd_file)[0])
            state["paths"] = [os.path.join(folder, f) for f in sorted(os.listdir(folder))
                              if f.lower().endswith((".pdf", ".docx", ".txt"))]
            refresh_list()
            root.after(300, rank)

    root.mainloop()


def run_cli(jd_path, paths):
    """python resume_screener.py job.txt resume1.pdf resume2.docx ..."""
    jd, _ = read_document(jd_path)
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in sorted(os.listdir(p))
                      if f.lower().endswith((".pdf", ".docx", ".txt"))]
        else:
            files.append(p)
    cands, errors = load_candidates(files, progress=lambda m: print("  " + m))
    ranked, jd_skills, need = rank_candidates(jd, cands)
    print(f"\nJob skills ({len(jd_skills)}): {', '.join(jd_skills)}; years asked: {need}\n")
    for i, c in enumerate(ranked, 1):
        print(f"{i}. {c.name:<22} {c.score:5.1f}  {c.verdict():<13} yrs={c.years:<3} "
              f"skills {len(c.matched)}/{len(jd_skills)}  missing: {', '.join(c.missing) or '-'}"
              + ("  [OCR]" if c.used_ocr else ""))
    for e in errors:
        print("Could not read", e)


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        run_cli(sys.argv[1], sys.argv[2:])
    else:
        run_app(demo="--demo" in sys.argv)
