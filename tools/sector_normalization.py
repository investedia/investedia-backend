"""Offline editorial taxonomy; original labels are never overwritten."""
import json
import re
from pathlib import Path
TAXONOMY = json.loads((Path(__file__).resolve().parents[1] / 'data/sector-taxonomy.json').read_text())
SECTORS = tuple(TAXONOMY['sectors'])

def normalize_sector(raw, sic=None):
    """Exact reviewed SIC mapping takes precedence; no fuzzy or range inference."""
    key = re.sub(r"\s+", " ", raw.strip()).casefold() if isinstance(raw, str) else ''
    sector = TAXONOMY['aliases'].get(key)
    basis = 'label' if sector else None
    if isinstance(sic, str) and re.fullmatch(r"\d{4}", sic) and sic in TAXONOMY['sic']:
        sector, basis = TAXONOMY['sic'][sic], 'SEC SIC'
    return {'sector': sector, 'raw': raw, 'basis': basis}
