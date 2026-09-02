"""
Ad-hoc self-test for PER-FOLDER credentials: proves that each protected
folder has genuinely independent credentials, so that one folder's password
or face grants no access whatsoever to another folder.

This is the security property that matters most about the per-folder
design, so it is asserted directly rather than assumed from the fact that
separate files exist on disk.

Run: python _selftest_multi.py
"""
import atexit
import shutil
import sys
import tempfile
from pathlib import Path

import access_control
import config
import security

tmp_root = Path(tempfile.mkdtemp(prefix="flock_multi_selftest_"))


@atexit.register
def _cleanup() -> None:
    try:
        for child in list(tmp_root.rglob("*")) + [tmp_root]:
            if child.is_dir():
                try:
                    access_control.restore_access(child)
                except Exception:
                    pass
    except Exception:
        pass
    shutil.rmtree(tmp_root, ignore_errors=True)


config.APP_DATA_DIR = tmp_root / "appdata"
config.VAULT_DIR = config.APP_DATA_DIR / "vault"
config.LOG_DIR = config.APP_DATA_DIR / "logs"
config.DEVICE_KEY_FILE = config.VAULT_DIR / "device.key"
config.SETTINGS_FILE = config.VAULT_DIR / "settings.json"
config.ensure_dirs()

import folder_manager  # noqa: E402
import password_auth  # noqa: E402

# Two folders, each with its own password and its own encryption key.
folder_a = tmp_root / "ClientA"
folder_b = tmp_root / "ClientB"
folder_a.mkdir()
folder_b.mkdir()
(folder_a / "a-secret.txt").write_text("client A confidential")
(folder_b / "b-secret.txt").write_text("client B confidential")

PW_A = "AlphaPass1!"
PW_B = "BravoPass2@"

profile_a = folder_manager.new_profile_id()
profile_b = folder_manager.new_profile_id()

print("== distinct profile ids ==")
assert profile_a != profile_b
print(f"  OK: {profile_a[:8]}... != {profile_b[:8]}...")

print("== each folder gets its own independent master key ==")
key_a = security.generate_master_key()
key_b = security.generate_master_key()
assert key_a != key_b, "each folder must get its own randomly generated key"
password_auth.create_password_vault(profile_a, PW_A, key_a)
password_auth.create_password_vault(profile_b, PW_B, key_b)
print("  OK: two independent keys, two independent password vaults")

print("== a folder's own password recovers only its own key ==")
got_a = password_auth.verify_password_and_get_master_key(profile_a, PW_A)
got_b = password_auth.verify_password_and_get_master_key(profile_b, PW_B)
assert got_a == key_a and got_b == key_b
assert got_a != got_b
print("  OK: each password unlocks exactly one folder's key")

print("== THE KEY PROPERTY: folder A's password must NOT open folder B ==")
try:
    password_auth.verify_password_and_get_master_key(profile_b, PW_A)
    raise SystemExit("FAIL: folder A's password was accepted for folder B")
except security.AuthenticationError:
    print("  OK: A's password rejected by B")
try:
    password_auth.verify_password_and_get_master_key(profile_a, PW_B)
    raise SystemExit("FAIL: folder B's password was accepted for folder A")
except security.AuthenticationError:
    print("  OK: B's password rejected by A")

print("== lock both folders independently ==")
folder_manager.assign_profile(folder_a, profile_a)
folder_manager.assign_profile(folder_b, profile_b)
folder_manager.lock_folder(folder_a, key_a, profile_a, progress_cb=lambda m: None)
folder_manager.lock_folder(folder_b, key_b, profile_b, progress_cb=lambda m: None)
assert folder_manager.is_locked(folder_a) and folder_manager.is_locked(folder_b)
assert folder_manager.profile_id_for(folder_a) == profile_a
assert folder_manager.profile_id_for(folder_b) == profile_b
print("  OK: both locked, each bound to its own profile")

print("== folder B's key must NOT decrypt folder A ==")
try:
    folder_manager.unlock_folder(folder_a, key_b, progress_cb=lambda m: None)
    raise SystemExit("FAIL: folder B's key decrypted folder A")
except SystemExit:
    raise
except Exception:
    print("  OK: cross-folder decryption rejected")
assert folder_manager.is_locked(folder_a), "A must remain locked after the failed attempt"

print("== unlocking A leaves B untouched ==")
folder_manager.unlock_folder(folder_a, key_a, progress_cb=lambda m: None)
assert not folder_manager.is_locked(folder_a)
assert folder_manager.is_locked(folder_b), "unlocking one folder must not unlock another"
assert (folder_a / "a-secret.txt").read_text() == "client A confidential"
print("  OK: A is open, B is still locked")

print("== changing A's password does not affect B ==")
password_auth.change_password(profile_a, PW_A, "NewAlpha9#")
assert password_auth.verify_password_and_get_master_key(profile_a, "NewAlpha9#") == key_a
assert password_auth.verify_password_and_get_master_key(profile_b, PW_B) == key_b
try:
    password_auth.verify_password_and_get_master_key(profile_b, "NewAlpha9#")
    raise SystemExit("FAIL: A's new password works on B")
except security.AuthenticationError:
    pass
print("  OK: B's password is unchanged and still exclusively B's")

print("== unlock B with its own credentials ==")
folder_manager.unlock_folder(folder_b, key_b, progress_cb=lambda m: None)
assert (folder_b / "b-secret.txt").read_text() == "client B confidential"
print("  OK: B recovered with its own key")

print("== registry tracks both folders separately ==")
known = {e["path"]: e for e in folder_manager.list_known_folders()}
assert str(folder_a) in known and str(folder_b) in known
assert known[str(folder_a)]["profile_id"] != known[str(folder_b)]["profile_id"]
print("  OK: two folders, two profiles, tracked independently")

print("== deleting a profile is refused while it protects a locked folder ==")
folder_manager.lock_folder(folder_b, key_b, profile_b, progress_cb=lambda m: None)
try:
    folder_manager.delete_profile(profile_b)
    raise SystemExit("FAIL: deleted credentials still protecting a locked folder")
except SystemExit:
    raise
except folder_manager.FolderManagerError:
    print("  OK: refused to delete in-use credentials")
folder_manager.unlock_folder(folder_b, key_b, progress_cb=lambda m: None)

print("\nALL PER-FOLDER CREDENTIAL SELF-TESTS PASSED")
sys.exit(0)
