"""Fictitious demo data for presentations. Run `python seed.py` or use Settings → Data → Load demo data."""
import random
from datetime import date, timedelta

from fpdf import FPDF

from core import auth, clock, db, duedates, invoice_pdf

DEMO_PASSWORD = "Demo@1234"
STAFF = [("CA Priya Shah", "priya", "Manager"), ("Rohan Mehta", "rohan", "Staff"),
         ("Neha Patel", "neha", "Staff"), ("Karan Joshi", "karan", "Staff")]

# name, entity, pan, gstin, state, gst_freq, tds, itr, audit, fee, contact
CLIENTS = [
    ("Shreeji Traders", "Proprietorship", "ABCPS1234A", "24ABCPS1234A1Z5", "Gujarat", "Monthly", 0, 1, 1, 6000, "Ramesh Shah"),
    ("Navkar Textiles Pvt Ltd", "Company", "AACCN4521B", "24AACCN4521B1Z2", "Gujarat", "Monthly", 1, 1, 1, 15000, "Vikram Jain"),
    ("Dr. Anil Desai", "Individual", "AFPPD7788C", "", "Gujarat", "None", 0, 1, 0, 2000, "Anil Desai"),
    ("Kalpataru Engineering LLP", "LLP", "AAKFK3344D", "27AAKFK3344D1Z9", "Maharashtra", "Monthly", 1, 1, 1, 12000, "Suresh Kulkarni"),
    ("Mehta & Sons", "Partnership Firm", "AAFFM9012E", "24AAFFM9012E1Z1", "Gujarat", "Quarterly", 1, 1, 1, 8000, "Dinesh Mehta"),
    ("Sunrise Pharma Distributors", "Proprietorship", "BQRPS5566F", "08BQRPS5566F1Z7", "Rajasthan", "Quarterly", 0, 1, 0, 5000, "Mahesh Agarwal"),
    ("Anjali Kothari", "Individual", "BKLPK2233G", "", "Gujarat", "None", 0, 1, 0, 1500, "Anjali Kothari"),
    ("Om Sai Constructions", "Partnership Firm", "AAFFO6677H", "24AAFFO6677H1Z3", "Gujarat", "Monthly", 1, 1, 1, 10000, "Bharat Patel"),
    ("Bluewave Tech Solutions Pvt Ltd", "Company", "AABCB8899J", "29AABCB8899J1Z6", "Karnataka", "Monthly", 1, 1, 1, 18000, "Arjun Rao"),
    ("Patel Education Trust", "Trust / Society", "AAATP1122K", "", "Gujarat", "None", 1, 1, 1, 7000, "Trustee Office"),
    ("Greenleaf Agro Exports", "Proprietorship", "CDEPG4455L", "24CDEPG4455L1Z8", "Gujarat", "Monthly", 1, 1, 1, 9000, "Hitesh Gandhi"),
    ("Vora Family HUF", "HUF", "AAJHV7788M", "", "Gujarat", "None", 0, 1, 0, 1500, "Kirit Vora"),
]


def _demo_pdf(title: str, client: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, f"Demo document for {client}.\nThis is fictitious sample content for the CA Practice Manager demo.")
    return bytes(pdf.output())


