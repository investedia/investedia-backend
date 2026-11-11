"""OurAirports reference sites require separately sourced development evidence."""
from .common import tabular
SOURCE = 'ourairports'
def parse(path, spec):
    return [r for r in tabular(path, spec) if r.get('airport_type') == 'large_airport' and r.get('development_evidence') is True]
