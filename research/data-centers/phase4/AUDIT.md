# Projects Phase 4 — local integration and verification audit

Continues `codex/data-centers-research` from `7be5c63`. Original 29 records, 32 Phase 2 reviewed rows, Phase 3 audits and previews remain unchanged. No shared Energy, live Globe, registry, production dataset, frozen ledger, workflow or secret was changed. No push, merge or deployment.

## Result and release boundaries

**One minimum Data Center factual projection (CoreSite NY3) completed a bounded source-specific data review. Four priority candidates remain data-blocked. Zero production releases or shared integrations are approved.** This is not a blanket licence, publisher legal sign-off, a five-project release, or permission to redistribute a corporate directory.

The minimum NY3 projection omits corporate specs/area/cost metrics and all imagery/marketing descriptions. It retains independently authored identity/status/operating-exposure facts, a source-qualified listed-parent chain, current AMT common equity, CC0 approximate city reference and documentary links. The exact factual digest and review scope are in `field-reuse-review.json`; the projection is in `dc-data-ready.json`. Any new facts invalidate that review. See [REUSE-ASSESSMENT.md](REUSE-ASSESSMENT.md) for the source-specific basis and remaining publisher/jurisdiction questions.

## Five candidate decisions

| Candidate | Economic classification and stage | Geography | Data review / remaining work |
|---|---|---|---|
| MD5 | Equinix EQIX / XNAS; issuer-reported group-owned development; opened as reported, not a verified deed | Madrid metropolitan city reference | Corporate factual reuse/access interpretation pending under Equinix terms §3; no exact site asserted |
| SV18 | Equinix EQIX / XNAS; issuer-reported group-owned development; opened as reported | San Jose city reference | Same reuse issue; official/address points disagree, so exact claim withheld |
| SG6 | Equinix EQIX / XNAS; operator exposure, dated opening; not property ownership | Singapore city reference | Same reuse issue; costs/capacity scope/currency held out of minimal export |
| DE3 | CoreSite through AMT / XNYS; planned operating relationship; announced development, current construction/completion unconfirmed | Denver city reference | Record-specific reuse assessment and current stage confirmation needed; conflicting area figures excluded |
| NY3 | CoreSite through AMT / XNYS; operating exposure, company-reported; launch 25 September 2025 | Secaucus city reference | Minimum factual data review completed; shared contract and production authorization still pending |

The [61-row blocker CSV](blocker-matrix.csv) gives remaining work for every original/Phase 2 record, with a separate shared integration gate. The local adapter gate is resolved for the five projections; that does not silently approve shared code. Context/programme rows remain excluded from individual-project counts. Eight shared registry mapping gaps, original source-country conflicts and unresolved affiliations remain explicit in the matrix.

## Ownership versus economic exposure

For the five candidates: two reported group-owned developments, two company-reported operating facilities, and one planned operator relationship with unknown current stage. **Zero new direct property-title or subsidiary/JV property-title verifications.** Across existing research, the prior 30 economic asset/project records and four issuer-reported group-owned observations remain unchanged; these overlapping observations are not extra facilities or deed proofs.

CoreSite's 64% / 36% company/business arrangement remains separate from facility ownership. The adapter never places it in a property-stake field. No Stonepeak Denver JV percentage is assigned to DE3. A legitimate developer, operator or lease role does not need a deed to establish company-level exposure, but it cannot be labelled direct real-estate ownership.

## Sector contract and compatibility

The isolated adapter supports Energy, Data Centers, Real Estate and explicitly registered future sectors; project/campus/building/asset/programme distinctions; source-qualified roles and parent securities; precision, HQ, imagery and investment access. The [contract proposal](CONTRACT.md) and machine-readable structural schema are ready for approval before shared-code integration.

All **150** current verified Energy records pass the wrapper, retaining the original normalized result unchanged. Raw inputs are unchanged. Original category A/B verification objects remain intact; pre-construction is planning, not active construction. The wrapper adds an envelope; it does not replace the legacy loader or rewrite its ownership rules. Full-record compatibility is pinned to frontend commit `c78ab084349b43e4c166fa0f6a0dde6dbae8af5c` and the loader hash. No assumption that the live loader already accepts new sectors is made.

Direct property ownership requires per-record proof; indirect property ownership additionally requires a scoped sourced chain. Company stakes are not property stakes. Current tickers/security types need evidence; Goodman stapled securities cannot become common stock by convenience. Unknown coordinates remain null with no marker. Exact-site claims and site imagery require scoped site evidence. Approximate locations and HQ cities stay visibly labelled.

## Geography and imagery

Five Data Center city references retained; **zero new verified exact sites** and zero project photos. NY3's named OSM building/address corroborates identity, but its point differs from the official service-page pin. SV18's address result also differs from the official pin. MD5/DE3 searches returned streets rather than facility proof. None became an exact point. `geolocation-review.json` records source ids, offsets, rejected results and ODbL scope separately; no OSM-derived coordinate enters the candidate release/Globe.

