package com.investedia.backend.service;

import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeFormatterBuilder;
import java.util.LinkedHashMap;
import java.util.Map;

final class SnapshotMetadata {
    private static final DateTimeFormatter ISO = new DateTimeFormatterBuilder().appendInstant(3).toFormatter();
    private SnapshotMetadata() {}

    static String iso(Instant instant) { return ISO.format(instant); }

    static Map<String, Object> at(Instant asOf, Instant now, String provider, int ttl) {
        long age = Duration.between(asOf, now).toMillis();
        Map<String, Object> meta = new LinkedHashMap<>();
        meta.put("state", age <= 360_000 ? "delayed" : "stale");
        meta.put("fetched_at", iso(asOf));
        meta.put("age_s", Math.round(age / 1000.0));
        meta.put("provider", provider);
        meta.put("licensed", false);
        meta.put("ttl_s", ttl);
        meta.put("upstream_ok", age <= 360_000);
        meta.put("version", 1);
        return meta;
    }
}
