#!/usr/bin/env python3
"""Real Estate release control (Phase 5C, owner decision 14 Nov 2026).

Two outputs, never mixed:
  PREVIEW  assets/globe/projects-realestate-preview.json  - every qualifying research record (photo OR development plan,
           documented ticker, verified site/address/city point), each marked "Preview - not approved", with any owner hold.
  RELEASE  assets/globe/projects-realestate.json          - ONLY records whose owner_approval in
           data/realestate/phase5b/approval-manifest.json is {"approved": true, ...} with a matching fact_sha256 and no hold.
Passing the importer or having a verified photo never puts a record into RELEASE.
validate_release() fails (exit 1) if any record in the release file is not individually approved.
Usage: release_build.py <frontend repo> [--check-only]
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
P5 = ROOT / 'data/realestate/phase5b'

def load():
    man = json.loads((P5 / 'approval-manifest.json').read_text())
    holds = json.loads((P5 / 'holds.json').read_text())
    return man, holds

def approved_ids(man, holds):
    ok = {}
    for r in man['records']:
        a = r.get('owner_approval')
        if isinstance(a, dict) and a.get('approved') is True and a.get('date') and r['id'] not in holds['holds']:
            ok[r['id']] = r['fact_sha256']
    return ok

def validate_release(doc, man, holds):
    """Every record in a release document must be individually owner-approved, unchanged since approval, and not held."""
    errors = []
    if doc.get('schema') != 'investedia.projects.realestate.v1' or doc.get('preview') is not False:
        errors.append('release file must be schema investedia.projects.realestate.v1 with preview=false')
    ok = approved_ids(man, holds); facts = {r['id']: r['fact_sha256'] for r in man['records']}
    for p in doc.get('projects', []):
        if p['id'] not in facts: errors.append(f"{p['id']}: not in the approval manifest")
        elif p['id'] in holds['holds']: errors.append(f"{p['id']}: on owner hold ({holds['holds'][p['id']]['type']})")
        elif p['id'] not in ok: errors.append(f"{p['id']}: not approved by the owner")
        elif p.get('fact_sha256') != ok[p['id']]: errors.append(f"{p['id']}: record changed since approval (fact_sha256 mismatch)")
        if p.get('release_status') != 'approved': errors.append(f"{p['id']}: release_status must be 'approved'")
    if doc.get('count') != len(doc.get('projects', [])): errors.append('count does not match projects')
    return errors

def build(fe):
    man, holds = load()
    prev = json.loads((fe / 'assets/globe/projects-realestate-preview.json').read_text())
    ok = approved_ids(man, holds); facts = {r['id']: r['fact_sha256'] for r in man['records']}
    rel = [dict(p, release_status='approved', fact_sha256=facts[p['id']]) for p in prev['projects'] if p['id'] in ok]
    doc = {'schema': 'investedia.projects.realestate.v1', 'as_of': prev['as_of'], 'preview': False, 'count': len(rel),
           'note': 'RELEASE: only records individually approved by the owner in approval-manifest.json', 'credit': prev['credit'], 'projects': rel}
    errs = validate_release(doc, man, holds)
    if errs: print('\n'.join(errs)); sys.exit(1)
    for d in ('assets/globe', 'docs/assets/globe'):
        (fe / d / 'projects-realestate.json').write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')))
    return doc

if __name__ == '__main__':
    fe = Path(sys.argv[1]); man, holds = load()
    if '--check-only' in sys.argv:
        errs = validate_release(json.loads((fe / 'assets/globe/projects-realestate.json').read_text()), man, holds)
        print('\n'.join(errs) or 'release file valid'); sys.exit(1 if errs else 0)
    doc = build(fe); print(f"release: {doc['count']} approved records (manifest approvals: {len(approved_ids(man, holds))})")
