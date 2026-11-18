"""Owner's tool: create the signing key pair once, then issue licence keys. NEVER commit or share the private key.

  python tools/make_license.py keygen                      # once; prints the PUBLIC key to paste into app/licensing.py
  python tools/make_license.py machine                     # shows THIS PC's machine id (the customer sends you theirs)
  python tools/make_license.py issue --licensee "Name" --machine XXXX-XXXX-XXXX-XXXX --days 365 --companies 3
  python tools/make_license.py issue --licensee "Reviewer" --machine "*" --days 30     # works on any PC, expires

The private key lives in  %USERPROFILE%\\.tallymis\\signing_key.hex  (outside this project), or the path in TALLYMIS_SIGNING_KEY.
"""
import argparse
import os
import secrets
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import licensing as L  # noqa: E402


def key_path() -> Path:
    return Path(os.environ.get("TALLYMIS_SIGNING_KEY") or Path.home() / ".tallymis" / "signing_key.hex")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("keygen")
    sub.add_parser("machine")
    i = sub.add_parser("issue")
    i.add_argument("--licensee", required=True)
    i.add_argument("--machine", default="*", help="the customer's machine id, or * for any PC")
    i.add_argument("--days", type=int, help="valid for this many days (omit = never expires)")
    i.add_argument("--companies", type=int, help="how many real companies (omit = unlimited)")
    a = ap.parse_args()
    if a.cmd == "machine":
        print(L.machine_id())
    elif a.cmd == "keygen":
        p = key_path()
        if p.exists():
            sys.exit(f"A signing key already exists at {p}. Delete it yourself if you really want a new one (old licences will stop working).")
        p.parent.mkdir(parents=True, exist_ok=True)
        secret = secrets.token_bytes(32)
        p.write_text(secret.hex(), encoding="utf-8")
        print("Private key saved to", p, "(keep it secret, back it up, never commit it)")
        print("PUBLIC_KEY_HEX =", L.public_key_from_secret(secret).hex())
    else:
        secret = bytes.fromhex(key_path().read_text(encoding="utf-8").strip())
        exp = (date.today() + timedelta(days=a.days)).isoformat() if a.days else None
        print(L.make_key(secret, licensee=a.licensee, machine=a.machine, expires=exp, companies=a.companies))


if __name__ == "__main__":
    main()
