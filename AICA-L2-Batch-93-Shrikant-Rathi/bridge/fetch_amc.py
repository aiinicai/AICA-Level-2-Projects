"""
Download AMC monthly portfolio files into data/amc_portfolios and record provenance.

Usage:  python fetch_amc.py <scheme_id> <yyyy-mm> <url> [<scheme_id> <yyyy-mm> <url> ...]
        python fetch_amc.py --local <file> <scheme_id> <yyyy-mm> <page the user downloaded it from>

--local registers a file the user downloaded by hand (for AMCs whose servers block automated downloads, e.g. behind a
bot-protection check): it must read as that scheme and month, is renamed to the standard <scheme_id>_<yyyy-mm> name,
and the manifest records the page, the original file name and the file's SHA-256.

For AMCs that publish one ZIP of all schemes, pass  <zip-url>::<exact member name>  and only
that member is extracted; the manifest then records the ZIP's hash as well as the file's.

Each download is appended to data/amc_portfolios/_sources.csv with the source URL, the
download time and the file's SHA-256, so every look-through figure can be traced back to
the exact file the AMC published. URLs are supplied by the user or taken from the AMC's
official disclosure page; nothing is scraped.
"""
import csv
import hashlib
import io
import sys
import zipfile
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from common import PORTFOLIO_DIR, log

try:  # verify TLS against the operating system's trust store (some AMC chains are not in Python's bundle)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

UA = {"User-Agent": "LookThrough/3 (AICA capstone; portfolio disclosure download)", "Accept": "*/*"}
MANIFEST = PORTFOLIO_DIR / "_sources.csv"
FIELDS = ["file", "scheme_id", "month", "url", "zip_member", "zip_sha256", "downloaded_at", "bytes", "sha256"]
_ZIPS = {}  # url -> bytes, so one monthly ZIP serves several schemes in the same run


def _get(url):
    if url not in _ZIPS:
        req = urllib.request.Request(url.replace(" ", "%20"), headers=UA)
        with urllib.request.urlopen(req, timeout=180) as r:
            body = r.read()
        if body[:15].lower().startswith((b"<!doctype", b"<html")):
            raise ValueError(f"{url}: server returned a web page, not a file")
        _ZIPS[url] = body
    return _ZIPS[url]


def fetch(scheme_id, month, url):
    url, _, member = url.partition("::")
    body = _get(url)
    zip_sha = ""
    if member:
        if not zipfile.is_zipfile(io.BytesIO(body)):
            raise ValueError(f"{url}: a member was named but the download is not a ZIP")
        zip_sha = hashlib.sha256(body).hexdigest()
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            if member not in z.namelist():
                raise ValueError(f"{member!r} not in ZIP; close names: {[n for n in z.namelist() if member.split()[0] in n][:5]}")
            body = z.read(member)
        ext = Path(member).suffix.lower()
    else:
        ext = Path(urlparse(url).path).suffix.lower() or ".xlsx"
    if ext not in (".xls", ".xlsx", ".xlsm", ".csv"):
        raise ValueError(f"{url}: unexpected file type {ext}")
    name = f"{scheme_id}_{month}{ext}"
    (PORTFOLIO_DIR / name).write_bytes(body)
    row = {"file": name, "scheme_id": scheme_id, "month": month, "url": url, "zip_member": member, "zip_sha256": zip_sha,
           "downloaded_at": datetime.now().isoformat(timespec="seconds"), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    new = not MANIFEST.exists()
    with MANIFEST.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    log.info("Saved %s (%d bytes) from %s", name, len(body), url)
    return name


def register_local(path, scheme_id, month, page):
    """Register a manually downloaded file: parse it first (it must be this scheme and month), then rename and record."""
    import amc_parser
    from common import config
    src = Path(path)
    if not src.is_file():
        raise ValueError(f"{src} not found")
    sc = config("schemes")
    schemes = sc if isinstance(sc, list) else sc.get("schemes", list(sc.values()))
    got = [r for r in amc_parser.parse_file(src, schemes) if r.get("scheme_id") == scheme_id]
    months = sorted({(r.get("portfolio_date") or "")[:7] for r in got})
    if months != [month]:
        raise ValueError(f"{src.name} reads as {scheme_id} for {months or 'no month'}, not {month}; not registered")
    body = src.read_bytes()
    name = f"{scheme_id}_{month}{src.suffix.lower()}"
    dst = PORTFOLIO_DIR / name
    if dst.exists() and dst.resolve() != src.resolve():
        raise ValueError(f"{name} already exists; not overwritten")
    src.rename(dst)
    row = {"file": name, "scheme_id": scheme_id, "month": month, "url": f"manual download by the user from {page} (saved as '{src.name}')",
           "zip_member": "", "zip_sha256": "", "downloaded_at": datetime.fromtimestamp(dst.stat().st_mtime).isoformat(timespec="seconds"),
           "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    with MANIFEST.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDS).writerow(row)
    log.info("Registered %s (was %s, %d bytes, %s)", name, src.name, len(body), got[0].get("portfolio_date"))
    return name


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--local"]:
        if len(args) != 5:
            raise SystemExit(__doc__)
        print("OK  ", register_local(*args[1:]))
        sys.exit(0)
    if not args or len(args) % 3:
        raise SystemExit(__doc__)
    failed = 0
    for i in range(0, len(args), 3):
        try:
            print("OK  ", fetch(*args[i:i + 3]))
        except Exception as e:  # noqa: BLE001 - report every failure, continue with the rest
            failed += 1
            print("FAIL", args[i], args[i + 1], e)
    sys.exit(1 if failed else 0)
