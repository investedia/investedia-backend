# Run this audit

Audit only. Not investment advice.

Claude opens the draft PR from `codex/markets-audit`; no merge or deployment is
performed by the agent. The manual workflow must become available through the
owner's normal approval process. Run **Markets feasibility audit (review only)**
with `sample_limit=25`. It uses no secrets, no schedule, no registry build, no
Gemini, no Worker writes and no UI changes. It uploads `markets-audit-review`.

Current checked-in reports are offline baselines. Exact remote terms dates,
commercial/republication grants, fresh source schemas, listing denominators,
ownership joins and real ECB correlations remain unverified until runner
collection and primary-source review. Fetching a notice records the fetch date,
not a legal clearance. A 429 is deferred; no robots/access bypass is attempted.

Reproduce only offline reports locally:

```sh
python -m tools.markets_audit.run
python -m unittest discover -s tests -p test_markets_audit.py
```

Only on the manual GitHub runner, add `--fetch`. This audit intentionally checks
bulk manifests/HEAD for very large SEC/GLEIF products instead of starting a
multi-gigabyte registry ingestion. Regional exchange files lacking an explicit
reuse grant are not downloaded. Companies House authenticated APIs are excluded.
The runner sample is deliberately insufficient to establish nationwide coverage;
verified coverage percentages stay null rather than being extrapolated.

Stop after these reports. No registry, schedules, Worker endpoints, font/UI
changes or publication are authorised by this phase.

Verification before push: 175 Python tests pass with 4 pre-existing skips;
52 current Worker tests pass, including all 45 tests referenced by the task.
Twelve new offline tests cover matching, identifier/checksum conflicts, FX base
sensitivity/alignment/thresholds, coverage nulls, SEC period/link shape and the
local-download guard. No provider download or workflow dispatch was performed.
