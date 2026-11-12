# Projects scale — stage 1, 11 November 2026

Draft branch artifacts only. Not investment advice. No frontend rollout, deployment, production write or financial job.

## Result

225 current, source-qualified site records across 35 countries: 96 in development/construction and 129 completed since 2020. These are source-qualified records, not independently field-audited locations. The 5,000 energy / 1,000 infrastructure targets remain unmet; no points were padded.

| Sector | Records | Capacity | Status date/year |
| --- | ---: | ---: | ---: |
| Coal energy | 25 | 72.0% | 24.0% |
| Gas & LNG | 3 | 100.0% | 100.0% |
| Geothermal energy | 2 | 100.0% | 0.0% |
| Hydro energy | 16 | 50.0% | 81.25% |
| Nuclear energy | 25 | 40.0% | 0.0% |
| Solar energy | 24 | 70.83% | 41.67% |
| Wind energy | 130 | 90.77% | 76.15% |

All records have sourced status and coordinate precision; 94 lack a status date/year, 49 lack capacity, all 225 lack reviewed cost, 59 lack owner. No publication date is substituted for a status date. P571 inception is never completion. Date precision is conservatively year-only where source time precision was not fetched. Photos: 0%; satellite: 0%; featured: 0. Earlier featured previews are excluded from this current-only artifact. Existing region metadata leaves 24 records Unknown; no region was guessed.

611 source-class candidate records yielded 225 accepted and 386 rejected, including hard conflict holds. This is not a census or 611 distinct projects. Full reasons, missing fields, countries, regions and conflicts are in ../build-report.json. Conflicting values are withheld rather than chosen. Same-provider unit/site IDs remain distinct; cross-source unit matching still needs real source files. No human match-accuracy sample exists; accuracy is unknown, not 100%.

## Reproduce

```sh
python -m pip install -r tools/projects/requirements.txt
python -m unittest discover -s tests -p 'test_projects*.py'
python tools/projects/build_projects.py --offline
python tools/projects/slim_projects.py
# Optional, live public Wikidata queries, bounded and resumable:
python -m tools.projects.scale.fetch_wikidata --seconds 600 --batch-size 20 --max-items 1500 --cached-ids
python tools/projects/build_projects.py --offline
```

Manual Actions: Projects registry (draft artifact only), fetch_reviewed=false for offline reproduction or true for approved Wikidata refresh. No secrets, schedule or publish step. Allow roughly 1–3 runner minutes offline; live fetch has a 10-minute budget inside a 15-minute job. Gemini calls: zero. Query ids first, facts in batches <=80; cache hashes, conditional refresh and host cooldowns are retained. Timeouts reduce batches; failures keep previous facts. Cached P19 ids are partial coverage, not a fresh worldwide denominator. Five recorded fetch runs made 58 requests and received 1,630,382 bytes, excluding earlier discovery/failed census probes. See fetch-runs.json for source-specific progress.

The public slim copy has 225 records, 188,871 bytes versus 515,781 bytes for the full artifact. This is a payload measurement, not a browser performance result. It preserves free basic facts; it is not an entitlement boundary. No UI changed, so no screenshots, 5,000-point phone benchmark or 60fps claim is made.

## Licensing and blockers

Wikidata facts use the merged P19 CC0 review and retain per-field provenance and response hashes. GEM adapters require owner-supplied tracker/version files, reviewed native headers, threshold, status codes and licence evidence. Test CSVs are synthetic contracts, never real project data. EIA requires the official version/redistribution review and explicit plant+generator IDs; no EIA file was ingested. Official EIA/GEM documentation requests returned CONNECT 403 in this environment. Batteries/hydrogen await a reviewed physical-project source/class. World Bank remains country-only without precise physical evidence. OSM/ODbL is excluded pending approval.

Stage 2 photo/satellite review is pending accessible, dataset/file-specific rights and exact-site/date evidence. No generic satellite placeholder was invented. Stage 3 infrastructure/real estate remains pending source review. Stage 4 frontend work is pending the missing CODEX-PROMPT-projects-working.md reference and separate visual review; existing every-project-dot rendering stays untouched.

## Validation

Python: 260 tests, OK, 4 existing skips. Worker: 80 passed. Java: 13 tests passed after fixing a pre-existing contract failure: Java omitted meta.stats added by the Worker; unknown aggregate statistics now return null. Existing Python ResourceWarnings are unchanged. New failures: none. Offline build and slim export passed; git diff --check passed.
