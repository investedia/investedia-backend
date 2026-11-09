# Live Prediction Track Record: outcome rule versions

Every judged live call stores the rule it was judged with (`rule`). Earlier verdicts are kept on the call (`prev`, `prev_v2`).
Prediction fields (direction, asset, created/public/start times, engine version, confidence) are frozen and never rewritten.

| Rule | In force | Entry (baseline) | End | Notes |
|---|---|---|---|---|
| outcome-v1 | 29 Oct 2026 – 31 Oct 09:16 UTC | first price recorded by the 15-minute recorder after creation | first recorded price ≥ 24 h later, within 48 h | stranded weekend calls |
| outcome-v2 | 31 Oct 09:16 – 31 Oct 2026 | prevailing traded price at the proven public start (last bar at or before it) | first traded price ≥ 24 h after start, within 4 days | could credit an overnight/after-hours move that happened before publication |
| **outcome-v3** | **from 31 Oct 2026, before 50 judged calls** | **first traded price at or after the proven public start** | first traded price ≥ 24 h after the entry, within 4 days | no move before publication is ever credited; adds the market-index benchmark |

Common to all: start = max(created_at, first provable public time); hit/miss need a move of at least 0.3% in/against the called direction;
smaller moves are "no clear move"; moves over 50% are price-series breaks (void). One live record uses one rule: moving to v3 re-scored all
live calls (v2 verdicts kept under `prev_v2`), decided before any v3 result was seen.

Benchmarks shown with the record: always long, random 50/50 (exact binomial test), and the market index over the same window
(does the call beat simply following the market?).
