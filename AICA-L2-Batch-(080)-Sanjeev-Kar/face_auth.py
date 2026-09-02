"""
face_auth.py
-------------
Face enrollment and verification built entirely on OpenCV (`opencv-contrib-
python`): Haar cascade classifiers for face/eye detection and the LBPH
(Local Binary Patterns Histograms) face recognizer for matching. Both are
long-established, published, reputable algorithms bundled with OpenCV
itself — not a custom/home-grown recognition algorithm.

Why OpenCV/LBPH instead of a deep-learning embedding model (e.g. dlib's
ResNet face encoder): dlib's prebuilt Windows binaries require AVX CPU
instructions. On hardware without AVX (common on low-power/older laptops),
dlib fails to load at all. LBPH is a classical, CPU-only algorithm with no
such requirement, at the cost of somewhat lower accuracy than a modern deep
embedding model under difficult lighting/pose. This is a deliberate,
disclosed trade-off for broad hardware compatibility, not an attempt to
claim equivalent recognition accuracy.

Important security notes (also surfaced in the GUI and README):

* The face template is used ONLY as an authentication gate. It is never
  used as, or to derive, the AES encryption key (see security.py /
  password_auth.py — the key comes from Argon2id over the password).
* Face template confidentiality at rest relies on a locally stored
  "device key" (security.get_or_create_device_key), NOT on the password.
  This is a deliberate trade-off: the workflow requires face verification
  to happen *before* the password is entered, so the template cannot be
  encrypted with a password-derived key. A local attacker with full
  filesystem access to this machine could therefore access both the
  encrypted template and its key. Treat face recognition here as a
  convenience/second-channel factor, not a secret on par with the
  password.
* Liveness detection here is a coarse best-effort blink check: it watches
  for the Haar eye cascade briefly failing to detect both eyes (which
  commonly happens during a natural blink) and then detecting them again.
  This is cruder than a landmark-based eye-aspect-ratio check and is NOT
  robust against a printed photo cut-out, a video replay, or a mask. It
  raises the bar against the most trivial spoof (a single static photo)
  and nothing more.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import numpy as np

import config
import security
from security import SecurityError

try:
    import cv2
except ImportError as exc:  # pragma: no cover
    cv2 = None
    _cv2_import_error = exc


class CameraError(SecurityError):
    """Webcam could not be opened or a frame could not be read."""


class FaceNotEnrolledError(SecurityError):
    """No face template has been enrolled yet."""


class DependencyMissingError(SecurityError):
    """A required third-party library (opencv-contrib-python) is not
    installed, or was installed without the contrib `cv2.face` module."""


def _base_dir() -> Path:
    """Directory to resolve bundled resource files against. When frozen by
    PyInstaller (--onefile or --onedir), sys._MEIPASS points at the
    extracted/bundled support-file directory; otherwise it's the directory
    containing this source file."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


RESOURCES_DIR = _base_dir() / "resources"
FRONTAL_FACE_CASCADE_PATH = RESOURCES_DIR / "haarcascade_frontalface_default.xml"
EYE_CASCADE_PATH = RESOURCES_DIR / "haarcascade_eye.xml"

FACE_SIZE = (200, 200)        # normalized size every face sample is resized to
MIN_FACE_BOX_PX = 90          # minimum face bounding-box side, for sample quality
SAMPLE_SPACING_SECONDS = 0.8  # minimum time between accepted enrollment samples
EYE_HISTORY_WINDOW = 10        # frames of eye-visibility history kept for blink detection


def _require_dependencies() -> None:
    if cv2 is None:
        raise DependencyMissingError(
            "opencv-contrib-python is not installed. Run: pip install opencv-contrib-python"
        ) from _cv2_import_error
    if not hasattr(cv2, "face") or not hasattr(cv2.face, "LBPHFaceRecognizer_create"):
        raise DependencyMissingError(
            "The installed OpenCV build is missing the 'face' (contrib) module. "
            "Install the contrib build: pip uninstall opencv-python -y && "
            "pip install opencv-contrib-python"
        )


StatusCB = Optional[Callable[[str], None]]
FrameCB = Optional[Callable[[np.ndarray], None]]
CancelCB = Optional[Callable[[], bool]]


class FaceCamera:
    """Thin, error-checked wrapper around cv2.VideoCapture."""

    def __init__(self, camera_index: int = 0):
        _require_dependencies()
        self.camera_index = camera_index
        self.cap = None

    def __enter__(self) -> "FaceCamera":
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(self.camera_index, backend)
        if self.cap is None or not self.cap.isOpened():
            raise CameraError(
                "Could not open the webcam. Make sure a camera is connected, "
                "not already in use by another application, and that this "
                "app has camera permission."
            )
        return self

    def read_frame(self, timeout: float = 5.0):
        if self.cap is None:
            raise CameraError("Camera is not open.")
        start = time.time()
        while time.time() - start < timeout:
            ok, frame = self.cap.read()
            if ok and frame is not None:
                return frame
        raise CameraError("Timed out waiting for a frame from the webcam.")

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None


