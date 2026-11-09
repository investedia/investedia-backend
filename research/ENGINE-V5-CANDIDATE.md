# Prediction Engine v5 candidate: FROZEN before the held-out test

Frozen 2026-10-31, before the Oct 28–31 calls are judged (most are judged after the US open on Mon 2026-11-02).

## Rule (one change to v4, chosen on the TRAIN window only)
A v4 Market View (long or short) is published as a v5 View only when the price has **not already moved in the call's direction**
before publication: `direction × pre_move_sigma ≤ 0` (pre_move_sigma = the asset's move from the previous close to publication time,
in units of its own 20-day daily volatility; long = +1, short = −1). Views with no pre-move data are not published.
Everything else (extraction, policy POLICY_ID d996c058deb1, horizons, outcome-v4 judging) is unchanged.

Why: a call in the direction the price already moved is largely priced in. Owner approved tuning on the replay data on 2026-10-31.

## Train window (Oct 21–27, 252 judged v4 views): what this rule was chosen on
| | judged | accuracy |
|---|---|---|
| all v4 views | 252 | 54.4% |
| v5 rule (not priced in) | 114 | 64.9% |
| always long, same 114 | 114 | 65.8% |
| price reversal only (no news), all with pre-move | 244 | 60.7% |

Honest note: on train, v5 does **not** beat "always long" on its own subset. Train numbers are tuned and are not evidence.

## Held-out test (Oct 28–31): the only number that counts for this candidate
Judged with outcome-v4 once due. Report v5 accuracy, n, Wilson 95% CI, and on the same calls: always long, follow the index,
reversal only. v5 passes only if it beats all three on the test window. No change to the rule after this file is committed.
