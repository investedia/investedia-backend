"""Canonical asset/entity registry: one identity for every asset Investedia talks about (news, Globe, asset and company pages,
implications, Track Record). Raw ticker strings are never trusted: a mention resolves to a stable internal id only when the
official identity behind the symbol matches the name the article used.

Ids (stable, never reused):
  EQ:<MIC>:<SYMBOL>   listed share or fund, e.g. EQ:XNAS:AAPL, EQ:XPAR:MC (LVMH), EQ:XNYS:MC (Moelis & Company)
  IX:<CODE>           index, e.g. IX:SPX, IX:STOXX600
  FX:<PAIR>           currency concept in the site's convention (strength against the US dollar), e.g. FX:USDBRL
  CR:<CODE>           crypto asset, e.g. CR:BTC
  CM:<CODE>           commodity (front-month future as the price), e.g. CM:XAU, CM:BRENT
  RT:<CODE>           rate / sovereign yield, e.g. RT:US10Y
Companies: CO:CIK<10 digits> for SEC registrants, otherwise CO:<listing id> of the home listing.

Data: data/registry.json (built by tools/registry/build_registry.py). Only verified listings are in it. A listing is verified by
the SEC company-ticker file (US issuers: ticker, CIK, exchange, registrant name) or by Yahoo Finance's security record for
exchange-qualified symbols (official long name, exchange, instrument type). Non-equity assets come from fixed tables.

resolve() never guesses: an unknown symbol, a symbol whose official owner has another name, an ambiguous name, a sector or
a country all return id None with a reason. The article is kept; it just cannot create a financial connection."""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, 'data', 'registry.json')
VERSION = 'registry-v1'

# words that do not identify a company
STOP = {'inc', 'incorporated', 'corp', 'corporation', 'co', 'company', 'cos', 'ltd', 'limited', 'plc', 'llc', 'lp', 'llp', 'holdings', 'holding',
        'group', 'grupo', 'the', 'sa', 'sab', 'cv', 'saa', 'nv', 'ag', 'se', 'spa', 'asa', 'ab', 'oyj', 'as', 'bhd', 'berhad', 'tbk', 'pt', 'pcl',
        'adr', 'ads', 'class', 'cl', 'shares', 'share', 'common', 'stock', 'ordinary', 'sponsored', 'unsponsored', 'new', 'and', 'of', 'de', 'del',
        'do', 'da', 'des', 'la', 'le', 'el', 'kgaa', 'societe', 'europeenne', 'participacoes', 'part', 'ord', 'pn', 'on', 'unit', 'units', 'trust',
        'reit', 'gmbh', 'bv', 'k', 'kk', 'ltda', 'sae', 'pjsc', 'psc', 'qpsc', 'jsc', 'tr', 'a', 'b', 'c', 'i', 'y', 'e', 'spolka', 'akcyjna',
        'anonim', 'sirketi', 'ortakligi', 'tbk', 'aps', 'fund', 'etf', 'index'}
# first words that are too common to identify a company on their own
GENERIC = {'bank', 'banco', 'energy', 'international', 'industries', 'financial', 'motor', 'motors', 'resources', 'technology', 'technologies',
           'global', 'national', 'first', 'american', 'china', 'united', 'general', 'capital', 'pharma', 'pharmaceuticals', 'oil', 'gas', 'power',
           'mining', 'metals', 'steel', 'airlines', 'air', 'insurance', 'investment', 'investments', 'systems', 'data', 'health', 'healthcare',
           'brasil', 'brazil', 'india', 'japan', 'korea', 'south', 'north', 'west', 'east', 'new', 'royal', 'standard', 'state', 'credit', 'trust',
           'real', 'estate', 'properties', 'development', 'electric', 'telecom', 'communications', 'media', 'entertainment', 'foods', 'food', 'auto'}

TRANSLIT = str.maketrans({'ø': 'o', 'Ø': 'O', 'æ': 'ae', 'Æ': 'AE', 'ß': 'ss', 'ł': 'l', 'Ł': 'L', 'đ': 'd', 'Đ': 'D', 'ı': 'i', 'œ': 'oe', 'Œ': 'OE'})

def ascii_lower(x):
    return unicodedata.normalize('NFKD', str(x or '').translate(TRANSLIT)).encode('ascii', 'ignore').decode().lower()

def words(x, keep_stop=False):
    x = re.sub(r'\.com\b', ' ', ascii_lower(x)).replace('&', ' and ').replace("'s", '').replace('.', '')
    w = re.sub(r'[^a-z0-9 ]', ' ', x).split()
    return w if keep_stop else [t for t in w if t not in STOP]

def name_key(x):
    """Normalised company name used for exact name lookups."""
    return ' '.join(words(x))

def same_company(said, official):
    """True when the name an article used clearly names the same company as the official registrant/security name."""
    a, b = words(said), words(official)
    if not a or not b: return False
    if a == b or ''.join(a) == ''.join(b): return True
    A, B = set(a), set(b)
    distinctive = lambda ws: len(ws) >= 2 or (ws[0] not in GENERIC and len(ws[0]) >= 3)
    if A <= B and distinctive(a) and a[0] in B: return True     # "Lilly" ⊂ "Eli Lilly and Co", "HSBC" ⊂ "HSBC Holdings plc"
    if B <= A and distinctive(b) and b[0] in A: return True     # "Toyota Motor Corp" ⊂ "Toyota Motor Corporation Japan"
    acr = lambda ws: ''.join(w[0] for w in ws)
    sa, sb = ''.join(a), ''.join(b)
    for full in (b, words(official, True)):
        if len(sa) >= 3 and sa == acr(full): return True        # "IBM" = International Business Machines
    for full in (a, words(said, True)):
        if len(sb) >= 3 and sb == acr(full): return True
    short, long_ = sorted((sa, sb), key=len)
    if len(short) >= 6 and long_.startswith(short) and len(short) >= .6 * len(long_): return True  # "SamsungElec" / "Samsung Electronics"
    return False

