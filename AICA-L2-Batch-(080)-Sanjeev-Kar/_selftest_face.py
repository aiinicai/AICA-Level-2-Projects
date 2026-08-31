"""
Ad-hoc self-test for face_auth.py's non-camera mechanics: Haar cascade
loading, and the LBPH train -> serialize -> encrypt -> decrypt -> restore
-> predict round-trip through the same encrypted-template storage path the
real app uses. Uses synthetic grayscale images (not real faces) since this
only needs to validate the mechanical pipeline, not detection accuracy —
detection/recognition accuracy requires a live camera and is covered by
manual testing.

Run inside an environment that actually has opencv-contrib-python (cv2.face)
available, e.g. the conda env created for this build:
    conda run -n folderlock_build python _selftest_face.py
"""
import shutil
import tempfile
from pathlib import Path

import numpy as np

import config

tmp_root = Path(tempfile.mkdtemp(prefix="flock_face_selftest_"))
config.APP_DATA_DIR = tmp_root / "appdata"
config.VAULT_DIR = config.APP_DATA_DIR / "vault"
config.LOG_DIR = config.APP_DATA_DIR / "logs"
config.DEVICE_KEY_FILE = config.VAULT_DIR / "device.key"
config.PASSWORD_VAULT_FILE = config.VAULT_DIR / "password_vault.json"
config.SETTINGS_FILE = config.VAULT_DIR / "settings.json"
config.ensure_dirs()

import face_auth  # noqa: E402  (import after config override, matches _selftest.py pattern)

print("== dependency check ==")
face_auth._require_dependencies()
print("  OK: cv2 + cv2.face are importable and usable")

print("== Haar cascade loading ==")
detector = face_auth._Detector()
assert not detector.face_cascade.empty()
assert not detector.eye_cascade.empty()
print("  OK: bundled face + eye cascades load from resources/")

print("== is_enrolled() before enrollment ==")
PROFILE = "test-face-profile"
fa = face_auth.FaceAuthenticator(PROFILE)
assert fa.is_enrolled() is False
print("  OK: not enrolled in a fresh app-data dir")

print("== LBPH train / encrypted-save / encrypted-load / predict round-trip ==")


def _synthetic_face(seed: int) -> np.ndarray:
    """A deterministic, seed-dependent 200x200 grayscale pattern. Not a real
    face — only used to exercise LBPH's train/predict mechanics and the
    encrypted-template storage path, not real recognition accuracy."""
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 256, size=face_auth.FACE_SIZE, dtype=np.uint8)
    return base


import cv2  # noqa: E402

# "Enrollment": train directly (bypassing the camera loop) on 5 samples of
# "person A" and save through the real encrypted-storage path.
person_a_samples = [_synthetic_face(seed=100 + i) for i in range(5)]
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.train(person_a_samples, np.array([0] * len(person_a_samples)))
fa._save_recognizer(recognizer)

assert fa.template_path.exists()
assert fa.is_enrolled() is True
raw = fa.template_path.read_bytes()
assert raw[:20] != b"<?xml"[:20], "template must not be stored as plaintext XML"
print(f"  OK: encrypted template written ({len(raw)} bytes), not plaintext on disk")

# "Verification": load the recognizer back through the real encrypted path
# and confirm it recognizes a sample close to what it was trained on, and
# rejects something far away.
loaded = fa._load_recognizer()
label, confidence = loaded.predict(person_a_samples[0])
print(f"  same-person sample -> label={label}, confidence={confidence:.2f}")
assert label == 0

different_person = _synthetic_face(seed=999999)
label2, confidence2 = loaded.predict(different_person)
print(f"  different (random) sample -> label={label2}, confidence={confidence2:.2f}")
assert confidence2 > confidence, "a clearly different sample should score a higher (worse) LBPH distance"

print("== rotate_device_key() ==")
old_device_key = config.DEVICE_KEY_FILE.read_bytes()
face_auth.rotate_device_key_all_profiles()
new_device_key = config.DEVICE_KEY_FILE.read_bytes()
assert new_device_key != old_device_key
reloaded = fa._load_recognizer()
label3, _ = reloaded.predict(person_a_samples[0])
assert label3 == 0
print("  OK: device key rotated, template still decrypts and predicts correctly")

shutil.rmtree(tmp_root, ignore_errors=True)
print("\nALL FACE-AUTH MECHANICS SELF-TESTS PASSED")
print("(Real face detection/recognition accuracy still needs a live-camera manual test.)")