The preview's two filled Energy markers are inherited verified sites, not newly verified Data Centers sites. Data Centers use hollow approximate markers. No approximate point requests satellite imagery; no generic facility image substitutes for a project photo. Wikidata and Natural Earth credits remain visible.

## Functional preview and measured limits

The [local preview](preview/index.html) shows two existing Energy projects and five Data Center candidates, distinct sectors, role-aware company exposure, current security references, project-to-HQ-city lines, search, company/role/sector filters, drag rotation, selection, directory navigation and both themes. It never labels all companies as property owners. Preview-only/data-reviewed/integration states remain explicit. Real Estate's unlocated research rows are not mapped.

Labelled screenshots are in `screenshots/`: PC1440 and phone390, light/dark, mixed Globe, Energy view and directory. Four automated viewport/theme cases passed with no page errors, external requests or horizontal overflow. Nearby HQ/project label placement was checked and separated after visual inspection.

Measured local seven-record load/ready time: 105–212 ms across the captured cases. All 150 Energy wrappers validated in roughly 35 ms on this environment (exact latest measurement in `energy-compatibility.json`). These are small local tests, not a production-scale benchmark or latency guarantee.

## Real Estate results

See [REAL-ESTATE.md](REAL-ESTATE.md), `real-estate-pilot.json` and its property CSV. Ten named property candidates: two SEGRO developments, WDP Hazeldonk and seven Montea property pages. **Three explicit developer relationships; seven portfolio affiliations; zero verified property-title chains, mapped property investment routes or public-ready records.** Ten candidates are not ten verified investments.

All five companies were source-audited. Prologis PLD common equity / NYSE was confirmed by current SEC submissions and cover table, but accessible source reports provide aggregates rather than sufficient property-level links. Goodman's logistics disclosures checked are aggregate/script-only; its named Data Center table was not misclassified as logistics property. No fictional property rows were created to meet the target. Exact current SEGRO/WDP/Montea security mappings remain pending, not name-only guesses. All ten property coordinates are unknown, with no images.

## Tests and audit outcomes

- Existing backend Python: 316 tests OK, four existing skips; inherited ResourceWarnings unchanged.
- Worker: 88 passed, zero failures.
- Java: Maven verify passed, 13 tests, no failures/errors/skips.
- Existing research: Phase 1 14, Phase 2 17, Phase 3 16 tests passed.
- Phase 4: 35 tests passed, no skips.
- Browser: four viewport/theme cases passed; all-record Energy compatibility passed.
- Five protected baseline files hash-identical; earlier research files unchanged; no secrets/raw corporate bodies staged.

Initial Java attempts encountered missing Maven on PATH, an unwritable default cache, an unconfigured fresh-download proxy and a system JRE without a compiler. Using the existing cached Maven/settings/JDK21 resolved them. These were environment setup attempts, not new code regressions. No unresolved test failure remains. Machine-readable results: `verification-results.json`.

## Reproduce locally

```sh
python research/data-centers/phase4/run_compatibility.py
python research/data-centers/phase4/build_phase4.py
python research/data-centers/phase4/build_real_estate.py
python -m unittest discover -s research/data-centers/phase4 -p 'test_*.py'
python -m http.server 8794 --directory research/data-centers/phase4/preview
# Separate terminal, Chromium / Playwright installed:
node research/data-centers/phase4/browser-test.mjs
```

Existing suites:

```sh
python -m unittest discover -s tests -p 'test_*.py'
node --test workers/live/test/*.test.mjs
JAVA_HOME=/workspace/.setup/tools/jdk-21.0.9+10 /workspace/.setup/tools/apache-maven-3.9.11/bin/mvn -o -q -s /workspace/.setup/maven-settings.xml -Dmaven.repo.local=/workspace/.setup/m2 verify
```

The Energy compatibility probe uses a local frontend Git object, not a live network request. Source bodies are ignored; committed receipts, minimal evidence facts and identifier fixture support offline rebuilding. Fresh source research is opt-in through the bounded `fetch_sources.py`, not part of tests or a scheduled job.

## Files and handoff

All changes are under `research/data-centers/phase4/`: adapter/validators and builders; structural contract and proposal; bounded source fetcher and source receipts; field reuse decisions and evidence; 61-record blockers; ten-property Real Estate pilot; isolated preview and labelled screenshots; compatibility, browser and unit tests/results. Previous phases and production files are unchanged.

Next significant decision is review of the proposed shared contract/role labels before anyone changes shared code. Equinix source-specific access/reuse questions and DE3's stage need resolution before expanding the minimum Data Center release. No push, deployment, production ingestion or rights waiver is authorized by this handoff.

Not investment advice.
