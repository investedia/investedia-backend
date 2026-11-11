Test-only, synthetic fixtures for `tests/test_gdelt_backfill.py`.
`gkg-sample.csv` mimics the *shape* of a GDELT GKG 2.1 15-minute file (27 tab-separated
columns); `publisher-page.html` mimics a publisher page's metadata. Every URL uses the
reserved `.invalid` domain and every headline starts with "Test-only"; nothing here is a
real article and nothing here is ever ingested.
