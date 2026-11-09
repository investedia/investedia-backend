package com.investedia.backend.controller;

import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SystemController {
    @GetMapping({"/", "/api/health"})
    public Map<String, Object> health() {
        return Map.of("status", "UP", "application", "investedia-backend", "backend", "Spring Boot",
                "mode", "read-only-snapshots", "authentication", "Supabase (unchanged)",
                "endpoints", Map.of("prices", "/v1/prices", "news", "/v1/news", "globe", "/v1/globe",
                        "calls", "/v1/calls", "status", "/v1/status"));
    }

    @PostMapping({"/v1/ingest/news", "/v1/ingest/calls"})
    public ResponseEntity<Map<String, String>> ingestionNotMigrated() {
        return ResponseEntity.status(503).body(Map.of("error", "ingest not configured"));
    }

    @GetMapping("/ticker")
    public ResponseEntity<Map<String, String>> tickerNotMigrated() {
        return ResponseEntity.status(503).body(Map.of("error", "upstream unavailable"));
    }
}
