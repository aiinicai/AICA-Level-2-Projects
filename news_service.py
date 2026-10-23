"""India tax & finance RSS headlines, fetched only on demand in daemon threads.

Feeds give titles and sometimes short excerpts, not full article text. We never invent
summaries or claim a third-party headline is a legal compliance notification.
"""
import datetime as dt
import email.utils
import html
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from .config import USER, load_json, save_json

CACHE_FILE = USER / 'india_news_cache.json'
REFRESH_SECONDS = 15 * 60
MAX_RESPONSE_BYTES = 2_000_000


def google_feed(term):
    q = urllib.parse.urlencode({'q': term + ' when:7d', 'hl': 'en-IN', 'gl': 'IN', 'ceid': 'IN:en'})
    return 'https://news.google.com/rss/search?' + q


# The official XML paths are linked by the publishers on their RSS subscription pages.
FEEDS = [
    ('CBDT Circulars', 'Direct Tax', 'Official',
     'https://www.incometaxindia.gov.in/circular-rss-feed/-/asset_publisher/bxhj/rss'),
    ('CBDT Notifications', 'Direct Tax', 'Official',
     'https://www.incometaxindia.gov.in/notification-rss-feed/-/asset_publisher/bxhj/rss'),
    ('CBDT Press Releases', 'Direct Tax', 'Official',
     'https://www.incometaxindia.gov.in/press-release-rss-feed/-/asset_publisher/bxhj/rss'),
    ('RBI Press Releases', 'RBI & Banking', 'Official', 'https://rbi.org.in/pressreleases_rss.xml'),
    ('RBI Notifications', 'RBI & Banking', 'Official', 'https://rbi.org.in/notifications_rss.xml'),
    ('SEBI Releases', 'Finance & Markets', 'Official', 'https://www.sebi.gov.in/sebirss.xml'),
    ('PIB Finance Releases', 'GST & Indirect Tax', 'Official',
     'https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1'),
    ('Business Standard Finance', 'Finance & Markets', 'News',
     'https://www.business-standard.com/rss/finance-103.rss'),
    ('Business Standard Markets', 'Finance & Markets', 'News',
     'https://www.business-standard.com/rss/markets-106.rss'),
    ('India Direct Tax News', 'Direct Tax', 'News',
     google_feed('India income tax CBDT tax audit ITR due date')), 
    ('India GST News', 'GST & Indirect Tax', 'News',
     google_feed('India GST CBIC GST Council indirect tax')), 
    ('India Finance News', 'Finance & Markets', 'News',
     google_feed('India SEBI stock market finance RBI economy')), 
    ('India Audit News', 'Audit & Corporate', 'News',
     google_feed('India ICAI audit MCA corporate law accounting')), 
]
TOPICS = ['All Topics', 'Direct Tax', 'GST & Indirect Tax', 'RBI & Banking', 'Finance & Markets', 'Audit & Corporate']