class _Detector:
    """Loads the bundled Haar cascades once and exposes face/eye detection
    helpers used by both enrollment and verification."""

    def __init__(self):
        _require_dependencies()
        self.face_cascade = cv2.CascadeClassifier(str(FRONTAL_FACE_CASCADE_PATH))
        if self.face_cascade.empty():
            raise DependencyMissingError(
                f"Could not load face detection data from {FRONTAL_FACE_CASCADE_PATH}."
            )
        self.eye_cascade = cv2.CascadeClassifier(str(EYE_CASCADE_PATH))
        if self.eye_cascade.empty():
            raise DependencyMissingError(
                f"Could not load eye detection data from {EYE_CASCADE_PATH}."
            )

    def detect_single_face(self, gray_frame: np.ndarray) -> Tuple[Optional[Tuple[int, int, int, int]], str]:
        """Returns ((x, y, w, h), "") on exactly one sufficiently large face,
        or (None, reason) otherwise."""
        faces = self.face_cascade.detectMultiScale(
            gray_frame, scaleFactor=1.1, minNeighbors=6, minSize=(MIN_FACE_BOX_PX, MIN_FACE_BOX_PX)
        )
        if len(faces) == 0:
            return None, "No face detected. Please look at the camera."
        if len(faces) > 1:
            return None, "Multiple faces detected. Only one person may be in frame."
        return tuple(faces[0]), ""

    def eyes_visible(self, gray_face_roi: np.ndarray) -> bool:
        eyes = self.eye_cascade.detectMultiScale(
            gray_face_roi, scaleFactor=1.1, minNeighbors=8, minSize=(18, 18)
        )
        return len(eyes) >= 2


