import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('basics',Path(__file__).resolve().parents[1]/'tools/coverage/country_basics.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class BasicsTests(unittest.TestCase):
 def test_saved_country_panel_values_and_dates_are_preserved(self):
  e=m.read(m.ROOT/'assets/globe/economy.json');r=m.saved(e,{'United States of America':'US'},{})
  self.assertEqual(r['countries']['US']['gdp'],e['countries']['US']['gdp']);self.assertEqual(r['countries']['US']['gdp_usd']['as_of'],str(e['countries']['US']['gdp'][0]));self.assertEqual(r['asof'],e['asof'])
  for key in ['policy_rate','credit_rating','next_cb_meeting']:self.assertIsNone(r['countries']['US'][key])
 def test_api_null_aggregate_and_future_values_never_fill_missing(self):
  r=m.saved({}, {'Brazil':'BR'},{});response=[{'pages':1},[{'country':{'id':'BR'},'date':'2025','value':None},{'country':{'id':'1W'},'date':'2025','value':10},{'country':{'id':'BR'},'date':'2999','value':10}]]
  m.apply_indicator(r,'gdp_usd',response,'test');self.assertIsNone(r['countries']['BR']['gdp_usd'])
 def test_negative_growth_is_valid_and_pagination_is_not_silently_truncated(self):
  r=m.saved({}, {'Brazil':'BR'},{});m.apply_indicator(r,'gdp_growth',[{'pages':1},[{'country':{'id':'BR'},'date':'2024','value':-2.1}]],'test')
  self.assertEqual(r['countries']['BR']['growth'],[[2024,-2.1]])
  with self.assertRaises(ValueError):m.apply_indicator(r,'gdp_growth',[{'pages':2},[]],'test')
if __name__=='__main__':unittest.main()
