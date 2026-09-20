"""Bounded HTTPS client using Python's standard library and system TLS checks."""
import json
import time
import urllib.request
import urllib.error
from http.cookiejar import CookieJar

# Many sites (Cloudflare and similar) answer a bare "Mozilla/5.0" client with a
# challenge page or an error instead of the real page. HTML pages are therefore
# requested with the headers a real desktop browser sends.
BROWSER_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-IN,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
}


class Response:
    def __init__(self, status, body, headers):
        self.headers = headers
        self.status_code = status
        self.content = body
        self.text = body.decode(headers.get_content_charset() or 'utf-8', errors='replace')
    def json(self):
        return json.loads(self.text)

class Session:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'identity'}
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    def get(self, url, headers=None, timeout=15):
        if not url.startswith('https://'):
            raise ValueError('Only HTTPS source requests are permitted')
        request = urllib.request.Request(url, headers={**self.headers, **(headers or {})})
        try:
            response = self.opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as e:
            response = e
        with response:
            chunks, size, start = [], 0, time.monotonic()
            while True:
                part = response.read(65536)
                if not part: break
                size += len(part)
                if size > 40 * 1024 * 1024 or time.monotonic() - start > timeout:
                    raise RuntimeError('Source response exceeded the size/time limit')
                chunks.append(part)
            return Response(response.code, b''.join(chunks), response.headers)

def get(url, headers=None, timeout=15):
    return Session().get(url, headers, timeout)


def get_page(url, timeout=15):
    """GET an HTML page with browser-like headers (see BROWSER_HEADERS)."""
    return Session().get(url, BROWSER_HEADERS, timeout)
