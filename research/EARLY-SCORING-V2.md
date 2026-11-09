# Early calls: scoring framework v2 (frozen before scoring)

Frozen in git **before** any v2 accuracy was computed. Parameters are fixed here and in `tools/track/score_early_v2.py`
(`FROZEN` block); changing any of them requires a new version number. The original scoring (`research/pre-live-outcomes.json`,
`assets/globe/early-calls.json`) is kept unchanged for audit.

## Audit of the original (v1) scoring, 653 judged calls
| Issue | Found |
|---|---|
| Calls made while the asset's market was closed: baseline was the earlier close, so an overnight/after-hours move that could already be public was credited to the call | 371 |
| End price was the first print after a reopening (one opening auction tick) | 328 |
| Same asset + same direction with overlapping windows (correlated, counted as independent) | 173 |
| Moves between 0.3% and 1% counted as hit/miss regardless of the asset's normal volatility | 129 |
| One 24 h window for every event type (commodities/geopolitics move over days) | 104 calls in slow families |

## Framework v2
1. **Proven start T**: first commit that contains the call (unchanged).
2. **Entry = first traded price at or after T** in the asset's own exchange session (5-minute bars). A reader could not have traded
   before T, so overnight gaps that happened before T are never credited. No traded price within 4 days of T: unresolved.
3. **Event-specific horizon H** from the entry:
   - 24 h: earnings, guidance, m&a, capital, regulation, rates, macro-data, labor, crypto, other;
   - 72 h: commodity-prices, energy-supply, geopolitics, trade.
4. **Exit = the session close at or after entry + H**: the last traded price of the first session that ends after entry + H
   (a whole session, not one opening print). Markets without a daily session close (crypto, and FX/futures whose bars run more than
   20 h without a 2 h break) use the first traded price at or after entry + H. *(Clarified in a second commit before any scoring:
   the first version would have slid FX/futures exits to the end of the trading week.)*
   No exit within 4 days after entry + H: unresolved; not yet reached: pending.
5. **Meaningful move**: |move| ≥ max(0.3%, 0.5 × σ_d × √(H / 24 h)), σ_d = standard deviation of the asset's daily returns over the
   20 trading days before T (daily closes). Smaller moves are **no clear move** (not counted as hits or misses).
6. **One outcome per correlated cluster**: calls on the same asset in the same direction whose windows overlap an earlier kept call's
   window [entry, exit] are collapsed into that earliest call (kept on record, marked `collapsed_into`, excluded from statistics).
   Opposite-direction calls on the same asset are not collapsed.
7. **Verdict**: hit if the move is meaningful and in the called direction, miss if meaningful and opposite.
8. **Statistics**: accuracy = hits / (hits + misses); Wilson 95% interval; exact two-sided binomial test against 50%;
   naive baselines "always long" and "always short" on the same calls.

Not possible for early calls: confidence (no confidence was stamped before 29 Oct).
