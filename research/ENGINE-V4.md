# Prediction Engine v4: design and frozen rules

Status: **design frozen 2026-10-31, before any v4 prediction exists.** Changing a rule in §5–§8 after the first v4 call
requires a new engine version (v4.1, …) recorded on every call. Public name: *Investedia Prediction Model · Prediction Engine v4*
(internal id `pe-v4`). Engine v3 (ranked impact tiers, branch `asset-intel`) was never released; its tiering is folded into v4.

## 1. Audit of the current live engine (Prediction Engine v2, `impact-gemini-v2`)

| Step | What happens today |
|---|---|
| Article → event | Gemini, per robot run, merges candidate headlines of the same batch ("members"); `news_core.dedupe` drops near-identical titles. No stable cross-run event id yet (event-id work in review). |
| Assets | Gemini lists ≤6 "impacts" (company/asset/sector/country), primary/secondary role; tickers resolved by the registry; sector/country rows are never scored. |
| Direction | Gemini writes `up/down/mixed/unclear` per impact from the article text. Only `up/down` with a resolved asset becomes a call. |
| Magnitude | **None.** |
| Confidence | Gemini's own `high/medium/low` label. Never calibrated; 120 of 176 live calls are "high". |
| Event type | Gemini `event_type` (14 values). Stored on the story, **not used by any logic**, not frozen on the call. |
| Horizon | Fixed 24 h for everything. |
| Market context | **None**: the prompt sees headline + short description only; no prices, no index, no prior move. |
| Duplicates | Every article's impacts are frozen separately: one story covered by 10 articles = 10 calls (Binance hack: 25 articles). |
| Abstention | Only implicit: `mixed/unclear`, unresolved tickers, sector/country rows. No "no call" decision, no reasons. |
| Outcome | outcome-v3: entry = first traded price after the proven public time; end = first traded price ≥ 24 h later; ±0.3 % flat band; index benchmark stored. |
| Frozen at creation | article id, symbol, asset id, direction, confidence label, created/public/start, engine version, model, headline, category, article time. |
| Used by | Market Implications and Track Record read the same ledger (`news-ledger.json`); Early calls are a separate file. |

**Five biggest weaknesses limiting real edge**
1. **No expectations.** Direction comes from how the article *sounds*, not from actual vs expected. Markets price surprises.
2. **No market context.** The engine cannot know the asset already moved, the index moved more, or volatility is high; "Bitcoin falls after hack" is called *after* the fall.
3. **Forced calls.** Commentary, previews, price-move recaps and indirect relationships still become directional calls; nothing abstains on purpose.
4. **Correlated duplicates.** One event produces many "independent" calls, inflating both wins and losses and any accuracy figure.
5. **Uncalibrated, unused metadata.** Confidence is a label, event type and horizon are not used, magnitude does not exist, so there is nothing to tune *honestly* and nothing to calibrate.

Measured evidence: the first engine scored 52.7 % (v2 historical method, p = 0.44 vs a coin flip) and lost to "follow the index"
(51.9 % vs 62.5 %, p = 0.03). The live engine has 17 judged calls: too few to say anything yet.

## 2. Architecture of v4 (shadow first, then promotion)

```
article ─► [1 extract]  LLM → structured record (no direction decision):
                         event_type (15 classes), catalyst facts with numbers *as stated*, expectation fields
                         (actual / expected / previous, or "unavailable"), relationship directness per asset,
                         flags: commentary, preview, price-move recap, competing catalysts, already-priced language,
                         LLM stance per asset (+/−/0) with a one-line reason
         ─► [2 resolve]  registry ids; asset class; benchmark index + sector ETF
         ─► [3 identity] stable event id (event_ids.py); one decision per event × asset × horizon
         ─► [4 context]  code, from prices at publication: asset move since previous close and last 24 h, in σ units;
                         index and sector move; 5-day trend; 20-day volatility; session state (open / pre / after / closed)
         ─► [5 decide]   deterministic policy table per event type: direction = Long | Short | No View, with the
                         reason codes for every abstention; raw score from frozen feature weights
         ─► [6 confidence] raw score → probability through a calibration map fitted on VALIDATION only, then frozen
         ─► [7 magnitude] expected move range = event-type × asset-class base (in σ), scaled by catalyst strength
         ─► [8 freeze]   full prediction record (§9) → shadow ledger; published to the site only after promotion
```
The LLM never decides publication. Direction, abstention, confidence and horizon are code + frozen tables, so every call is reproducible.

