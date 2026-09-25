"""ChaCha20-Poly1305 authenticated encryption (RFC 8439).

This dependency-free implementation is used for portable encrypted containers.
When a packaged build includes `cryptography`, interoperability tests ensure the
same RFC format. No unauthenticated fallback exists.
"""
from __future__ import annotations

import hmac
import secrets
import struct

from app.core.errors import IntegrityError

KEY_SIZE = 32
NONCE_SIZE = 12
TAG_SIZE = 16
CONTAINER_MAGIC = b"IBCXAE01"


def _rotl32(value: int, count: int) -> int:
    return ((value << count) & 0xFFFFFFFF) | (value >> (32 - count))


def _quarter_round(state: list[int], a: int, b: int, c: int, d: int) -> None:
    state[a] = (state[a] + state[b]) & 0xFFFFFFFF
    state[d] ^= state[a]
    state[d] = _rotl32(state[d], 16)
    state[c] = (state[c] + state[d]) & 0xFFFFFFFF
    state[b] ^= state[c]
    state[b] = _rotl32(state[b], 12)
    state[a] = (state[a] + state[b]) & 0xFFFFFFFF
    state[d] ^= state[a]
    state[d] = _rotl32(state[d], 8)
    state[c] = (state[c] + state[d]) & 0xFFFFFFFF
    state[b] ^= state[c]
    state[b] = _rotl32(state[b], 7)


def chacha20_block(key: bytes, counter: int, nonce: bytes) -> bytes:
    if len(key) != KEY_SIZE or len(nonce) != NONCE_SIZE:
        raise ValueError("ChaCha20 requires a 32-byte key and 12-byte nonce")
    if not 0 <= counter <= 0xFFFFFFFF:
        raise ValueError("ChaCha20 counter outside uint32 range")
    constants = struct.unpack("<4I", b"expand 32-byte k")
    initial = list(constants + struct.unpack("<8I", key) + (counter,) + struct.unpack("<3I", nonce))
    working = initial.copy()
    for _ in range(10):
        _quarter_round(working, 0, 4, 8, 12)
        _quarter_round(working, 1, 5, 9, 13)
        _quarter_round(working, 2, 6, 10, 14)
        _quarter_round(working, 3, 7, 11, 15)
        _quarter_round(working, 0, 5, 10, 15)
        _quarter_round(working, 1, 6, 11, 12)
        _quarter_round(working, 2, 7, 8, 13)
        _quarter_round(working, 3, 4, 9, 14)
    return struct.pack("<16I", *((working[i] + initial[i]) & 0xFFFFFFFF for i in range(16)))


def _chacha20_xor(key: bytes, nonce: bytes, data: bytes, initial_counter: int = 1) -> bytes:
    if len(data) > (0xFFFFFFFF - initial_counter) * 64:
        raise ValueError("plaintext is too large for a single nonce")
    output = bytearray(len(data))
    for block_index, offset in enumerate(range(0, len(data), 64)):
        stream = chacha20_block(key, initial_counter + block_index, nonce)
        chunk = data[offset : offset + 64]
        output[offset : offset + len(chunk)] = bytes(a ^ b for a, b in zip(chunk, stream))
    return bytes(output)


def _poly1305_mac(message: bytes, one_time_key: bytes) -> bytes:
    if len(one_time_key) != 32:
        raise ValueError("Poly1305 one-time key must contain 32 bytes")
    r = int.from_bytes(one_time_key[:16], "little")
    r &= 0x0FFFFFFC0FFFFFFC0FFFFFFC0FFFFFFF
    s = int.from_bytes(one_time_key[16:], "little")
    accumulator = 0
    modulus = (1 << 130) - 5
    for offset in range(0, len(message), 16):
        block = message[offset : offset + 16]
        number = int.from_bytes(block + b"\x01", "little")
        accumulator = ((accumulator + number) * r) % modulus
    tag = (accumulator + s) % (1 << 128)
    return tag.to_bytes(16, "little")


def _pad16(data: bytes) -> bytes:
    remainder = len(data) % 16
    return b"" if remainder == 0 else bytes(16 - remainder)


def _mac_data(aad: bytes, ciphertext: bytes) -> bytes:
    return (
        aad
        + _pad16(aad)
        + ciphertext
        + _pad16(ciphertext)
        + struct.pack("<Q", len(aad))
        + struct.pack("<Q", len(ciphertext))
    )


def encrypt(key: bytes, plaintext: bytes, aad: bytes = b"", nonce: bytes | None = None) -> bytes:
    if len(key) != KEY_SIZE:
        raise ValueError("encryption key must contain 32 bytes")
    nonce = nonce if nonce is not None else secrets.token_bytes(NONCE_SIZE)
    if len(nonce) != NONCE_SIZE:
        raise ValueError("nonce must contain 12 bytes")
    poly_key = chacha20_block(key, 0, nonce)[:32]
    ciphertext = _chacha20_xor(key, nonce, plaintext, 1)
    tag = _poly1305_mac(_mac_data(aad, ciphertext), poly_key)
    return nonce + ciphertext + tag


def decrypt(key: bytes, payload: bytes, aad: bytes = b"") -> bytes:
    if len(key) != KEY_SIZE:
        raise ValueError("decryption key must contain 32 bytes")
    if len(payload) < NONCE_SIZE + TAG_SIZE:
        raise IntegrityError("Encrypted information is incomplete or damaged.")
    nonce = payload[:NONCE_SIZE]
    ciphertext = payload[NONCE_SIZE:-TAG_SIZE]
    supplied_tag = payload[-TAG_SIZE:]
    poly_key = chacha20_block(key, 0, nonce)[:32]
    expected_tag = _poly1305_mac(_mac_data(aad, ciphertext), poly_key)
    if not hmac.compare_digest(supplied_tag, expected_tag):
        raise IntegrityError("Encrypted information failed its integrity check.")
    return _chacha20_xor(key, nonce, ciphertext, 1)


def seal_container(key: bytes, plaintext: bytes, context: bytes) -> bytes:
    """Versioned binary envelope; context is authenticated but not stored."""
    return CONTAINER_MAGIC + encrypt(key, plaintext, CONTAINER_MAGIC + context)


def open_container(key: bytes, container: bytes, context: bytes) -> bytes:
    if not container.startswith(CONTAINER_MAGIC):
        raise IntegrityError("Encrypted container format is invalid.")
    return decrypt(key, container[len(CONTAINER_MAGIC):], CONTAINER_MAGIC + context)
