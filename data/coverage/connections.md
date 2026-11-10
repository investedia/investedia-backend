# Evidence-based connection coverage

Not investment advice.

This branch maps countries to registry indices, FX, rates and listed companies
without asserting that the company list is ranked by size. The opt-in resolver
only fills an **existing explicit article impact**. It never adds a bank effect
merely because a central bank changed rates, nor an oil-major effect merely
because Angola published an oil article. Broad sector impacts still require a
named relationship; the existing connection format and sector rejection stay.

Eligibility requires a finite positive real saved price, dated within seven
days, verified coordinates and a reviewed source/redistribution entry in
`price-licences.json`. That manifest is deliberately empty: legacy Yahoo-derived
prices do not establish permission. Missing quotes/licences and ambiguous assets
are listed by reason in `connections-report.json`. Existing saved articles and
connections were not rewritten during this task. No live API was modified.

The current replay of 360 real saved articles resolves **zero** additional
impacts. This is a blocker report, not a claim of improved live connectivity.
Tests cover actual archived articles from Nigeria, Tanzania, Malaysia, Angola,
Kenya, Ghana, Brazil, Indonesia, Pakistan and Vietnam; none gains a guessed or
unlicensed link. A separate test proves an explicit company impact resolves to
its exact real registry asset and saved price when test-only licence metadata
is supplied, and fails without that metadata.

`NEWS_CONNECTIONS_ENABLED=true` is an optional repository variable (no secret).
Default is off. The hourly schedule, 200-candidate budget and ten-minute timeout
are unchanged. Dry replay takes about 0.05 seconds locally, **0 Gemini calls**;
when enabled the pipeline adds one bounded local subprocess (30-second timeout).
No added Actions minutes while off; actual hosted CPU timing must be measured
after source licensing is verified. Do not infer Gemini spend from this local
resolver: it makes no model calls.