def run():
    if db.scalar("SELECT COUNT(*) FROM clients") > 0:
        return
    random.seed(11)
    today = clock.today()
    ids = {}
    for name, uname, role in STAFF:
        existing = db.one("SELECT id FROM users WHERE username=:u", u=uname)
        ids[uname] = existing["id"] if existing else auth.create_user(name, uname, DEMO_PASSWORD, role,
                                                                       f"{uname}@example.com")
    managers = [ids["priya"], ids["rohan"], ids["neha"]]
    team = list(ids.values())

    fy = duedates.current_fy_start()
    for i, (n, e, pan, gstin, st_, gf, tds, itr, aud, fee, cp) in enumerate(CLIENTS):
        cid = db.insert(
            "INSERT INTO clients(name,entity_type,pan,gstin,state,contact_person,email,phone,gst_freq,has_tds,needs_itr,"
            "needs_audit,monthly_fee,manager_id,created_on) VALUES (:n,:e,:p,:g,:s,:cp,:em,:ph,:gf,:t,:i,:a,:f,:m,:c) "
            "RETURNING id", n=n, e=e, p=pan, g=gstin, s=st_, cp=cp, em=n.split()[0].lower().replace(".", "") + "@example.com",
            ph=f"98{random.randint(10000000, 99999999)}", gf=gf, t=tds, i=itr, a=aud, f=fee, m=managers[i % 3],
            c=db.now())
        duedates.generate_for_client(db.one("SELECT * FROM clients WHERE id=:i", i=cid), fy)

    for t in db.query("SELECT id, due_date, assigned_to FROM tasks"):
        due = date.fromisoformat(t["due_date"])
        days = (due - today).days
        if days < -20:
            status = "Done" if random.random() < 0.96 else "Under Review"
        elif days < 0:
            status = random.choices(["Done", "Under Review", "In Progress", "To Do"], [6, 1, 1, 1])[0]
        elif days <= 12:
            status = random.choices(["To Do", "In Progress", "Under Review", "Done"], [3, 3, 2, 1])[0]
        else:
            status = "To Do"
        who = random.choice(team) if random.random() < 0.55 else t["assigned_to"]
        completed = (due - timedelta(days=random.randint(0, 4))).isoformat() if status == "Done" else None
        if completed and completed > today.isoformat():
            completed = today.isoformat()
        db.execute("UPDATE tasks SET status=:s, assigned_to=:a, completed_on=:c, priority=:p, updated_on=:u WHERE id=:i",
                   s=status, a=who, c=completed, p=random.choices(["High", "Medium", "Low"], [2, 5, 2])[0],
                   u=db.now(), i=t["id"])

    # activity log: older completions + a lively last few hours
    recent = db.query("SELECT id, status, assigned_to, completed_on FROM tasks WHERE status<>'To Do' AND "
                      "(completed_on IS NULL OR completed_on>=:d)", d=(today - timedelta(days=20)).isoformat())
    random.shuffle(recent)
    now = clock.now()
    for k, t in enumerate(recent[:60]):
        when = now - timedelta(minutes=7 + k * random.randint(9, 55))
        prev = {"In Progress": "To Do", "Under Review": "In Progress", "Done": "Under Review"}[t["status"]]
        actor = t["assigned_to"] if t["status"] != "Done" else random.choice([ids["priya"], t["assigned_to"]])
        db.execute("INSERT INTO task_log(task_id,user_id,action,detail,at) VALUES (:t,:u,'Status',:d,:at)",
                   t=t["id"], u=actor, d=f"{prev} → {t['status']}", at=when.strftime("%Y-%m-%d %H:%M:%S"))

    # invoices: monthly retainers for the last three months
    firm_state = invoice_pdf.firm()["firm_state"]
    n = 0
    for c in db.query("SELECT * FROM clients ORDER BY id"):
        for back in (2, 1, 0):
            m = today.month - back
            y = today.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            d = date(y, m, 3)
            g = invoice_pdf.compute_gst(c["monthly_fee"], 18, c["state"], firm_state)
            n += 1
            paid = back == 2 and random.random() < 0.9 or back == 1 and random.random() < 0.6
            db.execute(
                "INSERT INTO invoices(invoice_no,client_id,invoice_date,due_date,description,sac,taxable_value,gst_rate,"
                "cgst,sgst,igst,total,status,paid_on,created_by) VALUES (:no,:c,:d,:dd,:desc,'998231',:v,18,:cg,:sg,:ig,"
                ":t,:s,:p,:by)", no=f"INV/{duedates.fy_label(duedates.current_fy_start(d))}/{n:04d}", c=c["id"],
                d=d.isoformat(), dd=(d + timedelta(days=15)).isoformat(),
                desc=f"Monthly compliance retainer — {d.strftime('%B %Y')}", v=c["monthly_fee"], cg=g["cgst"],
                sg=g["sgst"], ig=g["igst"], t=g["total"], s="Paid" if paid else "Unpaid",
                p=(d + timedelta(days=12)).isoformat() if paid else None, by=ids["priya"])

    fyl = duedates.fy_label(fy)
    for c in db.query("SELECT id, name FROM clients ORDER BY id LIMIT 6"):
        for title, cat in [("PAN card copy", "KYC"), ("Bank statement Apr-Sep", "Bank statements")]:
            data = _demo_pdf(title, c["name"])
            db.execute("INSERT INTO documents(client_id,category,fin_year,filename,mime,size_bytes,content,uploaded_by,"
                       "uploaded_on) VALUES (:c,:cat,:fy,:fn,'application/pdf',:s,:b,:u,:at)",
                       c=c["id"], cat=cat, fy=fyl, fn=f"{title.replace(' ', '_')}.pdf", s=len(data), b=data,
                       u=random.choice(team), at=(now - timedelta(days=random.randint(0, 40))).strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    db.init_db()
    auth.ensure_admin()
    duedates.seed_rules()
    run()
    print(f"Demo data loaded. Staff logins: priya / rohan / neha / karan, password {DEMO_PASSWORD}")
