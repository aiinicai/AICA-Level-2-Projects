"""Which browser Start_LookThrough.bat opens: Chrome first, then Edge, then the system default.
Launches nothing; missing installs are simulated with empty program folders."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bridge"))
import lookthrough_bridge as B  # noqa: E402

URL = "http://localhost:8765/"
ok = True


def check(name, cond, detail):
    global ok
    ok &= bool(cond)
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  -> {detail}"))


real = B.browser_command(URL)
chrome_here = any(Path(p).is_file() for p in (Path(os.environ.get(v, "")) / "Google/Chrome/Application/chrome.exe"
                                                for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")))
check("this PC: Chrome chosen when installed" if chrome_here else "this PC: no Chrome, fallback chosen",
      real and (Path(real[0]).stem.lower() == "chrome") == chrome_here and real[1] == URL, real)

saved = {k: os.environ.get(k) for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")}
which = shutil.which
try:
    with tempfile.TemporaryDirectory() as empty:
        edge_dir = Path(empty) / "x86" / "Microsoft/Edge/Application"
        edge_dir.mkdir(parents=True)
        (edge_dir / "msedge.exe").write_bytes(b"")
        os.environ.update({"ProgramFiles": str(Path(empty) / "pf"), "ProgramFiles(x86)": str(Path(empty) / "x86"), "LOCALAPPDATA": str(Path(empty) / "la")})
        shutil.which = lambda name: None
        c = B.browser_command(URL)
        check("no Chrome: Edge chosen", c and Path(c[0]).name == "msedge.exe", c)
        (edge_dir / "msedge.exe").unlink()
        c = B.browser_command(URL)
        check("no Chrome, no Edge: system default (None)", c is None, c)
finally:
    shutil.which = which
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
sys.exit(0 if ok else 1)
