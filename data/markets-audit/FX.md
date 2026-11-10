# Currency relationships feasibility

Not investment advice. This is **co-movement, not capital flows and not causation**.

The sample output is `fx-sample.json`. Locally it has no invented pairs/values:
no dated ECB snapshot was downloaded here. The manual runner can compute the
same output from official 90-day XML, still audit-only pending primary terms.
The old undated/22-value price sparklines cannot support this method.

Use ECB publication dates, not calendar-day forward filling. Keep the latest
31 publication dates to obtain at most **30 simple-return observations**:
`r[t] = price[t] / price[t-1] - 1`. A missing currency quote removes that exact
return interval; a multi-day gap is never treated as a one-day return. Join
pairs on both interval endpoints and require **at least 25 aligned returns**.
Pearson on those returns; constant/near-zero-variance series produce null, not 0.
Report |r| >= 0.70 in separate positive and negative lists, with base, interval
count, as-of date and threshold. Smaller overlaps do not get promoted to lines.

Compare both:

- EUR quote: units X per EUR (the ECB original convention).
- USD rebasing: `X/USD = (X/EUR) / (USD/EUR)`, applied to levels BEFORE returns.

The common EUR denominator can induce apparent co-movement. USD rebasing changes
the common denominator; it does not remove all mechanical base effects. The
runner reports all comparable pair deltas, sign changes and threshold-qualified
pairs for both bases. **Recommend USD-rebased for the stock-first launch**, with
“Base: USD” visible and EUR sensitivity retained in the method detail. This is a
product convention aligned with USD-denominated comparison, not a claim that USD
is mathematically neutral. Measure sensitivity on the fetched sample before approval.

The base currency has zero variance in its own base and is excluded naturally.
One node per ISO4217 code means euro-area countries do not generate duplicate
EUR–EUR edges. Explicit low-information exclusions: DKK–EUR and HKD–USD (owner
examples). Verify current regimes with Denmark's Nationalbank/HKMA before launch;
these exclusions are policy inputs, not a freshly verified claim about 2026 pegs.
No non-ECB currency, shared-currency country pair, made-up price or extrapolation.

The frontend proposal caps visible currency lines at five PC / three phone,
separate from corporate relationships. That UI is not built here. Methodological
checks use **synthetic mathematical fixtures only**; they are never exported as
real market sample data. A short/no response stays insufficient/null with reason.
