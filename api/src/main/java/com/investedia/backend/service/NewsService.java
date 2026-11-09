package com.investedia.backend.service;

import com.investedia.backend.dto.ApiEnvelope;
import com.investedia.backend.repository.NewsRepository;
import java.time.Clock;
import java.util.Comparator;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;

@Service
public class NewsService {
    private final NewsRepository repository;
    private final Clock clock;

    public NewsService(NewsRepository repository, Clock clock) {
        this.repository = repository;
        this.clock = clock;
    }

    public ApiEnvelope<Map<String, List<JsonNode>>> news() {
        var snapshot = repository.latest();
        var newest = snapshot.articles().stream()
                .sorted(Comparator.comparing((JsonNode article) -> article.path("published_at").asText()).reversed())
                .limit(40).toList();
        var articles = new ArrayList<>(newest);
        // The existing Worker ingest reverses equal-time runs after the robot selects its newest 40.
        // Preserve that observed ordering; the cross-runtime contract test exercises actual saved ties.
        for (int start = 0; start < articles.size();) {
            int end = start + 1;
            String time = articles.get(start).path("published_at").asText();
            while (end < articles.size() && articles.get(end).path("published_at").asText().equals(time)) end++;
            Collections.reverse(articles.subList(start, end));
            start = end;
        }
        var meta = SnapshotMetadata.at(snapshot.asOf(), clock.instant(), "rss+gemini", 30);
        meta.put("count", articles.size());
        meta.put("model", "github-ingest");
        meta.put("note", "newest AI-enriched priority articles; the client merges them with the static broad feed");
        return new ApiEnvelope<>(Map.of("stories", List.copyOf(articles)), meta);
    }

    public ApiEnvelope<Map<String, List<Map<String, Object>>>> globe() {
        var news = news();
        var events = news.data().get("stories").stream().map(article -> {
            Map<String, Object> event = new LinkedHashMap<>();
            for (String key : List.of("id", "headline", "category", "importance", "market_moving", "published_at")) {
                if (article.has(key)) event.put(key, article.get(key));
            }
            for (String key : List.of("place", "country", "lat", "lon")) {
                if (article.path("location").has(key)) event.put(key, article.path("location").get(key));
            }
            if (article.path("source").has("name")) event.put("source", article.path("source").get("name"));
            return event;
        }).toList();
        return new ApiEnvelope<>(Map.of("events", events), news.meta());
    }
}
