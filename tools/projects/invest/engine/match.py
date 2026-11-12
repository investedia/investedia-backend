"""Match document rows to research candidates: name tokens, exact phase numbers, country, capacity."""
import re

GENERIC = {'power', 'station', 'plant', 'solar', 'farm', 'wind', 'ipp', 'iwpp', 'iwp', 'iwspp', 'project', 'complex', 'cc', 'ccgt',
           'phase', 'the', 'pv', 'park', 'independent', 'producer', 'csp', 'energy', 'renewable', 'hybrid', 'co', 'and', 'of',
           'electric', 'electricity', 'bess', 'storage', 'battery', 'onshore', 'offshore', 'floating', 'hydro', 'hydroelectric',
           'cluster', 'facility', 'gas', 'thermal'}


def core(s):
    s = re.sub(r'\b\d+(\.\d+)?\s*(mw|gw|mwh)\b', ' ', (s or '').lower())  # capacities are not phase numbers
    s = re.sub(r'([a-z])(\d)', r'\1 \2', s.replace('-', ' '))
    s = re.sub(r'\biii\b', '3', re.sub(r'\bii\b', '2', re.sub(r'\bi\b', '1', s)))
    return [w for w in re.sub(r'[^a-z0-9 ]', ' ', s).split() if w not in GENERIC]


def nums(t):
    return {w for w in t if w.isdigit()}


def country_ok(row_name, country, comma_country=True):
    """If the document format puts the country after a comma ('Thakadu, South Africa'), it must agree."""
    if not comma_country or ',' not in (row_name or ''):
        return True
    tail = row_name.rsplit(',', 1)[1].strip().lower()
    c = (country or '').lower()
    return not tail or tail[:5] in c or c[:5] in tail or tail.startswith('philip') and c.startswith('philip')


def name_part(row_name, comma_country=True):
    return row_name.rsplit(',', 1)[0] if comma_country and row_name and ',' in row_name else row_name


def candidates_for(row, projects, company_tokens=()):
    """Research projects the row names. 'exact': every distinctive document word is in the project name.
    'loose': every distinctive project word is in a wordier document name; only kept when capacity agrees
    (checked by the classifier). Company names in brackets, e.g. '(NHPC)', are ignored."""
    drop = {t.lower() for t in company_tokens}
    cc = row.get('comma_country', False)
    rc = [w for w in core(name_part(row['doc_name'], cc)) if w not in drop]
    words = set(rc) - nums(rc)
    if not words:
        return []
    out = []
    for p in projects:
        pc = [w for w in core(p.get('plant_name') or p['name']) if w not in drop]
        if p.get('phase'):
            pc = pc + [str(p['phase'])]
        pw = set(pc) - nums(pc)
        if not (country_ok(row['doc_name'], p['country'], cc) and location_ok(row, p)) or not pw:
            continue
        if p.get('phase') and not nums(rc) and words <= set(pc):
            out.append((p, 'whole'))  # document names the whole plant; the batch checks the phases add up
            continue
        if nums(rc) != nums(pc) and not (not nums(pc) and nums(rc)):
            continue
        kind = 'exact' if words <= set(pc) else 'loose' if pw <= set(rc) else None
        if kind:
            if nums(rc) and not nums(pc):
                kind = 'expansion' if p.get('expansion') else 'phase'  # 'expansion' must agree on capacity
            out.append((p, kind))
    return out


US_STATE = re.compile(r'^US-([A-Z]{2})$')


def location_ok(row, project):
    """Rows that carry a location ('US-VA', 'Chile') must agree with the project's state or country."""
    loc = row.get('location')
    if not loc:
        return True
    st = US_STATE.match(loc)
    if st:
        return project.get('cc') == 'US' and project.get('state') == st.group(1)
    if loc.startswith('US-'):
        return False  # 'US-Various' cannot identify a site
    return (project.get('country') or '').lower().startswith(loc.lower()[:5])
