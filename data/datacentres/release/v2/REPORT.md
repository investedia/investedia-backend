# Data Centres release candidate v2: status, imagery, approvals (13 Nov 2026)
Local only. Nothing pushed, merged or deployed. Not investment advice.

## Counts (40 development records; SC2 on hold)
| Measure | Count |
|---|---|
| Release candidates | 39 (29 Equinix from SEC 10-K, 10 NEXTDC from ASX annual report) |
| On hold | 1 (NEXTDC SC2: location not verified) |
| Verified site coordinates (OSM object named for the facility) | 11 (8 building-level, 3 campus/site-level); FR8 and MU4 also agree with Equinix's own pin within 53 m |
| Commercially usable real photographs | 1 verified (Equinix MI1, Wikimedia Commons, CC BY-SA 3.0, April 2014, before redevelopment); file download rate-limited here, not yet in the asset folder |
| Correctly identified satellite imagery (current, reviewed by eye) | 9 |
| Before/after pairs (2024 vs 2026) | 7 (DA12, DC17, DC22, FR8, FR15, TR6, P1); MU4 has 2024 only, its 2026 scene rejected for haze |
| Placeholder only | 28 |
| Pass Codex public_projection today | 29 (Equinix; awaiting owner approval) |
| Blocked by reuse decision | 10 (NEXTDC: ASX-filing facts) |

## Capacity convention (whole dataset)
operating_mw / in_progress_mw / planned_mw are separate fields and never added together. KL1: 10 MW operating, +15 MW in progress, 15 MW planned. M4: 162 MW planned (campus). P1/B2: +2 MW in progress each. Equinix filing gives planned sellable cabinets per phase, not MW.

## What is ready
29 Equinix development phases: original one-sentence summaries, cited facts (target opening, planned capex, planned cabinets), listed parent EQIX (Nasdaq), role developer, city reference or OSM-identified site, imagery where reviewed. Review C1-C7 passed; importer and public gate pass.

## Legally uncertain / needs a decision
1. **NEXTDC (10):** facts from an ASX annual report. Used for internal research and verification only; public use needs your decision or legal review (ASX publication is not a redistribution licence).
2. **Aggregate use of one filing table (Equinix):** each fact is restated and cited, but publishing all rows of the 10-K project table could be argued to reuse its selection. Low risk in our view; flagged for legal review.
3. **OpenStreetMap site points (11):** ODbL attribution required ("© OpenStreetMap contributors"); single features, an insubstantial extract, so no share-alike obligation expected. Confirm.
4. **Equinix / Digital Realty / NEXTDC websites:** terms restrict copying (Equinix covers "data"; NEXTDC forbids commercialising information). Not used for public facts. Permission letter drafted (REPORT-PHASE2.md).
5. **Commons photo (MI1):** CC BY-SA 3.0, so attribution and share-alike apply to edited versions. Display unmodified or resized with credit.
6. **Copernicus Sentinel-2 imagery:** free and open; credit line "Contains modified Copernicus Sentinel data <year>" shown on every image.

## Approvals needed from the owner
A. Publish the 29 Equinix developments (sign-off of the prepared review).
B. Decide on NEXTDC ASX facts (publish, seek permission, or keep internal).
C. Confirm OSM attribution approach for the 11 site points.
D. Choose/approve the Projects UI (desktop B, phone B+C sheet) for implementation.
E. "push" for a review-only upload (checked: no workflow or deployment triggers on branch push; PR opens read-only CI only).

## Tests
Codex suites (research, phase2, phase3, phase4, scale): OK. Backend tests: OK (4 skipped, pre-existing). Importer: release v2 39/0 errors, release v1 29/0, NEXTDC 11/0, v2 research 631/0.

## Imagery manifest
data/datacentres/release/v1/imagery-manifest.json: per project, the OSM site identity, corroboration, each image's scene id, date, sha256, credit, licence, current/historical flag and review result. Image files are kept outside Git until the UI build.
