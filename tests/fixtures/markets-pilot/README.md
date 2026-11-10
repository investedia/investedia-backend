Synthetic offline identity fixture only. NEVER publish or interpret counts as
market coverage. Unit names, ticker pairs, dates and relationships are invented
for test cases. A few publicly documented reference identifiers exercise actual
ISIN/LEI checksums; they do not make these artificial listings real. Missing
identifiers stay null. `snapshot.fixture=true` prevents publication.

The Worker fixture is generated from this input by `build()` and contains the
same fixture flag. Worker unit tests simulate the publication boundary only in
memory; the production publisher refuses these artifacts.
