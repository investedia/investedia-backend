"""Run the unchanged priority producer in disposable storage; never publish."""
import argparse
import gzip
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, parse_qs
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE = Path(__file__).resolve().parents[2]
LIMIT = 32 * 1024 * 1024
EXPANDED_LIMIT = 128 * 1024 * 1024
STATE_NAMES = {"news-live.json", "news-archive.json", "news-48h.json", "news-seen.json",
               "news-status.json", "threads.json", "photos/index.json", "photos/blocked.json"}
SOURCES = ("update_globe_news.py", "news_core.py", "registry.py", "events.py", "tools/news_library.py",
           "tools/globe-news/connections.py", "tools/globe-news/iso.json", "tools/globe-news/wb-countries.json",
           "data/registry.json", "assets/quotes.js", "assets/globe/countries-50m.json",
           "assets/globe/iso.json", "assets/globe/markets.json", "assets/globe/projects.json")


def allowed(name):
    return name in STATE_NAMES or bool(re.fullmatch(r"events/[0-9]{4}-[0-9]{2}-[0-9]{2}\.json|library/[A-Za-z0-9_-]+\.json", name))


def validate(state):
    if not isinstance(state, dict) or not isinstance(state.get("files"), dict):
        raise ValueError("Invalid trial state")
    for name, value in state["files"].items():
        if not allowed(name) or not isinstance(value, (dict, list)):
            raise ValueError("Disallowed trial state file")
    for name in ("news-live.json", "news-archive.json", "news-seen.json", "news-status.json", "photos/index.json"):
        if name not in state["files"]:
            raise ValueError("Missing required trial state")
    for name in ("news-live.json", "news-archive.json"):
        feed = state["files"][name]
        if not isinstance(feed, dict) or not isinstance(feed.get("stories"), list):
            raise ValueError("Invalid saved feed")
    return state


def pack(root, include_library=True):
    g = root / "assets/globe"
    paths = [g / name for name in STATE_NAMES if (g / name).is_file()]
    paths += list((g / "events").glob("*.json"))
    if include_library:
        paths += list((g / "library").glob("*.json"))
    files = {f.relative_to(g).as_posix(): json.loads(f.read_text(encoding="utf-8")) for f in paths}
    return validate({"files": files})


def encode_bundle(value):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    if len(raw) > EXPANDED_LIMIT:
        raise ValueError("Expanded trial state exceeds 128 MiB")
    body = gzip.compress(raw, compresslevel=6, mtime=0)
    if len(body) > LIMIT:
        raise ValueError("Compressed trial state exceeds 32 MiB")
    return body


def decode_bundle(body):
    if len(body) > LIMIT:
        raise ValueError("Trial transfer exceeds 32 MiB")
    if body.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(body)) as source:
            body = source.read(EXPANDED_LIMIT + 1)
        if len(body) > EXPANDED_LIMIT:
            raise ValueError("Expanded trial state exceeds 128 MiB")
    return validate(json.loads(body))


def run(state, base=BASE, tier="priority"):
    if tier not in ("priority", "broad"):
        raise ValueError("Unknown news tier")
    validate(state)
    # Caller cannot supply commands, environment variables, URLs or filesystem paths.
    with tempfile.TemporaryDirectory(prefix="news-trial-") as tmp:
        root = Path(tmp)
        for name in SOURCES:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(base / name, target)
        g = root / "assets/globe"
        (root / "docs/assets/globe").mkdir(parents=True)
        for name, value in state["files"].items():
            target = g / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        started = datetime.now(timezone.utc)
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
               "NEWS_TIER": tier, "GEMINI_API_KEY": "trial-proxy", "PIXABAY_KEY": "",
               "SSL_CERT_FILE": "/etc/cloudflare/certs/cloudflare-containers-ca.crt"}
        # Never relay producer logs: upstream errors can include request details.
        for script in ("update_globe_news.py", "tools/globe-news/connections.py"):
            subprocess.run([sys.executable, str(root / script)], cwd=root, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=720)
            if script == "update_globe_news.py":
                status = json.loads((g / "news-status.json").read_text(encoding="utf-8"))
                tier_status = status.get("tiers", {}).get(tier, {})
                success = tier_status.get("last_success")
                if (not success or success != status.get("ran_at") or success != tier_status.get("last_run")
                        or datetime.fromisoformat(success.replace("Z", "+00:00")) < started.replace(microsecond=0)):
                    raise ValueError("News generation did not report a fresh success")
                if not status.get("fetched"):
                    raise ValueError("No sources fetched; trial cannot count as a successful comparison")
        result = pack(root)
        result["connections"] = json.loads((g / "connections.json").read_text(encoding="utf-8"))
        result["summary"] = {"trial": True, "tier": tier, "started_at": started.isoformat(),
                             "finished_at": datetime.now(timezone.utc).isoformat(),
                             "articles": len(result["files"]["news-live.json"]["stories"]),
                             "failed_sources": status.get("failed_sources", []),
                             "new_articles": status.get("new_stories", 0)}
        return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            url = urlsplit(self.path)
            tiers = parse_qs(url.query).get("tier", ["priority"])
            if url.path != "/run" or len(tiers) != 1 or tiers[0] not in ("priority", "broad") or not 0 < length <= LIMIT:
                raise ValueError("Invalid request")
            result = run(decode_bundle(self.rfile.read(length)), tier=tiers[0])
            body = encode_bundle(result)
            self.send_response(200)
            self.send_header("X-Trial-Summary", json.dumps(result["summary"], ensure_ascii=True))
        except Exception:
            body = b'{"error":"Trial failed; previous trial state retained"}'
            self.send_response(422)
        self.send_header("Content-Type", "application/gzip" if body.startswith(b"\x1f\x8b") else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, help="Write a seed locally; no uploads or network calls")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.pack:
        try:
            body = encode_bundle(pack(BASE, include_library=False))
        except ValueError as error:
            raise SystemExit(str(error))
        args.pack.write_bytes(body)
        print("Wrote compressed trial seed locally:", len(body), "bytes; no articles generated or published")
    elif args.preflight:
        for name in SOURCES:
            if not (BASE / name).is_file():
                raise SystemExit("Missing trial source: " + name)
        print("Offline preflight passed")
    else:
        HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
