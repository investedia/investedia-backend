"""Shared, dependency-free building blocks of the news pipeline (no network, no Gemini, no globals).
Used by update_globe_news.py and covered by tests/test_news_core.py.
  - URL canonicalisation, title normalisation and similarity, date parsing (always UTC, never in the future)
  - priority scoring (stored on every article as `score`, never shown raw)
  - duplicate removal that prefers the original / most authoritative source
  - content hashes, so unchanged articles are never sent to Gemini twice
  - atomic, validated JSON writes (a failed or empty feed never replaces the previous one)"""
import hashlib, json, os, re, tempfile, urllib.parse
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

ISO = '%Y-%m-%dT%H:%M:%SZ'
TRACKING = re.compile(r'(utm_|fbclid|gclid|ref$|ref_|cmp|ito$|at_|ocid|taid|mc_|igshid|source$|guccounter)', re.I)

# ---------- time ----------
def parse_time(text, now):
    """RFC 822 or ISO 8601 -> aware UTC datetime. Missing/garbled -> None. A time in the future is clamped to now."""
    text = (text or '').strip()
    if not text: return None
    ts = None
    try: ts = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        try: ts = datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError: return None
    if ts is None: return None
    if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
    ts = ts.astimezone(timezone.utc)
    return min(ts, now)

def iso(ts): return ts.strftime(ISO)
def from_iso(s): return datetime.fromisoformat(s.replace('Z', '+00:00'))
def age_minutes(published, now): return max(0.0, (now - from_iso(published)).total_seconds() / 60)

# ---------- urls and titles ----------
def canon(u):
    """Same article, different address: drop tracking parameters, fragments, www, amp markers and trailing slashes."""
    try:
        p = urllib.parse.urlsplit(u.strip())
        q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if not TRACKING.match(k)]
        path = re.sub(r'/amp/?$', '', p.path.rstrip('/'), flags=re.I)
        return (p.netloc.lower().removeprefix('www.') + path + ('?' + urllib.parse.urlencode(sorted(q)) if q else '')).lower()
    except Exception: return u

STOP = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'has', 'have', 'its', 'new', 'says', 'said', 'after', 'over', 'into', 'will', 'amid'}
def norm(t): return {w for w in re.sub(r'[^a-z0-9 ]', ' ', (t or '').lower()).split() if len(w) > 2 and w not in STOP}
def jaccard(a, b): return len(a & b) / max(1, len(a | b))
def entities(t):
    """Capitalised words and numbers: the parts of a headline that identify the event."""
    return {w.lower() for w in re.findall(r'\b(?:[A-Z][A-Za-z]{2,}|\d[\d.,]*%?)\b', t or '')} - STOP

def same_event(a, b, hours_apart):
    """Title similarity, widened by shared entities, and only for articles close in time."""
    wa, wb = norm(a), norm(b)
    if len(wa) < 3 or len(wb) < 3: return False
    j = jaccard(wa, wb)
    if j > .55: return True
    if hours_apart <= 12:
        ea, eb = entities(a), entities(b)
        shared = len(ea & eb)
        has_num = any(w[0].isdigit() for w in ea & eb)
        if (shared >= 3 and jaccard(ea, eb) >= .5 and j > .3) or (shared >= 2 and has_num and j > .3): return True
        if j > .4 and len(wa & wb) / max(1, min(len(wa), len(wb))) >= .8: return True  # one headline contains the other
    return False

def content_hash(c):
    return hashlib.sha1(f"{c.get('title','')}|{(c.get('desc') or '')[:400]}".encode('utf-8')).hexdigest()[:16]

