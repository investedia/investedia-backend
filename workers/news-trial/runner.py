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


def decode_bundle(body, validator=validate):
    if len(body) > LIMIT:
        raise ValueError("Trial transfer exceeds 32 MiB")
    if body.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(body)) as source:
            body = source.read(EXPANDED_LIMIT + 1)
        if len(body) > EXPANDED_LIMIT:
            raise ValueError("Expanded trial state exceeds 128 MiB")
    return validator(json.loads(body))


class GenerationFailed(ValueError):
    def __init__(self, status):
        super().__init__("News generation did not report a fresh success")
        self.diagnostic = {
            "fetched": int(status.get("fetched") or 0),
            "candidates": int(status.get("candidates") or 0),
            "gemini_ok": status.get("gemini_ok") is True,
            "failed_source_count": len(status.get("failed_sources") or []),
            "http_statuses": sorted({int(code) for message in status.get("errors", []) for code in re.findall(r"HTTP\s+(\d{3})", str(message))})[:10],
        }


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
                    raise GenerationFailed(status)
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


CALENDAR_SOURCES = ("update_calendar.py", "calendar_fred.py", "calendar_official.py", "workers/news-trial/calendar_job.py")


def validate_calendar(state):
    if not isinstance(state, dict) or not isinstance(state.get("files"), dict) or set(state.get("files", {})) != {"calendar-live.json"}:
        raise ValueError("Invalid calendar trial state")
    data = state["files"]["calendar-live.json"]
    if not isinstance(data, dict) or not all(isinstance(data.get(key), list) for key in ("events", "earnings")):
        raise ValueError("Invalid saved calendar")
    return state


def run_calendar(state, base=BASE, fred_enabled=False):
    validate_calendar(state)
    started = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="calendar-trial-") as tmp:
        root = Path(tmp)
        for name in CALENDAR_SOURCES:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(base / name, target)
        (root / "assets").mkdir(exist_ok=True)
        (root / "assets/calendar-live.json").write_text(json.dumps(state["files"]["calendar-live.json"]), encoding="utf-8")
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
               "CALENDAR_UNLICENSED": "off", "FRED_API_KEY": "trial-proxy" if fred_enabled else "",
               "SSL_CERT_FILE": "/etc/cloudflare/certs/cloudflare-containers-ca.crt"}
        subprocess.run([sys.executable, str(root / "workers/news-trial/calendar_job.py")], cwd=root, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=360)
        data = json.loads((root / "assets/calendar-live.json").read_text(encoding="utf-8"))
        status = json.loads((root / "calendar-trial-status.json").read_text(encoding="utf-8"))
        if not status.get("official_events") or datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) < started.replace(microsecond=0):
            raise ValueError("No fresh official calendar result")
        result = validate_calendar({"files": {"calendar-live.json": data}})
        result["summary"] = {"trial": True, "job": "calendar", "started_at": started.isoformat(),
                             "finished_at": datetime.now(timezone.utc).isoformat(), "events": len(data["events"]),
                             "earnings": len(data["earnings"]), **status}
        return result


DATA_JOBS = ("markets", "fx", "economy-history", "country-basics")
FRONTEND = ".local/cloudflare-frontend/"
DATA_SOURCES = {
    "markets": (FRONTEND + "scripts/update_markets.py", FRONTEND + "data/registry.json"),
    "fx": (FRONTEND + "scripts/fx_ecb.py",),
    "economy-history": (FRONTEND + "scripts/economy_history.py",),
    "country-basics": ("tools/coverage/country_basics.py", "assets/globe/iso.json", "assets/globe/economy.json",
                       "data/market-country-facts.json", "assets/globe/countries-50m.json"),
}


def validate_data(state, job):
    if job not in DATA_JOBS or not isinstance(state, dict) or not isinstance(state.get("files"), dict):
        raise ValueError("Invalid data trial state")
    for name, data in state["files"].items():
        valid = name == {"markets": "markets.json", "fx": "fx-ecb.json", "country-basics": "country-basics.json"}.get(job)
        if job == "economy-history":
            valid = bool(re.fullmatch(r"[A-Z]{2,3}\.json", name))
        if not valid or not isinstance(data, dict):
            raise ValueError("Disallowed data trial file")
    if job == "markets":
        assets = state["files"].get("markets.json", {}).get("assets")
        if not isinstance(assets, list) or not assets or len(assets) > 1000:
            raise ValueError("Missing market seed")
        symbols = []
        for asset in assets:
            if not isinstance(asset, dict) or not isinstance(asset.get("s"), str) or len(asset["s"]) > 80:
                raise ValueError("Invalid market asset")
            symbols.append(asset["s"])
        if len(set(symbols)) != len(symbols):
            raise ValueError("Duplicate market asset")
    return state


