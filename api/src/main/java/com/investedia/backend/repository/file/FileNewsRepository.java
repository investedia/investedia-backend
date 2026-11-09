package com.investedia.backend.repository.file;

import com.investedia.backend.exception.SnapshotUnavailableException;
import com.investedia.backend.model.NewsSnapshot;
import com.investedia.backend.repository.NewsRepository;
import java.time.Instant;
import java.util.ArrayList;
import org.springframework.stereotype.Repository;
import tools.jackson.databind.JsonNode;

@Repository
public class FileNewsRepository implements NewsRepository {
    private final JsonSnapshotReader reader;
    public FileNewsRepository(JsonSnapshotReader reader) { this.reader = reader; }

    @Override
    public NewsSnapshot latest() {
        try {
            var feed = reader.json("assets/globe/news-live.json");
            if (!feed.path("stories").isArray() || feed.path("stories").isEmpty()) {
                throw new SnapshotUnavailableException();
            }
            var articles = new ArrayList<JsonNode>();
            feed.path("stories").forEach(articles::add);
            return new NewsSnapshot(Instant.parse(feed.path("updated_at").asText()), articles);
        } catch (RuntimeException exception) {
            throw new SnapshotUnavailableException();
        }
    }
}
