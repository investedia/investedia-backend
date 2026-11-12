# Projects data — current scale draft

The default offline build now uses `scale-manifest.json`: current development/construction or source-confirmed completion from 2020 onward. See [stage 1 report](scale/REPORT.md) for actual coverage, missing fields, source limits, commands and tests. Output is branch-only and not ready for publication. Not investment advice.

The original P19 manifest remains available explicitly:

```sh
python tools/projects/build_projects.py --offline --manifest data/projects/manifest.json
```

The following is historical P19 foundation documentation; its snapshot counts and source-access status are not the current scale result.

---

# P19 draft project data

Not investment advice. This is an offline migration and ingestion foundation, **not a publication-ready expanded dataset**. No new source is cleared or downloaded; no model calls. Do not copy the draft output over the live frontend data.

## Reproduce

```sh
python -m pip install -r tools/projects/requirements.txt
python tools/projects/build_projects.py --offline
python -m tools.projects.review_news
python -m unittest discover -s tests -p test_projects_pipeline.py
```

`manifest.json` pins the build date and raw hashes. Repeating the offline command produces identical output hashes. `cache/wikidata-retained.json` is the existing frontend main `1e34575d` snapshot, not an original SPARQL response. Its hard-coded digest is the only retained migration exception. New inputs require explicit dataset-specific licence/redistribution review and a hash-bound evidence file; a CC licence string or reachable URL does not clear them.

`tools/projects/sources/` contains separate parsers for Wikidata SPARQL, GEM spreadsheets, World Bank Projects JSON, EIA sheets, NGA/OurAirports reference tables, WRI fallback tables and per-file Commons photo manifests. Real product versions, reviewed column/class maps, native thresholds and notices are still needed. XLSX sheets and field/unit/currency maps must be explicit. There is no generic name-based schema guessing or automated legal approval. GEM tracker variants are not claimed validated against unavailable spreadsheets.

`python -m tools.projects.fetch_sources` downloads only exact, already reviewed HTTPS versions under ignored `raw/`, with a 20MiB total budget, 60s request timeout, no redirects, one-second spacing and `InvestediaRobot/1.0`. Downloads must match the pre-reviewed hash. The retained snapshot is never fetched. A changed upstream version needs fresh manifest/evidence review. No secrets or paid services. Wikidata's query helper pages entity ids (<=100 per query) before joining multivalued facts; no unreviewed class ids are built in.

The manual `Projects registry (draft artifact only)` Actions workflow has no schedule, contents-write permission, publication or deployment. Default is offline. Its optional fetch does not approve or enable sources. Default planning estimate 1–3 Linux Actions minutes; maximum 15 minutes. Zero Gemini calls. Fetch size/coverage is bounded by the reviewed manifest, not by the desired point count.

## Outputs and limits

- `assets/globe/projects.json`: v2 with v1 short keys retained, source/field evidence and validation state. 631 retained-unverified rows after three logged merges and one unknown ISO country drop. Zero newly verified records. Output remains a draft.
- `projects-featured.json`: four inherited previews with local photo hashes, not 50 fully reviewed entries. `curated/*.yaml` holds the retained facts; no hand edits to generated JSON.
- `project-links.json`: exact verified listed-identity joins only (QID, ISIN, exact official registry name), with ambiguity/conflicting identifiers rejected. No ticker/name fuzzy matching or legacy-price verification. Existing registry has no suitable verified join, so zero links, not an inferred relationship.
- `build-report.json`: all 19 type totals (including zeros), status/country/source counts, missing fields, shares, conflicts, merges and dropped reasons. No country/coverage denominator is invented.
- `country-only.json`: World Bank operations that lack verified precise physical sites stay off-map. Finance approval is not construction/operating status.
- `news-match-review.json`: deterministic sample from actual articles and verified project names/aliases. Currently zero; no match-accuracy percentage. No synthetic fixture counts as review evidence.

Unknown status stays absent. The 111 old `y` values represent unspecified inception, not a sourced status year, so they are omitted. P571 never establishes commissioning; P729 can supply an operational year only with explicit status evidence. Costs preserve original currency/year; capacity preserves source unit. WRI facts stay labelled as of 2021 and are fallback only. ISO checks use the existing map, including its existing nonstandard XK mapping; no new country coding policy is invented. Centroid sentinels are derived from the existing Natural Earth `countries-50m.json` centres; checks reject points within 1km of those centres, not every possible provider's country placeholder.

Ports/airports are not imported merely because a port is L/M or an airport is large: each must have source-reviewed development evidence. World Bank sites require individual precise-location review. New basic verified facts remain free; no price changes, advanced Pro behaviour or visual redesign is implemented here.

The `connections.py` extension stays off unless a dataset-hash-bound human review checks >=100 distinct real matches with >=90% correct. Matching requires a unique exact whole project name/alias and a geolocated event in the same country. No country guess from source/region, no forced asset link, no article rewrite. Historical connection/financial job paths are not run or rewritten. A new dataset invalidates the prior review hash. Detailed UI handling and approved visual work remain separate.

## Licensing evidence / asked, not used

See the P19 section in the docs repository `SOURCE-LICENSING-AUDIT.md`, branch `codex/p19-projects-audit`. Current Wikidata, GEM and World Bank probes returned sandbox CONNECT403; no new primary notice or data was fetched. Retained Commons hashes check bytes, not rights; preserve each file's author, licence/version, source URL and crop/resize credit. New Commons downloads require per-file licence review.

OpenStreetMap/ODbL, IAEA PRIS, company/news websites, paid S&P/BNEF/Rystad/GlobalData and Google Maps are asked/not used. No permission was inferred.
