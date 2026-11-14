# Real Estate expansion — work plan (Claude, 14 Nov 2026)

Branch: `claude/realestate-expansion` (local, from `codex/data-centers-research` @ b620aed). Not pushed, not merged, no deploy, monitoring off.

## A. Existing work — what actually exists (checked, not taken from reports)
| Item | Found? | Verified count |
|---|---|---|
| `research/data-centers/CLAUDE-HANDOFF.md` | yes | — |
| `PROJECTS-COLLABORATION-HANDOFF.md` | **no** (not on the branch) | — |
| `phase2/phase2-dataset.json` | yes | 61 reviewed DC rows (29 + 32) |
| `phase4/sector_adapter.py`, `CONTRACT.md` | yes | contract is a *proposal*, not approved |
| `phase4/real-estate-pilot.json` | yes | 10 candidates: 3 developer relationships, 7 portfolio affiliations; 0 ownership-verified, 0 investment routes, 0 public-ready. All logistics (SEGRO, WDP, Montea) |
| `scale/CLAUDE1-INTEGRATION.md`, `AUDIT.md`, `import_projects.py`, `import.schema.json` | yes | importer `investedia.projects.import.v1` |
| commits e7faaff, b620aed | yes | — |
| `data/realestate/phase5b/REPORT.md`, backend commit `1f5d713` | **not found** in any of 84 remote branches | — |
| frontend branch `claude/realestate-projects`, commit `86ddf96f` | **not found** in any of 104 remote branches | — |
The reported "20-record release" and "Japanese pilot" therefore cannot be audited: nothing to recover. They are **not** recreated from the narrative; work restarts from the 10-candidate pilot.
Live site today: Projects tabs = Energy (186) and Data Centers (29); no Real Estate tab. `projects.json` still holds 183 Wikidata "Real estate" rows (old layer, no investment route) — not reused as investable records.

## B. Eligibility and investment-route rules
A visitor-facing record needs BOTH (1) a dated development/investment event from a primary source and (2) a substantiated route, one of: direct project equity · project-specific bond/debt · indirect listed equity/REIT · issuer-level bond · verified fund · else research-only (internal).
- Importer today supports access values public_equity / listed_REIT / listed_stapled_security / verified_fund / research_only. Bonds and direct offerings go in `extensions.real_estate.investment_route` (research extension) + a documented contract addition; never mislabelled as equity.
- Roles kept separate: property owner (direct/indirect/reported-group), developer, operator, lessee/brand, investor, contractor. A brand/franchise is never ownership.
- "Recently completed" = opened/completed on or after 14 Nov 2024, or older with a new material event.
- Every route carries `as_of`; no yields, returns, minimums or "open" status unless the document states it.
- Materiality: no single small outlet of a large chain; no ordinary store lists.

## C. Source strategy by region (primary sources first)
- North America: SEC EDGAR 10-K/10-Q/8-K (US government site; facts only) — lodging REITs (Host, Ryman, Park, Pebblebrook, Sunstone, DiamondRock, Xenia, Apple Hospitality), owner-developers (Hyatt owned, Wynn, MGM/VICI, Las Vegas Sands), mixed-use (Howard Hughes, Related not listed → excluded).
- UK/Europe: RNS / annual reports — Whitbread (owner-developer of Premier Inn), PPHE, Pandox, Covivio Hotels, Accor-invest (private → research only), British Land/Landsec food-led schemes.
- Japan/Asia: TDnet / J-REIT disclosures (Japan Hotel REIT, Invincible, Hoshino Resorts REIT), Mitsui Fudosan, Mori Trust; SGX (CDL Hospitality Trusts, Far East Hospitality, CapitaLand Ascott Trust); HKEX (Shangri-La Asia, Great Eagle); India (Indian Hotels, Chalet, Lemon Tree, Juniper).
- Australia/NZ: ASX (Lendlease, Mirvac, Star Entertainment).
- Middle East: Tadawul/DFM/ADX (Emaar, Aldar, Dur Hospitality, Taiba); giga-projects owned by PIF are private → research only unless a listed vehicle/sukuk is documented.
- Africa: JSE (Sun International, City Lodge, Southern Sun), NGX (Transcorp Hotels), Mauritius SEM.
- LatAm/Caribbean: BMV FIBRAs (FibraHotel, Fibra Inn), B3 (HBR Realty), Playa (acquired — verify).
- Corporate actions (mergers, delistings, renames) verified against current primary sources per company before use.

## D. Photos and licensing
Only after the route passes. Wikimedia Commons file-specific licence (CC0/CC BY/CC BY-SA) + identity check (same building, not a namesake); record file page, creator, licence+version, attribution, crop, date. States kept separate: verified photograph · licensed rendering/plan · no cleared image · blocked/identity unresolved. No satellite from city-level coordinates. No generic images.

## E. Batch extraction and validation
Cached downloads under `research/real-estate/sources/` (hash + retrieved-at + locator; no raw copyrighted documents committed), deterministic extraction scripts, then `scale/import_projects.py` (unchanged) for schema/dedupe. Dedupe keys: sector + authority + source id; against 61 DC rows, the 10 pilot rows, live Energy/DC ids, and within batch. Never merge on name/city/URL alone.

## F. Frontend (limited)
Sector order Real Estate → Energy → Data Centers in the existing Projects tabs/selectors/mobile controls; saved selections and URL params keep working; Energy/DC untouched. Route wording: "Indirect exposure through [company] shares", "Project-specific bond" only when proven, "Issuer-level bond exposure", "Restricted/private offering". No buy buttons/prices added for RE; "Not investment advice" visible. Note: the live Projects code exists only in built `assets/globe/news.html` (no source) — edits go there until reconciled; do not run `tools/globe-news/build.py`.
Checks: 1440 + 390, both themes, no console errors/overflow, Energy + DC unchanged.

## G. Milestones, budgets, stop conditions
1 inventory+plan (this file) → 2 discovery pool 100–200 → 3 route+identity review of best 30–50 → 4 images → 5 importer/dedupe → 6 frontend locally.
Budget: no paid services, no model/API calls beyond this session; polite fetching (cache, ≤1 req/s per host, stop on 403/429 and move on).
Stop and ask the owner when: a source needs login/licence; shared contract/loader change is required to show bonds/funds; anything would be pushed, merged or deployed.
