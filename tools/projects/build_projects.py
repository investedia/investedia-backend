"""Rebuild draft project artifacts from reviewed raw caches. No publication or AI calls.

python tools/projects/build_projects.py --offline
New source input requires a hash-bound licence/redistribution review in manifest.json.
The inherited site snapshot is explicitly unverified and never counts as new coverage.
"""
import argparse
import collections
import copy
import datetime as dt
import difflib
import hashlib
import json
import math
import re
import sys
from pathlib import Path

# Existing frontend main 1e34575d snapshot, migration only. This exception cannot admit fresh downloads.
RETAINED_SHA256 = '9dd222bd5575c3ce81bec3a6914128054b6682ef4ec5b8f4727cdf8cc19d243e'
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from tools.projects.sources import ADAPTERS
from tools.projects.sources.commons import validate as photo_valid
from tools.projects.status_map import normalize

TYPES = ('Solar energy', 'Wind energy', 'Hydro energy', 'Nuclear energy', 'Gas & LNG', 'Oil & gas',
         'Pipelines', 'Mining', 'Batteries & hydrogen', 'Semiconductors', 'Data centres',
         'High-speed rail', 'Metro & urban rail', 'Ports & logistics', 'Airports', 'Water',
         'Real estate', 'Megaproject', 'Development finance', 'Coal energy', 'Geothermal energy')
OPTIONAL = {'status_date','status_source','completion_date','retirement_date','coordinate_precision','coordinate_quality','record_level','external_ids','display_status','evidence','s', 'y', 'ys', 'ye', 'cap', 'cost', 'own', 'aliases', 'sub', 'geometry'}
FIELDS = {'k', 'n', 'lo', 'la', 'c', 'cc', 't'} | OPTIONAL
COUNTRY_ALIASES = {'United States': 'United States of America', "People's Republic of China": 'China',
                   'Republic of Ireland': 'Ireland', 'Russia': 'Russia', 'South Korea': 'South Korea',
                   'Czech Republic': 'Czechia', 'Democratic Republic of the Congo': 'Dem. Rep. Congo'}


def read(path): return json.loads(Path(path).read_text())
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value): return re.sub(r'\s+', ' ', str(value or '').strip().casefold())
def valid_url(s): return isinstance(s, str) and s.startswith('https://') and not re.search(r'[\s<>]', s)
def finite(n): return isinstance(n, (float, int)) and not isinstance(n, bool) and math.isfinite(n)
def distance(a, b):
    la, lo, lb, lob = map(math.radians, (a['la'], a['lo'], b['la'], b['lo']))
    h = math.sin((la-lb)/2)**2 + math.cos(la)*math.cos(lb)*math.sin((lo-lob)/2)**2
    return 6371*2*math.asin(min(1, math.sqrt(h)))


def covered(row, field):
    return any(field in s.get('field_list', []) and valid_url(s.get('url')) and s.get('licence')
               and re.fullmatch(r'\d{4}-\d{2}-\d{2}', s.get('checked_at', '')) for s in row.get('src', []))


def licence_gate(spec, directory):
    if spec.get('retained_snapshot'):
        # Narrow migration exception: the exact existing CC0-labelled site file, not new ingestion.
        if spec['source'] != 'wikidata' or spec.get('sha256') != RETAINED_SHA256 or digest(directory/spec['file']) != RETAINED_SHA256:
            raise ValueError('Retained snapshot changed; independent source review required')
        return
    review = spec.get('licence_review', {})
    evidence = (directory/review.get('evidence_file', '')).resolve()
    if not evidence.is_relative_to(directory.resolve()): raise ValueError('Licence evidence must stay inside projects data')
    if not (review.get('commercial_use') is True and review.get('redistribution') is True
            and valid_url(review.get('url')) and review.get('reviewer') and review.get('reviewed_at')
            and evidence.is_file() and digest(evidence) == review.get('sha256')
            and spec.get('licence') in ('CC0 1.0', 'CC BY 4.0', 'Public domain')
            and spec.get('checked_at') == review['reviewed_at'][:10]):
        raise ValueError('Dataset-specific licence and commercial redistribution review missing: '+spec['source'])
    if spec['source'] in ('nga', 'ourairports') and not spec.get('developments_only'):
        raise ValueError('Ports/airports require individually sourced infrastructure developments')


