"""Each adapter reads retained raw input; fetches are explicit and licence-gated."""
from . import wikidata, gem, world_bank, eia, nga, ourairports, wri, commons
ADAPTERS = {m.SOURCE: m for m in (wikidata, gem, world_bank, eia, nga, ourairports, wri, commons)}
