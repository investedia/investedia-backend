# Data Centres pipeline: handoff (Claude 1 -> Claude 2), 13 Nov 2026

Status: pipeline written, sample run (3 per operator) only. No full crawl yet. Nothing pushed.

Run: `python tools/datacentres/pipeline.py --cache <dir outside repo> [--operators ...] [--limit N]`

## Sources confirmed reachable and robots-allowed
- Equinix: sitemap-core.xml -> 282 IBX facility pages (address block; map-pin lat/lng on some pages only)
- Digital Realty: en-sitemap.xml -> ~261 facility pages (__NEXT_DATA__: site code, full address incl. country for non-US, lat/lng, building m2)
- CoreSite (American Tower): /data-center/{code}-{city}-{st} pages; addresses are on /data-center-locations/{market} pages ("address-text")
- NEXTDC: sitemap -> ~25 facility pages (suburb, IT MW, stage in nav "(In Planning)/(In Development)")
- SEC data API works (listing evidence for EQIX, DLR, AMT, IRM, GDS). Iron Mountain site returned 429; datacentermap 429.
- Nominatim reachable for approximate geocoding (label "approximate", ODbL attribution).

## Findings
- Codex's 61 reviewed records / sector adapter: not found on any branch of backend, frontend or docs repos.
- Ownership: Equinix 10-K = owned/leased per metro only; DLR Schedule III = per metro (building counts). No per-facility ownership evidence -> ownership_status "not established" for all.
- CyrusOne is private (KKR/GIP): rejected for listed exposure.

## Fixes needed before the full run
1. DLR US addresses have no country: infer "United States" from "ST 12345" (state + ZIP) pattern; otherwise use URL region + metro map.
2. CoreSite: build code -> address map from market pages (facility page JSON-LD is the HQ address, do not use).
3. NEXTDC stage: match code + city name (e.g. "C1 Canberra"); "GC1 Gold Coast (In Planning)" currently leaks into C1.
4. Equinix pages without map pin: geocode published address -> class "approximate".
