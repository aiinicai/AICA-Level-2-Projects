"""Re-creates the pictures used by the built-in Help (audit_manager/static/help). Run from the project folder:

    python tools/make_help_pictures.py

It starts Office Manager on a throw-away demo database, opens each screen in Chrome, draws numbered red boxes round the buttons the
Help text talks about, and saves a picture. Needs: pip install playwright, and Google Chrome installed. Demo data only - never real clients."""
import io
import os
import subprocess
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audit_manager" / "static" / "help"
PORT = 8765
B = f"http://127.0.0.1:{PORT}"
DATA = tempfile.mkdtemp(prefix="om-help-")
os.environ["AUDIT_MANAGER_DATA"] = DATA
sys.path.insert(0, str(ROOT))

HL_JS = """
(items) => {
  document.querySelectorAll('.om-hl-badge').forEach(e => e.remove());
  document.querySelectorAll('[data-om-hl]').forEach(e => { e.style.outline = ''; e.style.outlineOffset = ''; e.style.boxShadow = ''; e.removeAttribute('data-om-hl'); });
  const bs = String.fromCharCode(92); document.querySelectorAll('code').forEach(c => { if (c.textContent.includes('om-help-')) c.textContent = ['C:', 'Users', 'you', 'AppData', 'Roaming', 'AuditManager'].join(bs); });
  const missing = [];
  items.forEach(([sel, n]) => {
    let el = null; try { el = document.querySelector(sel); } catch (e) {}
    if (!el) { missing.push(sel); return; }
    el.setAttribute('data-om-hl', '1'); el.style.outline = '3px solid #e11d48'; el.style.outlineOffset = '3px'; el.style.borderRadius = '6px';
    el.style.boxShadow = '0 0 0 7px rgba(225,29,72,.22)';
    const r = el.getBoundingClientRect();
    const b = document.createElement('div'); b.className = 'om-hl-badge'; b.textContent = n;
    b.style.cssText = 'position:fixed;z-index:99999;width:26px;height:26px;border-radius:50%;background:#e11d48;color:#fff;font:700 14px/26px Arial;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.4);left:' + Math.max(2, r.left - 16) + 'px;top:' + Math.max(2, r.top - 16) + 'px';
    document.body.appendChild(b);
  });
  return missing;
}
"""


