package com.investedia.backend.repository.file;

import com.investedia.backend.exception.SnapshotUnavailableException;
import com.investedia.backend.model.PriceRow;
import com.investedia.backend.model.PriceSnapshot;
import com.investedia.backend.repository.MarketRepository;
import java.nio.charset.StandardCharsets;
import java.io.IOException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import org.springframework.stereotype.Repository;
import org.springframework.core.io.ClassPathResource;
import tools.jackson.databind.ObjectMapper;

@Repository
public class FileMarketRepository implements MarketRepository {
    private static final Pattern WRAPPER = Pattern.compile("(?s)^\\s*window\\.QUOTES\\s*=\\s*(\\{.*})\\s*;?\\s*$");
    private final JsonSnapshotReader reader;
    private final Map<String, List<String>> groups;

    public FileMarketRepository(JsonSnapshotReader reader, ObjectMapper mapper) {
        this.reader = reader;
        Map<String, List<String>> catalog = new LinkedHashMap<>();
        try (var input = new ClassPathResource("worker-symbol-groups.json").getInputStream()) {
            mapper.readTree(input).properties().forEach(entry -> {
                List<String> symbols = new ArrayList<>();
                entry.getValue().forEach(symbol -> symbols.add(symbol.asText()));
                catalog.put(entry.getKey(), List.copyOf(symbols));
            });
        } catch (IOException exception) {
            throw new IllegalStateException("Symbol catalog unavailable", exception);
        }
        this.groups = Collections.unmodifiableMap(catalog);
    }

    @Override
    public PriceSnapshot latest() {
        try {
            var wrapper = WRAPPER.matcher(new String(reader.bytes("assets/quotes.js"), StandardCharsets.UTF_8));
            if (!wrapper.matches()) throw new SnapshotUnavailableException();
            var data = reader.parse(wrapper.group(1).getBytes(StandardCharsets.UTF_8));
            Instant asOf = Instant.parse(data.path("updated").asText());
            var quotes = data.path("q");
            if (!quotes.isObject()) throw new SnapshotUnavailableException();
            Map<String, PriceRow> prices = new LinkedHashMap<>();
            quotes.properties().forEach(entry -> {
                var quote = entry.getValue();
                if (quote.path("p").isNumber() && quote.path("d").isNumber()) {
                    prices.put(entry.getKey(), new PriceRow(quote.path("p").decimalValue(),
                            quote.path("d").decimalValue(), quote.path("t").asLong(0) * 1000));
                }
            });
            if (prices.isEmpty()) throw new SnapshotUnavailableException();
            return new PriceSnapshot(asOf, prices);
        } catch (RuntimeException exception) {
            throw new SnapshotUnavailableException();
        }
    }

    @Override
    public Map<String, List<String>> symbolGroups() {
        return groups;
    }
}
