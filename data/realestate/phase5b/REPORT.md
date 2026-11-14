# Real Estate Phase 5B (14 Nov 2026, Claude) - local only

Nothing pushed, merged, deployed or published. Monitoring not activated.

**Owner rule (14 Nov 2026): only properties with a verified picture or a development plan are proposed or shown.**

## 1. The batch-1 properties, re-verified
- Live records: 160. Four were sold in 2026 and retired, with their history kept: Sheraton Parsippany (H1 2026), Sumner Square (5 Aug), 1330 Connecticut Ave (23 Sep) and The Lofts at Atlantic Wharf (25 Feb). One duplicate was merged: 121 Broadway into 121 Broadway Street. Two hotels acquired in October 2026 were added: Renaissance Dallas at Plano Legacy West (fee simple) and 1 Hotel Brooklyn Bridge (leasehold).
- Status updates from the Q3 2026 10-Qs:
  - Reston Next Retail was placed in service on 16 Jan 2026 and 290 Binney St on 30 Apr 2026.
  - 725 12th St's target moved to Q3 2029.
  - 651 Gateway is absent from BXP's construction table, so its status is unresolved.
  - Kingstowne Retail was sold (flagged).
- Ownership shares stated by the companies: 7. They come from the joint-venture and mortgage tables: 767 Fifth 60%, 601 Lexington 55%, 343 Madison 89.45%, plus the construction joint ventures.
- No record claims legal title.

## 2. Coordinates (live records)
- Exact: 96. Of these, 10 are building points (a Wikidata building point within 150 m of the company's own pin) and the rest are address points (US Census geocode of the published address, high or medium confidence).
- Approximate: 58.
- Unknown: 6.
- Host's own portfolio page provided addresses and pins for 75 of the 76 hotels. The pins are used only as an internal cross-check, because the website terms haven't been reviewed.

## 3. Imagery
- Commons photos matched by Wikidata identity and distance: 21.
- Accepted after licence and visual check: 13 (CC BY / CC BY-SA / public domain, with attribution).
- Rejected: 2 interior shots.
- Pending: 6 (licence checked, but the download was rate-limited by Commons).
- No hotel-brand photos were used.

## 4. Companies and the merger
- Vivmark Residential (NYSE: VMRK) is the former Equity Residential, renamed 12 Aug 2026.
- AvalonBay merged into Vivmark on 17 Aug 2026 (2.793 Vivmark shares per AVB share). AVB was removed from trading on the NYSE on 17 Aug, so it has no live exposure.
- BXP (NYSE) and HST (Nasdaq) are current.
- See company-reconciliation.json.

## 5. Proposed first release: 20 records (not published)
The proposal is smaller than the 30-50 asked for because of the picture-or-plan rule: 13 have photos and 7 are developments.

| id | ticker | relationship | stage | location | photo |
|---|---|---|---|---|---|
| re:hst:calgary-marriott-downtown-hotel | HST | reported_group_owner | operating | exact/building_point/high | yes |
| re:hst:hyatt-place-waikiki-beach | HST | reported_group_owner | operating | exact/building_point/high | yes |
| re:hst:new-orleans-marriott | HST | reported_group_owner | operating | exact/building_point/high | yes |
| re:hst:new-york-marriott-downtown | HST | reported_group_owner | operating | exact/building_point/high | yes |
| re:hst:san-francisco-marriott-fisherman-s-wharf | HST | reported_group_owner | operating | exact/building_point/high | yes |
| re:hst:swiss-tel-chicago | HST | reported_group_owner | operating | exact/building_point/high | yes |
| re:hst:the-ritz-carlton-marina-del-rey | HST | reported_group_owner | operating | exact/building_point/high | yes |
| re:bxp:100-federal-street | BXP | reported_group_owner | operating | exact/address_point/high | yes |
| re:bxp:399-park-avenue | BXP | reported_group_owner | operating | exact/address_point/high | yes |
| re:bxp:535-mission-street | BXP | reported_group_owner | operating | exact/address_point/high | yes |
| re:hst:the-don-cesar | HST | reported_group_owner | operating | exact/address_point/medium | yes |
| re:hst:the-westin-georgetown-washington-d-c | HST | reported_group_owner | operating | exact/address_point/medium | yes |
| re:hst:the-westin-seattle | HST | reported_group_owner | operating | exact/address_point/medium | yes |
| re:bxp:17-hartwell-avenue | BXP | developer 20.0% | under_construction | exact/address_point/medium | - |
| re:bxp:290-binney-street | BXP | developer 55.0% | completed | exact/address_point/medium | - |
| re:bxp:290-coles-street | BXP | developer 19.46% | under_construction | exact/address_point/medium | - |
| re:bxp:343-madison-avenue | BXP | developer 89.45% | under_construction | exact/address_point/medium | - |
| re:bxp:121-broadway-street | BXP | developer | under_construction | exact/address_point/medium | - |
| re:bxp:725-12th-street | BXP | developer | under_construction | approximate/-/- | - |
| re:bxp:reston-next-retail | BXP | developer | completed | approximate/-/- | - |

Per-record blockers are in release-review.json. Every record still needs your signature on its fact_sha256.

## 6. International pilot
- Japan Real Estate Investment Corporation (TSE 8952): 44 properties with exact GSI address points, 14 of them with partial ownership shares. Another 29 resolve only to a district (kept as research), and one was disposed.
- Data source: the company's official property workbook (EN and JA editions).
- Reuse is pending: the website disclaimer grants no rights.
- **The owner rule excludes all 44 from the preview**: none has a photo or a development plan.
- Other sources checked:
  - CapitaLand Integrated Commercial Trust (CICT): its portfolio web page is stale (2022) and the annual-report page would not load.
  - Nippon Building Fund (NBF), WDP and Goodman: blocked with HTTP 403.
  - Dexus, GPT, Mirvac, Emaar and Fibra Monterrey: HTTP 404.
  - Growthpoint: HTTP 403.
  - SEGRO, Landsec and British Land pages load but have not been parsed yet.
- Codex's 10 SEGRO/WDP/Montea records are unchanged.

## 7-9. Importer, monitoring fields, regression
- Codex's importer, on top of the 602 Data Centers records: 2 inserted, 159 updated, 4 retired. The JRE pilot added 44, for 811 records in total.
- Retirement is one-shot by design: re-running it is rejected because the hashes have changed.
- Each record carries a monitoring block (stable id, evidence refs, fingerprint, last verified time) with `enabled: false`.
- Local change-detection tests: unchanged input stays quiet; status changes, ownership changes, disposals (hash-checked) and acquisitions are all detected.
- Tests: tools/realestate/test_phase5b.py, 14 OK.

## 10. UI
- Frontend branch `claude/realestate-projects` (local only).
- A third sector tab, Real Estate, uses the existing components. The Investment tab shows the relationship, the stated share, the address, and a "Tracked by Investedia" company portfolio block.
- Energy and Data Centers render unchanged, with no page errors and no sideways scroll on phone.

## 11. Blockers and owner decisions
1. Sign the record-bound review for the 20 proposed records.
2. Confirm the SEC + Census + Wikidata + Commons basis for release.
3. JRE: ask for reuse permission, or rely on TDnet filings instead. Note that photos or plans are now required.
4. The 6 pending Commons images need a re-run once the rate limit clears.
5. The Host website pins and addresses are reused only as cross-checks.
