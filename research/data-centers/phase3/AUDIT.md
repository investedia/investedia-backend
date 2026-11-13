# Data Centers Phase 3 — verification and release audit

Audit date: 13 November 2026. Continues `d5513ed`; original and Phase 2 research remains intact. This is an isolated local research deliverable, not a production release.

## Result

**0 records cleared for publication; 5 technically prepared priority candidates.** No public dataset was populated. Five city-reference markers and three headquarters-city endpoints now have CC0 provenance. No new exact facility site or reusable project photograph was verified. The target of 5–10 public-ready projects was not reached because two significant gates remain; verification standards were not relaxed.

The [per-record matrix](blocker-matrix.csv) covers all 61 existing rows, including all 32 Phase 2 development/context rows. Its JSON companion contains full reasons and location notes. Context rows are not additional facilities. Prior counts remain: 29 original reviewed records plus 32 additional reviewed rows; 30 economic asset/project records, not 61 investment opportunities. Original accepted affiliations remain distinct from economic links.

## First candidates

| Candidate | Listed exposure | Relationship and stage | Location | Remaining gates |
|---|---|---|---|---|
| Equinix MD5 | EQIX / XNAS | Company development; issuer reports group-owned; opened as reported | Madrid city reference | Source reuse decision; sector contract approval |
| Equinix SV18 | EQIX / XNAS | Company development; issuer reports group-owned; opened as reported | San Jose city reference | Same two gates |
| Equinix SG6 | EQIX / XNAS | Lease/operating exposure; dated opening release supersedes undated forecast | Singapore city reference | Same two gates |
| CoreSite DE3 | AMT / XNYS through CoreSite | Planned operating exposure; elapsed opening target does not confirm operation | Denver city reference | Same two gates; conflicting area excluded from selected facts |
| CoreSite NY3 | AMT / XNYS through CoreSite | Confirmed operating exposure; distinct from NY2 despite shared address | Secaucus city reference | Same two gates |

The MD5/SV18 historical expected-opening fields are retained as reported targets, not new forecasts. The preview separately labels their reported opening. DE3 building capacity and campus capacity must stay separate; conflicting area figures are withheld. SG6 first-phase capacity and full build-out are not interchangeable. See original Phase 2 evidence packets and the bounded projection in `adapter-preview.json`.

## Economic classifications

Verified direct legal property ownership: **0**. Verified subsidiary/JV property-ownership chains: **0**. Four issuer-reported group-owned observations are retained, but none establishes legal title or a per-property corporate chain. These observations overlap development classifications and must not be added as extra assets.

Across the 61 rows, mutually exclusive adapter classifications are: 28 company-development rows (22 individual developments plus six context rows), five lease/operating rows (including planned DE3), one contractual-exposure row, two qualified group-ownership rows, and 25 research affiliations. The two qualified ownership rows plus the MD5/SV18 development notes account for the four issuer-owned observations. Two original records establish lease/operating relationships. Classifications are not public-release approvals.

CoreSite's 64% American Tower / 36% Stonepeak business arrangement is not individual facility ownership. The separate Denver development JV cannot be assigned to DE3 merely because both mention Denver. The adapter deliberately leaves property percentage and legal owner empty. Applied Digital contracted lease revenue is not construction cost or property ownership; its registry gap remains explicit.

## Location and imagery

Five Wikidata city references were checked against country and exact QID. San Jose replaces the broad Silicon Valley display reference, without asserting a facility pin. Headquarters endpoints are cities from the pinned frontend CC0 dataset, not surveyed offices. Hollow markers, city warnings and dashed HQ-city connections preserve this distinction. No approximate marker can request satellite imagery. No corporate image, logo or generic facility photograph is substituted. Natural Earth cartography retains its public-domain credit.

## Commercial reuse assessment

Facts and protected expression are different. US Copyright Office Compendium §313.3(C) and the primary Feist opinion support that distinction; creative compilation, prose, tables, photographs and access conditions require separate consideration. An absent express factual-data licence is not automatically a prohibition. Conversely, rewriting a corporate table is not an automatic clearance of its access or database conditions.

Sources reviewed: [Equinix terms](https://www.equinix.com/about/legal/terms), Digital Realty terms (exact fetched URL in its receipt), CoreSite facility/service pages, Wikidata licensing, SEC developer resources, [Copyright Office Compendium chapter 300](https://www.copyright.gov/comp3/chap300/ch300-copyrightable-authorship.pdf), and [Feist primary opinion](https://tile.loc.gov/storage-services/service/ll/usrep/usrep499/usrep499340/usrep499340.pdf). Receipts record retrieval time, HTTP status and content hash; raw corporate bodies remain ignored locally. No full table, brochure, press-release prose or photograph is redistributed in this phase.

Wikidata CC0 city/HQ facts and narrowly approved SEC issuer identifiers have a documented reuse basis. Corporate project facts remain pending a source-specific factual-reuse decision addressing applicable access/database terms, or documented permission or an independently cleared source. Failed guessed policy URLs provide no clearance. The fetched Equinix SEC earnings exhibit did not contain the relevant named project evidence, so it cannot replace corporate project sources. SEC hosting also does not convert issuer-authored exhibits into government works. The unused Circular 33 download is not relied upon as authority for the facts conclusion.

`reuse-decisions.json` records each priority decision. Approval records must bind the exact record digest and reviewer/date/basis; a boolean eligible flag cannot publish a record. Approval to integrate code would not itself resolve source rights.

## Integration and performance

See [INTEGRATION.md](INTEGRATION.md). The isolated common-field projection passes the shape probe, but actual live loader compatibility is **false**, because that loader hardcodes Energy and fills an ownership-labelled field. No shared pipeline, renderer, registry or production dataset changed.

The functional local Globe supports sector/company/exposure filtering, project search, project selection, rotation, directory navigation and HQ-city connections. Browser checks passed at 1440px and 390px in both themes, with no horizontal overflow, page errors or image/network dependencies. This validates five-candidate interaction only; no production-scale performance claim is made.

## Verification

Existing Python suite: 316 tests OK, four existing skips; existing ResourceWarnings unchanged. Worker: 88 passed. Phase 1 research: 14 passed; Phase 2: 17 passed; Phase 3: 16 passed. Browser: four viewport/theme cases passed. Compatibility probe passed the normalized-shape assertions while recording the real shared-loader incompatibility.

Reproduce offline:

```sh
python research/data-centers/phase3/build_phase3.py
python -m unittest discover -s research/data-centers/phase3 -p 'test_*.py'
node research/data-centers/phase3/compatibility-probe.mjs
python -m http.server 8793 --directory research/data-centers/phase3/preview
# In another terminal, with Playwright and Chromium available:
node research/data-centers/phase3/browser-test.mjs
```

Real Estate verified pilot remains deferred until the first Data Centers publication batch is actually cleared. The existing five-company source audit is carried forward without fabricated property records. See `real-estate-handoff.json`.

Not investment advice.
