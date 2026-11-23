"""Stage only pinned, committed frontend job inputs; never copy working-tree secrets."""
import argparse
import json
from pathlib import Path
import subprocess

COMMIT = "2402119767e01574d478e3df72398bba21ffc132"
FILES = ("scripts/update_markets.py", "scripts/fx_ecb.py", "scripts/economy_history.py", "data/registry.json")
DEST = Path(__file__).resolve().parents[2] / ".local/cloudflare-frontend"


def stage(checkout, destination=DEST):
    def git(*args):
        return subprocess.run(["git", "-c", "safe.directory=" + str(checkout.resolve()), "-C", str(checkout), *args],
                              capture_output=True, check=True).stdout
    blobs = {}
    for name in FILES:
        obj = COMMIT + ":" + name
        if git("ls-tree", COMMIT, "--", name).split()[0] != b"100644":
            raise ValueError("Expected a regular committed source")
        body = git("show", obj)
        if len(body) > 8 * 1024 * 1024:
            raise ValueError("Unexpectedly large source")
        if name.endswith(".py"):
            compile(body, name, "exec")
        else:
            json.loads(body)
        blobs[name] = body
    for name, body in blobs.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    print("Staged four pinned public source files; no credentials or working-tree files copied")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    stage(parser.parse_args().checkout)
