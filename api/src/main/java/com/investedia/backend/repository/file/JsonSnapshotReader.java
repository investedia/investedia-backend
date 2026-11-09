package com.investedia.backend.repository.file;

import com.investedia.backend.config.RepositoryProperties;
import com.investedia.backend.exception.SnapshotUnavailableException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@Component
public class JsonSnapshotReader {
    private final Path root;
    private final ObjectMapper mapper;

    public JsonSnapshotReader(RepositoryProperties properties, ObjectMapper mapper) {
        this.root = Path.of(properties.repositoryRoot()).toAbsolutePath().normalize();
        this.mapper = mapper;
    }

    public byte[] bytes(String relativePath) {
        try {
            Path file = root.resolve(relativePath).normalize().toRealPath();
            if (!file.startsWith(root.toRealPath())) throw new SnapshotUnavailableException();
            return Files.readAllBytes(file);
        } catch (IOException | SecurityException exception) {
            throw new SnapshotUnavailableException();
        }
    }

    public JsonNode json(String relativePath) {
        return parse(bytes(relativePath));
    }

    public JsonNode parse(byte[] bytes) {
        try {
            JsonNode value = mapper.readTree(bytes);
            if (value == null || !value.isObject()) throw new SnapshotUnavailableException();
            return value;
        } catch (RuntimeException exception) {
            throw new SnapshotUnavailableException();
        }
    }
}
