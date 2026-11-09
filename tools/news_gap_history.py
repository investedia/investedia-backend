"""Read-only P3 geography guards, adapted from recovered codex/p3-news-backfill.
Original: 9904e9770, tools/backfill_history.py. No archive writer/provider job.
"""
import json, math, re
from pathlib import Path

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def reference(root):
    iso = read(root / 'assets/globe/iso.json')
    shapes = read(root / 'assets/globe/countries-50m.json')
    regions = {}
    for c in read(root / 'tools/globe-news/wb-countries.json')[1]:
        r = c['region']['value'].strip()
        regions[c['iso2Code']] = {'North America':'na','Europe & Central Asia':'eu','East Asia & Pacific':'asia','South Asia':'asia',
                                'Sub-Saharan Africa':'af','Latin America & Caribbean':'latam','Middle East & North Africa':'me',
                                'Middle East, North Africa, Afghanistan & Pakistan':'me'}.get(r, 'eu')
    places = {}
    for row in shapes:
        if row[0] not in iso: continue
        points = []
        for ring in row[3:]:
            x = y = 0
            for i in range(0, len(ring), 2):
                x += ring[i]; y += ring[i+1]; points.append((x/50, y/50))
        if not points: continue
        places[row[0]] = {'place':row[0], 'country':row[0], 'lat':row[2]/50, 'lon':row[1]/50, 'region':regions.get(iso[row[0]], 'eu'),
                          'bounds':[min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)]}
    return iso, places


def named(name, text):
    return bool(re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', text, re.I))


def locate(candidate, iso, places):
    text = candidate['text']
    # A reviewed dateline may resolve a genuinely multi-country report. GDELT's
    # sourcecountry is deliberately never read. Supplied coordinates are bounded
    # using the same +/-1 degree rule as the live validator, but never clamped.
    loc = candidate.get('reviewed_location')
    if loc:
        if not named(loc['place'], text) or not named(loc['country'], text): raise ValueError('Origin is not named in article text')
        if loc['country'] not in places: raise ValueError('Unknown origin country')
        evidence = candidate.get('origin_evidence', '')
        if not evidence or evidence not in text or not named(loc['place'], evidence): raise ValueError('Missing reviewed origin evidence')
        b = places[loc['country']]['bounds']
        lat, lon = loc['lat'], loc['lon']
        if not (math.isfinite(lat) and math.isfinite(lon) and b[0]-1 <= lon <= b[2]+1 and b[1]-1 <= lat <= b[3]+1): raise ValueError('Origin outside country bounds')
        return {k:loc[k] for k in ('place','country','lat','lon')} | {'region':places[loc['country']]['region']}
    countries = [n for n in places if named(n, text)]
    # Explicit article wording, never the publisher's country or a currency.
    if ('United States of America' in places and ('United States' in text or 'U.S. economy' in text)):
        countries.append('United States of America')
    countries = list(set(countries))
    if len(countries) != 1: raise ValueError('Missing or ambiguous event location; needs reviewed dateline')
    return {k:v for k,v in places[countries[0]].items() if k != 'bounds'}

