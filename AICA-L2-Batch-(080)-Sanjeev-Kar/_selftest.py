"""
Ad-hoc self-test (not part of the shipped app) exercising the non-camera
crypto/file layers: password validation, master-key wrapping, streaming
file encryption/decryption round-trip, tamper detection, and a full
folder lock/unlock cycle. Run manually: python _selftest.py
"""
import shutil
import tempfile
from pathlib import Path

import atexit

import access_control
import config
import encryption
import folder_manager
import password_auth
import security

tmp_root = Path(tempfile.mkdtemp(prefix="flock_selftest_"))


@atexit.register
def _guaranteed_cleanup() -> None:
    """A test that dies part-way through a lock would otherwise leave an
    access-restricted temp folder behind that rmtree cannot even enumerate.
    Always lift any restriction we applied before deleting."""
    try:
        for child in tmp_root.rglob("*"):
            if child.is_dir():
                try:
                    access_control.restore_access(child)
                except Exception:
                    pass
        access_control.restore_access(tmp_root)
    except Exception:
        pass
    shutil.rmtree(tmp_root, ignore_errors=True)
config.APP_DATA_DIR = tmp_root / "appdata"
config.VAULT_DIR = config.APP_DATA_DIR / "vault"
config.LOG_DIR = config.APP_DATA_DIR / "logs"
config.DEVICE_KEY_FILE = config.VAULT_DIR / "device.key"
config.FACE_TEMPLATE_FILE = config.VAULT_DIR / "face_template.enc"
config.PASSWORD_VAULT_FILE = config.VAULT_DIR / "password_vault.json"
config.SETTINGS_FILE = config.VAULT_DIR / "settings.json"
config.ensure_dirs()

print("== password validation ==")
for pw, expect_ok in [
    ("123456", False),
    ("abcdef", False),
    ("abc123", False),
    ("abcdef!", False),
    ("Abc1!x", True),
    ("Secure9@", True),
    ("MyLock#7", True),
]:
    ok, problems = password_auth.validate_password(pw)
    status = "OK" if ok == expect_ok else "FAIL"
    print(f"  {status}: {pw!r} -> valid={ok} problems={problems}")
    assert ok == expect_ok, f"password validation mismatch for {pw!r}"

print("== master key wrap / unwrap via password vault ==")
master_key = security.generate_master_key()
PROFILE = "test-profile"
password_auth.create_password_vault(PROFILE, "Correct#123", master_key)
recovered = password_auth.verify_password_and_get_master_key(PROFILE, "Correct#123")
assert recovered == master_key, "recovered master key mismatch"
print("  OK: correct password recovers exact master key")

try:
    password_auth.verify_password_and_get_master_key(PROFILE, "Wrong#12345")
    raise SystemExit("FAIL: wrong password did not raise")
except security.AuthenticationError:
    print("  OK: wrong password rejected (AuthenticationError)")

print("== best_effort_zero actually wipes the real key (not a throwaway copy) ==")
key_to_wipe = password_auth.verify_password_and_get_master_key(PROFILE, "Correct#123")
assert isinstance(key_to_wipe, bytearray), "keys must be mutable bytearray so they can genuinely be zeroed"
assert any(b != 0 for b in key_to_wipe), "sanity check: key should not already be all zero"
security.best_effort_zero(key_to_wipe)
assert all(b == 0 for b in key_to_wipe), "best_effort_zero did not actually wipe the real key buffer"
print("  OK: the actual key buffer is zeroed in place, not a disposable bytearray() copy")

print("== change password re-wraps same master key ==")
password_auth.change_password(PROFILE, "Correct#123", "NewPass#456")
recovered2 = password_auth.verify_password_and_get_master_key(PROFILE, "NewPass#456")
assert recovered2 == master_key
print("  OK: master key unchanged after password change")

print("== streaming file encryption round-trip (multi-chunk) ==")
config.save_settings({"chunk_size_bytes": 1024})  # force multiple small chunks
work = tmp_root / "work"
work.mkdir()
plain = work / "plain.bin"
plain.write_bytes(bytes((i % 256) for i in range(5000)))
enc = work / "plain.bin.enc"
dec = work / "plain.bin.dec"
encryption.encrypt_file(plain, enc, master_key, b"selftest/plain.bin")
encryption.decrypt_file(enc, dec, master_key, b"selftest/plain.bin")
assert dec.read_bytes() == plain.read_bytes()
print(f"  OK: {plain.stat().st_size} bytes round-tripped across multiple chunks")

