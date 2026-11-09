"""Collect recent headlines for every asset from free public news feeds.

  python3 update_news.py

Writes assets/news.js (latest top stories, loaded on every page) and assets/news/<SYMBOL>.json
(headlines for each asset), then mirrors them into docs/. Headlines link to the original article;
we only keep the title, source, time and a short snippet.
Sources: Yahoo Finance RSS (per stock and fund), Google News RSS (indices, currencies, commodities,
bonds, crypto and anything else), CoinDesk and Cointelegraph RSS (crypto).
"""
import html, json, os, re, shutil, sys, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from update_market import YAHOO  # site symbol -> Yahoo symbol

UA = {"User-Agent": "Mozilla/5.0 (Investedia news bot)"}
MAX_AGE = 7 * 86400
PER_ASSET = 10

# Search terms for Google News where a ticker feed doesn't exist
QUERY = {
    "SPX": '"S&P 500"', "NDX": '"Nasdaq 100" OR "Nasdaq Composite"', "DJI": '"Dow Jones"', "RUT": '"Russell 2000"',
    "DAX": 'DAX index Germany stocks', "CAC": '"CAC 40"', "UKX": '"FTSE 100"', "NKY": 'Nikkei 225', "SX5E": '"Euro Stoxx 50" OR "European stocks"',
    "HSI": '"Hang Seng"', "TSX": 'TSX Toronto stocks', "IBOV": 'Ibovespa', "MXX": 'Mexico IPC stocks', "XJO": '"ASX 200"', "NZ50": 'NZX 50',
    "J203": 'JSE stocks South Africa', "EGX30": 'EGX30 Egypt stocks', "NGSE": 'Nigerian stock exchange NGX', "SENSEX": 'Sensex', "KOSPI": 'Kospi',
    "SSEC": '"Shanghai Composite"', "ES1": '"S&P 500 futures"', "YM1": '"Dow futures"', "NQ1": '"Nasdaq futures"',
    "EURUSD": '"EUR/USD" OR "euro dollar"', "GBPUSD": '"GBP/USD" OR "pound dollar"', "USDJPY": '"USD/JPY" OR "yen dollar"', "USDCHF": '"USD/CHF" OR "Swiss franc"',
    "AUDUSD": '"AUD/USD" OR "Australian dollar"', "DXY": '"dollar index"', "EURGBP": '"EUR/GBP" OR "euro pound"', "EURJPY": '"EUR/JPY" OR "euro yen"',
    "GBPJPY": '"GBP/JPY"', "EURCHF": '"EUR/CHF" OR "euro franc"', "USDTRY": '"Turkish lira"', "USDMXN": '"Mexican peso"', "USDZAR": '"South African rand"',
    "XAU": '"gold price" OR "gold prices"', "XAG": '"silver price" OR "silver prices"', "WTI": '"oil prices" OR "WTI crude"', "BRENT": '"Brent crude"',
    "NG": '"natural gas prices"', "HG": '"copper prices"', "PL": '"platinum price"', "ZW": '"wheat prices"', "ZC": '"corn prices"', "KC": '"coffee prices"', "ZS": '"soybean prices"',
    "US02Y": '"2-year Treasury yield"', "US10Y": '"10-year Treasury yield"', "US30Y": '"30-year Treasury yield"', "DE10Y": '"Bund yield" OR "German bonds"',
    "FR10Y": '"French bonds" OR "OAT yield"', "JP10Y": '"JGB yield" OR "Japanese government bonds"', "UK10Y": '"gilt yields"', "IT10Y": '"Italian bonds" OR "BTP yield"',
    "USIG": '"investment-grade bonds"', "USHY": '"high-yield bonds" OR "junk bonds"',
}
ALIAS = {'GOOGL': ['Google', 'Alphabet'], 'META': ['Facebook', 'Instagram'], 'JPM': ['JPMorgan', 'JP Morgan'], 'LLY': ['Lilly'], 'XOM': ['Exxon'], 'BRK': ['Berkshire'], 'TSM': ['TSMC'], 'KO': ['Coca-Cola'], 'BAC': ['BofA'], 'GS': ['Goldman'], 'HSBA': ['HSBC'], 'UNH': ['UnitedHealth'], 'JNJ': ['J&J', 'Johnson'], 'NVO': ['Novo', 'Wegovy', 'Ozempic'], 'MC': ['LVMH'], 'TM': ['Toyota'], 'BABA': ['Alibaba'], 'MELI': ['MercadoLibre'], 'PBR': ['Petrobras'], 'NU': ['Nubank'], 'SPY': ['S&P 500'], 'QQQ': ['Nasdaq'], 'VOO': ['Vanguard', 'S&P 500'], 'VTI': ['Vanguard'], 'IBIT': ['iShares', 'bitcoin ETF'], 'GLD': ['gold'], 'TLT': ['Treasury'], 'VWCE': ['Vanguard'], 'FXAIX': ['Fidelity'], 'VFIAX': ['Vanguard'], 'ARKK': ['ARK', 'Cathie Wood'], 'SCHD': ['Schwab', 'dividend ETF']}
GENERAL = {"Markets": '"stock market" today', "Economy": 'Fed OR ECB OR inflation economy', "Real Estate": '"housing market" OR "real estate" prices'}
CAT = {"stocks": "Stocks", "indices": "Markets", "crypto": "Crypto", "currencies": "Currencies", "commodities": "Commodities", "bonds": "Economy", "funds": "Markets"}