## 2a. Products (one engine, three outputs; never blurred)
| Product | Question | Nature |
|---|---|---|
| **Market Views** | "What does Investedia expect this event to do?" | broad, frequent, event-driven, hours to two sessions; free layer and the main forward dataset |
| **Priority Insights** | "Which current Views have unusually strong evidence?" | a labelled **subset** of Market Views (`view_tier: priority`), never a separate engine; candidate Pro feature |
| **Long-Term Outlooks** | "What is Investedia's longer-term thesis on this asset?" | fundamental, 1–12 months; separate engine, records and Track Record (research/LONG_TERM_OUTLOOKS.md) |

Objective: **maximise predictive quality subject to useful coverage**, not "as few predictions as possible".
Decision ladder: **No View → Market View → Priority Insight**, with three separate thresholds:
- *No-View rules*: obvious garbage only (§6); everything else with a direction is a candidate View.
- *View threshold*: minimum calibrated confidence to publish an View; chosen on validation to keep **60–80 % coverage of
  eligible events** unless forward data shows another range is better (§11).
- *Priority threshold*: much stronger evidence; deterministic gates on structured v4 features (§8a) plus a calibrated
  confidence threshold chosen on validation. LLM-stated confidence never makes anything Priority.
Wording stays informational and analytical (Market View, Priority Insight, Long-Term Outlook, directional outlook, expected
market impact, confidence, catalyst). Never "buy/sell now", "best trade", "you should invest", position sizing, or anything
personalised to a user's portfolio or risk tolerance. Payment restrictions are not implemented; Priority Insights run in shadow.

## 3. Versions (kept separate on every record)
- `engine`: pe-v4 (and `prompt` hash, `model` name). Existing v1/v2 calls stay frozen, untouched.
- `outcome_rule`: outcome-v4 for v4 calls (variable horizon, class floors, relative moves). v2 calls keep outcome-v3.
- `policy`: hash of the frozen tables in `engine/policy.py`; `calibration`: id of the frozen calibration map.

## 4. Event taxonomy (15)
earnings · guidance · m&a · financing (debt/equity raise, buyback) · analyst (rating/target change) · product (launch, contract) ·
legal-regulatory · management · macro-data · central-bank · geopolitical · commodity-supply · trade-tariff · crypto · other.

## 5. Horizon table (frozen; from the entry price)
"S1" = close of the first full trading session after entry; "S2" = close of the second. 24/7 and near-24 h markets use hours.

| Event type | Equity | Index | FX | Commodity | Crypto |
|---|---|---|---|---|---|
| earnings, guidance, financing, management | S1 | S1 | — | — | — |
| m&a | S1 (target), S2 (acquirer) | — | — | — | — |
| analyst | S2 | — | — | — | — |
| product, legal-regulatory | S1 | — | — | — | 24 h |
| macro-data | S1 | S1 | 6 h | 6 h | 6 h |
| central-bank | S1 | S1 | 24 h | 24 h | 24 h |
| geopolitical, trade-tariff | S2 | S2 | 48 h | 48 h | 48 h |
| commodity-supply | S2 | S2 | 48 h | 48 h | — |
| crypto | — | — | — | — | 24 h |
| other | S1 | S1 | 24 h | 24 h | 24 h |
"—" = this combination does not produce calls in v4 (abstain: `unsupported-combination`).

## 6. No-View rules (frozen; any one ⇒ No View, reason code stored)
Only obvious garbage: `commentary` · `preview` · `price-move-recap` (mainly reports a move, no new catalyst) · `indirect` (relationship
not subject/target/acquirer/issuer/direct counterparty/policy-rate/commodity-output) · `competing-catalysts` (genuinely ambiguous) ·
`stance-neutral` (no direction) · `unsupported-combination` (§5 "—") · `duplicate-event` (event × asset × horizon already covered) ·
`priced-in` (asset already moved ≥ 3 σ in the called direction before publication) · `below-view-threshold` (only once the
validation-chosen View threshold exists).
Missing expectations do **not** cause a No View: such events can be Views (direction from the stance), never Priority.

