"""Permanent article library: every story the robot publishes is kept as assets/globe/library/<id>.json (and the docs mirror),
so story.html can open any article ever published, not only the ones still in the 7-day feed / 600-story archive.
store(stories) is called by update_globe_news.py; `python3 tools/news_library.py --backfill` rebuilds from git history."""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = [os.path.join(ROOT, 'assets', 'globe', 'library'), os.path.join(ROOT, 'docs', 'assets', 'globe', 'library')]

def store(stories):
    n = 0
    for d in DIRS: os.makedirs(d, exist_ok=True)
    for s in stories:
        sid = str(s.get('id') or '')
        if not sid or not sid.replace('-', '').replace('_', '').isalnum() or s.get('demo'): continue
        body = json.dumps(s, ensure_ascii=False, separators=(',', ':'))
        for d in DIRS:
            p = os.path.join(d, sid + '.json')
            try:
                if open(p, encoding='utf-8').read() == body: continue
            except FileNotFoundError: pass
            open(p, 'w', encoding='utf-8').write(body); n += 1
    return n

def backfill():
    seen = {}
    for f in ('assets/globe/news-archive.json', 'assets/globe/news-live.json'):
        revs = subprocess.run(['git', 'log', '--format=%H', '--', f], cwd=ROOT, capture_output=True, text=True).stdout.split()
        for r in reversed(revs):  # oldest first, so later versions of a story win
            try: d = json.loads(subprocess.run(['git', 'show', f'{r}:{f}'], cwd=ROOT, capture_output=True, text=True).stdout)
            except Exception: continue
            for s in d.get('stories', []):
                if s.get('id'): seen[s['id']] = s
        print(f, len(revs), 'revisions', len(seen), 'stories so far', flush=True)
    print('written', store(list(seen.values())))

if __name__ == '__main__' and '--backfill' in sys.argv: backfill()