def normalise(raw, iso, centroids, date, verified, preserve_coordinates=False):
    row = {k: copy.deepcopy(v) for k, v in raw.items() if k in FIELDS and v not in (None, '', [])}
    if not row.get('k') or not (re.fullmatch(r'Q[1-9]\d*', str(row['k'])) or ':' in str(row['k'])):
        raise ValueError('invalid-id')
    if not isinstance(row.get('n'), str) or not row['n'].strip(): raise ValueError('missing-name')
    if row.get('t') not in TYPES: raise ValueError('unknown-type')
    try: row['la'], row['lo'] = float(row['la']), float(row['lo'])
    except (TypeError, ValueError, KeyError): raise ValueError('no-coordinates')
    if not (finite(row['la']) and finite(row['lo']) and abs(row['la']) <= 90 and abs(row['lo']) <= 180):
        raise ValueError('invalid-coordinates')
    if not preserve_coordinates:
        row['la'], row['lo'] = round(row['la'], 4), round(row['lo'], 4)
    cc = iso.get(COUNTRY_ALIASES.get(row.get('c'), row.get('c')))
    if row.get('cc'):
        if row['cc'] not in iso.values() or cc and cc != row['cc']: raise ValueError('conflicting-country')
        cc = row['cc']
    if not cc: raise ValueError('country-not-in-iso')
    row['cc'] = cc
    if not row.get('c'): row['c'] = next(k for k, v in iso.items() if v == cc)
    if raw.get('location_precision') in ('country', 'admin1', 'admin2', 1, 2): raise ValueError('imprecise-location')
    if raw.get('t') == 'Development finance' and raw.get('precise_physical_location_verified') is not True:
        raise ValueError('physical-location-not-verified')
    if raw.get('t') in ('Ports & logistics', 'Airports') and raw.get('development_evidence') is not True:
        raise ValueError('not-verified-development')
    for center in centroids.get(cc, []):
        if distance(row, dict(la=center[0], lo=center[1])) < 1: raise ValueError('country-centroid')
    row['src'] = copy.deepcopy(raw.get('src', []))
    # Derived ISO/type transformations keep the field's original source evidence.
    for s in row['src']:
        if 'c' in s.get('field_list', []) and 'cc' not in s['field_list']: s['field_list'].append('cc')
    if not row['src']: raise ValueError('missing-provenance')
    for field in list(row):
        if field != 'src' and not covered(row, field): raise ValueError('unsourced-'+field)
    if 's' in row:
        status = normalize(row['s'])
        if status: row['s'] = status
        else: row.pop('s')
    for f in ('y', 'ys', 'ye'):
        if f in row:
            try:
                value = int(row[f])
                if str(value) != str(row[f]) or not 1000 <= value <= 2200: raise ValueError()
                row[f] = value
            except (TypeError, ValueError): raise ValueError('invalid-'+f)
    if 'cap' in row and not (finite(row['cap'].get('value')) and row['cap']['value'] > 0 and row['cap'].get('unit')):
        raise ValueError('invalid-capacity')
    if 'cost' in row and not (finite(row['cost'].get('value')) and row['cost']['value'] > 0
            and re.fullmatch('[A-Z]{3}', row['cost'].get('currency', '')) and isinstance(row['cost'].get('year'), int)):
        raise ValueError('invalid-cost')
    for owner in row.get('own', []):
        if not owner.get('name') or owner.get('role') not in ('owner','operator','developer','contractor'):
            raise ValueError('invalid-owner')
        if 'qid' in owner and not re.fullmatch(r'Q[1-9]\d*', owner['qid']): raise ValueError('invalid-owner-qid')
        owner.pop('asset', None)  # Only the exact-identity join may attach assets.
    year = int(date[:4])
    if row.get('s') == 'Cancelled':
        if not row.get('y'): raise ValueError('cancelled-age-unknown')
        if row['y'] < year-5: raise ValueError('cancelled-older-than-five-years')
    if row.get('s') == 'Decommissioned':
        if row['t'] not in ('Nuclear energy','Hydro energy') or raw.get('active_decommissioning_verified') is not True:
            raise ValueError('decommissioned')
    row.update(upd=date, validation_status='verified' if verified else 'retained_unverified')
    return row