def seed():
    from PIL import Image, ImageDraw

    from audit_manager import create_app
    from audit_manager.models import (Client, FirmSetting, GstReturn, GstReturnType, Invoice, ItrFiling, Task, TdsReturn, User, WhatsAppTemplate, db)
    from audit_manager.services import billing, compliance, letterhead, pictures
    from audit_manager.services import whatsapp as wa

    app = create_app({"TESTING": True})
    with app.app_context():
        for k, v in {"firm_name": "Sharma & Associates", "firm_tagline": "Chartered Accountants", "firm_address": "Main Bazar, Abohar, Punjab 152116",
                     "firm_phone": "98765 00000", "firm_email": "office@example.in", "firm_frn": "012345N", "firm_pan": "AAAFS1234A",
                     "firm_gstin": "03AAAFS1234A1Z1", "firm_partner_name": "CA Demo Partner", "firm_membership_no": "512345", "invoice_prefix": "SA",
                     "hourly_billing": "1", "default_hourly_rate": "1500"}.items():
            FirmSetting.put(k, v)
        logo = Image.new("RGB", (400, 160), "#1e3a5f"); d = ImageDraw.Draw(logo); d.rectangle([14, 14, 386, 146], outline="#5eead4", width=5); d.text((150, 68), "S & A", fill="white")
        buf = io.BytesIO(); logo.save(buf, "PNG"); letterhead.save_logo(buf.getvalue())
        admin = User.query.first()
        staff = []
        for name, role in (("Ritu Verma", "manager"), ("Amit Kumar", "employee")):
            u = User(name=name, email=name.split()[0].lower() + "@example.in", role=role, phone="98111 00000"); u.set_password("DemoPass#1"); db.session.add(u); staff.append(u)
        db.session.flush()
        rows = [("Apex Traders", "03AABCA1234F1Z5", "AABCA1234F", "9876500001", "accounts@apex.example", "Abohar", True),
                ("Bansal Rice Mills", "03BBBCB2345G1Z4", "BBBCB2345G", "9876500002", "bansal@example.in", "Fazilka", True),
                ("City Medical Store", "03CCCPC3456H1Z3", "CCCPC3456H", "9876500003", "", "Abohar", True),
                ("Dr. Meena Arora", "", "DDDPD4567J", "9876500004", "meena@example.in", "Abohar", False),
                ("Evergreen Agro Pvt Ltd", "03EEECE5678K1Z2", "EEECE5678K", "", "info@evergreen.example", "Sri Ganganagar", True)]
        clients = []
        for i, (n, g, p, m, e, city, gst) in enumerate(rows, 1):
            c = Client(client_code=f"CL-{i:04d}", name=n, gstin=g or None, pan=p, mobile=m or None, email=e or None, city=city, state="Punjab", pincode="152116",
                       is_gst_registered=gst, is_itr_applicable=True, is_tds_applicable=i in (1, 5), assigned_to_id=staff[i % 2].id, category="business" if gst else "individual")
            db.session.add(c); clients.append(c)
        db.session.flush()
        rt = GstReturnType.query.filter_by(name="GSTR-3B").one()
        compliance.bulk_gst(Client.query, rt, "2026-10"); compliance.bulk_itr(Client.query, "2026-27", "ITR-3"); compliance.bulk_tds(Client.query, "2026-27", "Q3", "26Q")
        g1 = GstReturn.query.first(); g1.status, g1.filed_date, g1.arn = "filed", date(2026, 11, 14), "AA0311260001234"
        i1 = ItrFiling.query.first(); i1.status, i1.filed_date, i1.ack_number = "filed", date.today() - timedelta(days=6), "412345670311226"
        i2 = ItrFiling.query.offset(1).first(); i2.status, i2.filed_date, i2.verification_status, i2.verification_date = "filed", date(2026, 10, 20), "e_verified", date(2026, 10, 20)
        for title, st, days, who in (("Collect bank statements - Apex", "todo", 3, 1), ("Prepare tax audit report - Bansal", "in_progress", 9, 0),
                                     ("Reply to GST notice - City Medical", "under_review", 1, 1), ("File Form 26Q - Evergreen", "todo", 20, 0)):
            db.session.add(Task(title=title, status=st, due_date=date.today() + timedelta(days=days), assigned_to_id=staff[who].id, created_by_id=admin.id,
                                client_id=clients[0].id, priority="high" if days < 5 else "medium"))
        inv = billing.create_invoice(clients[0].id, date.today() - timedelta(days=4), date.today() + timedelta(days=11), "cgst_sgst",
                                     [{"description": "Statutory Audit Fee", "quantity": 1, "rate": 25000, "sac_code": "998221"},
                                      {"description": "GST Return Filing (Monthly)", "quantity": 3, "rate": 1500, "sac_code": "998231"}], 0, "", admin.id)
        billing.create_invoice(clients[1].id, date.today() - timedelta(days=40), date.today() - timedelta(days=10), "cgst_sgst",
                               [{"description": "Income Tax Return Filing", "quantity": 1, "rate": 5000, "sac_code": "998231"}], 0, "", admin.id)
        pic = Image.new("RGB", (500, 500), "#b45309"); d = ImageDraw.Draw(pic); d.ellipse([150, 150, 350, 350], fill="#fde68a"); d.text((190, 420), "Happy Diwali", fill="white")
        buf = io.BytesIO(); pic.save(buf, "PNG")
        t = WhatsAppTemplate(name="Diwali greeting", category="general", image=pictures.save(buf.getvalue()),
                             body="Dear {client_name},\n\nWishing you and your family a very Happy Diwali!\n\nRegards,\n{firm_name}")
        db.session.add(t); db.session.flush()
        for c in clients[:3]:
            wa.queue("client", c.mobile, c.name, wa.render(t.body, client_name=c.name, firm_name="Sharma & Associates"), admin.id, "bulk", client_id=c.id, image=t.image)
        db.session.commit()
    return inv