def _preprocess_face(gray_frame: np.ndarray, box: Tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = box
    roi = gray_frame[y : y + h, x : x + w]
    roi = cv2.resize(roi, FACE_SIZE, interpolation=cv2.INTER_AREA)
    roi = cv2.equalizeHist(roi)  # standard LBPH preprocessing to reduce lighting sensitivity
    return roi


class FaceAuthenticator:
    """Face enrollment/verification for ONE folder's credential profile.
    Each protected folder has its own independently enrolled face, stored
    under its own profile directory — the face that opens one folder has
    no bearing on any other folder."""

    def __init__(self, profile_id: str, settings: Optional[dict] = None):
        self.profile_id = profile_id
        self.settings = settings or config.get_settings()

    @property
    def template_path(self) -> Path:
        return config.profile_face_template(self.profile_id)

    # -- template persistence -------------------------------------------------

    def is_enrolled(self) -> bool:
        return self.template_path.exists()

    def _load_recognizer(self):
        _require_dependencies()
        if not self.is_enrolled():
            raise FaceNotEnrolledError("No face has been enrolled for this folder yet.")
        device_key = security.get_or_create_device_key(config.DEVICE_KEY_FILE)
        raw = self.template_path.read_bytes()
        if len(raw) < security.NONCE_SIZE:
            raise security.CorruptedFileError("Face template file is corrupted.")
        nonce, ciphertext = raw[: security.NONCE_SIZE], raw[security.NONCE_SIZE :]
        model_bytes = security.aes_gcm_decrypt(
            device_key, nonce, ciphertext, aad=b"folderlock-face-template-v2"
        )

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        with tempfile.TemporaryDirectory(prefix="flock_face_") as tmp:
            tmp_path = Path(tmp) / "model.xml"
            tmp_path.write_bytes(model_bytes)
            recognizer.read(str(tmp_path))
        return recognizer

    def _save_recognizer(self, recognizer) -> None:
        with tempfile.TemporaryDirectory(prefix="flock_face_") as tmp:
            tmp_path = Path(tmp) / "model.xml"
            recognizer.write(str(tmp_path))
            model_bytes = tmp_path.read_bytes()

        device_key = security.get_or_create_device_key(config.DEVICE_KEY_FILE)
        nonce = security.random_bytes(security.NONCE_SIZE)
        ciphertext = security.aes_gcm_encrypt(
            device_key, nonce, model_bytes, aad=b"folderlock-face-template-v2"
        )
        self.template_path.parent.mkdir(parents=True, exist_ok=True)
        self.template_path.write_bytes(nonce + ciphertext)
        try:
            os.chmod(self.template_path, 0o600)
        except OSError:
            pass

    # -- enrollment -------------------------------------------------------------

    def enroll(
        self,
        camera_index: int = 0,
        num_samples: Optional[int] = None,
        on_status: StatusCB = None,
        on_frame: FrameCB = None,
        should_cancel: CancelCB = None,
    ) -> None:
        """Capture `num_samples` distinct, single-face frames and train a
        fresh LBPH model on them as the authorized face template (overwrites
        any existing template — callers are responsible for enforcing the
        re-enrollment authorization rule *before* calling this)."""
        _require_dependencies()
        detector = _Detector()
        num_samples = num_samples or int(self.settings["face_min_samples"])
        collected: List[np.ndarray] = []
        last_capture_time = 0.0

        def status(msg: str) -> None:
            if on_status:
                on_status(msg)

        status("Starting camera...")
        with FaceCamera(camera_index) as cam:
            while len(collected) < num_samples:
                if should_cancel and should_cancel():
                    raise SecurityError("Enrollment cancelled by user.")
                frame = cam.read_frame()
                if on_frame:
                    on_frame(frame)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                box, reason = detector.detect_single_face(gray)

                if box is None:
                    status(reason)
                    continue

                now = time.time()
                if now - last_capture_time < SAMPLE_SPACING_SECONDS:
                    continue

                collected.append(_preprocess_face(gray, box))
                last_capture_time = now
                status(f"Captured sample {len(collected)}/{num_samples}.")

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(collected, np.array([0] * len(collected)))
        self._save_recognizer(recognizer)
        status("Face enrolled successfully. This face now unlocks this folder.")

    # -- verification -------------------------------------------------------------

    def verify(
        self,
        camera_index: int = 0,
        on_status: StatusCB = None,
        on_frame: FrameCB = None,
        should_cancel: CancelCB = None,
    ) -> bool:
        """Returns True only if the enrolled face is matched AND (when
        liveness checking is enabled) a natural blink was observed within
        the verification window."""
        _require_dependencies()
        detector = _Detector()
        recognizer = self._load_recognizer()
        threshold = float(self.settings["face_match_threshold"])
        timeout = float(self.settings["face_verify_timeout_seconds"])
        liveness_enabled = bool(self.settings["liveness_check_enabled"])

        def status(msg: str) -> None:
            if on_status:
                on_status(msg)

        eye_history: List[bool] = []
        blink_detected = False
        matched = False
        start = time.time()

        status("Starting camera...")
        with FaceCamera(camera_index) as cam:
            status("Searching for authorized face...")
            while time.time() - start < timeout:
                if should_cancel and should_cancel():
                    status("Verification cancelled.")
                    return False
                frame = cam.read_frame()
                if on_frame:
                    on_frame(frame)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                box, _reason = detector.detect_single_face(gray)

                if box is None:
                    continue

                face_roi = _preprocess_face(gray, box)
                label, confidence = recognizer.predict(face_roi)
                matched = (label == 0) and (confidence <= threshold)

                if liveness_enabled:
                    x, y, w, h = box
                    eyes_visible = detector.eyes_visible(gray[y : y + h, x : x + w])
                    eye_history.append(eyes_visible)
                    eye_history[:] = eye_history[-EYE_HISTORY_WINDOW:]
                    if len(eye_history) >= 3:
                        for i, was_open in enumerate(eye_history):
                            if not was_open and any(eye_history[:i]) and any(eye_history[i + 1 :]):
                                blink_detected = True
                                break

                if matched:
                    if not liveness_enabled:
                        status("Face recognized")
                        return True
                    if blink_detected:
                        status("Face recognized (liveness confirmed)")
                        return True
                    status("Face recognized — please blink naturally to confirm liveness...")
                else:
                    status("Face not recognized")

        if matched and liveness_enabled and not blink_detected:
            status("Liveness could not be confirmed (no blink detected). Access denied.")
        else:
            status("Face not recognized. Access denied.")
        return False


def enrolled_profile_ids() -> List[str]:
    """Profile ids that currently have a face template on disk."""
    profiles = config.profiles_dir()
    if not profiles.exists():
        return []
    return [
        d.name for d in sorted(profiles.iterdir())
        if d.is_dir() and config.profile_face_template(d.name).exists()
    ]


def rotate_device_key_all_profiles() -> int:
    """Re-encrypts EVERY profile's face template under a freshly generated
    device key, and returns how many were re-encrypted.

    All templates share one device key, so this must load them all with the
    old key *before* replacing it, then write them all back with the new
    one. Rotating a single profile in isolation would silently render every
    other folder's enrolled face undecryptable.

    This only changes the at-rest storage key. It does not change any
    enrolled face and makes no authentication decision, so it does not
    require face/password verification. See the module docstring for why
    the device key cannot be password-derived.
    """
    _require_dependencies()
    ids = enrolled_profile_ids()
    loaded = [(pid, FaceAuthenticator(pid)._load_recognizer()) for pid in ids]

    if config.DEVICE_KEY_FILE.exists():
        config.DEVICE_KEY_FILE.unlink()

    for pid, recognizer in loaded:
        FaceAuthenticator(pid)._save_recognizer(recognizer)
    return len(loaded)
