"""Owner's current-only eligibility. No status/date/precision is filled from build time."""
import datetime as dt
import math

DEVELOPMENT={'Proposed','Approved','Under construction','In development'}
EXCLUDED={'Cancelled','On hold','Decommissioned','Retired','Shelved'}


def current(row,asof,completed_since=2020,max_precision=.001):
    if row.get('_reject_reason'):raise ValueError(row['_reject_reason'])
    if row.get('validation_status')=='retained_unverified':raise ValueError('retained-snapshot-not-current-reviewed')
    precision=row.get('coordinate_precision')
    if row.get('coordinate_quality')!='exact':
        if not isinstance(precision,(float,int)) or not math.isfinite(precision) or not 0<precision<=max_precision:
            raise ValueError('coordinate-precision-unknown-or-coarse')
    # Four-decimal output must not disguise a two-decimal/integer source location.
    for key in ('la','lo'):
        if abs(float(row[key])*100-round(float(row[key])*100))<1e-7:raise ValueError('rounded-coordinate')
    status=row.get('s')
    if status in EXCLUDED:raise ValueError('excluded-status-'+status.lower().replace(' ','-'))
    if row.get('retirement_date') and row['retirement_date'][:4]<=asof[:4]:raise ValueError('retired-project')
    if row.get('status_date') and row['status_date']>asof[:len(row['status_date'])]:raise ValueError('future-status-date')
    if status in DEVELOPMENT:
        if row.get('status_date'):row['y']=int(row['status_date'][:4])
        row['display_status']='Under construction' if status=='Under construction' else 'In development'
    elif status in ('Completed','Operational'):
        completion=row.get('completion_date')
        if not completion:raise ValueError('completion-date-not-sourced')
        year=int(completion[:4])
        if year<completed_since:raise ValueError('completed-before-cutoff')
        if completion>asof[:len(completion)]:raise ValueError('completion-is-in-the-future')
        # A year-only event in this year does not itself prove that service has begun.
        if len(completion)==4 and year==int(asof[:4]) and not row.get('_explicit_operating'):
            raise ValueError('completion-not-confirmed-before-asof')
        row['s']='Completed';row['y']=year;row['display_status']='Completed '+str(year)
    else:raise ValueError('current-status-not-sourced')
    # These labels are derived from the cited status and completion event, not a new source.
    for source in row.get('src',[]):
        fields=source.get('field_list',[])
        if 's' in fields and 'display_status' not in fields:fields.append('display_status')
        if 'status_date' in fields and row.get('y') and 'y' not in fields:fields.append('y')
        if 'completion_date' in fields and row.get('y') and 'y' not in fields:fields.append('y')
    return row
