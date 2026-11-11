"""Version-reviewed unit adapters for owner-supplied GEM and official EIA files.
Column maps are explicit. Illustrative test headers never approve a real workbook.
"""
import csv
import hashlib
import json
from pathlib import Path

def records(path,spec):
    path=Path(path);header_row=spec.get('header_row',1)
    if not isinstance(header_row,int) or not 1<=header_row<=20:raise ValueError('Explicit header row required')
    if path.suffix=='.json':
        data=json.loads(path.read_text());rows=data if isinstance(data,list) else data['rows']
        headers=list(rows[0]) if rows else []
    elif path.suffix in ('.xlsx','.xlsm'):
        import openpyxl
        book=openpyxl.load_workbook(path,read_only=True,data_only=True)
        if spec.get('sheet') not in book.sheetnames:raise ValueError('Explicit sheet name required')
        raw=list(book[spec['sheet']].iter_rows(values_only=True));book.close()
        headers=list(raw[header_row-1]);rows=[dict(zip(headers,r)) for r in raw[header_row:] if any(v is not None for v in r)]
    else:
        with path.open(newline='',encoding='utf-8-sig') as handle:raw=list(csv.reader(handle))
        if len(raw)<header_row:raise ValueError('Header row missing')
        headers=raw[header_row-1];rows=[]
        for r in raw[header_row:]:
            if not any(r):continue
            if len(r)!=len(headers):raise ValueError('Row width differs from reviewed schema')
            rows.append(dict(zip(headers,r)))
    if len(set(headers))!=len(headers) or any(h in (None,'') for h in headers):raise ValueError('Duplicate/blank column names')
    return headers,rows



def header_hash(headers):
    return hashlib.sha256(json.dumps(list(headers),ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def parse(path,spec):
    required={'unit_id','name','latitude','longitude','status','capacity'}
    columns=spec.get('columns',{})
    if not required<=set(columns):raise ValueError('Explicit unit-level column map required')
    if not spec.get('source_version') or not spec.get('schema_review',{}).get('reviewer'):
        raise ValueError('Source version and schema review required')
    if spec.get('source')=='gem' and (not spec.get('tracker') or not spec.get('threshold_reviewed')):raise ValueError('GEM tracker threshold review required')
    if spec.get('source')=='eia' and 'plant_id' not in columns:raise ValueError('EIA generator ids need plant ids')
    headers,values=records(path,spec)
    if header_hash(headers)!=spec['schema_review'].get('header_sha256'):
        raise ValueError('Workbook headers changed; review the column contract')
    if not spec.get('status_values') or not spec.get('capacity_unit'):
        raise ValueError('Reviewed native status codes and capacity unit required')
    output=[]
    for native in values:
        val=lambda key:native.get(columns.get(key))
        identifier=val('unit_id');plant_id=val('plant_id')
        if not identifier:continue
        # Generator/unit identifiers can repeat between plants; namespace them by the site.
        identity=str(plant_id)+':'+str(identifier) if plant_id else str(identifier)
        row={'k':spec['source']+':'+spec.get('tracker',spec['source_version'])+':'+identity,
             'n':val('name'),'t':spec['type'],'record_level':'unit',
             'la':val('latitude'),'lo':val('longitude'),
             'external_ids':{spec['source']+':unit':identity},'s':spec['status_values'].get(str(val('status')))}
        if plant_id:row['external_ids'][spec['source']+':site']=str(plant_id)
        if 'country' in columns:row['c']=val('country')
        elif spec.get('country_scope',{}).get('reviewed') is True:
            row['c']=spec['country_scope']['name'];row['cc']=spec['country_scope']['iso2']
        else:row['_reject_reason']='country-not-sourced'
        if val('country_code'):row['cc']=val('country_code')
        if val('status_date'):row['status_date']=str(val('status_date'))[:10]
        # Only an explicitly reviewed commissioning/commercial-operation column is completion evidence.
        if val('commissioning_year'):
            try:row['completion_date']=str(int(val('commissioning_year')))
            except (ValueError,TypeError):row['_reject_reason']='invalid-commissioning-year'
        if val('planned_year'):
            try:row['ye']=int(val('planned_year'))
            except (ValueError,TypeError):row['_reject_reason']='invalid-planned-year'
        quality=val('coordinate_quality')
        if quality:row['coordinate_quality']=spec.get('coordinate_quality_values',{}).get(str(quality),'unknown')
        if val('coordinate_precision') is not None:row['coordinate_precision']=float(val('coordinate_precision'))
        try:row['la']=float(row['la']);row['lo']=float(row['lo']);row['cap']={'value':float(val('capacity')),'unit':spec['capacity_unit']}
        except (ValueError,TypeError):row['_reject_reason']='invalid-tabular-numeric-field'
        if spec.get('source')=='eia' and row.get('cap',{}).get('value',0)<spec.get('min_capacity_mw',50):row['_reject_reason']='below-reviewed-capacity-threshold'
        if val('owner'):row['own']=[{'name':str(val('owner')),'role':'owner'}]
        # No name-only LEI/company/asset matches, no guessed currency or conversion.
        if val('cost') is not None and val('currency') and val('cost_year'):
            row['cost']={'value':float(val('cost')),'currency':str(val('currency')),'year':int(val('cost_year'))}
        if not row.get('s'):row['_reject_reason']='unknown-native-status'
        if row.get('s') in ('Operational','Completed'):row['_explicit_operating']=True
        row['evidence']={'column_map':columns,'source_version':spec['source_version'],
                         'native_status':str(val('status')),'scope':spec.get('country_scope')}
        row['status_source']=spec['url']
        row['src']=[{'name':spec['name'],'url':spec['url'],'licence':spec['licence'],'checked_at':spec['checked_at'],
                     'field_list':sorted(k for k in row if not k.startswith('_'))}]
        output.append(row)
    return output
