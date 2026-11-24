"""Build compatible listings from the static catalog and already-published canonical articles only."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import urllib.request

BASELINE = Path(__file__).resolve().parents[2] / ".local/cloudflare-library-index"
ID = re.compile(r"[A-Za-z0-9_-]{4,80}")
MAX_FILE = 32 * 1024 * 1024
# shortcut: 100,000 rows / 32 MiB per export; use streaming exports before the catalog reaches this bound.
MAX_ROWS = 100000


def dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def fetch_input(path, limit):
    try:
        with urllib.request.urlopen("http://article-store/" + path, timeout=60) as response:
            body = response.read(limit + 1)
    except urllib.error.HTTPError as error:
        if path == "index-state.json.gz" and error.code == 404:
            return None
        raise
    if len(body) > limit:
        raise ValueError("Index input too large")
    return body


def build_index(seed, baseline=BASELINE, fetch=fetch_input):
    ids = seed.get("ids") if isinstance(seed, dict) else None
    if not isinstance(ids, list) or len(ids) > MAX_ROWS or any(not isinstance(i, str) or not ID.fullmatch(i) for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Invalid published article IDs")
    info = json.loads((baseline / "baseline.json").read_bytes())
    raw = (baseline / "all.json").read_bytes()
    if len(raw) > MAX_FILE or hashlib.sha256(raw).hexdigest() != info["catalog_sha256"]:
        raise ValueError("Static catalog checksum mismatch")
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("Invalid static catalog")
    known = {r["id"] for r in rows}
    if len(known) != len(rows):
        raise ValueError("Duplicate static article IDs")
    spec = importlib.util.spec_from_file_location("original_frontend_index", baseline / "news_library_index.py")
    original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
    by = {}
    for name in info["shards"]:
        if not re.fullmatch(r"tick-[A-Z_]\.json", name):
            raise ValueError("Invalid baseline shard")
        shard = json.loads((baseline / name).read_bytes())
        for symbol, links in shard.items():
            if symbol in by:
                raise ValueError("Duplicate baseline ticker")
            by[symbol] = links
    previous = fetch("index-state.json.gz", MAX_FILE)
    extras = {}
    if previous is not None:
        # Read the bounded state in the 1 GiB Container, never expand it in the Worker.
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(previous)) as source:
            body = source.read(128 * 1024 * 1024 + 1)
        if len(body) > 128 * 1024 * 1024:
            raise ValueError("Index state too large")
        saved = json.loads(body)
        if saved.get("baseline_sha256") == info["catalog_sha256"]:
            extras = saved["extras"]
    pending = sorted(set(ids) - known)
    if len(rows) + len(pending) > MAX_ROWS:
        raise ValueError("Catalog needs a larger indexing job")
    if set(extras) - set(ids) - known:
        raise ValueError("Published archive unexpectedly lost articles")
    extras = {sid: extras[sid] for sid in pending if sid in extras}
    for sid in pending:
        if sid in extras:
            continue
        article = json.loads(fetch("library/" + sid + ".json", 512 * 1024))
        if (not isinstance(article, dict) or article.get("id") != sid or not article.get("headline") or not article.get("published_at")
                or not isinstance(article.get("source"), dict) or not isinstance(article.get("location"), dict) or article.get("demo")):
            raise ValueError("Invalid published article")
        symbols = {str(x.get("ticker") or x.get("sym") or "").upper()
                   for x in (article.get("impacts") or []) + (article.get("entities") or []) if isinstance(x, dict)} - {""}
        if any(len(s) > 80 or (s[0].isalpha() and s[0] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ") for s in symbols):
            raise ValueError("Unsupported ticker shard")
        extras[sid] = {"row": original.row(article), "tickers": sorted(symbols)}
    for sid in pending:
        entry = extras[sid]; r = entry["row"]
        if r.get("id") != sid:
            raise ValueError("Invalid saved index row")
        rows.append(r)
        for symbol in entry["tickers"]:
            by.setdefault(symbol, []).append([r["id"], r["h"], r["t"], r["s"] or ""])
    rows.sort(key=lambda r: (r["t"], r["id"]), reverse=True)
    cats, regions = {}, {}
    for r in rows:
        cats[r["c"]] = cats.get(r["c"], 0) + 1
        if r["g"]:
            regions[r["g"]] = regions.get(r["g"], 0) + 1
    meta = {"total": len(rows), "sources": len({(r["s"] or "").strip().lower() for r in rows if r["s"]}),
            "first": rows[-1]["t"] if rows else None, "per_page": 24, "pages": max(1, (len(rows) + 23) // 24),
            "categories": dict(sorted(cats.items(), key=lambda x: -x[1])), "regions": regions,
            "catalog_sha256": info["catalog_sha256"]}
    encoded = [dump(r) for r in rows]
    all_rows = b"[" + b",".join(encoded) + b"]"
    objects = {"all.json": all_rows, "meta.json": dump(meta)}
    shards = {}
    for symbol, links in by.items():
        # Stable sort retains the original link order for equal publication dates.
        links.sort(key=lambda r: r[2], reverse=True)
        shards.setdefault(symbol[0] if symbol[0].isalpha() else "_", {})[symbol] = links[:30]
    for k, value in shards.items():
        objects["tick-" + k + ".json"] = dump(value)
    offset = 1; pages = []
    for start in range(0, len(encoded), 24):
        length = sum(map(len, encoded[start:start + 24])) + len(encoded[start:start + 24]) - 1
        if length > 512 * 1024:
            raise ValueError("Index page too large")
        pages.append([offset, length]); offset += length + 1
    if not pages:
        pages = [[1, 0]]
    if any(len(body) > MAX_FILE for body in objects.values()):
        raise ValueError("Index export too large")
    files = {name: {"size": len(body), "sha256": hashlib.sha256(body).hexdigest()} for name, body in objects.items()}
    version = hashlib.sha256(dump(files)).hexdigest()
    manifest = {"version": version, "baseline_sha256": info["catalog_sha256"], "files": files, "pages": pages}
    objects["manifest.json"] = dump(manifest)
    objects["state.json.gz"] = gzip.compress(dump({"baseline_sha256": info["catalog_sha256"], "extras": extras}), mtime=0)
    if len(objects["manifest.json"]) > 256 * 1024 or len(objects["state.json.gz"]) > MAX_FILE:
        raise ValueError("Index control export too large")
    return objects, {"job": "library-index", "articles": len(rows), "added": len(extras), "version": version, "gemini_calls": 0}