# ---------- scoring ----------
AUTHORITY = {'official': 1.0, 'wire': .85, 'publisher': .7, 'aggregator': .45, 'gdelt': .4}
MACRO = re.compile(r'\b(rate (?:decision|cut|hike)|interest rates?|policy rate|repo rate|inflation|cpi|ppi|gdp|payrolls?|unemployment|fomc|ecb|boj|rbi|rba|rbnz|sarb|banxico|selic|central bank|monetary policy|tariffs?|trade (?:deal|war)|opec|sanctions?|recession|treasury|yields?|stimulus|debt ceiling'
                   r'|tasa de inter[eé]s|inflaci[oó]n|infla[cç][aã]o|juros|banco central|banque centrale|taux directeur|faiz|enflasyon|merkez bankas[ıi]|inflacja|stopy procentowe|r[äa]nta|rente|styringsrente|pib|bip)\b', re.I)
SEVERE = re.compile(r'\b(crash|plunge[sd]?|surge[sd]?|soar[sd]?|tumble[sd]?|collapse[sd]?|default|bankrupt\w*|emergency|halt(?:ed|s)?|downgrade[sd]?|record (?:high|low)|shock|crisis|bank run|outage|attack|invasion|ceasefire)\b', re.I)
EXPOSURE = re.compile(r'\b(oil|brent|crude|gas|gold|copper|bitcoin|ether(?:eum)?|nasdaq|s&p|dow|dollar|euro|yen|yuan|sterling|nvidia|apple|microsoft|tesla|amazon|alphabet|meta|tsmc|asml|earnings|ipo|merger|acquisition|guidance'
                      r'|nikkei|topix|kospi|sensex|nifty|hang seng|taiex|asx|nzx|jse|tadawul|tasi|bist|ibovespa|bovespa|merval|ipsa|bmv|stoxx|dax|ftse|omx|smi'  # local benchmarks: a big local market move counts like a US one
                      r'|rupee|won|rupiah|baht|ringgit|dong|rand|naira|cedi|shilling|shekel|riyal|dirham|dinar|lira|zloty|krona|krone|franc|peso|real|sol'
                      r'|bolsa|borsa|b[öo]rs|giełda|acciones|a[cç][oõ]es|resultados|lucro|ganancias|fusi[oó]n|adquisi[cç][aã]o|bilan[cç]o|b[ée]n[ée]fice)\b', re.I)
RELEVANT = re.compile(r'\b(market|markets|stocks?|shares|bonds?|currency|commodit\w+|earnings|economy|economic|bank|fund|invest\w*|trade|price[sd]?|profit|revenue|oil|bitcoin|crypto'
                      r'|mercados?|econom[ií]a|empresas?|bancos?|inversi[oó]n|investimentos?|exporta\w*|precios?|pre[cç]os?|march[ée]s?|banque|entreprises?|piyasa|ekonomi|şirket|rynek|gospodarka|aktie\w*|marknad|økonomi|ekonomi)\b', re.I)
MAJOR_GEO = {'US', 'CN', 'EU', 'DE', 'JP', 'GB', 'FR', 'IN'}

def authority_of(c):
    k = c.get('kind', 'news')
    if k == 'official': return AUTHORITY['official']
    return AUTHORITY.get(c.get('class') or ('gdelt' if c.get('from_gdelt') else 'publisher'), AUTHORITY['publisher'])

def score(c, now, dup_count=0):
    """0-100. Stored for ordering only. Components are deliberately plain: authority, relevance, recency, asset exposure,
    macro significance, event severity, geography, minus a penalty for each near-duplicate already covered."""
    t = f"{c.get('title','')} {(c.get('desc') or '')[:200]}"
    mins = age_minutes(c['published'], now) if c.get('published') else 1440
    recency = max(0.0, 1 - mins / 720) ** 1.5  # full marks when new, ~0 after 12 hours
    relevance = min(1.0, .35 + .2 * len(set(m.lower() for m in RELEVANT.findall(t))))
    exposure = 1.0 if EXPOSURE.search(t) else 0.0
    macro = 1.0 if MACRO.search(t) else 0.0
    severity = 1.0 if SEVERE.search(t) else 0.0
    geo = 1.0 if (c.get('country') in MAJOR_GEO or re.search(r'\b(u\.?s\.?|united states|china|europe|eurozone|japan|britain|uk|germany|india)\b', t, re.I)) else .75 if c.get('region') else .4  # a regional publisher's own market counts
    raw = .26 * authority_of(c) + .16 * relevance + .20 * recency + .10 * exposure + .14 * macro + .08 * severity + .06 * geo
    return round(max(0.0, 100 * raw - 6 * min(dup_count, 4)), 1)

