from datetime import date

from app.db.connection import connect
from app.db.migrate import migrate
from app.security.audit import AuditService
from app.services.clients import ClientService
from app.services.communications import CommunicationService
from app.services.dashboard import DashboardService
from app.services.forms import FormService


def test_form_merge_version_export_communication_and_real_dashboard(tmp_path):
    db = connect(tmp_path / "forms.sqlite3")
    migrate(db)
    audit = AuditService(db, bytes(range(32)))
    clients = ClientService(db, bytes(reversed(range(32))), audit)
    client = clients.create({"name": "Form Client", "cin": "CIN123"})
    matter = clients.create_matter(client, {"title": "Form Matter", "matter_type": "CIRP", "case_number": "CP/1/2026"})
    forms = FormService(db, audit)
    template = forms.add_template(name="Practitioner Cover Note", template="Client: {{client.name}}\nCase: {{matter.case_number}}")
    version = forms.generate(template, matter)
    assert forms.content(version) == "Client: Form Client\nCase: CP/1/2026"
    revised = forms.generate(template, matter, edited_content=forms.content(version) + "\nReviewed: Yes")
    txt = forms.export(revised, tmp_path / "exports", "TXT")
    docx = forms.export(revised, tmp_path / "exports", "DOCX")
    pdf = forms.export(revised, tmp_path / "exports", "PDF")
    assert txt.read_text(encoding="utf-8").endswith("Reviewed: Yes")
    assert docx.read_bytes().startswith(b"PK")
    assert pdf.read_bytes().startswith(b"%PDF")

    communications = CommunicationService(db, audit)
    draft = communications.create(matter, "CREDITOR", "Claim acknowledgement", "We acknowledge receipt.", "creditor@example.invalid")
    eml = communications.export(draft, tmp_path / "exports", "EML")
    assert b"Claim acknowledgement" in eml.read_bytes()
    assert DashboardService(db).metrics(date(2026, 9, 22))["active_clients"] == 1
    assert DashboardService(db).metrics(date(2026, 9, 22))["active_assignments"] == 1
