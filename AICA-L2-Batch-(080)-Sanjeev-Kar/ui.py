"""
ui.py
------
Tkinter desktop GUI. Wires together face_auth, password_auth, and
folder_manager and enforces the mandatory authentication order:

    FACE RECOGNITION  -->  PASSWORD  -->  UNLOCK / LOCK / CHANGE CREDENTIALS

The password entry screen is only ever constructed/shown *after* a
background face-verification task has reported success (see
`AuthDialog._on_face_done`). There is no code path that reveals the
password field first.
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

import access_control
import config
import face_auth
import folder_manager
import password_auth
import security

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

logger = logging.getLogger("folder_lock")

MAX_PASSWORD_ATTEMPTS = 5
WINDOW_BG = "#1e1e2e"


class Status:
    FACE_NOT_RECOGNIZED = "Face not recognized"
    FACE_RECOGNIZED = "Face recognized"
    ENTER_PASSWORD = "Enter password"
    INCORRECT_PASSWORD = "Incorrect password"
    FOLDER_UNLOCKED = "Folder unlocked"
    ENCRYPTION_COMPLETED = "Encryption completed"
    ENCRYPTION_FAILED = "Encryption failed"
    DECRYPTION_FAILED = "Decryption failed"
    ACCESS_DENIED = "ACCESS DENIED"


def _safe_error_text(exc: Exception) -> str:
    """Show a clear but non-sensitive message. Our own SecurityError
    subclasses already carry safe, user-facing text; anything unexpected is
    reported by type name only, never a raw traceback (which could contain
    file-system detail we'd rather not surface, though never secrets)."""
    if isinstance(exc, security.SecurityError):
        return str(exc)
    return f"{type(exc).__name__}: an unexpected error occurred."


PREVIEW_SIZE = (480, 360)  # visible camera preview size, in pixels

STATUS_COLOR_SUCCESS = "#1b8a3a"
STATUS_COLOR_DENIED = "#c62828"
STATUS_COLOR_WARNING = "#b8860b"
STATUS_COLOR_NEUTRAL = "#1e1e1e"


def _status_color(text: str) -> str:
    """Maps a status message to a color so the user can tell at a glance
    what's happening (success / denied / needs-attention / neutral),
    without having to read closely."""
    lower = text.lower()
    if any(p in lower for p in ("not recognized", "access denied", "could not be confirmed", "cancelled", "failed")):
        return STATUS_COLOR_DENIED
    if any(p in lower for p in ("recognized", "enrolled successfully", "liveness confirmed")):
        return STATUS_COLOR_SUCCESS
    if any(p in lower for p in ("no face detected", "multiple faces", "move closer")):
        return STATUS_COLOR_WARNING
    return STATUS_COLOR_NEUTRAL


def _frame_to_photo(frame_bgr, size=PREVIEW_SIZE):
    if Image is None or ImageTk is None or frame_bgr is None:
        return None
    rgb = frame_bgr[:, :, ::-1]
    img = Image.fromarray(rgb).resize(size)
    return ImageTk.PhotoImage(img)


# ---------------------------------------------------------------------------
# Reusable widgets
# ---------------------------------------------------------------------------


class CameraPanel(tk.Frame):
    """Displays a live camera preview plus a prominent, color-coded status
    line. IMPORTANT: tk.Label's width/height are measured in *characters* if
    the label has no image, but silently switch to *pixels* the moment an
    image is set — so the preview must be given a real (blank) image from
    the start to guarantee a stable, correctly-sized pixel box throughout,
    rather than collapsing to a near-invisible size the first time a camera
    frame arrives."""

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        if Image is not None and ImageTk is not None:
            self._blank = ImageTk.PhotoImage(Image.new("RGB", PREVIEW_SIZE, (0, 0, 0)))
            self.image_label = tk.Label(self, image=self._blank, bg="black")
        else:
            self._blank = None
            self.image_label = tk.Label(self, bg="black", width=60, height=22)
        self.image_label.pack()
        self.status_label = tk.Label(
            self, text="", font=("Segoe UI", 13, "bold"),
            wraplength=PREVIEW_SIZE[0], justify="center", fg=STATUS_COLOR_NEUTRAL,
        )
        self.status_label.pack(pady=(10, 0))
        self._photo = None

    def set_status(self, text: str) -> None:
        self.status_label.config(text=text, fg=_status_color(text))

    def set_frame(self, frame_bgr) -> None:
        photo = _frame_to_photo(frame_bgr)
        if photo is not None:
            self._photo = photo  # keep a reference alive
            self.image_label.config(image=photo)


class PasswordChecklist(tk.Frame):
    """Live-updating checklist of the four password requirements."""

    LABELS = [
        "6+ characters",
        "Contains a letter",
        "Contains a number",
        "Contains a symbol",
    ]

    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.rows = []
        for text in self.LABELS:
            row = tk.Label(self, text=f"✗ {text}", fg="#b00020", anchor="w", justify="left")
            row.pack(fill="x")
            self.rows.append(row)

    def update_from(self, password: str) -> bool:
        settings = config.get_settings()
        min_len = settings["min_password_length"]
        checks = [
            len(password or "") >= min_len,
            any(c.isalpha() for c in (password or "")),
            any(c.isdigit() for c in (password or "")),
            any(not c.isalnum() for c in (password or "")),
        ]
        for row, ok, label in zip(self.rows, checks, self.LABELS):
            row.config(
                text=f"{'✓' if ok else '✗'} {label}",
                fg="#2e7d32" if ok else "#b00020",
            )
        return all(checks)


class BackgroundFaceTask:
    """Runs a face_auth call (enroll or verify) in a daemon thread and
    forwards status/frame/result events through a thread-safe queue for a
    Tk widget to poll on the main thread (Tk/Tcl is not thread-safe)."""

    def __init__(self, fn, **kwargs):
        self._queue: "queue.Queue" = queue.Queue()
        self._cancel_flag = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(fn, kwargs), daemon=True)

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        self._cancel_flag.set()

    def _should_cancel(self) -> bool:
        return self._cancel_flag.is_set()

    def _run(self, fn, kwargs) -> None:
        try:
            result = fn(
                on_status=lambda m: self._queue.put(("status", m)),
                on_frame=lambda f: self._queue.put(("frame", f)),
                should_cancel=self._should_cancel,
                **kwargs,
            )
            self._queue.put(("done", result))
        except Exception as exc:  # surfaced to the UI, never swallowed
            self._queue.put(("error", exc))

    def poll(self):
        events = []
        try:
            while True:
                events.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        return events


