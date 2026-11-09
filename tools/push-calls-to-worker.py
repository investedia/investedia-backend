"""Sends the live call ledger (assets/globe/v5-ledger.json) to the Cloudflare Worker (POST /v1/ingest/calls) so visitors see new calls
within seconds, without waiting for a commit and a Pages deploy. Git stays the permanent record. Never fails the run."""
import json, os, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
url, token = (os.environ.get('WORKER_URL', '').strip() or 'https://investedia-live.adonaykabeya10.workers.dev').rstrip('/'), os.environ.get('NEWS_INGEST_TOKEN', '').strip()
if not url or not token: print('worker calls ingest not configured: skipped'); sys.exit(0)
try:
    body = open(os.path.join(ROOT, 'assets', 'globe', 'v5-ledger.json'), 'rb').read()
    req = urllib.request.Request(url + '/v1/ingest/calls', data=body, method='POST', headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token, 'User-Agent': 'InvestediaRobot/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r: print('worker calls ingest:', r.read()[:200].decode())
except Exception as e: print('worker calls ingest failed (git path unaffected):', str(e)[:200])