def assets():
    """Symbol, name and asset class straight from assets/mock.js."""
    src = open(os.path.join(ROOT, "assets", "mock.js")).read()
    out = {}
    for s, n, c in re.findall(r"\{ s: '([A-Z0-9]+)', n: '([^']+)'(?:, [a-z]+: '[^']*')*?, c: '([a-z]+)'", src):
        out[s] = (n, c)
    for s, n in re.findall(r"\bS\('([A-Z0-9]+)', '([^']+)'", src):
        out[s] = (n, "stocks")
    for s, n in re.findall(r"\{ s: '([A-Z0-9]+)', n: '([^']+)', t: '", src):  # REITs
        out[s] = (n, "reits")
    return out


def fetch(url):
    for i in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read()
        except Exception:
            if i == 2:
                raise
            time.sleep(2 * (i + 1))


def clean(text, n=200):
    t = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def parse(xml, default_src):
    items = []
    root = ET.fromstring(xml)
    for it in root.iter("item"):
        title, link = it.findtext("title") or "", it.findtext("link") or ""
        try:
            ts = int(parsedate_to_datetime(it.findtext("pubDate")).timestamp())
        except Exception:
            continue
        src_el = it.find("source")
        src = (src_el.text if src_el is not None and src_el.text else default_src).strip()
        if default_src == "Google News":  # titles end with " - Publisher"
            title = title[: -len(src) - 3] if title.endswith(" - " + src) else re.sub(r"\s+-\s+[^-]+$", "", title)
            desc = ""
        title = re.sub(r"\s+[|–-]\s+(FXStreet|Reuters|Bloomberg|CNBC|Investing\.com|MarketWatch|Barron's|Forbes|Fortune|Yahoo Finance|Benzinga|ad-hoc-news\.de)$", "", title)
        # skip quote pages and price widgets that aren't news
        if re.search(r"Stock Price, News|Quote & History|Live Price|Price Chart|Stock Quote|Historical Data|Price Today, Live|Market Cap and", title, re.I):
            continue
        # English-language headlines only
        if sum(ch.isascii() for ch in title + src) < 0.9 * len(title + src):
            continue
        else:
            desc = clean(it.findtext("description"))
        if title and link and time.time() - ts < MAX_AGE:
            items.append({"t": clean(title, 220), "u": link, "src": src, "ts": ts, "d": clean(desc, 100)})  # keep extracts very short (EU press publishers' right)
    return items


def google(q):
    u = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q + " when:7d", "hl": "en-US", "gl": "US", "ceid": "US:en"})
    return parse(fetch(u), "Google News")