# ---------------------------------------------------------------------------
# Mandatory FACE -> PASSWORD authentication dialog
# ---------------------------------------------------------------------------


class AuthDialog(tk.Toplevel):
    """mode="full": on success self.result = master_key (bytes).
    mode="face_only": on success self.result = True.
    Denial or cancellation always leaves self.result = None.

    The password widgets are created but never packed/shown until the face
    stage reports a match — enforcing FACE -> PASSWORD at the UI level, not
    just by convention.
    """

    def __init__(self, master, profile_id: str, mode: str = "full", title: str = "Authenticate"):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.configure(padx=4, pady=4)
        self.profile_id = profile_id
        self.mode = mode
        self.result = None
        self._task: Optional[BackgroundFaceTask] = None
        self._attempts = 0

        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self.camera_panel = CameraPanel(self, padx=16, pady=16)
        self.camera_panel.pack()

        self.password_frame = tk.Frame(self, padx=16, pady=8)
        tk.Label(self.password_frame, text=Status.ENTER_PASSWORD, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.password_var = tk.StringVar()
        self.password_entry = tk.Entry(self.password_frame, textvariable=self.password_var, show="*", width=32)
        self.password_entry.pack(fill="x", pady=(4, 0))
        self.password_entry.bind("<Return>", lambda _e: self._submit_password())
        self.password_status = tk.Label(self.password_frame, text="", fg="#b00020")
        self.password_status.pack(anchor="w")
        tk.Button(self.password_frame, text="Submit", command=self._submit_password).pack(anchor="e", pady=(6, 0))

        btn_frame = tk.Frame(self, padx=16, pady=8)
        btn_frame.pack(fill="x")
        self.retry_btn = tk.Button(btn_frame, text="Try Again", command=self._start_face_stage)
        tk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side="right")

        self._start_face_stage()

    def _start_face_stage(self) -> None:
        self.retry_btn.pack_forget()
        self.password_frame.pack_forget()
        self.password_var.set("")
        self.password_status.config(text="")
        self.camera_panel.set_status("Starting camera...")
        fa = face_auth.FaceAuthenticator(self.profile_id)
        self._task = BackgroundFaceTask(fa.verify)
        self._task.start()
        self.after(60, self._poll_face)

    def _poll_face(self) -> None:
        if not self.winfo_exists():
            return  # dialog was closed/cancelled; stop touching destroyed widgets
        for kind, payload in self._task.poll():
            if kind == "status":
                self.camera_panel.set_status(payload)
            elif kind == "frame":
                self.camera_panel.set_frame(payload)
            elif kind == "done":
                self._on_face_done(bool(payload))
                return
            elif kind == "error":
                self._on_face_error(payload)
                return
        self.after(60, self._poll_face)

    def _on_face_error(self, exc: Exception) -> None:
        logger.warning("face verification error: %s", type(exc).__name__)
        messagebox.showerror("Camera error", _safe_error_text(exc), parent=self)
        self.result = None
        self.destroy()

    def _on_face_done(self, matched: bool) -> None:
        if not matched:
            logger.info("face verification denied")
            self.camera_panel.set_status(f"{Status.FACE_NOT_RECOGNIZED}\n{Status.ACCESS_DENIED}")
            self.retry_btn.pack(side="left")
            return
        logger.info("face verification succeeded")
        self.camera_panel.set_status(Status.FACE_RECOGNIZED)
        if self.mode == "face_only":
            self.result = True
            self.after(400, self.destroy)
            return
        self.after(300, self._show_password_stage)

    def _show_password_stage(self) -> None:
        self.retry_btn.pack_forget()
        self.password_frame.pack()
        self.password_entry.focus_set()

    def _submit_password(self) -> None:
        password = self.password_var.get()
        try:
            master_key = password_auth.verify_password_and_get_master_key(self.profile_id, password)
        except security.AuthenticationError:
            logger.info("password verification failed")
            self._attempts += 1
            remaining = MAX_PASSWORD_ATTEMPTS - self._attempts
            self.password_var.set("")
            if remaining <= 0:
                self.password_status.config(text=f"{Status.INCORRECT_PASSWORD}. {Status.ACCESS_DENIED}")
                self.result = None
                self.after(900, self.destroy)
            else:
                self.password_status.config(text=f"{Status.INCORRECT_PASSWORD} ({remaining} attempts left)")
            return
        except security.SecurityError as exc:
            messagebox.showerror("Error", _safe_error_text(exc), parent=self)
            self.result = None
            self.destroy()
            return

        logger.info("password verification succeeded")
        self.password_var.set("")
        self.result = master_key
        self.destroy()

    def _on_cancel(self) -> None:
        if self._task:
            self._task.cancel()
        self.result = None
        self.destroy()


