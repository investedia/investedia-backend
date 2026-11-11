"""Exact project names/retained aliases + matching verified country/place, no forced links.

Suggestions stay off the robot until a hash-bound human sample of 100 is >=90% correct.
No article fields, financial ledgers, or stock-price data are modified.
"""
import hashlib
import json
import math
import re


def fingerprint(projects):
    return hashlib.sha256(json.dumps(projects,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def candidates(articles, projects, iso):
    index = {}
    for p in projects:
        if p.get('validation_status') != 'verified': continue
        for alias in [p['n']]+p.get('aliases', []):
            if len(alias.strip()) < 5: continue  # Short generic names need individual review, never forced.
            index.setdefault(alias.casefold(), []).append(p)
    out=[]
    for a in articles:
        location=a.get('location') or {}
        if not location.get('place') or location.get('confidence') == 'low': continue
        if not all(isinstance(location.get(k),(int,float)) and math.isfinite(location[k]) for k in ('lat','lon')): continue
        cc=iso.get(location.get('country'))
        if not cc: continue
        text=' '.join(str(a.get(k) or '') for k in ('headline','summary'))
        found=set()
        for alias, matches in index.items():
            # Only unique, whole-name evidence in actual article text. A source region is irrelevant.
            if len({p['k'] for p in matches})!=1 or not re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text,re.I): continue
            p=matches[0]
            if p['cc']!=cc or p['k'] in found: continue
            found.add(p['k'])
            out.append({'event':a['id'],'project':p['k'],'headline':a.get('headline'),
                        'published_at':a.get('published_at'),'source':a.get('source'),
                        'origin':location,'dest':{'project':p['k'],'name':p['n'],'country':p['cc'],'lat':p['la'],'lon':p['lo']},
                        'evidence':{'name':alias,'rule':'exact-name; unique-project; same verified event country'},
                        'type':'project','relation':'named-project','tier':1,'confidence':.9})
    return out


def review_passes(review, projects):
    sample=review.get('sample', [])
    ids={(r.get('event'),r.get('project')) for r in sample}
    # Actual link rendering remains disabled until a human has checked 100 distinct real matches.
    return (review.get('enabled') is True and bool(review.get('reviewer')) and bool(review.get('checked_at'))
            and review.get('dataset_sha256')==fingerprint(projects) and len(sample)>=100 and len(ids)==len(sample)
            and all(r.get('source_url','').startswith('https://') and isinstance(r.get('correct'),bool) for r in sample)
            and sum(r['correct'] for r in sample)/len(sample)>=.9)


def connections(articles, projects, iso, review):
    if not review_passes(review,projects): return []
    out=candidates(articles,projects,iso)
    for row in out:
        row['id']=row['event']+'>project:'+row['project']
        row['explanation']='The article explicitly names '+row['dest']['name']+'.'
    return out
