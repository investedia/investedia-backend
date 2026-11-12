"""Deterministic extractors. Each returns rows: {doc_name, pct, mw, cod, section, line, passage}.

table: a layout spec per document family (regex with named groups, optional multi-line name window,
       optional section by column). prose: sentences that name a project together with an ownership verb.
No value is inferred: a missing stake stays None.
"""
import re


def _num(s):
    return None if s in (None, '', '-') else float(s.replace(',', ''))


def table(text, spec):
    lines = text.split('\n')
    row = re.compile(spec['row'])
    out = []
    hits = []
    cont = re.compile(spec['continuation']) if spec.get('continuation') else None
    extra = {}
    for i, l in enumerate(lines):
        for m in (row.finditer(l) if spec.get('multi') else [row.match(l)]):
            if m:
                hits.append((i, m))
        if cont and hits and not row.match(l):
            c = cont.match(l.strip())
            if c and i - hits[-1][0] <= 3:  # component line right under a project row (e.g. 'Energy Storage 500')
                extra.setdefault(hits[-1][0], []).append((c.group('tech'), _num(c.group('mw'))))
    for k, (i, m) in enumerate(hits):
        g = m.groupdict()
        name = (g.get('name') or '').strip()
        if spec.get('name_window'):  # names wrapped over several lines in the first column (ACWA layout)
            w, prev = spec['name_window'], hits[k - 1][0] if k else None
            nxt = hits[k + 1][0] if k + 1 < len(hits) else None
            lo = max((prev + i) // 2 + 1 if prev is not None else i - 3, i - 3, 0)
            hi = min((i + nxt) // 2 if nxt is not None else i + 3, i + 3, len(lines) - 1)
            frag = [lines[j][:w].strip() for j in range(lo, hi + 1)]
            name = re.sub(r'\s+', ' ', ' '.join(f for f in frag if f and not re.fullmatch(r'[\d.,%-]+', f))).replace('- ', '')
            ctx = lines[lo:hi + 1]
        else:
            ctx = [m.group(0)] if spec.get('multi') else [lines[i]]
        if len(name) > 70:
            continue  # footnote text caught by the row pattern, not a project name
        section = None
        for start, label in spec.get('sections_by_column', []):
            if m.start() >= start:
                section = label
        cod = re.search(spec.get('cod', r'Q[1-4] 20\d\d'), lines[i])
        comps = [(g.get('tech'), _num(g.get('mw')))] + extra.get(i, [])
        mw = sum(x[1] for x in comps if x[1]) if g.get('mw') else None
        out.append({'doc_name': re.sub(r'\s+', ' ', name).strip(' ,'), 'pct': _num(g.get('pct')), 'mw': mw, 'components': comps,
                    'location': (g.get('loc') or '').strip() or None, 'comma_country': bool(spec.get('comma_country')),
                    'cod': cod.group(0) if cod else None, 'section': section or spec.get('section'), 'line': i + 1,
                    'passage': ' / '.join(c.strip() for c in ctx if c.strip())[:500]})
    return out


OWN = re.compile(r'\b(we are building|is building|are building|builds|owns|stake|interest|developing|develops|to construct|construct and operate|is constructing|baut|errichtet|Beteiligung)\b', re.I)


def prose(text, company_words):
    """Sentences mentioning the company (or 'we/our') and an ownership verb, with any MW / % figures."""
    out = []
    for i, s in enumerate(re.split(r'(?<=[.!?])\s+|\n', text)):
        if len(s) < 25 or not OWN.search(s):
            continue
        if not (any(w.lower() in s.lower() for w in company_words) or re.search(r'\b(we|our)\b', s, re.I)):
            continue
        mw = re.search(r'([\d.,]+)\s*(MW|megawatts)', s, re.I)
        pct = re.search(r'(\d{1,3}(?:\.\d+)?)\s*%', s)
        out.append({'doc_name': None, 'sentence': s.strip()[:500], 'pct': _num(pct.group(1)) if pct else None,
                    'mw': _num(mw.group(1)) if mw else None, 'cod': None, 'section': None, 'line': i + 1, 'passage': s.strip()[:500]})
    return out


def prose_for(text, project_name, core, company_words=(), window=4):
    """Project pages spread facts over sentences. Accept only when a sentence names the company with an
    owner/builder verb AND the project's distinctive name words occur within `window` sentences of it.
    Returns the passage (window text) and any MW / % figures in it."""
    words = {w for w in core(project_name) if not w.isdigit()}
    if not words:
        return None
    sents = [x.strip() for x in re.split(r'(?<=[.!?])\s+|\n', text) if x.strip()]
    for i, s in enumerate(sents):
        if not OWN.search(s) or not any(c.lower() in s.lower() for c in company_words):
            continue
        lo, hi = max(0, i - window), min(len(sents), i + window + 1)
        win = sents[lo:hi]
        if not words <= set(w for x in win for w in core(x)):
            continue
        blob = ' '.join(win)
        mw = re.search(r'([\d.,]+)\s*(?:MW|megawatts|Megawatt)\b', blob, re.I)
        pct = re.search(r'(\d{1,3}(?:[.,]\d+)?)\s*(?:%|percent|Prozent)', blob, re.I)
        mwv = mw.group(1).replace('.', '').replace(',', '.') if mw and re.fullmatch(r'\d{1,3}(\.\d{3})+', mw.group(1)) else (mw.group(1) if mw else None)
        cost = re.search(r'(?:expected to cost|estimated (?:total )?cost of|total cost of|cost of approximately|capital cost of)\s+(?:approximately\s+)?(\$|€|EUR\s?|USD\s?)([\d.,]+)\s*(billion|million)', blob, re.I)
        cost_v = {'amount': float(cost.group(2).replace(',', '')) * (1e9 if cost.group(3).lower() == 'billion' else 1e6),
                  'currency': 'USD' if '$' in cost.group(1) or 'USD' in cost.group(1) else 'EUR', 'basis': 'company estimate',
                  'quote': cost.group(0)} if cost else None
        return {'doc_name': project_name, 'prose': True, 'cost': cost_v, 'pct': _num(pct.group(1).replace(',', '.')) if pct else None, 'mw': _num(mwv),
                'cod': None, 'section': None, 'line': i + 1, 'passage': blob[:600]}
    return None


def html_table(raw_html, spec):
    """Rows from <tr>/<td> cells. spec: name_cell, mw_cells (first parsable wins), strip (regex removed from
    the name, e.g. trailing state names), section, jv_marker (regex flagging joint ventures)."""
    import html as H
    out = []
    for i, tr in enumerate(re.findall(r'(?is)<tr[^>]*>(.*?)</tr>', raw_html)):
        cells = [re.sub(r'\s+', ' ', H.unescape(H.unescape(re.sub('<[^>]+>', ' ', c)))).strip()
                 for c in re.findall(r'(?is)<t[dh][^>]*>(.*?)</t[dh]>', tr)]
        if len(cells) <= spec['name_cell'] or not cells[spec['name_cell']] or re.match(r'(?i)name of project|total', cells[spec['name_cell']]):
            continue
        name = cells[spec['name_cell']]
        mw = None
        for j in spec.get('mw_cells', []):
            if j < len(cells):
                m = re.fullmatch(r'([\d.,]+)\s*(MW)?', cells[j].replace(' ', ''), re.I)
                if m:
                    mw = _num(m.group(1))
                    break
        jv = bool(re.search(spec['jv_marker'], name)) if spec.get('jv_marker') else False
        if spec.get('strip'):
            name = re.sub(spec['strip'], '', name).strip(' ,')
        out.append({'doc_name': name, 'pct': None, 'mw': mw, 'cod': None, 'section': spec.get('section'), 'line': i + 1,
                    'joint_venture': jv, 'passage': ' | '.join(cells)[:400]})
    return out
