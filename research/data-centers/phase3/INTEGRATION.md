# Proposed sector integration contract — approval required

The adapter is research-local. It does not replace the Energy loader or change a shared schema. Read-only compatibility was checked against frontend commit `c78ab084349b43e4c166fa0f6a0dde6dbae8af5c`; `compatibility-report.json` pins the loader hash.

## Concrete proposed hook

Accept a separately versioned Data Centers export only after its record-bound release gates pass. Reuse the current normalized common fields, with the economic/precision metadata in the proposed sidecar described in `schema-contract.json`. Dispatch sector explicitly instead of hardcoding Energy. Keep all existing Energy inputs and behavior intact.

Expose company links under **Listed-company exposure**, with a role-aware label, never the current unconditional **Listed owner** label. `listed` is intentionally null in this projection; company connections live in `invest.exposures`. Public equity is indirect company exposure, not an offer of direct project investment. Exact and approximate locations must remain distinct through search, cards and rendering. HQ endpoints must retain city precision.

Support sector, company, economic-role and development-status filters; project discovery uses name, city, company and ticker. Images require per-image licence/attribution and exact-site verification for site-specific satellite crops. No image is required for a city-reference marker; do not add a generic substitute. Economic relationships carry dated evidence, maturity and scope. Keep cost currency and capacity scope; do not promote contract revenue to capex or an elapsed target to completion.

## Release handoff

1. Review the five source-specific decisions in `reuse-decisions.json`, recording basis and exact fact digest rather than changing a convenience flag.
2. Approve the proposed sector hook and role-aware labels with the shared pipeline owner. Shared changes are outside this local task's authorization.
3. Re-run the adapter validation and regressions against the then-current loader. Only validated, cleared rows enter a new release artifact.
4. Separately authorize any production integration or publishing. This branch performs neither.

Current handoff: five private prepared projections; zero public export rows. `public-export.json` is deliberately empty. The local preview demonstrates the contract without altering the production Globe. No live stock-price changes or investment-return claims are displayed.
