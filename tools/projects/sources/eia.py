"""EIA-860/860M explicitly mapped public spreadsheets. Generator rows are not plant totals."""
from .common import tabular
from ..status_map import normalize
SOURCE = 'eia'
def parse(path, spec):
    if spec.get("scale_v1"):
        from tools.projects.scale.tabular import parse as parse_scale
        return parse_scale(path,spec)
    return [r for r in tabular(path, spec) if r.get('cap', {}).get('unit') == 'MW'
            and r['cap']['value'] >= 50 and normalize(r.get('s')) in ('Proposed', 'Approved', 'Under construction')]
