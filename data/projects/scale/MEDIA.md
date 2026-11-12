# Projects media — stage 2 preparation

Not investment advice. Branch artifacts only; nothing published or deployed.

## Actual pass, 11 November 2026

Checked all 225 current draft projects for Wikidata P18 assertions: **23 image candidates / 23 projects (10.22%)**, six requests, 7,225 response bytes; zero Gemini calls. By sector: nuclear 7, hydro 6, wind 4, coal 4, solar 1, geothermal 1. These are not 23 approved photos. Commons access returns CONNECT 403 in this environment, so per-file licence/author/site review and image downloads remain pending. Accepted photos **0**, satellites **0**, missing media **225**. No placeholder images were generated. `media-candidates.json` retains query receipt hashes and source dates.

Manual warning examples: Akkuyu's candidate is a model; Hanhikivi's is a design; Jaitapur's filename mentions OLK3; Thambapavani's points to a 2012 Mannar Island image. P18 alone does not prove a current exact-site photograph. Review these before any use. Source project status also needs independent review for suspicious records; this pass does not certify that Wikidata is current or correct.

## Run candidate collection

```sh
python -m pip install -r tools/projects/requirements.txt
python -m tools.projects.scale.discover_media --limit 225 --seconds 180
# Once Commons is accessible; metadata only, no image download or approval:
python -m tools.projects.scale.discover_media --limit 225 --seconds 600 --commons
```

Alternatively run **Projects media candidates (draft only)** manually on this branch. Inputs `limit=225`, `commons=true`. It has read-only permissions, shared Projects concurrency, a 15-minute timeout, ten-minute source budget, cached conditional requests and an artifact for review. No secrets, schedules, production writes or automatic licence approvals. Estimated 1 minute for cached IDs; up to 10 minutes for metadata, bounded by the source budget. Slow/cooldown runs preserve previous complete candidate batches and cached source responses. There is no paid imagery service or AI call.

## Approve and attach individual files

`media-reviewed.json` starts empty. A reviewer must inspect the Commons description/file terms and exact project match. Save the licence and site evidence under `data/projects/`, with a SHA-256. Place only the reviewed raster in `assets/img/projects/scale/`; download/resize manually after review and record any transformation. The manifest entry requires:

- `project` (exact current ID), `site_sha256` from `tools.projects.scale.media.site_hash(project)`; relocation/name/country changes invalidate review.
- `kind`: `photo` or `satellite`; local `file` relative to repository root; image `sha256`.
- `author`, `licence`, `licence_url`, `source_url`, `changes` (e.g. resized from the original).
- `review`: `reviewer`, `checked_at` (ISO date), `exact_site=true`, `commercial_use=true`, `redistribution=true`, `evidence_file` (root-relative under data/projects), `evidence_sha256`.

Photos require a Commons File page, full credit and CC0, CC BY, CC BY-SA or specifically evidenced public-domain rights. NC/ND/unknown terms are rejected. Metadata suggestions do not populate approvals. No executable source HTML is copied into public credits.

Satellite entries additionally require `provider` (`USGS Landsat`, `NASA Landsat`, `Copernicus Sentinel-2`), an actual scene/source URL, the exact `acquired_at` date and crop `bbox=[west,south,east,north]`. Bounds must contain the verified site and span at most 0.1 degree per axis; the exact-site review is still required. Source/date cannot be inferred from coordinates. USGS/NASA entries require evidenced public-domain rights; Copernicus requires reviewed Sentinel terms. This is an intake contract, not a claim that any candidate provider/scene has been cleared or downloaded.

```sh
python tools/projects/build_projects.py --offline
python tools/projects/slim_projects.py
```

The build validates evidence/image hashes, path containment, raster decoding, 10 MiB / 20 MP limits, rights, dates and site binding. Ambiguous media is held. Reviewed photos take precedence over satellite. Removing an approval removes the media on rebuild. Basic map facts/points survive missing imagery; no fake photo is substituted. Public slim output retains approved credit and source fields. Per-sector media coverage and rejection reasons appear in `build-report.json`.

## Validation and remaining work

15 media tests: photo preference, public credits, future/missing dates, exact crops, rights restrictions, modified evidence, project relocation, traversal/symlink prevention, corrupted raster, ambiguity, revocation/idempotence, query caps, metadata sanitization and cooldown resume. Full Python: 275 OK, four existing skips and unchanged ResourceWarnings. No Java/Worker code changed in this stage; previous checks remain 13 Java / 80 Worker passed. No UI changed; browser screenshots/fps are not claimed.

Stage 2 is **prepared but incomplete** until real file rights/site review is possible. UI integration awaits approved media and the missing Projects working brief. GEM/EIA source blockers remain unchanged.
