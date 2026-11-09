package com.investedia.backend.model;

import java.time.Instant;
import java.util.List;
import tools.jackson.databind.JsonNode;

public record NewsSnapshot(Instant asOf, List<JsonNode> articles) {
    public NewsSnapshot {
        articles = List.copyOf(articles);
    }
}
