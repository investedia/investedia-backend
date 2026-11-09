"""Offline, reviewed exchange identities; never fetch quotes or infer HQ."""
import copy
import re
from collections import Counter
from datetime import date
from registry import name_key, norm_ticker

def merge_official_listings(registry, source):
    out = copy.deepcopy(registry)
    if source.get('schema') != 'investedia.official-listings/v1' or source.get('mic') != 'XNSA' or source.get('listing_country') != 'NG':
        raise ValueError('Unreviewed source/venue')
    if source.get('source_url') != 'https://doclib.ngxgroup.com/REST/api/issuers/companydirectory?$orderby=CompanyName':
        raise ValueError('Unreviewed source URL')
    date.fromisoformat(source['checked_at'])
    if not re.fullmatch('[0-9a-f]{64}', source['source_sha256']): raise ValueError('Missing source fingerprint')
    seen = set()
    for row in source['listings']:
        symbol, isin = row['symbol'], row['isin']
        if not re.fullmatch('[A-Z0-9]+', symbol) or not re.fullmatch('NG[A-Z0-9]{9}[0-9]', isin) or symbol in seen:
            raise ValueError('Invalid/duplicate listing identity')
        seen.add(symbol)
        # ISO6166 checksum after letter expansion.
        digits = ''.join(str(ord(c)-55) if c.isalpha() else c for c in isin)
        if sum((int(c)*2//10 + int(c)*2%10) if i%2 else int(c) for i,c in enumerate(reversed(digits)))%10:
            raise ValueError('Invalid ISIN checksum')
        date.fromisoformat(row['listed_on'])
        if not row['official_name'].strip(): raise ValueError('Missing issuer name')
        aid = f'EQ:XNSA:{symbol}'; company = f'CO:{aid}'
        asset = {'id':aid,'class':'equity','name':row['official_name'],'official':row['official_name'],'sym':symbol,'mic':'XNSA',
                 'country':'NG','country_basis':'listing-jurisdiction','isin':isin,'company':company,'primary':True,'names':row['names'],
                 'sector_raw':row['sector_raw'],'subsector_raw':row['subsector_raw'],
                 'verify':{'method':'official-exchange-directory','at':source['checked_at'],'url':source['source_url'],'sha256':source['source_sha256']}}
        if aid in out['assets'] and out['assets'][aid] != asset: raise ValueError('Listing conflict: '+aid)
        out['assets'][aid] = asset
        out['companies'][company] = {'id':company,'name':asset['name'],'listings':[aid]}
        for alias in [symbol]:
            key=norm_ticker(alias); ids=out['alias'].setdefault(key,[])
            if ids and aid not in ids: raise ValueError('Ticker collision: '+symbol)
            if aid not in ids: ids.append(aid)
        for name in [row['official_name']]+row['names']:
            key=name_key(name);ids=out['names'].setdefault(key,[])
            if ids and aid not in ids: raise ValueError('Name collision: '+name)
            if aid not in ids:ids.append(aid)
    out['counts']=dict(Counter(a['class'] for a in out['assets'].values()))
    out['sources']['ngx']=source['source_url']
    return out
