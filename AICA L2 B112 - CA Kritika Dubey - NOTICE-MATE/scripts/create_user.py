"""Create a user from the command line. The first user must be an ADMIN.
Subsequent users: pass --admin-username to authorise as an existing ADMIN."""
import argparse
import getpass
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from noticemate.core.db import init_db  # noqa: E402
from noticemate.core.errors import NoticeMateError  # noqa: E402
from noticemate.services import auth  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--username", required=True)
p.add_argument("--full-name", required=True)
p.add_argument("--role", choices=auth.ROLES, required=True)
p.add_argument("--membership-no", default=None)
p.add_argument("--admin-username", default=None, help="Existing ADMIN authorising this creation")
a = p.parse_args()
init_db()
actor = None
try:
    if a.admin_username:
        pw = getpass.getpass(f"Password for ADMIN {a.admin_username}: ")
        actor = auth.login(a.admin_username, pw)["user"]["id"]
    new_pw = getpass.getpass(f"New password for {a.username} (≥10 chars, 3 of lower/upper/digit/symbol): ")
    if new_pw != getpass.getpass("Repeat: "):
        sys.exit("Passwords do not match.")
    u = auth.create_user(a.username, a.full_name, a.role, new_pw, membership_no=a.membership_no, actor_id=actor)
    print(f"Created user {u['username']} ({u['role']}) id={u['id']}")
except NoticeMateError as e:
    sys.exit(f"Error: {e.message}")
