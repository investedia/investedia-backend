"""Prediction Engine v4, step 7: expected move range (research/ENGINE-V4.md §8). Kept separate from direction: never used to judge a
View right or wrong. Frozen v4.0 table of base moves in units of sigma_h (the asset's daily volatility scaled to the horizon), set
before any v4 prediction; it is re-estimated only in a new version, from development data.
"""
import math

BASE = {'earnings': 1.5, 'guidance': 1.5, 'm&a': 2.0, 'financing': 1.0, 'analyst': 1.0, 'product': 0.8, 'legal-regulatory': 1.0,
        'management': 0.8, 'macro-data': 0.8, 'central-bank': 1.0, 'geopolitical': 1.0, 'commodity-supply': 1.0, 'trade-tariff': 1.0,
        'crypto': 1.0, 'other': 0.7}
STRONG_X = 1.5
HORIZON_DAYS = {'S1': 1.0, 'S2': 2.0, '6h': 0.25, '24h': 1.0, '48h': 2.0}


def expected(event_type, horizon, sigma_daily, direction, strong):
    """-> {sigma_h, move_sigma, low, high} (signed %, low/high = 0.5x / 1.5x of the expected move) or None without volatility."""
    if not sigma_daily or not horizon or direction not in ('long', 'short'): return None
    sh = sigma_daily * math.sqrt(HORIZON_DAYS.get(horizon, 1.0))
    m = BASE.get(event_type, 0.7) * (STRONG_X if strong else 1.0)
    sign = 1 if direction == 'long' else -1
    return {'sigma_h': round(sh, 3), 'move_sigma': round(m, 2), 'expected_pct': round(sign * m * sh, 2),
            'low_pct': round(sign * 0.5 * m * sh, 2), 'high_pct': round(sign * 1.5 * m * sh, 2)}
