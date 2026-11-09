package com.investedia.backend.service;

import com.investedia.backend.dto.ApiEnvelope;
import com.investedia.backend.exception.SnapshotUnavailableException;
import com.investedia.backend.exception.UnknownGroupException;
import com.investedia.backend.repository.MarketRepository;
import java.time.Clock;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class MarketService {
    private final MarketRepository repository;
    private final Clock clock;

    public MarketService(MarketRepository repository, Clock clock) {
        this.repository = repository;
        this.clock = clock;
    }

    public ApiEnvelope<Map<String, List<Number>>> prices(String group) {
        var snapshot = repository.latest();
        var groups = repository.symbolGroups();
        if (!group.equals("all") && !groups.containsKey(group)) {
            var allowed = new ArrayList<>(List.of("all"));
            allowed.addAll(groups.keySet());
            throw new UnknownGroupException(allowed);
        }
        Map<String, List<Number>> rows = new LinkedHashMap<>();
        var symbols = group.equals("all") ? snapshot.prices().keySet() : groups.get(group);
        for (String symbol : symbols) {
            var price = snapshot.prices().get(symbol);
            if (price != null) rows.put(symbol, List.of(price.price(), price.changePercent(),
                    price.providerTimeMillis(), snapshot.asOf().toEpochMilli()));
        }
        var meta = SnapshotMetadata.at(snapshot.asOf(), clock.instant(), "yahoo-spark", 15);
        meta.put("group", group);
        meta.put("count", rows.size());
        meta.put("format", List.of("price", "change_pct", "provider_time_ms", "fetched_at_ms"));
        return new ApiEnvelope<>(rows, meta);
    }

    public Map<String, Object> status() {
        Map<String, Object> status = new LinkedHashMap<>();
        status.put("now", SnapshotMetadata.iso(clock.instant()));
        try {
            var snapshot = repository.latest();
            status.put("prices", Map.of("fetched_at", SnapshotMetadata.iso(snapshot.asOf()),
                    "age_s", Math.round((clock.millis() - snapshot.asOf().toEpochMilli()) / 1000.0),
                    "symbols", snapshot.prices().size(), "provider", "yahoo-spark"));
        } catch (SnapshotUnavailableException exception) {
            status.put("prices", null);
        }
        // This JVM does not have Cloudflare KV/cron budgets; never invent those statistics.
        status.put("kv", null);
        status.put("cron", null);
        status.put("limits", null);
        status.put("version", 1);
        status.put("backend", "spring");
        status.put("mode", "read-only-snapshots");
        return status;
    }
}
