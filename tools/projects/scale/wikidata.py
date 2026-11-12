"""Scale bindings: exact source facts, explicit conflicts, no P571 completion inference."""
import collections
import datetime as dt
import re

STATES={
 'proposed building or structure':'Proposed','proposed':'Proposed','planned':'Proposed','announced':'Proposed',
 'pre-construction':'Approved','approved':'Approved','permitted':'Approved','financed':'Approved',
 'building or structure under construction':'Under construction','under construction':'Under construction',
 'in use':'Operational','operational':'Operational','in partial operation':'Partial operation','starting up':'In development',
 'decommissioned':'Decommissioned','nuclear decommissioning':'Decommissioned','retired':'Decommissioned',
 'cancelled':'Cancelled','canceled':'Cancelled','abandoned':'Cancelled','postponed':'On hold','shelved':'On hold',
}


def parse(data,spec):
    grouped=collections.defaultdict(list)
    for binding in data['results']['bindings']:
        key=binding['item']['value'].rsplit('/',1)[-1]
        if not re.fullmatch(r'Q[1-9]\d*',key):raise ValueError('Unexpected source id')
        grouped[key].append(binding)
    out=[]
    for key,bindings in sorted(grouped.items()):
        values=lambda name:sorted({r[name]['value'] for r in bindings if r.get(name)})
        row={'k':key,'t':spec['type'],'record_level':'site','external_ids':{'wikidata':key}}
        evidence={};errors=[];field_conflicts={}
        def one(name,critical=False):
            vals=values(name)
            if len(vals)>1:
                (errors.append('conflicting-'+name) if critical else field_conflicts.setdefault(name,vals))
                return None
            return vals[0] if vals else None
        row['n']=one('itemLabel',True);
        if re.fullmatch(r'Q[1-9]\d*',row['n'] or ''):errors.append('project-name-not-readable')
        row['c']=one('countryLabel',True);row['cc']=one('countryCode',True)
        coord=one('coord',True);point=re.fullmatch(r'Point\((-?[\d.]+) (-?[\d.]+)\)',coord or '')
        if point:
            row['lo'],row['la']=map(float,point.groups());evidence['coordinates']={'property':'P625','raw':coord}
        else:errors.append('no-coordinate')
        precision=one('precision',True)
        if precision is not None:
            row['coordinate_precision']=float(precision);row['coordinate_quality']='source-declared precision in degrees'
        aliases=values('alias')
        if aliases:row['aliases']=aliases
        state=one('statusLabel',True)
        if state:
            row['s']=STATES.get(state.casefold());evidence['s']={'property':'P5817','value':state}
            row['_explicit_operating']=row['s']=='Operational'
        status_date=one('statusDate') or one('statusStart')
        if status_date:
            row['status_date']=status_date.lstrip('+')[:4]
            evidence['status_date']={'property':'P585/P580 qualifier of P5817','raw':status_date,'output_precision':'year-only; source time precision not fetched'}
        entry=one('entry');opening=one('opening');completion=entry or opening
        if completion:
            row['completion_date']=completion.lstrip('+')[:4]
            evidence['completion_date']={'property':'P729' if entry else 'P1619','raw':completion,'output_precision':'year-only; source time precision not fetched'}
            if row.get('s') in (None,'Operational'):
                row['s']='Completed';evidence.setdefault('s',{'property':'P729' if entry else 'P1619','rule':'service entry/official opening; not an operating-now claim'})
                row['status_date']=row['completion_date'];evidence['status_date']=evidence['completion_date']
        retirement=one('retirement')
        if retirement:row['retirement_date']=retirement.lstrip('+')[:4];evidence['retirement_date']={'property':'P730','raw':retirement}
        power=one('capacity');unit=one('capacityUnitLabel')
        if power and unit and not re.fullmatch(r'Q\d+',unit):
            row['cap']={'value':float(power),'unit':unit};evidence['cap']={'property':'P2109','value':power,'unit':unit}
        # No silent currency mapping and no cost year inferred from commissioning/build date.
        amount=one('cost');currency=one('costCurrency');cost_date=one('costDate')
        if amount and currency and re.fullmatch('[A-Z]{3}',currency) and cost_date:
            row['cost']={'value':float(amount),'currency':currency,'year':int(cost_date.lstrip('+')[:4])}
            evidence['cost']={'property':'P2130 + statement date P585 + currency P498','raw_date':cost_date}
        owners=[]
        for role,prop in [('owner','P127'),('operator','P137'),('developer','P178'),('contractor','P1652')]:
            for b in bindings:
                if not b.get(role) or not b.get(role+'Label'):continue
                owner={'qid':b[role]['value'].rsplit('/',1)[-1],'name':b[role+'Label']['value'],'role':role}
                if owner not in owners:owners.append(owner)
        if owners:row['own']=owners;evidence['own']={'properties':['P127','P137','P178','P1652']}
        row['evidence']=evidence
        checked=min(values('__checked_at') or [spec['checked_at']])
        row['status_source']='https://www.wikidata.org/wiki/'+key
        row['src']=[{'name':spec['name'],'url':row['status_source'],'licence':spec['licence'],
                     'checked_at':checked,'field_list':sorted(k for k in row if not k.startswith('_'))}]
        if errors:row['_reject_reason']=';'.join(errors)
        if field_conflicts:row['_field_conflicts']=field_conflicts
        out.append(row)
    return out
