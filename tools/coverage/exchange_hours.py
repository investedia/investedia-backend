"""Import supported MIC calendars from Apache-2.0 exchange-calendars.
No network, price/provider calls, or production deployment. Exact library MICs only.
"""
import argparse,copy,json
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE='https://github.com/gerrymanoim/exchange_calendars'
LICENCE=SOURCE+'/blob/v4.13.2/LICENSE'

def active_time(values,day):
 active=None
 for since,value in values or []:
  if since is not None and hasattr(since,'date'):since=since.date()
  if since is None or since<=day:active=value
 return active.isoformat(timespec='seconds') if active is not None else None

def calendar_metadata(calendar,day,version):
 import pandas as pd
 opens=active_time(calendar.open_times,day);closes=active_time(calendar.close_times,day)
 if not opens or not closes:raise ValueError('no_defined_regular_session')
 tz=str(calendar.tz);end=day+timedelta(days=32)
 dated=[]
 for session,row in calendar.schedule.loc[day.isoformat():end.isoformat()].iterrows():
  def value(key):
   v=row[key];return None if pd.isna(v) else v.tz_convert(tz).isoformat()
  dated.append({'date':session.date().isoformat(),'open':value('open'),'close':value('close'),
                'break_start':value('break_start'),'break_end':value('break_end')})
 return {'timezone':tz,'sessions':[{'weekmask':calendar.weekmask,'open':opens,'close':closes,
          'open_day_offset':calendar.open_offset,'close_day_offset':calendar.close_offset,
          'break_start':active_time(getattr(calendar,'break_start_times',None),day),
          'break_end':active_time(getattr(calendar,'break_end_times',None),day)}],
          'calendar':{'provider':'exchange-calendars','version':version,'calendar_name':calendar.name,
          'source_url':SOURCE,'licence':'Apache-2.0','licence_url':LICENCE,'as_of':day.isoformat(),
          'valid_from':day.isoformat(),'valid_through':end.isoformat(),
          'dated_sessions':dated,'notice':'Library-maintained calendar; exceptional emergency closures may change. Dates absent within this horizon are non-session days. Outside the horizon, only regular hours are known.'}}

def enrich(exchanges,factory,day,version):
 out=copy.deepcopy(exchanges);missing={};filled=[]
 for mic,row in out.items():
  try:
   if (row.get('sessions') or row.get('timezone')) and row.get('calendar',{}).get('provider')!='exchange-calendars':continue # never overwrite other reviewed venue data
   metadata=calendar_metadata(factory(mic),day,version)
  except Exception as e:
   missing[mic]=type(e).__name__;continue
  row.update(metadata);filled.append(mic)
 return out,{'updated_mics':filled,'unsupported':missing,'source_url':SOURCE,'licence':'Apache-2.0','version':version,'as_of':day.isoformat()}

def main():
 import exchange_calendars as xc
 if xc.__version__!='4.13.2':raise ValueError('install_the_pinned_calendar_version_before_import')
 p=argparse.ArgumentParser();p.add_argument('--as-of',default=datetime.now(timezone.utc).date().isoformat());a=p.parse_args()
 path=ROOT/'data/exchanges.json';ex=json.loads(path.read_text());out,report=enrich(ex,xc.get_calendar,date.fromisoformat(a.as_of),xc.__version__)
 path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'data/coverage/exchange-hours-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'updated':len(report['updated_mics']),'unsupported':len(report['unsupported'])}))
if __name__=='__main__':main()
