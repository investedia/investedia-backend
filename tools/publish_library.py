"""Publish the article library to the website (owner, 15 Nov 2026).

The news robot only sends its newest articles to the live news service, so the website's article library
(investedia-frontend assets/globe/library) was a one-time snapshot that stopped at 7 Nov 2026.
After every robot run, the publish-library workflow calls this script to copy each full article the robot
holds (news-live, news-48h, news-archive) into the website checkout, rebuild the library index pages and
refresh the homepage totals in site-stats.json. Existing articles are never changed or removed.

Usage: python tools/publish_library.py --frontend ../frontend [--check]
  --check  report what would be added without writing anything.
"""
import argparse, json, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FEEDS = ('news-live.json', 'news-48h.json', 'news-archive.json')
SAFE_ID = re.compile(r'^[A-Za-z0-9_-]{4,80}$')
REQUIRED = ('id', 'headline', 'published_at', 'location', 'source')


def robot_stories(root=ROOT):
    """Full articles the robot currently holds, newest copy of each id wins. Demo or incomplete rows are skipped."""
    out = {}
    for name in FEEDS:
        p = root / 'assets/globe' / name
        try: data = json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        if data.get('demo'): continue
        for s in data.get('stories') or []:
            if not isinstance(s, dict) or s.get('demo') or any(not s.get(k) for k in REQUIRED): continue
            if not SAFE_ID.match(str(s['id'])): continue
            out.setdefault(s['id'], s)
    return out


def publish(frontend, stories, check=False):
    """Write articles that the website does not have yet. Returns the ids added."""
    lib = frontend / 'assets/globe/library'
    mirrors = [lib] + ([frontend / 'docs/assets/globe/library'] if (frontend / 'docs/assets/globe').is_dir() else [])
    have = {p.stem for p in lib.glob('*.json')} if lib.is_dir() else set()
    new = sorted(sid for sid in stories if sid not in have)
    if check: return new
    for d in mirrors: d.mkdir(parents=True, exist_ok=True)
    for sid in new:
        body = json.dumps(stories[sid], ensure_ascii=False, separators=(',', ':'))
        for d in mirrors: (d / f'{sid}.json').write_text(body, encoding='utf-8')
    return new


def site_stats(frontend, meta):
    """Homepage totals from the published library (what visitors can open); projects count kept as it was."""
    for base in ('assets/globe', 'docs/assets/globe'):
        p = frontend / base / 'site-stats.json'
        if not p.parent.is_dir(): continue
        try: cur = json.loads(p.read_text(encoding='utf-8'))
        except Exception: cur = {}
        cur.update({'articles': meta['total'], 'sources': meta['sources']})
        p.write_text(json.dumps(cur, separators=(',', ':')), encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--frontend', required=True, type=pathlib.Path)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    fe = a.frontend.resolve()
    if not (fe / 'tools/news_library_index.py').is_file(): sys.exit(f'not a website checkout: {fe}')
    stories = robot_stories()
    new = publish(fe, stories, check=a.check)
    dates = sorted(stories[s]['published_at'] for s in new)
    print(json.dumps({'robot_articles': len(stories), 'new_on_site': len(new), 'first_new': dates[0] if dates else None, 'last_new': dates[-1] if dates else None, 'check': a.check}))
    if a.check or not new: return 0
    out = subprocess.run([sys.executable, 'tools/news_library_index.py'], cwd=fe, check=True, capture_output=True, text=True).stdout
    print(out.strip())
    meta = json.loads((fe / 'assets/globe/library-index/meta.json').read_text(encoding='utf-8'))
    site_stats(fe, meta)
    return 0


if __name__ == '__main__':
    sys.exit(main())
