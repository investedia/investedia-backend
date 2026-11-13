"""Explicitly synthetic capacity fixtures; never research records or production data."""
import copy,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'phase4'))
from sector_adapter import SCHEMA

def fixture(i):
 sector='data_centers' if i%2==0 else 'real_estate';rid=f'test:{sector}:{i:06d}';exact=i%3==0;company=i%40
 ev={'url':'https://fixtures.example.invalid/evidence','sha256':'0'*64,'checked_at':'2026-11-13','locator':'SYNTHETIC load-test fixture, no real evidence'}
 loc={'precision':'exact' if exact else 'approximate','lat':round(-60+((i*37)%12000)/100,5),'lon':round(-175+((i*73)%35000)/100,5),'label':'SYNTHETIC coordinate','basis':'Procedural test point, no real facility','satellite_allowed':False,'evidence':{**ev,'record_id':rid,'scope':'specific_site' if exact else 'synthetic_city'}}
 return {'schema':SCHEMA,'id':rid,'name':f'SYNTHETIC TEST {i:06d}','sector':sector,'source_identity':{'authority':'synthetic_fixture','id':str(i)},'synthetic':True,'country_code':None,'city':'SYNTHETIC place','asset':{'category':'project','subtype':'Synthetic infrastructure fixture','parent_id':None,'count_as_project':True},'status':{'stage':['planning','under_construction','operating','expanding'][i%4],'label':'SYNTHETIC status','as_of':'2026-11-13'},'location':loc,'identity_evidence':ev,'exposures':[{'role':['developer','operator','lessee','affiliation'][i%4],'label':'SYNTHETIC relationship','relationship_scope':'test_only','property_stake':None,'evidence':ev,'listing':{'name':f'SYNTHETIC COMPANY {company:02d}','ticker':f'TEST{company:02d}','exchange':'TEST ONLY','exchange_mic':None,'security_type':'synthetic','evidence':ev},'headquarters':{'city':'SYNTHETIC HQ','lat':10+company,'lon':-120+company,'precision':'approximate','evidence':ev},'investment_access':{'type':'research_only','verified':False,'scope':'SYNTHETIC; no investment access'}}],'imagery':[],'verification':{'classification':'synthetic','company':f'SYNTHETIC COMPANY {company:02d}'},'reuse':{'fields':{k:{'status':'omit','basis':'Synthetic fixture, never publish as real'} for k in ['identity','status','economic_relationship','listing','location']},'review':None},'preview_only':True,'extensions':{sector:{'synthetic_only':True}}}

def bundle(count):
 return {'schema':'investedia.projects.import.v1','synthetic':True,'records':[fixture(i) for i in range(count)]}
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--count',type=int,default=1000);a.add_argument('--output',required=True);args=a.parse_args()
 if not 1<=args.count<=100000:raise SystemExit('Count must be 1–100000')
 Path(args.output).write_text(json.dumps(bundle(args.count),sort_keys=True,separators=(',',':'))+'\n')