# ---------------------------------------------------------------------------
# First-time setup wizard (and face re-enrollment reuse)
# ---------------------------------------------------------------------------


class EnrollmentDialog(tk.Toplevel):
    """Standalone camera-driven enrollment screen. Used by the setup wizard
    and by the Enroll/Re-enroll Face menu action (after prior verification
    for re-enrollment, enforced by the caller)."""

    def __init__(self, master, profile_id: str, title: str = "Face Enrollment"):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.profile_id = profile_id
        self.success = False
        self._task: Optional[BackgroundFaceTask] = None

        tk.Label(
            self,
            text="Look directly at the camera. We will capture several samples.\n"
                 "Please only one face in frame.",
            padx=16, justify="center",
        ).pack(pady=(16, 0))

        self.camera_panel = CameraPanel(self, padx=16, pady=16)
        self.camera_panel.pack()

        self.start_btn = tk.Button(self, text="Begin Enrollment", command=self._start)
        self.start_btn.pack(pady=(0, 12))
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _start(self) -> None:
        self.start_btn.config(state="disabled")
        fa = face_auth.FaceAuthenticator(self.profile_id)
        self._task = BackgroundFaceTask(fa.enroll)
        self._task.start()
        self.after(60, self._poll)

    def _poll(self) -> None:
        if not self.winfo_exists():
            return  # dialog was closed/cancelled; stop touching destroyed widgets
        for kind, payload in self._task.poll():
            if kind == "status":
                self.camera_panel.set_status(payload)
            elif kind == "frame":
                self.camera_panel.set_frame(payload)
            elif kind == "done":
                self.success = True
                self.after(600, self.destroy)
                return
            elif kind == "error":
                messagebox.showerror("Enrollment failed", _safe_error_text(payload), parent=self)
                self.destroy()
                return
        self.after(60, self._poll)

    def _on_cancel(self) -> None:
        if self._task:
            self._task.cancel()
        self.destroy()


