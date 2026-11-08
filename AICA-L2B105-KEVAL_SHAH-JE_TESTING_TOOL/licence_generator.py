"""
============================================================================
 JE TESTING  --  VENDOR licence generator   (NOT shipped to customers)
----------------------------------------------------------------------------
 The vendor (seller) uses this script to:
   1. init        create the vendor key pair (once)
   2. issue       sign a licence key for a customer's login ID
   3. add-user    create a login ID (password hashed) in a users.json

 The PRIVATE key is saved in vendor/vendor_private_key.pem.  Keep it secret:
 anyone who has it can create licences.  It is excluded from Git and from
 the .exe.  The PUBLIC key is written into je_access.py so the tool can
 check licences.

 USAGE
   python licence_generator.py init
   python licence_generator.py issue --username admin --role admin \
          --licensee "ABC & Co., Chartered Accountants" --days 365
   python licence_generator.py add-user --users "release/users.json" \
          --username user --role user
============================================================================
"""

import argparse
import base64
import getpass
import json
import re
import secrets
from datetime import date, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import je_access

HERE = Path(__file__).resolve().parent
PRIVATE_KEY = HERE / "vendor" / "vendor_private_key.pem"
SERIAL_FILE = HERE / "vendor" / "issued_licences.json"


def _b64e(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def init_keys():
    if PRIVATE_KEY.exists():
        raise SystemExit(f"Key pair already exists: {PRIVATE_KEY}\n"
                         "Creating a new one would invalidate every licence already sold.")
    PRIVATE_KEY.parent.mkdir(exist_ok=True)
    priv = Ed25519PrivateKey.generate()
    PRIVATE_KEY.write_bytes(priv.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    pub = priv.public_key().public_bytes(serialization.Encoding.Raw,
                                         serialization.PublicFormat.Raw)
    src = HERE / "je_access.py"
    text = re.sub(r'VENDOR_PUBLIC_KEY_B64 = "[^"]*"',
                  f'VENDOR_PUBLIC_KEY_B64 = "{base64.b64encode(pub).decode()}"',
                  src.read_text(encoding="utf-8"))
    src.write_text(text, encoding="utf-8")
    print(f"Private key saved to {PRIVATE_KEY}  (keep it secret)")
    print("Public key written into je_access.py")


def issue(username, role, licensee, days):
    if not PRIVATE_KEY.exists():
        raise SystemExit("No vendor key yet. Run:  python licence_generator.py init")
    priv = serialization.load_pem_private_key(PRIVATE_KEY.read_bytes(), password=None)
    log = json.loads(SERIAL_FILE.read_text()) if SERIAL_FILE.exists() else []
    lic = {
        "licence_no": f"JE-{date.today():%Y}-{len(log) + 1:04d}",
        "licensee": licensee,
        "username": username,
        "role": role,
        "issued": date.today().isoformat(),
        "expires": (date.today() + timedelta(days=days)).isoformat(),
    }
    payload = json.dumps(lic, separators=(",", ":"), sort_keys=True).encode()
    key = je_access.LICENCE_PREFIX + _b64e(payload) + "." + _b64e(priv.sign(payload))
    log.append(lic)
    SERIAL_FILE.write_text(json.dumps(log, indent=2))
    return lic, key


def add_user(users_path, username, role, password):
    users_path = Path(users_path)
    store = (json.loads(users_path.read_text(encoding="utf-8"))
             if users_path.exists() else {"users": {}})
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")
    store["users"][username] = {"role": role,
                                "password": je_access.hash_password(password),
                                "licence_key": ""}
    users_path.parent.mkdir(parents=True, exist_ok=True)
    je_access.save_users(store, users_path)
    return store


def make_password():
    """Readable random password, e.g. 'Kite-4821-Moss' style."""
    words = ["Audit", "Ledger", "Kite", "River", "Cedar", "Amber", "Falcon",
             "Maple", "Orbit", "Quartz", "Harbor", "Saffron"]
    return (f"{secrets.choice(words)}-{secrets.randbelow(9000) + 1000}-"
            f"{secrets.choice(words)}")


def main():
    ap = argparse.ArgumentParser(description="JE Testing vendor licence tool")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p = sub.add_parser("issue")
    p.add_argument("--username", required=True)
    p.add_argument("--role", choices=["admin", "user"], required=True)
    p.add_argument("--licensee", required=True)
    p.add_argument("--days", type=int, default=365)
    p = sub.add_parser("add-user")
    p.add_argument("--users", required=True)
    p.add_argument("--username", required=True)
    p.add_argument("--role", choices=["admin", "user"], required=True)
    a = ap.parse_args()
    if a.cmd == "init":
        init_keys()
    elif a.cmd == "issue":
        lic, key = issue(a.username, a.role, a.licensee, a.days)
        print(json.dumps(lic, indent=2)); print("\nLICENCE KEY:\n" + key)
    elif a.cmd == "add-user":
        pw = getpass.getpass("New password (min 8 characters): ")
        add_user(a.users, a.username, a.role, pw)
        print(f"Login ID '{a.username}' ({a.role}) saved in {a.users}")


if __name__ == "__main__":
    main()
