from __future__ import annotations

import json

import pytest

from app.core.errors import AuthenticationError, IntegrityError
from app.security import aead
from app.security.kdf import derive_subkey
from app.security.passwords import (
    change_master_password,
    create_master_envelope,
    unlock_master_envelope,
)


def test_chacha20_rfc8439_block_vector():
    key = bytes.fromhex(
        "000102030405060708090a0b0c0d0e0f"
        "101112131415161718191a1b1c1d1e1f"
    )
    nonce = bytes.fromhex("000000090000004a00000000")
    expected = bytes.fromhex(
        "10f1e7e4d13b5915500fdd1fa32071c4"
        "c7d1f4c733c068030422aa9ac3d46c4e"
        "d2826446079faa0914c2d705d98b02a2"
        "b5129cd1de164eb9cbd083e8a2503c4e"
    )
    assert aead.chacha20_block(key, 1, nonce) == expected


def test_aead_rfc8439_vector():
    key = bytes.fromhex(
        "808182838485868788898a8b8c8d8e8f"
        "909192939495969798999a9b9c9d9e9f"
    )
    nonce = bytes.fromhex("070000004041424344454647")
    aad = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")
    plaintext = bytes.fromhex(
        "4c616469657320616e642047656e746c656d656e206f662074686520636c61737320"
        "6f66202739393a204966204920636f756c64206f6666657220796f75206f6e6c7920"
        "6f6e652074697020666f7220746865206675747572652c2073756e73637265656e20"
        "776f756c642062652069742e"
    )
    expected_ciphertext = bytes.fromhex(
        "d31a8d34648e60db7b86afbc53ef7ec2a4aded51296e08fea9e2b5a736ee62d6"
        "3dbea45e8ca9671282fafb69da92728b1a71de0a9e060b2905d6a5b67ecd3b36"
        "92ddbd7f2d778b8c9803aee328091b58fab324e4fad675945585808b4831d7bc"
        "3ff4def08e4b7a9de576d26586cec64b6116"
    )
    expected_tag = bytes.fromhex("1ae10b594f09e26a7e902ecbd0600691")
    payload = aead.encrypt(key, plaintext, aad, nonce)
    assert payload[:12] == nonce
    assert payload[12:-16] == expected_ciphertext
    assert payload[-16:] == expected_tag
    assert aead.decrypt(key, payload, aad) == plaintext


def test_tampered_ciphertext_and_aad_are_rejected():
    key = bytes(range(32))
    payload = aead.encrypt(key, b"confidential claim data", b"client:1")
    changed = bytearray(payload)
    changed[15] ^= 1
    with pytest.raises(IntegrityError):
        aead.decrypt(key, bytes(changed), b"client:1")
    with pytest.raises(IntegrityError):
        aead.decrypt(key, payload, b"client:2")


def test_subkeys_are_separated_by_purpose_and_object():
    master = bytes(range(32))
    assert derive_subkey(master, "vault", "1") != derive_subkey(master, "backup", "1")
    assert derive_subkey(master, "vault", "1") != derive_subkey(master, "vault", "2")
    assert derive_subkey(master, "vault", "1") == derive_subkey(master, "vault", "1")


def test_master_password_round_trip_wrong_password_and_change():
    envelope, expected_master = create_master_envelope("correct horse battery staple")
    assert unlock_master_envelope("correct horse battery staple", envelope) == expected_master
    with pytest.raises(AuthenticationError):
        unlock_master_envelope("wrong password is long enough", envelope)
    replacement = change_master_password(
        "correct horse battery staple", "a new and much better password", envelope
    )
    assert unlock_master_envelope("a new and much better password", replacement) == expected_master
    with pytest.raises(AuthenticationError):
        unlock_master_envelope("correct horse battery staple", replacement)
