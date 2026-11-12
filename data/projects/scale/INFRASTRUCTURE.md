# Projects scale — stage 3 partial source pass

11 November 2026. Draft only, not ready for publication. Not investment advice.

## Result

308 eligible records / 53 countries after reconciliation: energy222 (wind130, solar24, hydro13, nuclear25, coal25, gas3, geothermal2), water35, real estate50, data centres1. 143 ongoing/development and165 completed2020+. Three former hydro records are held because dam-class copies disagree on type; no classification was guessed. Net increase83, not86. No airport/port was admitted merely for being listed. 1,000 infrastructure /5,000 energy targets are unmet.

| Source class | Candidate rows | Eligible before cross-source reconciliation | Rejected |
| --- | ---: | ---: | ---: |
| ports | 2 | 0 | 2 |
| airports | 63 | 0 | 63 |
| dam | 74 | 38 | 36 |
| water | 2 | 0 | 2 |
| skyscraper | 73 | 50 | 23 |
| datacentre | 1 | 1 | 0 |
| semiconductor | 1 | 0 | 1 |

827 source-class rows overall,519 rejected,308 admitted; not827 unique projects. The final report contains all reasons, countries, regions, field evidence and conflicts. Status100%; status date/year54.22%; capacity62.01%; cost0%; media0%. Missing date/year141, capacity117, cost308, owner122. All points retain source precision. Region Unknown24 remains explicit. No human matching-accuracy percentage is claimed.

## Source method and limits

Live Wikidata CC0 class labels/descriptions were checked before selecting physical port, airport, dam, water-treatment, skyscraper, data-centre and semiconductor-factory classes. Ambiguous label-search results were not used. Receipts are in infrastructure-class-review.json; the source-specific licence gate remains the merged P19 evidence. Two-step current-candidate queries then fresh facts:26 requests,603,218 bytes,zero Gemini calls; run bounded to240 seconds/100 ids per class/20 facts per batch. All seven direct-class candidate sets completed within those bounds, **not** an exhaustive subclass/global census. Airports/ports mostly failed the existing verified-development gate or precision/source rules. Real estate covers skyscrapers only, not all buildings. No residential-directory bulk import.

Rail/metro remains queued: a line's representative coordinate does not prove an exact physical development site. Mining and broader real estate await reviewed physical-project classes/files. GEM/EIA, imagery access and licensing blockers remain. World Bank country-level only; OSM excluded. No paid service, model, financial job, ingest, workflow dispatch or production write ran.

```sh
python -m tools.projects.scale.fetch_wikidata --seconds 240 --max-items 100 --batch-size 20 --classes ports airports dam water skyscraper datacentre semiconductor
python tools/projects/build_projects.py --offline
python tools/projects/slim_projects.py
```

Public basic-facts export:308 records/253,602 bytes, versus669,398-byte full artifact. These are payload sizes, not browser performance measurements. Stage1/2 reports describe their historical225-record snapshots; this is the new current branch count. Rerun media discovery for the expanded dataset before approving any media.

Validation:275 Python tests OK,4 existing skips; unchanged ResourceWarnings. No new failures. Build, slim export and diff checks pass. Worker/Java code unchanged since the prior80/13 passes. UI remains a separate frontend branch. No screenshots/fps claim for this backend stage.
