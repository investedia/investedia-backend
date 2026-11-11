"""Explicit reviewed column maps; no inferred columns/units/currency/status."""
import csv
import json
from pathlib import Path


def records(path, spec):
    if Path(path).suffix == '.json':
        data = json.loads(Path(path).read_text())
        return data if isinstance(data, list) else data['rows']
    if Path(path).suffix in ('.xlsx', '.xlsm'):
        import openpyxl
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = book[spec['sheet']]
        rows = sheet.iter_rows(values_only=True)
        headers = next(rows)
        return [dict(zip(headers, r)) for r in rows]
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def tabular(path, spec):
    columns = spec['columns']
    required = {'source_id', 'n', 'la', 'lo', 'c'}
    if not required <= set(columns):
        raise ValueError('Reviewed source column map missing required fields')
    out = []
    for source in records(path, spec):
        row = {k: source.get(v) for k, v in columns.items() if source.get(v) not in ('', None)}
        if not row.get('source_id'):
            continue
        row.setdefault('t', spec.get('type'))
        # Review manifests may bind per-record verification, never a dataset-wide location guess.
        proof = spec.get('record_reviews', {}).get(str(row['source_id']), {})
        for field in ('development_evidence', 'precise_physical_location_verified', 'active_decommissioning_verified'):
            if proof.get(field) is True: row[field] = True
        # Nested facts must be supplied as structured values by an explicit mapping,
        # not reconstructed from a name, a fuel guess or a currency conversion.
        if spec.get('capacity_unit') and 'capacity' in row:
            row['cap'] = {'value': float(row.pop('capacity')), 'unit': spec['capacity_unit']}
        if 'cost_value' in row and spec.get('currency') and spec.get('cost_year'):
            row['cost'] = {'value': float(row.pop('cost_value')), 'currency': spec['currency'], 'year': spec['cost_year']}
        if row.get('owner'):
            row['own'] = [{'name': row.pop('owner'), 'role': spec.get('owner_role', 'owner')}]
        row['k'] = row.get('qid') or spec['source'] + ':' + str(row.pop('source_id'))
        row['src'] = [dict(name=spec['name'], url=spec['url'], licence=spec['licence'],
                           field_list=sorted(row), checked_at=spec['checked_at'])]
        out.append(row)
    return out