class FolderCredentialsWizard(tk.Toplevel):
    """Creates the password + enrolled face for ONE folder.

    Each folder gets its own independent credentials, so this runs once per
    folder rather than once per installation. On success `success` is True
    and `master_key` holds that folder's freshly generated encryption key,
    handed straight to the caller so the folder can be locked immediately
    without making the user authenticate again seconds after choosing the
    password."""

    def __init__(self, master, profile_id: str, folder_path: Path, on_complete=None):
        super().__init__(master)
        self.title(f"Set Up Protection - {Path(folder_path).name}")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.profile_id = profile_id
        self.folder_path = Path(folder_path)
        self.success = False
        self.master_key: Optional[bytearray] = None
        self._on_complete = on_complete
        self._password = None
        self._active_task: Optional[BackgroundFaceTask] = None

        self.container = tk.Frame(self, padx=20, pady=20)
        self.container.pack()

        self._show_password_step()

    def _clear(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    def _show_password_step(self) -> None:
        self._clear()
        tk.Label(self.container, text="Create Password", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(
            self.container,
            text="These credentials protect only this folder:\n" + str(self.folder_path),
            fg="#555555", justify="left", wraplength=340,
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(self.container, text="Password:").pack(anchor="w", pady=(10, 0))
        pw_var = tk.StringVar()
        pw_entry = tk.Entry(self.container, textvariable=pw_var, show="*", width=34)
        pw_entry.pack()

        tk.Label(self.container, text="Confirm password:").pack(anchor="w", pady=(8, 0))
        pw2_var = tk.StringVar()
        pw2_entry = tk.Entry(self.container, textvariable=pw2_var, show="*", width=34)
        pw2_entry.pack()

        checklist = PasswordChecklist(self.container)
        checklist.pack(fill="x", pady=(10, 0))

        match_label = tk.Label(self.container, text="", fg="#b00020")
        match_label.pack(anchor="w")

        next_btn = tk.Button(self.container, text="Next", state="disabled")
        next_btn.pack(anchor="e", pady=(12, 0))

        def on_change(*_args) -> None:
            valid = checklist.update_from(pw_var.get())
            match = pw_var.get() == pw2_var.get() and pw_var.get() != ""
            match_label.config(text="" if match else "Passwords do not match.")
            next_btn.config(state="normal" if (valid and match) else "disabled")

        pw_var.trace_add("write", on_change)
        pw2_var.trace_add("write", on_change)

        def go_next() -> None:
            ok, problems = password_auth.validate_password(pw_var.get())
            if not ok:
                messagebox.showerror("Invalid password", "\n".join(problems), parent=self)
                return
            self._password = pw_var.get()
            pw_var.set("")
            pw2_var.set("")
            self._commit_password_and_continue()

        next_btn.config(command=go_next)
        pw_entry.focus_set()

    def _commit_password_and_continue(self) -> None:
        # This folder's own randomly generated encryption key. Deliberately
        # NOT zeroed here: the caller locks the folder with it immediately
        # after the wizard finishes, so wiping it now would force the user
        # to re-authenticate seconds after choosing their password. The
        # caller zeroes it once the lock completes.
        master_key = security.generate_master_key()
        try:
            password_auth.create_password_vault(self.profile_id, self._password, master_key)
        except Exception as exc:
            security.best_effort_zero(master_key)
            messagebox.showerror("Error", _safe_error_text(exc), parent=self)
            return
        finally:
            self._password = None
        self.master_key = master_key
        messagebox.showinfo(
            "Password accepted",
            "Password accepted for this folder.\n\nNow enroll the face that will unlock it.",
            parent=self,
        )
        self._show_face_step()

    def _show_face_step(self) -> None:
        self._clear()
        tk.Label(self.container, text="Face Enrollment", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(
            self.container,
            text="Starting camera...\nPlease look at the camera.",
            justify="center",
        ).pack(pady=(6, 6))

        cam = CameraPanel(self.container)
        cam.pack()
        start_btn = tk.Button(self.container, text="Begin Enrollment")
        start_btn.pack(pady=10)

        def start() -> None:
            start_btn.config(state="disabled")
            fa = face_auth.FaceAuthenticator(self.profile_id)
            task = BackgroundFaceTask(fa.enroll)
            self._active_task = task
            task.start()

            def poll() -> None:
                if not self.winfo_exists():
                    return  # window was closed/cancelled; stop touching destroyed widgets
                for kind, payload in task.poll():
                    if kind == "status":
                        cam.set_status(payload)
                    elif kind == "frame":
                        cam.set_frame(payload)
                    elif kind == "done":
                        self._active_task = None
                        self.success = True
                        messagebox.showinfo(
                            "Setup complete",
                            f"Face enrolled successfully.\n\nThis face and "
                            f"password now protect '{self.folder_path.name}' only.",
                            parent=self,
                        )
                        if self._on_complete:
                            self._on_complete()
                        self.destroy()
                        return
                    elif kind == "error":
                        self._active_task = None
                        messagebox.showerror("Enrollment failed", _safe_error_text(payload), parent=self)
                        start_btn.config(state="normal")
                        return
                self.after(60, poll)

            self.after(60, poll)

        start_btn.config(command=start)

    def _on_close(self) -> None:
        if not messagebox.askyesno(
            "Cancel setup?",
            "Setup for this folder is not complete, so it will NOT be locked. Cancel?",
            parent=self,
        ):
            return
        if self._active_task is not None:
            self._active_task.cancel()
        # Abandoning half-way would otherwise leave a profile holding a
        # password but no enrolled face - unusable, and it would block a
        # later attempt to set this folder up properly. Discard it.
        if not self.success:
            if self.master_key is not None:
                security.best_effort_zero(self.master_key)
                self.master_key = None
            folder_manager.delete_profile(self.profile_id)
        self.destroy()


# ---------------------------------------------------------------------------
# Security settings
# ---------------------------------------------------------------------------


class SecuritySettingsDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Security Settings")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        settings = config.get_settings()
        frm = tk.Frame(self, padx=16, pady=16)
        frm.pack()

        row = 0
        tk.Label(frm, text="Face match threshold (LBPH confidence, lower = stricter):").grid(row=row, column=0, sticky="w")
        self.threshold_var = tk.DoubleVar(value=settings["face_match_threshold"])
        tk.Spinbox(frm, from_=20, to=150, increment=1, textvariable=self.threshold_var, width=8).grid(row=row, column=1)
        row += 1

        tk.Label(frm, text="Face verification timeout (seconds):").grid(row=row, column=0, sticky="w")
        self.timeout_var = tk.IntVar(value=settings["face_verify_timeout_seconds"])
        tk.Spinbox(frm, from_=10, to=90, textvariable=self.timeout_var, width=8).grid(row=row, column=1)
        row += 1

        self.liveness_var = tk.BooleanVar(value=settings["liveness_check_enabled"])
        tk.Checkbutton(frm, text="Enable blink-based liveness check", variable=self.liveness_var).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1

        tk.Label(
            frm,
            text=(
                "Liveness check is a coarse, best-effort deterrent against a static\n"
                "photo — it watches for the eye detector briefly losing and then\n"
                "regaining both eyes, as happens during a natural blink. It is NOT a\n"
                "robust anti-spoofing measure and will not reliably stop a video\n"
                "replay attack or a printed photo held very steadily."
            ),
            fg="#8a6d00", justify="left", wraplength=380,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 8))
        row += 1

        self.restrict_var = tk.BooleanVar(value=settings.get("restrict_folder_access", True))
        tk.Checkbutton(
            frm, text="Block locked folders from opening (Windows/NTFS only)",
            variable=self.restrict_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(6, 0))
        row += 1

        tk.Label(
            frm,
            text=(
                "Applies a Windows 'Deny Read' permission so a locked folder refuses\n"
                "to open in Explorer. This is a deterrent layered on top of encryption,\n"
                "not a replacement for it: as the folder's owner you can always restore\n"
                "access through Windows' own Security tab, and an administrator can\n"
                "always override it. Your files stay unreadable either way, because\n"
                "their contents are encrypted."
            ),
            fg="#8a6d00", justify="left", wraplength=420,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 8))
        row += 1

        tk.Label(frm, text="Argon2id time cost (applies at next password change):").grid(row=row, column=0, sticky="w")
        self.time_cost_var = tk.IntVar(value=settings["argon2_time_cost"])
        tk.Spinbox(frm, from_=1, to=10, textvariable=self.time_cost_var, width=8).grid(row=row, column=1)
        row += 1

        tk.Label(frm, text="Argon2id memory cost (KiB):").grid(row=row, column=0, sticky="w")
        self.mem_cost_var = tk.IntVar(value=settings["argon2_memory_cost_kib"])
        tk.Spinbox(frm, from_=8192, to=262144, increment=8192, textvariable=self.mem_cost_var, width=8).grid(row=row, column=1)
        row += 1

        tk.Label(frm, text="Argon2id parallelism:").grid(row=row, column=0, sticky="w")
        self.parallelism_var = tk.IntVar(value=settings["argon2_parallelism"])
        tk.Spinbox(frm, from_=1, to=8, textvariable=self.parallelism_var, width=8).grid(row=row, column=1)
        row += 1

        tk.Label(frm, text="App data directory:").grid(row=row, column=0, sticky="w", pady=(10, 0))
        data_dir_entry = tk.Entry(frm, width=42)
        data_dir_entry.grid(row=row, column=1, pady=(10, 0))
        data_dir_entry.insert(0, str(config.APP_DATA_DIR))
        data_dir_entry.config(state="readonly")
        row += 1

        tk.Button(frm, text="Rotate device key (re-encrypt face template)", command=self._rotate_device_key).grid(
            row=row, column=0, columnspan=2, sticky="we", pady=(10, 0)
        )
        row += 1

        btns = tk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=2, pady=(14, 0), sticky="e")
        tk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        tk.Button(btns, text="Save", command=self._save).pack(side="right")

    def _rotate_device_key(self) -> None:
        if not messagebox.askyesno(
            "Rotate device key",
            "This re-encrypts every folder's stored face template under a new local key.\n"
            "It does not change any enrolled face or require re-enrollment.\nContinue?",
            parent=self,
        ):
            return
        try:
            count = face_auth.rotate_device_key_all_profiles()
            messagebox.showinfo(
                "Done",
                f"Device key rotated. {count} folder face template(s) re-encrypted.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Error", _safe_error_text(exc), parent=self)

    def _save(self) -> None:
        config.save_settings({
            "face_match_threshold": float(self.threshold_var.get()),
            "face_verify_timeout_seconds": int(self.timeout_var.get()),
            "liveness_check_enabled": bool(self.liveness_var.get()),
            "restrict_folder_access": bool(self.restrict_var.get()),
            "argon2_time_cost": int(self.time_cost_var.get()),
            "argon2_memory_cost_kib": int(self.mem_cost_var.get()),
            "argon2_parallelism": int(self.parallelism_var.get()),
        })
        messagebox.showinfo("Saved", "Settings saved.", parent=self)
        self.destroy()


# ---------------------------------------------------------------------------
# New-password dialog (used by Change Password)
# ---------------------------------------------------------------------------


class NewPasswordDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Set New Password")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.new_password: Optional[str] = None

        frm = tk.Frame(self, padx=20, pady=20)
        frm.pack()

        tk.Label(frm, text="New password:").pack(anchor="w")
        pw_var = tk.StringVar()
        tk.Entry(frm, textvariable=pw_var, show="*", width=34).pack()

        tk.Label(frm, text="Confirm new password:").pack(anchor="w", pady=(8, 0))
        pw2_var = tk.StringVar()
        tk.Entry(frm, textvariable=pw2_var, show="*", width=34).pack()

        checklist = PasswordChecklist(frm)
        checklist.pack(fill="x", pady=(10, 0))
        match_label = tk.Label(frm, text="", fg="#b00020")
        match_label.pack(anchor="w")

        ok_btn = tk.Button(frm, text="Change Password", state="disabled")
        ok_btn.pack(anchor="e", pady=(12, 0))

        def on_change(*_a):
            valid = checklist.update_from(pw_var.get())
            match = pw_var.get() == pw2_var.get() and pw_var.get() != ""
            match_label.config(text="" if match else "Passwords do not match.")
            ok_btn.config(state="normal" if (valid and match) else "disabled")

        pw_var.trace_add("write", on_change)
        pw2_var.trace_add("write", on_change)

        def confirm():
            self.new_password = pw_var.get()
            pw_var.set("")
            pw2_var.set("")
            self.destroy()

        ok_btn.config(command=confirm)
        self.protocol("WM_DELETE_WINDOW", self.destroy)


# ---------------------------------------------------------------------------
# Folder pickers
# ---------------------------------------------------------------------------


class FolderPicker(tk.Toplevel):
    """Chooses among folders this app knows about.

    A picker rather than a browse dialog because a locked folder is
    access-restricted: Explorer cannot open it, so there is nothing to
    confirm by browsing into it. `selected` is the chosen Path, or None.
    """

    def __init__(self, master, entries, title="Select Folder",
                 action_label="Select", allow_browse=False, empty_message=None):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.selected = None
        self._entries = list(entries)

        frm = tk.Frame(self, padx=16, pady=16)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text=title + ":", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        list_frame = tk.Frame(frm)
        list_frame.pack(fill="both", expand=True, pady=(6, 0))
        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        self.listbox = tk.Listbox(
            list_frame, width=68, height=8, yscrollcommand=scrollbar.set, font=("Consolas", 9)
        )
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda _e: self._choose())

        if self._entries:
            for entry in self._entries:
                bits = []
                if entry.get("locked"):
                    bits.append("LOCKED")
                if not entry.get("exists", True):
                    bits.append("MISSING")
                suffix = ("   [" + ", ".join(bits) + "]") if bits else ""
                self.listbox.insert("end", entry["path"] + suffix)
            self.listbox.selection_set(0)
        else:
            self.listbox.insert("end", empty_message or "(nothing to show)")
            self.listbox.config(state="disabled")

        tk.Label(
            frm,
            text="Each folder has its own password and its own enrolled face.",
            fg="#555555", justify="left",
        ).pack(anchor="w", pady=(8, 0))

        btns = tk.Frame(frm)
        btns.pack(fill="x", pady=(12, 0))
        tk.Button(btns, text="Cancel", command=self._cancel).pack(side="right")
        tk.Button(btns, text=action_label, command=self._choose).pack(side="right", padx=(0, 6))
        if allow_browse:
            tk.Button(btns, text="Browse...", command=self._browse).pack(side="left")
        if any(not e.get("exists", True) for e in self._entries):
            tk.Button(btns, text="Forget Missing", command=self._forget_missing).pack(side="left", padx=(6, 0))

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _choose(self):
        if not self._entries:
            return
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("Select a folder", "Please select a folder from the list.", parent=self)
            return
        entry = self._entries[sel[0]]
        if not entry.get("exists", True):
            messagebox.showerror(
                "Folder missing",
                "This folder no longer exists at that location. It may have been "
                "moved or deleted outside this app." + NL + NL + "Use 'Forget Missing' to remove it.",
                parent=self,
            )
            return
        self.selected = Path(entry["path"])
        self.destroy()

    def _browse(self):
        chosen = filedialog.askdirectory(title="Select folder", parent=self)
        if chosen:
            self.selected = Path(chosen)
            self.destroy()

    def _forget_missing(self):
        missing = [e for e in self._entries if not e.get("exists", True)]
        if not missing:
            messagebox.showinfo("Nothing to forget", "All listed folders still exist.", parent=self)
            return
        if not messagebox.askyesno(
            "Forget missing folders",
            "Remove " + str(len(missing)) + " missing folder(s) from the list?" + NL + NL
            + "This only updates this app's records. No files are deleted, but the "
            "stored password and face for those folders are discarded.",
            parent=self,
        ):
            return
        for entry in missing:
            folder_manager.forget_folder(Path(entry["path"]), delete_profile=True)
        messagebox.showinfo("Updated", "Missing folders removed from the list.", parent=self)
        self.destroy()

    def _cancel(self):
        self.selected = None
        self.destroy()


