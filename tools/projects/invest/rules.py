"""Public eligibility rules for the Projects investment layer (owner decisions, 12 Nov 2026).

A project is public only when every base rule passes and at least one exposure to a listed
company is verified in the ledger. Nothing here estimates or fills in a value: unknown stays None.
"""
from datetime import date

PUBLIC_CATEGORIES = {'A', 'B'}  # owner decision 12 Nov 2026: A company-confirmed, B regulator-confirmed
PIPELINE = {'Announced', 'Pre-construction', 'Under construction', 'Commissioning'}
MAX_AGE_DAYS = {'Energy & Utilities': 183}
DEFAULT_MAX_AGE_DAYS = 365
# A link document must be a primary source. Aggregators can point to evidence but are not evidence.
NOT_PRIMARY = ('gem.wiki', 'globalenergymonitor.org', 'wikipedia.org', 'wikidata.org')


def _days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def exposure_problems(exposure, record, today):
    """Reasons a candidate exposure is not verified. Empty list means verified."""
    if not record:
        return ['no verification record']
    out = []
    if record.get('category', 'A') not in PUBLIC_CATEGORIES:
        out.append('category %s is never public' % record.get('category'))
    if record.get('internal_only'):
        out.extend(record['internal_only'])
    ident = record.get('identity') or {}
    if ident.get('scheme') not in ('LEI', 'CIK') or not ident.get('id') or not ident.get('source_url'):
        out.append('legal entity not confirmed (LEI or CIK with registry URL)')
    listing = record.get('listing') or {}
    if not listing.get('ticker') or not listing.get('exchange') or not listing.get('source_url'):
        out.append('listing not confirmed (ticker, exchange, source)')
    links = [l for l in record.get('link') or [] if l.get('url') and l.get('retrieved_at') and l.get('proves')]
    primary = [l for l in links if not any(h in l['url'] for h in NOT_PRIMARY)]
    if not primary:
        out.append('no primary document for the project-to-company link')
    # A listed parent's own publication stating its interest in the project proves the indirect exposure itself.
    if exposure['type'] == 'E3' and not record.get('company_states_interest'):
        proved = {tuple(l['edge']) for l in primary if l.get('edge')}
        missing = [e for e in exposure['path_edges'] if tuple(e) not in proved]
        if missing:
            out.append('parent chain not fully documented: %d link(s) missing' % len(missing))
    if exposure['type'] == 'E4' and not record.get('company_calls_material'):
        out.append('contract not described as material by the company itself')
    if exposure['type'] == 'E5':
        out.append('direct offerings are switched off')
    if not record.get('reviewer') or not record.get('verified_at'):
        out.append('no reviewer or verification date')
    elif _days(record['verified_at'], today) > MAX_AGE_DAYS.get(exposure.get('sector'), DEFAULT_MAX_AGE_DAYS):
        out.append('verification expired')
    return out


def evaluate(project, exposures, ledger, today):
    """Return (public, reasons, verified_exposures) for one research record."""
    reasons = []
    if not project.get('source', {}).get('licence'):
        reasons.append('no licensed source')
    if project.get('stage') not in PIPELINE:
        reasons.append('not in the development pipeline')
    if project.get('precision') not in ('exact', 'approximate'):
        reasons.append('no usable location')
    if project.get('lat') is None or project.get('lon') is None or not project.get('cc'):
        reasons.append('missing coordinates or country code')
    verified = []
    for e in exposures:
        key = '%s|%s' % (project['id'], e['listed_entity_id'])
        if not exposure_problems(dict(e, sector=project.get('sector')), ledger.get(key), today):
            verified.append(dict(e, verification=ledger[key]))
    if not verified:
        reasons.append('no verified exposure to a listed company')
    return (not reasons, reasons, verified)
