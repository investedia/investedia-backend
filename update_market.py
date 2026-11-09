"""Collect real market prices for every asset on the site, using free sources only.

  python3 update_market.py           quotes + intraday charts (run every 30 minutes)
  python3 update_market.py --full    also rebuilds the long-term history files (run once a day)

Writes assets/quotes.js, assets/intraday.json and assets/hist/<SYMBOL>.json, then mirrors them into docs/.
Sources: Yahoo Finance chart data (stocks, indices, futures, currencies, commodities, funds, crypto)
and FRED, the US Federal Reserve's free data service (US 2-year, foreign 10-year and corporate bond yields).
Live crypto ticks come straight from Coinbase in the visitor's browser (see assets/live.js).
"""
import json, os, shutil, sys, time, datetime as dt, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
FULL = "--full" in sys.argv or not os.path.isdir(os.path.join(ROOT, "assets", "hist"))

# Site symbol -> Yahoo symbol
YAHOO = {
    # indices and index futures
    "SPX": "^GSPC", "NDX": "^NDX", "DJI": "^DJI", "RUT": "^RUT", "DAX": "^GDAXI", "CAC": "^FCHI", "UKX": "^FTSE",
    "NKY": "^N225", "SX5E": "^STOXX50E", "HSI": "^HSI", "TSX": "^GSPTSE", "IBOV": "^BVSP", "MXX": "^MXX",
    "XJO": "^AXJO", "NZ50": "^NZ50", "J203": "^J203.JO", "EGX30": "^EGX30.CA", "SENSEX": "^BSESN",
    "KOSPI": "^KS11", "SSEC": "000001.SS", "ES1": "ES=F", "YM1": "YM=F", "NQ1": "NQ=F",
    # crypto
    "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "XRP": "XRP-USD", "BNB": "BNB-USD", "DOGE": "DOGE-USD",
    "ADA": "ADA-USD", "AVAX": "AVAX-USD", "LINK": "LINK-USD", "UNI": "UNI7083-USD", "AAVE": "AAVE-USD",
    "USDT": "USDT-USD", "USDC": "USDC-USD",
    "TRX": "TRX-USD", "ZEC": "ZEC-USD", "HYPE": "HYPE32196-USD", "XMR": "XMR-USD", "LEO": "LEO-USD", "XLM": "XLM-USD", "NEAR": "NEAR-USD", "BCH": "BCH-USD", "DAI": "DAI-USD", "LTC": "LTC-USD", "SUI": "SUI20947-USD", "HBAR": "HBAR-USD", "PYUSD": "PYUSD-USD", "SHIB": "SHIB-USD", "CRO": "CRO-USD", "QNT": "QNT-USD", "ENA": "ENA-USD", "RLUSD": "RLUSD-USD",
    # currencies
    "DXY": "DX-Y.NYB",
    # commodities (front-month futures)
    "XAU": "GC=F", "XAG": "SI=F", "WTI": "CL=F", "BRENT": "BZ=F", "NG": "NG=F", "HG": "HG=F", "PL": "PL=F",
    "ZW": "ZW=F", "ZC": "ZC=F", "KC": "KC=F", "ZS": "ZS=F",
    # bonds quoted by Yahoo (yield x1)
    "US10Y": "^TNX", "US30Y": "^TYX",
    # non-US listings
    "SAP": "SAP.DE", "HSBA": "HSBA.L", "SHEL": "SHEL.L", "BNP": "BNP.PA", "TTE": "TTE.PA", "MC": "MC.PA",
    "VWCE": "VWCE.DE", "URW": "URW.PA", "VNA": "VNA.DE",
    # regional companies on their home exchanges
    "NESN": "NESN.SW", "NOVN": "NOVN.SW", "ROG": "RO.SW", "AZN": "AZN.L", "ULVR": "ULVR.L", "SIE": "SIE.DE", "ALV": "ALV.DE", "RHM": "RHM.DE",
    "AIR": "AIR.PA", "OR": "OR.PA", "ITX": "ITX.MC", "SAN": "SAN.MC", "RACE": "RACE.MI", "ENEL": "ENEL.MI",
    "SMSN": "005930.KS", "HYMTF": "005380.KS", "SONY": "6758.T", "MUFG": "8306.T", "NTDOY": "7974.T", "SFTBY": "9984.T",
    "TCEHY": "0700.HK", "BYDDY": "1211.HK", "XIACY": "1810.HK", "RELI": "RELIANCE.NS", "INFY": "INFY.NS", "HDB": "HDFCBANK.NS", "DBS": "D05.SI",
    "BRKB": "BRK-B", "TD": "TD.TO", "ENB": "ENB.TO", "CNQ": "CNQ.TO",
    "BHP": "BHP.AX", "RIO": "RIO.AX", "FMG": "FMG.AX", "CBA": "CBA.AX", "WBC": "WBC.AX", "NAB": "NAB.AX", "MQG": "MQG.AX", "CSL": "CSL.AX", "WES": "WES.AX",
    "FPH": "FPH.NZ", "MEL": "MEL.NZ", "NPN": "NPN.JO", "MTN": "MTN.JO", "SBK": "SBK.JO", "FSR": "FSR.JO", "CPI": "CPI.JO", "GFI": "GFI.JO", "ANG": "ANG.JO",
    "SSL": "SOL.JO", "SHP": "SHP.JO", "COMI": "COMI.CA", "ARMCO": "2222.SR", "RJHI": "1120.SR", "SABIC": "2010.SR", "STC": "7010.SR", "QNBK": "QNBK.QA",
    "EMAAR": "EMAAR.AE", "ENBD": "EMIRATESNBD.AE",
    # regional indices
    "IBEX": "^IBEX", "FTSEMIB": "FTSEMIB.MI", "SMI": "^SSMI", "AEX": "^AEX", "NIFTY": "^NSEI", "STI": "^STI", "TWII": "^TWII", "TASI": "^TASI.SR", "TA35": "TA35.TA",
}
FX = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "USDTRY", "USDMXN", "USDZAR", "USDCAD", "USDBRL", "USDCNY", "USDINR", "USDKRW", "NZDUSD", "USDILS", "USDEGP"]
YAHOO.update({s: s + "=X" for s in FX})
# Bond yields from FRED: (series id, how often it's published)
FRED = {"US02Y": ("DGS2", "daily"), "USIG": ("BAMLC0A0CMEY", "daily"), "USHY": ("BAMLH0A0HYM2EY", "daily"),
        "DE10Y": ("IRLTLT01DEM156N", "monthly"), "FR10Y": ("IRLTLT01FRM156N", "monthly"),
        "IT10Y": ("IRLTLT01ITM156N", "monthly"), "UK10Y": ("IRLTLT01GBM156N", "monthly"),
        "JP10Y": ("IRLTLT01JPM156N", "monthly"), "ES10Y": ("IRLTLT01ESM156N", "monthly"), "CH10Y": ("IRLTLT01CHM156N", "monthly"),
        "CA10Y": ("IRLTLT01CAM156N", "monthly"), "MX10Y": ("IRLTLT01MXM156N", "monthly"), "AU10Y": ("IRLTLT01AUM156N", "monthly"),
        "KR10Y": ("IRLTLT01KRM156N", "monthly"), "IN10Y": ("INDIRLTLT01STM", "monthly"), "ZA10Y": ("IRLTLT01ZAM156N", "monthly"),
        "IL10Y": ("IRLTLT01ILM156N", "monthly")}