class LockedFolderPicker(FolderPicker):
    """Convenience wrapper listing only the folders currently locked."""

    def __init__(self, master):
        super().__init__(
            master,
            folder_manager.list_locked_folders(),
            title="Locked folders",
            action_label="Unlock Selected",
            allow_browse=True,
            empty_message="(no folders are currently locked)",
        )


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(config.APP_NAME)
        self.resizable(False, False)
        config.ensure_dirs()

        self.status_var = tk.StringVar(value="Ready.")

        header = tk.Label(self, text="Folder Lock", font=("Segoe UI", 18, "bold"), pady=16)
        header.pack()

        btn_frame = tk.Frame(self, padx=24, pady=8)
        btn_frame.pack()

        buttons = [
            ("Lock a Folder", self._on_lock_folder),
            ("Unlock a Folder", self._on_unlock_folder),
            ("Change a Folder's Password", self._on_change_password),
            ("Re-enroll a Folder's Face", self._on_enroll_face),
            ("Security Settings", self._on_security_settings),
            ("Exit", self.destroy),
        ]
        for text, cmd in buttons:
            tk.Button(btn_frame, text=text, width=30, command=cmd).pack(pady=4)

        tk.Label(
            self,
            text="Every folder has its own password and its own enrolled face.",
            fg="#555555", pady=(6),
        ).pack()

        status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief="sunken", anchor="w", padx=8)
        status_bar.pack(fill="x", side="bottom")

    # -- state / status helpers -------------------------------------------------

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _pick_known_folder(self, title: str, action_label: str) -> Optional[Path]:
        """Choose among folders that already have their own credentials."""
        entries = [e for e in folder_manager.list_known_folders() if e.get("profile_id")]
        if not entries:
            messagebox.showinfo(
                "No protected folders",
                "No folder has been set up yet. Use 'Lock a Folder' to protect one.",
                parent=self,
            )
            return None
        picker = FolderPicker(self, entries, title=title, action_label=action_label)
        self.wait_window(picker)
        return picker.selected

    def _authenticate_for(self, folder_path: Path, title: str) -> Optional[bytearray]:
        """Runs the mandatory face-then-password check against THIS folder's
        own credentials. Returns that folder's master key, or None if denied."""
        profile_id = folder_manager.profile_id_for(folder_path)
        if not profile_id or not folder_manager.has_credentials(folder_path):
            messagebox.showerror(
                "No credentials",
                "This app has no stored credentials for that folder, so it "
                "cannot be unlocked here.",
                parent=self,
            )
            return None
        dialog = AuthDialog(self, profile_id, mode="full", title=title)
        self.wait_window(dialog)
        if not dialog.result:
            self._set_status(Status.ACCESS_DENIED)
            return None
        return dialog.result

    # -- menu actions -------------------------------------------------------------

    def _on_lock_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select a folder to lock")
        if not folder:
            return
        folder_path = Path(folder)
        if folder_manager.is_locked(folder_path):
            messagebox.showerror("Cannot lock", "This folder is already locked.", parent=self)
            return

        if folder_manager.has_credentials(folder_path):
            # This folder has been protected before: prove ownership with its
            # own face and password rather than silently re-protecting it.
            master_key = self._authenticate_for(
                folder_path, f"Authenticate to Lock '{folder_path.name}'"
            )
            if not master_key:
                return
            profile_id = folder_manager.profile_id_for(folder_path)
        else:
            profile_id = folder_manager.new_profile_id()
            wizard = FolderCredentialsWizard(self, profile_id, folder_path)
            self.wait_window(wizard)
            if not wizard.success or wizard.master_key is None:
                self._set_status("Setup cancelled - folder was not locked.")
                return
            master_key = wizard.master_key
            folder_manager.assign_profile(folder_path, profile_id)

        def verify_restriction() -> None:
            """Confirm the folder really is closed off, rather than assuming
            it. If encryption succeeded but access restriction silently did
            not apply, the user must be told plainly - otherwise they would
            believe the folder is inaccessible when it is merely encrypted."""
            settings = config.get_settings()
            if not settings.get("restrict_folder_access", True):
                return
            if not access_control.is_available():
                messagebox.showwarning(
                    "Encrypted, but access not restricted",
                    "The folder's contents are encrypted, but blocking the folder "
                    "from opening is only supported on Windows (NTFS).",
                    parent=self,
                )
                return
            if not access_control.is_access_denied(folder_path):
                messagebox.showwarning(
                    "Encrypted, but access not restricted",
                    "The folder's contents are encrypted and unreadable, but Windows "
                    "did not apply the access restriction - so the folder can still "
                    "be opened.\n\nThis usually means the drive is not NTFS-formatted "
                    "(for example a FAT32/exFAT USB drive).",
                    parent=self,
                )

        self._run_folder_task(
            folder_manager.lock_folder,
            folder_path,
            master_key,
            profile_id,
            success_status=Status.ENCRYPTION_COMPLETED,
            failure_status=Status.ENCRYPTION_FAILED,
            sensitive_key=master_key,
            on_success=verify_restriction,
        )

    def _on_unlock_folder(self) -> None:
        picker = LockedFolderPicker(self)
        self.wait_window(picker)
        folder_path = picker.selected
        if not folder_path:
            return
        if not folder_manager.is_locked(folder_path):
            messagebox.showerror("Not a locked folder", "This folder is not locked.", parent=self)
            return

        master_key = self._authenticate_for(
            folder_path, f"Authenticate to Unlock '{folder_path.name}'"
        )
        if not master_key:
            return

        self._run_folder_task(
            folder_manager.unlock_folder,
            folder_path,
            master_key,
            success_status=Status.FOLDER_UNLOCKED,
            failure_status=Status.DECRYPTION_FAILED,
            sensitive_key=master_key,
        )

    def _on_enroll_face(self) -> None:
        folder_path = self._pick_known_folder(
            "Re-enroll Face for a Folder", "Re-enroll Face"
        )
        if not folder_path:
            return
        if not messagebox.askyesno(
            "Re-enroll face",
            f"Changing the face for '{folder_path.name}' requires verifying its "
            "CURRENT face and password first.\n\nOther folders are unaffected. Continue?",
            parent=self,
        ):
            return
        master_key = self._authenticate_for(
            folder_path, f"Authenticate to Re-enroll Face for '{folder_path.name}'"
        )
        if not master_key:
            return
        security.best_effort_zero(master_key)

        profile_id = folder_manager.profile_id_for(folder_path)
        dlg = EnrollmentDialog(self, profile_id, title=f"Re-enroll Face - {folder_path.name}")
        self.wait_window(dlg)
        self._set_status(
            f"Face re-enrolled for '{folder_path.name}'." if dlg.success else "Re-enrollment cancelled."
        )

    def _on_change_password(self) -> None:
        folder_path = self._pick_known_folder(
            "Change Password for a Folder", "Change Password"
        )
        if not folder_path:
            return
        master_key = self._authenticate_for(
            folder_path, f"Authenticate to Change Password for '{folder_path.name}'"
        )
        if not master_key:
            return

        try:
            dlg = NewPasswordDialog(self)
            self.wait_window(dlg)
            if not dlg.new_password:
                self._set_status("Password change cancelled.")
                return
            profile_id = folder_manager.profile_id_for(folder_path)
            password_auth.create_password_vault(profile_id, dlg.new_password, master_key)
            messagebox.showinfo(
                "Success",
                f"Password changed for '{folder_path.name}'.\n\nOther folders keep their own passwords.",
                parent=self,
            )
            self._set_status(f"Password changed for '{folder_path.name}'.")
        except Exception as exc:
            messagebox.showerror("Error", _safe_error_text(exc), parent=self)
        finally:
            security.best_effort_zero(master_key)

    def _on_security_settings(self) -> None:
        SecuritySettingsDialog(self)

    # -- generic background folder task runner -------------------------------------------------

    def _run_folder_task(
        self, fn, *args, success_status: str, failure_status: str,
        sensitive_key: Optional[bytearray] = None, on_success=None,
    ) -> None:
        progress_win = tk.Toplevel(self)
        progress_win.title("Please wait")
        progress_win.resizable(False, False)
        progress_win.transient(self)
        progress_win.grab_set()
        # Encryption/decryption is running on disk in the background; closing
        # this window would only hide progress, not stop the operation, and
        # would leave the user with no way to see the final result. Disable
        # the close button for the duration instead of allowing a confusing
        # half-cancelled state.
        progress_win.protocol("WM_DELETE_WINDOW", lambda: None)

        label = tk.Label(progress_win, text="Starting...", width=60, anchor="w", padx=12, pady=12)
        label.pack()
        pbar = ttk.Progressbar(progress_win, mode="indeterminate", length=360)
        pbar.pack(padx=12, pady=(0, 12))
        pbar.start(15)

        q: "queue.Queue" = queue.Queue()

        def worker() -> None:
            try:
                fn(*args, progress_cb=lambda m: q.put(("status", m)))
                q.put(("done", None))
            except Exception as exc:  # surfaced below, not swallowed
                q.put(("error", exc))
            finally:
                # Only safe to wipe the key here: this runs after fn() has
                # fully returned (success or failure), so nothing is still
                # using it. Zeroing it any earlier — e.g. right after
                # starting this thread — would race with the encryption/
                # decryption still in progress.
                if sensitive_key is not None:
                    security.best_effort_zero(sensitive_key)

        threading.Thread(target=worker, daemon=True).start()

        def poll() -> None:
            if not progress_win.winfo_exists():
                return
            try:
                while True:
                    kind, payload = q.get_nowait()
                    if kind == "status":
                        label.config(text=payload)
                    elif kind == "done":
                        pbar.stop()
                        progress_win.destroy()
                        self._set_status(success_status)
                        messagebox.showinfo("Success", success_status, parent=self)
                        if on_success is not None:
                            on_success()
                        return
                    elif kind == "error":
                        pbar.stop()
                        progress_win.destroy()
                        self._set_status(failure_status)
                        messagebox.showerror(failure_status, _safe_error_text(payload), parent=self)
                        return
            except queue.Empty:
                pass
            progress_win.after(60, poll)

        progress_win.after(60, poll)