def run_data(state, job, base=BASE):
    validate_data(state, job)
    started = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="data-trial-") as tmp:
        root = Path(tmp)
        for name in DATA_SOURCES[job]:
            relative = name.removeprefix(FRONTEND)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(base / name, target)
        (root / "assets/globe").mkdir(parents=True, exist_ok=True)
        (root / "docs/assets/globe").mkdir(parents=True, exist_ok=True)
        if job == "markets":
            (root / "assets/globe/markets.json").write_text(json.dumps(state["files"]["markets.json"]), encoding="utf-8")
        commands = {
            "markets": ["scripts/update_markets.py"], "fx": ["scripts/fx_ecb.py"],
            "economy-history": ["scripts/economy_history.py", "--output", "out/economy-history"],
            "country-basics": ["tools/coverage/country_basics.py", "--fetch", "--output", "out/country-basics.json"],
        }
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
               "SSL_CERT_FILE": "/etc/cloudflare/certs/cloudflare-containers-ca.crt"}
        subprocess.run([sys.executable, *commands[job]], cwd=root, env=env, check=True, timeout=900,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        paths = {"markets": [root / "assets/globe/markets.json"], "fx": [root / "assets/globe/fx-ecb.json"],
                 "country-basics": [root / "out/country-basics.json"],
                 "economy-history": list((root / "out/economy-history").glob("*.json"))}[job]
        files = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in paths}
        if not files:
            raise ValueError("No data produced")
        if job == "markets":
            data = files["markets.json"]
            if (datetime.fromisoformat(data["asof"].replace("Z", "+00:00")) < started.replace(microsecond=0)
                    or [a["s"] for a in data["assets"]] != [a["s"] for a in state["files"]["markets.json"]["assets"]]):
                raise ValueError("Stale or changed market universe")
        elif job == "fx":
            data = files["fx-ecb.json"]
            if data.get("schema") != "investedia.fx-ecb/v1" or len(data.get("usd", {})) < 20:
                raise ValueError("Incomplete ECB result")
        elif job == "country-basics":
            data = files["country-basics.json"]
            if data["refresh"]["failed_fields"] or not data["countries"]:
                raise ValueError("Incomplete country result")
        elif not {"US.json", "GB.json", "EMU.json", "WLD.json"} <= files.keys():
            raise ValueError("Incomplete history result")
        result = validate_data({"files": files}, job)
        result["summary"] = {"trial": True, "job": job, "started_at": started.isoformat(),
                             "finished_at": datetime.now(timezone.utc).isoformat(), "files": len(files),
                             "review_only": job in ("economy-history", "country-basics"), "gemini_calls": 0}
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
            query = parse_qs(url.query)
            jobs = query.get("job", ["news"])
            tiers = query.get("tier", ["priority"])
            if url.path != "/run" or len(jobs) != 1 or jobs[0] not in ("news", "calendar", *DATA_JOBS) or len(tiers) != 1 or tiers[0] not in ("priority", "broad") or not 0 < length <= LIMIT:
                raise ValueError("Invalid request")
            raw = self.rfile.read(length)
            if jobs[0] in DATA_JOBS:
                job = jobs[0]
                result = run_data(decode_bundle(raw, lambda value: validate_data(value, job)), job)
            elif jobs[0] == "calendar":
                result = run_calendar(decode_bundle(raw, validate_calendar), fred_enabled=self.headers.get("X-Fred-Enabled") == "1")
            else:
                result = run(decode_bundle(raw), tier=tiers[0])
            body = encode_bundle(result)
            self.send_response(200)
            self.send_header("X-Trial-Summary", json.dumps(result["summary"], ensure_ascii=True))
        except GenerationFailed as error:
            body = json.dumps({"error": "generation_failed", "diagnostic": error.diagnostic}).encode()
            self.send_response(422)
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
        for name in SOURCES + CALENDAR_SOURCES + tuple(name for sources in DATA_SOURCES.values() for name in sources):
            if not (BASE / name).is_file():
                raise SystemExit("Missing trial source: " + name)
        print("Offline preflight passed")
    else:
        HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