def merge_rows(rows):
    output, conflicts, merges = [], [], []
    # Stable ordering; newest per-field source wins. WRI is fallback even if retrieved later.
    def rank(r, field):
        return max(((0 if s['name'].startswith('WRI') else 1, s['checked_at'])
                    for s in r['src'] if field in s['field_list']), default=(0, ''))
    for row in sorted(rows, key=lambda r: (r['k'], json.dumps(r, sort_keys=True))):
        match = next((p for p in output if p['k'] == row['k']), None)
        if not match:
            match = next((p for p in output if p['t'] == row['t'] and p['cc'] == row['cc']
                          and abs(p['la']-row['la']) < .019 and distance(p,row) <= 2
                          and difflib.SequenceMatcher(None,canonical(p['n']),canonical(row['n'])).ratio() >= .85), None)
        if match is None: output.append(copy.deepcopy(row)); continue
        merges.append({'kept':match['k'],'merged':row['k']})
        # The same QID in incompatible countries/places requires review; never last-row wins.
        if match['cc'] != row['cc'] or distance(match,row) > 2:
            raise ValueError('Conflicting identity/place: '+row['k'])
        for field in FIELDS-{'k'}:
            if field not in row: continue
            if field in ('aliases','own'):
                match.setdefault(field, [])
                for x in row[field]:
                    if x not in match[field]: match[field].append(copy.deepcopy(x))
                continue
            if field not in match: match[field] = copy.deepcopy(row[field]); continue
            if match[field] != row[field]:
                newer = rank(row,field) > rank(match,field)
                conflicts.append({'project':match['k'],'field':field,'kept':row[field] if newer else match[field],
                                  'rejected':match[field] if newer else row[field], 'rule':'newer-field-source; ties stable'})
                if newer: match[field] = copy.deepcopy(row[field])
        for src in row['src']:
            if src not in match['src']: match['src'].append(src)
        # Verified coverage cannot be manufactured by mixing an unreviewed record.
        if row['validation_status'] != 'verified': match['validation_status'] = 'retained_unverified'
    return sorted(output, key=lambda p:p['k']), conflicts, merges


def company_links(projects, registry, markets):
    assets = registry.get('assets', {})
    site_ids = {a.get('site') for a in markets.get('assets', []) if a.get('site')}
    links, rejected = [], collections.Counter()
    for p in projects:
        for owner in p.get('own', []):
            # Only a registry record with explicit listed-equity and verified identity is eligible.
            candidates = []
            for asset in assets.values():
                if asset.get('class') != 'equity' or asset.get('validation_status') != 'verified' or asset.get('site') not in site_ids:
                    continue
                if owner.get('qid') and asset.get('qid') and owner['qid'] != asset['qid']:
                    rejected['conflicting-company-qid'] += 1; continue
                if owner.get('isin') and asset.get('isin') and owner['isin'] != asset['isin']:
                    rejected['conflicting-company-isin'] += 1; continue
                if owner.get('qid') and owner['qid'] == asset.get('qid'): method='exact-qid'
                elif owner.get('isin') and owner['isin'] == asset.get('isin'): method='exact-isin'
                elif canonical(owner['name']) == canonical(asset.get('official')): method='exact-registry-name'
                else: continue
                candidates.append((asset,method))
            if len(candidates) != 1:
                rejected['ambiguous-company' if candidates else 'no-verified-listed-identity'] += 1; continue
            asset, method = candidates[0]
            src = next((s for s in p['src'] if 'own' in s['field_list']), None)
            if not src: continue
            owner['asset'] = asset['site']
            links.append({'project':p['k'],'asset':asset['site'],'role':owner['role'],'source':src,'method':method})
    return links, dict(rejected)


def featured(directory, globe):
    import yaml
    output, rejected = [], []
    for path in sorted(directory.glob('*.yaml')):
        doc = yaml.safe_load(path.read_text()) or {}
        for p in doc.get('featured', []):
            if p.get('review_status') != 'inherited_preview':
                # New curated material needs a per-file review and date, not a claim in its title.
                if not (p.get('review_status') == 'reviewed' and p.get('reviewer') and p.get('reviewed_at')
                        and len(p.get('milestones', [])) >= 2 and p.get('description')
                        and all(m.get('title') and re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?',m.get('date',''))
                                and m.get('source',{}).get('checked_at') for m in p.get('milestones', []))):
                    rejected.append({'id':p.get('id'),'reason':'incomplete-featured-review'}); continue
            # Previously retained previews remain marked inherited; they do not count toward 50 fully reviewed entries.
            if not photo_valid(p.get('photo'), globe):
                rejected.append({'id':p.get('id'),'reason':'invalid-photo-hash-or-licence'}); continue
            if not p.get('sources') or not all(valid_url(m.get('source',{}).get('url')) for m in p.get('milestones', [])):
                rejected.append({'id':p.get('id'),'reason':'missing-featured-evidence'}); continue
            output.append(p)
    return sorted(output,key=lambda p:p['id']), rejected


