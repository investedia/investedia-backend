"""Frozen 2021 fallback facts only; never replace newer project facts."""
from .common import tabular
SOURCE = 'wri'
def parse(path, spec):
    if spec.get('as_of') != '2021': raise ValueError('WRI must be explicitly labelled as of 2021')
    return tabular(path, spec)