## 7. Direction policy (frozen)
- With expectations (earnings, guidance, macro-data, central-bank): direction = sign of the surprise when |surprise| ≥ the
  type's floor (EPS/revenue 2 %, guidance midpoint 1 %, macro 0.5 × the series' historical surprise σ when available, else any
  non-zero beyond rounding, rates 10 bp); conflicting surprises (e.g. EPS beat, revenue miss) ⇒ the guidance sign if stated,
  else `competing-catalysts`. Asset mapping: equities the company; macro/central-bank: currency (higher-than-expected
  inflation/rates ⇒ currency long), index (⇒ short), gold (⇒ short).
- Without expectations, or for expectation types whose expectations are unavailable (View only), (m&a, financing, analyst, product, legal, management, geopolitical, commodity, trade, crypto, other):
  direction = LLM stance only if directness passes and no abstention rule fires; m&a targets of cash offers at a premium ⇒ long
  target; equity raise ⇒ short issuer; downgrade ⇒ short, upgrade ⇒ long.
- Context never flips a direction; it can only cause abstention (`already-moved`) or lower the score.

## 8. Score, confidence, magnitude (frozen form; numbers fitted on validation only)
- Raw score = sum of frozen points: expectations surprise used (+2), |surprise| ≥ 2× floor (+1), strong catalyst (+1, §8a table),
  direct relationship (+1), single catalyst (+1), not already moving ≥ 1.5 σ the called way (+1), LLM stance agrees with the surprise (+1).
- Confidence = calibration map(raw score, event-type group), isotonic, fitted on validation, then frozen. Buckets 50–59, 60–69, 70–79,
  80–89, 90+; a bucket is only shown with ≥ 30 judged calls.
- Expected move: base |move| = m(event type, class) × σ_h (σ_h = 20-day daily σ × √(horizon in days)), m from the development set,
  × 1.5 when the catalyst is strong or |surprise| ≥ 2× floor; reported as a range [0.5×, 1.5×] with the direction's sign.
  `expected_move_sigma` = expected |move| / σ_h. Never used to judge direction.

## 8a. Priority Insight gates (deterministic, all required; failed gates stored in `priority_missing`)
`direct-subject` (subject, target, issuer, policy-rate, commodity-output) · `evidence` (expectation types: surprise used and
|surprise| ≥ 2× floor; other types: a strong numeric catalyst — m&a premium ≥ 15 %, financing ≥ 5 % of market cap, legal amount
≥ 1 % of market cap, product/contract ≥ 5 % of revenue, analyst ≥ 1 rating notch, commodity/geopolitical supply ≥ 1 % of supply,
tariff change ≥ 10 pts, crypto ≥ $1 bn; missing numbers = not strong) · `single-catalyst` · `not-priced-in` (< 1.5 σ already moved
the called way) · `context-supports` (index and sector not already ≥ 1 σ against the call) · `move-above-noise` (expected move
≥ 1 σ_h) · `data-complete` (context fields present) · `type-enabled` (after ≥ 30 judged Views of the type, its View accuracy
must beat follow-the-index on validation; until then pending, recorded) · `priority-confidence` (≥ the validation-chosen Priority threshold).

## 9. Prediction record (frozen at creation; outcome fields appended, never overwritten)
prediction id · event id · article id · asset id/symbol · asset class · event type · created / public / start · engine, prompt,
policy, calibration ids · decision (long/short/none) + reason codes · `view_tier` (none/standard/priority) + `priority_missing` · raw score · confidence · expected move range · horizon code ·
benchmark index + sector ETF · catalyst fields (surprise %, premium %, size % of market cap, bp…) with explicit `null` = unavailable ·
expectations-available flag · context fields (pre-publication move σ, index/sector move, trend, vol, session) ·
then outcome-v4: entry, exit, asset move, index move, sector move, relative move, verdict, magnitude error.

