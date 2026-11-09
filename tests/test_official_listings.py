import copy
import json
import unittest
from pathlib import Path
from registry import Registry
from tools.registry.official_listings import merge_official_listings
ROOT=Path(__file__).resolve().parents[1]
class OfficialListingTests(unittest.TestCase):
    def setUp(self):
        self.source=json.loads((ROOT/'data/official-listings-ngx.json').read_text())
        self.registry=json.loads((ROOT/'data/registry.json').read_text())
    def test_idempotence_and_no_existing_changes(self):
        self.assertEqual(merge_official_listings(self.registry,self.source),self.registry)
    def test_identity_collisions_and_isin_fail_closed(self):
        for field,value in [('isin','NGMTNN000003'),('symbol','MTNN.NG')]:
            source=copy.deepcopy(self.source);source['listings'][0][field]=value
            with self.assertRaises(ValueError):merge_official_listings(self.registry,source)
        registry=copy.deepcopy(self.registry);registry['alias']['MTNN']=['EQ:XJSE:MTN']
        with self.assertRaisesRegex(ValueError,'collision'):merge_official_listings(registry,self.source)
        self.assertEqual(registry['alias']['MTNN'],['EQ:XJSE:MTN'])
    def test_resolves_subsidiary_not_parent_and_no_guessed_price_or_geo(self):
        registry=Registry(path=str(ROOT/'data/registry.json'))
        self.assertEqual(registry.resolve('MTN Nigeria','MTNN','company','NG')['id'],'EQ:XNSA:MTNN')
        self.assertEqual(registry.resolve('MTN Group','MTN','company','ZA')['id'],'EQ:XJSE:MTN')
        for row in self.source['listings']:
            a=self.registry['assets']['EQ:XNSA:'+row['symbol']]
            self.assertEqual(a['isin'],row['isin'])
            self.assertEqual(a['verify']['method'],'official-exchange-directory')
            for k in ['px','geo','price','volume','market_cap']:self.assertNotIn(k,a)