SHOTS = []  # (file, url or callable, [(selector, number)], optional pre-action)


def main():
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    server = subprocess.Popen([sys.executable, str(ROOT / "run_desktop.py"), "--server"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
            pg = browser.new_page(viewport={"width": 1240, "height": 720})

            def shot(name, items, scroll=None, full=False):
                if scroll:
                    pg.evaluate("(s) => { const e = document.querySelector(s); if (e) window.scrollTo({top: e.getBoundingClientRect().top + window.scrollY - 60, behavior: 'instant'}); }", scroll)
                    pg.wait_for_timeout(250)
                missing = pg.evaluate(HL_JS, [[s, str(n)] for s, n in items])
                if missing:
                    print("  !! not found on", name, missing)
                pg.wait_for_timeout(120)
                pg.screenshot(path=str(OUT / f"{name}.jpg"), type="jpeg", quality=68, full_page=full)
                print("saved", name)

            pg.goto(B + "/")
            for k, v in dict(firm_name="Sharma & Associates", name="CA Demo Partner", email="demo@example.in").items():
                pg.fill(f"[name={k}]", v)
            shot("01-setup", [("[name=firm_name]", 1), ("[name=email]", 2), ("[name=password]", 3), ("form button", 4)])
            pg.fill("[name=password]", "DemoPass#1"); pg.fill("[name=password2]", "DemoPass#1"); pg.locator("form button").first.click(); pg.wait_for_load_state()
            seed()
            pg.goto(B + "/login"); pg.fill("[name=email]", "demo@example.in")
            shot("02-login", [("[name=email]", 1), ("[name=password]", 2), ("form button", 3)])
            pg.fill("[name=password]", "DemoPass#1"); pg.locator("form button").first.click(); pg.wait_for_load_state()
            go = lambda u: (pg.goto(B + u), pg.wait_for_load_state())

            go("/"); shot("03-dashboard", [("aside.sidebar nav", 1), ("#backBtn", 2), ("aside.sidebar a[title*='My account']", 3), ("aside.sidebar form button", 4)])
            go("/account/password"); shot("04-my-account", [("#theme", 1), ("form:not(#theme) button.btn-primary", 2)])
            go("/settings/"); shot("05-settings-firm", [("[name=firm_logo]", 1), ("[name=firm_name]", 2), ("[name=firm_frn]", 3), ("#office", 4)])
            shot("06-settings-office", [("#office [name=profession]", 1), ("#hb", 2), ("#invFolder", 3), ("#office button.btn-primary", 4)], scroll="#office")
            shot("07-settings-report-header", [("#theme", 1), ("#reportHeader .row", 2), ("#reportHeader button", 3)], scroll="#dataFolder")
            shot("08-settings-backup", [("a[href='/settings/backup']", 1), ("#backupFolder", 2), ("[name=backup_when]", 3), ("form[action='/settings/backup/now'] button", 4), ("[name=backup_file]", 5)], scroll="#backup")
            shot("09-settings-email", [("#me", 1), ("[name=mail_host]", 2), ("[name=mail_password]", 3), ("form[action='/settings/mail'] button", 4), ("form[action='/settings/mail/test'] button", 5)], scroll="#me")
            shot("10-settings-data-folder", [("#dataFolderInput", 1), ("#dataFolder form button.btn-outline-primary", 2)], scroll="#dataFolder")
            go("/clients/"); shot("11-clients", [("a[href='/clients/new']", 1), ("a[href='/clients/import']", 2), ("[name=q]", 3), ("tbody tr:first-child a.btn", 4), (".grid-count", 5)])
            go("/clients/new"); pg.fill("[name=gstin]", "03AABCA1234F1Z5")
            shot("12-client-new", [("#gstFetchBtn", 1), ("[name=pan]", 2), ("[name=pincode]", 3), ("form.card-box div.mt-3 button.btn-primary", 4)])
            go("/clients/import"); shot("13-client-import", [("a[href*='template.xlsx']", 1), ("[name=file]", 2), ("form button.btn-primary", 3)])
            go("/clients/1"); shot("14-client-page", [("#gstHistBtn", 1), ("a[href='/clients/1/edit']", 2), ("a[href*='/billing/new']", 3)])
            shot("15-portal-logins", [("#logins select[name=portal]", 1), ("#logins [name=username]", 2), ("#logins [name=password]", 3), ("#logins button.btn-primary", 4)], scroll="#logins")
            go("/gst"); shot("16-gst", [("form[action='/gst/bulk'] button", 1), ("a[href='/trackers/import/gst']", 2), ("form[action='/gst/add'] button", 3), ("#extend", 4)])
            shot("17-gst-rows", [("[name=status]", 1), ("tbody tr:first-child [name=due_date]", 2), ("tbody tr:first-child select[name=status]", 3), ("tbody tr:first-child [name=arn]", 4), ("tbody tr:first-child button.btn-outline-primary", 5)], scroll="form.card-box.p-2")
            go("/itr"); shot("18-itr-verification", [("tbody tr:first-child select[name=verification_status]", 1), ("tbody tr:first-child [name=verification_date]", 2), ("tbody tr:first-child button.btn-outline-primary", 3), ("tbody tr:first-child td:nth-child(4)", 4)], scroll="form.card-box.p-2")
            go("/trackers/import/gst"); shot("19-filing-import", [("a[href*='template.xlsx']", 1), ("[name=file]", 2), ("form button.btn-primary", 3)])
            go("/calendar/due-dates"); shot("20-due-date-master", [("form button.btn-outline-success", 1), ("tbody tr:first-child a.btn-outline-success", 2), ("tbody tr:first-child a.btn-outline-primary", 3), (".col-lg-4 form button.btn-primary", 4)])
            go("/calendar/?year=2026&month=12"); shot("21-calendar", [("td.day[data-date='2026-12-18']", 1), ("a[href='/calendar/due-dates']", 2), ("form[action='/calendar/add'] button", 3)])
            pg.click("td.day[data-date='2026-12-18'] .d"); pg.wait_for_timeout(500); pg.fill("#taskTitle", "Collect bank statements")
            shot("22-calendar-new-task", [("#taskTitle", 1), ("#taskDate", 2), ("#taskModal button.btn-primary", 3)])
            go("/tasks/"); shot("23-tasks", [("button[data-bs-target='#newTask']", 1), (".kanban-card", 2), (".kanban-col[data-status='completed']", 3), ("a[href*='view=table']", 4)])
            go("/whatsapp/"); pg.select_option("#tpl", label="Due date alert"); pg.select_option("#dueMaster", index=2); pg.check("input[name=client_ids] >> nth=0"); pg.check("input[name=client_ids] >> nth=1")
            shot("24-compose-top", [("label[for=c1]", 1), ("#tpl", 2), ("#body", 3), ("#chips", 4), ("#pick-client", 5)])
            shot("25-compose-fields", [("#dueMaster", 1), ("#work_type", 2), ("#period", 3), ("[name=image]", 4), ("#goBtn", 5)], scroll="#chips")
            go("/whatsapp/queue"); pg.wait_for_timeout(500)
            shot("26-whatsapp-queue", [("label[for=m-web]", 1), ("label[for=m-desktop]", 2), ("tbody tr:first-child a.open", 3), ("tbody tr:first-child .copy-pic", 4), ("tbody tr:first-child form button", 5)])
            go("/whatsapp/automation"); shot("27-automatic", [("[name=return_filed_whatsapp]", 1), ("[name=return_filed_email]", 2), ("[name=auto_due_days]", 3), ("tbody tr:first-child a.btn", 4), ("form button.btn-primary", 5)])
            go("/whatsapp/templates"); shot("28-templates", [("tbody tr:first-child a.btn-outline-primary", 1), ("#tbody", 2), (".field-chip", 3), ("form[enctype] [name=image]", 4), ("form[enctype] button.btn-primary", 5)])
            go("/billing/"); shot("29-billing", [("a[href='/billing/new']", 1), ("a[href='/billing/services']", 2), ("[name=status]", 3), ("tbody tr:first-child a", 4)])
            go("/billing/services"); shot("30-services", [("tbody tr:first-child [name=name]", 1), ("tbody tr:first-child [name=default_rate]", 2), ("tbody tr:first-child button.btn-outline-primary", 3), (".col-lg-4 form button", 4)])
            go("/billing/new"); pg.select_option("[name=client_id]", index=1); pg.fill("[name=description]", "Statutory Audit Fee"); pg.dispatch_event("[name=description]", "change"); pg.fill("[name=rate]", "25000")
            shot("31-invoice-new", [("[name=client_id]", 1), ("#taxMode", 2), ("[name=description]", 3), ("#addRow", 4), ("form.card-box div.mt-3 button.btn-primary", 5)])
            go("/billing/1"); shot("32-invoice", [("a[href='/billing/1/preview']", 1), ("a[href='/billing/1/pdf']", 2), ("form[action='/billing/1/payment'] button", 3), ("form[action='/billing/1/whatsapp'] button", 4), ("form[action='/billing/1/email'] button", 5)])
            go("/billing/1/preview"); shot("33-invoice-preview", [("button[onclick*='print']", 1), ("a[href='/billing/1/pdf']", 2)])
            go("/time/"); shot("34-time-sheet", [("form[action='/time/add'] [name=client_id]", 1), ("[name=hours]", 2), ("form[action='/time/add'] button", 3), ("form[action='/time/bill'] button", 4)])
            go("/reports/?type=own_gst_outward"); shot("35-reports", [("[name=type]", 1), ("[name=from_date]", 2), ("form button.btn-primary", 3), ("a[href*='export.pdf']", 4), ("a[href*='export.xlsx']", 5)])
            go("/staff/"); shot("36-staff", [(".col-lg-4 form button", 1), ("a[href='/staff/permissions']", 2), ("tbody tr:nth-child(2) select[name=role]", 3), ("tbody tr:nth-child(2) button", 4)])
            go("/staff/permissions"); shot("37-permissions", [("tbody tr:nth-child(2) td:nth-child(8) input", 1), ("tbody tr:nth-child(3) td:nth-child(5) input", 2), ("form button.btn-primary", 3)])
            go("/activity/"); shot("38-activity-log", [("[name=user_id]", 1), ("[name=module]", 2), ("form button.btn-primary", 3)])
            go("/settings/"); pg.select_option("#office [name=profession]", "advocate"); pg.check("#hb"); pg.click("#office button.btn-primary"); pg.wait_for_load_state()
            go("/matters/"); pg.select_option("form.card-box [name=client_id]", index=1); pg.fill("[name=title]", "Apex Traders vs State Bank"); pg.fill("[name=case_number]", "CS 45/2026"); pg.fill("[name=court]", "Civil Judge, Abohar")
            pg.fill("[name=next_hearing]", str(date.today() + timedelta(days=5))); pg.click("form.card-box button.btn-primary"); pg.wait_for_load_state()
            shot("39-matters", [("form.card-box [name=title]", 1), ("[name=next_hearing]", 2), ("form.card-box button.btn-primary", 3), ("a[href*='when=week']", 4), ("a[href*='matter_register']", 5)])
            browser.close()
    finally:
        server.terminate()
    total = sum(f.stat().st_size for f in OUT.glob("*.jpg"))
    print(f"{len(list(OUT.glob('*.jpg')))} pictures, {total / 1024:.0f} KB in {OUT}")


if __name__ == "__main__":
    main()
