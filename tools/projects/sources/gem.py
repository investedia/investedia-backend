"""Public GEM spreadsheets only; a reviewed per-tracker column/threshold map is required."""
from .common import tabular
SOURCE = 'gem'
def parse(path, spec):
    if spec.get("scale_v1"):
        from tools.projects.scale.tabular import parse as parse_scale
        return parse_scale(path,spec)
    if not spec.get('tracker') or not spec.get('threshold_reviewed'):
        raise ValueError('GEM tracker and its native inclusion threshold must be reviewed')
    return tabular(path, spec)
