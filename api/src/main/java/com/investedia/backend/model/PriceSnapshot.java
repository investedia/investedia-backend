package com.investedia.backend.model;

import java.time.Instant;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

public record PriceSnapshot(Instant asOf, Map<String, PriceRow> prices) {
    public PriceSnapshot {
        prices = Collections.unmodifiableMap(new LinkedHashMap<>(prices));
    }
}