class _StripHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.ignored += 1
        elif tag in ('br', 'p', 'li'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.ignored:
            self.ignored -= 1
        elif tag in ('br', 'p', 'li'):
            self.parts.append(' ')

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def clean_text(raw):
    parser = _StripHTML()
    try:
        parser.feed(html.unescape(raw or ''))
    except Exception:
        return re.sub(r'\s+', ' ', html.unescape(raw or '')).strip()
    return re.sub(r'\s+', ' ', ''.join(parser.parts)).strip()


def _child_text(node, names):
    for ch in node:
        if ch.tag.rsplit('}', 1)[-1].lower() in names:
            return (ch.text or '').strip()
    return ''


def _date_to_ts(raw):
    if not raw:
        return 0
    try:
        value = email.utils.parsedate_to_datetime(raw)
    except (ValueError, TypeError, IndexError):
        try:
            value = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return 0
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.timestamp()


def parse_feed(payload, feed_label, topic, kind, limit=25):
    """RSS 2.0 / Atom; only source-provided excerpts are represented as summaries."""
    root = ET.fromstring(payload)
    is_google = 'News' in feed_label and kind == 'News'
    items = []
    for node in root.iter():
        if node.tag.rsplit('}', 1)[-1].lower() not in ('item', 'entry'):
            continue
        title = clean_text(_child_text(node, {'title'}))
        if not title:
            continue
        url = _child_text(node, {'link'})
        if not url:
            for ch in node:
                if ch.tag.rsplit('}', 1)[-1].lower() == 'link':
                    url = ch.attrib.get('href', '')
                    if url:
                        break
        if urllib.parse.urlsplit(url).scheme not in ('https', 'http'):
            continue
        source = _child_text(node, {'source'}) or feed_label
        if kind == 'Official':
            source = feed_label
        elif source == feed_label and ' - ' in title:
            title, source = title.rsplit(' - ', 1)
        if kind == 'News' and source and title.endswith(' - ' + source):
            title = title[:-(len(source) + 3)]
        title = title.strip()[:250]
        excerpt = clean_text(_child_text(node, {'description', 'summary', 'content', 'encoded'}))
        # Google News descriptions often contain multiple linked headlines, not an
        # excerpt from the article. Suppress them rather than mislabel as a summary.
        if is_google:
            excerpt = ''
        if excerpt and (excerpt.lower() == title.lower() or excerpt.lower().startswith(title.lower())):
            excerpt = ''
        excerpt = excerpt[:280].strip()
        date = _date_to_ts(_child_text(node, {'pubdate', 'published', 'updated', 'date'}))
        items.append({'title': title, 'summary': excerpt, 'url': url, 'source': source[:90],
                      'topic': topic, 'kind': kind, 'published': date})
        if len(items) >= limit:
            break
    return items


def fetch_feed(feed):
    label, topic, kind, url = feed
    req = urllib.request.Request(url, headers={'User-Agent': 'BreakBuddyPro/4.0 (desktop RSS reader)',
                                               'Accept': 'application/rss+xml,application/atom+xml,application/xml,text/xml,*/*'})
    with urllib.request.urlopen(req, timeout=7) as resp:
        raw = resp.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError('Feed exceeded size limit')
    items = parse_feed(raw, label, topic, kind, limit=100 if 'PIB' in label else 25)
    if label == 'PIB Finance Releases':
        relevant = re.compile(r'\b(gst|indirect tax|income tax|taxation|finance ministry|central board of|'
                              r'budget|fiscal|banking|reserve bank|sebi|corporate affairs|'
                              r'financial sector|economic affairs)\b', re.I)
        filtered = []
        for item in items:
            body = item['title'] + ' ' + item['summary']
            if not relevant.search(body):
                continue
            if re.search(r'\b(gst|indirect tax|cbic)\b', body, re.I):
                item['topic'] = 'GST & Indirect Tax'
            elif re.search(r'\b(income tax|cbdt|direct tax|tax audit)\b', body, re.I):
                item['topic'] = 'Direct Tax'
            elif re.search(r'\b(banking|reserve bank|rbi)\b', body, re.I):
                item['topic'] = 'RBI & Banking'
            else:
                item['topic'] = 'Finance & Markets'
            filtered.append(item)
        return filtered
    return items


def collect_feeds(stop_event=None, fetcher=fetch_feed):
    """Bounded parallel requests. Daemon workers cannot hold the app open on exit."""
    results = []
    failures = []
    lock = threading.Lock()
    workers = []
    def work(feed):
        try:
            found = fetcher(feed)
            with lock:
                results.extend(found)
                if not found:
                    failures.append(feed[0] + ': no entries')
        except Exception as exc:
            with lock:
                failures.append(feed[0] + ': ' + type(exc).__name__)
    for feed in FEEDS:
        if stop_event and stop_event.is_set():
            break
        worker = threading.Thread(target=work, args=(feed,), daemon=True)
        worker.start()
        workers.append(worker)
    deadline = time.monotonic() + 11
    for worker in workers:
        if stop_event and stop_event.is_set():
            break
        worker.join(max(0, deadline - time.monotonic()))
    if stop_event and stop_event.is_set():
        return [], ['Stopped']
    if any(w.is_alive() for w in workers):
        failures.append('Some sources timed out')
    cutoff = time.time() - 30 * 86400
    unique = {}
    for item in results:
        if item['published'] and item['published'] < cutoff:
            continue
        key = re.sub(r'\W+', '', item['title'].casefold())[:100]
        if not key:
            continue
        old = unique.get(key)
        if old is None or (item['kind'] == 'Official' and old['kind'] != 'Official'):
            unique[key] = item
    ordered = sorted(unique.values(), key=lambda x: (x['published'], x['kind'] == 'Official'), reverse=True)
    return ordered[:160], failures


class IndiaNewsManager:
    def __init__(self):
        saved = load_json(CACHE_FILE, {})
        if not isinstance(saved, dict):
            saved = {}
        raw_items = saved.get('items', []) if isinstance(saved.get('items'), list) else []
        self.items = [item for item in raw_items if isinstance(item, dict) and
                      all(k in item for k in ('title', 'url', 'source', 'topic', 'kind', 'published'))]
        try:
            self.updated = float(saved.get('updated', 0) or 0)
        except (TypeError, ValueError):
            self.updated = 0
        self.attempted = 0
        self.failures = []
        self.loading = False
        self.version = 1
        self.lock = threading.Lock()
        self.stopped = threading.Event()

    def snapshot(self):
        with self.lock:
            return {'items': list(self.items), 'updated': self.updated, 'attempted': self.attempted,
                    'loading': self.loading, 'failures': list(self.failures), 'version': self.version}

    def refresh(self, force=False):
        with self.lock:
            if self.stopped.is_set() or self.loading:
                return False
            if not force and time.time() - max(self.updated, self.attempted) < REFRESH_SECONDS:
                return False
            self.loading = True
            self.attempted = time.time()
            self.failures = []
            self.version += 1
        threading.Thread(target=self._worker, name='BreakBuddyNews', daemon=True).start()
        return True

    def _worker(self):
        data, errors = collect_feeds(self.stopped)
        if self.stopped.is_set():
            return
        now = time.time()
        with self.lock:
            if data:
                self.items = data
                self.updated = now
            self.failures = errors
            self.loading = False
            self.version += 1
            stored = {'updated': self.updated, 'items': list(self.items)}
        if data and not self.stopped.is_set():
            save_json(CACHE_FILE, stored)

    def stop(self):
        self.stopped.set()
