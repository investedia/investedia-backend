"""Golden vectors so the Python (news_core.py) and JavaScript (workers/live/v1/newscore.js) implementations cannot drift.
Run: python3 tools/gen-news-vectors.py  -> tests/fixtures/news-core-vectors.json"""
import json, sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '.')
import news_core as c
NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
urls = ['https://www.Example.com/a/b/?utm_source=x&id=7#frag', 'https://example.com/a/b/amp/', 'https://news.site/x?ref=rss&b=2&a=1', 'https://bbc.co.uk/news/business-123']
pairs = [('ECB holds interest rates steady at 2%', 'ECB holds interest rates steady at 2%', 1), ('Nvidia shares jump 8% after record earnings', 'Nvidia stock surges 8% on record earnings beat', 2),
         ('Apple unveils new iPhone', 'Tesla recalls vehicles', 1), ('Fed cuts rates by 25 basis points', 'Federal Reserve lowers rates 25 basis points amid slowing jobs', 3)]
cands = [{'title': 'ECB raises interest rates in surprise decision', 'kind': 'official', 'mins': 3}, {'title': 'ECB raises interest rates in surprise decision', 'kind': 'news', 'mins': 3},
         {'title': 'US inflation CPI surges, Treasury yields jump', 'kind': 'news', 'mins': 20}, {'title': 'Local shop opens new branch', 'kind': 'news', 'mins': 900},
         {'title': 'Oil prices jump as OPEC trims output; Brent hits record high', 'kind': 'news', 'mins': 45, 'desc': 'Crude and gas markets react'}]
out = {'canon': [[u, c.canon(u)] for u in urls], 'same': [[a, b, h, c.same_event(a, b, h)] for a, b, h in pairs],
       'score': [[x, round(c.score({'title': x['title'], 'kind': x['kind'], 'desc': x.get('desc', ''), 'published': c.iso(NOW - timedelta(minutes=x['mins']))}, NOW), 1)] for x in cands],
       'now': c.iso(NOW)}
json.dump(out, open('tests/fixtures/news-core-vectors.json', 'w'), indent=1)
print('vectors written')
