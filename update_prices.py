"""Refresh the POV calculator's price history (assets/data.js).
Run:  python3 update_prices.py   then upload the site folder again."""
import json, urllib.request, datetime as dt, time

ASSETS = {"AMZN": "Amazon", "MSFT": "Microsoft", "AAPL": "Apple", "NVDA": "Nvidia", "TSLA": "Tesla",
          "NFLX": "Netflix", "GOOGL": "Google", "META": "Meta", "RACE": "Ferrari", "SNAP": "Snapchat",
          "SPY": "S&P 500", "QQQ": "Nasdaq 100", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum"}
KIND = {"BTC-USD": "crypto", "ETH-USD": "crypto", "SPY": "index", "QQQ": "index"}

out = []
for t, name in ASSETS.items():
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1=946684800&period2={int(time.time())}&interval=1mo"
    j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})))["chart"]["result"][0]
    months = {}
    for ts, p in zip(j["timestamp"], j["indicators"]["adjclose"][0]["adjclose"]):
        if p is None:
            continue
        d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
        months[f"{d.year}-{d.month:02d}"] = round(p, 4 if p < 10 else 2)
    keys = sorted(months)
    out.append({"t": t.replace("-USD", ""), "n": name, "k": KIND.get(t, "stock"), "s": keys[0],
                "p": [months[k] for k in keys], "last": j["meta"]["regularMarketPrice"]})
    print(f"{name}: {len(keys)} months")

with open("assets/data.js", "w") as f:
    f.write("window.POV_DATA=" + json.dumps(out, separators=(",", ":")) + ";\n")
print("Updated assets/data.js")
