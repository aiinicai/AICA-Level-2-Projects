"""SurakshaScan v1 scanner (reconstructed from bytecode)."""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def scan_page(url):
    result = {
        "url": url,
        "status_code": None,
        "reachable": False,
        "policy_links": [],
        "cookie_wording_found": False,
        "forms": [],
        "trackers": [],
    }
    try:
        resp = requests.get(url, timeout=10, headers=HEADERS)
        result["status_code"] = resp.status_code
        if resp.status_code != 200:
            return result
        result["reachable"] = True
        soup = BeautifulSoup(resp.text, "html.parser")

        keywords = ("privacy", "policy", "data protection", "terms")
        for a in soup.find_all("a", href=True):
            text = a.get_text().lower()
            if any(k in text for k in keywords):
                result["policy_links"].append(urljoin(url, a["href"]))

        cookie_words = ("cookie", "consent", "we use cookies", "accept cookies")
        page_text = soup.get_text().lower()
        if any(w in page_text for w in cookie_words):
            result["cookie_wording_found"] = True

        for form in soup.find_all("form"):
            fields = []
            for inp in form.find_all(["input", "textarea"]):
                fields.append({
                    "name": inp.get("name", "(unnamed field)"),
                    "type": inp.get("type", "text"),
                })
            result["forms"].append({
                "action": form.get("action", "(no action specified)"),
                "fields": fields,
            })

        tracker_patterns = (
            "google-analytics", "gtag", "googletagmanager", "facebook.net",
            "fbevents", "pixel", "hotjar", "doubleclick", "adservice",
        )
        for script in soup.find_all("script", src=True):
            src = script["src"]
            if any(p in src for p in tracker_patterns):
                result["trackers"].append(src)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def check_common_policy_paths(base_url):
    paths = ("/privacy-policy", "/privacy", "/privacy-policy/",
             "/data-protection-policy", "/terms-and-conditions")
    found = []
    for path in paths:
        url = base_url.rstrip("/") + path
        try:
            resp = requests.get(url, timeout=8, headers=HEADERS)
            if resp.status_code == 200:
                found.append(url)
        except Exception:
            pass
    return found


def scan_institution(base_url, extra_pages=None):
    data = {"base_url": base_url, "pages": [], "policy_paths_found": []}
    data["pages"].append(scan_page(base_url))
    for page in (extra_pages or []):
        data["pages"].append(scan_page(page))
    data["policy_paths_found"] = check_common_policy_paths(base_url)
    return data