# ---------- duplicates ----------
def dedupe(items, known, now=None):
    """items: candidate dicts {title,url,published,kind,...}. known: [(title, published_iso)] already online.
    Keeps one article per event: the most authoritative, then the earliest. Returns (kept, dropped_count).
    The kept item records how many other sources covered it (`dups`)."""
    now = now or datetime.now(timezone.utc)
    known = [(t, from_iso(p)) if isinstance(p, str) else (t, p) for t, p in known]
    kept, urls, dropped = [], set(), 0
    order = sorted(items, key=lambda c: (-authority_of(c), c.get('published') or ''))
    for c in order:
        cu = canon(c['url'])
        if cu in urls: dropped += 1; continue
        pub = from_iso(c['published']) if c.get('published') else now
        hit = None
        for k in kept:
            if same_event(c['title'], k['title'], abs((pub - from_iso(k['published'])).total_seconds()) / 3600 if k.get('published') else 0): hit = k; break
        if hit: hit['dups'] = hit.get('dups', 0) + 1; hit.setdefault('also', []).append({'name': c['source'], 'url': c['url']}); dropped += 1; urls.add(cu); continue
        if any(same_event(c['title'], t, abs((pub - kp).total_seconds()) / 3600) for t, kp in known): dropped += 1; urls.add(cu); continue
        urls.add(cu); kept.append(c)
    return kept, dropped

# ---------- validation and atomic writes ----------
REQUIRED = ('id', 'headline', 'category', 'published_at', 'source', 'location')

def validate_feed(obj, min_stories=1):
    """Returns a list of problems; empty means safe to publish."""
    if not isinstance(obj, dict): return ['not an object']
    st = obj.get('stories')
    if not isinstance(st, list): return ['stories is not a list']
    bad = []
    if len(st) < min_stories: bad.append(f'only {len(st)} stories (minimum {min_stories})')
    ids = set()
    for i, s in enumerate(st):
        if not isinstance(s, dict): bad.append(f'story {i} not an object'); continue
        miss = [k for k in REQUIRED if not s.get(k)]
        if miss: bad.append(f'story {i} missing {miss}'); continue
        if s['id'] in ids: bad.append(f"duplicate id {s['id']}")
        ids.add(s['id'])
        try: from_iso(s['published_at'])
        except Exception: bad.append(f"story {s['id']} bad published_at")
        if len(bad) > 8: break
    return bad

def atomic_write(path, obj, validate=None):
    """Write to a temp file in the same folder, validate by re-reading it, then replace. On any failure the old file is untouched."""
    text = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    json.loads(text)
    if validate:
        problems = validate(obj)
        if problems: raise ValueError('; '.join(problems))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.tmp-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f: f.write(text)
        json.load(open(tmp, encoding='utf-8'))
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise

# ---------- retention ----------
def retain(stories, now, keep_days, max_n):
    """Newest first, unique ids, nothing older than keep_days, at most max_n."""
    cut = now - timedelta(days=keep_days); seen, out = set(), []
    for s in sorted(stories, key=lambda s: s['published_at'], reverse=True):
        if s['id'] in seen or from_iso(s['published_at']) <= cut: continue
        seen.add(s['id']); out.append(s)
    return out[:max_n]

def freshness(updated_at, now):
    """Plain label for how old the data is. Never says LIVE."""
    m = int((now - from_iso(updated_at)).total_seconds() // 60)
    if m < 1: return 'Updated just now'
    if m < 60: return f'Updated {m}m ago'
    if m < 1440: return f'Updated {m // 60}h ago'
    return f'Updated {m // 1440}d ago'