def for_asset(sym, name, kind):
    try:
        if kind in ("stocks", "funds", "reits"):
            short = re.sub(r"\b(Inc|Corp|Co|plc|SE|Ltd|Holdings?|Group|Trust|ETF|Platforms|Technologies|Motor|Wholesale)\b\.?", "", name).strip()
            items = google(f'"{short}" stock' if kind == "stocks" else f'"{short}" OR {sym}')
        elif kind == "crypto":
            items = google(f'"{name}" crypto' if name not in ("XRP", "BNB") else f"{name} crypto")
        else:
            items = google(QUERY.get(sym, f'"{name}"'))
        return sym, items, None
    except Exception as e:
        return sym, None, f"{type(e).__name__}: {e}"[:100]


def main():
    A = assets()
    out_dir = os.path.join(ROOT, "assets", "news")
    os.makedirs(out_dir, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(lambda kv: for_asset(kv[0], *kv[1]), A.items()))
    pool, ok, failed = {}, 0, []
    for sym, items, err in results:
        path = os.path.join(out_dir, f"{sym}.json")
        if items is None:  # keep the previous headlines if a feed failed this time
            failed.append(sym)
            continue
        seen, mine = set(), []
        for it in sorted(items, key=lambda x: -x["ts"]):
            key = re.sub(r"\W+", "", it["t"].lower())[:80]
            if key in seen:
                continue
            seen.add(key)
            mine.append(it)
        mine = mine[:PER_ASSET]
        cat = "Real Estate" if A[sym][1] == "reits" else CAT.get(A[sym][1], "Markets")
        for it in mine:
            it["cat"] = "Earnings" if cat == "Stocks" and re.search(r"\b(earnings|results|quarter|Q[1-4]|guidance|revenue)\b", it["t"], re.I) else cat
            key = re.sub(r"\W+", "", it["t"].lower())[:80]
            p = pool.setdefault(key, dict(it, syms=[]))
            p["syms"].append(sym)
        with open(path, "w") as f:
            json.dump({"s": sym, "items": mine}, f, separators=(",", ":"))
        ok += 1
    # General market, economy and real estate stories, plus crypto news sites
    extra = [(c, lambda q=q: google(q)) for c, q in GENERAL.items()]
    extra += [("Crypto", lambda: parse(fetch("https://www.coindesk.com/arc/outboundfeeds/rss/"), "CoinDesk")),
              ("Crypto", lambda: parse(fetch("https://cointelegraph.com/rss"), "Cointelegraph"))]
    for cat, fn in extra:
        try:
            for it in fn()[:15]:
                key = re.sub(r"\W+", "", it["t"].lower())[:80]
                pool.setdefault(key, dict(it, cat=cat, syms=[]))
        except Exception as e:
            print("  general feed failed:", cat, e)
    # Top stories for every page: newest first, at most 3 per asset so one ticker can't flood the list
    top, per = [], {}
    for it in sorted(pool.values(), key=lambda x: -x["ts"]):
        s0 = it["syms"][0] if it["syms"] else it["cat"]
        if per.get(s0, 0) >= 3:
            continue
        per[s0] = per.get(s0, 0) + 1
        top.append(it)
        if len(top) >= 80:
            break
    if len(top) < 10:
        sys.exit("Too few headlines came back; keeping the previous news.")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(ROOT, "assets", "news.js"), "w") as f:
        f.write("window.NEWS=" + json.dumps({"updated": now, "items": top}, separators=(",", ":")) + ";\n")
    docs = os.path.join(ROOT, "docs", "assets")
    if os.path.isdir(docs):
        shutil.copy2(os.path.join(ROOT, "assets", "news.js"), os.path.join(docs, "news.js"))
        shutil.copytree(out_dir, os.path.join(docs, "news"), dirs_exist_ok=True)
    print(f"News for {ok}/{len(A)} assets, {len(top)} top stories" + (f"; kept previous for {', '.join(failed)}" if failed else ""))


if __name__ == "__main__":
    main()
