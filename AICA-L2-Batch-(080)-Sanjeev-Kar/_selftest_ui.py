"""
Ad-hoc self-test that actually constructs every GUI dialog class with a
real Tkinter root (this machine has a real Windows desktop, so this is not
mocked) and immediately tears each one down. This catches widget-
construction bugs — like passing a pack()-only tuple option (e.g.
pady=(10, 0)) straight into a Frame/Label constructor, which Tk accepts
syntactically but rejects at runtime with TclError: "bad screen distance"
— that headless crypto/logic self-tests can never exercise, since they
never actually build a single widget.

Does NOT require a webcam: AuthDialog/EnrollmentDialog kick off their
camera work in a background thread *after* their widgets are already
built, so we can construct-then-immediately-destroy them without a camera
ever needing to succeed.

Run: python _selftest_ui.py
"""
import shutil
import tempfile
import tkinter as tk
from pathlib import Path

import config

tmp_root = Path(tempfile.mkdtemp(prefix="flock_ui_selftest_"))
config.APP_DATA_DIR = tmp_root / "appdata"
config.VAULT_DIR = config.APP_DATA_DIR / "vault"
config.LOG_DIR = config.APP_DATA_DIR / "logs"
config.DEVICE_KEY_FILE = config.VAULT_DIR / "device.key"
config.FACE_TEMPLATE_FILE = config.VAULT_DIR / "face_template.enc"
config.PASSWORD_VAULT_FILE = config.VAULT_DIR / "password_vault.json"
config.SETTINGS_FILE = config.VAULT_DIR / "settings.json"
config.ensure_dirs()

import ui  # noqa: E402

root = tk.Tk()
root.withdraw()  # no visible flicker; we're only checking construction succeeds

failures = []


def try_build(label, factory):
    try:
        widget = factory()
        root.update()  # process any pending idle tasks the constructor scheduled
        widget.destroy()
        root.update()
        print(f"  OK: {label}")
    except Exception as exc:
        failures.append((label, exc))
        print(f"  FAIL: {label} -> {type(exc).__name__}: {exc}")


print("== CameraPanel renders at the intended pixel size, not a tiny collapsed box ==")
import numpy as np  # noqa: E402

TOLERANCE_PX = 10  # Label border/padding adds a few px beyond the raw image size


def _assert_reasonable_size(label, w, h, when):
    target_w, target_h = ui.PREVIEW_SIZE
    assert abs(w - target_w) <= TOLERANCE_PX and abs(h - target_h) <= TOLERANCE_PX, (
        f"BUG: preview is {w}x{h} {when} — expected close to {ui.PREVIEW_SIZE} "
        f"(this is exactly the old bug: Label width/height silently switch from "
        f"character-units to pixel-units once an image is set, collapsing the "
        f"preview to a near-invisible size)"
    )


panel = ui.CameraPanel(root)
panel.pack()
root.update_idletasks()
w0, h0 = panel.image_label.winfo_reqwidth(), panel.image_label.winfo_reqheight()
print(f"  before any frame: {w0}x{h0}")
_assert_reasonable_size(panel.image_label, w0, h0, "before any frame")

fake_frame = np.zeros((240, 320, 3), dtype=np.uint8)  # arbitrary camera-like BGR frame
panel.set_frame(fake_frame)
root.update_idletasks()
w1, h1 = panel.image_label.winfo_reqwidth(), panel.image_label.winfo_reqheight()
print(f"  after a real frame: {w1}x{h1}")
_assert_reasonable_size(panel.image_label, w1, h1, "after receiving a frame")

panel.set_status("Face recognized")
assert panel.status_label.cget("fg") == ui.STATUS_COLOR_SUCCESS
panel.set_status("Face not recognized")
assert panel.status_label.cget("fg") == ui.STATUS_COLOR_DENIED
panel.destroy()
print(f"  OK: preview stays a visible {ui.PREVIEW_SIZE[0]}x{ui.PREVIEW_SIZE[1]} px before and after a frame, status colors switch correctly")

print("== constructing every dialog/screen with real Tkinter widgets ==")
try_build(
    "FolderCredentialsWizard",
    lambda: ui.FolderCredentialsWizard(root, "ui-test-profile", tmp_root / "SomeFolder"),
)
try_build(
    "FolderPicker (empty)",
    lambda: ui.FolderPicker(root, [], title="Test", action_label="Go"),
)
try_build(
    "FolderPicker (populated)",
    lambda: ui.FolderPicker(
        root,
        [{"path": str(tmp_root / "A"), "profile_id": "p1", "locked": True, "exists": True},
         {"path": str(tmp_root / "B"), "profile_id": "p2", "locked": False, "exists": False}],
        title="Test", action_label="Go", allow_browse=True,
    ),
)
try_build("LockedFolderPicker", lambda: ui.LockedFolderPicker(root))
try_build("EnrollmentDialog", lambda: ui.EnrollmentDialog(root, "ui-test-profile"))
try_build("NewPasswordDialog", lambda: ui.NewPasswordDialog(root))
try_build("SecuritySettingsDialog", lambda: ui.SecuritySettingsDialog(root))
try_build("AuthDialog (mode=full)", lambda: ui.AuthDialog(root, "ui-test-profile", mode="full"))
try_build("AuthDialog (mode=face_only)", lambda: ui.AuthDialog(root, "ui-test-profile", mode="face_only"))

print("== constructing the main App window itself ==")
try:
    app = ui.App()
    app.update()
    app.destroy()
    print("  OK: App main window")
except Exception as exc:
    failures.append(("App main window", exc))
    print(f"  FAIL: App main window -> {type(exc).__name__}: {exc}")

root.destroy()
shutil.rmtree(tmp_root, ignore_errors=True)

if failures:
    print(f"\n{len(failures)} WIDGET CONSTRUCTION FAILURE(S):")
    for label, exc in failures:
        print(f"  - {label}: {exc}")
    raise SystemExit(1)

print("\nALL UI WIDGET CONSTRUCTION SELF-TESTS PASSED")