## 10. Outcome rule outcome-v4 (for v4 calls)
Entry = first traded price at or after the proven public time. Exit per §5 (S1/S2 = session close; hours = first price at or after).
Verdict: |move| < max(class floor, 0.5 σ_h) ⇒ no clear move; else hit/miss by sign. Class floors: equity 0.3 %, index 0.2 %, FX 0.1 %,
commodity 0.3 %, crypto 0.5 %. Also stored: index move, sector move, relative move = asset − benchmark (second metric: event alpha).

## 11. Evaluation (no tuning on the holdout)
- **Development** (design only): early calls 21–30 Oct, live v2 calls, and a v4 *replay* of archived articles since 15 Oct.
- **Validation** (fit calibration, choose the View and Priority thresholds, enable/disable event types): the first 300 judged forward
  v4 shadow Views.
- **Freeze** policy + calibration + both thresholds (git tag `pe-v4-frozen`).
- **Holdout** (never used to tune): the next 400 judged forward v4 Views after the freeze.
- **Coverage is a first-class metric**: eligible events (resolved, direct, supported, not garbage), Views produced, Views per day and
  per week, coverage = Views / eligible, abstention rate with reasons.
- **Quality/coverage curve** (validation): for each frozen confidence level, calls, coverage of eligible events, directional accuracy,
  benchmark-relative accuracy, significance, calls per day, no-clear-move rate. The View and Priority thresholds are read off this curve
  on validation data only.
- **Priority Insights from day one**, in shadow: evaluated separately and against the remaining standard Views (paired by event where
  possible) and the market baselines. "Interesting" only after ≥ 50 judged Priority Insights; prominent only after ≥ 100 and a significant
  difference.
- Metrics per version and tier: directional accuracy (hits / (hits + misses)), no-clear-move rate, Wilson 95 % interval, exact binomial
  vs 50 %, paired McNemar vs always-long, follow-the-index, follow-the-sector and v2 on the same events, calibration (bucket accuracy vs
  stated, ECE, n ≥ 30), magnitude MAE / median AE vs a naive σ baseline, relative-move accuracy, by event type / class (n ≥ 30).
- Power: 55 % vs 50 % needs ≈ 780 independent calls; 57 % needs ≈ 400.

## 11a. Track Record datasets
1. **Market View Track Record** (all v4 Views, standard + priority); 2. **Priority Insight Track Record** (the labelled subset,
shown separately but never added to (1) as extra independent evidence); 3. **Long-Term Outlook Track Record** (separate methodology and
horizons). Early calls and the v2 live record stay as their own frozen histories.

## 11b. Expected volume (archive proxy, 22–30 Oct; development estimate, not a target)
v2 labels as a stand-in for v4 extraction: ≈ 330–490 articles/day → ≈ 68–77 eligible events/day → ≈ 40–54 Views/day (59–70 %
coverage) → ≈ 10 Priority candidates/day (≈ 20 % of Views; stated-expectation and numeric-catalyst headlines only). ≈ 50 judged
Priority Insights in about a week, ≈ 100 in about two. Real v4 numbers come from the shadow run.

## 12. Data
Existing: articles + event archive, registry (identity, class), exchange bars (5-min ≤ 60 days; daily years), index and sector ETF
prices, macro calendar with consensus for 130/236 releases (ForexFactory), earnings calendar with EPS estimates (Nasdaq).
Needs new data: revenue/guidance consensus (only when the article states it, otherwise `unavailable`), macro surprise history
for σ, pre/post-market quotes (Yahoo `includePrePost`). Licensing caveats in YAHOO-AUDIT.md / DATA-LICENSING.md apply.

## 13. Known risks
LLM look-ahead: any backtest on events before the model's training cutoff is contaminated; only forward shadow results count as
evidence. Sample size: weeks of forward data before any claim. Article-stated expectations can be wrong: stored verbatim with source.

## Naming history
Product names were renamed before any v4 prediction existed: Market Outlooks → **Market Views**, Priority Signals → **Priority Insights**
(tier field `view_tier`), Long-Term Outlooks unchanged. Earlier versions (v1/v2 live calls, early calls) keep their historical names.
