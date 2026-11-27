"""Keeps statement passwords on THIS laptop only, in Windows Credential Manager (through the 'keyring' package).
One password per label, for example: cas, bank_a, zerodha, fund_a. Set one with:  py set_password.py <label> Nothing is written to a file.
Other programs on this laptop run under your Windows sign-in can read it, which is the same as any saved Windows password.
"""
SERVICE = "AICA_private"


def _kr():
    try:
        import keyring
        return keyring
    except ImportError:
        return None


def get(label):
    kr = _kr()
    if kr is None:
        return None
    try:
        return kr.get_password(SERVICE, label)
    except Exception:
        return None


def put(label, password):
    kr = _kr()
    if kr is None:
        raise RuntimeError("keyring is missing. Type:  pip install keyring")
    kr.set_password(SERVICE, label, password)


def delete(label):
    kr = _kr()
    if kr is None:
        return
    try:
        kr.delete_password(SERVICE, label)
    except Exception:
        pass
