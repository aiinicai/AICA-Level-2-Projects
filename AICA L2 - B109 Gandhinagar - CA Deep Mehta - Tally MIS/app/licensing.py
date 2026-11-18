"""Licensing: signed, offline licence keys. No server, no internet.

A licence key is  base64url(JSON) + "." + base64url(Ed25519 signature).  The app holds only the PUBLIC key, so it can check a key
but nobody can make one without the private key, which stays with the owner and is never part of this project.

What a licence can limit (all optional in the key):
  * machine  – the key only works on one PC (a fingerprint of the Windows machine id); "*" = any PC (for reviewers)
  * expires  – last valid date
  * companies – how many real (non-demo) companies may be loaded
Without a valid key the app runs in EVALUATION mode: the fictional demo company is unlimited, but real data is limited to
one company, three months per Tally sync and files up to 3 MB. Saved only as a small text file; no company data is involved.

Honest note: the source is open, so this deters casual or commercial reuse; it cannot stop a determined programmer. The
legal protection is the LICENSE file at the top of the project.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------------------------- Ed25519 (RFC 8032, pure Python)
_P = 2**255 - 19
_D = -121665 * pow(121666, _P - 2, _P) % _P
_Q = 2**252 + 27742317777372353535851937790883648493


def _inv(x: int) -> int:
    return pow(x, _P - 2, _P)


def _recover_x(y: int, sign: int):
    if y >= _P:
        return None
    x2 = (y * y - 1) * _inv(_D * y * y + 1) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * pow(2, (_P - 1) // 4, _P) % _P
    if (x * x - x2) % _P:
        return None
    return _P - x if (x & 1) != sign else x


_GY = 4 * _inv(5) % _P
_GX = _recover_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)


def _add(a, b):
    A, B = (a[1] - a[0]) * (b[1] - b[0]) % _P, (a[1] + a[0]) * (b[1] + b[0]) % _P
    C, D = 2 * a[3] * b[3] * _D % _P, 2 * a[2] * b[2] % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _mul(s: int, p):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _add(q, p)
        p = _add(p, p)
        s >>= 1
    return q


def _same(a, b) -> bool:
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _compress(p) -> bytes:
    zi = _inv(p[2])
    x, y = p[0] * zi % _P, p[1] * zi % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(s: bytes):
    y = int.from_bytes(s, "little")
    sign, y = y >> 255, y & ((1 << 255) - 1)
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def _h(b: bytes) -> int:
    return int.from_bytes(hashlib.sha512(b).digest(), "little") % _Q


def _expand(secret: bytes):
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key_from_secret(secret: bytes) -> bytes:
    return _compress(_mul(_expand(secret)[0], _G))


def sign(secret: bytes, msg: bytes) -> bytes:
    a, prefix = _expand(secret)
    pub = _compress(_mul(a, _G))
    r = _h(prefix + msg)
    big_r = _compress(_mul(r, _G))
    s = (r + _h(big_r + pub + msg) * a) % _Q
    return big_r + int.to_bytes(s, 32, "little")


def verify(public: bytes, msg: bytes, sig: bytes) -> bool:
    if len(public) != 32 or len(sig) != 64:
        return False
    a, r = _decompress(public), _decompress(sig[:32])
    if a is None or r is None:
        return False
    s = int.from_bytes(sig[32:], "little")
    if s >= _Q:
        return False
    return _same(_mul(s, _G), _add(r, _mul(_h(sig[:32] + public + msg), a)))


# ---------------------------------------------------------------------------------------------- the licence
# The owner's PUBLIC key (the matching private key is kept outside this project and is never published).
PUBLIC_KEY_HEX = "55026a67bc9a9c99473c09d07cefb58960e9581207672da591d0a280f7410b04"

EVAL_LIMITS = {"companies": 1, "monthsPerSync": 3, "importMB": 3}


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def machine_id() -> str:
    """A stable, anonymous fingerprint of this PC (a hash; the raw id never leaves the machine)."""
    raw = ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as k:
            raw = str(winreg.QueryValueEx(k, "MachineGuid")[0])
    except Exception:
        import uuid
        raw = str(uuid.getnode())
    h = hashlib.sha256(("tallymis|" + raw).encode()).hexdigest()[:16].upper()
    return "-".join(h[i:i + 4] for i in range(0, 16, 4))


def make_key(secret: bytes, *, licensee: str, machine: str = "*", expires: str | None = None, companies: int | None = None,
             edition: str = "full", issued: str | None = None) -> str:
    payload = {"v": 1, "licensee": licensee, "machine": machine, "edition": edition, "issued": issued or date.today().isoformat(),
               "expires": expires, "companies": companies}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return _b64e(body) + "." + _b64e(sign(secret, body))


@dataclass
class Licence:
    status: str          # licensed | evaluation | expired | wrong_machine | invalid
    message: str
    licensee: str | None = None
    expires: str | None = None
    companies: int | None = None   # None = unlimited
    edition: str | None = None

    def public(self) -> dict:
        return {"status": self.status, "message": self.message, "licensee": self.licensee, "expires": self.expires,
                "companies": self.companies, "edition": self.edition, "machineId": machine_id(),
                "evaluationLimits": EVAL_LIMITS if self.status != "licensed" else None}

    @property
    def licensed(self) -> bool:
        return self.status == "licensed"


def check_key(key: str, *, today: date | None = None, public_hex: str | None = None, machine: str | None = None) -> Licence:
    today = today or date.today()
    try:
        body_b64, sig_b64 = key.strip().split(".")
        body, sig = _b64d(body_b64), _b64d(sig_b64)
    except Exception:
        return Licence("invalid", "That licence key is not in the right format.")
    if not verify(bytes.fromhex(public_hex or PUBLIC_KEY_HEX), body, sig):
        return Licence("invalid", "That licence key is not genuine (the signature does not match).")
    try:
        p = json.loads(body)
        lic = Licence("licensed", "Licensed", p.get("licensee"), p.get("expires"), p.get("companies"), p.get("edition"))
        if p.get("machine") not in ("*", machine or machine_id()):
            return Licence("wrong_machine", "This licence key was issued for a different computer.", p.get("licensee"), p.get("expires"))
        if p.get("expires") and date.fromisoformat(p["expires"]) < today:
            return Licence("expired", f"This licence expired on {p['expires']}.", p.get("licensee"), p.get("expires"))
        return lic
    except Exception:
        return Licence("invalid", "That licence key could not be read.")


def _store_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home())
    return base / "TallyMIS" / "licence.key"


class LicenceManager:
    """Holds the current licence. The key is kept as a small text file in the user's AppData folder."""

    def __init__(self, path: Path | None = None, public_hex: str | None = None):
        self.path, self.public_hex = path or _store_path(), public_hex
        self.current = self._load()

    def _load(self) -> Licence:
        try:
            key = self.path.read_text(encoding="utf-8").strip()
        except OSError:
            return Licence("evaluation", "Evaluation mode: the demo company is unlimited; real data is limited. Enter a licence key to unlock.")
        return check_key(key, public_hex=self.public_hex)

    def activate(self, key: str) -> Licence:
        lic = check_key(key, public_hex=self.public_hex)
        if lic.licensed:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(key.strip(), encoding="utf-8")
            self.current = lic
        return lic

    def remove(self) -> Licence:
        try:
            self.path.unlink()
        except OSError:
            pass
        self.current = self._load()
        return self.current

    # ---- the rules the server applies
    def check_sync(self, months: int, real_companies_after: int) -> str | None:
        lic = self.current
        if lic.licensed:
            return self._company_rule(lic.companies, real_companies_after)
        if months > EVAL_LIMITS["monthsPerSync"]:
            return (f"Evaluation mode syncs up to {EVAL_LIMITS['monthsPerSync']} months at a time. "
                    "Enter a licence key (Settings → Licence) to sync more.")
        return self._company_rule(EVAL_LIMITS["companies"], real_companies_after)

    def check_import(self, size_bytes: int, real_companies_after: int) -> str | None:
        lic = self.current
        if lic.licensed:
            return self._company_rule(lic.companies, real_companies_after)
        if size_bytes > EVAL_LIMITS["importMB"] * 1024 * 1024:
            return (f"Evaluation mode imports files up to {EVAL_LIMITS['importMB']} MB. "
                    "Enter a licence key (Settings → Licence) to import larger files.")
        return self._company_rule(EVAL_LIMITS["companies"], real_companies_after)

    @staticmethod
    def _company_rule(limit: int | None, after: int) -> str | None:
        if limit is not None and after > limit:
            return (f"Your licence allows {limit} real {'company' if limit == 1 else 'companies'}. "
                    "Remove the others or enter a licence key that allows more (Settings → Licence).")
        return None


def _main_not_used() -> None:  # pragma: no cover
    print("Use tools/make_license.py to create keys.", file=sys.stderr)
