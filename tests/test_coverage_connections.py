import importlib.util,json,unittest
from pathlib import Path
from datetime import datetime,timezone
s=importlib.util.spec_from_file_location('resolve',Path(__file__).resolve().parents[1]/'tools/coverage/resolve_impacts.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ConnectionTests(unittest.TestCase):
 def test_ten_real_country_articles_never_get_guessed_links(self):
  rows=m.read(m.ROOT/'assets/globe/news-archive.json')['stories'];countries=['Nigeria','Tanzania','Malaysia','Angola','Kenya','Ghana','Brazil','Indonesia','Pakistan','Vietnam']
  sample=[next(s for s in rows if s.get('location',{}).get('country')==c) for c in countries]
  reg=m.read(m.ROOT/'data/registry.json')['assets'];prices=m.read(m.ROOT/'assets/globe/news-prices.json')['assets']
  out,report=m.resolve(sample,reg,prices,{},datetime.now(timezone.utc))
  self.assertEqual(out,sample);self.assertEqual(report['resolved_impacts'],0)
  mapping=m.country_map(reg)
  for c in ['NG','TZ','MY','AO','KE','GH','BR','ID','PK','VN']:
   for role,ids in mapping.get(c,{}).items():
    for aid in ids:self.assertEqual(reg[aid]['country'],c)
 def test_named_company_resolves_only_when_real_price_and_licence_match(self):
  reg=m.read(m.ROOT/'data/registry.json')['assets'];prices=m.read(m.ROOT/'assets/globe/news-prices.json')['assets']
  asset=next(a for a in reg.values() if a.get('class')=='equity' and a.get('geo',{}).get('la') is not None and prices.get(a.get('px'),{}).get('p',0)>0)
  now=datetime.now(timezone.utc);row={'impacts':[{'kind':'company','name':asset['name'],'country':asset['country'],'ticker':asset.get('sym'),'why':'Test-only explicit relationship','confidence':'high'}]}
  only={asset['id']:asset};lic={asset['px']:{'redistribution_allowed':True,'licence_url':'https://example.test/licence','source_url':'https://example.test/price','as_of':now.isoformat()}}
  out,r=m.resolve([row],only,prices,lic,now);self.assertEqual(r['resolved_impacts'],1);self.assertEqual(out[0]['impacts'][0]['asset']['id'],asset['id'])
  self.assertNotIn('asset',row['impacts'][0]);self.assertEqual(m.resolve([row],only,prices,{},now)[1]['resolved_impacts'],0)
 def test_sector_not_a_named_company_relationship(self):
  out,r=m.resolve([{'impacts':[{'kind':'sector','name':'Oil'}]}],{}, {},{},datetime.now(timezone.utc));self.assertEqual(r['rejected']['sector_requires_named_explicit_asset'],1)
if __name__=='__main__':unittest.main()