print("== zero-byte file round-trip ==")
empty = work / "empty.bin"
empty.write_bytes(b"")
enc0 = work / "empty.bin.enc"
dec0 = work / "empty.bin.dec"
encryption.encrypt_file(empty, enc0, master_key, b"selftest/empty.bin")
encryption.decrypt_file(enc0, dec0, master_key, b"selftest/empty.bin")
assert dec0.read_bytes() == b""
print("  OK: zero-byte file round-tripped")

print("== tamper detection ==")
tampered = bytearray(enc.read_bytes())
tampered[-1] ^= 0xFF  # flip a bit in the last chunk's ciphertext/tag
enc_tampered = work / "plain.bin.tampered.enc"
enc_tampered.write_bytes(bytes(tampered))
try:
    encryption.decrypt_file(enc_tampered, work / "should_not_exist.dec", master_key, b"selftest/plain.bin")
    raise SystemExit("FAIL: tampered ciphertext decrypted without error")
except security.TamperDetectedError:
    print("  OK: bit-flip in ciphertext detected (TamperDetectedError)")
assert not (work / "should_not_exist.dec").exists(), "FAIL: partial plaintext leaked to disk after tamper"
print("  OK: no partial plaintext file was left on disk")

print("== wrong AAD (simulated path-rename attack) detected ==")
try:
    encryption.decrypt_file(enc, work / "should_not_exist2.dec", master_key, b"selftest/DIFFERENT_PATH.bin")
    raise SystemExit("FAIL: wrong AAD decrypted without error")
except security.TamperDetectedError:
    print("  OK: mismatched associated data (moved/renamed file) detected")

print("== full folder lock/unlock cycle (folder name/path must never change) ==")
protected = tmp_root / "MyDocs"
(protected / "sub").mkdir(parents=True)
(protected / "a.txt").write_text("hello world")
(protected / "sub" / "b.bin").write_bytes(bytes(range(256)) * 20)
(protected / "sub" / "empty_dir").mkdir()

assert not folder_manager.is_locked(protected)

events = []
result_path = folder_manager.lock_folder(protected, master_key, PROFILE, progress_cb=events.append)
assert result_path == protected, "lock_folder must return the SAME path, not a renamed one"
assert protected.exists() and protected.is_dir(), "folder must still exist at its original name/path after locking"
assert folder_manager.is_locked(protected), "folder should now report as locked"
assert (protected / "a.txt.enc").exists(), "plaintext file should be replaced by its encrypted form"
assert not (protected / "a.txt").exists(), "plaintext file should no longer exist in cleartext"
print(f"  OK: locked in place - still named '{protected.name}' at the same path ({len(events)} progress events)")

restored_path = folder_manager.unlock_folder(protected, master_key, progress_cb=events.append)
assert restored_path == protected, "unlock_folder must return the SAME path"
assert not folder_manager.is_locked(protected), "folder should no longer report as locked"
assert (protected / "a.txt").read_text() == "hello world"
assert (protected / "sub" / "b.bin").read_bytes() == bytes(range(256)) * 20
assert (protected / "sub" / "empty_dir").is_dir()
print("  OK: unlocked in place, file contents + empty directory structure preserved, name unchanged throughout")

print("== lock refuses to double-lock an already-locked folder ==")
folder_manager.lock_folder(protected, master_key, PROFILE, progress_cb=lambda m: None)
try:
    folder_manager.lock_folder(protected, master_key, PROFILE, progress_cb=lambda m: None)
    raise SystemExit("FAIL: locking an already-locked folder did not raise")
except folder_manager.FolderManagerError:
    print("  OK: refused to lock an already-locked folder")

print("== unlock refuses to unlock a folder that isn't locked ==")
folder_manager.unlock_folder(protected, master_key, progress_cb=lambda m: None)  # back to plaintext
try:
    folder_manager.unlock_folder(protected, master_key, progress_cb=lambda m: None)
    raise SystemExit("FAIL: unlocking a non-locked folder did not raise")
except folder_manager.FolderManagerError:
    print("  OK: refused to unlock a folder that isn't locked")

shutil.rmtree(tmp_root, ignore_errors=True)
print("\nALL SELF-TESTS PASSED")
