"""
Ad-hoc self-test for the access-restriction layer: proves that a locked
folder genuinely cannot be opened (not merely that its contents are
encrypted), and — just as importantly — that access is always fully
restored afterwards so nobody can be stranded out of their own data.

Runs entirely inside a throwaway temp directory. Every path it touches is
one it created itself.

Run: python _selftest_access.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

import config

tmp_root = Path(tempfile.mkdtemp(prefix="flock_access_selftest_"))
config.APP_DATA_DIR = tmp_root / "appdata"
config.VAULT_DIR = config.APP_DATA_DIR / "vault"
config.LOG_DIR = config.APP_DATA_DIR / "logs"
config.DEVICE_KEY_FILE = config.VAULT_DIR / "device.key"
config.FACE_TEMPLATE_FILE = config.VAULT_DIR / "face_template.enc"
config.PASSWORD_VAULT_FILE = config.VAULT_DIR / "password_vault.json"
config.SETTINGS_FILE = config.VAULT_DIR / "settings.json"
config.ensure_dirs()

import access_control  # noqa: E402
import folder_manager  # noqa: E402
import security  # noqa: E402

protected = tmp_root / "ClientFiles"
(protected / "sub").mkdir(parents=True)
(protected / "invoice.txt").write_text("confidential invoice")
(protected / "sub" / "notes.txt").write_text("private notes")

PROFILE = "access-test-profile"
master_key = security.generate_master_key()


def _can_open(path: Path) -> bool:
    try:
        os.listdir(path)
        return True
    except PermissionError:
        return False
    except OSError:
        return False


def _cleanup_and_exit(code: int) -> None:
    # Never leave a deny ACE behind on a test folder, even on failure.
    try:
        if protected.exists():
            access_control.restore_access(protected)
    except Exception:
        pass
    shutil.rmtree(tmp_root, ignore_errors=True)
    sys.exit(code)


try:
    print(f"== platform: {sys.platform} | access restriction available: {access_control.is_available()} ==")

    print("== before locking: folder opens normally ==")
    assert _can_open(protected), "test folder should be readable before locking"
    print("  OK: folder opens, contents visible")

    print("== locking ==")
    folder_manager.lock_folder(protected, master_key, PROFILE, progress_cb=lambda m: None)
    assert folder_manager.is_locked(protected), "folder should report as locked"
    print("  OK: locked, registry updated")

    if access_control.is_available():
        print("== THE ACTUAL REQUIREMENT: locked folder must not open ==")
        opened = _can_open(protected)
        assert not opened, "BUG: locked folder can still be opened/listed"
        print("  OK: folder REFUSES to open (PermissionError) while locked")

        print("== registry records that access was restricted ==")
        entry = folder_manager._registry_entry(protected)
        assert entry is not None and entry.get("access_restricted") is True
        print("  OK: registry entry records access_restricted=True")

        print("== lock state is still detectable even though folder is unreadable ==")
        assert folder_manager.is_locked(protected), "is_locked must not depend on reading the folder"
        print("  OK: is_locked() works via the registry, not by reading inside")

        print("== a manual recovery command is always available to the user ==")
        cmd = access_control.manual_restore_command(protected)
        assert cmd and "icacls" in cmd and "/remove:d" in cmd
        print(f"  OK: {cmd}")
    else:
        print("  SKIPPED: access restriction is Windows-only; encryption still applies")

    print("== unlocking restores access AND decrypts ==")
    folder_manager.unlock_folder(protected, master_key, progress_cb=lambda m: None)
    assert _can_open(protected), "BUG: folder still not openable after unlock"
    assert not folder_manager.is_locked(protected), "folder should no longer report as locked"
    assert (protected / "invoice.txt").read_text() == "confidential invoice"
    assert (protected / "sub" / "notes.txt").read_text() == "private notes"
    print("  OK: access restored, nested contents intact and readable")

    print("== registry marks it unlocked but REMEMBERS its credentials ==")
    entry = folder_manager._registry_entry(protected)
    assert entry is not None, "the folder should stay on record after unlocking"
    assert entry.get("locked") is False, "it must no longer be marked locked"
    assert entry.get("profile_id") == PROFILE, (
        "its credentials must be remembered so re-locking reuses the same "
        "password and face instead of silently starting over"
    )
    assert all(e["path"] != str(protected) for e in folder_manager.list_locked_folders())
    print("  OK: marked unlocked, still bound to its own profile")

    print("== failed unlock (wrong key) must NOT downgrade protection ==")
    folder_manager.lock_folder(protected, master_key, PROFILE, progress_cb=lambda m: None)
    wrong_key = security.generate_master_key()
    try:
        folder_manager.unlock_folder(protected, wrong_key, progress_cb=lambda m: None)
        raise SystemExit("FAIL: unlock with the wrong key did not raise")
    except SystemExit:
        raise
    except Exception:
        pass  # expected: authentication/tamper failure
    assert folder_manager.is_locked(protected), "folder must remain locked after a failed unlock"
    if access_control.is_available():
        assert not _can_open(protected), (
            "BUG: a failed unlock attempt left the folder openable — protection was downgraded"
        )
        print("  OK: still locked AND still access-restricted after a failed attempt")
    else:
        print("  OK: still locked after a failed attempt")

    print("== final unlock with the correct key ==")
    folder_manager.unlock_folder(protected, master_key, progress_cb=lambda m: None)
    assert _can_open(protected)
    assert (protected / "invoice.txt").read_text() == "confidential invoice"
    print("  OK: recovered cleanly")

except AssertionError as exc:
    print(f"\nASSERTION FAILED: {exc}")
    _cleanup_and_exit(1)
except SystemExit:
    raise
except Exception as exc:
    print(f"\nUNEXPECTED ERROR: {type(exc).__name__}: {exc}")
    _cleanup_and_exit(1)

print("\nALL ACCESS-CONTROL SELF-TESTS PASSED")
_cleanup_and_exit(0)
