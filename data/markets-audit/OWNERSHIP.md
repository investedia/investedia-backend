# Reported parent / subsidiary relationships

Not investment advice. **Not a complete ownership graph.**

GLEIF Level 2 primarily reports accounting-consolidation relationships to direct
and ultimate parents. A parent edge is not a beneficial ownership percentage,
control-proof for every jurisdiction, a complete subsidiary list, or proof that
no parent exists when no edge is returned. Keep the direction child → reported
parent, relationship type/status, start/end/validation dates, LEIs, source and
reported exceptions. An ultimate parent edge is not the same as the direct one.
Do not synthesise chains, investment flows or ownership stakes from correlation.

Coverage must use a verified issuer population, deduplicated across listings:

1. `listed_issuers_with_reported_parent / all_verified_listed_issuers`.
2. The same numerator divided by `verified_listed_issuers_with_valid_LEI`.
3. Separately count issuers with LEI but an exception/no published parent,
   unknown LEI linkage, stale/inactive relationship and missing upstream coverage.

Keep numerator, denominator, source version and date for both shares. A random
25-record LEI API sample is not a listed-issuer or country population sample.
The existing saved equity rows contain no LEI fields, so cross-source linkage
is not established. Both ownership shares are **null with reasons** in every
coverage row. Do not report 0% as though absence were measured.

Production would use GLEIF Level-1 + Level-2 Golden Copy/deltas, join only valid,
source-backed LEIs to issuers, preserve reporting exceptions and sample the joins
in each proposed launch country. Legal registered address is not a usable HQ
coordinate; GLEIF HeadquartersAddress still needs a separately licensed geocoder
or an explicit licensed coordinate assertion. This audit starts no geocoding or
ownership ingestion and approves no corporate-line UI.
