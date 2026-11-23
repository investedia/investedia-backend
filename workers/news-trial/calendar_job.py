"""Run the existing calendar unchanged and require actual official-source results."""
import json
import contextlib
import io
import os
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        result = runpy.run_path(str(ROOT / "update_calendar.py"), run_name="__main__")
    if any(line.startswith("events failed:") for line in log.getvalue().splitlines()):
        raise SystemExit("Calendar event generation failed; trial state retained")
    official = result.get("official") or []
    if not official:
        raise SystemExit("No official calendar events fetched; trial state retained")
    report = {"official_events": len(official),
              "failed_sources": [str(row).split(":", 1)[0] for row in result.get("failed", [])],
              "fred_configured": bool(os.environ.get("FRED_API_KEY")),
              "fred_failures": len(result.get("fred_failed", []))}
    (ROOT / "calendar-trial-status.json").write_text(json.dumps(report), encoding="utf-8")