def build(root=ROOT, manifest_path=None, output=None):
    root = Path(root)
    manifest_path = Path(manifest_path or root/'data/projects/manifest.json')
    manifest = read(manifest_path); directory=manifest_path.parent
    date = manifest['build_date']  # Pin for offline reproducibility; never touch provider dates.
    dt.date.fromisoformat(date)
    iso=read(root/'assets/globe/iso.json')
    centroids=read(directory/'country-centroids.json')
    all_rows, drops, source_reports, country_only = [], [], [], []
    source_conflicts=[]
    for spec in manifest['sources']:
        if not spec.get('enabled'):
            source_reports.append({'source':spec['source'],'state':'not-ingested','reason':spec.get('reason'),'rows':0}); continue
        licence_gate(spec, directory)
        path = (directory/spec['file']).resolve()
        if not path.is_relative_to(directory.resolve()) or digest(path) != spec['sha256']: raise ValueError('Raw hash mismatch')
        parsed=ADAPTERS[spec['source']].parse(path, spec)
        source_entry={'source':spec['source'],'name':spec.get('name'),'class':spec.get('class_key'),'state':'retained-unverified' if spec.get('retained_snapshot') else 'licence-reviewed','rows':len(parsed)}
        source_reports.append(source_entry)
        accepted_before=len(all_rows);dropped_before=len(drops)
        for raw in parsed:
            if raw.get('_field_conflicts'):source_conflicts.append({'id':raw.get('k'),'fields':raw['_field_conflicts'],'action':'ambiguous fields withheld'})
            try:
                if manifest.get('policy',{}).get('name')=='projects-scale-current-v1':
                    from tools.projects.scale.policy import current
                    raw=current(raw,date,manifest['policy'].get('completed_since',2020),manifest['policy'].get('max_coordinate_precision_degrees',.001))
                all_rows.append(normalise(raw,iso,centroids,date,not spec.get('retained_snapshot'),preserve_coordinates=manifest.get('policy',{}).get('name')=='projects-scale-current-v1'))
            except ValueError as e:
                drops.append({'id':raw.get('k'),'source':spec['source'],'reason':str(e)})
                if raw.get('t')=='Development finance' and str(e) in ('no-coordinates','imprecise-location','physical-location-not-verified'):
                    country_only.append(raw)
        source_entry['eligible_before_reconciliation']=len(all_rows)-accepted_before
        source_entry['rejected_before_reconciliation']=len(drops)-dropped_before
    # Curated map facts use exactly the same provenance/validation rules.
    import yaml
    for path in sorted((directory/'curated').glob('*.yaml')):
        doc=yaml.safe_load(path.read_text()) or {}
        for raw in doc.get('projects', []):
            # Curated records require licence review for all underlying datasets, not a hand-written approval flag.
            sources={s['name'] for s in raw.get('src', [])}
            cleared={s['name'] for s in manifest['sources'] if s.get('enabled') and not s.get('retained_snapshot')}
            if not sources or not sources <= cleared: raise ValueError('Curated source not cleared')
            try: all_rows.append(normalise(raw,iso,centroids,date,True))
            except ValueError as e: drops.append({'id':raw.get('k'),'source':'curated','reason':str(e)})
    if manifest.get('policy',{}).get('name')=='projects-scale-current-v1':
        from tools.projects.scale.reconcile import reconcile
        projects,conflicts,merges,reconcile_drops=reconcile(all_rows)
        drops.extend(reconcile_drops)
    else:
        projects,conflicts,merges=merge_rows(all_rows)
    conflicts=source_conflicts+conflicts
    media_report={'accepted':[],'rejected':[],'missing':[p['k'] for p in projects]}
    if manifest.get('policy',{}).get('name')=='projects-scale-current-v1':
        from tools.projects.scale.media import attach
        media_path=directory/'scale/media-reviewed.json'
        if media_path.is_file():
            projects,media_report=attach(projects,read(media_path),root,date)
    links,unlinked=company_links(projects,read(root/'data/registry.json'),read(root/'assets/globe/markets.json'))
    feats,feat_drops=featured(directory/'curated',root/'assets/globe')
    if manifest.get('policy',{}).get('name')=='projects-scale-current-v1':
        feats=[p for p in feats if p.get('wikidata_id') in {r['k'] for r in projects}]
    reviewed=[p for p in feats if p.get('review_status')=='reviewed' and len(p.get('milestones',[]))>=2]
    region_by_cc={a.get('cc','').upper():a['r'] for a in read(root/'assets/globe/markets.json').get('assets',[]) if a.get('cc') and a.get('r')}
    total=len(projects)
    share=lambda key: round(100*sum(bool(p.get(key)) for p in projects)/total,2) if total else 0
    report={'schema':'investedia.projects.build-report.v1','build_date':date,'policy':manifest.get('policy'),'map_points':total,
            'verified_points':sum(p['validation_status']=='verified' for p in projects),
            'retained_unverified':sum(p['validation_status']!='verified' for p in projects),
            'by_type':{t:sum(p['t']==t for p in projects) for t in TYPES},
            'missing_fields':{f:sum(not p.get(f) for p in projects) for f in ('s','y','cap','cost','own','aliases','status_date','coordinate_precision')},
            'by_status':dict(sorted(collections.Counter(p.get('s','Not sourced') for p in projects).items())),
            'by_country':dict(sorted(collections.Counter(p['cc'] for p in projects).items())),
            'by_region':dict(sorted(collections.Counter(region_by_cc.get(p['cc'],'Unknown') for p in projects).items())),
            'by_source':source_reports,'media':media_report,'status_pct':share('s'),'year_pct':share('y'),
            'capacity_or_cost_pct':round(100*sum(bool(p.get('cap') or p.get('cost')) for p in projects)/total,2) if total else 0,
            'duplicates_merged':len(merges),'merges':merges,'conflicts':conflicts,'rows_dropped':len(drops),
            'drops_by_reason':dict(sorted(collections.Counter(d['reason'] for d in drops).items())), 'drops':drops,
            'country_only':len(country_only),'featured_retained':len(feats),'featured_reviewed':len(reviewed),
            'featured_rejected':feat_drops,'company_links':len(links),'company_link_rejections':unlinked,
            'linked_projects_by_type':dict(collections.Counter(p['t'] for p in projects if any(l['project']==p['k'] for l in links))),
            'linked_projects_by_region':dict(collections.Counter(a.get('r','Unknown') for a in read(root/'assets/globe/markets.json').get('assets', []) if any(l['asset']==a.get('site') for l in links))),
            'omitted_legacy_inception_years':sum(bool(r.get('y')) for s in manifest['sources'] if s.get('retained_snapshot') for r in read(directory/s['file']).get('projects', [])),
            'news_match_review':{'checked':0,'correct':0,'accuracy_pct':None,'enabled':False,'reason':'100 real matches require human review'},
            'targets':({'energy_points':5000,'infrastructure_points':1000,'quality_dependent':True} if manifest.get('policy') else {'points':4000,'status_pct':70,'year_pct':60,'capacity_or_cost_pct':40,'featured':50}),
            'record_levels':dict(collections.Counter(p.get('record_level','legacy') for p in projects)),
            'unique_source_sites':len({(ns,str(v)) for p in projects for ns,v in p.get('external_ids',{}).items() if ns.endswith(':site')}),
            'sector_coverage':{t:{'count':sum(p['t']==t for p in projects),
                'capacity_pct':round(100*sum(p['t']==t and bool(p.get('cap')) for p in projects)/max(1,sum(p['t']==t for p in projects)),2),
                'status_date_pct':round(100*sum(p['t']==t and bool(p.get('status_date')) for p in projects)/max(1,sum(p['t']==t for p in projects)),2),
                'photo_pct':round(100*sum(p['t']==t and bool(p.get('photo')) for p in projects)/max(1,sum(p['t']==t for p in projects)),2),
                'satellite_pct':round(100*sum(p['t']==t and bool(p.get('satellite')) for p in projects)/max(1,sum(p['t']==t for p in projects)),2)} for t in TYPES},
            'ready_for_publication':False,'notice':'Draft artifacts only. Retained data is not new verified coverage. Not investment advice.'}
    # Stage all validation before replacing outputs; a failed ingest leaves the last good files untouched.
    dest=Path(output or root)
    outputs={dest/'assets/globe/projects.json':{'schema':'investedia.projects.v2','build_date':date,'policy':manifest.get('policy'),'projects':projects},
             dest/'assets/globe/projects-featured.json':{'schema':'investedia.projects.featured.v1','reviewed_count':len(reviewed),
                'curation_target':[50,50],'curation_status':'Retained previews; new primary-source review blocked','projects':feats},
             dest/'assets/globe/project-links.json':{'schema':'investedia.project-links.v1','links':links},
             dest/'data/projects/country-only.json':{'projects':country_only},dest/'data/projects/build-report.json':report}
    for path,value in outputs.items():
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'); tmp.replace(path)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline',action='store_true',help='Required: build only from hash-bound caches')
    parser.add_argument('--manifest',type=Path,default=ROOT/'data/projects/scale-manifest.json' if (ROOT/'data/projects/scale-manifest.json').exists() else None)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if not args.offline: parser.error('Use --offline; fetch and licence review are separate explicit steps')
    report=build(manifest_path=args.manifest,output=args.output)
    print(json.dumps({k:report[k] for k in ('map_points','verified_points','status_pct','year_pct','capacity_or_cost_pct','featured_reviewed','ready_for_publication')},indent=2))
if __name__=='__main__': main()
