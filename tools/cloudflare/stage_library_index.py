"""Stage a committed frontend catalog and its original row projection, without working-tree files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

DEST = Path(__file__).resolve().parents[2] / ".local/cloudflare-library-index"


def stage(checkout, commit, destination=DEST):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("An exact reviewed frontend commit is required")
    def git(*args):
        return subprocess.run(["git", "-c", "safe.directory=" + str(checkout.resolve()), "-C", str(checkout), *args],
                              capture_output=True, check=True).stdout
    prefix = "assets/globe/library-index/"
    names = git("ls-tree", "--name-only", commit + ":assets/globe/library-index").decode().splitlines()
    shards = [n for n in names if re.fullmatch(r"tick-[A-Z_]\.json", n)]
    if any(n.startswith("tick-") and n not in shards for n in names):
        raise ValueError("Unexpected ticker shard")
    files = ["tools/news_library_index.py", prefix + "all.json", prefix + "meta.json"] + [prefix + n for n in shards]
    blobs = {}
    for name in files:
        if git("ls-tree", commit, "--", name).split()[0] != b"100644":
            raise ValueError("Expected a regular committed catalog file")
        body = git("show", commit + ":" + name)
        if len(body) > 32 * 1024 * 1024:
            raise ValueError("Catalog file exceeds transport limit")
        if name.endswith(".py"):
            compile(body, name, "exec")
        else:
            json.loads(body)
        blobs[Path(name).name] = body
    if sum(map(len, blobs.values())) > 64 * 1024 * 1024:
        raise ValueError("Catalog baseline too large")
    meta = json.loads(blobs["meta.json"])
    if meta.get("total") != len(json.loads(blobs["all.json"])) or meta.get("per_page") != 24:
        raise ValueError("Inconsistent static catalog")
    manifest = {"commit": commit, "catalog_sha256": hashlib.sha256(blobs["all.json"]).hexdigest(), "shards": shards}
    destination.mkdir(parents=True, exist_ok=True)
    for name, body in blobs.items():
        (destination / name).write_bytes(body)
    (destination / "baseline.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--commit", required=True)
    print(json.dumps(stage(**vars(parser.parse_args()))))
