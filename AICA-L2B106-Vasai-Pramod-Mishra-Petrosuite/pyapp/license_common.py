"""
license_common.py - Shared by the client app and the private key generator
(tools/generate_key.py, kept only by the software owner, never shipped in the
client installer). Both must use the SAME licence secret to agree on keys.

The secret is NOT stored in this repository. Production builds: create an
untracked file `license_secret_local.py` next to this file (copy
`license_secret_local.py.example`) containing LICENSE_SECRET. It is listed in
.gitignore and must never be committed or shared.

Public/demo copy: if that file is absent, a DEMO secret is used so the app can
be run and reviewed. Keys generated with the demo secret are NOT secure.
"""
import hashlib
import hmac
import platform

try:
    from license_secret_local import LICENSE_SECRET  # private, not in the repo
except ImportError:
    LICENSE_SECRET = "DEMO-ONLY-SECRET-NOT-FOR-PRODUCTION"


def get_machine_id() -> str:
    """
    Returns a stable per-PC identifier.
    Windows: reads the OS-level MachineGuid (unique per Windows install,
    stable across reboots, changes only on OS reinstall).
    Falls back to platform.node() (hostname) on non-Windows dev machines.
    """
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            )
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            raw = guid
        except Exception:
            raw = platform.node() or "UNKNOWN-MACHINE"
    else:
        raw = platform.node() or "UNKNOWN-MACHINE"

    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    # Present as readable groups, e.g. ABCD-1234-EF56-7890
    return "-".join(digest[i:i + 4] for i in range(0, 16, 4))


def generate_activation_key(machine_id: str) -> str:
    """
    Deterministically derives an activation key from a machine ID using HMAC.
    Same machine ID always yields the same key (given the same secret).
    """
    mac = hmac.new(
        LICENSE_SECRET.encode("utf-8"),
        machine_id.upper().strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()
    return "-".join(mac[i:i + 4] for i in range(0, 20, 4))


def verify_activation_key(machine_id: str, key: str) -> bool:
    expected = generate_activation_key(machine_id)
    provided = (key or "").strip().upper()
    return hmac.compare_digest(expected, provided)