YIELDS = {"ES10Y", "CH10Y", "CA10Y", "MX10Y", "AU10Y", "KR10Y", "IN10Y", "ZA10Y", "IL10Y", "US02Y", "US10Y", "US30Y", "USIG", "USHY", "DE10Y", "FR10Y", "IT10Y", "UK10Y", "JP10Y"}
CENTS = {"GBp", "GBX", "ZAc", "USX", "ILA"}  # quoted in pence/cents -> convert to main unit


def site_symbols():
    """Read the asset list straight out of assets/mock.js so the two never drift apart."""
    import re
    src = open(os.path.join(ROOT, "assets", "mock.js")).read()
    syms = re.findall(r"\{ s: '([A-Z0-9]+)'", src) + re.findall(r"\bS\('([A-Z0-9]+)'", src)
    return list(dict.fromkeys(syms))


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Investedia data bot)"})
            return urllib.request.urlopen(req, timeout=20).read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def yahoo(sym, rng, interval):
    q = urllib.parse.quote(sym)
    j = json.loads(get(f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?range={rng}&interval={interval}"))
    r = j["chart"]["result"][0]
    ts = r.get("timestamp") or []
    qd = r["indicators"]["quote"][0] if ts else {}
    rows = []
    for i, t in enumerate(ts):
        c = qd["close"][i]
        if c is None:
            continue
        o, h, l, v = qd["open"][i], qd["high"][i], qd["low"][i], qd["volume"][i]
        rows.append([t, o if o is not None else c, h if h is not None else c, l if l is not None else c, c, v or 0])
    return r["meta"], rows


def rnd(v, ref):
    """Round to a sensible number of significant digits for the price level."""
    a = abs(ref) or 1
    return round(v, 2 if a >= 100 else 3 if a >= 10 else 4 if a >= 1 else 6)


def pct(a, b):
    return round((a / b - 1) * 100, 2) if b else 0.0


def thin(xs, n):
    if len(xs) <= n:
        return xs
    step = (len(xs) - 1) / (n - 1)
    return [xs[round(i * step)] for i in range(n)]


def fmt_vol(v):
    return "—" if not v else f"{v / 1e9:.1f}B" if v >= 1e9 else f"{v / 1e6:.1f}M" if v >= 1e6 else f"{v / 1e3:.0f}K"


def from_yahoo(s):
    ysym = YAHOO.get(s, s)
    meta, daily = yahoo(ysym, "3mo", "1d")
    k = 0.01 if meta.get("currency") in CENTS else 1
    cur = {"GBp": "GBP", "GBX": "GBP", "ZAc": "ZAR", "USX": "USD"}.get(meta.get("currency"), meta.get("currency"))
    price = (meta.get("regularMarketPrice") or (daily[-1][4] if daily else 0)) * k
    closes = [r[4] * k for r in daily]
    if closes:
        closes[-1] = price
    y = s in YIELDS
    prev = closes[-2] if len(closes) > 1 else (meta.get("chartPreviousClose") or price) * k

    def chg(n):  # change vs n sessions ago: % for prices, basis points for yields
        if len(closes) <= n:
            return 0.0
        return round((price - closes[-1 - n]) * 100, 1) if y else pct(price, closes[-1 - n])

    q = {"p": rnd(price, price), "d": round((price - prev) * 100, 1) if y else pct(price, prev), "w": chg(5), "m1": chg(21),
         "sp": [rnd(c, price) for c in closes[-48:]], "t": meta.get("regularMarketTime"), "cur": cur}
    if daily:
        last = daily[-1]
        q.update(hi=rnd(meta.get("regularMarketDayHigh", last[2]) * k, price), lo=rnd(meta.get("regularMarketDayLow", last[3]) * k, price))
        if meta.get("regularMarketVolume"):
            q["v"] = meta["regularMarketVolume"]
    # Intraday: today's session at 15 minutes, last five sessions at 1 hour
    intra = {}
    try:
        _, m15 = yahoo(ysym, "5d", "15m")
        if m15:
            day = dt.datetime.fromtimestamp(m15[-1][0] + meta.get("gmtoffset", 0), dt.timezone.utc).date()
            today = [r for r in m15 if dt.datetime.fromtimestamp(r[0] + meta.get("gmtoffset", 0), dt.timezone.utc).date() == day]
            # compact: start time + step for today; one list per day for the 5-day view
            d1 = thin(today, 60)
            days = {}
            for r in m15[::4]:
                days.setdefault(dt.datetime.fromtimestamp(r[0] + meta.get("gmtoffset", 0), dt.timezone.utc).date(), []).append(r)
            intra = {"d1": {"t": [d1[0][0], d1[-1][0]], "c": [rnd(r[4] * k, price) for r in d1]},
                     "d5": [{"t": v[0][0], "c": [rnd(r[4] * k, price) for r in thin(v, 24)]} for v in list(days.values())[-5:]]}
    except Exception:
        pass
    return q, intra, ysym, k


def history(s, ysym, k):
    meta, rows = yahoo(ysym, "5y", "1d")
    if not rows:
        return None
    ref = rows[-1][4] * k
    daily = [[r[0], rnd(r[1] * k, ref), rnd(r[2] * k, ref), rnd(r[3] * k, ref), rnd(r[4] * k, ref), r[5]] for r in rows[-260:]]
    # Weekly bars for the 5-year view
    weekly, cur = [], None
    for r in rows:
        wk = dt.datetime.fromtimestamp(r[0], dt.timezone.utc).isocalendar()[:2]
        if cur and cur[0] == wk:
            b = cur[1]; b[2] = max(b[2], r[2]); b[3] = min(b[3], r[3]); b[4] = r[4]; b[5] += r[5]
        else:
            cur = (wk, [r[0], r[1], r[2], r[3], r[4], r[5]]); weekly.append(cur[1])
    weekly = [[b[0], rnd(b[1] * k, ref), rnd(b[2] * k, ref), rnd(b[3] * k, ref), rnd(b[4] * k, ref), b[5]] for b in weekly]
    yr = daily[-252:] if len(daily) >= 252 else daily
    jan1 = dt.datetime(dt.datetime.now(dt.timezone.utc).year, 1, 1, tzinfo=dt.timezone.utc).timestamp()
    ytd_base = next((r[4] for r in reversed(rows) if r[0] < jan1), None)
    y = s in YIELDS

    def perf(base):
        if base is None:
            return None
        return round((ref - base * k) * 100, 1) if y else pct(ref, base * k)
    n = len(rows)
    return {"s": s, "src": "Yahoo Finance", "daily": daily, "weekly": weekly,
            "hi52": max(r[2] for r in yr), "lo52": min(r[3] for r in yr),
            "perf": {"1M": perf(rows[-22][4] if n > 22 else None), "3M": perf(rows[-64][4] if n > 64 else None),
                     "YTD": perf(ytd_base), "1Y": perf(rows[-253][4] if n > 253 else None), "5Y": perf(rows[0][4] if n > 1000 else None)}}


def from_fred(s):
    sid, freq = FRED[s]
    txt = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}").decode()
    pts = []
    for line in txt.strip().splitlines()[1:]:
        d, _, v = line.partition(",")
        try:
            pts.append((d, float(v)))
        except ValueError:
            continue  # FRED marks missing days with "."
    vals = [v for _, v in pts]
    p = vals[-1]
    back = (lambda n: round((p - vals[-1 - n]) * 100, 1) if len(vals) > n else 0.0)
    if freq == "daily":
        q = {"p": round(p, 3), "d": back(1), "w": back(5), "m1": back(21), "sp": [round(v, 3) for v in vals[-48:]]}
    else:  # monthly averages: "today" shows the latest monthly move
        q = {"p": round(p, 3), "d": 0.0, "w": 0.0, "m1": back(1), "sp": [round(v, 3) for v in vals[-48:]]}  # no daily data: only the monthly move is real
    q.update(asof=pts[-1][0], freq=freq)
    ts = lambda d: int(dt.datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp())
    tail = pts[-1300:] if freq == "daily" else pts[-60:]
    rows = [[ts(d), v, v, v, v, 0] for d, v in tail]
    hist = {"s": s, "src": "FRED, Federal Reserve Bank of St. Louis", "freq": freq,
            "daily": rows[-260:] if freq == "daily" else rows, "weekly": rows[::5] if freq == "daily" else rows,
            "hi52": max(v for _, v in pts[-(252 if freq == 'daily' else 12):]),
            "lo52": min(v for _, v in pts[-(252 if freq == 'daily' else 12):]), "perf": {}}
    return q, hist


def one(s):
    try:
        if s in FRED:
            q, hist = from_fred(s)
            return s, q, {}, hist, None
        q, intra, ysym, k = from_yahoo(s)
        hist = history(s, ysym, k) if FULL else None
        return s, q, intra, hist, None
    except Exception as e:
        return s, None, None, None, f"{type(e).__name__}: {e}"[:120]


def main():
    syms = site_symbols()
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(one, syms))
    quotes, intraday, missing = {}, {}, []
    os.makedirs(os.path.join(ROOT, "assets", "hist"), exist_ok=True)
    for s, q, intra, hist, err in results:
        if err or not q or not q.get("p"):
            missing.append(s)
            print(f"  skip {s}: {err or 'no price'}")
            continue
        quotes[s] = q
        if intra:
            intraday[s] = intra
        if hist:
            with open(os.path.join(ROOT, "assets", "hist", f"{s}.json"), "w") as f:
                json.dump(hist, f, separators=(",", ":"))
    if len(quotes) < len(syms) * 0.6:
        sys.exit(f"Only {len(quotes)} of {len(syms)} prices came back; keeping the previous data.")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(ROOT, "assets", "quotes.js"), "w") as f:
        f.write("window.QUOTES=" + json.dumps({"updated": now, "q": quotes}, separators=(",", ":")) + ";\n")
    with open(os.path.join(ROOT, "assets", "intraday.json"), "w") as f:
        json.dump({"updated": now, "s": intraday}, f, separators=(",", ":"))
    # GitHub Pages publishes the docs/ copy of the site
    docs = os.path.join(ROOT, "docs", "assets")
    if os.path.isdir(docs):
        for name in ("quotes.js", "intraday.json"):
            shutil.copy2(os.path.join(ROOT, "assets", name), os.path.join(docs, name))
        shutil.copytree(os.path.join(ROOT, "assets", "hist"), os.path.join(docs, "hist"), dirs_exist_ok=True)
    print(f"Updated {len(quotes)}/{len(syms)} assets at {now}" + (f"; no data for {', '.join(missing)}" if missing else "") + (" (with history)" if FULL else ""))


if __name__ == "__main__":
    main()
