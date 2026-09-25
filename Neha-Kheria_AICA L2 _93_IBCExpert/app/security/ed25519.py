"""
Pure-Python Ed25519 digital signature implementation (RFC 8032).

WHY PURE PYTHON:
IBC Expert's licensing system must be able to VERIFY signatures on the
customer machine even if the optional `cryptography` package failed to
install (no internet, corporate firewall, antivirus interference, etc).
Since license/activation verification is the single most safety-critical
piece of the whole product, it must never depend on an optional native
extension compiling correctly. This module has ZERO external
dependencies (only hashlib), so it always works on any Python 3 install.

If the `cryptography` package IS available, higher layers may still use
it for speed elsewhere (e.g. bulk document encryption), but signature
verification always goes through this vetted, test-vector-checked code
path so behaviour is identical everywhere.

Implements RFC 8032 Ed25519 exactly (b=256, SHA-512, curve25519 twisted
Edwards form). Validated against the official RFC 8032 test vectors in
tests/test_ed25519.py.
"""
from __future__ import annotations

import hashlib

# ---- Curve constants (RFC 8032 / Ed25519) ----
_b = 256
_q = 2 ** 255 - 19
_l = 2 ** 252 + 27742317777372353535851937790883648493

def _H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()

def _inv(x: int) -> int:
    return pow(x, _q - 2, _q)

_d = (-121665 * _inv(121666)) % _q
_I = pow(2, (_q - 1) // 4, _q)

def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = pow(xx, (_q + 3) // 8, _q)
    if (x * x - xx) % _q != 0:
        x = (x * _I) % _q
    if x % 2 != 0:
        x = _q - x
    return x

_By = (4 * _inv(5)) % _q
_Bx = _xrecover(_By)
_B = (_Bx % _q, _By % _q)
_ZERO_PT = (0, 1)


def _edwards_add(P, Q):
    x1, y1 = P
    x2, y2 = Q
    dxxyy = _d * x1 * x2 * y1 * y2
    x3 = ((x1 * y2 + x2 * y1) * _inv(1 + dxxyy)) % _q
    y3 = ((y1 * y2 + x1 * x2) * _inv(1 - dxxyy)) % _q
    return (x3, y3)


def _scalarmult(P, e: int):
    if e == 0:
        return _ZERO_PT
    Q = _scalarmult(P, e // 2)
    Q = _edwards_add(Q, Q)
    if e & 1:
        Q = _edwards_add(Q, P)
    return Q


def _encodeint(y: int) -> bytes:
    return y.to_bytes(_b // 8, "little")


def _encodepoint(P) -> bytes:
    x, y = P
    out = bytearray(_encodeint(y))
    out[-1] = (out[-1] & 0x7F) | ((x & 1) << 7)
    return bytes(out)


def _decodeint(s: bytes) -> int:
    return int.from_bytes(s, "little")


def _decodepoint(s: bytes):
    y = int.from_bytes(s, "little") & ((1 << 255) - 1)
    x = _xrecover(y)
    if x & 1 != (s[31] >> 7) & 1:
        x = _q - x
    P = (x, y)
    if not _is_on_curve(P):
        raise ValueError("decoding point that is not on curve")
    return P


def _is_on_curve(P) -> bool:
    x, y = P
    return (-x * x + y * y - 1 - _d * x * x * y * y) % _q == 0


class BadSignatureError(Exception):
    """Raised when a signature fails verification."""


def generate_signing_key() -> bytes:
    """Generate a random 32-byte Ed25519 seed (the private key)."""
    import secrets
    return secrets.token_bytes(32)


def publickey_from_seed(seed: bytes) -> bytes:
    if len(seed) != 32:
        raise ValueError("seed must be 32 bytes")
    h = _H(seed)
    a = 2 ** (_b - 2) + sum(2 ** i * _bit(h, i) for i in range(3, _b - 2))
    A = _scalarmult(_B, a)
    return _encodepoint(A)


def _bit(h: bytes, i: int) -> int:
    return (h[i // 8] >> (i % 8)) & 1


def sign(seed: bytes, message: bytes) -> bytes:
    """Sign `message` with the 32-byte private seed. Returns 64-byte signature."""
    if len(seed) != 32:
        raise ValueError("seed must be 32 bytes")
    h = _H(seed)
    a = 2 ** (_b - 2) + sum(2 ** i * _bit(h, i) for i in range(3, _b - 2))
    r = _decodeint(_H(h[_b // 8: _b // 4] + message)) % _l
    R = _scalarmult(_B, r)
    A = _scalarmult(_B, a)
    S = (r + _decodeint(_H(_encodepoint(R) + _encodepoint(A) + message)) * a) % _l
    return _encodepoint(R) + _encodeint(S)


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Verify a 64-byte signature over `message` using a 32-byte public key.

    Returns True/False; never raises for a merely-invalid signature
    (only raises for structurally malformed input).
    """
    if len(public_key) != 32:
        raise ValueError("public key must be 32 bytes")
    if len(signature) != 64:
        return False
    try:
        R = _decodepoint(signature[:32])
        A = _decodepoint(public_key)
        S = _decodeint(signature[32:])
    except Exception:
        return False
    if S >= _l:
        return False
    h = _decodeint(_H(_encodepoint(R) + public_key + message)) % _l
    left = _scalarmult(_B, S)
    right = _edwards_add(R, _scalarmult(A, h))
    return left == right


def public_key_to_hex(pk: bytes) -> str:
    return pk.hex()


def public_key_from_hex(s: str) -> bytes:
    return bytes.fromhex(s)
