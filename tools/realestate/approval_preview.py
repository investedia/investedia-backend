#!/usr/bin/env python3
"""Generate the owner's visual approval preview directly from data/realestate/phase5b/approval-manifest.json.

Output: data/realestate/phase5b/approval-preview.html (+ approval-photos/). Opens locally in a browser; no server needed.
Shows per record: name/location, verified photo (licence, attribution, year) or development plan, listed company and
relationship, status, evidence links, coordinate precision, owner holds and unresolved issues, and the approval field
exactly as stored (null = not approved). The page cannot approve anything; approvals are made only in the manifest.
Usage: approval_preview.py <frontend repo>
"""
import html, json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; FE = Path(sys.argv[1]); P5 = ROOT / 'data/realestate/phase5b'
man = json.loads((P5 / 'approval-manifest.json').read_text()); prev = {p['id']: p for p in json.loads((FE / 'assets/globe/projects-realestate-preview.json').read_text())['projects']}
holds = json.loads((P5 / 'holds.json').read_text())
(P5 / 'approval-photos').mkdir(exist_ok=True)
E = html.escape
EXCH = {'XNYS': 'NYSE', 'XNAS': 'Nasdaq'}
cards, n_issue = [], 0
for r in man['records']:
    rid = r['id']; pv = prev.get(rid, {}); ph = next((q for q in r['qualifies_by'] if q['type'] == 'verified_photograph'), None); pl = next((q for q in r['qualifies_by'] if q['type'] == 'development_plan'), None)
    hold = r.get('hold'); keep = holds['retained_historical_photos'].get(rid)
    media = '<div class="ph"><span><i></i>No licensed photo or rendering<br>Qualifies by documented development plan</span></div>'
    if ph and pv.get('photo'):
        fn = pv['photo']['file'].split('/')[-1]; shutil.copyfile(FE / 'assets/img/projects/photo' / fn, P5 / 'approval-photos' / fn)
        credit = (keep or {}).get('credit_override') or ph['author_credit'].split(' / ')[0]
        year = (keep or {}).get('label') or (('Photo ' + ph['capture_date'][:4]) if (ph.get('capture_date') or '')[:4].isdigit() else 'capture date not recorded')
        media = f'<img src="approval-photos/{E(fn)}" alt=""><div class="cap">Photo: {E(credit)} · {E(ph["licence"])} · {E(year)} · <a href="{E(ph["file_page"])}">Wikimedia Commons</a></div>'
    elif ph:
        media = '<div class="ph"><span><i></i>Photo withheld (owner hold)</span></div>'
    st = (pv.get('stage') or {'under_construction': 'Under construction', 'completed': 'Completed'}.get((pl or {}).get('stage'), 'Operating'))
    cls = 't-done' if 'Completed' in st else 't-uc' if ('construction' in st or 'Redevelopment' in st) else 't-op'
    c = r['coordinates']['class']; dot = 'd-b' if c.startswith('Building') else 'd-a' if 'address' in c else 'd-c'
    rel = r['relationship']; co = r['company']
    ev = [rel['evidence']] + ([pl['evidence']] if pl and pl['evidence']['url'] != rel['evidence']['url'] else [])
    evh = ' · '.join(f'<a href="{E(e["url"])}">{"SEC 10-Q (Q3 2026)" if "20260930" in e["url"] else "SEC 10-K (FY2025)" if "sec.gov" in e["url"] else E(e["url"].rsplit("/", 1)[-1][:30])}</a> <small>sha256 {e["sha256"][:10]}…</small>' for e in ev)
    issues = [b for b in r['blockers'] if not b.startswith('Owner approval')]
    if issues: n_issue += 1
    lic = ' · '.join(f'{k}: {v["status"]}' for k, v in r['licensing'].items())
    cards.append(f'''<article class="card{' held' if hold else ''}" data-hold="{1 if hold else 0}" data-kind="{'photo' if ph else 'plan'}"><div class="media">{media}</div><div class="body"><div class="top"><div><h2 class="name">{E(r['name'])}</h2><div class="loc">{E(r.get('address') or pv.get('country') or '')}</div></div><span class="tag {cls}">{E(st)}</span></div>
<dl><dt>Listed company</dt><dd><span class="tk">{E(co['ticker'])}</span>{E(co['name'].title().replace(', Inc.', ', Inc.'))} · {EXCH.get(co['exchange'], co['exchange'])}</dd><dt>Relationship</dt><dd>{E(rel['label'])}{f" · stated share {rel['stated_share_pct']}%" if rel['stated_share_pct'] is not None else ''}<br><small>{E(rel['scope'])}</small></dd>
{f"<dt>Development</dt><dd>{E(pl['statement'])}</dd>" if pl else ''}<dt>Location</dt><dd><span class="prec"><span class="dot {dot}"></span>{E(c)}</span><br><small>{E(r['coordinates']['basis'] or '')}</small></dd>
<dt>Field reuse</dt><dd><small>{E(lic)}</small></dd><dt>Attribution</dt><dd><small>{'<br>'.join(E(a) for a in r['attribution'])}</small></dd></dl></div>
<div class="ev">Evidence: {evh}</div>
{f'<div class="issues{" hold" if hold else ""}"><b>{"On hold" if hold else "Unresolved"}</b>{"<br>".join(E(i) for i in issues)}</div>' if issues else '<div class="none">No unresolved issues found</div>'}
<div class="appr"><span class="st">owner_approval: <b>{E(json.dumps(r['owner_approval']))}</b> {'(not approved)' if r['owner_approval'] is None else ''}</span><span class="fp">fact {r['fact_sha256'][:12]}</span></div></article>''')
tpl = (ROOT / 'tools/realestate/approval_preview_template.html').read_text()
head = tpl[:tpl.index('<main')]
head = head.replace('<b>0 / 20</b>', f'<b>{sum(1 for r in man["records"] if r["owner_approval"])} / {len(man["records"])}</b>').replace('<b id="kIss">–</b>', f'<b>{n_issue}</b>')
head = head.replace('<span class="chip on">All 20</span><span class="chip">Open issues</span><span class="chip">Photo</span><span class="chip">Development</span><span class="chip">Building point</span><span class="chip">Address point</span>',
                    '<button class="chip on" data-f="all">All 20</button><button class="chip" data-f="hold">On hold</button><button class="chip" data-f="photo">Photo</button><button class="chip" data-f="plan">Development</button>')
css = '<style>.card[hidden]{display:none!important}.card.held{opacity:.8}.issues.hold{background:rgba(248,113,113,.07);border-color:rgba(248,113,113,.3);color:#fecaca}.issues.hold b{color:#f87171}.chip{cursor:pointer;font:inherit}.fp{margin-left:auto;color:var(--fg3);font:11px ui-monospace,monospace}.cap a{color:inherit}dd small{color:var(--fg3)}.ev small{color:var(--fg3)}</style>'
js = "document.querySelectorAll('[data-f]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-f]').forEach(x=>x.classList.toggle('on',x===b));const f=b.dataset.f;document.querySelectorAll('.card').forEach(c=>c.hidden=!(f==='all'||(f==='hold'&&c.dataset.hold==='1')||c.dataset.kind===f));});"
out = head + css + f'<main id="m">{"".join(cards)}<p class="note">Generated from approval-manifest.json ({man["created"]}). This page cannot approve anything: approvals are recorded only by the owner in the manifest (owner_approval). Facts: SEC filings. Locations: US Census (public domain), Wikidata (CC0).</p></main><script>{js}</script></body></html>'
(P5 / 'approval-preview.html').write_text(out)
print(len(cards), 'cards;', n_issue, 'with issues/holds')
