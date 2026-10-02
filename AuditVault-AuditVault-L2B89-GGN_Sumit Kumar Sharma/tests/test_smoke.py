import unittest
import hashlib
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from database import get_db, init_db
from models import AuditTrailEntry, User
from rcm_import import read_uploaded_rcm


ROOT = Path(__file__).resolve().parents[1]


class UploadStub:
    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.name

    def getvalue(self):
        return self.path.read_bytes()


class AuditVaultSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_csv_and_excel_rcm_templates_parse(self):
        csv_frame = read_uploaded_rcm(UploadStub(ROOT / "sample_data" / "sample_rcm.csv"))
        xlsx_frame = read_uploaded_rcm(UploadStub(ROOT / "sample_data" / "sample_rcm_template.xlsx"))
        self.assertGreaterEqual(len(csv_frame), 3)
        self.assertGreaterEqual(len(xlsx_frame), 3)
        self.assertIn("Risk_Description", csv_frame.columns)
        self.assertIn("Control_Description", xlsx_frame.columns)

    def _run_as(self, username, page):
        session = get_db()
        user = session.query(User).filter(User.username == username).first()
        self.assertIsNotNone(user)
        test_app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
        test_app.session_state["auth"] = True
        test_app.session_state["user_id"] = user.user_id
        test_app.session_state["username"] = user.username
        test_app.session_state["user_name"] = user.name
        test_app.session_state["role"] = user.role
        test_app.session_state["page"] = page
        test_app.run()
        self.assertEqual(len(test_app.exception), 0, [str(item.value) for item in test_app.exception])
        return test_app

    def test_manager_engagement_workspace_renders(self):
        test_app = self._run_as("rohit.sharma", "Engagements")
        rendered = " ".join(item.value for item in test_app.markdown)
        self.assertNotIn("Export IDR", rendered)
        self.assertGreaterEqual(len(test_app.download_button), 5)
        self.assertIn("🗑️ Delete Engagement", [item.label for item in test_app.expander])

    def test_manager_client_deletion_control_renders(self):
        test_app = self._run_as("rohit.sharma", "Clients")
        self.assertIn("🗑️ Delete Client Organization", [item.label for item in test_app.expander])
        button_labels = [item.label for item in test_app.button]
        self.assertIn("Delete Selected Client", button_labels)

    def test_manager_cannot_create_another_manager(self):
        test_app = self._run_as("rohit.sharma", "Team Management")
        role_inputs = [item for item in test_app.selectbox if item.label == "Role *"]
        self.assertEqual(len(role_inputs), 1)
        self.assertEqual(role_inputs[0].options, ["Team Member"])

    def test_team_member_engagement_workspace_renders(self):
        self._run_as("anita.kulkarni", "Engagements")

    def test_admin_team_management_renders(self):
        test_app = self._run_as("admin", "Team Management")
        tab_labels = [item.label for item in test_app.tabs]
        self.assertIn("🗑️ Delete Account", tab_labels)
        self.assertIn("🛡️ Access Control Audit", tab_labels)
        rendered = " ".join(item.value for item in test_app.markdown)
        self.assertIn("Manager authority", rendered)

        delete_selectors = [item for item in test_app.selectbox if item.label == "Select account"]
        self.assertEqual(len(delete_selectors), 1)
        session = get_db()
        expected = {
            f"{user.name} (@{user.username})"
            for user in session.query(User).filter(User.role == "Manager", User.is_deleted == False).all()
        }
        session.close()
        self.assertEqual(set(delete_selectors[0].options), expected)

    def test_manager_delete_account_list_contains_team_members_only(self):
        test_app = self._run_as("rohit.sharma", "Team Management")
        delete_selectors = [item for item in test_app.selectbox if item.label == "Select account"]
        self.assertEqual(len(delete_selectors), 1)
        option_text = " ".join(delete_selectors[0].options)
        self.assertNotIn("@manager.", option_text)
        self.assertNotIn("@admin", option_text)

    def test_admin_audit_ledgers_and_compliance_export_render(self):
        test_app = self._run_as("admin", "Audit Trail")
        rendered = " ".join(item.value for item in test_app.markdown)
        tab_labels = [item.label for item in test_app.tabs]
        self.assertIn("Complete System Audit Ledger", tab_labels)
        self.assertIn("Access Control & RBAC Accountability", tab_labels)
        self.assertIn("Access Control & RBAC Accountability", rendered)
        download_labels = [item.label for item in test_app.download_button]
        self.assertIn("Export Compliance CSV", download_labels)

    def test_audit_trail_sha256_chain_is_valid(self):
        session = get_db()
        entries = session.query(AuditTrailEntry).order_by(AuditTrailEntry.id.asc()).all()
        previous_hash = "GENESIS"
        for entry in entries:
            payload = {
                "id": entry.id,
                "timestamp": entry.timestamp_str,
                "action": entry.action_type,
                "entity": entry.target_entity,
                "target_id": entry.target_id or "",
                "description": entry.description,
                "user_id": entry.user_id,
                "actor": entry.acting_user_name,
                "previous_hash": previous_hash,
            }
            expected = hashlib.sha256(
                json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            self.assertEqual(entry.previous_hash, previous_hash)
            self.assertEqual(entry.integrity_hash, expected)
            previous_hash = expected
        session.close()


if __name__ == "__main__":
    unittest.main()
