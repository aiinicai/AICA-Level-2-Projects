"""
access_control.py
------------------
Windows NTFS access-control layer: makes a locked folder refuse to open in
Explorer (or any other program running as this user) by applying an
explicit "Deny Read & Execute" ACE for the current user, and removing that
ACE again on unlock.

WHAT THIS IS AND IS NOT
~~~~~~~~~~~~~~~~~~~~~~~
This is a genuine use of the operating system's own permission system —
not a trick, and not an attempt to bypass or subvert OS security. It uses
the stock `icacls` tool exactly as an administrator would.

It is, however, a *deterrent*, not an unbreakable barrier:

* The folder's owner (you) always retains the WRITE_DAC right, so you can
  always change the permission back through Explorer's Security tab or
  `icacls`. Windows Explorer will even offer an administrator a "Continue"
  button that restores access in one click.
* An administrator, or anyone who can take ownership, can remove the ACE.
* Copying the folder to a non-NTFS volume (FAT32/exFAT, many USB sticks)
  or into a ZIP silently drops ACLs entirely.

That is why this layer is deliberately the *second* line of defence. The
real protection is that every file inside is AES-256-GCM ciphertext:
even with access fully restored, the contents are unreadable without the
password. Anyone claiming a user-space application can make a folder truly
un-openable on Windows without a kernel-mode filesystem driver is
overselling; this module does the strongest honest thing available.

Deliberately only "Read & Execute" is denied, never Delete. You must always
be able to remove your own folder, even if this application is uninstalled
or stops working.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

# Avoid a console window flashing up when the frozen --windowed .exe shells
# out to icacls.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0

# Object+Container inherit; deny FILE_LIST_DIRECTORY / FILE_READ_DATA ONLY.
#
# This exact right is load-bearing and must not be "strengthened" casually.
# Denying the broader (RX) also denies READ_CONTROL (permission to read the
# ACL) and traverse. On folders whose DACL grants the user access solely
# through an inherited OWNER RIGHTS ACE — which is what Windows produces in
# several common cases — that leaves nothing able to read the ACL in order
# to undo it, and the folder becomes permanently unreachable without an
# elevated administrator running takeown. That is unacceptable for user
# data. (RD) blocks opening the folder just as effectively while leaving
# READ_CONTROL and WRITE_DAC intact, so the restriction can always be
# lifted again. Verified against the worst-case DACL.
_DENY_RIGHTS = "(OI)(CI)(RD)"


class AccessControlError(Exception):
    """Raised when an ACL operation fails in a way the caller must know
    about (e.g. unlock could not restore access)."""


def is_available() -> bool:
    """ACL enforcement is Windows/NTFS only. Everywhere else the app still
    works, just without this extra layer (encryption is unaffected)."""
    return sys.platform == "win32"


def _run_icacls(args: list[str]) -> Tuple[int, str]:
    try:
        proc = subprocess.run(
            ["icacls", *args],
            capture_output=True,
            text=True,
            errors="replace",
            creationflags=_NO_WINDOW,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError as exc:
        raise AccessControlError("Windows 'icacls' tool was not found.") from exc
    except OSError as exc:
        raise AccessControlError(f"Could not run 'icacls': {exc}") from exc


def current_user() -> str:
    """Returns DOMAIN\\User for the account this process runs as."""
    try:
        proc = subprocess.run(
            ["whoami"], capture_output=True, text=True, errors="replace",
            creationflags=_NO_WINDOW,
        )
        name = (proc.stdout or "").strip()
        if name:
            return name
    except OSError:
        pass
    domain = os.environ.get("USERDOMAIN", "")
    user = os.environ.get("USERNAME", "")
    if domain and user:
        return f"{domain}\\{user}"
    if user:
        return user
    raise AccessControlError("Could not determine the current Windows user account.")


def _can_read_acl(folder_path: Path) -> bool:
    """Whether we can still read the folder's ACL — i.e. whether we are
    still able to undo a restriction we applied."""
    return _run_icacls([str(folder_path)])[0] == 0


def deny_access(folder_path: Path) -> None:
    """Blocks this user from opening/reading the folder.

    Applies a hard safety net: immediately after applying the restriction,
    it verifies the ACL is still readable (i.e. the restriction can still
    be lifted). If that check fails for any reason, the restriction is
    reverted at once and an error is raised. A folder must never be left
    in a state this application cannot undo.
    """
    if not is_available():
        raise AccessControlError("Folder access restriction is only supported on Windows (NTFS).")
    user = current_user()
    code, output = _run_icacls([str(folder_path), "/deny", f"{user}:{_DENY_RIGHTS}"])
    if code != 0:
        raise AccessControlError(
            "Could not restrict folder access. This usually means the drive is "
            f"not NTFS-formatted. Details: {output.strip()[:300]}"
        )

    if not _can_read_acl(folder_path):
        _run_icacls([str(folder_path), "/remove:d", user])
        raise AccessControlError(
            "Folder access restriction was reverted: applying it would have left "
            "the folder impossible to restore without administrator rights. The "
            "folder's contents remain encrypted."
        )


def restore_access(folder_path: Path) -> None:
    """Removes the Deny ACE this app applied, restoring normal access.
    Safe to call when no ACE is present (icacls treats it as a no-op)."""
    if not is_available():
        return
    user = current_user()
    code, output = _run_icacls([str(folder_path), "/remove:d", user])
    if code != 0:
        raise AccessControlError(
            "Could not restore folder access. You can restore it manually by "
            f'running:  icacls "{folder_path}" /remove:d "{user}"    '
            f"Details: {output.strip()[:300]}"
        )


def is_access_denied(folder_path: Path) -> bool:
    """Best-effort check of whether the folder is currently unreadable to
    us. Used only for diagnostics/UI hints, never as the authoritative
    lock-state source (that is the locked-folder registry)."""
    try:
        os.listdir(folder_path)
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def manual_restore_command(folder_path: Path) -> Optional[str]:
    """The exact command a user can run to recover access themselves if
    this application is ever unavailable. Surfaced in the UI and docs so
    nobody can be permanently locked out of their own folder by this app."""
    if not is_available():
        return None
    try:
        user = current_user()
    except AccessControlError:
        user = "%USERNAME%"
    return f'icacls "{folder_path}" /remove:d "{user}"'
