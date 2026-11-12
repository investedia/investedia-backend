"""Collect review candidates only: Wikidata P18 plus Commons per-file metadata.

No image download, licence approval, project mutation or publication. Zero AI calls.
"""
import argparse
import collections
import datetime as dt
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import unquote, urlencode, urlsplit

from tools.projects.scale.media import CC, site_hash
from tools.projects.scale.transport import Client, BudgetExceeded, Deferred


def query(ids):
    if not 1 <= len(ids) <= 80 or not all(re.fullmatch(r'Q[1-9][0-9]*', k) for k in ids):
        raise ValueError('Expected 1 to 80 exact Wikidata ids')
    return ('SELECT ?item ?image WHERE { VALUES ?item { ' + ' '.join('wd:' + k for k in ids)
            + ' } ?item wdt:P18 ?image . } ORDER BY ?item ?image')


def text(value):
    return html.unescape(re.sub(r'<[^>]+>', '', str(value or ''))).strip()


def commons_candidate(payload):
    """A permitted licence is a candidate, not a verified exact-site photo."""
    pages = payload.get('query', {}).get('pages', {})
    if len(pages) != 1:
        raise ValueError('commons-file-response-invalid')
    page = next(iter(pages.values()))
    info = page.get('imageinfo', [{}])[0]
    ext = info.get('extmetadata', {})
    get = lambda k: text(ext.get(k, {}).get('value'))
    licence = get('LicenseShortName')
    reasons = []
    if not CC.fullmatch(licence) and licence != 'Public domain':
        reasons.append('licence-not-approved')
    if get('NonFree') or get('Restrictions'):
        reasons.append('rights-restrictions-need-review')
    if not get('Artist') or not get('LicenseUrl'):
        reasons.append('credit-or-terms-missing')
    if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
        reasons.append('not-supported-raster')
    return {'file_title': page.get('title'), 'author': get('Artist'), 'licence': licence,
            'licence_url': get('LicenseUrl'), 'description': get('ImageDescription'),
            'source_url': info.get('descriptionurl'), 'download_url': info.get('url'),
            'media_timestamp': info.get('timestamp'), 'width': info.get('width'), 'height': info.get('height'),
            'needs_exact_site_review': True, 'rejected_reasons': reasons}


def discover(document, client, previous=None, commons=False, limit=500):
    if not 1 <= limit <= 5000:
        raise ValueError('Project cap must be 1..5000')
    rows = [p for p in document['projects'] if p.get('validation_status') == 'verified'][:limit]
    by_id = {p['k']: p for p in rows if re.fullmatch(r'Q[1-9][0-9]*', p['k'])}
    # Only reuse candidates for the identical project identity/location.
    candidates = {r['project']: r for r in (previous or {}).get('projects', [])
                  if r['project'] in by_id and r.get('site_sha256') == site_hash(by_id[r['project']])}
    def fresh(candidate):
        try:
            stamp = dt.datetime.fromisoformat(candidate['checked_at'])
            age = (dt.datetime.now(dt.timezone.utc)-stamp).total_seconds()
            return 0 <= age < 7*86400
        except (KeyError, ValueError, TypeError):
            return False
    pending = [k for k in by_id if k not in candidates or not fresh(candidates[k]) or (commons and any(
        'commons' not in image for image in candidates[k].get('images', [])))]
    deferred = None
    try:
        for start in range(0, len(pending), 40):
            batch = pending[start:start+40]
            response, receipt = client.sparql(query(batch))
            found = collections.defaultdict(list)
            for row in response['results']['bindings']:
                key = row['item']['value'].rsplit('/', 1)[-1]
                if key not in batch:
                    raise ValueError('Unexpected media source entity')
                u = urlsplit(row['image']['value'])
                if u.hostname != 'commons.wikimedia.org' or not u.path.startswith('/wiki/Special:FilePath/'):
                    continue
                title = 'File:' + unquote(u.path.split('/wiki/Special:FilePath/', 1)[1])
                image = {'title': title, 'assertion': 'Wikidata P18', 'receipt_sha256': receipt['sha256'],
                         'checked_at': receipt['checked_at'], 'licence_inherited_from_wikidata': False}
                if re.search(r'\b(model|design|rendering|impression)\b', title, re.I):
                    image['review_warnings'] = ['possible-model-or-rendering-not-a-site-photo']
                if commons:
                    url = 'https://commons.wikimedia.org/w/api.php?' + urlencode({
                        'action': 'query', 'format': 'json', 'prop': 'imageinfo', 'titles': title,
                        'iiprop': 'url|timestamp|mime|size|extmetadata'})
                    body, meta_receipt = client.get(url)
                    image['commons'] = commons_candidate(json.loads(body))
                    image['commons_receipt_sha256'] = meta_receipt['sha256']
                    time.sleep(1.1)
                found[key].append(image)
            # Commit a batch only after every requested metadata lookup completed.
            for key in batch:
                p = by_id[key]
                candidates[key] = {'project': key, 'name': p['n'], 'country': p['cc'], 'type': p['t'],
                                   'site_sha256': site_hash(p), 'images': found[key],
                                   'checked_at': receipt['checked_at'], 'receipt_sha256': receipt['sha256']}
            time.sleep(1.1)
    except (Deferred, BudgetExceeded, OSError, ValueError) as e:
        deferred = str(e) if isinstance(e, (Deferred, BudgetExceeded, ValueError)) else type(e).__name__
    for candidate in candidates.values():
        for image in candidate['images']:
            if re.search(r'\b(model|design|rendering|impression)\b', image['title'], re.I):
                image['review_warnings'] = ['possible-model-or-rendering-not-a-site-photo']
    completed = [k for k in by_id if k in candidates and fresh(candidates[k]) and (not commons or all(
        'commons' in image for image in candidates[k]['images']))]
    return {'schema': 'investedia.projects.media-candidates.v1',
            'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'notice': 'Candidates only. No image is approved, downloaded or published. Not investment advice.',
            'counts': {'projects_requested': len(rows), 'projects_checked': len(completed),
                       'projects_with_candidates': sum(bool(r['images']) for r in candidates.values()),
                       'images': sum(len(r['images']) for r in candidates.values()),
                       'not_wikidata': len(rows)-len(by_id), 'pending': len(by_id)-len(completed)},
            'requests': client.requests, 'bytes': client.bytes, 'cache_hits': client.hits,
            'deferred': deferred, 'projects': [candidates[k] for k in sorted(candidates)]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=Path('assets/globe/projects-v2.json'))
    p.add_argument('--output', type=Path, default=Path('data/projects/scale/media-candidates.json'))
    p.add_argument('--commons', action='store_true', help='Fetch per-file licence/credit candidates; still requires exact-site review')
    p.add_argument('--seconds', type=int, default=180)
    p.add_argument('--limit', type=int, default=500)
    args = p.parse_args()
    if not 1 <= args.seconds <= 900:
        p.error('Source budget must be 1..900 seconds')
    client = Client('data/projects/raw/scale/media-http', seconds=args.seconds,
                    hosts=('query.wikidata.org', 'commons.wikimedia.org'))
    previous = json.loads(args.output.read_text()) if args.output.exists() else None
    report = discover(json.loads(args.input.read_text()), client, previous, args.commons, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix('.tmp')
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    temp.replace(args.output)
    print(json.dumps({k: report[k] for k in ('counts', 'requests', 'bytes', 'deferred')}))


if __name__ == '__main__':
    main()
