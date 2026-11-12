"""Polite document fetcher with a content-addressed cache.

Each document is downloaded once, hashed (sha256) and reused by every project it supports.
Identification: a plain Investedia client name; for sec.gov the approved contact is read from
.local/sec-contact.env (SEC fair-access policy: identify yourself, at most 10 requests per second).
No blocked site is retried with a different identity.
"""
import hashlib, json, re, subprocess, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CACHE = ROOT / 'data/projects/raw/invest/docs'
_last = {}


def _agent(host):
    if host.endswith('sec.gov'):
        env = ROOT / '.local/sec-contact.env'
        contact = dict(l.split('=', 1) for l in env.read_text().split() if '=' in l).get('SEC_CONTACT') if env.exists() else None
        if not contact:
            raise RuntimeError('SEC contact not configured in .local/sec-contact.env')
        return 'Investedia research ' + contact
    return 'Investedia-research/1.0'


def fetch(url, min_interval=None):
    """Return (path, sha256, meta). Raises on HTTP errors (403/404 are recorded by the caller, not bypassed)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    meta_path = CACHE / (key + '.json')
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        return CACHE / meta['file'], meta['sha256'], meta
    host = re.sub(r'^https?://([^/]+).*$', r'\1', url)
    gap = min_interval if min_interval is not None else (0.15 if host.endswith('sec.gov') else 1.0)
    wait = _last.get(host, 0) + gap - time.time()
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={'User-Agent': _agent(host)})
    with urllib.request.urlopen(req, timeout=120) as r:
        body, ctype = r.read(), r.headers.get('Content-Type', '')
    _last[host] = time.time()
    sha = hashlib.sha256(body).hexdigest()
    ext = '.pdf' if body[:4] == b'%PDF' else '.json' if 'json' in ctype else '.html'
    (CACHE / (sha + ext)).write_bytes(body)
    meta = {'url': url, 'file': sha + ext, 'sha256': sha, 'content_type': ctype, 'bytes': len(body), 'fetched_at': time.strftime('%Y-%m-%d')}
    meta_path.write_text(json.dumps(meta))
    return CACHE / meta['file'], sha, meta


def text_of(path):
    """Plain text with layout preserved (PDF via pdftotext -layout; HTML stripped)."""
    path = Path(path)
    if path.suffix == '.pdf':
        return subprocess.run(['pdftotext', '-layout', str(path), '-'], capture_output=True, text=True, check=True).stdout
    raw = path.read_text(encoding='utf-8', errors='ignore')
    raw = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', raw)
    raw = re.sub(r'(?i)<br\s*/?>|</(p|div|li|tr|h\d)>', '\n', raw)
    raw = re.sub(r'<[^>]+>', ' ', raw)
    import html
    return '\n'.join(re.sub(r'[ \t]+', ' ', html.unescape(l)).strip() for l in raw.split('\n') if l.strip())
