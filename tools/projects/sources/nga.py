"""NGA ports require individually reviewed infrastructure-development evidence."""
from .common import tabular
SOURCE = 'nga'
def parse(path, spec):
    return [r for r in tabular(path, spec) if r.get('size') in ('L', 'M') and r.get('development_evidence') is True]