def norm_ticker(t):
    t = str(t or '').strip().upper().replace(' ', '')
    t = re.sub(r'^\$', '', t)
    return t

class Registry:
    def __init__(self, data=None, path=PATH):
        if data is None:
            if os.path.exists(path):
                with open(path, encoding='utf-8') as f: data = json.load(f)
            else: data = {'assets': {}, 'alias': {}, 'names': {}, 'companies': {}}
        self.data = data
        self.assets = data.setdefault('assets', {})
        self.alias = data.setdefault('alias', {})
        self.names = data.setdefault('names', {})
        self.companies = data.setdefault('companies', {})
        self.patterns = [(re.compile(p, re.I), i) for p, i in data.get('patterns', [])]

    def ids_for_ticker(self, t):
        return list(self.alias.get(norm_ticker(t), []))

    def verified(self, aid):
        return aid in self.assets

    def drawable(self, aid):
        """Verified AND has a legitimate place (crypto never does)."""
        a = self.assets.get(aid)
        return bool(a and a.get('geo') and a['geo'].get('la') is not None)

    def public(self, aid):
        """The compact copy stored on a story: enough to draw and price it without loading the registry."""
        a = self.assets[aid]; g = a.get('geo') or {}
        out = {'id': aid, 'n': a['name'], 'c': a['class'], 'px': a.get('px')}
        if g.get('la') is not None: out.update(la=g['la'], lo=g['lo'], geo=g.get('src'))
        if a.get('site'): out['site'] = a['site']
        if a.get('company'): out['co'] = a['company']
        if a.get('freq') == 'monthly': out['freq'] = 'monthly'
        return out

    def _names_of(self, aid):
        a = self.assets[aid]
        return [x for x in [a.get('name'), a.get('official')] + a.get('names', []) if x]

    def resolve(self, name=None, ticker=None, kind=None, country=None):
        """-> {'id': asset id or None, 'method': ..., 'reason': ...}. kind: company / asset / sector / country (impact kinds)."""
        if kind in ('sector', 'country'): return {'id': None, 'reason': f'{kind}-not-an-asset'}
        t = norm_ticker(ticker)
        if t:
            ids = self.ids_for_ticker(t)
            if not ids: return self._by_name(name, kind, f'unknown-ticker:{t}')
            fixed = [i for i in ids if self.assets[i]['class'] in ('fx', 'crypto', 'commodity', 'index', 'rate')]
            if fixed and len(fixed) == len(ids) and len(set(fixed)) == 1:  # a fixed-table symbol (BRL=X, BTC-USD, ^TNX ...) means one thing
                return {'id': fixed[0], 'method': 'ticker-fixed'}
            ok = [i for i in ids if name and any(same_company(name, n) for n in self._names_of(i))]
            if len(ok) == 1: return {'id': ok[0], 'method': 'ticker+name'}
            if len(ok) > 1:
                same_co = {self.assets[i].get('company') or i for i in ok}
                if len(same_co) == 1:  # several listings of one company: prefer the home listing, then the first
                    home = [i for i in ok if self.assets[i].get('home')]
                    return {'id': (home or ok)[0], 'method': 'ticker+name'}
                return {'id': None, 'reason': f'ambiguous-ticker:{t}'}
            if not name: return {'id': None, 'reason': f'ticker-without-name:{t}'}
            r = self._by_name(name, kind, None)
            if r['id']: return {**r, 'note': f'ticker {t} belongs to {self.assets[ids[0]].get("official") or self.assets[ids[0]]["name"]}'}
            return {'id': None, 'reason': f'name-mismatch:{t}={self.assets[ids[0]].get("official") or self.assets[ids[0]]["name"]}'}
        return self._by_name(name, kind, 'no-ticker')

    def _by_name(self, name, kind, reason):
        if not name: return {'id': None, 'reason': reason or 'no-name'}
        for rx, aid in self.patterns:  # fixed phrases for indices, currencies, commodities, crypto and rates
            if rx.fullmatch(ascii_lower(name).strip()): return {'id': aid, 'method': 'name-pattern'}
        ids = self.names.get(name_key(name), [])
        cos = {self.assets[i].get('company') or i for i in ids}
        if ids and len(cos) == 1:
            home = [i for i in ids if self.assets[i].get('home')]
            return {'id': (home or ids)[0], 'method': 'name-exact'}
        if ids: return {'id': None, 'reason': 'ambiguous-name'}
        return {'id': None, 'reason': reason or 'unknown-name'}

_REG = None
def get():
    global _REG
    if _REG is None: _REG = Registry()
    return _REG

def stamp(row, reg=None):
    """Adds the resolution to an impact/entity row in place: row['asset'] (compact public copy) or row['unresolved'] (reason)."""
    reg = reg or get()
    r = reg.resolve(row.get('name'), row.get('ticker'), row.get('kind'), row.get('country'))
    row.pop('asset', None); row.pop('unresolved', None)
    if r['id']: row['asset'] = {**reg.public(r['id']), 'm': r['method'], 'rv': VERSION}
    else: row['unresolved'] = r['reason'][:80]
    return row
