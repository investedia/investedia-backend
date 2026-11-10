# SEC financials feasibility

Not investment advice. Phase 1 should show **reported annual figures only** for
SEC filers, with explicit concept, period, unit/currency and filing link. Other
issuers get null plus `not_SEC_filer` / `identifier_not_linked` / `concept_missing`.
No business/company facts are assumed worldwide-complete from a US source.

| Display field | Candidate concepts | Conditions |
|---|---|---|
| Revenue | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax; Revenues; SalesRevenueNet; ifrs-full:Revenue | Concept choice must match the issuer's reported economics. Banks/insurers may not have a comparable simple “Revenue” figure; do not add every revenue-like tag. |
| Net income | us-gaap:NetIncomeLoss; IFRS ProfitLoss | Preserve concept/scope, consolidated vs attributable distinctions and amended facts. |
| Assets / Liabilities | us-gaap/IFRS Assets, Liabilities | Instant end-date balance-sheet figures, not annual/quarterly flows. Separate LiabilitiesAndStockholdersEquity; never substitute that for liabilities. |
| Shares outstanding | dei:EntityCommonStockSharesOutstanding | Instant shares and date. Multiple classes/contexts can differ. |
| Weighted diluted shares | us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding | Period average, explicitly a different metric from instant shares. Never interchangeable. |

Known concept families are not measured reliability. The manual collector saves
`sec-sample.json`: present-in-returned-sample flags, taxonomies, units, periods,
accessions and joined filing URLs for ONE existing CIK. Absence means not present
in that returned sample; it does not establish unavailable financials for all
filers or a missing economic fact. Larger, stratified bulk validation is needed
before any concept is described as “reliably present” across launch countries.

Retain start, end, fy, fp, form, filed, accn, frame, taxonomy, concept and unit.
FY is not TTM. Q2 YTD is not a standalone Q2. Do not compare durations merely
because the labels say Q1/Q2/FY; fiscal calendars and 52/53-week years differ.
A form 10-Q/10-K alone does not distinguish every context. Separate annual,
quarter, YTD and instant records; no automatic annualisation or TTM in phase 1.
If future TTM is approved, require four compatible discrete quarters, the same
unit/concept/scope and consistent amendment policy. Do not double-count YTD.

Join companyfacts `accn` to submissions recent `accessionNumber` to obtain the
actual `primaryDocument`; retain CIK padding internally but use the integer CIK
and dashless accession in the SEC archive URL. If the primary document cannot
be joined, return null with reason; never invent its filename or a working link.
Choose amended/duplicate contexts deliberately, preserve superseded assertions,
and show the reported currency rather than silently converting it. No financial
figures or accounting histories are generated or modified by this audit.
