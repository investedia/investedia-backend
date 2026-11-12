"""A/B/C/D classification with safeguards. Only A (and B where approved) may become public.

A  company-confirmed: an official publication of the listed company (or its subsidiary) names the project
   and the relationship. B  regulator-confirmed: a government source names the owner and official registries
   confirm the current listed parent. C  research candidate. D  contradicted.
"""
from datetime import date

FINANCIAL = ('bank', 'groep', 'blackstone', 'capital', 'fund', 'asset management', 'investment', 'insurance', 'kkr',
             'macquarie group', 'allianz', 'bnp', 'hsbc', 'jpmorgan', 'mizuho', 'mitsubishi ufj', 'sumitomo mitsui')
MAX_DOC_AGE_DAYS = 548  # 18 months


def quarter_end(q):
    """'Q3 2027' or '2H 2026' / '1H-2H 2026' / '2H 2027 - 1H 2028' -> last day bucket of the EARLIEST period named."""
    import re
    m = re.search(r'Q([1-4]) (20\d\d)', q)
    if m:
        return date(int(m.group(2)), int(m.group(1)) * 3, 28)
    m = re.search(r'([12])H\D{0,6}?(20\d\d)', q)
    return date(int(m.group(2)), 6 if m.group(1) == '1' else 12, 28)


def safeguards(exposure):
    """Reasons that keep an otherwise verified relationship internal (owner decisions 12 Nov 2026)."""
    out = []
    if (exposure.get('hq_country') or '') == 'Russia':
        out.append('russian-listed company: internal only (owner decision)')
    if any(w in (exposure.get('listed_name') or '').lower() for w in FINANCIAL):
        out.append('bank or fund as the only listed link: internal only (owner decision)')
    return out


def classify(project, exposure, row, match_kind, doc, today):
    """Return (category, reasons, stake). Never invents a stake: only the document's stated value."""
    reasons = []
    age = (date.fromisoformat(today) - date.fromisoformat(doc['date'])).days
    if age > MAX_DOC_AGE_DAYS:
        return 'C', ['document older than 18 months: needs a newer source'], None
    if match_kind == 'phase':
        return 'C', ['document lists phases (%s); the GEM plant must be split by phase first' % row['doc_name']], None
    if row.get('prose') and not (row.get('mw') and project.get('mw')):
        return 'C', ['prose passage states no capacity to confirm the project'], None
    if match_kind == 'loose' and not (row.get('mw') and project.get('mw')):
        return 'C', ['name match is partial and capacity cannot confirm it'], None
    if row.get('mw') and project.get('mw') and not (0.85 <= row['mw'] / project['mw'] <= 1.15):
        return 'C', ['capacity differs: document %s MW vs GEM %s MW' % (row['mw'], project['mw'])], None
    gem = exposure.get('effective_stake')
    if row.get('pct') is not None and gem is not None and abs(row['pct'] - gem) > 0.6:
        return 'C', ['stake conflict: company %s%% vs GEM %s%% (not resolved automatically)' % (row['pct'], gem)], None
    if row.get('cod') and quarter_end(row['cod']) <= date.fromisoformat(doc['date']):
        return 'D', ['company start date %s is on or before the document date: operating, not pipeline' % row['cod']], None
    if (row.get('section') or '').lower().startswith(('in operation', 'power station', 'operating')):
        return 'D', ['company lists it as in operation'], None
    if doc['kind'] == 'company':
        return 'A', ['named in the company publication' + (' with %s%%' % row['pct'] if row.get('pct') is not None else '')], row.get('pct')
    if doc['kind'] == 'regulator':
        return 'B', ['named by the regulator'], row.get('pct')
    return 'C', ['source is not an official company or regulator publication'], None
