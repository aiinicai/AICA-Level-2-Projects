"""Saves ONE statement password on THIS laptop, in Windows Credential Manager. Nothing is written to a file.

Use:  py set_password.py cas              (type the password when asked; it is not shown)
      py set_password.py bank_a
      py set_password.py cas --delete     (removes the saved password)

The label is the statement type used by probe_all.py: cas, zerodha, zerodha_cn, bank_a, bank_b, fund_a, fund_b.
The readers use the saved password, so it is typed once. It is never in a file, on a command line, or sent to Claude.
Needs:  pip install keyring
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import secrets_store  # noqa: E402


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 1
    label = args[0].strip().lower()
    if "--delete" in argv:
        secrets_store.delete(label)
        print(f"Removed the saved password for '{label}' (if there was one).")
        return 0
    pw = getpass.getpass(f"Password for '{label}' (hidden): ")
    if not pw:
        print("Nothing typed. Nothing saved.")
        return 1
    try:
        secrets_store.put(label, pw)
    except RuntimeError as e:
        print(e)
        return 1
    print(f"Saved '{label}' in Windows Credential Manager.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
