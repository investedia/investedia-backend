"""Attach only locally stored, hash-bound, per-file reviewed project imagery.

Discovery is not approval. A Wikidata P18 assertion never licenses its image.
"""
import copy
import datetime as dt
import hashlib
import json
import math
import re
import warnings
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

CC = re.compile(r'CC(?:0 1\.0| BY(?:-SA)? (?:1\.0|2\.0|2\.5|3\.0|4\.0))')


def https(value, hosts=None):
    u = urlsplit(value or '')
    return (u.scheme == 'https' and bool(u.hostname) and not u.username and not u.password
            and u.port in (None, 443) and not u.query and not u.fragment
            and (hosts is None or u.hostname in hosts))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def site_hash(project):
    """An image approval cannot silently follow a relocated or renamed record."""
    fields = {k: project[k] for k in ('k', 'n', 'cc', 'la', 'lo')}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def contained(root, relative, prefix):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('media-path-invalid')
    p = (root / relative).resolve()
    if not p.is_relative_to((root / prefix).resolve()) or not p.is_file():
        raise ValueError('media-file-missing-or-outside-root')
    return p


def date(value, asof):
    d = dt.date.fromisoformat(value)
    if d > dt.date.fromisoformat(asof):
        raise ValueError('media-date-in-future')
    return d.isoformat()


def validate(entry, project, root, asof):
    root = Path(root)
    if any('<' in str(entry.get(k, '')) or '>' in str(entry.get(k, '')) for k in ('author', 'changes', 'provider')):
        raise ValueError('media-credit-must-be-plain-text')
    if entry.get('site_sha256') != site_hash(project):
        raise ValueError('media-site-review-mismatch')
    review = entry.get('review', {})
    if not (review.get('reviewer') and review.get('exact_site') is True
            and review.get('commercial_use') is True and review.get('redistribution') is True):
        raise ValueError('media-review-incomplete')
    checked = date(review.get('checked_at', ''), asof)
    evidence = contained(root, review.get('evidence_file'), 'data/projects')
    if sha(evidence) != review.get('evidence_sha256'):
        raise ValueError('media-evidence-hash-mismatch')
    image = contained(root, entry.get('file'), 'assets/img/projects/scale')
    if image.stat().st_size > 10*1024*1024:
        raise ValueError('media-file-too-large')
    if sha(image) != entry.get('sha256'):
        raise ValueError('media-image-hash-mismatch')
    data = image.read_bytes()
    if not (data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG\r\n\x1a\n')
            or (data.startswith(b'RIFF') and data[8:12] == b'WEBP')):
        raise ValueError('media-not-supported-raster')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(image) as decoded:
                if decoded.width*decoded.height > 20_000_000:
                    raise ValueError('media-pixel-budget-exceeded')
                decoded.verify()
    except (OSError, SyntaxError, Image.DecompressionBombWarning, Image.DecompressionBombError) as error:
        raise ValueError('media-raster-invalid') from error
    if not entry.get('author') or not https(entry.get('source_url')) or not https(entry.get('licence_url')):
        raise ValueError('media-credit-incomplete')
    kind, licence = entry.get('kind'), entry.get('licence', '')
    if kind == 'photo':
        if not https(entry['source_url'], {'commons.wikimedia.org'}) or not urlsplit(entry['source_url']).path.startswith('/wiki/File:'):
            raise ValueError('photo-needs-commons-file-evidence')
        if not CC.fullmatch(licence) and licence != 'Public domain':
            raise ValueError('photo-licence-not-approved')
        label = 'Photo · ' + entry['author'] + ' · ' + licence
    elif kind == 'satellite':
        providers = {
            'USGS Landsat': {'www.usgs.gov', 'landsatlook.usgs.gov'},
            'NASA Landsat': {'www.nasa.gov', 'earthobservatory.nasa.gov'},
            'Copernicus Sentinel-2': {'www.copernicus.eu', 'dataspace.copernicus.eu'},
        }
        if not https(entry['source_url'], providers.get(entry.get('provider'), set())):
            raise ValueError('satellite-source-not-reviewed-provider')
        acquired = date(entry.get('acquired_at', ''), asof)
        bbox = entry.get('bbox', [])
        if (len(bbox) != 4 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in bbox)):
            raise ValueError('satellite-bounds-invalid')
        west, south, east, north = bbox
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90
                and west <= project['lo'] <= east and south <= project['la'] <= north
                and east-west <= .1 and north-south <= .1):
            raise ValueError('satellite-not-exact-site-crop')
        expected = 'Copernicus Sentinel data terms' if entry['provider']=='Copernicus Sentinel-2' else 'Public domain'
        if licence != expected:
            raise ValueError('satellite-terms-not-reviewed')
        label = 'Satellite view · ' + entry['provider'] + ' · ' + acquired
    else:
        raise ValueError('media-kind-invalid')
    # Explicit output allowlist: internal review notes and source HTML never reach the browser.
    public = {k: entry[k] for k in ('file', 'sha256', 'author', 'licence', 'licence_url', 'source_url')}
    public.update(checked_at=checked, label=label, changes=entry.get('changes', 'Unmodified'))
    if kind == 'satellite':
        public.update(provider=entry['provider'], acquired_at=acquired, bbox=bbox)
    return public


def attach(projects, manifest, root, asof):
    if manifest.get('schema') != 'investedia.projects.media-reviewed.v1':
        raise ValueError('media-schema-invalid')
    output = copy.deepcopy(projects)
    for project in output:
        project.pop('photo', None)
        project.pop('satellite', None)
        project['src'] = [{**s, 'field_list': [f for f in s.get('field_list', []) if f not in ('photo', 'satellite')]}
                          for s in project.get('src', []) if any(f not in ('photo', 'satellite') for f in s.get('field_list', []))]
    by_id = {p['k']: p for p in output}
    accepted, rejected, grouped = [], [], {}
    for entry in manifest.get('media', []):
        key = entry.get('project')
        try:
            if key not in by_id:
                raise ValueError('media-project-not-in-current-dataset')
            public = validate(entry, by_id[key], root, asof)
            grouped.setdefault((key, entry['kind']), []).append(public)
        except (ValueError, TypeError, KeyError, OSError) as e:
            reason = str(e) if isinstance(e, ValueError) else 'media-manifest-invalid'
            rejected.append({'project': key, 'reason': reason})
    for key, project in by_id.items():
        for kind in ('photo', 'satellite'):
            candidates = grouped.get((key, kind), [])
            if len(candidates) > 1:
                rejected.append({'project': key, 'reason': 'ambiguous-' + kind})
                continue
            if candidates:
                project[kind] = candidates[0]
                project['src'].append({'name': candidates[0]['label'], 'url': candidates[0]['source_url'],
                                       'licence': candidates[0]['licence'], 'checked_at': candidates[0]['checked_at'],
                                       'field_list': [kind]})
                accepted.append({'project': key, 'kind': kind})
                break  # Reviewed photos take precedence over satellite.
    return output, {'accepted': accepted, 'rejected': rejected,
                    'missing': [p['k'] for p in output if not p.get('photo') and not p.get('satellite')]}
