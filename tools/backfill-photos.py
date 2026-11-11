"""One-time, manual top-up of the Pixabay topic-photo pool (owner request, 11 Nov 2026).

Downloads more licensed Pixabay photos (Pixabay Content License, photographer credited) for the robot's
40 topics and 30 extra backfill topics, up to PER_TOPIC each, with exactly the live robot's rules:
professional photographs only (same NOT_PHOTO filter and blocked.json ids), resized to at most 1200x800,
JPEG quality 78, file name <topic-slug>-<pixabay-id>.jpg, index entry {file, credit, source_url, alt}.

Writes only into --output: photos/*.jpg (new files) and index.json (old entries kept, new appended).
Nothing is published by this tool: the photos go to the frontend through a reviewed pull request first,
and only then the backend index is updated, so no article ever points at a missing file.
Importing is offline; network use is limited to pixabay.com and cdn.pixabay.com.
"""
import argparse
import importlib.util
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import update_globe_news as robot

PER_TOPIC = 30
API = 'https://pixabay.com/api/'
HOSTS = {'pixabay.com', 'cdn.pixabay.com'}
# Backfill-only topics: thin regions and sectors the 40 live topics do not cover. The live robot keeps its own list.
EXTRA_TOPICS = [
    'middle east city skyline', 'desert oil field', 'mosque city skyline', 'african market', 'african city skyline',
    'tea plantation', 'cocoa beans', 'caribbean harbour', 'tropical island resort', 'fishing boats harbour',
    'central bank building', 'stock exchange building', 'asian city skyline', 'rice field', 'textile factory',
    'shipping containers yard', 'power plant', 'hydroelectric dam', 'water treatment plant', 'railway construction',
    'highway bridge construction', 'warehouse logistics', 'cattle ranch', 'vineyard grapes', 'palm oil plantation',
    'cotton field', 'eastern europe city', 'mediterranean port', 'mountain mining site', 'pacific island coast']
TOPICS = list(dict.fromkeys(robot.PHOTO_TOPICS + EXTRA_TOPICS))
UA = 'InvestediaPhotos/1.0 (+https://investedia.com)'


def get(url, timeout=60, limit=25_000_000):
    u = urlsplit(url)
    if u.scheme != 'https' or u.hostname not in HOSTS: raise ValueError('pixabay_hosts_only')
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=timeout) as r:
        body = r.read(limit + 1)
    if len(body) > limit: raise ValueError('image_too_large')
    return body


def slug(topic): return re.sub(r'[^a-z0-9]+', '-', topic)


def resize(raw):
    from PIL import Image
    im = Image.open(io.BytesIO(raw)).convert('RGB'); im.thumbnail((1200, 800))
    out = io.BytesIO(); im.save(out, 'JPEG', quality=78, optimize=True, progressive=True)
    return out.getvalue()


def top_up(topic, entries, hits, blocked, fetch, save, per_topic=PER_TOPIC):
    """Adds photos for one topic until per_topic; returns (entries, added, skipped reasons)."""
    entries = list(entries); have = {e['file'] for e in entries}; added = 0; skipped = {}
    for h in hits:
        if len(entries) >= per_topic: break
        def skip(reason): skipped[reason] = skipped.get(reason, 0) + 1
        if not isinstance(h, dict) or not h.get('largeImageURL') or not h.get('id'): skip('invalid_hit'); continue
        if str(h['id']) in blocked: skip('blocked_id'); continue
        if robot.NOT_PHOTO.search(str(h.get('tags', ''))): skip('not_a_photograph'); continue
        name = f"{slug(topic)}-{h['id']}.jpg"; file = f'photos/{name}'
        if file in have: skip('already_in_pool'); continue
        try: save(name, resize(fetch(h['largeImageURL'])))
        except Exception: skip('download_or_image_error'); continue
        entries.append({'file': file, 'credit': str(h.get('user') or 'Pixabay')[:80], 'source_url': h.get('pageURL'), 'alt': topic})
        have.add(file); added += 1
    return entries, added, skipped


def run(key, index_path, blocked_path, output, per_topic=PER_TOPIC, fetch=get, sleep=time.sleep):
    if not key: raise ValueError('PIXABAY_KEY_required')
    index = json.loads(Path(index_path).read_text())
    blocked = {str(i) for i in json.loads(Path(blocked_path).read_text()).get('ids', [])} if Path(blocked_path).exists() else set()
    out = Path(output); (out/'photos').mkdir(parents=True, exist_ok=True)
    def save(name, data): (out/'photos'/name).write_bytes(data)
    report = {'per_topic': per_topic, 'topics': {}, 'added': 0, 'notice': 'Pixabay Content License; photographer credited per photo.'}
    for topic in TOPICS:
        entries = index.get(topic) or []
        if len(entries) >= per_topic: report['topics'][topic] = {'had': len(entries), 'added': 0}; continue
        sleep(1.0)  # Pixabay allows 100 requests a minute; one a second stays well inside it
        q = urllib.parse.urlencode({'key': key, 'q': topic, 'image_type': 'photo', 'orientation': 'horizontal',
                                    'safesearch': 'true', 'per_page': 100, 'min_width': 1200})
        try: hits = json.loads(fetch(API + '?' + q)).get('hits', [])
        except Exception: report['topics'][topic] = {'had': len(entries), 'added': 0, 'error': 'search_failed'}; continue
        new, added, skipped = top_up(topic, entries, hits, blocked, fetch, save, per_topic)
        index[topic] = new; report['added'] += added
        report['topics'][topic] = {'had': len(entries), 'added': added, 'now': len(new), 'skipped': skipped}
        save_progress(out, index, report, key)  # after every topic: a stopped job keeps everything finished
    save_progress(out, index, report, key)
    return report


def save_progress(out, index, report, key):
    (out/'index.json').write_text(json.dumps(index, indent=1, ensure_ascii=False) + '\n')
    text = json.dumps(report, indent=1)
    if key in text: raise ValueError('secret_in_report')
    (out/'report.json').write_text(text + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--confirm', required=True); p.add_argument('--per-topic', type=int, default=PER_TOPIC)
    p.add_argument('--output', type=Path, default=ROOT/'.local/backfill-photos')
    a = p.parse_args()
    if a.confirm != 'PHOTOS': p.error('confirm_must_equal_PHOTOS')
    if not 10 <= a.per_topic <= 40: p.error('per_topic_must_be_10_to_40')
    r = run(os.environ.get('PIXABAY_KEY', '').strip(), ROOT/'assets/globe/photos/index.json', ROOT/'assets/globe/photos/blocked.json', a.output, a.per_topic)
    print(json.dumps({'added': r['added'], 'topics': len(r['topics'])}))
    return 0


if __name__ == '__main__': sys.exit(main())
